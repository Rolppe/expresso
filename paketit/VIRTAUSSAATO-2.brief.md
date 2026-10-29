# VIRTAUSSAATO-2

## Task
Muuta uuttovaiheen virtaussäätö kaskadista suoraksi duty-ohjaukseksi ja laajenna simulaatio koko
venttiilialueelle täsmälleen niin kuin `paketit/VIRTAUSSAATO-2.spec.md` määrää.

## Files
may:
- `Infra/iot/expresso/pico/classes.py`
- `Infra/iot/expresso/pico/functions.py`
- `Infra/iot/expresso/testit/flow_ctrl_sim.py`

must not:
- `Infra/iot/expresso/testit/shot_test.py` (regressiomitta)
- `Infra/iot/expresso/pico/commands.py`, `main.py`, `scale.py`, `devsafe.py`, `MANIFEST.json`
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/paketit/VIRTAUSSAATO-2.spec.md`, `VIRTAUSSAATO-2.md`
- `Infra/iot/expresso/pico/classes.py`, `functions.py`
- `Infra/iot/expresso/testit/flow_ctrl_sim.py`, `shot_test.py`

## Do
1. Lue spec ja paketti, sitten `classes.py:630-848` (`PumpPressureController` ja nykyinen
   `FlowController`) ja `functions.py:197-258`.
2. Kirjoita `FlowController` uudelleen spesifikaation luvun 1 mukaisesti (duty ulos, paineikatto,
   `p_min`/`lead`/`rate_bar_s` pois).
3. Lisää `PumpPressureController.apply_duty` spesifikaation luvun 2 mukaisesti.
4. Muuta `run_shot`in kutsut ja lokirivi spesifikaation luvun 3 mukaisesti.
5. Muuta simulaation `k`-aikataulu, kesto ja väitteet spesifikaation luvun 4 mukaisesti.
6. Viritä vain `kp` ja `ki` niin että väitteet toteutuvat. Älä muuta `p_max`, `p_margin` tai
   väitteiden lukuja.
7. Aja `## Acceptance` ja `## Budget` ja korjaa vain se, minkä ne raportoivat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && rm -rf /tmp/fw && mkdir -p /tmp/fw && cp pico/*.py pico/scale_cal.json /tmp/fw/ && cp -r pico/lib /tmp/fw/ && python3 testit/shot_test.py > /tmp/acc1.out && grep -qx "RESULT: 0 failed" /tmp/acc1.out
```
```bash
cd /srv/work/Infra/iot/expresso && python3 testit/flow_ctrl_sim.py > /tmp/acc2.out && grep -qx "RESULT: 0 failed" /tmp/acc2.out
```
```bash
cd /srv/work && git diff --name-only -- Infra/iot/expresso > /tmp/acc3.out && grep -cvE "^Infra/iot/expresso/(pico/(classes|functions)\.py|testit/flow_ctrl_sim\.py)$" /tmp/acc3.out | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/classes.py pico/functions.py testit/flow_ctrl_sim.py | wc -l) -le 2000
```
Mitattu lähtötaso (`wc -l`, commit 4c18f62): `classes.py` 1210 + `functions.py` 536 +
`flow_ctrl_sim.py` 139 = 1885 riviä — varaa 115 riviä, koska muutos poistaa rakenteita
(`p_min`, `lead`, rampitus) yhtä paljon kuin lisää.

## Stop
- `shot_test.py` on punainen jo ennen ensimmäistä muokkausta.
- Jokin luvun 4 väite ei toteudu kahden viritysyrityksen jälkeen pelkillä `kp`/`ki`-arvoilla.
- Spesifikaatio ja lähdekoodi ovat ristiriidassa.

Kysy tällöin täsmälleen yksi kysymys ja lopeta vuorosi. Älä laajenna `may:`-listaa äläkä koske
laitteeseen: tässä paketissa ei ajeta `pico_dev.py`:tä eikä flashata mitään.

## Report
```text
brief: VIRTAUSSAATO-2
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/2000
iterations: <viritysyritysten määrä>
note: <yksi rivi: mitkä kp/ki-arvot jäivät voimaan>
```
