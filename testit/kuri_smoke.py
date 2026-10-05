#!/usr/bin/env python3
"""kuri_smoke.py — kuristimen saatotila kuri:<n> (kayttaja 28.9.2026, KAYTTAJAN-TIEDOT TILAUS-M).

Ajaa firmwaren `throttle_set_run`-korutiinin esiuutto_smoke.py:n virtuaaliajalla ja iskumallilla: nollaylitys-SSR
(tila vaihtuu vain nollakohdissa), pumppu iskee vain aktiivisella puolijaksolla, vareily kalibroitu vsweep-a:han.
Pysahdykset kuten laitteella: automaattinen keruu 15-28 ms, hallittu keruu 15-28 ms ja toisen tehtavan varaukset.

Paatarkistus (kuri6, kayttajan havainto "ylimaaraisia iskuja ja jatti valista"): lukituksen jalkeen mallin
toteutuneet iskut ovat tasan kuvion mukaiset (25/s: jokainen vali 2 jaksoa; 24/s: 24 iskua / 50 jaksoa, ei vierekkaisia).
Ohjauskoe: sama ajo paatoksilla nollakohdassa Z (kuri2-5:n pahin vaihe) tuottaa virheita, eli testi erottaa vian.

    python3 testit/kuri_smoke.py        RESULT: <n> failed, epanolla paluuarvo jos punaisia
"""

import asyncio
import io
import os
import random
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esiuutto_smoke as E   # noqa: E402  (vale-utime, functions + vale-gc, verkkokello)
F, U, GC = E.F, E.U, E.GC
E.IQ_CLOSE_US[0] = 11000     # kellon ikkunan sulku laitteella 10-11 ms (ao/ap)
CYC = 2 * E.HALF_US          # verkkojakso mallissa (50,01 Hz)


class Bd(E.BrewData):
    def __init__(self, rate=25, weight=300.0, **kw):
        kw.setdefault('delta', 0.4)
        kw.setdefault('tau', 0.8)     # tasapaino 25/s: 25 x 0,4 x 0,8 = 8 bar
        super().__init__(**kw)
        self.throttle_set, self.dev_safe, self.weight = rate, False, weight

    def get_weight(self): return self.weight
    def get_weight_ms(self): return U.us // 1000
    def get_weight_limit(self): return 720.0
    def get_weight_rise_limit(self): return 250.0


def run(bd, press_s, seed=1, gc=True, stall_hz=5.0, stall_ms=(5, 15), devsafe_at=None):
    random.seed(seed)
    if gc: GC.enable()
    else: GC.disable()
    GC.start()
    t_call = U.us

    def sw():
        if devsafe_at is not None and U.us - t_call >= devsafe_at * 1e6:
            bd.dev_safe = True
        return U.us - t_call < press_s * 1e6

    out = io.StringIO()
    with redirect_stdout(out):
        asyncio.run(F.throttle_set_run(bd, U, E.Asyncio(stall_ms=stall_ms, stall_hz=stall_hz), E.Ratio(), sw))
    GC.disable()
    return out.getvalue(), t_call


def locked_strokes(bd, txt, t_call, settle_s=0.2):
    lock_ms = int(E.field(txt, 'KURI_END', 'lock_ms') or -1)
    if lock_ms < 0: return lock_ms, []
    t_lock = t_call + lock_ms * 1000 + settle_s * 1e6
    return lock_ms, [t for t in bd.plant.stroke_times if t >= t_lock]


def pattern_errors_25(st):
    """Iskujen valit jaksoina: kuviossa 25/s jokainen vali 2. Palauttaa poikkeavien valien maaran."""
    gaps = [round((b - a) / CYC) for a, b in zip(st, st[1:])]
    return sum(1 for g in gaps if g != 2), gaps


