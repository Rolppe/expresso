#!/usr/bin/env python3
"""pskip_gate_smoke.py — suunnittelijan holdout portitetulle kaappaukselle (PWM-1B2, sääntö 6).

Testaa kaksi asiaa, jotka py_compile ja lähdekoodin grep eivät näe:
  1. `pcap_gate(i, phase_us)` on paketin säännön 6 kaava, ja sen jaksollisuus pitää;
  2. portitettu `pressure_capture_run` todella kytkee pumppua kaappauksen aikana, ja sen
     toteutunut kuvio on sama kuin `pcap_gate` — eli isäntä voi laskea portin uudelleen.

    python3 testit/pskip_gate_smoke.py       RESULT: <n> failed, epänolla paluuarvo jos punaisia

Ajo kestää noin 7 s: asettuminen 2 s, pito 3 s, kaappaus 1,2 s (samat vakiot kuin laitteella).
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
        self.log = []          # (t_us, arvo) jokaisesta muutoksesta

    def value(self, x=None):
        if x is None:
            return self.v
        if x != self.v:
            self.log.append((time.monotonic_ns() // 1000, x))
        self.v = x


class Adc:
    def read_u16(self):
        return 30000           # gain 1.0, offset -0.99 -> 4,94 bar: yli PLATEAU_MIN, alle OVER


class Sensor:
    def __init__(self):
        self.pressure_sensor = Adc()
        self.gain = 1.0
        self.offset = -0.99


class BrewData:
    def __init__(self, phase_us=None):
        self.pump, self.solenoid, self.heater = Pin(), Pin(), Pin()
        self.brew, self.water, self.steam = Pin(), Pin(), Pin()
        self.pressure_sensor = Sensor()
        self.dev_safe = False
        self.pcap_abort = False
        self.pcap_target_bar = None
        self.pcap_gate_phase_us = phase_us
        self.mode = None

    def get_relays(self):
        return self.pump, self.solenoid, self.heater

    def get_switches(self):
        return self.brew, self.water, self.steam

    def set_mode(self, m):
        self.mode = m

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
        return time.monotonic_ns() // 1000000

    def ticks_us(self):
        return time.monotonic_ns() // 1000

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b


class Asyncio:
    async def sleep_ms(self, ms):
        await asyncio.sleep(ms / 1000.0)


def run(bd, ms):
    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(F.pressure_capture_run(bd, Utime(), Asyncio(), ms))
    return buf.getvalue()


def main():
    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name)
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    # 1. Vakiot ja portin kaava
    check('PCAP_MAINS_US on 19960', getattr(F, 'PCAP_MAINS_US', None) == 19960,
          str(getattr(F, 'PCAP_MAINS_US', None)))
    check('PCAP_GATE_PERIOD_US on 39920', getattr(F, 'PCAP_GATE_PERIOD_US', None) == 39920,
          str(getattr(F, 'PCAP_GATE_PERIOD_US', None)))
    g = getattr(F, 'pcap_gate', None)
    check('pcap_gate on moduulitason funktio', callable(g))
    if callable(g):
        bad = [i for i in range(4000)
               if g(i, 0) != (1 if ((i * F.PCAP_RATE_US) % 39920) < 19960 else 0)]
        check('pcap_gate vastaa sääntö 6:n kaavaa', not bad, 'ensimmäinen ero i=%s' % (bad[:1],))
        check('vaihesiirto 0: näyte 19 päällä, 20 pois', g(19, 0) == 1 and g(20, 0) == 0,
              '%d %d' % (g(19, 0), g(20, 0)))
        duty = sum(g(i, 0) for i in range(4000)) / 4000.0
        check('duty on 0,50 +- 0,01', abs(duty - 0.5) <= 0.01, '%.3f' % duty)
        shifted = all(g(i, 5000) == g(i + 0, 5000) for i in range(100))
        check('vaihesiirto ei kaadu', shifted)
        per = all(g(i, 0) == g(i + 3992, 0) for i in range(200))
        check('jakso on 3992 näytettä', per)

    # 2. Portitettu ajo kytkee pumppua, portittamaton ei
    bd = BrewData(phase_us=0)
    out = run(bd, 1200)
    check('PCAP_START kertoo gate=on', 'gate=on' in out, out.splitlines()[0] if out else '(tyhjä)')
    check('PCAP_START kertoo kalibroinnin', 'gain=' in out and 'offset=' in out,
          out.splitlines()[0] if out else '(tyhjä)')
    check('PCAP_END reason=ok', 'reason=ok' in out, out.strip().splitlines()[-1] if out.strip() else '')
    # pumpun muutokset kaappauksen aikana: päälle/pois vuorotellen, vähintään 20 reunaa 1,2 s:ssa
    edges = [v for _, v in bd.pump.log]
    check('pumppu kytkeytyi kaappauksen aikana', len(edges) >= 20, 'reunoja %d' % len(edges))
    check('reunat vuorottelevat', all(edges[i] != edges[i + 1] for i in range(len(edges) - 1)))
    check('pumppu pois lopussa', bd.pump.value() == 0)

    bd2 = BrewData(phase_us=None)
    out2 = run(bd2, 1200)
    check('portittamaton kertoo gate=off', 'gate=off' in out2,
          out2.splitlines()[0] if out2 else '(tyhjä)')
    edges2 = [v for _, v in bd2.pump.log]
    # ilman porttia vain kaksi muutosta: päälle alussa, pois finallyssa
    check('portittamaton ei kytke pumppua kesken kaappauksen', len(edges2) <= 2,
          'reunoja %d' % len(edges2))

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
