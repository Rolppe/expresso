"""Pre-infusion overshoot: devsafe6 (80 % chopped build-up) vs devsafe7 (continuous build-up).

Reuses the fake MicroPython layer from shot_test.py (everything before the checks) so the plant,
the sensor noise and the 70 ms actuator delay are identical to the test suite.
"""
import sys, random, io, contextlib, asyncio as aio
src = open('/tmp/devsafe7-testit/shot_test.py').read().split('fails = []')[0]
exec(compile(src, 'shot_test_prelude', 'exec'), globals())

def peak(seed, target=2.0, hold=5.0):
    random.seed(seed)
    bd = make_brew_data()
    bd.pre_infusion_pressure = target; bd.pre_infusion_time = hold
    state['p'] = 0.0; state['queue'] = [0] * 70; state['force_over'] = False; clock[0] = 0.0
    peaks = []
    orig = globals()['plant']
    def traced(dt_s):
        orig(dt_s); peaks.append(state['p'])
    globals()['plant'] = traced
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        aio.run(functions.pre_infusion(bd, utime, FakeAsyncio,
                                       PumpRatioCalculator(utime, FakeAsyncio),
                                       lambda: clock[0] < 12.0))
    globals()['plant'] = orig
    lines = [l for l in buf.getvalue().splitlines() if l.startswith('PI ')]
    return max(peaks), peaks[-1], len(lines)

rows = [peak(s) for s in range(5)]
print('  ajo   huippu  loppu')
for i, (mx, last, n) in enumerate(rows):
    print('   %d    %5.2f   %5.2f  bar' % (i, mx, last))
print('KESKIARVO huippu %.2f bar (tavoite 2.00), loppu %.2f bar'
      % (sum(r[0] for r in rows) / len(rows), sum(r[1] for r in rows) / len(rows)))
