#!/usr/bin/env python3
"""vkello_dpdt.py — TILAUS-G: väreilyn viiveen poikkeama selittyy paineen nousunopeudella (24.9.2026).

Ajaa lokit `vkello_analyysi.analyse()`:n läpi (E ja vakiotilan käyrä kuten hyväksynnässä) ja
vertaa ikkunan jäännöstä (E − käyrä = todellinen viive − LAG_US) selittäjiin: paine, vaje
tasanteesta, aika tauosta ja paineen nousunopeus. Nousunopeus lasketaan taaksepäin edellisestä
saman segmentin ikkunasta, koska firmware ei tunne seuraavaa ikkunaa.

    python3 testit/vkello_dpdt.py [loki ...]     oletuksena vkello-20260924-b ja -20260923-e/g/h
"""
import os
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vkello_analyysi as A

LOGS = ['vkello-20260924-b.log', 'vkello-20260923-e.log', 'vkello-20260923-g.log', 'vkello-20260923-h.log']
BINS = ((-99, -0.5), (-0.5, 0.5), (0.5, 2), (2, 4), (4, 7), (7, 12), (12, 99))


def lstsq(X, y):
    n = len(X[0])
    M = [[sum(r[i] * r[j] for r in X) for j in range(n)] + [sum(r[i] * v for r, v in zip(X, y))] for i in range(n)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]; M[r] = [u - f * v for u, v in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def windows(vk, path):
    st = A.analyse(vk, path)
    rows = st['rows']
    p0 = S.median([r['p'] for r in rows if r['seg'] == 0 and r['k'] >= 3])
    out = []
    for i, r in enumerate(rows):
        if i == 0 or 'res' not in r or (r['seg'] == 0 and r['k'] < 3):
            continue
        pr = rows[i - 1]
        if pr['seg'] != r['seg']:
            continue
        dp = (r['p'] - pr['p']) / ((r['t'] - pr['t']) / 1e6)
        out.append({'log': os.path.basename(path), 'p': r['p'], 'd': max(0.0, p0 - r['p']),
                    'k': min(r['k'], 20), 'dp': dp, 'res': r['res']})
    return out


def main(paths):
    import io
    from contextlib import redirect_stdout
    vk = A.load_fw()
    data = []
    for p in paths:
        with redirect_stdout(io.StringIO()):
            data += windows(vk, p)
    y = [x['res'] for x in data]
    print('ikkunoita %d, jäännöksen sd ilman mallia %.0f us' % (len(data), S.pstdev(y)))
    for keys in (['p'], ['d'], ['k'], ['dp'], ['dp', 'p'], ['dp', 'd']):
        X = [[1.0] + [x[k] for k in keys] for x in data]
        b = lstsq(X, y)
        r = [v - sum(bi * xi for bi, xi in zip(b, row)) for row, v in zip(X, y)]
        print('  %-6s sd %4.0f us  R2 %.3f  kertoimet %s' % (
            '+'.join(keys), S.pstdev(r), 1 - S.pvariance(r) / S.pvariance(y), [round(c, 1) for c in b]))
    logs = sorted({x['log'] for x in data})
    print('nousunopeus bar/s   kaikki (n, sd)        ' + '  '.join(l[7:17] for l in logs))
    for lo, hi in BINS:
        b = [x for x in data if lo <= x['dp'] < hi]
        if not b:
            continue
        per = []
        for l in logs:
            c = [x['res'] for x in b if x['log'] == l]
            per.append('%+6.0f(%3d)' % (S.mean(c), len(c)) if c else '     -     ')
        print('  %5.1f..%5.1f  %+6.0f us (%3d, %4.0f)  %s' % (
            lo, hi, S.mean(x['res'] for x in b), len(b), S.pstdev([x['res'] for x in b]), '  '.join(per)))
    return 0


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    sys.exit(main(sys.argv[1:] or [os.path.join(here, l) for l in LOGS]))
