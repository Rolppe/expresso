"""EXPRESSO-UUTTOLOKI smoke (5.10.2026): the August brew log ported to the current firmware, on the host.

  python3 testit/uuttoloki_smoke.py        (from Infra/iot/expresso; reads pico/ directly, no copy)

Checks the logger (10 Hz v3 rows, session tare, phases, short and long sessions), the app commands (sync,
brew_log?, brew_log:ack), the BLE multipack against a fake BLE stack (piece sizes, frame order, rows intact,
no live packet inside a multipack, resend after a reconnect, ack mid-flight) and run_shot: a brew-switch shot
(PB) leaves a pending log, a test shot (TS) does not. The app's reassembly is modelled from the August
firmware's contract: pieces are joined until a newline closes the frame. Exit 0 = RESULT: 0 failed.
"""
import sys, os, types, json, asyncio as _aio, io, contextlib, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.join(HERE, '..', 'pico')
sys.path.insert(0, FW)

clock = [0.0]
hooks = []                      # called every simulated ms, like the BLE task getting turns
utime = types.ModuleType('utime')
utime.ticks_ms = lambda: int(round(clock[0] * 1000))
utime.ticks_us = lambda: int(round(clock[0] * 1000000))
utime.ticks_diff = lambda a, b: a - b
utime.ticks_add = lambda a, b: a + b
utime.sleep_ms = lambda ms: advance(ms / 1000.0)
sys.modules['utime'] = utime

pins = {}
class Pin:
    OUT = 1; IN = 0; PULL_DOWN = 2; PULL_UP = 3
    def __init__(self, n, mode=None, pull=None, value=None):
        self.n = n
        pins.setdefault(n, 0)
        if value is not None: pins[n] = value
    def value(self, v=None):
        if v is None: return pins[self.n]
        pins[self.n] = 1 if v else 0
machine = types.ModuleType('machine'); machine.Pin = Pin
machine.WDT = lambda timeout=0: types.SimpleNamespace(feed=lambda: None)
machine.disable_irq = lambda: 0; machine.enable_irq = lambda s=0: None
sys.modules['machine'] = machine
bluetooth = types.ModuleType('bluetooth')
bluetooth.UUID = lambda x: x.encode()   # bytes() of a real UUID; 128-bit here, so not in the adv payload
bluetooth.FLAG_READ = 1; bluetooth.FLAG_NOTIFY = 2; bluetooth.FLAG_WRITE = 4
sys.modules['bluetooth'] = bluetooth
mp = types.ModuleType('micropython'); mp.const = lambda x: x
sys.modules['micropython'] = mp
# MicroPython asyncio: sleep_ms; here it advances the virtual clock
masync = types.ModuleType('asyncio')
masync.__dict__.update(_aio.__dict__)
async def _sleep_ms(ms):
    advance(max(ms, 0) / 1000.0)
    await _aio.sleep(0)
async def _sleep(s):
    advance(s)
    await _aio.sleep(0)
masync.sleep_ms = _sleep_ms; masync.sleep = _sleep
# One loop for the whole run: BLE IRQs call create_task outside any coroutine, as on the Pico
LOOP = _aio.new_event_loop(); _aio.set_event_loop(LOOP)
masync.create_task = LOOP.create_task
RUN = LOOP.run_until_complete
sys.modules['asyncio'] = masync

state = {'p': 0.0}
def advance(dt_s):
    for _ in range(int(round(dt_s * 1000))):
        p = state['p']
        p += ((26 * (1 - p / 13.0)) if pins.get(11, 0) else (-1.25 * p)) / 1000.0
        state['p'] = p
        clock[0] += 0.001
        if int(round(clock[0] * 1000)) % 30 == 0:
            for h in hooks:
                h()

spec = importlib.util.spec_from_file_location('preset', os.path.join(FW, 'preset.py'))
preset = importlib.util.module_from_spec(spec); spec.loader.exec_module(preset); sys.modules['preset'] = preset
import brew_logger as BL
import commands, functions, classes
import bluetooth_handler as bh

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
    if not cond: fails.append(name)


