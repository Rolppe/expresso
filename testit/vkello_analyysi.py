#!/usr/bin/env python3
"""vkello_analyysi.py — portillisen firmwaren (43e207a, vkello3) laitelokien analyysi
(EXPRESSO-VERKKOKELLO-LAITETESTI2).

VAATIMUS: TILAUS-B, TILAUS-G, TILAUS-H, TILAUS-I, TILAUS-J

`vkello_replay.py` todentaa korjauksen vanhoilla lokeilla simulaation kellolla. Tämä ajaa uudet
lokit firmwaren oman `Verkkokello`-luokan läpi portteineen: lokin z:t syötetään samassa
järjestyksessä, portin päätös lasketaan uudelleen amplitudista ja sen on täsmättävä lokin `gate`-
kenttään, ja kellon T:n on täsmättävä lokin T:hen. Siitä saadaan mitattu reuna E = kellon reuna + z.
Verkon vaihe on E:hen sovitettu toisen asteen käyrä vakiotilan ikkunoista (portti läpi, tauon
jälkeiset 3 ikkunaa ja 5 s tauon 8 ikkunaa pois, paine ±1 bar ensimmäisen käyntijakson mediaanista).
Kellon todellinen virhe = kellon ennuste ennen päivitystä miinus käyrä.

Raaka `|z| > 1000 us` lukittuna ei ole kellovirhe: z on yksittäisen ikkunan mittaus (kohina ~500 us).

TILAUS-G-aineisto: jäännös E − käyrä on väreilyn viiveen poikkeama vakiotilasta. Se tulostetaan
paineluokittain ja paineen suhteen sovitettuna.

    python3 testit/vkello_analyysi.py <loki>...      RESULT: <n> failed
"""

import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vkello_replay import load_fw, qfit, wrap  # noqa: E402

fails = []
PAT = re.compile(r'VKELLO w=\d+ t_ms=(\d+) z_us=(\S+) T_us=(\S+) d=\S+ sd_us=\S+ amp=(\S+) lock=(\d) '
                 r'p_bar=(\S+) gate=(\d)')


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)


def parse(path):
    rows, seg, k, prev, events = [], 0, 0, None, []
    for line in open(path):
        m = PAT.match(line)
        if not m:
            if line.startswith('VKELLO_'): events.append(line.split()[0])
            continue
        t_ms = int(m.group(1)); T = float(m.group(3))
        if prev is not None and t_ms - prev > 300: seg, k = seg + 1, 0
        rows.append({'seg': seg, 'k': k, 't': t_ms * 1000 - 4 * T, 'z': float(m.group(2)), 'T': T,
                     'amp': float(m.group(4)), 'lock': int(m.group(5)), 'p': float(m.group(6)),
                     'gate': int(m.group(7))})
        k += 1; prev = t_ms
        events.append('w')
    return rows, events


def field(path, tag, key):
    for line in open(path):
        if line.startswith(tag + ' '):
            m = re.search(r'\b%s=(\S+)' % key, line)
            if m: return m.group(1)
    return None


def analyse(vk, path):
    name = os.path.basename(path)
    rows, events = parse(path)
    # 1. Firmwaren kello uudelleen: portti ja T täsmättävä lokiin.
    c = vk.Verkkokello(0)
    dT, gate_diff = 0.0, 0
    for r in rows:
        ti = int(round(r['t']))
        r['pre_edge'], r['pre_lock'] = c.edge(ti), c.locked(ti)
        r['E'] = r['pre_edge'] + r['z']
        used = c.gate(r['amp'])
        if used != (r['gate'] == 0): gate_diff += 1
        if used: c.update(ti, r['z'])
        dT = max(dT, abs(c.T - r['T']))
    check('%s rekonstruktio: firmwaren T = lokin T' % name, dT < 0.5, 'suurin ero %.2f us' % dT)
    check('%s rekonstruktio: portin päätös = lokin gate' % name, gate_diff == 0, '%d eroa' % gate_diff)

    # 2. Verkon vaihekäyrä vakiotilasta.
    p, last = [], None
    for r in rows:
        v = r['E'] % 20000.0
        if last is not None: v += 20000.0 * round((last - v) / 20000.0)
        p.append(v); last = v
    p0 = statistics.median([r['p'] for r in rows if r['seg'] == 0])
    steady = [i for i, r in enumerate(rows)
              if r['gate'] == 0 and r['k'] >= (8 if r['seg'] == 4 else 3) and abs(r['p'] - p0) < 1.0]
    co = qfit([rows[i]['t'] / 1e6 for i in steady], [p[i] for i in steady])
    curve = lambda t: co[0] + co[1] * t / 1e6 + co[2] * (t / 1e6) ** 2
    for r, v in zip(rows, p): r['res'] = wrap(v - curve(r['t']))
    sd_steady = statistics.pstdev([rows[i]['res'] for i in steady])
    print('INFO %s vakiotila: %d ikkunaa, paine %.2f bar (±1), jäännöksen sd %.0f us' % (
        name, len(steady), p0, sd_steady))

    # 3. Kellon todellinen virhe lukittuna, ennen päivitystä (ensimmäinen ikkuna on alkulukitus).
    locked = [r for r in rows[1:] if r['pre_lock']]
    errs = [abs(wrap(r['pre_edge'] - curve(r['t']))) for r in locked]
    bad = sum(e > vk.LOCK_US for e in errs)
    raw = [r for r in rows if r['lock'] == 1 and abs(r['z']) > 1000]
    return {'name': name, 'rows': rows, 'events': events, 'bad': bad, 'max': max(errs) if errs else 0.0,
            'locked': len(locked), 'n': len(rows) - 1, 'raw': len(raw),
            'raw_gated': sum(r['gate'] for r in raw), 'sd': sd_steady, 'p0': p0}


