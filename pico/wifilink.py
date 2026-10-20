# ============================================================================
# WIFI LINK — the app straight to the Pico over UDP (EXPRESSO-WIFI-APPI vaihe 1, 20.10.2026)
# ============================================================================
# Plan: paketit/WIFI-APPI.md luku 4 (user 20.10.2026: "äpin yhteys suoraan iphone", logs stay on DIAGNET -> HA).
# App -> Pico, one ASCII datagram to port 47211:
#   EXA1 hello                              -> {"type":"hello","boot":<id>,"name":"EspressoPico","v":1}
#   EXA1 <boot> <seq> <mac16> <command>     -> {"type":"ack","seq":n,"r":"ok|updated|unknown|denied|stale"}
#   mac16 = first 16 hex of HMAC-SHA256(key, "<boot> <seq> <command>"); boot = this boot's DIAGNET id, so a
#   restart voids old commands; seq grows per sender, a repeat gets the same ack again without running twice.
# Pico -> app: the BLE notify objects themselves (live, scale, pcal/cal state, settings A+B, brew-log
# multipack frames), one JSON object per datagram, to every sender that sent `sub` in the last SUB_MS.
# The commands are exactly the app's (ALLOWED); dev commands (tshot, phold, dev:*) stay serial-only, and the
# key travels only over BLE (`wifi:key?`, bluetooth_handler.py), so Wi-Fi allows nothing BLE does not.
# Same rules as DIAGNET: non-blocking socket, every error counted and swallowed, nothing here may raise
# into asyncio.gather.

PORT = 47211
SUB_MS = 15000
MAX_SUBS = 2
LIVE_MS = 200               # 5 Hz, as BLE
SETTINGS_MS = 2000
BLOG_FRAME_MS = 100
RX_PER_STEP = 4
STEP_MS = 50
# EXPRESSO-WIFI-AIKAIKKUNA (20.10.2026): during a shot (diag.brew) the task wakes at 100 ms, which still
# keeps live at 5 Hz, and the settings packets stay home; with no subscriber it only listens for hello/sub.
STEP_BREW_MS = 100
STEP_IDLE_MS = 500
KEY_FILE = 'link_key.txt'
DENY_LOG_MS = 10000

ALLOWED_EXACT = ('sync', 'get:settings', 'settings?', 'brew_log?', 'brew_log:get', 'tare', 'sub')
ALLOWED_PREFIX = ('brew_log:ack', 'stby:', 'stbt:', 'pit:', 'srt:', 'bt:', 'pip:', 'bp:', 'fhu:', 'pcal:', 'cal:')
_SYNC = ('sync', 'get:settings', 'settings?')


def allowed(cmd):
    if cmd in ALLOWED_EXACT:
        return True
    for p in ALLOWED_PREFIX:
        if cmd.startswith(p):
            return True
    return False


def hmac16(hashlib, key, msg):
    """HMAC-SHA256 (RFC 2104) by hand: MicroPython has hashlib.sha256 but no hmac module."""
    if len(key) > 64:
        key = hashlib.sha256(key).digest()
    key = key + bytes(64 - len(key))
    inner = hashlib.sha256(bytes(b ^ 0x36 for b in key) + msg).digest()
    d = hashlib.sha256(bytes(b ^ 0x5c for b in key) + inner).digest()
    return ''.join('%02x' % b for b in d[:8])


def load_key(os_mod, path=KEY_FILE):
    """32-byte key from the Pico's flash, made on first use. Not in the repo or the manifest."""
    try:
        with open(path) as f:
            h = f.read().strip()
        if len(h) == 64:
            return bytes(int(h[i:i + 2], 16) for i in range(0, 64, 2))
    except OSError:
        pass
    k = os_mod.urandom(32)
    with open(path, 'w') as f:
        f.write(''.join('%02x' % b for b in k))
    return k


