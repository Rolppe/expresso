#!/usr/bin/env python3
"""vkello_replay.py — firmwaren verkkokello laitelokeilla vkello-20260923-{a,b,d} (EXPRESSO-VERKKOKELLO-KORJAUS).

VAATIMUS: TILAUS-B, TILAUS-I, TILAUS-J

Laitetesti 23.9.2026 antoi lukitun z-hajonnan 785–950 us ja lukkoja |z| > 1000 us. Lokissa on
jokaisen ikkunan z (mitattu reuna miinus kellon ennuste) ja kellon T. Kun lokin z:t ajetaan
simulaation KF3Clock-luokan läpi samoilla vakioilla, T täsmää lokiin (tarkistus 1). Siitä saadaan
kellosta riippumaton mitattu reuna E = ennuste + z jokaiselle ikkunalle. Verkon vaihe on E:hen
sovitettu toisen asteen käyrä vakiotilan ikkunoista (tauon jälkeiset 3 ikkunaa ja 5 s tauon 8
ikkunaa pois, koska niissä väreilyn viive on transientissa). Kellon todellinen virhe = ennuste
miinus käyrä.

Havainto, jonka korjaus todentaa: 5 s tauon jälkeen viive on 3,5–5,3 ms vakiotilaa suurempi ja
palautuu ~0,8 s:ssa, ja amplitudi on samalla 2–5-kertainen. Ilman porttia kello ottaa transientin
vastaan ja karkaa lukittuna 3–5 ms. Transienttiportilla (`pico/verkkokello.py` GATE_RATIO) lukittu
virhe pysyy alle LOCK_US:n.

    python3 testit/vkello_replay.py      RESULT: <n> failed
"""

import importlib.util
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verkkokello_sim as sim  # noqa: E402

LOGS = ['vkello-20260923-%s.log' % k for k in 'abd']
fails = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)


