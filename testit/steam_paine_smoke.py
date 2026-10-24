#!/usr/bin/env python3
"""steam_paine_smoke.py — Höyrytystilan paineohjauksen ja venttiiliavauksen tiputustunnistuksen testaus.

Käyttäjävaatimus:
- Höyrytystilassa paine tippuu kun höyryventtiili avataan.
- Keittimen lämmitin pitää heti saada päälle kun paine alkaa tippua (tiputus eri ominaisuutena).
- Turvaraja: lämmitin EI saa olla päällä jos lämpötila ylittää tavoiterajan 0.5 °C.
- Venttiilin avauksesta johtuvan paineentiputuksen korjausliike pitää loppua kun venttiili suljetaan ja paine nousee.
- Säädettävä paineen alaraja ja yläraja höyrytystilassa.
"""

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.environ.get('FW') or os.path.join(HERE, '..', 'pico')
sys.path.insert(0, FW)
utime_mod = types.ModuleType('utime')
utime_mod.ticks_ms = lambda: clock[0]
utime_mod.ticks_diff = lambda a, b: a - b
utime_mod.ticks_add = lambda a, b: a + b
sys.modules['utime'] = utime_mod
import classes as C
import commands as CMD

FAILED = []
clock = [0]


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info else ''))
    if not ok:
        FAILED.append(name)


class U:
    ticks_ms = staticmethod(lambda: clock[0])
    ticks_diff = staticmethod(lambda a, b: a - b)
    ticks_add = staticmethod(lambda a, b: a + b)


class Relay:
    def __init__(self):
        self.v = 0
        self.writes = 0

    def value(self, x=None):
        if x is None:
            return self.v
        self.v = 1 if x else 0
        self.writes += 1


class Sensor:
    def __init__(self, t=135.0):
        self.t = t

    def read_temperature(self):
        return self.t


class MockBD:
    def __init__(self, mode='STEAM', target=135.0, temp=135.0, p=2.2):
        self.mode = mode
        self.steam_temperature = target
        self.steam_temperature_max = 140.0
        self.target_temperature = target
        self.boiler_temperature = temp
        self.pressure = p
        self.steam_valve_trigger = 1.8
        self.steam_valve_release = 2.1
        self.steam_pressure_high = 2.5
        self.setting_changed = False
        self.bh_steam_t = None
        self.bh_arm = 0

    def note_activity(self, now, source):
        pass

    def get_mode(self):
        return self.mode

    def get_target_temperature(self):
        return self.steam_temperature

    def get_steam_temperature(self):
        return self.steam_temperature

    def get_steam_temperature_max(self):
        return self.steam_temperature_max

    def set_steam_temperature_max(self, t):
        self.steam_temperature_max = min(145.0, max(120.0, round(float(t), 1)))
        if self.steam_temperature_max < self.steam_temperature:
            self.steam_temperature_max = self.steam_temperature
        self.setting_changed = True

    def get_heating_speed(self):
        return 0.0

    @property
    def steam_pressure_low(self):
        return self.steam_valve_trigger

    @steam_pressure_low.setter
    def steam_pressure_low(self, p):
        self.set_steam_valve_trigger(p)

    def get_steam_valve_trigger(self):
        return self.steam_valve_trigger

    def set_steam_valve_trigger(self, p):
        self.steam_valve_trigger = min(3.0, max(0.5, round(float(p), 1)))
        if self.steam_valve_trigger > self.steam_valve_release:
            self.steam_valve_release = self.steam_valve_trigger
        if self.steam_valve_trigger > self.steam_pressure_high:
            self.steam_pressure_high = self.steam_valve_trigger
        self.setting_changed = True

    def get_steam_pressure_low(self):
        return self.get_steam_valve_trigger()

    def set_steam_pressure_low(self, p):
        self.set_steam_valve_trigger(p)

    def get_steam_valve_release(self):
        return self.steam_valve_release

    def set_steam_valve_release(self, p):
        self.steam_valve_release = min(3.2, max(0.6, round(float(p), 1)))
        if self.steam_valve_release < self.steam_valve_trigger:
            self.steam_valve_trigger = self.steam_valve_release
        if self.steam_valve_release > self.steam_pressure_high:
            self.steam_pressure_high = self.steam_valve_release
        self.setting_changed = True

    def get_steam_pressure_high(self):
        return self.steam_pressure_high

    def set_steam_pressure_high(self, p):
        self.steam_pressure_high = min(3.5, max(1.0, round(float(p), 1)))
        if self.steam_pressure_high < self.steam_valve_release:
            self.steam_valve_release = self.steam_pressure_high
        if self.steam_pressure_high < self.steam_valve_trigger:
            self.steam_valve_trigger = self.steam_pressure_high
        self.setting_changed = True


