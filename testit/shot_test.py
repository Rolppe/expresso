import os, sys, types, asyncio as aio, random
HERE = os.path.dirname(os.path.abspath(__file__))
# Repo firmware unless FW names another set: a leftover /tmp/fw was picked silently and the test ran against
# stale code (6.10.2026)
FW = os.environ.get('FW') or os.path.join(HERE, '..', 'pico')
sys.path.insert(0, FW)
# --- fake MicroPython modules ---
clock = [0.0]
utime = types.ModuleType('utime')
utime.ticks_ms = lambda: int(clock[0] * 1000)
utime.ticks_diff = lambda a, b: a - b
utime.ticks_add = lambda a, b: a + b
utime.ticks_us = lambda: int(clock[0] * 1000000)
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
wdt_feeds = [0]
class WDT:
    def __init__(self, timeout): self.timeout = timeout
    def feed(self): wdt_feeds[0] += 1
machine = types.ModuleType('machine'); machine.Pin = Pin; machine.WDT = WDT
machine.disable_irq = lambda: 0; machine.enable_irq = lambda s=0: None   # scale.py bit-bangs the HX711
sys.modules['machine'] = machine
import importlib.util
# Ei esiehtoa: oletuksena repon pico/; FW ja FW_PRESET ovat valinnaisia (toinen firmwarejoukko / preset.py)
PRESET = os.environ.get('FW_PRESET') or os.path.join(FW, 'preset.py')
spec = importlib.util.spec_from_file_location('preset', PRESET); preset = importlib.util.module_from_spec(spec); spec.loader.exec_module(preset); sys.modules['preset'] = preset
import classes, functions, commands, devsafe
from classes import BrewData, PumpRatioCalculator

# --- plant: pump relay 11 raises pressure, relay off decays; 70 ms actuator delay ---
state = {'p': 0.0, 'queue': [0] * 70, 'force_over': False}
def plant(dt_s):
    for _ in range(int(round(dt_s * 1000))):
        state['queue'].append(pins.get(11, 0)); a = state['queue'].pop(0)
        p = state['p']
        p += ((10 * (1 - p / 13.0) * 13 / 5) if a else (-10 * p / 8.0)) / 1000.0
        if state['force_over'] and pins.get(11, 0): p += 0.05
        state['p'] = p; clock[0] += 0.001
class FakeAsyncio:
    @staticmethod
    async def sleep_ms(ms): plant(max(ms, 1) / 1000.0)
    @staticmethod
    async def sleep(s): plant(s)

class Sensor:
    gain = 1.0; offset = 0.0; last_raw_bar = 0.0; window_peak = 0.0; WINDOW_US = 16667
    def get_pressure(self):
        plant(0.020)
        v = round(state['p'] + random.gauss(0, 0.2), 1); self.last_raw_bar = v; return v
    # run the real firmware averaging code against a fake ADC
    class _ADC:
        def read_u16(self):
            bar = state['p'] + random.gauss(0, 0.6)
            return int((bar + 3.522929) / 0.000314936)
    pressure_sensor = _ADC()
    def sample_average(self, utime_mod, window_us=None, burst=8):
        plant(0.004)
        return classes.PressureSensor.sample_average(self, utime_mod, window_us, burst)
    def reset_average(self):
        self._avg_buf = []
class Temp:
    def read_temperature(self): plant(0.080); return 93.0
    # Ilman toista ydinta (classes.TemperatureSensor.c1_*): uutto lukee kuten ennen
    def c1_active(self): return False
    def c1_on(self): return False
    def c1_off(self): pass
    def c1_temperature(self): return None
    def c1_ms(self): return None
    def c1_log(self): return 'c1_n=-1'

