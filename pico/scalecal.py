# ============================================================================
# SCALE TARE AND CALIBRATION FOR THE APP (EXPRESSO-WIFI-APPI vaihe 0, 20.10.2026)
# ============================================================================
# The app has always sent `tare` and `cal:*` (tare_button.dart, calibration_view.dart) but the firmware had
# no handler for either: the buttons did nothing. This module is that handler, written to the app's phases:
#   quick:  cal:quick:<g>  -> quick_tare -> quick_wait -> quick_done | error
#   full:   cal:full:start -> full_empty -(next)-> full_tare_run -> full_left_ready -(next)-> full_left_measure
#           -> full_right_ready -(next)-> full_right_measure -> full_tray_ready -(next)-> full_tray_measure
#           -> full_done | error
#   cal:next on quick_done/full_done/error -> idle; cal:cancel -> idle, nothing saved.
# Rules:
# - never blocks: the HX711 gives a sample every ~86 ms, so nothing here reads it. scale_poll_once (main.py)
#   hands every new raw pair to on_sample(), and a measurement is the mean of MEASURE_N samples (~2 s);
# - the tare is a software offset (tare_abs_g) like the app's DemoPico. Scale.tare() would move the
#   calibration zero that the tray guard and the weight limits stand on;
# - trim_b comes from both corner measurements, t = (dA1 - dA2) / (dB2 - dB1): the same mass on each side
#   gives the same counts whichever cell is "left" and however the corner shares the load;
# - no calibration while a shot runs (mode not IDLE): the scale is the tray guard's input then.

MEASURE_N = 24              # samples per measurement, ~2 s at 11.6 samples/s
TRAY_REF_G = 454.5          # empty drip tray, the app's reference (calibration_view.dart)
QUICK_MIN_G = 5.0
QUICK_MAX_G = 5000.0
QUICK_STABLE_N = 12         # samples that must agree before the quick weight counts
QUICK_TIMEOUT_MS = 60000
DONE_HOLD_MS = 30000        # done/error stays visible this long, then idle (the app may never send next)
SCALE_CHANGE_MAX = 0.30     # a new factor more than 30 % off a calibrated one is a mistake, not a fix
TRIM_MIN = 0.3
TRIM_MAX = 3.0

_MEASURING = ('quick_tare', 'full_tare_run', 'full_left_measure', 'full_right_measure', 'full_tray_measure')


def tare(brew_data):
    """`tare`: the current absolute weight becomes the zero of weight_g. False without a reading."""
    w = brew_data.weight
    if w is None:
        return False
    brew_data.tare_abs_g = w
    return True


def weight_g(brew_data):
    w = brew_data.weight
    if w is None:
        return None
    return w - (getattr(brew_data, 'tare_abs_g', None) or 0.0)


def zero_track(brew_data, alpha=0.05, deadband=0.25):
    """Zero tracking in IDLE mode: slowly creeps tare_abs_g when close to zero to cancel thermal drift."""
    tare = getattr(brew_data, 'tare_abs_g', None)
    w = getattr(brew_data, 'weight', None)
    if tare is None or w is None:
        return
    net = w - tare
    if abs(net) <= deadband:
        brew_data.tare_abs_g = (1.0 - alpha) * tare + alpha * w


def _mean_sd(v):
    n = len(v)
    m = sum(v) / n
    return m, (sum((x - m) * (x - m) for x in v) / n) ** 0.5


