# ============================================================================
# WATER TANK LEVEL ESTIMATOR FROM THERMAL STABILITY (EXPRESSO-VESIMAARA-TUNNISTUS, 27.10.2026)
# ============================================================================
# Kayttajan tilaus (TILAUS-Q, KAYTTAJAN-TIEDOT.md §2, REKISTERI.md):
# "Ota huomioon että ylläpito teho tarve muuttuu keittimen ollessa pitkään päällä ja keittimen
#  rungon ja muiden osien lämmitessä. Tämä arvo lasketaan ja nimetään thermal stability...
#  Myös vesisäiliön vesi lämpiää." (Vesisäiliö = keittimen vesisäiliö, josta boileri ottaa uutta vettä)
#
# Jatkotehtävä: Säiliön vesimäärän tunnistus lämpöstabiiliuden saavutusnopeudesta.
#
# Toimintaperiaate:
# 1. Kylmäkäynnistyksessä keittimen boileri saavuttaa tavoitelämpötilan nopeasti, mutta runko
#    ja vesisäiliö ovat kylmiä. Ylläpitoteho on korkea ja thermal stability (TS) alkaa arvosta
#    -10.0 (tai <= -8.0).
# 2. Lämmön siirtyessä kattilasta runkoon ja vesisäiliöön ylläpitoteho pienenee ja TS nousee
#    kohti vakiotilaa (0.0). Vesisäiliön veden suuri lämpökapasiteetti (c = 4.18 J/g*K)
#    toimii lämpönieluna:
#    - Täysi säiliö (~2.0 L) hidastaa tasaantumista merkittävästi (pitkä saavutusaika t_reach).
#    - Lähes tyhjä säiliö (~0.2-0.5 L) tasaantuu paljon nopeammin (lyhyt t_reach).
# 3. WaterTankTracker mittaa saavutusajan t_reach kylmästä (TS <= TS_START_MAX, esim. -8.0)
#    arviointikynnykseen (TS >= TS_TARGET, esim. -2.0):
#    t_reach = (t_target - t_start) sekunneissa.
# 4. Vesimäärä L arvioidaan mallilla:
#    V_est = model_a * t_reach + model_b
#    (oletus a = 0.0020 L/s, b = -0.40 L, jolloin 300 s -> 0.20 L, 700 s -> 1.00 L, 1200 s -> 2.00 L).
#    Tulos rajataan välille [0.0, TANK_CAPACITY_L] (2.0 L).
# 5. Jos keitin käynnistetään lämpimänä (TS > -6.0), saavutusaikaa ei voida mitata kylmänoususta.
#    Tällöin käytetään edellistä tallennettua vesimäärää ('warm_start' / 'steady').
# 6. Vedenkulutus: kun pumppu käy (uutto, huuhtelu, kuuma vesi), consume_water_ml(ml)
#    vähentää arvioitua vesimäärää.
# 7. Varoituskynnys: jos vesimäärä <= LOW_WATER_THRESHOLD_L (0.3 L), asetetaan tila 'low_water'.
# 8. Komennot (tank?, tank:fill, tank:set:<L>, tank:cal:<a>:<b>, tank:consume:<ml>) ja
#    pysyvyys (water_tank.json atomisella kirjoituksella).
# ============================================================================

import json
import os

TANK_CAPACITY_L = 2.0
TANK_LOW_WATER_L = 0.3
TS_START_MAX = -8.0
TS_TARGET = -2.0
DEFAULT_MODEL_A = 0.0020
DEFAULT_MODEL_B = -0.40
STATE_FILE = 'water_tank.json'


