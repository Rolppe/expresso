#!/usr/bin/env python3
"""verkkokello_sim.py — isäntäsimulaatio sisäiselle verkkojaksokellolle (EXPRESSO-VERKKOKELLO).

VAATIMUS: TILAUS-A, TILAUS-B, TILAUS-F, TILAUS-G, TILAUS-I, TILAUS-J

Suunnitelma `paketit/VERKKOKELLO.md`, brief `paketit/VERKKOKELLO.brief.md`. Simuloi kellon
jakson tasolla: verkon jaksot kulkevat taajuusprofiilin mukaan 49,9–50,1 Hz, pumppu käy ja on
tauolla aikataulun mukaan (tauot 0,5–10 s), ja jokaisesta käyvästä jaksosta saadaan paineesta luettu
vaihe, jossa on mitattu kohina. Kellot samalla syötteellä:

  PI  — suunnitelman kohta 3: kiinteä PI-silmukka, lukko = M peräkkäistä ikkunaa |e| < raja.
        Vertailu: lukkosääntö ei erota lukkoa kohinasta.
  KF  — kaksitilainen Kalman-suodin (vaihe, jakso). Vertailu: ylivarma verkon rampissa.
  KF3 — valittu: kolmitilainen (vaihe, jakso, jakson muutos). Vahvistus seuraa omaa epävarmuuttaan,
        joten alkulukitus, kapea seuranta ja tauon jälkeinen paluu ovat sama kaava. Lukko = kellon
        oma vaiheen epävarmuus 2,5·sd < lukkoraja, ennustettuna kysymyshetkeen (myös tauon aikana).
        Firmwaren `pico/verkkokello.py` on tämän luokan käännös (brief VERKKOKELLO).

Kohinamalli on mitattu, ei oletettu (`/tmp`-analyysi 23.9.2026 kaappauksista
pcap-20260919-8bar/-tasanne/-verkkotaajuus, täysi pumppu, 2 s, jaksokohtainen I/Q):
  yhden jakson vaiheen hajonta 571–1441 us, 8 jakson ikkunan 295–616 us, 32 jakson 98–402 us.
  Hajonta ei laske puhtaasti 1/sqrt(N):llä, ja nousevassa paineessa (tasanne) peräkkäisten
  jaksojen korrelaatio on 0,65 → malli = valkoinen jaksokohina SIGMA1 + hidas vaellus (OU) SIGMAW.

Mittari on aina TODELLINEN virhe: kellon ennustama jakson alku miinus oikea jakson alku.
Tunnetun viiveen 37–41 ms (TILAUS-I) vähennys on vakio-offset, joka ei vaikuta seurantaan; sen
epävarmuus ±2 ms siirtää koko kehystä eikä näy tässä (ks. brief, kohta "Kehys").

    python3 testit/verkkokello_sim.py            skenaariotaulukko + RESULT: <n> failed
    python3 testit/verkkokello_sim.py --sweep    PI- ja KF-parametrien pyyhkäisy
"""

import math
import random
import sys

STEP_US = 832            # 1b:n vaiheaskel (REKISTERI.md, 10 vaiheen hajontamittaus)
LOCK_US = STEP_US / 4    # hyväksyntä: vaihevirhe lukittuna < 1/4 vaiheaskelta (VERKKOKELLO.md)
T_MIN, T_MAX = 19950.0, 20050.0   # suunnitelman kohta 3: alue + marginaali; raja on vika
T_START = 20000.0        # TILAUS-F: uutto aloitetaan 50 Hz:llä

# Pumpun aikataulu: esiuuton paineennosto 6 s (TILAUS-G), sitten tauko + 4 s käyntiä.
PAUSES_S = [0.5, 1, 2, 5, 10, 0.5, 2, 10, 1, 5]
FIRST_ON_S, ON_S = 6.0, 4.0

NOISE = {   # nimi: (SIGMA1 us, SIGMAW us, TAUW s, LAGSHIFT us)
    'mitattu':   (1000.0, 150.0, 0.5, 0.0),     # 8bar/verkkotaajuus-tyyppinen
    'huonoin':   (1450.0, 400.0, 1.0, 0.0),     # tasanne: korreloitu vaellus
    'rasitus':   (2000.0, 400.0, 1.0, 500.0),   # + viiveen siirtymä tauon jälkeen, 1 s palautuminen
}