def make_brew_data():
    bd = BrewData.__new__(BrewData)
    bd.pressure_sensor = Sensor(); bd.temperature_sensor = Temp()
    bd.relay_guard = types.SimpleNamespace(utime=utime, user_retry=lambda now, reason: None)   # user_retry: classes.note_activity (9103dc2) kutsuu; classes.get_boiler_temperature lukee sen kellon (TURVA-TOIMILAITE)
    bd.RELAY_PUMP, bd.RELAY_SOLENOID, bd.RELAY_HEATER = Pin(11), Pin(12), Pin(13)
    bd.SWITCH_BREW, bd.SWITCH_WATER, bd.SWITCH_STEAM = Pin(7), Pin(8), Pin(9)
    bd.pre_infusion_mode = True; bd.pre_infusion_time = 3.0; bd.pre_infusion_pressure = 2.0
    bd.brew_pressure = 8.0; bd.pressure_soft_release_mode = True; bd.pressure_soft_release_time = 1.0
    bd.soft_pressure_release_arming_pressure = 3; bd.brew_temperature = 93.0; bd.steam_temperature = 125
    bd.fast_heatup_mode = False; bd.mode = 'IDLE'; bd.pressure = 0.0; bd.boiler_temperature = 0.0
    bd.pump_ratio = 0; bd.setting_changed = False
    bd.test_shot_request = None; bd.test_shot_abort = False; bd.dev_safe = False
    bd.pcal_request = None; bd.pcal_cancel = False; bd.pcal_state = 'idle'; bd.pcal_stage = ''; bd.pcal_msg = ''
    bd.pcal_target = 0.0; bd.pcal_raw = {}; bd.pcal_points = {}
    # Learned pre-infusion/brew values that save_settings persists (classes.BrewData defaults). Methods stay 0 (PI path):
    # this plant only advances the clock on sleep, so pre_infusion_phased (pim:1) never ends here; esiuutto_smoke covers it.
    bd.pre_infusion_method = 0; bd.eu_coast_s = 0.3; bd.eu_coast_fast_s = 0.2; bd.eu_g_pre = 0.0; bd.eu_tau_pre = 0.0
    bd.brew_method = 0; bd.eb_ff = 0.0; bd.eb_x = 0.0; bd.eb_g = 0.0; bd.eb_tau = 0.0; bd.eb_coast_s = 0.2
    bd.learned_ff_pre = 0.3; bd.learned_ff_brew = 0.5; bd.pressure_filtered = 0.0
    bd.weight = None; bd.weight_ms = 0; bd.weight_limit = 0.0; bd.weight_rise_limit = 0.0
    bd.weight_a = 0.0; bd.weight_b = 0.0     # per-cell grams, logged since devsafe13
    bd.flow = None; bd.flow_window_ms = 1000
    bd.pre_heat_time = 0          # save_settings reads it; not otherwise used by these tests
    bd.command_known = True
    bd.standby = False; bd.standby_timeout_ms = 30 * 60000; bd.standby_temperature = 90; bd.last_activity_ms = 0   # VALMIUSTILA
    bd.get_switch_brew = lambda: bd.SWITCH_BREW
    return bd

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)

# 1. commands
bd = make_brew_data()
commands.handle_command(bd, 'pit:4.5'); commands.handle_command(bd, 'srt:0')
commands.handle_command(bd, 'pip:9'); commands.handle_command(bd, 'bp:3')
check('pit/srt', bd.pre_infusion_time == 4.5 and bd.pre_infusion_mode and bd.pressure_soft_release_time == 0 and not bd.pressure_soft_release_mode)
check('pip/bp clamps', bd.pre_infusion_pressure == 4.0 and bd.brew_pressure == 5.0)
commands.handle_command(bd, 'tshot:200'); check('tshot clamps to 60 s', bd.test_shot_request == 60.0)
commands.handle_command(bd, 'dev:safe'); check('dev:safe cancels test shot', bd.dev_safe and bd.test_shot_request is None and bd.test_shot_abort)
check('tshot refused in dev safe', bd.request_test_shot(10) is False)
commands.handle_command(bd, 'dev:resume'); check('dev:resume', not bd.dev_safe and bd.request_test_shot(10))

# 2. test shot runs full path and stops on time
def run_shot_with(bd, seconds, label='TS', over=False, switch_at=None):
    state['p'] = 0.0; state['queue'] = [0] * 70; state['force_over'] = over; clock[0] = 0.0
    end = utime.ticks_add(utime.ticks_ms(), int(seconds * 1000))
    def running():
        if switch_at is not None and clock[0] >= switch_at: bd.SWITCH_STEAM.value(1)
        if bd.SWITCH_BREW.value() or bd.SWITCH_WATER.value() or bd.SWITCH_STEAM.value(): return False
        if bd.test_shot_abort or bd.dev_safe: return False
        return utime.ticks_diff(end, utime.ticks_ms()) > 0
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        reason = aio.run(functions.run_shot(bd, utime, FakeAsyncio, PumpRatioCalculator(utime, FakeAsyncio), running, label))
    bd.SWITCH_STEAM.value(0)
    return reason, buf.getvalue().splitlines()

