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
        if GC.period is not None: GC.tick()
        return self.us

    def ticks_ms(self):
        return self.ticks_us() // 1000

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b


class Gc:
    """MicroPythonin roskienkeruu virtuaalikellolla (EXPRESSO-ESIUUTTO-VUORONVARAUS). Oletuksena pois: tapaukset 1-13 eivat
    kuluta kekoa. enable(): keko kuluu tasaisesti, ja kun se loppuu, automaattinen keruu pysayttaa silmukan 15-28 ms missa
    kohdassa tahansa (laite an 26.9.2026, euv:0: keko 307 kt taynna 0,5-0,8 s:ssa, keruu 15-28 ms). collect() pysayttaa yhta
    kauan, mutta firmwaren valitsemassa kohdassa. Jakso arvotaan run():ssa siemenen jalkeen."""
    HEAP = 200 * 1024

    def __init__(self):
        self.enabled, self.period, self.last, self.auto, self.auto_t = False, None, 0, 0, []

    def enable(self, period_s=(0.5, 0.8), stall_ms=(15, 28)):
        self.enabled, self.period_s, self.stall_ms = True, period_s, stall_ms

    def disable(self):
        self.enabled, self.period = False, None

    def start(self):
        if self.enabled:
            self.auto, self.last, self.auto_t = 0, U.us, []
            self.period = random.uniform(*self.period_s) * 1e6

    def _stall(self):
        U.us += random.randint(*self.stall_ms) * 1000
        self.last = U.us
        self.period = random.uniform(*self.period_s) * 1e6

    def mem_free(self):
        if self.period is None: return self.HEAP
        return max(0, int(self.HEAP * (1 - (U.us - self.last) / self.period)))

    def collect(self):
        if self.period is not None: self._stall()

    def tick(self):
        if U.us - self.last >= self.period:
            self.auto += 1
            self.auto_t.append(U.us)
            self._stall()


U = Utime()
GC = Gc()
sys.modules['utime'] = U
sys.modules.setdefault('devsafe', types.SimpleNamespace(feed=lambda: None))
import functions as F   # noqa: E402
F.gc = GC

IQ_CLOSE_US = [0]    # kellon ikkunan sulun hinta virtuaaliaikana; tapaus 14: laite ao/ap 10-11 ms naytteenotossa


def _iq_close_cost(close):
    def wrapped(self, t, learn=True):
        U.us += IQ_CLOSE_US[0]
        return close(self, t, learn)
    return wrapped


import verkkokello   # noqa: E402
verkkokello.Verkkokello.iq_close = _iq_close_cost(verkkokello.Verkkokello.iq_close)

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
    """Iskumalli. Puolijakso k: [phi + k*HALF, phi + (k+1)*HALF); pariton = aktiivinen (isku).

    delta_f > 0: isku nostaa myos nopeaa osaa, joka purkautuu tau_f:lla (kahden osan malli, EXPRESSO-ESIUUTTO-UUTTOASENTO).
    Laite af/ag (kuristin lahella uuttoa): pudotus iskuryopyn jalkeen ~9 bar/s ja 300 ms rajasykli, vaikka pidon tarve
    0,19 vastaa hidasta vuotoa; yksiosainen malli ei toistanut jaksoa eika hajontaa."""

    def __init__(self, pump, delta=0.2, tau=0.8, lag_us=40000, phi_us=0.0, noise=0.02, fill_us=0, cyc_sd=0.0,
                 delta_f=0.0, tau_f=0.08, gas_bar=None, c0=None, tau_sched=None, leak_n=None, turns=None, arm_bar=5.0):
        self.pump, self.delta, self.tau, self.lag = pump, delta, tau, lag_us
        # c0: 8 barin malli (EXPRESSO-UUTTO-8BAR, testit/uutto8_sovitus.py). Jousto C(p) = c0 + 1/(1 + p)^2 (vakio + kaasu/
        # p_abs^2), kappa = C(p) / C(2,5): isku = delta / kappa ja vuodon aikavakio = tau x kappa, eli delta ja tau ovat
        # 2,5 barin arvot ja pidon tarve p / (50 delta tau) (jousto supistuu pois). c0 = None: vanha malli ennallaan.
        # tau_sched: [(aika us, tau), ...] kuristimen kaanto kesken ajon (TILAUS-C). leak_n: vuoto ~ p^n (None = 1, laminaari);
        # tau on silloin 2,5 barin aikavakio ja pidon tarve p^n:n mukainen.
        self.c0, self.tau_sched, self.leak_n = c0, list(tau_sched or []), leak_n
        # turns: [(us, tau), ...] suhteessa hetkeen, jolloin paine ylittaa ensimmaisen kerran arm_bar (uuton nousu): sama
        # kaannon hetki vanhalle ja uudelle uuttopolulle ilman erillista ajoa uuton alun selvittamiseksi
        self.turns, self.arm_bar, self.turn_at = list(turns or []), arm_bar, []
        self.probe, self.probe_t = [], 0     # todellinen paine (hidas + nopea osa) 1 ms valein: (us, bar)
        # gas_bar: iskun painevaikutus kaasujoustosta (ilma jarjestelmassa): delta on iskukoko tassa paineessa, ja se skaalautuu
        # absoluuttisen paineen nelioon (isoterminen kaasu: dp = p_abs^2 / (p0 V0) dV). Laite ao-as 27.9.2026: G katkaisussa
        # (~1,4 bar) 9-10 bar/s = isku ~0,2 bar, pidossa 2,5 barissa isku +0,35-0,45 bar; suhde (3,5 / 2,4)^2 = 2,1
        self.gas_bar = gas_bar
        self.delta_f, self.tau_f, self.pf = delta_f, tau_f, 0.0
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

    def kappa(self, p):
        return (self.c0 + 1.0 / (1.0 + max(-0.99, p)) ** 2) / (self.c0 + 1.0 / 3.5 ** 2)

    def _leak(self, dt_us):
        if self.c0 is None:
            self.p *= math.exp(-dt_us / 1e6 / self.tau)
        else:
            left = dt_us
            while left > 0:           # tau riippuu paineesta: 2 ms askelin
                h = min(left, 2000)
                if self.leak_n is None:
                    self.p *= math.exp(-h / 1e6 / (self.tau * self.kappa(self.p)))
                elif self.p > 0.0:
                    self.p = max(0.0, self.p - h / 1e6 * (2.5 / self.tau) * (self.p / 2.5) ** self.leak_n / self.kappa(self.p))
                left -= h
        if self.delta_f: self.pf *= math.exp(-dt_us / 1e6 / self.tau_f)

    def advance(self, now):
        if self.turns and self.p >= self.arm_bar:
            self.turn_at = [(now + dt, tau) for dt, tau in self.turns]
            self.tau_sched += self.turn_at
            self.turns = []
        while self.tau_sched and self.tau_sched[0][0] <= now:
            self._apply(self.tau_sched[0][0])
            self.tau = self.tau_sched.pop(0)[1]
        if self.c0 is not None and now - self.probe_t >= 1000:
            self._apply(now)
            self.probe_t = now - now % 1000
            self.probe.append((now, self.p + self.pf))
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
            if self.gas_bar is not None: dp *= ((1.0 + max(-0.99, self.p)) / (1.0 + self.gas_bar)) ** 2
            if self.c0 is not None: dp /= self.kappa(self.p)
            self.p += dp
            self.pf += self.delta_f
        self._leak(t - self.last); self.last = t

    def bar(self, now):
        self.advance(now)
        ph = (now - self.phi) / (2 * HALF_US)
        rip = RIPPLE_AMP * math.sin(2 * math.pi * (ph - RIPPLE_SHIFT_US / (2 * HALF_US))) if (self.eff and self.k % 2 == 1) else 0.0
        return self.p + self.pf + rip + self.cn + random.gauss(0.0, self.noise)


