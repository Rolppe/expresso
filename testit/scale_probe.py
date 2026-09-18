#!/usr/bin/env python3
"""Is a scale physically connected to the Pico, and does it read?

Reads only. Enters devsafe first (relays driven off and read back as [0, 0, 0]) and ends with
machine.reset(), which restarts the normal firmware and BLE. Samples in short chunks so the 8 s
hardware watchdog is fed between them (Link.exec feeds it at the start of every chunk).
"""
import sys, time
sys.path.insert(0, '/srv/work/Infra/iot/expresso')
import pico_dev

SETUP = """
import scale
s = scale.Scale()
print('INFO', s.info())
print('LINK_OK', s.link_ok())
"""
SAMPLE = """
import time
for _ in range(4):
    print('W %.2f g   cells %.2f / %.2f g' % ((s.weight(),) + s.cells(10)))
    time.sleep_ms(200)
"""

link = pico_dev.Link()
link.enter_devsafe()
try:
    out = link.exec(SETUP, 30)
    print(out.strip())
    if 'LINK_OK True' not in out:
        print('VAAKA EI VASTAA — kumpikaan HX711-datalinja ei noussut ylös 200 ms:ssa')
    else:
        for i in range(3):
            print(link.exec(SAMPLE, 30).strip())
finally:
    link.reset()
    print('machine.reset() ajettu — firmware ja BLE käynnistyvät uudelleen')
