#!/usr/bin/env python3
"""esiuutto_smoke.py — vaiheseurattu esiuutto pim:1 (TILAUS-K vaiheet 1-2, EXPRESSO-ESIUUTTO-25BAR).

Ajaa `functions.pre_infusion_phased`:n CPythonilla virtuaalikellolla ja iskumallilla:
nollaylitys-SSR (releen tila vaihtuu vain verkon nollakohdissa), pumppu iskee vain toisella
puolijaksolla, iskun vaikutus paineeseen 40 ms viiveella, vuoto kuristimen lapi (tau), vareily
johtavalla puolijaksolla. Verkon vaihe on satunnainen suhteessa ajon alkuun, joten tauon kohta
riippuu kellosta eika sattumasta.

Tarkistaa: vaiheet oikeassa jarjestyksessa, yliampuma ja pidon hajonta, 10 ms tauot kaytossa
lukon jalkeen, laitteen kirjaamat iskut = mallin toteutuneet iskut (tauko osui poistettavaan
iskuun), myohastymisvahti pysahdyksilla, jalkinousun oppiminen, pysaytys ja huuhtelu (paine ei
nouse -> pumppu ei katko).

    python3 testit/esiuutto_smoke.py       RESULT: <n> failed
"""
import asyncio
import io
import math
import os
import random
import re
import sys
import types
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pico'))


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

F_MAINS = 50.01
HALF_US = 1e6 / F_MAINS / 2
# Mallin vareilyn vaihe: valittu niin, etta verkkokellon reuna + 8,5-18,7 ms on poistava lohko kuten
# laitteella (vsweep-20260924-a). Kalibroitu tassa mallissa ajolla, joka tulosti taukojen kohdan
# suhteessa passiiviseen puolijaksoon (keskikohta = paras).
RIPPLE_SHIFT_US = 5460.0
# Johtavan puolijakson vareily: perusaallon amplitudi = 0,5 x tama x iskutiheys; 1,0 antaa pidossa
# (iskutiheys ~0,3) ~0,15 bar, AMP_MIN 0,1:n ylapuolelle. Laitteen arvo 2,5 barissa on mittaamatta.
RIPPLE_AMP = 1.0


class Pin:
    def __init__(self):
        self.v, self.hook = 0, None

    def value(self, x=None):
        if x is None:
            return self.v
        if self.hook: self.hook()
        self.v = 1 if x else 0


class Plant:
    """Iskumalli. Puolijakso k: [phi + k*HALF, phi + (k+1)*HALF); pariton = aktiivinen (isku)."""

    def __init__(self, pump, delta=0.2, tau=0.8, lag_us=40000, phi_us=0.0, noise=0.02, fill_us=0, cyc_sd=0.0):
        self.pump, self.delta, self.tau, self.lag = pump, delta, tau, lag_us
        # Tayttovaihe (iskut eivat nosta painetta) ja puolijaksoittainen kohina: laitteella yksittaisen
        # jakson keskiarvo heilui taytossa +-0,5 bar (esiuutto-20260924-b/c)
        self.fill_us, self.cyc_sd, self.cn, self.t_first = fill_us, cyc_sd, 0.0, None
        self.phi, self.noise = phi_us, noise
        self.p, self.last, self.eff, self.k = 0.0, 0, 0, 0
        self.pending = []           # (aika, delta)
        self.strokes = 0
        self.stroke_times = []
        self.pause_offs = []        # releen pois-kaskyjen kohta passiivisen puolijakson alusta (us)
        pump.hook = self.on_pin

    def on_pin(self):
        self.advance(U.us)
        if self.pump.v == 1:        # kutsutaan ennen muutosta: 1 -> 0 on tauon alku
            k = math.floor((U.us - self.phi) / HALF_US)
            start_passive = self.phi + (k if k % 2 == 0 else k + 1) * HALF_US
            if k % 2 == 1:          # aktiivisella puolijaksolla: seuraava passiivinen
                self.pause_offs.append(U.us - (start_passive - 2 * HALF_US))
            else:
                self.pause_offs.append(U.us - start_passive)

    def _leak(self, dt_us):
        self.p *= math.exp(-dt_us / 1e6 / self.tau)

    def advance(self, now):
        while self.phi + (self.k + 1) * HALF_US <= now:
            t_zc = self.phi + (self.k + 1) * HALF_US
            self._apply(t_zc)
            if self.k % 2 == 1 and self.eff:        # aktiivinen puolijakso paattyi johtavana
                if self.t_first is None: self.t_first = t_zc
                if t_zc - self.t_first >= self.fill_us:
                    self.pending.append((t_zc + self.lag, self.delta))
                self.strokes += 1
                self.stroke_times.append(t_zc)
            self.k += 1
            self.eff = self.pump.v                   # tila vaihtuu nollakohdassa
            if self.cyc_sd: self.cn = random.gauss(0.0, self.cyc_sd)
        self._apply(now)

    def _apply(self, t):
        while self.pending and self.pending[0][0] <= t:
            ta, dp = self.pending.pop(0)
            self._leak(ta - self.last); self.last = ta
            self.p += dp
        self._leak(t - self.last); self.last = t

    def bar(self, now):
        self.advance(now)
        ph = (now - self.phi) / (2 * HALF_US)
        rip = RIPPLE_AMP * math.sin(2 * math.pi * (ph - RIPPLE_SHIFT_US / (2 * HALF_US))) if (self.eff and self.k % 2 == 1) else 0.0
        return self.p + rip + self.cn + random.gauss(0.0, self.noise)


