#!/usr/bin/env python3
"""Measure how much water a test shot delivers, with the drift removed.

Method. The scale is precise (sd ~0.2 g) but the platform loses mass continuously while hot water
sits on it - measured 1-2 g/min on 18.9.2026. A plain "after minus before" therefore under-reports by
the drift accumulated in between. So a line is fitted to a quiet window on each side and evaluated at
the moment the shot starts and the moment it ends: the drift is carried by the fits, not by the
difference. Nothing may touch the tray from the start of the pre-window to the end of the post-window.

Usage: shot_measure.py <shot_seconds> [pre_s] [settle_s] [post_s]
"""
import subprocess, sys, time, statistics

SHOT = float(sys.argv[1])
PRE_S = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
SETTLE_S = float(sys.argv[3]) if len(sys.argv) > 3 else 90.0
POST_S = float(sys.argv[4]) if len(sys.argv) > 4 else 60.0
CSV = '/tmp/scale.csv'


def window(t_from, t_to):
    rows = [tuple(map(float, l.split(','))) for l in open(CSV) if ',' in l]
    return [(t, g) for t, g in rows if t_from <= t <= t_to]


def fit(rows, at):
    """Least squares line through (t, g), evaluated at time `at`. Returns value, slope g/min, sd."""
    t0 = rows[0][0]
    ts = [t - t0 for t, _ in rows]
    gs = [g for _, g in rows]
    mt, mg = statistics.mean(ts), statistics.mean(gs)
    sxx = sum((t - mt) ** 2 for t in ts)
    sxy = sum((t - mt) * (g - mg) for t, g in zip(ts, gs))
    slope = sxy / sxx if sxx else 0.0
    resid = [g - (mg + slope * (t - mt)) for t, g in zip(ts, gs)]
    return mg + slope * (at - t0 - mt), slope * 60.0, statistics.pstdev(resid)


print('Perustaso: %.0f s ilman kosketusta...' % PRE_S)
pre_from = time.time()
time.sleep(PRE_S)
pre_to = time.time()
pre = window(pre_from, pre_to)
if len(pre) < 20:
    sys.exit('perustasossa vain %d näytettä' % len(pre))
pre_v, pre_slope, pre_sd = fit(pre, pre_to)
print('  n=%d  arvo %.3f g  ryöminta %+.2f g/min  jäännös-sd %.3f g' % (len(pre), pre_v, pre_slope, pre_sd))
if pre_sd > 1.0:
    sys.exit('perustaso ei ole rauhallinen (sd %.2f g) - odota ja aja uudelleen' % pre_sd)
# A straight fit survives a steady drift but not a curved one. Lifting the tray off the hot machine
# left the cells warming back up: +13 g/min right after, still +1.6 g/min four minutes later
# (18.9.2026). Compare the two halves of the pre-window - if the slope is still changing, the fit
# cannot carry the drift and the measurement would inherit the error.
half = len(pre) // 2
_, slope_a, _ = fit(pre[:half], pre[half][0])
_, slope_b, _ = fit(pre[half:], pre_to)
if abs(slope_b - slope_a) > 1.0:
    sys.exit('ryöminta ei ole tasaantunut (%.2f -> %.2f g/min) - odota ja aja uudelleen'
             % (slope_a, slope_b))
print('  ryöminta vakaa: %.2f -> %.2f g/min' % (slope_a, slope_b))

t_start = time.time()
print('Testiuutto %.0f s...' % SHOT)
r = subprocess.run([sys.executable, '/srv/work/Infra/iot/expresso/pico_dev.py', 'shot', str(SHOT),
                    '/tmp/tshot-mittaus.log'], capture_output=True, text=True, timeout=SHOT + 120)
t_end = time.time()
tail = [l for l in r.stdout.splitlines() if l.startswith(('TS_END', 'PI_END', 'TS_START', 'CMD_OK'))]
print('  ' + ' | '.join(tail[-3:]) if tail else '  (ei TS-rivejä; katso /tmp/tshot-mittaus.log)')

print('Laskeutuminen %.0f s, sitten %.0f s mittaus...' % (SETTLE_S, POST_S))
time.sleep(SETTLE_S)
post_from = time.time()
time.sleep(POST_S)
post = window(post_from, time.time())
if len(post) < 20:
    sys.exit('loppumittauksessa vain %d näytettä' % len(post))
post_v, post_slope, post_sd = fit(post, t_end)
print('  n=%d  arvo (takaisin uuton loppuun) %.3f g  ryöminta %+.2f g/min  jäännös-sd %.3f g'
      % (len(post), post_v, post_slope, post_sd))

# The two fits carry the drift outside the shot, but not the drift during it: the water arrives
# gradually, so the mass lost between t_start and t_end belongs to neither window. Add it back using
# the mean of the two slopes (validated on synthetic data: residual 0.81 g -> 0.02 g).
drift_during = (pre_slope + post_slope) / 2.0 / 60.0 * (t_end - t_start)
delivered = post_v - pre_v - drift_during
naive = statistics.mean([g for _, g in post]) - statistics.mean([g for _, g in pre])
print()
print('UUTON KESTO        %.1f s' % (t_end - t_start))
print('TOIMITETTU VESI    %.2f g   (ryöminta poistettu, uuton aikainen %+.2f g)' % (delivered, -drift_during))
print('  korjaamaton ero  %.2f g   ero korjaukseen %+.2f g' % (naive, delivered - naive))
print('  virtaus          %.2f g/s uuton kestoon suhteutettuna' % (delivered / max(t_end - t_start, 1)))
print('  haihtuminen nyt  %+.2f g/min - punnitse astia pian, tai kerro kellonaika niin korjaan' % post_slope)