def test_pressure_settings():
    bd = MockBD()
    bd.set_steam_valve_trigger(1.2)
    check('P1 steam_valve_trigger asetettu', bd.steam_valve_trigger == 1.2, bd.steam_valve_trigger)
    bd.set_steam_valve_release(2.2)
    check('P2 steam_valve_release asetettu', bd.steam_valve_release == 2.2, bd.steam_valve_release)
    bd.set_steam_pressure_high(2.8)
    check('P3 steam_pressure_high asetettu', bd.steam_pressure_high == 2.8, bd.steam_pressure_high)
    bd.set_steam_valve_trigger(3.2) # clamps to 3.0, bumps release & high to 3.0
    check('P4 trigger ylärajaus ja trigger<=release<=high', bd.steam_valve_trigger == 3.0 and bd.steam_valve_release == 3.0 and bd.steam_pressure_high == 3.0)
    bd.set_steam_temperature_max(142.0)
    check('P5 steam_temperature_max asetettu', bd.steam_temperature_max == 142.0)

    # Command handling
    bd = MockBD()
    CMD.handle_command(bd, 'svt:1.6')
    check('P6 CMD svt:1.6 päivittää', bd.steam_valve_trigger == 1.6)
    CMD.handle_command(bd, 'spl:1.5')
    check('P7 CMD spl:1.5 päivittää (alias)', bd.steam_valve_trigger == 1.5)
    CMD.handle_command(bd, 'svr:2.3')
    check('P8 CMD svr:2.3 päivittää', bd.steam_valve_release == 2.3)
    CMD.handle_command(bd, 'sph:2.6')
    check('P9 CMD sph:2.6 päivittää', bd.steam_pressure_high == 2.6)
    CMD.handle_command(bd, 'stmax:139.5')
    check('P10 CMD stmax:139.5 päivittää', bd.steam_temperature_max == 139.5)


def test_valve_open_and_close():
    clock[0] = 1000
    bd = MockBD(mode='STEAM', target=135.0, temp=134.8, p=2.4)
    bd.steam_valve_trigger = 1.8
    bd.steam_valve_release = 2.1
    sensor = Sensor(134.8)
    relay = Relay()
    th = C.Thermostat(bd, {}, relay, sensor, U)

    # 1. Steady idle: pressure 2.4, temp 134.8 (near target), p > trigger
    th.run()
    check('V1 lepotila höyrytystilassa: ei boostia lepotilassa', not th.steam_boost)

    # 2. Venttiili avataan: paine tippuu 2.4 -> 2.1 ja 1.9 bar (vielä yli trigger 1.8)
    # Ei saa käynnistää boostia ennen kuin trigger-raja alitetaan
    bd.pressure = 2.1
    th.run()
    check('V2 paine yli triggerin (2.1 > 1.8): ei boostia', not th.steam_boost)
    bd.pressure = 1.9
    th.run()
    check('V3 paine yli triggerin (1.9 > 1.8): ei boostia', not th.steam_boost)

    # 3. Paine saavuttaa trigger-rajan (1.8 bar) -> boost aktivoituu heti
    bd.pressure = 1.8
    th.run()
    check('V4 paine trigger-rajalla (1.8 <= 1.8): boost aktivoituu heti', th.steam_boost and th.heat_on and relay.v == 1)

    # 4. Höyrytys jatkuu: paine tippuu 1.5 baariin -> lämmitin pysyy päällä
    bd.pressure = 1.5
    th.run()
    check('V5 höyrytys käynnissä (p=1.5): lämmitin päällä', th.steam_boost and th.heat_on and relay.v == 1 and th.steam_p_min == 1.5)

    # 5. Venttiili suljetaan: paine alkaa nousta 1.5 -> 1.8 -> 2.0 bar
    # Koska steam_valve_release on 2.1 bar, 2.0 barissa boost PYSYY PÄÄLLÄ!
    bd.pressure = 1.8
    th.run()
    check('V6 nousu 1.8 bar: boost jatkuu täydellä teholla', th.steam_boost and th.heat_on)
    bd.pressure = 2.0
    th.run()
    check('V7 nousu 2.0 bar: boost jatkuu kunnes release (2.1 bar) saavutetaan', th.steam_boost and th.heat_on)

    # 6. Paine saavuttaa steam_valve_release (2.1 bar) -> 2 syklin jälkeen boost sammuu
    bd.pressure = 2.1
    th.run()
    check('V8 nousu 2.1 bar pass 1: rise_count 1, boost vielä', th.steam_rise_count == 1 and th.steam_boost)
    th.run()
    check('V9 nousu 2.1 bar pass 2: paineohjattu lämmitys PYSÄHTYY', not th.steam_boost)

    # 7. Tämän jälkeen toimii normaalisti termostaatilla:
    # Jos T >= tavoite (135.0 C), lämmitin POIS
    sensor.t = 135.2
    th.run()
    check('V10 release jälkeen normaali termostaatti T >= tavoite: lämmitin POIS', not th.heat_on and relay.v == 0)


