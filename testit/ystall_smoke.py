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

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
