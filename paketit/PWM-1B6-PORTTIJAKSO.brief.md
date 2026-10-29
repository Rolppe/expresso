# PWM-1B6-PORTTIJAKSO

## Task
Tee portin jaksosta mittausparametri (`psweep:<ms>:<bar>[:<n>[:<mult>]]`) ja lue pyyhkäisyn tuomio
viiveen hajonnasta taitosbinin mitalla.

## Files
may:
- `Infra/iot/expresso/pico/functions.py`, `pico/commands.py`, `pico/classes.py`
- `Infra/iot/expresso/pico_dev.py`, `Infra/iot/expresso/PICO-HALLINTA.md`
- `Infra/iot/expresso/testit/psweep_read.py`

must not:
- `Infra/iot/expresso/testit/` muut tiedostot — ne ovat suunnittelijan mittoja
- `Infra/iot/expresso/pico/main.py`, `paketit/` kokonaan
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/paketit/PWM-1B6-PORTTIJAKSO.spec.md` kokonaan
- `Infra/iot/expresso/paketit/PUMPPU-PWM.md` luku "Kuivaharjoitus 19.9.2026" (sääntö 14)
- `pico/functions.py` rivit 556-570, 818-830, 883-941; `pico/commands.py` rivit 97-125;
  `pico/classes.py` rivit 129-140, 476-510; `testit/psweep_read.py` kokonaan
- `Infra/iot/expresso/testit/psweep_mult_smoke.py` kokonaan — se on hyväksynnän mitta

## Do
1. Lue spec ja holdout. Holdout kertoo tarkalleen, mitä rajapinnalta odotetaan.
2. `functions.py`: spec kohta 1 — vakiot, `pcap_gate`:n ja `psweep_phases`:n kolmas parametri
   oletuksineen. Oletuspolun on pysyttävä sanatarkasti entisenä.
3. `functions.py`: spec kohta 2 — `pressure_sweep_run` lukee kertoimen, laskee jakson ja vie sen
   portitukseen, vaihesiirtoihin ja otsikoihin.
4. `commands.py` ja `classes.py`: spec kohta 3.
5. `pico_dev.py` ja `PICO-HALLINTA.md`: spec kohta 3:n viimeinen kappale.
6. `psweep_read.py`: spec kohta 4 — `delay_mean_ms`, `delay_spread_ms` ja tuomio niistä.
7. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico/functions.py pico/commands.py pico/classes.py pico_dev.py testit/psweep_read.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/psweep_mult_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 900 python3 testit/psweep_fixture.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 400 python3 testit/psweep_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 180 python3 testit/pskip_gate_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 180 python3 testit/tray_guard_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/psweep_read.py --selftest
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "(functions|commands|classes|pico_dev)\.py$|PICO-HALLINTA\.md$|testit/psweep_read\.py$" | wc -l | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/functions.py pico/commands.py pico/classes.py pico/main.py pico_dev.py PICO-HALLINTA.md testit/psweep_read.py | wc -l) -le 3925
```
Mitattu `wc -l`, commit `2d8d71f`: 1209+268+1317+360+300+166+233 = 3853 — varaa 72 riviä.

## Stop
- Holdout vaatii jotain, mikä on ristiriidassa spec:n kanssa — kerro kumpi kohta ja lopeta
  vuorosi. Älä muuta holdoutia.
- Kertoimen vienti `_pcap_capture`:een ei onnistu ilman `pressure_capture_run`:n käyttäytymisen
  muuttamista.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: PWM-1B6-PORTTIJAKSO
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/3925
iterations: <yritysten määrä>
note: <yksi rivi: mika duty holdout mittasi portin jaksolla 8 x verkkojakso>
```
