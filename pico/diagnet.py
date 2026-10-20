# ============================================================================
# DIAGNET — diagnostics over Wi-Fi to the palvelin collector (EXPRESSO-DIAGNET 20.10.2026)
# ============================================================================
# Spec: paketit/DIAGNET.md. The Pico's whole stdout (os.dupterm tee: GUARD_TRIP, *_END, EU_STALL,
# tracebacks) plus network-only DIAG_* lines go into a fixed ring and leave as UDP packets
#   EXD1 <boot> <seq> <up_ms> <drop>\n<data>
# to the collector, which writes them to files and publishes them to Home Assistant. Without this, a run
# leaves no trace when the Zero is not on the USB port: the Pico keeps no log.
# Rules, because the pump loops are timing-critical:
# - nothing here waits for the network: a non-blocking UDP socket to an IP literal (no DNS), a send error
#   is counted and the data dropped;
# - the ring is preallocated; a full ring overwrites the oldest bytes and counts them in drop;
# - no reconnect while a shot records (wlan.connect talks to the radio over SPI);
# - every method a task or print calls catches its own exceptions: an exception in an asyncio.gather task
#   ends all tasks (main.py), and one in the dupterm write detaches the tee.

import io

RING_BYTES = 8192
PKT_BYTES = 1400            # UDP payload, under the 1472 B Ethernet limit
MIN_MS = 60000              # DIAG_MIN: heater/pump on-time and pressure per minute (user 20.10.2026)
HB_IDLE_MS = 60000
HB_BREW_MS = 5000
JOIN_RETRY_MS = 30000
SEND_PERIOD_MS = 100
SEND_PKTS_PER_STEP = 2


def _f2(x):
    return '-' if x is None else '%.2f' % x


class Ring:
    """Byte ring: put() never fails, take() returns up to n of the oldest bytes. Both run with IRQs
    off, because the relay guard prints from a Timer callback that can land inside either."""
    def __init__(self, n, irq=None):
        self.buf = bytearray(n)
        self.n = n
        self.r = 0
        self.size = 0
        self.drop = 0
        self.irq = irq      # machine module or None (host tests)

    def put(self, data):
        mv = memoryview(data)
        ln = len(mv)
        if not ln:
            return
        st = self.irq.disable_irq() if self.irq else None
        try:
            n = self.n
            if ln > n:
                self.drop += ln - n
                mv = mv[ln - n:]
                ln = n
            over = ln - (n - self.size)
            if over > 0:
                self.r = (self.r + over) % n
                self.size -= over
                self.drop += over
            w = (self.r + self.size) % n
            first = ln if ln <= n - w else n - w
            self.buf[w:w + first] = mv[:first]
            if ln > first:
                self.buf[0:ln - first] = mv[first:]
            self.size += ln
        finally:
            if self.irq:
                self.irq.enable_irq(st)

    def take(self, k):
        st = self.irq.disable_irq() if self.irq else None
        try:
            if k > self.size:
                k = self.size
            r = self.r
            if r + k <= self.n:
                out = bytes(self.buf[r:r + k])
            else:
                out = bytes(self.buf[r:]) + bytes(self.buf[:k - (self.n - r)])
            self.r = (r + k) % self.n
            self.size -= k
            return out
        finally:
            if self.irq:
                self.irq.enable_irq(st)


class _Tee(io.IOBase):
    """os.dupterm stream: write() copies into the ring, input never comes from here. MicroPython gives a
    Python object the stream protocol only through io.IOBase."""
    def __init__(self, diag):
        self.diag = diag

    def write(self, data):
        d = self.diag
        try:
            t0 = d.utime.ticks_us()
            d.ring.put(data)
            dt = d.utime.ticks_diff(d.utime.ticks_us(), t0)
            if dt > d.tee_max_us:
                d.tee_max_us = dt
        except Exception:
            pass
        return len(data)

    def readinto(self, buf):
        return None

    def ioctl(self, req, arg):
        return 0


