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
# (inside the IDLE PI band +-2 C the PI may hold a small duty above the target; that is section 5)
on, _, _, _ = runs('IDLE', 100.5)
check('C1 IDLE: PI-kaistan yllä rele ei koskaan päällä', on == 0, on)
on, _, _, _ = runs('STEAM', 98.5)
check('C1b STEAM: tavoitteen yllä rele ei koskaan päällä', on == 0, on)
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

# 5. TILAUS-P: IDLE PI on a plant model. Full power 0.6 C/s through a first-order lag, loss 0.024 C/s at
# 98 C (DIAGNET 21.10.2026), sensor read every 250 ms as a 7-reading average of noisy 0.03 C readings.
import random


def plant(lag_s, rate=0.6, start=97.0, dur_s=1800, target=98.0, noise=0.03, seed=1, step_at=None):
    random.seed(seed)
    clock[0] = 0
    sensor = Sensor()
    calc = C.HeatingSpeedCalculator(U, None)
    relay = Relay()
    bd = BD('IDLE', target, sensor, calc)
    th = C.Thermostat(bd, {}, relay, sensor, U)
    T, q, raw = start, 0.0, [start] * 7
    sensor.t = start
    d10, on_runs, cur = [], [], 0
    k = 0.024 / 78.0
    while clock[0] < dur_s * 1000:
        if step_at is not None and clock[0] == step_at * 1000:
            bd.target = target - 8.0     # standby step 98 -> 90
        if clock[0] % 250 == 0:
            raw = raw[1:] + [T + random.gauss(0, noise)]
            sensor.t = round(sum(raw) / 7, 2)
        th.run()
        if relay.v:
            cur += 5
        elif cur:
            on_runs.append(cur)
            cur = 0
        q += (rate * relay.v - q) * 0.005 / lag_s
        T += (q - k * (T - 20.0)) * 0.005
        clock[0] += 5
        if clock[0] % 60000 == 0:
            n, mn, mx = th.take_t10()
            d10.append((clock[0] // 1000, n, mn, mx))
    return d10, on_runs, th


for lag in (10, 20, 40):
    for rate in (0.4, 0.6, 0.8):
        d10, runs_, th = plant(lag, rate)
        settled = [x for x in d10 if x[0] > 600 and x[1]]
        worst = max(max(abs(x[2]), abs(x[3])) for x in settled)
        check('E lag %2d s rate %.1f: 10 s keskiarvot +-0,05 C 10 min jälkeen' % (lag, rate), worst <= 0.05,
              'max |d| %.3f, pi_i %.3f' % (worst, th.pi_i))
d10, runs_, th = plant(20)
check('E2 päällejaksot 50 ms:n monikertoja', all(r % 50 == 0 for r in runs_), sorted(set(runs_))[:6])
check('E3 mittari: 6 kpl 10 s keskiarvoa minuutissa', all(x[1] in (5, 6) for x in d10 if x[0] > 60),
      [x[1] for x in d10][:5])
d10, runs_, th = plant(20, step_at=900, dur_s=2700, start=98.0)
settled = [x for x in d10 if x[0] > 2100 and x[1]]
worst = max(max(abs(x[2]), abs(x[3])) for x in settled)
check('E4 valmiustilan askel 98 -> 90: +-0,05 C 20 min jälkeen', worst <= 0.05, 'max |d| %.3f' % worst)

# 6. TILAUS-R uutto: lämmitys iskuista, jäännös maksetaan uuton jälkeen ja kerroin opitaan tasaantuneesta lämpötilasta.
# Uutto mallissa: N iskua (paine-painotettuna) tuo kylmää vettä, joka vie E_true = k_true * N ms lämmitystä; uuton
# aikana lämmitin maksaa kertymää enintään uuton keston verran, loput jäävät bh_credit_us:ksi (kuten functions BH_*).
import tempfile
C.Thermostat.BH_FILE = os.path.join(tempfile.mkdtemp(), 'brew_heat.json')


class BD2(BD):
    def __init__(self, *a):
        BD.__init__(self, *a)
        self.brew_heat_k, self.bh_credit_us, self.bh_sum_us, self.bh_arm = C.BH_K0_MS, 0.0, 0.0, 0


def shots(k_true, rate=0.6, lag_s=20, n_shots=8, n_eff=250, shot_s=16, seed=2):
    random.seed(seed)
    clock[0] = 0
    sensor = Sensor()
    calc = C.HeatingSpeedCalculator(U, None)
    relay = Relay()
    bd = BD2('IDLE', 98.0, sensor, calc)
    th = C.Thermostat(bd, {}, relay, sensor, U)
    T, q, raw = 98.0, 0.0, [98.0] * 7
    k = 0.024 / 78.0
    per_c_ms = 1000.0 / rate               # heater ms per C in this plant
    res = []

    def step(heat):
        nonlocal T, q, raw
        if clock[0] % 250 == 0:
            raw = raw[1:] + [T + random.gauss(0, 0.03)]
            sensor.t = round(sum(raw) / 7, 2)
        q += (rate * heat - q) * 0.005 / lag_s
        T += (q - k * (T - 20.0)) * 0.005
        clock[0] += 5

    for _ in range(600 * 200):            # settle in IDLE first (10 min)
        th.run(); step(relay.v)
    for i in range(n_shots):
        bd.mode = 'BREW'
        need_ms = k_true * n_eff
        T -= need_ms / per_c_ms           # cold water in (instant, plant units)
        given = bd.brew_heat_k * n_eff * 1000.0
        on_us = min(given, shot_s * 1e6)
        bd.bh_sum_us, bd.bh_credit_us, bd.bh_arm = given, given - on_us, 1
        for j in range(shot_s * 200):
            step(1 if j * 5000 < on_us else 0)
        bd.mode = 'IDLE'
        k_before = bd.brew_heat_k
        tmin = tmax = None
        t_end = clock[0]
        while th.bh_phase is not None or bd.bh_arm:
            th.run(); step(relay.v)
            tmin = sensor.t if tmin is None or sensor.t < tmin else tmin
            tmax = sensor.t if tmax is None or sensor.t > tmax else tmax
            if clock[0] - t_end > 400000: break
        for _ in range(300 * 200):        # 5 min IDLE between shots
            th.run(); step(relay.v)
        res.append((k_before, bd.brew_heat_k, tmin, tmax, th.bh_last_t))
    return res


for k_true, rate in ((100.0, 0.6), (100.0, 0.45), (50.0, 0.6)):
    r = shots(k_true, rate)
    k_last = r[-1][1]
    check('F k_true %.0f rate %.2f: kerroin oppii (±15 %%) %d uutossa' % (k_true, rate, len(r)),
          abs(k_last - k_true) <= 0.15 * k_true, ' '.join('%.0f' % x[1] for x in r))
    ts = r[-1][4]
    check('F k_true %.0f rate %.2f: viimeisen uuton jälkeen tasaantunut T 97,5–98,1 (tavoite −0,2) ilman lisälämmitystä'
          % (k_true, rate), ts is not None and 97.5 <= ts <= 98.1, 'tasaantunut %s, kuoppa min %.2f (uuton aikainen, tieto)' % (
              '%.2f' % ts if ts is not None else None, r[-1][2]))
    # Ylitys korjaantuu hitaasti (käyttäjä 21.10.2026): kolmen viimeisen uuton jälkeen ei yli 98,3
    check('F k_true %.0f rate %.2f: kolmen viimeisen uuton jälkeen max T ≤ 98,3' % (k_true, rate),
          max(x[3] for x in r[-3:]) <= 98.3, ' '.join('%.2f' % x[3] for x in r))
check('F2 kerroin tallennettu', os.path.exists(C.Thermostat.BH_FILE))

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