class Adc:
    def __init__(self, plant):
        self.plant = plant

    def read_u16(self):
        return int((self.plant.bar(U.us) + 0.99 - F.PCAP_RAW_B) / F.PCAP_RAW_A)


class Ratio:
    def set_pump_on(self): pass
    def set_pump_off(self): pass


class BrewData:
    def __init__(self, target=2.5, hold_s=5.0, **plant_kw):
        self.pump, self.solenoid, self.heater, self.brew = Pin(), Pin(), Pin(), Pin()
        self.plant = Plant(self.pump, **plant_kw)
        self.pressure_sensor = types.SimpleNamespace(pressure_sensor=Adc(self.plant), gain=1.0, offset=-0.99)
        self.target, self.hold_s = target, hold_s
        self.learned_ff_pre, self.eu_coast_s = 0.3, F.EU_COAST_S0
        self.mode, self.pressure, self.pressure_filtered = None, 0.0, 0.0

    def get_relays(self): return self.pump, self.solenoid, self.heater
    def get_switch_brew(self): return self.brew
    def get_pre_infusion_pressure(self): return self.target
    def get_pre_infusion_time(self): return self.hold_s
    def set_mode(self, m): self.mode = m
    def get_pressure(self): return self.plant.bar(U.us)
    def get_weight(self): return None
    def get_flow(self): return None


class Asyncio:
    def __init__(self, stall_p=0.0, stall_ms=(5, 15)):
        self.stall_p, self.stall_ms = stall_p, stall_ms

    async def sleep_ms(self, ms):
        U.us += ms * 1000 if ms > 0 else 150
        if self.stall_p and random.random() < self.stall_p:
            U.us += random.randint(*self.stall_ms) * 1000   # toinen tehtava (BLE, vaaka) varaa vuoron


def run(bd, until_s=None, stall_p=0.0, seed=1):
    random.seed(seed)
    start = U.us
    keep = (lambda: True) if until_s is None else (lambda: U.us - start < until_s * 1e6)
    out = io.StringIO()
    with redirect_stdout(out):
        asyncio.run(F.pre_infusion_phased(bd, U, Asyncio(stall_p), Ratio(), keep))
    return out.getvalue()


def field(text, prefix, key):
    line = next((l for l in text.splitlines() if l.startswith(prefix)), '')
    m = re.search(r'\b%s=(\S+)' % key, line)
    return m.group(1) if m else None


def num(text, prefix, key):
    v = field(text, prefix, key)
    return float(v) if v is not None else float('nan')


