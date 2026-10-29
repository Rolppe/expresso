# PWM-1A-VERKKOTAAJUUS — korjaus 1

Hyväksyntä oli vihreä 4/4 ja budjetti 2797/2800 myös suunnittelijan omassa ajossa. Nämä kolme
vikaa löytyivät vasta koodia lukemalla. Viat 1 ja 2 ovat **briefin vikoja**, eivät sinun: briefin
`## Do` kohta 4 on korjattu ennen tätä kierrosta, ja korjattu teksti on se, jota noudatat.

`may:`-lista on ennallaan: vain `pico/functions.py` muuttuu tässä korjauksessa.

## Vika 1 — magneettiventtiili jää kiinni, pumppu ajaa umpeen

`pressure_capture_run` (`functions.py:540-605`) kytkee vain `RELAY_PUMP`:n. Jokainen muu pumppaava
polku avaa myös kolmitieventtiilin ennen pumppua: `pre_infusion` (`functions.py:24`), `run_shot`
(`192`), `pressure_calibration_run` (`375`), `fast_heatup` (`617`), ja jokainen sulkee sen
lopuksi (`282`, `295`, `466`, `512`, `621`).

Ilman sitä vesi ei pääse ryhmään: pumppu ajaa umpinaista piiriä, paine nousee sekunneissa
ylipainerajaan, eikä käyttäjä voi kuristimella pitää mittausta halutussa ~5 barissa. Mitattu
väreily olisi umpipiirin väreilyä, ei työskentelevän piirin — ja juuri sitä jälkimmäistä koko
paketti tarvitsee.

**Korjaus:** `RELAY_SOLENOID.value(1)` ennen `RELAY_PUMP.value(1)`:tä, ja `RELAY_SOLENOID.value(0)`
samassa `finally`-lohkossa kuin pumpun sammutus.

## Vika 2 — ylipaineraja ja `pmax` ohittavat anturin kalibroinnin

`PCAP_OVER_RAW = (11.0 + 3.522929) / 0.000314936` (`functions.py:537`) ja rivin 599 `pmax_bar`
käyttävät pelkkää tehdaskaavaa `raw*0.000314936 - 3.522929`. Todellinen paine on
`gain*raw_bar + offset` (`classes.py:930,948`). Voimassa oleva kalibrointi on
`gain=1,0000 offset=-0,990` (`Infra/paarekisteri.md:950`), joten nykyinen raja laukeaa noin
**10,0 todellisessa barissa**, ei 11,0:ssa, ja `pmax=` aliraportoi noin barin verran. Suunta on
turvallinen, mutta luku on väärä eikä kestä kalibroinnin muuttumista.

**Korjaus:** laske raja ajonaikaisesti anturin omista arvoista — raaka kynnys on se `raw`, jolla
`sensor.gain * (raw*0.000314936 - 3.522929) + sensor.offset` ylittää 11,0 — ja raportoi `pmax`
samalla kalibroidulla muunnoksella. Käytä `brew_data.pressure_sensor`in `gain`- ja
`offset`-kenttiä, älä kovakoodaa niitä.

## Vika 3 — tulostussilmukka ei anna vahtikoiralle vuoroa

Kaappauksen jälkeinen silmukka (`functions.py:601-604`) tulostaa jopa 125 riviä USB-sarjaan
ilman yhtään `await`ia, heti perään 2,5 s:n estävästä kaappauksesta. Vahtikoira on 8 s ja sitä
ruokitaan omasta taskistaan 1 s välein (`main.py:318-322`), joka ei saa vuoroa kummankaan aikana.

**Korjaus:** `await asyncio.sleep_ms(0)` joka kymmenennen rivin jälkeen. Samalla `PCAP_START`-rivin
`rate=1000` lasketaan `PCAP_RATE_US`:stä kovakoodatun luvun sijaan, jotta protokollan rivi ei
valehtele jos jakso muuttuu.

## Acceptance

Kaikki briefin neljä komentoa uudelleen, ja lisäksi tämä rakennetarkistus:

```bash
cd /srv/work/Infra/iot/expresso && python3 - <<'PY'
import re, sys
src = open('pico/functions.py').read()
body = src[src.index('async def pressure_capture_run'):]
body = body[:body.index('\ndef ') if '\ndef ' in body else len(body)]
body = body[:body.index('\nasync def ') if '\nasync def ' in body else len(body)]
fails = []
if 'RELAY_SOLENOID.value(1)' not in body: fails.append('solenoidia ei avata')
if 'RELAY_SOLENOID.value(0)' not in body: fails.append('solenoidia ei suljeta')
if not re.search(r'\.gain', body + src[:src.index('async def pressure_capture_run')][-2000:]): fails.append('kalibroinnin gain ei ole kaytossa')
if 'sleep_ms(0)' not in body: fails.append('tulostussilmukka ei anna vuoroa')
for f in fails: print('FAIL ' + f)
print('RESULT: %d failed' % len(fails))
sys.exit(1 if fails else 0)
PY
```

## Report

Sama kuusirivinen muoto kuin briefissä, `iterations: 2`.