class Relay:
    def __init__(self, n): self.n = n
    def value(self, v=None): return Pin(self.n).value(v)

class FakeScale:
    raw_a = 670000; raw_b = 58000
    def scale_meta(self):
        return {'scale': 2175.0, 'trim_b': 1.05, 'sense': 1, 'off_a': 669877.7, 'off_b': 58314.4}


def brew_data():
    bd = types.SimpleNamespace()
    bd.pending_brew_log = None; bd.brew_log_send_requested = False; bd.brew_log_tx_reset = False
    bd.settings_requested = False; bd.command_known = True
    bd.RELAY_PUMP, bd.RELAY_SOLENOID, bd.RELAY_HEATER = Relay(11), Relay(12), Relay(13)
    bd.boiler_temperature = 93.4; bd.pressure = 0.0; bd.flow = None; bd.weight = 250.0; bd.mode = 'IDLE'
    bd.standby = False
    bd.tray_scale = FakeScale(); bd.brew_logger = BL.BrewSessionLogger(utime)
    return bd


def record(bd, seconds, modes=(('pre-infusion main', 0), ('brew loop', 5), ('soft pressure release', 25))):
    """Drive a logger session for <seconds> through brew_log_service every 30 ms, weight rising 1.5 g/s."""
    log = bd.brew_logger
    t0 = utime.ticks_ms()
    log.start(t0, bd.weight, bd.tray_scale.scale_meta() if bd.tray_scale else None)
    w0 = bd.weight
    def hook():
        el = (utime.ticks_ms() - t0) / 1000.0
        for m, at in modes:
            if el >= at:
                bd.mode = m
        bd.weight = None if w0 is None else w0 + 1.5 * el; bd.flow = 1.5; bd.pressure = 8.0 if el > 5 else 2.5
        pins[11] = int(el * 50) % 2
        BL.brew_log_service(bd, utime)
    hooks.append(hook)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        advance(seconds)
        hooks.remove(hook)
        ready = log.end_session(utime.ticks_ms(), bd.weight, 'spr_end')
        BL.brew_log_service(bd, utime)
    return ready, out.getvalue()


# ---------------------------------------------------------------- 1. logger
bd = brew_data()
ready, out = record(bd, 30)
p = bd.pending_brew_log
check('30 s session becomes READY and is handed to pending_brew_log', ready and p is not None, out.strip()[-120:])
check('logger back to IDLE after the hand-over', not bd.brew_logger.is_active() and not bd.brew_logger.is_ready())
check('send requested from meta', bd.brew_log_send_requested and bd.brew_log_tx_reset)
n = p['n_samples']
check('10 Hz: 30 s gives 295-301 rows', 295 <= n <= 301, 'n=%d' % n)
gaps = [b[0] - a[0] for a, b in zip(p['samples'], p['samples'][1:])]
check('row spacing 70-130 ms on a 100 ms grid (sampling from a 30 ms task)', min(gaps) >= 70 and max(gaps) <= 130,
      'min %d max %d' % (min(gaps), max(gaps)))
r = p['samples'][-1]
check('v3 row: 8 ints', len(r) == 8 and all(isinstance(x, int) for x in r), str(r))
check('row values: T x10, P x100, F x100, raw HX, W x10 session-tared',
      r[1] == 934 and r[2] == 800 and r[3] == 150 and r[4] == 670000 and r[5] == 58000 and 440 <= r[6] <= 450,
      str(r))
check('first row W is 0 (session tare)', p['samples'][0][6] == 0, str(p['samples'][0]))
check('flags carry pump and heater bits', set(x[7] for x in p['samples']) <= {0, 1, 2, 3}
      and any(x[7] & 1 for x in p['samples']))
names = [e[0] for e in p['events']]
check('events: start, three phases once each, log_stop, end',
      names == ['session_start', 'phase_PRE_INFUSION', 'phase_BREW', 'phase_SOFT_RELEASE', 'log_stop',
                'log_stop_spr_end', 'session_end'], str(names))
