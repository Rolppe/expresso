#!/usr/bin/env python3
"""vsweep_analyysi.py — taukojen vaihepyyhkäisyn (vsweep) tulkinta, TILAUS-K/L askel 1 (24.9.2026).

Jokaisesta tauosta vaste c = post1 − ennuste, jossa post1 on keskipaine 30–130 ms tauon alusta ja
ennuste jatkaa kahden 100 ms:n puoliskon (−200…−100, −100…0 ms) trendiä post1:n keskelle; kaikki
ikkunat ovat kokonaisia jaksoja. Tyhjien vertailujen (cond 20, ei taukoa) keskiarvo on trendi, joka
vähennetään. 20 ms tauko (cond 21) poistaa aina yhden iskun: sen vaste on yhden iskun mitta.

Tulostaa kohtakohtaisen taulukon (0–19 ms kellon reunasta) ja sovittaa 10 ms levyisen lohkon:
missä kohdissa 10 ms tauko poistaa iskun. Lohkon reunojen jyrkkyys kertoo SSR:n tyypin ja sen,
kuinka tarkasti yksittäinen tauko paljastaa vaiheen.

    python3 testit/vsweep_analyysi.py <loki> [...]
"""
import re
import statistics as S
import sys

PAT = re.compile(r'VSWEEP k=(\d+) cond=(\d+) off_us=(\d+) len_us=(\d+) act_us=(\S+) pre0=(\S+) pre=(\S+) post1=(\S+) '
                 r'post2=(\S+) dmin=(\S+) sd_us=(\S+) lock=(\d) T_us=(\S+)')
N_OFF, SHAM, FULL = 20, 20, 21


def parse(paths):
    rows = []
    for p in paths:
        for line in open(p):
            m = PAT.match(line)
            if m:
                g = m.groups()
                rows.append({'k': int(g[0]), 'cond': int(g[1]), 'off': int(g[2]), 'len': int(g[3]),
                             'act': float(g[4]), 'pre0': float(g[5]), 'pre': float(g[6]),
                             'post1': float(g[7]), 'post2': float(g[8]), 'dmin': float(g[9]),
                             'sd': float(g[10]), 'lock': int(g[11]), 'T': float(g[12]), 'log': p})
    return rows


def analyse(rows):
    """Palauttaa sanakirjan: trend, full, per_off {ms: (ka, n)}, lohko (alku, loppu, jyrkkyys)."""
    for r in rows:
        # Perustaso jatketaan trendina: puoliskojen keskipisteet -150 ja -50 ms, post1:n 80 ms,
        # joten ennuste = pre + (pre - pre0) * 130 / 100. Edellisen kuopan palautuminen (tau ~0,8 s)
        # on muuten mukana vasteessa.
        r['c'] = r['post1'] - (r['pre'] + (r['pre'] - r['pre0']) * 1.3)
    sham = [r['c'] for r in rows if r['cond'] == SHAM]
    trend = S.mean(sham) if sham else 0.0
    full = [r['c'] - trend for r in rows if r['cond'] == FULL]
    per = {}
    for o in range(N_OFF):
        v = [r['c'] - trend for r in rows if r['cond'] == o]
        if v:
            per[o] = (S.mean(v), len(v))
    out = {'trend': trend, 'sham_sd': S.pstdev(sham) if len(sham) > 1 else 0.0, 'n_sham': len(sham),
           'full': S.mean(full) if full else None, 'n_full': len(full), 'per': per,
           'act_err': max((abs((r['act'] - r['off'] + r['T'] / 2) % r['T'] - r['T'] / 2)
                           for r in rows if r['len'] > 0), default=0.0),
           'unlocked': sum(1 for r in rows if not r['lock'])}
    if len(per) == N_OFF:
        # 10 ms levyinen lohko (kiertyvä): alku s, jolla kahden tason ero on suurin
        vals = [per[o][0] for o in range(N_OFF)]
        best = None
        for s in range(N_OFF):
            inside = [vals[(s + i) % N_OFF] for i in range(10)]
            outside = [vals[(s + 10 + i) % N_OFF] for i in range(10)]
            score = S.mean(outside) - S.mean(inside)   # poistettu isku = negatiivinen vaste
            if best is None or score > best[0]:
                best = (score, s, S.mean(inside), S.mean(outside))
        score, s, lo, hi = best
        half = (lo + hi) / 2.0
        # jyrkkyys: kohtia, jotka ovat tasojen välissä (20–80 %)
        mid = sum(1 for v in vals if lo + 0.2 * (hi - lo) < v < lo + 0.8 * (hi - lo))
        out.update({'block_start_ms': s, 'block_end_ms': (s + 10) % N_OFF, 'level_in': lo,
                    'level_out': hi, 'contrast': score, 'mid': mid, 'half': half})
    return out


def main(paths):
    rows = parse(paths)
    if not rows:
        print('ei VSWEEP-rivejä'); return 1
    a = analyse(rows)
    print('taukoja %d, tyhjiä %d (trendi %+.3f bar, sd %.3f), 20 ms %d (vaste %s bar), lukitsematta %d, '
          'toteutuneen kohdan suurin virhe %.0f us' % (
              len(rows), a['n_sham'], a['trend'], a['sham_sd'], a['n_full'],
              '%+.3f' % a['full'] if a['full'] is not None else '-', a['unlocked'], a['act_err']))
    print('kohta ms  vaste bar (trendi pois)  n')
    for o in range(N_OFF):
        if o in a['per']:
            m, n = a['per'][o]
            bar = '#' * max(0, int(round(-m / 0.02)))
            print('  %2d      %+.3f  %2d  %s' % (o, m, n, bar))
    if 'block_start_ms' in a:
        print('lohko (10 ms tauko poistaa iskun): %d–%d ms kellon reunasta, tasot %+.3f / %+.3f bar, '
              'välitasoja %d/20 (0–2 = jyrkkä raja)' % (
                  a['block_start_ms'], a['block_end_ms'], a['level_in'], a['level_out'], a['mid']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
