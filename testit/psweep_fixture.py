#!/usr/bin/env python3
"""psweep_fixture.py — suunnittelijan holdout pyyhkäisyn analysaattorille (PWM-1B5, säännöt 9-12).

Rakentaa synteettisiä `psweep`-lokeja, joiden vastaus tunnetaan, ja tarkistaa mitä
`psweep_read.py` niistä lukee. Testaa neljä asiaa:

  1. monisegmenttinen loki hajoaa segmenteiksi ja portitetut erottuvat referenssisegmenteistä;
  2. invariantti `(PSKIP_DELAY(p) - p) mod 19960 us` on vakio, kun viive on vakio — tämä on
     paketin säännön 9 korjattu muoto (modulus on verkkojakso, ei portin jakso);
  3. verkkotaajuus luetaan referenssisegmentin omasta väreilystä hienohaulla;
  4. taajuusvirhe levittää taitosta mitatun verran (sääntö 12).

    python3 testit/psweep_fixture.py      RESULT: <n> failed

Toteuttaja ei muokkaa tätä tiedostoa (brief: must not).
"""

import math
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
READER = os.path.join(HERE, 'psweep_read.py')

FS = 1000.0
PERIOD_US = 39920
MAINS_US = 19960
SEG_MS = 2000
AMP = 0.30
TAU = 0.005
NOISE = 0.36
GAIN = 1.0
OFFSET = -0.99
RAW_A = 0.000314936
RAW_B = -3.522929


def bar_to_raw(bar):
    return int(round(((bar - OFFSET) / GAIN - RAW_B) / RAW_A))


def gate(i, phase_us):
    return 1 if ((i * 1000 + phase_us) % PERIOD_US) < MAINS_US else 0


def segment(f_true, phase_us, delay_s, seed, gated, base_bar=7.7):
    """Yksi segmentti raakalukemina: iskut verkkotaajuudella, portti näytteen indeksistä."""
    rnd = random.Random(seed)
    n = SEG_MS
    x = [0.0] * n
    k = 0
    while k / f_true < n / FS:
        t = k / f_true
        i = int(t * FS)
        if 0 <= i < n and (not gated or gate(i, phase_us)):
            t0 = t + delay_s
            for j in range(max(0, int(t0 * FS)), n):
                dt = j / FS - t0
                if dt < 0:
                    continue
                if dt > 8 * TAU:
                    break
                x[j] += AMP * math.exp(-dt / TAU)
        k += 1
    return [bar_to_raw(base_bar + v + rnd.gauss(0, NOISE)) for v in x]


