# EXPRESSO-TURVAKATO-NOLLAUSIKKUNA

## Task
Poista releiden nollausikkuna ajamalla releet (pumppu=11, solenoidi=12, lämmitin=13) alas
heti `boot.py`:n alussa ennen muita alustuksia, importteja tai viiveitä. Auditoi työkalupolut
(`pico_dev.py`) ja kirjaa vaatimus `KAYTTAJAN-TIEDOT.md`:hen.

VAATIMUS: TILAUS-RELEET-ALAS, TILAUS-AUTONOMIA

## Files
may:
- `Infra/iot/expresso/pico/boot.py`
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md`
- `Infra/iot/expresso/testit/nollausikkuna_smoke.py`
- `Infra/iot/expresso/pico/MANIFEST.json`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/ARKISTO.md`

read:
- `Infra/iot/expresso/pico/boot.py`
- `Infra/iot/expresso/pico/devsafe.py`
- `Infra/iot/expresso/pico/main.py:1-4`
- `Infra/iot/expresso/pico_dev.py:274-304`
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md`

## Do
1. `pico/boot.py`: Lisää ensimmäiseksi suoritettavaksi koodiksi `import devsafe` ja `devsafe.relays_off()`.
   Releet ajetaan alas ennen switch-pinnien määritystä ja ennen `time.sleep(0.1)` -viivettä.
2. `KAYTTAJAN-TIEDOT.md`: Kirjaa käyttäjän 7.10.2026 asettama vaatimus tunnusrivinä `TILAUS-RELEET-ALAS`.
3. `pico_dev.py`: Auditoi kehityspolut. Kaikki Picoa ohjaavat tai resetoivat toiminnot (`safe`, `verify`, `flash`,
   `watchdog-test`) käyttävät `enter_devsafe()`-kutsua, joka varmistaa releiden olevan alhaalla.
4. `testit/nollausikkuna_smoke.py`: Luo kattava smoke-testi, joka tarkistaa `boot.py`:n, `main.py`:n, `devsafe.py`:n
   ja `pico_dev.py`:n releiden alasajoinvariantit ja suorittaa simuloidun `boot.py`-ajon.
5. `pico/MANIFEST.json`: Päivitä tiivisteet komennolla `python3 pico_dev.py manifest pico/MANIFEST.json`.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico/boot.py
python3 Infra/iot/expresso/testit/nollausikkuna_smoke.py
python3 Infra/iot/expresso/testit/turva_toimilaite_smoke.py
python3 Infra/iot/expresso/testit/turva_pika_smoke.py
```
