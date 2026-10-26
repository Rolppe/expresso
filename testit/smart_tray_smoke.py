#!/usr/bin/env python3
"""smart_tray_smoke.py — EXPRESSO-ALYKAS-PAINO (26.10.2026).

Testaa älykkään painon ja kaukalon tunnistuksen (KAYTTAJAN-TIEDOT.md §9 kohta 4):
1. Kaukaloon tulleen veden määrän tunnistus (water_g, water_pct, max 400 g)
2. Tyhjennys sammuksissa (tray_state.json vertailu käynnistyksen painoon)
3. Kupin painon (293.9 g) ja ulkoisen vaa'an (130.0 g) tunnistus kaukalolla
4. Koeastian (50.7 g) ja yhdistelmän (vaaka + kuppi ~423.9 g) tunnistus
5. Esineen läsnäollessa tapahtuva veden erottaminen esineestä
6. Kaukalon irrottaminen (<200 g -> no_tray) ja takaisinlaitto
7. Komennot (tray?, tray:empty, tray:cal_empty, tray:wmax, obj?, obj:cup, obj:scale)
8. BrewData-getterit ja bluetooth_handler.scale_payload -telemetria

    python3 testit/smart_tray_smoke.py       RESULT: 0 failed
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

import smart_tray
import classes
import commands
import bluetooth_handler


class FakeScale:
    def __init__(self, weight=454.5):
        self.w = weight
        self.drop = False

    def drop_detected(self):
        return self.drop

    def value(self):
        return self.w


class FakeUtime:
    def __init__(self):
        self._ms = 100000

    def ticks_ms(self):
        return self._ms

    def advance(self, ms):
        self._ms += ms


def main():
    fails = []

    def check(name, cond, extra=''):
        if cond:
            print('ok   %s' % name)
        else:
            fails.append(name)
            print('FAIL %s %s' % (name, ('— ' + str(extra)) if extra else ''))

    tmp_state = '/tmp/test_tray_state.json'
    if os.path.exists(tmp_state):
        os.remove(tmp_state)

    utime = FakeUtime()
    scale = FakeScale(454.5)

    # -------------------------------------------------------------------------
    # 1. Perusalustus tyhjällä kaukalolla
    # -------------------------------------------------------------------------
    tracker = smart_tray.SmartTrayTracker(scale, utime=utime, state_file=tmp_state)
    for _ in range(5):
        tracker.update(454.5, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    check('1a. Perusalustus: status == ok', tracker.status == 'ok', tracker.status)
    check('1b. Perusalustus: water_g == 0.0', tracker.water_g == 0.0, tracker.water_g)
    check('1c. Perusalustus: water_pct == 0.0', tracker.water_pct == 0.0, tracker.water_pct)
    check('1d. Perusalustus: emptied_offline == False', tracker.emptied_offline is False)
    check('1e. Perusalustus: detected_object == none', tracker.detected_object == 'none', tracker.detected_object)
    check('1f. Perusalustus: object_present == False', tracker.object_present is False)

    # -------------------------------------------------------------------------
    # 2. Veden kertyminen kaukaloon (pumppu päällä tai solenoidipurkaus)
    # -------------------------------------------------------------------------
    # Lisätään 50 g vettä
    for _ in range(4):
        tracker.update(504.5, now_ms=utime.ticks_ms(), is_idle=False, pump_on=True)
        utime.advance(86)

    check('2a. Veden lisäys 50 g: water_g ~50.0', abs(tracker.water_g - 50.0) < 0.2, tracker.water_g)
    check('2b. Veden lisäys: water_session_g ~50.0', abs(tracker.water_session_g - 50.0) < 0.2, tracker.water_session_g)
    check('2c. Veden lisäys: water_pct ~12.5%', abs(tracker.water_pct - 12.5) < 0.2, tracker.water_pct)
    check('2d. Veden lisäys: ei luulla esineeksi', tracker.detected_object == 'none', tracker.detected_object)

    # Lisätään toinen 75 g (yhteensä 125 g vettä, paino 579.5 g)
    for _ in range(4):
        tracker.update(579.5, now_ms=utime.ticks_ms(), is_idle=False, pump_on=True)
        utime.advance(86)

    check('2e. Veden kumulatiivinen lisäys: water_g ~125.0', abs(tracker.water_g - 125.0) < 0.2, tracker.water_g)
    tracker.save_state(force=True)
    check('2f. Tila tallentuu tiedostoon', os.path.exists(tmp_state))

    # -------------------------------------------------------------------------
    # 3. Kupin tunnistus kaukalolla (kuppi 293.9 g)
    # -------------------------------------------------------------------------
    # Kaukalossa on 125 g vettä (kokonaispaino 579.5 g).
    # Asetetaan kuppi 293.9 g kaukalolle lepotilassa -> paino hyppää 579.5 + 293.9 = 873.4 g
    for _ in range(5):
        tracker.update(873.4, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    check('3a. Kupin lisäys: detected_object == cup', tracker.detected_object == 'cup', tracker.detected_object)
    check('3b. Kupin lisäys: object_present == True', tracker.object_present is True)
    check('3c. Kupin lisäys: object_weight ~293.9 g', abs(tracker.object_weight - 293.9) < 0.5, tracker.object_weight)
    check('3d. Kupin lisäys: water_g EI kasva (pysyy ~125.0 g)', abs(tracker.water_g - 125.0) < 0.2, tracker.water_g)

    # Kupin poistaminen kaukalolta (paino palaa 579.5 g)
    for _ in range(5):
        tracker.update(579.5, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    check('3e. Kupin poisto: detected_object == none', tracker.detected_object == 'none', tracker.detected_object)
    check('3f. Kupin poisto: object_present == False', tracker.object_present is False)
    check('3g. Kupin poisto: water_g pysyy ~125.0 g', abs(tracker.water_g - 125.0) < 0.2, tracker.water_g)

    # -------------------------------------------------------------------------
    # 4. Ulkoisen vaa'an tunnistus kaukalolla (vaaka 130.0 g)
    # -------------------------------------------------------------------------
    # Asetetaan ulkoinen vaaka kaukalolle: 579.5 + 130.0 = 709.5 g
    for _ in range(5):
        tracker.update(709.5, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    check('4a. Ulkoisen vaa\'an lisäys: detected_object == external_scale',
          tracker.detected_object == 'external_scale', tracker.detected_object)
    check('4b. Ulkoisen vaa\'an lisäys: object_weight ~130.0 g',
          abs(tracker.object_weight - 130.0) < 0.5, tracker.object_weight)
    check('4c. Ulkoisen vaa\'an lisäys: water_g pysyy ~125.0 g',
          abs(tracker.water_g - 125.0) < 0.2, tracker.water_g)

    # Poistetaan ulkoinen vaaka
    for _ in range(5):
        tracker.update(579.5, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    check('4d. Ulkoisen vaa\'an poisto: detected_object == none', tracker.detected_object == 'none')

    # -------------------------------------------------------------------------
    # 5. Ulkoisen vaa'an ja kupin yhdistelmän tunnistus (~423.9 g)
    # -------------------------------------------------------------------------
    # 579.5 + 423.9 = 1003.4 g
    for _ in range(5):
        tracker.update(1003.4, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    check('5a. Vaaka + kuppi -yhdistelmä: detected_object == scale_and_cup',
          tracker.detected_object == 'scale_and_cup', tracker.detected_object)
    check('5b. Vaaka + kuppi -yhdistelmä: water_g pysyy ~125.0 g',
          abs(tracker.water_g - 125.0) < 0.2, tracker.water_g)

    # Poisto
    for _ in range(5):
        tracker.update(579.5, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)
    check('5c. Yhdistelmän poisto: detected_object == none', tracker.detected_object == 'none')

    # -------------------------------------------------------------------------
    # 6. Koeastian tunnistus (50.7 g)
    # -------------------------------------------------------------------------
    # 579.5 + 50.7 = 630.2 g
    for _ in range(5):
        tracker.update(630.2, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    check('6a. Koeastia: detected_object == test_vessel',
          tracker.detected_object == 'test_vessel', tracker.detected_object)
    check('6b. Koeastia: water_g pysyy ~125.0 g', abs(tracker.water_g - 125.0) < 0.2, tracker.water_g)

    # Poisto
    for _ in range(5):
        tracker.update(579.5, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    # -------------------------------------------------------------------------
    # 7. Kaukalon tyhjennys sammuksissa (Offline emptying detection)
    # -------------------------------------------------------------------------
    # Tallennetaan nykytila: kaukalossa on 125 g vettä, kokonaispaino 579.5 g
    tracker.save_state(force=True)

    # Simuloidaan koneen sammutus ja kaukalon tyhjennys sammuksissa:
    # Uusi käynnistys puhtaalla tyhjällä kaukalolla (454.5 g)
    tracker_reboot = smart_tray.SmartTrayTracker(scale, utime=utime, state_file=tmp_state)
    for _ in range(5):
        tracker_reboot.update(454.5, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    check('7a. Sammuksissa tyhjennys: emptied_offline == True', tracker_reboot.emptied_offline is True)
    check('7b. Sammuksissa tyhjennys: status == emptied_offline', tracker_reboot.status == 'emptied_offline', tracker_reboot.status)
    check('7c. Sammuksissa tyhjennys: water_g resetoitunut ~0.0 g', tracker_reboot.water_g < 0.2, tracker_reboot.water_g)

    # Simuloidaan toinen käynnistys, jossa kaukaloa EI tyhjennetty sammuksissa:
    # Tallennetaan 125 g vettä
    tracker.save_state(force=True)
    tracker_no_empty = smart_tray.SmartTrayTracker(scale, utime=utime, state_file=tmp_state)
    for _ in range(5):
        tracker_no_empty.update(579.5, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)

    check('7d. Ei tyhjennetty sammuksissa: emptied_offline == False', tracker_no_empty.emptied_offline is False)
    check('7e. Ei tyhjennetty sammuksissa: water_g säilyy ~125.0 g', abs(tracker_no_empty.water_g - 125.0) < 0.2, tracker_no_empty.water_g)
    check('7f. Ei tyhjennetty sammuksissa: status == ok', tracker_no_empty.status == 'ok', tracker_no_empty.status)

    # -------------------------------------------------------------------------
    # 8. Kaukalon täyttörajat (ok, warning_full, full)
    # -------------------------------------------------------------------------
    # 360 g vettä -> warning_full (>350 g)
    for _ in range(5):
        tracker_no_empty.update(454.5 + 360.0, now_ms=utime.ticks_ms(), is_idle=False, pump_on=True)
        utime.advance(86)
    check('8a. 360 g vettä: status == warning_full', tracker_no_empty.status == 'warning_full', tracker_no_empty.status)
    check('8b. 360 g vettä: water_pct == 90%', abs(tracker_no_empty.water_pct - 90.0) < 0.2, tracker_no_empty.water_pct)

    # 410 g vettä -> full (>400 g)
    for _ in range(5):
        tracker_no_empty.update(454.5 + 410.0, now_ms=utime.ticks_ms(), is_idle=False, pump_on=True)
        utime.advance(86)
    check('8c. 410 g vettä: status == full', tracker_no_empty.status == 'full', tracker_no_empty.status)

    # -------------------------------------------------------------------------
    # 9. Kaukalon poisto (<200 g)
    # -------------------------------------------------------------------------
    for _ in range(3):
        tracker_no_empty.update(10.0, now_ms=utime.ticks_ms(), is_idle=True, pump_on=False)
        utime.advance(86)
    check('9a. Kaukalo poistettu: status == no_tray', tracker_no_empty.status == 'no_tray', tracker_no_empty.status)
    check('9b. Kaukalo poistettu: object_present == False', tracker_no_empty.object_present is False)

    # -------------------------------------------------------------------------
    # 10. BrewData-integraatio ja getterit
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
            return 93.0

    class UtimeMock:
        @staticmethod
        def ticks_ms(): return 1000
        @staticmethod
        def ticks_diff(a, b): return a - b
        @staticmethod
        def ticks_us(): return 1000000

    import preset
    calc = classes.HeatingSpeedCalculator(UtimeMock, None)
    sensor = SensorMock()
    bd = classes.BrewData(PinMock, None, preset.PINS, preset.TARGET_TEMPERATURES, preset.FEATURES,
                          calc, sensor, None, UtimeMock)
    bd.tray_scale = scale
    bd.smart_tray = tracker_reboot
    bd.weight = 454.5

    check('10a. bd.get_tray_water_g()', bd.get_tray_water_g() == tracker_reboot.water_g)
    check('10b. bd.get_tray_water_pct()', bd.get_tray_water_pct() == tracker_reboot.water_pct)
    check('10c. bd.get_tray_status()', bd.get_tray_status() == tracker_reboot.status)
    check('10d. bd.get_detected_object()', bd.get_detected_object() == tracker_reboot.detected_object)
    check('10e. bd.is_tray_emptied_offline()', bd.is_tray_emptied_offline() == tracker_reboot.emptied_offline)

    # -------------------------------------------------------------------------
    # 11. bluetooth_handler.scale_payload -telemetria
    # -------------------------------------------------------------------------
    sp = bluetooth_handler.scale_payload(bd)
    check('11a. scale_payload ei ole None', sp is not None)
    check('11b. scale_payload sisältää tray_water_g', 'tray_water_g' in sp, sp)
    check('11c. scale_payload sisältää tray_pct', 'tray_pct' in sp, sp)
    check('11d. scale_payload sisältää tray_status', 'tray_status' in sp, sp)
    check('11e. scale_payload sisältää detected_object', 'detected_object' in sp, sp)

    # -------------------------------------------------------------------------
    # 12. Komennot (tray?, tray:empty, tray:cal_empty, tray:wmax, obj?, obj:cup, obj:scale)
    # -------------------------------------------------------------------------
    def run_cmd(c):
        buf = io.StringIO()
        with redirect_stdout(buf):
            commands.handle_command(bd, c)
        return buf.getvalue().strip()

    out_tray_q = run_cmd('tray?')
    check('12a. cmd tray?', 'TRAY status=' in out_tray_q, out_tray_q)

    out_obj_q = run_cmd('obj?')
    check('12b. cmd obj?', 'OBJ detected=' in out_obj_q, out_obj_q)

    out_cup = run_cmd('obj:cup:305.5')
    check('12c. cmd obj:cup:305.5 -> OBJ_SET ok', 'OBJ_SET ok cup=305.5' in out_cup, out_cup)
    check('12d. tracker cup_g päivittyi', tracker_reboot.cup_g == 305.5)

    out_scale = run_cmd('obj:scale:145.0')
    check('12e. cmd obj:scale:145.0 -> OBJ_SET ok', 'OBJ_SET ok scale=145.0' in out_scale, out_scale)
    check('12f. tracker scale_g päivittyi', tracker_reboot.scale_g == 145.0)

    out_wmax = run_cmd('tray:wmax:450')
    check('12g. cmd tray:wmax:450 -> TRAY_WMAX ok', 'TRAY_WMAX ok max=450.0' in out_wmax, out_wmax)
    check('12h. tracker max_water_g päivittyi', tracker_reboot.max_water_g == 450.0)

    out_cal_empty = run_cmd('tray:cal_empty')
    check('12i. cmd tray:cal_empty -> TRAY_CAL_EMPTY ok', 'TRAY_CAL_EMPTY ok' in out_cal_empty, out_cal_empty)

    out_empty = run_cmd('tray:empty')
    check('12j. cmd tray:empty -> TRAY_EMPTY ok', 'TRAY_EMPTY ok' in out_empty, out_empty)
    check('12k. water_g nollautui', tracker_reboot.water_g == 0.0)

    # Siivotaan tmp-tiedosto
    if os.path.exists(tmp_state):
        os.remove(tmp_state)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
