# PWM-1B1-PHOLD — spec

Suunnittelijan kirjoittama sisältö. Toteuttaja ei päätä näistä mitään; brief sanoo mihin ne tulevat.

## 1. Sarjatuloste

```text
PHOLD_START s=<n>
PHOLD t=<ms> bar=<x.xx> filt=<x.xx> slope=<x.xx>
PHOLD_END reason=<ok|stop|switch|devsafe|overpressure> bar=<x.xx>
```

- `PHOLD`-rivi tulostetaan `PHOLD_PRINT_MS = 500` millisekunnin välein, `t` on kulunut aika
  ajon alusta.
- `bar` on raaka muunnettu lukema, `filt` yksinapaisen alipäästön (`PCAP_FILT_TAU`) arvo.
- `slope` on `filt`:n muutos edellisestä tulostuksesta jaettuna kuluneella ajalla, bar/s.
  Ensimmäisellä rivillä `slope=0.00`.
- `PHOLD_END`:n `bar` on viimeisin suodatettu arvo.

## 2. Silmukan säännöt

1. Magneettiventtiili päälle ennen pumppua; `finally` sammuttaa molemmat ja palauttaa
   `set_mode('IDLE')` — sama muoto kuin `pressure_capture_run`:ssä (`functions.py:578-586`,
   `707-712`).
2. Paine lasketaan `gain * (raw * PCAP_RAW_A + PCAP_RAW_B) + offset`, jossa `gain`/`offset` luetaan
   `brew_data.pressure_sensor`:sta kuten `functions.py:570-572`.
3. Alipäästö päivitetään mitatulla `dt`:llä, ei oletetulla (`functions.py:617`).
4. `await asyncio.sleep_ms(5)` joka kierroksella: 120 s ajo ei saa nälkiinnyttää BLE- eikä
   vahtikoiratehtävää, ja 5 ms on yhä 60-kertainen ylinäytteistys 0,3 s suodattimelle.
5. Keskeytysehdot ovat `pcap`:n ehdot: mikä tahansa kytkin (`switch`), `dev_safe`, `phold_abort`
   (`stop`), ja raaka lukema yli `PCAP_OVER_BAR` (`overpressure`). Turvaraja luetaan **raa'asta**
   lukemasta, ei suodatetusta — se ei saa odottaa suotimen viivettä.
6. Ajon pituus rajataan välille 1-120 s (`PHOLD_MAX_S = 120`) jo `classes.py`:n pyyntömetodissa,
   samalla `min/max`-muodolla kuin `request_pressure_capture` (`classes.py:475`).

## 3. Miksi komento on olemassa

Vaiheen 1a ajo 3 osoitti, ettei nykyisellä kuristimen asennolla ole tasapainoa 6 barissa (paine
ajautui pidon aikana 1,92 bar). Vaiheen 1b portitettu mittaus pudottaa pumpun tehon puoleen, joten
ajautuma ja portituksen vaikutus menisivät sekaisin. `phold:` on se ajo, jonka aikana käyttäjä
kääntää kuristinta, kunnes `slope` on nollassa halutussa paineessa.
