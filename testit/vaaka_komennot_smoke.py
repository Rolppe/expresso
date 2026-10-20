#!/usr/bin/env python3
"""vaaka_komennot_smoke.py — äpin tara ja vaa'an kalibrointi firmwarella (EXPRESSO-WIFI-APPI vaihe 0, 20.10.2026).

Äppi on aina lähettänyt `tare` ja `cal:*` (tare_button.dart, calibration_view.dart), mutta firmwarella ei ollut
käsittelijää. Testaa `pico/scalecal.py`:n tilakoneen äpin vaiheilla valevaa'alla (kaksi kennoa, eri vahvistus,
eri nollat), komentoreitityksen `commands.handle_command`in kautta ja ettei mikään lue HX711:tä itse.

    python3 testit/vaaka_komennot_smoke.py        RESULT: <n> failed, epänolla paluuarvo jos punaisia
"""

import os
import random
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico'))
import scalecal as SC  # noqa: E402

FAILED = []


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + ('' if ok else '  ' + str(info)))
    if not ok:
        FAILED.append(name)


class Clock:
    def __init__(self):
        self.ms = 0

    def ticks_ms(self):
        return self.ms

    def ticks_diff(self, a, b):
        return a - b


class FakeScale:
    """Scale's calibration fields; raw_retry() must never be called (it would block for ~86 ms per sample)."""
    def __init__(self, calibrated=True, scale=2000.0):
        self.off_a = 600000.0
        self.off_b = 50000.0
        self.trim_b = 1.0
        self.scale = scale
        self.calibrated = calibrated
        self.saved = 0
        self._buf = [1]
        self._hist = [1]
        self._raw = [1]
        self._flow_raw = [1]

    def save(self):
        self.saved += 1
        self.calibrated = True

    def raw_retry(self, tries=3):
        raise AssertionError('scalecal must not read the HX711')


# True cells: A 2100 counts/g, B 1900 counts/g, zero 610000 / 48000
KA, KB, ZA, ZB = 2100.0, 1900.0, 610000.0, 48000.0
rnd = random.Random(7)


def raw(load_a, load_b, noise=300.0):
    return ZA + KA * load_a + rnd.gauss(0, noise), ZB + KB * load_b + rnd.gauss(0, noise)


def feed(cal, load_a, load_b, n):
    for _ in range(n):
        a, b = raw(load_a, load_b)
        cal.on_sample(a, b)


idle = [True]
clk = Clock()

# ---- full program -----------------------------------------------------------------------------------
s = FakeScale()
cal = SC.ScaleCal(s, clk, lambda: idle[0])
check('starts idle', cal.status() == {'cal_phase': 'idle', 'cal_msg': '', 'cal_err': ''} and not cal.active())
cal.command('full:start')
check('full_empty waits for Next', cal.phase == 'full_empty')
feed(cal, 0, 0, 30)
check('samples ignored before Next', cal.phase == 'full_empty')
cal.command('next')
check('full_tare_run', cal.phase == 'full_tare_run')
feed(cal, 0, 0, SC.MEASURE_N)
check('tare done -> full_left_ready', cal.phase == 'full_left_ready')
cal.command('next')
feed(cal, 118 * 0.8, 118 * 0.2, SC.MEASURE_N)       # corner shares the load 80/20
check('left done -> full_right_ready', cal.phase == 'full_right_ready')
cal.command('next')
feed(cal, 118 * 0.15, 118 * 0.85, SC.MEASURE_N)
check('right done -> full_tray_ready', cal.phase == 'full_tray_ready', cal.status())
cal.command('next')
feed(cal, 454.5 / 2, 454.5 / 2, SC.MEASURE_N)
check('tray done -> full_done, saved', cal.phase == 'full_done' and s.saved == 1, cal.status())
check('zero = empty platform', abs(s.off_a - ZA) < 300 and abs(s.off_b - ZB) < 300, (s.off_a, s.off_b))
check('trim_b = KB/KA... per-count balance', abs(s.trim_b - KA / KB) < 0.01, s.trim_b)
check('scale = counts/g in cell A units', abs(s.scale - KA) / KA < 0.005, s.scale)
check('filtered history cleared', s._buf == [] and s._hist == [] and s._raw == [] and s._flow_raw == [])
check('done visible to the app', cal.active() and cal.status()['cal_phase'] == 'full_done')
clk.ms += SC.DONE_HOLD_MS
cal.tick()
check('done -> idle after hold', cal.phase == 'idle')

# ---- full: same reading left and right ----------------------------------------------------------------
s = FakeScale()
cal = SC.ScaleCal(s, clk, lambda: idle[0])
cal.command('full:start'); cal.command('next'); feed(cal, 0, 0, SC.MEASURE_N)
cal.command('next'); feed(cal, 59, 59, SC.MEASURE_N)
cal.command('next')
for _ in range(SC.MEASURE_N):
    cal.on_sample(ZA + KA * 59, ZB + KB * 59)
check('same load both sides -> error', cal.phase == 'error' and cal.status()['cal_err'] != '' and s.saved == 0,
      cal.status())
cal.command('next')
check('Next on error -> idle', cal.phase == 'idle' and cal.status()['cal_err'] == '')

