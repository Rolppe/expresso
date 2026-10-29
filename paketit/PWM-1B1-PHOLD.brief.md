# PWM-1B1-PHOLD

## Task
Lisää firmwareen komento `phold:<s>`, joka ajaa pumppua ja venttiiliä vapaasti ja tulostaa 500 ms
välein paineen ja sen muutosnopeuden, jotta kuristin voidaan kääntää tasapainoon ennen vaihetta 1b.

## Files
may:
- `Infra/iot/expresso/pico/classes.py`, `pico/functions.py`, `pico/main.py`, `pico/commands.py`
- `Infra/iot/expresso/pico_dev.py`, `Infra/iot/expresso/PICO-HALLINTA.md`

must not:
- `Infra/iot/expresso/testit/` ja `paketit/` kokonaan
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/paketit/PWM-1B1-PHOLD.spec.md` kokonaan — tuloste ja silmukan säännöt
- `pico/functions.py` rivit 533-556, 568-620, 707-724
- `pico/classes.py` rivit 129-131, 472-486; `pico/main.py` rivit 180-190
- `pico/commands.py` rivit 94-110; `pico_dev.py` rivit 10-18, 178-196, 244-262

## Do
1. Lue spec ja rivivälit. `pcap:` on tarkka malli joka askeleelle.
2. `classes.py`: `phold_request` / `phold_abort` rivien 129-131 malliin; metodit
   `request_pressure_hold(seconds)`, `take_pressure_hold_request()`, `stop_pressure_hold()`
   rivien 472-486 malliin, spec kohta 2.6.
3. `functions.py`: `PHOLD_PRINT_MS`, `PHOLD_MAX_S` ja
   `async def pressure_hold_run(brew_data, utime, asyncio, seconds)` spec kohtien 1-2 mukaan.
   Käytä vakioita `PCAP_RAW_A/B`, `PCAP_OVER_BAR`, `PCAP_FILT_TAU`; älä kirjoita niitä uudelleen.
4. `main.py`: tuonti riville 19, ajo rivien 183-185 malliin.
5. `commands.py`: lohko `phold:` rivien 94-108 malliin; `phold:stop` pysäyttää.
6. `pico_dev.py`: operaatio `phold <s> [out.log]` — yksi `Link()`, `CMD phold:<s>`, kaappaus samalta
   yhteydeltä `stop_marker=b'PHOLD_END'`, aikakatkaisu `<s> + 20`. Epänolla paluuarvo, jos
   `PHOLD_END` puuttuu tai `reason=` on muu kuin `ok` tai `stop`. Rivi käyttöohjeeseen.
7. `PICO-HALLINTA.md`: rivi luvun 4 taulukkoon, tunnisteet `PHOLD_START|PHOLD|PHOLD_END` lukuun 10.
8. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico/classes.py pico/functions.py pico/main.py pico/commands.py pico_dev.py
```
```bash
cd /srv/work/Infra/iot/expresso && python3 pico_dev.py 2>&1 | grep -q "phold <s>"
```
```bash
cd /srv/work/Infra/iot/expresso/pico && python3 - <<'PY'
import sys, inspect
sys.path.insert(0, '.')
import functions as F, classes as C
f = []
s = inspect.getsource(F.pressure_hold_run)
if s.index('RELAY_SOLENOID.value(1)') > s.index('RELAY_PUMP.value(1)'): f.append('venttiili pumpun jalkeen')
if 'finally' not in s or 'RELAY_PUMP.value(0)' not in s: f.append('ei finally-sammutusta')
for t in ('PHOLD_START','PHOLD_END','slope=','PCAP_OVER_BAR','PCAP_FILT_TAU','sleep_ms','dev_safe','phold_abort'):
    if t not in s: f.append('puuttuu: ' + t)
for m in ('request_pressure_hold','take_pressure_hold_request','stop_pressure_hold'):
    if not hasattr(C.BrewData, m): f.append('BrewData.' + m)
if F.PHOLD_MAX_S != 120: f.append('PHOLD_MAX_S != 120')
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f))
sys.exit(1 if f else 0)
PY
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "(classes|functions|main|commands|pico_dev)\.py$|PICO-HALLINTA\.md$" | wc -l | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/classes.py pico/functions.py pico/main.py pico/commands.py pico_dev.py PICO-HALLINTA.md | wc -l) -le 3320
```
Mitattu `wc -l`, commit `ebb7eec`: 3172 riviä — varaa 148.

## Stop
- `classes.py`:n rivien 472-486 metodit eivät ole luokassa `BrewData`, tai `main.py`:n rivit
  183-185 eivät vastaa kuvausta.
- `brew_data.get_relays()` ei palauta kolmea relettä.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: PWM-1B1-PHOLD
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/3320
iterations: <yritysten määrä>
note: <yksi rivi>
```
