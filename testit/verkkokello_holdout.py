#!/usr/bin/env python3
"""verkkokello_holdout.py — suunnittelijan holdout firmwaren kellomoduulille (brief VERKKOKELLO).

VAATIMUS: TILAUS-B, TILAUS-F, TILAUS-I, TILAUS-J

Tarkistaa, että `pico/verkkokello.py`:n `Verkkokello` on `verkkokello_sim.py`:n `KF3Clock`
(numeerisesti samoilla vakioilla), että ticks-arvojen ympärikierto ei muuta tulosta ja että
I/Q-polku lukee paineväreilystä oikean reunan tunnetulla viiveellä LAG_US. Fysiikka ja odotukset
on kirjoitettu tässä riippumattomasti toteutuksesta.

    python3 testit/verkkokello_holdout.py     RESULT: <n> failed, epänolla paluuarvo jos punaisia

Toteuttaja ei muokkaa tätä tiedostoa (brief: must not). Ympäristömuuttuja VKELLO_MODULE vaihtaa
testattavan tiedoston (suunnittelijan oma viitetoteutus holdoutin todentamiseen).
"""

import importlib.util
import inspect
import math
import os
import random
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verkkokello_sim as sim  # noqa: E402

MODULE = os.environ.get('VKELLO_MODULE') or os.path.join(HERE, '..', 'pico', 'verkkokello.py')
PERIOD = 1 << 30          # RP2040:n ticks_us kiertää 2^30:ssä
fails = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)