class ScaleCal:
    def __init__(self, scale, utime, is_idle):
        self.scale = scale
        self.utime = utime
        self.is_idle = is_idle          # () -> True while the machine is IDLE
        self.phase = 'idle'
        self.msg = ''
        self.err = ''
        self._acc_a = []
        self._acc_b = []
        self._t_phase = 0
        self._known = 0.0
        self._base = None               # (a, b) of the empty platform or the tray
        self._noise = 0.0
        self._win = []
        self._left = None

    # ---- state ------------------------------------------------------------------------------------
    def active(self):
        return self.phase != 'idle'

    def status(self):
        return {'cal_phase': self.phase, 'cal_msg': self.msg[:60], 'cal_err': self.err[:60]}

    def _go(self, phase, msg=''):
        self.phase = phase
        self.msg = msg
        self._t_phase = self.utime.ticks_ms()
        if phase in _MEASURING:
            self._acc_a = []
            self._acc_b = []
        try:
            print('SCALE_CAL %s %s' % (phase, msg))
        except Exception:
            pass

    def _fail(self, err):
        self.err = err
        self._go('error', err)

    # ---- commands ---------------------------------------------------------------------------------
    def command(self, arg):
        """arg is the text after 'cal:'. Returns True when it was a calibration command."""
        p = arg.split(':')
        if p[0] == 'cancel':
            self.err = ''
            self._go('idle', 'cancelled')
            return True
        if p[0] == 'next':
            self._next()
            return True
        if not self.is_idle():
            self._fail('machine busy: calibrate when idle')
            return True
        if p[0] == 'quick' and len(p) == 2:
            try:
                g = float(p[1])
            except ValueError:
                self._fail('bad mass')
                return True
            if not QUICK_MIN_G <= g <= QUICK_MAX_G:
                self._fail('mass must be 5-5000 g')
                return True
            self._known = g
            self.err = ''
            self._go('quick_tare', 'keep only the tray on the scale')
            return True
        if p[0] == 'full' and len(p) == 2 and p[1] == 'start':
            self.err = ''
            self._go('full_empty', 'remove everything, then Next')
            return True
        return False

    def _next(self):
        ph = self.phase
        if ph in ('quick_done', 'full_done', 'error'):
            self.err = ''
            self._go('idle')
        elif ph == 'full_empty':
            self._go('full_tare_run', 'measuring empty zero')
        elif ph == 'full_left_ready':
            self._go('full_left_measure', 'measuring left')
        elif ph == 'full_right_ready':
            self._go('full_right_measure', 'measuring right')
        elif ph == 'full_tray_ready':
            self._go('full_tray_measure', 'measuring tray')

    # ---- samples ----------------------------------------------------------------------------------
    def on_sample(self, a, b):
        """A new raw HX711 pair (scale_poll_once). Never raises."""
        try:
            ph = self.phase
            if ph in _MEASURING:
                self._acc_a.append(a)
                self._acc_b.append(b)
                if len(self._acc_a) >= MEASURE_N:
                    self._measured(ph)
            elif ph == 'quick_wait':
                self._quick_sample(a, b)
        except Exception as e:
            self._fail('cal error %s' % e)

    def _mean(self):
        return sum(self._acc_a) / len(self._acc_a), sum(self._acc_b) / len(self._acc_b)

    def _counts(self, a, b, base):
        return (a - base[0]) + self.scale.trim_b * (b - base[1])

    def _measured(self, ph):
        a, b = self._mean()
        if ph == 'quick_tare':
            self._base = (a, b)
            c = [self._counts(x, y, self._base) for x, y in zip(self._acc_a, self._acc_b)]
            self._noise = _mean_sd(c)[1]
            self._win = []
            self._go('quick_wait', 'place the %.1f g weight' % self._known)
        elif ph == 'full_tare_run':
            self._base = (a, b)
            self._go('full_left_ready', 'corner weight on the LEFT cell, then Next')
        elif ph == 'full_left_measure':
            self._left = (a - self._base[0], b - self._base[1])
            self._go('full_right_ready', 'same weight on the RIGHT cell, then Next')
        elif ph == 'full_right_measure':
            da1, db1 = self._left
            da2, db2 = a - self._base[0], b - self._base[1]
            if abs(db2 - db1) < 1e-6:
                self._fail('left and right read the same: move the weight to one corner')
                return
            t = (da1 - da2) / (db2 - db1)
            if not TRIM_MIN <= t <= TRIM_MAX:
                self._fail('cell balance %.2f out of range' % t)
                return
            self._trim = t
            self._go('full_tray_ready', 'remove the weight, empty tray centred, then Next')
        elif ph == 'full_tray_measure':
            c = (a - self._base[0]) + self._trim * (b - self._base[1])
            new = c / TRAY_REF_G
            if not self._sane(new):
                return
            s = self.scale
            s.off_a, s.off_b = self._base
            s.trim_b = self._trim
            self._apply(new, 'full_done')

    def _quick_sample(self, a, b):
        c = self._counts(a, b, self._base)
        self._win.append(c)
        if len(self._win) > QUICK_STABLE_N:
            self._win.pop(0)
        if len(self._win) < QUICK_STABLE_N:
            return
        m, sd = _mean_sd(self._win)
        # Placed = half the expected load with a calibration, else well above the tray's own noise
        expect = self._known * self.scale.scale if self.scale.calibrated else 0.0
        floor = 0.5 * expect if expect > 0 else max(20.0 * self._noise, 1.0)
        if m < floor:
            return                       # nothing placed yet
        if sd > max(0.002 * m, 3.0 * self._noise):
            return                       # still settling
        new = m / self._known
        if self._sane(new):
            self._apply(new, 'quick_done')

    def _sane(self, new):
        s = self.scale
        if new <= 0:
            self._fail('no load measured')
            return False
        if s.calibrated and abs(new / s.scale - 1.0) > SCALE_CHANGE_MAX:
            self._fail('factor %.1f is >30%% off %.1f: check the mass' % (new, s.scale))
            return False
        return True

    def _apply(self, new, phase):
        s = self.scale
        old = s.scale
        s.scale = new
        # Filtered history is in the old units
        s._buf = []
        s._hist = []
        s._raw = []
        s._flow_raw = []
        s.save()
        self._go(phase, 'saved: %.2f counts/g (was %.2f)' % (new, old))

    # ---- time -------------------------------------------------------------------------------------
    def tick(self, brew_data=None):
        """Timeouts and the shot interlock; call every pass of a task. Never raises."""
        try:
            if brew_data is not None and self.is_idle():
                zero_track(brew_data)
            ph = self.phase
            if ph == 'idle':
                return
            age = self.utime.ticks_diff(self.utime.ticks_ms(), self._t_phase)
            if ph in ('quick_done', 'full_done', 'error'):
                if age >= DONE_HOLD_MS:
                    self.err = ''
                    self._go('idle')
            elif not self.is_idle():
                self._fail('shot started: calibration stopped')
            elif ph == 'quick_wait' and age >= QUICK_TIMEOUT_MS:
                self._fail('no stable weight in 60 s')
        except Exception:
            pass
