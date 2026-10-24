#!/usr/bin/env python3
"""paine_tasaus_smoke.py — Paineen tasaus IDLE-tilassa ja alkulämmityksessä.

Käyttäjävaatimus:
"keittimen ollessa alku lämmitysvaiheessa tai iddle tilassa ja paineen erotessa 0 bar tilasta +- 0.5 bar
painetta tasataan. paineen tasaus tapahtuu 30s välein avaamalla solenoidi -> odotetaan 100ms -> suljetaan solenoidi."
"""

import asyncio
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.environ.get('FW') or os.path.join(HERE, '..', 'pico')
sys.path.insert(0, FW)

clock = [1000]     # ms
utime_mod = types.ModuleType('utime')
utime_mod.ticks_ms = lambda: clock[0]
utime_mod.ticks_diff = lambda a, b: a - b
utime_mod.ticks_add = lambda a, b: a + b
utime_mod.sleep_ms = lambda ms: clock.__setitem__(0, clock[0] + ms)
sys.modules['utime'] = utime_mod

import classes as C
import commands as CMD
import preset

FAILED = []


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info else ''))
    if not ok:
        FAILED.append(name)


class PinMock:
    IN, OUT, PULL_DOWN = 0, 1, 2

    def __init__(self, pin_num=0, mode=None, pull=None, value=0):
        self.pin_num = pin_num
        self.v = value
        self.history = []

    def value(self, x=None):
        if x is None:
            return self.v
        val = 1 if x else 0
        self.v = val
        self.history.append((clock[0], val))


class AsyncioMock:
    @staticmethod
    async def sleep_ms(ms):
        clock[0] += ms


def make_bd():
    bd = C.BrewData(PinMock, None, preset.PINS, preset.TARGET_TEMPERATURES, preset.FEATURES,
                    None, None, None, utime_mod)
    bd.mode = 'IDLE'
    bd.pressure = 0.0
    return bd


# ---- TESTIT ----

# 1. Paine 0.0 bar: ei tasausta
bd = make_bd()
bd.pressure = 0.0
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('1. paine 0.0 bar: ei tasausta', res is False and bd.RELAY_SOLENOID.value() == 0)

# 2. Paine 0.4 bar: ei tasausta (|p| < 0.5)
bd.pressure = 0.4
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('2. paine +0.4 bar: ei tasausta', res is False and bd.RELAY_SOLENOID.value() == 0)

# 3. Paine -0.4 bar: ei tasausta (|p| < 0.5)
bd.pressure = -0.4
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('3. paine -0.4 bar: ei tasausta', res is False and bd.RELAY_SOLENOID.value() == 0)

# 4. Paine +0.5 bar: tasaus aktivoituu, solenoidi käy päällä 100 ms ja sulkeutuu
bd.pressure = 0.5
t_start = clock[0]
bd.RELAY_SOLENOID.history.clear()
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('4. paine +0.5 bar: tasaus suoritettu', res is True)
check('4b. solenoidi suljettu toimenpiteen jälkeen', bd.RELAY_SOLENOID.value() == 0)
check('4c. solenoidi oli päällä 100 ms', len(bd.RELAY_SOLENOID.history) >= 2 and
      bd.RELAY_SOLENOID.history[-2][1] == 1 and bd.RELAY_SOLENOID.history[-1][1] == 0 and
      (clock[0] - t_start) == 100)

# 5. Paine -0.5 bar: tasaus aktivoituu
bd = make_bd()
clock[0] = 50000
bd.pressure = -0.5
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('5. paine -0.5 bar: alipaineen tasaus suoritettu', res is True and bd.RELAY_SOLENOID.value() == 0)

# 6. Paine 1.2 bar: tasaus aktivoituu
clock[0] += 35000
bd.pressure = 1.2
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('6. paine 1.2 bar: tasaus suoritettu', res is True and bd.RELAY_SOLENOID.value() == 0)

# 7. 30 s aikaväli:
# Edellinen tasaus tehtiin hetkellä t = 85100 ms.
# 5 s myöhemmin (t = 90100):
clock[0] = 90100
bd.pressure = 0.8
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('7a. 5 s edellisestä (p=0.8): ei tasausta ennen 30 s', res is False)

# 29 s myöhemmin (t = 114100):
clock[0] = 114100
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('7b. 29 s edellisestä: ei tasausta', res is False)

# 30.1 s myöhemmin (t = 115201):
clock[0] = 115201
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('7c. 30 s kuluttua: tasaus sallittu ja suoritettu', res is True)