class Adc:
    def __init__(self, plant):
        self.plant = plant

    def read_u16(self):
        return int((self.plant.bar(U.us) + 0.99 - F.PCAP_RAW_B) / F.PCAP_RAW_A)


class Max31865:
    """MAX31865-ajurin askelittainen luku (EXPRESSO-TEMPSTALE-JA-OLETUS): jokainen askel vie virtuaaliaikaa kuten SPI-siirrot
    50 kHz:lla laitteella (~0,5 ms/siirto; rtd_start 4, rtd_convert 2, rtd_result 1 pidempi). Arvio, ei mitattu: laitteen
    pisin askel EU_VV/EB_VV t_max_us:ssa."""
    COST_US = {'start': 2000, 'convert': 1000, 'result': 700}

    def __init__(self):
        self.steps = []           # (us, askel)

    def _spend(self, k):
        self.steps.append((U.us, k))
        U.us += self.COST_US[k]

    def rtd_start(self): self._spend('start')
    def rtd_convert(self): self._spend('convert')
    def rtd_result(self): self._spend('result'); return 0
    def temperature_from_rtd(self, rtd): return 93.0


def temp_sensor():
    import classes
    ts = classes.TemperatureSensor.__new__(classes.TemperatureSensor)
    ts.temperature_sensor, ts.temps, ts.temps_i = Max31865(), [0] * 7, 0
    ts.step_reset()
    return ts


