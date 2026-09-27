"""verkkokello.py — sisainen verkkojaksokello (brief VERKKOKELLO, paketit/VERKKOKELLO.md).

`Verkkokello` on `testit/verkkokello_sim.py`:n `KF3Clock`-luokan MicroPython-kaannos, lisattyna
I/Q-vaihemittaus paineesta. Holdout (`testit/verkkokello_holdout.py`) todentaa numeerisen
vastaavuuden ja rajaosumat; talla tiedostolla ei ole omaa hyvaksyntaa.

RP2040:n MicroPython-float on 32-bittinen eika mahdu absoluuttiseen ticks-arvoon (enintaan 2^30)
mikrosekunnin tarkkuudella. Siksi vaiheen viite `ref` pidetaan kokonaislukuna (ticks) ja pieni
jaljelle jaava osa `frac`:ssa liukulukuna; liukulukuun muunnetaan vain erotuksia, ja `frac`
normalisoidaan takaisin `ref`:iin joka paivityksen jalkeen (`_norm`), jotta se pysyy pienena.
"""

import math
import utime

N_WIN = 8
SIGMA1 = 1450
SIGMAW = 500
Q_D = 0.001
D0 = 0.04
T_START = 20000
T_MIN = 19950
T_MAX = 20050
LAG_US = 39000
LOCK_US = 1000
AMP_MIN = 0.1     # bar: heikompi vareily ei paivita kelloa (amplitudiportti)
# Transienttiportti (EXPRESSO-VERKKOKELLO-KORJAUS 23.9.2026): paineen uudelleennousussa tauon
# jalkeen vareilyn viive on 4-5 ms tavallista suurempi ~0,8 s ajan ja amplitudi 2-5-kertainen
# (vkello-20260923-a/b/d, 5 s tauko). Ikkuna, jonka amplitudi ylittaa GATE_RATIO x hyvaksyttyjen
# liukuvan keskiarvon, ei paivita kelloa. GATE_MAX perakkaisen hylkayksen jalkeen viite siirtyy
# nykyiseen amplitudiin (pysyva painetason muutos ei ole transientti); havaittu pisin 10 ikkunaa.
GATE_RATIO = 2.0
GATE_ALPHA = 0.2
GATE_MAX = 20
# Paineportti (EXPRESSO-VERKKOKELLO-LAITETESTI2 23.9.2026): tauon jalkeen paineen palautumisen hanta
# lapaisee amplitudiportin, ja sen vareilyn viive on 0,5-1,5 ms tasannetta lyhyempi (viive riippuu
# paineesta, TILAUS-G) -> kello lukittuna 1,4-1,7 ms vaarassa (vkello-20260923-e/g). Ikkuna, jonka
# keskipaine on yli P_GATE_BAR hyvaksyttyjen liukuvan keskiarvon alapuolella, ei paivita kelloa;
# replay e/g/h: lukittuja virheita > LOCK_US 0 (ilman 16/10/0). GATE_MAX:n jalkeen viite siirtyy
# (pysyva painetason muutos, esim. kuristimen kaanto).
P_GATE_BAR = 1.0

_TAB_N = 256
_COS = [math.cos(2 * math.pi * i / _TAB_N) for i in range(_TAB_N)]
_SIN = [math.sin(2 * math.pi * i / _TAB_N) for i in range(_TAB_N)]