class WifiLink:
    def __init__(self, brew_data, diag, socket, utime, hashlib, json, handle_command, payloads, key):
        self.bd = brew_data
        self.diag = diag                    # DiagNet: wlan, boot id
        self.socket = socket
        self.utime = utime
        self.hashlib = hashlib
        self.json = json
        self.handle_command = handle_command
        self.p = payloads                   # bluetooth_handler: live/scale/settings payloads, brew_log_frame
        self.key = key
        self.sock = None
        self.subs = {}                      # addr -> ticks_ms of the last sub
        self.last_seq = {}                  # addr -> (seq, ack dict)
        self.rx = self.tx = self.txerr = self.denied = self.errs = 0
        self.send_max_us = 0                # longest sendto since the last DIAG_HB (diagnet reads and resets it)
        self._t_live = None
        self._t_set = None
        self._t_blog = None
        self._t_deny_log = None
        self._blog_step = None
        self._blog_id = None
        self._blog_done_id = None

    # ---- BLE side ---------------------------------------------------------------------------------
    def key_packet(self):
        ip = '?'
        try:
            ip = self.diag.wlan.ifconfig()[0]
        except Exception:
            pass
        return {'type': 'wifi_key', 'key': ''.join('%02x' % b for b in self.key), 'host': ip, 'port': PORT}

    # ---- io ---------------------------------------------------------------------------------------
    def _open(self):
        s = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_DGRAM)
        s.setblocking(False)
        s.bind(('0.0.0.0', PORT))
        self.sock = s

    def _send(self, obj, addr):
        try:
            self.sock.sendto(self.json.dumps(obj).encode(), addr)
            self.tx += 1
        except OSError:
            self.txerr += 1

    def _send_subs(self, obj):
        if not self.subs:
            return
        try:
            raw = self.json.dumps(obj).encode()
        except Exception:
            self.errs += 1
            return
        for addr in self.subs:
            t0 = self.utime.ticks_us()
            try:
                self.sock.sendto(raw, addr)
                self.tx += 1
            except OSError:
                self.txerr += 1
            dt = self.utime.ticks_diff(self.utime.ticks_us(), t0)
            if dt > self.send_max_us:
                self.send_max_us = dt

    # ---- receive ----------------------------------------------------------------------------------
    def _deny(self, addr, why, seq=None):
        self.denied += 1
        now = self.utime.ticks_ms()
        if self._t_deny_log is None or self.utime.ticks_diff(now, self._t_deny_log) >= DENY_LOG_MS:
            self._t_deny_log = now
            print('WIFI_DENY %s from %s (n=%d)' % (why, addr[0], self.denied))
        if seq is not None:
            self._send({'type': 'ack', 'seq': seq, 'r': why}, addr)

    def _packet(self, data, addr, now):
        try:
            text = data.decode()
        except Exception:
            self._deny(addr, 'bytes')
            return
        parts = text.strip().split(' ', 4)
        if parts[0] != 'EXA1':
            self._deny(addr, 'proto')
            return
        if len(parts) == 2 and parts[1] == 'hello':
            self._send({'type': 'hello', 'boot': self.diag.boot, 'name': 'EspressoPico', 'v': 1}, addr)
            return
        if len(parts) != 5:
            self._deny(addr, 'format')
            return
        boot, seq_s, mac, cmd = parts[1], parts[2], parts[3], parts[4]
        try:
            seq = int(seq_s)
        except ValueError:
            self._deny(addr, 'format')
            return
        if mac != hmac16(self.hashlib, self.key, ('%s %s %s' % (boot, seq_s, cmd)).encode()):
            self._deny(addr, 'auth')        # no ack: an unauthenticated sender learns nothing
            return
        if boot != self.diag.boot:
            self._deny(addr, 'stale', seq)
            return
        last = self.last_seq.get(addr)
        if last is not None and seq <= last[0]:
            if seq == last[0]:
                self._send(last[1], addr)   # the ack was lost: same answer, no second run
            return
        if not allowed(cmd):
            self._deny(addr, 'denied', seq)
            return
        r = self._run(cmd, addr, now)
        ack = {'type': 'ack', 'seq': seq, 'r': r}
        if addr not in self.last_seq and len(self.last_seq) >= 8:
            self.last_seq.clear()           # every app restart is a new source port: keep this bounded
        self.last_seq[addr] = (seq, ack)
        self._send(ack, addr)

    def _run(self, cmd, addr, now):
        if cmd == 'sub':
            new = addr not in self.subs
            if new and len(self.subs) >= MAX_SUBS:
                del self.subs[max(self.subs, key=lambda a: self.utime.ticks_diff(now, self.subs[a]))]
            self.subs[addr] = now
            if new:
                self._t_set = None          # settings to the new subscriber right away
                print('WIFI sub %s' % addr[0])
            return 'ok'
        if cmd in ('brew_log?', 'brew_log:get'):
            # Wi-Fi's own multipack: handle_command would also start BLE's and pause BLE's live packets
            self._blog_step = 0 if self.bd.pending_brew_log is not None else None
            return 'ok'
        print('WIFI cmd %s' % cmd)
        updated = self.handle_command(self.bd, cmd)
        if updated or cmd in _SYNC:
            self._t_set = None
        if not getattr(self.bd, 'command_known', True):
            return 'unknown'
        return 'updated' if updated else 'ok'

    # ---- send -------------------------------------------------------------------------------------
    def _due(self, t, now, period):
        return t is None or self.utime.ticks_diff(now, t) >= period

    def _stream(self, now):
        for a in [a for a in self.subs if self.utime.ticks_diff(now, self.subs[a]) >= SUB_MS]:
            del self.subs[a]
            print('WIFI unsub %s' % a[0])
        if not self.subs:
            return
        bd = self.bd
        if self._due(self._t_live, now, LIVE_MS):
            self._t_live = now
            # Weight rides in the live packet: UDP has no 240 B notify limit, and the app reads each key on
            # its own (machine_data_notifier.dart), so one json.dumps and one sendto instead of two
            live = self.p.live_payload(bd)
            sp = self.p.scale_payload(bd)
            if sp is not None:
                live.update(sp)
            self._send_subs(live)
            if getattr(bd, 'pcal_state', 'idle') != 'idle':
                self._send_subs(bd.get_pressure_calibration_status())
            sc = getattr(bd, 'scale_cal', None)
            if sc is not None and sc.active():
                self._send_subs(sc.status())
        if not self.diag.in_shot() and self._due(self._t_set, now, SETTINGS_MS):
            self._t_set = now
            for packet in self.p.settings_payloads(bd):
                self._send_subs(packet)
        self._brew_log(now)

    def _brew_log(self, now):
        log = self.bd.pending_brew_log
        if log is None:
            self._blog_step = None
            return
        if self._blog_step is None and log['id'] != self._blog_done_id:
            self._blog_step = 0                 # a new shot's log goes out without asking, as on BLE
        if self._blog_step is None or not self._due(self._t_blog, now, BLOG_FRAME_MS):
            return
        if self._blog_id != log['id']:
            self._blog_id = log['id']
            if self._blog_step:
                self._blog_step = 0
        self._t_blog = now
        step = self._blog_step
        self._send_subs(self.p.brew_log_frame(log, step))
        if step + 1 >= self.p.brew_log_steps(log):
            self._blog_step = None
            self._blog_done_id = log['id']
            print('WIFI brew_log sent id=%s' % log['id'])
        else:
            self._blog_step = step + 1

    def step(self):
        """One pass. Never raises."""
        try:
            if not self.diag.wlan.isconnected():
                return
            if self.sock is None:
                self._open()
            now = self.utime.ticks_ms()
            for _ in range(RX_PER_STEP):
                try:
                    data, addr = self.sock.recvfrom(512)
                except OSError:
                    break                       # EAGAIN: nothing waiting
                self.rx += 1
                self._packet(data, addr, now)
            self._stream(now)
        except Exception as e:
            self.errs += 1
            try:
                print('WIFI_ERR %r' % (e,))
            except Exception:
                pass

    async def run(self, asyncio, task_busy=None):
        while True:
            t0 = self.utime.ticks_us()
            self.step()
            if task_busy is not None:
                task_busy('wifi', t0)
            await asyncio.sleep_ms(self.step_ms())

    def step_ms(self):
        if not self.subs:
            return STEP_IDLE_MS
        return STEP_BREW_MS if self.diag.in_shot() else STEP_MS