bd = make_brew_data(); bd.pre_infusion_time = 3.0
reason, out = run_shot_with(bd, 20)
ts = [l for l in out if l.startswith('TS ')]
brew = [float(l.split()[2]) for l in ts if int(l.split()[1]) > 12000]
end = [l for l in out if l.startswith('TS_END')]
pi = [l for l in out if l.startswith('PI ')]
check('test shot ran pre-infusion', len(pi) > 5, '%d PI lines' % len(pi))
check('test shot ended by time', reason == '' and end and 'reason=stopped' in end[0], end[0] if end else '')
check('duration ~20 s', abs(clock[0] - 21) < 2.5, 'clock %.1f s' % clock[0])
check('brew pressure held near 8 bar', brew and abs(sum(brew) / len(brew) - 8.0) < 0.3 and min(brew) > 6.5, 'mean %.2f min %.1f max %.1f' % (sum(brew)/len(brew), min(brew), max(brew)) if brew else 'no samples')
check('relays off after shot', [pins[11], pins[12], pins[13]] == [0, 0, 0], str([pins[11], pins[12], pins[13]]))
check('max loop reported', 'max_loop_ms=' in end[0] if end else False, end[0] if end else '')

# 3. overpressure abort: a faulty controller that keeps the pump on
bd = make_brew_data(); bd.pre_infusion_mode = False; bd.brew_pressure = 10.0
_orig_update = classes.PumpPressureController.update
def _stuck_on(self, pressure, target):
    self.filtered = pressure
    self._set(True, utime.ticks_ms(), force=True); return True
classes.PumpPressureController.update = _stuck_on
reason, out = run_shot_with(bd, 30, over=True)
classes.PumpPressureController.update = _orig_update
check('overpressure aborts', reason.startswith('overpressure'), reason)
check('relays off after overpressure', [pins[11], pins[12], pins[13]] == [0, 0, 0])

# 3b. trapped thermal-expansion pressure at start (pump off) must not abort; it drains
bd = make_brew_data(); bd.pre_infusion_mode = True
state_init = 14.5
def run_trapped():
    state['p'] = state_init
    return None
orig_run = run_shot_with
def run_shot_trapped(bd, seconds):
    state['force_over'] = False
    import io, contextlib
    clock[0] = 0.0; state['queue'] = [0] * 70; state['p'] = 14.5; bd.pressure = 14.5; bd.pressure_filtered = 14.5
    end = utime.ticks_add(utime.ticks_ms(), int(seconds * 1000))
    running = lambda: utime.ticks_diff(end, utime.ticks_ms()) > 0
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        reason = aio.run(functions.run_shot(bd, utime, FakeAsyncio, PumpRatioCalculator(utime, FakeAsyncio), running, 'TS'))
    return reason, buf.getvalue().splitlines()
reason, out = run_shot_trapped(bd, 15)
check('trapped 14.5 bar at start does not abort', reason == '', reason)
check('trapped pressure shot still reaches brew loop', any(l.startswith('TS ') for l in out))

# 4. machine switch aborts test shot
bd = make_brew_data()
reason, out = run_shot_with(bd, 30, switch_at=6.0)
check('switch ends test shot within 0.2 s', clock[0] < 8.5, 'ended at %.2f s (switch 6.0 s, + soft release)' % clock[0])
check('relays off after switch', [pins[11], pins[12], pins[13]] == [0, 0, 0])

# 5. devsafe
pins[11] = pins[12] = pins[13] = 1
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf): ok = devsafe.enter()
check('devsafe.enter relays off + read-back', ok and [pins[11], pins[12], pins[13]] == [0, 0, 0], buf.getvalue().strip())
devsafe.start_watchdog(); n = wdt_feeds[0]; devsafe.feed(); check('watchdog feed', wdt_feeds[0] == n + 1)

# 6. learned feed-forward changes after a shot
bd = make_brew_data(); bd.pre_infusion_time = 3.0
reason, out = run_shot_with(bd, 20)
endl = [l for l in out if l.startswith('TS_END')]
check('learned_ff_brew updated and bounded', 0.05 <= bd.learned_ff_brew <= 0.9 and bd.learned_ff_brew != 0.5, endl[0] if endl else '')
check('learned_ff_pre updated', bd.learned_ff_pre != 0.3, 'pre %.2f' % bd.learned_ff_pre)


# 7. the pump must not be chopped while the pressure is far below the target (user, 18.9.2026)
# 7a. unit: controller with a low max_duty still holds the relay on when the error is large
pins[11] = 0
clock[0] = 0.0          # before the controller: it timestamps its window from the clock
ctrl = classes.PumpPressureController(Pin(11), PumpRatioCalculator(utime, FakeAsyncio), utime,
                                      ff=0.2, max_duty=0.25)
