#!/usr/bin/env python3
"""vsweep_smoke.py — taukojen vaihepyyhkäisy vsweep:<reps> (TILAUS-K/L askel 1, 24.9.2026).

Ajaa `pressure_phase_sweep_run`:n CPythonilla virtuaalikellolla (kuten vkello_rise_smoke) ja
iskumallilla: pumppu iskee vain nousevalla puolijaksolla (Δ bar/isku, vuoto τ 0,8 s, tasanne
~8 bar), väreily 0,4 bar kun rele johtaa. SSR-malli:
  - nollaylitys: releen tila vaihtuu vain verkon nollakohdissa (10 ms tauko poistaa iskun vain,
    jos poistettu puolijakso on nouseva -> 10 ms levyinen lohko, jyrkät reunat),
  - vapaavaiheinen: tila vaihtuu heti, isku skaalautuu nousevan puolijakson johtoajalla (loiva).
Tarkistaa ajon kulun, releet, tauon toteutuneen kohdan, tyhjän ja 20 ms vertailun, ja
`vsweep_analyysi.analyse`:n lohkon.

    python3 testit/vsweep_smoke.py       RESULT: <n> failed
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
sys.path.insert(0, HERE)


class Utime:
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
import vsweep_analyysi as VA   # noqa: E402

F_MAINS = 50.02
HALF_US = 1e6 / F_MAINS / 2


class Pin:
    def __init__(self):
        self.v, self.hook = 0, None

    def value(self, x=None):
        if x is None:
            return self.v
        if self.hook: self.hook()
        self.v = x


class Plant:
    def __init__(self, pump, solenoid, zero_cross=True, delta=0.2, tau=0.8):
        self.pump, self.solenoid, self.zc = pump, solenoid, zero_cross
        self.delta, self.tau = delta, tau
        self.p, self.last, self.eff = 0.0, 0, 0
        self.first_on, self.k = None, 1          # seuraava nollakohta k * HALF_US
        self.on_acc = 0.0                        # vapaavaihe: johtoaika nousevalla puolijaksolla
        self.strokes = 0
        pump.hook = solenoid.hook = lambda: self.advance(U.us)

    def _leak(self, dt_us):
        self.p *= math.exp(-dt_us / 1e6 / self.tau)

    def advance(self, now):
        while self.k * HALF_US <= now:
            t_zc = self.k * HALF_US
            self._leak(t_zc - self.last)
            if not self.zc and self.k % 2 == 1 and self.pump.v:   # nousevan puolijakson loppu
                self.on_acc += t_zc - self.last
            self.last = t_zc
            if self.zc:
                self.eff = self.pump.v                             # tila vaihtuu nollakohdassa
            primed = self.first_on is not None and t_zc - self.first_on > 1.2e6
            if self.k % 2 == 1:                                     # nouseva puolijakso loppui
                if self.zc:
                    frac = 1.0 if self._rising_eff else 0.0
                else:
                    frac = self.on_acc / HALF_US
                if primed and frac > 0:
                    self.p += self.delta * frac; self.strokes += frac
                self.on_acc = 0.0
            else:
                self._rising_eff = self.eff                         # alkava nouseva puolijakso
            self.k += 1
        if self.pump.v and self.first_on is None: self.first_on = now
        if not self.zc and (self.k % 2 == 1) and self.pump.v:
            self.on_acc += now - self.last
        self._leak(now - self.last)
        self.last = now

    def bar(self, now):
        self.advance(now)
        cond = self.eff if self.zc else self.pump.v
        rising = (self.k % 2 == 1)
        ripple = 0.4 * math.sin(2 * math.pi * F_MAINS * now / 1e6) if (cond and rising) else 0.0
        return self.p + ripple


class Adc:
    def __init__(self, plant):
        self.plant = plant

    def read_u16(self):
        return int((self.plant.bar(U.us) + 0.99 - F.PCAP_RAW_B) / F.PCAP_RAW_A)


class BrewData:
    def __init__(self, zero_cross=True):
        self.pump, self.solenoid, self.heater = Pin(), Pin(), Pin()
        self.brew, self.water, self.steam = Pin(), Pin(), Pin()
        self.plant = Plant(self.pump, self.solenoid, zero_cross)
        self.plant._rising_eff = 0
        self.pressure_sensor = types.SimpleNamespace(pressure_sensor=Adc(self.plant), gain=1.0, offset=-0.99)
        self.dev_safe, self.vsweep_abort, self.mode = False, False, None

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


def run(reps, zero_cross=True):
    bd = BrewData(zero_cross)
    out = io.StringIO()
    with redirect_stdout(out):
        asyncio.run(F.pressure_phase_sweep_run(bd, U, Asyncio(), reps))
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

    tmp = os.path.join('/tmp', 'vsweep_smoke_zc.log')
    bd, out = run(2, zero_cross=True)
    open(tmp, 'w').write(out)
    check('1 ajo loppuun', field(out, 'VSWEEP_END', 'reason') == 'ok',
          '%s %s' % (field(out, 'VSWEEP_END', 'reason'), [l for l in out.splitlines() if 'ERR' in l][:1]))
    check('1 taukoja 2 x 22', field(out, 'VSWEEP_END', 'trials') == '44', field(out, 'VSWEEP_END', 'trials'))
    check('1 purku, tasanne ja lukko ennen ensimmäistä taukoa',
          0 <= out.find('VSWEEP_VENT') < out.find('VSWEEP_RISE') < out.find('VSWEEP_LOCK') < out.find('VSWEEP k='))
    check('1 releet pois', bd.pump.v == 0 and bd.solenoid.v == 0)
    check('1 kello seuraa verkkoa (50,02 Hz)', abs(float(field(out, 'VSWEEP_END', 'hz') or 0) - F_MAINS) < 0.01,
          field(out, 'VSWEEP_END', 'hz'))
    a = VA.analyse(VA.parse([tmp]))
    check('1 toteutunut kohta = käsketty (≤ 100 us)', a['act_err'] <= 100, '%.0f us' % a['act_err'])
    rows = VA.parse([tmp])
    check('1 kellon epävarmuus ≤ 500 us joka tauolla (lukitsematta %d)' % a['unlocked'],
          max(r['sd'] for r in rows) <= 500, '%.0f us' % max(r['sd'] for r in rows))
    check('1 tyhjä vertailu < 1/4 iskusta', a['full'] is not None and abs(a['trend']) < 0.25 * abs(a['full']),
          '%+.3f (sd %.3f)' % (a['trend'], a['sham_sd']))
    check('1 20 ms tauko poistaa iskun', a['full'] is not None and a['full'] < -0.1, '%+.3f' % (a['full'] or 0))
    check('1 nollaylitys: 10 ms lohko, jyrkkä raja (välitasoja ≤ 2)',
          a.get('mid', 99) <= 2 and a.get('contrast', 0) > 0.1,
          'lohko %s–%s ms, välitasoja %s, ero %.3f' % (a.get('block_start_ms'), a.get('block_end_ms'),
                                                     a.get('mid'), a.get('contrast', 0)))
    check('1 lohkon sisällä vaste ≈ 20 ms tauon vaste', abs(a.get('level_in', 0) - (a['full'] or 0)) < 0.05,
          '%+.3f vs %+.3f' % (a.get('level_in', 0), a['full'] or 0))

    tmp2 = os.path.join('/tmp', 'vsweep_smoke_rp.log')
    bd, out = run(1, zero_cross=False)
    open(tmp2, 'w').write(out)
    a2 = VA.analyse(VA.parse([tmp2]))
    check('2 vapaavaiheinen SSR: ajo loppuun', field(out, 'VSWEEP_END', 'reason') == 'ok',
          field(out, 'VSWEEP_END', 'reason'))
    check('2 vapaavaiheinen SSR: loiva raja (välitasoja ≥ 4)', a2.get('mid', 0) >= 4,
          'välitasoja %s' % a2.get('mid'))

    print('RESULT: %d failed' % len(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
