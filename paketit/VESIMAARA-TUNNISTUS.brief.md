# EXPRESSO-VESIMAARA-TUNNISTUS

## Task
Toteuta säiliön vesimäärän tunnistus lämpöstabiiliuden saavutusnopeudesta (TILAUS-Q) firmwareen, telemetriaan ja sarjakomentoihin:
1. `WaterTankTracker` (`pico/water_tank.py`):
   - Seuraa lämpöstabiiliuden (TS) nousua kylmäkäynnistyksestä (TS <= -8.0) arviointikynnykseen (TS >= -2.0).
   - Laskee saavutusajan t_reach_s = (t_target - t_start).
   - Arvioi säiliön vesimäärän V_est = model_a * t_reach_s + model_b (oletus a=0.0020, b=-0.40; rajataan 0.0...capacity 2.0 L).
   - Tunnistaa lämpimän käynnistyksen (TS > -6.0), jolloin säilyttää edellisen tallennetun tason ('warm_start').
   - Seuraa vedenkulutusta (consume_water_ml / consume_water_l), ja asettaa 'low_water'-varoituksen (<= 0.3 L).
   - Tallentaa tilan Picolla atomisesti tiedostoon `water_tank.json` (tmp + rename).
2. `BrewData` (`pico/classes.py`):
   - Attribuutti `water_tank` ja getterit `get_tank_water_l()`, `get_tank_water_pct()`, `get_tank_status()`, `get_tank_last_reach_s()`.
3. `Thermostat` (`pico/classes.py`):
   - Kutsuu `wt.update(self.thermal_stability, now, mode)` jokaisella ajokerralla.
4. `diagnet.py`:
   - Lisää `tk=%s` (`_f2(bd.get_tank_water_l())`) `DIAG_MIN`-riville.
5. `bluetooth_handler.py`:
   - Lisää `tank_water_l`, `tank_pct`, `tank_status` reaaliaikatelemetriaan (`live_payload` ja `scale_payload`).
   - Päivitä `NOTIFY_DROP_ORDER` sisältämään uudet kentät, jotta 240 B MTU ei ylity koskaan.
6. `commands.py`:
   - Lisää kyselykomento `tank?` ja ohjauskomennot `tank:fill`, `tank:set:<L>`, `tank:cal:<a>:<b>`, `tank:consume:<ml>`.
7. `main.py`:
   - Alusta `brew_data.water_tank = water_tank.WaterTankTracker(utime)`.
8. `testit/vesimaara_smoke.py`:
   - Luo kattavat savutestit M1–M8 vesimäärän arvioinnille, eri vesimäärille (tyhjä 0.2 L, puoli 1.0 L, täysi 2.0 L), lämpimälle käynnistykselle, vedenkulutukselle, varoituskynnykselle, sarjakomennoille, pysyvyydelle ja telemetrialle.
9. Päivitä `pico/MANIFEST.json`, `REKISTERI.md`, `HISTORIA.md`.

VAATIMUS: TILAUS-Q, TILAUS-AUTONOMIA

## Files
may:
- `Infra/iot/expresso/pico/water_tank.py`
- `Infra/iot/expresso/pico/classes.py`
- `Infra/iot/expresso/pico/diagnet.py`
- `Infra/iot/expresso/pico/bluetooth_handler.py`
- `Infra/iot/expresso/pico/commands.py`
- `Infra/iot/expresso/pico/main.py`
- `Infra/iot/expresso/testit/vesimaara_smoke.py`
- `Infra/iot/expresso/pico/MANIFEST.json`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/paketit/VESIMAARA-TUNNISTUS.brief.md`

read:
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md:203-213`
- `Infra/iot/expresso/REKISTERI.md:642`
- `Infra/iot/expresso/pico/classes.py`
- `Infra/iot/expresso/pico/diagnet.py`
- `Infra/iot/expresso/pico/bluetooth_handler.py`
- `Infra/iot/expresso/pico/commands.py`
- `Infra/iot/expresso/pico/main.py`

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico/water_tank.py
python3 -m py_compile Infra/iot/expresso/pico/classes.py
python3 -m py_compile Infra/iot/expresso/pico/diagnet.py
python3 -m py_compile Infra/iot/expresso/pico/bluetooth_handler.py
python3 -m py_compile Infra/iot/expresso/pico/commands.py
python3 -m py_compile Infra/iot/expresso/pico/main.py
python3 Infra/iot/expresso/testit/vesimaara_smoke.py
python3 Infra/iot/expresso/testit/termostaatti_smoke.py
python3 Infra/iot/expresso/testit/smart_tray_smoke.py
python3 Infra/iot/expresso/testit/lampotilatilat_smoke.py
python3 Infra/iot/expresso/testit/valmiustila_smoke.py
python3 Infra/iot/expresso/testit/tilaus_invariantit_smoke.py
node claude/siirto/tools/vaatimukset.mjs --tarkista "infra expresso" Infra/iot/expresso/paketit/VESIMAARA-TUNNISTUS.brief.md
```
