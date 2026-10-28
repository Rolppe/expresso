#!/usr/bin/env python3
"""scale_heater_test.py — Tutkii lämmityksen vaikutusta vaa'an lukemaan.

Ajaa kaksi koetta:
  1. BASELINE: 50 näytettä (~4,3 s) lämmitin kokonaan pois päältä.
  2. HEATER PULSE: 1 s ennen, 300 ms lämmitin päällä (kuten lepotilassa), 2 s jälkeen.
Tallentaa jokaisen näytteen aikaleiman, raaka-arvot (kenno A ja B) ja lasketun painon.
Turvallisuus: alkaa enter_devsafe():lla ja lopettaa machine.reset():iin.
"""
import os
import sys
import time

EXP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, EXP_ROOT)
import pico_dev

SETUP = """
import scale, devsafe
from machine import Pin
s = scale.Scale()
heater_pin = Pin(13, Pin.OUT, value=0)
print('INFO', s.info())
print('LINK_OK', s.link_ok())
"""

# Koe 1: Baseline ilman lämmitintä (50 näytettä)
BASELINE = """
import time
t0 = time.ticks_us()
samples = []
heater_pin.value(0)
while len(samples) < 50:
    if s.ready():
        try:
            a, b = s._shift()
        except OSError:
            continue
        c = (a - s.off_a) + s.trim_b * (b - s.off_b)
        t = time.ticks_diff(time.ticks_us(), t0)
        g = c / s.scale
        samples.append((t, g, a, b, 0))
devsafe.feed()
print('BASE_N %d' % len(samples))
for t, g, a, b, h in samples:
    print('DATA %d,%.4f,%d,%d,%d' % (t, g, a, b, h))
"""

# Koe 2: Lämmittimen pulssitus (1 s ennen, 300 ms lämmitin päällä, 2 s jälkeen)
PULSE = """
import time
t0 = time.ticks_us()
samples = []
heater_pin.value(0)
heat_state = 0
pulse_started = False
pulse_ended = False

# Otetaan näytteitä n. 3,5 sekunnin ajan (~40 näytettä)
start_ms = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), start_ms) < 3500:
    now_ms = time.ticks_diff(time.ticks_ms(), start_ms)
    # 1000 ms kohdalla lämmitin päälle 300 ms ajaksi
    if now_ms >= 1000 and not pulse_started:
        heater_pin.value(1)
        heat_state = 1
        pulse_started = True
    elif now_ms >= 1300 and not pulse_ended:
        heater_pin.value(0)
        heat_state = 0
        pulse_ended = True

    if s.ready():
        try:
            a, b = s._shift()
        except OSError:
            continue
        c = (a - s.off_a) + s.trim_b * (b - s.off_b)
        t = time.ticks_diff(time.ticks_us(), t0)
        g = c / s.scale
        samples.append((t, g, a, b, heat_state))

heater_pin.value(0)
devsafe.feed()
print('PULSE_N %d' % len(samples))
for t, g, a, b, h in samples:
    print('DATA %d,%.4f,%d,%d,%d' % (t, g, a, b, h))
"""


def parse_samples(lines):
    rows = []
    for line in lines:
        if line.startswith('DATA '):
            parts = line[5:].strip().split(',')
            if len(parts) == 5:
                t_us = int(parts[0])
                g = float(parts[1])
                raw_a = int(parts[2])
                raw_b = int(parts[3])
                heater = int(parts[4])
                rows.append((t_us / 1000.0, g, raw_a, raw_b, heater))
    return rows


def stats(values):
    import statistics
    if not values:
        return 0.0, 0.0, 0.0, 0.0
    mean = statistics.mean(values)
    sd = statistics.pstdev(values) if len(values) > 1 else 0.0
    return mean, sd, min(values), max(values)


def main():
    print('Yhdistetään Picoon...')
    link = pico_dev.Link()
    print('Siirrytään devsafe-tilaan (releet varmistettu pois)...')
    link.enter_devsafe()
    try:
        out = link.exec(SETUP, 30)
        print(out.strip())
        if 'LINK_OK True' not in out:
            print('VIRHE: Vaaka ei vastaa (HX711 linkki epäonnistui)')
            return

        print('\n--- KOE 1: BASELINE (Lämmitin POIS päältä, 50 näytettä) ---')
        raw_base = link.exec(BASELINE, 30)
        base_samples = parse_samples(raw_base.strip().splitlines())
        if base_samples:
            grams = [r[1] for r in base_samples]
            mean, sd, vmin, vmax = stats(grams)
            print('Näytteitä: %d' % len(base_samples))
            print('Keskiarvo: %.4f g, Keskihajonta (SD): %.4f g' % (mean, sd))
            print('Vaihteluväli (min ... max): %.4f g ... %.4f g (ero: %.4f g)' % (vmin, vmax, vmax - vmin))
            if sd < 0.02 and (vmax - vmin) < 0.05:
                print('>> TULOS: Erittäin vakaa! Pisarantunnistus (0.05 g) mahdollista tässä tilassa.')
            else:
                print('>> TULOS: Kohinaa/heittoa esiintyy myös ilman lämmitintä.')

        print('\n--- KOE 2: HEATER PULSE (1 s ennen, 300 ms lämmitin PÄÄLLÄ, 2 s jälkeen) ---')
        raw_pulse = link.exec(PULSE, 30)
        pulse_samples = parse_samples(raw_pulse.strip().splitlines())
        if pulse_samples:
            before = [r[1] for r in pulse_samples if r[4] == 0 and r[0] < 1000]
            during = [r[1] for r in pulse_samples if r[4] == 1]
            after = [r[1] for r in pulse_samples if r[4] == 0 and r[0] >= 1300]

            m_bef, sd_bef, _, _ = stats(before)
            m_dur, sd_dur, _, _ = stats(during)
            m_aft, sd_aft, _, _ = stats(after)

            print('Ennen pulssia (n=%d):      ka = %8.4f g, sd = %.4f g' % (len(before), m_bef, sd_bef))
            print('Lämmittimen aikana (n=%d): ka = %8.4f g, sd = %.4f g' % (len(during), m_dur, sd_dur))
            print('Pulssin jälkeen (n=%d):    ka = %8.4f g, sd = %.4f g' % (len(after), m_aft, sd_aft))
            delta = m_dur - m_bef
            print('Välitön siirtymä lämmittimen kytkeytyessä: %+8.4f g' % delta)

            print('\nYksityiskohtaiset näytteet pulssin ympärillä:')
            for t_ms, g, a, b, h in pulse_samples:
                tag = ' [HEATER ON]' if h else ''
                print('t = %6.1f ms: %8.4f g  (A: %7d, B: %7d)%s' % (t_ms, g, a, b, tag))

    finally:
        print('\nPalautetaan laite ja ajetaan machine.reset()...')
        link.reset()
        print('Valmis: firmware ja BLE käynnistyvät uudelleen.')


if __name__ == '__main__':
    main()
