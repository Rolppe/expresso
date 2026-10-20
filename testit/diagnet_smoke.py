#!/usr/bin/env python3
"""diagnet_smoke.py — Picon diagnostiikkalinkin isäntätesti (EXPRESSO-DIAGNET 20.10.2026, paketit/DIAGNET.md).

Ajaa `pico/diagnet.py`:n ja `pico/brew_logger.py`:n näytekoukun CPythonilla valemoduuleilla: rengas ja sen
ylivuoto, dupterm-tee, EXD1-otsake ja paketointi, estämätön virhepolku, Wi-Fin uudelleenliittyminen (ei uuton
aikana), sykkeen väli ja kentät, kaatumispolun flush ja `enabled: False`.

    python3 testit/diagnet_smoke.py        RESULT: <n> failed, epänolla paluuarvo jos punaisia
"""

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico'))

FAILED = []


def check(name, ok):
    print(('ok   ' if ok else 'FAIL ') + name)
    if not ok:
        FAILED.append(name)


class Clock:
    def __init__(self):
        self.ms = 1000
        self.s = 100

    def ticks_ms(self):
        return self.ms

    def ticks_us(self):
        return self.ms * 1000

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b

    def time(self):
        return self.s


class Wlan:
    def __init__(self):
        self.connected = False
        self.joins = 0
        self.act = None

    def active(self, v=None):
        if v is not None:
            self.act = v
        return self.act

    def config(self, key):
        return b'\x28\xcd\xc1\x01\x02\x03'

    def isconnected(self):
        return self.connected

    def connect(self, ssid, pw):
        self.joins += 1

    def status(self, key):
        return -61


WLAN = Wlan()
network = types.SimpleNamespace(STA_IF=0, WLAN=lambda i: WLAN)


class Sock:
    def __init__(self):
        self.sent = []
        self.fail = False
        self.blocking = None

    def setblocking(self, v):
        self.blocking = v

    def sendto(self, data, addr):
        if self.fail:
            raise OSError(113)
        self.sent.append((bytes(data), addr))     # sendto copies: the sender reuses one packet buffer


SOCK = Sock()
socket_mod = types.SimpleNamespace(AF_INET=2, SOCK_DGRAM=2, socket=lambda a, b: SOCK)


class FakeOs:
    def __init__(self):
        self.dupterm_args = None

    def dupterm(self, stream, slot):
        self.dupterm_args = (stream, slot)

    def urandom(self, n):
        return bytes([0xab, 0xcd, 0x12, 0x34][:n])

    def uname(self):
        return types.SimpleNamespace(version='v1.28.0 on 2026-04-01')


class Irq:
    def __init__(self):
        self.depth = 0
        self.max_depth = 0

    def disable_irq(self):
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        return 7

    def enable_irq(self, st):
        self.depth -= 1

    def reset_cause(self):
        return 3


gc_mod = types.SimpleNamespace(mem_free=lambda: 123456, mem_alloc=lambda: 98765)

import diagnet as D  # noqa: E402

# ---- Ring -------------------------------------------------------------------------------------------
irq = Irq()
r = D.Ring(16, irq)
r.put(b'abcdef')
check('ring take order', r.take(3) == b'abc' and r.take(10) == b'def' and r.size == 0)
r.put(b'0123456789')
r.put(b'ABCDEFGHIJ')      # 20 bytes into 16: 4 oldest overwritten
check('ring overflow drops oldest', r.drop == 4 and r.take(100) == b'456789ABCDEFGHIJ')
r.put(b'x' * 40)
check('ring oversized write keeps tail', r.size == 16 and r.drop == 4 + 24 and r.take(100) == b'x' * 16)
r.put(b'wrap1234')
r.take(5)
r.put(b'WXYZWXYZWXYZ')    # wraps around the end
check('ring wrap', r.take(100) == b'234WXYZWXYZWXYZ')
check('ring irq balanced', irq.depth == 0 and irq.max_depth == 1)

# EXPRESSO-GC-UUTTO: take_into and put against a reference, and an IRQ put landing between the snapshot and
# the IRQ-off section (the hook runs once, just before disable_irq: the guard's Timer print)
class HookIrq(Irq):
    def __init__(self):
        Irq.__init__(self)
        self.hook = None

    def disable_irq(self):
        h, self.hook = self.hook, None
        if h is not None:
            h()
        return Irq.disable_irq(self)


