#!/usr/bin/env python3
"""kuumavesi_smoke.py — suunnittelijan holdout-testi kuumavesikytkimen rajoille (EXPRESSO-KUUMAVESI-RAJAT).

TURVAKATO kohta 4, käyttäjän päätös 7.10.2026: kuumavesiajo katkeaa 1 s:n jälkeen (`HOT_WATER_MAX_MS`),
lämmitin sammuu, kun vartio katkaisee pumpun (ei kuivakuumennusta), ja lämmitintä ohjaa termostaatti
eikä jatkuva 100 %. Ajaa firmwaren `hot_water_run`-korutiinin CPythonilla valelaitteilla.

    python3 testit/kuumavesi_smoke.py        RESULT: <n> failed, epänolla paluuarvo jos punaisia

Toteuttaja ei muokkaa tätä tiedostoa (brief: must not).
"""

import asyncio
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico'))
import functions as F

FAILED = []


def check(name, ok):
    print(('ok   ' if ok else 'FAIL ') + name)
    if not ok:
        FAILED.append(name)


class Pin:
    def __init__(self, v=0):
        self.v = v

    def value(self, x=None):
        if x is None:
            return self.v
        self.v = 1 if x else 0


class Clock:
    """utime-kuori ja asyncio-kuori samaan kelloon: sleep_ms siirtää aikaa ja ajaa ajastetut tapahtumat."""
    def __init__(self):
        self.t = 0
        self.events = []      # (ms, fn)
        self.trace = []       # (ms, pump, heater) jokaisen unen jälkeen

    def ticks_ms(self):
        return self.t

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b

    def at(self, ms, fn):
        self.events.append((ms, fn))

    async def sleep_ms(self, ms):
        end = self.t + ms
        while self.t < end:
            self.t += 1
            for e in [e for e in self.events if e[0] == self.t]:
                e[1]()
        self.trace.append((self.t, self.bd.pump.v, self.bd.heater.v))
        if self.t > 20000:
            raise RuntimeError('hot_water_run ei palannut 20 s:ssa')

    async def sleep(self, s):
        await self.sleep_ms(int(s * 1000))


class BrewData:
    def __init__(self, temp, target=93.0):
        self.pump, self.solenoid, self.heater = Pin(), Pin(), Pin()
        self.brew, self.water, self.steam = Pin(), Pin(1), Pin()
        self.mode = None
        self.temp = temp
        self.target = target
        self.temp_reads = 0
        self.activity = []
        self.dev_safe = False

    def get_relays(self):
        return self.pump, self.solenoid, self.heater

    def get_switches(self):
        return self.brew, self.water, self.steam

    def set_mode(self, m):
        self.mode = m

    def get_target_temperature(self):
        return self.target

    def get_boiler_temperature(self):
        self.temp_reads += 1
        return self.temp

    def note_activity(self, now, kind):
        self.activity.append((now, kind))


class Thermostat:
    def __init__(self, bd):
        self.bd = bd
        self.calls = []

    def run(self):
        self.calls.append(self.bd.mode)
        self.bd.heater.value(1 if self.bd.temp < self.bd.target else 0)


def run(temp, events):
    clk = Clock()
    bd = BrewData(temp)
    clk.bd = bd
    th = Thermostat(bd)
    for ms, fn in events(bd):
        clk.at(ms, fn)
    out = io.StringIO()
    with redirect_stdout(out):
        reason = asyncio.run(F.hot_water_run(bd, th, clk, clk))
    return reason, bd, th, clk, out.getvalue()


def main():
    check('H0 functions.HOT_WATER_MAX_MS == 1000 (käyttäjä 7.10.2026)', getattr(F, 'HOT_WATER_MAX_MS', None) == 1000)
    check('H0 functions.hot_water_run on olemassa', hasattr(F, 'hot_water_run'))
    if FAILED:
        print('RESULT: %d failed' % len(FAILED))
        return 1

    # H1: kytkin pidetään 3 s, lämmitys tarpeen -> pumppu ja lämmitin pois 1 s:n kohdalla ja pysyvät pois
    reason, bd, th, clk, out = run(80.0, lambda bd: [(3000, lambda: bd.water.value(0))])
    early = [p for t, p, h in clk.trace if t < 1000]
    late = [(p, h) for t, p, h in clk.trace if 1000 + 100 <= t]
    check('H1 paluu reason == "time"', reason == 'time')
    check('H1 pumppu päällä ennen 1 s:ia', early and all(early))
    check('H1 pumppu ja lämmitin pois 1,1 s:sta kytkimen vapautukseen asti', late and all(p == 0 and h == 0 for p, h in late))
    check('H1 lokirivi HOT_WATER_END reason=time', 'HOT_WATER_END reason=time' in out)
    check('H1 tila WATER', bd.mode == 'WATER')
    check('H1 lopussa releet pois ja note_activity switch', bd.pump.v == 0 and bd.heater.v == 0 and
          any(k == 'switch' for _, k in bd.activity))
    check('H1 palasi vasta kytkimen vapautuksen jälkeen', clk.t >= 3000)

    # H2: kytkin vapautetaan 400 ms:ssa -> reason switch
    reason, bd, th, clk, out = run(80.0, lambda bd: [(400, lambda: bd.water.value(0))])
    check('H2 paluu reason == "switch"', reason == 'switch')
    check('H2 palasi alle 600 ms:ssa', clk.t < 600)
    check('H2 releet pois lopussa', bd.pump.v == 0 and bd.heater.v == 0)

    # H3: vartio katkaisee pumpun 300 ms:ssa -> lämmitin pois viimeistään 100 ms:ssa, termostaattia ei enää ajeta
    def cut(bd):
        return [(300, lambda: bd.pump.pin_cut()), (2000, lambda: bd.water.value(0))]
    def ev3(bd):
        bd.pump.pin_cut = lambda: setattr(bd.pump, 'v', 0)
        return cut(bd)
    reason, bd, th, clk, out = run(80.0, ev3)
    after = [h for t, p, h in clk.trace if t >= 400]
    check('H3 paluu reason == "pump"', reason == 'pump')
    check('H3 lämmitin pois 0,4 s:sta loppuun (ei kuivakuumennusta)', after and all(h == 0 for h in after))
    n_at_cut = len([1 for t, p, h in clk.trace if t <= 400])
    check('H3 termostaattia ei ajeta katkon jälkeen', len(th.calls) <= n_at_cut)
    check('H3 lokirivi HOT_WATER_END reason=pump', 'HOT_WATER_END reason=pump' in out)

    # H4: kattila tavoitteen yllä -> lämmitin ei kytkeydy kertaakaan (ei pakotettua 100 %)
    reason, bd, th, clk, out = run(99.0, lambda bd: [(800, lambda: bd.water.value(0))])
    check('H4 termostaatti ajettiin WATER-tilassa', th.calls and all(m == 'WATER' for m in th.calls))
    check('H4 lämmitin pysyi pois tavoitteen yllä', all(h == 0 for _, _, h in clk.trace))

    # H5: kattila tavoitteen alla -> termostaatti kytkee lämmittimen ajon aikana
    reason, bd, th, clk, out = run(80.0, lambda bd: [(800, lambda: bd.water.value(0))])
    check('H5 lämmitin päällä ajon aikana tavoitteen alla', any(h == 1 for t, _, h in clk.trace if t < 800))
    check('H5 lämpötila luettiin (vartion tuoreusraja)', bd.temp_reads >= 1)

    print('RESULT: %d failed' % len(FAILED))
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
