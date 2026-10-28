# eXpresso

Firmware and development tools for a Raspberry Pi Pico 2 W that controls an espresso machine
(boiler, pump, solenoid, pressure, scale). MicroPython on the Pico, Python 3 tools on a host.

## Layout

- `pico/` firmware that runs on the Pico (`main.py`, `boot.py`, `lib/`, `MANIFEST.json` = SHA-256 of every file)
- `pico_dev.py` host tool: flash, verify, send commands, capture shots over a serial link
- `build_set.py` builds a firmware set on an Android phone (phone link only)
- `diagnet/` optional diagnostics: the Pico sends UDP packets over Wi-Fi to a collector (`keraaja.py`)
- `testit/` offline tests (`*_smoke.py`) and analysis/simulation scripts
- `scale/` hardware tests for the scale (see below)

## Flashing with pico_dev.py

The Pico is reached over a serial link. Default (`PICO_LINK=zero`): a small Linux host
(for example a Raspberry Pi Zero) has the Pico on USB and serves it as raw TCP with ser2net
(`<host>:2217`). `PICO_LINK=phone` is the older route through an Android phone and adb.

```
export PICO_ZERO=<address of the host that has the Pico on USB>   # default 192.0.2.10 is only an example
python3 pico_dev.py verify pico/MANIFEST.json     # compare the Pico's files with the manifest
python3 pico_dev.py flash pico/MANIFEST.json      # write changed files, check SHA-256, reset
python3 pico_dev.py safe                          # relays off, read back, reset
python3 pico_dev.py cmd <command> [seconds]       # send CMD <command> to the running firmware
```

`python3 pico_dev.py` without arguments prints the full usage. Every operation first drives the
relays off and verifies it. After editing files in `pico/` run `python3 pico_dev.py manifest pico/MANIFEST.json`.
Wi-Fi credentials go in `secrets.py` on the Pico (not in this repository, listed in `.gitignore`).

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `PICO_LINK` | `zero` | `zero` = TCP via ser2net, `phone` = adb and the phone app |
| `PICO_ZERO` | `192.0.2.10` | host of the ser2net link (port 2217) |
| `PICO_PHONE` | `192.0.2.11:5555` | adb address of the phone (phone link only) |
| `PICO_ADB` | search PATH | path to adb |
| `PICO_CHARGER_CYCLE` | off | `1` = cut the hub's charger through Home Assistant during USB operations (phone link only; needs `../ha/ha.sh`) |
| `PICO_DEV_LOCK` | `/tmp/pico_dev.lock` | lock file, one run at a time per machine |
| `DIAGNET_PORTTI`, `DIAGNET_OSOITE`, `DIAGNET_TILA` | 47210, `0.0.0.0`, `~/.local/state/expresso-diag` | diagnostics collector |
| `HA_URL`, `HA_TOKEN_FILE` | `http://192.0.2.12:8123`, `~/.config/ha/token` | Home Assistant for the collector (optional) |

The addresses `192.0.2.x` are RFC 5737 documentation addresses, replace them with your own.

## Offline tests

The tests run on any machine with Python 3, without a Pico:

```
python3 testit/<name>_smoke.py        # prints OK/FAIL lines and a RESULT line, exit code 0 = pass
```

The other scripts in
`testit/` (`*_sim.py`, `*_probe.py`, `shot_*`, `tray_calib.py`, ...) analyse logs or talk to real hardware.

## scale/

Tests for the scale and the first-drop detector: `scale/testit/*.py`. They import the firmware modules
from `pico/` and some need a running machine on the network.