offs = 0
for _ in range(200):          # 1 s at 5 ms steps, pressure stuck at 0.5 bar, target 2.0
    ctrl.update(0.5, 2.0)
    if pins[11] == 0: offs += 1
    clock[0] += 0.005
check('large error keeps the pump on (max_duty 0.25)', offs == 0 and ctrl.duty == 1.0,
      '%d off samples, duty %.2f' % (offs, ctrl.duty))

# 7b. unit: near the target the time-proportional window is back in use
pins[11] = 0
ctrl = classes.PumpPressureController(Pin(11), PumpRatioCalculator(utime, FakeAsyncio), utime,
                                      ff=0.2, max_duty=0.25)
offs = 0
for _ in range(200):          # pressure 1.8 bar, target 2.0 -> error 0.2 < 1.0 bar
    ctrl.update(1.8, 2.0)
    if pins[11] == 0: offs += 1
    clock[0] += 0.005
check('small error still modulates the pump', offs > 0, '%d off samples of 200' % offs)

# 7c. flush: no basket, the pressure never leaves ~0.5 bar -> the pump runs without a single break
orig_plant = plant
trace = []
def plant_flush(dt_s):
    for _ in range(int(round(dt_s * 1000))):
        state['queue'].append(pins.get(11, 0)); a = state['queue'].pop(0)
        trace.append(pins.get(11, 0))
        p = state['p']
        # open grouphead: the pump cannot build pressure, it settles at ~0.5 bar
        p += ((0.5 - p) * 8.0 if a else -10 * p / 8.0) / 1000.0
        state['p'] = p; clock[0] += 0.001
plant = plant_flush
bd = make_brew_data(); bd.pre_infusion_pressure = 2.0; bd.pre_infusion_time = 5.0
state['p'] = 0.0; state['queue'] = [0] * 70; clock[0] = 0.0
end_t = 4.0
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aio.run(functions.pre_infusion(bd, utime, FakeAsyncio, PumpRatioCalculator(utime, FakeAsyncio),
                                   lambda: clock[0] < end_t))
plant = orig_plant
first_on = trace.index(1) if 1 in trace else -1
breaks = sum(1 for i in range(first_on + 1, len(trace)) if trace[i] == 0 and trace[i-1] == 1) if first_on >= 0 else -1
check('flush runs the pump without breaks', first_on >= 0 and breaks == 0,
      'pump started at %d ms, %d breaks, final %.2f bar' % (first_on, breaks, state['p']))
check('flush leaves the relays off at the end', pins[11] == 0, str(pins[11]))


# 8. drip-tray weight limit for test shots (user, 18.9.2026)
# 8a. command parsing and clamps
bd = make_brew_data()
commands.handle_command(bd, 'wmax:850')
check('wmax sets the limit', bd.get_weight_limit() == 850.0, str(bd.get_weight_limit()))
commands.handle_command(bd, 'wmax:-5'); low = bd.get_weight_limit()
commands.handle_command(bd, 'wmax:9999'); high = bd.get_weight_limit()
check('wmax clamps to 0..5000', low == 0.0 and high == 5000.0, '%s / %s' % (low, high))
commands.handle_command(bd, 'wmax:0')
check('wmax:0 turns the limit off', bd.get_weight_limit() == 0.0)

def run_limited(bd, seconds, limit_weight, grams, sample_hz=10.0, stale_after=None):
    """grams: callable(clock seconds) -> tray weight. The scale is sampled at sample_hz; after
    stale_after seconds it stops answering (the timestamp freezes)."""
    state['p'] = 0.0; state['queue'] = [0] * 70; state['force_over'] = False; clock[0] = 0.0
    bd.get_weight = lambda: grams(clock[0])
    def _ms():
        t = clock[0] if stale_after is None else min(clock[0], stale_after)
        return int(t * sample_hz) * int(1000 / sample_hz)
    bd.get_weight_ms = _ms
    end = utime.ticks_add(utime.ticks_ms(), int(seconds * 1000))
    running = lambda: utime.ticks_diff(end, utime.ticks_ms()) > 0
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        reason = aio.run(functions.run_shot(bd, utime, FakeAsyncio, PumpRatioCalculator(utime, FakeAsyncio),
                                            running, 'TS', limit_weight=limit_weight))
    return reason, buf.getvalue().splitlines()

# 8b. a test shot stops when the tray reaches the limit
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_limit(800)
reason, out = run_limited(bd, 30, True, lambda t: 700.0 + 20.0 * t)   # 700 g + 20 g/s -> 800 g at 5 s
check('test shot stops at the tray limit', reason.startswith('tray ') and '800' in reason, reason)
check('stopped near 5 s, not at the time limit', 4.0 < clock[0] < 8.0, 'ended %.1f s' % clock[0])
check('relays off after the weight abort', [pins[11], pins[12], pins[13]] == [0, 0, 0])

