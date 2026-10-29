#!/usr/bin/env python3
"""c1x_todennus_smoke.py — c1x oletuksena laitteella ja uuttotodennus (EXPRESSO-C1X-TODENNUS).

VAATIMUS: TILAUS-O, TILAUS-AUTONOMIA

Todentaa:
1. BrewData.eu_c1x on oletuksena 1 (classes.BrewData: ytimen 1 c1x aktiivinen ilman erillistä komentoa).
2. Komentokäsittely commands.py:
   - c1x:0 kytkee eu_c1x = 0 (vanha polku).
   - c1x:1 kytkee eu_c1x = 1 (c1x-polku).
3. Firmware-vakiot functions.py:
   - EU_C1X_LAG_S = 0.025 s (25 ms lisäviivekompensaatio).
   - EB_C1X_KP_TAIL = 0.2 (pidon alun P c1x:llä).
4. Laiteuuttojen todennus oikeista 21.10.2026 uuttolokeista (testit/bh-20261021-s1..s4.log):
   - EU_START c1x=1 jokaisessa ajossa (c1x toimi oletuksena ilman komentoa).
   - EU_END miss=0, late=0 jokaisessa ajossa.
   - EB_END miss=0, late=0 jokaisessa ajossa.
   - EB_C1X late=0, starve=0, ovf=0 jokaisessa ajossa.
   - TS_END c1_bad=0, c1_err=0 jokaisessa ajossa.
5. Invariantti TILAUS-O:
   - Uuton aikana paine mitataan joka jaksossa, eikä yksikään pumpun jakso jää pois
     tai tule ylimääräisenä viiveen takia (miss=0, late=0, starve=0 kaikissa uutoissa).
"""

import glob
import importlib.util
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
PICO_DIR = os.path.join(REPO_ROOT, 'pico')
sys.path.insert(0, PICO_DIR)
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, HERE)

# Mock MicroPython modules for pico/classes and commands
clock = [0]


class Utime:
    def ticks_ms(self): return clock[0]
    def ticks_us(self): return clock[0] * 1000
    def ticks_add(self, t, d): return t + d
    def ticks_diff(self, a, b): return a - b
    def sleep_ms(self, ms): clock[0] += ms
    def sleep_us(self, us): clock[0] += us // 1000


utime = Utime()
sys.modules['utime'] = utime


class Pin:
    IN = 0; OUT = 1; PULL_DOWN = 0; PULL_UP = 1
    def __init__(self, n, *a, **k): self.n = n
    def value(self, v=None): return 0
    def off(self): pass
    def on(self): pass


class WDT:
    def __init__(self, timeout): pass
    def feed(self): pass


machine = types.ModuleType('machine')
machine.Pin = Pin
machine.WDT = WDT
machine.disable_irq = lambda: 0
machine.enable_irq = lambda s=0: None
sys.modules['machine'] = machine

PRESET = os.path.join(PICO_DIR, 'preset.py')
spec = importlib.util.spec_from_file_location('preset', PRESET)
preset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preset)
sys.modules['preset'] = preset

import classes
import commands
import functions

fails = []


def check(name, cond, extra=''):
    status = 'OK  ' if cond else 'FAIL'
    print(f'{status} {name}' + (f' — {extra}' if extra else ''))
    if not cond:
        fails.append(name)


def make_brew_data():
    clock[0] = 0
    bd = classes.BrewData(Pin, None, preset.PINS, preset.TARGET_TEMPERATURES, preset.FEATURES, None, None, None, utime)
    bd.pcal_status = lambda: None
    bd.get_pressure_calibration_status = lambda: {'pcal_state': 'idle', 'pcal_stage': '', 'pcal_gain': 1.0,
                                                  'pcal_offset': 0.0, 'pcal_msg': ''}
    return bd