def load_fw():
    u = types.ModuleType('utime')
    u.ticks_diff = lambda a, b: a - b
    u.ticks_add = lambda a, b: a + b
    u.ticks_us = lambda: 0
    sys.modules['utime'] = u
    spec = importlib.util.spec_from_file_location('verkkokello_fw', os.path.join(HERE, '..', 'pico', 'verkkokello.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def windows(path):
    """[(segmentti, k, t_mid_us, z, T_log, amp)]; segmentti vaihtuu, kun ikkunoiden väli > 300 ms."""
    rows, seg, k, prev = [], 0, 0, None
    pat = re.compile(r'VKELLO w=\d+ t_ms=(\d+) z_us=(\S+) T_us=(\S+) d=\S+ sd_us=\S+ amp=(\S+)')
    for line in open(path):
        m = pat.match(line)
        if not m: continue
        t_ms, z, T, amp = int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
        if prev is not None and t_ms - prev > 300: seg, k = seg + 1, 0
        # iq_close tulostaa ikkunan lopussa; t_mid on puoli ikkunaa (N_WIN jaksoa) aiemmin
        rows.append((seg, k, t_ms * 1000 - 4 * T, z, T, amp)); k += 1; prev = t_ms
    return rows


def wrap(e, T=20000.0):
    return e - T * round(e / T)


def qfit(x, y):
    S = [sum(v ** p for v in x) for p in range(5)]
    b = [sum(yy * v ** p for v, yy in zip(x, y)) for p in range(3)]
    M = [[S[0], S[1], S[2], b[0]], [S[1], S[2], S[3], b[1]], [S[2], S[3], S[4], b[2]]]
    for i in range(3):
        for r in range(3):
            if r != i:
                f = M[r][i] / M[i][i]
                M[r] = [a - f * c for a, c in zip(M[r], M[i])]
    return [M[i][3] / M[i][i] for i in range(3)]


def truth(rows):
    """Mitattu reuna E ja verkon vaihekäyrä; palauttaa (E-lista, käyrä, T:n suurin ero lokiin)."""
    c = sim.KF3Clock(8, lock_us=sim.LOCK_KELLO_US, **sim.KF3_BEST)
    E, dT = [], 0.0
    for seg, k, t, z, T_log, amp in rows:
        E.append(c.pred(t) + z)
        c.update(t, z)
        dT = max(dT, abs(c.T - T_log))
    p, last = [], None
    for e in E:                        # avaa jaksokierto
        v = e % 20000.0
        if last is not None: v += 20000.0 * round((last - v) / 20000.0)
        p.append(v); last = v
    steady = [i for i, r in enumerate(rows) if r[1] >= (8 if r[0] == 4 else 3)]
    co = qfit([rows[i][2] / 1e6 for i in steady], [p[i] for i in steady])
    return E, (lambda t: co[0] + co[1] * t / 1e6 + co[2] * (t / 1e6) ** 2), dT


def replay(vk, rows, E, curve, gated):
    c = vk.Verkkokello(0)
    st = {'locked': 0, 'bad': 0, 'max': 0.0, 'n': 0, 'rej0': 0}
    for (seg, k, t, _, _, amp), e in zip(rows, E):
        ti = int(round(t))
        if not (seg == 0 and k == 0):      # ensimmäinen ikkuna on alkulukitus
            st['n'] += 1
            if c.locked(ti):
                err = abs(wrap(c.edge(ti) - curve(t)))
                st['locked'] += 1; st['max'] = max(st['max'], err)
                if err > vk.LOCK_US: st['bad'] += 1
        z = wrap(e - c.edge(ti), c.T)
        if not gated: c.update(ti, z)
        elif c.gate(amp): c.update(ti, z)
        elif seg == 0: st['rej0'] += 1
    st['gated'] = getattr(c, 'gated', 0)
    return st


def main():
    vk = load_fw()
    check('portin vakiot', getattr(vk, 'GATE_RATIO', None) == 2.0 and getattr(vk, 'GATE_MAX', None) == 20,
          'GATE_RATIO %s GATE_MAX %s' % (getattr(vk, 'GATE_RATIO', None), getattr(vk, 'GATE_MAX', None)))
    if not hasattr(vk.Verkkokello(0), 'gate'): check('Verkkokello.gate olemassa', False); return finish()

    # Portin logiikka: transientti hylätään, pysyvä amplitudimuutos hyväksytään GATE_MAX:n jälkeen.
    c = vk.Verkkokello(0)
    first = [c.gate(0.4) for _ in range(5)]
    burst = [c.gate(1.5) for _ in range(6)]
    back = c.gate(0.45)
    check('portti: vakiotila läpi, transientti hylätään, paluu läpi', all(first) and not any(burst) and back,
          'vakio %s transientti %s paluu %s' % (first, burst, back))
    c = vk.Verkkokello(0)
    c.gate(0.3)
    seq = [c.gate(1.8) for _ in range(vk.GATE_MAX + 2)]
    check('portti: pysyvä muutos hyväksytään %d. hylkäyksen kohdalla' % vk.GATE_MAX,
          not any(seq[:vk.GATE_MAX - 1]) and all(seq[vk.GATE_MAX - 1:]) and c.rebased == 1,
          'ensimmäinen läpi %s, rebased %d' % (seq.index(True) + 1 if True in seq else None, c.rebased))

    for name in LOGS:
        rows = windows(os.path.join(HERE, name))
        E, curve, dT = truth(rows)
        check('%s rekonstruktio: KF3Clock-T = lokin T' % name, dT < 0.5, 'suurin ero %.2f us' % dT)
        base = replay(vk, rows, E, curve, gated=False)
        got = replay(vk, rows, E, curve, gated=True)
        check('%s ilman porttia lukittuja virheitä (testi erottelee)' % name, base['bad'] > 0,
              '%d lukittua > LOCK_US, max %.0f us' % (base['bad'], base['max']))
        check('%s portilla ei lukittuja virheitä > LOCK_US' % name, got['bad'] == 0,
              '%d, max %.0f us, hylätty %d' % (got['bad'], got['max'], got['gated']))
        check('%s portti ei hylkää ikkunoita tasanteessa ennen ensimmäistä taukoa' % name, got['rej0'] == 0,
              '%d hylätty' % got['rej0'])
        print('INFO %s lupa %d/%d ikkunaa portilla, %d/%d ilman (simulaatio 85 %% käyntiajasta)' % (
            name, got['locked'], got['n'], base['locked'], base['n']))
    return finish()


def finish():
    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