# ---- quick correction -------------------------------------------------------------------------------
s = FakeScale(scale=KA * 1.06)          # 6 % off
s.off_a, s.off_b, s.trim_b = ZA, ZB, KA / KB
cal = SC.ScaleCal(s, clk, lambda: idle[0])
cal.command('quick:100.0')
check('quick_tare', cal.phase == 'quick_tare')
feed(cal, 300, 300, SC.MEASURE_N)        # tray
check('quick_wait', cal.phase == 'quick_wait')
clk.ms += 1000
feed(cal, 300, 300, 40)
check('no weight placed -> still waiting', cal.phase == 'quick_wait')
feed(cal, 300 + 30, 300 + 20, 3)          # placing: moving
feed(cal, 300 + 60, 300 + 40, SC.QUICK_STABLE_N)
check('stable 100 g -> quick_done, saved', cal.phase == 'quick_done' and s.saved == 1, cal.status())
check('quick factor corrected', abs(s.scale - KA) / KA < 0.01, s.scale)
check('quick keeps the zero and trim', s.off_a == ZA and s.off_b == ZB and abs(s.trim_b - KA / KB) < 1e-9)

# ---- quick errors -----------------------------------------------------------------------------------
s = FakeScale(scale=KA)
s.off_a, s.off_b, s.trim_b = ZA, ZB, KA / KB
cal = SC.ScaleCal(s, clk, lambda: idle[0])
cal.command('quick:2')
check('mass < 5 g -> error', cal.phase == 'error')
cal.command('quick:abc')
check('bad mass -> error', cal.phase == 'error' and cal.status()['cal_err'] == 'bad mass')
cal.command('quick:50')
feed(cal, 300, 300, SC.MEASURE_N)
feed(cal, 300 + 50, 300 + 50, SC.QUICK_STABLE_N)    # 100 g placed while the app said 50 g: factor 2x
check('factor > 30 % off -> error, not saved', cal.phase == 'error' and s.saved == 0 and s.scale == KA,
      cal.status())
cal.command('quick:100')
feed(cal, 300, 300, SC.MEASURE_N)
clk.ms += SC.QUICK_TIMEOUT_MS
cal.tick()
check('no stable weight in 60 s -> error', cal.phase == 'error')

# ---- interlock and cancel -----------------------------------------------------------------------------
cal.command('next')
idle[0] = False
cal.command('full:start')
check('not idle -> refuses', cal.phase == 'error' and 'busy' in cal.status()['cal_err'])
idle[0] = True
cal.command('next')
cal.command('full:start'); cal.command('next')
idle[0] = False
cal.tick()
check('shot starts mid-calibration -> error', cal.phase == 'error' and 'shot' in cal.status()['cal_err'])
idle[0] = True
cal.command('full:start'); cal.command('next'); feed(cal, 0, 0, 5)
cal.command('cancel')
check('cancel -> idle, nothing saved', cal.phase == 'idle' and s.saved == 0)
check('unknown cal command not handled', cal.command('bogus') is False)
cal.on_sample(None, None)
check('bad sample does not raise', True)

# ---- tare and weight_g ------------------------------------------------------------------------------
bd = types.SimpleNamespace(weight=731.94, tare_abs_g=None)
check('weight_g untared = abs', SC.weight_g(bd) == 731.94)
check('tare ok', SC.tare(bd) is True and bd.tare_abs_g == 731.94)
bd.weight = 750.0
check('weight_g after tare', abs(SC.weight_g(bd) - 18.06) < 1e-9)
bd2 = types.SimpleNamespace(weight=None, tare_abs_g=5.0)
check('tare without reading -> False, keeps old', SC.tare(bd2) is False and bd2.tare_abs_g == 5.0)

# ---- commands.handle_command routing ----------------------------------------------------------------
sys.modules['functions'] = types.SimpleNamespace(PCAP_GATE_PERIOD_US=1, PSWEEP_N_MAX=1, PSWEEP_MULT_MAX=1,
                                                 PGAP_SPACING_MAX_MS=1)
import commands as C  # noqa: E402
s = FakeScale()
bd = types.SimpleNamespace(weight=500.0, tare_abs_g=None, scale_cal=SC.ScaleCal(s, clk, lambda: True))
C.handle_command(bd, 'tare')
check('cmd tare', bd.tare_abs_g == 500.0)
C.handle_command(bd, 'cal:full:start')
check('cmd cal:full:start', bd.scale_cal.phase == 'full_empty')
C.handle_command(bd, 'cal:cancel')
check('cmd cal:cancel', bd.scale_cal.phase == 'idle')
bd3 = types.SimpleNamespace(weight=500.0, tare_abs_g=None, scale_cal=None)
try:
    C.handle_command(bd3, 'cal:quick:100')
    check('cmd cal without scale does not raise', True)
except Exception as e:
    check('cmd cal without scale does not raise', False, e)


# ---- SerialLine: a stray byte must not end the firmware (UnicodeError 20.10.2026 10.18.58) ------------
sl = C.SerialLine()
out = [sl.feed(x) for x in b'\xff\xfe\x00CMD heat?\xe4\r']
check('serial: non-ASCII dropped, line kept', out[-1] == 'CMD heat?' and all(o is None for o in out[:-1]), out[-1])
out = [sl.feed(x) for x in (b'x' * 200) + b'\n']
check('serial: line capped at 80', out[-1] == 'x' * 80)
check('serial: empty line', sl.feed(10) == '')

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
