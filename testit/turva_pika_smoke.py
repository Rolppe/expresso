#!/usr/bin/env python3
"""turva_pika_smoke.py — EXPRESSO-TURVA-PIKAKORJAUKSET (21.9.2026), paketit/TURVAKATO.md kohta 3.

Yksi tarkistus kutakin korjausta kohden, valelaitteella (psweep_dryrun) tai suoraan funktiolla:

1. fast_heatup ei kaadu NameErroriin ja jattaa kaikki releet pois myos virheessa
2. bt:/asetuslampotila yli 150 C hylataan
3. pgap-vali rajautuu 2000 ms:iin ja ajo katkeaa koko ajon kattoon
4. psweep-trimmaus: ylipaine katkaisee, ja keskeytyksen jalkeen pumppu jaa pois
5. mcal: ylipaine katkaisee kaappauksen
6. main.py: jokainen testikomento kulkee dev_run:n kautta (lammitin pois)

    python3 testit/turva_pika_smoke.py       RESULT: <n> failed
"""

import asyncio
import io
import os
import re
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
PICO = os.path.join(HERE, '..', 'pico')
sys.path.insert(0, PICO)
sys.path.insert(0, HERE)

import types                              # noqa: E402
sys.modules.setdefault('devsafe', types.SimpleNamespace(feed=lambda: None))   # machine-moduulia ei ole
import functions as F                     # noqa: E402
import commands as C                      # noqa: E402
import classes                            # noqa: E402
import psweep_dryrun as D                 # noqa: E402


def run(coro):
    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(coro)
    return buf.getvalue()


