# PWM-1B5-INVARIANTTI

## Task
Kirjoita `testit/psweep_read.py`, joka lukee pyyhkäisylokin invariantin verkkojakson modulolla,
ja ota Goertzelin vaihe käyttöön `mains_freq.py`:ssä.

## Files
may:
- `Infra/iot/expresso/testit/mains_freq.py`
- `Infra/iot/expresso/testit/psweep_read.py` (uusi tiedosto)

must not:
- `Infra/iot/expresso/testit/psweep_fixture.py`, `pskip_fixture.py`, `pskip_delay.py`,
  `pskip_gate_smoke.py`, `psweep_smoke.py` — nämä ovat suunnittelijan mittoja
- `Infra/iot/expresso/pico/` ja `Infra/iot/expresso/paketit/` kokonaan
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/paketit/PWM-1B5-INVARIANTTI.spec.md` kokonaan
- `Infra/iot/expresso/paketit/PUMPPU-PWM.md` luku "Vaihe 1b:n pyyhkäisy" (säännöt 9-12)
- `testit/mains_freq.py` kokonaan; `testit/pskip_delay.py` rivit 40-120, 170-251
- `Infra/iot/expresso/testit/psweep_fixture.py` kokonaan — se on hyväksynnän mitta

## Do
1. Lue spec ja holdout. Holdout kertoo tarkalleen, mitä tulosteelta odotetaan.
2. `mains_freq.py`: spec kohta 1 — `goertzel`, `goertzel_amp` sen ohueksi kääreeksi,
   `refine_peak`. Vanhan tulosteen on pysyttävä sananmukaisesti samana.
3. `psweep_read.py`: spec kohta 2.1 — segmentointi ja segmenttikohtainen kalibrointi.
4. `psweep_read.py`: spec kohdat 2.2-2.3 — taitos ja `PSKIP_INV`, invariantti verkkojakson
   modulolla.
5. `psweep_read.py`: spec kohta 2.4 — `PSWEEP_REF` ja `PSWEEP_MAINS` referenssisegmenteistä.
6. `psweep_read.py`: spec kohdat 2.5-2.6 — ympyräkeskiarvo, `verdict`, torjunta.
7. `psweep_read.py`: spec kohta 3 — `--selftest`.
8. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile testit/mains_freq.py testit/psweep_read.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 900 python3 testit/psweep_fixture.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/psweep_read.py --selftest
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/pskip_fixture.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 180 python3 testit/mains_freq.py --selftest
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/pskip_delay.py --selftest
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "testit/(mains_freq|psweep_read)\.py$" | wc -l | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat testit/mains_freq.py testit/pskip_delay.py testit/psweep_read.py | wc -l) -le 720
```
Mitattu `wc -l`, commit `fe84baf`: 210+251 = 461, uusi tiedosto mahtuu 259 riviin.

## Stop
- Holdout `psweep_fixture.py` vaatii jotain, mikä on ristiriidassa spec:n kanssa — kerro kumpi
  kohta ja lopeta vuorosi. Älä muuta holdoutia.
- `goertzel_amp`:n kääreeksi tekeminen muuttaa `pskip_fixture.py`:n tulosta.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: PWM-1B5-INVARIANTTI
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/720
iterations: <yritysten määrä>
note: <yksi rivi: PSWEEP_INV spread_ms holdoutin nimellistaajuisesta lokista>
```

## Korjaus 1 (suunnittelija, ei uutta ajoa)
`goertzel_amp`:n kommentti väitti paluuarvoa bittitarkasti samaksi kuin vanha kaava. Mitattu:
200 satunnaissyötteestä 125 eroaa viimeisessä ulp:ssä, suurin suhteellinen ero 1,3e-15.
Muoto on algebrallisesti sama, ei bittitarkasti; kommentti korjattu sanomaan se.
