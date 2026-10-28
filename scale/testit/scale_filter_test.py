#!/usr/bin/env python3
"""scale_filter_test.py — Testaa uutta 12-näytteen syklisuodatinta ja FirstDropDetectoria.

Tarkistaa:
1. Syklisuodattimen vaimennuksen 1.05 Hz keinumiselle (kohina laskee merkittävästi).
2. FirstDropDetectorin: 0 väärää hälytystä lepotilassa, luotettava laukaisu asetetulla pisaralla.
"""
import math
import statistics
import os
import sys
import types

machine = types.ModuleType('machine')
class Pin:
    OUT = 1; IN = 0
    def __init__(self, *args, **kwargs): pass
    def value(self, *args): return 0
machine.Pin = Pin
machine.disable_irq = lambda: 0
machine.enable_irq = lambda s=0: None
sys.modules['machine'] = machine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pico')))
from scale import FirstDropDetector


def test_filter():
    # Simuloitu aito signaali: 500 g perustaso + 0.5 g siniaalto (1.05 Hz) + Gauss-kohina (sd 0.15 g)
    fs = 11.6
    dt = 1.0 / fs
    f_sine = 1.05
    N = 200
    import random
    rnd = random.Random(42)

    raw_samples = []
    for i in range(N):
        t = i * dt
        val = 500.0 + 0.5 * math.sin(2 * math.pi * f_sine * t) + rnd.gauss(0, 0.15)
        raw_samples.append(val)

    # Suodatus: W=8 (vanha)
    w8_out = []
    buf = []
    for x in raw_samples:
        buf.append(x)
        if len(buf) > 8: buf.pop(0)
        v = sorted(buf)
        if len(v) >= 5: v = v[1:-1]
        w8_out.append(sum(v)/len(v))

    # Suodatus: W=12 (uusi)
    w12_out = []
    buf = []
    for x in raw_samples:
        buf.append(x)
        if len(buf) > 12: buf.pop(0)
        v = sorted(buf)
        if len(v) >= 8: v = v[2:-2]
        elif len(v) >= 5: v = v[1:-1]
        w12_out.append(sum(v)/len(v))

    sd_raw = statistics.pstdev(raw_samples[20:])
    sd_w8 = statistics.pstdev(w8_out[20:])
    sd_w12 = statistics.pstdev(w12_out[20:])

    print(f'Raw noise sd:  {sd_raw:.4f} g')
    print(f'W=8 (vanha):   {sd_w8:.4f} g (vaimennus {(1-sd_w8/sd_raw)*100:.1f}%)')
    print(f'W=12 (uusi):   {sd_w12:.4f} g (vaimennus {(1-sd_w12/sd_raw)*100:.1f}%)')
    assert sd_w12 < sd_w8, 'Uuden suodattimen on oltava parempi kuin vanha'

    # Pisarantunnistustesti:
    # 1. Lepotila (ei pisaroita): ei yhtään väärää hälytystä
    det = FirstDropDetector()
    det.arm(w12_out[20])
    for i, g in enumerate(w12_out[20:]):
        hit = det.feed(g, int(i * dt * 1000), pressure=0.0)
        assert not hit, f'Väärä hälytys lepotilassa näytteessä {i}'
    print('Lepotilatesti: 0 väärää hälytystä (PASS)')

    # 2. Lisätään aito pisara/noron alku (+0.30 g) näytteeseen 100
    det.reset()
    drop_samples = list(raw_samples)
    for i in range(100, N):
        drop_samples[i] += 0.30

    drop_w12 = []
    buf = []
    for x in drop_samples:
        buf.append(x)
        if len(buf) > 12: buf.pop(0)
        v = sorted(buf)
        if len(v) >= 8: v = v[2:-2]
        elif len(v) >= 5: v = v[1:-1]
        drop_w12.append(sum(v)/len(v))

    det.arm(drop_w12[20])
    hit_idx = None
    for i, g in enumerate(drop_w12):
        if i >= 20 and det.feed(g, int(i * dt * 1000), pressure=0.5):
            hit_idx = i
            break

    assert hit_idx is not None, 'Pisaraa ei tunnistettu!'
    delay_ms = (hit_idx - 100) * dt * 1000
    print(f'Pisarantunnistus: tunnistettu näytteessä {hit_idx} (viive {delay_ms:.0f} ms) (PASS)')
    print('KAIKKI TESTIT LÄPÄISTY!')

if __name__ == '__main__':
    test_filter()
