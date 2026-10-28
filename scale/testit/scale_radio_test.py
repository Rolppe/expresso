#!/usr/bin/env python3
"""scale_radio_test.py — Testaa vaikuttaako Pico 2 W:n radio (BLE / Wi-Fi) vaa'an kohinaan.

Mittaa vaa'an kohinan kahdessa tilassa:
  1. RADIO ON (nykyinen tila, BLE/Wi-Fi mahdollisesti aktiivisena)
  2. RADIO OFF (ble.active(False) ja wlan.active(False))
"""
import os, sys

EXP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, EXP_ROOT)
import pico_dev

TEST_CODE = """
import scale, devsafe, time
from machine import Pin

s = scale.Scale()

# Mittaus 1: Nykyinen tila (radio ennallaan)
s1 = []
while len(s1) < 40:
    if s.ready():
        a, b = s._shift()
        c = (a - s.off_a) + s.trim_b * (b - s.off_b)
        s1.append(c / s.scale)
devsafe.feed()

# Sammutetaan BLE ja WLAN
try:
    import bluetooth
    ble = bluetooth.BLE()
    ble.active(False)
except Exception as e:
    print('BLE_OFF_ERR', e)

try:
    import network
    for iface in (network.STA_IF, network.AP_IF):
        wlan = network.WLAN(iface)
        wlan.active(False)
except Exception as e:
    print('WLAN_OFF_ERR', e)

time.sleep_ms(300)

# Mittaus 2: Radio sammutettuna
s2 = []
while len(s2) < 40:
    if s.ready():
        a, b = s._shift()
        c = (a - s.off_a) + s.trim_b * (b - s.off_b)
        s2.append(c / s.scale)
devsafe.feed()

print('RADIO_ON', ','.join('%.4f' % g for g in s1))
print('RADIO_OFF', ','.join('%.4f' % g for g in s2))
"""

def stats(vals):
    import statistics
    return statistics.mean(vals), statistics.pstdev(vals), min(vals), max(vals)

def main():
    link = pico_dev.Link()
    link.enter_devsafe()
    try:
        out = link.exec(TEST_CODE, 30)
        for line in out.strip().splitlines():
            if line.startswith('RADIO_ON '):
                vals = [float(x) for x in line[9:].split(',')]
                m, sd, vmin, vmax = stats(vals)
                print('RADIO ON  (n=%d): ka = %8.4f g, sd = %.4f g, range = %.4f g (min %.4f, max %.4f)' % (len(vals), m, sd, vmax-vmin, vmin, vmax))
            elif line.startswith('RADIO_OFF '):
                vals = [float(x) for x in line[10:].split(',')]
                m, sd, vmin, vmax = stats(vals)
                print('RADIO OFF (n=%d): ka = %8.4f g, sd = %.4f g, range = %.4f g (min %.4f, max %.4f)' % (len(vals), m, sd, vmax-vmin, vmin, vmax))
            elif 'ERR' in line:
                print('HUOM:', line)
    finally:
        link.reset()
        print('machine.reset() ajettu.')

if __name__ == '__main__':
    main()
