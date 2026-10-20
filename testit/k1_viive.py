#!/usr/bin/env python3
"""k1_viive.py — C1-JAKSOT K1: kuinka paljon yhden tai kahden jakson lisaviive pumpun paatoksessa heikentaa painesaatoa.

Ajaa oikean `functions.run_shot`-silmukan (esiuutto 2,5 bar + uutto 8 bar, bim:1) esiuutto_smoke.py:n iskumallilla.
Viive tehdaan vain testissa: pumppureleen kirjoitus (RELAY_PUMP.value) tulee voimaan vasta N verkkojaksoa
(N x 1e6 / 50,01 us virtuaaliaikaa) myohemmin. Mallin nollakohta ottaa viivastetun tilan. pico/ ei muutu.

    python3 testit/k1_viive.py [--lags 0,1,2] [--seeds 260-267] [--states 25b,26b] [--noise 1] [--raw]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import esiuutto_smoke as E   # noqa: E402

T_US = 1e6 / E.F_MAINS


class DPin:
    """Pumppurele: loop nakee heti (value() palauttaa pyydetyn), malli vasta viiveen jalkeen (v = voimassa oleva)."""
    delay_us = 0

    def __init__(self):
        self.v, self.req, self.hook, self.q = 0, 0, None, []

    def value(self, x=None):
        if x is None:
            return self.req
        if self.hook: self.hook(x)          # Plant.on_pin: vie mallin nykyhetkeen ennen muutosta
        self.req = 1 if x else 0
        self.q.append((E.U.us + self.delay_us, self.req))


class DPlant(E.Plant):
    def on_pin(self, x):
        self.advance(E.U.us)

    def advance(self, now):
        q = self.pump.q
        while q and q[0][0] <= now:         # viivastetut kirjoitukset voimaan omalla ajallaan, nollakohtien valissa
            e, x = q.pop(0)
            E.Plant.advance(self, e)
            self.pump.v = x
        E.Plant.advance(self, now)


def make_bd(st, seed, noisy, lag, wrap=True):
    bd = E.brew_bd(st, seed, noisy)
    if wrap:
        dp = DPin()
        DPin.delay_us = int(round(lag * T_US))
        dp.hook = bd.plant.on_pin
        bd.pump = bd.plant.pump = dp
        bd.plant.__class__ = DPlant
    return bd


def fields(txt):
    r = {}
    for ph, pre in (('eu', 'EU_END'), ('eb', 'EB_END')):
        for k in ('hold_mean', 'hold_sd', 'over', 'max', 'strokes', 'rm', 'late', 'miss', 'hold_n'):
            r[ph + '_' + k] = E.num(txt, pre, k)
    return r


def parse_seeds(s):
    if '-' in s:
        a, b = s.split('-')
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(',')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lags', default='0,1,2')
    ap.add_argument('--seeds', default='260-267')
    ap.add_argument('--states', default='25b,26b')
    ap.add_argument('--noise', type=int, default=1)
    ap.add_argument('--raw', type=int, default=0, help='1: myos lag 0 ilman kaaretta (tarkistaa kaaren ei muuta tulosta)')
    ap.add_argument('--until', type=float, default=16.0)
    a = ap.parse_args()
    noisy = bool(a.noise)
    lags = [int(x) for x in a.lags.split(',')]
    rows = []
    for st in a.states.split(','):
        for lag in ([None] if a.raw else []) + lags:
            for seed in parse_seeds(a.seeds):
                bd = make_bd(st, seed, noisy, lag or 0, wrap=lag is not None)
                txt, _ = E.run_brew(bd, a.until, bim=1, seed=seed, stall_hz=5.0 if noisy else 0.0)
                f = fields(txt)
                f.update(st=st, str_diff=f['eu_strokes'] + f['eb_strokes'] - bd.plant.strokes, lag='raw' if lag is None else lag, seed=seed, model_strokes=bd.plant.strokes,
                         end_eu=E.field(txt, 'EU_END', 'reason'), end_eb=E.field(txt, 'EB_END', 'reason'))
                rows.append(f)
                print('%s lag=%s seed=%d eu[%s] mean=%.3f sd=%.3f over=%+.2f max=%.2f str=%d rm=%d late=%d miss=%d | '
                      'eb[%s] mean=%.3f sd=%.3f over=%+.2f max=%.2f str=%d rm=%d late=%d miss=%d | plant_strokes=%d' % (
                      st, f['lag'], seed, f['end_eu'], f['eu_hold_mean'], f['eu_hold_sd'], f['eu_over'], f['eu_max'],
                      f['eu_strokes'], f['eu_rm'], f['eu_late'], f['eu_miss'], f['end_eb'], f['eb_hold_mean'], f['eb_hold_sd'],
                      f['eb_over'], f['eb_max'], f['eb_strokes'], f['eb_rm'], f['eb_late'], f['eb_miss'], bd.plant.strokes), flush=True)
    print('\nSUMMARY (ka / min..max seeds yli)')
    keys = ['eu_hold_mean', 'eu_hold_sd', 'eu_over', 'eu_max', 'eb_hold_mean', 'eb_hold_sd', 'eb_over', 'eb_max',
            'eu_late', 'eb_late', 'eu_miss', 'eb_miss', 'str_diff']
    seen = []
    for r in rows:
        if (r['st'], r['lag']) not in seen: seen.append((r['st'], r['lag']))
    for st, lag in seen:
        g = [r for r in rows if r['st'] == st and r['lag'] == lag]
        print('%s lag=%s n=%d' % (st, lag, len(g)))
        for k in keys:
            xs = [r[k] for r in g]
            sd = (sum((x - sum(xs) / len(xs)) ** 2 for x in xs) / len(xs)) ** 0.5
            print('   %-13s ka %+.3f  min %+.3f  max %+.3f  sd_seed %.3f' % (k, sum(xs) / len(xs), min(xs), max(xs), sd))


if __name__ == '__main__':
    main()
