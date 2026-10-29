# EXPRESSO-THERMAL-STABILITY

## Task
Toteuta thermal stability (-10…+10) ylläpitotehon tarpeesta (TILAUS-Q) firmwareen, telemetriaan ja sarjakomentoihin:
1. `Thermostat`: laske thermal stability IDLE-PI:n integraalista (`self.pi_i`), jossa opittu pitkän aikavälin vakioteho P0 (muuttumaton 30 min, tallennetaan Picolle tiedostoon `thermal_stability.json`) = 0, kylmäkäynnistyksen ensimmäisen tasaantumisen teho = -10 (skaalaus span ~0.040), rajaus [-10.0, +10.0]. Muissa tiloissa säilytetään viimeinen lepoarvo.
2. `BrewData`: attribuutti `thermal_stability` ja metodi `get_thermal_stability()`.
3. `diagnet.py`: lisää `ts=%.1f` `DIAG_MIN`-riville.
4. `bluetooth_handler.py`: lisää `thermal_stability` live-telemetriaan (`live_payload` ja `scale_payload`), ja `NOTIFY_DROP_ORDER = ('thermal_stability',)` jotta 240 B MTU ei ylity missään tilassa.
5. `commands.py`: lisää kyselykomento `ts?` ja asetuskomento `ts:p0:<val>`.
6. `testit/termostaatti_smoke.py`: lisää kattavat testit L1–L6 thermal stabilityn laskennalle, rajaukselle, P0-tallennukselle, tilasiirtymille ja DIAG_MIN-tulosteelle.
7. Päivitä `pico/MANIFEST.json`, `REKISTERI.md`, `HISTORIA.md`.

VAATIMUS: TILAUS-Q, TILAUS-P, TILAUS-AUTONOMIA

## Files
may:
- `Infra/iot/expresso/pico/classes.py`
- `Infra/iot/expresso/pico/diagnet.py`
- `Infra/iot/expresso/pico/bluetooth_handler.py`
- `Infra/iot/expresso/pico/commands.py`
- `Infra/iot/expresso/testit/termostaatti_smoke.py`
- `Infra/iot/expresso/pico/MANIFEST.json`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/paketit/THERMAL-STABILITY.brief.md`

read:
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md:203-213`
- `Infra/iot/expresso/REKISTERI.md:638`
- `Infra/iot/expresso/pico/classes.py`
- `Infra/iot/expresso/pico/diagnet.py`
- `Infra/iot/expresso/pico/bluetooth_handler.py`
- `Infra/iot/expresso/pico/commands.py`
- `Infra/iot/expresso/testit/termostaatti_smoke.py`

## Do
1. `pico/classes.py`:
   - Määritä vakiot:
     `TS_P0_DEFAULT = 0.045`
     `TS_SPAN_DEFAULT = 0.040`
     `TS_STABLE_TIME_MS = 1800000` (30 min)
     `TS_STABLE_EPS = 0.003`
     `TS_FILE = 'thermal_stability.json'`
   - `Thermostat.__init__`: alusta `self.ts_p0`, `self.ts_span`, `self.ts_candidate_p`, `self.ts_candidate_start`, `self.thermal_stability = -10.0`. Kutsu `self._ts_load()`.
   - Toteuta `_ts_load(self)` ja `_ts_save(self)` atomisella `.tmp` + rename -kirjoituksella.
   - `Thermostat._pi_period`: laske `raw_ts = (self.ts_p0 - self.pi_i) / self.ts_span * 10.0`, rajoita [-10.0, +10.0] ja pyöristä 1 desimaaliin. Aseta `self.thermal_stability` ja `self.brew_data.thermal_stability`.
   - `Thermostat.run`: päivitä 30 min vakauslaskuria IDLE-tilassa. Jos pi_i pysyy +-TS_STABLE_EPS sisällä 30 min, päivitä `self.ts_p0` ja tallenna. Muissa tiloissa nollaa kandidaatti ja säilytä viimeinen arvo.
   - `BrewData`: lisää `self.thermal_stability = -10.0` ja metodi `get_thermal_stability()`.
2. `pico/diagnet.py`:
   - Lisää `_f1`-apufunktio (`%.1f` tai `-`).
   - `DIAG_MIN`-riville kenttä `ts=%s` (`_f1(getattr(bd, 'thermal_stability', None))`).
3. `pico/bluetooth_handler.py`:
   - Määritä `NOTIFY_DROP_ORDER = ('thermal_stability',)`
   - `live_payload`: lisää `'thermal_stability': round(brew_data.get_thermal_stability(), 1)`
   - `scale_payload`: lisää `'thermal_stability': round(brew_data.get_thermal_stability(), 1)`
4. `pico/commands.py`:
   - Lisää `ts?` / `thermal?` tulostamaan `TS val=... p0=... pi_i=...`
   - Lisää `ts:p0:<float>` asettamaan `ts_p0` manuaalisesti
5. `testit/termostaatti_smoke.py`:
   - Lisää testitapaukset L1–L6:
     - L1: Kylmäkäynnistys (pi_i 0.085) tuottaa thermal stability -10.0
     - L2: Vakiotila (pi_i == p0 0.045) tuottaa 0.0
     - L3: Kuuma tila (pi_i 0.005) tuottaa +10.0
     - L4: Rajaus [-10.0, +10.0] ylityksille ja alituksille
     - L5: 30 min vakaa IDLE oppii uuden P0:n ja tallentaa sen
     - L6: Muut tilat (STEAM, BREW) säilyttävät edellisen IDLE-arvon
6. `pico/MANIFEST.json`:
   - Päivitä manifesti `pico_dev.py manifest pico/MANIFEST.json`.
7. `REKISTERI.md` ja `HISTORIA.md`:
   - Päivitä päätös, avoimet asiat ja toteutushistoria.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico/classes.py
python3 -m py_compile Infra/iot/expresso/pico/diagnet.py
python3 -m py_compile Infra/iot/expresso/pico/bluetooth_handler.py
python3 -m py_compile Infra/iot/expresso/pico/commands.py
python3 Infra/iot/expresso/testit/termostaatti_smoke.py
python3 Infra/iot/expresso/testit/lampotilatilat_smoke.py
python3 Infra/iot/expresso/testit/valmiustila_smoke.py
python3 Infra/iot/expresso/testit/turva_pika_smoke.py
python3 Infra/iot/expresso/testit/turva_toimilaite_smoke.py
python3 Infra/iot/expresso/testit/nollausikkuna_smoke.py
python3 Infra/iot/expresso/testit/tilaus_invariantit_smoke.py
node claude/siirto/tools/vaatimukset.mjs --tarkista "infra expresso" Infra/iot/expresso/paketit/THERMAL-STABILITY.brief.md
```
