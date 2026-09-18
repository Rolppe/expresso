#!/usr/bin/env python3
"""Statistics over a time window of /tmp/scale.csv: mean, sd, drift slope.

Usage: scale_stats.py <seconds ago from> <seconds ago to> [label]
       scale_stats.py 60 0   -> the last 60 s
"""
import sys, time, statistics
rows = [tuple(map(float, l.split(','))) for l in open('/tmp/scale.csv') if ',' in l]
now = time.time()
a, b = float(sys.argv[1]), float(sys.argv[2])
w = [(t, g) for t, g in rows if now - a <= t <= now - b]
if len(w) < 4:
    sys.exit('vain %d näytettä ikkunassa' % len(w))
ts = [t - w[0][0] for t, _ in w]
gs = [g for _, g in w]
mean = statistics.mean(gs)
# least squares slope, g per minute
mt, mg = statistics.mean(ts), mean
sxy = sum((t - mt) * (g - mg) for t, g in zip(ts, gs))
sxx = sum((t - mt) ** 2 for t in ts)
slope = (sxy / sxx * 60.0) if sxx else 0.0
print('%s n=%d  kesto %.1f s  ka %8.3f g  sd %.3f g  vaihteluväli %.2f g  ryöminta %+.2f g/min'
      % (sys.argv[3] if len(sys.argv) > 3 else 'ikkuna', len(w), ts[-1], mean,
         statistics.pstdev(gs), max(gs) - min(gs), slope))