import random as _rnd  # noqa: E402
_rnd.seed(7)
hi = HookIrq()
r = D.Ring(64, hi)
ref = bytearray()
pkt = bytearray(80)
bad = 0
for i in range(3000):
    if _rnd.random() < 0.6:
        data = bytes(_rnd.randrange(256) for _ in range(_rnd.randrange(1, 90)))
        if _rnd.random() < 0.2:
            extra = bytes(_rnd.randrange(256) for _ in range(_rnd.randrange(1, 70)))
            hi.hook = lambda e=extra: (r.put(e), ref.extend(e))
        r.put(data)
        ref.extend(data)
        del ref[:max(0, len(ref) - 64)]
    else:
        k = _rnd.randrange(1, 80)
        off = _rnd.randrange(0, 4)
        if _rnd.random() < 0.2:
            extra = bytes(_rnd.randrange(256) for _ in range(_rnd.randrange(1, 70)))

            def _h(e=extra):
                r.put(e)
                ref.extend(e)
                del ref[:max(0, len(ref) - 64)]
            hi.hook = _h
        n = r.take_into(pkt, off, k)
        hi.hook = None
        want = bytes(ref[:n])
        del ref[:n]
        if bytes(pkt[off:off + n]) != want or len(want) != n:
            bad += 1
    if r.size != len(ref):
        bad += 1
check('ring take_into and put match reference, IRQ put in between', bad == 0 and hi.depth == 0)

# ---- start, tee, boot line --------------------------------------------------------------------------
clk = Clock()
fos = FakeOs()
d = D.DiagNet(network, socket_mod, clk, {'host': '192.0.2.11', 'port': 47210}, 'S', 'P',
              machine=Irq(), gc=gc_mod, os_mod=fos)
d.start()
check('boot id from urandom', d.boot == 'abcd1234')
check('dupterm slot 0', fos.dupterm_args is not None and fos.dupterm_args[1] == 0)
check('wlan active and join', WLAN.act is True and WLAN.joins == 1)
tee = fos.dupterm_args[0]
check('tee write returns len', tee.write(b'GUARD_TRIP pump reason=overpressure\n') == 36)
check('tee readinto none', tee.readinto(bytearray(4)) is None)
buf = d.ring.take(10000).decode()
check('boot line', 'DIAG_BOOT rc=3 fw=v1.28.0_on_2026-04-01 mac=28cdc1010203' in buf)
check('tee into ring', 'GUARD_TRIP pump reason=overpressure' in buf)


class Broken:
    def put(self, data):
        raise ValueError('x')


ring_saved, d.ring = d.ring, Broken()
try:
    n = tee.write(b'abc')
    check('tee never raises', n == 3)
except Exception:
    check('tee never raises', False)
d.line('x')
check('line never raises', True)
d.ring = ring_saved

# ---- step while disconnected ------------------------------------------------------------------------
d._t_hb = None
d.step(None)
check('hb queued while offline', b'DIAG_HB' in bytes(d.ring.buf) and not SOCK.sent)
clk.ms += 31000
d.step(None)
check('join retry after 30 s', WLAN.joins == 2)
d.shot_start()
clk.ms += 31000
d.step(None)
check('no join during shot', WLAN.joins == 2)
d.shot_end('spr_end', 3)
d.ring.take(100000)

# ---- connected: packets ----------------------------------------------------------------------------
WLAN.connected = True
payload = ''.join('EU_STALL sec=y task=ble:%05d\n' % i for i in range(120)).encode()   # ~3,6 kB
d.ring.put(payload)
d._t_hb = clk.ms
pk = []
for _ in range(4):
    d.step(None)
pk = [p for p, a in SOCK.sent]
check('nonblocking socket', SOCK.blocking is False)
check('addr literal', all(a == ('192.0.2.11', 47210) for p, a in SOCK.sent))
check('packet size', all(len(p) <= D.PKT_BYTES for p in pk))
heads = [p.split(b'\n', 1)[0].split() for p in pk]
check('header EXD1 boot seq', all(h[0] == b'EXD1' and h[1] == b'abcd1234' for h in heads)
      and [int(h[2]) for h in heads] == list(range(int(heads[0][2]), int(heads[0][2]) + len(pk))))
data = b''.join(p.split(b'\n', 1)[1] for p in pk)
check('payload reassembles', data == payload)
check('two packets per step', len(pk) == 3)
# LEGACY_SEND (ystall bit 4): the old path sends the same bytes
n0 = len(SOCK.sent)
d.ring.put(payload)
D.LEGACY_SEND = True
for _ in range(4):
    d.step(None)
D.LEGACY_SEND = False
pl = [p for p, a in SOCK.sent[n0:]]
check('legacy send same payload', b''.join(p.split(b'\n', 1)[1] for p in pl) == payload and len(pl) == 3)

# ---- send error ------------------------------------------------------------------------------------
SOCK.fail = True
d.ring.put(b'lost line\n')
drop0, err0 = d.ring.drop, d.txerr
try:
    d.step(None)
    check('send error does not raise', True)
except Exception:
    check('send error does not raise', False)
