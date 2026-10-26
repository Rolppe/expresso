#!/usr/bin/env python3
"""lampotilatilat_smoke.py — Keittimen lämpötilatilat (EXPRESSO-LAMPOTILATILAT, 26.10.2026).

Vaatimus (KAYTTAJAN-TIEDOT.md §9, kohta 2):
"keittimen tila iddle kuuluu olla vasta silloin päällä kun oikea lämpötila on suurinpiirtein
asettunut kohdilleen. Jos lämpötila ob viellä heilahtelu vaiheessa se kuuluu olla stabilizing.
Jos se on reilusti alle niin warming up. Jos se on yli se on cooling down."

Testaa:
1. warming up: reilusti alle tavoitteen (> 2.0 C alle tavoitteen)
2. stabilizing: heilahteluvaiheessa (-2.0 C ... +0.5 C ennen asettumisaikaa tai nopeuden ollessa suuri)
3. IDLE: asettunut kohdalleen (+-0.5 C kaistalla >= 10 s ilman heilahtelua)
4. cooling down: yli tavoitteen (> 0.5 C yli tavoitteen, esim. höyrytyksen tai yliampuman jälkeen)
5. Siirtymät: tavoitteen muutos (valmiustila / herätys), aktiivisten tilojen koskemattomuus (BREW, STEAM, WATER)
6. set_mode('IDLE') reititys ja is_idle() apumetodi
7. Telemetria: live_payload välittää tilan oikein
"""

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.environ.get('FW') or os.path.join(HERE, '..', 'pico')
sys.path.insert(0, FW)
sys.modules.setdefault('utime', types.ModuleType('utime'))

bluetooth = types.ModuleType('bluetooth')
bluetooth.UUID = lambda x: x
bluetooth.FLAG_READ = 1; bluetooth.FLAG_NOTIFY = 2; bluetooth.FLAG_WRITE = 4
sys.modules['bluetooth'] = bluetooth
mp = types.ModuleType('micropython'); mp.const = lambda x: x
sys.modules['micropython'] = mp

import classes as C
import preset
import bluetooth_handler

FAILED = []
clock = [0]


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info else ''))
    if not ok:
        FAILED.append(name)


class UtimeMock:
    @staticmethod
    def ticks_ms():
        return clock[0]

    @staticmethod
    def ticks_diff(a, b):
        return a - b

    @staticmethod
    def ticks_add(a, b):
        return a + b


class PinMock:
    IN, OUT, PULL_DOWN = 0, 1, 2

    def __init__(self, pin_num=0, mode=None, pull=None, value=0):
        self.v = value

    def value(self, x=None):
        if x is None:
            return self.v
        self.v = 1 if x else 0


class SensorMock:
    def __init__(self, t=20.0):
        self.t = t

    def read_temperature(self):
        return self.t

    def c1_active(self):
        return False


def make_bd(t=20.0, target=98.0):
    clock[0] = 1000
    sensor = SensorMock(t)
    calc = C.HeatingSpeedCalculator(UtimeMock, None)
    bd = C.BrewData(PinMock, None, preset.PINS, preset.TARGET_TEMPERATURES, preset.FEATURES,
                    calc, sensor, None, UtimeMock)
    bd.brew_temperature = target
    bd.boiler_temperature = t
    bd.mode = 'IDLE'
    return bd, sensor, calc


# ============================================================================
# 1. WARMING UP: reilusti alle tavoitteen (> 2.0 C alle)
# ============================================================================
bd, sensor, calc = make_bd(t=20.0, target=98.0)
m = bd.update_temperature_mode(clock[0])
check('1a. Kylmäkäynnistys T=20 C (target 98): warming up', m == 'warming up', m)

sensor.t = 50.0; bd.boiler_temperature = 50.0
check('1b. T=50 C: warming up', bd.update_temperature_mode(clock[0]) == 'warming up', bd.mode)

sensor.t = 90.0; bd.boiler_temperature = 90.0
check('1c. T=90 C: warming up', bd.update_temperature_mode(clock[0]) == 'warming up', bd.mode)

sensor.t = 95.9; bd.boiler_temperature = 95.9
check('1d. T=95.9 C (> 2.0 C alle): warming up', bd.update_temperature_mode(clock[0]) == 'warming up', bd.mode)