class DiagNet:
    def __init__(self, network, socket, utime, cfg, ssid, password, machine=None, gc=None, os_mod=None,
                 wlan=None, boot_id=None):
        self.network = network
        self.socket = socket
        self.utime = utime
        self.machine = machine
        self.gc = gc
        self.os = os_mod
        self.addr = (cfg['host'], cfg['port'])
        self.ssid = ssid
        self.password = password
        self.wlan = wlan if wlan is not None else network.WLAN(network.STA_IF)
        self.ring = Ring(RING_BYTES, machine)
        self.boot = boot_id if boot_id is not None else self._boot_id()
        # Uptime from the RTC seconds: ticks_ms wraps after 12.4 days, and long uptimes are the question
        self.t_boot_s = utime.time()
        self.sock = None
        self.seq = 0
        self.txp = 0
        self.txerr = 0
        self.errs = 0
        self.send_max_us = 0
        self.tee_max_us = 0
        self.rssi = 0
        self.brew = False
        self._t_join = None
        self._t_hb = None
        self._t_min = None
        self._tee = None

    def _boot_id(self):
        try:
            return '%08x' % int.from_bytes(self.os.urandom(4), 'big')
        except Exception:
            return '%08x' % (self.utime.ticks_us() & 0xFFFFFFFF)

    # ---- boot ---------------------------------------------------------------------------------------
    def start(self):
        """Tee stdout into the ring, raise the radio and queue DIAG_BOOT. Never raises."""
        try:
            self._tee = _Tee(self)
            self.os.dupterm(self._tee, 0)
        except Exception as e:
            self.line('DIAG_TEE_FAIL %r' % (e,))
        rc = mac = -1
        try:
            rc = self.machine.reset_cause()
        except Exception:
            pass
        try:
            self.wlan.active(True)
            mac = ''.join('%02x' % b for b in self.wlan.config('mac'))
        except Exception as e:
            self.line('DIAG_WLAN_FAIL %r' % (e,))
        try:
            fw = self.os.uname().version
        except Exception:
            fw = '?'
        self.line('DIAG_BOOT rc=%s fw=%s mac=%s' % (rc, fw.replace(' ', '_'), mac))
        self._join(self.utime.ticks_ms())

    def _join(self, now):
        self._t_join = now
        try:
            if not self.wlan.isconnected():
                self.wlan.connect(self.ssid, self.password)
        except Exception:
            self.errs += 1

    # ---- writers ------------------------------------------------------------------------------------
    def line(self, s):
        """A network-only line (not on the serial port, so it cannot fill the USB CDC buffer)."""
        try:
            self.ring.put((s + '\n').encode())
        except Exception:
            pass

    def shot_start(self):
        self.brew = True
        self._t_hb = None       # first brew heartbeat right away
        self.line('DIAG_SHOT start')

    def shot_end(self, reason, n):
        self.brew = False
        self.line('DIAG_SHOT end reason=%s n=%d' % (reason, n))

    def sample(self, row):
        """brew_logger row [t_ms, T_x10, P_x100, F_x100, hx_a, hx_b, W_x10, flags]."""
        self.line('DIAG_S t=%d T=%d p=%d f=%d w=%d r=%d' % (row[0], row[1], row[2], row[3], row[6], row[7]))

    def heartbeat(self, bd=None):
        free = alloc = -1
        try:
            free = self.gc.mem_free()
            alloc = self.gc.mem_alloc()
        except Exception:
            pass
        if not self.brew:
            try:
                self.rssi = self.wlan.status('rssi')
            except Exception:
                pass
        pend = 1 if bd is not None and getattr(bd, 'pending_brew_log', None) is not None else 0
        self.line('DIAG_HB up_s=%d free=%d alloc=%d drop=%d txp=%d txerr=%d smax_us=%d tmax_us=%d rssi=%d '
                  'brew=%d pend=%d err=%d' % (
                      self.utime.time() - self.t_boot_s, free, alloc, self.ring.drop, self.txp, self.txerr,
                      self.send_max_us, self.tee_max_us, self.rssi, 1 if self.brew else 0, pend, self.errs))
        self.send_max_us = 0
        self.tee_max_us = 0

    def minute(self, bd):
        """DIAG_MIN from the relay guard's window. win_ms is the real window: a busy loop that delays this
        task makes the window longer, not the numbers wrong."""
        g = getattr(bd, 'relay_guard', None) if bd is not None else None
        if g is None:
            return
        win, heat, pump, n, avg, mn, mx = g.take_minute()
        t = getattr(bd, 'boiler_temperature', None)
        try:
            target = bd.get_target_temperature()
        except Exception:
            target = None
        self.line('DIAG_MIN win_ms=%d heat_ms=%d pump_ms=%d p_n=%d p_avg=%s p_min=%s p_max=%s T=%s target=%s' % (
            win, heat, pump, n, _f2(avg), _f2(mn), _f2(mx), _f2(t), _f2(target)))

    # ---- sender -------------------------------------------------------------------------------------
    def _send_one(self):
        if not self.ring.size:
            return False
        if self.sock is None:
            s = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_DGRAM)
            s.setblocking(False)
            self.sock = s
        head = ('EXD1 %s %d %d %d\n' % (self.boot, self.seq, self.utime.ticks_ms(), self.ring.drop)).encode()
        data = self.ring.take(PKT_BYTES - len(head))
        self.seq += 1
        t0 = self.utime.ticks_us()
        try:
            self.sock.sendto(head + data, self.addr)
            self.txp += 1
        except OSError:
            # Not connected, no ARP entry yet, lwIP out of buffers: the data is gone, the loop goes on
            self.txerr += 1
            self.ring.drop += len(data)
        dt = self.utime.ticks_diff(self.utime.ticks_us(), t0)
        if dt > self.send_max_us:
            self.send_max_us = dt
        return True

    def step(self, bd=None):
        """One sender pass. Never raises."""
        try:
            now = self.utime.ticks_ms()
            if self._t_hb is None or self.utime.ticks_diff(now, self._t_hb) >= (HB_BREW_MS if self.brew else HB_IDLE_MS):
                self._t_hb = now
                self.heartbeat(bd)
            if self._t_min is None:
                self._t_min = now
                if bd is not None and getattr(bd, 'relay_guard', None) is not None:
                    bd.relay_guard.take_minute()     # drop the partial window from boot
            elif self.utime.ticks_diff(now, self._t_min) >= MIN_MS:
                self._t_min = now
                self.minute(bd)
            if not self.wlan.isconnected():
                if not self.brew and (self._t_join is None or
                                      self.utime.ticks_diff(now, self._t_join) >= JOIN_RETRY_MS):
                    self._join(now)
                return
            for _ in range(SEND_PKTS_PER_STEP):
                if not self._send_one():
                    break
        except Exception:
            self.errs += 1

    async def run(self, bd, asyncio):
        while True:
            self.step(bd)
            await asyncio.sleep_ms(SEND_PERIOD_MS)

    def flush(self, max_pkts=8):
        """Crash path (main.py): send what the ring holds now, without the task loop. Never raises."""
        try:
            if not self.wlan.isconnected():
                return
            for _ in range(max_pkts):
                if not self._send_one():
                    break
        except Exception:
            pass


def start(network, socket, utime, cfg, ssid, password):
    """main.py entry: a started DiagNet, or None with Wi-Fi off (cfg enabled False, or the start failed)."""
    import machine, gc, os
    # diag_wifi.py on the Pico only (not in the repo or the manifest): the IoT network's credentials,
    # written from the router's config. secrets.py named a network that no longer exists (20.10.2026).
    try:
        import diag_wifi
        ssid, password = diag_wifi.ssid, diag_wifi.password
    except ImportError:
        pass
    if cfg.get('enabled'):
        try:
            d = DiagNet(network, socket, utime, cfg, ssid, password, machine=machine, gc=gc, os_mod=os)
            d.start()
            return d
        except Exception as e:
            print('DIAG_START_FAIL %r' % (e,))
    try:
        network.WLAN(network.STA_IF).active(False)
    except Exception:
        pass
    return None