check('scale_at_end_g is session weight (~45 g)', 44.0 <= p['scale_at_end_g'] <= 45.5, str(p['scale_at_end_g']))
check('scale_meta carried', p['scale_meta']['scale'] == 2175.0)
check('format v3, 10 Hz, duration = last row', p['v'] == 3 and p['sample_hz'] == 10
      and p['duration_ms'] == p['samples'][-1][0])

bd2 = brew_data()
ready, out = record(bd2, 10)
check('10 s session discarded (MIN_SESSION_MS 15 s), nothing pending', not ready and bd2.pending_brew_log is None,
      out.strip().splitlines()[-1])
bd3 = brew_data()
ready, out = record(bd3, 70)
p3 = bd3.pending_brew_log
check('70 s session truncated at 65 s', p3 is not None and p3['truncated'] and p3['duration_ms'] < 65000
      and p3['n_samples'] <= 651, 'n=%s' % (p3 and p3['n_samples']))
bd4 = brew_data()
bd4.brew_logger.start(utime.ticks_ms(), None, None)
for i in range(200):
    bd4.brew_logger._event('x%d' % i, i)
check('events capped at MAX_EVENTS', len(bd4.brew_logger._events) == BL.MAX_EVENTS)
bd5 = brew_data(); bd5.tray_scale = None; bd5.weight = None
ready, out = record(bd5, 20)
check('no scale: log still made, raw HX 0, W 0', bd5.pending_brew_log is not None
      and all(x[4] == 0 and x[5] == 0 and x[6] == 0 for x in bd5.pending_brew_log['samples']))

# ---------------------------------------------------------------- 2. commands
bd = brew_data()
with contextlib.redirect_stdout(io.StringIO()) as o:
    up = commands.handle_command(bd, 'sync')
check('sync: known, not a setting change, asks settings', bd.command_known and up is False and bd.settings_requested)
with contextlib.redirect_stdout(io.StringIO()) as o:
    commands.handle_command(bd, 'brew_log?')
check('brew_log? with nothing pending: no request', bd.command_known and not bd.brew_log_send_requested,
      o.getvalue().strip())
bd.pending_brew_log = {'id': 7}
with contextlib.redirect_stdout(io.StringIO()) as o:
    commands.handle_command(bd, 'brew_log?')
check('brew_log? with a pending log: resend from meta', bd.brew_log_send_requested and bd.brew_log_tx_reset,
      o.getvalue().strip())
bd.brew_log_tx_reset = False
with contextlib.redirect_stdout(io.StringIO()) as o:
    commands.handle_command(bd, 'brew_log:ack:7')
check('brew_log:ack:<id> frees the log', bd.pending_brew_log is None and not bd.brew_log_send_requested
      and bd.command_known, o.getvalue().strip())

# ---------------------------------------------------------------- 3. BLE multipack
class FakeBLE:
    def __init__(self): self.sent = []; self.fail_next = 0; self.irq_cb = None
    def active(self, v): pass
    def irq(self, cb): self.irq_cb = cb
    def gatts_register_services(self, s): return ((1, 2),)
    def gap_advertise(self, *a, **k): pass
    def gatts_read(self, h): return self.cmd
    def gatts_notify(self, conn, h, data):
        if self.fail_next:
            self.fail_next -= 1
            raise OSError('ENOMEM')
        self.sent.append(bytes(data) if not isinstance(data, str) else data.encode())


def full_brew_data():
    bd = brew_data()
    bd.pcal_state = 'idle'
    for name, val in (('get_mode', 'IDLE'), ('get_brew_temperature', 93.0), ('get_pre_infusion_mode', True),
                      ('get_pressure_soft_release_mode', True), ('get_fast_heatup_mode', False),
                      ('get_pump_ratio', 0), ('get_weight', 250.0), ('get_flow', None), ('get_brew_pressure', 8.0),
                      ('get_pre_infusion_pressure', 2.5), ('get_pre_infusion_time', 3.0),
                      ('get_pressure_soft_release_time', 1.0)):
        setattr(bd, name, (lambda v: (lambda: v))(val))
    return bd


