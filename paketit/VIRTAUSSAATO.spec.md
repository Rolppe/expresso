# VIRTAUSSAATO — toteutuksen sopimus

Tämä tiedosto kertoo *mitä* rakennetaan, merkki merkiltä. Perustelut ovat paketissa
`paketit/VIRTAUSSAATO.md`. Rivinumerot viittaavat commitiin `b90be1c` (muuttumaton devsafe14).

## 1. `FlowController` (`pico/classes.py`, uusi luokka `PumpPressureController`in jälkeen)

```python
class FlowController:
    def __init__(self, utime, target, p_start, kp=0.5, ki=1.5, p_min=2.0, p_max=10.5,
                 rate_bar_s=2.0, lead=0.8, update_ms=100, stale_limit=3):
```

Tila: `sp = float(p_start)`, `e_prev = None`, `stale = 0`, `failed = False`, `sat_ms = 0.0`,
`saturated = False`, `last_update = utime.ticks_ms()`.

`set_target(self, target)` asettaa `self.target` (ajonaikainen `fset:`).

`update(self, flow, pressure)` palauttaa paineen asetusarvon (bar) tai `None`:

1. `failed` → palauta `None` heti.
2. `now = utime.ticks_ms()`; jos `ticks_diff(now, last_update) < update_ms`, palauta `self.sp`
   muuttumattomana. (Uuttosilmukka ajaa 20–25 ms, virtausestimaatti päivittyy 11,6 Hz.)
3. `dt = ticks_diff(now, last_update) / 1000.0`, katkaise `dt > 0.5` → `0.5`; `last_update = now`.
4. `flow is None` → `stale += 1`; jos `stale >= stale_limit`, `failed = True` ja palauta `None`;
   muuten palauta `self.sp` muuttumattomana (`e_prev` koskematta).
5. Muuten `stale = 0`, `e = self.target - flow`,
   `de = 0.0 if e_prev is None else e - e_prev`, `e_prev = e`.
6. Nopeusmuotoinen PI: `sp_new = sp + kp * de + ki * e * dt`.
7. Rampitus: rajaa `sp_new` väliin `[sp - rate_bar_s*dt, sp + rate_bar_s*dt]`.
8. Etäisyysraja: rajaa `sp_new` väliin `[pressure - lead, pressure + lead]`. Tämä pitää sisemmän
   säätimen pois `continuous_error = 1.0` -tilasta (`classes.py:663-666,704-711`), jossa duty
   pakotetaan ykköseen. Nopeusmuoto + rajaus on samalla anti-windup: integraattoria ei ole.
9. Alue: rajaa `[p_min, p_max]`, sijoita `self.sp`.
10. Saturaatio: jos `sp` on ≤ `p_min + 0.01` tai ≥ `p_max - 0.01` **ja** `abs(e) > 0.1`, kasvata
    `sat_ms += dt*1000`, muuten `sat_ms = 0`; `self.saturated = sat_ms >= 2000`.
11. Palauta `self.sp`.

## 2. `BrewData` (`pico/classes.py`)

`__init__`: `self.flow_mode = False`, `self.flow_target = 2.2`.
Metodit `get_flow_mode()`, `set_flow_mode(enabled)` (tallentaa `bool(enabled)`),
`get_flow_target()`, `set_flow_target(g_s)` — `float`, rajattu **0,5–5,0**, palauttaa rajatun arvon,
epäkelpo arvo jättää entisen voimaan. Malli: `set_flow_window_ms` (`classes.py:510-521`).

## 3. `run_shot` (`pico/functions.py:126-250`) — vain uuttosilmukka

`pressure_controller`-luonnin jälkeen (`functions.py:199`):

```python
flow_controller = None
if brew_data.get_flow_mode() and brew_data.get_flow() is not None:
    flow_controller = FlowController(utime, brew_data.get_flow_target(),
                                     brew_data.get_brew_pressure())
```

Silmukassa `brew_pressure`-rivin jälkeen (`functions.py:230-232`):

