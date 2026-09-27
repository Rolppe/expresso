#!/usr/bin/env python3
"""uutto8_sovitus.py — 8 barin laitemalli olemassa olevista lokeista (EXPRESSO-UUTTO-8BAR, TILAUS-K vaiheet 3-4).

Malli (tilavuusvirtana, jotta 2,5 ja 8 bar ovat samaa fysiikkaa):
    isku tuo tilavuuden dV (pumpun kayra pmax: dV(p) = dV0 (1 - p/pmax))
    vuoto Q = k p^n                                       (kuristin: n = 1 laminaari, 0,5 aukko)
    jousto C(p) = c0 + 1/(1 + p)^2                        (vakio + kaasu/p_abs^2, suhteellinen)
Normitettu 2,5 bariin (kappa(p) = C(p)/C(2,5), f(p) = dV(p)/dV(2,5)):
    isku(p) = s25 f(p) / kappa(p),  vuoto(p) = (2,5/tau25) (p/2,5)^n / kappa(p)  [bar/s],
    taysi nousu(p) = [50 s25 f(p) - (2,5/tau25)(p/2,5)^n] / kappa(p),  pidon tarve(p) = tarve25 (p/2,5)^n / f(p)
    (jousto supistuu tarpeesta pois). Nykyinen smoke-malli (gas_bar) on c0 = 0, n = 1, pmax = inf: 8 barissa isku
    ~0,45 x (9/3,5)^2 ~ 3 bar.

Aineisto: ajot, joissa uutto ajettiin samalla kuristimen tilalla heti esiuuton jalkeen (24.9. b-e, 25.9. a-c, 26.9. b):
  - esiuuton pito: iskuosuus EU-rivien poistolaskurista (rm) pidon 1 s:sta loppuun -> tarve25, eli s25 tau25,
  - esiuuton katkaisu (EU_CUT p, rate) ja uuton nousu (TS-rivit, duty 1,00, 100 ms parit 2,5-7,2 bar): taysi nousu(p),
  - uuton pito (TS-rivit ensimmaisesta duty < 1 -rivista): vanhan saatimen keskipaine, min, max ja komennettu duty.
Vaihe 1: nousun pienimman neliosumman haku (per ajo tau25, yhteiset c0, n, pmax). Vaihe 2 ajaa vanhan uuttosilmukan
(run_shot bim:0, esiuutto_smoke-harness) mallilla ja vertaa TS-pitoon: n valitaan pidon keskipaineesta. Vanhan saatimen
komennettu duty on harhainen tarpeen mitta (17 ms pois-askel poistaa iskun nollaylitys-SSR:lla vain osan kerroista,
vsweep-a), siksi vertailu mallin kautta.

    python3 testit/uutto8_sovitus.py [--nopea]      (--nopea: vain vaihe 1)
"""
import math
import os
import re
import statistics as S
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LOGS = ['esiuutto-20260924-b-pim1.log', 'esiuutto-20260924-c-pim1.log', 'esiuutto-20260924-d-pim1.log',
        'esiuutto-20260924-e-pim1.log', 'esiuutto-20260925-a-pim1.log', 'esiuutto-20260925-b-pim1.log',
        'esiuutto-20260925-c-pim1.log', 'esiuutto-20260926-b-pim1.log']
C0_GRID = [0.0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.2, 1e3]
N_GRID = [1.0, 0.8, 0.7, 0.6, 0.5]
# Valinta tulosteen perusteella: n pidosta (vaihe 2: 0,8 rms 0,19 bar, 1,0 -> 0,69, 0,7 -> 0,30), c0 nousun rms:sta
# (n 0,8: 0,02-0,03 tasainen 2,91-2,92, 0 -> 3,30, 0,08 -> 3,25) ja vsweep-a:sta (10 ms tauon vaste 7,8 barissa -0,67...
# -0,76 bar = isku x ikkunakerroin ~0,7-0,8 -> isku ~0,85-1,1; c0 0,03 antaa tarve8 ~1 -ajoille 0,80-0,93)
C0, N_LEAK = 0.03, 0.8


def kappa(p, c0):
    return (c0 + 1.0 / (1.0 + p) ** 2) / (c0 + 1.0 / 3.5 ** 2)


def fpump(p, pm):
    return (1.0 - p / pm) / (1.0 - 2.5 / pm)