def ticks(h, n):
    """n transmission ticks (200 ms apart in main.py); each runs the tasks it created to completion."""
    async def go():
        for _ in range(n):
            h.run_transmission()
            await _aio.sleep(0); await _aio.sleep(0)
            for _ in range(50):
                if not h._brew_busy: break
                await _aio.sleep(0)
    with contextlib.redirect_stdout(io.StringIO()) as o:
        RUN(go())
    return o.getvalue()


def frames(sent):
    """App-side reassembly: join pieces until a newline. Returns (frames, stray) where stray are pieces that
    are not part of a newline-terminated frame (live packets have no newline)."""
    out, buf, stray = [], b'', []
    for piece in sent:
        if buf or piece.endswith(b'\n') or b'"brew_log"' in piece:
            buf += piece
            if buf.endswith(b'\n'):
                out.append(json.loads(buf.decode())); buf = b''
        else:
            stray.append(piece)
    return out, stray, buf


bd = full_brew_data()
record(bd, 30)
log = bd.pending_brew_log
ble = FakeBLE()
h = bh.BLEHandler(ble, bd)
h._irq(1, (0, 0, 0)); h._irq(21, (0, 247))
ble.sent = []
steps = bh.brew_log_steps(log)
out = ticks(h, steps + 5)
fr, stray, rest = frames(ble.sent)
mp_pieces = [x for x in ble.sent if x not in stray]
check('MTU 247: every piece <= 240 B', all(len(x) <= 240 for x in ble.sent), 'max %d' % max(len(x) for x in ble.sent))
check('frame order meta, samples 0..n-1, end', [f['part'] for f in fr] == ['meta'] + ['samples'] * (steps - 2) + ['end']
      and [f['i'] for f in fr if f['part'] == 'samples'] == list(range(steps - 2)), str([f['part'] for f in fr][:4]))
rows = [row for f in fr if f['part'] == 'samples' for row in f['rows']]
check('rows arrive intact', rows == log['samples'], '%d vs %d' % (len(rows), len(log['samples'])))
meta = fr[0]
check('meta: id, n_samples, n_parts, events, scale_meta', meta['id'] == log['id'] and meta['n_samples'] == len(rows)
      and meta['n_parts'] == steps - 2 and meta['events'] == log['events'] and 'scale_meta' in meta)
mp_idx = [i for i, x in enumerate(ble.sent) if x not in stray]
inside = [i for i, x in enumerate(ble.sent) if x in stray and mp_idx[0] < i < mp_idx[-1]]
check('no live or settings packet inside the multipack', inside == [], '%d inside' % len(inside))
check('live telemetry resumes after end', len(stray) > 0 and not bd.brew_log_send_requested and h._brew_step is None)
check('log kept until ack', bd.pending_brew_log is log)
check('largest frame %d B' % max(len(json.dumps(f)) for f in fr), max(len(json.dumps(f)) for f in fr) < 4000)

# default MTU 23 -> 20 B pieces
bd = full_brew_data(); record(bd, 20)
ble = FakeBLE(); h = bh.BLEHandler(ble, bd); h._irq(1, (0, 0, 0)); ble.sent = []
ticks(h, bh.brew_log_steps(bd.pending_brew_log) + 1)
fr, stray, rest = frames(ble.sent)
check('MTU 23: multipack in 20 B pieces, frames still whole',
      all(len(x) <= 20 for x in ble.sent if x not in stray) and fr and fr[-1]['part'] == 'end'
      and len(fr) == bh.brew_log_steps(bd.pending_brew_log))

