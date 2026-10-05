from machine import Pin, disable_irq, enable_irq
import time
import json

_GAIN_PULSES = {128: 1, 32: 2, 64: 3}

# Flow fit (18.9.2026). The window is the whole trade-off: at 11.6 samples/s and sd 0.25 g a
# least-squares slope over T seconds has sd 0.25*sqrt(12)/(T*sqrt(11.6*T)) g/s and reaches 90 % of a
# step in about T s. Measured on the synthetic shot: 0.5 s -> +-0.69 g/s in 0.64 s, 1.0 s ->
# +-0.23 g/s in 1.07 s, 2.0 s -> +-0.08 g/s in 1.83 s. 1.0 s is the default because the restricted
# test shot runs at 2.3 g/s and +-0.23 g/s is 10 % of that.
FLOW_WINDOW_MS = 1000
FLOW_WINDOW_MIN_MS = 200
FLOW_WINDOW_MAX_MS = 3000
FLOW_MIN_POINTS = 4
# A flow read from samples older than this is not a flow but a memory: the HX711 has stopped
# answering (the same failure the weight staleness guard covers in run_shot).
FLOW_STALE_MS = 500


class Scale:

    def __init__(self, dt_a=18, dt_b=20, sck=19, gain=128,
                 cal_file='scale_cal.json', window=8):
        self.pin_a = dt_a
        self.pin_b = dt_b
        self.pin_sck = sck
        self.extra = _GAIN_PULSES[gain]
        self.cal_file = cal_file
        self.window = window

        self.off_a = 0.0
        self.off_b = 0.0
        self.trim_b = 1.0
        self.scale = 1.0
        self.calibrated = False

        self.errors = 0
        self.last_a = 0.0
        self.last_b = 0.0
        self.raw_a = 0          # last raw HX711 counts, for the brew log's dual-cell rows (UUTTOLOKI)
        self.raw_b = 0
        self._buf = []
        self._hist = []
        # Raw (unfiltered) samples for the flow fit, and the same series cleaned with a median of
        # three. Measured 18.9.2026: one sample every 86 ms (11.6 Hz), single-sample sd 0.25 g, and
        # the difference of consecutive samples has sd = sd*sqrt(2) -> the noise is white, so a
        # least-squares fit gains the full sqrt(N). Room for a 3.5 s window.
        self._raw = []
        self._flow_raw = []
        self._flow_n = 48
        self.flow_window_ms = FLOW_WINDOW_MS

        self.sck = Pin(sck, Pin.OUT, value=0)
        self.a = Pin(dt_a, Pin.IN)
        self.b = Pin(dt_b, Pin.IN)
        self.reset()
        self.load()

    # ------------------------------------------------------------ ajuri --
    def unlatch(self):
        Pin(self.pin_a, Pin.OUT, value=0)
        Pin(self.pin_b, Pin.OUT, value=0)
        time.sleep_us(300)
        self.a = Pin(self.pin_a, Pin.IN)
        self.b = Pin(self.pin_b, Pin.IN)

    def reset(self):
        self.sck.value(1)
        time.sleep_us(100)
        self.sck.value(0)
        self.unlatch()
        time.sleep_ms(400)
        self._buf = []
        self._hist = []
        self._raw = []
        self._flow_raw = []

    def ready(self):
        return not (self.a.value() or self.b.value())

    def _shift(self):
        x = y = 0
        sck = self.sck
        pa = self.a
        pb = self.b
        st = disable_irq()
        try:
            for _ in range(24):
                sck.value(1)
                sck.value(0)
                x = (x << 1) | pa.value()
                y = (y << 1) | pb.value()
            for _ in range(self.extra):
                sck.value(1)
                sck.value(0)
        finally:
            enable_irq(st)
        if x & 0x800000:
            x -= 0x1000000
        if y & 0x800000:
            y -= 0x1000000
        return x, y

    def raw(self, timeout_ms=300):
        t0 = time.ticks_ms()
        while not self.ready():
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                self.errors += 1
                raise OSError('HX711 timeout A=%d B=%d'
                              % (self.a.value(), self.b.value()))
            time.sleep_us(200)
        return self._shift()

    def raw_retry(self, tries=3):
        for _ in range(tries):
            try:
                return self.raw()
            except OSError:
                self.reset()
        raise OSError('HX711 ei vastaa')

    def link_ok(self):
        self.unlatch()
        for _ in range(25):
            self.sck.value(1)
            self.sck.value(0)
        hi_a = hi_b = 0
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < 200:
            hi_a |= self.a.value()
            hi_b |= self.b.value()
            time.sleep_ms(5)
        return bool(hi_a and hi_b)

    # -------------------------------------------------------- mittaus ----
    def counts(self):
        a, b = self.raw_retry()
        return (a - self.off_a) + self.trim_b * (b - self.off_b)

    def counts_avg(self, n=8):
        v = [self.counts() for _ in range(n)]
        if n >= 5:
            v.sort()
            v = v[1:-1]
        return sum(v) / len(v)

    def raw_delta(self, n=20):
        sa = sb = 0.0
        for _ in range(n):
            a, b = self.raw_retry()
            sa += a - self.off_a
            sb += b - self.off_b
        return sa / n, sb / n

    def weight(self, n=8):
        return self.counts_avg(n) / self.scale

    def cells(self, n=20):
        sa, sb = self.raw_delta(n)
        return sa / self.scale, (self.trim_b * sb) / self.scale

    # ------------------------------------------- ei-blokkaava paivitys ----
    def update(self):
        """Kutsu paaluupissa. Palauttaa grammat kun uusi nayte on
        valmiina, muuten None. Ei odota koskaan."""
        if not self.ready():
            return None
        try:
            a, b = self._shift()
        except OSError:
            self.errors += 1
            return None
        self.raw_a, self.raw_b = a, b
        c = (a - self.off_a) + self.trim_b * (b - self.off_b)
        # Per-cell values in grams (18.9.2026). The sum is what everything else uses, but the split
        # is the only way to test whether the load distribution during a shot correlates with the
        # measurement error - at-rest probes cannot answer that.
        self.last_a = (a - self.off_a) / self.scale
        self.last_b = (self.trim_b * (b - self.off_b)) / self.scale
        now = time.ticks_ms()
        g_raw = c / self.scale
        self._raw.append((now, g_raw))
        if len(self._raw) > self._flow_n:
            self._raw.pop(0)
        if len(self._raw) >= 3:
            w = self._raw[-3:]
            v = sorted((w[0][1], w[1][1], w[2][1]))
            # Median of three costs one sample (86 ms) of delay and pays for it: the single-sample
            # -16 g glitches (0.19 % of samples) move a 1 s flow fit by 8 g/s without it and by
            # 0.4 g/s with it (measured on the synthetic shot, 18.9.2026).
            self._flow_raw.append((w[1][0], v[1]))
            if len(self._flow_raw) > self._flow_n:
                self._flow_raw.pop(0)
        self._buf.append(c)
        if len(self._buf) > self.window:
            self._buf.pop(0)
        v = sorted(self._buf)
        if len(v) >= 5:
            v = v[1:-1]
        g = (sum(v) / len(v)) / self.scale
        self._hist.append((now, g))
        if len(self._hist) > 16:
            self._hist.pop(0)
        return g

    def value(self):
        """Viimeisin suodatettu lukema ilman uutta mittausta."""
        return self._hist[-1][1] if self._hist else 0.0

    def set_flow_window(self, ms):
        """Virtausikkuna millisekunteina. Mittausnuppi: pieni ikkuna vastaa nopeammin ja kohisee
        enemman, ks. FLOW_WINDOW_MS."""
        try:
            ms = int(ms)
        except (TypeError, ValueError):
            return self.flow_window_ms
        if ms < FLOW_WINDOW_MIN_MS:
            ms = FLOW_WINDOW_MIN_MS
        elif ms > FLOW_WINDOW_MAX_MS:
            ms = FLOW_WINDOW_MAX_MS
        self.flow_window_ms = ms
        return self.flow_window_ms

    def flow(self, span_ms=None):
        """Virtaus g/s: pienimman neliosumman suora raakanaytteisiin (mediaani-3 siivottuna) ikkunan
        yli. None kun ikkunassa on alle FLOW_MIN_POINTS naytetta tai uusin nayte on yli
        FLOW_STALE_MS vanha — jaatynyt lukema ei ole virtaus. Ei kutsu anturia, joten tata voi
        kutsua niin usein kuin haluaa."""
        h = self._flow_raw
        if not h:
            return None
        span = self.flow_window_ms if span_ms is None else span_ms
        t_last = h[-1][0]
        if time.ticks_diff(time.ticks_ms(), t_last) > FLOW_STALE_MS:
            return None
        n = 0
        sx = sy = sxx = sxy = 0.0
        for i in range(len(h) - 1, -1, -1):
            t, g = h[i]
            dt = time.ticks_diff(t_last, t)
            if dt > span:
                break
            x = -dt / 1000.0
            n += 1
            sx += x
            sy += g
            sxx += x * x
            sxy += x * g
        if n < FLOW_MIN_POINTS:
            return None
        den = n * sxx - sx * sx
        if abs(den) < 1e-9:
            return None
        return (n * sxy - sx * sy) / den

    # ---------------------------------------------------- kalibrointi ----
    def tare(self, n=40):
        self.off_a = self.off_b = 0.0
        sa = sb = 0
        for _ in range(n):
            a, b = self.raw_retry()
            sa += a
            sb += b
        self.off_a = sa / n
        self.off_b = sb / n
        self._buf = []
        self._hist = []
        return self.off_a, self.off_b

    def scale_meta(self):
        """Calibration for the brew log (UUTTOLOKI): the app rebuilds grams from the raw rows as
        ((a - off_a) + trim_b * (b - off_b)) / scale, the same sum as update()."""
        return {'scale': self.scale, 'trim_b': self.trim_b, 'sense': 1,
                'off_a': self.off_a, 'off_b': self.off_b}

    def load(self):
        try:
            with open(self.cal_file) as f:
                d = json.load(f)
            self.off_a = d['off_a']
            self.off_b = d['off_b']
            self.trim_b = d['trim_b']
            self.scale = d['scale']
            self.calibrated = True
        except (OSError, ValueError, KeyError):
            self.calibrated = False
        return self.calibrated

    def save(self):
        d = {'off_a': self.off_a, 'off_b': self.off_b,
             'trim_b': self.trim_b, 'scale': self.scale}
        with open(self.cal_file, 'w') as f:
            json.dump(d, f)
        self.calibrated = True
        return d

    def info(self):
        return ('scale=%.2f counts/g trim_b=%.4f off=%.0f/%.0f cal=%s'
                % (self.scale, self.trim_b, self.off_a, self.off_b,
                   self.calibrated))