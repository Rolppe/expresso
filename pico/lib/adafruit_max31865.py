#
# Copyright (c) 2017 Tony DiCola for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_max31865`
====================================================MicroPython module for the MAX31865 platinum RTD temperature sensor.  See
examples/simpletest.py for an example of the usage.* Author(s): Tony DiCola, original CircuitPython version
             Chris Osterwood, port _read and _write methods to MicroPython
"""
import machine
import math
import time
from micropython import const
import spi_device

#pylint: disable=bad-whitespace
# Register and other constant values:
_MAX31865_CONFIG_REG          = const(0x00)
_MAX31865_CONFIG_BIAS         = const(0x80)
_MAX31865_CONFIG_MODEAUTO     = const(0x40)
_MAX31865_CONFIG_MODEOFF      = const(0x00)
_MAX31865_CONFIG_1SHOT        = const(0x20)
_MAX31865_CONFIG_3WIRE        = const(0x10)
_MAX31865_CONFIG_24WIRE       = const(0x00)
_MAX31865_CONFIG_FAULTSTAT    = const(0x02)
_MAX31865_CONFIG_FILT50HZ     = const(0x01)
_MAX31865_CONFIG_FILT60HZ     = const(0x00)
_MAX31865_RTDMSB_REG          = const(0x01)
_MAX31865_RTDLSB_REG          = const(0x02)
_MAX31865_HFAULTMSB_REG       = const(0x03)
_MAX31865_HFAULTLSB_REG       = const(0x04)
_MAX31865_LFAULTMSB_REG       = const(0x05)
_MAX31865_LFAULTLSB_REG       = const(0x06)
_MAX31865_FAULTSTAT_REG       = const(0x07)
_MAX31865_FAULT_HIGHTHRESH    = const(0x80)
_MAX31865_FAULT_LOWTHRESH     = const(0x40)
_MAX31865_FAULT_REFINLOW      = const(0x20)
_MAX31865_FAULT_REFINHIGH     = const(0x10)
_MAX31865_FAULT_RTDINLOW      = const(0x08)
_MAX31865_FAULT_OVUV          = const(0x04)
_RTD_A = 3.9083e-3
_RTD_B = -5.775e-7
#pylint: enable=bad-whitespace

class MAX31865:
    """Driver for the MAX31865 thermocouple amplifier."""
    def __init__(
        self, rtd_nominal=100, ref_resistor=430.0, wires=3,
        pin_sck = None, pin_mosi = None, pin_miso = None, pin_cs = None
        ):

        if None in (pin_sck, pin_mosi, pin_miso, pin_cs):
            raise Exception('Provide GPIO-pins for leads')

        sck  = machine.Pin(6, machine.Pin.OUT)
        mosi = machine.Pin(3, machine.Pin.IN)
        miso = machine.Pin(4, machine.Pin.OUT)
        spi  = machine.SPI(0, baudrate=50000, sck=sck, mosi=mosi, miso=miso, polarity=0, phase=1)
        cs = machine.Pin(5, machine.Pin.OUT, value=1)        

        self.rtd_nominal = rtd_nominal
        self.ref_resistor = ref_resistor
        self._device = spi_device.SPIDevice(spi, cs)# Set wire config register based on the number of wires specified.
        # rtd_start/rtd_convert/rtd_result buffers: the reads run on core 1 with the heap locked (classes.TemperatureSensor)
        self._na, self._nw, self._nr1, self._nr2 = bytearray(1), bytearray(2), bytearray(1), bytearray(2)
        if wires not in (2, 3, 4):
            raise ValueError('Wires must be a value of 2, 3, or 4!')
        config = self._read_u8(_MAX31865_CONFIG_REG)
        if wires == 3:
            config |= _MAX31865_CONFIG_3WIRE
        else:
            # 2 or 4 wire
            config &= ~_MAX31865_CONFIG_3WIRE
        self._write_u8(_MAX31865_CONFIG_REG, config)# Default to no bias and no auto conversion.
        self.set_bias(False)
        self.set_auto_convert(False)
        # rtd_part buffers: the config register without bias, one-shot, fault detection and fault clear bits, as left
        # above; nothing changes it later except bias, which rtd_part sets itself
        cfg = self._read_u8(_MAX31865_CONFIG_REG) & ~(_MAX31865_CONFIG_BIAS | 0x2C | _MAX31865_CONFIG_FAULTSTAT)
        self._pw = bytearray([_MAX31865_CONFIG_REG | 0x80])
        self._pb = bytearray([cfg | _MAX31865_CONFIG_BIAS | _MAX31865_CONFIG_FAULTSTAT])
        self._pc = bytearray([cfg | _MAX31865_CONFIG_BIAS | _MAX31865_CONFIG_1SHOT])
        self._pr = bytearray([_MAX31865_RTDMSB_REG])
        self._pm, self._pl = bytearray(1), bytearray(1)

    def _read_u8(self, address):
        # Read an 8-bit unsigned value from the specified 8-bit address.
        with self._device as device:
            device.write(bytes([address & 0x7F]))
            buf = device.read(1)
        return buf[0]
    
    def _read_u16(self, address):
        # Read a 16-bit BE unsigned value from the specified 8-bit address.
        with self._device as device:
            device.write(bytes([address & 0x7F]))
            buf = device.read(2)
        return (buf[0] << 8) | buf[1]

    def _write_u8(self, address, val):
        # Write an 8-bit unsigned value to the specified 8-bit address.
        with self._device as device:
            buf = bytearray(2)
            buf[0] = (address | 0x80) & 0xFF
            buf[1] = val & 0xFF
            device.write(buf)

    @property
    def bias(self):
        """Get and set the boolean state of the sensor's bias (True/False)."""
        return bool(self._read_u8(_MAX31865_CONFIG_REG) & _MAX31865_CONFIG_BIAS)

    def set_bias(self, val):
        config = self._read_u8(_MAX31865_CONFIG_REG)
        if val:
            config |= _MAX31865_CONFIG_BIAS  # Enable bias.
        else:
            config &= ~_MAX31865_CONFIG_BIAS  # Disable bias.
        self._write_u8(_MAX31865_CONFIG_REG, config)

    @property
    def auto_convert(self):
        """Get and set the boolean state of the sensor's automatic conversion
        mode (True/False).
        """
        return bool(self._read_u8(_MAX31865_CONFIG_REG) & _MAX31865_CONFIG_MODEAUTO)

    def set_auto_convert(self, val):
        config = self._read_u8(_MAX31865_CONFIG_REG)
        if val:
            config |= _MAX31865_CONFIG_MODEAUTO   # Enable auto convert.
        else:
            config &= ~_MAX31865_CONFIG_MODEAUTO  # Disable auto convert.
        self._write_u8(_MAX31865_CONFIG_REG, config)

    @property
    def fault(self):
        """Get the fault state of the sensor.  Use `clear_faults` to clear the
        fault state.  Returns a 6-tuple of boolean values which indicate if any
        faults are present:
            - HIGHTHRESH
            - LOWTHRESH
            - REFINLOW
            - REFINHIGH
            - RTDINLOW
            - OVUV
        """
        faults = self._read_u8(_MAX31865_FAULTSTAT_REG)
        #pylint: disable=bad-whitespace
        highthresh = bool(faults & _MAX31865_FAULT_HIGHTHRESH)
        lowthresh  = bool(faults & _MAX31865_FAULT_LOWTHRESH)
        refinlow   = bool(faults & _MAX31865_FAULT_REFINLOW)
        refinhigh  = bool(faults & _MAX31865_FAULT_REFINHIGH)
        rtdinlow   = bool(faults & _MAX31865_FAULT_RTDINLOW)
        ovuv       = bool(faults & _MAX31865_FAULT_OVUV)
        #pylint: enable=bad-whitespace
        return (highthresh, lowthresh, refinlow, refinhigh, rtdinlow, ovuv)

    def clear_faults(self):
        """Clear any fault state previously detected by the sensor."""
        config = self._read_u8(_MAX31865_CONFIG_REG)
        config &= ~0x2C
        config |= _MAX31865_CONFIG_FAULTSTAT
        self._write_u8(_MAX31865_CONFIG_REG, config)

    def read_rtd(self):
        """Perform a raw reading of the thermocouple and return its 15-bit
        value.  You'll need to manually convert this to temperature using the
        nominal value of the resistance-to-digital conversion and some math.  If you just want
        temperature use the temperature property instead.
        """
        self.clear_faults()
        self.set_bias(True)
        time.sleep(0.01)
        config = self._read_u8(_MAX31865_CONFIG_REG)
        config |= _MAX31865_CONFIG_1SHOT
        self._write_u8(_MAX31865_CONFIG_REG, config)
        time.sleep(0.065)
        rtd = self._read_u16(_MAX31865_RTDMSB_REG)
        # Remove fault bit.
        rtd >>= 1
        return rtd

    # The same reading as read_rtd in three steps without time.sleep and without allocating (EXPRESSO-TEMPSTALE-JA-OLETUS,
    # 28.9.2026): core 1 runs them with the heap locked while a shot runs (classes.TemperatureSensor.c1_*), so every SPI
    # transfer uses the buffers made in __init__. The caller keeps the gaps: bias on >= 10 ms before rtd_convert, and the
    # conversion >= 65 ms before rtd_result.
    def _n_read_u8(self, address):
        dev, a, r = self._device, self._na, self._nr1
        a[0] = address & 0x7F
        dev.chip_select.value(0)
        dev.spi.write(a)
        dev.spi.readinto(r)
        dev.chip_select.value(1)
        return r[0]
    def _n_write_u8(self, address, val):
        dev, w = self._device, self._nw
        w[0] = (address | 0x80) & 0xFF
        w[1] = val & 0xFF
        dev.chip_select.value(0)
        dev.spi.write(w)
        dev.chip_select.value(1)
    def rtd_start(self):
        # clear_faults, then set_bias(True)
        config = self._n_read_u8(_MAX31865_CONFIG_REG)
        config &= ~0x2C
        config |= _MAX31865_CONFIG_FAULTSTAT
        self._n_write_u8(_MAX31865_CONFIG_REG, config)
        config = self._n_read_u8(_MAX31865_CONFIG_REG)
        self._n_write_u8(_MAX31865_CONFIG_REG, config | _MAX31865_CONFIG_BIAS)
    def rtd_convert(self):
        config = self._n_read_u8(_MAX31865_CONFIG_REG)
        self._n_write_u8(_MAX31865_CONFIG_REG, config | _MAX31865_CONFIG_1SHOT)
    def rtd_result(self):
        dev, a, r = self._device, self._na, self._nr2
        a[0] = _MAX31865_RTDMSB_REG
        dev.chip_select.value(0)
        dev.spi.write(a)
        dev.spi.readinto(r)
        dev.chip_select.value(1)
        # Remove fault bit.
        return ((r[0] << 8) | r[1]) >> 1
    # The same reading one byte at a time (EXPRESSO-C1-JAKSOT vaihe 2, K3, 20.10.2026): the SPI runs at 50 kHz, a byte
    # takes 160 us, and rtd_start's four transfers took 2 ms between core 1's 1 ms samples. Parts 0-1 bias on and faults
    # cleared, 2-3 one-shot conversion, 4-6 the result, which part 6 returns (the others -1). The config comes from
    # __init__, so no read-modify-write; CS stays low between the parts of one transfer. Gaps as above: >= 10 ms after
    # part 1, >= 65 ms after part 3.
    def rtd_part(self, k):
        dev = self._device
        if k == 0 or k == 2:
            dev.chip_select.value(0)
            dev.spi.write(self._pw)
        elif k == 1 or k == 3:
            dev.spi.write(self._pb if k == 1 else self._pc)
            dev.chip_select.value(1)
        elif k == 4:
            dev.chip_select.value(0)
            dev.spi.write(self._pr)
        elif k == 5:
            dev.spi.readinto(self._pm)
        else:
            dev.spi.readinto(self._pl)
            dev.chip_select.value(1)
            return ((self._pm[0] << 8) | self._pl[0]) >> 1
        return -1
    @property
    def resistance(self):
        """Read the resistance of the RTD and return its value in Ohms."""
        resistance = self.read_rtd()
        resistance /= 32768
        resistance *= self.ref_resistor
        return resistance

    @property
    def temperature(self):
        """Read the temperature of the sensor and return its value in degrees
        Celsius.
        """
        # This math originates from:
        # http://www.analog.com/media/en/technical-documentation/application-notes/AN709_0.pdf
        # To match the naming from the app note we tell lint to ignore the Z1-4
        # naming.
        return self.temperature_from_rtd(self.read_rtd())

    def temperature_from_rtd(self, rtd):
        """Temperature (C) of a raw 15-bit reading from read_rtd or rtd_result."""
        # pylint: disable=invalid-name
        raw_reading = rtd / 32768 * self.ref_resistor
        Z1 = -_RTD_A
        Z2 = _RTD_A * _RTD_A - (4 * _RTD_B)
        Z3 = (4 * _RTD_B) / self.rtd_nominal
        Z4 = 2 * _RTD_B
        temp = Z2 + (Z3 * raw_reading)
        temp = (math.sqrt(temp) + Z1) / Z4
        if temp >= 0:
            return temp

        # Have to normalize to 100 ohms if temperure is less than 0C for the following math to work
        raw_reading /= self.rtd_nominal
        raw_reading *= 100
        rpoly = raw_reading
        temp = -242.02
        temp += 2.2228 * rpoly
        rpoly *= raw_reading  # square
        temp += 2.5859e-3 * rpoly
        rpoly *= raw_reading  # ^3
        temp -= 4.8260e-6 * rpoly
        rpoly *= raw_reading  # ^4
        temp -= 2.8183e-8 * rpoly
        rpoly *= raw_reading  # ^5
        temp += 1.5243e-10 * rpoly
        return temp
