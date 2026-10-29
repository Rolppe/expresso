# EXPRESSO-C1X-TODENNUS

## Task
Todenna c1x oletuksena laitteella ja uuttotoiminta (EU_START c1x=1, EB_C1X miss 0):
1. `testit/c1x_todennus_smoke.py`:
   - Todenna `BrewData.eu_c1x = 1` oletuksena firmware-tasolla (`pico/classes.py`).
   - Todenna `commands.handle_command` käsittelee `c1x:0` ja `c1x:1` oikein (`pico/commands.py`).
   - Todenna firmware-vakiot `EU_C1X_LAG_S = 0.025` ja `EB_C1X_KP_TAIL = 0.2` (`pico/functions.py`).
   - Todenna laiteuuttojen data `testit/bh-20261021-s1..s4.log` (21.10.2026 laiteuuttosarja):
     - `EU_START` sisältää `c1x=1` oletuksena jokaisessa 4 uutossa ilman erillistä komentoa.
     - `EU_END` `late=0, miss=0` ja `EB_END` `late=0, miss=0` kaikissa uutoissa.
     - `EB_C1X` `ovf=0, late=0, starve=0` kaikissa uutoissa.
     - Invariantti TILAUS-O toteutuu täydellisesti (0 pudonnutta tai lisättyä jaksoa).
2. Päivitä `REKISTERI.md` ja `HISTORIA.md`:
   - Merkitse `c1x oletuksena laitteella` todennetuksi (27.10.2026).
   - Lisää `EXPRESSO-C1X-TODENNUS` historiaan.
   - Aseta seuraava paketti odottamaan käyttäjän toimenpiteitä (`SEURAAVA PAKETTI: ei mitään, odottaa käyttäjää`).

VAATIMUS: TILAUS-O, TILAUS-AUTONOMIA

## Files
may:
- `Infra/iot/expresso/testit/c1x_todennus_smoke.py`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/paketit/C1X-TODENNUS.brief.md`

read:
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/pico/classes.py`
- `Infra/iot/expresso/pico/commands.py`
- `Infra/iot/expresso/pico/functions.py`
- `Infra/iot/expresso/testit/bh-20261021-s1.log`
- `Infra/iot/expresso/testit/bh-20261021-s2.log`
- `Infra/iot/expresso/testit/bh-20261021-s3.log`
- `Infra/iot/expresso/testit/bh-20261021-s4.log`

## Acceptance
```bash
python3 Infra/iot/expresso/testit/c1x_todennus_smoke.py
python3 Infra/iot/expresso/testit/tilaus_invariantit_smoke.py
node claude/siirto/tools/vaatimukset.mjs --tarkista "infra expresso" Infra/iot/expresso/paketit/C1X-TODENNUS.brief.md
```
