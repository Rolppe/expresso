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
RUN_S = T0 + 44.0   # VIRTAUSSAATO-2 luku 4: covers the whole valve range, not just the tight end
K_SLOWEST = 0.50    # slowest reachable phase in the k-schedule below
# VIRTAUSSAATO-2.correction-3.md K4: settle margin for assertion 1, derived, not chosen. Plant time
# constant tau = 1/k; a step response settles in about 2*tau; the slowest reachable phase is
# k=0.50 (tau=2.0 s) -> 2*tau=4.0 s. correction-2's 1.0 s moving average eats its own window on
# top of that. Total: 2/K_SLOWEST + 1.0 = 5.0 s. Recompute this if the k-schedule below changes.
SETTLE_MARGIN_S = 2.0 / K_SLOWEST + 1.0
def k_at(t):
    t -= T0
    if t < 8.0: return 0.50
    if t < 16.0: return 0.166
    if t < 26.0: return 0.50
    if t < 35.0: return 1.5
    return 3.0
# Known limitation, recorded here per VIRTAUSSAATO-2.spec.md luku 4: this model makes flow directly
# proportional to duty (6.7*u at equilibrium), while the real pump has a minimum stroke and
# backflow. Retune from the first hardware run.
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
            # VIRTAUSSAATO-2.correction-1.md K1: fmode:off regression proves pressure control is
            # unchanged, not that it survives an open valve (it can't, k=3.0 caps at ~2.2 bar) — so
            # it runs the plant at a fixed, reachable k instead of the fmode:on schedule.
            k = k_at(clock[0]) if flow_mode else 0.50
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

def band_ok(ts, fs, t0, t1, margin=2.5, tol=0.3, target=TARGET):
    return all(abs(f - target) <= tol for t, f in zip(ts, fs) if t0 + margin <= t < t1)

def moving_avg_1s(fs, window_s=1.0, sample_ms=1):
    """Trailing moving average over the same window length (default 1.0 s) as the scale's own flow
    estimator (bd.flow_window_ms), applied to the trace's flow_true series (VIRTAUSSAATO-2
    correction-2 K2): pump strokes and the 1.0 s scale window mean nobody controls or observes
    instantaneous flow, only its 1.0 s average."""
    window_n = int(round(window_s * 1000 / sample_ms))
    csum = [0.0]
    for f in fs:
        csum.append(csum[-1] + f)
    out = []
    for i in range(len(fs)):
        j = max(0, i - window_n + 1)
        out.append((csum[i + 1] - csum[j]) / (i - j + 1))
    return out

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)

trace, lines = run(True)
ts = [r[0] for r in trace]; ps = [r[1] for r in trace]; fs = [r[2] for r in trace]
fs_avg = moving_avg_1s(fs)
check('flow (1.0 s moving average) settles within 5.0 s (derived, correction-3 K4) at the start (k=0.50) and stays there', band_ok(ts, fs_avg, T0, T0 + 8.0, margin=SETTLE_MARGIN_S))
check('flow (1.0 s moving average) settles within 5.0 s (derived, correction-3 K4) of the 16 s change (k=0.50) and stays there', band_ok(ts, fs_avg, T0 + 16.0, T0 + 26.0, margin=SETTLE_MARGIN_S))
check('flow (1.0 s moving average) settles within 5.0 s (derived, correction-3 K4) of the 26 s change (k=1.5) and stays there', band_ok(ts, fs_avg, T0 + 26.0, T0 + 35.0, margin=SETTLE_MARGIN_S))
check('flow (1.0 s moving average) settles within 5.0 s (derived, correction-3 K4) of the 35 s change (k=3.0) and stays there', band_ok(ts, fs_avg, T0 + 35.0, RUN_S, margin=SETTLE_MARGIN_S))
check('pressure never exceeds 12.0 bar', max(ps) <= 12.0, 'huippu %.2f bar' % max(ps))
check('pressure never reaches 13 bar', max(ps) < 13.0, 'huippu %.2f bar' % max(ps))
rows = parse_log(lines)
tail_rows = [r for r in rows if T0 + 8.0 <= r[0] / 1000.0 < T0 + 16.0]
sat_rows = [r for r in tail_rows if r[2] == 1]
first_sat = sat_rows[0][0] / 1000.0 if sat_rows else None
stays_sat = first_sat is not None and all(r[2] == 1 for r in tail_rows if r[0] / 1000.0 >= first_sat)
check('fsat reaches 1 within 6.5 s of the k=0.166 phase (8 s) and stays 1 to the end of that phase',
      first_sat is not None and first_sat - (T0 + 8.0) <= 6.5 and stays_sat,
      ('fsat=1 at %.2f s' % first_sat) if first_sat is not None else 'ei koskaan')
check('the run reaches the end without an early abort', end_reason(lines) == 'stopped', str(end_reason(lines)))
# VIRTAUSSAATO-2.correction-5.md K9: assertion 6 — a flag tied only to filtered error can rise
# briefly in a big valve-change transient; that's fine, but it must prove it comes back down.
# correction-6 K11: the start phase is excluded. Flow starts from zero there, so the flag is
# *correct* to rise, and clearing it needs the derived 5.0 s settle plus the 4.0 s half-rate leak
# = 9.0 s, which does not fit an 8.0 s phase. Assertion 7 below covers the start phase instead.
phase_windows = [
    ('16 s (k=0.50)', T0 + 16.0, T0 + 26.0),
    ('26 s (k=1.5)', T0 + 26.0, T0 + 35.0),
    ('35 s (k=3.0)', T0 + 35.0, RUN_S),
]
for name, t0, t1 in phase_windows:
    last3 = [r for r in rows if t1 - 3.0 <= r[0] / 1000.0 < t1]
    n_sat = sum(1 for r in last3 if r[2] == 1)
    # correction-6 K12: the extra text states this row's own count. It used to print the failure
    # reason on passing rows too, and a green row carrying a red reason is how a green fence stops
    # being evidence.
    check('fsat is 0 for the last 3.0 s of phase %s' % name,
          bool(last3) and n_sat == 0,
          'no rows' if not last3 else 'fsat=1 %d/%d riviä' % (n_sat, len(last3)))

# correction-6 K11, assertion 7: the start phase gets a positive requirement instead of an
# exemption — flow starts from zero, the target is genuinely not met, and the flag must say so.
start_rows = [r for r in rows if T0 <= r[0] / 1000.0 < T0 + 5.0]
n_start_sat = sum(1 for r in start_rows if r[2] == 1)
check('fsat is 1 somewhere in the first 5.0 s of the start phase (flow starts from zero)',
      n_start_sat > 0, 'fsat=1 %d/%d riviä' % (n_start_sat, len(start_rows)))

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
