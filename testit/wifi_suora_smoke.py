#!/usr/bin/env python3
"""wifi_suora_smoke.py — äpin suora Wi-Fi-kanava Picolle (EXPRESSO-WIFI-APPI vaihe 1, paketit/WIFI-APPI.md luku 4).

Ajaa `pico/wifilink.py`:n CPythonilla: HMAC (vs. Pythonin hmac), väärä avain ja vanha boot, toisto ja vanha seq,
kielletyt komennot (tshot, dev, wifi:key?), tilaus ja vanhentuminen, live/vaaka/asetukset tilaajille, `updated`
→ asetukset heti, uuttolokin kehykset täsmälleen BLE:n `brew_log_frame`illa eikä BLE:n multipackin liputusta,
kaksi tilaajaa, avaintiedosto ja ettei mikään nosta poikkeusta.

    python3 testit/wifi_suora_smoke.py        RESULT: <n> failed, epänolla paluuarvo jos punaisia
"""

import hashlib
import hmac
import json
import os
import sys
import tempfile
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico'))
bluetooth = types.ModuleType('bluetooth')
bluetooth.UUID = lambda x: x
bluetooth.FLAG_READ = 1; bluetooth.FLAG_NOTIFY = 2; bluetooth.FLAG_WRITE = 4
sys.modules['bluetooth'] = bluetooth
mp = types.ModuleType('micropython'); mp.const = lambda x: x
sys.modules['micropython'] = mp
import bluetooth_handler as BH  # noqa: E402
import wifilink as W  # noqa: E402

FAILED = []


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + ('' if ok else '  ' + str(info)))
    if not ok:
        FAILED.append(name)


class Clock:
    def __init__(self):
        self.ms = 1000

    def ticks_ms(self):
        return self.ms

    def ticks_us(self):
        return self.ms * 1000

    def ticks_diff(self, a, b):
        return a - b


class Sock:
    def __init__(self):
        self.inbox = []
        self.out = []
        self.bound = None
        self.blocking = None

    def setblocking(self, v):
        self.blocking = v

    def bind(self, addr):
        self.bound = addr

    def recvfrom(self, n):
        if not self.inbox:
            raise OSError(11)
        return self.inbox.pop(0)

    def sendto(self, data, addr):
        assert isinstance(data, bytes)
        self.out.append((json.loads(data), addr))

    def take(self, addr=None):
        o = [d for d, a in self.out if addr is None or a == addr]
        self.out = [] if addr is None else [(d, a) for d, a in self.out if a != addr]
        return o


SOCK = Sock()
socket_mod = types.SimpleNamespace(AF_INET=2, SOCK_DGRAM=2, socket=lambda a, b: SOCK)
wlan = types.SimpleNamespace(up=True, isconnected=lambda: wlan.up, ifconfig=lambda: ('192.0.2.13', '', '', ''))
diag = types.SimpleNamespace(boot='abcd1234', wlan=wlan)
clk = Clock()


class BD:
    def __init__(self):
        self.boiler_temperature = 99.5
        self.pressure = 0.1
        self.mode = 'IDLE'
        self.standby = False
        self.weight = 731.9
        self.flow = None
        self.tray_scale = object()
        self.tare_abs_g = 700.0
        self.pcal_state = 'idle'
        self.scale_cal = None
        self.pending_brew_log = None
        self.brew_log_send_requested = False
        self.brew_log_tx_reset = False
        self.command_known = True
        self.bt = 93.0

    def get_weight(self): return self.weight
    def get_flow(self): return self.flow
    def get_mode(self): return self.mode
    def get_brew_temperature(self): return self.bt
    def get_pre_infusion_mode(self): return True
    def get_pressure_soft_release_mode(self): return True
    def get_fast_heatup_mode(self): return False
    def get_pump_ratio(self): return 0.0
    def get_brew_pressure(self): return 9.0
    def get_pre_infusion_pressure(self): return 2.5
    def get_pre_infusion_time(self): return 5
    def get_pressure_soft_release_time(self): return 4


bd = BD()
RUN = []


def handle_command(b, cmd):
    RUN.append(cmd)
    b.command_known = not cmd.startswith('zz')
    if cmd.startswith('bt:'):
        b.bt = float(cmd[3:])
        return True
    if cmd.startswith('brew_log:ack'):
        b.pending_brew_log = None
    return False


KEY = bytes(range(32))
L = W.WifiLink(bd, diag, socket_mod, clk, hashlib, json, handle_command, BH, KEY)
APP = ('192.0.2.15', 50001)
APP2 = ('192.0.2.30', 50002)
APP3 = ('192.0.2.16', 50003)