check('send error counted', d.txerr == err0 + 1 and d.ring.drop == drop0 + len(b'lost line\n'))
SOCK.fail = False

# ---- heartbeat ------------------------------------------------------------------------------------
SOCK.sent.clear()
bd = types.SimpleNamespace(pending_brew_log={'x': 1})
clk.s += 3600
d._t_hb = clk.ms
clk.ms += 60000
d.step(bd)
hb = b''.join(p for p, a in SOCK.sent)
check('hb fields', b'DIAG_HB up_s=3600 free=123456 alloc=98765' in hb and b'rssi=-61' in hb and b'pend=1' in hb
      and b'brew=0' in hb)
check('hb without collect/lmax -> -1', b'lmax_us=-1 l100=-1 gc_us=-1 live_kb=-1' in hb)
# idle HB: collection time, live heap and the 30 ms task lateness, reset after reading (EXPRESSO-GC-UUTTO)
gc_mod.collect = lambda: None
bd2 = types.SimpleNamespace(lmax=[123456, 2])
n0 = len(SOCK.sent)
d._t_hb = clk.ms
clk.ms += 60000
d.step(bd2)
hb2 = b''.join(p for p, a in SOCK.sent[n0:])
check('hb lmax, gc_us, live_kb', b'lmax_us=123456 l100=2 gc_us=' in hb2 and b'live_kb=96' in hb2 and bd2.lmax == [0, 0])
del gc_mod.collect
d.shot_start()
SOCK.sent.clear()
clk.ms += 5000
d.step(bd)
check('hb every 5 s in shot', b'DIAG_HB' in b''.join(p for p, a in SOCK.sent) and b'brew=1' in b''.join(p for p, a in SOCK.sent))
hb = b''.join(p for p, a in SOCK.sent)
check('shot hb skips heap walk (WIFI-AIKAIKKUNA)', b'free=-1 alloc=-1' in hb)
check('no wifi link -> w fields -1', b'wtx=-1 wtxerr=-1 wsmax_us=-1' in hb)
wl = types.SimpleNamespace(tx=42, txerr=1, send_max_us=777)
SOCK.sent.clear()
clk.ms += 5000
d.step(types.SimpleNamespace(pending_brew_log=None, wifi_link=wl))
hb = b''.join(p for p, a in SOCK.sent)
check('hb carries wifi link counters and resets max', b'wtx=42 wtxerr=1 wsmax_us=777' in hb and wl.send_max_us == 0)
d.shot_end('max', 0)
SOCK.sent.clear()
d.step(bd)
check('full hb right after the shot', b'free=123456' in b''.join(p for p, a in SOCK.sent))


class _Aio:
    def __init__(self, dd, stop_after):
        self.sleeps = []
        self.dd = dd
        self.stop_after = stop_after

    async def sleep_ms(self, ms):
        self.sleeps.append(ms)
        if len(self.sleeps) == self.stop_after:
            self.dd.brew = True
        if len(self.sleeps) > self.stop_after:
            raise StopIteration


busy = []
aio = _Aio(d, 1)
try:
    import asyncio as _real_asyncio
    _real_asyncio.run(d.run(bd, aio, lambda name, t0: busy.append(name)))
except (StopIteration, RuntimeError):
    pass
d.brew = False
check('sender period 100 ms idle, 500 ms in shot', aio.sleeps[:2] == [D.SEND_PERIOD_MS, D.SEND_PERIOD_BREW_MS])
check('sender reports task_busy diag', busy and set(busy) == {'diag'})
d.quiet = True
check('test shot (quiet, no log) counts as shot', d.in_shot() and not d.brew)
d.quiet = False
check('idle is not a shot', not d.in_shot())

# ---- DIAG_MIN: relay guard window + diagnet line ---------------------------------------------------
import relayguard as RG  # noqa: E402


class Pin:
    def __init__(self, v):
        self.v = v

    def value(self, *a):
        return self.v


g = RG.RelayGuard(types.SimpleNamespace(), clk)
g.relays = {'heater': types.SimpleNamespace(pin=Pin(1)), 'pump': types.SimpleNamespace(pin=Pin(0))}
for i, p in enumerate((0.5, 9.0, 2.5)):
    g.pressure = p
    g._accumulate(100, i == 1)
g.relays['heater'].pin.v = 0
g.pressure = 1.0
g._accumulate(100, False)
w = g.take_minute()
check('guard window sums', w[:4] == (400, 300, 100, 4) and abs(w[4] - 3.25) < 1e-9 and w[5] == 0.5 and w[6] == 9.0)
check('guard window resets', g.take_minute()[:4] == (0, 0, 0, 0) and g.take_minute()[4] is None)
g.bd = types.SimpleNamespace(pressure=1.0, boiler_temperature=95.0, get_target_temperature=lambda: 100.0, dev_safe=False)
g._accumulate = lambda dt, pump_on: 1 / 0
try:
    g.poll()
    g.poll()
    check('accumulate error cannot trip guard', g.block.get('all') != 'guarderror')
