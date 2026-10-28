#!/usr/bin/env python3
"""scale_clock_test.py — Testaa HX711 SCK-kellotuksen ajoituksen vaikutusta kohinaan.

Vertaa kahta lukutapaa ilman lämmitintä:
  1. NO DELAY (nykyinen scale.py: sck.value(1); sck.value(0))
  2. WITH 2 us DELAY (speksin mukainen: sleep_us(2) high ja low)
Molemmat ottavat 40 näytettä lepotilassa.
"""
import os, sys

EXP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, EXP_ROOT)
import pico_dev

TEST_CODE = """
import scale, devsafe, time
from machine import Pin, disable_irq, enable_irq

s = scale.Scale()
heater_pin = Pin(13, Pin.OUT, value=0)

def shift_nodelay():
    x = y = 0
    sck = s.sck
    pa = s.a
    pb = s.b
    st = disable_irq()
    try:
        for _ in range(24):
            sck.value(1)
            sck.value(0)
            x = (x << 1) | pa.value()
            y = (y << 1) | pb.value()
        for _ in range(s.extra):
            sck.value(1)
            sck.value(0)
    finally:
        enable_irq(st)
    if x & 0x800000: x -= 0x1000000
    if y & 0x800000: y -= 0x1000000
    return x, y

def shift_withdelay():
    x = y = 0
    sck = s.sck
    pa = s.a
    pb = s.b
    st = disable_irq()
    try:
        for _ in range(24):
            sck.value(1)
            time.sleep_us(2)
            sck.value(0)
            time.sleep_us(2)
            x = (x << 1) | pa.value()
            y = (y << 1) | pb.value()
        for _ in range(s.extra):
            sck.value(1)
            time.sleep_us(2)
            sck.value(0)
            time.sleep_us(2)
    finally:
        enable_irq(st)
    if x & 0x800000: x -= 0x1000000
    if y & 0x800000: y -= 0x1000000
    return x, y

# Mittaus 1: NO DELAY (40 näytettä)
samples_nodelay = []
while len(samples_nodelay) < 40:
    if s.ready():
        a, b = shift_nodelay()
        c = (a - s.off_a) + s.trim_b * (b - s.off_b)
        samples_nodelay.append((c / s.scale, a, b))
devsafe.feed()

# Mittaus 2: WITH DELAY (40 näytettä)
samples_delay = []
while len(samples_delay) < 40:
    if s.ready():
        a, b = shift_withdelay()
        c = (a - s.off_a) + s.trim_b * (b - s.off_b)
        samples_delay.append((c / s.scale, a, b))
devsafe.feed()

print('RES_NODELAY', ','.join('%.4f' % g for g, a, b in samples_nodelay))
print('RES_DELAY', ','.join('%.4f' % g for g, a, b in samples_delay))
"""

def stats(vals):
    import statistics
    return statistics.mean(vals), statistics.pstdev(vals), min(vals), max(vals)

def main():
    link = pico_dev.Link()
    link.enter_devsafe()
    try:
        out = link.exec(TEST_CODE, 30)
        lines = out.strip().splitlines()
        for line in lines:
            if line.startswith('RES_NODELAY '):
                vals = [float(x) for x in line[12:].split(',')]
                m, sd, vmin, vmax = stats(vals)
                print('NO DELAY (n=%d):   ka = %8.4f g, sd = %.4f g, range = %.4f g (min %.4f, max %.4f)' % (len(vals), m, sd, vmax-vmin, vmin, vmax))
            elif line.startswith('RES_DELAY '):
                vals = [float(x) for x in line[10:].split(',')]
                m, sd, vmin, vmax = stats(vals)
                print('WITH DELAY (n=%d): ka = %8.4f g, sd = %.4f g, range = %.4f g (min %.4f, max %.4f)' % (len(vals), m, sd, vmax-vmin, vmin, vmax))
    finally:
        link.reset()
        print('machine.reset() ajettu.')

if __name__ == '__main__':
    main()
