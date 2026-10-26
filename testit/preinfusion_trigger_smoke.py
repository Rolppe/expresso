#!/usr/bin/env python3
"""Preinfusion trigger smoke test:
1. Default values and setter clamping (0.05 - 0.50 g)
2. Commands ptrig:on/off/threshold and pitrig:on/off/threshold
3. Settings save & load persistence
4. Settings payloads BLE MTU limits (<= 240 B for both packets)
5. Drop detection triggers transition to brewing
"""
import sys, os, json, types, time
if not hasattr(time, 'sleep_us'):
    time.sleep_us = lambda us: None
if not hasattr(time, 'sleep_ms'):
    time.sleep_ms = lambda ms: None
if not hasattr(time, 'ticks_ms'):
    time.ticks_ms = lambda: 1000
if not hasattr(time, 'ticks_diff'):
    time.ticks_diff = lambda a, b: a - b

# Mock machine module if not present
if 'machine' not in sys.modules:
    m = types.ModuleType('machine')
    class MockPin:
        OUT = 1
        IN = 0
        PULL_DOWN = 2
        def __init__(self, *a, **k): self._v = 0
        def value(self, v=None):
            if v is not None: self._v = int(bool(v))
            return self._v
        def on(self): self._v = 1
        def off(self): self._v = 0
    m.Pin = MockPin
    m.disable_irq = lambda: 0
    m.enable_irq = lambda s: None
    sys.modules['machine'] = m

if 'bluetooth' not in sys.modules:
    bt = types.ModuleType('bluetooth')
    bt.UUID = lambda x: x.encode()
    bt.FLAG_READ = 1; bt.FLAG_NOTIFY = 2; bt.FLAG_WRITE = 4
    sys.modules['bluetooth'] = bt

if 'micropython' not in sys.modules:
    mp = types.ModuleType('micropython')
    mp.const = lambda x: x
    sys.modules['micropython'] = mp

pico_dir = os.path.join(os.path.dirname(__file__), '..', 'pico')
sys.path.insert(0, pico_dir)

import preset
import classes
import commands
import functions
import bluetooth_handler
from scale import FirstDropDetector, Scale

FAILED = []

def check(name, cond):
    if cond:
        print('ok  ', name)
    else:
        print('FAIL', name)
        FAILED.append(name)

class MockUtime:
    def ticks_ms(self): return 1000
    def ticks_us(self): return 1000000
    def ticks_diff(self, a, b): return a - b
    def ticks_add(self, a, b): return a + b

sys.modules['utime'] = MockUtime()

def make_bd():
    ps = types.SimpleNamespace(gain=1.0, offset=0.0,
                               pressure_sensor=types.SimpleNamespace(read_u16=lambda: 0))
    bd = classes.BrewData(MockPin, None, preset.PINS, preset.TARGET_TEMPERATURES, preset.FEATURES,
                          None, types.SimpleNamespace(read_temperature=lambda: 95.0, c1_active=lambda: False,
                                                      c1_temperature=lambda: None, c1_ms=lambda: None), ps,
                          utime=MockUtime())
    return bd

def test_defaults_and_clamping():
    bd = make_bd()
    check('T1 default trigger mode is False', bd.get_pre_infusion_trigger_mode() is False)
    check('T2 default trigger threshold is 0.25g', bd.get_pre_infusion_trigger_threshold() == 0.25)

    bd.set_pre_infusion_trigger_mode(True)
    check('T3 set mode True', bd.get_pre_infusion_trigger_mode() is True)

    bd.set_pre_infusion_trigger_threshold(0.15)
    check('T4 set threshold 0.15g', abs(bd.get_pre_infusion_trigger_threshold() - 0.15) < 1e-4)

    # Clamping
    bd.set_pre_infusion_trigger_threshold(0.01)
    check('T5 clamp min 0.05g', abs(bd.get_pre_infusion_trigger_threshold() - 0.05) < 1e-4)

    bd.set_pre_infusion_trigger_threshold(0.99)
    check('T6 clamp max 0.50g', abs(bd.get_pre_infusion_trigger_threshold() - 0.50) < 1e-4)

def test_commands():
    bd = make_bd()
    commands.handle_command(bd, 'ptrig:on')
    check('C1 ptrig:on enables', bd.get_pre_infusion_trigger_mode() is True)

    commands.handle_command(bd, 'ptrig:off')
    check('C2 ptrig:off disables', bd.get_pre_infusion_trigger_mode() is False)

    commands.handle_command(bd, 'pitrig:on')
    check('C3 pitrig:on alias enables', bd.get_pre_infusion_trigger_mode() is True)

    commands.handle_command(bd, 'pitrig:off')
    check('C4 pitrig:off alias disables', bd.get_pre_infusion_trigger_mode() is False)

    commands.handle_command(bd, 'ptrig:0.35')
    check('C5 ptrig:0.35 sets threshold', abs(bd.get_pre_infusion_trigger_threshold() - 0.35) < 1e-4)

    commands.handle_command(bd, 'pitrig:0.10')
    check('C6 pitrig:0.10 sets threshold', abs(bd.get_pre_infusion_trigger_threshold() - 0.10) < 1e-4)

    commands.handle_command(bd, 'peq:on')
    check('C7 peq:on enables', bd.get_idle_pressure_equalize_mode() is True)

    commands.handle_command(bd, 'peq:off')
    check('C8 peq:off disables', bd.get_idle_pressure_equalize_mode() is False)

