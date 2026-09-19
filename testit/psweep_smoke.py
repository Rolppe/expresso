#!/usr/bin/env python3
"""psweep_smoke.py — suunnittelijan holdout vaihesiirtopyyhkäisylle (PWM-1B4, säännöt 10 ja 13).

Testaa sen, mitä py_compile ja lähdekoodin grep eivät näe: että `pressure_sweep_run` todella
ajaa segmentit järjestyksessä ref, p_0..p_{n-1}, ref yhden asettumisen sisällä, että portitetut
segmentit kytkevät pumppua ja referenssisegmentit eivät, että segmenttien väliin ajetaan
trimmausaskel, ja että kaappauksen jälkeinen kaukalovahdin tarkistus hakee vaa'alta tuoreen
lukeman sen sijaan että tuomitsisi ajon syyhyn `scalelost` (avoin vika 19.9.2026).

    python3 testit/psweep_smoke.py      RESULT: <n> failed, epänolla paluuarvo jos punaisia

Ajo kestää noin 55 s: kuusi ajoa, joista pisin on vaakatesti (2 x 2500 ms segmenttiä).
Toteuttaja ei muokkaa tätä tiedostoa (brief: must not).
"""

import asyncio
import io
import os
import re
import sys
import time
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico'))
import functions as F