def mac(boot, seq, cmd, key=KEY):
    return hmac.new(key, ('%s %s %s' % (boot, seq, cmd)).encode(), hashlib.sha256).hexdigest()[:16]


def send(cmd, seq, addr=APP, boot='abcd1234', key=KEY, step=True):
    SOCK.inbox.append((('EXA1 %s %d %s %s' % (boot, seq, mac(boot, seq, cmd, key), cmd)).encode(), addr))
    if step:
        L.step()


def acks(addr=APP):
    return [d for d in SOCK.take(addr) if d.get('type') == 'ack']


check('hmac16 = Python hmac', W.hmac16(hashlib, KEY, b'abc 1 sync') == hmac.new(KEY, b'abc 1 sync', hashlib.sha256).hexdigest()[:16])

# ---- hello and socket ------------------------------------------------------------------------------
SOCK.inbox.append((b'EXA1 hello', APP))
L.step()
o = SOCK.take()
check('socket bound 47211 nonblocking', SOCK.bound == ('0.0.0.0', 47211) and SOCK.blocking is False)
check('hello -> boot id', o == [{'type': 'hello', 'boot': 'abcd1234', 'name': 'EspressoPico', 'v': 1}], o)

# ---- auth ------------------------------------------------------------------------------------------
send('sync', 1)
a = acks()
check('signed sync -> ack ok, executed', a == [{'type': 'ack', 'seq': 1, 'r': 'ok'}] and RUN == ['sync'], (a, RUN))
send('sync', 2, key=bytes(32))
check('wrong key -> no ack, not run', acks() == [] and RUN == ['sync'] and L.denied == 1)
send('sync', 3, boot='00000000')
check('old boot -> stale, not run', acks() == [{'type': 'ack', 'seq': 3, 'r': 'stale'}] and RUN == ['sync'])
SOCK.inbox.append((b'\xff\xfe junk', APP)); SOCK.inbox.append((b'HELLO', APP)); SOCK.inbox.append((b'EXA1 a b', APP))
L.step()
check('garbage counted, no reply, no raise', SOCK.take() == [] and L.denied == 5)

# ---- replay ----------------------------------------------------------------------------------------
send('bt:94', 5)
first = acks()
send('bt:94', 5)
again = acks()
send('bt:95', 4)
check('updated ack', first == [{'type': 'ack', 'seq': 5, 'r': 'updated'}], first)
check('repeat seq -> same ack, not run twice', again == first and RUN.count('bt:94') == 1)
check('lower seq ignored', acks() == [] and 'bt:95' not in RUN)

# ---- not allowed -----------------------------------------------------------------------------------
for i, c in enumerate(('tshot:30', 'dev:safe', 'wifi:key?', 'phold:5', 'pre:on')):
    send(c, 10 + i)
check('dev, key and non-app commands denied, not run',
      all(x['r'] == 'denied' for x in acks()) and not any(c in RUN for c in ('tshot:30', 'dev:safe', 'wifi:key?')))
send('zzz', 20)
check('non-app command -> denied', acks() == [{'type': 'ack', 'seq': 20, 'r': 'denied'}] and 'zzz' not in RUN)
for i, c in enumerate(('stby:30', 'stbt:90', 'pit:5', 'srt:4', 'pip:2.5', 'bp:9', 'fhu:on', 'pcal:end', 'tare',
                       'cal:cancel', 'brew_log:ack:3', 'get:settings', 'settings?')):
    send(c, 30 + i)
ok_all = acks()
check('every app command allowed', len(ok_all) == 13 and all(x['r'] in ('ok', 'updated') for x in ok_all), ok_all)

# ---- subscribe and stream --------------------------------------------------------------------------
SOCK.take()
send('sub', 50)
got = SOCK.take(APP)
kinds = [('ack' if d.get('type') == 'ack' else 'live' if 'boiler_temperature' in d else 'scale' if 'weight_g' in d
          else 'setB' if 'brew_pressure' in d else 'setA' if 'fast_heatup_mode' in d else '?') for d in got]
check('sub -> ack, live, scale, settings A+B at once', kinds == ['ack', 'live', 'scale', 'setA', 'setB'], kinds)
scale = [d for d in got if 'weight_g' in d][0]
check('scale packet = BLE scale_payload', scale == BH.scale_payload(bd), scale)
live = [d for d in got if 'boiler_temperature' in d][0]
check('live packet = BLE live_payload', live == json.loads(json.dumps(BH.live_payload(bd))))
n_live = 0
for _ in range(20):         # 1 s in 50 ms steps
    clk.ms += 50
    L.step()
    n_live += sum(1 for d in SOCK.take(APP) if 'boiler_temperature' in d)
