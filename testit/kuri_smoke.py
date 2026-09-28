#!/usr/bin/env python3
"""kuri_smoke.py — kuristimen saatotila kuri:1 (kayttaja 28.9.2026, KAYTTAJAN-TIEDOT TILAUS-M).

Ajaa firmwaren `throttle_set_run`-korutiinin CPythonilla klamp_smoke.py:n valelaitteilla: uuttonappi
paalla -> pumppu joka toisella jaksolla (25 iskua/s) ja venttiili paalla, lammitin pois; nappi pois -> releet pois. Rajat: raaka
ylipaine, kaukalo ja dev_safe; rajan lauettua korutiini odottaa napin vapautusta. Lisaksi kuri:-komento.

    python3 testit/kuri_smoke.py        RESULT: <n> failed, epanolla paluuarvo jos punaisia
"""

import asyncio
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klamp_smoke as K
F = K.F


class Utime(K.Utime):
    def ticks_us(self):
        import time
        return int(time.monotonic() * 1000000)


def run(bd, press_s, release_after=None, devsafe_after=None):
    """Nappi paalle heti, pois press_s:n jalkeen. Palauttaa (tuloste, releiden tila napin aikana)."""
    seen = {}

    async def main():
        bd.brew.value(1)
        task = asyncio.ensure_future(F.throttle_set_run(bd, Utime(), K.Asyncio(), K.Ratio(), bd.brew.value))
        if devsafe_after is not None:
            await asyncio.sleep(devsafe_after)
            bd.dev_safe = True
        await asyncio.sleep(min(press_s, 0.3) if devsafe_after is None else 0.05)
        seen.update(pump=bd.pump.v, sol=bd.solenoid.v, heater=bd.heater.v, mode=bd.mode)
        # Pumpun kuvio: naytteet 1 ms valein 1 s ajan (paalla-osuus ~0,5)
        samples = []
        t_end = asyncio.get_event_loop().time() + min(1.0, max(0.0, press_s - 0.3))
        while asyncio.get_event_loop().time() < t_end:
            samples.append(bd.pump.v)
            await asyncio.sleep(0.001)
        seen['on_frac'] = (sum(samples) / len(samples)) if samples else None
        seen['pump_any'] = bool(samples) and max(samples) == 1
        await asyncio.sleep(max(0.0, press_s - 1.3))
        seen['done_before_release'] = task.done()
        bd.brew.value(0)
        await asyncio.wait_for(task, 2.0)

    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(main())
    return buf.getvalue(), seen


def main():
    fails = []

    def check(name, cond, detail=''):
        print('%s %s %s' % ('ok  ' if cond else 'FAIL', name, detail))
        if not cond:
            fails.append(name)

    # 1. Normaali saato: pumppu joka toisella 20 ms:n jaksolla koko napin ajan, filt lahestyy tasannetta, releet pois lopuksi
    bd = K.BrewData(p_full=lambda t: 9.0)
    bd.heater.value(1)
    out, seen = run(bd, 6.0)
    end = [l for l in out.splitlines() if l.startswith('KURI_END')]
    lines = [l for l in out.splitlines() if l.startswith('KURI t=')]
    check('1 KURI_START', 'KURI_START wmax=720' in out, out.splitlines()[:1])
    check('1 venttiili paalla, lammitin pois', seen.get('sol') == 1 and seen.get('heater') == 0, seen)
    check('1 pumpun paalla-osuus ~0,5 (joka toinen jakso)', seen.get('on_frac') is not None
          and 0.4 < seen['on_frac'] < 0.6, seen.get('on_frac'))
    n = int(K.field(end[0], 'n')) if end else 0
    check('1 iskuja ~25/s (6 s -> ~150)', 140 <= n <= 152, n)
    check('1 mode KURI napin aikana', seen.get('mode') == 'KURI', seen.get('mode'))
    check('1 reason=switch', end and 'reason=switch' in end[0], end)
    check('1 KURI-rivit ~200 ms valein', 25 <= len(lines) <= 31, len(lines))
    filt = float(K.field(end[0], 'filt')) if end else 0.0
    check('1 filt puolen tehon tasanteen lahella (9,0 x 0,5)', 3.9 < filt < 5.0, filt)
    check('1 releet pois ja IDLE lopussa', bd.pump.v == 0 and bd.solenoid.v == 0 and bd.mode == 'IDLE',
          (bd.pump.v, bd.solenoid.v, bd.mode))

    # 2. Raaka ylipaine: pumppu pois heti, korutiini odottaa napin vapautusta
    bd = K.BrewData(raw=int((11.5 - F.PCAP_RAW_B) / F.PCAP_RAW_A))
    out, seen = run(bd, 1.0)
    check('2 reason=overpressure', 'KURI_END reason=overpressure' in out, out.strip().splitlines()[-1:])
    check('2 pumppu pois ennen vapautusta', seen.get('pump') == 0 and not seen.get('pump_any'), seen)
    check('2 odottaa vapautusta', seen.get('done_before_release') is False, seen)
    check('2 releet pois', bd.pump.v == 0 and bd.solenoid.v == 0)

    # 3. Kaukalo tayna: pumppu ei kaynnisty lainkaan
    bd = K.BrewData(weight=730.0)
    out, seen = run(bd, 0.5)
    check('3 reason=tray, ei KURI_STARTia', 'KURI_END reason=tray' in out and 'KURI_START' not in out, out.strip())
    check('3 pumppu ei kaynnistynyt', seen.get('pump') == 0 and not seen.get('pump_any') and bd.pump.v == 0, seen)

    # 4. dev_safe kesken ajon
    bd = K.BrewData(p_full=lambda t: 9.0)
    out, seen = run(bd, 1.0, devsafe_after=0.3)
    check('4 reason=devsafe', 'KURI_END reason=devsafe' in out, out.strip().splitlines()[-1:])
    check('4 releet pois', bd.pump.v == 0 and bd.solenoid.v == 0)

    # 5. kuri:-komento
    import commands as C

    class Bd:
        command_known = True
        throttle_set = 0

        def set_setting_changed(self):
            pass

    b = Bd()
    C.handle_command(b, 'kuri:1')
    on = b.throttle_set
    C.handle_command(b, 'kuri:0')
    check('5 kuri:1 -> 1, kuri:0 -> 0', on == 1 and b.throttle_set == 0 and b.command_known, (on, b.throttle_set))

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
