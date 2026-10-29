# PWM-1A-VERKKOTAAJUUS

## Task
Lisää firmwareen raaka paineen kaappaus `pcap:` ja analysaattori `testit/mains_freq.py` niin kuin
`paketit/PUMPPU-PWM.md` säännöt 2-4 ja sen kaksi viimeistä lukua määräävät.

## Files
may:
- `Infra/iot/expresso/pico/classes.py`, `commands.py`, `functions.py`, `main.py`
- `Infra/iot/expresso/testit/mains_freq.py` (uusi)

must not:
- `testit/shot_test.py`, `flow_ctrl_sim.py` (regressiomitat)
- `pico/MANIFEST.json`, `scale.py`, `devsafe.py`, `preset.py`
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/paketit/PUMPPU-PWM.md`
- `pico/classes.py` 120-130, 355-380, 440-465, 900-1011; `commands.py` 1-100;
  `functions.py` 330-400, 480-526; `main.py` 175-230, 272-339 (kaikki `Infra/iot/expresso/`)

## Do
1. Lue paketti ja rivivälit. Malli on `pressure_zero`-pari: pyyntö `BrewData`ssa, nosto
   pääsilmukassa, ajo `functions.py`:ssä.
2. `classes.BrewData`: `request_pressure_capture(ms)` (rajaus 200-2500, oletus 2000),
   `take_pressure_capture_request()`, `stop_pressure_capture()` — samalla kuviolla kuin
   `request_test_shot`/`take_test_shot_request` riveillä 362-376.
3. `commands.py`: haara `pcap:` — `pcap:<ms>` ja `pcap:stop` — muiden haarojen tyyliin.
4. `functions.py`: `async def pressure_capture_run(brew_data, utime, asyncio, ms)` — kieltäydy jos
   jokin kytkin on päällä tai `dev_safe`; **magneettiventtiili auki** ja pumppu päälle; 1000 ms
   asettuminen; yhtäjaksoinen silmukka, joka lukee `read_u16()` 1000 µs:n jaksolla
   `ticks_us()`-kohdistuksella `array('H')`-puskuriin; keskeytä yli 11,0 barissa **anturin
   kalibroidulla** arvolla (`gain`, `offset`); molemmat releet pois `finally`ssä; tulosta
   protokollaluvun rivit täsmälleen.
5. `main.py`: kutsu se pääsilmukasta samasta kohdasta kuin `pressure_zero_run` (rivit 179-180).
6. `testit/mains_freq.py`: loki argumenttina, näytetaajuus `PCAP_END`:n `dur_us`/`n`-suhteesta,
   lineaarinen trendi pois, Goertzel 40,0-70,0 ja 80,0-140,0 Hz, `MAINS`- ja `HARM2`-rivit ulos.
7. Sama tiedosto, `--selftest`: synteettinen puoliaaltopumppu 50,0 ja 60,0 Hz, kohina sd 0,25 bar,
   nousu 2 bar/2 s, 2000 näytettä — väitä kumpikin taajuus 0,5 Hz:n sisällä ja `conf` > 2,0.
   Viimeinen rivi `RESULT: <n> failed`.
8. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne raportoivat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 testit/mains_freq.py --selftest > /tmp/acc1.out && grep -qx "RESULT: 0 failed" /tmp/acc1.out
```
```bash
cd /srv/work/Infra/iot/expresso && rm -rf /tmp/fw && mkdir -p /tmp/fw && cp pico/*.py pico/scale_cal.json /tmp/fw/ && cp -r pico/lib /tmp/fw/ && python3 testit/shot_test.py > /tmp/acc2.out && grep -qx "RESULT: 0 failed" /tmp/acc2.out
```
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico/classes.py pico/commands.py pico/functions.py pico/main.py
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso > /tmp/acc4.out && grep -cvE "(pico/(classes|commands|functions|main)\.py|testit/mains_freq\.py)$" /tmp/acc4.out | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/classes.py pico/commands.py pico/functions.py pico/main.py testit/mains_freq.py | wc -l) -le 2990
```
Mitattu lähtötaso (`wc -l`, commit 648202b): 1258 + 207 + 710 + 339 + 0 = 2514 — varaa 476 riviä.

## Stop
- `shot_test.py` on punainen jo ennen ensimmäistä muokkausta.
- Itsetestin väite ei toteudu kahden yrityksen jälkeen muuttamatta paketin sääntöä 3.
- Paketti ja lähdekoodi ovat ristiriidassa.

Kysy tällöin yksi kysymys ja lopeta vuorosi. Älä laajenna `may:`-listaa. **Älä koske
laitteeseen:** ei `pico_dev.py`:tä, ei flashausta, ei adb-yhteyttä.

## Report
```text
brief: PWM-1A-VERKKOTAAJUUS
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/2990
iterations: <yritysten määrä>
note: <yksi rivi: itsetestin palauttamat taajuudet ja conf-arvot>
```