def profile(name):
    """Verkon taajuus ajan funktiona (s -> Hz)."""
    if name == 'vakio49.9': return lambda t: 49.9
    if name == 'vakio50.1': return lambda t: 50.1
    if name == 'ramppi5mHz': return lambda t: min(50.1, 49.9 + 0.005 * t)
    if name == 'ramppi20mHz': return lambda t: 50.05 - 0.02 * min(max(t - 20.0, 0.0), 7.5)
    raise ValueError(name)

PROFILES = ['vakio49.9', 'vakio50.1', 'ramppi5mHz', 'ramppi20mHz']


def schedule():
    """[(alku_s, loppu_s)] pumpun käyntijaksot."""
    on, t = [(0.0, FIRST_ON_S)], FIRST_ON_S
    for p in PAUSES_S:
        t += p; on.append((t, t + ON_S)); t += ON_S
    return on, t


def wrap(e, T):
    return e - T * round(e / T)


class PIClock:
    """Suunnitelman kohta 3: vaihe Kp·e, jakso Ki·e/N, muutosrajat ja jakson rajat."""
    def __init__(self, n, kp=0.15, ki=0.012, e_lock=400.0, m_lock=3, lock_us=LOCK_US):
        self.n, self.kp, self.ki, self.e_lock, self.m_lock = n, kp, ki, e_lock, m_lock
        self.lock_us = lock_us     # vain mittarin raja: PI:n lukkosääntö ei tiedä siitä
        self.t_ref, self.T, self.good, self.clamped = 0.0, T_START, 0, 0
        self.acq = True            # ensimmäinen ikkuna asettaa vaiheen suoraan

    def pred(self, t):
        return self.t_ref + self.T * round((t - self.t_ref) / self.T)

    def update(self, t_mid, z):
        self.t_ref = self.pred(t_mid)
        if self.acq:
            self.t_ref += z; self.acq = False; return
        self.t_ref += max(-200.0, min(200.0, self.kp * z))
        self.T += max(-2.0, min(2.0, self.ki * z / self.n))
        if not T_MIN <= self.T <= T_MAX:
            self.clamped += 1; self.T = max(T_MIN, min(T_MAX, self.T))
        self.good = self.good + 1 if abs(z) < self.e_lock else 0

    def pump_restart(self):
        self.good = 0              # kohta 6: täysiä jaksoja, kunnes lukko on palannut

    def locked(self, t):
        return self.good >= self.m_lock


class KFClock:
    """Tila (vaihe = t_ref, jakso T), kovarianssi P. Ennuste jaksoina m: t_ref += m·T."""
    def __init__(self, n, sigma1=1450.0, sigmaw=300.0, q_t=0.05, q_phi=0.0, lock_us=LOCK_US):
        self.n, self.lock_us = n, lock_us
        self.r = sigma1 * sigma1 / n + sigmaw * sigmaw      # ikkunan mittauskohina, us^2
        self.q_t, self.q_phi = q_t * q_t, q_phi * q_phi     # per jakso: jakson ja vaiheen vaellus
        self.t_ref, self.T = 0.0, T_START
        self.P = [[1e8, 0.0], [0.0, 45.0 ** 2]]             # vaihe tuntematon; T 49,9–50,1 ~ ±40 us
        self.clamped = 0

    def pred(self, t):
        return self.t_ref + self.T * round((t - self.t_ref) / self.T)

    def _grow(self, m):
        (a, b), (_, d) = self.P
        m2 = abs(m)
        return [[a + 2 * m * b + m * m * d + self.q_phi * m2, b + m * d],
                [b + m * d, d + self.q_t * m2]]

    def update(self, t_mid, z):
        m = round((t_mid - self.t_ref) / self.T)
        self.t_ref += m * self.T
        P = self._grow(m)
        s = P[0][0] + self.r
        k0, k1 = P[0][0] / s, P[1][0] / s
        self.t_ref += k0 * z; self.T += k1 * z
        self.P = [[(1 - k0) * P[0][0], (1 - k0) * P[0][1]],
                  [P[1][0] - k1 * P[0][0], P[1][1] - k1 * P[0][1]]]
        if not T_MIN <= self.T <= T_MAX:
            self.clamped += 1; self.T = max(T_MIN, min(T_MAX, self.T))

    def pump_restart(self):
        pass                       # epävarmuus on jo kasvanut tauon ajan

    def sd_at(self, t):
        return math.sqrt(max(0.0, self._grow((t - self.t_ref) / self.T)[0][0]))

    def locked(self, t):
        return 2.5 * self.sd_at(t) < self.lock_us


