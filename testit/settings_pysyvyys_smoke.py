"""settings_pysyvyys_smoke.py — smoke-testi wmax-pysyvyydelle ja settings-atomisuudelle

Todentaa (wmax-pysyvyys, 26.10.2026):
1. save_settings kirjoittaa atomisesti (tmp + rename).
2. load_settings ei koskaan poista settings.txt-tiedostoa virhetilanteessa (korruptoitunut JSON tms.).
3. load_settings toipuu settings.txt.tmp-tiedostosta, jos varsinainen tiedosto puuttuu.
4. Yksittäisten kenttien virheet (esim. virheellinen arvo) eivät kaada tiedoston muiden kenttien (kuten wmax) latausta.
"""

import os
import sys
import json
import tempfile
import types

# Lisaa pico-hakemisto polkuun
PICO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pico'))
if PICO_DIR not in sys.path:
    sys.path.insert(0, PICO_DIR)

# Feikki-moduulit MicroPython-riippuvuuksille
mp = types.ModuleType('micropython')
mp.const = lambda x: x
sys.modules['micropython'] = mp

bluetooth = types.ModuleType('bluetooth')
bluetooth.UUID = lambda x: x
bluetooth.FLAG_READ = 1
bluetooth.FLAG_NOTIFY = 2
bluetooth.FLAG_WRITE = 4
sys.modules['bluetooth'] = bluetooth

time_mod = types.ModuleType('time')
time_mod.ticks_ms = lambda: 1000
time_mod.ticks_diff = lambda a, b: a - b
time_mod.ticks_add = lambda a, b: a + b
sys.modules['time'] = time_mod

import functions

class MockBrewData:
    def __init__(self):
        self.brew_temperature = 93.0
        self.steam_temperature = 135.0
        self.pre_infusion_time = 2.5
        self.pressure_soft_release_time = 1.0
        self.pre_infusion_mode = False
        self.pressure_soft_release_mode = False
        self.fast_heatup_mode = False
        self.brew_pressure = 8.0
        self.pre_infusion_pressure = 2.5
        self.weight_limit = 0.0
        self.weight_rise_limit = 0.0
        self.learned_ff_pre = 0.25
        self.eu_g_pre = 0.0
        self.eu_tau_pre = 0.0
        self.eu_coast_s = 0.2
        self.eu_coast_fast_s = 0.1
        self.eb_ff = 0.5
        self.eb_x = 0.0
        self.eb_g = 0.0
        self.eb_tau = 0.0
        self.eb_coast_s = functions.EB_COAST_S0
        self.setting_changed = False

    def get_brew_temperature(self): return self.brew_temperature
    def set_brew_temperature(self, v):
        if v > 150.0 or v < 0.0:
            raise ValueError("setpoint out of range: %s" % v)
        self.brew_temperature = v

    def get_steam_temperature(self): return self.steam_temperature
    def set_steam_temperature(self, v):
        if v > 150.0 or v < 0.0:
            raise ValueError("setpoint out of range: %s" % v)
        self.steam_temperature = v

    def get_pre_infusion_time(self): return self.pre_infusion_time
    def set_pre_infusion_time(self, v): self.pre_infusion_time = v

    def get_pressure_soft_release_time(self): return self.pressure_soft_release_time
    def set_pressure_soft_release_time(self, v): self.pressure_soft_release_time = v

    def get_pre_heat_time(self): return 0.0
    def get_pre_infusion_mode(self): return self.pre_infusion_mode
    def set_pre_infusion_mode(self, v): self.pre_infusion_mode = v

    def get_pressure_soft_release_mode(self): return self.pressure_soft_release_mode
    def set_pressure_soft_release_mode(self, v): self.pressure_soft_release_mode = v

    def get_fast_heatup_mode(self): return self.fast_heatup_mode
    def set_fast_heatup_mode(self, v): self.fast_heatup_mode = v

    def get_brew_pressure(self): return self.brew_pressure
    def set_brew_pressure(self, v): self.brew_pressure = v

    def get_pre_infusion_pressure(self): return self.pre_infusion_pressure
    def set_pre_infusion_pressure(self, v): self.pre_infusion_pressure = v

    def get_weight_limit(self): return self.weight_limit
    def set_weight_limit(self, v): self.weight_limit = float(v)

    def get_weight_rise_limit(self): return self.weight_rise_limit
    def set_weight_rise_limit(self, v): self.weight_rise_limit = float(v)