# 8. Alkulämmitystila ('fast_heatup'): tasaus toimii
clock[0] += 35000
bd.mode = 'fast_heatup'
bd.pressure = 0.7
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('8. alkulämmitystila (fast_heatup, p=0.7): tasaus suoritettu', res is True)

# 9. Höyrytystilassa (STEAM): EI saa tasata painetta!
clock[0] += 35000
bd.mode = 'STEAM'
bd.pressure = 2.0
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('9. STEAM-tila: EI tasausta', res is False and bd.RELAY_SOLENOID.value() == 0)

# 10. Uuttotilassa (BREW): EI saa tasata painetta!
clock[0] += 35000
bd.mode = 'BREW'
bd.pressure = 9.0
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('10. BREW-tila: EI tasausta', res is False and bd.RELAY_SOLENOID.value() == 0)

# 11. Kuumavesitilassa (WATER): EI saa tasata painetta!
clock[0] += 35000
bd.mode = 'WATER'
bd.pressure = 1.0
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('11. WATER-tila: EI tasausta', res is False and bd.RELAY_SOLENOID.value() == 0)

# 12. Kytkimet päällä:
bd.mode = 'IDLE'
clock[0] += 35000
bd.pressure = 0.9

bd.SWITCH_BREW.value(1)
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('12a. SWITCH_BREW päällä: ei tasausta', res is False)
bd.SWITCH_BREW.value(0)

bd.SWITCH_WATER.value(1)
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('12b. SWITCH_WATER päällä: ei tasausta', res is False)
bd.SWITCH_WATER.value(0)

bd.SWITCH_STEAM.value(1)
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('12c. SWITCH_STEAM päällä: ei tasausta', res is False)
bd.SWITCH_STEAM.value(0)

# 13. Pumppu päällä:
bd.RELAY_PUMP.value(1)
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('13. RELAY_PUMP päällä: ei tasausta', res is False)
bd.RELAY_PUMP.value(0)

# 14. dev_safe päällä:
bd.dev_safe = True
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('14. dev_safe päällä: ei tasausta', res is False)
bd.dev_safe = False

# 15. PEQ?-komento:
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    CMD.handle_command(bd, 'peq?')

peq_out = buf.getvalue()
check('15. CMD peq? vastaa', 'PEQ enabled=1' in peq_out and 'th=0.5' in peq_out, peq_out.strip())

# 16. Lämpötilaraja: Ei tasata jos lämpötila on >= 0.1 °C YLI tavoitelämpötilan
bd.set_brew_temperature(98.0)
bd.mode = 'IDLE'
bd.pressure = 0.8

# 16a: T = 98.0 C (tasan tavoite, ero 0.0) -> sallittu
clock[0] += 35000
bd.boiler_temperature = 98.0
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('16a. T=98.0 C (target 98.0): tasaus sallittu', res is True)

# 16b: T = 50.0 C (kylmä alkulämmitys) -> sallittu
clock[0] += 35000
bd.boiler_temperature = 50.0
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('16b. T=50.0 C (kylmä alkulämmitys): tasaus sallittu', res is True)

# 16c: T = 98.05 C (< 0.1 C yli) -> sallittu
clock[0] += 35000
bd.boiler_temperature = 98.05
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('16c. T=98.05 C (< 0.1 C yli): tasaus sallittu', res is True)

# 16d: T = 98.10 C (tasan 0.1 C yli) -> EI SAA TASATA
clock[0] += 35000
bd.boiler_temperature = 98.10
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('16d. T=98.10 C (0.1 C yli): EI SAA TASATA', res is False and bd.RELAY_SOLENOID.value() == 0)

# 16e: T = 99.0 C (1.0 C yli) -> EI SAA TASATA
clock[0] += 35000
bd.boiler_temperature = 99.0
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('16e. T=99.0 C (1.0 C yli): EI SAA TASATA', res is False and bd.RELAY_SOLENOID.value() == 0)

# 16f: T = 104.5 C (jäähtymässä höyrytyksestä) -> EI SAA TASATA
clock[0] += 35000
bd.boiler_temperature = 104.5
res = asyncio.run(bd.check_pressure_equalization(clock[0], AsyncioMock))
check('16f. T=104.5 C (höyrytyksen jälkeen jäähtymässä): EI SAA TASATA', res is False and bd.RELAY_SOLENOID.value() == 0)

print('RESULT: %d failed' % len(FAILED))
sys.exit(1 if FAILED else 0)