class Pin:
    def __init__(self, v=0):
        self.v = v
        self.log = []          # (t_ms, arvo) jokaisesta muutoksesta

    def value(self, x=None):
        if x is None:
            return self.v
        if x != self.v:
            self.log.append((time.monotonic_ns() // 1000000, x))
        self.v = x


class Adc:
    """Vakiolukema, jonka testi voi vaihtaa kesken ajon."""

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
    """Valelaite. `scale_live=True` päivittää vaa'an aikaleiman vain silmukan antaessa vuoron,
    kuten laitteella: kaappaussilmukka ei anna vuoroa, joten lukema vanhenee sen aikana."""

    def __init__(self, target=4.9, n=None, raw=30000, scale_live=False, scale_dead=False):
        self.pump, self.solenoid, self.heater = Pin(), Pin(), Pin()
        self.brew, self.water, self.steam = Pin(), Pin(), Pin()
        self.pressure_sensor = Sensor(raw)
        self.dev_safe = False
        self.pcap_abort = False
        self.pcap_target_bar = None
        self.pcap_gate_phase_us = None
        self.psweep_abort = False
        self.psweep_target_bar = target
        self.psweep_n = n
        self.mode = None
        self.scale_live = scale_live
        self.scale_dead = scale_dead
        self.weight_ms = int(time.monotonic() * 1000)

    def get_relays(self):
        return self.pump, self.solenoid, self.heater

    def get_switches(self):
        return self.brew, self.water, self.steam

    def set_mode(self, m):
        self.mode = m

    def get_weight(self):
        return 100.0

    def get_weight_ms(self):
        if self.scale_dead:
            return self.weight_ms          # jäätynyt: aito scalelost
        if self.scale_live:
            return self.weight_ms          # päivittyy vain taustatehtävässä
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
    """Ajaa pyyhkäisyn ja palauttaa tulosteen. Vaakatehtävä pyörii rinnalla kuten laitteella."""

    async def scale_task():
        while True:
            bd.weight_ms = int(time.monotonic() * 1000)
            await asyncio.sleep(0.05)      # EXPRESSO-SCALE-POLL: 50 ms

    async def both():
        t = asyncio.ensure_future(scale_task())
        try:
            await F.pressure_sweep_run(bd, Utime(), Asyncio(), ms)
        finally:
            t.cancel()

    if not callable(getattr(F, 'pressure_sweep_run', None)):
        return ''              # ei vielä toteutettu: kaikki ajoon nojaavat väitteet punaisina
    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(both())
    return buf.getvalue()


def starts(out):
    return [dict(p.split('=', 1) for p in ln.split()[1:] if '=' in p)
            for ln in out.splitlines() if ln.startswith('PCAP_START')]


def main():
    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name)
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    check('pressure_sweep_run on moduulitason korutiini',
          callable(getattr(F, 'pressure_sweep_run', None)))

    # 1. Vakiot ja vaihesiirtolista (sääntö 10)
    check('PSWEEP_N_DEFAULT on 5', getattr(F, 'PSWEEP_N_DEFAULT', None) == 5,
          str(getattr(F, 'PSWEEP_N_DEFAULT', None)))
    check('PSWEEP_TRIM_BAR on positiivinen', (getattr(F, 'PSWEEP_TRIM_BAR', 0) or 0) > 0)
    check('PSWEEP_TRIM_MS on positiivinen', (getattr(F, 'PSWEEP_TRIM_MS', 0) or 0) > 0)
    check('TRAY_RESYNC_MS on positiivinen', (getattr(F, 'TRAY_RESYNC_MS', 0) or 0) > 0)
    ph = getattr(F, 'psweep_phases', None)
    check('psweep_phases on moduulitason funktio', callable(ph))
    if callable(ph):
        p5 = list(ph(5))
        check('psweep_phases(5) antaa viisi arvoa', len(p5) == 5, str(p5))
        check('ensimmäinen vaihesiirto on 0', p5 and p5[0] == 0, str(p5[:1]))
        check('vaihesiirrot ovat tasavälein portin jakson yli',
              p5 == [k * F.PCAP_GATE_PERIOD_US // 5 for k in range(5)], str(p5))
        check('kaikki vaihesiirrot ovat portin jakson sisällä',
              all(0 <= p < F.PCAP_GATE_PERIOD_US for p in p5), str(p5))

    # 2. Koko pyyhkäisy: järjestys, otsikot, trimmaukset (säännöt 10 ja 13)
    bd = BrewData(target=4.9, n=3)
    out = run(bd, 300)
    hs = starts(out)
    check('PSWEEP_START tulostuu', 'PSWEEP_START' in out, out.splitlines()[:1])
    check('segmenttejä on n+2', len(hs) == 5, 'PCAP_START-rivejä %d' % len(hs))
    if len(hs) == 5:
        check('seg-numerot ovat 0..4', [h.get('seg') for h in hs] == ['0', '1', '2', '3', '4'],
              str([h.get('seg') for h in hs]))
        check('referenssisegmentit ovat portittamattomia',
              hs[0].get('gate') == 'off' and hs[4].get('gate') == 'off',
              '%s %s' % (hs[0].get('gate'), hs[4].get('gate')))
        check('mittaussegmentit ovat portitettuja',
              all(h.get('gate') == 'on' for h in hs[1:4]),
              str([h.get('gate') for h in hs[1:4]]))
        if callable(ph):
            check('vaihesiirrot tulevat psweep_phases(3):sta',
                  [int(h.get('phase_us', -1)) for h in hs[1:4]] == list(ph(3)),
                  str([h.get('phase_us') for h in hs[1:4]]))
        check('jokainen otsikko kertoo elävän kalibroinnin',
              all('gain' in h and 'offset' in h for h in hs))
        check('jokainen otsikko kertoo näytetaajuuden ja pituuden',
              all(h.get('rate') == '1000' and h.get('n') == '300' for h in hs),
              str([(h.get('rate'), h.get('n')) for h in hs]))
    ends = [ln for ln in out.splitlines() if ln.startswith('PCAP_END')]
    check('jokaisella segmentillä on PCAP_END', len(ends) == 5, 'PCAP_END-rivejä %d' % len(ends))
    check('kaikki segmentit päättyivät ok', all('reason=ok' in ln for ln in ends),
          ' | '.join(ln for ln in ends if 'reason=ok' not in ln))
    check('PCAP_END kertoo segmentin numeron', all(re.search(r'\bseg=\d', ln) for ln in ends))
    trims = [ln for ln in out.splitlines() if ln.startswith('PSWEEP_TRIM')]
    check('trimmaus ajetaan segmenttien väliin', len(trims) == 4, 'PSWEEP_TRIM-rivejä %d' % len(trims))
    check('PSWEEP_TRIM kertoo paineen ja syyn',
          all('bar=' in ln and 'reason=' in ln for ln in trims), ' | '.join(trims[:1]))
    last = out.strip().splitlines()[-1] if out.strip() else '(tyhjä)'
    check('PSWEEP_END on viimeinen rivi', last.startswith('PSWEEP_END'), last)
    check('PSWEEP_END reason=ok', 'reason=ok' in last, last)
    check('PSWEEP_END kertoo segmenttien määrän', 'segs=5' in last, last)
    check('PCAP-rivejä on kaikilta segmenteiltä',
          len([ln for ln in out.splitlines() if ln.startswith('PCAP ')]) == 5 * (300 // 20),
          str(len([ln for ln in out.splitlines() if ln.startswith('PCAP ')])))
    check('pumppu pois lopussa', bd.pump.value() == 0)
    check('magneettiventtiili pois lopussa', bd.solenoid.value() == 0)
    edges = [v for _, v in bd.pump.log]
    check('portitetut segmentit kytkivät pumppua', len(edges) >= 30, 'reunoja %d' % len(edges))

    # 3. Oletus n=5, kun kenttää ei anneta (sääntö 10)
    bd = BrewData(target=4.9, n=None)
    out = run(bd, 200)
    check('oletusmäärä on 5 mittaussegmenttiä', len(starts(out)) == 7,
          'PCAP_START-rivejä %d' % len(starts(out)))

    # 4. Trimmaus purkaa painetta, eikä pyyhkäisy kaadu siihen (sääntö 13)
    trim_ms = getattr(F, 'PSWEEP_TRIM_MS', None)
    F.PSWEEP_TRIM_MS = 400          # testin oma lyhennys: vale-ADC ei laske painetta koskaan
    try:
        bd = BrewData(target=1.0, n=2)      # 4,94 bar >> 1,0 + PSWEEP_TRIM_BAR
        out = run(bd, 200)
        trims = [ln for ln in out.splitlines() if ln.startswith('PSWEEP_TRIM')]
        check('ylipaineinen trimmaus avasi magneettiventtiilin', len(bd.solenoid.log) >= 2,
              'venttiilin reunoja %d' % len(bd.solenoid.log))
        check('trimmaus päättyy aikakatkaisuun kun paine ei laske',
              any('reason=timeout' in ln for ln in trims), ' | '.join(trims[:2]))
        check('pyyhkäisy jatkuu trimmauksen aikakatkaisun jälkeen', len(starts(out)) == 4,
              'PCAP_START-rivejä %d' % len(starts(out)))
    finally:
        if trim_ms is None:
            del F.PSWEEP_TRIM_MS
        else:
            F.PSWEEP_TRIM_MS = trim_ms

    # 5. Kaukalovahti: vanhentunut mutta elpyvä lukema ei ole scalelost (avoin vika)
    bd = BrewData(target=4.9, n=2, scale_live=True)
    out = run(bd, 2500)
    check('kaappauksen jälkeen haetaan tuore lukema, ei scalelost',
          'scalelost' not in out, ' | '.join(ln for ln in out.splitlines() if 'scalelost' in ln))
    tail = out.strip().splitlines()[-1] if out.strip() else '(tyhjä)'
    check('elpyvällä vaa\'alla pyyhkäisy päättyy ok', 'reason=ok' in tail, tail)

    # 6. Kuollut vaaka on yhä aito scalelost
    bd = BrewData(target=4.9, n=2, scale_live=True, scale_dead=True)
    bd.weight_ms = int(time.monotonic() * 1000) - 60000
    out = run(bd, 200)
    check('kuollut vaaka pysäyttää pyyhkäisyn', 'scalelost' in out,
          out.strip().splitlines()[-1] if out.strip() else '(tyhjä)')
    check('kuollut vaaka: pumppu pois', bd.pump.value() == 0)

    # 7. Kytkin keskeyttää ennen yhtäkään relettä
    bd = BrewData(target=4.9, n=2)
    bd.brew.value(1)
    out = run(bd, 200)
    check('kytkin päällä: ei kaappauksia', not starts(out), str(len(starts(out))))
    check('kytkin päällä: PSWEEP_END reason=switch', 'reason=switch' in out,
          out.strip().splitlines()[-1] if out.strip() else '(tyhjä)')

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
