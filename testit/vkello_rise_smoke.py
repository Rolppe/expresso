#!/usr/bin/env python3
"""vkello_rise_smoke.py — vkellon nousuvaihe paattyy tasanteeseen (kayttaja 23.9.2026).

"Nyt me ei mitata paineita. Tarkeinta on se etta huomaat koska paine ei enaa nouse." Ajaa
`pressure_clock_run`:n CPythonilla virtuaalikellolla ja painemallilla (tayttoviive, nousu
tasanteeseen, 50 Hz vareily) ja tarkistaa:
  1. vkello:0, tasanne 5 bar -> VKELLO_RISE reason=plateau, ajo jatkuu taukosarjaan (reason=ok),
  2. vkello:7, tasanne 5 bar -> sama tasanne; vanha koodi antoi tassa reason=noreach,
  3. vkello:7, tasanne 9 bar -> reason=target,
  4. paine ei nouse yli 1 barin (tayttovaihe) -> ei tasannetta, reason=noreach, releet pois,
  5. jaannospaine 6 bar -> VKELLO_VENT purkaa ennen pumppua (TILAUS-H), nousu alkaa purettuna,
  6. hidas nousu 0,2 bar/s (tasanne ~26 s) -> plateau, ei noreach (katto VKELLO_REACH_MAX_MS;
     vkello-20260923-a nousi 19,2 s:ssa, vanha 20 s:n katto oli rajalla).

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
        self.v, self.hook = 0, None

    def value(self, x=None):
        if x is None:
            return self.v
        if self.hook: self.hook()   # laitos integroi vanhalla tilalla vaihtoon asti
        self.v = x


class Plant:
    """Pumppu paalla: 1,2 s tayttoviive, sitten ensimmaisen kertaluvun nousu tasanteeseen (tai
    lineaarinen `rate` bar/s). Pumppu pois: paine purkautuu vain venttiilin ollessa auki, kiinni
    oleva jarjestelma pitaa paineen (`p0` = jaannospaine ennen ajoa)."""

    def __init__(self, pump, solenoid, plateau, p0=0.0, rate=None):
        self.pump, self.solenoid, self.plateau, self.rate = pump, solenoid, plateau, rate
        self.p, self.on_us, self.last = p0, None, 0
        self.p_first_on = None   # paine pumpun ensimmaisella kaynnistyksella
        pump.hook = solenoid.hook = lambda: self.bar(U.us)

    def bar(self, now):
        dt = (now - self.last) / 1e6
        self.last = now
        if self.pump.value():
            if self.on_us is None: self.on_us = now
            if self.p_first_on is None: self.p_first_on = self.p
            if now - self.on_us > 1200000:
                if self.rate: self.p = min(self.plateau, self.p + self.rate * dt)
                else: self.p += (self.plateau - self.p) * min(1.0, dt / 0.8)
        else:
            self.on_us = None
            if self.solenoid.value(): self.p += (0.0 - self.p) * min(1.0, dt / 0.5)
        ripple = 0.4 * math.sin(2 * math.pi * 50.02 * now / 1e6) if self.pump.value() else 0.0
        return self.p + ripple


class Adc:
    def __init__(self, plant):
        self.plant = plant

    def read_u16(self):
        bar = self.plant.bar(U.us)
        return int((bar + 0.99 - F.PCAP_RAW_B) / F.PCAP_RAW_A)


class BrewData:
    def __init__(self, plateau, p0=0.0, rate=None):
        self.pump, self.solenoid, self.heater = Pin(), Pin(), Pin()
        self.brew, self.water, self.steam = Pin(), Pin(), Pin()
        self.plant = Plant(self.pump, self.solenoid, plateau, p0, rate)
        self.pressure_sensor = types.SimpleNamespace(
            pressure_sensor=Adc(self.plant), gain=1.0, offset=-0.99)
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


def run(plateau, target, p0=0.0, rate=None):
    bd = BrewData(plateau, p0, rate)
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

    bd, out = run(5.0, 0.0, p0=6.0)
    vent = out.find('VKELLO_VENT')
    check('5 purku ennen nousua (TILAUS-H)', 0 <= vent < out.find('VKELLO_RISE') and
          int(field(out, 'VKELLO_VENT', 'cycles') or 0) >= 2, (field(out, 'VKELLO_VENT', 'cycles') or '-') + ' sykliä')
    check('5 pumppu kaynnistyy purettuna', bd.plant.p_first_on is not None and bd.plant.p_first_on < 1.0,
          '%s bar' % (None if bd.plant.p_first_on is None else '%.2f' % bd.plant.p_first_on))
    check('5 ajo loppuun', field(out, 'VKELLO_END', 'reason') == 'ok', field(out, 'VKELLO_END', 'reason'))

    bd, out = run(6.0, 0.0, rate=0.2)
    check('6 hidas nousu yli 20 s -> plateau', field(out, 'VKELLO_RISE', 'reason') == 'plateau' and
          int(field(out, 'VKELLO_RISE', 'reach_ms') or 0) > 20000,
          '%s %s ms' % (field(out, 'VKELLO_RISE', 'reason'), field(out, 'VKELLO_RISE', 'reach_ms')))
    check('6 ajo loppuun', field(out, 'VKELLO_END', 'reason') == 'ok', field(out, 'VKELLO_END', 'reason'))

    print('RESULT: %d failed' % len(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
