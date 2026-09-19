#!/usr/bin/env python3
"""phold_smoke.py — suunnittelijan holdout-testi komennolle phold: (PWM-1B1-PHOLD, korjaus 1).

Ajaa firmwaren `pressure_hold_run`-korutiinin CPythonilla valelaitteilla: releet, kytkimet ja
paineanturi ovat tynkiä, `utime` ja `asyncio` ohuita kuoria. Tarkoitus on ajaa funktio *oikeasti*
läpi, koska py_compile ja lähdekoodin grep eivät näe ajonaikaista virhettä — korjaus 1 syntyi
juuri siitä, että `SWITCH_BREW` luettiin sitomatta sitä `get_switches()`:llä.

    python3 testit/phold_smoke.py        RESULT: <n> failed, epänolla paluuarvo jos punaisia

Toteuttaja ei muokkaa tätä tiedostoa (brief: must not).
"""

import asyncio
import io
import os
import sys
import time
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico'))
import functions as F


class Pin:
    def __init__(self, v=0):
        self.v = v

    def value(self, x=None):
        if x is None:
            return self.v
        self.v = x


class Adc:
    def __init__(self, raw=30000):
        self.raw = raw

    def read_u16(self):
        return self.raw


class Sensor:
    def __init__(self, raw=30000):
        self.pressure_sensor = Adc(raw)
        self.gain = 1.0
        self.offset = -0.99


class BrewData:
    def __init__(self, raw=30000):
        self.pump, self.solenoid, self.heater = Pin(), Pin(), Pin()
        self.brew, self.water, self.steam = Pin(), Pin(), Pin()
        self.pressure_sensor = Sensor(raw)
        self.dev_safe = False
        self.phold_abort = False
        self.mode = None
        self.order = []

    def get_relays(self):
        return self.pump, self.solenoid, self.heater

    def get_switches(self):
        return self.brew, self.water, self.steam

    def set_mode(self, m):
        self.mode = m
        self.order.append(m)

    # Kaukalovahdin vaakarajapinta (EXPRESSO-KAUKALOVAHTI): tuore lukema rajojen sisalla, jotta
    # vahti ei katkaise tata testia. Vahdin oma testi on testit/tray_guard_smoke.py.
    def get_weight(self):
        return 100.0

    def get_weight_ms(self):
        return int(time.monotonic() * 1000)

    def get_weight_limit(self):
        return 470.0

    def get_weight_rise_limit(self):
        return 250.0


class Utime:
    def ticks_ms(self):
        return int(time.monotonic() * 1000)

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b


class Asyncio:
    async def sleep_ms(self, ms):
        await asyncio.sleep(ms / 1000.0)


def run(bd, seconds, abort_after=None):
    async def main():
        task = asyncio.ensure_future(F.pressure_hold_run(bd, Utime(), Asyncio(), seconds))
        if abort_after is not None:
            await asyncio.sleep(abort_after)
            bd.phold_abort = True
        await task

    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(main())
    return buf.getvalue()


def main():
    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name + (' — ' + extra if extra else ''))
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    # 1. Normaali ajo: 1 s, paine 4,94 bar (raaka 30000, gain 1.0, offset -0.99)
    bd = BrewData()
    try:
        out = run(bd, 1)
    except Exception as e:
        print('FAIL normaali ajo nosti poikkeuksen: %r' % (e,))
        print('RESULT: 1 failed')
        return 1
    lines = out.splitlines()
    check('PHOLD_START tulostuu', any(l.startswith('PHOLD_START') for l in lines))
    holds = [l for l in lines if l.startswith('PHOLD ')]
    check('PHOLD-rivejä vähintään 1 sekunnissa', len(holds) >= 1, 'saatiin %d' % len(holds))
    end = [l for l in lines if l.startswith('PHOLD_END')]
    check('PHOLD_END tulostuu', len(end) == 1, 'saatiin %d' % len(end))
    if end:
        check('PHOLD_END reason=ok', 'reason=ok' in end[0], end[0])
    if holds:
        check('bar-kenttä noin 4,94', 'bar=4.9' in holds[0], holds[0])
        check('slope-kenttä on rivillä', 'slope=' in holds[0], holds[0])
    check('pumppu sammutettu lopussa', bd.pump.value() == 0)
    check('venttiili sammutettu lopussa', bd.solenoid.value() == 0)
    check('mode palautui IDLEksi', bd.mode == 'IDLE', str(bd.mode))

    # 2. Kytkin päällä: ajon on päätyttävä heti reason=switch, releet pois
    bd2 = BrewData()
    bd2.brew.value(1)
    out2 = run(bd2, 5)
    check('kytkin lopettaa ajon', 'reason=switch' in out2, out2.strip().splitlines()[-1] if out2.strip() else '(tyhjä)')
    check('kytkinajon jälkeen pumppu pois', bd2.pump.value() == 0)

    # 3. Ylipaine: raaka 60000 -> 14,9 bar > PCAP_OVER_BAR
    bd3 = BrewData(raw=60000)
    out3 = run(bd3, 5)
    check('ylipaine lopettaa ajon', 'reason=overpressure' in out3)
    check('ylipaineajon jälkeen pumppu pois', bd3.pump.value() == 0)

    # 4. phold:stop kesken ajon
    bd4 = BrewData()
    out4 = run(bd4, 10, abort_after=0.6)
    check('abort lopettaa ajon', 'reason=stop' in out4)
    check('abort-lippu nollattu', bd4.phold_abort is False)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
