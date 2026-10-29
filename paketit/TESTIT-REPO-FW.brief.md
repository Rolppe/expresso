# TESTIT-REPO-FW

## Task
`testit/ctrl_real_test.py` ja `testit/shot_test.py` testaavat repon firmwarea eivätkä hiljaa `/tmp/fw`:n vanhaa kopiota
(Viat: `valmiustila_smoke.py` testasi `/tmp/fw`:tä, 5.10.2026; "muut avoin").
VAATIMUS: ei koske — testityökalun firmwarelähde, ei mittaus- tai ohjausmenetelmää.

## Files
may:
- `Infra/iot/expresso/testit/ctrl_real_test.py`
- `Infra/iot/expresso/testit/shot_test.py`

must not:
- mikään muu tiedosto, erityisesti `pico/` (firmware) ja rekisterit

read:
- `Infra/iot/expresso/testit/valmiustila_smoke.py:1-22` (malli: `FW`/`FW_PRESET`-ympäristömuuttujat)
- `Infra/iot/expresso/testit/ctrl_real_test.py:1-5`, `Infra/iot/expresso/testit/shot_test.py:1-5`, `:25-35`, `:70-85`
- `Infra/iot/expresso/pico/relayguard.py:245-265` (`user_retry`)

## Do
1. Molemmissa: `FW = os.environ.get('FW') or os.path.join(HERE, '..', 'pico')` (`HERE` = testin hakemisto),
   `sys.path.insert(0, FW)`; kommentti kuten valmiustila_smokessa (vanha `/tmp/fw` valittiin hiljaa, 6.10.2026).
2. `shot_test.py`: preset `os.environ.get('FW_PRESET') or os.path.join(FW, 'preset.py')`; päivitä `Esiehto`-kommentti
   (ei esiehtoa; `FW`/`FW_PRESET` valinnaisia).
3. `shot_test.py`: valelaite `bd.relay_guard` (rivi ~79) saa `user_retry=lambda now, reason: None` — repon
   `classes.note_activity` kutsuu sitä (9103dc2), ja `/tmp/fw`:n kopio ei kutsunut, siksi testi kaatui repolla.
4. Aja molemmat repoa vasten. Jos `shot_test.py` kaatuu tai näyttää `FAIL`ia vielä muusta valelaitteen puutteesta,
   lisää puuttuva valejäsen samalla tavalla (no-op tai kiinteä arvo, kommentti mistä firmware-kohdasta). Älä muuta
   firmwarea äläkä testin väitteitä (`PASS`/`FAIL`-ehtoja).

## Acceptance
```bash
timeout 120 python3 Infra/iot/expresso/testit/ctrl_real_test.py
timeout 120 python3 Infra/iot/expresso/testit/shot_test.py
timeout 120 python3 Infra/iot/expresso/testit/shot_test.py | grep -q "RESULT: 0 failed"
test "$(grep -c "'/tmp/fw" Infra/iot/expresso/testit/ctrl_real_test.py Infra/iot/expresso/testit/shot_test.py | grep -v ':0$' | wc -l)" -eq 0
test "$(git status --porcelain -- Infra/iot/expresso | grep -v -E ' Infra/iot/expresso/(testit/ctrl_real_test\.py|testit/shot_test\.py|paketit/TESTIT-REPO-FW\.brief\.md)$' | wc -l)" -eq 0
```

## Budget
603 riviä (`wc -l` molemmat testit), luetaan vain nimetyt rivit; muutos alle 40 riviä.

## Stop
Jos testi epäonnistuu väitteen (`FAIL`) takia eikä valelaitteen puutteen, tai korjaus vaatisi firmware-muutoksen tai
väitteen muuttamista, kysy yksi kysymys ja lopeta: nimeä väite ja firmware-kohta. Älä committaa.

## Report
Kuusi riviä: Status, Changed, Acceptance, Budget, Deviations, Questions.