def main(paths):
    vk = load_fw()
    ok_runs, all_rows = [], []
    for path in paths:
        st = analyse(vk, path)
        name, rows, ev = st['name'], st['rows'], st['events']
        reason = field(path, 'VKELLO_END', 'reason')
        rise = field(path, 'VKELLO_RISE', 'reason')
        vent_first = 'VKELLO_VENT' in ev and 'VKELLO_RISE' in ev and ev.index('VKELLO_VENT') < ev.index('VKELLO_RISE')
        gated_after = sum(r['gate'] for r in rows if r['seg'] >= 1)
        gated_before = sum(r['gate'] for r in rows if r['seg'] == 0)
        traja = ev.count('VKELLO_TRAJA')
        print('INFO %s END reason=%s hz=%s windows=%s gated=%s rebased=%s TRAJA=%d' % (
            name, reason, field(path, 'VKELLO_END', 'hz'), field(path, 'VKELLO_END', 'windows'),
            field(path, 'VKELLO_END', 'gated'), field(path, 'VKELLO_END', 'rebased'), traja))
        check('%s VKELLO_VENT ennen nousua (TILAUS-H)' % name, vent_first,
              'cycles=%s bar=%s' % (field(path, 'VKELLO_VENT', 'cycles'), field(path, 'VKELLO_VENT', 'bar')))
        check('%s nousu päättyy tasanteeseen, ei noreach' % name, rise == 'plateau',
              'reason=%s bar=%s reach_ms=%s' % (rise, field(path, 'VKELLO_RISE', 'bar'),
                                               field(path, 'VKELLO_RISE', 'reach_ms')))
        check('%s portti hylkää tauon jälkeen, ei tasanteessa ennen ensimmäistä taukoa' % name,
              gated_after > 0 and gated_before == 0, 'tauon jälkeen %d, ennen %d' % (gated_after, gated_before))
        check('%s kello lukittuna: todellinen virhe ≤ LOCK_US' % name, st['bad'] == 0,
              '%d/%d lukittua > %d us, max %.0f us' % (st['bad'], st['locked'], vk.LOCK_US, st['max']))
        print('INFO %s raaka z: lukittuna |z| > 1000 us %d ikkunaa, joista gate=1 %d (z on mittaus, ei kellovirhe)'
              % (name, st['raw'], st['raw_gated']))
        print('INFO %s lupa %d/%d ikkunaa' % (name, st['locked'], st['n']))
        rs = ['%d:%+.0f' % (r['seg'], r['res']) for r in rows if r['seg'] >= 1 and r['k'] == 0]
        print('INFO %s tauon jälkeinen 1. ikkuna, jäännös us (segmentti:jäännös) %s' % (name, ' '.join(rs)))
        if reason == 'ok' and traja == 0: ok_runs.append(st)
        for r in rows: r['run'] = name
        all_rows += rows

    # TILAUS-G: viiveen poikkeama paineen mukaan, kaikista portin läpäisseistä ikkunoista.
    print('INFO TILAUS-G viiveen poikkeama (E − vakiotilan käyrä) paineluokittain, portti läpi:')
    use = [r for r in all_rows if r['gate'] == 0 and r['k'] >= 1]
    for lo, hi in ((-1, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 10)):
        b = [r['res'] for r in use if lo <= r['p'] < hi]
        if len(b) >= 3:
            print('INFO   %4.1f–%4.1f bar n=%3d ka %+6.0f us sd %5.0f us' % (
                lo, hi, len(b), statistics.mean(b), statistics.pstdev(b)))
    xs, ys = [r['p'] for r in use], [r['res'] for r in use]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    rr = slope * (sxx / sum((y - my) ** 2 for y in ys)) ** 0.5
    print('INFO TILAUS-G lineaarinen sovitus: %+.0f us/bar, r=%.2f, n=%d' % (slope, rr, len(use)))
    check('vähintään 3 ehjää ajoa (reason=ok, ei TRAJA)', len(ok_runs) >= 3,
          ', '.join(s['name'] for s in ok_runs))
    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    sys.exit(main([os.path.join(HERE, a) if not os.path.isabs(a) and not os.path.exists(a) else a
                   for a in sys.argv[1:]]))
