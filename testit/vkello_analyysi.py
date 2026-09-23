#!/usr/bin/env python3
"""vkello_analyysi.py — portillisen firmwaren (43e207a, vkello3) laitelokien analyysi
(EXPRESSO-VERKKOKELLO-LAITETESTI2).

VAATIMUS: TILAUS-B, TILAUS-G, TILAUS-H, TILAUS-I, TILAUS-J

`vkello_replay.py` todentaa korjauksen vanhoilla lokeilla simulaation kellolla. Tämä ajaa uudet
lokit firmwaren oman `Verkkokello`-luokan läpi portteineen: lokin z:t syötetään samassa
järjestyksessä, portin päätös lasketaan uudelleen (amplitudi, uudessa lokissa myös paine) ja sen on
täsmättävä lokin `gate`-kenttään (0 = päivitti, 1 = amplitudi, 2 = paine), ja kellon T:n on
täsmättävä lokin T:hen. Siitä saadaan mitattu reuna E = kellon reuna + z, joka ei riipu kellosta.
Verkon vaihe on E:hen sovitettu kolmannen asteen käyrä vakiotilan ikkunoista (portti läpi, tauon
jälkeiset 3 ikkunaa ja 5 s tauon 8 ikkunaa pois, paine ±1 bar ensimmäisen käyntijakson
mediaanista); toinen aste jätti ajossa e verkon vaelluksen jäännökseen (sd 673 → 449 us).
Kellon todellinen virhe = kellon ennuste ennen päivitystä miinus käyrä. Sama E ajetaan myös
paineportillisen firmwaren kellon läpi (`accept`), jolloin vanhat lokit todentavat korjauksen.

Raaka `|z| > 1000 us` lukittuna ei ole kellovirhe: z on yksittäisen ikkunan mittaus (kohina ~500 us).

TILAUS-G-aineisto: jäännös E − käyrä on väreilyn viiveen poikkeama vakiotilasta. Se tulostetaan
paineluokittain ja paineen suhteen sovitettuna. Nousun ikkunat (`VKELLO_R`, kello ei päivity)
verrataan käyrään, joka on lineaarinen sovitus käynnin ensimmäisiin 6 s:iin ja jatkettu taaksepäin.

    python3 testit/vkello_analyysi.py <loki>...      RESULT: <n> failed
"""

import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vkello_replay import load_fw, wrap  # noqa: E402

fails = []
PAT = re.compile(r'VKELLO w=\d+ t_ms=(\d+) z_us=(\S+) T_us=(\S+) d=\S+ sd_us=\S+ amp=(\S+) lock=(\d) '
                 r'p_bar=(\S+) gate=(\d)')
RPAT = re.compile(r'VKELLO_R w=\d+ t_ms=(\d+) z_us=(\S+) amp=(\S+) p_bar=(\S+)')
LONG_GAP_MS = 4000      # ikkunaväli, jota pidempi tauko on 5 s:n tauko (transientti 8 ikkunaa)
DEG = 3


def polyfit(x, y, deg):
    n = deg + 1
    M = [[sum(v ** (i + j) for v in x) for j in range(n)] + [sum(b * v ** i for v, b in zip(x, y))]
         for i in range(n)]
    for i in range(n):
        piv = max(range(i, n), key=lambda r: abs(M[r][i])); M[i], M[piv] = M[piv], M[i]
        for r in range(n):
            if r != i:
                f = M[r][i] / M[i][i]; M[r] = [a - f * b for a, b in zip(M[r], M[i])]
    co = [M[i][n] / M[i][i] for i in range(n)]
    return lambda v: sum(c * v ** i for i, c in enumerate(co))


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)


def parse(path):
    rows, rise, seg, k, prev, long_, events = [], [], 0, 0, None, False, []
    for line in open(path):
        m = RPAT.match(line)
        if m:
            rise.append({'t': int(m.group(1)) * 1000 - 4 * 20000.0, 'z': float(m.group(2)),
                         'amp': float(m.group(3)), 'p': float(m.group(4))})
            continue
        m = PAT.match(line)
        if not m:
            if line.startswith('VKELLO_'): events.append(line.split()[0])
            continue
        t_ms = int(m.group(1)); T = float(m.group(3))
        if prev is not None and t_ms - prev > 300: seg, k, long_ = seg + 1, 0, t_ms - prev > LONG_GAP_MS
        rows.append({'seg': seg, 'k': k, 'long': long_, 't': t_ms * 1000 - 4 * T, 'z': float(m.group(2)),
                     'T': T, 'amp': float(m.group(4)), 'lock': int(m.group(5)), 'p': float(m.group(6)),
                     'gate': int(m.group(7))})
        k += 1; prev = t_ms
        events.append('w')
    return rows, rise, events


