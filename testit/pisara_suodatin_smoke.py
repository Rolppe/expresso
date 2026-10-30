#!/usr/bin/env python3
"""pisara_suodatin_smoke.py — pisaratunnistuksen suodatin oikealla Scale.update-kutsulla (30.10.2026).

Vika: Scale.update siemensi 12 naytteen puskurin yhdella raakanaytteella jokaisella releen vaihdolla, joten
pulssitus teki yhdesta kohinanaytteesta suodattimen tuloksen (1,1 g:n piikki laukaisi tunnistuksen ilman tippaa)
ja tyhjensi virtauksen datan. Siemenyksen tarkoitus (1 s liukuma pumpun tilanmuutoksessa) sailyy: kertasiemenys
uuton pumpun kaynnistyksessa ja DROP_ARM_BLANK_MS pidon alussa (P7 todistaa, etta katve tarvitaan).

    python3 testit/pisara_suodatin_smoke.py       RESULT: 0 failed
"""
import os
import random
import sys
import time
import types

m = types.ModuleType('machine')
class Pin:
    OUT, IN = 1, 0
    def __init__(self, *a, **k): pass
    def value(self, v=None): return 0
m.Pin = Pin
m.disable_irq = lambda: 0
m.enable_irq = lambda s: None
sys.modules.setdefault('machine', m)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pico')))

clock = [100000]
time.ticks_ms = lambda: clock[0]
time.ticks_diff = lambda a, b: a - b
time.sleep_ms = lambda ms: None
time.sleep_us = lambda us: None

import scale as scale_mod
from scale import Scale, FirstDropDetector

STEP_MS = 86                 # mitattu naytevali
K = 2000.0
BLANK = 1200                 # functions.DROP_ARM_BLANK_MS; functions ei tuo host-testiin kevyesti

fails = []


def check(name, cond, extra=''):
    print(('ok   %s' if cond else 'FAIL %s') % name, extra if not cond else '')
    if not cond:
        fails.append(name)


def make(rest=1500.0, sd=0.0, rng=None):
    s = Scale.__new__(Scale)
    s.window, s.errors, s.extra = 12, 0, 1
    s.off_a, s.off_b, s.trim_b, s.scale, s.calibrated = 0.0, 0.0, 1.0, K, True
    s.last_a = s.last_b = 0.0
    s.raw_a = s.raw_b = 0
    s._buf, s._hist, s._raw, s._flow_raw = [], [], [], []
    s._flow_n, s.flow_window_ms = 48, scale_mod.FLOW_WINDOW_MS
    s.drop_detector = FirstDropDetector()
    s._seed_pending = False
    s.ready = lambda: True
    s.next_g = rest
    s._shift = lambda: (int(s.next_g * K), 0)
    for _ in range(16):
        sample(s, rest, False, sd, rng)
    return s


def sample(s, g, pump_on, sd=0.0, rng=None):
    clock[0] += STEP_MS
    s.next_g = g + (rng.gauss(0, sd) if rng else 0.0)
    return s.update(pump_on=pump_on, pressure=2.0)


def arm(s, blank=BLANK):
    s.arm_drop_detector(w=s.value(), threshold=0.25, blanking_ms=blank)


