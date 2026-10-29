# PWM-1G-TAAJUUSKALIBROINTI

## Task
Kirjoita `mains_calibrate`, joka purkaa paineen käyttäjän syklillä ja mittaa verkkotaajuuden ja
sen vaiheen pumpun omasta paineväreilystä laitteella, sekä komento `mcal:<ms>`.

## Files
may:
- `Infra/iot/expresso/pico/functions.py`, `pico/commands.py`, `pico/classes.py`, `pico/main.py`

must not:
- `Infra/iot/expresso/testit/` kokonaan — siellä ovat suunnittelijan mitat
- `Infra/iot/expresso/paketit/` kokonaan, `pico_dev.py`, `PICO-HALLINTA.md`
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/paketit/PWM-1G-TAAJUUSKALIBROINTI.spec.md` kokonaan
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md` luku 2b (TILAUS-F, -G, -H, käyttäjän sanat)
- `pico/functions.py` rivit 533-570, 706-760; `pico/commands.py` rivit 97-135;
  `pico/classes.py` rivit 129-145, 476-515; `pico/main.py` rivit 185-205
- `Infra/iot/expresso/testit/mcal_smoke.py` kokonaan — se on hyväksynnän mitta

## Do
1. Lue spec ja holdout. Holdout ajaa koodisi laitosmallia vasten; se on mitta, ei muotoseikka.
2. `functions.py`: spec kohta 2 — vakiot `MCAL_VENT_ON_MS`, `MCAL_VENT_OFF_MS` ja purkusykli.
3. `functions.py`: spec kohta 3 kohdat 1-3 — keskeytysehdot, releiden järjestys, näytteenotto.
4. `functions.py`: spec kohta 3 kohdat 4-6 — virtaava Goertzel, hila, paraabeli, vaihe, `conf`.
5. `functions.py`: spec kohta 3 kohta 7 — tallennus `brew_data`-kenttiin ja `MAINSCAL`-rivi.
6. `commands.py`, `classes.py` ja `main.py`: spec kohta 4.
7. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico/functions.py pico/commands.py pico/classes.py pico/main.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 600 python3 testit/mcal_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 400 python3 testit/psweep_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/psweep_mult_smoke.py
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
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "pico/(functions|commands|classes|main)\.py$" | wc -l | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/functions.py pico/commands.py pico/classes.py pico/main.py | wc -l) -le 3290
```
Mitattu `wc -l`, commit `e8a5012`: 1237+280+1329+326 = 3172 — varaa 118 riviä.

## Stop
- Holdout vaatii jotain, mikä on ristiriidassa spec:n kanssa — kerro kumpi kohta ja lopeta
  vuorosi. Älä muuta holdoutia.
- Virtaava Goertzel ei mahdu näytteiden väliin (1000 µs) laitteella niin, että ajoitus pettää.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: PWM-1G-TAAJUUSKALIBROINTI
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/3290
iterations: <yritysten määrä>
note: <yksi rivi: mika taajuus holdoutin 50,30 Hz mallista mitattiin>
```
