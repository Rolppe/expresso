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

    def iq_close(self, t):
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
        self.update(t_mid, z)
        return (z, amp)
