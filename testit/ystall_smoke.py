"""ystall_smoke.py — pico/ystall.py CPythonilla (EXPRESSO-GC-UUTTO 20.10.2026): kayntiaika, rivit, bitit ja palautus.

    python3 testit/ystall_smoke.py     RESULT: <n> failed
"""
import asyncio as aio
import contextlib
import io
import os
import sys
import time
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico'))
FAILED = []


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + (' — %s' % (info,) if info and not ok else ''))
    if not ok:
        FAILED.append(name)


ut = types.SimpleNamespace(ticks_us=lambda: int(time.perf_counter() * 1e6), ticks_diff=lambda a, b: a - b,
                           ticks_add=lambda a, b: a + b, ticks_ms=lambda: int(time.perf_counter() * 1e3))
GC_N = [0]
sys.modules['gc'] = types.SimpleNamespace(collect=lambda: GC_N.__setitem__(0, GC_N[0] + 1), mem_free=lambda: 1000)
import diagnet  # noqa: E402
import ystall  # noqa: E402


class SlowAio:
    """sleep_ms(0) vie 60 ms joka 200. kerralla: katko, jonka ystall nayttaa."""
    def __init__(self):
        self.k = 0

    async def sleep_ms(self, ms):
        self.k += 1
        if self.k % 200 == 0:
            time.sleep(0.06)


bd = types.SimpleNamespace(diag=types.SimpleNamespace(quiet=False), tbusy=['-', 0])
buf = io.StringIO()
t = time.perf_counter()
with contextlib.redirect_stdout(buf):
    aio.run(ystall.ystall_run(bd, ut, SlowAio(), 1, 7))
el = time.perf_counter() - t
out = buf.getvalue().splitlines()
end = [l for l in out if l.startswith('YSTALL_END')]
check('runs ~1 s', 0.9 < el < 2.0, el)
check('start and end lines', out[0].startswith('YSTALL_START s=1 mode=7') and len(end) == 1, out[:1] + end)
check('stalls logged with task', any(l.startswith('YSTALL t_ms=') and 'task=-:0' in l for l in out))
check('y50 counted', end and ' y50=0 ' not in end[0], end)
check('gc every 300 ms', 2 <= GC_N[0] <= 4 and end and ('gc_n=%d ' % GC_N[0]) in end[0], (GC_N, end))
check('quiet and legacy restored', bd.diag.quiet is False and diagnet.LEGACY_SEND is False)

# bit 8: the guard's poll pauses for the run and resumes afterwards, also when the run raises; the timer stays
class Guard:
    def __init__(self):
        self.paused = False
        self.seen = []


class SeeAio(SlowAio):
    def __init__(self, g):
        SlowAio.__init__(self); self.g = g

    async def sleep_ms(self, ms):
        self.g.seen.append(self.g.paused)
        await SlowAio.sleep_ms(self, ms)


g = Guard()
bd = types.SimpleNamespace(diag=types.SimpleNamespace(quiet=False), tbusy=['-', 0], relay_guard=g)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aio.run(ystall.ystall_run(bd, ut, SeeAio(g), 1, 10))
check('bit 8: paused during the run, resumed after', g.seen and all(g.seen) and g.paused is False
      and 'guard_off=1' in buf.getvalue())


class Boom:
    async def sleep_ms(self, ms):
        raise RuntimeError('x')


g2 = Guard()
bd = types.SimpleNamespace(diag=types.SimpleNamespace(quiet=False), tbusy=['-', 0], relay_guard=g2)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        aio.run(ystall.ystall_run(bd, ut, Boom(), 1, 8))
except RuntimeError:
    pass
check('bit 8: resumed after an exception', g2.paused is False)
g3 = Guard()
bd = types.SimpleNamespace(diag=None, tbusy=None, relay_guard=g3)
with contextlib.redirect_stdout(io.StringIO()):
    aio.run(ystall.ystall_run(bd, ut, SeeAio(g3), 1, 3))
check('without bit 8 the guard is not paused', g3.seen and not any(g3.seen))

# bit 16: radio off for the run, back on and a join afterwards
class Wlan:
    def __init__(self):
        self.calls = []

    def active(self, v):
        self.calls.append(v)


