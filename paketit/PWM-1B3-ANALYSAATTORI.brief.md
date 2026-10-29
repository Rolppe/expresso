# PWM-1B3-ANALYSAATTORI

## Task
Kirjoita `testit/pskip_delay.py`, joka lukee portitetun pcap-lokin ja tulostaa viiveen pumpulta
paineanturille, ja korjaa `mains_freq.py`:n DRIFT-rivin kalibrointivika.

## Files
may:
- `Infra/iot/expresso/testit/pskip_delay.py` (uusi)
- `Infra/iot/expresso/testit/mains_freq.py`

must not:
- `Infra/iot/expresso/pico/` ja `paketit/` kokonaan, `pico_dev.py`
- `Infra/iot/expresso/testit/pskip_fixture.py` — suunnittelijan holdout, älä muokkaa sitä
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella
- lokitiedostot `testit/pcap-*.log` — ne ovat mittausaineistoa, ei muokattavaa

read:
- `Infra/iot/expresso/paketit/PWM-1B3-ANALYSAATTORI.spec.md` kokonaan
- `Infra/iot/expresso/testit/mains_freq.py` kokonaan
- `Infra/iot/expresso/testit/pskip_fixture.py` kokonaan — holdout, hyväksynnän mitta
- `Infra/iot/expresso/paketit/PUMPPU-PWM.md` luku "Vaihe 1b — säännöt" (säännöt 5, 6, 8 ja
  protokollalisäys)

## Do
1. Lue spec ja `mains_freq.py` kokonaan. Analysaattori **tuo** `parse_log`- ja `goertzel_amp`
   -funktiot `mains_freq`:stä samasta hakemistosta; jäsennintä ei kopioida.
2. Korjaa `mains_freq.py` spec kohdan 4 mukaan: `parse_log` palauttaa `gain`/`offset`
   `PCAP_START`-riviltä, `drift()` ottaa ne argumentteina, `print_result` merkitsee `(cal=raw)`
   kun kalibrointia ei ole. Nykyisten kutsujien on toimittava ennallaan.
3. Kirjoita `testit/pskip_delay.py`: käyttöohje-docstring (myös sääntö 5:n varaus siitä, mitä
   `PSKIP_DELAY` mittaa), `python3 pskip_delay.py <loki.log>` ja `--selftest`.
4. Toteuta laskenta spec kohdan 2 mukaan: elävä kalibrointi, boxcar-jäännös, taitto nimellisellä
   1000 µs näytevälillä, spektri todellisella `fs`:llä.
5. Toteuta tuloste spec kohdan 1 mukaan, myös `PSKIP_NOGATE`- ja `PSKIP_UNDECIDED`-tapaukset.
6. Toteuta `--selftest` spec kohdan 3 mukaan: neljä väitettä, `RESULT: <n> failed`, epänolla
   paluuarvo jos punaisia.
7. Aja holdout `python3 testit/pskip_fixture.py`: se rakentaa omat fikstuurinsa ja ajaa
   analysaattorin niitä vasten. Sen kuusi väitettä ovat tämän briefin varsinainen mitta.
8. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso/testit && python3 pskip_delay.py --selftest | tee /tmp/b3.out && grep -qx "RESULT: 0 failed" /tmp/b3.out
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/pskip_fixture.py | tail -1 | grep -qx "RESULT: 0 failed"
```
```bash
cd /srv/work/Infra/iot/expresso/testit && python3 mains_freq.py --selftest | tail -1 | grep -qx "RESULT: 0 failed"
```
```bash
cd /srv/work/Infra/iot/expresso/testit && python3 mains_freq.py pcap-20260919-8bar.log | grep "^DRIFT" | grep -q "cal=raw"
```
```bash
cd /srv/work/Infra/iot/expresso/testit && python3 pskip_delay.py pcap-20260919-8bar.log > /tmp/b4.out 2>&1; test $? -ne 0 && grep -q PSKIP_NOGATE /tmp/b4.out
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "testit/(pskip_delay|mains_freq)\.py$" | wc -l | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat testit/mains_freq.py testit/pskip_delay.py | wc -l) -le 540
```
Mitattu `wc -l`, commit `ebb7eec`: `mains_freq.py` 196 — uudelle tiedostolle ja korjaukselle
344 riviä.

## Stop
- `mains_freq.parse_log` ei ole tuotavissa ilman sivuvaikutuksia (moduulitason ajo).
- Spec kohdan 3 väite 1 ei mene läpi millään toteutuksella, koska 40 binin erottelukyky
  (998 µs) on karkeampi kuin vaadittu 2,0 ms — kerro silloin mitattu hajonta.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: PWM-1B3-ANALYSAATTORI
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/540
iterations: <yritysten määrä>
note: <yksi rivi: itsetestin suurin viive-ero millisekunteina>
```
