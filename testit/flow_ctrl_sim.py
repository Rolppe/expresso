"""Host simulation for the outer flow cascade (VIRTAUSSAATO), no hardware. Loads shot_test.py's
fixture prelude the same way as real_plant_sim.py:12-14, but the path is this file's own directory,
not a /tmp constant, so it runs straight from a working copy."""
import os, sys, types, random, io, contextlib, asyncio as aio, time as _real_time
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'shot_test.py')).read().split('fails = []')[0]
exec(compile(src, 'shot_test_prelude', 'exec'), globals())
# Real scale.Scale through a faked `time` module tied to the same clock (model: shot_test.py's
# section 12, make_scale/feed).
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
GAIN = 6.7          # dp/dt = GAIN*u - k*p, pump relay only (functions.py brew loop)
SAMPLE_MS = 86      # scale sample interval (measured, KEHITYSYHTEYS.md:747-776)
SIGMA, TARGET = 0.25, 2.2
P_MAX = 10.5        # frozen FlowController default (correction-1 K4: not tunable)
T0 = 7 * SAMPLE_MS / 1000.0   # prime the scale (median-3 costs 2, FLOW_MIN_POINTS 4, pump off) first
RUN_S = T0 + 34.0   # last phase 24-34 s (correction-1 K3)
def k_at(t):
    t -= T0
    if t < 8.0: return 0.50
    if t < 16.0: return 0.30
    if t < 24.0: return 0.50
    return 0.166
def run(flow_mode):
    random.seed(1)
    bd = make_brew_data()
    bd.pre_infusion_mode = False
    sc = make_scale()
    state['p'] = 0.0; state['queue'] = [0] * 70; state['force_over'] = False; clock[0] = 0.0
    w = [0.0]
    trace = []       # (t_s, p_bar, flow_true_g_s)
    since = [0]
    def plant_sim(dt_s):
        for _ in range(int(round(dt_s * 1000))):
            state['queue'].append(pins.get(11, 0)); a = state['queue'].pop(0)
            k = k_at(clock[0])
            p = state['p'] + ((GAIN if a else 0.0) - k * state['p']) / 1000.0
            p = p if p > 0.0 else 0.0
            state['p'] = p
            flow_true = k * p
            w[0] += flow_true / 1000.0
            clock[0] += 0.001
            trace.append((clock[0], p, flow_true))
            since[0] += 1
            if since[0] >= SAMPLE_MS:
                since[0] = 0
                g = w[0] + random.gauss(0, SIGMA)
                sc._shift = lambda g=g: (g, 0.0)
                sc.update()
                bd.flow = sc.flow(bd.flow_window_ms)
    orig = globals()['plant']; globals()['plant'] = plant_sim
    plant_sim(T0)
    commands.handle_command(bd, 'fmode:%s' % ('on' if flow_mode else 'off'))
    commands.handle_command(bd, 'fset:%.1f' % TARGET)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        aio.run(functions.run_shot(bd, utime, FakeAsyncio, PumpRatioCalculator(utime, FakeAsyncio),
                                    lambda: clock[0] < RUN_S, 'TS'))
    globals()['plant'] = orig
    return trace, buf.getvalue().splitlines()

def parse_log(lines):
    rows = []
    for ln in lines:
        parts = ln.split()
        if len(parts) < 13 or parts[0] != 'TS':
            continue
        rows.append((int(parts[1]), float(parts[3]), int(parts[-1].split('=')[1])))
    return rows
def end_reason(lines):
    for ln in lines:
        if ln.startswith('TS_END'):
            return ln.split('reason=')[1].split()[0]
    return None

def band_ok(ts, fs, t0, t1, margin=2.5, tol=0.25, target=TARGET):
    return all(abs(f - target) <= tol for t, f in zip(ts, fs) if t0 + margin <= t < t1)

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)

trace, lines = run(True)
ts = [r[0] for r in trace]; ps = [r[1] for r in trace]; fs = [r[2] for r in trace]
check('flow settles within 2.0 s (+0.5 s grace) of the 8 s change and stays there', band_ok(ts, fs, T0 + 8.0, T0 + 16.0))
check('flow settles within 2.0 s (+0.5 s grace) of the 16 s change and stays there', band_ok(ts, fs, T0 + 16.0, T0 + 24.0))
check('pressure never exceeds 12.0 bar', max(ps) <= 12.0, 'huippu %.2f bar' % max(ps))
check('pressure never reaches 13 bar', max(ps) < 13.0, 'huippu %.2f bar' % max(ps))
settle = [p for t, p in zip(ts, ps) if T0 + 30.0 <= t < RUN_S]
worst_p = max(abs(p - P_MAX) for p in settle) if settle else -1.0
check('pressure settles within p_max +- 0.5 bar by 6.0 s into the unreachable-target phase and stays there',
      bool(settle) and worst_p <= 0.5, 'poikkeama %.2f bar' % worst_p)
rows = parse_log(lines)
tail_rows = [r for r in rows if r[0] / 1000.0 >= T0 + 24.0]
sat_rows = [r for r in tail_rows if r[2] == 1]
first_sat = sat_rows[0][0] / 1000.0 if sat_rows else None
stays_sat = first_sat is not None and all(r[2] == 1 for r in tail_rows if r[0] / 1000.0 >= first_sat)
check('fsat reaches 1 within 6.5 s of the unreachable-target phase (24 s) and stays 1 to the end',
      first_sat is not None and first_sat - (T0 + 24.0) <= 6.5 and stays_sat,
      ('fsat=1 at %.2f s' % first_sat) if first_sat is not None else 'ei koskaan')
check('the run reaches the end without an early abort', end_reason(lines) == 'stopped', str(end_reason(lines)))

trace2, lines2 = run(False)
rows2 = parse_log(lines2)
check('fmode:off keeps target constant at brew_pressure',
      bool(rows2) and all(abs(t - 8.0) < 1e-6 for _, t, _ in rows2))
tail = [p for t, p, f in trace2 if T0 + 30.0 <= t < RUN_S]
worst = max(abs(p - 8.0) for p in tail) if tail else -1.0
check('fmode:off settles pressure within 0.5 bar of brew_pressure (regression)', tail and worst <= 0.5,
      'poikkeama %.2f bar' % worst)

print('RESULT: %d failed' % len(fails))
sys.exit(0 if not fails else 1)
