# Hardware

What the code and the working notes state about the machine and the electronics. There is no schematic or parts list
in the repository, so anything not stated there is not stated here either. Pin numbers are GPIO numbers from
`pico/preset.py` (`PINS`).

## The machine and the controller

| Item | Detail | Source |
|---|---|---|
| Espresso machine | Rancilio Silvia | `REKISTERI.md`, `KEHITYSYHTEYS.md` |
| Controller | Raspberry Pi Pico 2 W (RP2350) | `REKISTERI.md`; the device reports `Raspberry Pi Pico 2 W with RP2350` in `testit/rate_probe.out` |
| Firmware runtime | MicroPython v1.28.0 (build date 2026-04-06) | `testit/rate_probe.out` |
| Mains frequency | 50 Hz; measured 50.1 Hz on the machine on 19.9.2026 | `HISTORIA.md` |

The Pico replaces the machine's own control. It reads the front-panel switches, drives three relays (pump, solenoid
valve, heater) and measures boiler temperature, pressure and the weight of the drip tray.

## Pin map

| Function | GPIO | Notes |
|---|---|---|
| Brew / water / steam switch inputs | 7 / 8 / 9 | inputs with pull-down |
| Switch LEDs (brew / water / steam) | 14 / 15 / 16 | outputs |
| Pump relay | 11 | passes through `GuardedRelay` |
| Solenoid relay | 12 | raw pin, not guarded: opening it only releases pressure |
| Heater relay | 13 | passes through `GuardedRelay` |
| MAX31865 SPI: SCK / MOSI / MISO / CS | 6 / 3 / 4 / 5 | hardware SPI 0 at 50 kHz |
| Pressure transducer (ADC) | 28 | 16-bit ADC reading |
| HX711 data, cell A / cell B | 18 / 20 | defaults in `Scale.__init__` (`pico/scale.py`) |
| HX711 clock (shared by both cells) | 19 | |

`pico/devsafe.py` hard-codes the relay pins `(11, 12, 13)` for the boot-time shutdown; they must stay in step with `PINS`.

## Sensors

**Boiler temperature.** A PT100 resistance thermometer read by a MAX31865 amplifier board in 3-wire mode. `MAX31865_CONFIG`:
nominal resistance 100 ohm, reference resistor 430 ohm. The driver is Adafruit's `adafruit_max31865.py` with `spi_device.py` (both MIT licensed, in
`pico/lib/`), modified: the pins are fixed in the constructor and a step-wise, allocation-free read was added so that core 1 can run the conversion while a shot is running. A full blocking reading takes 75 ms or more.
The reading is averaged over 7 samples. The relay guard treats a reading older than 10 s, or at or above 160 C, as a fault.

**Pressure.** An analogue pressure transducer on ADC pin 28. The code converts the raw 16-bit value with a fixed formula
(`bar = raw16 * 0.000314936 - 3.522929`, described in the code as the factory formula) and then applies a gain and an offset
that are stored in `pressure_cal.json` on the Pico. They are set with the calibration wizard (`pcal:*`) or `pcalset:`. A valid gain is 0.5 to 1.5 and a valid
offset is -3 to 3 bar. The notes say the machine has two pressure gauges: its own gauge sits in the water line after the pump, and a reference gauge was mounted at the group head
together with the restrictor. They cannot be read at the same time, because only one of them is connected to the microcontroller (the notes do not say which).
An open or shorted transducer reads about -3.5 bar, which the relay guard recognises (raw below -1.5 bar for three polls shuts the pump off).

**Drip-tray scale.** Two HX711 load-cell amplifiers (cell A and cell B) share one clock pin. `Scale` reads them by bit-banging, at about 11.6 samples per second
per cell (measured, `pico/scale.py`), sums them with a trim factor, and calibrates with `scale_cal.json`
(`off_a`, `off_b`, `trim_b`, `scale`). A machine without a scale boots normally: `main.py` leaves `tray_scale` as `None` if neither cell answers.
Single-sample noise is about 0.25 g.

## Actuators

- **Pump.** A vibratory pump (the notes call it a "vibration pump"). It gives one stroke per mains cycle, and the code treats one cycle (about 20 ms at 50 Hz) as
  the smallest dose it can give. Much of `pico/functions.py` measures and works around this quantisation.
- **Solenoid valve.** Opened to release group pressure after a shot and to vent for pressure zeroing.
- **Heater.** The boiler heating element, switched time-proportionally by the thermostat.
- **Relays.** The notes name an SSR-40DA solid-state relay in the pump path. Retailers' specifications call the model zero-crossing switching with an 8.3 ms response,
  but the notes record that the same designation is also sold in a random turn-on version, and the check of the label on the unit was dropped from the task list. Treat the
  switching behaviour as measured, not specified: the firmware assumes a mean 5 ms delay after the zero crossing (`EU_C1X_LAG_S` is 25 ms in total).

The relays are the only path to mains power from the firmware. They are driven low in `boot.py` before any other import
and again whenever `main.py` exits, so a reset leaves them off. See `ARCHITECTURE.md`.

## Power, watchdog and wireless

- The hardware watchdog (`machine.WDT`) is set to 8000 ms, near the RP2350 maximum of about 8.3 s. The main loop feeds it once a second. It is started
  by the watchdog task in `main.py`, after boot.
- In the Pi Zero setup the Pico is powered from the Zero's 5 V USB supply continuously, also when the machine itself is off the mains.
  The heater's no-rise latch in `pico/relayguard.py` has a retry rule for exactly this case (a cold start with the boiler at room temperature).
- Wi-Fi is the Pico W's on-board radio. `EXD1` diagnostics and the `EXA1` app link use it; BLE is switched off by default in `preset.py` to
  keep the radio from slowing the control loops.

## Development link: Pi Zero and ser2net

For development the Pico is not attached to a computer directly. The default (`PICO_LINK=zero`) is:

```
dev host --TCP 2217 (ser2net, raw)--> Raspberry Pi Zero --USB-CDC--> Pico
```

- The Pico is plugged into the Pi Zero's USB data port. ser2net on the Zero serves the Pico's USB serial device as raw TCP on port 2217.
  `pico_dev.py` talks to `<PICO_ZERO>:2217` and speaks the MicroPython raw REPL and the `CMD` protocol (`docs/PROTOCOL.md`) over it.
- After the Pico re-enumerates (every flash ends with a reset), ser2net on the Zero stayed silent until the serial device was opened once on the Zero;
  `pico_dev.py` does that itself before each connection (`PICO-HALLINTA.md` section 1; the cause is noted as unproven).
- The earlier route, `PICO_LINK=phone`, put an Android phone between the Pico and the host (USB-OTG, adb, a small bridge app).
  It is kept in `pico_dev.py` and `build_set.py` but not used any more.

The addresses in the repository (`192.0.2.x`) are documentation placeholders; set your own in `local.env`.
