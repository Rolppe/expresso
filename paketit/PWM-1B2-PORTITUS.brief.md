# PWM-1B2-PORTITUS

## Task
Laajenna `pcap:`-kaappaus ohittamaan joka toinen verkkojakso annetulla vaihesiirrolla, ja lisää
anturin elävä kalibrointi `PCAP_START`-riville.

## Files
may:
- `Infra/iot/expresso/pico/functions.py`, `pico/commands.py`
- `Infra/iot/expresso/pico_dev.py`, `Infra/iot/expresso/PICO-HALLINTA.md`

must not:
- `Infra/iot/expresso/testit/` kokonaan — sielläkin oleva holdout on suunnittelijan todiste
- `Infra/iot/expresso/pico/classes.py`, `pico/main.py`, `paketit/` kokonaan
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/paketit/PWM-1B2-PORTITUS.spec.md` kokonaan
- `Infra/iot/expresso/paketit/PUMPPU-PWM.md` luku "Vaihe 1b — säännöt" (säännöt 5-6)
- `pico/functions.py` rivit 533-556, 556-570, 676-712; `pico/commands.py` rivit 94-110
- `Infra/iot/expresso/testit/pskip_gate_smoke.py` kokonaan — se on hyväksynnän mitta

## Do
1. Lue spec, säännöt ja holdout. Holdout kertoo tarkalleen, mitä rajapinnalta odotetaan.
2. `functions.py`: vakiot `PCAP_MAINS_US`, `PCAP_GATE_PERIOD_US` ja moduulitason funktio
   `pcap_gate(i, phase_us)` spec kohtien 1-2 mukaan.
3. `functions.py`: lue vaihesiirto `brew_data`:lta samalla tavalla kuin `pcap_target_bar`
   (rivi 561), ja sovella porttia **vain** kaappaussilmukassa spec kohdan 3 mukaan — kutsu
   `RELAY_PUMP.value(g)` vain kun arvo muuttuu.
4. `functions.py`: `PCAP_START`-rivi spec kohdan 4 mukaan, `gain`/`offset` mukaan lukien.
5. `commands.py`: kolmas kenttä spec kohdan 4 mukaan; se vaatii toisen kentän ja nollautuu
   `None`:ksi joka pyynnöllä, myös `pcap:stop`:lla ja virheellisellä syötteellä.
6. `pico_dev.py`: päivitä käyttöohjerivi muotoon `pcap <ms>[:<bar>[:<phase_us>]]`.
   `PICO-HALLINTA.md`: sama luvun 4 taulukkoon.
7. Varmista spec kohta 5: `pcap:<ms>` ja `pcap:<ms>:<bar>` ajautuvat kuten ennen.
8. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico/functions.py pico/commands.py pico_dev.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 180 python3 testit/pskip_gate_smoke.py | tail -1 | grep -qx "RESULT: 0 failed"
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 120 python3 testit/phold_smoke.py | tail -1 | grep -qx "RESULT: 0 failed"
```
```bash
cd /srv/work/Infra/iot/expresso && python3 pico_dev.py 2>&1 | grep -q "phase_us"
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "(functions|commands|pico_dev)\.py$|PICO-HALLINTA\.md$" | wc -l | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/functions.py pico/commands.py pico_dev.py PICO-HALLINTA.md | wc -l) -le 1760
```
Mitattu `wc -l`, commit `8614f48`: 990+234+280+161 = 1665 — varaa 95 riviä.

## Stop
- Kaappaussilmukan `for i in range(n)` ei ole enää riveillä 676-712 siinä muodossa, jossa
  näytteen järjestysnumero `i` on käytettävissä.
- Holdout `pskip_gate_smoke.py` vaatii jotain, mikä on ristiriidassa spec:n kanssa — kerro kumpi
  kohta ja lopeta vuorosi. Älä muuta holdoutia.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: PWM-1B2-PORTITUS
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/1760
iterations: <yritysten määrä>
note: <yksi rivi: montako pumpun reunaa holdout mittasi 1,2 s kaappauksessa>
```