check('live 5 Hz', n_live == 5, n_live)
send('bt:96', 51)
got = SOCK.take(APP)
check('updated -> settings at once', any(d.get('brew_temperature') == 96.0 and 'brew_pressure' in d for d in got), got)
clk.ms += W.SUB_MS
L.step()
SOCK.take()
clk.ms += 400
L.step()
check('sub expires after 15 s', SOCK.take() == [] and APP not in L.subs)

# ---- two subscribers, third evicts the oldest ----------------------------------------------------------
send('sub', 60)
clk.ms += 100
send('sub', 1, addr=APP2)
clk.ms += 100
send('sub', 1, addr=APP3)
check('max 2 subscribers, oldest dropped', set(L.subs) == {APP2, APP3}, L.subs)
SOCK.take()

# ---- brew log --------------------------------------------------------------------------------------
L.subs = {APP: clk.ms}
rows = [[i * 100, 930, 850, 210, 2255847, 975977, i, 1] for i in range(530)]
events = [['phase_%d' % i, i * 1000] for i in range(40)]
bd.pending_brew_log = {'type': 'brew_log', 'v': 3, 'id': 7, 'sample_hz': 10, 'duration_ms': 52900, 'n_samples': 530,
                       'n_events': 40, 'truncated': False, 'scale_at_end_g': 40.69, 'samples': rows, 'events': events,
                       'scale_meta': {'scale': 2175.04, 'trim_b': 1.0525, 'sense': 1, 'off_a': 669878.0, 'off_b': 58314.0}}
frames = []
sizes = []
for _ in range(200):
    clk.ms += 50
    L.subs[APP] = clk.ms
    L.step()
    for d, a in SOCK.out:
        if d.get('type') == 'brew_log':
            frames.append(d)
            sizes.append(len(json.dumps(d)))
    SOCK.out = []
expect = [json.loads(json.dumps(BH.brew_log_frame(bd.pending_brew_log, s))) for s in range(BH.brew_log_steps(bd.pending_brew_log))]
check('new log goes out unasked, frames = BLE brew_log_frame', frames == expect, (len(frames), len(expect)))
check('frames fit a datagram (<= 1472 B)', max(sizes) <= 1472, max(sizes))
check('BLE multipack flags untouched', bd.brew_log_send_requested is False and bd.brew_log_tx_reset is False)
check('sent once', len(frames) == len(expect))
send('brew_log?', 70)
got = []
for _ in range(60):
    clk.ms += 50
    L.subs[APP] = clk.ms
    L.step()
    got += [d for d, a in SOCK.out if d.get('type') == 'brew_log']
    SOCK.out = []
check('brew_log? resends from meta', got and got[0]['part'] == 'meta' and len(got) == len(expect),
      (len(got), got and got[0].get('part')))
check('brew_log? not passed to handle_command', 'brew_log?' not in RUN)
send('brew_log:ack:7', 71)
check('ack via handle_command frees the log', bd.pending_brew_log is None)

# ---- robustness ------------------------------------------------------------------------------------
SOCK.take()
wlan.up = False
SOCK.inbox.append((b'EXA1 hello', APP))
L.step()
check('offline: nothing read or sent', len(SOCK.inbox) == 1 and SOCK.take() == [])
wlan.up = True
SOCK.inbox = []
L.p = None                   # payload module broken
L.subs = {APP: clk.ms}
clk.ms += 300
try:
    L.step()
    check('internal error never raises', L.errs >= 1)
except Exception as e:
    check('internal error never raises', False, e)
L.p = BH
for i in range(20):
    send('sync', 1, addr=('192.0.2.15', 40000 + i))
check('seq table bounded', len(L.last_seq) <= 8, len(L.last_seq))

# ---- key -------------------------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'k.txt')
    k1 = W.load_key(types.SimpleNamespace(urandom=os.urandom), p)
    k2 = W.load_key(types.SimpleNamespace(urandom=lambda n: b'x' * n), p)
    check('key made once, reloaded', len(k1) == 32 and k1 == k2 and len(open(p).read().strip()) == 64)
kp = L.key_packet()
check('key packet', kp == {'type': 'wifi_key', 'key': KEY.hex(), 'host': '192.0.2.13', 'port': 47211}, kp)

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