def main():
    failed = []

    def check(name, cond, extra=''):
        print('%s %s %s' % ('OK  ' if cond else 'FAIL', name, extra))
        if not cond: failed.append(name)

    # 1 perusajo 2,5 bar, pito 5 s
    bd = BrewData(phi_us=7300.0)
    out = run(bd)
    open('/tmp/esiuutto_smoke_1.log', 'w').write(out)
    check('1 ajo loppuun pitoajan jälkeen', field(out, 'EU_END', 'reason') == 'done', field(out, 'EU_END', 'reason'))
    pos = [out.find(k) for k in ('EU_START', 'EU_CUT', 'EU_COAST', 'EU_HOLD', 'EU_END')]
    check('1 vaiheet järjestyksessä (start, cut, coast, hold, end)', all(0 <= a < b for a, b in zip(pos, pos[1:])), str(pos))
    check('1 pumppurele pois lopussa', bd.pump.v == 0)
    over = num(out, 'EU_END', 'over')
    # Yliampuman ikkuna kattaa pidon ensimmaisen sekunnin (EU_OVER_MS), jolloin mallin iskukoko 0,2 bar
    # nakyy jo pidon sahalaitana: raja on yksi isku, ei sen alle
    check('1 yliampuma ≤ yksi isku (0,2 bar)', over <= 0.2, '%+.2f bar' % over)
    hm, hs = num(out, 'EU_END', 'hold_mean'), num(out, 'EU_END', 'hold_sd')
    check('1 pidon keskiarvo 2,5 ± 0,05 bar', abs(hm - 2.5) <= 0.05, '%.3f' % hm)
    check('1 pidon hajonta < 0,1 bar', hs < 0.1, '%.3f' % hs)
    sk10, sk20 = int(num(out, 'EU_END', 'sk10')), int(num(out, 'EU_END', 'sk20'))
    check('1 10 ms taukoja käytössä lukon jälkeen (≥ 80 %)', sk10 >= 0.8 * (sk10 + sk20), 'sk10=%d sk20=%d' % (sk10, sk20))
    check('1 ei myöhästymisiä', field(out, 'EU_END', 'late') == '0', field(out, 'EU_END', 'late'))
    fw = int(num(out, 'EU_END', 'strokes'))
    check('1 laitteen iskut = mallin iskut (±2): tauot osuvat', abs(bd.plant.strokes - fw) <= 2,
          'laite %d, malli %d, poistettu %s' % (fw, bd.plant.strokes, field(out, 'EU_END', 'rm')))
    offs = bd.plant.pause_offs[5:]
    if offs:
        mean_off = sum(offs) / len(offs)
        check('1 tauon alku passiivisen puolijakson keskellä (±2 ms)', abs(mean_off - HALF_US / 2) < 2000,
              'keskim. %.0f us, min %.0f, max %.0f (puolijakso %.0f)' % (mean_off, min(offs), max(offs), HALF_US))
    check('1 kello seuraa verkkoa', abs(num(out, 'EU_END', 'hz') - F_MAINS) < 0.02, field(out, 'EU_END', 'hz'))
    check('1 nousun ikkunat eivät opeta kelloa (gate=-1 ennen EU_CUT)',
          all('gate=-1' in l for l in out[:out.find('EU_CUT')].splitlines() if l.startswith('VKELLO')))
    check('1 opittu ff päivittyi (pito ≥ 2 s)', abs(bd.learned_ff_pre - 0.3) > 1e-3, '%.2f' % bd.learned_ff_pre)

    # 2 jälkinousun oppiminen: toinen ajo samalla laitteella
    c1 = bd.eu_coast_s
    bd.plant.p, bd.plant.pending = 0.0, []    # ajojen valissa paine purkautuu kuristimen lapi
    out2 = run(bd, seed=2)
    open('/tmp/esiuutto_smoke_2.log', 'w').write(out2)
    check('2 jälkinousu opittu ja rajoissa', F.EU_COAST_MIN <= bd.eu_coast_s <= F.EU_COAST_MAX and c1 != F.EU_COAST_S0,
          '%.3f -> %.3f' % (c1, bd.eu_coast_s))
    check('2 toinen ajo: yliampuma ≤ yksi isku (0,2 bar)', num(out2, 'EU_END', 'over') <= 0.2, field(out2, 'EU_END', 'over'))

    # 3 pysähdykset (toinen tehtävä varaa vuoron 5-15 ms)
    bd3 = BrewData(phi_us=2100.0)
    out3 = run(bd3, stall_p=0.005, seed=3)
    open('/tmp/esiuutto_smoke_3.log', 'w').write(out3)
    fw3 = int(num(out3, 'EU_END', 'strokes'))
    check('3 pysähdykset: ajo loppuun', field(out3, 'EU_END', 'reason') == 'done', field(out3, 'EU_END', 'reason'))
    bad = [o for o in bd3.plant.pause_offs if o >= HALF_US]
    check('3 pysähdykset: jokainen tehty tauko alkaa passiivisella puolijaksolla', not bad and bd3.plant.pause_offs,
          '%d/%d väärin, late=%s miss=%s' % (len(bad), len(bd3.plant.pause_offs), field(out3, 'EU_END', 'late'),
                                           field(out3, 'EU_END', 'miss')))
    check('3 pysähdykset: vahti toimi (late > 0)', int(num(out3, 'EU_END', 'late')) > 0, field(out3, 'EU_END', 'late'))
    check('3 pysähdykset: pito 2,5 ± 0,08 bar', abs(num(out3, 'EU_END', 'hold_mean') - 2.5) <= 0.08,
          field(out3, 'EU_END', 'hold_mean'))

    # 4 pysäytys kesken pidon
    bd4 = BrewData(phi_us=15000.0)
    out4 = run(bd4, until_s=3.0, seed=4)
    check('4 pysäytys: reason=stop ja rele pois', field(out4, 'EU_END', 'reason') == 'stop' and bd4.pump.v == 0,
          field(out4, 'EU_END', 'reason'))

    # 5 huuhtelu: vuoto niin suuri, ettei paine nouse puoleen tavoitteesta -> pumppua ei katkota
    bd5 = BrewData(tau=0.1, phi_us=500.0)
    out5 = run(bd5, until_s=3.0, seed=5)
    check('5 huuhtelu: ei katkaisua, ei taukoja', 'EU_CUT' not in out5 and field(out5, 'EU_END', 'rm') == '0',
          'max=%s rm=%s' % (field(out5, 'EU_END', 'max'), field(out5, 'EU_END', 'rm')))

    # 6 kohinainen taytto kuten laitteella (b/c-ajot): 2,4 s ilman painetta, jaksokohina sd 0,3 bar
    bd6 = BrewData(phi_us=4100.0, fill_us=2400000, cyc_sd=0.3)
    out6 = run(bd6, seed=6)
    open('/tmp/esiuutto_smoke_6.log', 'w').write(out6)
    cut_p, cut_ms = num(out6, 'EU_CUT', 'p'), num(out6, 'EU_CUT', 't_ms')
    check('6 taytto: katkaisu vasta taytön jälkeen, ei piikistä (t > 2,6 s, p5 ≥ 1,0 bar)',
          cut_ms > 2600 and cut_p >= 1.0, 't=%s ms p=%s' % (field(out6, 'EU_CUT', 't_ms'), field(out6, 'EU_CUT', 'p')))
    hold_p = num(out6, 'EU_HOLD', 'p')
    check('6 taytto: pito alkaa vasta tavoitepaineessa (p5 ≥ 2,4)', hold_p >= 2.4, field(out6, 'EU_HOLD', 'p'))
    check('6 taytto: yliampuma (p5) ≤ 0,3 bar', num(out6, 'EU_END', 'over') <= 0.3, field(out6, 'EU_END', 'over'))
    check('6 taytto: pidon keskiarvo 2,5 ± 0,1', abs(num(out6, 'EU_END', 'hold_mean') - 2.5) <= 0.1,
          field(out6, 'EU_END', 'hold_mean'))

    # 7 laitteeseen sovitettu malli (esiuutto-20260924-d/e): jaksokohina sd 0,25 ja pysahdykset 0,8 %
    # asyncio-vuoroista toistavat laitteen pidon p5-hajonnan 0,16-0,17, iskuvaihtelun ~0,9 / 100 ms,
    # late 13-18 ja jaksohajonnan 0,25. Myohastynyt paatos (5-10 ms) ei saa jattaa jaksoa ilman paatosta:
    # vanha koodi paasti 14-24 laskematonta iskua ajossa.
    gaps = []
    for seed in (7, 8, 9):
        bd7 = BrewData(hold_s=6.0, phi_us=(7300.0 * seed) % 20000, cyc_sd=0.25)
        out7 = run(bd7, stall_p=0.008, seed=seed)
        gaps.append(int(num(out7, 'EU_END', 'strokes')) - bd7.plant.strokes)
    check('7 sovitettu malli: laitteen iskut = mallin iskut (±4) pysähdyksissä', all(abs(g) <= 4 for g in gaps),
          'laite - malli %s' % gaps)

    print('RESULT: %d failed' % len(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