class KF3Clock:
    """Kolmitilainen: vaihe t_ref, jakso T ja jakson muutos d (us/jakso) — verkon taajuus liikkuu
    rampeissa, ja tauon aikana vaihe karkaa r·t²/2 (VERKKOKELLO.md kohta 5). Prosessikohina on
    d:n vaellus q_d per jakso (valkoinen nykäys), joten tauon epävarmuus kasvaa kuten m^5.
    d = 0,04 us/jakso vastaa 5 mHz/s (T² · r / 1e6 / 50)."""
    def __init__(self, n, sigma1=1450.0, sigmaw=300.0, q_d=0.002, d0=0.04, lock_us=LOCK_US):
        self.n, self.lock_us = n, lock_us
        self.r = sigma1 * sigma1 / n + sigmaw * sigmaw
        self.q = q_d * q_d
        self.t_ref, self.T, self.d = 0.0, T_START, 0.0
        self.P = [[1e8, 0.0, 0.0], [0.0, 45.0 ** 2, 0.0], [0.0, 0.0, d0 * d0]]
        self.clamped = 0

    def _m(self, t):
        return (t - self.t_ref) / self.T

    def pred(self, t):
        m = round(self._m(t))
        return self.t_ref + m * self.T + self.d * m * m / 2

    def _grow(self, m):
        F = [[1.0, m, m * m / 2], [0.0, 1.0, m], [0.0, 0.0, 1.0]]
        a = abs(m)
        Q = [[a ** 5 / 20, a ** 4 / 8, a ** 3 / 6], [a ** 4 / 8, a ** 3 / 3, a * a / 2],
             [a ** 3 / 6, a * a / 2, a]]
        FP = [[sum(F[i][k] * self.P[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        return [[sum(FP[i][k] * F[j][k] for k in range(3)) + self.q * Q[i][j] for j in range(3)]
                for i in range(3)]

    def update(self, t_mid, z):
        m = round(self._m(t_mid))
        self.t_ref += m * self.T + self.d * m * m / 2
        self.T += self.d * m
        P = self._grow(m)
        s = P[0][0] + self.r
        K = [P[i][0] / s for i in range(3)]
        self.t_ref += K[0] * z; self.T += K[1] * z; self.d += K[2] * z
        self.P = [[P[i][j] - K[i] * P[0][j] for j in range(3)] for i in range(3)]
        if not T_MIN <= self.T <= T_MAX:
            # Rajalla myös ulospäin työntävä muutos nollataan: muuten d ajaa ennusteen rajan yli
            # joka ikkunassa, kun ramppi pysähtyy äkisti (ramppi20mHz, 23.9.2026).
            self.clamped += 1; self.T = max(T_MIN, min(T_MAX, self.T))
            if (self.T >= T_MAX and self.d > 0) or (self.T <= T_MIN and self.d < 0): self.d = 0.0

    def pump_restart(self):
        pass

    def sd_at(self, t):
        return math.sqrt(max(0.0, self._grow(self._m(t))[0][0]))

    def locked(self, t):
        return 2.5 * self.sd_at(t) < self.lock_us


def run(clock, prof, noise, seed):
    """Ajaa yhden aikataulun; palauttaa mittarit todellisesta virheestä."""
    sigma1, sigmaw, tauw, lagshift = noise
    rnd = random.Random(seed)
    f = profile(prof)
    on, t_end = schedule()
    t_us, k = rnd.uniform(0, 20000.0), 0           # verkon vaihe kellon suhteen satunnainen
    w, n = 0.0, clock.n
    win, win_t, was_on, restart_t = [], [], False, None
    st = {'perm': 0, 'false': 0, 'oncyc': 0, 'errs': [], 'restart': [], 'relock': []}
    seg = 0
    clamped0 = None
    while t_us < t_end * 1e6:
        ts = t_us / 1e6
        T_true = 1e6 / f(ts)
        # OU-vaellus jaksoittain
        a = math.exp(-T_true / 1e6 / tauw)
        w = w * a + sigmaw * math.sqrt(1 - a * a) * rnd.gauss(0, 1)
        while seg < len(on) and ts >= on[seg][1]: seg += 1
        if clamped0 is None and seg >= 1: clamped0 = clock.clamped   # alkulukitus ohi
        pump = seg < len(on) and on[seg][0] <= ts < on[seg][1]
        if pump:
            if not was_on:
                if ts > 0.1:        # uudelleenkäynnistys: kellon ennuste vs todellinen alku
                    st['restart'].append((round(ts - on[seg - 1][1] if seg else 0, 1),
                                          abs(wrap(clock.pred(t_us) - t_us, T_true))))
                clock.pump_restart(); restart_t = ts; win, win_t = [], []
            true_err = wrap(clock.pred(t_us) - t_us, T_true)
            st['oncyc'] += 1
            if clock.locked(t_us):
                st['perm'] += 1; st['errs'].append(abs(true_err))
                if abs(true_err) > clock.lock_us: st['false'] += 1
                if restart_t is not None and restart_t > 0.1:
                    st['relock'].append(ts - restart_t)
                restart_t = None
            lag = lagshift * math.exp(-(ts - restart_t) / 1.0) if (restart_t and lagshift) else 0.0
            y = t_us + w + lag + sigma1 * rnd.gauss(0, 1)
            win.append(wrap(y - clock.pred(t_us), clock.T)); win_t.append(t_us)
            if len(win) == n:
                clock.update(0.5 * (win_t[0] + win_t[-1]), sum(win) / n)
                win, win_t = [], []
        else:
            win, win_t = [], []
        was_on = pump
        t_us += T_true; k += 1
    st['clamped'] = clock.clamped - (clamped0 or 0)
    return st


def pct(xs, q):
    if not xs: return float('nan')
    s = sorted(xs); return s[min(len(s) - 1, int(q * len(s)))]


def evaluate(make, seeds=20, noises=('mitattu', 'huonoin', 'rasitus'), verbose=True):
    rows, agg = [], {}
    for nk in noises:
        for pr in PROFILES:
            tot = {'perm': 0, 'false': 0, 'oncyc': 0, 'errs': [], 'restart': [], 'relock': [],
                   'clamped': 0}
            for s in range(seeds):
                st = run(make(), pr, NOISE[nk], 1000 * s + 7)
                for key in ('perm', 'false', 'oncyc', 'clamped'): tot[key] += st[key]
                for key in ('errs', 'restart', 'relock'): tot[key] += st[key]
            rows.append((nk, pr, tot))
            a = agg.setdefault(nk, {'perm': 0, 'false': 0, 'oncyc': 0, 'clamped': 0, 'clamped_vakio': 0})
            for key in ('perm', 'false', 'oncyc', 'clamped'): a[key] += tot[key]
            if pr.startswith('vakio'): a['clamped_vakio'] += tot['clamped']
    if verbose:
        print('%-8s %-12s %6s %7s %6s %6s %6s | %s' % (
            'kohina', 'verkko', 'lupa%', 'vääriä%', 'p50us', 'p99us', 'T-raja',
            'käynnistysvirhe p95 us / lukko palaa p50 s, tauon mukaan'))
        for nk, pr, t in rows:
            by = {}
            for p, e in t['restart']: by.setdefault(p, []).append(e)
            rel = ' '.join('%gs:%4.0f' % (p, pct(by[p], 0.95)) for p in sorted(by))
            print('%-8s %-12s %6.1f %7.2f %6.0f %6.0f %6d | %s | lukko %.2f s' % (
                nk, pr, 100.0 * t['perm'] / max(1, t['oncyc']),
                100.0 * t['false'] / max(1, t['perm']), pct(t['errs'], 0.5), pct(t['errs'], 0.99),
                t['clamped'], rel, pct(t['relock'], 0.5)))
    return agg


def sweep():
    for n in (4, 8, 16):
        for kp, ki in ((0.08, 0.004), (0.15, 0.012), (0.3, 0.04)):
            a = evaluate(lambda: PIClock(n, kp, ki), seeds=6, noises=('huonoin',), verbose=False)['huonoin']
            print('PI N=%2d kp=%.2f ki=%.3f  lupa %.1f %%  väärä %.2f %%  T-raja %d' % (
                n, kp, ki, 100.0 * a['perm'] / a['oncyc'], 100.0 * a['false'] / max(1, a['perm']), a['clamped']))
        for qt, qp in ((0.02, 10.0), (0.05, 20.0), (0.2, 40.0)):
            a = evaluate(lambda: KFClock(n, q_t=qt, q_phi=qp), seeds=6, noises=('huonoin',), verbose=False)['huonoin']
            print('KF N=%2d q_t=%.2f q_phi=%.0f  lupa %.1f %%  väärä %.2f %%  T-raja %d' % (
                n, qt, qp, 100.0 * a['perm'] / a['oncyc'], 100.0 * a['false'] / max(1, a['perm']), a['clamped']))


KF3_BEST = dict(sigma1=1450.0, sigmaw=500.0, q_d=0.001)   # pyyhkäisy 23.9.2026, ks. brief
LOCK_KELLO_US = 1000.0   # käyttäjän päätös 23.9.2026 (¼ askelta ei saavutettavissa); tarkistetaan,
                         # kun SSR-40DA:n tyyppi on selvillä


def main():
    if '--sweep' in sys.argv:
        sweep(); return 0
    fails = []

    def check(name, ok, extra):
        print('%s %s — %s' % ('PASS' if ok else 'FAIL', name, extra))
        if not ok: fails.append(name)

    print('== PI, suunnitelman kohta 3 (N=8, lukko 3 ikkunaa |e|<400 us), mittari 1000 us ==')
    evaluate(lambda: PIClock(8, lock_us=1000.0), seeds=10)
    print('\n== KF3 (N=8), lukkoraja 208 us = 1/4 vaiheaskelta (suunnitelman hyväksyntä) ==')
    a208 = evaluate(lambda: KF3Clock(8, lock_us=LOCK_US, **KF3_BEST), seeds=10)
    print('\n== KF3 (N=8), lukkoraja %.0f us (käyttäjän päätös 23.9.2026) ==' % LOCK_KELLO_US)
    agg = evaluate(lambda: KF3Clock(8, lock_us=LOCK_KELLO_US, **KF3_BEST))
    m = agg['mitattu']
    fr = 100.0 * m['false'] / max(1, m['perm'])
    check('KF3/mitattu väärät luvat', fr <= 1.0, '%.2f %% (raja 1 %%)' % fr)
    check('KF3/mitattu lupa käyntiajasta', m['perm'] >= 0.5 * m['oncyc'],
          '%.1f %% (raja 50 %%)' % (100.0 * m['perm'] / m['oncyc']))
    # Rajaosuma on tapahtuma VKELLO_TRAJA, ei vika (käyttäjän päätös 23.9.2026): ramppi, joka
    # pysähtyy alueen reunaan, osuu siihen oikeassa lukossa. Vakiotaajuudella alueen sisällä osuma
    # kertoo väärästä lukosta, joten se on yhä vika.
    check('KF3/mitattu T-raja vakiotaajuudella', m['clamped_vakio'] == 0, '%d osumaa' % m['clamped_vakio'])
    print('INFO KF3/mitattu T-rajaosumat kaikkiaan %d (tapahtuma VKELLO_TRAJA)' % m['clamped'])
    for nk in ('huonoin', 'rasitus'):
        a = agg[nk]
        print('INFO KF3/%s väärät luvat %.2f %%, T-raja %d — vaelluksen pohja, ei hyväksyntää' % (
            nk, 100.0 * a['false'] / max(1, a['perm']), a['clamped']))
    a = a208['mitattu']
    print('INFO KF3 208 us: lupa %.1f %% käyntiajasta — 1/4 askeleen raja ei ole saavutettavissa '
          'mitatulla kohinalla' % (100.0 * a['perm'] / a['oncyc']))
    print('\nRESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