def main():
    fails = []

    def check(name, cond, extra=''):
        print(('ok   ' if cond else 'FAIL ') + name + (' — ' + extra if extra and not cond else ''))
        if not cond:
            fails.append(name)

    # 1. fast_heatup
    class HeatBD:
        def __init__(self):
            self.pump, self.sol, self.heater = D.Pin(None), D.Pin(None), D.Pin(None)
            self.n = 0
        def get_relays(self): return self.pump, self.sol, self.heater
        def get_boiler_temperature(self):
            self.n += 1
            if self.n > 3:
                raise RuntimeError('anturi kaatui')     # virhe kesken lammityksen
            return 20.0

    class FastAio:
        @staticmethod
        async def sleep(s): await asyncio.sleep(0)

    bd = HeatBD()
    err = None
    try:
        run(F.fast_heatup(None, FastAio, bd))
    except RuntimeError as e:
        err = e
    except NameError as e:
        err = e
    check('fast_heatup ei kaadu NameErroriin', not isinstance(err, NameError), repr(err))
    check('fast_heatup: virhe paasee kutsujalle', isinstance(err, RuntimeError), repr(err))
    check('fast_heatup: releet pois virheen jalkeen',
          (bd.pump.value(), bd.sol.value(), bd.heater.value()) == (0, 0, 0),
          str((bd.pump.value(), bd.sol.value(), bd.heater.value())))

    # 2. lampotilaraja
    for v, ok in ((93, True), (150, True), (151, False), (200, False), (0, False), (None, True)):
        try:
            classes._check_setpoint(v); got = True
        except ValueError:
            got = False
        check('asetusarvo %s %s' % (v, 'hyvaksytaan' if ok else 'hylataan'), got == ok)

    class TempBD:
        def __init__(self): self.brew_temperature = 97; self.setting_changed = False
        set_brew_temperature = classes.BrewData.set_brew_temperature
    tb = TempBD()
    with redirect_stdout(io.StringIO()):
        upd = C.handle_command(tb, 'bt:250')
    check('bt:250 ei muuta lampotilaa', tb.brew_temperature == 97, str(tb.brew_temperature))
    check('bt:250 ei kuittaa paivitetyksi', not upd, str(upd))
    with redirect_stdout(io.StringIO()):
        C.handle_command(tb, 'bt:94')
    check('bt:94 menee lapi', tb.brew_temperature == 94, str(tb.brew_temperature))

    # 3. pgap
    class GapCmd:
        pgap_n = pgap_spacing_ms = pgap_len_ms = pgap_phases = pgap_lo_us = pgap_hi_us = None
        def request_pressure_gap(self, t): self.t = t
        def abort_pressure_gap(self): pass
    g = GapCmd()
    C.handle_command(g, 'pgap:7:5:999999')
    check('pgap-vali rajautuu %d ms:iin' % F.PGAP_SPACING_MAX_MS,
          g.pgap_spacing_ms == F.PGAP_SPACING_MAX_MS, str(g.pgap_spacing_ms))

    bd, ut, aio, clk = D.make(4.0, 5, 0.0, 1)
    bd.pgap_abort = False
    bd.pgap_n = 60
    bd.pgap_spacing_ms = F.PGAP_SPACING_MAX_MS      # 60 x 2 s + nousu > katto
    out = run(F.pressure_gap_run(bd, ut, aio, 4.0))
    end = [l for l in out.splitlines() if l.startswith('PGAP_END')]
    check('pgap katkeaa koko ajon kattoon', end and 'reason=timeout' in end[0],
          end[0] if end else out[-200:])
    check('pgap: ajo ei ylita kattoa yli sekunnilla',
          clk.us / 1000 <= F.PGAP_RUN_MAX_MS + 1000, '%d ms' % (clk.us // 1000))
    check('pgap: pumppu pois lopuksi', bd.pump.value() == 0)

    # 4. psweep-trimmaus
    bd, ut, aio, clk = D.make(4.0, 5, 0.0, 1)
    bd.offset_ = -12.0                               # anturi nayttaa ~12 bar
    state, r = F.tray_guard_start(bd, ut)
    sensor = bd.pressure_sensor.pressure_sensor
    out = run(F._psweep_trim(bd, ut, aio, sensor, 1.0, 0.0, 20.0, state, 0, 0.0))
    check('trimmaus: ylipaine katkaisee', 'reason=overpressure' in out, out.strip())
    check('trimmaus: ylipaineen jalkeen pumppu pois', bd.pump.value() == 0)

    bd, ut, aio, clk = D.make(4.0, 5, 0.0, 1)
    state, r = F.tray_guard_start(bd, ut)
    bd.psweep_abort = True
    sensor = bd.pressure_sensor.pressure_sensor
    out = run(F._psweep_trim(bd, ut, aio, sensor, 1.0, 0.0, 4.0, state, 0, 0.0))
    check('trimmaus: keskeytys raportoidaan', 'reason=stop' in out, out.strip())
    check('trimmaus: keskeytyksen jalkeen pumppu pois', bd.pump.value() == 0)

    bd, ut, aio, clk = D.make(4.0, 5, 0.0, 1)
    state, r = F.tray_guard_start(bd, ut)
    sensor = bd.pressure_sensor.pressure_sensor
    out = run(F._psweep_trim(bd, ut, aio, sensor, 1.0, 0.0, 4.0, state, 0, 4.0))
    check('trimmaus: normaalisti pumppu jatkaa', 'reason=ok' in out and bd.pump.value() == 1,
          out.strip())

    # 5. mcal
    bd, ut, aio, clk = D.make(4.0, 5, 0.0, 1)
    bd.mcal_abort = False
    bd.offset_ = -12.0
    out = run(F.mains_calibrate(bd, ut, aio, 2000))
    check('mcal: ylipaine katkaisee', 'MAINSCAL_END reason=overpressure' in out,
          out.strip().splitlines()[-1] if out.strip() else '')
    check('mcal: pumppu pois', bd.pump.value() == 0)

    # 6. main.py: lammitin pois testikomentojen ajaksi
    src = open(os.path.join(PICO, 'main.py')).read()
    runs = re.findall(r'await (\w*(?:_run|mains_calibrate))\(', src)
    direct = [f for f in runs if f not in ('run_shot', 'dev_run')]
    check('main.py: ei suoria testiajokutsuja dev_run:n ohi', not direct, str(direct))
    check('main.py: dev_run sammuttaa lammittimen',
          re.search(r'async def dev_run\(coro\):\s*\n\s*RELAY_HEATER\.value\(0\)', src) is not None)
    check('main.py: 12 testikomentoa dev_run:n kautta', src.count('await dev_run(') == 12,
          str(src.count('await dev_run(')))

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