class Ratio:
    def set_pump_on(self): pass
    def set_pump_off(self): pass
    def get_ratio(self): return 0.0


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
        # Kattilan lampotila (EXPRESSO-TEMPSTALE-JA-OLETUS): askelittainen luku classes.TemperatureSensorilla ja
        # anturimallilla; lammittimen jokaisen paallekytkennan hetkella lukeman ika (ms) heat_age:en kuten rele-vahti sen nakee
        self.temperature_sensor = temp_sensor()
        self.relay_guard = types.SimpleNamespace(utime=U)
        self.boiler_temperature, self.boiler_temperature_ms, self.heat_age = 93.0, None, []
        self.heater.hook = lambda x: self.heat_age.append(
            None if self.boiler_temperature_ms is None else U.us // 1000 - self.boiler_temperature_ms) if x else None

    def get_relays(self): return self.pump, self.solenoid, self.heater
    def get_switch_brew(self): return self.brew
    def get_pre_infusion_pressure(self): return self.target
    def get_pre_infusion_time(self): return self.hold_s
    def set_mode(self, m): self.mode = m
    def set_setting_changed(self): self.saved += 1
    def get_pressure(self): return self.plant.bar(U.us)
    def get_weight(self): return None
    def get_flow(self): return None
    # run_shot (EXPRESSO-UUTTO-8BAR): uutto 8 bar, vanha polku lukee paineen PressureSensor.sample_average:lla
    brew_p, brew_method, pre_infusion_method, learned_ff_brew, weight_a, weight_b = 8.0, 0, 1, 0.5, 0.0, 0.0
    def get_brew_pressure(self): return self.brew_p
    def get_pre_infusion_mode(self): return True
    def get_flow_mode(self): return False
    def set_pump_ratio(self, r): self.pump_ratio = r
    def get_boiler_temperature(self):
        self.boiler_temperature_ms = U.us // 1000
        return 93.0
    def step_boiler_temperature(self, now_ms):
        import classes
        return classes.BrewData.step_boiler_temperature(self, now_ms)
    def get_soft_pressure_release_arming_pressure(self): return 99.0
    def get_pressure_soft_release_mode(self): return False
    def get_pressure_average(self, utime):
        self.pressure = self.pressure_sensor.sample_average(utime)
        return self.pressure


class Asyncio:
    def __init__(self, stall_p=0.0, stall_ms=(5, 15), stall_hz=0.0):
        self.stall_p, self.stall_ms = stall_p, stall_ms
        # stall_hz (uudet tapaukset 16-): varaus aikaan eika vuoroon sidottuna, jotta vanha uuttosilmukka (vuoro ~0,3 ms
        # valein) ja pre_infusion_phased (vuoro vain tauoissa) saavat saman maaran varauksia sekunnissa
        self.stall_hz, self.last = stall_hz, None

    async def sleep_ms(self, ms):
        if self.stall_hz:
            if self.last is None: self.last = U.us
            if random.random() < 1.0 - math.exp(-self.stall_hz * (U.us - self.last) / 1e6):
                U.us += random.randint(*self.stall_ms) * 1000
            U.us += ms * 1000 if ms > 0 else 150
            self.last = U.us
            return
        U.us += ms * 1000 if ms > 0 else 150
        if self.stall_p and random.random() < self.stall_p:
            U.us += random.randint(*self.stall_ms) * 1000   # toinen tehtava (BLE, vaaka) varaa vuoron


def run(bd, until_s=None, stall_p=0.0, seed=1, stall_ms=(5, 15)):
    random.seed(seed)
    GC.start()
    start = U.us
    # Aikaraja aina: ajo, jonka pito ei ala, ei paaty koskaan (26.9.2026: kaksi testiajoa pyori ~80 min).
    # 30 s virtuaaliaikaa ylittaa jokaisen tapauksen pidon; raja -> reason=stop -> tapaus kaatuu.
    lim = 30.0 if until_s is None else until_s
    keep = lambda: U.us - start < lim * 1e6
    out = io.StringIO()
    with redirect_stdout(out):
        asyncio.run(F.pre_infusion_phased(bd, U, Asyncio(stall_p, stall_ms), Ratio(), keep))
    return out.getvalue()


class Stamp(io.StringIO):
    """stdout, joka kirjaa jokaisen rivin virtuaaliajan (us) kirjoitushetkella: vanhan ja uuden uuttopolun rivit samalle
    aika-akselille kuin Plant.probe."""
    def __init__(self):
        super().__init__()
        self.at, self.buf = [], ''

    def write(self, x):
        if not self.buf: self.at.append(U.us)
        self.buf += x
        if self.buf.endswith('\n'): self.buf = ''
        return super().write(x)


def run_brew(bd, until_s, bim=1, seed=1, stall_hz=0.0, stall_ms=(5, 15), gc=False, iq_cost=0):
    """run_shot (tshot-polku) virtuaalikellolla: pim:1-esiuutto ja bim:<bim>-uutto, kunnes aikaraja. Palauttaa (teksti,
    [(us, rivi)])."""
    import classes
    random.seed(seed)
    ps = classes.PressureSensor.__new__(classes.PressureSensor)
    ps.pressure_sensor, ps.gain, ps.offset, ps.window_peak = bd.pressure_sensor.pressure_sensor, 1.0, -0.99, 0.0
    bd.pressure_sensor = ps
    bd.brew_method = bim
    if gc: GC.enable()
    GC.start()
    IQ_CLOSE_US[0] = iq_cost
    start = U.us
    keep = lambda: U.us - start < until_s * 1e6
    out = Stamp()
    try:
        with redirect_stdout(out):
            asyncio.run(F.run_shot(bd, U, Asyncio(stall_ms=stall_ms, stall_hz=stall_hz), Ratio(), keep, 'TS', False))
    finally:
        IQ_CLOSE_US[0] = 0
        bd.gc_auto, bd.gc_auto_t = GC.auto, list(GC.auto_t)
        GC.disable()
    text = out.getvalue()
    return text, list(zip(out.at, text.splitlines()))


def field(text, prefix, key):
    # Ensimmainen prefiksilla alkava rivi, jolla avain on: EU_END on jaettu riveihin EU_END ja EU_END2 (<= 255 merkkia)
    for line in text.splitlines():
        if line.startswith(prefix):
            m = re.search(r'\b%s=(\S+)' % key, line)
            if m: return m.group(1)
    return None


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


# ---- uutto 8 bar (tapaukset 16-21, EXPRESSO-UUTTO-8BAR) ----
# Malli testit/uutto8_sovitus.py: jousto c0 + 1/(1 + p)^2, vuoto ~ p^0,8, viive iskun puolijakson jalkeen 10 ms (= ~40 ms
# kaskysta, TILAUS-I; 8 barin viivetta ei sovitettu), taytto 0,3 s kuten tapaus 15.
M8 = dict(c0=0.03, leak_n=0.8, lag_us=10000, fill_us=300000)
N8_PHASE = 6            # kohinattomat vaiheet
N8_NOISE = 8            # kohinaiset siemenet


def kappa8(p):
    return (M8['c0'] + 1.0 / (1.0 + p) ** 2) / (M8['c0'] + 1.0 / 3.5 ** 2)


def tau_for_need8(s25, need):
    """tau25, jolla pidon tarve 8 barissa on need (tarve8 = tarve25 x (8/2,5)^0,8, tarve25 = 2,5 / (50 s25 tau25))."""
    return (8.0 / 2.5) ** M8['leak_n'] * 2.5 / (50.0 * s25 * need)


TURN8 = {n: tau_for_need8(0.27, n) for n in (0.3, 0.6, 0.2)}
STATES8 = {'25b': (0.238, 0.77), '26b': (0.129, 3.74), 'kaanto': (0.27, TURN8[0.3])}


def brew_bd(st, seed, noisy, turns=None):
    s25, tau25 = STATES8[st]
    bd = BrewData(hold_s=6.0, phi_us=(3100.0 * seed) % 20000, delta=s25, tau=tau25, noise=0.02 if noisy else 0.0,
                  cyc_sd=0.25 if noisy else 0.0, turns=turns, **M8)
    # Edellisen ajon esiuuton tiedot (kuten laitteella hyvaksynnan jalkeen): tarve = mallin tarve 2,5 barissa
    bd.learned_ff_pre, bd.eu_g_pre, bd.eu_coast_s, bd.eu_tau_pre = 2.5 / (50.0 * s25 * tau25), 9.0, 0.1, 1.5
    return bd


def p100(probe):
    """Plant.probe (1 ms) -> 100 ms liukuva keskiarvo 10 ms valein: [(us, bar)]."""
    import bisect
    ts, ps = [t for t, _ in probe], [p for _, p in probe]
    cum = [0.0]
    for p in ps: cum.append(cum[-1] + p)
    out, t = [], ts[0] + 100000
    while t <= ts[-1]:
        a, b = bisect.bisect_left(ts, t - 100000), bisect.bisect_right(ts, t)
        if b > a: out.append((t, (cum[b] - cum[a]) / (b - a)))
        t += 10000
    return out


def brew_metrics(bd, txt, stamps, bim, target=8.0):
    """Siirtyman suureet todellisesta paineesta (100 ms): ylitys uuton alusta pidon 1. s:n loppuun, pienin paine pidon
    1. s:ssa, pidon 2-5 s keskiarvo (poikkeamina tavoitteesta), uuton alusta pitoon (s); uudelta polulta myos kello."""
    pr = p100(bd.plant.probe)
    tb = next(t for t, l in stamps if (l.startswith('EU_END ') if bim else l.startswith('TS ')))
    th = next((t for t, l in stamps if l.startswith('EB_HOLD')), None) if bim else \
        next((t for t, p in pr if t > tb and p >= target - 0.1), None)
    m = dict(maxline=max(len(l) for l in txt.splitlines()), sd_hold=9e9, sd_pre=9e9, sk10_4=0, sk20_4=0)
    if th is None:
        tail = [p for t, p in pr if t > pr[-1][0] - 3e6]
        m.update(over=max(p for t, p in pr if t >= tb) - target, drop=-9.0, m25=sum(tail) / len(tail) - target, t_hold=99.0)
        return m
    m.update(over=max(p for t, p in pr if tb <= t <= th + 1e6) - target,
             drop=min(p for t, p in pr if th <= t <= th + 1e6) - target,
             m25=sum(p for t, p in pr if th + 2e6 <= t < th + 5e6) / max(1, sum(1 for t, p in pr if th + 2e6 <= t < th + 5e6)) - target,
             t_hold=(th - tb) / 1e6)
    if bim:
        hold_ms = int(field(txt, 'EB_HOLD', 't_ms'))
        rows = [(int(l.split()[1]), float(re.search(r'sd_us=(\S+)', l).group(1)), int(re.search(r'sk10=(\d+)', l).group(1)),
                 int(re.search(r'sk20=(\d+)', l).group(1))) for l in txt.splitlines()
                if l.startswith('EU ') and l.split()[6] in ('3', '4')]
        h = [r for r in rows if r[0] >= hold_ms]
        m.update(sd_hold=h[0][1], sd_pre=num(txt, 'EU_END2', 'sd_us'), sk10_4=h[-1][2] - h[0][2], sk20_4=h[-1][3] - h[0][3])
    return m


def turn_metrics(pr, tt, target=8.0, band=0.3):
    """Kuristimen kaanto hetkella tt: aika kaistalle target +- band niin, etta paine pysyy siella 0,5 s (s; 9,9 = ei
    palannut), ja keskiarvo 1,5-3 s kaannosta - target."""
    ts = [t for t, _ in pr if t >= tt]
    back = next(((t - tt) / 1e6 for t in ts if all(abs(p - target) <= band for u, p in pr if t <= u <= t + 500000)), 9.9)
    seg = [p for t, p in pr if tt + 1.5e6 <= t < tt + 3e6]
    return back, (sum(seg) / len(seg) - target) if seg else 9.9


def stat_ok(xs, hi, lo, share):
    mean = sum(xs) / len(xs)
    n_out = sum(1 for x in xs if x > hi or (lo is not None and x < lo))
    return mean <= hi and (lo is None or mean >= lo) and n_out <= share * len(xs)


class _Settings:
    """save_settings/load_settings-testin brew_data: get_* palauttaa 1.0, set_* ei tee mitaan."""
    def __init__(self):
        self.learned_ff_pre, self.eu_g_pre, self.eu_tau_pre, self.eu_coast_s, self.eu_coast_fast_s = 0.3, 0.0, 0.0, 0.3, 0.2
        self.eb_ff, self.eb_x, self.eb_g, self.eb_tau, self.eb_coast_s = 0.0, 0.0, 0.0, 0.0, F.EB_COAST_S0

    def __getattr__(self, name):
        if name.startswith('get_'): return lambda *a: 1.0
        if name.startswith('set_'): return lambda *a: None
        raise AttributeError(name)


def settings_roundtrip():
    import json
    import tempfile
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
        os.chdir(d)
        try:
            a = _Settings()
            a.eb_ff, a.eb_x, a.eb_g, a.eb_tau, a.eb_coast_s = 0.61, 2.4, 23.5, 0.62, 0.137
            F.save_settings(a, json)
            b = _Settings()
            F.load_settings(json, b)
            ok = (b.eb_ff, b.eb_x, b.eb_g, b.eb_tau, b.eb_coast_s) == (0.61, 2.4, 23.5, 0.62, 0.137)
            data = json.load(open('settings.txt'))
            for k in ('eb_ff', 'eb_x', 'eb_g', 'eb_tau', 'eb_coast_s'): del data[k]
            json.dump(data, open('settings.txt', 'w'))
            c = _Settings()
            F.load_settings(json, c)
            ok = ok and (c.eb_ff, c.eb_x, c.eb_g, c.eb_tau, c.eb_coast_s) == (0.0, 0.0, 0.0, 0.0, F.EB_COAST_S0)
        finally:
            os.chdir(cwd)
    return ok


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

    # 2 jälkinousun oppiminen: toinen ajo samalla laitteella. Nopea ja hidas nousu opitaan erikseen
    # (EXPRESSO-ESIUUTTO-UUTTOASENTO): tarkistetaan katkaisun nousunopeuden luokka
    fast = num(out, 'EU_CUT', 'rate') >= F.EU_RATE_FAST
    attr, c0 = ('eu_coast_fast_s', F.EU_COAST_FAST_S0) if fast else ('eu_coast_s', F.EU_COAST_S0)
    c1 = getattr(bd, attr)
    bd.plant.p, bd.plant.pending = 0.0, []    # ajojen valissa paine purkautuu kuristimen lapi
    out2 = run(bd, seed=2)
    open('/tmp/esiuutto_smoke_2.log', 'w').write(out2)
    check('2 jälkinousu opittu ja rajoissa (%s)' % ('nopea' if fast else 'hidas'),
          F.EU_COAST_MIN <= getattr(bd, attr) <= F.EU_COAST_MAX and c1 != c0, '%.3f -> %.3f' % (c1, getattr(bd, attr)))
    check('2 toinen ajo: yliampuma ≤ yksi isku (0,2 bar)', num(out2, 'EU_END', 'over') <= 0.2, field(out2, 'EU_END', 'over'))

    # 3 pysähdykset (toinen tehtävä varaa vuoron 5-15 ms). vv=0 (euv:0, vanha vuorosaanto): myohastymisvahti jattaa tauon
    # tekematta. vv=1 (EXPRESSO-ESIUUTTO-VUORONVARAUS): vaiheessa 2 vuoro vain releen ollessa pois ja seuraavan jakson
    # ollessa tauko, joten vuoron varaus ei myohastyta yhtaan taukoa; vahti jaa varmistukseksi (keskeytykset).
    for vv in (0, 1):
        bd3 = BrewData(phi_us=2100.0)
        bd3.eu_vv = vv
        out3 = run(bd3, stall_p=0.005, seed=3)
        open('/tmp/esiuutto_smoke_3_vv%d.log' % vv, 'w').write(out3)
        c3 = '3 pysähdykset vv=%d' % vv
        check('%s: ajo loppuun' % c3, field(out3, 'EU_END', 'reason') == 'done', field(out3, 'EU_END', 'reason'))
        # Vain kellon lukituttua alkaneet tauot (firmwaren ehto 2,5 sd < EU_PHASE_OK_US -> 10 ms tauot): sita ennen 20 ms
        # tauko poistaa iskun vaiheesta riippumatta, eika ajon lopun katkaisu (rele ei palaa) ole tauko. Kun kello jatkui
        # edellisesta tapauksesta, HEADin vaihe vaisti molemmat sattumalta (EXPRESSO-SMOKE-TILASTO).
        t_lock = next((int(l.split()[1]) * 1000 for l in out3.splitlines() if l.startswith('EU ')
                       and 2.5 * float(re.search(r'sd_us=(\S+)', l).group(1)) < F.EU_PHASE_OK_US), None)
        offs10 = [o for o, t, n in zip(bd3.plant.pause_offs, bd3.plant.pause_t, bd3.plant.pause_lens)
                  if n is not None and t_lock is not None and t >= t_lock]
        bad = [o for o in offs10 if o >= HALF_US]
        check('%s: jokainen tehty 10 ms tauko alkaa passiivisella puolijaksolla' % c3, not bad and offs10,
              '%d/%d väärin, late=%s miss=%s' % (len(bad), len(offs10), field(out3, 'EU_END', 'late'),
                                               field(out3, 'EU_END', 'miss')))
        if vv:
            check('%s: ei myöhästyneitä taukoja (late = 0)' % c3, int(num(out3, 'EU_END', 'late')) == 0,
                  field(out3, 'EU_END', 'late'))
        else:
            check('%s: vahti toimi (late > 0)' % c3, int(num(out3, 'EU_END', 'late')) > 0, field(out3, 'EU_END', 'late'))
        check('%s: pito 2,5 ± 0,08 bar' % c3, abs(num(out3, 'EU_END', 'hold_mean') - 2.5) <= 0.08,
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

    # 13 uuttoasento (EXPRESSO-ESIUUTTO-UUTTOASENTO, laite af/ag 26.9.2026: kuristin lahella uuttoa, G 13-18, pidon tarve
    # 0,14-0,19). Kahden osan malli (hidas 0,25 / 0,8 s, nopea 0,6 / 0,08 s, viive 20 ms) sovitettiin af:hen vanhalla
    # saatimella: g 18,6, pidon sd 0,59, 300 ms jakso (p:n autokorrelaatio 3 x 100 ms 0,54, laite 0,62), iskuosuus 0,20.
    # Ketju: 1. ajo ae:n opituilla arvoilla (hidas tila ennen kaantoa, kuten af), 2. ajo edellisen tiedolla. Vanha saadin:
    # jakso 0,51-0,53, pidon p5 sd 0,48-0,49, opittu tarve 0,10-0,12 vs. iskuosuus 0,19 (u:n keskiarvo).
    def run13(seed, carry, cf):
        bd13 = BrewData(hold_s=6.0, phi_us=(3100.0 * seed) % 20000, delta=0.25, tau=0.8, delta_f=0.6, tau_f=0.08,
                        lag_us=20000, fill_us=600000, noise=0.02, cyc_sd=0.25)
        bd13.learned_ff_pre, bd13.eu_g_pre, bd13.eu_coast_s, bd13.eu_tau_pre = carry
        if cf is not None: bd13.eu_coast_fast_s = cf
        out13 = run(bd13, stall_p=0.008, seed=seed)
        open('/tmp/esiuutto_smoke_13_%d.log' % seed, 'w').write(out13)
        hold13 = num(out13, 'EU_HOLD', 't_ms')
        rows = [(int(l.split()[1]) - hold13, float(l.split()[2]), float(re.search(r'p5=(\S+)', l).group(1)),
                 int(re.search(r'rm=(\d+)', l).group(1))) for l in out13.splitlines() if l.startswith('EU ')]
        h = [r for r in rows if 500 <= r[0] < 5000]
        ps = [r[1] for r in h]
        m = sum(ps) / len(ps)
        # 300 ms rajasyklin voimakkuus: p:n autokovarianssi 3 x 100 ms viiveella. Normalisoitu autokorrelaatio mittasi
        # kohinaa, kun vuoronvarauksen korjaus puolitti pidon hajonnan (sd 0,37 -> 0,17, korrelaatio 3/8 yli 0,3:n);
        # kayttajan paatos 27.9.2026: raja = entisten rajojen tulo 0,3 x 0,45^2 (laite af 0,62 x 0,61^2 = 0,23)
        cov3 = sum((ps[i] - m) * (ps[i + 3] - m) for i in range(len(ps) - 3)) / (len(ps) - 3)
        p5 = [r[2] for r in h]
        m5 = sum(p5) / len(p5)
        h25 = [r[2] for r in rows if 2000 <= r[0] < 5000]
        # Iskuosuus poistolaskurista pidon 2 s:sta loppuun, sama ikkuna kuin oppimisessa (EU_LEARN_SKIP_MS)
        l2 = [r for r in rows if r[0] >= F.EU_LEARN_SKIP_MS]
        sfrac = 1 - (l2[-1][3] - l2[0][3]) / ((l2[-1][0] - l2[0][0]) / 20.0)
        return dict(cov3=cov3, sd5=math.sqrt(sum((x - m5) ** 2 for x in p5) / len(p5)), h25=sum(h25) / len(h25) - 2.5,
                    learn=bd13.learned_ff_pre - sfrac), \
            (bd13.learned_ff_pre, bd13.eu_g_pre, bd13.eu_coast_s, bd13.eu_tau_pre), getattr(bd13, 'eu_coast_fast_s', None)
    r13 = {1: [], 2: []}
    for seed in range(130, 138):
        carry, cf = (0.08, 7.73, 0.061, 4.55), None
        for r in (1, 2):
            res, carry, cf = run13(seed + 50 * (r - 1), carry, cf)
            r13[r].append(res)
    for r in (1, 2):
        rs = r13[r]
        stat(check, '13 uuttoasento ajo %d: ei 300 ms rajasykliä (p:n autokovarianssi 3 × 100 ms ≤ 0,3 × 0,45² bar²)' % r,
             [x['cov3'] for x in rs], 0.3 * 0.45 ** 2, share=NOISE_SHARE)
        stat(check, '13 uuttoasento ajo %d: pidon p5 sd ≤ 0,45 bar' % r, [x['sd5'] for x in rs], 0.45, share=NOISE_SHARE)
        stat(check, '13 uuttoasento ajo %d: pidon 2-5 s p5 ka 2,5 ± 0,1' % r, [x['h25'] for x in rs], 0.1, lo=-0.1)
        check('13 uuttoasento ajo %d: opittu tarve = iskuosuus (±0,03)' % r, all(abs(x['learn']) <= 0.03 for x in rs),
              'max |%.3f|' % max(abs(x['learn']) for x in rs))

    # 14 vuoronvaraus (EXPRESSO-ESIUUTTO-VUORONVARAUS, laite ah-am 26.9.2026): silmukka pysahtyi 13-28 ms 0,4-1,2 s valein,
    # ja kun rele oli paalla, tauko jai tekematta (late) ja pidon p5 nousi 3,2-3,6 bariin. Laite an (euv:0): syy on
    # automaattinen roskienkeruu. Uuttoasennon malli (tapaus 13), keruu (Gc) ja toisen tehtavan varaukset (0,8 % vuoroista,
    # 13-28 ms), 8 siementa x 2 ajoa.
    # vv=0 (euv:0) on vanha: rele paalla vuoron ja keruun ajan. vv=1: vuoro ja keruu vain releen ollessa pois.
    def run14(seed, carry, cf, vv):
        bd14 = BrewData(hold_s=6.0, phi_us=(3100.0 * seed) % 20000, delta=0.25, tau=0.8, delta_f=0.6, tau_f=0.08,
                        lag_us=20000, fill_us=600000, noise=0.02, cyc_sd=0.25)
        bd14.learned_ff_pre, bd14.eu_g_pre, bd14.eu_coast_s, bd14.eu_tau_pre = carry
        if cf is not None: bd14.eu_coast_fast_s = cf
        bd14.eu_vv = vv
        GC.enable()
        IQ_CLOSE_US[0] = 9000
        out14 = run(bd14, stall_p=0.008, seed=seed, stall_ms=(13, 28))
        IQ_CLOSE_US[0] = 0
        auto = GC.auto
        GC.disable()
        open('/tmp/esiuutto_smoke_14_%d_vv%d.log' % (seed, vv), 'w').write(out14)
        r14_len[0] = max(r14_len[0], max(len(l) for l in out14.splitlines()))
        hold14 = num(out14, 'EU_HOLD', 't_ms')
        rows = [(int(l.split()[1]) - hold14, float(re.search(r'p5=(\S+)', l).group(1))) for l in out14.splitlines()
                if l.startswith('EU ')]
        h = [r[1] for r in rows if F.EU_OVER_MS <= r[0] < 5000]
        m = sum(h) / len(h)
        h25 = [r[1] for r in rows if 2000 <= r[0] < 5000]
        return dict(late=int(num(out14, 'EU_END', 'late')), peak=max(h) - 2.5, sd=math.sqrt(sum((x - m) ** 2 for x in h) / len(h)),
                    h25=sum(h25) / len(h25) - 2.5, auto=auto, gc=int(num(out14, 'EU_VV', 'gc_n'))), \
            (bd14.learned_ff_pre, bd14.eu_g_pre, bd14.eu_coast_s, bd14.eu_tau_pre), getattr(bd14, 'eu_coast_fast_s', None)
    r14 = {(vv, r): [] for vv in (0, 1) for r in (1, 2)}
    r14_len = [0]
    for vv in (0, 1):
        for seed in range(140, 148):
            carry, cf = (0.08, 7.73, 0.061, 4.55), None
            for r in (1, 2):
                res, carry, cf = run14(seed + 50 * (r - 1), carry, cf, vv)
                r14[(vv, r)].append(res)
    for r in (1, 2):
        rs0, rs1 = r14[(0, r)], r14[(1, r)]
        pk0 = sum(x['peak'] for x in rs0) / len(rs0)
        check('14 vuoronvaraus ajo %d: vanha (vv=0) toistaa vian (late > 0, pidon piikki ka ≥ +0,7)' % r,
              all(x['late'] > 0 for x in rs0) and pk0 >= 0.7,
              'late %s, piikki ka %+.2f' % ([x['late'] for x in rs0], pk0))
        check('14 vuoronvaraus ajo %d: vv=1 ei myöhästyneitä taukoja eikä automaattista keruuta' % r,
              all(x['late'] == 0 and x['auto'] == 0 for x in rs1),
              'late %s, auto %s, hallittu %s' % ([x['late'] for x in rs1], [x['auto'] for x in rs1], [x['gc'] for x in rs1]))
        stat(check, '14 vuoronvaraus ajo %d: vv=1 pidon piikki (p5 max 1 s:sta) ≤ +0,7 bar' % r, [x['peak'] for x in rs1],
             0.7, share=NOISE_SHARE)
        stat(check, '14 vuoronvaraus ajo %d: vv=1 pidon p5 sd ≤ 0,3 bar' % r, [x['sd'] for x in rs1], 0.3, share=NOISE_SHARE)
        stat(check, '14 vuoronvaraus ajo %d: vv=1 pidon 2-5 s p5 ka 2,5 ± 0,1' % r, [x['h25'] for x in rs1], 0.1, lo=-0.1)
    check('14 vuoronvaraus: rivit ≤ 255 merkkiä (USB-CDC:n jono)', r14_len[0] <= 255, '%d' % r14_len[0])

    # 15 rampin loppu (EXPRESSO-ESIUUTTO-RAMPIN-LOPPU, laite ao-as 27.9.2026: kylma, lahes kiinni oleva kuristin, tarve 0,05,
    # G katkaisussa 9-10, isku pidossa +0,35-0,45 bar). Jalkinousu vei paineen rampin ylle (huippu 2,55-2,93), paine putosi
    # rampille 2,0-2,3 bariin, ja rampin myotakytkenta + D antoivat 2-3 iskun ryopyn: ylitys 0,36-1,32, huippu jalkinousun
    # jalkeen +0,32-1,18, ao:n pito alkoi 3,45:ssa. Malli: kaasujousto (isku 0,45 bar 2,5 barissa, ~0,2 katkaisussa), vuoto
    # tau 2,5 s, viive 10 ms, taytto 0,3 s; satunnaishaku laitteen keskiarvoihin, vanha koodi: ylitys 0,53 / 0,65 (laite 0,69),
    # huippu jalkinousun jalkeen 0,49 / 0,58 (0,61), pito alkoi ka 2,72. 1. ajo ao-as:n opituilla arvoilla, 2. ajo edellisesta.
    def run15(seed, carry, cf):
        bd15 = BrewData(hold_s=6.0, phi_us=(3100.0 * seed) % 20000, delta=0.45, tau=2.5, lag_us=10000, fill_us=300000,
                        gas_bar=2.5, noise=0.02, cyc_sd=0.25)
        bd15.learned_ff_pre, bd15.eu_g_pre, bd15.eu_coast_s, bd15.eu_tau_pre = carry
        bd15.eu_coast_fast_s = cf
        out15 = run(bd15, stall_p=0.008, seed=seed)
        open('/tmp/esiuutto_smoke_15_%d.log' % seed, 'w').write(out15)
        cut15, hold15 = num(out15, 'EU_CUT', 't_ms'), num(out15, 'EU_HOLD', 't_ms')
        rows = [(int(l.split()[1]), float(re.search(r'p5=(\S+)', l).group(1))) for l in out15.splitlines() if l.startswith('EU ')]
        # Rampin lopun huippu: jalkinousun ikkunan (EU_COAST_MS) jalkeen pidon 1. sekunnin loppuun
        tail = [p for t, p in rows if cut15 + F.EU_COAST_MS <= t <= hold15 + F.EU_OVER_MS]
        wait = num(out15, 'EU_HOLD', 'wait_ms')
        return dict(over=num(out15, 'EU_END', 'over'), tail=(max(tail) if tail else 9.0) - 2.5, hold_p=num(out15, 'EU_HOLD', 'p'),
                    wait=0.0 if wait != wait else wait), \
            (bd15.learned_ff_pre, bd15.eu_g_pre, bd15.eu_coast_s, bd15.eu_tau_pre), bd15.eu_coast_fast_s
    r15 = {1: [], 2: []}
    for seed in range(150, 150 + N_PHASE):
        carry, cf = (0.05, 9.8, 0.401, 5.2), 0.14
        for r in (1, 2):
            res, carry, cf = run15(seed + 50 * (r - 1), carry, cf)
            r15[r].append(res)
    for r in (1, 2):
        rs = r15[r]
        # Menetelmaohje: yliampuma ei aloita laskuria. Varalla EU_HOLD_WAIT_MS (kuristin ilman vuotoa)
        check('15 rampin loppu ajo %d: pito alkaa tavoitteessa (p5 2,5 ± %s)' % (r, ('%.1f' % F.EU_HOLD_TOL_BAR).replace('.', ',')),
              all(abs(x['hold_p'] - 2.5) <= F.EU_HOLD_TOL_BAR + 1e-9 or x['wait'] >= F.EU_HOLD_WAIT_MS for x in rs),
              'p5 %.2f…%.2f' % (min(x['hold_p'] for x in rs), max(x['hold_p'] for x in rs)))
        stat(check, '15 rampin loppu ajo %d: yliampuma ≤ yksi isku (0,45 bar)' % r, [x['over'] for x in rs], 0.45,
             share=NOISE_SHARE)
        stat(check, '15 rampin loppu ajo %d: huippu jälkinousun jälkeen ≤ yksi isku (0,45 bar)' % r, [x['tail'] for x in rs],
             0.45, share=NOISE_SHARE)

    # ======================================================================================================================
    # 16-21 uutto 8 bar vaiheseurannalla (EXPRESSO-UUTTO-8BAR, TILAUS-K vaiheet 3-4, bim:1) ja vanha uuttosilmukka (bim:0).
    # Malli testit/uutto8_sovitus.py: jousto c0 + kaasu, vuoto ~ p^0,8 (M8). Tilat sovitettu laitteen ajoista: 25b (esiuutto-
    # 20260925-b: isku 2,5 barissa 0,238, tau25 0,77 s, tarve 8 barissa 0,69) ja 26b (esiuutto-20260926-b: 0,129 / 3,74 s /
    # 0,26). Vertailu mallin todellisesta paineesta (Plant.probe, 100 ms keskiarvo = p5 ilman mittauskohinaa), jotta
    # vanha ja uusi polku mitataan samalla mittarilla: pito alkaa uudella EB_HOLDista, vanhalla ensimmaisesta hetkesta,
    # jolloin paine >= tavoite - 0,1.
    t16, old_fail = {}, {'over': [], 'drop': [], 'm25': []}
    for st in ('25b', '26b'):
        s25, tau25 = STATES8[st]
        stroke = s25 / kappa8(8.0)
        for noisy in (False, True):
            seeds = range(160, 160 + N8_PHASE) if not noisy else range(260, 260 + N8_NOISE)
            for bim in (1, 0):
                rs = []
                for seed in seeds:
                    bd = brew_bd(st, seed, noisy)
                    txt, stamps = run_brew(bd, 16.0, bim=bim, seed=seed, stall_hz=5.0 if noisy else 0.0)
                    if seed == seeds[0]: open('/tmp/esiuutto_smoke_16_%s_%d_bim%d.log' % (st, noisy, bim), 'w').write(txt)
                    rs.append(brew_metrics(bd, txt, stamps, bim))
                t16[(st, noisy, bim)] = rs
            new, old = t16[(st, noisy, 1)], t16[(st, noisy, 0)]
            lab = '16 siirtymä %s %s' % (st, 'kohina' if noisy else 'kohinaton')
            sh = NOISE_SHARE if noisy else STAT_SHARE
            for key, name, hi, lo in (('over', 'vaiheen 3 ylitys < yksi 8 barin isku (%.2f bar)' % stroke, stroke, None),
                                      ('drop', 'ei pudotusta pidon 1. s:ssa (p ≥ tavoite − 0,5)', None, -0.5),
                                      ('m25', 'pidon 2–5 s keskiarvo 8 ± 0,15', 0.15, -0.15)):
                xs, xo = [m[key] for m in new], [m[key] for m in old]
                stat(check, '%s: %s' % (lab, name), xs, 99.0 if hi is None else hi, lo=lo, share=sh)
                print('     vanha (bim:0): ka %+.3f, min %+.3f, max %+.3f; pitoon uusi %.2f s, vanha %.2f s' % (
                    sum(xo) / len(xo), min(xo), max(xo), sum(m['t_hold'] for m in new) / len(new),
                    sum(m['t_hold'] for m in old) / len(old)))
            for k, hi, lo in (('over', stroke, None), ('drop', None, -0.5), ('m25', 0.15, -0.15)):
                if not stat_ok([m[k] for m in old], 99.0 if hi is None else hi, lo, sh): old_fail[k].append(lab[3:])

    # Tarkistus tunnistaa vian: vanha uuttosilmukka kaatuu ylitykseen (26b: isku 0,34 bar, vanha +0,74...+1,04) ja
    # pudotukseen (25b kohina, vanha ka -0,57). Pidon keskiarvon vanha polku pitaa ~rajalla (ka -0,15...0), joten sen
    # kaatumista ei vaadita (tulostetaan).
    for k in ('over', 'drop'):
        check('16 vanha uuttosilmukka (bim:0) kaatuu tarkistukseen %s' % k, bool(old_fail[k]), ', '.join(old_fail[k]))
    print('     pidon keskiarvo: vanha kaatuu tiloissa %s' % (', '.join(old_fail['m25']) or '-'))

    # 17 kuristimen kaanto kesken pidon (TILAUS-C): tarve 8 barissa 0,3 -> 0,6 -> 0,2 askeleena 4 ja 7 s uuton nousun
    # jalkeen (Plant.turns, sama hetki molemmille poluille). Paine palaa kaistalle 8 +- 0,3 ~1 s:ssa eika lukkiudu:
    # keskiarvo 1,5-3 s kaannosta 8 +- 0,15. Integraali ja ff sallivat tarpeen koko valilla 0...1.
    r17 = {1: [], 0: []}
    for bim in (1, 0):
        for seed in range(170, 170 + N8_NOISE):
            bd = brew_bd('kaanto', seed, True, turns=[(4000000, TURN8[0.6]), (7000000, TURN8[0.2])])
            txt, stamps = run_brew(bd, 19.0, bim=bim, seed=seed, stall_hz=5.0)
            if seed == 170: open('/tmp/esiuutto_smoke_17_bim%d.log' % bim, 'w').write(txt)
            pr = p100(bd.plant.probe)
            r17[bim].append([turn_metrics(pr, t) for t, _ in bd.plant.turn_at])
    old17 = []
    for i, name in ((0, '0,3 → 0,6'), (1, '0,6 → 0,2')):
        xs, xo = [r[i][0] for r in r17[1]], [r[i][0] for r in r17[0]]
        stat(check, '17 kuristimen kääntö %s: kaistalle 8 ± 0,3 ≤ 1,0 s' % name, xs, 1.0, share=NOISE_SHARE, fmt='%.2f')
        print('     vanha (bim:0): ka %.2f s, max %.2f s' % (sum(xo) / len(xo), max(xo)))
        check('17 kuristimen kääntö %s: vanha (bim:0) ei palaa kaistalle 1,0 s:ssa' % name,
              not stat_ok(xo, 1.0, None, NOISE_SHARE), 'ka %.2f s' % (sum(xo) / len(xo)))
        xs, xo = [r[i][1] for r in r17[1]], [r[i][1] for r in r17[0]]
        stat(check, '17 kuristimen kääntö %s: ei lukkiutumista (ka 1,5–3 s käännöstä 8 ± 0,15)' % name, xs, 0.15, lo=-0.15,
             share=NOISE_SHARE)
        print('     vanha (bim:0): ka %+.3f, min %+.3f, max %+.3f' % (sum(xo) / len(xo), min(xo), max(xo)))
        old17.append(not stat_ok(xo, 0.15, -0.15, NOISE_SHARE))
    check('17 kuristimen kääntö: vanha (bim:0) kaatuu lukkiutumistarkistukseen vähintään toisessa käännössä', any(old17),
          str(old17))

    # 18 kello (kayttajan valinta a 27.9.2026): lukossa (2,5 sd < EU_PHASE_OK_US) viimeistaan vaiheen 4 alussa, ja
    # vaiheessa 4 tauot ovat 10 ms. 26b:n esiuuton tarve 0,1 on pieni kuten laitteella ao-as: pidon vareily jaa AMP_MIN:n
    # alle, kello on vapaa vaiheessa 2 ja lukittuu vasta vaiheen 3 hitaista ikkunoista (EB_CLK_RATE). Ilman niita
    # (EB_CLK_RATE -inf: vaiheet 3-4 eivat opeta, kuten vanha learn=(phase == 2)) tarkistus kaatuu.
    def clock18(rate):
        keep, F.EB_CLK_RATE = F.EB_CLK_RATE, rate
        rs = []
        try:
            for seed, noisy in [(x, False) for x in range(160, 160 + N8_PHASE)] + [(x, True) for x in range(260, 260 + N8_NOISE)]:
                bd = brew_bd('26b', seed, noisy)
                txt, stamps = run_brew(bd, 16.0, bim=1, seed=seed, stall_hz=5.0 if noisy else 0.0)
                rs.append(brew_metrics(bd, txt, stamps, 1))
        finally:
            F.EB_CLK_RATE = keep
        return rs
    for st in ('25b', '26b'):
        rs = [m for noisy in (False, True) for m in t16[(st, noisy, 1)]]
        check('18 kello %s: lukossa pidon alussa (2,5 sd < %d us)' % (st, F.EU_PHASE_OK_US),
              all(2.5 * m['sd_hold'] < F.EU_PHASE_OK_US for m in rs),
              'sd_us max %.0f, esiuuton lopussa max %.0f' % (max(m['sd_hold'] for m in rs), max(m['sd_pre'] for m in rs)))
        check('18 kello %s: vaiheen 4 tauoista ≥ 80 %% 10 ms' % st, all(m['sk10_4'] >= 0.8 * (m['sk10_4'] + m['sk20_4']) and
                                                                     m['sk10_4'] > 0 for m in rs),
              'sk10/sk20 %s' % ['%d/%d' % (m['sk10_4'], m['sk20_4']) for m in rs[-4:]])
    # Kohinattomassa 26b:ssa kello on esiuuton lopussa vapaa (sd ~9 ms): pidon alun lukko tulee vaiheen 3 hitaista
    # ikkunoista. Kohinaisissa se on lukossa jo vaiheessa 2, mutta ilman vaiheen 4 oppia tauot muuttuvat 20 ms:ksi.
    rs = clock18(-1e9)
    check('18 kello 26b ilman vaiheiden 3-4 oppia: kohinaton lukitsematta pidon alussa, kohinainen 20 ms tauot',
          not all(2.5 * m['sd_hold'] < F.EU_PHASE_OK_US for m in rs[:N8_PHASE]) and
          not all(m['sk10_4'] >= 0.8 * (m['sk10_4'] + m['sk20_4']) for m in rs[N8_PHASE:]),
          'sd_us %s, sk10/sk20 %s' % (['%.0f' % m['sd_hold'] for m in rs[:N8_PHASE]],
                                     ['%d/%d' % (m['sk10_4'], m['sk20_4']) for m in rs[N8_PHASE:]]))

    # 19 vuoronvaraus vaiheissa 3-4: roskienkeruu (Gc kuten tapaus 14), toisen tehtavan varaukset 13-28 ms 5/s ja kellon
    # ikkunan sulku 9 ms. vv=1: ei myohastyneita taukoja (late 0) releen ollessa paalla; vv=0 (euv:0): vahti laskee.
    r19 = {0: [], 1: []}
    for vv in (1, 0):
        for seed in range(190, 190 + N8_NOISE):
            bd = brew_bd('25b', seed, True)
            bd.eu_vv = vv
            txt, stamps = run_brew(bd, 16.0, bim=1, seed=seed, stall_hz=5.0, stall_ms=(13, 28), gc=True, iq_cost=9000)
            # Automaattiset keruut vain vaiheista 3-4 (siirtyman jalkeen): vaiheessa 1 rele on paalla joka tapauksessa
            tb = next(t for t, l in stamps if l.startswith('EU_END '))
            r19[vv].append((int(num(txt, 'EB_END', 'late')), sum(1 for t in bd.gc_auto_t if t >= tb),
                            int(num(txt, 'EB_VV', 'gc_n')), max(len(l) for l in txt.splitlines())))
    check('19 vuoronvaraus vaiheet 3-4 vv=1: late 0, ei automaattista keruuta vaiheissa 3-4',
          all(x[0] == 0 and x[1] == 0 for x in r19[1]),
          'late %s, auto %s, hallittu %s' % ([x[0] for x in r19[1]], [x[1] for x in r19[1]], [x[2] for x in r19[1]]))
    check('19 vuoronvaraus vaiheet 3-4 vv=0: vahti laskee myöhästymiset (late > 0)', all(x[0] > 0 for x in r19[0]),
          'late %s' % [x[0] for x in r19[0]])

    # 20 opitut uuttoarvot erillaan: uuton oppi ei muuta esiuuton arvoja (samat kuin samalla siemenella bim:0:lla, jossa
    # uuttoa ei opita), eb_* talteen, ja 2. ajo kayttaa 1. ajon uuttoarvoja (EB_START). settings.txt: eb_*-avaimet
    # tallentuvat ja latautuvat; vanha tiedosto ilman avaimia -> oletukset.
    pre_keys = ('learned_ff_pre', 'eu_g_pre', 'eu_tau_pre', 'eu_coast_s', 'eu_coast_fast_s')
    vals = {}
    for bim in (1, 0):
        bd = brew_bd('25b', 200, False)
        txt, stamps = run_brew(bd, 16.0, bim=bim, seed=200)
        vals[bim] = (bd, txt, [getattr(bd, k) for k in pre_keys], stamps)
    bd1, txt1, pre1, stamps1 = vals[1]
    check('20 uuton oppi ei muuta esiuuton arvoja (= bim:0 samalla siemenellä)', pre1 == vals[0][2],
          'bim:1 %s, bim:0 %s' % (['%.3f' % v for v in pre1], ['%.3f' % v for v in vals[0][2]]))
    eu_same = [l for l in txt1.splitlines() if l.startswith('EU_END ')] == \
              [l for l in vals[0][1].splitlines() if l.startswith('EU_END ')]
    check('20 esiuuton EU_END sama bim:1 ja bim:0', eu_same)
    eb = {k: getattr(bd1, k, 0.0) for k in ('eb_ff', 'eb_x', 'eb_g', 'eb_tau', 'eb_coast_s')}
    check('20 uuttoarvot opittu (eb_ff, eb_x, eb_g, eb_tau > 0)', all(eb[k] > 0 for k in ('eb_ff', 'eb_x', 'eb_g', 'eb_tau')),
          ' '.join('%s=%.3f' % kv for kv in eb.items()))
    bd1.plant.p, bd1.plant.pending = 0.0, []    # ajojen valissa paine purkautuu (kuten tapaus 2)
    txt2, _ = run_brew(bd1, 16.0, bim=1, seed=201)
    ex = lambda k: float(field(txt2, 'EB_START', k))
    ok2 = abs(ex('x') - eb['eb_x']) < 0.006 and abs(ex('coast_s') - eb['eb_coast_s']) < 0.0006 and \
        abs(ex('g') - eb['eb_g']) < 0.006 and abs(ex('tau') - eb['eb_tau']) < 0.006 and \
        abs(ex('ff') - min(1.0, max(0.05, float(field(txt2, 'EB_START', 'ff_pre')) * eb['eb_x']))) < 0.006
    check('20 2. ajo käyttää 1. ajon uuttoarvoja (EB_START x, coast_s, g, tau; ff = esiuuton tarve × x)', ok2,
          [l for l in txt2.splitlines() if l.startswith('EB_START')][0][:160])
    txt2b, _ = run_brew(brew_bd('25b', 201, False), 16.0, bim=1, seed=201)
    check('20 ilman edellistä uuttoa x = (8 / 2,5)^%.1f' % F.EB_LEAK_N,
          abs(float(field(txt2b, 'EB_START', 'x')) - (8.0 / 2.5) ** F.EB_LEAK_N) < 0.006, field(txt2b, 'EB_START', 'x'))
    check('20 settings.txt: eb_* tallentuu ja latautuu, vanha tiedosto -> oletukset', settings_roundtrip(), '')

    # 21 bim:0 ajaa vanhan uuttosilmukan (TS-rivit, ei EB-riveja, TS_END kerran), ja uuden polun siirtymarivit tulostuvat
    # jonosta enintaan yksi jaksoa kohden (EU_END, EU_END2, EU_VV, EB_START >= 15 ms valein), rivit <= 255 merkkia.
    txt0 = vals[0][1]
    check('21 bim:0: vanha uuttosilmukka (TS-rivejä, ei EB-rivejä, TS_END kerran)',
          sum(1 for l in txt0.splitlines() if l.startswith('TS ')) > 50 and 'EB_' not in txt0 and txt0.count('TS_END') == 1,
          'TS %d, EB %d' % (sum(1 for l in txt0.splitlines() if l.startswith('TS ')), txt0.count('EB_')))
    check('21 bim:1: TS_END kerran, ei TS-rivejä', txt1.count('TS_END') == 1 and '\nTS ' not in txt1, field(txt1, 'TS_END', 'loops'))
    at = [t for t, l in stamps1 if l.startswith(('EU_END ', 'EU_END2', 'EU_VV', 'EB_START'))]
    check('21 siirtymän loppurivit jonosta ≥ 15 ms välein', len(at) == 4 and all(b - a >= 15000 for a, b in zip(at, at[1:])),
          'välit ms %s' % [round((b - a) / 1000) for a, b in zip(at, at[1:])])
    ml = max(m['maxline'] for rs in t16.values() for m in rs)
    check('21 rivit ≤ 255 merkkiä (USB-CDC:n jono)', max(ml, max(x[3] for x in r19[1])) <= 255, '%d' % ml)

    print('RESULT: %d failed' % len(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