```python
target = brew_pressure
if flow_controller is not None:
    flow_controller.set_target(brew_data.get_flow_target())
    sp = flow_controller.update(brew_data.get_flow(), pressure)
    if sp is None:
        print('%s_FLOW_OFF reason=scale silent' % label)
        flow_controller = None
    else:
        target = sp
pressure_controller.update(pressure, target)
```

Lokirivi (`functions.py:236-241`): kolmas kenttä tulostaa `target`in `brew_pressure`in sijaan, ja
riville lisätään loppuun `fsp=%.2f fsat=%d` — `fsp` on `brew_data.get_flow_target()` ja `fsat`
`1 if flow_controller.saturated else 0`, molemmat `0` kun `flow_controller is None`. Kenttien
järjestys ja muoto ennen `w=`-häntää ei muutu (`analyze_shot.py` lukee ne paikan mukaan).

Esiuutto (`pre_infusion`), keskeytysehdot, painorajat, soft release ja `finally` eivät muutu.

## 4. Komennot (`pico/commands.py`, `fwin:`-haaran malli `commands.py:115-122`)

- `fmode:on` / `fmode:off` → `set_flow_mode(True/False)`. Muu argumentti:
  `brew_data.command_known = False` ja `return updated` (tuntematon komento, `commands.py:139-147`).
- `fset:<g/s>` → `set_flow_target(_float_arg(command))`.

Kumpikaan **ei** aseta `updated = True`: asetukset eivät tallennu, joten laite on käynnistyksen
jälkeen aina paineohjauksessa.

## 5. `TS_START` (`pico/main.py:219-222`)

Muotoiluun lisätään loppuun ` fmode=%s`, arvo `'off'` kun tila on pois, muuten
`'%.2f' % brew_data.get_flow_target()`. Muut kentät säilyvät.

## 6. Simulaatio `testit/flow_ctrl_sim.py` (uusi, isäntäkone, ei laitteistoa)

Lataa `shot_test.py`:n esittelyosa (valemodulit) samaan tapaan kuin `real_plant_sim.py:12-14`,
mutta polku lasketaan `os.path.dirname(os.path.abspath(__file__))`-kautta, ei `/tmp`-vakiona.

Malli, 1 ms askel: `p += ((6.7 if rele else 0.0) - k*p) / 1000.0`, toimilaitteen viive 70 ms
jonona (`real_plant_sim.py:17-24`), ulosvirtaus `flow_true = k * p` [g/s], kertyvä paino
`w += flow_true/1000`. Vaakanäyte työnnetään virtausestimaattorin historiaan **86 ms välein**
kohinalla sd 0,25 g; säädin lukee virtauksen estimaattorin läpi, ei `flow_true`-arvoa.

Ajo 32 s, `fmode:on`, `fset:2.2`, `k`: 0,50 alussa → **8,0 s: 0,30** → **16,0 s: 0,50** →
**24,0 s: 0,166**. Väitteet:

1. 8 s ja 16 s muutosten jälkeen `flow_true` on ±0,25 g/s sisällä tavoitteesta ≤ 2,0 s kuluessa ja
   pysyy siellä vaiheen loppuun (0,5 s asettumisvara sallitaan mittauksen alussa).
2. `p` ei ylitä 11,0 bar missään kohtaa eikä 13,0 bar koskaan.
3. Viimeisessä vaiheessa (saavuttamaton tavoite) `fsat` on 1 viimeistään 3,0 s kuluttua, ajo jatkuu
   loppuun asti eikä paine ylitä 11,0 bar.
4. Regressio: sama ajo `fmode:off` pitää `target`in vakiona `brew_pressure`issa ja paine asettuu
   0,5 bar sisään siitä.

Tuloste: rivi `PASS`/`FAIL` per väite ja viimeisenä `RESULT: <n> failed`; paluuarvo 0 vain kun
`n == 0`. Malli `shot_test.py`.
