#!/usr/bin/env python3
"""tray_total_smoke.py — EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO (21.9.2026).

Laukaisija: 20.9.2026 neljä peräkkäistä ajoa sai kukin oman 250 g:n wrise-varansa, wmax oli
asettamatta ja kaukalo tulvi yli. Tarkistaa valelaitteilla, että
  1. pelkkä wrise ei riitä: ajo ei ala ilman wmax:ia (reason=nolimit),
  2. ajo ei ala, jos kaukalo on jo wmax:ssa (reason=tray), eikä yhtään relettä kytketä,
  3. peräkkäiset ajot eivät kerrytä painoa yli wmax:n (kertymä pysähtyy rajaan),
  4. mcal noudattaa samaa vahtia.

    python3 testit/tray_total_smoke.py       RESULT: <n> failed
"""

import asyncio
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tray_guard_smoke as T
F = T.F


class Tray(T.BrewData):
    """Kaukalo, jonka paino kasvaa vain pumpun ollessa päällä ja säilyy ajojen välissä."""

    def __init__(self, start=100.0, rate=300.0, **kw):
        super().__init__(weight_mode='ok', **kw)
        self.base = start
        self.rate = rate
        self.mcal_abort = False
        self._on_since = None

    def get_weight(self):
        now = T.time.monotonic()
        if self.pump.v:
            if self._on_since is None:
                self._on_since = now
            self.base += self.rate * (now - self._on_since)
            self._on_since = now
        else:
            self._on_since = None
        return self.base


def run_mcal(bd, ms):
    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(F.mains_calibrate(bd, T.Utime(), T.Asyncio(), ms))
    return buf.getvalue()


def main():
    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name)
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    runners = (('phold', T.run_hold, 5), ('pcap', T.run_cap, 400), ('mcal', run_mcal, 400))

    # --- 1. Pelkkä wrise ei riitä
    for name, runner, arg in runners:
        bd = Tray(wmax=0.0, wrise=250.0)
        out = runner(bd, arg)
        check('%s: vain wrise -> reason=nolimit' % name, 'reason=nolimit' in out, out.strip()[-80:])
        check('%s: vain wrise -> ei releitä' % name, bd.pump.ons == 0 and bd.solenoid.ons == 0)

    # --- 2. Kaukalo jo rajalla
    for name, runner, arg in runners:
        bd = Tray(start=480.0, wmax=470.0, wrise=250.0)
        out = runner(bd, arg)
        check('%s: kaukalo täynnä -> reason=tray' % name, 'reason=tray' in out, out.strip()[-80:])
        check('%s: kaukalo täynnä -> ei releitä' % name, bd.pump.ons == 0 and bd.solenoid.ons == 0)

    # --- 3. Kertymä: toistetut phold-ajot samaan kaukaloon eivät ylitä wmax:ia
    bd = Tray(start=100.0, rate=300.0, wmax=470.0, wrise=250.0)
    reasons = []
    for _ in range(6):
        bd.pump.ons = 0
        out = T.run_hold(bd, 30)
        reasons.append(out.strip().splitlines()[-1])
    over = bd.base - 470.0
    check('kertymä: viimeiset ajot estetään (reason=tray, ei pumppua)',
          'reason=tray' in reasons[-1] and bd.pump.ons == 0, reasons[-1])
    # Kaksi vaakanäytettä rajan yli + silmukan viive: ylitys pysyy pienenä, ei 4 x 250 g.
    check('kertymä: kokonaispaino pysyy lähellä wmax:ia (ylitys < 60 g)', over < 60.0,
          'paino=%.0f' % bd.base)

    # --- 4. mcal rajojen sisällä ajaa normaalisti
    bd = Tray(start=100.0, rate=10.0, wmax=470.0, wrise=250.0)
    out = run_mcal(bd, 400)
    check('mcal: rajojen sisällä pumppu kytkettiin', bd.pump.ons >= 1, out.strip()[-80:])
    check('mcal: lopussa releet pois', bd.pump.value() == 0 and bd.solenoid.value() == 0)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