# notify failure: same step again, never samples without meta
bd = full_brew_data(); record(bd, 20)
ble = FakeBLE(); h = bh.BLEHandler(ble, bd); h._irq(1, (0, 0, 0)); h._irq(21, (0, 247)); ble.sent = []
ble.fail_next = 1
ticks(h, bh.brew_log_steps(bd.pending_brew_log) + 3)
fr, stray, rest = frames(ble.sent)
check('failed meta notify is retried; meta first, all parts, end', fr[0]['part'] == 'meta' and fr[-1]['part'] == 'end'
      and len([f for f in fr if f['part'] == 'samples']) == fr[0]['n_parts'])

# disconnect mid-flight, reconnect: resend from meta; live stays off while waiting
bd = full_brew_data(); record(bd, 20)
ble = FakeBLE(); h = bh.BLEHandler(ble, bd); h._irq(1, (0, 0, 0)); h._irq(21, (0, 247)); ble.sent = []
ticks(h, 3)
h._irq(2, (0, 0, 0)); ble.sent = []
ticks(h, 5)
check('no notifies while disconnected', ble.sent == [])
h._irq(1, (1, 0, 0)); h._irq(21, (1, 247)); ble.sent = []
ticks(h, bh.brew_log_steps(bd.pending_brew_log) + 2)
fr, stray, rest = frames(ble.sent)
check('reconnect resends from meta to end', fr and fr[0]['part'] == 'meta' and fr[-1]['part'] == 'end'
      and len(fr) == bh.brew_log_steps(bd.pending_brew_log))

# ack mid-flight: live resumes, nothing pending
bd = full_brew_data(); record(bd, 20)
ble = FakeBLE(); h = bh.BLEHandler(ble, bd); h._irq(1, (0, 0, 0)); h._irq(21, (0, 247))
ticks(h, 3)
ble.cmd = b'brew_log:ack:1'
with contextlib.redirect_stdout(io.StringIO()):
    h._irq(3, (0, 2))
ble.sent = []
ticks(h, 3)
fr, stray, rest = frames(ble.sent)
check('ack mid-flight: multipack stops, live resumes', bd.pending_brew_log is None and h._brew_step is None
      and fr == [] and len(stray) > 0)

# sync over BLE sends settings
bd = full_brew_data()
ble = FakeBLE(); h = bh.BLEHandler(ble, bd)
async def conn0():
    h._irq(1, (0, 0, 0)); await _aio.sleep(0); await _aio.sleep(0)
with contextlib.redirect_stdout(io.StringIO()):
    RUN(conn0())
ble.sent = []
ble.cmd = b'sync'
async def irq_sync():
    h._irq(3, (0, 2))
    await _aio.sleep(0); await _aio.sleep(0)
with contextlib.redirect_stdout(io.StringIO()):
    RUN(irq_sync())
check('sync over BLE sends the two settings packets', len(ble.sent) == 2 and b'pre_infusion_time' in ble.sent[1]
      and not bd.settings_requested)

# connect with a pending log requests it
bd = full_brew_data(); record(bd, 20); bd.brew_log_send_requested = False; bd.brew_log_tx_reset = False
ble = FakeBLE(); h = bh.BLEHandler(ble, bd)
async def conn():
    h._irq(1, (0, 0, 0)); await _aio.sleep(0)
with contextlib.redirect_stdout(io.StringIO()):
    RUN(conn())
check('connect with a pending log requests it from meta', bd.brew_log_send_requested and bd.brew_log_tx_reset)

# ---------------------------------------------------------------- 4. run_shot: PB logs, TS does not
class Sensor:
    window_peak = 0.0
    def get_pressure(self): advance(0.020); return state['p']
    def sample_average(self, utime_mod, window_us=None, burst=8): advance(0.004); return state['p']
    def reset_average(self): pass
class Temp:
    def read_temperature(self): advance(0.080); return 93.0
    def c1_active(self): return False
    def c1_on(self): return False
    def c1_off(self): pass
    def c1_temperature(self): return None
    def c1_log(self): return 'c1_n=-1'