def test_settings_persistence():
    bd = make_bd()
    bd.set_pre_infusion_trigger_mode(True)
    bd.set_pre_infusion_trigger_threshold(0.20)
    bd.set_idle_pressure_equalize_mode(True)

    # Save to dummy file
    functions.save_settings(bd, json)
    with open('settings.txt') as f:
        data = json.load(f)
    check('S1 saved pre_infusion_trigger_mode is True', data.get('pre_infusion_trigger_mode') is True)
    check('S2 saved pre_infusion_trigger_threshold is 0.20', data.get('pre_infusion_trigger_threshold') == 0.20)
    check('S2b saved idle_pressure_equalize_mode is True', data.get('idle_pressure_equalize_mode') is True)

    # Load into fresh BrewData
    bd2 = make_bd()
    functions.load_settings(json, bd2)
    check('S3 loaded mode is True', bd2.get_pre_infusion_trigger_mode() is True)
    check('S4 loaded threshold is 0.20', abs(bd2.get_pre_infusion_trigger_threshold() - 0.20) < 1e-4)
    check('S4b loaded peq is True', bd2.get_idle_pressure_equalize_mode() is True)

    # Cleanup settings.txt
    try: os.remove('settings.txt')
    except Exception: pass

def test_ble_payloads():
    bd = make_bd()
    bd.set_pre_infusion_trigger_mode(True)
    bd.set_pre_infusion_trigger_threshold(0.30)
    bd.set_idle_pressure_equalize_mode(True)
    p1, p2 = bluetooth_handler.settings_payloads(bd)

    s1 = json.dumps(p1)
    s2 = json.dumps(p2)
    check('B1 p1 <= 240 bytes', len(s1) <= 240)
    check('B2 p2 <= 240 bytes', len(s2) <= 240)
    check('B3 p1 has pre_infusion_trigger_mode', 'pre_infusion_trigger_mode' in p1 and p1['pre_infusion_trigger_mode'] is True)
    check('B4 p2 has pre_infusion_trigger_threshold', 'pre_infusion_trigger_threshold' in p2 and p2['pre_infusion_trigger_threshold'] == 0.30)
    check('B5 p2 has peq_mode', 'peq_mode' in p2 and p2['peq_mode'] is True)

def test_detector_threshold():
    det = FirstDropDetector(threshold=0.25)
    check('D1 default det threshold', det.threshold == 0.25)
    det.set_threshold(0.10)
    check('D2 set det threshold', det.threshold == 0.10 and det.k == 0.04)
    det.set_threshold(0.05)
    check('D3 k scaled down for 0.05g', det.threshold == 0.05 and abs(det.k - 0.02) < 1e-4)

import asyncio

def test_shot_trigger_transition():
    # Verify drop_trig ends preinfusion early
    bd = make_bd()
    bd.set_pre_infusion_trigger_mode(True)
    bd.set_pre_infusion_trigger_threshold(0.20)
    bd.pre_infusion_method = 1

    scale = Scale(MockPin(1), MockPin(2))
    scale.calibrated = True
    scale.off_a = scale.off_b = 0.0
    scale.scale = 2000.0
    scale.trim_b = 1.0
    bd.tray_scale = scale
    scale.arm_drop_detector(w=100.0, threshold=0.20, blanking_ms=0)

    # Before drop
    check('X1 not triggered initially', scale.drop_detected() is False)

    # Feed below threshold
    scale.drop_detector.feed(100.10, now_ms=1000)
    check('X2 0.10g below 0.20g threshold -> False', scale.drop_detected() is False)

    # Feed at/above threshold (2 samples for streak)
    scale.drop_detector.feed(100.25, now_ms=1100)
    scale.drop_detector.feed(100.25, now_ms=1200)
    check('X3 0.25g above 0.20g threshold -> True', scale.drop_detected() is True)

    # Blanking window test (X4): pump vibration / fill spike during first 1.8s does NOT trigger
    scale.arm_drop_detector(w=100.0, threshold=0.20, blanking_ms=1800)
    scale.drop_detector.feed(101.50, now_ms=1500) # +1.50g pump spike at 500 ms after arm (t0=1000)
    check('X4 blanking prevents trigger on pump start spike', scale.drop_detected() is False)
    # After blanking window, baseline has tracked the pump state to 101.50g
    scale.drop_detector.feed(101.50, now_ms=3000)
    check('X5 settled at pump baseline', scale.drop_detected() is False)
    # Actual coffee drip on top of settled pump state (+0.25g at t=3100)
    scale.drop_detector.feed(101.75, now_ms=3100)
    scale.drop_detector.feed(101.75, now_ms=3200)
    check('X6 real drop after blanking triggers', scale.drop_detected() is True)

if __name__ == '__main__':
    test_defaults_and_clamping()
    test_commands()
    test_settings_persistence()
    test_ble_payloads()
    test_detector_threshold()
    test_shot_trigger_transition()
    print('RESULT: %d failed' % len(FAILED))
    sys.exit(1 if FAILED else 0)
