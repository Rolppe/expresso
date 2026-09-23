#!/usr/bin/env python3
"""vkello_rise_smoke.py — vkellon nousuvaihe paattyy tasanteeseen (kayttaja 23.9.2026).

"Nyt me ei mitata paineita. Tarkeinta on se etta huomaat koska paine ei enaa nouse." Ajaa
`pressure_clock_run`:n CPythonilla virtuaalikellolla ja painemallilla (tayttoviive, nousu
tasanteeseen, 50 Hz vareily) ja tarkistaa:
  1. vkello:0, tasanne 5 bar -> VKELLO_RISE reason=plateau, ajo jatkuu taukosarjaan (reason=ok),
  2. vkello:7, tasanne 5 bar -> sama tasanne; vanha koodi antoi tassa reason=noreach,
  3. vkello:7, tasanne 9 bar -> reason=target,
  4. paine ei nouse yli 1 barin (tayttovaihe) -> ei tasannetta, reason=noreach, releet pois.

    python3 testit/vkello_rise_smoke.py       RESULT: <n> failed
"""

import asyncio
import io
import math
import os
import re
import sys
import types
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pico'))


class Utime:
    """Virtuaaliaika: jokainen ticks_us-kutsu vie 20 us, joten kiireiset odotussilmukat etenevat."""

    def __init__(self):
        self.us = 0

    def ticks_us(self):
        self.us += 20
        return self.us

    def ticks_ms(self):
        return self.ticks_us() // 1000

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b


U = Utime()
sys.modules['utime'] = U
sys.modules.setdefault('devsafe', types.SimpleNamespace(feed=lambda: None))
import functions as F   # noqa: E402


class Pin:
    def __init__(self):
        self.v = 0

    def value(self, x=None):
        if x is None:
            return self.v
        self.v = x


class Plant:
    """Pumppu paalla: 1,2 s tayttoviive, sitten ensimmaisen kertaluvun nousu tasanteeseen."""

    def __init__(self, pump, plateau):
        self.pump, self.plateau = pump, plateau
        self.p, self.on_us, self.last = 0.0, None, 0

    def bar(self, now):
        dt = (now - self.last) / 1e6
        self.last = now
        if self.pump.value():
            if self.on_us is None: self.on_us = now
            if now - self.on_us > 1200000:
                self.p += (self.plateau - self.p) * min(1.0, dt / 0.8)
        else:
            self.on_us = None
            self.p += (0.0 - self.p) * min(1.0, dt / 0.5)
        ripple = 0.4 * math.sin(2 * math.pi * 50.02 * now / 1e6) if self.pump.value() else 0.0
        return self.p + ripple


class Adc:
    def __init__(self, plant):
        self.plant = plant

    def read_u16(self):
        bar = self.plant.bar(U.us)
        return int((bar + 0.99 - F.PCAP_RAW_B) / F.PCAP_RAW_A)


class BrewData:
    def __init__(self, plateau):
        self.pump, self.solenoid, self.heater = Pin(), Pin(), Pin()
        self.brew, self.water, self.steam = Pin(), Pin(), Pin()
        self.pressure_sensor = types.SimpleNamespace(
            pressure_sensor=Adc(Plant(self.pump, plateau)), gain=1.0, offset=-0.99)
        self.dev_safe, self.vkello_abort, self.mode = False, False, None

    def get_relays(self): return self.pump, self.solenoid, self.heater
    def get_switches(self): return self.brew, self.water, self.steam
    def set_mode(self, m): self.mode = m
    def get_weight(self): return 480.0
    def get_weight_ms(self): return (U.us // 100000) * 100
    def get_weight_limit(self): return 720.0
    def get_weight_rise_limit(self): return 0.0


class Asyncio:
    async def sleep_ms(self, ms):
        U.us += max(ms, 1) * 1000


def run(plateau, target):
    bd = BrewData(plateau)
    out = io.StringIO()
    with redirect_stdout(out):
        asyncio.run(F.pressure_clock_run(bd, U, Asyncio(), target))
    return bd, out.getvalue()


def field(text, prefix, key):
    line = next((l for l in text.splitlines() if l.startswith(prefix)), '')
    m = re.search(r'\b%s=(\S+)' % key, line)
    return m.group(1) if m else None


def main():
    failed = []

    def check(name, cond, extra=''):
        print('%s %s %s' % ('OK  ' if cond else 'FAIL', name, extra))
        if not cond: failed.append(name)

    bd, out = run(5.0, 0.0)
    check('1 vkello:0 tasanne 5 bar -> plateau', field(out, 'VKELLO_RISE', 'reason') == 'plateau',
          field(out, 'VKELLO_RISE', 'bar'))
    check('1 ajo jatkuu loppuun', field(out, 'VKELLO_END', 'reason') == 'ok', field(out, 'VKELLO_END', 'reason'))
    check('1 nelja taukoa', out.count('VKELLO_RESTART') == 4, str(out.count('VKELLO_RESTART')))
    check('1 releet pois lopussa', bd.pump.v == 0 and bd.solenoid.v == 0)

    bd, out = run(5.0, 7.0)
    check('2 vkello:7 tasanne 5 bar -> plateau, ei noreach',
          field(out, 'VKELLO_RISE', 'reason') == 'plateau' and field(out, 'VKELLO_END', 'reason') == 'ok',
          '%s/%s' % (field(out, 'VKELLO_RISE', 'reason'), field(out, 'VKELLO_END', 'reason')))

    bd, out = run(9.0, 7.0)
    check('3 vkello:7 tasanne 9 bar -> target', field(out, 'VKELLO_RISE', 'reason') == 'target',
          field(out, 'VKELLO_RISE', 'bar'))

    bd, out = run(0.8, 0.0)
    check('4 alle 1 barin tayttovaihe ei ole tasanne', 'VKELLO_RISE' not in out and
          field(out, 'VKELLO_END', 'reason') == 'noreach', field(out, 'VKELLO_END', 'reason'))
    check('4 releet pois', bd.pump.v == 0 and bd.solenoid.v == 0)

    print('RESULT: %d failed' % len(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