def parse(path):
    txt = open(path).read().splitlines()
    d = {'name': os.path.basename(path)[9:19]}
    hold = None
    eu, ts = [], []
    for l in txt:
        if l.startswith('EU_CUT'):
            d['p_cut'] = float(re.search(r'p=(\S+)', l).group(1))
            d['rate_cut'] = float(re.search(r'rate=(\S+)', l).group(1))
        elif l.startswith('EU_HOLD'):
            hold = int(re.search(r't_ms=(\d+)', l).group(1))
        elif l.startswith('EU '):
            f = l.split()
            eu.append((int(f[1]), int(re.search(r'rm=(\d+)', l).group(1)), float(f[2])))
        elif l.startswith('TS ') and len(l.split()) > 6:
            f = l.split()
            try:
                ts.append((int(f[1]), float(f[2]), float(f[5])))
            except ValueError:
                pass
    h = [r for r in eu if hold is not None and r[0] >= hold + 1000]
    d['need25'] = 1.0 - (h[-1][1] - h[0][1]) / ((h[-1][0] - h[0][0]) / 20.0) if len(h) >= 5 else None
    rise = []
    for a, b in zip(ts, ts[1:]):
        if a[2] < 1.0 or b[2] < 1.0:
            break
        pm = (a[1] + b[1]) / 2
        if 2.5 <= pm <= 7.2:
            rise.append((pm, (b[1] - a[1]) / ((b[0] - a[0]) / 1000.0)))
    d['rise'] = rise
    first = next((i for i, r in enumerate(ts) if r[2] < 1.0), None)
    h8 = ts[first:] if first is not None else []
    d['hold8'] = (S.mean(r[1] for r in h8), min(r[1] for r in h8), max(r[1] for r in h8), S.mean(r[2] for r in h8)) \
        if len(h8) >= 3 else None
    return d


def rate_model(p, A, tau25, pm, c0, n):
    return (50.0 * A * fpump(p, pm) - 2.5 * (p / 2.5) ** n) / (tau25 * kappa(p, c0))


def tau25_ls(d, pm, c0, n):
    """Paras tau25 ajolle (lineaarinen 1/tau25:ssa), A = s25 tau25 = 2,5 / (50 tarve25). Havainnot: uuton nousu ja
    esiuuton katkaisu."""
    A = 2.5 / (50.0 * d['need25'])
    pts = list(d['rise']) + [(d['p_cut'], d['rate_cut'])]
    xs = [(50.0 * A * fpump(p, pm) - 2.5 * (p / 2.5) ** n) / kappa(p, c0) for p, _ in pts]
    ys = [r for _, r in pts]
    sxx = sum(x * x for x in xs)
    inv = sum(x * y for x, y in zip(xs, ys)) / sxx if sxx > 0 else 0.0
    res = [y - inv * x for x, y in zip(xs, ys)]
    return (1.0 / inv if inv > 0 else float('inf')), res, A


def rms(ds, pm, c0, n):
    k = sum(len(d['rise']) + 1 for d in ds)
    return math.sqrt(sum(sum(r * r for r in tau25_ls(d, pm, c0, n)[1]) for d in ds) / k)


def state(d, c0=C0, n=N_LEAK, pm=1e9):
    tau25, _, A = tau25_ls(d, pm, c0, n)
    s25 = A / tau25
    return dict(s25=s25, tau25=tau25, s8=s25 * fpump(8.0, pm) / kappa(8.0, c0),
                tau8=8.0 / ((2.5 / tau25) * (8.0 / 2.5) ** n / kappa(8.0, c0)),     # p / vuoto(p) 8 barissa
                need8=d['need25'] * (8.0 / 2.5) ** n / fpump(8.0, pm),
                r=[rate_model(p, A, tau25, pm, c0, n) for p in (3.0, 5.0, 7.0)])


