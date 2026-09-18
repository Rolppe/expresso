#!/usr/bin/env python3
"""Cut /tmp/scale.csv into steady segments and report the step between each pair.

Why this shape: the scale's weakness is not noise (sd < 0.1 g when averaged) but disturbance -
reseating the tray moves the reading up to 10 g, and every load change is followed by creep. So the
trace is segmented automatically, each segment gets a settle margin trimmed off its front, and the
step is taken between segment means. The user never has to time anything; the trace shows when the
load changed.

Usage: scale_steps.py [seconds_back] [settle_s] [min_step_g]
"""
import sys, time, statistics

BACK = float(sys.argv[1]) if len(sys.argv) > 1 else 900.0
SETTLE = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
MIN_STEP = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
MIN_SEG = 12.0          # a segment shorter than this is a transition, not a level

rows = [tuple(map(float, l.split(','))) for l in open('/tmp/scale.csv') if ',' in l]
now = time.time()
rows = [r for r in rows if now - r[0] <= BACK]
if len(rows) < 10:
    sys.exit('liian vähän näytteitä')

# split where consecutive samples jump more than MIN_STEP/2: a load change is far bigger than noise
segs, cur = [], [rows[0]]
for prev, r in zip(rows, rows[1:]):
    if abs(r[1] - prev[1]) > MIN_STEP / 2:
        segs.append(cur); cur = [r]
    else:
        cur.append(r)
segs.append(cur)
# keep only segments long enough to be a level, and trim the settle margin off the front
levels = []
for s in segs:
    if s[-1][0] - s[0][0] < MIN_SEG:
        continue
    t0 = s[0][0] + SETTLE
    body = [(t, g) for t, g in s if t >= t0]
    if len(body) < 8:
        body = s[len(s) // 2:]
    ts = [t - body[0][0] for t, _ in body]
    gs = [g for _, g in body]
    mt, mg = statistics.mean(ts), statistics.mean(gs)
    sxy = sum((t - mt) * (g - mg) for t, g in zip(ts, gs))
    sxx = sum((t - mt) ** 2 for t in ts)
    levels.append({'alku': s[0][0], 'loppu': s[-1][0], 'kesto': s[-1][0] - s[0][0],
                   'n': len(body), 'ka': mg, 'sd': statistics.pstdev(gs),
                   'ryominta': (sxy / sxx * 60.0) if sxx else 0.0})

print('%-8s %7s %6s %10s %7s %12s' % ('kello', 'kesto', 'n', 'keskiarvo', 'sd', 'ryöminta'))
for L in levels:
    print('%-8s %6.0fs %6d %9.3f g %6.3f %+9.2f g/min'
          % (time.strftime('%H:%M:%S', time.localtime(L['alku'])), L['kesto'], L['n'],
             L['ka'], L['sd'], L['ryominta']))
print()
if len(levels) > 1:
    print('ASKELEET tasojen välillä:')
    for a, b in zip(levels, levels[1:]):
        print('  %s → %s : %+8.3f g'
              % (time.strftime('%H:%M:%S', time.localtime(a['alku'])),
                 time.strftime('%H:%M:%S', time.localtime(b['alku'])), b['ka'] - a['ka']))