def run_tests():
    fails = []
    def check(name, ok, extra=""):
        if ok:
            print("ok   %s" % name)
        else:
            print("FAIL %s %s" % (name, extra))
            fails.append(name)

    orig_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        try:
            # 1. save_settings kirjoittaa tiedoston ja wmax tallentuu
            bd = MockBrewData()
            bd.weight_limit = 720.0
            bd.weight_rise_limit = 250.0
            res = functions.save_settings(bd, json)
            check("1a. save_settings palauttaa True", res is True)
            check("1b. settings.txt luotu", os.path.exists("settings.txt"))
            check("1c. settings.txt.tmp poistunut (tai uudelleennimetty)", not os.path.exists("settings.txt.tmp"))
            with open("settings.txt", "r") as f:
                saved_data = json.load(f)
            check("1d. wmax tallentunut tiedostoon", saved_data.get("weight_limit") == 720.0)
            check("1e. wrise tallentunut tiedostoon", saved_data.get("weight_rise_limit") == 250.0)

            # 2. load_settings palauttaa arvot
            bd2 = MockBrewData()
            res_load = functions.load_settings(json, bd2)
            check("2a. load_settings palauttaa True", res_load is True)
            check("2b. wmax palautettu (720.0)", bd2.get_weight_limit() == 720.0)
            check("2c. wrise palautettu (250.0)", bd2.get_weight_rise_limit() == 250.0)

            # 3. settings.txt korruptoitunut syntaksi (katkennut JSON)
            # EI SAA POISTAA TIEDOSTOA!
            with open("settings.txt", "w") as f:
                f.write('{"weight_limit": 720.0, "broken')
            bd3 = MockBrewData()
            res_corrupt = functions.load_settings(json, bd3)
            check("3a. Korruptoitunut JSON palauttaa False", res_corrupt is False)
            check("3b. settings.txt EI OLE POISTETTU", os.path.exists("settings.txt"))
            check("3c. bd3 oletukset säilyvät", bd3.get_weight_limit() == 0.0)

            # 4. Toipuminen settings.txt.tmp-tiedostosta
            os.remove("settings.txt")
            with open("settings.txt.tmp", "w") as f:
                json.dump({"weight_limit": 680.0, "weight_rise_limit": 210.0}, f)
            bd4 = MockBrewData()
            res_tmp = functions.load_settings(json, bd4)
            check("4a. tmp-toipuminen palauttaa True", res_tmp is True)
            check("4b. tmp:stä ladattu wmax (680.0)", bd4.get_weight_limit() == 680.0)
            check("4c. settings.txt palautettu levylle", os.path.exists("settings.txt"))

            # 5. Yksittäisen kentän virhe (esim. liian suuri lämpötila) ei estä wmaxin latausta
            with open("settings.txt", "w") as f:
                json.dump({
                    "brew_temperature": 250.0,  # yli 150 astetta -> nostaa ValueError
                    "weight_limit": 800.0,
                    "weight_rise_limit": 200.0,
                    "tuntematon_avain": 12345
                }, f)
            bd5 = MockBrewData()
            res_over = functions.load_settings(json, bd5)
            check("5a. load_settings selviää yksittäisen kentän virheestä", res_over is True)
            check("5b. wmax ladattu onnistuneesti (800.0)", bd5.get_weight_limit() == 800.0)
            check("5c. wrise ladattu onnistuneesti (200.0)", bd5.get_weight_rise_limit() == 200.0)
            check("5d. virheellinen lämpötila piti oletuksensa (93.0)", bd5.get_brew_temperature() == 93.0)
            check("5e. settings.txt säilyi tallessa", os.path.exists("settings.txt"))

            # 6. Tyhjä tiedosto ei aiheuta poistoa
            with open("settings.txt", "w") as f:
                pass
            bd6 = MockBrewData()
            res_empty = functions.load_settings(json, bd6)
            check("6a. Tyhjä tiedosto palauttaa False", res_empty is False)
            check("6b. Tyhjä tiedosto EI OLE POISTETTU", os.path.exists("settings.txt"))

        finally:
            os.chdir(orig_cwd)

    print("\nRESULT: %d failed" % len(fails))
    return len(fails) == 0

if __name__ == '__main__':
    ok = run_tests()
    sys.exit(0 if ok else 1)
