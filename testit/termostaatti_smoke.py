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
    IDLE_MODES = ('IDLE', 'idle', 'warming up', 'stabilizing', 'cooling down')
    def __init__(self, *a):
        BD.__init__(self, *a)
        self.brew_heat_k, self.bh_credit_us, self.bh_sum_us, self.bh_arm = C.BH_K0_MS, 0.0, 0.0, 0


def shots(k_true, rate=0.6, lag_s=20, n_shots=8, n_eff=250, shot_s=16, seed=2, arm=1, k0=None, dead_s=0):
    random.seed(seed)
    clock[0] = 0
    sensor = Sensor()
    calc = C.HeatingSpeedCalculator(U, None)
    relay = Relay()
    bd = BD2('IDLE', 98.0, sensor, calc)
    th = C.Thermostat(bd, {}, relay, sensor, U)
    if k0 is not None:
        bd.brew_heat_k = k0
    T, q, raw = 98.0, 0.0, [98.0] * 7
    k = 0.024 / 78.0
    per_c_ms = 1000.0 / rate               # heater ms per C in this plant
    res = []
    dq = [0] * int(dead_s * 200)          # heater dead time (11.07 rinse fit: ~25 s)

    def step(heat):
        nonlocal T, q, raw
        if dq:
            dq.append(heat)
            heat = dq.pop(0)
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
        bd.bh_sum_us, bd.bh_credit_us, bd.bh_arm = given, given - on_us, arm
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
        tpost = thand = tpmax = None
        for j in range(300 * 200):        # 5 min IDLE between shots
            th.run(); step(relay.v)
            thand = sensor.t if thand is None or sensor.t < thand else thand
            tpmax = sensor.t if tpmax is None or sensor.t > tpmax else tpmax
            if j >= 60 * 200:             # after the first minute: the PI's own swing
                tpost = sensor.t if tpost is None or sensor.t < tpost else tpost
        res.append((k_before, bd.brew_heat_k, tmin, tmax, th.bh_last_t, tpost, sensor.t, thand, tpmax))
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

