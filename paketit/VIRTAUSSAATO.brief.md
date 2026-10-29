# VIRTAUSSAATO

## Task
Toteuta eXpresso-firmwaren uuttovaiheeseen virtauspohjainen kaskadisäätö ja sen isäntäsimulaatio
täsmälleen niin kuin `paketit/VIRTAUSSAATO.spec.md` määrää.

## Files
may:
- `Infra/iot/expresso/pico/classes.py`
- `Infra/iot/expresso/pico/functions.py`
- `Infra/iot/expresso/pico/commands.py`
- `Infra/iot/expresso/pico/main.py`
- `Infra/iot/expresso/testit/flow_ctrl_sim.py` (uusi)

must not:
- `Infra/iot/expresso/testit/shot_test.py` (regressiomitta — ei saa muuttua)
- `Infra/iot/expresso/pico/scale.py`, `devsafe.py`, `bluetooth_handler.py`, `backflush.py`,
  `api_functions.py`, `ugit.py`, `MANIFEST.json`
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/paketit/VIRTAUSSAATO.spec.md`
- `Infra/iot/expresso/paketit/VIRTAUSSAATO.md`
- `Infra/iot/expresso/pico/classes.py`, `functions.py`, `commands.py`, `main.py`, `scale.py`
- `Infra/iot/expresso/testit/shot_test.py`, `testit/real_plant_sim.py`

## Do
1. Lue spec ja paketti, sitten `classes.py:630-748` (`PumpPressureController`),
   `functions.py:126-260` (`run_shot`), `commands.py:115-147`, `main.py:210-228`,
   `scale.py:222-255` (`flow`).
2. Lisää `FlowController` `classes.py`:hyn spesifikaation luvun 1 mukaisesti.
3. Lisää `BrewData`:n kentät ja metodit spesifikaation luvun 2 mukaisesti.
4. Muuta `run_shot`in uuttosilmukka ja sen lokirivi spesifikaation luvun 3 mukaisesti.
5. Lisää komennot `fmode:` ja `fset:` spesifikaation luvun 4 mukaisesti ja `fmode=`-kenttä
   `TS_START`-riville luvun 5 mukaisesti.
6. Kirjoita `testit/flow_ctrl_sim.py` spesifikaation luvun 6 mukaisesti.
7. Viritä vain `FlowController`in oletusarvot `kp`, `ki` ja `rate_bar_s` niin että luvun 6 väitteet
   toteutuvat. Älä muuta säätimen rakennetta, rajoja (`p_min`, `p_max`, `lead`) äläkä väitteitä.
8. Aja `## Acceptance` ja `## Budget` ja korjaa vain se, minkä ne raportoivat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && rm -rf /tmp/fw && mkdir -p /tmp/fw && cp pico/*.py pico/scale_cal.json /tmp/fw/ && cp -r pico/lib /tmp/fw/ && python3 testit/shot_test.py > /tmp/acc1.out && grep -qx "RESULT: 0 failed" /tmp/acc1.out
```
```bash
cd /srv/work/Infra/iot/expresso && python3 testit/flow_ctrl_sim.py > /tmp/acc2.out && grep -qx "RESULT: 0 failed" /tmp/acc2.out
```
```bash
cd /srv/work && git diff --name-only -- Infra/iot/expresso > /tmp/acc3.out && grep -cvE "^Infra/iot/expresso/pico/(classes|functions|commands|main)\.py$" /tmp/acc3.out | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/classes.py pico/functions.py pico/commands.py pico/main.py testit/flow_ctrl_sim.py | wc -l) -le 2370
```
Mitattu lähtötaso `wc -l` commitissa b90be1c: 1106 + 520 + 149 + 335 = 2110 riviä, uusi
simulaatiotiedosto 0 — varaa 260 riviä.

## Stop
- `shot_test.py` on punainen jo ennen ensimmäistä muokkausta.
- Luvun 6 väite 1 ei toteudu kahden viritysyrityksen jälkeen kohdan 7 sallimilla arvoilla.
- Spesifikaatio ja lähdekoodi ovat ristiriidassa (rivinumero tai nimi ei vastaa).

Kysy tällöin täsmälleen yksi kysymys ja lopeta vuorosi. Älä laajenna `may:`-listaa, älä koske
laitteeseen: tässä paketissa ei ajeta `pico_dev.py`:tä eikä flashata mitään.

## Report
```text
brief: VIRTAUSSAATO
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/2370
iterations: <viritysyritysten määrä>
note: <yksi rivi: mitkä kp/ki/rate-arvot jäivät voimaan>
```