def main(fast):
    ds = [parse(os.path.join(HERE, f)) for f in LOGS]
    ds = [d for d in ds if d['need25'] and d['need25'] > 0.02 and len(d['rise']) >= 2]
    k = sum(len(d['rise']) + 1 for d in ds)
    rs = [r for d in ds for _, r in d['rise']]
    print('ajoja %d, nousuhavaintoja %d + %d katkaisua; uuton nousu 2,5-7,2 bar mitattu mediaani %.1f bar/s (%.1f...%.1f)' % (
        len(ds), k - len(ds), len(ds), S.median(rs), min(rs), max(rs)))
    print('VAIHE 1: nousun jaannoksen rms (bar/s), rivit c0, sarakkeet n (pmax inf) ja n=1 pmax 15 bar')
    print('  c0      ' + ' '.join('n=%-5g' % n for n in N_GRID) + ' n=1,pmax15')
    for c0 in C0_GRID:
        print('  %-7g ' % c0 + ' '.join('%-7.2f' % rms(ds, 1e9, c0, n) for n in N_GRID) + ' %.2f' % rms(ds, 15.0, c0, 1.0))
    print('VALITTU c0=%g n=%g pmax=inf' % (C0, N_LEAK))
    print('%-10s %6s %6s %6s %6s %6s %6s | %s' % ('ajo', 'tarve', 'tau25', 's25', 's8', 'tau8', 'tarve8',
                                                 'taysi nousu 3/5/7 bar malli (mitattu nousu@p)'))
    rows = []
    for d in ds:
        st = state(d)
        rows.append(st)
        print('%-10s %6.3f %6.2f %6.3f %6.3f %6.2f %6.2f | %4.1f %4.1f %4.1f (%s)' % (
            d['name'], d['need25'], st['tau25'], st['s25'], st['s8'], st['tau8'], st['need8'], st['r'][0], st['r'][1],
            st['r'][2], ' '.join('%.1f@%.1f' % (r, p) for p, r in d['rise'])))
    print('isku 8 barissa %.2f-%.2f bar (mediaani %.2f), vuodon aikavakio p/vuoto 8 barissa %.2f-%.2f s, tarve 8 barissa '
          '%.2f-%.2f' % (min(r['s8'] for r in rows), max(r['s8'] for r in rows), S.median(r['s8'] for r in rows),
                         min(r['tau8'] for r in rows), max(r['tau8'] for r in rows),
                         min(r['need8'] for r in rows), max(r['need8'] for r in rows)))
    if fast:
        return
    validate([d for d in ds if d['hold8']])


def validate(ds, seeds=(1, 2, 3)):
    """VAIHE 2: vanha uuttosilmukka (bim:0) mallilla vs laitteen TS-pito eri n:n arvoilla."""
    import esiuutto_smoke as E
    print('VAIHE 2: vanha saadin mallissa (bim:0, jaksokohina 0,25, pysahdykset 5/s, %d siementa) vs laite: TS-pito '
          'p ka / min / max, komennettu duty ka' % len(seeds))
    for n in (1.0, 0.8, 0.7, 0.6, 0.5):
        errs = []
        for d in ds:
            st = state(d, n=n)
            res = []
            for seed in seeds:
                bd = E.BrewData(hold_s=3.0, phi_us=3100.0 * seed % 20000, delta=st['s25'], tau=st['tau25'], c0=C0,
                                leak_n=n, lag_us=10000, fill_us=300000, noise=0.02, cyc_sd=0.25)
                bd.learned_ff_pre, bd.eu_g_pre, bd.eu_coast_s, bd.eu_tau_pre = d['need25'], 0.0, 0.15, 0.0
                txt, _ = E.run_brew(bd, 10.0, bim=0, seed=seed, stall_hz=5.0)
                ts = [(float(l.split()[2]), float(l.split()[5])) for l in txt.splitlines() if l.startswith('TS ')]
                first = next((i for i, r in enumerate(ts) if r[1] < 1.0), None)
                h = ts[first:] if first is not None else []
                # Pumppu ei paase tavoitteeseen (duty 1 koko ajan): tasanne viimeisista riveista, min/max 0
                res.append((S.mean(r[0] for r in h), min(r[0] for r in h), max(r[0] for r in h), S.mean(r[1] for r in h))
                           if len(h) >= 3 else (S.mean(r[0] for r in ts[-10:]), 0.0, 0.0, 1.0))
            m = [S.mean(x[i] for x in res) for i in range(4)]
            errs.append(m[0] - d['hold8'][0])
            print('  n=%-4g %-10s malli %.2f / %.1f / %.1f, %.2f | laite %.2f / %.1f / %.1f, %.2f' % (
                n, d['name'], m[0], m[1], m[2], m[3], *d['hold8']))
        print('  n=%-4g pidon keskipaine malli - laite: ka %+.2f, rms %.2f bar' % (
            n, S.mean(errs), math.sqrt(S.mean(e * e for e in errs))))


if __name__ == '__main__':
    main('--nopea' in sys.argv)