# 8c. limit off: the same rising weight does not stop the shot
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_limit(0)
reason, out = run_limited(bd, 12, True, lambda t: 700.0 + 20.0 * t)
check('limit 0 never stops a shot', reason == '', reason)

# 8d. the brew-switch path is never stopped by weight (a cup sits on the same scale)
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_limit(800)
reason, out = run_limited(bd, 12, False, lambda t: 700.0 + 20.0 * t)
check('switch path ignores the weight limit', reason == '', reason)

# 8e. no scale on the machine: with no limit set the shot runs; with a limit set it refuses,
# because a limit that cannot be watched is worse than no limit - the user believes they are covered
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_limit(0)
reason, out = run_limited(bd, 12, True, lambda t: None)
check('no scale and no limit: shot runs', reason == '', reason)
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_limit(800)
reason, out = run_limited(bd, 12, True, lambda t: None)
check('no scale but a limit set: shot refuses', reason.startswith('scale silent'), reason)


# 8f. a scale that stops answering must stop the shot, not leave the limit blind (18.9.2026)
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_limit(800)
reason, out = run_limited(bd, 30, True, lambda t: 700.0, stale_after=3.0)
check('silent scale stops a limited shot', reason.startswith('scale silent'), reason)
check('stopped within ~2 s of going silent', 4.0 < clock[0] < 9.0, 'ended %.1f s' % clock[0])
check('relays off after the silent-scale abort', [pins[11], pins[12], pins[13]] == [0, 0, 0])

# 8g. a single spike over the limit must not stop the shot; two samples must
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_limit(800)
spike = lambda t: 900.0 if 4.0 < t < 4.06 else 700.0     # one sample at 10 Hz
reason, out = run_limited(bd, 12, True, spike)
check('single spike does not stop a shot', reason == '', reason)
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_limit(800)
reason, out = run_limited(bd, 30, True, lambda t: 900.0 if t > 4.0 else 700.0)
check('two samples over the limit do stop it', reason.startswith('tray '), reason)


# 9. per-shot rise limit (18.9.2026): immune to the slow drift the absolute limit inherits
bd = make_brew_data()
commands.handle_command(bd, 'wrise:120')
check('wrise sets the rise limit', bd.get_weight_rise_limit() == 120.0, str(bd.get_weight_rise_limit()))
commands.handle_command(bd, 'wrise:-1'); lo = bd.get_weight_rise_limit()
commands.handle_command(bd, 'wrise:9999'); hi = bd.get_weight_rise_limit()
check('wrise clamps to 0..5000', lo == 0.0 and hi == 5000.0, '%s / %s' % (lo, hi))

# 9a. the shot stops once it has added the allowed amount, whatever the absolute level is
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_rise_limit(100)
reason, out = run_limited(bd, 30, True, lambda t: 5000.0 + 20.0 * t)   # absurd absolute level
check('rise limit stops the shot', reason.startswith('shot added'), reason)
check('stopped near 5 s', 4.0 < clock[0] < 9.0, 'ended %.1f s' % clock[0])

# 9b. a slow drift far larger than the rise limit must not trip it: the baseline is taken per shot
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_rise_limit(100)
reason, out = run_limited(bd, 12, True, lambda t: 900.0 + 0.5 * t)     # 0.5 g/s, 6 g over the shot
check('slow drift does not trip the rise limit', reason == '', reason)

# 9c. the two limits coexist: whichever is reached first stops the shot, with its own reason
bd = make_brew_data(); bd.pre_infusion_time = 1.0
bd.set_weight_limit(760); bd.set_weight_rise_limit(500)
reason, out = run_limited(bd, 30, True, lambda t: 700.0 + 20.0 * t)
check('absolute limit wins when it is reached first', reason.startswith('tray '), reason)
bd = make_brew_data(); bd.pre_infusion_time = 1.0
bd.set_weight_limit(5000); bd.set_weight_rise_limit(60)
reason, out = run_limited(bd, 30, True, lambda t: 700.0 + 20.0 * t)
check('rise limit wins when it is reached first', reason.startswith('shot added'), reason)

# 9d. a silent scale must stop a shot that is relying on the rise limit alone
bd = make_brew_data(); bd.pre_infusion_time = 1.0; bd.set_weight_rise_limit(100)
reason, out = run_limited(bd, 30, True, lambda t: 700.0, stale_after=3.0)
check('silent scale stops a rise-limited shot', reason.startswith('scale silent'), reason)


