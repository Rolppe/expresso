#!/usr/bin/env python3
"""How fast and how quiet is the scale really? Bounds every real-time flow estimate.

Reads only: enters devsafe (relays off + read-back) and ends with machine.reset(). Samples the
HX711 pair unfiltered (no median, no averaging) in 3 s chunks so the 8 s watchdog is fed between
them, and prints time_us:grams so the host can measure rate, jitter and per-sample noise.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pico_dev

SETUP = """
import scale
s = scale.Scale()
print('INFO', s.info())
print('LINK_OK', s.link_ok())
"""

RAW = """
import time
s.reset()
t = []
g = []
t0 = time.ticks_us()
end = time.ticks_add(time.ticks_ms(), 3000)
while time.ticks_diff(end, time.ticks_ms()) > 0:
    if s.ready():
        try:
            a, b = s._shift()
        except OSError:
            continue
        c = (a - s.off_a) + s.trim_b * (b - s.off_b)
        t.append(time.ticks_diff(time.ticks_us(), t0))
        g.append(c / s.scale)
print('N %d' % len(t))
print(','.join('%d:%.3f' % (x, y) for x, y in zip(t, g)))
"""

link = pico_dev.Link()
link.enter_devsafe()
try:
    out = link.exec(SETUP, 30)
    print(out.strip())
    if 'LINK_OK True' not in out:
        sys.exit('VAAKA EI VASTAA')
    for i in range(3):
        print('--- CHUNK %d' % (i + 1))
        print(link.exec(RAW, 30).strip())
finally:
    link.reset()
    print('machine.reset() ajettu')