def main():
    fails = []

    def check(name, cond, detail=''):
        print('%s %s %s' % ('ok  ' if cond else 'FAIL', name, detail))
        if not cond:
            fails.append(name)

    # 1. 25/s, pysahdykset paalla (keruu + varaukset 5 Hz 5-15 ms), 4 siementa x 20 s: ei yhtaan vaaraa iskua lukituksen jalkeen
    for seed in (1, 2, 3, 4):
        bd = Bd(rate=25, phi_us=random.Random(seed).uniform(0, CYC))
        txt, t_call = run(bd, 20.0, seed=seed)
        lock_ms, st = locked_strokes(bd, txt, t_call)
        n_err, gaps = pattern_errors_25(st)
        check('1.%d lukittui (lock_ms=%d)' % (seed, lock_ms), 0 <= lock_ms < 3000, 'win=%s' % E.field(txt, 'KURI_END', 'win'))
        check('1.%d 25/s: kaikki iskuvalit 2 jaksoa' % seed, n_err == 0 and len(gaps) > 400,
              'virheet=%d valeja=%d muut=%s' % (n_err, len(gaps), sorted(set(gaps))))
        fw_err = int(E.field(txt, 'KURI_END', 'err') or -1)
        check('1.%d firmwaren err=0' % seed, fw_err == 0, 'err=%d lmax=%s' % (fw_err, E.field(txt, 'KURI_END', 'lmax')))
        filt = float(E.field(txt, 'KURI_END', 'filt') or 0)
        check('1.%d paine ~8 bar (25 x 0,4 x 0,8)' % seed, 7.0 < filt < 9.0, filt)

    # 2. Rasitus: varaukset 13-28 ms (tapaus 14:n tapaan) 10 Hz
    bd = Bd(rate=25, phi_us=7300.0)
    txt, t_call = run(bd, 20.0, seed=7, stall_hz=10.0, stall_ms=(13, 28))
    lock_ms, st = locked_strokes(bd, txt, t_call)
    n_err, gaps = pattern_errors_25(st)
    check('2 rasitus 13-28 ms 10 Hz: ei vaaria iskuja', n_err == 0 and len(gaps) > 400,
          'virheet=%d valeja=%d err=%s lmax=%s' % (n_err, len(gaps), E.field(txt, 'KURI_END', 'err'),
                                                  E.field(txt, 'KURI_END', 'lmax')))

    # 3. Ohjauskoe: paatokset nollakohdassa Z (kuri2-5:n pahin vaihe) -> virheita samoilla pysahdyksilla
    saved = F.KURI_OFF_US
    F.KURI_OFF_US = F.EU_OFF_US + 5000          # 18 600 us = Z
    try:
        bd = Bd(rate=25, phi_us=7300.0)
        txt, t_call = run(bd, 20.0, seed=7, stall_hz=10.0, stall_ms=(13, 28))
    finally:
        F.KURI_OFF_US = saved
    lock_ms, st = locked_strokes(bd, txt, t_call)
    n_err_bad, _ = pattern_errors_25(st)
    check('3 ohjauskoe: vaara vaihe (Z) tuottaa vaaria iskuja', n_err_bad > 5, 'virheet=%d' % n_err_bad)

    # 4. 24/s: 24 iskua jokaisessa 50 jakson ikkunassa, ei vierekkaisia iskuja
    bd = Bd(rate=24, phi_us=3100.0)
    txt, t_call = run(bd, 12.0, seed=11)
    lock_ms, st = locked_strokes(bd, txt, t_call)
    gaps = [round((b - a) / CYC) for a, b in zip(st, st[1:])]
    k = [0]
    for g in gaps: k.append(k[-1] + g)
    wins = [sum(1 for x in k if a <= x < a + 50) for a in range(0, k[-1] - 50, 7)] if k[-1] > 60 else []
    check('4 24/s: valit vain 2 tai 3 jaksoa', bool(gaps) and set(gaps) <= {2, 3}, sorted(set(gaps)))
    check('4 24/s: 24 iskua / 50 jaksoa', bool(wins) and min(wins) >= 23 and max(wins) <= 25,
          (min(wins or [0]), max(wins or [0])))

    # 5. Ennen lukitusta taysi sykli: ensimmaiset iskut 1 jakson valein, ei kytkentoja
    bd = Bd(rate=25, phi_us=11000.0)
    txt, t_call = run(bd, 3.0, seed=5)
    lock_ms = int(E.field(txt, 'KURI_END', 'lock_ms') or -1)
    pre = [t for t in bd.plant.stroke_times if t < t_call + lock_ms * 1000]
    pg = [round((b - a) / CYC) for a, b in zip(pre, pre[1:])]
    check('5 ennen lukitusta taysi sykli (valit 1 jakso)', lock_ms > 0 and bool(pg) and set(pg) == {1},
          (lock_ms, sorted(set(pg))))
    check('5 purku ennen pumppua ja KURI_START', 0 <= txt.find('MAINSCAL_VENT') < txt.find('KURI_START'), '')
    check('5 releet pois ja IDLE lopussa', bd.pump.v == 0 and bd.solenoid.v == 0 and bd.mode == 'IDLE',
          (bd.pump.v, bd.solenoid.v, bd.mode))
    n_fw = int(E.field(txt, 'KURI_END', 'n') or -1)
    check('5 firmwaren n = mallin iskut (+-2)', abs(n_fw - bd.plant.strokes) <= 2, (n_fw, bd.plant.strokes))

    # 6. Raaka ylipaine: pumppu pois, reason=overpressure
    bd = Bd(rate=25, delta=2.0, tau=3.0)     # tasapaino 25 x 2 x 3 = 150 bar -> ylittaa 11 bar
    txt, _ = run(bd, 8.0, seed=3)
    check('6 reason=overpressure', 'KURI_END reason=overpressure' in txt, E.field(txt, 'KURI_END', 'raw_max'))
    check('6 releet pois', bd.pump.v == 0 and bd.solenoid.v == 0)

    # 7. Kaukalo tayna: pumppu ei kaynnisty
    bd = Bd(rate=25, weight=730.0)
    txt, _ = run(bd, 1.0, seed=3)
    check('7 reason=tray, ei KURI_STARTia', 'KURI_END reason=tray' in txt and 'KURI_START' not in txt, txt.strip()[:80])
    check('7 pumppu ei kaynnistynyt', bd.plant.strokes == 0 and bd.pump.v == 0, bd.plant.strokes)

    # 8. dev_safe kesken ajon
    bd = Bd(rate=25)
    txt, _ = run(bd, 6.0, seed=3, devsafe_at=3.0)
    check('8 reason=devsafe', 'KURI_END reason=devsafe' in txt, E.field(txt, 'KURI_END', 'reason'))
    check('8 releet pois', bd.pump.v == 0 and bd.solenoid.v == 0)

    # 9. kuri:-komento
    import commands as C

    class Cb:
        command_known = True
        throttle_set = 0

        def set_setting_changed(self):
            pass

        def note_activity(self, now_ms, reason):    # handle_command wakes the standby (VALMIUSTILA)
            pass

    b = Cb()
    got = []
    for cmd in ('kuri:24', 'kuri:99', 'kuri:0'):
        C.handle_command(b, cmd)
        got.append(b.throttle_set)
    check('9 kuri:24 -> 24, kuri:99 -> 50, kuri:0 -> 0', got == [24, 50, 0] and b.command_known, got)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
