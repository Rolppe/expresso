#!/usr/bin/env python3
"""eXpresso Pico development tool (Mac) — runs without anyone at the machine.

Talks to the Pico through the phone app's USB serial bridge: adb forward tcp:2217 → OnePlus
(192.0.2.11:5555) → PicoBridgeService → USB-CDC → Pico. Every REPL operation starts with
devsafe: Ctrl-C (firmware's finally drives relays off), then devsafe.enter() reads the relay pins
back and must report [0, 0, 0] before anything else runs. The 8 s hardware watchdog is fed
throughout; a tool that dies leaves a Pico that resets itself.

Usage:
  pico_dev.py safe                      relays off + read-back, then machine.reset()
  pico_dev.py cmd <command> [seconds]   send "CMD <command>" to the running firmware (no interrupt)
                                        and print serial output for <seconds> (default 3)
  pico_dev.py shot <seconds> [out.log]  CMD tshot:<seconds>, capture PI/TS lines until TS_END
  pico_dev.py pcap <ms>[:<bar>[:<phase_us>]] [out.log]  CMD pcap:<ms>[:<bar>[:<phase_us>]], capture
                                        PCAP lines until PCAP_END
  pico_dev.py psweep <ms>:<bar>[:<n>[:<mult>]] [out.log]  CMD psweep:<ms>:<bar>[:<n>[:<mult>]],
                                        capture PSWEEP/PCAP lines until PSWEEP_END
  pico_dev.py plen <bar>[:<reps>] [out.log]  CMD plen:..., capture PLEN lines until PLEN_END:
                                        gap-length sweep, tests for half-cycle quantisation
  pico_dev.py pgap <bar>[:<n>[:<spacing_ms>]] [out.log]  CMD pgap:..., capture PGAP lines until
                                        PGAP_END: several 20 ms gaps, alignment searched in-run
  pico_dev.py pstep <bar>[:<hold_ms>[:<tail_ms>]] [out.log]  CMD pstep:..., capture PSTEP lines
                                        until PSTEP_END: one skipped mains cycle at target pressure
  pico_dev.py phold <s> [out.log]       CMD phold:<s>, capture PHOLD lines until PHOLD_END
  pico_dev.py vkello <bar> [out.log]    CMD vkello:<bar> (0 = rise ends at plateau only), capture VKELLO lines until VKELLO_END
  pico_dev.py vsweep <reps> [out.log]   CMD vsweep:<reps 1-5>: vent, rise to plateau, lock the mains clock, then
                                        single 10 ms gaps at 0..19 ms from the clock edge + sham + 20 ms,
                                        reps times; VSWEEP/VKELLO lines until VSWEEP_END
  pico_dev.py klamp <s> [out.log]       CMD klamp:<s 10-120>: throttle warm-up — continuous pump to the
                                        plateau, hold that pressure until the pump is unlimited
                                        (duty_avg >= 0.95 for 3 s); KLAMP lines until KLAMP_END
  pico_dev.py capture <seconds> [out]   print/save serial output (no interrupt)
  pico_dev.py verify <MANIFEST.json>    SHA-256 of every file on the Pico vs. the manifest
  pico_dev.py watchdog-test             Ctrl-C and stop feeding: the Pico must reset itself (≤ 8 s)
  pico_dev.py restore <set>             flash a set from the phone backup, wait for RESTORE_OK/FAIL
  pico_dev.py charger on|off            switch the hub's charger (Shelly via Home Assistant)

Every operation except `charger` runs with the charger off and powers it again when done
(CHARGER_CYCLE, temporary until the Type-C fault is fixed; PICO_CHARGER_CYCLE=0 disables).

Source of truth: /srv/work/Infra/iot/expresso/pico_dev.py (copied to the Mac legacy folder).
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time

# Mac: /opt/homebrew/bin/adb; palvelin: ~/.local/share/platform-tools/adb (PICO_ADB overrides)
# palvelin: /usr/bin/adb from PATH when neither exists
ADB = os.environ.get('PICO_ADB') or next(
    (a for a in ('/opt/homebrew/bin/adb', os.path.expanduser('~/.local/share/platform-tools/adb'))
     if os.path.exists(a)), None) or shutil.which('adb') or 'adb'
PHONE = '192.0.2.11:5555'
PORT = 2217
APP = 'com.example.silvia_pico_ui'

# TEMPORARY (user 23.9.2026): with the hub's PD charger powered the phone drops the USB2 hub and the
# Pico, so every USB operation cuts the charger through the Shelly first and powers it again when
# done. Turn off (False, or PICO_CHARGER_CYCLE=0) once the Type-C fault is found and fixed
# (PICO-HALLINTA.md luku 8).
CHARGER_CYCLE = os.environ.get('PICO_CHARGER_CYCLE', '1') != '0'
CHARGER_ENTITY = 'switch.shellyplus1pm_example'
HA_SH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ha', 'ha.sh')
PICO_VID = '2e8a'


def adb(*args, check=True):
    # errors='replace': logcat carries non-UTF-8 bytes, and a decode crash mid-restore turned the
    # charger back on while the flasher was still writing (23.9.2026)
    return subprocess.run([ADB, '-s', PHONE] + list(args), capture_output=True, text=True,
                          errors='replace', check=check)


def charger(on):
    r = subprocess.run([HA_SH, 'palvelu', 'switch.turn_on' if on else 'switch.turn_off',
                        json.dumps({'entity_id': CHARGER_ENTITY})], capture_output=True, text=True)
    ok = r.returncode == 0
    print('CHARGER %s%s' % ('on' if on else 'off', '' if ok else ' FAILED: ' + (r.stderr or r.stdout).strip()[-200:]))
    return ok


def pico_on_usb():
    r = adb('shell', 'cat /sys/bus/usb/devices/*/idVendor', check=False)
    return PICO_VID in r.stdout.split()


class ChargerOff:
    """Charger off and the Pico enumerated for the block; charger back on afterwards, also on error."""

    def __enter__(self):
        if not CHARGER_CYCLE:
            return self
        subprocess.run([ADB, 'connect', PHONE], capture_output=True)
        # otg_switch drops to 0 on boot and after idling; adbd runs as root on this build
        adb('shell', 'grep -q 1 /sys/class/power_supply/usb/otg_switch || '
                     'echo 1 > /sys/class/power_supply/usb/otg_switch', check=False)
        charger(False)
        end = time.time() + 30
        while not pico_on_usb():
            if time.time() > end:
                print('PICO_NOT_ON_USB after charger off (30 s)')
                break
            time.sleep(1)
        return self

    def __exit__(self, *exc):
        if CHARGER_CYCLE:
            charger(True)
        return False


def ensure_bridge():
    # Only start the app bridge and the forward. Do not open probe connections: the bridge serves one
    # client, and a probe closing right after the real client connects restores the old USB listener
    # over the new one, so the real client receives nothing (seen 17.9.2026).
    subprocess.run([ADB, 'connect', PHONE], capture_output=True)
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP', check=False)
    adb('shell', 'am', 'start', '-n', APP + '/.MainActivity', '--ez', 'espressopico_start_bridge', 'true',
        check=False)
    if on_phone():
        # palvelin runs on the phone itself: the bridge listens on this 127.0.0.1, and an adb
        # forward would take the port first, so the bridge could not bind it (25.9.2026)
        adb('forward', '--remove', 'tcp:%d' % PORT, check=False)
    else:
        adb('forward', 'tcp:%d' % PORT, 'tcp:%d' % PORT, check=False)
    time.sleep(2)


def on_phone():
    # Binding succeeds only to an address of this host
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind((PHONE.split(':')[0], 0))
        return True
    except OSError:
        return False
    finally:
        s.close()


class Link:
    def __init__(self):
        ensure_bridge()
        self._connect()
        hello = self.drain(0.8)
        if b'ERR usb closed' in hello:
            # USB re-enumerated (Pico reset): restart the app so it reopens the port
            self.s.close()
            adb('shell', 'am', 'force-stop', APP, check=False)
            time.sleep(2)
            ensure_bridge()
            # Sama uusinta kuin ensimmaisessa yhteydessa: tassa ilman sita laturisyklin jalkeinen komento kaatui
            # 'Connection refused' (26.9.2026: pit:6, 4 x shot/cmd, ennen sita 25.9.2026 b-ajo)
            self._connect()
            self.drain(0.8)

    def _connect(self):
        for attempt in range(10):
            try:
                self.s = socket.create_connection(('127.0.0.1', PORT), timeout=5)
                break
            except OSError:
                time.sleep(1.5)
        else:
            sys.exit('bridge not reachable on 127.0.0.1:%d' % PORT)
        self.s.settimeout(0.3)

    def drain(self, seconds):
        buf = b''
        end = time.time() + seconds
        while time.time() < end:
            try:
                d = self.s.recv(65536)
                if d:
                    buf += d
                    end = max(end, time.time() + 0.2)
            except socket.timeout:
                pass
        return buf

    def until(self, marker, seconds):
        buf = b''
        end = time.time() + seconds
        while time.time() < end:
            try:
                d = self.s.recv(65536)
                if d:
                    buf += d
                    if buf.endswith(marker):
                        return buf
            except socket.timeout:
                pass
        raise RuntimeError('timeout waiting for %r, tail %r' % (marker, buf[-200:]))

    def send(self, data):
        self.s.sendall(data)

    # ---- raw REPL (after devsafe) ----
    def enter_devsafe(self):
        self.send(b'\r\x03\x03')
        out = self.drain(1.0)
        self.send(b'\x02')
        self.drain(0.3)
        self.send(b'\x01')
        self.until(b'raw REPL; CTRL-B to exit\r\n>', 5)
        res = self.exec("try:\n import devsafe\n ok = devsafe.enter()\nexcept ImportError:\n"
                        " from machine import Pin\n for n in (11, 12, 13): Pin(n, Pin.OUT, value=0).value(0)\n"
                        " ok = [Pin(n).value() for n in (11, 12, 13)] == [0, 0, 0]\n print('NO_DEVSAFE relays off ok=%s' % ok)\n"
                        "print('SAFE_OK' if ok else 'SAFE_FAIL')")
        print(out.decode('utf-8', 'replace').strip()[-300:])
        print(res.strip())
        if 'SAFE_OK' not in res:
            self.reset()
            sys.exit('relays did not read back 0 — aborted before any operation')

    def exec(self, code, seconds=30):
        # Feed the watchdog at the start of every chunk of work
        code = "try:\n import devsafe; devsafe.feed()\nexcept Exception:\n pass\n" + code
        self.send(code.encode() + b'\x04')
        r = self.until(b'\x04>', seconds)
        body = r[r.index(b'OK') + 2:-2]
        out, err = body.split(b'\x04', 1)
        if err.strip():
            raise RuntimeError(err.decode('utf-8', 'replace'))
        return out.decode('utf-8', 'replace')

    def reset(self):
        # In raw REPL code runs on Ctrl-D; a full reset also re-initialises BLE
        self.send(b'import machine\nmachine.reset()\x04')
        time.sleep(1.5)


def cmd(command, seconds=3.0):
    link = Link()
    link.send(('CMD %s\r\n' % command).encode())
    print(link.drain(seconds).decode('utf-8', 'replace'))


def capture(seconds, out_path=None, stop_marker=None, link=None):
    link = link or Link()
    out = open(out_path, 'ab') if out_path else None
    end = time.time() + seconds
    tail = b''
    while time.time() < end:
        try:
            d = link.s.recv(65536)
        except socket.timeout:
            continue
        if not d:
            break
        sys.stdout.write(d.decode('utf-8', 'replace'))
        sys.stdout.flush()
        if out:
            out.write(d)
            out.flush()
        tail = (tail + d)[-4096:]
        if stop_marker and stop_marker in tail:
            end = min(end, time.time() + 2)
    return tail


def shot(seconds, out_path=None):
    # One connection for the command and the capture: reopening the bridge in between lost the
    # first 24 s of test shot 1 (17.9.2026)
    link = Link()
    link.send(('CMD tshot:%s\r\n' % seconds).encode())
    capture(float(seconds) + 60, out_path, stop_marker=b'TS_END', link=link)


def hold(hold_s, out_path=None):
    # Pelkka esiuutto (kayttaja 26.9.2026: laiteajot vain 2,5 barin pidolla, kunnes esiuutto on hyvaksytty).
    # pit on rajattu 6 s:iin, joten tshot:<n> ei yksin estaisi uuttoa nopealla taytolla: tshot:stop lahtee
    # <hold_s> s EU_HOLDin jalkeen ja heti, jos uuton TS-rivi silti tulee. Sama yhteys kuin shot().
    link = Link()
    link.s.settimeout(0.1)
    link.send(b'CMD tshot:40\r\n')
    out = open(out_path, 'ab') if out_path else None
    end, stop_at, sent, buf = time.time() + 100, None, False, b''
    while time.time() < end:
        try:
            d = link.s.recv(65536)
        except socket.timeout:
            d = b''
        if d:
            sys.stdout.write(d.decode('utf-8', 'replace')); sys.stdout.flush()
            if out: out.write(d); out.flush()
            buf = (buf + d)[-8192:]
            if stop_at is None and b'EU_HOLD' in buf:
                stop_at = time.time() + float(hold_s)
        brew = b'\nTS ' in buf
        if not sent and (brew or b'EU_END' in buf or (stop_at is not None and time.time() >= stop_at)):
            link.send(b'CMD tshot:stop\r\n')
            sent = True
            print('\nHOLD_STOP %s' % ('brew' if brew else 'hold'))
        if b'TS_END' in buf:
            end = min(end, time.time() + 2)
        if not d:
            time.sleep(0.02)
    return 0


def pcap(ms, out_path=None):
    # One connection for the command and the capture, same pattern as shot(): the bridge serves
    # a single client (PICO-HALLINTA.md luku 3). ms is <ms>[:<bar>] (korjaus 4); the whole argument
    # goes to the firmware unchanged, only the <ms> part feeds the host-side timeout.
    ms_part = ms.split(':', 1)[0]
    link = Link()
    link.send(('CMD pcap:%s\r\n' % ms).encode())
    # Settling is now event-driven and can take up to PCAP_SETTLE_MAX_MS (15 s, korjaus 4) before the
    # capture itself even starts, on top of the pre-existing 20 s margin.
    tail = capture(float(ms_part) / 1000.0 + 15 + 20, out_path, stop_marker=b'PCAP_END', link=link)
    text = tail.decode('utf-8', 'replace')
    line = next((l for l in text.splitlines() if l.startswith('PCAP_END')), None)
    reason = line.split('reason=')[-1].strip() if line and 'reason=' in line else None
    if not line or reason != 'ok':
        print('PCAP_FAIL reason=%s' % (reason or 'no_end'))
        return 1
    return 0


def psweep(arg, out_path=None):
    # Same pattern as pcap(), but stop marker is PSWEEP_END and timeout is at least 180 s
    # (PWM-1B4-PYYHKAISY): a sweep is seven segments and six trim steps at the default n=5.
    link = Link()
    link.send(('CMD psweep:%s\r\n' % arg).encode())
    tail = capture(180, out_path, stop_marker=b'PSWEEP_END', link=link)
    text = tail.decode('utf-8', 'replace')
    line = next((l for l in text.splitlines() if l.startswith('PSWEEP_END')), None)
    reason = line.split('reason=')[-1].strip() if line and 'reason=' in line else None
    if not line or reason != 'ok':
        print('PSWEEP_FAIL reason=%s' % (reason or 'no_end'))
        return 1
    return 0


def plen(arg, out_path=None):
    # Gap-length sweep: does the cut quantise to mains half cycles? Stop marker PLEN_END.
    link = Link()
    link.send(('CMD plen:%s\r\n' % arg).encode())
    tail = capture(300, out_path, stop_marker=b'PLEN_END', link=link)
    text = tail.decode('utf-8', 'replace')
    line = next((l for l in text.splitlines() if l.startswith('PLEN_END')), None)
    reason = line.split('reason=')[-1].strip() if line and 'reason=' in line else None
    if not line or reason != 'ok':
        print('PLEN_FAIL reason=%s' % (reason or 'no_end'))
        return 1
    return 0


def pgap(arg, out_path=None):
    # Same pattern as pstep(): several 20 ms gaps with the alignment searched during the run.
    link = Link()
    link.send(('CMD pgap:%s\r\n' % arg).encode())
    tail = capture(300, out_path, stop_marker=b'PGAP_END', link=link)
    text = tail.decode('utf-8', 'replace')
    line = next((l for l in text.splitlines() if l.startswith('PGAP_END')), None)
    reason = line.split('reason=')[-1].strip() if line and 'reason=' in line else None
    if not line or reason != 'ok':
        print('PGAP_FAIL reason=%s' % (reason or 'no_end'))
        return 1
    return 0


def vkello(arg, out_path=None):
    link = Link()
    link.send(('CMD vkello:%s\r\n' % arg).encode())
    tail = capture(300, out_path, stop_marker=b'VKELLO_END', link=link)
    text = tail.decode('utf-8', 'replace')
    line = next((l for l in text.splitlines() if l.startswith('VKELLO_END')), None)
    reason = line.split('reason=')[-1].strip() if line and 'reason=' in line else None
    if not line or reason != 'ok':
        print('VKELLO_FAIL reason=%s' % (reason or 'no_end')); return 1
    return 0


def vsweep(reps, out_path=None):
    # Phase sweep of single 10 ms gaps from the mains clock edge (TILAUS-K/L step 1, 24.9.2026).
    link = Link()
    link.send(('CMD vsweep:%s\r\n' % reps).encode())
    tail = capture(300, out_path, stop_marker=b'VSWEEP_END', link=link)
    text = tail.decode('utf-8', 'replace')
    line = next((l for l in text.splitlines() if l.startswith('VSWEEP_END')), None)
    reason = line.split('reason=')[-1].split()[0].strip() if line and 'reason=' in line else None
    if not line or reason != 'ok':
        print('VSWEEP_FAIL reason=%s' % (reason or 'no_end')); return 1
    return 0


def klamp(seconds, out_path=None):
    # Throttle warm-up (24.9.2026): success is reason=done — the plateau pressure is held with the
    # pump unlimited. timeout means the throttle still needed limiting when the time ran out.
    link = Link()
    link.send(('CMD klamp:%s\r\n' % seconds).encode())
    tail = capture(float(seconds) + 20, out_path, stop_marker=b'KLAMP_END', link=link)
    text = tail.decode('utf-8', 'replace')
    line = next((l for l in text.splitlines() if l.startswith('KLAMP_END')), None)
    reason = line.split('reason=')[-1].split()[0].strip() if line and 'reason=' in line else None
    if not line or reason != 'done':
        print('KLAMP_FAIL reason=%s' % (reason or 'no_end')); return 1
    return 0


def pstep(arg, out_path=None):
    # Same pattern as psweep(), stop marker PSTEP_END. The timeout is 300 s because the run itself
    # is up to 25 s and the device then prints up to 14000 raw samples, 20 to a line.
    link = Link()
    link.send(('CMD pstep:%s\r\n' % arg).encode())
    tail = capture(300, out_path, stop_marker=b'PSTEP_END', link=link)
    text = tail.decode('utf-8', 'replace')
    line = next((l for l in text.splitlines() if l.startswith('PSTEP_END')), None)
    reason = line.split('reason=')[-1].strip() if line and 'reason=' in line else None
    if not line or reason != 'ok':
        print('PSTEP_FAIL reason=%s' % (reason or 'no_end'))
        return 1
    return 0


def phold(seconds, out_path=None):
    # One connection for the command and the capture, same pattern as pcap()/shot(): the bridge
    # serves a single client (PICO-HALLINTA.md luku 3).
    link = Link()
    link.send(('CMD phold:%s\r\n' % seconds).encode())
    tail = capture(float(seconds) + 20, out_path, stop_marker=b'PHOLD_END', link=link)
    text = tail.decode('utf-8', 'replace')
    line = next((l for l in text.splitlines() if l.startswith('PHOLD_END')), None)
    reason = line.split('reason=')[-1].split()[0].strip() if line and 'reason=' in line else None
    if not line or reason not in ('ok', 'stop'):
        print('PHOLD_FAIL reason=%s' % (reason or 'no_end'))
        return 1
    return 0


def verify(manifest_path):
    manifest = json.load(open(manifest_path))
    link = Link()
    link.enter_devsafe()
    bad = n = 0
    for e in manifest:
        if e.get('skipped'):
            continue
        h = link.exec("import uhashlib,ubinascii\nh=uhashlib.sha256()\nf=open(%r,'rb')\nwhile True:\n b=f.read(512)\n"
                      " if not b: break\n h.update(b)\nf.close()\nprint(ubinascii.hexlify(h.digest()).decode())"
                      % e['name']).strip()
        n += 1
        ok = h == e['sha256']
        bad += not ok
        print('%-32s %s' % (e['name'], 'OK' if ok else 'MISMATCH ' + h[:12]))
    link.reset()
    print('VERIFIED %d/%d' % (n - bad, n))
    return bad == 0


def restore(set_name, seconds=300):
    # The app's flasher writes the set over USB; wait for its verdict in logcat so the charger stays
    # off until the flash is over (PICO-HALLINTA.md luku 7: no serial link before RESTORE_OK).
    # One argument: adb shell joins its argv with spaces, so a split format string reaches date as two
    # Fresh app process first: after the CHARGER_CYCLE re-enumeration the running app can still hold
    # the dead USB handle, and the flasher then fails at once with 'no size ack for /api_functions.py'
    # (logcat: 'USB get_status request failed'; klamp1 and vsweep1 24.9.2026, force-stop fixed both).
    adb('shell', 'am', 'force-stop', APP, check=False)
    time.sleep(2)
    since = adb('shell', "date '+%m-%d %H:%M:%S.000'").stdout.strip()
    adb('shell', 'am', 'start', '-n', APP + '/.MainActivity', '--es', 'espressopico_restore_backup', set_name)
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(3)
        log = adb('logcat', '-d', '-T', since, check=False).stdout
        for line in log.splitlines():
            if 'RESTORE_OK' in line or 'RESTORE_FAIL' in line or 'FLASH_BLOCKED' in line:
                print(line.strip())
                return 'RESTORE_OK' in line
    print('RESTORE_TIMEOUT after %d s' % seconds)
    return False


def safe():
    link = Link()
    link.enter_devsafe()
    link.reset()


def watchdog_test():
    link = Link()
    link.enter_devsafe()
    link.s.close()
    print('stopped feeding at %s; waiting for the watchdog reset' % time.strftime('%H:%M:%S'))
    t0 = time.time()
    time.sleep(15)
    # A reset re-enumerates USB: restart the app so it reopens the port and the bridge
    adb('shell', 'am', 'force-stop', APP, check=False)
    time.sleep(2)
    link = Link()
    link.send(b'CMD dev:resume\r\n')
    out = link.drain(4).decode('utf-8', 'replace')
    print(out.strip()[-300:])
    alive = 'CMD_OK dev:resume' in out
    print('WATCHDOG_TEST %s (%.0f s after last feed the firmware %s)' % (
        'PASS' if alive else 'FAIL', time.time() - t0, 'answers CMD again' if alive else 'does not answer'))
    return alive


def main(op):
    if op == 'safe':
        safe()
    elif op == 'cmd':
        cmd(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 3.0)
    elif op == 'shot':
        shot(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif op == 'hold':
        hold(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif op == 'pcap':
        sys.exit(pcap(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif op == 'psweep':
        sys.exit(psweep(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif op == 'plen':
        sys.exit(plen(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif op == 'pgap':
        sys.exit(pgap(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif op == 'vkello':
        sys.exit(vkello(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif op == 'vsweep':
        sys.exit(vsweep(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif op == 'klamp':
        sys.exit(klamp(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif op == 'pstep':
        sys.exit(pstep(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif op == 'phold':
        sys.exit(phold(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif op == 'capture':
        capture(float(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
    elif op == 'verify':
        sys.exit(0 if verify(sys.argv[2]) else 1)
    elif op == 'watchdog-test':
        watchdog_test()
    elif op == 'restore':
        sys.exit(0 if restore(sys.argv[2]) else 1)
    else:
        sys.exit(__doc__)


OPS = ('safe', 'cmd', 'shot', 'hold', 'pcap', 'psweep', 'plen', 'pgap', 'vkello', 'vsweep', 'klamp', 'pstep', 'phold', 'capture',
       'verify', 'watchdog-test', 'restore')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    op = sys.argv[1]
    if op == 'charger' and len(sys.argv) > 2 and sys.argv[2] in ('on', 'off'):
        sys.exit(0 if charger(sys.argv[2] == 'on') else 1)
    if op not in OPS:
        sys.exit(__doc__)
    with ChargerOff():
        main(op)