# ============================================================================
# 2. STABILIZING: lämpötila lähestyy tavoitetta tai heilahtelee
# ============================================================================
# 96.5 C (1.5 C alle, lähestymisalueella)
sensor.t = 96.5; bd.boiler_temperature = 96.5
m = bd.update_temperature_mode(clock[0])
check('2a. T=96.5 C (1.5 C alle): stabilizing', m == 'stabilizing', m)

sensor.t = 97.2; bd.boiler_temperature = 97.2
check('2b. T=97.2 C (0.8 C alle): stabilizing', bd.update_temperature_mode(clock[0]) == 'stabilizing', bd.mode)

# Lämpötila saapuu tavoitekaistalle +-0.5 C (esim. 97.8 C), mutta ei ole vielä asettunut (t < 10 s)
sensor.t = 97.8; bd.boiler_temperature = 97.8
clock[0] = 5000
m = bd.update_temperature_mode(clock[0])
check('2c. T=97.8 C t=0s kaistalla: stabilizing', m == 'stabilizing', m)

clock[0] = 9000  # 4 s kaistalla
check('2d. T=98.0 C t=4s (< 10s): stabilizing', bd.update_temperature_mode(clock[0]) == 'stabilizing', bd.mode)

# Suuri lämmitysnopeus estää IDLE-tilaan siirtymisen vaikka T=98.0 ja aika täyttyisi
clock[0] = 16000 # 11 s kaistalla
bd.heating_speed = 1.2  # nopeus liian suuri (> 0.5)
check('2e. T=98.0 C t=11s mutta nopeus suuri (1.2): stabilizing', bd.update_temperature_mode(clock[0]) == 'stabilizing', bd.mode)


# ============================================================================
# 3. IDLE: asettunut kohdilleen (kaistalla >= 10 s, nopeus vakaa)
# ============================================================================
bd.heating_speed = 0.1
clock[0] = 16000 # t=11 s, nopeus pieni
m = bd.update_temperature_mode(clock[0])
check('3a. T=98.0 C t=11s ja nopeus pieni (0.1): IDLE', m == 'IDLE', m)

# Pysyy IDLEssä kaistalla
sensor.t = 98.1; bd.boiler_temperature = 98.1
clock[0] = 20000
check('3b. T=98.1 C: pysyy IDLE', bd.update_temperature_mode(clock[0]) == 'IDLE', bd.mode)

sensor.t = 97.7; bd.boiler_temperature = 97.7
clock[0] = 25000
check('3c. T=97.7 C: pysyy IDLE', bd.update_temperature_mode(clock[0]) == 'IDLE', bd.mode)

# Hystereesi: 0.55 C poikkeama ei heti pudota pois IDLEstä jos nopeus pieni
sensor.t = 98.55; bd.boiler_temperature = 98.55
check('3d. T=98.55 C (hystereesi <= 0.6): pysyy IDLE', bd.update_temperature_mode(clock[0]) == 'IDLE', bd.mode)


# ============================================================================
# 4. COOLING DOWN: yli tavoitteen (> 0.5 C yli)
# ============================================================================
# Yliampuma > 0.5 C (98.65 C)
sensor.t = 98.65; bd.boiler_temperature = 98.65
m = bd.update_temperature_mode(clock[0])
check('4a. T=98.65 C (> 0.5 C yli): cooling down', m == 'cooling down', m)

sensor.t = 102.0; bd.boiler_temperature = 102.0
check('4b. T=102.0 C: cooling down', bd.update_temperature_mode(clock[0]) == 'cooling down', bd.mode)

# Höyrytyksen jälkeen
sensor.t = 135.0; bd.boiler_temperature = 135.0
check('4c. T=135.0 C (höyryn jälkeen): cooling down', bd.update_temperature_mode(clock[0]) == 'cooling down', bd.mode)

# Jäähtyy takaisin: 135 -> 99 -> 98.4 -> 98.0
sensor.t = 99.0; bd.boiler_temperature = 99.0
check('4d. Jäähtyy T=99.0 C: cooling down', bd.update_temperature_mode(clock[0]) == 'cooling down', bd.mode)

# Saapuu tavoitekaistalle jäähtyessään (98.4 C) -> stabilizing
sensor.t = 98.4; bd.boiler_temperature = 98.4
clock[0] = 50000
m = bd.update_temperature_mode(clock[0])
check('4e. Jäähtynyt T=98.4 C kaistalle: stabilizing', m == 'stabilizing', m)