def shot_brew_data():
    bd = classes.BrewData.__new__(classes.BrewData)
    bd.pressure_sensor = Sensor(); bd.temperature_sensor = Temp()
    bd.relay_guard = types.SimpleNamespace(utime=utime)
    bd.RELAY_PUMP, bd.RELAY_SOLENOID, bd.RELAY_HEATER = Pin(11), Pin(12), Pin(13)
    bd.pre_infusion_mode = False; bd.brew_pressure = 8.0; bd.pressure_soft_release_mode = True
    bd.pressure_soft_release_time = 1.0; bd.soft_pressure_release_arming_pressure = 3; bd.brew_temperature = 93.0
    bd.mode = 'IDLE'; bd.pressure = 0.0; bd._boiler_temperature = 93.0; bd.pump_ratio = 0
    bd.learned_ff_brew = 0.5; bd.pressure_filtered = 0.0; bd.flow_mode = False
    bd.weight = 250.0; bd.weight_ms = 0; bd.flow = None; bd.weight_a = bd.weight_b = 0.0
    bd.weight_limit = 0.0; bd.weight_rise_limit = 0.0
    bd.pending_brew_log = None; bd.brew_log_send_requested = False; bd.brew_log_tx_reset = False
    bd.brew_logger = BL.BrewSessionLogger(utime); bd.tray_scale = FakeScale()
    return bd

class Ratio:
    def get_ratio(self): return 0.5
    def set_pump_on(self): pass
    def set_pump_off(self): pass

def shot(bd, label, seconds):
    t_end = utime.ticks_ms() + int(seconds * 1000)
    def running(): return utime.ticks_diff(t_end, utime.ticks_ms()) > 0
    def hook():
        bd.pressure = state['p']
        BL.brew_log_service(bd, utime)
    hooks.append(hook)
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            RUN(functions.run_shot(bd, utime, masync, Ratio(), running, label))
            BL.brew_log_service(bd, utime)
    finally:
        hooks.remove(hook)
    return out.getvalue()

bd = shot_brew_data()
try:
    out = shot(bd, 'PB', 20)
    pl = bd.pending_brew_log
    check('PB shot 20 s: pending log, ended at soft release', pl is not None
          and [e[0] for e in pl['events']][-2:] == ['log_stop_spr_end', 'session_end'],
          str(pl and [e[0] for e in pl['events']]))
    check('PB log ~20-21 s of rows, phases BREW and SOFT_RELEASE', pl is not None and 190 <= pl['n_samples'] <= 212
          and 'phase_BREW' in [e[0] for e in pl['events']] and 'phase_SOFT_RELEASE' in [e[0] for e in pl['events']],
          'n=%s' % (pl and pl['n_samples']))
    check('PB log pressure reaches the 8 bar hold', pl is not None and max(r[2] for r in pl['samples']) >= 700)
except Exception as e:
    check('PB shot runs', False, repr(e))
bd = shot_brew_data()
try:
    out = shot(bd, 'TS', 20)
    check('TS test shot: no log', bd.pending_brew_log is None and not bd.brew_logger.is_active())
except Exception as e:
    check('TS shot runs', False, repr(e))
bd = shot_brew_data()
try:
    out = shot(bd, 'PB', 8)
    check('PB shot 8 s: discarded as too short', bd.pending_brew_log is None and 'BREW_LOG discard' in out)
except Exception as e:
    check('short PB shot runs', False, repr(e))

# VALMIUSTILA in the live packet (5.10.2026): the key only while standby holds, and the packet still fits
bd = full_brew_data()
check('live packet: no standby key outside standby', 'standby' not in bh.live_payload(bd))
bd.standby = True
raw = bh.trim_payload(bh.live_payload(bd), json, bh.BLEHandler.MAX_NOTIFY)
check('live packet in standby: standby true, weight kept, <= 240 B', raw is not None
      and json.loads(raw).get('standby') is True and 'weight' in json.loads(raw), '%s B' % (raw and len(raw)))

print('\nRESULT: %d failed' % len(fails)); sys.exit(1 if fails else 0)
