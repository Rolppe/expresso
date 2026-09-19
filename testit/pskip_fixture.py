#!/usr/bin/env python3
"""pskip_fixture.py — suunnittelijan holdout analysaattorille pskip_delay.py (PWM-1B3).

Rakentaa synteettisiä portitettuja pcap-lokeja, joiden oikea vastaus tiedetään, ja ajaa
`pskip_delay.py`:n niitä vasten erillisenä prosessina. Fikstuurin fysiikka on kirjoitettu tässä
riippumattomasti spec:stä `PWM-1B3-ANALYSAATTORI.spec.md` kohta 3, jotta analysaattori ei voi
läpäistä testiä kopioimalla omaa oletustaan.

    python3 testit/pskip_fixture.py          RESULT: <n> failed, epänolla paluuarvo jos punaisia
    python3 testit/pskip_fixture.py --write <hakemisto>   kirjoittaa fikstuurit ja lopettaa

Toteuttaja ei muokkaa tätä tiedostoa (brief: must not).
"""

import math
import os
import random
import subprocess
import sys
import tempfile

A, B = 0.000314936, -3.522929      # tehdaskaava, classes.py:930
T_US, GATE_US = 19960, 39920       # mitattu verkkojakso ja portin jakso
RATE_US, N = 1000, 1500
HERE = os.path.dirname(os.path.abspath(__file__))


def synth(delay_us, mains_off_us=0, phase_us=0, gated=True, seed=1, gain=1.0, offset=-0.99):
    """Paine bar-sarjana: pohja laskee eksponentiaalisesti, läpi päässyt isku lisää pulssin."""
    rnd = random.Random(seed)
    bars = []
    for i in range(N):
        t = i * float(RATE_US)
        p = 7.7 - 0.8 * (1.0 - math.exp(-t / 810000.0))
        k = 0
        while True:
            tk = k * T_US + mains_off_us
            if tk > t:
                break
            passed = True if not gated else (((tk + phase_us) % GATE_US) < T_US)
            if passed and t >= tk + delay_us:
                p += 0.30 * math.exp(-(t - tk - delay_us) / 3000.0)
            k += 1
        bars.append(p + rnd.gauss(0.0, 0.36))
    raw = [max(0, min(65535, int(round(((b - offset) / gain - B) / A)))) for b in bars]
    return raw


def write_log(path, raw, phase_us, gated=True, gain=1.0, offset=-0.99):
    n = len(raw)
    with open(path, 'w') as fh:
        if gated:
            fh.write('PCAP_START rate=1000 n=%d settle=target gain=%.4f offset=%.3f '
                     'gate=on period_us=%d on_us=%d phase_us=%d\n'
                     % (n, gain, offset, GATE_US, T_US, phase_us))
        else:
            fh.write('PCAP_START rate=1000 n=%d settle=target gain=%.4f offset=%.3f gate=off\n'
                     % (n, gain, offset))
        for r in range(n // 20):
            vals = ' '.join(str(v) for v in raw[r * 20:(r + 1) * 20])
            fh.write('PCAP %d %d %s\n' % (r * 20, r * 20 * RATE_US, vals))
        fh.write('PCAP_END n=%d dur_us=%d pmax=8.00 reason=ok\n' % (n, (n - 1) * RATE_US))
    return path


def run_analyzer(path):
    r = subprocess.run([sys.executable, os.path.join(HERE, 'pskip_delay.py'), path],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def delay_of(out):
    for line in out.splitlines():
        if line.startswith('PSKIP_DELAY'):
            return float(line.split()[1])
    return None


def main():
    if '--write' in sys.argv:
        d = sys.argv[sys.argv.index('--write') + 1]
        write_log(os.path.join(d, 'fix-d9.log'), synth(9000), 0)
        print('kirjoitettu ' + d)
        return 0

    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name)
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    tmp = tempfile.mkdtemp(prefix='pskip-')

    # 1. Viive kolmella arvolla, vaihesiirto 0
    for d_ms in (3, 9, 15):
        p = write_log(os.path.join(tmp, 'd%d.log' % d_ms), synth(d_ms * 1000), 0)
        rc, out = run_analyzer(p)
        got = delay_of(out)
        check('D=%d ms: analysaattori palautti PSKIP_DELAY' % d_ms, got is not None, out.strip()[:200])
        if got is not None:
            check('D=%d ms: viive 2,0 ms sisalla' % d_ms, abs(got - d_ms) <= 2.0, 'sai %.1f' % got)
        check('D=%d ms: paluuarvo 0' % d_ms, rc == 0, 'rc=%d' % rc)

    # 2. Verkon vaihesiirto nakyy yhdistelmana (saanto 5): D=3 ms, mains_off=7 ms -> 10 ms
    p = write_log(os.path.join(tmp, 'off7.log'), synth(3000, mains_off_us=7000), 0)
    rc, out = run_analyzer(p)
    got = delay_of(out)
    check('mains_off 7 ms nostaa viiveen 10 ms:iin', got is not None and abs(got - 10.0) <= 2.0,
          'sai %s' % got)

    # 3. Toistettavuus kolmella siemenella
    seen = []
    for seed in (1, 7, 11):
        p = write_log(os.path.join(tmp, 's%d.log' % seed), synth(9000, seed=seed), 0)
        rc, out = run_analyzer(p)
        seen.append(delay_of(out))
    check('kolme siementa antavat saman binin', all(v is not None for v in seen)
          and (max(seen) - min(seen)) <= 1.0, str(seen))

    # 4. Kalibrointi: offset ei saa siirtaa viivetta (boxcar poistaa DC:n)
    p1 = write_log(os.path.join(tmp, 'cal-a.log'), synth(9000, offset=-0.99), 0, offset=-0.99)
    p2 = write_log(os.path.join(tmp, 'cal-b.log'), synth(9000, offset=0.0), 0, gain=1.0, offset=0.0)
    d1, d2 = delay_of(run_analyzer(p1)[1]), delay_of(run_analyzer(p2)[1])
    check('offset ei muuta viivetta', d1 is not None and d1 == d2, '%s vs %s' % (d1, d2))

    # 5. Portittamaton loki torjutaan otsikon perusteella
    raw = synth(9000, gated=False)
    p = write_log(os.path.join(tmp, 'nogate.log'), raw, 0, gated=False)
    rc, out = run_analyzer(p)
    check('portittamaton loki torjutaan', rc != 0 and 'PSKIP_NOGATE' in out, out.strip()[:200])

    # 6. Vaihesiirto siirtaa raportoitua viivetta tasan itsensa verran, koska taitto lasketaan
    # portin nousevasta reunasta: mitattu viive = (D + phase_us) mod GATE_US. Laiteajossa juuri
    # taman invariantin sailyminen erottaa hydraulisen viiveen SSR:n kvantisoinnista (saanto 5).
    p = write_log(os.path.join(tmp, 'ph10.log'), synth(9000, phase_us=10000), 10000)
    got = delay_of(run_analyzer(p)[1])
    check('vaihesiirto 10 ms nostaa viiveen 19 ms:iin', got is not None and abs(got - 19.0) <= 2.0,
          'sai %s' % got)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
