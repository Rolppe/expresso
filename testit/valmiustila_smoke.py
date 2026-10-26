#!/usr/bin/env python3
"""valmiustila_smoke.py — EXPRESSO-VALMIUSTILA: 30 min käyttämättä -> kattilan lepotavoite 90 C.

Valelaitteet kuten shot_test.py. Esiehto: /tmp/fw = kopio pico/*.py (+ lib/) ja /tmp/fw_preset.py = kopio
pico/preset.py; jos niitä ei ole, käytetään suoraan hakemistoa ../pico (sama koodi, ei kopiota).

    python3 testit/valmiustila_smoke.py      RESULT: <n> failed, epänolla paluuarvo jos punaisia

Tapaukset: (a) 29 min 59 s -> ei valmiustilaa; (b) 30 min -> STBY_ON, tavoite 90; (c) uuttokytkin -> STBY_OFF
reason=switch; (d) pre:on -> STBY_OFF reason=app; (e) lukukomento ei herätä; (f) brew 88 -> tavoite 88;
(g) STEAM valmiustilassa -> höyrytavoite; (h) stby:0 -> ei valmiustilaa 2 h:ssa; (i) ticks_diff negatiivinen
(kierto) valmiustilassa -> pysyy. Lisäksi oletukset, stby:on/stby:<min> ja main.py:n kytkentä.
"""
import contextlib, importlib.util, io, os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
# Repo firmware unless FW names another set: a leftover /tmp/fw (5.10.2026) was picked silently and the smoke
# passed against stale code (V-154-SYY, 6.10.2026)
FW = os.environ.get('FW') or os.path.join(HERE, '..', 'pico')
PRESET = os.environ.get('FW_PRESET') or os.path.join(FW, 'preset.py')
sys.path.insert(0, FW)

clock = [0]     # ms
utime = types.ModuleType('utime')
utime.ticks_ms = lambda: clock[0]
utime.ticks_diff = lambda a, b: a - b          # kuten shot_test.py; kierto simuloidaan negatiivisella erotuksella
utime.ticks_add = lambda a, b: a + b
utime.ticks_us = lambda: clock[0] * 1000
sys.modules['utime'] = utime
pins = {}


class Pin:
    OUT = 1; IN = 0; PULL_DOWN = 2

    def __init__(self, n, mode=None, pull=None, value=None):
        self.n = n
        pins.setdefault(n, 0)
        if value is not None: pins[n] = value

    def value(self, v=None):
        if v is None: return pins[self.n]
        pins[self.n] = 1 if v else 0


class WDT:
    def __init__(self, timeout): pass
    def feed(self): pass


machine = types.ModuleType('machine'); machine.Pin = Pin; machine.WDT = WDT
machine.disable_irq = lambda: 0; machine.enable_irq = lambda s=0: None
sys.modules['machine'] = machine
spec = importlib.util.spec_from_file_location('preset', PRESET); preset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preset); sys.modules['preset'] = preset
import classes, commands
from classes import BrewData

fails = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)


def make():
    clock[0] = 0
    bd = BrewData(Pin, None, preset.PINS, preset.TARGET_TEMPERATURES, preset.FEATURES, None, None, None, utime)
    bd.pcal_status = lambda: None
    bd.get_pressure_calibration_status = lambda: {'pcal_state': 'idle', 'pcal_stage': '', 'pcal_gain': 1.0,
                                                  'pcal_offset': 0.0, 'pcal_msg': ''}
    return bd