w = Wlan()
joins = []
dg = types.SimpleNamespace(quiet=False, wlan=w, _join=lambda now: joins.append(now))
bd = types.SimpleNamespace(diag=dg, tbusy=['-', 0])
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aio.run(ystall.ystall_run(bd, ut, SlowAio(), 1, 16))
check('bit 16: radio off then on, join', w.calls == [False, True] and len(joins) == 1 and 'radio_off=1' in buf.getvalue())
w2 = Wlan()
bd = types.SimpleNamespace(diag=types.SimpleNamespace(quiet=False, wlan=w2, _join=lambda now: None), tbusy=None)
with contextlib.redirect_stdout(io.StringIO()):
    aio.run(ystall.ystall_run(bd, ut, SlowAio(), 1, 2))
check('without bit 16 the radio is untouched', w2.calls == [])

# bit 32: core 1 reads as in a shot (c1_on), handed back after (c1_off), also when the run raises
class Ts:
    def __init__(self):
        self.calls = []

    def c1_on(self):
        self.calls.append('on'); return True

    def c1_off(self):
        self.calls.append('off')


ts = Ts()
bd = types.SimpleNamespace(diag=None, tbusy=None, temperature_sensor=ts)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aio.run(ystall.ystall_run(bd, ut, SlowAio(), 1, 34))
check('bit 32: c1_on then c1_off', ts.calls == ['on', 'off'] and ' c1=1' in buf.getvalue())
ts2 = Ts()
bd = types.SimpleNamespace(diag=None, tbusy=None, temperature_sensor=ts2)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        aio.run(ystall.ystall_run(bd, ut, Boom(), 1, 32))
except RuntimeError:
    pass
check('bit 32: c1_off after an exception', ts2.calls == ['on', 'off'])

# bit 64: core 1 jitter test is requested (WANT 2) with the ADC, and its C1J line printed when core 1 is done
import threading  # noqa: E402
import classes as CL  # noqa: E402


class Ts64:
    def __init__(self):
        self.c1 = [0] * 13
        self.c1[9] = 1
        self.c1_test = [0] * 7
        self.c1_adc = None


ts = Ts64()
adc = types.SimpleNamespace(read_u16=lambda: 1234)
bd = types.SimpleNamespace(diag=None, tbusy=None, temperature_sensor=ts,
                           pressure_sensor=types.SimpleNamespace(pressure_sensor=adc))


def core1():
    while ts.c1[0] != 2:
        time.sleep(0.001)
    CL.TemperatureSensor._c1_jitter(ts, ut)
    ts.c1[0] = 0


th = threading.Thread(target=core1, daemon=True)
th.start()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aio.run(ystall.ystall_run(bd, ut, SlowAio(), 1, 66))
c1j = [l for l in buf.getvalue().splitlines() if l.startswith('C1J')]
check('bit 64: C1J line from the core 1 loop', len(c1j) == 1 and 'done=1' in c1j[0] and ' adc=1' in c1j[0]
      and 900 <= ts.c1_test[1] <= 1100, c1j)
check('bit 64: WANT back to 0', ts.c1[0] == 0)

# core 1 runs with the heap locked: no tuple building in its code (1cd1bbf: r[1], ..., r[5] = ... ended the thread)
import inspect  # noqa: E402
import re  # noqa: E402
src = inspect.getsource(CL.TemperatureSensor._c1_jitter) + inspect.getsource(CL.TemperatureSensor._c1_loop) + \
    inspect.getsource(CL.TemperatureSensor._c1_exec) + inspect.getsource(CL.TemperatureSensor._c1_put)
code = '\n'.join(l.split('#')[0] for l in src.splitlines() if not l.strip().startswith(('"""', 'locked', 'an event')))
check('core 1 code: no true division (float = allocation)', not re.search(r'[^/]/[^/]', code.replace('//', '')),
      re.findall(r'.{20}[^/]/[^/].{10}', code.replace('//', ''))[:3])
multi = [l.strip() for l in src.splitlines() if re.match(r'^\s*[^#=]*,[^#=]*,[^#=]*,[^#=]*=[^=]', l)]
check('core 1 code: no assignment to more than 3 targets (tuple = allocation)', not multi, multi)

# bit 128: dry executor on a host thread (core 1) with the real _c1_exec; core 0 (ystall) feeds events and reads samples
from array import array  # noqa: E402


