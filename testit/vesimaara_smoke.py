#!/usr/bin/env python3
"""vesimaara_smoke.py — EXPRESSO-VESIMAARA-TUNNISTUS (27.10.2026).

Testaa säiliön vesimäärän tunnistuksen lämpöstabiiliuden saavutusnopeudesta (TILAUS-Q):
1. M1: Kylmäkäynnistyksen tunnistus (TS <= -8.0) ja mittauksen käynnistyminen
2. M2: Saavutusajan perusteella laskettu vesimäärä (tyhjä 0.2 L, puoli 1.0 L, täysi 2.0 L ja rajaukset)
3. M3: Lämpimänä käynnistys (TS > -6.0) ja edellisen tilan säilyminen ('warm_start')
4. M4: Vedenkulutuksen seuranta (consume_water_ml ja consume_water_l)
5. M5: Varoitusraja: vesimäärä <= 0.3 L -> 'low_water'
6. M6: Sarjakomennot (tank?, tank:fill, tank:set, tank:cal, tank:consume)
7. M7: Pysyvyys (water_tank.json atominen tallennus ja lataus)
8. M8: Telemetria (BrewData-getterit, live_payload, scale_payload, NOTIFY_DROP_ORDER, DIAG_MIN tk=)
9. M9: Thermostat.run -integraatio (TS-nousu päivittää vesisäiliön tilan)

    python3 testit/vesimaara_smoke.py       RESULT: 0 failed
"""

import sys
import os
import json
import io
import types
from contextlib import redirect_stdout

# Lisätään pico polkuun
PICO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pico'))
sys.path.insert(0, PICO_DIR)

bluetooth = types.ModuleType('bluetooth')
bluetooth.UUID = lambda x: x
bluetooth.FLAG_READ = 1; bluetooth.FLAG_NOTIFY = 2; bluetooth.FLAG_WRITE = 4
sys.modules['bluetooth'] = bluetooth
mp = types.ModuleType('micropython'); mp.const = lambda x: x
sys.modules['micropython'] = mp

import water_tank
import classes
import commands
import bluetooth_handler
import diagnet


class FakeUtime:
    def __init__(self, start_ms=100000):
        self._ms = start_ms

    def ticks_ms(self):
        return self._ms

    def ticks_us(self):
        return self._ms * 1000

    def time(self):
        return int(self._ms / 1000)

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b

    def advance(self, ms):
        self._ms += ms


class FakeRelay:
    def __init__(self):
        self.val = 0

    def value(self, v=None):
        if v is not None:
            self.val = v
        return self.val


class FakeSensor:
    def __init__(self, t=20.0):
        self.t = t

    def read_temperature(self):
        return self.t