def capture(fn, *a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn(*a)
    return r, buf.getvalue().splitlines()


def idle_for(bd, ms):
    clock[0] += ms
    return capture(bd.update_standby, clock[0])[1]


S = 1000
MIN = 60 * S

# 0. defaults from the real constructor
try:
    bd = make()
    check('defaults', bd.standby_startup_timeout_ms == 120 * MIN and bd.standby_brew_timeout_ms == 30 * MIN
          and bd.standby_timeout_ms == 30 * MIN and bd.standby_temperature == 90 and bd.standby is False
          and bd.has_brewed is False and bd.last_activity_ms == 0,
          '%s %s %s %s %s' % (bd.standby_startup_timeout_ms, bd.standby_brew_timeout_ms, bd.standby_temperature, bd.standby, bd.last_activity_ms))
    clock[0] = 5000
    bd2 = BrewData(Pin, None, preset.PINS, preset.TARGET_TEMPERATURES, preset.FEATURES, None, None, None, utime)
    check('last_activity_ms = ticks_ms at construction', bd2.last_activity_ms == 5000, str(bd2.last_activity_ms))
except Exception as e:
    check('0. raised', False, repr(e))

# (a) käynnistyksen jälkeen lepotila 120 min: 119 min 59 s
try:
    bd = make(); out = idle_for(bd, 120 * MIN - S)
    check('a: startup 119:59 no standby, target = brew', not bd.standby and bd.get_target_temperature() == bd.brew_temperature and not out,
          '%s %s' % (bd.get_target_temperature(), out))

    # (b) 120 min -> standby
    out = idle_for(bd, S)
    check('b: startup 120 min STBY_ON, target 90', bd.standby and bd.get_target_temperature() == 90 and out == ['STBY_ON idle_s=7200 target=90'],
          '%s %s' % (bd.get_target_temperature(), out))

    # (c) brew switch herättää
    out = capture(bd.note_activity, clock[0], 'switch')[1]
    check('c: switch -> STBY_OFF reason=switch, target = brew', not bd.standby and out == ['STBY_OFF reason=switch']
          and bd.get_target_temperature() == bd.brew_temperature, '%s' % out)

    # (c2) veden lasku keittimen läpi (huuhtelu, p < 2.5 bar) EI triggeröi uuttotilaa
    r_flush, out_flush = capture(bd.record_brew_completed, clock[0], 0.8, 3000)
    check('c2: flush -> has_brewed stays False', not r_flush and not bd.has_brewed and out_flush == ['FLUSH_DETECTED peak_p=0.80 dur_s=3.0'])

    # (c3) oikea uutto (p >= 2.5 bar, kesto >= 5000 ms) triggeröi uuttotilan
    r_brew, out_brew = capture(bd.record_brew_completed, clock[0], 8.5, 25000)
    check('c3: real brew -> has_brewed is True', r_brew and bd.has_brewed and out_brew == ['BREW_COMPLETE peak_p=8.50 dur_s=25.0'])

    # (c4) uuton jälkeen ajastin 30 min: 29 min 59 s
    out = idle_for(bd, 30 * MIN - S)
    check('c4: post-brew 29:59 no standby', not bd.standby and not out)

    # (c5) uuton jälkeen 30 min -> STBY_ON
    out = idle_for(bd, S)
    check('c5: post-brew 30 min STBY_ON target 90', bd.standby and bd.get_target_temperature() == 90 and out == ['STBY_ON idle_s=1800 target=90'])
except Exception as e:
    check('(a) raised', False, repr(e))

# (d) app change wakes
try:
    bd = make(); capture(commands.handle_command, bd, 'stby:on'); assert bd.standby
    known, out = capture(commands.handle_command, bd, 'pre:on')
    check('d: pre:on -> STBY_OFF reason=app', not bd.standby and 'STBY_OFF reason=app' in out, '%s' % out)
except Exception as e:
    check('(d) raised', False, repr(e))

# (e) read command does not wake
try:
    bd = make(); capture(commands.handle_command, bd, 'stby:on'); assert bd.standby
    r, out = capture(commands.handle_command, bd, 'pcal:st')
    r2, out2 = capture(commands.handle_command, bd, 'nosuchcommand')
    check('e: read-only command (updated False) does not wake', r is False and r2 is False and bd.standby and
          not [l for l in out + out2 if l.startswith('STBY_OFF')], '%s %s' % (out, out2))
except Exception as e:
    check('(e) raised', False, repr(e))

# (f) brew temperature 88
try:
    bd = make(); bd.brew_temperature = 88.0; capture(commands.handle_command, bd, 'stby:on')
    check('f: brew 88 -> standby target 88', bd.standby and bd.get_target_temperature() == 88.0, str(bd.get_target_temperature()))
except Exception as e:
    check('(f) raised', False, repr(e))

# (g) STEAM / WATER / BREW while in standby
try:
    bd = make(); capture(commands.handle_command, bd, 'stby:on')
    bd.mode = 'STEAM'; steam = bd.get_target_temperature()
    bd.mode = 'WATER'; water = bd.get_target_temperature()
    bd.mode = 'BREW'; brew = bd.get_target_temperature()
    bd.mode = 'BACKFLUSH_PHASE_1'; bf = bd.get_target_temperature()
    check('g: STEAM in standby -> steam target; WATER/BREW/BACKFLUSH unchanged', steam == bd.steam_temperature and
          water == bd.brew_temperature and brew == bd.brew_temperature and bf == bd.BACKFLUSH_PHASE_1_temperature,
          '%s %s %s %s' % (steam, water, brew, bf))
    bd = make(); bd.mode = 'STEAM'; out = idle_for(bd, 60 * MIN)
    check('g: no standby latch outside IDLE', not bd.standby and not out)
except Exception as e:
    check('(g) raised', False, repr(e))

# (h) stby:0
try:
    bd = make(); r, out = capture(commands.handle_command, bd, 'stby:0')
    check('h: stby:0 reports', out == ['STBY timeout_min=0 standby=0 target=%s' % bd.brew_temperature], '%s' % out)
    capture(commands.handle_command, bd, 'stby:start:0')
    out = idle_for(bd, 120 * MIN)
    check('h: stby:0 -> no standby in 2 h', not bd.standby and not out and bd.get_target_temperature() == bd.brew_temperature)
except Exception as e:
    check('(h) raised', False, repr(e))

# (i) negative ticks_diff (ticks wrap) in standby: latch stays
try:
    bd = make(); capture(commands.handle_command, bd, 'stby:on'); assert bd.standby
    out = capture(bd.update_standby, clock[0] - 10 * 24 * 3600 * S)[1]
    out += capture(bd.update_standby, clock[0] + 7 * 24 * 3600 * S)[1]
    check('i: wrapped (negative) ticks_diff keeps standby', bd.standby and bd.get_target_temperature() == 90 and not out, '%s' % out)
except Exception as e:
    check('(i) raised', False, repr(e))

# stby: command variants
try:
    bd = make(); r, out = capture(commands.handle_command, bd, 'stby:on')
    check('stby:on enters standby now, stays (not activity)', bd.standby and r is True and out ==
          ['STBY_ON idle_s=0 target=90', 'STBY timeout_min=30 standby=1 target=90'], '%s' % out)
    r, out = capture(commands.handle_command, bd, 'stby:start:180')
    check('stby:start:180 updates timeout in standby without waking', bd.standby and bd.standby_startup_timeout_ms == 180 * MIN and
          out == ['STBY startup_min=180 standby=1 target=90'], '%s' % out)
    r, out = capture(commands.handle_command, bd, 'stby:brew:45')
    check('stby:brew:45 updates timeout in standby without waking', bd.standby and bd.standby_brew_timeout_ms == 45 * MIN and
          out == ['STBY timeout_min=45 standby=1 target=90'], '%s' % out)
    r, out = capture(commands.handle_command, bd, 'stby:15')
    check('stby:15 (compat alias) updates timeout in standby without waking', bd.standby and bd.standby_brew_timeout_ms == 15 * MIN and
          out == ['STBY timeout_min=15 standby=1 target=90'], '%s' % out)
    r, out = capture(commands.handle_command, bd, 'stby:wake')
    check('stby:wake explicitly wakes from standby', not bd.standby and r is True and
          out == ['STBY_OFF reason=app', 'STBY timeout_min=15 standby=0 target=%s' % bd.brew_temperature], '%s' % out)
    capture(commands.handle_command, bd, 'stby:999')
    check('stby clamps to 240 min', bd.standby_timeout_ms == 240 * MIN)
    capture(commands.handle_command, bd, 'stby:-5')
    check('stby clamps to 0', bd.standby_timeout_ms == 0)
    r, out = capture(commands.handle_command, bd, 'stby:abc')
    check('stby:abc reports, changes nothing, not activity', r is False and out == ['STBY timeout_min=0 standby=0 target=%s' % bd.brew_temperature], '%s' % out)
    r, out = capture(commands.handle_command, bd, 'stby?')
    check('stby? reports state', r is False and out == ['STBY startup_min=180 brew_min=0 has_brewed=0 standby=0 target=%s' % bd.brew_temperature], '%s' % out)
except Exception as e:
    check('stby: raised', False, repr(e))

# stbt: standby temperature (6.10.2026)
try:
    bd = make(); capture(commands.handle_command, bd, 'stby:on'); assert bd.standby
    r, out = capture(commands.handle_command, bd, 'stbt:70')
    check('stbt:70 in standby: target 70, stays in standby (not activity), reports', r is True and bd.standby and
          bd.standby_temperature == 70 and bd.get_target_temperature() == 70 and
          out == ['STBT temp=70 standby=1 target=70'], '%s' % out)
    capture(commands.handle_command, bd, 'stbt:120')
    check('stbt clamps to 95', bd.standby_temperature == 95)
    capture(commands.handle_command, bd, 'stbt:10')
    check('stbt clamps to 60', bd.standby_temperature == 60)
    r, out = capture(commands.handle_command, bd, 'stbt:abc')
    check('stbt:abc changes nothing, reports, not activity', r is False and bd.standby_temperature == 60 and bd.standby and
          out == ['STBT temp=60 standby=1 target=60'], '%s' % out)
    bd = make(); bd.brew_temperature = 88.0; capture(commands.handle_command, bd, 'stbt:95'); capture(commands.handle_command, bd, 'stby:on')
    check('stbt 95 > brew 88 -> standby target 88', bd.standby and bd.get_target_temperature() == 88.0, str(bd.get_target_temperature()))
    bd = make(); capture(commands.handle_command, bd, 'stbt:75'); capture(commands.handle_command, bd, 'stby:on')
    check('stbt:75 in standby -> target 75', bd.get_target_temperature() == 75, str(bd.get_target_temperature()))
except Exception as e:
    check('stbt: raised', False, repr(e))

# main.py wiring (text check: the loop itself needs the whole firmware)
src = open(os.path.join(HERE, '..', 'pico', 'main.py')).read()
loop = src[src.index('while True:', src.index('MAIN LOOP - LOCAL PROGRAM')):]
check('main.py: update_standby before thermostat.run', 0 < loop.index('update_standby(') < loop.index('thermostat.run()'))
check('main.py: all three switches note activity', all(s in loop[:loop.index('thermostat.run()')]
      for s in ('SWITCH_BREW.value()', 'SWITCH_WATER.value()', 'SWITCH_STEAM.value()')) and "note_activity(_now, 'switch')" in loop)
# hot water moved to functions.hot_water_run (EXPRESSO-KUUMAVESI-RAJAT 7.10.2026): it notes activity itself
fsrc = open(os.path.join(HERE, '..', 'pico', 'functions.py')).read()
hw = fsrc[fsrc.index('async def hot_water_run('):]
check('main.py: brew and tshot branches note activity on return, hot water via hot_water_run',
      loop.count('brew_data.note_activity(utime.ticks_ms()') == 2 and 'await hot_water_run(' in loop and
      "brew_data.note_activity(utime.ticks_ms(), 'switch')" in hw)

print('RESULT: %d failed' % len(fails))
sys.exit(1 if fails else 0)
