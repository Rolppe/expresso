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

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