def main():
    fails = []

    def check(name, cond, extra=''):
        if cond:
            print('ok   %s' % name)
        else:
            fails.append(name)
            print('FAIL %s %s' % (name, ('— ' + str(extra)) if extra else ''))

    tmp_state = '/tmp/test_water_tank.json'
    for f in (tmp_state, tmp_state + '.tmp'):
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    utime = FakeUtime(100000)

    # -------------------------------------------------------------------------
    # M1: Kylmäkäynnistyksen tunnistus (TS <= -8.0)
    # -------------------------------------------------------------------------
    wt = water_tank.WaterTankTracker(utime, state_file=tmp_state)
    check('M1a alkutila on init', wt.status == 'init')
    check('M1b oletustilavuus 2.0 L', wt.tank_water_l == 2.0)

    wt.update(ts=-9.5, now_ms=utime.ticks_ms(), mode='IDLE')
    check('M1c kylmäkäynnistys (TS=-9.5) aloittaa mittauksen', wt.status == 'measuring' and wt._measuring)

    # -------------------------------------------------------------------------
    # M2: Saavutusaika ja vesimäärän arviointi
    # -------------------------------------------------------------------------
    # M2a: Tyhjä / vähäinen vesi: 300 s -> 0.0020 * 300 - 0.40 = 0.20 L
    utime.advance(300 * 1000)
    wt.update(ts=-2.0, now_ms=utime.ticks_ms(), mode='IDLE')
    check('M2a 300 s saavutusaika arvioi 0.20 L (tyhjä/vähäinen)', abs(wt.tank_water_l - 0.20) < 0.01, wt.tank_water_l)
    check('M2a_status tila on low_water (<= 0.3 L)', wt.status == 'low_water', wt.status)
    check('M2a_reach tallennettu reach_s', wt.last_reach_time_s == 300.0, wt.last_reach_time_s)

    # M2b: Puoli säiliötä: 700 s -> 0.0020 * 700 - 0.40 = 1.00 L
    wt._measuring = True
    wt._measure_start_ms = utime.ticks_ms()
    utime.advance(700 * 1000)
    wt.update(ts=-1.9, now_ms=utime.ticks_ms(), mode='IDLE')
    check('M2b 700 s saavutusaika arvioi 1.00 L', abs(wt.tank_water_l - 1.00) < 0.01, wt.tank_water_l)
    check('M2b_status tila on estimated', wt.status == 'estimated', wt.status)
    check('M2b_pct prosentti on 50.0%', wt.tank_water_pct == 50.0, wt.tank_water_pct)

    # M2c: Täysi säiliö: 1200 s -> 0.0020 * 1200 - 0.40 = 2.00 L
    wt._measuring = True
    wt._measure_start_ms = utime.ticks_ms()
    utime.advance(1200 * 1000)
    wt.update(ts=-1.8, now_ms=utime.ticks_ms(), mode='IDLE')
    check('M2c 1200 s saavutusaika arvioi 2.00 L (täysi)', abs(wt.tank_water_l - 2.00) < 0.01, wt.tank_water_l)
    check('M2c_pct prosentti on 100.0%', wt.tank_water_pct == 100.0, wt.tank_water_pct)

    # M2d: Ylipitkä saavutusaika: 1500 s -> leikkautuu kapasiteettiin 2.00 L
    wt._measuring = True
    wt._measure_start_ms = utime.ticks_ms()
    utime.advance(1500 * 1000)
    wt.update(ts=-2.0, now_ms=utime.ticks_ms(), mode='IDLE')
    check('M2d 1500 s leikkautuu kapasiteettiin 2.00 L', wt.tank_water_l == 2.00, wt.tank_water_l)

    # -------------------------------------------------------------------------
    # M3: Lämpimänä käynnistys (TS > -6.0)
    # -------------------------------------------------------------------------
    wt_warm = water_tank.WaterTankTracker(utime, state_file='/tmp/test_nonexistent_tank.json')
    wt_warm.update(ts=-3.0, now_ms=utime.ticks_ms(), mode='IDLE')
    check('M3 lämmin käynnistys (TS=-3.0) asettaa warm_start eikä ala mitata',
          wt_warm.status == 'warm_start' and not wt_warm._measuring, wt_warm.status)

    # -------------------------------------------------------------------------
    # M4: Vedenkulutuksen seuranta
    # -------------------------------------------------------------------------
    wt.set_water_level(1.50)
    wt.consume_water_ml(200) # -0.20 L -> 1.30 L
    check('M4a consume_water_ml(200) vähentää 0.20 L', abs(wt.tank_water_l - 1.30) < 0.001, wt.tank_water_l)
    wt.consume_water_l(0.30) # -0.30 L -> 1.00 L
    check('M4b consume_water_l(0.30) vähentää 0.30 L', abs(wt.tank_water_l - 1.00) < 0.001, wt.tank_water_l)

    # -------------------------------------------------------------------------
    # M5: Varoitusraja (low_water)
    # -------------------------------------------------------------------------
    wt.consume_water_l(0.75) # 1.00 -> 0.25 L (< 0.30 L)
    check('M5a vesimäärä 0.25 L on alle low_water_l', wt.tank_water_l == 0.25, wt.tank_water_l)
    check('M5b status muuttuu low_water', wt.status == 'low_water', wt.status)
    wt.consume_water_l(1.0) # ei alita nollaa
    check('M5c vesimäärä ei mene negatiiviseksi', wt.tank_water_l == 0.0, wt.tank_water_l)

    # -------------------------------------------------------------------------
    # M6: Sarjakomennot
    # -------------------------------------------------------------------------
    bd = types.SimpleNamespace(
        water_tank=wt,
        utime=utime,
        is_idle=lambda: True,
        get_mode=lambda: 'IDLE'
    )

    buf = io.StringIO()
    with redirect_stdout(buf):
        commands.handle_command(bd, 'tank?')
    out = buf.getvalue().strip()
    check('M6a tank? palauttaa tilatiedot', 'TANK level=' in out and 'pct=' in out, out)

    buf = io.StringIO()
    with redirect_stdout(buf):
        commands.handle_command(bd, 'tank:fill')
    out = buf.getvalue().strip()
    check('M6b tank:fill täyttää säiliön', wt.tank_water_l == 2.0 and wt.status == 'full', out)

    buf = io.StringIO()
    with redirect_stdout(buf):
        commands.handle_command(bd, 'tank:set:1.45')
    out = buf.getvalue().strip()
    check('M6c tank:set:1.45 asettaa 1.45 L', abs(wt.tank_water_l - 1.45) < 0.01 and wt.status == 'set', out)

    buf = io.StringIO()
    with redirect_stdout(buf):
        commands.handle_command(bd, 'tank:consume:250')
    out = buf.getvalue().strip()
    check('M6d tank:consume:250 vähentää 250 ml -> 1.20 L', abs(wt.tank_water_l - 1.20) < 0.01, out)

    buf = io.StringIO()
    with redirect_stdout(buf):
        commands.handle_command(bd, 'tank:cal:0.0025:-0.50')
    out = buf.getvalue().strip()
    check('M6e tank:cal päivittää kertoimet', wt.model_a == 0.0025 and wt.model_b == -0.50, out)

    # -------------------------------------------------------------------------
    # M7: Pysyvyys (save_state ja load_state)
    # -------------------------------------------------------------------------
    wt.save_state()
    wt_reloaded = water_tank.WaterTankTracker(utime, state_file=tmp_state)
    check('M7a ladattu taso vastaa tallennettua', abs(wt_reloaded.tank_water_l - 1.20) < 0.01, wt_reloaded.tank_water_l)
    check('M7b ladattu malli a vastaa tallennettua', wt_reloaded.model_a == 0.0025, wt_reloaded.model_a)
    check('M7c ladattu malli b vastaa tallennettua', wt_reloaded.model_b == -0.50, wt_reloaded.model_b)

    # -------------------------------------------------------------------------
    # M8: Telemetria ja getterit
    # -------------------------------------------------------------------------
    class PinMock:
        IN, OUT, PULL_DOWN = 0, 1, 2
        def __init__(self, *a, **k):
            self.v = 0
        def value(self, v=None):
            if v is not None: self.v = v
            return self.v

    class SensorMock:
        def get_temperature(self):
            return 98.0
        def read_temperature(self):
            return 98.0

    import preset
    calc = classes.HeatingSpeedCalculator(utime, None)
    sensor_mock = SensorMock()
    bd_real = classes.BrewData(PinMock, None, preset.PINS, preset.TARGET_TEMPERATURES, preset.FEATURES,
                              calc, sensor_mock, None, utime)
    bd_real.water_tank = wt
    check('M8a bd.get_tank_water_l() palauttaa litrat', abs(bd_real.get_tank_water_l() - 1.20) < 0.01, bd_real.get_tank_water_l())
    check('M8b bd.get_tank_water_pct() palauttaa prosentin', bd_real.get_tank_water_pct() == 60.0, bd_real.get_tank_water_pct())
    check('M8c bd.get_tank_status() palauttaa tilan', bd_real.get_tank_status() == wt.status, bd_real.get_tank_status())

    live = bluetooth_handler.live_payload(bd_real)
    check('M8d live_payload sisältää tank_water_l', 'tank_water_l' in live and live['tank_water_l'] == 1.2, live)
    check('M8e live_payload sisältää tank_pct', 'tank_pct' in live and live['tank_pct'] == 60.0, live)
    check('M8f live_payload sisältää tank_status', 'tank_status' in live, live)

    # Testataan NOTIFY_DROP_ORDER
    check('M8g NOTIFY_DROP_ORDER sisältää tank-kentät',
          'tank_pct' in bluetooth_handler.NOTIFY_DROP_ORDER and
          'tank_status' in bluetooth_handler.NOTIFY_DROP_ORDER and
          'tank_water_l' in bluetooth_handler.NOTIFY_DROP_ORDER)

    # Testataan DIAG_MIN rivi diagnetissä
    diag_ring = diagnet.Ring(1024)
    fake_wlan = types.SimpleNamespace()
    diag = diagnet.DiagNet(None, None, utime, {'host': '127.0.0.1', 'port': 1234}, 'S', 'P', wlan=fake_wlan, boot_id='testboot')
    diag.ring = diag_ring
    diag._t_min = utime.ticks_ms()
    bd_real.relay_guard = types.SimpleNamespace(take_minute=lambda: (60000, 1000, 200, 10, 8.5, 8.0, 9.0))
    diag.minute(bd_real)
    diag_output = diag_ring.buf[:diag_ring.size].decode('utf-8')
    check('M8h DIAG_MIN sisältää tk=1.20', 'tk=1.20' in diag_output, diag_output)

    # -------------------------------------------------------------------------
    # M9: Thermostat.run -integraatio
    # -------------------------------------------------------------------------
    sensor = FakeSensor(25.0)          # kylmä kattila: cold_boot
    relay = FakeRelay()
    th = classes.Thermostat(bd_real, {}, relay, sensor, utime)
    wt.status = 'ready'
    th.run()
    check('M9z kylmä kattila merkitsee cold_boot, paikkamerkki-TS ei aloita mittausta',
          wt.cold_boot and wt.status == 'ready' and not th.ts_measured, (wt.cold_boot, wt.status))
    sensor.t = 98.0
    th.thermal_stability = -9.0
    th.ts_measured = True
    th.run()
    check('M9a Thermostat.run aloittaa mittauksen TS=-9.0 kylmästä käynnistyksestä', wt.status == 'measuring')

    utime.advance(800 * 1000)
    th.thermal_stability = -1.5 # ylittää targetin -2.0
    th.run()
    check('M9b Thermostat.run päättää mittauksen kun TS=-1.5', wt.status == 'estimated' and not wt._measuring)
    check('M9c vesimäärä arvioitu oikein Thermostat.runin kautta', wt.tank_water_l > 0.0, wt.tank_water_l)

    # -------------------------------------------------------------------------
    # B: lämmin käynnistys 30.10.2026 (boot 3308fb01): TS-paikkamerkki -10 aloitti mittauksen, ensimmäinen
    # PI-jakso antoi -1.25 -> reach 0 s -> 0.00 L low_water
    # -------------------------------------------------------------------------
    st_b = '/tmp/test_water_tank_b.json'
    for f in (st_b, st_b + '.tmp'):
        if os.path.exists(f):
            os.remove(f)
    wt_b = water_tank.WaterTankTracker(utime, state_file=st_b)
    bd_real.water_tank = wt_b
    th_b = classes.Thermostat(bd_real, {}, FakeRelay(), FakeSensor(97.5), utime)
    buf = io.StringIO()
    with redirect_stdout(buf):
        th_b.run()
        utime.advance(5000)
        th_b.run()
    check('B1a lämmin boot: paikkamerkki -10 ei aloita mittausta', 'TANK_MEASURE_START' not in buf.getvalue(), buf.getvalue())
    check('B1b lämmin boot: ensimmäinen mitattu TS -> warm_start, taso säilyy 2.0 L',
          th_b.ts_measured and wt_b.status == 'warm_start' and wt_b.tank_water_l == 2.0,
          (th_b.thermal_stability, wt_b.status, wt_b.tank_water_l))

    wt_c = water_tank.WaterTankTracker(utime, state_file='/tmp/test_nonexistent_tank.json')
    wt_c.update(ts=-9.0, now_ms=utime.ticks_ms(), mode='IDLE', cold=False, measured=True)
    check('B2 mitattu TS -9 kuumalla kattilalla (ei kylmää bootia) ei aloita mittausta',
          not wt_c._measuring and wt_c.status == 'init', wt_c.status)

    wt_c.update(ts=-9.0, now_ms=utime.ticks_ms(), mode='IDLE', cold=True, measured=True)
    utime.advance(30 * 1000)
    buf = io.StringIO()
    with redirect_stdout(buf):
        wt_c.update(ts=-1.0, now_ms=utime.ticks_ms(), mode='IDLE', cold=False, measured=True)
    check('B3 alle REACH_MIN_S saavutus hylätään, taso ja tila ennallaan',
          'TANK_REJECT' in buf.getvalue() and wt_c.tank_water_l == 2.0 and wt_c.status == 'init'
          and wt_c.last_reach_time_s is None, (buf.getvalue(), wt_c.status, wt_c.tank_water_l))

    with open(st_b, 'w') as f:
        json.dump({'tank_water_l': 0.0, 'status': 'low_water', 'last_reach_time_s': 0.0,
                   'capacity_l': 2.0, 'low_water_l': 0.3, 'model_a': 0.002, 'model_b': -0.4}, f)
    buf = io.StringIO()
    with redirect_stdout(buf):
        wt_d = water_tank.WaterTankTracker(utime, state_file=st_b)
    saved = json.load(open(st_b))
    check('B4 laitteen virheellinen tila (low_water, reach 0) nollautuu latauksessa ja tallentuu',
          'TANK_RESET_BOGUS' in buf.getvalue() and wt_d.status == 'init' and wt_d.tank_water_l == 2.0
          and saved['status'] == 'init', (wt_d.status, wt_d.tank_water_l, saved))
    for f in (st_b, st_b + '.tmp'):
        if os.path.exists(f):
            os.remove(f)

    # Siivous
    for f in (tmp_state, tmp_state + '.tmp'):
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    print('RESULT: %d failed' % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
