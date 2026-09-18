import sys, types, asyncio as aio, time
sys.path.insert(0, '/tmp/fw')
# MicroPython-only modules used at import time
for m in ('utime',):
    sys.modules[m] = types.ModuleType(m)
import classes, functions
from classes import BrewData, PressureSensor

class Pin:
    def __init__(self, v=0): self.v = v
    def value(self, x=None):
        if x is None: return self.v
        self.v = x

class FakeSensor(PressureSensor):
    """True pressure = physics; sensor raw_bar reads true*0.9 - 0.4 (miscalibrated)."""
    def __init__(self, machine):
        self.gain, self.offset, self.last_raw_bar, self.m = 1.0, 0.0, 0.0, machine
        self.CAL_FILE = '/tmp/pcal_test_cal.json'
    def get_pressure(self):
        # the real read takes a 20 ms averaging window
        m.step(pump.v == 1, 0.020); clock[0] += 0.020
        raw = self.m.true * 0.9 - 0.4
        self.last_raw_bar = raw
        return round(self.gain * raw + self.offset, 1)

class Machine:
    def __init__(self): self.true = 0.0; self.acc = 0.0; self.n = 0; self.t = 0.0
    def step(self, pump_on, dt):
        self.true = max(0.0, self.true + (8.0 if pump_on else -3.0) * dt)
        self.t += dt
        if self.t >= 5.0: self.acc += self.true * dt; self.n += dt

class U:
    @staticmethod
    def ticks_ms(): return int(clock[0] * 1000)
    @staticmethod
    def ticks_diff(a, b): return a - b
    @staticmethod
    def ticks_add(a, b): return a + b

clock = [0.0]
m = Machine()
pump, sol, heat = Pin(), Pin(), Pin(1)
sw = (Pin(), Pin(), Pin())

class A:
    @staticmethod
    async def sleep_ms(ms):
        dt = ms / 1000.0
        m.step(pump.v == 1, dt); clock[0] += dt

bd = BrewData.__new__(BrewData)
bd.pressure_sensor = FakeSensor(m)
bd.pcal_request = None; bd.pcal_cancel = False; bd.pcal_state = 'idle'; bd.pcal_stage = ''
bd.pcal_msg = ''; bd.pcal_target = 0.0; bd.pcal_raw = {}; bd.pcal_points = {}
bd.pre_infusion_pressure = 2.0; bd.brew_pressure = 9.0; bd.mode = 'IDLE'
bd.get_relays = lambda: (pump, sol, heat)
bd.get_switches = lambda: sw

def run(stage):
    assert bd.request_pressure_calibration(stage)
    st = bd.take_pressure_calibration_request()
    m.acc = 0.0; m.n = 0.0; m.t = 0.0
    aio.run(functions.pressure_calibration_run(bd, U, A, st))
    return m.acc / m.n if m.n else m.true

for it in range(4):
    true = run('pre')
    gauge = round(true, 1)
    print('pre  it%d state=%s sensor_target=2.0 gauge=%.1f gain=%.3f off=%.3f relays P%d S%d H%d mode=%s' % (
        it, bd.pcal_state, gauge, bd.pressure_sensor.gain, bd.pressure_sensor.offset, pump.v, sol.v, heat.v, bd.mode))
    if abs(gauge - 2.0) <= 0.2: break
    bd.pressure_calibration_measured('pre', gauge)
for it in range(4):
    true = run('brew')
    gauge = round(true, 1)
    print('brew it%d state=%s sensor_target=9.0 gauge=%.1f gain=%.3f off=%.3f' % (
        it, bd.pcal_state, gauge, bd.pressure_sensor.gain, bd.pressure_sensor.offset))
    if abs(gauge - 9.0) <= 0.2: break
    bd.pressure_calibration_measured('brew', gauge)
print('final: true gain should be 1/0.9=%.3f offset 0.4/0.9=%.3f' % (1/0.9, 0.4/0.9))
run('pre'); print('pre recheck gauge %.1f' % m.true)
# switch abort
sw[0].v = 1; run('pre'); print('switch abort ->', bd.pcal_state, bd.pcal_msg, 'relays P%d S%d' % (pump.v, sol.v)); sw[0].v = 0
# invalid measurement rejected
bd.pcal_raw['pre'] = 2.0; bd.pcal_points.pop('brew', None); g0 = bd.pressure_sensor.gain
bd.pressure_calibration_measured('pre', 9.5); print('reject ->', bd.pcal_state, bd.pcal_msg, 'gain unchanged', bd.pressure_sensor.gain == g0)
bd.pressure_calibration_save(); import json; print('saved', json.load(open('/tmp/pcal_test_cal.json')))
bd.pressure_sensor.gain = 7; bd.pressure_calibration_end_session(); print('reload after end ->', bd.pressure_sensor.gain, bd.pcal_state)