except Exception:
    check('accumulate error cannot trip guard', False)
# paused (ystall bit 8, EXPRESSO-GC-UUTTO): poll does nothing, and works again once resumed
calls = []
g.read_pressure = lambda: (calls.append(1), (2.0, 2.0))[1]
g.paused = True
g.poll()
paused_none = calls == []
g.paused = False
g.poll()
check('guard paused poll does nothing, resumed reads again', paused_none and calls == [1] and g.pressure == 2.0)
WLAN.connected = False
d.ring.take(100000)
bd2 = types.SimpleNamespace(relay_guard=types.SimpleNamespace(take_minute=lambda: (61000, 30500, 2000, 610, 1.234, -0.05, 9.5)),
                            boiler_temperature=99.5, get_target_temperature=lambda: 100.0)
d._t_min = None
d._t_hb = clk.ms
d.step(bd2)
clk.ms += 60000
d._t_hb = clk.ms
d.step(bd2)
txt = d.ring.take(100000).decode()
check('DIAG_MIN line', 'DIAG_MIN win_ms=61000 heat_ms=30500 pump_ms=2000 p_n=610 p_avg=1.23 p_min=-0.05 p_max=9.50 T=99.50 target=100.00' in txt)
check('DIAG_MIN once per minute', txt.count('DIAG_MIN') == 1)
WLAN.connected = True

# ---- flush -----------------------------------------------------------------------------------------
SOCK.sent.clear()
d.ring.put(b'Traceback (most recent call last):\nMemoryError: memory allocation failed\n')
d.flush()
check('flush sends traceback', b'MemoryError' in b''.join(p for p, a in SOCK.sent))
WLAN.connected = False
d.ring.put(b'x\n')
d.flush()
check('flush offline no raise', True)

# ---- brew_logger hook ------------------------------------------------------------------------------
import brew_logger as BL  # noqa: E402
SOCK.sent.clear()
WLAN.connected = True
d.ring.take(100000)
BL.SINK = d
log = BL.BrewSessionLogger(clk)
log.start(clk.ms, 10.0)
for i in range(200):
    clk.ms += 100
    log.tick(clk.ms, 93.2, 8.5, 2.1, 30.0, True, False, 1, 2, 'brew loop')
    d.step(None)            # the sender task drains the ring every 100 ms
log.end_session(clk.ms, 40.0)
txt = (b''.join(p.split(b'\n', 1)[1] for p, a in SOCK.sent) + d.ring.take(100000)).decode()
check('shot start line', 'DIAG_SHOT start' in txt)
check('sample lines 10 Hz', txt.count('DIAG_S t=') == 200 and 'DIAG_S t=100 T=932 p=850 f=210 w=200 r=1' in txt)
check('shot end once', txt.count('DIAG_SHOT end') == 1 and 'DIAG_SHOT end reason=spr_end n=200' in txt)
check('brew flag off after shot', d.brew is False)
log.start(clk.ms, 10.0)
clk.ms += 2000
log.tick(clk.ms, 93.0, 1.0, 0.0, 10.0, True, False)
log.end_session(clk.ms, 10.0)          # < 15 s: discarded
txt = d.ring.take(100000).decode()
check('discard ends shot once', txt.count('DIAG_SHOT end') == 1 and 'reason=spr_end n=1' in txt)
log.start(clk.ms, 10.0)
log.abandon()
txt = d.ring.take(100000).decode()
check('abandon while recording ends shot', 'DIAG_SHOT end reason=abandon' in txt and d.brew is False)
BL.SINK = None

# ---- module start(): disabled and enabled ---------------------------------------------------------
sys.modules['machine'] = Irq()
sys.modules['gc'] = gc_mod
sys.modules['os'] = fos
WLAN.act = None
x = D.start(network, socket_mod, clk, {'enabled': False, 'host': 'h', 'port': 1}, 'S', 'P')
check('disabled -> None and wifi off', x is None and WLAN.act is False)
x = D.start(network, socket_mod, clk, {'enabled': True, 'host': 'h', 'port': 1}, 'S', 'P')
check('enabled -> DiagNet', isinstance(x, D.DiagNet) and WLAN.act is True)
check('secrets ssid without diag_wifi', x.ssid == 'S')
sys.modules['diag_wifi'] = types.SimpleNamespace(ssid='IOT_SSID', password='pw')
x = D.start(network, socket_mod, clk, {'enabled': True, 'host': 'h', 'port': 1}, 'S', 'P')
check('diag_wifi overrides secrets', x.ssid == 'IOT_SSID' and x.password == 'pw')

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
