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
        if self.hook: self.hook(x)
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
        self.pause_t = []           # tauon alku (us)
        self.pause_lens = []        # tauon pituus (us); None = rele ei palannut paalle (ajon loppu)
        pump.hook = self.on_pin

    def on_pin(self, x):
        self.advance(U.us)
        if self.pump.v == 0 and x and self.pause_lens and self.pause_lens[-1] is None:
            self.pause_lens[-1] = U.us - self.t_off
        if self.pump.v == 1 and not x:     # kutsutaan ennen muutosta: 1 -> 0 on tauon alku
            self.t_off = U.us
            self.pause_t.append(U.us)
            self.pause_lens.append(None)
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
        # Uusi laite = kello nollasta: verkon vaihe ajon alussa riippuu vain phi_us:sta, ei aiempien tapausten
        # kestosta (EXPRESSO-SMOKE-TILASTO: yhden tapauksen muutos vaihtoi muiden kohinatoteuman)
        U.us = 0
        self.pump, self.solenoid, self.heater, self.brew = Pin(), Pin(), Pin(), Pin()
        self.plant = Plant(self.pump, **plant_kw)
        self.pressure_sensor = types.SimpleNamespace(pressure_sensor=Adc(self.plant), gain=1.0, offset=-0.99)
        self.target, self.hold_s = target, hold_s
        self.learned_ff_pre, self.eu_coast_s, self.eu_g_pre, self.eu_tau_pre = 0.3, F.EU_COAST_S0, 0.0, 0.0
        self.saved = 0
        self.mode, self.pressure, self.pressure_filtered = None, 0.0, 0.0

    def get_relays(self): return self.pump, self.solenoid, self.heater
    def get_switch_brew(self): return self.brew
    def get_pre_infusion_pressure(self): return self.target
    def get_pre_infusion_time(self): return self.hold_s
    def set_mode(self, m): self.mode = m
    def set_setting_changed(self): self.saved += 1
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
    # Aikaraja aina: ajo, jonka pito ei ala, ei paaty koskaan (26.9.2026: kaksi testiajoa pyori ~80 min).
    # 30 s virtuaaliaikaa ylittaa jokaisen tapauksen pidon; raja -> reason=stop -> tapaus kaatuu.
    lim = 30.0 if until_s is None else until_s
    keep = lambda: U.us - start < lim * 1e6
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


# Tilastolliset tarkistukset (EXPRESSO-SMOKE-TILASTO): kohinasta tai verkon vaiheesta riippuva tulos ajetaan
# N siemenella/vaiheella. Hyvaksynta: keskiarvo valilla [lo, hi] ja sen ulkopuolella enintaan osuus share.
# 1. ajo ilman edellisen tietoa lahtee alakanttiin (paatos 26.9.2026), joten sille omat rajat (kayttaja 26.9.2026:
# rampin viive <= 0,5, pidon ka -0,15...+0,1); kohinaisen parin hanta ~25 % -> osuus 1/3.
N_PHASE = 12            # kohinattomat: vain vaihe vaihtelee
N_NOISE = 24            # kohinaiset parit: 24:lla keskiarvon sd ~0,01 bar
STAT_SHARE = 0.25
NOISE_SHARE = 1 / 3


def stat(check, name, xs, hi, lo=None, share=STAT_SHARE, fmt='%+.3f'):
    mean = sum(xs) / len(xs)
    n_out = sum(1 for x in xs if x > hi or (lo is not None and x < lo))
    check('%s [N=%d: ka, ulkona ≤ %d %%]' % (name, len(xs), round(share * 100)),
          mean <= hi and (lo is None or mean >= lo) and n_out <= share * len(xs),
          ('ka ' + fmt + ', min ' + fmt + ', max ' + fmt + ', ulkona %d/%d') % (mean, min(xs), max(xs), n_out, len(xs)))