# 10 s kaistalla jäähtymisen jälkeen -> IDLE
clock[0] = 61000
sensor.t = 98.02; bd.boiler_temperature = 98.02
bd.heating_speed = -0.05
m = bd.update_temperature_mode(clock[0])
check('4f. 11 s kaistalla jäähtymisen jälkeen: IDLE', m == 'IDLE', m)


# ============================================================================
# 5. SIIRTYMÄT JA TAVOITTEEN MUUTOS
# ============================================================================
# Valmiustilaan siirtyminen: tavoite muuttuu 98 -> 90 C
bd.standby = True
bd.standby_temperature = 90.0
# Nyt T=98.0, tavoite=90.0 -> diff = +8.0 C -> cooling down!
m = bd.update_temperature_mode(clock[0])
check('5a. Valmiustilaan siirtyminen (T=98, target=90): cooling down', m == 'cooling down', m)

# Jäähtyy 90.2 C:een valmiustilassa
sensor.t = 90.2; bd.boiler_temperature = 90.2
clock[0] = 80000
bd.update_temperature_mode(clock[0])
clock[0] = 92000
bd.heating_speed = 0.0
check('5b. Valmiustilassa asettunut 90 C: IDLE', bd.update_temperature_mode(clock[0]) == 'IDLE', bd.mode)

# Herätys valmiustilasta: tavoite muuttuu 90 -> 98 C
bd.standby = False
# Nyt T=90.2, tavoite=98.0 -> diff = -7.8 C -> warming up!
m = bd.update_temperature_mode(clock[0])
check('5c. Herätys valmiustilasta (T=90, target=98): warming up', m == 'warming up', m)


# ============================================================================
# 6. AKTIIVISET TILAT JA SET_MODE
# ============================================================================
bd.set_mode('BREW')
check('6a. BREW-tila pysyy koskemattomana', bd.update_temperature_mode(clock[0]) == 'BREW' and bd.mode == 'BREW')

bd.set_mode('STEAM')
check('6b. STEAM-tila pysyy koskemattomana', bd.update_temperature_mode(clock[0]) == 'STEAM' and bd.mode == 'STEAM')

bd.set_mode('WATER')
check('6c. WATER-tila pysyy koskemattomana', bd.update_temperature_mode(clock[0]) == 'WATER' and bd.mode == 'WATER')

bd.set_mode('DEV_SAFE')
check('6d. DEV_SAFE pysyy koskemattomana', bd.update_temperature_mode(clock[0]) == 'DEV_SAFE' and bd.mode == 'DEV_SAFE')

# set_mode('IDLE') reitittää lämpötilatilaan
sensor.t = 25.0; bd.boiler_temperature = 25.0
bd.set_mode('IDLE')
check('6e. set_mode(IDLE) kylmällä (25 C): warming up', bd.mode == 'warming up', bd.mode)

sensor.t = 120.0; bd.boiler_temperature = 120.0
bd.set_mode('IDLE')
check('6f. set_mode(IDLE) kuumalla (120 C): cooling down', bd.mode == 'cooling down', bd.mode)


# ============================================================================
# 7. IS_IDLE JA TELEMETRIA
# ============================================================================
for st in ('IDLE', 'warming up', 'stabilizing', 'cooling down'):
    bd.mode = st
    check('7a. is_idle() on True tilassa %s' % st, bd.is_idle() is True)

for st in ('BREW', 'STEAM', 'WATER', 'DEV_SAFE', 'pre-infusion main'):
    bd.mode = st
    check('7b. is_idle() on False aktiivisessa tilassa %s' % st, bd.is_idle() is False)

# Telemetria: live_payload välittää tilan sellaisenaan
bd.mode = 'stabilizing'
live = bluetooth_handler.live_payload(bd)
check('7c. live_payload mode: stabilizing', live['mode'] == 'stabilizing', live.get('mode'))

bd.mode = 'warming up'
live = bluetooth_handler.live_payload(bd)
check('7d. live_payload mode: warming up', live['mode'] == 'warming up', live.get('mode'))

bd.mode = 'cooling down'
live = bluetooth_handler.live_payload(bd)
check('7e. live_payload mode: cooling down', live['mode'] == 'cooling down', live.get('mode'))

bd.mode = 'IDLE'
live = bluetooth_handler.live_payload(bd)
check('7f. live_payload mode: IDLE', live['mode'] == 'IDLE', live.get('mode'))

print('RESULT: %d failed' % len(FAILED))
if FAILED:
    sys.exit(1)
