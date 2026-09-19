#!/usr/bin/env python3
"""psweep_mult_smoke.py — holdout portin jakson kertoimelle (PWM-1B6, sääntö 14).

Kuivaharjoitus osoitti, että portin jakso 39,92 ms on lyhyempi kuin koneen 70-90 ms:n viive ja
taitos kiertää ympäri. Mittausportti on siis lyhyt pulssi pitkässä ikkunassa: **yksi verkkojakso
päällä, `mult`-1 pois**. Tämä testaa kertoimen päästä päähän, myös komentojäsennyksen, jota
`psweep_smoke.py` ei kata.

    python3 testit/psweep_mult_smoke.py      RESULT: <n> failed

Toteuttaja ei muokkaa tätä tiedostoa (brief: must not).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pico'))
sys.path.insert(0, HERE)

import functions as F                     # noqa: E402
import commands as C                      # noqa: E402
import psweep_smoke as S                  # noqa: E402  — sama valelaite, ei kopiota


def starts(out):
    return [dict(p.split('=', 1) for p in ln.split()[1:] if '=' in p)
            for ln in out.splitlines() if ln.startswith('PCAP_START')]


class CmdBD:
    """Pelkkä komentojäsennyksen vastaanottaja: vain ne kentät, joita psweep-haara koskee."""

    def __init__(self):
        self.psweep_request = None
        self.psweep_abort = False
        self.psweep_target_bar = None
        self.psweep_n = None
        self.psweep_mult = None

    def request_pressure_sweep(self, ms):
        self.psweep_request = min(2500, max(200, int(ms)))
        self.psweep_abort = False

    def abort_pressure_sweep(self):
        self.psweep_request = None
        self.psweep_abort = True


def main():
    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name)
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    M = F.PCAP_MAINS_US
    LONG = 8 * M

    # 1. Vakiot
    check('PSWEEP_MULT_DEFAULT on 2', getattr(F, 'PSWEEP_MULT_DEFAULT', None) == 2,
          str(getattr(F, 'PSWEEP_MULT_DEFAULT', None)))
    check('PSWEEP_MULT_MAX on 16', getattr(F, 'PSWEEP_MULT_MAX', None) == 16,
          str(getattr(F, 'PSWEEP_MULT_MAX', None)))

    # 2. pcap_gate ottaa jakson parametrina, oletus ennallaan (sääntö 6)
    try:
        F.pcap_gate(0, 0, LONG)
        takes_period = True
    except TypeError:
        takes_period = False
    check('pcap_gate ottaa period_us-parametrin', takes_period)
    if takes_period:
        bad = [i for i in range(4000)
               if F.pcap_gate(i, 0) != (1 if ((i * F.PCAP_RATE_US) % F.PCAP_GATE_PERIOD_US) < M else 0)]
        check('oletusjakso käyttäytyy kuten ennen', not bad, 'ensimmäinen ero %s' % (bad[:1],))
        duty = sum(F.pcap_gate(i, 0, LONG) for i in range(8000)) / 8000.0
        check('pitkällä jaksolla duty on 1/8', abs(duty - 0.125) <= 0.01, '%.3f' % duty)
        # Portin jakso on 159,68 naytetta, ei kokonaisluku: yksi paallaolo on 20 naytetta ja
        # lohkojen vali vuorottelee 159/160 naytteen valilla. Naiden on oltava erillisia
        # vaitteita, koska 400 nayteen ikkunaan mahtuu 2,5 jaksoa (korjaus 1).
        g = [F.pcap_gate(i, 0, LONG) for i in range(8000)]
        first = 0
        while first < len(g) and g[first]:
            first += 1
        check('ensimmäinen päälläolo on tasan yksi verkkojakso', first == 20 and g[0] == 1,
              'päällä %d näytettä alusta' % first)
        rises = [i for i in range(1, len(g)) if g[i] and not g[i - 1]]
        gaps = set(b - a for a, b in zip([0] + rises, rises))
        check('lohkojen väli on 159 tai 160 näytettä', gaps <= {159, 160}, str(sorted(gaps)))
        check('lohkoja on 8000 näytteessä 50 kappaletta', abs(len(rises) + 1 - 50) <= 1,
              'lohkoja %d' % (len(rises) + 1))
        lens = []
        run = 0
        for v in g:
            if v:
                run += 1
            elif run:
                lens.append(run); run = 0
        check('jokainen päälläolo on 19 tai 20 näytettä', set(lens) <= {19, 20},
              str(sorted(set(lens))))

    # 3. psweep_phases jakaa annetun jakson yli
    try:
        ph = F.psweep_phases(5, LONG)
        ok = list(ph) == [k * LONG // 5 for k in range(5)]
    except TypeError:
        ok = False
        ph = None
    check('psweep_phases(n, period_us) jakaa annetun jakson', ok, str(ph))
    check('psweep_phases(n) ilman jaksoa ennallaan',
          list(F.psweep_phases(5)) == [k * F.PCAP_GATE_PERIOD_US // 5 for k in range(5)])

    # 4. Komentojäsennys (psweep_smoke ei kata tätä)
    bd = CmdBD(); C.handle_command(bd, 'psweep:2000:4.0:5:8')
    check('kerroin luetaan viidennestä kentästä', bd.psweep_mult == 8, str(bd.psweep_mult))
    check('kerroin ei riko muita kenttiä',
          bd.psweep_target_bar == 4.0 and bd.psweep_n == 5 and bd.psweep_request == 2000,
          '%s %s %s' % (bd.psweep_target_bar, bd.psweep_n, bd.psweep_request))
    bd = CmdBD(); C.handle_command(bd, 'psweep:2000:4.0:5:1')
    check('kerroin rajautuu alhaalta kahteen', bd.psweep_mult == 2, str(bd.psweep_mult))
    bd = CmdBD(); C.handle_command(bd, 'psweep:2000:4.0:5:99')
    check('kerroin rajautuu ylhäältä kuuteentoista', bd.psweep_mult == 16, str(bd.psweep_mult))
    bd = CmdBD(); C.handle_command(bd, 'psweep:2000:4.0:5')
    check('ilman kenttää kerroin on None (oletus ajossa)', bd.psweep_mult is None,
          str(bd.psweep_mult))
    bd = CmdBD(); C.handle_command(bd, 'psweep:2000:4.0:5:abc')
    check('kelvoton kerroin nollaa koko pyynnön',
          bd.psweep_mult is None and bd.psweep_target_bar is None and bd.psweep_request is None,
          '%s %s %s' % (bd.psweep_mult, bd.psweep_target_bar, bd.psweep_request))
    bd = CmdBD(); C.handle_command(bd, 'psweep:stop')
    check('stop nollaa kertoimen', bd.psweep_mult is None and bd.psweep_abort)

    # 5. Ajo pitkällä jaksolla
    bd = S.BrewData(target=4.9, n=2)
    bd.psweep_mult = 8
    out = S.run(bd, 400)
    hs = starts(out)
    check('pitkällä jaksolla segmenttejä on yhä n+2', len(hs) == 4, str(len(hs)))
    gated = [h for h in hs if h.get('gate') == 'on']
    check('otsikko kertoo pitkän jakson',
          all(h.get('period_us') == str(LONG) for h in gated),
          str([h.get('period_us') for h in gated]))
    check('otsikko kertoo päälläolon yhtenä verkkojaksona',
          all(h.get('on_us') == str(M) for h in gated), str([h.get('on_us') for h in gated]))
    check('otsikko kertoo kertoimen', all(h.get('mult') == '8' for h in gated),
          str([h.get('mult') for h in gated]))
    check('PSWEEP_START kertoo kertoimen', 'mult=8' in out, out.splitlines()[0] if out else '')
    last = out.strip().splitlines()[-1] if out.strip() else '(tyhjä)'
    check('pitkän jakson ajo päättyy ok', 'reason=ok' in last, last)
    edges = [v for _, v in bd.pump.log]
    check('pumppu kytkeytyi pitkälläkin jaksolla', len(edges) >= 6, 'reunoja %d' % len(edges))

    # 6. Oletus ennallaan
    bd = S.BrewData(target=4.9, n=2)
    out = S.run(bd, 400)
    gated = [h for h in starts(out) if h.get('gate') == 'on']
    check('ilman kerrointa jakso on entinen',
          all(h.get('period_us') == str(F.PCAP_GATE_PERIOD_US) for h in gated),
          str([h.get('period_us') for h in gated]))

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