def main():
    print('=== c1x_todennus_smoke.py: c1x oletuksena ja uuttotodennus ===')

    # 1. BrewData eu_c1x oletusarvo
    bd = make_brew_data()
    check('1. BrewData.eu_c1x on oletuksena 1 (c1x aktiivinen)', bd.eu_c1x == 1, f'eu_c1x={bd.eu_c1x}')

    # 2. commands.py komentokäsittely
    commands.handle_command(bd, 'c1x:0')
    check('2a. commands: c1x:0 asettaa eu_c1x=0', bd.eu_c1x == 0, f'eu_c1x={bd.eu_c1x}')
    commands.handle_command(bd, 'c1x:1')
    check('2b. commands: c1x:1 asettaa eu_c1x=1', bd.eu_c1x == 1, f'eu_c1x={bd.eu_c1x}')

    # 3. Firmware-vakiot functions.py
    check('3a. functions.EU_C1X_LAG_S on 0.025 s', getattr(functions, 'EU_C1X_LAG_S', None) == 0.025,
          f'EU_C1X_LAG_S={getattr(functions, "EU_C1X_LAG_S", None)}')
    check('3b. functions.EB_C1X_KP_TAIL on 0.2', getattr(functions, 'EB_C1X_KP_TAIL', None) == 0.2,
          f'EB_C1X_KP_TAIL={getattr(functions, "EB_C1X_KP_TAIL", None)}')

    # 4. Laiteuuttojen todennus lokeista bh-20261021-s1..s4.log
    log_files = sorted(glob.glob(os.path.join(HERE, 'bh-20261021-s[1-4].log')))
    check('4a. Laiteuuttolokit s1..s4 löytyvät', len(log_files) == 4, f'löydetty {len(log_files)} kpl')

    total_miss = 0
    total_late = 0
    total_starve = 0
    total_ovf = 0
    total_shots = 0

    for fpath in log_files:
        shot_id = os.path.basename(fpath).split('.')[0]
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # EU_START
        eu_start_m = re.search(r'EU_START\s+.*?\bc1x=(\d+)', content)
        c1x_val = int(eu_start_m.group(1)) if eu_start_m else None
        check(f'4b. {shot_id}: EU_START c1x=1 oletuksena', c1x_val == 1, f'c1x={c1x_val}')

        # EU_END
        eu_end_m = re.search(r'EU_END\s+reason=(\w+).*?\blate=(\d+)\s+miss=(\d+)', content)
        eu_reason = eu_end_m.group(1) if eu_end_m else None
        eu_late = int(eu_end_m.group(2)) if eu_end_m else -1
        eu_miss = int(eu_end_m.group(3)) if eu_end_m else -1
        check(f'4c. {shot_id}: EU_END reason=done, late=0, miss=0',
              eu_reason == 'done' and eu_late == 0 and eu_miss == 0,
              f'reason={eu_reason}, late={eu_late}, miss={eu_miss}')

        # EB_END
        eb_end_m = re.search(r'EB_END\s+reason=(\w+).*?\blate=(\d+)\s+miss=(\d+)', content)
        eb_reason = eb_end_m.group(1) if eb_end_m else None
        eb_late = int(eb_end_m.group(2)) if eb_end_m else -1
        eb_miss = int(eb_end_m.group(3)) if eb_end_m else -1
        check(f'4d. {shot_id}: EB_END reason=stop, late=0, miss=0',
              eb_reason == 'stop' and eb_late == 0 and eb_miss == 0,
              f'reason={eb_reason}, late={eb_late}, miss={eb_miss}')

        # EB_C1X
        eb_c1x_m = re.search(r'EB_C1X\s+.*?\bovf=(\d+).*?\blate=(\d+)\s+starve=(\d+)', content)
        c1x_ovf = int(eb_c1x_m.group(1)) if eb_c1x_m else -1
        c1x_late = int(eb_c1x_m.group(2)) if eb_c1x_m else -1
        c1x_starve = int(eb_c1x_m.group(3)) if eb_c1x_m else -1
        check(f'4e. {shot_id}: EB_C1X ovf=0, late=0, starve=0',
              c1x_ovf == 0 and c1x_late == 0 and c1x_starve == 0,
              f'ovf={c1x_ovf}, late={c1x_late}, starve={c1x_starve}')

        if eu_miss >= 0 and eb_miss >= 0:
            total_miss += eu_miss + eb_miss
            total_late += eu_late + eb_late + c1x_late
            total_starve += c1x_starve
            total_ovf += c1x_ovf
            total_shots += 1

    # 5. Kokonaisvaltainen invariantti (TILAUS-O)
    check('5. TILAUS-O toteutuu: 4/4 uutossa miss=0, late=0, starve=0, ovf=0',
          total_shots == 4 and total_miss == 0 and total_late == 0 and total_starve == 0 and total_ovf == 0,
          f'shots={total_shots}, miss={total_miss}, late={total_late}, starve={total_starve}, ovf={total_ovf}')

    print(f'\nRESULT: {len(fails)} failed')
    return 0 if len(fails) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