class Verkkokello:
    """Kolmitilainen Kalman-suodin (vaihe, jakso T, jakson muutos d) + I/Q-vaihemittaus."""

    def __init__(self, t0_us):
        self.ref, self.frac, self.T, self.d = t0_us, 0.0, float(T_START), 0.0
        self.P = [[1e8, 0.0, 0.0], [0.0, 45.0 ** 2, 0.0], [0.0, 0.0, D0 * D0]]
        self.traja = 0
        self.r = SIGMA1 * SIGMA1 / N_WIN + SIGMAW * SIGMAW
        self.q = Q_D * Q_D
        self.iq_n = 0
        self.amp_ref, self.gate_run, self.gated, self.rebased = None, 0, 0, 0
        self.p_ref, self.p_run, self.pgated = None, 0, 0

    def _m(self, t):
        return (utime.ticks_diff(t, self.ref) - self.frac) / self.T

    def _norm(self):
        df = round(self.frac)
        if df:
            self.ref = utime.ticks_add(self.ref, int(df)); self.frac -= df

    def _grow(self, m):
        P = self.P
        F = [[1.0, m, m * m / 2.0], [0.0, 1.0, m], [0.0, 0.0, 1.0]]
        a = abs(m)
        Q = [[a ** 5 / 20.0, a ** 4 / 8.0, a ** 3 / 6.0],
             [a ** 4 / 8.0, a ** 3 / 3.0, a * a / 2.0],
             [a ** 3 / 6.0, a * a / 2.0, a]]
        FP = [[sum(F[i][k] * P[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        return [[sum(FP[i][k] * F[j][k] for k in range(3)) + self.q * Q[i][j] for j in range(3)]
                for i in range(3)]

    def edge(self, t):
        m = round(self._m(t))
        return utime.ticks_add(self.ref, round(self.frac + m * self.T + self.d * m * m / 2.0))

    def update(self, t_mid, z):
        m = round(self._m(t_mid))
        self.frac += m * self.T + self.d * m * m / 2.0
        self._norm()
        self.T += self.d * m
        P = self._grow(m)
        s = P[0][0] + self.r
        K = [P[i][0] / s for i in range(3)]
        self.frac += K[0] * z
        self._norm()
        self.T += K[1] * z; self.d += K[2] * z
        self.P = [[P[i][j] - K[i] * P[0][j] for j in range(3)] for i in range(3)]
        if not (T_MIN <= self.T <= T_MAX):
            # Rajalla ulospain tyontava muutos nollataan (VKELLO_TRAJA, kayttajan paatos 23.9.2026).
            self.traja += 1
            self.T = max(T_MIN, min(T_MAX, self.T))
            if (self.T >= T_MAX and self.d > 0) or (self.T <= T_MIN and self.d < 0):
                self.d = 0.0

    def sd_us(self, t):
        v = self._grow(self._m(t))[0][0]
        return math.sqrt(v) if v > 0.0 else 0.0

    def locked(self, t):
        return 2.5 * self.sd_us(t) < LOCK_US

    def iq_start(self, t):
        self.iq_t0, self.iq_e, self.iq_T = t, self.edge(t), self.T
        self.iq_scale = _TAB_N / self.iq_T
        self.iq_si = self.iq_sq = self.iq_sc = self.iq_ss = self.iq_sum = 0.0
        self.iq_n = 0

    def iq_add(self, t, x):
        # Ei cos/sin-kutsuja tassa (1 kHz:n silmukka): valmis 256 alkion taulukko.
        ph = utime.ticks_diff(t, self.iq_e) % self.iq_T
        idx = round(ph * self.iq_scale) % _TAB_N
        c, s = _COS[idx], _SIN[idx]
        self.iq_si += x * c; self.iq_sq += x * s
        self.iq_sc += c; self.iq_ss += s
        self.iq_sum += x; self.iq_n += 1

    def iq_ready(self, t):
        return utime.ticks_diff(t, self.iq_t0) >= N_WIN * self.iq_T

    def iq_abort(self):
        self.iq_n = 0

    def gate(self, amp):
        """True = ikkuna saa paivittaa kellon (transienttiportti, ks. GATE_RATIO)."""
        if self.amp_ref is None:
            self.amp_ref = amp; return True
        if amp > GATE_RATIO * self.amp_ref:
            self.gate_run += 1; self.gated += 1
            if self.gate_run < GATE_MAX: return False
            self.amp_ref, self.gate_run = amp, 0; self.rebased += 1
            return True
        self.amp_ref += GATE_ALPHA * (amp - self.amp_ref); self.gate_run = 0
        return True

    def pgate(self, p):
        """True = ikkunan paine kelpaa (paineportti, ks. P_GATE_BAR). Kutsutaan vain, kun
        amplitudiportti on paastanyt ikkunan."""
        if self.p_ref is None:
            self.p_ref = p; return True
        if p < self.p_ref - P_GATE_BAR:
            self.p_run += 1; self.pgated += 1
            if self.p_run < GATE_MAX: return False
            self.p_ref, self.p_run = p, 0; self.rebased += 1
            return True
        self.p_ref += GATE_ALPHA * (p - self.p_ref); self.p_run = 0
        return True

    def gate_reset(self):
        """Porttien viitteet alusta (EXPRESSO-UUTTO-8BAR): esiuutosta uuttoon siirryttaessa paineen taso muuttuu
        pysyvasti 2,5 -> 8 bar ja vareilyn amplitudi sen mukana. Ilman nollausta amplitudiportti hylkaisi GATE_MAX
        ikkunaa (~3 s) ennen viitteen siirtoa, ja kello lukittuisi vasta pidossa."""
        self.amp_ref, self.gate_run, self.p_ref, self.p_run = None, 0, None, 0

    def accept(self, amp, p):
        """0 = ikkuna paivittaa kellon, 1 = amplitudiportti hylkasi, 2 = paineportti hylkasi."""
        if not self.gate(amp): return 1
        return 0 if self.pgate(p) else 2

    def iq_close(self, t, learn=True):
        n = self.iq_n
        if n == 0: return None
        mean = self.iq_sum / n
        I = self.iq_si - mean * self.iq_sc
        Q = self.iq_sq - mean * self.iq_ss
        amp = 2.0 * math.sqrt(I * I + Q * Q) / n
        self.iq_n = 0
        if amp < AMP_MIN: return None
        ang = math.atan2(Q, I)
        z = ang * self.iq_T / (2 * math.pi) - LAG_US
        z -= self.iq_T * round(z / self.iq_T)
        half = utime.ticks_diff(t, self.iq_t0) // 2
        t_mid = utime.ticks_add(self.iq_t0, half)
        if not learn:
            return (z, amp, mean, -1)   # vain lokiin (nousu, TILAUS-G): ei portteja, ei paivitysta
        g = self.accept(amp, mean)
        if g == 0: self.update(t_mid, z)
        return (z, amp, mean, g)
