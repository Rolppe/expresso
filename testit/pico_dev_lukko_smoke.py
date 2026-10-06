#!/usr/bin/env python3
"""Smoke test for pico_dev.py lock and signal exit. No device, no network; never runs pico_dev.py as a CLI."""
import os
import re
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(HERE, '..'))
TMP = tempfile.mkdtemp(prefix='pico_lukko_')
LOCK = os.path.join(TMP, 'test.lock')
os.environ['PICO_DEV_LOCK'] = LOCK
sys.path.insert(0, SRC_DIR)
import pico_dev  # noqa: E402,F401

PRE = 'import sys; sys.path.insert(0, %r); import pico_dev, time; ' % SRC_DIR
results = []


def check(name, ok, info=''):
    results.append(ok)
    print('%s %s %s' % ('PASS' if ok else 'FAIL', name, info))


def wait_for(path, text, limit=10):
    end = time.time() + limit
    while time.time() < end:
        try:
            if text in open(path).read():
                return True
        except OSError:
            pass
        time.sleep(0.1)
    return False


# (a)
p1 = subprocess.Popen([sys.executable, '-c', PRE + "f = pico_dev.acquire_lock('capture'); time.sleep(5)"])
try:
    up = wait_for(LOCK, 'op=capture')
    r = subprocess.run([sys.executable, '-c', PRE + "pico_dev.acquire_lock('cmd')"],
                       capture_output=True, text=True, timeout=20)
    check('a busy', up and r.returncode != 0 and 'PICO_BUSY pid=' in r.stderr, 'rc=%s' % r.returncode)
    # (b)
    p1.kill()
    p1.wait(timeout=20)
    r = subprocess.run([sys.executable, '-c', PRE + "pico_dev.acquire_lock('cmd')"],
                       capture_output=True, text=True, timeout=20)
    check('b free after kill', r.returncode == 0, 'rc=%s %s' % (r.returncode, r.stderr.strip()[-100:]))
finally:
    if p1.poll() is None:
        p1.kill()

# (c)
MARK = os.path.join(TMP, 'mark')
READY = os.path.join(TMP, 'ready')
code = PRE + ("""
class C:
    def __enter__(self): return self
    def __exit__(self, *e): open(%r, 'w').write('x'); return False
pico_dev.install_signal_exit()
with C():
    open(%r, 'w').write('r')
    time.sleep(10)
""" % (MARK, READY))
p2 = subprocess.Popen([sys.executable, '-c', code])
try:
    up = wait_for(READY, 'r')
    p2.send_signal(signal.SIGTERM)
    rc = p2.wait(timeout=20)
    check('c sigterm exit', up and os.path.exists(MARK) and rc == 143, 'rc=%s' % rc)
finally:
    if p2.poll() is None:
        p2.kill()

# (d)
src = open(os.path.join(SRC_DIR, 'pico_dev.py')).read()
m = src.find("if __name__ == '__main__':")
a = src.find('acquire_lock(op)', m)
w = src.find('with ChargerOff():', m)
r_ = src.find("op != 'restore'", m)
i_ = src.find('install_signal_exit()', m)
check('d source order', m >= 0 and a >= 0 and w >= 0 and a < w and 0 <= r_ < i_)

n = sum(results)
if n == 4:
    print('LUKKO_SMOKE OK 4/4')
    sys.exit(0)
print('LUKKO_SMOKE FAIL %d/4' % n)
sys.exit(1)