def main():
    # P1: tasainen paino, pulssitus, levon kohina: ei juuri vaaria laukaisuja (vanhalla koodilla ~2/3)
    rng = random.Random(3)
    hits = 0
    runs = 300
    for _ in range(runs):
        s = make(sd=0.25, rng=rng)
        arm(s)
        for i in range(70):          # 6 s
            sample(s, 1500.0, i % 3 == 0, 0.25, rng)
        hits += s.drop_detected()
    check('P1 pulssitus + tasainen paino 6 s: vaaria alle 12 %', hits / runs < 0.12, '%d/%d' % (hits, runs))

    # P2: yksi raakanayte +1,1 g pulssin kohdalla ei nay tuloksessa eika laukaise
    s = make()
    arm(s, 0)
    out = []
    for i in range(30):
        g = 1501.1 if i == 15 else 1500.0
        out.append(sample(s, g, i % 2 == 0))
    check('P2a yksi 1,1 g:n raakanayte ei laukaise', not s.drop_detected())
    check('P2b tulos ei liiku', max(out) - min(out) < 0.05, max(out) - min(out))

    # P3-P4: virtaus elaa pulssituksessa ja on oikein
    s = make()
    g, none = 1500.0, 0
    for i in range(60):
        g += 2.0 * STEP_MS / 1000.0
        sample(s, g, i % 2 == 0)
        if i > 12 and s.flow() is None:
            none += 1
    f = s.flow()
    check('P3 virtaus ei katoa pulssituksessa', none == 0, none)
    check('P4 virtaus 2 g/s pulssituksessa', f is not None and 1.9 < f < 2.1, f)

    # P5: kaukalovahdin kaksi nayteaa: yksittainen -16 g tai +16 g ei toistu tuloksessa
    for spike in (-16.0, 16.0):
        s = make()
        out = []
        for i in range(30):
            out.append(sample(s, 1500.0 + (spike if i == 15 else 0.0), i % 2 == 0))
        check('P5 piikki %+.0f g ei nay tuloksessa' % spike, max(abs(x - 1500.0) for x in out) < 0.05)

    # P6: oikea tippa laukaisee pidon aikana
    s = make()
    arm(s)
    t_on, t_hit = None, None
    g = 1500.0
    for i in range(70):
        if i * STEP_MS >= 2000:
            t_on = t_on if t_on is not None else i
            g += 0.5 * STEP_MS / 1000.0
        sample(s, g, i % 3 == 0)
        if s.drop_detected():
            t_hit = i
            break
    check('P6 tippa 0,5 g/s laukaisee alle 2 s:ssa', t_hit is not None and (t_hit - t_on) * STEP_MS < 2000, t_hit)

    # P7: tarkoitus sailyy: siirtyma pulssitukseen (+0,8 g askel) valuu suodattimen lapi liukumana
    for blank, want, name in ((0, True, 'P7a ilman katvetta askel nakyy tippana (siksi katve)'),
                              (BLANK, False, 'P7b katve estaa liukuman laukaisun')):
        s = make()
        for _ in range(3):
            sample(s, 1500.0, True)
        arm(s, blank)
        for i in range(60):
            sample(s, 1500.8, i % 3 == 0)
        check(name, s.drop_detected() is want)
    g = 1500.8
    for i in range(30):
        g += 0.5 * STEP_MS / 1000.0
        sample(s, g, i % 3 == 0)
    check('P7c katveen jalkeen oikea tippa laukaisee', s.drop_detected())

    # P8: kertasiemenys kaynnistyksessa, ei pulsseissa
    s = make()
    s.seed_on_pump_start()
    sample(s, 1503.0, False)
    check('P8a ei siemenna ennen pumppua', len(set(s._buf)) > 1 and s._seed_pending)
    sample(s, 1503.0, True)
    check('P8b siementaa pumpun kaynnistyksessa kerran', not s._seed_pending and abs(s.value() - 1503.0) < 0.01)
    sample(s, 1504.0, False)
    sample(s, 1505.0, True)
    check('P8c seuraava pulssi ei siemenna', len(s._raw) >= 3 and abs(s.value() - 1503.0) < 0.5, s.value())

    # P9: lokirivi
    s = make(sd=0.25, rng=random.Random(5))
    arm(s, 0)
    r2 = random.Random(6)
    for i in range(40):
        sample(s, 1500.0, i % 3 == 0, 0.25, r2)
    line = s.drop_detector.stats_line()
    sd = float(line.split('raw_sd=')[1].split()[0])
    check('P9 stats_line raakahajonta ~0,25 g', s.drop_detector.st_n > 0 and 0.15 < sd < 0.35, line)

    print('RESULT: %d failed' % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