def test_priority_hierarchy():
    """Testaa käyttäjän tilaama prioriteettijärjestys:
    1. Maksimilämpötila (korkein prioriteetti)
    2. Minimi paine (täysi teho alle alarajan, ohittaa tavoitelämpötilan kunhan max ei ylity)
    3. Tavoitelämpötila (lepotilasäätö kun paine ei ole alle alarajan)
    """
    clock[0] = 5000
    bd = MockBD(mode='STEAM', target=135.0, temp=134.5, p=2.2)
    bd.steam_temperature_max = 140.0
    bd.steam_pressure_low = 1.8
    sensor = Sensor(134.5)
    relay = Relay()
    th = C.Thermostat(bd, {}, relay, sensor, U)

    # PRIORITY 3: Lepotilassa p > p_low (2.2 > 1.8)
    # T = 135.2 >= target (135.0) -> lämmitin POIS
    sensor.t = 135.2
    th.run()
    check('PR1 lepotila T >= tavoite: lämmitin POIS', not th.heat_on and relay.v == 0)

    # PRIORITY 2: Paine tippuu alle alarajan (1.7 <= 1.8)
    # Vaikka T = 136.0 > tavoite (135.0), lämmitin käy TÄYDELLÄ TEHOLLA koska T < max (140.0)!
    bd.pressure = 1.7
    sensor.t = 136.0
    th.run()
    check('PR2 p <= p_low ja T > tavoite mutta T < max: lämmitin TÄYDELLÄ TEHOLLA', th.heat_on and relay.v == 1 and th.steam_boost)

    # PRIORITY 1: Maksimilämpötila saavutetaan (140.0 C >= 140.0 C)
    # Vaikka paine olisi kuinka alhaalla (1.4 bar), maksimilämpötila pakottaa lämmittimen POIS!
    sensor.t = 140.0
    bd.pressure = 1.4
    th.run()
    check('PR3 T >= max (140 C): lämmitin ehdottomasti POIS vaikka p <= p_low', not th.heat_on and relay.v == 0 and not th.steam_boost)

    # Kun T jäähtyy alle max (139.5 C) ja paine alhaalla (1.4 bar) -> täysi teho palaa heti
    sensor.t = 139.5
    th.run()
    check('PR4 T jäähtyy alle max ja p <= p_low: täysi teho palaa heti', th.heat_on and relay.v == 1 and th.steam_boost)


def test_upper_pressure_limit():
    clock[0] = 10000
    bd = MockBD(mode='STEAM', target=135.0, temp=134.0, p=2.4)
    bd.steam_pressure_high = 2.5
    sensor = Sensor(134.0)
    relay = Relay()
    th = C.Thermostat(bd, {}, relay, sensor, U)

    th.run()
    # Paine saavuttaa ylärajan (2.5 bar)
    bd.pressure = 2.5
    th.run()
    check('U1 paineen yläraja saavutettu: lämmitin pois', not th.heat_on and relay.v == 0)

    bd.pressure = 2.6
    th.run()
    check('U2 paine ylärajan yli: lämmitin pois', not th.heat_on and relay.v == 0)


if __name__ == '__main__':
    test_pressure_settings()
    test_valve_open_and_close()
    test_priority_hierarchy()
    test_upper_pressure_limit()
    print('RESULT: %d failed' % len(FAILED))
    sys.exit(1 if FAILED else 0)