# 10. an unknown command must be distinguishable from a real one (18.9.2026): main.py printed
# CMD_OK for every line, so wrise:40 on a firmware without that command looked accepted
bd = make_brew_data()
commands.handle_command(bd, 'wrise:40')
check('known command reports known', bd.command_known is True)
commands.handle_command(bd, 'nosuch:1')
check('unknown command reports unknown', bd.command_known is False)
commands.handle_command(bd, 'bp:9')
check('known command after unknown resets the flag', bd.command_known is True)


# 11. the limits must survive a restart (18.9.2026): not persisting them left every run after a
# flash silently unprotected, which put the burden on the user's memory instead of the firmware
import json as _json, os as _os
bd = make_brew_data()
commands.handle_command(bd, 'wmax:470')
commands.handle_command(bd, 'wrise:250')
check('setting a limit marks settings dirty', bd.get_setting_changed())
_cwd = _os.getcwd(); _os.chdir('/tmp')
functions.save_settings(bd, _json)
saved = _json.load(open('/tmp/settings.txt'))
check('limits are written to settings', saved.get('weight_limit') == 470.0 and saved.get('weight_rise_limit') == 250.0,
      str({k: saved.get(k) for k in ('weight_limit', 'weight_rise_limit')}))
bd2 = make_brew_data()
functions.load_settings(_json, bd2)
check('limits are restored on load', bd2.get_weight_limit() == 470.0 and bd2.get_weight_rise_limit() == 250.0,
      '%s / %s' % (bd2.get_weight_limit(), bd2.get_weight_rise_limit()))
# a settings file from before the keys existed must keep the defaults, not crash
_json.dump({k: v for k, v in saved.items() if not k.startswith('weight_')}, open('/tmp/settings.txt', 'w'))
bd3 = make_brew_data()
functions.load_settings(_json, bd3)
check('old settings file keeps limits off', bd3.get_weight_limit() == 0.0 and bd3.get_weight_rise_limit() == 0.0,
      '%s / %s' % (bd3.get_weight_limit(), bd3.get_weight_rise_limit()))
# a setpoint over the limit keeps its default but must not delete the file (and wmax with it)
_json.dump(dict(saved, brew_temperature=200), open('/tmp/settings.txt', 'w'))
bd4 = make_brew_data()
functions.load_settings(_json, bd4)
check('over-limit setpoint keeps its default', bd4.brew_temperature == 93.0, str(bd4.brew_temperature))
check('over-limit setpoint keeps the file and wmax', _os.path.exists('/tmp/settings.txt') and bd4.get_weight_limit() == 470.0,
      str(bd4.get_weight_limit()))

# wmax-pysyvyys (26.10.2026): corrupt JSON must not delete settings.txt or lose defaults
with open('/tmp/settings.txt', 'w') as f:
    f.write('{"corrupted_json": ')
bd5 = make_brew_data()
res5 = functions.load_settings(_json, bd5)
check('corrupted JSON returns False', res5 is False)
check('corrupted JSON does NOT delete settings.txt', _os.path.exists('/tmp/settings.txt'))
check('corrupted JSON keeps defaults safely', bd5.get_weight_limit() == 0.0)

# wmax-pysyvyys: atomic write and recovery from .tmp
_os.remove('/tmp/settings.txt')
_json.dump(dict(saved, weight_limit=720.0, weight_rise_limit=250.0), open('/tmp/settings.txt.tmp', 'w'))
bd6 = make_brew_data()
res6 = functions.load_settings(_json, bd6)
check('recovery from settings.txt.tmp succeeds', res6 is True and bd6.get_weight_limit() == 720.0)
check('recovery restores settings.txt', _os.path.exists('/tmp/settings.txt'))

_os.chdir(_cwd)

# 12. real-time flow from the drip-tray scale (18.9.2026). Measured on the Pico: one sample every
# 86.2 ms (11.6 Hz), single-sample sd 0.22-0.26 g, consecutive differences sd*sqrt(2) -> white
# noise. The numbers below are the ones the estimator was chosen by, so they are asserted here.
import statistics as st
import time as _real_time
_t = types.ModuleType('time')
for _k in dir(_real_time):
    setattr(_t, _k, getattr(_real_time, _k))
_t.ticks_ms = lambda: int(clock[0] * 1000)
_t.ticks_us = lambda: int(clock[0] * 1000000)
_t.ticks_diff = lambda a, b: a - b
_t.ticks_add = lambda a, b: a + b
_t.sleep_ms = lambda ms: None
_t.sleep_us = lambda us: None
sys.modules['time'] = _t
import scale

