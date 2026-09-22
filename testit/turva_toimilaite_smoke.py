#!/usr/bin/env python3
"""turva_toimilaite_smoke.py — EXPRESSO-TURVA-TOIMILAITE (22.9.2026), paketit/TURVAKATO.md kohta 1.

A. Koneellinen tarkistus lahteesta (grep): mikaan polku ei paase pumpun tai lammittimen raakapinniin
   vartion ohi, joten jokainen RELAY_PUMP.value(1) / RELAY_HEATER.value(1) kulkee vartion kautta.
B. Vartio valelaitteilla: dev_safe, ylipaine, aikaraja, lammittimen lampo ja tuoreus, vartion oma virhe.
C. Testikomentojen kaukalovahti ajon aikana (tray_guard_poll).

    python3 testit/turva_toimilaite_smoke.py       RESULT: <n> failed
"""

import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
PICO = os.path.join(HERE, '..', 'pico')
sys.path.insert(0, PICO)

sys.modules.setdefault('devsafe', types.SimpleNamespace(feed=lambda: None))
import relayguard as G      # noqa: E402
import classes              # noqa: E402
import functions as F       # noqa: E402
import preset               # noqa: E402


def src(name):
    with open(os.path.join(PICO, name)) as f:
        return f.read()


def code_lines(text):
    """Lines with comments stripped (a '#' inside a string is rare enough here to ignore)."""
    for n, line in enumerate(text.split('\n'), 1):
        yield n, line.split('#', 1)[0]


class Clock:
    def __init__(self): self.ms = 0


class Utime:
    def __init__(self, c): self.c = c
    def ticks_ms(self): return self.c.ms
    def ticks_us(self): return self.c.ms * 1000
    def ticks_diff(self, a, b): return a - b
    def ticks_add(self, a, b): return a + b


class Pin:
    IN, OUT, PULL_DOWN = 0, 1, 2
    def __init__(self, n=None, mode=None, pull=None, value=0): self.n = n; self.v = value
    def value(self, v=None):
        if v is None: return self.v
        self.v = 1 if v else 0


def make_bd(clock):
    ps = types.SimpleNamespace(gain=1.0, offset=0.0,
                               pressure_sensor=types.SimpleNamespace(read_u16=lambda: 0))
    bd = classes.BrewData(Pin, None, preset.PINS, preset.TARGET_TEMPERATURES, preset.FEATURES,
                          None, types.SimpleNamespace(read_temperature=lambda: 95.0), ps,
                          utime=Utime(clock))
    bd.relay_guard.read_pressure = lambda: bd._p       # test sets the pressure directly
    bd._p = 0.0
    return bd


