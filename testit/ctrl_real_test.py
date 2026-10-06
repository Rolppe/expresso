import os, sys, types, random, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
# Repo firmware unless FW names another set: a leftover /tmp/fw was picked silently and the test ran against
# stale code (6.10.2026)
FW = os.environ.get('FW') or os.path.join(HERE, '..', 'pico')
sys.path.insert(0, FW); sys.modules['utime'] = types.ModuleType('utime')
from classes import PumpPressureController
clock = [0]  # ms
class U:
    ticks_ms = staticmethod(lambda: clock[0])
    ticks_diff = staticmethod(lambda a, b: a - b)
    ticks_add = staticmethod(lambda a, b: a + b)
class Pin:
    v = 0
    def value(self, x=None):
        if x is None: return self.v
        self.v = x
class R:
    def set_pump_on(self): pass
    def set_pump_off(self): pass
def run(mode, ron, roff, target=8.0, delay_ms=70, noise=0.3, T=14000, seed=1):
    random.seed(seed); clock[0] = 0; relay = Pin(); c = PumpPressureController(relay, R(), U, mode=mode)
    p = 2.0; q = [0] * delay_ms; true = []; meas_all = []; next_ctrl = 0
    while clock[0] < T:
        if clock[0] >= next_ctrl:
            next_ctrl = clock[0] + 23               # measured loop ~23 ms (20 ms pressure window)
            m = p + random.gauss(0, noise); c.update(m, target)
            if clock[0] > 2000: meas_all.append(m)
        q.append(relay.v); a = q.pop(0)
        p += ((ron * (1 - p / 13.0) * 13 / 5) if a else (-roff * p / 8.0)) / 1000.0
        clock[0] += 1
        if clock[0] > 2000: true.append(p)
    return st.mean(true), st.pstdev(true), min(true), max(true), st.pstdev(meas_all)
for mode in ('bang', 'pi'):
    for ron, roff in ((10, 10), (14, 8), (7, 12)):
        m, sd, mn, mx, msd = run(mode, ron, roff)
        print('%-4s plant %2d/%2d  TRUE mean %.2f sd %.2f range %.1f-%.1f | measured sd %.2f' % (mode, ron, roff, m, sd, mn, mx, msd))
# pre-infusion target 2 bar from 0
for mode in ('bang', 'pi'):
    m, sd, mn, mx, msd = run(mode, 10, 10, target=2.0)
    print('%-4s pre-infusion 2 bar  TRUE mean %.2f sd %.2f range %.1f-%.1f' % (mode, m, sd, mn, mx))