DT = 0.0862
SIGMA = 0.25

def make_scale(window_ms=1000):
    sc = scale.Scale.__new__(scale.Scale)
    sc.pin_a, sc.pin_b, sc.pin_sck = 18, 20, 19
    sc.extra = 1
    sc.cal_file = '/tmp/does-not-exist.json'
    sc.window = 8
    sc.off_a = sc.off_b = 0.0
    sc.trim_b = 1.0
    sc.scale = 1.0
    sc.calibrated = True
    sc.errors = 0
    sc._buf = []; sc._hist = []; sc._raw = []; sc._flow_raw = []
    sc._flow_n = 48
    sc.flow_window_ms = window_ms
    sc.ready = lambda: True
    return sc

def feed(sc, grams_series):
    """One sample per 86.2 ms tick; returns the flow reading after each sample."""
    out = []
    for g in grams_series:
        clock[0] += DT
        sc._shift = lambda g=g: (g, 0.0)
        sc.update()
        out.append(sc.flow())
    return out

def shot_series(rng, flow=2.3, quiet_s=3.0, run_s=12.0, glitch_at=None):
    """Tray mass with `quiet_s` at rest, then a 0.4 s ramp to `flow` g/s."""
    out = []
    m = 0.0
    n = int((quiet_s + run_s) / DT)
    for i in range(n):
        t = i * DT
        if t > quiet_s:
            out_flow = flow * min((t - quiet_s) / 0.4, 1.0)
            m += out_flow * DT
        g = m + rng.gauss(0, SIGMA)
        if glitch_at is not None and i == glitch_at:
            g -= 16.0            # the single-sample glitch seen in 0.19 % of real samples
        out.append(g)
    return out

rng = random.Random(7)
sc = make_scale()
f = feed(sc, shot_series(rng))

