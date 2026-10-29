# EXPRESSO-KAUKALOVAHTI

## Task
Lisää kaukalon painovahti kehityskomentoihin `phold` ja `pcap` niin, ettei kumpikaan käynnisty,
jos kaukaloa ei voi nähdä, eikä jatka, jos raja ylittyy.

## Files
may:
- `Infra/iot/expresso/pico/functions.py`
- `Infra/iot/expresso/PICO-HALLINTA.md`

must not:
- `Infra/iot/expresso/testit/` kokonaan — siellä olevat holdoutit ovat suunnittelijan todisteita
- `pico/classes.py`, `pico/commands.py`, `pico/main.py`, `pico_dev.py`, `paketit/` kokonaan
- `run_shot` ja `tshot`-polku tiedostossa `functions.py` — käyttäjän oma uutto ei saa katketa
  painoon (spec kohta 0)

read:
- `Infra/iot/expresso/paketit/KAUKALOVAHTI.spec.md` kokonaan
- `Infra/iot/expresso/paketit/TURVAKATO.md` luku "Laukaisija" — miksi tämä brief on olemassa
- `pico/functions.py` rivit 145-182 (nykyinen vahti tshot-polulla), 604-640, 655-700, 727-812
- `Infra/iot/expresso/testit/tray_guard_smoke.py` kokonaan — se on hyväksynnän mitta

## Do
1. Lue spec, TURVAKATO:n laukaisija ja holdout. Holdout kertoo tarkalleen, mitä odotetaan.
2. `functions.py`: `TRAY_STALE_MS` ja funktiot `tray_guard_start` / `tray_guard_check` spec
   kohdan 1 mukaan. Kahden peräkkäisen näytteen sääntö kopioidaan rivien 169-176 muodosta.
3. Kytke vahti `pressure_hold_run`:iin: `tray_guard_start` ennen releitä, `tray_guard_check`
   joka kierros. Estetty ajo palauttaa syyn `PHOLD_END`-riville kytkemättä releitä.
4. Kytke vahti `pressure_capture_run`:iin spec kohdan 2 taulukon mukaan: alkutarkistus ennen
   releitä, tarkistus asettumis- ja pitosilmukassa, sekä juuri ennen ja heti jälkeen
   kaappaussilmukan — **ei kaappaussilmukan sisällä**, ks. spec kohdan 2 perustelu.
5. Varmista spec kohta 4: yksikään olemassa oleva keskeytysehto ei häviä eikä muutu, eikä
   `run_shot`-polkuun kosketa.
6. `PICO-HALLINTA.md`: lisää luvun 4 alle lyhyt maininta, että `phold` ja `pcap` vaativat
   toimivan vaa'an ja asetetun `wmax:`- tai `wrise:`-rajan, ja luettele syyt
   `noscale|nolimit|scalelost|tray|trayrise`.
7. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico/functions.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/tray_guard_smoke.py | tail -1 | grep -qx "RESULT: 0 failed"
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 120 python3 testit/phold_smoke.py | tail -1 | grep -qx "RESULT: 0 failed"
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/pskip_gate_smoke.py | tail -1 | grep -qx "RESULT: 0 failed"
```
```bash
cd /srv/work/Infra/iot/expresso/pico && python3 -c "import sys,inspect; sys.path.insert(0,'.'); import functions as F; s=inspect.getsource(F.run_shot); sys.exit(0 if 'tray_guard' not in s else 1)"
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "pico/functions\.py$|PICO-HALLINTA\.md$" | wc -l | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/functions.py PICO-HALLINTA.md | wc -l) -le 1250
```
Mitattu `wc -l`, commit `90ac4b8`: 990+161 = 1151 — varaa 99 riviä.

## Stop
- Vaakametodeja `get_weight`, `get_weight_ms`, `get_weight_limit`, `get_weight_rise_limit` ei ole
  `classes.py`:ssä siinä muodossa, jota spec olettaa.
- Holdout vaatii jotain, mikä on ristiriidassa spec:n kanssa — kerro kumpi kohta, älä muuta
  holdoutia.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: EXPRESSO-KAUKALOVAHTI
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/1250
iterations: <yritysten määrä>
note: <yksi rivi: mihin kohtaan kaappaussilmukan ympärillä tarkistukset tulivat>
```