def load(wrap):
    """Lataa moduulin omalla utime-väärennöksellä; wrap=True: ticks kiertää 2^30:ssä."""
    u = types.ModuleType('utime')
    if wrap:
        u.ticks_diff = lambda a, b: ((a - b + PERIOD // 2) % PERIOD) - PERIOD // 2
        u.ticks_add = lambda a, b: (a + b) % PERIOD
    else:
        u.ticks_diff = lambda a, b: a - b
        u.ticks_add = lambda a, b: a + b
    u.ticks_us = lambda: 0
    sys.modules['utime'] = u
    spec = importlib.util.spec_from_file_location('verkkokello_%d' % wrap, MODULE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    if not os.path.exists(MODULE):
        check('moduuli olemassa', False, MODULE); return finish()
    vk = load(False)

    # 1. Vakiot: sama kuin simulaation valittu kokoonpano ja käyttäjän päätös 23.9.2026.
    want = dict(N_WIN=8, SIGMA1=1450.0, SIGMAW=500.0, Q_D=0.001, D0=0.04, T_START=20000.0,
                T_MIN=19950.0, T_MAX=20050.0, LAG_US=39000.0, LOCK_US=1000.0)
    bad = [k for k, v in want.items() if not hasattr(vk, k) or abs(float(getattr(vk, k)) - v) > 1e-9]
    check('vakiot', not bad, 'väärin tai puuttuu: %s' % ', '.join(bad) if bad else '')

    # 2. Numeerinen vastaavuus simulaation silmukassa: KF3Clock vs moduuli samalla syötteellä.
    class Adapter:
        def __init__(self):
            self.c = vk.Verkkokello(0)
            self.n, self.lock_us = vk.N_WIN, vk.LOCK_US
        T = property(lambda self: self.c.T)
        clamped = property(lambda self: self.c.traja)
        def pred(self, t): return self.c.edge(int(round(t)))
        def update(self, t_mid, z): self.c.update(int(round(t_mid)), z)
        def pump_restart(self): pass
        def locked(self, t): return self.c.locked(int(round(t)))

    worst = []
    for prof in ('vakio50.1', 'ramppi5mHz', 'ramppi20mHz'):
        for seed in (7, 1007, 2007):
            ref = sim.run(sim.KF3Clock(8, lock_us=sim.LOCK_KELLO_US, **sim.KF3_BEST), prof,
                          sim.NOISE['mitattu'], seed)
            got = sim.run(Adapter(), prof, sim.NOISE['mitattu'], seed)
            dp = abs(got['perm'] - ref['perm']) / max(1, ref['perm'])
            dm = abs(sim.pct(got['errs'], 0.5) - sim.pct(ref['errs'], 0.5))
            worst.append((dp, dm, got['false'] - ref['false'], prof, seed))
    w = max(worst)
    ok = all(dp <= 0.01 and dm <= 5.0 and abs(df) <= 2 for dp, dm, df, _, _ in worst)
    check('sama kuin KF3Clock simulaatiossa', ok,
          'suurin ero: lupa %.2f %%, p50 %.1f us, vääriä %+d (%s/%d)' % (100 * w[0], w[1], w[2], w[3], w[4]))

    # 3. Ympärikierto: sama päivityssarja suorana ja 2^30:n yli siirrettynä.
    vw = load(True)
    off = PERIOD - 3000000
    a, b = vk.Verkkokello(0), vw.Verkkokello(off)
    rnd = random.Random(3)
    t, err = 0, 0.0
    same_lock = True
    for i in range(120):
        t += 160000 if i % 20 else 2500000                 # välillä 2,5 s:n tauko
        z = rnd.gauss(0, 400) + (3000 if i == 0 else 0)
        a.update(t, z); b.update((t + off) % PERIOD, z)
        q = t + 80000
        ea, eb = a.edge(q), b.edge((q + off) % PERIOD)
        err = max(err, abs(((eb - (ea + off)) + PERIOD // 2) % PERIOD - PERIOD // 2))
        same_lock &= a.locked(q) == b.locked((q + off) % PERIOD)
    check('ticks-kierto 2^30', err <= 1 and same_lock, 'suurin reunaero %d us, lukko sama %s' % (err, same_lock))

    # 4. I/Q-polku: puhdas kosini, jonka reuna tunnetaan; paine x = c + A·cos(2π(t−e−LAG)/T).
    def run_iq(f_true, e0, amp, noise, secs, seed=11):
        rnd = random.Random(seed)
        T = 1e6 / f_true
        c = vk.Verkkokello(0)
        t = 0
        c.iq_start(t)
        while t < secs * 1e6:
            x = 7.0 + amp * math.cos(2 * math.pi * (t - e0 - vk.LAG_US) / T) + rnd.gauss(0, noise)
            c.iq_add(t, x)
            t += 1000
            if c.iq_ready(t):
                c.iq_close(t); c.iq_start(t)
        e = c.edge(t) - e0
        e = ((e + T / 2) % T) - T / 2
        return c, t, e, T

    c, t, e, T = run_iq(50.08, 7000, 0.3, 0.0, 3.0)
    check('I/Q ilman kohinaa: reuna', abs(e) <= 30, 'virhe %.1f us' % e)
    check('I/Q ilman kohinaa: jakso', abs(c.T - T) <= 0.5, 'T %.3f vs %.3f' % (c.T, T))
    c, t, e, T = run_iq(49.92, 15000, 0.3, 0.05, 5.0)
    check('I/Q kohinalla: reuna', abs(e) <= 150, 'virhe %.1f us' % e)
    check('I/Q kohinalla: lukko', c.locked(t), 'sd %.0f us' % c.sd_us(t))
    check('pito: lukko 0,1 s tauon jälkeen', c.locked(t + 100000), 'sd %.0f us' % c.sd_us(t + 100000))
    check('pito: ei lukkoa 10 s tauon jälkeen', not c.locked(t + 10000000),
          'sd %.0f us' % c.sd_us(t + 10000000))

    # 5. Amplitudiportti: heikko väreily ei päivitä kelloa.
    c, t, e, T = run_iq(50.05, 4000, 0.05, 0.0, 2.0)
    check('amplitudiportti', c.T == vk.T_START and not c.locked(t), 'T %.3f' % c.T)

    # 6. Jakson raja: ulospäin työntävä muutos nollataan, osumat lasketaan (VKELLO_TRAJA).
    c = vk.Verkkokello(0)
    t, inside = 0, True
    for i in range(80):
        t += 160000
        c.update(t, 3000.0 if i else 0.0)
        inside &= vk.T_MIN <= c.T <= vk.T_MAX and not (c.T >= vk.T_MAX and c.d > 0)
    check('jakson raja', inside and c.traja > 0, 'T %.3f d %.4f traja %d' % (c.T, c.d, c.traja))

    # 7. 1 kHz:n silmukka: iq_add ei laske trigonometriaa (brief Do 2).
    src = inspect.getsource(vk.Verkkokello.iq_add)
    check('iq_add ilman cos/sin-kutsua', 'cos(' not in src and 'sin(' not in src)
    return finish()


def finish():
    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
