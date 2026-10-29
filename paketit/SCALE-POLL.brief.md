# EXPRESSO-SCALE-POLL

## Task
Nimeä vaa'an lukutahti vakioksi `SCALE_POLL_MS` ja aseta se 20 ms:stä **50 ms:iin** (käyttäjän
päätös 19.9.2026), johdanto kommenttiin.

## Files
may:
- `Infra/iot/expresso/pico/main.py`

must not:
- `Infra/iot/expresso/testit/` kokonaan, `pico/scale.py`, `pico/functions.py`, `pico/classes.py`,
  `pico/commands.py`, `pico_dev.py`, `paketit/` kokonaan
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `pico/main.py` rivit 300-330 (`scale_reader`)
- `pico/scale.py` rivit 6-20 (virtausikkunan vakiot ja niiden johdanto)
- `Infra/iot/expresso/testit/scale_rate_smoke.py` kokonaan — se on hyväksynnän mitta

## Do
1. Lue rivivälit ja holdout. Holdout kertoo, mitkä invariantit tahdin on täytettävä.
2. Lisää `main.py`:hyn moduulitason vakio `SCALE_POLL_MS = 50` lähelle muita moduulitason
   asetuksia, ja käytä sitä `scale_reader`:n `await asyncio.sleep_ms(...)`-kutsussa literaalin
   `20` sijaan.
3. Kirjoita vakion viereen kommentti, joka nimeää johdannon **luvuilla, ei väitteillä**:
   anturi tuottaa 11,6 näytettä sekunnissa (`scale.py` rivi 7), eli näyteväli on noin 86 ms;
   50 ms nappaa jokaisen näytteen; `FLOW_MIN_POINTS=4` näytettä mahtuu `FLOW_WINDOW_MS=1000`
   ikkunaan kaksinkertaisella marginaalilla; yksi väliin jäänyt luenta ei ylitä
   `FLOW_STALE_MS=500`; kaukalovahti (`TRAY_STALE_MS=2000`) ehtii nähdä kaksi näytettä.
4. Älä muuta mitään muuta `scale_reader`:ssä: `update()`:n paluuarvon käsittely, `weight_ms`:n
   päivitys ja `flow()`-kutsu joka kierroksella pysyvät ennallaan.
5. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico/main.py
```
```bash
cd /srv/work/Infra/iot/expresso && python3 testit/scale_rate_smoke.py | tail -1 | grep -qx "RESULT: 0 failed"
```
```bash
cd /srv/work/Infra/iot/expresso && grep -c "sleep_ms(20)" pico/main.py | grep -qx 0
```
```bash
cd /srv/work/Infra/iot/expresso && python3 -c "import re,sys; s=open('pico/main.py').read(); b=s[s.index('async def scale_reader'):]; b=b[:b.index('async def', 10)]; sys.exit(0 if 'SCALE_POLL_MS' in b and 'weight_ms' in b and 'flow(' in b else 1)"
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "pico/main\.py$" | wc -l | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(wc -l < pico/main.py) -le 365
```
Mitattu `wc -l`, commit `53994bc`: `main.py` 349 — varaa 16 riviä.

## Stop
- `scale_reader` ei ole `main.py`:ssä siinä muodossa, jossa `sleep_ms`-kutsu on sen oma.
- Holdout vaatii jotain, mikä on ristiriidassa `scale.py`:n vakioiden kanssa — kerro mikä, älä
  muuta holdoutia äläkä `scale.py`:tä.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: EXPRESSO-SCALE-POLL
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit>/365
iterations: <yritysten määrä>
note: <yksi rivi>
```