class WaterTankTracker:
    def __init__(self, utime=None, state_file=STATE_FILE):
        self.utime = utime
        self.state_file = state_file

        self.capacity_l = TANK_CAPACITY_L
        self.low_water_l = TANK_LOW_WATER_L
        self.ts_start_max = TS_START_MAX
        self.ts_target = TS_TARGET
        self.model_a = DEFAULT_MODEL_A
        self.model_b = DEFAULT_MODEL_B

        self.tank_water_l = self.capacity_l
        self.status = 'init'             # 'init', 'measuring', 'estimated', 'warm_start', 'low_water', 'full', 'set'
        self.last_reach_time_s = None

        self._measuring = False
        self._measure_start_ms = None
        self._measure_start_ts = None

        self.load_state()

    def _ticks_diff(self, a, b):
        if self.utime is not None and hasattr(self.utime, 'ticks_diff'):
            return self.utime.ticks_diff(a, b)
        return a - b

    def load_state(self):
        """Lataa tallennetun tilan tiedostosta."""
        try:
            with open(self.state_file, 'r') as f:
                d = json.load(f)
            if 'tank_water_l' in d:
                self.tank_water_l = max(0.0, min(self.capacity_l, float(d['tank_water_l'])))
            if 'capacity_l' in d:
                self.capacity_l = float(d['capacity_l'])
            if 'low_water_l' in d:
                self.low_water_l = float(d['low_water_l'])
            if 'model_a' in d:
                self.model_a = float(d['model_a'])
            if 'model_b' in d:
                self.model_b = float(d['model_b'])
            if 'last_reach_time_s' in d and d['last_reach_time_s'] is not None:
                self.last_reach_time_s = float(d['last_reach_time_s'])
            if 'status' in d and d['status']:
                self.status = d['status']
        except Exception:
            pass

    def save_state(self):
        """Tallentaa tilan atomisesti tmp + rename -menetelmällä."""
        try:
            d = {
                'tank_water_l': self.tank_water_l,
                'capacity_l': self.capacity_l,
                'low_water_l': self.low_water_l,
                'status': self.status,
                'last_reach_time_s': self.last_reach_time_s,
                'model_a': self.model_a,
                'model_b': self.model_b
            }
            tmp = self.state_file + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(d, f)
            os.rename(tmp, self.state_file)
        except Exception as e:
            print('WATER_TANK_SAVE_FAIL %r' % (e,))

    @property
    def tank_water_pct(self):
        """Vesimäärä prosentteina säiliön tilavuudesta."""
        if self.capacity_l <= 0.0:
            return 0.0
        return round((self.tank_water_l / self.capacity_l) * 100.0, 1)

    def update(self, ts, now_ms, mode='IDLE'):
        """Päivittää vesimäärän tilan lämpöstabiiliuden (TS) ja ajan perusteella."""
        if ts is None:
            return

        if self._measuring:
            if ts >= self.ts_target:
                dt_ms = self._ticks_diff(now_ms, self._measure_start_ms)
                reach_s = dt_ms / 1000.0
                self.last_reach_time_s = round(reach_s, 1)
                raw_vol = self.model_a * reach_s + self.model_b
                self.tank_water_l = max(0.0, min(self.capacity_l, round(raw_vol, 2)))
                self._measuring = False
                self.status = 'estimated' if self.tank_water_l > self.low_water_l else 'low_water'
                self.save_state()
                print('TANK_ESTIMATED level=%.2fL reach_s=%d status=%s' % (
                    self.tank_water_l, int(reach_s), self.status))
        else:
            if self.status in ('init', 'ready', 'warm_start'):
                # Aloita mittaus, jos kone on kylmä ja lähestyy tavoitetta IDLE-tilassa
                if ts <= self.ts_start_max and (mode == 'IDLE' or mode in ('warming up', 'stabilizing', 'WARMING_UP')):
                    self._measuring = True
                    self._measure_start_ms = now_ms
                    self._measure_start_ts = ts
                    self.status = 'measuring'
                    print('TANK_MEASURE_START ts=%.1f' % ts)
                elif ts > -6.0 and self.status == 'init':
                    # Käynnistys lämpimänä
                    self.status = 'warm_start' if self.tank_water_l > self.low_water_l else 'low_water'

    def consume_water_ml(self, ml):
        """Vähentää kulutetun veden (ml) säiliön tasosta."""
        if ml <= 0.0:
            return
        liters = ml / 1000.0
        self.tank_water_l = max(0.0, round(self.tank_water_l - liters, 3))
        if self.tank_water_l <= self.low_water_l and self.status != 'measuring':
            self.status = 'low_water'
        self.save_state()

    def consume_water_l(self, liters):
        """Vähentää kulutetun veden (L) säiliön tasosta."""
        self.consume_water_ml(liters * 1000.0)

    def fill_tank(self):
        """Asettaa säiliön täydeksi (2.0 L)."""
        self.tank_water_l = self.capacity_l
        self.status = 'full'
        self.save_state()

    def set_water_level(self, liters):
        """Asettaa säiliön vesimäärän suoraan litroina."""
        val = max(0.0, min(self.capacity_l, round(float(liters), 2)))
        self.tank_water_l = val
        if self.tank_water_l >= self.capacity_l:
            self.status = 'full'
        elif self.tank_water_l <= self.low_water_l:
            self.status = 'low_water'
        else:
            self.status = 'set'
        self.save_state()

    def set_calibration(self, a, b):
        """Asettaa mallin kertoimet a ja b."""
        self.model_a = float(a)
        self.model_b = float(b)
        self.save_state()

    def info(self):
        """Palauttaa tilatiedot merkkijonona sarjakomennolle tank?."""
        reach_str = '%ds' % int(self.last_reach_time_s) if self.last_reach_time_s is not None else '-'
        return 'TANK level=%.2fL pct=%.1f%% status=%s reach=%s model=%.4f,%.2f' % (
            self.tank_water_l, self.tank_water_pct, self.status, reach_str, self.model_a, self.model_b)
