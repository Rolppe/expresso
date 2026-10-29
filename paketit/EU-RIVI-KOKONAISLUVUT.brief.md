# EXPRESSO-EU-RIVI-KOKONAISLUVUT

## Task
Arvioi ja kevennä EU-rivin lokituksen ja uuttosilmukan (`pre_infusion_phased`) merkkijono- ja
lista-allokaatiot. Säilytä EU-rivin kenttämuoto yhteensopivana olemassa olevien analyysityökalujen
(`esiuutto_analyysi.py`, `uutto8_sovitus.py`, `esiuutto_smoke.py`) ja aiempien lokien kanssa.
Poista uuttosilmukan toistuvat lista- ja välimerkkijonoallokaatiot.

VAATIMUS: TILAUS-O, TILAUS-AUTONOMIA

## Files
may:
- `Infra/iot/expresso/pico/functions.py`
- `Infra/iot/expresso/testit/eu_rivi_smoke.py`
- `Infra/iot/expresso/pico/MANIFEST.json`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/ARKISTO.md`

read:
- `Infra/iot/expresso/pico/functions.py:875-920`
- `Infra/iot/expresso/paketit/GC-UUTTO.md:15-64`
- `Infra/iot/expresso/paketit/C1-JAKSOT.md:20-50,75-80`
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md`

## Do
1. Arvioi `EU-rivi kokonaisluvuin`: C1-JAKSOT siirsi 1 kHz näytteistyksen ja releiden käännöt
   ytimelle 1 muistilukittuna (`heap_lock()`), joten ytimen 0 keruuviiveet eivät aiheuta
   myöhästymisiä tai syklin ohituksia (`miss = 0`, `late = 0`, TILAUS-O toteutuu). EU-rivin
   arvojen muuttaminen kiinteiksi kokonaisluvuiksi (kuten senttibaareiksi) rikkoisi kaikki
   olemassa olevat analyysit ja vertailukelpoisuuden aiempiin uuttolokeihin ilman hyötyä
   ytimen 1 ajoitukselle.
2. `pico/functions.py`:
   - Korvaa `out = []` jokaisessa 20 ms jaksossa in-place-tyhjennyksellä `del out[:]` (poistaa
     50 listan allokaatiota sekunnissa).
   - Inlinoa `weight_flow_log`:n paino- ja virtauskentät suoraan EU-rivin muotoilumerkkijonoon
     ilman väliaikaista 'w=... f=...' -merkkijonoa.
   - Korvaa USB-CDC -jonotarkistuksen generaattorilauseke `sum(len(x) + 1 for x in out)`
     suoralla silmukalla.
3. `testit/eu_rivi_smoke.py`: Luo smoke-testi, joka tarkistaa AST:llä ja ajonaikaisesti
   in-place-tyhjennyksen, generaattorin poiston ja EU-rivin jäsennettävyyden.
4. `pico/MANIFEST.json`: Päivitä manifesti komennolla `python3 pico_dev.py manifest pico/MANIFEST.json`.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico/functions.py
python3 Infra/iot/expresso/testit/eu_rivi_smoke.py
python3 Infra/iot/expresso/testit/shot_test.py
```
