"""max31865_osat_smoke.py — pico/lib/adafruit_max31865.py rtd_part CPythonilla (EXPRESSO-C1-JAKSOT vaihe 2, K3, 20.10.2026).

    python3 testit/max31865_osat_smoke.py     RESULT: <n> failed

Simuloitu MAX31865 (rekisterit, osoitteen automaattinen kasvu, CS-kehys) tarkistaa, että osat 0-6 tekevät saman kuin
rtd_start + rtd_convert + rtd_result: bias paalle ja viat nollaksi, yksi muunnos, sama raakalukema. Jokainen osa siirtaa
enintaan yhden tavun, CS on ylhaalla osien 1, 3 ja 6 jalkeen, eika rtd_part varaa muistia (puskurit __init__ista).
"""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pico', 'lib'))

fails = 0


def check(name, ok, info=''):
    global fails
    print(('ok   ' if ok else 'FAIL ') + name + ('' if ok else '  ' + repr(info)))
    if not ok:
        fails += 1


class Chip:
    """MAX31865: register file, a frame starts at CS low with the address byte; reads auto-increment."""
    def __init__(self):
        self.reg = [0] * 8
        self.reg[0] = 0x01                    # 50 Hz filter at power-up
        self.reg[1], self.reg[2] = 0x5A, 0x3C  # RTD MSB/LSB (bit 0 = fault)
        self.cs = 1
        self.addr = None
        self.write = False
        self.oneshots = 0
        self.faultclears = 0
        self.part_bytes = 0

    def select(self, v):
        if v == 0 and self.cs == 1:
            self.addr = None
        self.cs = v

    def tx(self, data):
        assert self.cs == 0, 'transfer with CS high'
        for b in data:
            self.part_bytes += 1
            if self.addr is None:
                self.addr, self.write = b & 0x7F, bool(b & 0x80)
            elif self.write:
                if self.addr == 0:
                    if b & 0x20:
                        self.oneshots += 1
                    if b & 0x02:
                        self.faultclears += 1
                    b &= ~0x22                 # 1-shot and fault clear bits clear themselves
                self.reg[self.addr] = b
                self.addr += 1

    def rx(self, buf):
        assert self.cs == 0, 'read with CS high'
        for i in range(len(buf)):
            self.part_bytes += 1
            buf[i] = self.reg[self.addr]
            self.addr += 1


chip = Chip()


class SPI:
    def __init__(self, *a, **k):
        pass

    def write(self, b):
        chip.tx(bytes(b))

    def readinto(self, b):
        chip.rx(b)

    def read(self, n):
        b = bytearray(n)
        chip.rx(b)
        return b


class Pin:
    OUT, IN = 1, 0

    def __init__(self, n, mode=None, value=None):
        self.n = n
        if value is not None and n == 5:
            chip.select(value)

    def value(self, v=None):
        if v is None:
            return chip.cs
        if self.n == 5:
            chip.select(v)


sys.modules['machine'] = types.SimpleNamespace(SPI=SPI, Pin=Pin)
sys.modules['micropython'] = types.SimpleNamespace(const=lambda x: x)

import adafruit_max31865 as M  # noqa: E402

drv = M.MAX31865(wires=3, pin_sck=6, pin_mosi=3, pin_miso=4, pin_cs=5)
cfg0 = chip.reg[0]
check('init: 3-wire, filter kept, bias and auto off', cfg0 == 0x11, hex(cfg0))

# the reference: the three whole steps
chip.reg[0] |= 0x0C                           # fault detection bits left set: rtd_start clears them
drv.rtd_start()
ref_bias = chip.reg[0]
drv.rtd_convert()
ref_raw = drv.rtd_result()
ref = (ref_bias, chip.oneshots, chip.faultclears)

chip.reg[0] = cfg0 | 0x0C
chip.oneshots = chip.faultclears = 0
raws, cs_after, nbytes = [], [], []
for k in range(7):
    chip.part_bytes = 0
    raws.append(drv.rtd_part(k))
    cs_after.append(chip.cs)
    nbytes.append(chip.part_bytes)
    if k == 1:
        part_bias = chip.reg[0]

check('parts: bias on, faults cleared, fault detection off as rtd_start', part_bias == ref[0] == 0x91,
      (hex(part_bias), hex(ref[0])))
check('parts: one conversion and one fault clear', (chip.oneshots, chip.faultclears) == (1, 1) == ref[1:],
      (chip.oneshots, chip.faultclears, ref))
check('parts: part 6 returns the raw reading of rtd_result, others -1', raws[6] == ref_raw == (0x5A3C >> 1)
      and raws[:6] == [-1] * 6, (raws, ref_raw))
check('parts: one byte each (K3)', nbytes == [1] * 7, nbytes)
check('parts: CS up after parts 1, 3 and 6 only', cs_after == [0, 1, 0, 1, 0, 0, 1], cs_after)
check('parts: bias stays on after the reading (as read_rtd)', chip.reg[0] & 0x80 and not chip.reg[0] & 0x20, hex(chip.reg[0]))

# no allocation: the part buffers are the ones made in __init__
ids = [id(drv._pw), id(drv._pb), id(drv._pc), id(drv._pr), id(drv._pm), id(drv._pl)]
for k in range(7):
    drv.rtd_part(k)
check('parts: buffers from __init__ only', ids == [id(drv._pw), id(drv._pb), id(drv._pc), id(drv._pr), id(drv._pm),
                                                   id(drv._pl)])
src = open(os.path.join(HERE, '..', 'pico', 'lib', 'adafruit_max31865.py')).read()
body = src[src.index('def rtd_part'):src.index('@property', src.index('def rtd_part'))]
check('parts: no bytes(), bytearray() or list in rtd_part', not any(w in body for w in ('bytes(', 'bytearray(', '[0]*')),
      body)

print('RESULT: %d failed' % fails)
sys.exit(1 if fails else 0)
