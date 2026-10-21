#!/usr/bin/env python3
"""termostaatti_smoke.py — lämmittimen jakso aikaan sidottuna (käyttäjä 21.10.2026: lämmitys "levoton").

4b0a529 lyhensi pääsilmukan kierroksen ~5 ms:iin, ja kierroksina laskettu 10 askeleen jakso kutistui
50–300 ms:iin. Testi ajaa firmwaren `Thermostat`- ja `HeatingSpeedCalculator`-luokkia CPythonilla
valekellolla 5 ms:n kierroksin ja tarkistaa jakson pituuden, minimiajat ja lämmitysnopeuden ikkunan.

    python3 testit/termostaatti_smoke.py     RESULT: <n> failed, epänolla paluuarvo jos punaisia
"""

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.environ.get('FW') or os.path.join(HERE, '..', 'pico')
sys.path.insert(0, FW)
sys.modules.setdefault('utime', types.ModuleType('utime'))
import classes as C

FAILED = []
clock = [0]


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info else ''))
    if not ok:
        FAILED.append(name)


class U:
    ticks_ms = staticmethod(lambda: clock[0])
    ticks_diff = staticmethod(lambda a, b: a - b)
    ticks_add = staticmethod(lambda a, b: a + b)


class Relay:
    def __init__(self):
        self.v = 0
        self.writes = 0

    def value(self, x=None):
        if x is None:
            return self.v
        self.v = 1 if x else 0
        self.writes += 1


class Sensor:
    def __init__(self):
        self.t = 95.0

    def read_temperature(self):
        return self.t


class BD:
    def __init__(self, mode, target, sensor, speed):
        self.mode, self.target, self.sensor, self.calc = mode, target, sensor, speed

    def get_mode(self):
        return self.mode

    def get_target_temperature(self):
        return self.target

    def get_heating_speed(self):
        return self.calc.get_heating_speed(self.sensor.t)


def runs(mode, temp, target=98.0, dur_ms=20000, pass_ms=5):
    """Fixed temperature, heating speed 0: returns relay on-fraction and on/off run lengths (ms)."""
    clock[0] = 0
    sensor = Sensor()
    sensor.t = temp
    calc = C.HeatingSpeedCalculator(U, None)
    relay = Relay()
    th = C.Thermostat(BD(mode, target, sensor, calc), {}, relay, sensor, U)
    trace = []
    while clock[0] < dur_ms:
        th.run()
        trace.append(relay.v)
        clock[0] += pass_ms
    lengths, cur, n = [], trace[0], 0
    for v in trace:
        if v == cur:
            n += 1
        else:
            lengths.append((cur, n * pass_ms))
            cur, n = v, 1
    inner = lengths[1:]  # the first run starts at t=0, not at an edge
    on = sum(trace) / len(trace)
    return on, inner, relay.writes, len(trace)


# 1. IDLE: 5 s cycle, 500 ms steps; 2.7 C below target -> 3/10 steps on (cycler: 10 % per 0.9 C)
on, inner, writes, passes = runs('IDLE', 95.3)
switches = sum(1 for v, _ in inner if v == 1)
check('A1 IDLE: osuus ~30 %', abs(on - 0.30) < 0.03, '%.3f' % on)
check('A2 IDLE: lyhin päällä/pois-jakso >= 500 ms', inner and min(l for _, l in inner) >= 500, min(l for _, l in inner) if inner else None)
check('A3 IDLE: päällekytkentöjä 20 s:ssa 3-4 (5 s jakso)', 3 <= switches <= 4, switches)
check('A4 rele kirjoitetaan joka kierroksella (vartio näkee)', writes == passes, '%d/%d' % (writes, passes))

# 2. other modes: 2 s cycle, 200 ms steps
on, inner, _, _ = runs('STEAM', 95.3)
switches = sum(1 for v, _ in inner if v == 1)
check('B1 STEAM: lyhin jakso >= 200 ms', inner and min(l for _, l in inner) >= 200, min(l for _, l in inner) if inner else None)
check('B2 STEAM: päällekytkentöjä 20 s:ssa 9-10 (2 s jakso)', 9 <= switches <= 10, switches)

# 3. at or above target: never on; far below: always on
on, _, _, _ = runs('IDLE', 98.5)
check('C1 tavoitteen yllä rele ei koskaan päällä', on == 0, on)
on, _, _, _ = runs('IDLE', 85.0)
check('C2 13 C alle tavoitteen rele aina päällä', on == 1, on)

# 4. heating speed: called twice per 5 ms pass, reading steps every 250 ms at 0.2 C/s
clock[0] = 0
calc = C.HeatingSpeedCalculator(U, None)
true_t, vals = 90.0, []
reading = true_t
while clock[0] < 12000:
    if clock[0] % 250 == 0:
        reading = round(true_t, 2)
    for _ in range(2):
        vals.append(calc.get_heating_speed(reading))
    true_t += 0.2 * 5 / 1000
    clock[0] += 5
late = vals[len(vals) // 4:]
check('D1 nopeus vakaa: ei nollia eikä piikkejä lämmitettäessä (0,2 C/s = 2,0 / 10 s)',
      min(late) > 1.5 and max(late) < 2.5, 'min %.2f max %.2f' % (min(late), max(late)))
changes = sum(1 for a, b in zip(late, late[1:]) if a != b)
check('D2 nopeus päivittyy enintään 2 s välein', changes <= len(late) * 5 / 2000 / 2 + 2, changes)

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