# flow() cache (EXPRESSO-GC-UUTTO): a repeat call without a new sample returns the cached fit, a new span or
# sample recomputes it, and a stale reading is still None
h = sc._flow_raw
v1 = sc.flow()
hit = sc.flow() is v1 and v1 == sc._flow_fit(h, h[-1][0], sc.flow_window_ms)
v_span = sc.flow(sc.flow_window_ms // 2)
fresh_span = v_span == sc._flow_fit(h, h[-1][0], sc.flow_window_ms // 2)
clock[0] += DT
sc._shift = lambda: (h[-1][1] + 0.2, 0.0)
sc.update()
v2 = sc.flow()
fresh_new = v2 == sc._flow_fit(sc._flow_raw, sc._flow_raw[-1][0], sc.flow_window_ms)
clock[0] += (scale.FLOW_STALE_MS + 50) / 1000.0
stale = sc.flow() is None
check('flow cache: hit, new span, new sample, stale', hit and fresh_span and fresh_new and stale,
      'hit=%s span=%s new=%s stale=%s' % (hit, fresh_span, fresh_new, stale))
clock[0] -= (scale.FLOW_STALE_MS + 50) / 1000.0
steady = [x for x in f[int(6.0 / DT):] if x is not None]
check('flow follows a steady 2.3 g/s', abs(st.mean(steady) - 2.3) < 0.25, 'mean %.2f g/s' % st.mean(steady))
check('flow noise at a 1 s window stays under 0.35 g/s', st.pstdev(steady) < 0.35, 'sd %.2f g/s' % st.pstdev(steady))

# latency: how long after the real step does the reading reach 90 % of it
lat = None
for i, x in enumerate(f):
    t = (i + 1) * DT
    if t > 3.0 and x is not None and x >= 0.9 * 2.3:
        lat = t - 3.0
        break
check('flow reaches 90 % of the step within 1.3 s', lat is not None and lat < 1.3,
      'viive %.2f s' % (lat if lat is not None else -1))

# glitch immunity: the median of three must keep one -16 g sample out of the fit
rng2 = random.Random(7)
clean = feed(make_scale(), shot_series(rng2, glitch_at=None))
rng3 = random.Random(7)
dirty = feed(make_scale(), shot_series(rng3, glitch_at=int(8.0 / DT)))
worst = max(abs(a - b) for a, b in zip(clean, dirty) if a is not None and b is not None)
check('one -16 g glitch moves flow by less than 1.5 g/s', worst < 1.5, 'pahin %.2f g/s' % worst)

# too few samples, and stale samples, are not a flow
sc2 = make_scale()
few = feed(sc2, [0.0, 0.1, 0.0, 0.1])
check('under 4 points in the window gives None', few[0] is None and few[1] is None)
sc3 = make_scale()
feed(sc3, shot_series(random.Random(1), run_s=6.0))
check('a flow is read while the samples are fresh', sc3.flow() is not None)
clock[0] += 0.6
check('samples older than 0.5 s give None, not a frozen flow', sc3.flow() is None)

# the window is a knob, clamped
bdf = make_brew_data()
commands.handle_command(bdf, 'fwin:300')
check('fwin sets the flow window', bdf.get_flow_window_ms() == 300 and bdf.command_known)
commands.handle_command(bdf, 'fwin:9000'); hi = bdf.get_flow_window_ms()
commands.handle_command(bdf, 'fwin:10'); lo = bdf.get_flow_window_ms()
check('fwin clamps to 200-3000 ms', hi == 3000 and lo == 200, '%s / %s' % (hi, lo))
sc4 = make_scale()
feed(sc4, shot_series(random.Random(3), run_s=8.0))
narrow = sc4.flow(300)
wide = sc4.flow(2000)
check('a narrower window is still a flow, from fewer points', narrow is not None and wide is not None
      and abs(narrow - 2.3) < 1.2 and abs(wide - 2.3) < 0.4, '0.3 s %.2f / 2.0 s %.2f' % (narrow, wide))

# 13. the flow must not cost the telemetry packet (18.9.2026: weight alone pushed it to 246 B and
# the whole packet was lost during a shot)
bluetooth = types.ModuleType('bluetooth')
bluetooth.UUID = lambda x: x
bluetooth.FLAG_READ = 1; bluetooth.FLAG_NOTIFY = 2; bluetooth.FLAG_WRITE = 4
sys.modules['bluetooth'] = bluetooth
mp = types.ModuleType('micropython'); mp.const = lambda x: x
sys.modules['micropython'] = mp
import bluetooth_handler as bh
import json as _json

bdp = make_brew_data()
bdp.mode = 'pre-infusion pressure build-up'      # longest mode string in the firmware
bdp.weight = 4999.94
bdp.flow = -12.345
bdp.pressure = 12.345678
bdp.boiler_temperature = 123.456789
payload = bh.live_payload(bdp)
raw_len = len(_json.dumps(payload))
sent = bh.trim_payload(payload, _json)
check('the worst-case live packet fits 240 B without dropping anything', sent is not None
      and len(sent) <= 240, '%d B raakana' % raw_len)
check('no weight or flow in the live packet (V-210: own packet)', 'flow' not in payload and 'weight' not in payload)

bdp.tray_scale = object()
bdp.tare_abs_g = 4000.0
fp = bh.scale_payload(bdp)
fsent = bh.trim_payload(fp, _json)
check('the scale packet carries the app keys and fits 240 B',
      fsent is not None and len(fsent) <= 240 and {'weight_g', 'weight_abs_g', 'flow_g_s'}.issubset(set(fp)),
      '%d B: %s' % (len(fsent), fsent))
check('weight_g is tared, weight_abs_g absolute, rounding 0.1 g / 0.01 g/s',
      fp['weight_g'] == 999.9 and fp['weight_abs_g'] == 4999.9 and fp['flow_g_s'] in (-12.35, -12.34), str(fp))
bdp2 = make_brew_data()
check('no scale means no scale packet', bh.scale_payload(bdp2) is None)
bdp3 = make_brew_data(); bdp3.tray_scale = object(); bdp3.weight = 700.04
check('a stale flow is 0.0, not null (the app keeps the old value on null)',
      bh.scale_payload(bdp3).get('flow_g_s') == 0.0 and bh.scale_payload(bdp3).get('weight_g') == 700.0)
bdp4 = make_brew_data(); bdp4.tray_scale = object()
check('no reading means no scale packet', bh.scale_payload(bdp4) is None)
over = bh.trim_payload(dict(payload), _json, max_len=40)
check('a packet that cannot be trimmed to fit returns None', over is None)

# 14. no scale: no flow, and the log line says so instead of printing a number
bdn = make_brew_data()
check('no scale gives no flow', bdn.get_flow() is None)
check('the log tail marks a missing scale', functions.weight_flow_log(bdn) == 'w=- f=-',
      functions.weight_flow_log(bdn))
bdn.weight = 772.49; bdn.flow = 2.3456
check('the log tail prints weight and flow', functions.weight_flow_log(bdn) == 'w=772.5 f=2.35',
      functions.weight_flow_log(bdn))


print('\nRESULT: %d failed' % len(fails)); sys.exit(1 if fails else 0)