# 7. Peräkkäiset ajot ennen oppia summautuvat (kahvi 21.10.2026 09.11 + kytkimen napautus 09.12: oppi laski
# virheen vain napautuksen 2,3 s:n summasta, k 67,2 -> 70,5). run_shot esiuutto_smoken virtuaalikellolla.
import types
sys.path.insert(0, HERE)
import esiuutto_smoke as ES
bd = ES.brew_bd('25b', 220, False)
ES.run_brew(bd, 16.0, bim=1, seed=220)
s1, a1 = bd.bh_sum_us, bd.bh_arm
check('G1 uutto: summa > 0 ja oppi viritetty (arm 1)', s1 > 0 and a1 == 1, 'sum %d ms arm %d' % (s1 // 1000, a1))
bd.thermostat, bd.bh_arm = types.SimpleNamespace(bh_phase='settle'), 0     # oppi kesken
ES.run_brew(bd, 3.0, bim=1, seed=221)
check('G2 kesken jääneen opin aikana uusi ajo summautuu', bd.bh_sum_us > s1 and bd.bh_arm == 1,
      'sum %d -> %d ms' % (s1 // 1000, bd.bh_sum_us // 1000))
bd.thermostat.bh_phase, bd.bh_arm = None, 0                                 # oppi valmis
ES.run_brew(bd, 3.0, bim=1, seed=222)
check('G3 opin jälkeen uusi ajo alkaa nollasta', 0 < bd.bh_sum_us < s1, 'sum %d ms' % (bd.bh_sum_us // 1000))

# 8. Täytön katto ja höyry (käyttäjä 21.10.2026: s3 höyryn jälkeen 555 täyttöiskua, ylitys +8 C)
F = ES.F
bd = ES.brew_bd('25b', 220, False)
ES.run_brew(bd, 16.0, bim=1, seed=220)
n_fill, s_norm = bd.bh_fill_n, bd.bh_sum_us
check('H1 normaali täyttö katon alla, oppi päällä', 0 < n_fill <= F.BH_FILL_MAX and bd.bh_arm == 1,
      'fill %d, arm %d' % (n_fill, bd.bh_arm))
old = F.BH_FILL_MAX
F.BH_FILL_MAX = max(1, n_fill // 3)
try:
    bd = ES.brew_bd('25b', 220, False)
    ES.run_brew(bd, 16.0, bim=1, seed=220)
finally:
    F.BH_FILL_MAX = old
check('H2 katon ylitys: kertymä pienenee ja oppi pois (arm 2)', bd.bh_sum_us < s_norm and bd.bh_arm == 2,
      'sum %d -> %d ms, arm %d' % (s_norm // 1000, bd.bh_sum_us // 1000, bd.bh_arm))
bd = ES.brew_bd('25b', 220, False)
bd.bh_steam_t = ES.U.us // 1000
ES.run_brew(bd, 16.0, bim=1, seed=220)
check('H3 höyrystä alle 20 min: oppi pois (arm 2)', bd.bh_arm == 2, 'arm %d' % bd.bh_arm)

# Vapaa virtaus (kahva irti, huuhtelu 21.10.2026): paine ~0, koko ajo täyttöä. Kaukalon nousu erottaa läpivirtauksen
# kattilan täytöstä: nousu (0,2 g/isku 60 iskun jälkeen) → katon yli iskut lasketaan; ei nousua tai ei vaakaa → katto.
class FreeBD(ES.BrewData):
    def __init__(self, g_per_stroke, scale=True):
        ES.BrewData.__init__(self, hold_s=6.0, phi_us=3100.0, delta=0.2, tau=0.01, noise=0.02, **ES.M8)
        self.learned_ff_pre, self.eu_g_pre, self.eu_coast_s, self.eu_tau_pre = 0.3, 9.0, 0.1, 1.5
        self.g, self.scale = g_per_stroke, scale

    def get_weight(self):
        return 300.0 + self.g * max(0, self.plant.strokes - 60) if self.scale else None

    def get_weight_ms(self):
        return ES.U.us // 1000


free = {}
for name, g, sc in (('virtaus', 0.2, True), ('täyttö', 0.0, True), ('ei vaakaa', 0.2, False)):
    bd = FreeBD(g, sc)
    txt, _ = ES.run_brew(bd, 15.0, bim=1, seed=5)
    free[name] = (bd.bh_sum_us, bd.bh_arm, bd.bh_fill_n, 'BH_FREE' in txt)
cap = F.BH_FILL_MAX * F.BH_K0_MS * 1000.0
check('H7 vapaa virtaus kaukalon noustessa: katon yli iskut lasketaan (BH_FREE), ei oppia (arm 2)',
      free['virtaus'][3] and free['virtaus'][0] > 4 * cap and free['virtaus'][1] == 2,
      'sum %d ms (katto %d), fill %d' % (free['virtaus'][0] // 1000, cap // 1000, free['virtaus'][2]))
check('H8 ei kaukalon nousua tai ei vaakaa: katto ennallaan',
      all(not free[k][3] and free[k][0] <= cap * 1.01 for k in ('täyttö', 'ei vaakaa')),
      ' '.join('%s %d ms' % (k, free[k][0] // 1000) for k in ('täyttö', 'ei vaakaa')))

# 9. Tasaantuminen myös ilman oppia (arm 2, 21.10.2026 09.56–09.59): PI otti ohjauksen heti maksun jälkeen, integraali
# valui ylityksessä ja lämpötila alittui −1,3 C. Nyt maksun jälkeen aina pito pi_i:llä, oppi vain arm 1:llä.
r = shots(50.0, 0.6, n_shots=3, arm=2, k0=75.0)
check('H4 arm 2: kerroin ei muutu', all(x[1] == 75.0 for x in r), ' '.join('%.1f' % x[1] for x in r))
check('H5 arm 2 ylityksen jälkeen: ei alitusta (min T ≥ 97,7 minuutin jälkeen)', min(x[5] for x in r) >= 97.7,
      'min %s, max %s' % (' '.join('%.2f' % x[5] for x in r), ' '.join('%.2f' % x[3] for x in r)))
r = shots(50.0, 0.6, n_shots=3, arm=2, k0=30.0)
check('H6 arm 2 vaje (täytön katto): 5 min jälkeen 97,8–98,2 ja kerroin ei muutu',
      all(97.8 <= x[6] <= 98.2 and x[1] == 30.0 for x in r), ' '.join('%.2f' % x[6] for x in r))

# 10. Huuhtelu kahva irti 21.10.2026 11.07 (testit/vapaa-20261021-b*): 3 s, 147 iskua, maksettu 10,3 s, arm 2. Malli
# sovitettu laitteeseen kuolleella ajalla 25 s ja viiveellä 10 s (kuoppa −4,7 / laite −5,3, ohjaus PI:lle 137 / 138 s,
# alitus −0,85 / −0,86). Ennen BH_HOLD_LEAD_S:ää lämmitin oli pois tavoitteen yllä, ja PI:n pito tuli 25 s myöhässä.
for need_k, name in ((54.4, 'ylitys'), (47.6, 'iso ylitys')):
    r = shots(need_k, 0.6, lag_s=10, n_shots=2, n_eff=147, shot_s=3, arm=2, k0=70.0, dead_s=25)
    check('H9 arm 2 huuhtelu, kuollut aika 25 s (%s): luovutuksen jälkeen min T ≥ 97,7' % name,
          min(x[7] for x in r) >= 97.7, 'min %s, max %s' % (' '.join('%.2f' % x[7] for x in r),
                                                            ' '.join('%.2f' % x[3] for x in r)))
r = shots(54.4, 0.6, lag_s=40, n_shots=1, n_eff=147, shot_s=3, arm=2, k0=70.0, dead_s=25)
check('H10 arm 2 hidas kattila: ei luovutusta kuopassa (max T ≤ 99,5 myös luovutuksen jälkeen)',
      max(r[0][3], r[0][8]) <= 99.5, 'max %.2f, min %.2f' % (max(r[0][3], r[0][8]), r[0][7]))

# 11. Kylmäkäynnistys ja kylmä huuhtelu (EXPRESSO-POST-BREW-COLD-SETTLE):
# Kun kattila on kylmä (T < target - BH_COLD_C, esim. 25 C), huuhtelu ei saa jäädä settle-tilaan 5,6 % pito-teholla.
# Sen tulee luovuttaa ohjaus heti normaalille lämmitykselle (step cycler), jotta kattila lämpenee täydellä teholla.
sensor = Sensor()
sensor.t = 25.0
calc = C.HeatingSpeedCalculator(U, None)
relay = Relay()
bd = BD2('warming up', 98.0, sensor, calc)
bd.bh_sum_us, bd.bh_credit_us, bd.bh_arm = 5000.0 * 1000, 2000.0 * 1000, 2
th = C.Thermostat(bd, {}, relay, sensor, U)
th.run()
check('K1 kylmä huuhtelu T=25 C: bh_arm nollataan eikä siirry settle-tilaan', bd.bh_arm == 0 and th.bh_phase is None)
check('K2 kylmä huuhtelu T=25 C: lämmitin on päällä (step cycler lämmittää)', relay.v == 1)

# Kylmä settle-poistuminen: jos bh_phase jostain syystä olisi settle ja T < target - BH_COLD_C, luovutus tapahtuu heti
th.bh_phase = 'settle'
th.run()
check('K3 settle-tila kylmällä T=25 C: luovutus välittömästi (cold)', th.bh_phase is None)

# Myös IDLE-tilassa kylmällä (esim. T=25 C) bh_arm nollataan
bd.mode = 'IDLE'
bd.bh_arm = 2
th.run()
check('K4 IDLE-tila kylmällä T=25 C: bh_arm nollataan', bd.bh_arm == 0 and th.bh_phase is None)

# 12. Thermal stability (TILAUS-Q, EXPRESSO-THERMAL-STABILITY):
# Asteikko -10...+10, P0 = 0.045 (vakiotila 0.0), span = 0.040 (kylmäkäynnistyksen tasaantumisteho ~0.085 -> -10.0).
sensor = Sensor()
sensor.t = 98.0
relay = Relay()
bd = BD2('IDLE', 98.0, sensor, calc)
th = C.Thermostat(bd, {}, relay, sensor, U)
th.ts_p0 = 0.045
th.ts_span = 0.040

# L1: Kylmä tila (pi_i = 0.085)
th.pi_i = 0.085
th._update_ts()
check('L1 kylmä tila pi_i=0.085 -> thermal stability -10.0', th.thermal_stability == -10.0 and bd.thermal_stability == -10.0, th.thermal_stability)

# L2: Vakiotila (pi_i = 0.045)
th.pi_i = 0.045
th._update_ts()
check('L2 vakiotila pi_i=0.045 -> thermal stability 0.0', th.thermal_stability == 0.0 and bd.thermal_stability == 0.0, th.thermal_stability)

# L3: Kuuma tila (pi_i = 0.005)
th.pi_i = 0.005
th._update_ts()
check('L3 kuuma tila pi_i=0.005 -> thermal stability +10.0', th.thermal_stability == 10.0 and bd.thermal_stability == 10.0, th.thermal_stability)

# L4: Rajaus [-10.0, +10.0]
th.pi_i = 0.150
th._update_ts()
check('L4a alaraja: pi_i=0.150 rajautuu -10.0', th.thermal_stability == -10.0, th.thermal_stability)
th.pi_i = 0.000
th._update_ts()
check('L4b yläraja: pi_i=0.000 rajautuu +10.0', th.thermal_stability == 10.0, th.thermal_stability)

# L5: 30 min vakaa IDLE oppii uuden P0:n
clock[0] = 1000
th.pi_i = 0.048
th.run() # candidate starts at 0.048
clock[0] = 1000 + 1790000 # 29.8 min
th.run()
check('L5a alle 30 min: P0 ei vielä päivity', th.ts_p0 == 0.045, th.ts_p0)
clock[0] = 1000 + 1805000 # 30.1 min
th.run()
check('L5b 30 min vakaa IDLE: P0 oppii uuden arvon', abs(th.ts_p0 - 0.048) < 0.001, th.ts_p0)

# L6: Muut tilat (STEAM, BREW) säilyttävät edellisen IDLE-arvon
saved_ts = th.thermal_stability
bd.mode = 'STEAM'
sensor.t = 135.0
th.run()
check('L6 STEAM-tilassa thermal stability säilyy', th.thermal_stability == saved_ts and bd.thermal_stability == saved_ts, th.thermal_stability)

# Siivoa testin luoma pysyvyystiedosto
for f in ('thermal_stability.json', 'thermal_stability.json.tmp'):
    if os.path.exists(f):
        try: os.remove(f)
        except Exception: pass

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
