# EXPRESSO-STANDBY-IMPORT-UTIME

## Task
Siirrä `import utime` `BrewData.update_standby`-metodista moduulitasolle `pico/classes.py`:ssä.
Poista toistuva `import utime` -kutsu pääsilmukasta valmiustilassa ja käytä instanssin
kelloa (`self.utime`) tai moduulitason kelloa (`utime`). Varmista toiminta `testit/valmiustila_smoke.py`:llä.

VAATIMUS: TILAUS-AUTONOMIA, TILAUS-P

## Files
may:
- `Infra/iot/expresso/pico/classes.py`
- `Infra/iot/expresso/testit/valmiustila_smoke.py`
- `Infra/iot/expresso/pico/MANIFEST.json`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/ARKISTO.md`

read:
- `Infra/iot/expresso/pico/classes.py:595-620`
- `Infra/iot/expresso/testit/valmiustila_smoke.py`
- `Infra/iot/expresso/REKISTERI.md`

## Do
1. `pico/classes.py`:
   - Tuo `utime` moduulitasolla (`try: import utime except ImportError: utime = None`).
   - Poista `import utime` `update_standby`-metodin sisältä ja käytä `clock = self.utime or utime`.
2. `testit/valmiustila_smoke.py`:
   - Lisää tarkistus, joka varmistaa että `update_standby` ei sisällä paikallista `import utime` -kutsua.
3. `pico/MANIFEST.json`:
   - Päivitä manifesti komennolla `python3 pico_dev.py manifest pico/MANIFEST.json`.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico/classes.py
python3 Infra/iot/expresso/testit/valmiustila_smoke.py
python3 Infra/iot/expresso/testit/termostaatti_smoke.py
python3 Infra/iot/expresso/testit/turva_pika_smoke.py
python3 Infra/iot/expresso/testit/turva_toimilaite_smoke.py
```
