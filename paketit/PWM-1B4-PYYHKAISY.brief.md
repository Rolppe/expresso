# PWM-1B4-PYYHKAISY

## Task
Kirjoita `psweep:<ms>:<bar>[:<n>]`, joka ajaa kaikki vaihesiirrot yhden asettumisen sisällä
trimmausaskelin, ja korjaa kaappauksen jälkeinen kaukalovahdin tarkistus hakemaan tuore lukema.

## Files
may:
- `Infra/iot/expresso/pico/functions.py`, `pico/commands.py`, `pico/classes.py`, `pico/main.py`
- `Infra/iot/expresso/pico_dev.py`, `Infra/iot/expresso/PICO-HALLINTA.md`

must not:
- `Infra/iot/expresso/testit/` kokonaan — siellä ovat suunnittelijan holdoutit
- `Infra/iot/expresso/paketit/` kokonaan
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/paketit/PWM-1B4-PYYHKAISY.spec.md` kokonaan
- `Infra/iot/expresso/paketit/PUMPPU-PWM.md` luku "Vaihe 1b:n pyyhkäisy" (säännöt 10-13)
- `pico/functions.py` rivit 533-570, 604-812; `pico/commands.py` rivit 94-125;
  `pico/classes.py` rivit 129-134, 476-506; `pico/main.py` rivit 185-200;
  `pico_dev.py` rivit 180-200, 265-275
- `Infra/iot/expresso/testit/psweep_smoke.py` kokonaan — se on hyväksynnän mitta

## Do
1. Lue spec ja holdout. Holdout kertoo tarkalleen, mitä rajapinnalta odotetaan.
2. `functions.py`: spec kohta 0 — irrota `pcap_settle`, lisää `TRAY_RESYNC_MS` ja
   `tray_guard_recheck`, ja ota jälkimmäinen käyttöön myös `pressure_capture_run`:n
   kaappauksen jälkeisessä tarkistuksessa. Vanhojen holdoutien on pysyttävä vihreinä.
3. `functions.py`: spec kohta 1 — vakiot ja `psweep_phases(n)`.
4. `functions.py`: spec kohdat 2-3 — `pressure_sweep_run` ja segmenttien tuloste.
5. `functions.py`: spec kohta 4 — trimmausaskel segmenttien väliin.
6. `commands.py` ja `classes.py`: spec kohta 5; `main.py`: sama kolmen rivin kuvio kuin
   `pcap`-pyynnöllä.
7. `pico_dev.py` ja `PICO-HALLINTA.md`: spec kohta 6.
8. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico/functions.py pico/commands.py pico/classes.py pico/main.py pico_dev.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/psweep_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 180 python3 testit/pskip_gate_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 180 python3 testit/phold_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 180 python3 testit/tray_guard_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && python3 pico_dev.py 2>&1 | grep -q "psweep"
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "(functions|commands|classes|main|pico_dev)\.py$|PICO-HALLINTA\.md$" | wc -l | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/functions.py pico/commands.py pico/classes.py pico/main.py pico_dev.py PICO-HALLINTA.md | wc -l) -le 3620
```
Mitattu `wc -l`, commit `9144894`: 1085+247+1296+355+281+165 = 3429 — varaa 191 riviä.

## Stop
- `pcap_settle`-irrotus ei onnistu ilman `pressure_capture_run`:n käyttäytymisen muuttamista,
  eli jokin vanha holdout jää punaiseksi siitä syystä.
- Holdout `psweep_smoke.py` vaatii jotain, mikä on ristiriidassa spec:n kanssa — kerro kumpi
  kohta ja lopeta vuorosi. Älä muuta holdoutia.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: PWM-1B4-PYYHKAISY
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/3620
iterations: <yritysten määrä>
note: <yksi rivi: montako pumpun reunaa holdout mittasi portitetuissa segmenteissä>
```