def replay(vk, rows, curve, pgate):
    """Kello E:tä vastaan; palauttaa (lukittuja > LOCK_US, max, lukittuja, hylätyt)."""
    c = vk.Verkkokello(0)
    bad, mx, lk, rej = 0, 0.0, 0, 0
    for i, r in enumerate(rows):
        ti = int(round(r['t']))
        if i and c.locked(ti):
            e = abs(wrap(c.edge(ti) - curve[i])); lk += 1; mx = max(mx, e); bad += e > vk.LOCK_US
        z = wrap(r['E'] - c.edge(ti), c.T)
        g = c.accept(r['amp'], r['p']) if pgate else (0 if c.gate(r['amp']) else 1)
        if g == 0: c.update(ti, z)
        else: rej += 1
    return bad, mx, lk, rej


def field(path, tag, key):
    for line in open(path):
        if line.startswith(tag + ' '):
            m = re.search(r'\b%s=(\S+)' % key, line)
            if m: return m.group(1)
    return None


def analyse(vk, path):
    name = os.path.basename(path)
    rows, rise, events = parse(path)
    new_fw = field(path, 'VKELLO_END', 'pgated') is not None
    # 1. Firmwaren kello uudelleen: portti ja T täsmättävä lokiin.
    c = vk.Verkkokello(0)
    dT, gate_diff = 0.0, 0
    for r in rows:
        ti = int(round(r['t']))
        r['pre_edge'], r['pre_lock'] = c.edge(ti), c.locked(ti)
        r['E'] = r['pre_edge'] + r['z']
        g = c.accept(r['amp'], r['p']) if new_fw else (0 if c.gate(r['amp']) else 1)
        if g != r['gate']: gate_diff += 1
        if g == 0: c.update(ti, r['z'])
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
              if r['gate'] == 0 and r['k'] >= (8 if r['long'] else 3) and abs(r['p'] - p0) < 1.0]
    ta, tb = rows[0]['t'], rows[-1]['t']
    xs = [(r['t'] - ta) / (tb - ta) * 2 - 1 for r in rows]
    f = polyfit([xs[i] for i in steady], [p[i] for i in steady], DEG)
    curve = [f(x) for x in xs]
    for r, v, cv in zip(rows, p, curve): r['res'] = wrap(v - cv)
    sd_steady = statistics.pstdev([rows[i]['res'] for i in steady])
    print('INFO %s vakiotila: %d ikkunaa, paine %.2f bar (±1), jäännöksen sd %.0f us (käyrä aste %d)' % (
        name, len(steady), p0, sd_steady, DEG))

    # 3. Kellon todellinen virhe lukittuna, ennen päivitystä (ensimmäinen ikkuna on alkulukitus).
    locked = [(r, cv) for r, cv in zip(rows[1:], curve[1:]) if r['pre_lock']]
    errs = [abs(wrap(r['pre_edge'] - cv)) for r, cv in locked]
    bad = sum(e > vk.LOCK_US for e in errs)
    raw = [r for r in rows if r['lock'] == 1 and abs(r['z']) > 1000]
    pg = replay(vk, rows, curve, pgate=True)

    # 4. Nousun ikkunat: alkuperäinen kello (ei päivityksiä) + z; vertailu lineaariseen käyrään.
    c0 = vk.Verkkokello(0)
    early = [i for i in steady if rows[i]['t'] - ta < 6e6]
    for r in rise:
        v = (c0.edge(int(round(r['t']))) + r['z']) % 20000.0
        r['E'] = v
    if rise and len(early) >= 5:
        lf = polyfit([rows[i]['t'] / 1e6 for i in early], [p[i] for i in early], 1)
        for r in rise: r['res'] = wrap(r['E'] - lf(r['t'] / 1e6))
    return {'name': name, 'rows': rows, 'rise': rise, 'events': events, 'bad': bad,
            'max': max(errs) if errs else 0.0, 'locked': len(locked), 'n': len(rows) - 1, 'raw': len(raw),
            'raw_gated': sum(1 for r in raw if r['gate']), 'sd': sd_steady, 'p0': p0, 'pg': pg,
            'new_fw': new_fw}


