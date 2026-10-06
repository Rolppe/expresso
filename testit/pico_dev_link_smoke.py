#!/usr/bin/env python3
"""Smoke test for pico_dev.py Link.until noise handling and enter_devsafe bridge reopen.
No device, no network, no adb; never runs pico_dev.py as a CLI."""
import os
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, SRC_DIR)
import pico_dev  # noqa: E402

NOISE = b"OK hi\x04\x04>Received: 'sync'\r\n"
results = []


def check(name, ok, info=''):
    results.append(ok)
    print('%s %s %s' % ('PASS' if ok else 'FAIL', name, info))


class FakeSock:
    def __init__(self, chunks=(), on_send=None):
        self.chunks = list(chunks)
        self.sent = []
        self.on_send = on_send

    def recv(self, n):
        if self.chunks:
            return self.chunks.pop(0)
        raise socket.timeout()

    def sendall(self, data):
        self.sent.append(data)
        if self.on_send:
            self.on_send(self, data)

    def close(self):
        pass


def make_link(sock):
    link = object.__new__(pico_dev.Link)
    link.s = sock
    return link


# (a)
link = make_link(FakeSock([NOISE]))
r = link.until(b'\x04>', 2)
check('a until drops noise', r.endswith(b'\x04>') and b'Received' not in r, repr(r))

# (b)
link = make_link(FakeSock([NOISE]))
r = link.exec('print(1)')
check('b exec with noise', r.strip() == 'hi', repr(r))

# (c)
link = make_link(FakeSock())
try:
    link.until(b'X', 0.5)
    check('c timeout', False, 'no exception')
except pico_dev.LinkTimeout as e:
    check('c timeout', e.buf == b'', repr(e.buf))


# (d)
def good_send(sock, data):
    if data == b'\x01':
        sock.chunks.append(b'raw REPL; CTRL-B to exit\r\n>')
    elif data.endswith(b'\x04'):
        sock.chunks.append(b'OK SAFE_OK\r\n\x04\x04>')


calls = []
link = make_link(FakeSock())


def fake_reopen():
    calls.append(1)
    link.s = FakeSock(on_send=good_send)


link.reopen = fake_reopen
ok_d = True
info = ''
try:
    link.enter_devsafe()
except SystemExit as e:
    ok_d = False
    info = 'SystemExit %s' % e
except Exception as e:  # noqa: BLE001
    ok_d = False
    info = repr(e)
ok_d = ok_d and len(calls) == 1

calls2 = []
link2 = make_link(FakeSock(on_send=lambda sock, data: sock.chunks.append(b'junk') if data == b'\x01' else None))
link2.reopen = lambda: calls2.append(1)
try:
    link2.enter_devsafe()
    ok_d = False
    info += ' nonempty: no exception'
except pico_dev.LinkTimeout:
    ok_d = ok_d and len(calls2) == 0
check('d devsafe reopen', ok_d, 'reopen=%d/%d %s' % (len(calls), len(calls2), info))

n = sum(results)
if n == 4:
    print('LINK_SMOKE OK 4/4')
    sys.exit(0)
print('LINK_SMOKE FAIL %d/4' % n)
sys.exit(1)
