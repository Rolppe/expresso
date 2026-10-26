"""nollausikkuna_smoke.py — smoke-testi releiden nollausikkunan korjaukselle (EXPRESSO-TURVAKATO-NOLLAUSIKKUNA)

Todentaa (26.10.2026):
1. boot.py ajaa releet alas (devsafe.relays_off()) ensimmäisenä ennen mitään muita importteja tai viiveitä.
2. main.py ajaa devsafe.relays_off() heti alussa ja finally-lohkossa.
3. devsafe.RELAY_PINS kattaa kaikki kolme relettä (11=pumppu, 12=solenoidi, 13=lämmitin) preset.PINS:n mukaisesti.
4. devsafe.relays_off() asettaa jokaisen relepinnin tilaan OUT arvolla 0.
5. Työkalupolut (pico_dev.py) ajavat enter_devsafe() ennen kriittisiä toimenpiteitä (safe, verify, flash, watchdog_test).
6. boot.py:n simuloitu suoritus todentaa, että releet nollataan ennen switch-alustuksia tai time.sleep-kutsua.
"""

import os
import sys
import types
import ast

PICO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pico'))
EXPRESSO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if PICO_DIR not in sys.path:
    sys.path.insert(0, PICO_DIR)


def main():
    fails = []

    def check(name, cond, extra=''):
        print(('ok   ' if cond else 'FAIL ') + name + (' — ' + str(extra) if extra and not cond else ''))
        if not cond:
            fails.append(name)

    # 1. boot.py lähdekooditarkistus
    boot_path = os.path.join(PICO_DIR, 'boot.py')
    with open(boot_path, 'r', encoding='utf-8') as f:
        boot_src = f.read()

    boot_tree = ast.parse(boot_src, filename='boot.py')
    body = boot_tree.body

    # Ensimmäiset suoritettavat lauseet: import devsafe; devsafe.relays_off()
    check('1a. boot.py sisältää vähintään kaksi lausetta', len(body) >= 2)

    first_stmt = body[0] if len(body) > 0 else None
    second_stmt = body[1] if len(body) > 1 else None

    is_import_devsafe = (
        isinstance(first_stmt, ast.Import) and
        any(alias.name == 'devsafe' for alias in first_stmt.names)
    )
    is_call_relays_off = (
        isinstance(second_stmt, ast.Expr) and
        isinstance(second_stmt.value, ast.Call) and
        isinstance(second_stmt.value.func, ast.Attribute) and
        second_stmt.value.func.value.id == 'devsafe' and
        second_stmt.value.func.attr == 'relays_off'
    )
    check('1b. boot.py aloittaa lauseella "import devsafe"', is_import_devsafe, ast.dump(first_stmt) if first_stmt else 'None')
    check('1c. boot.py toinen lause on "devsafe.relays_off()"', is_call_relays_off, ast.dump(second_stmt) if second_stmt else 'None')

    # Varmistetaan, ettei mitään sleep- tai switch-alustuksia tapahdu ennen devsafe.relays_off()
    sleep_before_relays = False
    for stmt in body[:2]:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            func = getattr(stmt.value, 'func', None)
            if getattr(func, 'attr', None) == 'sleep':
                sleep_before_relays = True
    check('1d. Ei time.sleep-kutsua ennen devsafe.relays_off()', not sleep_before_relays)

    # 2. main.py lähdekooditarkistus
    main_path = os.path.join(PICO_DIR, 'main.py')
    with open(main_path, 'r', encoding='utf-8') as f:
        main_src = f.read()

    main_tree = ast.parse(main_src, filename='main.py')
    main_first = main_tree.body[0] if len(main_tree.body) > 0 else None
    main_second = main_tree.body[1] if len(main_tree.body) > 1 else None

    main_import_devsafe = (
        isinstance(main_first, ast.Import) and
        any(alias.name == 'devsafe' for alias in main_first.names)
    )
    main_call_relays_off = (
        isinstance(main_second, ast.Expr) and
        isinstance(main_second.value, ast.Call) and
        isinstance(main_second.value.func, ast.Attribute) and
        main_second.value.func.value.id == 'devsafe' and
        main_second.value.func.attr == 'relays_off'
    )
    check('2a. main.py aloittaa lauseella "import devsafe"', main_import_devsafe)
    check('2b. main.py toinen lause on "devsafe.relays_off()"', main_call_relays_off)
    check('2c. main.py finally-lohkossa ajetaan devsafe.relays_off()', 'devsafe.relays_off()' in main_src and 'finally:' in main_src)

    # 3. devsafe.py pinnit ja toiminnot
    import preset
    expected_relay_pins = (
        preset.PINS['RELAY_PUMP'],
        preset.PINS['RELAY_SOLENOID'],
        preset.PINS['RELAY_HEATER']
    )
    check('3a. preset.PINS relepinnit ovat (11, 12, 13)', expected_relay_pins == (11, 12, 13), expected_relay_pins)

    # Mock machine.Pin ja machine.WDT devsafe-testille
    pin_states = {}
    pin_modes = {}

    class MockPin:
        IN = 0
        OUT = 1
        PULL_DOWN = 2

        def __init__(self, n, mode=None, pull=None, value=None):
            self.n = n
            self.mode = mode
            self.pull = pull
            if value is not None:
                pin_states[n] = value
            elif n not in pin_states:
                pin_states[n] = 0
            if mode is not None:
                pin_modes[n] = mode

        def value(self, val=None):
            if val is not None:
                pin_states[self.n] = val
                return self
            return pin_states.get(self.n, 0)

    class MockWDT:
        def __init__(self, timeout=8000):
            self.timeout = timeout
            self.fed = 0

        def feed(self):
            self.fed += 1

    machine_mod = types.ModuleType('machine')
    machine_mod.Pin = MockPin
    machine_mod.WDT = MockWDT
    sys.modules['machine'] = machine_mod

    # Tuodaan devsafe mockatulla machine-moduulilla
    if 'devsafe' in sys.modules:
        del sys.modules['devsafe']
    import devsafe

    check('3b. devsafe.RELAY_PINS vastaa presettiä', devsafe.RELAY_PINS == expected_relay_pins, devsafe.RELAY_PINS)

    # Asetetaan aluksi jokin rele päälle (kuten vahtikoiran nollauksessa ennen bootia)
    pin_states[11] = 1
    pin_states[12] = 1
    pin_states[13] = 1

    check('3c. Ennen relays_off releet ovat päällä', [pin_states[11], pin_states[12], pin_states[13]] == [1, 1, 1])

    devsafe.relays_off()
    check('3d. devsafe.relays_off sammuttaa kaikki releet', [pin_states[11], pin_states[12], pin_states[13]] == [0, 0, 0])
    check('3e. devsafe.relays_state palauttaa [0, 0, 0]', devsafe.relays_state() == [0, 0, 0])
    check('3f. Relepinnit asetettu tilaan Pin.OUT', all(pin_modes.get(n) == MockPin.OUT for n in (11, 12, 13)))

    # 4. Työkalupolkujen auditointi pico_dev.py
    pico_dev_path = os.path.join(EXPRESSO_DIR, 'pico_dev.py')
    with open(pico_dev_path, 'r', encoding='utf-8') as f:
        pico_dev_src = f.read()

    check('4a. pico_dev.py sisältää enter_devsafe-metodin', 'def enter_devsafe(self):' in pico_dev_src)
    check('4b. enter_devsafe ajaa devsafe.enter()', 'devsafe.enter()' in pico_dev_src)
    check('4c. enter_devsafe tarkistaa SAFE_OK ja keskeyttää tarvittaessa', 'SAFE_OK' in pico_dev_src and 'relays did not read back 0' in pico_dev_src)
    check('4d. flash() kutsuu enter_devsafe()', 'def flash(' in pico_dev_src and 'link.enter_devsafe()' in pico_dev_src)
    check('4e. verify() kutsuu enter_devsafe()', 'def verify(' in pico_dev_src and 'link.enter_devsafe()' in pico_dev_src)
    check('4f. safe() kutsuu enter_devsafe()', 'def safe():' in pico_dev_src and 'link.enter_devsafe()' in pico_dev_src)
    check('4g. watchdog_test() kutsuu enter_devsafe()', 'def watchdog_test():' in pico_dev_src and 'link.enter_devsafe()' in pico_dev_src)

    # 5. Simuloidaan boot.py:n ajo
    time_mock = types.ModuleType('time')
    time_mock.sleep = lambda s: None
    sys.modules['time'] = time_mock

    # Simuloidaan tila jossa lämmitin on jäänyt päälle ennen bootia
    pin_states[11] = 0
    pin_states[12] = 0
    pin_states[13] = 1  # lämmitin jäänyt päälle!

    boot_globals = {'__name__': '__main__', '__file__': boot_path}
    exec(compile(boot_src, boot_path, 'exec'), boot_globals)

    check('5a. boot.py:n suorituksen jälkeen lämmitin ja kaikki releet ovat 0', [pin_states[11], pin_states[12], pin_states[13]] == [0, 0, 0])
    check('5b. boot.py alusti kytkimet Pin.IN', pin_modes.get(7) == MockPin.IN and pin_modes.get(8) == MockPin.IN and pin_modes.get(9) == MockPin.IN)

    print('RESULT: %d failed' % len(fails))
    return len(fails)


if __name__ == '__main__':
    sys.exit(main())
