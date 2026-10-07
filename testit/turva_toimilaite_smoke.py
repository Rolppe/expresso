#!/usr/bin/env python3
"""turva_toimilaite_smoke.py — EXPRESSO-TURVA-TOIMILAITE (22.9.2026), paketit/TURVAKATO.md kohta 1.

A. Koneellinen tarkistus lahteesta (grep): mikaan polku ei paase pumpun tai lammittimen raakapinniin
   vartion ohi, joten jokainen RELAY_PUMP.value(1) / RELAY_HEATER.value(1) kulkee vartion kautta.
B. Vartio valelaitteilla: dev_safe, ylipaine, aikaraja, lammittimen lampo ja tuoreus, vartion oma virhe.
C. Testikomentojen kaukalovahti ajon aikana (tray_guard_poll).
D. Anturien uskottavuus (TURVAKATO kohta 5): painenturi rikki, lammitys ei nosta lampoa.

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
                          None, types.SimpleNamespace(read_temperature=lambda: 95.0, c1_active=lambda: False,
                                                      c1_temperature=lambda: None, c1_ms=lambda: None), ps,
                          utime=Utime(clock))
    # test sets the pressure directly; raw (uncalibrated) follows it unless set
    bd.relay_guard.read_pressure = lambda: (bd._p, bd._p if bd._raw is None else bd._raw)
    bd._p = 0.0
    bd._raw = None
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
    # Kuumavesisilmukka siirtyi functions.hot_water_run:iin (EXPRESSO-KUUMAVESI-RAJAT 7.10.2026)
    check('A7 kuumavesisilmukka lukee lampotilan (lammittimen tuoreusraja)',
          re.search(r"while \(SWITCH_WATER\.value\(\)\):[\s\S]{0,600}get_boiler_temperature\(\)", src('functions.py')) is not None)
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

    # ---- D. sensor plausibility ------------------------------------------------------------
    c = Clock()
    bd = make_bd(c)
    pump, sol, heater = bd.get_relays()
    g = bd.relay_guard

    def run(ms, temp=None, dtemp_per_s=0.0):
        end = c.ms + ms
        while c.ms < end:
            c.ms += G.POLL_MS
            if temp is not None:
                bd.boiler_temperature = temp[0]
                bd.boiler_temperature_ms = c.ms
                temp[0] += dtemp_per_s * G.POLL_MS / 1000.0
            g.poll()

    pump.value(1)
    bd._raw = -3.5
    run(G.POLL_MS * (G.PRESSURE_TRIP_N - 1))
    check('D1 kaksi rikkinaista painelukemaa ei viela katkaise', pump.value() == 1)
    run(G.POLL_MS)
    check('D2 painenturi rikki (raw -3,5 bar) sammuttaa pumpun', pump.value() == 0)
    bd._raw = None
    run(G.POLL_MS)
    pump.value(1)
    check('D3 anturin palattua pumppu saa kaynnistya', pump.value() == 1)
    pump.value(0)

    bd.mode = 'IDLE'                     # target = brew_temperature 97 C
    t = [95.0]
    bd.get_boiler_temperature(); heater.value(1)
    run(30 * 60000, t)
    check('D4 30 min lahella tavoitetta (95/97 C) ei laukaise', heater.value() == 1)

    t = [30.0]
    run(300000, t, dtemp_per_s=0.2)      # warm-up 12 C/min
    check('D5 normaali lammitys kylmasta (0,2 C/s, 5 min) ei laukaise', heater.value() == 1)

    t = [90.0]
    pump.value(1)
    run(170000, t, dtemp_per_s=-0.05)    # hot water: pump on, cold water in, reading drops
    check('D6 kuumavesi (pumppu paalla, lampo laskee) ei laukaise', heater.value() == 1 and pump.value() == 1)
    pump.value(0)

    t = [25.0]                           # sensor off the boiler: room temperature, no rise
    run(G.HEATER_NORISE_ON_MS - 2000, t)
    check('D7 alle %d s ilman nousua ei viela katkaise' % (G.HEATER_NORISE_ON_MS // 1000), heater.value() == 1)
    run(3000, t)
    check('D8 %d s lammitysta ilman nousua sammuttaa' % (G.HEATER_NORISE_ON_MS // 1000), heater.value() == 0)
    t = [96.0]
    run(G.POLL_MS, t)
    heater.value(1)
    check('D9 ei-nouse-laukaisu ei vapaudu heti', heater.value() == 0)

    # V-154 (a): lukon uusinta. Ilman jaahtymistodistetta anturi voi olla irti kattilasta.
    t = [25.0]
    run(G.HEATER_NORISE_RETRY_MS - 5000, t); heater.value(1)
    check('D10 ilman jaahtymista ei uusita ennen %d min' % (G.HEATER_NORISE_RETRY_MS // 60000), heater.value() == 0)
    run(6000, t); heater.value(1)
    check('D11 uusinta %d min kuluttua vapauttaa lammittimen' % (G.HEATER_NORISE_RETRY_MS // 60000),
          heater.value() == 1)
    run(G.HEATER_NORISE_RETRY_ON_MS + 1000, t)
    check('D12 uusinnassa %d s ilman nousua lukitsee uudelleen' % (G.HEATER_NORISE_RETRY_ON_MS // 1000),
          heater.value() == 0)
    for _ in range(G.HEATER_NORISE_RETRY_MAX - 1):
        run(G.HEATER_NORISE_RETRY_MS + 1000, t); heater.value(1)
        run(G.HEATER_NORISE_RETRY_ON_MS + 1000, t)
    run(3 * G.HEATER_NORISE_RETRY_MS, t); heater.value(1)
    check('D13 %d uusinnan jalkeen ilman jaahtymista lukko pysyy' % G.HEATER_NORISE_RETRY_MAX,
          heater.value() == 0 and g.heat_retries == G.HEATER_NORISE_RETRY_MAX, g.heat_retries)

    # Keitin irti verkosta illalla, Pico Zeron virralla: lukema laskee yon yli, aamulla verkkovirta takaisin
    c = Clock()
    bd = make_bd(c)
    pump, sol, heater = bd.get_relays()
    g = bd.relay_guard
    bd.mode = 'IDLE'
    t = [90.0]
    for _ in range(8 * 60):              # 8 h, termostaatti pyytaa lammitysta minuutin valein
        heater.value(1)
        run(60000, t, dtemp_per_s=-0.01)
        t[0] = max(22.0, t[0])
    check('D14 yo ilman verkkovirtaa: jaahtyminen todistaa anturin kattilassa', g.heat_proven, g.heat_proven)
    on_s = None
    for s in range(180):                 # verkkovirta takaisin: lammitin nostaa 0,2 C/s kun rele on paalla
        heater.value(1)
        run(1000, t, dtemp_per_s=0.2 if heater.value() else 0.0)
        if on_s is None and t[0] >= 25.0:
            on_s = s
    check('D15 aamulla lammitys alkaa %d s sisalla' % (G.HEATER_NORISE_RETRY_PROVEN_MS // 1000 + 30),
          on_s is not None and on_s <= G.HEATER_NORISE_RETRY_PROVEN_MS // 1000 + 30, on_s)
    check('D16 nousu nollaa uusinnat ja todisteen',
          heater.value() == 1 and not g.heat_dead and not g.heat_proven and g.heat_retries == 0,
          (heater.value(), g.heat_dead, g.heat_proven, g.heat_retries))

    # V-154-SYY 6.10.2026: Pico kaynnistyi kylmana irti verkosta (flash 5.10. illalla, kattila 25,9 C).
    # Lukko syntyy huoneenlammossa, jaahtymistodistetta ei voi tulla, ja 3 uusintaa kuluu yon aikana.
    c = Clock()
    bd = make_bd(c)
    pump, sol, heater = bd.get_relays()
    g = bd.relay_guard
    bd.mode = 'IDLE'
    t = [25.9]
    for _ in range(8 * 60):
        heater.value(1)
        run(60000, t, dtemp_per_s=-0.0001)
        t[0] = max(23.1, t[0])
    check('D17 kylma kaynnistys irti verkosta: yon jalkeen lukko paalla ilman todistetta',
          g.heat_dead and not g.heat_proven and g.heat_retries == G.HEATER_NORISE_RETRY_MAX,
          (g.heat_dead, g.heat_proven, g.heat_retries))
    for _ in range(120):                 # verkkovirta takaisin, kukaan ei koske: lukko pysyy (tunnettu raja)
        heater.value(1)
        run(1000, t, dtemp_per_s=0.2 if heater.value() else 0.0)
    check('D18 ilman kayttajan toimintoa lukko pysyy (uusintabudjetti kulunut)', g.heat_dead and t[0] < 24.0, t[0])
    bd.note_activity(c.ms, 'app')        # kayttaja muuttaa asetusta sovelluksesta tai kaantaa kytkinta
    on_s = None
    for s in range(60):
        heater.value(1)
        run(1000, t, dtemp_per_s=0.2 if heater.value() else 0.0)
        if on_s is None and t[0] >= 25.0:
            on_s = s
    check('D19 kayttajan toiminto vapauttaa lukon ja lammitys alkaa %d s sisalla' % (G.HEATER_NORISE_RETRY_ON_MS // 1000),
          on_s is not None and on_s <= G.HEATER_NORISE_RETRY_ON_MS // 1000, on_s)
    check('D20 nousun jalkeen lukko, uusinnat ja todiste nollattu',
          heater.value() == 1 and not g.heat_dead and g.heat_retries == 0, (g.heat_dead, g.heat_retries))

    # Irronnut anturi: kayttajan toiminto antaa yhden 30 s uusinnan, ei uutta automaattibudjettia
    t = [25.0]
    g.heat_dead = True; g.heat_dead_ms = c.ms; g.heat_dead_c = 25.0
    g.heat_retries = G.HEATER_NORISE_RETRY_MAX; g.heat_proven = False
    bd.note_activity(c.ms, 'switch')
    heater.value(1)
    check('D21 kayttajan toiminto vapauttaa lukon heti', heater.value() == 1)
    run(G.HEATER_NORISE_RETRY_ON_MS + 1000, t)
    run(3 * G.HEATER_NORISE_RETRY_MS, t); heater.value(1)
    check('D22 irronneella anturilla lukitsee 30 s jalkeen eika uusi itse', heater.value() == 0 and g.heat_dead,
          (heater.value(), g.heat_dead, g.heat_retries))

    # Tilakomento heat? (V-154-SYY): mitattu lampotila ja lukon tila, ei asetusarvoa
    import commands, io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = commands.handle_command(bd, 'heat?')
    out = buf.getvalue().strip().splitlines()
    check('D23 heat? raportoi mitatun lampotilan ja lukon tilan, ei aktiivisuutta',
          r is False and bd.command_known and len(out) == 1 and out[0].startswith('HEAT temp=25.0 ')
          and ' dead=1 ' in out[0] and ' retries=%d ' % G.HEATER_NORISE_RETRY_MAX in out[0]
          and ' target=%s ' % bd.get_target_temperature() in out[0], out)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
