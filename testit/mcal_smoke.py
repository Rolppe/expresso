#!/usr/bin/env python3
"""mcal_smoke.py — holdout ajonaikaiselle taajuus- ja vaihemittaukselle (PWM-1G, TILAUS-F/G/H).

Mittari on laitosmalli, ei synteettinen sinifunktio: `psweep_dryrun.py` ajaa oikean firmware-
korutiinin laitosta vasten virtuaalikellolla, ja mallin verkkotaajuus asetetaan ympäristöstä
(`DRY_MAINS`). Testi kysyy yhden asian: löytääkö laite taajuuden, jonka malli sille antoi.

    python3 testit/mcal_smoke.py       RESULT: <n> failed

Toteuttaja ei muokkaa tätä tiedostoa (brief: must not).
"""

import asyncio
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pico'))
sys.path.insert(0, HERE)

import functions as F                     # noqa: E402
import commands as C                      # noqa: E402


def fields(line):
    return dict(p.split('=', 1) for p in line.split()[1:] if '=' in p)


def dry(mains_hz, p0=0.0, ms=2000, seed=1):
    """Ajaa mains_calibrate laitosmallilla, jonka verkkotaajuus on `mains_hz`."""
    os.environ['DRY_MAINS'] = '%.4f' % mains_hz
    import psweep_dryrun
    importlib.reload(psweep_dryrun)        # F_MAINS luetaan moduulin latauksessa
    out, dur, bd = psweep_dryrun.drive(
        lambda b, ut, aio: F.mains_calibrate(b, ut, aio, ms), 4.0, 5, p0, seed)
    return out, dur, bd


class CmdBD:
    def __init__(self):
        self.mcal_request = None
        self.mcal_abort = False

    def request_mains_calibration(self, ms):
        self.mcal_request = min(5000, max(500, int(ms)))
        self.mcal_abort = False

    def abort_mains_calibration(self):
        self.mcal_request = None
        self.mcal_abort = True


def main():
    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name)
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    have = callable(getattr(F, 'mains_calibrate', None))
    check('mains_calibrate on moduulitason korutiini', have)
    if not have:
        print('RESULT: %d failed' % len(fails))
        return 1

    # 1. Taajuus loytyy laitosmallista, jonka taajuuden testi asettaa (TILAUS-F)
    for want in (49.90, 50.10, 50.30):
        out, dur, bd = dry(want)
        line = [ln for ln in out.splitlines() if ln.startswith('MAINSCAL ')]
        check('MAINSCAL-rivi tulostuu (%.2f Hz)' % want, len(line) == 1,
              out.strip().splitlines()[-1] if out.strip() else '(tyhjä)')
        if not line:
            continue
        fl = fields(line[0])
        check('MAINSCAL kertoo f, phase_us, amp, conf, n (%.2f Hz)' % want,
              all(k in fl for k in ('f', 'phase_us', 'amp', 'conf', 'n')), line[0])
        if 'f' in fl:
            check('taajuus osuu 0,10 Hz:n päähän mallin arvosta (%.2f Hz)' % want,
                  abs(float(fl['f']) - want) <= 0.10, 'sai %s' % fl['f'])
        if 'phase_us' in fl:
            check('vaihe on verkkojakson sisällä (%.2f Hz)' % want,
                  0 <= float(fl['phase_us']) < 1e6 / want + 1, fl['phase_us'])
        check('tulos jää brew_dataan (%.2f Hz)' % want,
              abs(getattr(bd, 'mains_hz', 0.0) - want) <= 0.10, str(getattr(bd, 'mains_hz', None)))
        per = getattr(bd, 'mains_period_us', None)
        check('jakso on taajuuden käänteisluku (%.2f Hz)' % want,
              per is not None and abs(per - 1e6 / float(fl.get('f', want))) <= 1.0, str(per))

    # 2. Purkusykli (TILAUS-H): paineisesta jarjestelmasta useita kierroksia, tyhjasta yksi
    out, dur, bd = dry(50.10, p0=6.0)
    vent = [ln for ln in out.splitlines() if ln.startswith('MAINSCAL_VENT')]
    check('purkusykli raportoidaan', len(vent) == 1, str(vent))
    if vent:
        fl = fields(vent[0])
        check('purkusykli kertoo kierrokset ja paineen', 'cycles' in fl and 'bar' in fl, vent[0])
        if 'cycles' in fl:
            check('paineinen jarjestelma vaatii useamman kuin yhden kierroksen',
                  int(fl['cycles']) >= 2, vent[0])
    # venttiilin jaksotus: 0,5 s paalla, 0,2 s pois (kayttajan antamat ajat)
    edges = bd.solenoid.log
    ons = [t for t, v in edges if v == 1]
    offs = [t for t, v in edges if v == 0]
    if len(ons) >= 2 and len(offs) >= 1:
        on_len = offs[0] - ons[0]
        off_len = ons[1] - offs[0]
        check('venttiili on paalla 0,5 s', abs(on_len - 500000) <= 30000, '%d us' % on_len)
        check('venttiili on pois 0,2 s', abs(off_len - 200000) <= 30000, '%d us' % off_len)
    else:
        check('venttiili jaksottui vahintaan kahdesti', False,
              'reunoja %d' % len(edges))

    out0, dur0, bd0 = dry(50.10, p0=0.0)
    vent0 = [ln for ln in out0.splitlines() if ln.startswith('MAINSCAL_VENT')]
    if vent0 and 'cycles' in fields(vent0[0]):
        check('tyhjasta jarjestelmasta purku paattyy yhteen kierrokseen',
              int(fields(vent0[0])['cycles']) == 1, vent0[0])

    # 3. Kytkin ja dev_safe keskeyttavat ennen pumppua
    os.environ['DRY_MAINS'] = '50.1000'
    import psweep_dryrun
    importlib.reload(psweep_dryrun)
    bd, ut, aio, c = psweep_dryrun.make(4.0, 5, 0.0, 1)
    bd.brew.value(1)
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(F.mains_calibrate(bd, ut, aio, 500))
    out = buf.getvalue()
    check('kytkin paalla: ei MAINSCAL-tulosta', not [l for l in out.splitlines()
                                                     if l.startswith('MAINSCAL ')], out[:80])
    check('kytkin paalla: syy sanotaan', 'reason=switch' in out,
          out.strip().splitlines()[-1] if out.strip() else '(tyhjä)')
    check('kytkin paalla: pumppu ei kaynnistynyt', bd.pump.value() == 0)

    # 4. Komentojasennys
    bd = CmdBD(); C.handle_command(bd, 'mcal:2000')
    check('mcal:<ms> jonouttaa mittauksen', bd.mcal_request == 2000, str(bd.mcal_request))
    bd = CmdBD(); C.handle_command(bd, 'mcal:10')
    check('liian lyhyt pyynto rajautuu', bd.mcal_request == 500, str(bd.mcal_request))
    bd = CmdBD(); C.handle_command(bd, 'mcal:abc')
    check('kelvoton pyynto hylataan', bd.mcal_request is None, str(bd.mcal_request))
    bd = CmdBD(); C.handle_command(bd, 'mcal:stop')
    check('mcal:stop keskeyttaa', bd.mcal_abort and bd.mcal_request is None)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
