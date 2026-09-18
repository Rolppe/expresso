#!/usr/bin/env python3
"""When does water actually start arriving after the pump starts?

The boiler sometimes holds air (user, 18.9.2026), so the first seconds of a shot deliver nothing and
a flow rate extrapolated from a short shot is wrong. Both facts are in the same telemetry: `mode`
leaves IDLE when the shot starts, and the weight starts rising when water reaches the tray.
"""
import re, datetime, sys, statistics

rx = re.compile(r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+).*\[DATA\] RX settings \{(.*)\}')
rows = []
for line in open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/hist3.log', errors='replace'):
    m = rx.match(line)
    if not m:
        continue
    d = dict(p.split(': ', 1) for p in m.group(2).split(', ') if ': ' in p)
    t = datetime.datetime.strptime('2026-' + m.group(1), '%Y-%m-%d %H:%M:%S.%f')
    rows.append((t, d.get('mode'), float(d['weight']) if 'weight' in d else None))

shot = [r for r in rows if r[1] and r[1] != 'IDLE']
if not shot:
    sys.exit('lokissa ei ole uuttoa (kaikki mode: IDLE)')
t_pump = shot[0][0]
t_stop = shot[-1][0]
print('pumppu kaynnistyi  %s  (tila %s)' % (t_pump.strftime('%H:%M:%S.%f')[:-3], shot[0][1]))
print('uutto paattyi      %s  kesto %.1f s' % (t_stop.strftime('%H:%M:%S.%f')[:-3],
                                               (t_stop - t_pump).total_seconds()))

w = [(t, g) for t, g, in [(r[0], r[2]) for r in rows] if g is not None]
before = [g for t, g in w if (t_pump - t).total_seconds() > 0 and (t_pump - t).total_seconds() < 30]
if not before:
    sys.exit('ei painonaytteita ennen uuttoa')
base = statistics.median(before)
sd = statistics.pstdev(before)
thr = base + max(4 * sd, 1.0)
onset = next((t for t, g in w if t > t_pump and g > thr), None)
print('perustaso ennen    %.2f g  (sd %.3f, kynnys %.2f g)' % (base, sd, thr))
if onset is None:
    print('VESI EI SAAPUNUT kynnyksen yli koko ajon aikana')
else:
    print('vesi alkoi tulla   %s  eli %.1f s pumpun kaynnistyksesta'
          % (onset.strftime('%H:%M:%S.%f')[:-3], (onset - t_pump).total_seconds()))
    rise = [(t, g) for t, g in w if onset <= t <= t_stop]
    if len(rise) > 4:
        ts = [(t - rise[0][0]).total_seconds() for t, _ in rise]
        gs = [g for _, g in rise]
        mt, mg = statistics.mean(ts), statistics.mean(gs)
        sxx = sum((x - mt) ** 2 for x in ts)
        sxy = sum((x - mt) * (y - mg) for x, y in zip(ts, gs))
        print('virtaus nousun aikana %.2f g/s  (%d naytetta, %.1f s)'
              % (sxy / sxx if sxx else 0, len(rise), ts[-1]))
