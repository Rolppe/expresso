# EXPRESSO-LAMMITYS-VIRTAUS

## Task
Todennus ja rekisteröinti uuton lämmitykselle virtauksesta (TILAUS-N, TILAUS-R):
1. Varmista uuton lämmitystehon ohjaus kattilaan vaihtuneesta vedestä pumpun iskuista ja paineesta (EP5, BH_PMAX 15 bar, `_bh_add(p)`).
2. Poista tarpeeton käyttämätön pulssitusvakio `EB_HEAT_OFF_MS, EB_HEAT_ON_MS` `pico/functions.py`:stä.
3. Päivitä `pico/MANIFEST.json`, `REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`.

VAATIMUS: TILAUS-N, TILAUS-R, TILAUS-AUTONOMIA

## Files
may:
- `Infra/iot/expresso/pico/functions.py`
- `Infra/iot/expresso/pico/MANIFEST.json`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/ARKISTO.md`

read:
- `Infra/iot/expresso/pico/functions.py:320-350`
- `Infra/iot/expresso/testit/termostaatti_smoke.py`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md:165-223`

## Do
1. `pico/functions.py`:
   - Poista käyttämätön `EB_HEAT_OFF_MS, EB_HEAT_ON_MS = 100, 50`.
2. `pico/MANIFEST.json`:
   - Päivitä manifesti komennolla `python3 pico_dev.py manifest pico/MANIFEST.json`.
3. `REKISTERI.md`:
   - Merkitse `EXPRESSO-LAMMITYS-VIRTAUS` toteutetuksi ja todennetuksi.
   - Merkitse `EXPRESSO-TURVAKATO` valmiiksi (nollausikkuna toteutettu 26.10.2026).
   - Valitse seuraavaksi paketiksi `EXPRESSO-TILAUS-INVARIANTIT`.
4. `HISTORIA.md` ja `ARKISTO.md`:
   - Kirjaa paketin valmistuminen ja todennus.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico/functions.py
python3 Infra/iot/expresso/testit/termostaatti_smoke.py
python3 Infra/iot/expresso/testit/shot_test.py
python3 Infra/iot/expresso/testit/turva_pika_smoke.py
python3 Infra/iot/expresso/testit/valmiustila_smoke.py
```