def run9_dev(seed, carry, delta=0.12, tau=9.0):
    """Laitteeseen sovitettu kiinni-tila kohinalla; palauttaa pidon 2 s keskiarvon poikkeaman ja opitut arvot."""
    bd = BrewData(hold_s=6.0, phi_us=(3100.0 * seed) % 20000, delta=delta, tau=tau, fill_us=1000000,
                  noise=0.02, cyc_sd=0.25)
    if carry: bd.learned_ff_pre, bd.eu_g_pre, bd.eu_coast_s, bd.eu_tau_pre = carry
    out = run(bd, stall_p=0.008, seed=seed)
    hold = num(out, 'EU_HOLD', 't_ms')
    ps = [float(l.split()[2]) for l in out.splitlines() if l.startswith('EU ') and hold <= int(l.split()[1]) < hold + 2000]
    return (sum(ps) / len(ps) - 2.5) if ps else 9.0, (bd.learned_ff_pre, bd.eu_g_pre, bd.eu_coast_s, bd.eu_tau_pre)


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
    # Vain kellon lukituttua alkaneet tauot (firmwaren ehto 2,5 sd < EU_PHASE_OK_US -> 10 ms tauot): sita ennen 20 ms
    # tauko poistaa iskun vaiheesta riippumatta, eika ajon lopun katkaisu (rele ei palaa) ole tauko. Kun kello jatkui
    # edellisesta tapauksesta, HEADin vaihe vaisti molemmat sattumalta (EXPRESSO-SMOKE-TILASTO).
    t_lock = next((int(l.split()[1]) * 1000 for l in out3.splitlines() if l.startswith('EU ')
                   and 2.5 * float(re.search(r'sd_us=(\S+)', l).group(1)) < F.EU_PHASE_OK_US), None)
    offs10 = [o for o, t, n in zip(bd3.plant.pause_offs, bd3.plant.pause_t, bd3.plant.pause_lens)
              if n is not None and t_lock is not None and t >= t_lock]
    bad = [o for o in offs10 if o >= HALF_US]
    check('3 pysähdykset: jokainen tehty 10 ms tauko alkaa passiivisella puolijaksolla', not bad and offs10,
          '%d/%d väärin, late=%s miss=%s' % (len(bad), len(offs10), field(out3, 'EU_END', 'late'),
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
    # Taytto loppuu 2,4 s + viive 40 ms. Nopea nousu saa katkaista jo 1/4 tavoitteesta (EXPRESSO-ESIUUTTO-ALKU): raja
    # oli p5 >= 1,0 / t > 2,6 s vanhan 1/2 tavoitteen saannon mukaan; uusi katkaisee 2593 ms / 0,92 todellisessa nousussa.
    check('6 taytto: katkaisu vasta taytön jälkeen, ei piikistä (t > 2,44 s, p5 ≥ 1/4 tavoite)',
          cut_ms > 2440 and cut_p >= 0.625, 't=%s ms p=%s' % (field(out6, 'EU_CUT', 't_ms'), field(out6, 'EU_CUT', 'p')))
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

    # 8 loppunosto sovitetulla iskumallilla (esiuutto-20260925-a/b: iskukoko ~0,1 bar, vuoto tau ~1,6 s,
    # tayttö ~1 s), ilman kohinaa: ramppi ei saa jaada nousemaan pelkan P-termin varassa. Vanha koodi:
    # katkaisusta pitoon 1,4-1,6 s ja paine ~0,6 bar rampin alla. Viimeiset 0,1-0,2 bar ennen pitoa
    # vievat hitaalla vuodolla ~0,4 s, eika sita kiirehdita (ylitys).
    # Kohinaton, joten tulos riippuu vain verkon vaiheesta: N_PHASE vaihetta, tilastollinen tarkistus (EXPRESSO-SMOKE-TILASTO).
    r8 = {1: [], 2: []}
    for seed in range(80, 80 + N_PHASE):
        bd8 = BrewData(hold_s=3.0, phi_us=(3100.0 * seed) % 20000, delta=0.1, tau=1.6, fill_us=1000000, noise=0.0)
        for r in (1, 2):
            bd8.plant.p, bd8.plant.pending, bd8.plant.t_first = 0.0, [], None
            out8 = run(bd8, seed=seed)
            cut8, hold8 = num(out8, 'EU_CUT', 't_ms'), num(out8, 'EU_HOLD', 't_ms')
            lag = max([float(l.split()[3]) - float(re.search(r'p5=(\S+)', l).group(1)) for l in out8.splitlines()
                       if l.startswith('EU ') and cut8 + 150 < int(l.split()[1]) < hold8
                       and float(l.split()[3]) < float(field(out8, 'EU_START', 'target'))] or [0.0])
            r8[r].append((lag, hold8 - cut8, num(out8, 'EU_END', 'over')))
    for r in (1, 2):
        lim8 = 0.5 if r == 1 else 0.3       # ajo 1 ilman edellisen tietoa: omat rajat
        stat(check, '8 sovitettu malli ajo %d: paine enintään %s bar rampin alla' % (r, ('%.1f' % lim8).replace('.', ',')),
             [x[0] for x in r8[r]], lim8)
        stat(check, '8 sovitettu malli ajo %d: katkaisusta pitoon ≤ 1,1 s' % r, [x[1] for x in r8[r]], 1100, fmt='%.0f')
        stat(check, '8 sovitettu malli ajo %d: yliampuma ≤ 0,2 bar' % r, [x[2] for x in r8[r]], 0.2)

    # 9 pidon myotakytkenta (EXPRESSO-ESIUUTTO-FF): vuoto edellisen ajon pidosta, G taman ajon noususta, ja
    # ensimmainen ajo alakanttiin (laite 26.9.2026: nousun arvio 0,22-0,43, tarve 0,09-0,10). Tilat: lampin
    # (iskukoko 0,1, tau 1,6 s, tarve 0,31), kylma (0,15 / 2,2, tarve 0,15) ja kiinni (0,05 / 10 s, tarve 0,10:
    # hidas nousu kuten 26.9. a-ajo). Parit: 1. ajo ilman edellista, 2. ajo edellisen pidon tiedoilla.
    states = {'lämmin': (0.1, 1.6), 'kylmä': (0.15, 2.2), 'kiinni': (0.05, 10.0)}

    def run9(state, seed, noisy, carry=None):
        delta, tau = states[state]
        bd9 = BrewData(hold_s=6.0, phi_us=(3100.0 * seed) % 20000, delta=delta, tau=tau, fill_us=1000000,
                       noise=0.02 if noisy else 0.0, cyc_sd=0.25 if noisy else 0.0)
        if carry: bd9.learned_ff_pre, bd9.eu_g_pre, bd9.eu_coast_s, bd9.eu_tau_pre = carry
        out9 = run(bd9, stall_p=0.008 if noisy else 0.0, seed=seed)
        open('/tmp/esiuutto_smoke_9_%s_%d.log' % (state, seed), 'w').write(out9)
        hold9 = num(out9, 'EU_HOLD', 't_ms')
        ps = [float(l.split()[2]) for l in out9.splitlines() if l.startswith('EU ') and hold9 <= int(l.split()[1]) < hold9 + 2000]
        need = 2.5 / (50 * delta * tau)
        return dict(ff=num(out9, 'EU_CUT', 'ff') - need, dev=(sum(ps) / len(ps) - 2.5) if ps else 9.0,
                    c2h=hold9 - num(out9, 'EU_CUT', 't_ms'), learn=bd9.learned_ff_pre - need,
                    over=num(out9, 'EU_END', 'over')), (bd9.learned_ff_pre, bd9.eu_g_pre, bd9.eu_coast_s, bd9.eu_tau_pre)

    # 1. ajo kohinattomana riippuu vain verkon vaiheesta: N_PHASE vaihetta. ff ja opittu tarve ovat vaiheesta
    # riippumattomia (hajonta < 0,01), joten ne pysyvat jokaisen ajon tarkistuksina.
    first = {}
    for st in ('lämmin', 'kylmä'):
        rs = []
        for seed in range(90, 90 + N_PHASE):
            r, c = run9(st, seed, False)
            rs.append(r)
            if seed == 90: first[st] = c
        check('9 1. ajo %s: ff ei yli tarpeen (≤ +0,05)' % st, all(r['ff'] <= 0.05 for r in rs),
              'max %+.2f' % max(r['ff'] for r in rs))
        stat(check, '9 1. ajo %s: pidon 2 s keskiarvo 2,5 −0,15…+0,1' % st, [r['dev'] for r in rs], 0.1, lo=-0.15)
        stat(check, '9 1. ajo %s: katkaisusta pitoon ≤ 1,1 s' % st, [r['c2h'] for r in rs], 1100, fmt='%.0f')
        check('9 1. ajo %s: pidon tarve opittu (±0,03)' % st, all(abs(r['learn']) <= 0.03 for r in rs),
              'max |%.3f|' % max(abs(r['learn']) for r in rs))
    for a, b in (('lämmin', 'kylmä'), ('kylmä', 'lämmin')):
        r, _ = run9(b, 91, False, first[a])
        check('9 %s -> %s: ff ±0,1 tarpeesta' % (a, b), abs(r['ff']) <= 0.1, '%+.2f' % r['ff'])
        check('9 %s -> %s: pidon 2 s keskiarvo 2,5 ± 0,05, yliampuma ≤ 0,2' % (a, b),
              abs(r['dev']) <= 0.05 and r['over'] <= 0.2, '%+.2f bar, over %.2f' % (r['dev'], r['over']))
    # Kiinni: 1. ajo yliarvioi (tunnettu raja, laite 26.9. a), mutta oppii tarpeen, ja 2. ajo osuu
    r1, c1 = run9('kiinni', 92, False)
    check('9 1. ajo kiinni: pidon tarve opittu (±0,03)', abs(r1['learn']) <= 0.03, '%+.3f (1. ajon ff %+.2f)' % (r1['learn'], r1['ff']))
    r2, _ = run9('kiinni', 93, False, c1)
    check('9 kiinni -> kiinni: pidon 2 s keskiarvo 2,5 ± 0,05', abs(r2['dev']) <= 0.05, '%+.2f bar' % r2['dev'])
    # Kohina (jaksokohina 0,25, pysahdykset 0,8 %): lampin -> kylma ja kylma -> lampin, N_NOISE siementa. 3 siementa
    # "kaikki rajan sisalla" kaatui ~joka toisella toteumalla (osuus yli ±0,1 ~20 %).
    for a, b in (('lämmin', 'kylmä'), ('kylmä', 'lämmin')):
        devs = []
        for seed in range(200, 200 + N_NOISE):
            _, c = run9(a, seed, True)
            r, _ = run9(b, seed + 100, True, c)
            devs.append(r['dev'])
        stat(check, '9 kohina %s -> %s: pidon 2 s keskiarvo 2,5 ± 0,1' % (a, b), devs, 0.1, lo=-0.1, share=NOISE_SHARE)

    # 10 pidon alun ylitys kohinasta (EXPRESSO-ESIUUTTO-ALKU): laite 26.9. g/h, kuristin lahes kiinni (tarve ~0,05,
    # tau_obs ~9 s), edellisen pidon tieto (ff = tarve). Jaksokohina 0,25 ja pysahdykset 0,8 %. Nollaan rajattu duty
    # tasasuuntasi kohinan lisaiskuiksi: vanha koodi 2 s keskiarvo +0,16 (max +0,39) 24 siemenella, laite g +0,11.
    devs = []
    for seed in range(100, 108):
        _, c = run9_dev(seed, None)
        dev, _ = run9_dev(seed + 50, c)
        devs.append(dev)
    mean10 = sum(devs) / len(devs)
    check('10 kiinni + kohina, edellisen tieto: pidon 2 s keskiarvo ka ≤ +0,06, max ≤ +0,2',
          mean10 <= 0.06 and max(devs) <= 0.2, 'ka %+.3f, max %+.2f' % (mean10, max(devs)))

    # 11 nopea nousu ilman tayttoa (EXPRESSO-ESIUUTTO-ALKU, laite 26.9. o-q: kuristin lahes kiinni, jarjestelma taynna,
    # nousu 11,5 bar/s, iskun vaikutus ~100 ms viiveella). Huuhtelusaanto p5 >= 1/2 tavoite myohastytti katkaisun 1,3-1,6
    # bariin -> huippu 3,4-4,3. Kohinaton malli: vanha koodi katkaisu 1,46 / over 1,07, uusi 1,05 / 0,61.
    bd11 = BrewData(hold_s=6.0, phi_us=(3100.0 * 510) % 20000, delta=0.25, tau=4.0, lag_us=100000, fill_us=0,
                    noise=0.0)
    out11 = run(bd11, seed=510)
    open('/tmp/esiuutto_smoke_11.log', 'w').write(out11)
    check('11 nopea nousu: katkaisu ennen puolta tavoitetta ja yliampuma ≤ 0,8 bar',
          num(out11, 'EU_CUT', 'p') < 1.25 and num(out11, 'EU_END', 'over') <= 0.8,
          'katkaisu %s, over %s' % (field(out11, 'EU_CUT', 'p'), field(out11, 'EU_END', 'over')))

    # 12 avoin kuristin (EXPRESSO-ESIUUTTO-AVOIN, laite 26.9. l-n: tarve 0,64-0,69, tau_obs 0,35-0,92 s): iskukoko 0,128,
    # tau 0,6 s, taytto 3 s, kohina kuten laitteella. ff EU_TAU_S:lla 0,20 -> pidon 2 ensimmaista s p5 2,33 (laite 2,28-2,37),
    # edellisen tau:lla 0,64 -> 2,49. 1. ajo ff 0,09: integraali rajattiin 0,45:een, joten pito jai 2,27:aan koko ajaksi.
    def run12(seed, carry):
        bd12 = BrewData(hold_s=6.0, phi_us=(3100.0 * seed) % 20000, delta=0.128, tau=0.6, fill_us=3000000,
                        noise=0.02, cyc_sd=0.28)
        if carry: bd12.learned_ff_pre, bd12.eu_g_pre, bd12.eu_coast_s, bd12.eu_tau_pre = carry
        out12 = run(bd12, stall_p=0.008, seed=seed)
        hold12 = num(out12, 'EU_HOLD', 't_ms')
        p5 = [(int(l.split()[1]) - hold12, float(re.search(r'p5=(\S+)', l).group(1))) for l in out12.splitlines()
              if l.startswith('EU ') and int(l.split()[1]) >= hold12]
        h02 = [v for t, v in p5 if t < 2000]
        h26 = [v for t, v in p5 if 2000 <= t < 6000]
        return (sum(h02) / len(h02) if h02 else 0.0, sum(h26) / len(h26) if h26 else 0.0), \
            (bd12.learned_ff_pre, bd12.eu_g_pre, bd12.eu_coast_s, bd12.eu_tau_pre)
    firsts, seconds = [], []
    for seed in (120, 121, 122, 123):
        h1, c = run12(seed, None)
        h2, _ = run12(seed + 50, c)
        firsts.append(h1[1]); seconds.append(h2[0])
    check('12 avoin 1. ajo: pito 2-6 s p5 ≥ 2,42 (integraali ei rajaa tarvetta)', min(firsts) >= 2.42,
          '%s' % ['%.2f' % v for v in firsts])
    check('12 avoin, edellisen tieto: pidon 0-2 s p5 ka ≥ 2,42', sum(seconds) / len(seconds) >= 2.42,
          'ka %.3f, %s' % (sum(seconds) / len(seconds), ['%.2f' % v for v in seconds]))

    print('RESULT: %d failed' % len(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
