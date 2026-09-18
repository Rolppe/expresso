"""Pre-infusion against a plant fitted to the measured real shot (18.9.2026 06:56:42).

The shot_test plant was fitted to the needle-valve test shots and rises ~5 bar/s at 25 % duty; the
real coffee puck rose 0.19 bar/s. Rates read from the BLE capture:
  build-up step 2 (25 % duty): 1.0 -> 1.5 bar in 2.6 s      -> 0.19 bar/s net
  hold start (max_duty back to 1.0): 1.9 -> 3.84 in 0.6 s   -> 3.2 bar/s
  brew ramp (full duty): 2.0 -> 9.41 bar in 1.1 s           -> 6.7 bar/s
  => dp/dt = 6.7 when the pump relay is on, minus a flow term 1.24 * p
Actuator+sensor delay 70 ms as in the fitted model (pi_sim.py).
"""
import sys, random, io, contextlib, asyncio as aio, statistics
src = open('/tmp/devsafe7-testit/shot_test.py').read().split('fails = []')[0]
exec(compile(src, 'shot_test_prelude', 'exec'), globals())

GAIN, LEAK = 6.7, 1.24

def make_plant(trace):
    def plant_real(dt_s):
        for _ in range(int(round(dt_s * 1000))):
            state['queue'].append(pins.get(11, 0)); a = state['queue'].pop(0)
            p = state['p'] + ((GAIN if a else 0.0) - LEAK * state['p']) / 1000.0
            state['p'] = p if p > 0 else 0.0
            trace.append(state['p']); clock[0] += 0.001
    return plant_real

def run(seed):
    random.seed(seed)
    bd = make_brew_data(); bd.pre_infusion_pressure = 2.0; bd.pre_infusion_time = 5.0
    state['p'] = 0.0; state['queue'] = [0] * 70; state['force_over'] = False; clock[0] = 0.0
    trace = []
    orig = globals()['plant']; globals()['plant'] = make_plant(trace)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        aio.run(functions.pre_infusion(bd, utime, FakeAsyncio,
                                       PumpRatioCalculator(utime, FakeAsyncio),
                                       lambda: clock[0] < 14.0))
    globals()['plant'] = orig
    # time to first reach the target, and the peak after it
    hit = next((i for i, p in enumerate(trace) if p >= 1.9), None)
    peak = max(trace[hit:]) if hit is not None else max(trace)
    return hit / 1000.0 if hit is not None else float('nan'), peak, trace[-1]

rows = [run(s) for s in range(5)]
print('  ajo  tavoite saavutettu  huippu sen jälkeen  loppu')
for i, (t, mx, last) in enumerate(rows):
    print('   %d        %5.2f s            %5.2f bar     %5.2f' % (i, t, mx, last))
print('KESKIARVO: tavoitteeseen %.2f s, huippu %.2f bar, loppu %.2f bar'
      % (statistics.mean(r[0] for r in rows), statistics.mean(r[1] for r in rows),
         statistics.mean(r[2] for r in rows)))
print('MITATTU oikeassa uutossa: tavoitteeseen 5.0 s, huippu 3.84 bar')