def main():
    fails = []

    def check(name, cond, extra=''):
        print(('ok   ' if cond else 'FAIL ') + name + (' — ' + str(extra) if extra and not cond else ''))
        if not cond:
            fails.append(name)

    files = sorted(f for f in os.listdir(PICO) if f.endswith('.py'))

    # ---- A. source check -------------------------------------------------------------------
    raw_pin = re.compile(r"Pin\(\s*PINS\[\s*'RELAY_(PUMP|HEATER)'\s*\]")
    bad = []
    for f in files:
        for n, line in code_lines(src(f)):
            if raw_pin.search(line) and not (f == 'classes.py' and 'GuardedRelay(' in line):
                bad.append('%s:%d' % (f, n))
    check('A1 pumpun/lammittimen Pin() vain GuardedRelay(...):n sisalla', not bad, bad)

    bad = []
    for f in files:
        if f == 'relayguard.py':
            continue
        for n, line in code_lines(src(f)):
            if re.search(r"\.pin\.value\(\s*(1|True)", line) or re.search(r"\bpin\.value\(\s*(1|True)", line):
                bad.append('%s:%d' % (f, n))
    check('A2 kukaan ei kytke raakapinnia paalle relayguard.py:n ulkopuolella', not bad, bad)

    bad = [n for n, line in code_lines(src('devsafe.py')) if re.search(r"value\(\s*(1|True)", line)]
    check('A3 devsafe.py vain sammuttaa (ei value(1))', not bad, bad)

    # Raw pin numbers 11 (pump) and 13 (heater) are touched only by devsafe.py, which only turns off
    pins = (preset.PINS['RELAY_PUMP'], preset.PINS['RELAY_HEATER'])
    bad = []
    for f in files:
        if f in ('devsafe.py', 'preset.py'):
            continue
        for n, line in code_lines(src(f)):
            if re.search(r"Pin\(\s*(%d|%d)\b" % pins, line):
                bad.append('%s:%d' % (f, n))
    check('A4 releiden pinninumeroita ei kayteta suoraan (paitsi devsafe/preset)', not bad, bad)

    # Every binding of a RELAY_PUMP/RELAY_HEATER name comes from get_relays(), the guarded
    # attribute, or a constructor parameter that main.py fills from get_relays()
    bind = re.compile(r"\bRELAY_(PUMP|HEATER)\b[^=\n()]*=(?!=)(.*)")
    ok_rhs = ('get_relays()', 'GuardedRelay(', 'self.RELAY_PUMP', 'self.RELAY_HEATER', 'RELAY_HEATER')
    bad = []
    for f in files:
        for n, line in code_lines(src(f)):
            m = bind.search(line)
            if m and not any(t in m.group(2) for t in ok_rhs):
                bad.append('%s:%d %s' % (f, n, line.strip()))
    check('A5 RELAY_PUMP/RELAY_HEATER sidotaan vain get_relays():sta', not bad, bad)

    # Constructor parameters: PumpPressureController(relay=...) and Thermostat(RELAY_HEATER) get
    # their relay from get_relays() at every call site
    bad = []
    for f in files:
        for n, line in code_lines(src(f)):
            m = re.search(r"PumpPressureController\(\s*([A-Za-z_\.]+)", line)
            if m and m.group(1) not in ('RELAY_PUMP',):
                bad.append('%s:%d' % (f, n))
            m = re.search(r"Thermostat\([^)]*", line)
            if m and 'class ' not in line and 'RELAY_HEATER' not in m.group(0):
                bad.append('%s:%d' % (f, n))
    check('A6 saatimet ja termostaatti saavat releen get_relays():sta', not bad, bad)

    ons = sum(len(re.findall(r"RELAY_(PUMP|HEATER)\.value\(\s*(1|g)\s*\)", l))
              for f in files for _, l in code_lines(src(f)))
    print('info A: %d RELAY_PUMP/RELAY_HEATER-paallekytkentaa lahteessa, kaikki GuardedRelay-olioita' % ons)

    main_src = src('main.py')
    check('A7 kuumavesisilmukka lukee lampotilan (lammittimen tuoreusraja)',
          re.search(r"while \(SWITCH_WATER\.value\(\)\):[\s\S]{0,400}get_boiler_temperature\(\)", main_src) is not None)
    check('A8 vartion ajastin kaynnistetaan main.py:ssa', 'relay_guard.start()' in main_src)

    # ---- B. guard behaviour ----------------------------------------------------------------
    c = Clock()
    bd = make_bd(c)
    pump, sol, heater = bd.get_relays()
    g = bd.relay_guard
    check('B0 get_relays() antaa vartioidut pumpun ja lammittimen',
          isinstance(pump, G.GuardedRelay) and isinstance(heater, G.GuardedRelay)
          and not isinstance(sol, G.GuardedRelay))

    def step(ms):                         # advance virtual time with guard polls every POLL_MS
        end = c.ms + ms
        while c.ms < end:
            c.ms += G.POLL_MS
            g.poll()

    pump.value(1)
    check('B1 pumppu kaynnistyy normaalisti', pump.value() == 1)
    bd.dev_safe = True
    step(100)
    check('B2 dev_safe sammuttaa kaynnissa olevan pumpun', pump.value() == 0)
    pump.value(1)
    check('B3 dev_safe estaa kaynnistyksen', pump.value() == 0)
    bd.dev_safe = False
    pump.value(0)
    step(G.PUMP_RUN_GAP_MS)

    pump.value(1)
    bd._p = 14.0
    step(G.POLL_MS * (G.PRESSURE_TRIP_N - 1))
    check('B4 yksi-kaksi ylipainenaytetta ei viela katkaise (iskupiikki)', pump.value() == 1)
    step(G.POLL_MS)
    check('B5 ylipaine %d perakkaista kertaa sammuttaa' % G.PRESSURE_TRIP_N, pump.value() == 0)
    pump.value(1)
    check('B6 ylipaineessa kaynnistys estetaan', pump.value() == 0)
    bd._p = 9.0
    step(G.POLL_MS)
    pump.value(1)
    check('B7 paineen laskettua pumppu saa kaynnistya', pump.value() == 1)
    pump.value(0)
    step(G.PUMP_RUN_GAP_MS)

    # Run time: continuous (hot water) and PWM (a path that keeps switching)
    pump.value(1)
    step(G.PUMP_RUN_MAX_MS - 1000)
    check('B8 jatkuva ajo alle aikarajan jatkuu', pump.value() == 1)
    step(2000)
    check('B9 jatkuva ajo katkeaa aikarajaan', pump.value() == 0)
    for _ in range(100):                  # the path keeps asking (switch still held)
        pump.value(1); c.ms += 50; g.poll()
    check('B10 jatkuva pyytaminen ei anna uutta ajoa', pump.value() == 0)
    c.ms += G.PUMP_RUN_GAP_MS; g.poll()
    pump.value(1)
    check('B11 %d s tauon jalkeen uusi ajo alkaa' % (G.PUMP_RUN_GAP_MS // 1000), pump.value() == 1)
    pump.value(0)
    step(G.PUMP_RUN_GAP_MS)

    tripped = False
    for k in range(170000 // 20):         # PWM 170 s: on/off every 20 ms, like the controllers
        pump.value(k & 1); c.ms += 20
        if k % 5 == 0: g.poll()
        if (k & 1) and pump.value() == 0: tripped = True
    check('B12 170 s PWM-ajo (phold 120 s + vara) ei katkea', not tripped)
    pump.value(0)
    step(G.PUMP_RUN_GAP_MS)

    tripped = False                       # backflush: 4 s pulse, 10 s pause, 30 pulses = 7 min
    for _ in range(30):
        pump.value(1); step(4000)
        if pump.value() == 0: tripped = True
        pump.value(0); step(10000)
    check('B13 takaisinhuuhtelun pulssit (4 s + 10 s tauko) eivat laukaise aikarajaa', not tripped)

    # Heater
    bd.get_boiler_temperature()
    heater.value(1)
    check('B14 lammitin kaynnistyy tuoreella lukemalla', heater.value() == 1)
    step(G.HEATER_TEMP_STALE_MS + 500)
    check('B15 vanhentunut lampolukema sammuttaa lammittimen', heater.value() == 0)
    bd.get_boiler_temperature()
    heater.value(1)
    bd.boiler_temperature = 165.0
    step(G.POLL_MS)
    check('B16 yli %.0f C sammuttaa' % G.HEATER_TEMP_MAX_C, heater.value() == 0)
    bd.boiler_temperature = 200          # TemperatureSensor's permanent-fault value
    bd.boiler_temperature_ms = c.ms
    heater.value(1)
    check('B17 anturivika (200 C) estaa kaynnistyksen', heater.value() == 0)
    bd.boiler_temperature = 95.0
    bd.boiler_temperature_ms = c.ms
    bd.dev_safe = True
    heater.value(1)
    check('B18 dev_safe estaa lammittimen', heater.value() == 0)
    bd.dev_safe = False

    # Guard error fails safe
    pump.value(1); bd.get_boiler_temperature(); heater.value(1)
    def boom(): raise OSError('adc')
    g.read_pressure = boom
    g.poll()
    check('B19 vartion oma virhe sammuttaa kaiken', pump.value() == 0 and heater.value() == 0)
    pump.value(1)
    check('B20 virheen jalkeen kaynnistys estetaan', pump.value() == 0)

    # ---- C. tray check during a capture run ------------------------------------------------
    tb = types.SimpleNamespace(weight=300.0, weight_ms=0)
    tb.get_weight_limit = lambda: 470.0
    tb.get_weight_rise_limit = lambda: 250.0
    tb.get_weight = lambda: tb.weight
    tb.get_weight_ms = lambda: tb.weight_ms
    tc = Clock(); tu = Utime(tc)
    state, reason = F.tray_guard_start(tb, tu)
    def poll_scale():
        tb.weight_ms = tc.ms
    tb.scale_poll = poll_scale
    results = []
    for w in (320.0, 480.0, 490.0):
        tc.ms += 1024; tb.weight = w
        results.append(F.tray_guard_poll(tb, tu, state))
    check('C1 kaukalo yli wmax:n kesken ajon katkaisee (2 tuoretta naytetta)',
          results == [None, None, 'tray'], results)
    del tb.scale_poll
    state, _ = F.tray_guard_start(tb, tu) if tb.weight < 470 else ({'start': 300.0, 'last_ms': None, 'over': 0}, None)
    tc.ms += 3000
    check('C2 vaaka ei paivity ajon aikana -> scalelost', F.tray_guard_poll(tb, tu, state) == 'scalelost')

    fsrc = src('functions.py')
    n = len(re.findall(r"_sweep_break\(brew_data, '(pstep|pgap|plen)_abort'\) or tray_guard_poll", fsrc))
    check('C3 pstep/pgap/plen tarkistavat kaukalon ajon aikana', n == 3, n)
    check('C4 main.py antaa vaa\'an lukijan kaappaussilmukoille', 'brew_data.scale_poll = scale_poll_once' in main_src)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
