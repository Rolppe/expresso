#!/usr/bin/env python3
"""psweep_dryrun.py — pyyhkaisyn kuivaharjoitus: oikea pressure_sweep_run laitosmallia vasten.

    python3 testit/psweep_dryrun.py [tavoite_bar] [n] [ms]     ajaa ja kirjoittaa lokin /tmp:hen
    DRY_NOISE=0.0 GATE_MULT=8 python3 testit/psweep_dryrun.py  kohina ja portin jakso ympariston kautta

Tarkoitus on nahda ennen vedenkeittoa, tuottaako asetelma luettavan viiveen. Virtuaalikello: yksi
ajo kestaa sekunteja, ei minuutteja. Tama ei korvaa laiteajoa eika ole hyvaksyntatesti.

Laitos: dp/dt = 6.7*pumppu - 1.24*p (real_plant_sim.py, sovitettu oikeaan uuttoon), 70 ms
kuljetusviive. Magneettiventtiili auki + pumppu pois: dp/dt = -8.0*p (arvio, ei mitattu).
Vareily: iskut 50,1 Hz, hydraulinen viive 9 ms (tuntematon, jota mittaus etsii), amplitudi
mitatuista pisteista (0 bar -> 1,788 / 6,5 -> 0,947 / 7,7 -> 0,307), kohina sd 0,36 bar.
"""
import asyncio, io, math, os, random, sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pico'))
sys.path.insert(0, HERE)
import functions as F

RAW_A, RAW_B = F.PCAP_RAW_A, F.PCAP_RAW_B
GAIN, LEAK, LEAK_OPEN = 6.7, 1.24, 8.0
DELAY_S = 0.009
F_MAINS = 50.1
TAU_PULSE = 0.005
NOISE = float(os.environ.get("DRY_NOISE", "0.36"))
DEAD_S = 0.070

def amp_at(p):
    pts = [(0.0, 1.788), (6.55, 0.947), (7.69, 0.307)]
    if p <= pts[0][0]: return pts[0][1]
    if p >= pts[-1][0]: return max(0.05, pts[-1][1])
    for (x0,y0),(x1,y1) in zip(pts, pts[1:]):
        if x0 <= p <= x1:
            return y0 + (y1-y0)*(p-x0)/(x1-x0)
    return 0.3

class Clock:
    def __init__(self): self.us = 0

class Plant:
    def __init__(self, clock, p0=0.0, seed=1):
        self.c = clock; self.p = p0; self.last = 0; self.q = [0.0]*70
        self.rnd = random.Random(seed); self.strokes = []
        self.pump = 0; self.sol = 0
    def advance(self, now_us):
        dt_ms = (now_us - self.last)//1000
        if dt_ms <= 0: return
        if dt_ms > 5000: dt_ms = 5000
        for k in range(dt_ms):
            t = (self.last + k*1000)/1e6
            self.q.append(self.pump); u = self.q.pop(0)
            if self.pump == 0 and self.sol:
                dp = -LEAK_OPEN*self.p
            else:
                dp = (GAIN if u else 0.0) - LEAK*self.p
            self.p = max(0.0, self.p + dp/1000.0)
            # Portti ohjaa pumppua viiveetta: isku syntyy self.pump:sta, ei viivastetysta u:sta.
            # Vain vaste viivastyy, ja se on strokes-listan aikaleimassa.
            if self.pump:
                ph = (t*F_MAINS) % 1.0
                if ph < 1.0/1000*F_MAINS:
                    self.strokes.append(t + DEAD_S + DELAY_S)
        self.last = now_us
    def bar(self, now_us):
        self.advance(now_us)
        t = now_us/1e6
        r = 0.0
        a = amp_at(self.p)
        for ts in self.strokes[-40:]:
            d = t - ts
            if 0 <= d < 8*TAU_PULSE:
                r += a*math.exp(-d/TAU_PULSE)
        return self.p + r + self.rnd.gauss(0, NOISE)

class Pin:
    def __init__(self, plant, which=None):
        self.v = 0; self.plant = plant; self.which = which
    def value(self, x=None):
        if x is None: return self.v
        self.v = x
        if self.which == 'pump': self.plant.pump = x
        if self.which == 'sol': self.plant.sol = x

class Adc:
    def __init__(self, plant, clock, bd): self.plant, self.c, self.bd = plant, clock, bd
    def read_u16(self):
        bar = self.plant.bar(self.c.us)
        raw = ((bar - self.bd.offset_)/1.0 - RAW_B)/RAW_A
        return int(max(0, min(65535, raw)))

class Sensor:
    def __init__(self, adc): self.pressure_sensor = adc; self.gain = 1.0; self.offset = 0.0

class BD:
    def __init__(self, clock, target, n, p0=0.0, seed=1):
        self.c = clock; self.offset_ = 0.0
        self.plant = Plant(clock, p0, seed)
        self.pump = Pin(self.plant, 'pump'); self.solenoid = Pin(self.plant, 'sol')
        self.heater = Pin(self.plant)
        self.brew = Pin(self.plant); self.water = Pin(self.plant); self.steam = Pin(self.plant)
        self.pressure_sensor = Sensor(Adc(self.plant, clock, self))
        self.dev_safe = False; self.pcap_abort = False; self.psweep_abort = False
        self.pcap_target_bar = None; self.pcap_gate_phase_us = None
        self.psweep_target_bar = target; self.psweep_n = n; self.mode = None
        self.w_ms = 0
    def get_relays(self): return self.pump, self.solenoid, self.heater
    def get_switches(self): return self.brew, self.water, self.steam
    def set_mode(self, m): self.mode = m
    def get_weight(self): return 100.0
    def get_weight_ms(self): return self.w_ms
    def get_weight_limit(self): return 470.0
    def get_weight_rise_limit(self): return 250.0

class Utime:
    def __init__(self, c): self.c = c
    def ticks_ms(self): return self.c.us // 1000
    def ticks_us(self):
        self.c.us += 50                     # busy-wait etenee virtuaalikellossa
        return self.c.us
    def ticks_diff(self, a, b): return a - b
    def ticks_add(self, a, b): return a + b

class Aio:
    def __init__(self, c, bd): self.c, self.bd = c, bd
    async def sleep_ms(self, ms):
        self.c.us += max(ms, 1)*1000
        if self.c.us - self.bd.w_ms*1000 >= 50000:   # vaaka paivittyy 50 ms tahtiin
            self.bd.w_ms = self.c.us//1000
        await asyncio.sleep(0)

def run(target, n, ms, p0=0.0, seed=1):
    c = Clock(); bd = BD(c, target, n, p0, seed)
    bd.w_ms = 0
    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(F.pressure_sweep_run(bd, Utime(c), Aio(c, bd), ms))
    return buf.getvalue(), c.us/1e6

def _gate_mult():
    m = int(os.environ.get('GATE_MULT', '2'))
    if m != 2:
        F.PCAP_GATE_PERIOD_US = m * F.PCAP_MAINS_US
    return m


if __name__ == '__main__':
    _gate_mult()
    target = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    ms = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
    out, dur = run(target, n, ms)
    path = '/tmp/psweep-dryrun-%.1fbar-mult%d.log' % (target, _gate_mult())
    open(path, 'w').write(out)
    heads = [l for l in out.splitlines() if not l.startswith('PCAP ')]
    print('\n'.join(heads[:4] + ['...'] + heads[-8:]))
    print('virtuaalikesto %.1f s, loki %s' % (dur, path))
