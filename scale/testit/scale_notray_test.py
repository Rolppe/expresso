#!/usr/bin/env python3
"""scale_notray_test.py — Mittaa vaa'an käyttäytymisen ilman kaukaloa.

Ottaa 50 näytettä (~4,3 s), tulostaa:
- Tilastot (ka, sd, min, max, vaihteluväli)
- Kennojen A ja B hajonta ja keskinäinen korrelaatio
- ASCII-aaltomuoto (onko 1 Hz siniaalto yhä olemassa vai kadonnut?)
- Fourier-teho ~1 Hz taajuudella
"""
import os, sys, math, statistics

EXP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, EXP_ROOT)
import pico_dev

SAMPLE_CODE = """
import scale, devsafe, time

s = scale.Scale()
t0 = time.ticks_us()
samples = []

while len(samples) < 50:
    if s.ready():
        a, b = s._shift()
        c = (a - s.off_a) + s.trim_b * (b - s.off_b)
        t = time.ticks_diff(time.ticks_us(), t0)
        g = c / s.scale
        samples.append((t, g, a, b))

devsafe.feed()
print('N %d' % len(samples))
for t, g, a, b in samples:
    print('S %d,%.4f,%d,%d' % (t, g, a, b))
"""

def corr(x, y):
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den = (sum((xi - mx)**2 for xi in x) * sum((yi - my)**2 for yi in y))**0.5
    return num / den if den else 0

def main():
    link = pico_dev.Link()
    link.enter_devsafe()
    try:
        out = link.exec(SAMPLE_CODE, 30)
        lines = out.strip().splitlines()
        rows = []
        for line in lines:
            if line.startswith('S '):
                p = line[2:].strip().split(',')
                if len(p) == 4:
                    rows.append((int(p[0])/1000.0, float(p[1]), int(p[2]), int(p[3])))

        if not rows:
            print('Ei saatu näytteitä:', out)
            return

        ts = [r[0] for r in rows]
        gs = [r[1] for r in rows]
        as_ = [r[2] for r in rows]
        bs = [r[3] for r in rows]

        m_g = statistics.mean(gs)
        sd_g = statistics.pstdev(gs)
        vmin_g = min(gs)
        vmax_g = max(gs)
        span_g = vmax_g - vmin_g

        print('=== MITTAUSTULOS ILMAN KAUKALOA (n=%d, kesto %.2f s) ===' % (len(rows), (ts[-1]-ts[0])/1000.0))
        print('Paino (ka):        %8.4f g' % m_g)
        print('Keskihajonta (SD): %8.4f g' % sd_g)
        print('Vaihteluväli:      %8.4f g ... %8.4f g (ero: %.4f g)' % (vmin_g, vmax_g, span_g))
        print()
        print('Kenno A (counts):  ka = %d, sd = %.1f (%.4f g), span = %d (%.4f g)' %
              (statistics.mean(as_), statistics.pstdev(as_), statistics.pstdev(as_)/2175, max(as_)-min(as_), (max(as_)-min(as_))/2175))
        print('Kenno B (counts):  ka = %d, sd = %.1f (%.4f g), span = %d (%.4f g)' %
              (statistics.mean(bs), statistics.pstdev(bs), statistics.pstdev(bs)/2175, max(bs)-min(bs), (max(bs)-min(bs))/2175))
        r_ab = corr(as_, bs)
        print('Kennojen A ja B välinen korrelaatio: %+.4f' % r_ab)

        # 1 Hz teho
        d = [g - m_g for g in gs]
        cos_s = sum(di * math.cos(2*math.pi*1.1*(ti/1000.0)) for di, ti in zip(d, ts))
        sin_s = sum(di * math.sin(2*math.pi*1.1*(ti/1000.0)) for di, ti in zip(d, ts))
        power_1hz = (cos_s**2 + sin_s**2) / len(gs)
        print('Fourier-teho 1.1 Hz kohdalla: %.5f (kaukalon kanssa oli 0.54890)' % power_1hz)

        # ASCII Waveform
        print('\nASCII Waveform ilman kaukaloa:')
        for t, g in zip(ts, gs):
            pos = int((g - vmin_g) / (span_g if span_g > 0 else 1) * 30)
            print('%6.0f ms | %7.3f g |%s' % (t, g, ' '*pos + '*'))

    finally:
        link.reset()
        print('\nmachine.reset() ajettu.')

if __name__ == '__main__':
    main()
