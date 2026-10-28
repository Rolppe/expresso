#!/usr/bin/env python3
"""Watch the drip-tray scale over BLE telemetry and record every steady plateau.

The user fills the tray to the brim and nudges it every ~5 s. Each nudge reseats the tray on the two
load cells, so the same water level reads slightly differently - that spread is what the safety
margin has to cover. A plateau is reported once the weight has stayed inside STABLE_BAND for
STABLE_S; the next one is only reported after the reading has moved away again, so one settle gives
one value.

Reads the phone's log only; nothing is sent to the Pico.
"""
import subprocess, re, sys, time, statistics

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import localenv  # noqa: E402,F401  local.env -> os.environ (README: Local configuration)
ADB = os.environ.get('PICO_ADB') or os.path.expanduser('~/.local/share/platform-tools/adb')
PHONE = os.environ.get('PICO_PHONE', '192.0.2.11:5555')
STABLE_S = 3.0          # how long it must sit still
STABLE_BAND = 2.0       # grams, peak-to-peak, inside the window (resting noise measured ~0.7 g)
MOVE_BAND = 4.0         # grams away from the last plateau before a new one may be reported

rx = re.compile(r'\[DATA\] RX settings \{(.*)\}')
proc = subprocess.Popen([ADB, '-s', PHONE, 'logcat', '-v', 'time', '-s', 'flutter'],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
window = []             # (t, grams)
plateaus = []
armed = True
last_print = 0.0
print('Seurataan vaakaa. Liikuttele kaukaloa ~5 s välein; tasanne kirjataan kun lukema on ollut')
print('%.0f s paikallaan (±%.0f g). Lopeta Ctrl-C:llä.\n' % (STABLE_S, STABLE_BAND))
try:
    for line in proc.stdout:
        m = rx.search(line)
        if not m:
            continue
        d = dict(p.split(': ', 1) for p in m.group(1).split(', ') if ': ' in p)
        if 'weight' not in d:
            continue
        try:
            g = float(d['weight'])
        except ValueError:
            continue
        now = time.time()
        window.append((now, g))
        # Keep a longer tail than the judging window: trimming to exactly STABLE_S leaves a span that
        # is always just under it, so a "span >= STABLE_S" test can never fire (seen 18.9.2026).
        window[:] = [(t, v) for t, v in window if now - t <= STABLE_S + 3.0]
        if now - last_print >= 2.0:
            last_print = now
            print('  seuraa: %6.1f g' % g, flush=True)
        recent = [(t, v) for t, v in window if now - t <= STABLE_S]
        watched_long_enough = now - window[0][0] >= STABLE_S
        if len(recent) < 6 or not watched_long_enough:
            continue
        vals = [v for _, v in recent]
        spread = max(vals) - min(vals)
        mean = statistics.mean(vals)
        if armed and spread <= STABLE_BAND:
            plateaus.append(mean)
            print('TASANNE %2d: %7.2f g   (n=%2d, hajonta %.2f g, vaihteluväli %.2f g)'
                  % (len(plateaus), mean, len(vals), statistics.pstdev(vals), spread))
            armed = False
            window.clear()
        elif not armed and plateaus and abs(g - plateaus[-1]) > MOVE_BAND:
            armed = True
except KeyboardInterrupt:
    pass
finally:
    proc.terminate()
    if plateaus:
        print('\n\nTASANTEITA %d kpl' % len(plateaus))
        print('  pienin   %7.2f g' % min(plateaus))
        print('  suurin   %7.2f g' % max(plateaus))
        print('  keskiarvo %6.2f g' % statistics.mean(plateaus))
        print('  hajonta  %7.2f g' % (statistics.pstdev(plateaus) if len(plateaus) > 1 else 0.0))
        print('  vaihteluväli %.2f g' % (max(plateaus) - min(plateaus)))
    else:
        print('\n\nEi yhtään tasannetta.')