def write_log(path, f_true=50.1, delay_s=0.009, n_phase=5, seed=1):
    phases = [k * PERIOD_US // n_phase for k in range(n_phase)]
    segs = [(None, 'off')] + [(p, 'on') for p in phases] + [(None, 'off')]
    with open(path, 'w') as f:
        f.write('PSWEEP_START segs=%d n=%d ms=%d target=7.70 period_us=%d on_us=%d\n'
                % (len(segs), n_phase, SEG_MS, PERIOD_US, MAINS_US))
        for k, (p, g) in enumerate(segs):
            head = ('PCAP_START rate=1000 n=%d settle=target gain=%.4f offset=%.3f seg=%d gate=%s'
                    % (SEG_MS, GAIN, OFFSET, k, g))
            if g == 'on':
                head += ' period_us=%d on_us=%d phase_us=%d' % (PERIOD_US, MAINS_US, p)
            f.write(head + '\n')
            vals = segment(f_true, p or 0, delay_s, seed * 10 + k, g == 'on')
            for r in range(len(vals) // 20):
                row = vals[r * 20:(r + 1) * 20]
                f.write('PCAP %d %d %s\n' % (r * 20, r * 20 * 1000,
                                             ' '.join(str(v) for v in row)))
            f.write('PCAP_END n=%d dur_us=%d pmax=8.50 seg=%d reason=ok\n'
                    % (len(vals), len(vals) * 1000, k))
            if k < len(segs) - 1:
                f.write('PSWEEP_TRIM seg=%d bar=7.70 ms=1200 reason=ok\n' % k)
        f.write('PSWEEP_END segs=%d dur_ms=%d reason=ok\n' % (len(segs), len(segs) * 3200))
    return phases


def read(path):
    r = subprocess.run([sys.executable, READER, path], capture_output=True, text=True)
    return r.stdout, r.returncode


def fields(line):
    return dict(p.split('=', 1) for p in line.split()[1:] if '=' in p)


def main():
    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name)
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    check('psweep_read.py on olemassa', os.path.exists(READER))
    if not os.path.exists(READER):
        print('RESULT: %d failed' % len(fails))
        return 1

    tmp = tempfile.mkdtemp(prefix='psweep')

    # 1. Rakenne
    log = os.path.join(tmp, 'sweep.log')
    phases = write_log(log, f_true=50.1, delay_s=0.009, n_phase=5, seed=1)
    out, rc = read(log)
    check('analysaattori palaa nollalla', rc == 0, 'rc=%d' % rc)
    segs = [ln for ln in out.splitlines() if ln.startswith('PSWEEP_SEGS')]
    check('PSWEEP_SEGS tulostuu', len(segs) == 1, str(len(segs)))
    if segs:
        fl = fields(segs[0])
        check('segmenttien määrä on 7', fl.get('n') == '7', segs[0])
        check('portitettuja on 5', fl.get('gated') == '5', segs[0])
        check('referenssejä on 2', fl.get('ref') == '2', segs[0])
    invs = [ln for ln in out.splitlines() if ln.startswith('PSKIP_INV')]
    check('jokaisesta portitetusta segmentistä tulee PSKIP_INV', len(invs) == 5, str(len(invs)))
    if len(invs) == 5:
        check('PSKIP_INV kertoo vaihesiirron, viiveen ja invariantin',
              all(all(k in fields(ln) for k in ('phase_us', 'delay_ms', 'inv_ms', 'amp', 'conf'))
                  for ln in invs), invs[0])
        check('vaihesiirrot ovat lokin omat',
              [int(fields(ln)['phase_us']) for ln in invs] == phases,
              str([fields(ln)['phase_us'] for ln in invs]))
        vals = [float(fields(ln)['inv_ms']) for ln in invs]
        check('invariantti on verkkojakson sisällä',
              all(0 <= v < MAINS_US / 1000.0 + 1e-6 for v in vals), str(vals))
        # ympyrähajonta: invariantti elää modulo verkkojakson
        m = MAINS_US / 1000.0
        ang = [2 * math.pi * v / m for v in vals]
        R = math.hypot(sum(math.cos(a) for a in ang) / 5.0, sum(math.sin(a) for a in ang) / 5.0)
        spread = math.sqrt(max(0.0, -2 * math.log(R))) * m / (2 * math.pi)
        check('invariantti on vakio kun viive on vakio (hajonta alle 3 ms)', spread < 3.0,
              'hajonta %.2f ms, arvot %s' % (spread, vals))

    # 2. Verkkotaajuus referenssisegmenteistä
    mains = [ln for ln in out.splitlines() if ln.startswith('PSWEEP_MAINS')]
    check('PSWEEP_MAINS tulostuu', len(mains) == 1, str(len(mains)))
    if mains:
        fl = fields(mains[0])
        check('PSWEEP_MAINS kertoo taajuuden ja hajonnan',
              'f' in fl and 'spread' in fl and 'from' in fl, mains[0])
        if 'f' in fl:
            check('taajuus osuu 0,08 Hz:n päähän synteettisestä 50,10:stä',
                  abs(float(fl['f']) - 50.10) <= 0.08, fl['f'])

    # 3. Sama loki toisella viiveellä: invariantti seuraa viivettä
    log2 = os.path.join(tmp, 'sweep2.log')
    write_log(log2, f_true=50.1, delay_s=0.014, n_phase=5, seed=2)
    out2, _ = read(log2)
    invs2 = [ln for ln in out2.splitlines() if ln.startswith('PSKIP_INV')]
    if len(invs) == 5 and len(invs2) == 5:
        m = MAINS_US / 1000.0
        def circmean(v):
            a = [2 * math.pi * x / m for x in v]
            return (math.atan2(sum(math.sin(t) for t in a), sum(math.cos(t) for t in a))
                    % (2 * math.pi)) * m / (2 * math.pi)
        d1 = circmean([float(fields(ln)['inv_ms']) for ln in invs])
        d2 = circmean([float(fields(ln)['inv_ms']) for ln in invs2])
        diff = (d2 - d1) % m
        check('5 ms suurempi viive siirtää invarianttia 5 ms (+-2 ms)', abs(diff - 5.0) <= 2.0,
              'siirtymä %.2f ms (%.2f -> %.2f)' % (diff, d1, d2))

    # 4. Taajuusvirhe levittää taitosta (sääntö 12)
    log3 = os.path.join(tmp, 'sweep3.log')
    write_log(log3, f_true=50.2, delay_s=0.009, n_phase=5, seed=3)
    out3, _ = read(log3)
    w0 = [ln for ln in out.splitlines() if ln.startswith('PSKIP_INV')]
    w3 = [ln for ln in out3.splitlines() if ln.startswith('PSKIP_INV')]
    if w0 and w3 and 'width_bins' in fields(w0[0]):
        b0 = sum(float(fields(ln)['width_bins']) for ln in w0) / len(w0)
        b3 = sum(float(fields(ln)['width_bins']) for ln in w3) / len(w3)
        check('0,1 Hz:n virhe leventää taitoksen huippua', b3 > b0,
              'leveys %.1f -> %.1f binia' % (b0, b3))
    else:
        check('PSKIP_INV kertoo taitoksen huipun leveyden (width_bins)', False,
              w0[0] if w0 else '(ei PSKIP_INV-rivia)')

    # 5. Portittamaton loki ei kelpaa pyyhkäisyksi
    log4 = os.path.join(tmp, 'plain.log')
    with open(log4, 'w') as f:
        f.write('PCAP_START rate=1000 n=20 settle=target gain=1.0 offset=-0.99 gate=off\n')
        f.write('PCAP 0 0 %s\n' % ' '.join(['30000'] * 20))
        f.write('PCAP_END n=20 dur_us=20000 pmax=5.00 reason=ok\n')
    out4, rc4 = read(log4)
    check('yksisegmenttinen pcap-loki torjutaan', rc4 != 0 and 'PSWEEP_NOSWEEP' in out4,
          'rc=%d %s' % (rc4, out4.strip().splitlines()[-1] if out4.strip() else ''))

    # 6. Itsetesti
    r = subprocess.run([sys.executable, READER, '--selftest'], capture_output=True, text=True)
    check('--selftest palaa nollalla', r.returncode == 0,
          r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:])

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