class TsX:
    def __init__(self):
        self.c1 = [0] * 13
        self.c1[1] = self.c1[9] = 1
        self.cx = array('i', [0] * 21)
        self.cx_wt = array('i', [0] * CL.CX_NE)
        self.cx_samp = array('i', [0] * (2 * CL.CX_NS))
        self.cx_ev = array('i', [0] * (2 * CL.CX_NE))
        self.cx_pin = types.SimpleNamespace(value=lambda v: (_ for _ in ()).throw(AssertionError('dry run set the pin')))
        self.c1_adc = None
        self.temperature_sensor = self.c1_ring = self.c1_tab = None      # TEMP 0: not used


P30 = 1 << 30
utw = types.SimpleNamespace(ticks_us=lambda: int(time.perf_counter() * 1e6) % P30,
                            ticks_diff=lambda a, b: ((a - b + P30 // 2) % P30) - P30 // 2,
                            ticks_add=lambda a, b: (a + b) % P30, ticks_ms=lambda: int(time.perf_counter() * 1e3))
tx = TsX()
bd = types.SimpleNamespace(diag=None, tbusy=None, temperature_sensor=tx,
                           pressure_sensor=types.SimpleNamespace(pressure_sensor=types.SimpleNamespace(read_u16=lambda: 20000)))


def core1x():
    while tx.c1[0] != 3:
        time.sleep(0.0005)
    tx.c1[1] = 0
    CL.TemperatureSensor._c1_exec(tx, tx.c1, utw)
    tx.c1[1] = 1


thx = threading.Thread(target=core1x, daemon=True)
thx.start()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aio.run(ystall.ystall_run(bd, utw, SlowAio(), 1, 128))
c1x = [l for l in buf.getvalue().splitlines() if l.startswith('C1X')]
vals = dict(kv.split('=') for kv in c1x[0].split()[1:]) if c1x else {}
check('bit 128: C1X line', len(c1x) == 1, buf.getvalue()[-300:])
check('bit 128: ~1000 samples, all read as bar', vals and 800 <= int(vals['n']) <= 1100 and int(vals['bar_n']) >= int(vals['n']) - 300, vals)
check('bit 128: events carried out in order, few pending', vals and 60 <= int(vals['nev']) <= int(vals['written'])
      and int(vals['written']) - int(vals['nev']) <= 8, vals)
# SlowAio stops core 0 for 60 ms, longer than the 40 ms queue: the worst event was written after its due time
check('bit 128: worst late event shows it was written late', vals and int(vals['late']) > 0 and int(vals['lwr_us']) > 0, vals)
check('bit 128: WANT back to 0, dry pin state recorded', tx.c1[0] == 0 and tx.cx[CL.CX_DRY] == 1)

# C1-JAKSOT vaihe 2: core 1 never sleeps (a sleep_ms there stretched core 0's collections to 80-600 ms, 20.10.2026)
check('core 1 code: no sleep', 'sleep' not in code, [l for l in code.splitlines() if 'sleep' in l][:3])


class Drv:
    """MAX31865 steps and parts: each takes STEP s; rtd_result and rtd_part 6 give RAW. Records the order."""
    STEP = 0.0002
    RAW = CL.TEMP_C1_RAW_LO + 9 * 256          # table below: 90.00 C

    def __init__(self):
        self.seq = []

    def _step(self, k):
        self.seq.append(k)
        t = time.perf_counter()
        while time.perf_counter() - t < self.STEP:
            pass

    def rtd_start(self):
        self._step('s')

    def rtd_convert(self):
        self._step('c')

    def rtd_result(self):
        self._step('r')
        return self.RAW

    def rtd_part(self, k):
        self._step(str(k))
        return self.RAW if k == 6 else -1


def real_ts(ut_):
    """A TemperatureSensor without the chip: the real c1_* methods and core 1 code on host arrays."""
    t = CL.TemperatureSensor.__new__(CL.TemperatureSensor)
    t.temperature_sensor = Drv()
    t.temps = [93.0] * 7
    t.temps_i = 3
    t.c1_utime = ut_
    t.c1_ring = array('i', [0] * 7)
    t.c1_tab = array('i', [k * 1000 for k in range(CL.TEMP_C1_RAW_N + 1)])
    t.c1_seq0 = 0
    t.c1_log0 = 0
    t.c1_rest = 0
    t.c1 = array('i', [0] * 14)
    t.c1[CL.C1_IDLE] = t.c1[CL.C1_RUN] = 1
    t.c1_test = array('i', [0] * 7)
    t.c1_adc = None
    t.cx = array('i', [0] * 21)
    t.cx_wt = array('i', [0] * CL.CX_NE)
    t.cx_samp = array('i', [0] * (2 * CL.CX_NS))
    t.cx_ev = array('i', [0] * (2 * CL.CX_NE))
    t.cx_pin = types.SimpleNamespace(value=lambda v: (_ for _ in ()).throw(AssertionError('dry run set the pin')))
    return t


# bit 512 (with 128): the executor reads the temperature between samples; c1_off ends it and hands the average back
tt = real_ts(utw)
th5 = threading.Thread(target=lambda: CL.TemperatureSensor._c1_loop(tt, tt.c1, tt.c1_ring, tt.c1_tab,
                                                                     tt.temperature_sensor, utw), daemon=True)
th5.start()
bd = types.SimpleNamespace(diag=None, tbusy=None, temperature_sensor=tt,
                           pressure_sensor=types.SimpleNamespace(pressure_sensor=types.SimpleNamespace(read_u16=lambda: 20000)))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aio.run(ystall.ystall_run(bd, utw, SlowAio(), 1, 640))
out5 = buf.getvalue().splitlines()
c1x = [l for l in out5 if l.startswith('C1X')]
c1t = [l for l in out5 if l.startswith('C1T')]
vx = dict(kv.split('=') for kv in c1x[0].split()[1:]) if c1x else {}
vt = dict(kv.split('=') for kv in c1t[0].split()[1:]) if c1t else {}
check('bit 512: C1X and C1T lines', len(c1x) == 1 and len(c1t) == 1, out5[-4:])
def avg_after(n):
    """core 0's 93.0 x 7 (temps_i 3) after n readings of 90.0: the average and the list c1_off hands back"""
    r = [93.0] * 7
    for k in range(n):
        r[(3 + k) % 7] = 90.0
    return '%.2f' % (sum(r) / 7), r


check('bit 512: readings every ~250 ms between samples', vt and 2 <= int(vt['t_n']) <= 5
      and vt['cdeg'] == avg_after(int(vt['t_n']))[0], vt)
check('bit 512: step durations recorded (K3)', vt and all(0 < int(vt[k]) < 50000 for k in ('ts_us', 'tc_us', 'tr_us')), vt)
check('bit 512: samples and events go on', vx and int(vx['n']) >= 700 and int(vx['nev']) >= 60, vx)
seq = ''.join(tt.temperature_sensor.seq)
check('bit 512: parts 0-6 in order, one byte each (K3); a reading left half way is finished',
      seq.replace('0123456', '') == '' and seq.endswith('6'), seq[-12:])
check('bit 512: c1_off handed the sensor back', tt.c1[CL.C1_WANT] == 0 and tt.cx[CL.CX_TEMP] == 0
      and vt and tt.temps == avg_after(tt.c1[CL.C1_SEQ])[1] and not tt.c1_active(),
      (tt.c1[CL.C1_WANT], tt.cx[CL.CX_TEMP], tt.temps))

# the reading loop (WANT 1) on core 1 without sleep_ms: utime here has none, a call would raise and end the thread
t1 = real_ts(utw)
th6 = threading.Thread(target=lambda: CL.TemperatureSensor._c1_main(t1), daemon=True)
sys.modules['micropython'] = types.SimpleNamespace(heap_lock=lambda: None, heap_unlock=lambda: None)
th6.start()
time.sleep(0.05)
check('WANT 0: core 1 idle', t1.c1[CL.C1_IDLE] == 1 and t1.c1[CL.C1_RUN] == 1)
t1.c1_on()
time.sleep(0.6)
n1 = t1.c1[CL.C1_SEQ]
check('WANT 1: readings every ~250 ms, no sleep', 2 <= n1 <= 4 and '%.2f' % t1.c1_temperature() == avg_after(n1)[0]
      and t1.c1[CL.C1_ERR] == 0, (n1, t1.c1_temperature(), t1.c1[CL.C1_ERR]))
t1.c1_off()
check('c1_off: back to WANT 0 and core 0', t1.c1[CL.C1_IDLE] == 1 and not t1.c1_active()
      and t1.temps == avg_after(t1.c1[CL.C1_SEQ])[1], t1.temps)
t1.c1[CL.C1_WANT] = -1
th6.join(1)
check('WANT -1 ends the thread without an error', not th6.is_alive() and t1.c1[CL.C1_ERR] == 0 and t1.c1[CL.C1_RUN] == 0)

# C1-JAKSOT vaihe 2: core 1 reads at rest too (core 0's read_rtd slept 75 ms twice a main loop round, 20.10.2026)
src_main = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico', 'main.py')).read()
check('rest: main.py starts the rest reading right after c1_start',
      re.search(r'c1_start\(utime\)\n\s*temperature_sensor\.c1_rest_on\(\)', src_main) is not None)
tr = real_ts(utw)
tr.temperature_sensor.temperature = property(lambda s: (_ for _ in ()).throw(AssertionError('core 0 read the chip')))
th7 = threading.Thread(target=lambda: CL.TemperatureSensor._c1_main(tr), daemon=True)
th7.start()
time.sleep(0.05)
with contextlib.redirect_stdout(io.StringIO()):
    tr.c1_rest_on()
time.sleep(0.4)
check('rest: WANT 1, core 1 reads, core 0 takes its average', tr.c1_rest == 1 and tr.c1[CL.C1_WANT] == 1
      and tr.c1[CL.C1_SEQ] >= 1 and tr.read_temperature() == tr.c1_temperature(), (tr.c1[CL.C1_WANT], tr.c1[CL.C1_SEQ]))
tr.c1[CL.C1_GAP] = 99999
s0 = tr.c1[CL.C1_SEQ]
check('rest: a shot c1_on keeps core 1 reading', tr.c1_on() and tr.c1[CL.C1_WANT] == 1 and tr.c1_temperature() is not None)
time.sleep(0.4)
log = dict(kv.split('=') for kv in tr.c1_log().split())
check('rest: the shot log counts from its c1_on, gap started again (RST)', 1 <= int(log['c1_n']) <= 3
      and int(log['c1_gap_ms']) < 1000 and tr.c1[CL.C1_RST] == 0 and tr.c1[CL.C1_SEQ] - s0 == int(log['c1_n']), log)
tr.c1_off()
check('rest: c1_off leaves core 1 reading', tr.c1[CL.C1_WANT] == 1 and tr.c1_active())
bd7 = types.SimpleNamespace(diag=None, tbusy=None, temperature_sensor=tr,
                            pressure_sensor=types.SimpleNamespace(pressure_sensor=types.SimpleNamespace(read_u16=lambda: 20000)))
for mode, name in ((640, '128+512: the executor reads from the rest reading'), (128, '128: core 0 takes the chip for the run')):
    tr.temperature_sensor.seq = []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        aio.run(ystall.ystall_run(bd7, utw, SlowAio(), 1, mode))
    o7 = buf.getvalue()
    n7 = tr.c1[CL.C1_SEQ]
    time.sleep(0.4)
    seq7 = ''.join(tr.temperature_sensor.seq)
    check('rest: ystall %s; WANT 1 again after it' % name, 'C1X' in o7 and ('C1T' in o7) == (mode == 640)
          and tr.c1[CL.C1_WANT] == 1 and tr.c1_rest == 1 and tr.c1[CL.C1_SEQ] > n7 and tr.cx[CL.CX_TEMP] == 0
          and (('0123456' in seq7) == (mode == 640)), (o7.splitlines()[-3:], tr.c1[CL.C1_WANT], seq7[:30]))
with contextlib.redirect_stdout(io.StringIO()):
    tr.c1_take()
check('rest: c1_take gives the chip to core 0 (WANT 0, average handed back)', tr.c1[CL.C1_WANT] == 0
      and tr.c1[CL.C1_IDLE] == 1 and not tr.c1_active() and tr.temps == avg_after(tr.c1[CL.C1_SEQ])[1], tr.temps)
tr.c1[CL.C1_WANT] = -1
th7.join(1)

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
