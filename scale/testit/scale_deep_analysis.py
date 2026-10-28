#!/usr/bin/env python3
"""scale_deep_analysis.py — Kerää ja analysoi tarkkaan vaa'an arvonmuutokset laitteella.

Mittaa:
1. Pidemmän jakson (150 näytettä ≈ 13 sekuntia) lepotilan käyttäytymistä.
2. Erittelee:
   - Jäännöskohina (high-frequency noise)
   - 1 Hz syklin jäännösamplitudi
   - Hidas vaellus/ryömintä (drift slope g/min)
   - Kennojen A ja B yksittäinen käyttäytyminen ja drift
3. Laskennan tehokkuus Picolla:
   - Suoritusaika (µs per update)
   - Muistinvaraus / roskienkeruupaine (gc.mem_alloc() per näyte)
"""
import os
import sys
import math
import statistics

EXP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, EXP_ROOT)
import pico_dev

SAMPLE_CODE = """
import scale, devsafe, time, gc

s = scale.Scale()
samples = []
t0 = time.ticks_ms()

# Lämpenemisen jälkeen mitataan 150 näytettä
gc.collect()
m0 = gc.mem_alloc()

while len(samples) < 150:
    devsafe.feed()
    if s.ready():
        t_start = time.ticks_us()
        g_filt = s.update()
        t_calc_us = time.ticks_diff(time.ticks_us(), t_start)
        now_ms = time.ticks_diff(time.ticks_ms(), t0)
        # s.raw_a ja s.raw_b ovat viimeisimmät counts-arvot
        samples.append((now_ms, g_filt, s.last_a, s.last_b, s.raw_a, s.raw_b, t_calc_us))
    time.sleep_ms(15)

m1 = gc.mem_alloc()
devsafe.feed()

print('MEM_DELTA %d' % (m1 - m0))
print('N %d' % len(samples))
for row in samples:
    print('D %d,%.4f,%.4f,%.4f,%d,%d,%d' % row)
"""

def main():
    link = pico_dev.Link()
    link.enter_devsafe()
    try:
        out = link.exec(SAMPLE_CODE, 40)
    finally:
        link.reset()
        link.s.close()

    lines = out.strip().splitlines()
    mem_delta = None
    data = []
    for l in lines:
        if l.startswith('MEM_DELTA '):
            mem_delta = int(l.split()[1])
        elif l.startswith('D '):
            parts = l[2:].split(',')
            if len(parts) == 7:
                data.append({
                    't_ms': int(parts[0]),
                    'g_filt': float(parts[1]),
                    'g_a': float(parts[2]),
                    'g_b': float(parts[3]),
                    'raw_a': int(parts[4]),
                    'raw_b': int(parts[5]),
                    't_us': int(parts[6])
                })

    if not data:
        print("Ei saatu dataa:", out)
        return

    print(f"=== VAAN MITTAUS JA ARVONMUUTOSANALYYSI (N={len(data)}) ===")
    ts = [d['t_ms'] / 1000.0 for d in data]
    gs = [d['g_filt'] for d in data]
    ga = [d['g_a'] for d in data]
    gb = [d['g_b'] for d in data]
    calc_us = [d['t_us'] for d in data]

    t_total = ts[-1] - ts[0]
    print(f"Kesto:               {t_total:.2f} s ({len(data)} näytettä, taajuus {len(data)/t_total:.2f} Hz)")
    print(f"Laskenta-aika Picolla: ka {statistics.mean(calc_us):.1f} µs (max {max(calc_us)} µs)")
    if mem_delta is not None:
        print(f"Muistinvaraus (150 näytettä): {mem_delta} tavua ({mem_delta / len(data):.1f} B/näyte)")

    # 1. Kokonaispaino
    g_start = gs[0]
    g_end = gs[-1]
    g_span = max(gs) - min(gs)
    g_sd = statistics.pstdev(gs)
    drift_rate_g_min = ((g_end - g_start) / t_total) * 60.0

    print(f"\n--- PAINO (Suodatettu) ---")
    print(f"Alku:                {g_start:.4f} g")
    print(f"Loppu:               {g_end:.4f} g (muutos {g_end - g_start:+.4f} g)")
    print(f"Keskihajonta (SD):   {g_sd:.4f} g")
    print(f"Koko vaihteluväli:   {min(gs):.4f} ... {max(gs):.4f} g (span {g_span:.4f} g)")
    print(f"Vaellusnopeus:       {drift_rate_g_min:+.3f} g/min")

    # 2. Lineaarisen ryöminnän poisto (Detrending) jäännöskohinan laskemiseksi
    # Sovitetaan lineaarinen trendi y = a*t + b
    n = len(ts)
    sx = sum(ts)
    sy = sum(gs)
    sxx = sum(x*x for x in ts)
    sxy = sum(x*y for x, y in zip(ts, gs))
    slope = (n*sxy - sx*sy) / (n*sxx - sx*sx)
    intercept = (sy - slope*sx) / n

    residuals = [g - (slope*t + intercept) for t, g in zip(ts, gs)]
    res_sd = statistics.pstdev(residuals)
    res_span = max(residuals) - min(residuals)

    print(f"\n--- TRENDINPOISTETTU KOHINA (Kun hidas vaellus poistettu) ---")
    print(f"Lineaarinen ryömintä:{slope*60.0:+.3f} g/min (kulmakerroin {slope:+.4f} g/s)")
    print(f"Jäännöskohina (SD):  {res_sd:.4f} g")
    print(f"Huippu-huippu kohina:{res_span:.4f} g")

    # 3. Kennojen A ja B erittely
    slope_a = (n*sum(x*y for x,y in zip(ts, ga)) - sx*sum(ga)) / (n*sxx - sx*sx)
    slope_b = (n*sum(x*y for x,y in zip(ts, gb)) - sx*sum(gb)) / (n*sxx - sx*sx)
    print(f"\n--- KENNOJEN A JA B ERITTELY ---")
    print(f"Kenno A: ka {statistics.mean(ga):.2f} g, vaellus {slope_a*60.0:+.3f} g/min, sd {statistics.pstdev(ga):.3f} g")
    print(f"Kenno B: ka {statistics.mean(gb):.2f} g, vaellus {slope_b*60.0:+.3f} g/min, sd {statistics.pstdev(gb):.3f} g")

    # 4. 1 Hz aaltokomponentin teho trendinpoistetussa signaalissa
    # Goertzel tai diskreetti DFT 1.05 Hz kohdalla
    k = 1.05
    re_sum = sum(r * math.cos(2 * math.pi * k * t) for t, r in zip(ts, residuals))
    im_sum = sum(r * math.sin(2 * math.pi * k * t) for t, r in zip(ts, residuals))
    amp_1hz = 2.0 * math.hypot(re_sum, im_sum) / n
    print(f"\n--- SYKLIKOMPONENTTI ---")
    print(f"1.05 Hz jäännösamplitudi suodatetussa signaalissa: {amp_1hz:.4f} g (huippu-huippu {2*amp_1hz:.4f} g)")

if __name__ == '__main__':
    main()
