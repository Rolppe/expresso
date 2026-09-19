"""Host tests for the pressure calibration run and the vented zero (PCAL-KORJAUS), no hardware.

Loads shot_test.py's fixture prelude the same way flow_ctrl_sim.py does. The hold and timeout
constants are shortened here: what is under test is the phase logic, not the wall-clock length of a
hold a human reads a gauge during.
"""
import os, sys, io, contextlib, asyncio as aio
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'shot_test.py')).read().split('fails = []')[0]
exec(compile(src, 'shot_test_prelude', 'exec'), globals())

functions.PCAL_HOLD_MS = 3000
functions.PCAL_TIMEOUT_MS = 20000

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)

def closed_plant(rise_per_s, leak_per_s=0.02, stroke_bar=0.0):
    """Closed circuit: the pump only adds, and nothing takes pressure back out.

    `rise_per_s` is the continuous rise while the relay is held on (the coarse phase). `stroke_bar`
    is a fixed dose added on the relay's *rising edge*, which is how the real machine behaves: one
    17 ms stroke is worth about 1 bar (measured 19.9.2026, closed circuit), and that dose does not
    scale with how long the relay stays on."""
    prev = [0]
    def plant_fn(dt_s):
        for _ in range(int(round(dt_s * 1000))):
            on = pins.get(11, 0)
            p = state['p'] + ((rise_per_s if on else -leak_per_s) / 1000.0)
            if on and not prev[0] and stroke_bar:
                p += stroke_bar
            prev[0] = on
            state['p'] = p if p > 0.0 else 0.0
            clock[0] += 0.001
    return plant_fn

def run_stage(plant_fn, target, stage='brew', window_ms=500):
    bd = make_brew_data()
    bd.set_brew_pressure(target) if stage == 'brew' else bd.set_pre_infusion_pressure(target)
    bd.set_pcal_window_ms(window_ms)
    state['p'] = 0.0; state['queue'] = [0] * 70; state['force_over'] = False; clock[0] = 0.0
    orig = globals()['plant']; globals()['plant'] = plant_fn
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        aio.run(functions.pressure_calibration_run(bd, utime, FakeAsyncio, stage))
    globals()['plant'] = orig
    return bd, buf.getvalue()

def line(out, prefix):
    for ln in out.splitlines():
        if ln.startswith(prefix):
            return ln
    return ''

# 1. a slow rise must not store a point: the old run averaged seconds 5-10 regardless
bd, out = run_stage(closed_plant(0.05), 8.0)
check('a pressure that never reaches the target stores no point',
      bd.pcal_raw.get('brew') is None and 'not settled' in out, line(out, 'PCAL_ABORT') or 'ei ABORT-riviä')

# 2. the timeout ends the run with a named reason
check('the timeout reason is named on the abort line', 'reason=not settled' in out, line(out, 'PCAL_ABORT'))

# 3. a normal rise settles and stores a point measured at the target
bd, out = run_stage(closed_plant(3.0), 8.0)
raw = bd.pcal_raw.get('brew')
check('a settled hold stores a point', raw is not None, 'raw=%s' % raw)
check('the stored point is measured at the target, not on the way up',
      raw is not None and abs(raw - 8.0) <= 0.5, 'raw=%.2f vs target 8.0' % raw if raw else 'ei pistettä')

# 4. the hold starts only after the settle, and says so
check('the settled line is printed before the end line',
      'PCAL_SETTLED' in out and out.index('PCAL_SETTLED') < out.index('PCAL_END'), line(out, 'PCAL_SETTLED'))

# 5. the end line carries the named fields, including the ripple measurement
end = line(out, 'PCAL_END')
check('the end line names raw, n, the ripple and the window',
      all(k in end for k in ('raw=', 'n=', 'p_min=', 'p_max=', 'window=')), end)

# 6. an overshoot does not start the counter and stores nothing
# A dose far larger than the coarse phase leaves room for: the fine phase's first stroke lands
# well past the target, and a closed circuit cannot give it back.
bd, out = run_stage(closed_plant(3.0, stroke_bar=3.0), 8.0)
check('an overshoot ends the run and stores no point',
      bd.pcal_raw.get('brew') is None and 'overshoot' in out, line(out, 'PCAL_ABORT') or 'ei ABORT-riviä')

# A realistic dose (one stroke ~= 1 bar) must still settle: the criteria are on the 1 s average, so
# a sawtooth of a stroke's size is not an overshoot.
bd, out = run_stage(closed_plant(3.0, stroke_bar=1.0), 8.0)
raw1 = bd.pcal_raw.get('brew')
check('a one-bar stroke sawtooth still settles and stores a point',
      raw1 is not None and abs(raw1 - 8.0) <= 1.5, line(out, 'PCAL_END') or line(out, 'PCAL_ABORT'))

# 7. the vented zero cycles until the raw value stops moving, then writes the offset
class _Sensor:
    gain = 0.9; offset = 0.0; saved = [0]
    def __init__(self): self.reads = 0
    @staticmethod
    def calibration_valid(gain, offset): return 0.5 <= gain <= 1.5 and -3.0 <= offset <= 3.0
    def set_calibration(self, gain, offset): self.gain, self.offset = gain, offset
    def save_calibration(self): self.saved[0] += 1

bd = make_brew_data()
sensor = _Sensor()
bd.pressure_sensor = sensor
decay = [3.0]
def fake_avg(utime_module):
    decay[0] *= 0.5
    return decay[0]
bd.get_pressure_average = fake_avg
bd.get_pressure_raw = lambda: round(decay[0], 3)
state['p'] = 0.0; clock[0] = 0.0
orig = globals()['plant']; globals()['plant'] = closed_plant(0.0)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aio.run(functions.pressure_zero_run(bd, utime, FakeAsyncio))
globals()['plant'] = orig
out = buf.getvalue()
check('the vented zero writes the offset only after the raw value is stable',
      'PZERO_OK' in out and sensor.saved[0] == 1, line(out, 'PZERO_OK') or line(out, 'PZERO_ABORT'))
check('the offset zeroes the vented reading', abs(sensor.offset + sensor.gain * round(decay[0], 3)) < 1e-6,
      'offset=%.4f gain=%.3f raw=%.4f' % (sensor.offset, sensor.gain, decay[0]))

print('\nRESULT: %d failed' % len(fails)); sys.exit(1 if fails else 0)