def main(paths):
    vk = load_fw()
    ok_runs, all_rows = [], []
    for path in paths:
        st = analyse(vk, path)
        name, rows, ev = st['name'], st['rows'], st['events']
        reason = field(path, 'VKELLO_END', 'reason')
        rise = field(path, 'VKELLO_RISE', 'reason')
        vent_first = 'VKELLO_VENT' in ev and 'VKELLO_RISE' in ev and ev.index('VKELLO_VENT') < ev.index('VKELLO_RISE')
        gated_after = sum(1 for r in rows if r['seg'] >= 1 and r['gate'])
        gated_before = sum(1 for r in rows if r['seg'] == 0 and r['gate'])
        traja = ev.count('VKELLO_TRAJA')
        print('INFO %s END reason=%s hz=%s windows=%s gated=%s pgated=%s rebased=%s TRAJA=%d taukoja=%d' % (
            name, reason, field(path, 'VKELLO_END', 'hz'), field(path, 'VKELLO_END', 'windows'),
            field(path, 'VKELLO_END', 'gated'), field(path, 'VKELLO_END', 'pgated'),
            field(path, 'VKELLO_END', 'rebased'), traja, ev.count('VKELLO_RESTART')))
        check('%s VKELLO_VENT ennen nousua (TILAUS-H)' % name, vent_first,
              'cycles=%s bar=%s' % (field(path, 'VKELLO_VENT', 'cycles'), field(path, 'VKELLO_VENT', 'bar')))
        check('%s nousu päättyy tasanteeseen, ei noreach' % name, rise == 'plateau',
              'reason=%s bar=%s reach_ms=%s' % (rise, field(path, 'VKELLO_RISE', 'bar'),
                                               field(path, 'VKELLO_RISE', 'reach_ms')))
        check('%s portti hylkää tauon jälkeen, ei tasanteessa ennen ensimmäistä taukoa' % name,
              gated_after > 0 and gated_before == 0, 'tauon jälkeen %d, ennen %d' % (gated_after, gated_before))
        msg = '%d/%d lukittua > %d us, max %.0f us' % (st['bad'], st['locked'], vk.LOCK_US, st['max'])
        if st['new_fw']:
            check('%s kello lukittuna: todellinen virhe ≤ LOCK_US' % name, st['bad'] == 0, msg)
        else:   # vanha firmware (43e207a): tämä on korjattava vika, hyväksyntä on replay alla
            print('INFO %s kello lukittuna ilman paineporttia (43e207a): %s' % (name, msg))
        if not st['new_fw']:
            b, mx, lk, rej = st['pg']
            check('%s paineportilla (replay, 43e207a + P_GATE_BAR): todellinen virhe ≤ LOCK_US' % name, b == 0,
                  '%d/%d lukittua > %d us, max %.0f us, hylätty %d' % (b, lk, vk.LOCK_US, mx, rej))
        print('INFO %s raaka z: lukittuna |z| > 1000 us %d ikkunaa, joista gate=1 %d (z on mittaus, ei kellovirhe)'
              % (name, st['raw'], st['raw_gated']))
        print('INFO %s lupa %d/%d ikkunaa' % (name, st['locked'], st['n']))
        rs = ['%d:%+.0f' % (r['seg'], r['res']) for r in rows if r['seg'] >= 1 and r['k'] == 0]
        print('INFO %s tauon jälkeinen 1. ikkuna, jäännös us (segmentti:jäännös) %s' % (name, ' '.join(rs)))
        if reason == 'ok' and traja == 0: ok_runs.append((st, ev.count('VKELLO_RESTART')))
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
    rise = [r for st, _ in ok_runs for r in st['rise'] if 'res' in r]
    if rise:
        print('INFO TILAUS-G nousun ikkunat (VKELLO_R, käyrä jatkettu taaksepäin), paineluokittain:')
        for lo, hi in ((-1, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 10)):
            b = [r['res'] for r in rise if lo <= r['p'] < hi]
            if len(b) >= 3:
                print('INFO   %4.1f–%4.1f bar n=%3d ka %+6.0f us sd %5.0f us' % (
                    lo, hi, len(b), statistics.mean(b), statistics.pstdev(b)))
    xs, ys = [r['p'] for r in use], [r['res'] for r in use]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    rr = slope * (sxx / sum((y - my) ** 2 for y in ys)) ** 0.5
    print('INFO TILAUS-G lineaarinen sovitus: %+.0f us/bar, r=%.2f, n=%d' % (slope, rr, len(use)))
    series = sum(n for _, n in ok_runs) // 4
    check('vähintään 3 taukosarjaa ehjissä ajoissa (reason=ok, ei TRAJA)', series >= 3,
          '%d sarjaa: %s' % (series, ', '.join(st['name'] for st, _ in ok_runs)))
    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    sys.exit(main([os.path.join(HERE, a) if not os.path.isabs(a) and not os.path.exists(a) else a
                   for a in sys.argv[1:]]))
