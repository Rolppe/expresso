# EXPRESSO-DIAGNET — Picon diagnostiikka Wi-Fillä Home Assistantiin (20.10.2026)

Käyttäjä 20.10.2026: "toteutetaan ongelmien parempi diagnostiikka siten että tehdään expresso pico firmwareen wifi
yhteys homeassistantiin ja aina kun uutto on käynnissä siirretään homeassistantille tarkkaa diagnostiikkatietoa".
Siirtotapa: pääistunnon valinta (käyttäjä: "valitse itse"; myöhemmin myös iOS-äppi Wi-Fillä) — UDP
palvelimen keräimeen, joka vie HA:han. Ketju hyväksytty kerralla (rakennus, reititin, flash, todennus uutolla).

Tausta: vikatilat ajossa (pumpun ohjaus pitkällä viiveellä, riski kasvaa käyntiajan myötä), eikä ajoista jää jälkeä,
kun Zero ei ole kiinni: Pico ei kirjoita lokia, `GUARD_TRIP`/`*_END`/`EU_STALL`/traceback menevät vain sarjaan.

## Arkkitehtuuri

    Pico W (IoT-VLAN 30, Wi-Fi STA)  --UDP 47210-->  palvelin 192.0.2.11 (keraaja.py)  --REST-->  HA 192.0.2.12
                                                     └ ~/.local/state/expresso-diag/*.log (kaikki rivit)

Pico ei koskaan odota verkkoa: UDP-soketti on estämätön, kohde on IP-literaali (ei DNS:ää), lähetysvirhe
lasketaan ja ohitetaan, ja puskuri on kiinteä rengas (täysi rengas ylikirjoittaa vanhimman ja kasvattaa `drop`ia).
Reititin: vyöhyke `iot` → `trust` on REJECT; yksi kapea sääntö Picon MAC → 192.0.2.11 udp/47210.

## Protokolla (versio EXD1)

Jokainen UDP-paketti (≤ 1400 B):

    EXD1 <boot> <seq> <up_ms> <drop>\n<data>

- `boot`: 8 heksamerkkiä, satunnainen joka käynnistyksessä. `seq`: paketin järjestysluku 0.. tämän bootin sisällä.
  `up_ms`: `ticks_ms()` lähetyshetkellä. `drop`: kumulatiivinen ylikirjoitettujen tavujen määrä.
- `data`: raakatavuja Picon tekstivirrasta. Rivi voi jakautua kahteen pakettiin; keräin liittää peräkkäiset `seq`:t
  ja kirjaa aukon (`seq` hyppää) rivinä `[LOST n]`.

Tekstivirta = Picon koko stdout (`os.dupterm`-tee: sama kuin sarjassa, myös traceback) + rivit, jotka firmware
kirjoittaa vain verkkoon (ei sarjaan, ettei USB-CDC tukkeudu):

| Rivi | Milloin | Kentät |
|---|---|---|
| `DIAG_BOOT rc=<n> fw=<s> mac=<hex>` | käynnistys | `machine.reset_cause()` (0 POWER_ON, 1 WDT, …), firmware-tunniste, Wi-Fi-MAC |
| `DIAG_HB up_s= free= alloc= drop= txp= txerr= smax_us= rssi= brew= pend=` | 60 s välein, uuton aikana 5 s | käyntiaika, `gc.mem_free/alloc`, pudotetut tavut, lähetetyt paketit, virheet, pisin `sendto` µs, RSSI, uutto 0/1, kuittaamaton uuttoloki 0/1 |
| `DIAG_S t= T= p= f= w= r=` | uuton 10 Hz näyte (brew_logger) | ms alusta, °C×10, bar×100, g/s×100, g×10, bitit pumppu=1 lämmitin=2 |
| `DIAG_SHOT start` / `DIAG_SHOT end reason=<r> n=<näytteet>` | uuttolokin alku ja loppu | |
| `DIAG_MIN win_ms= heat_ms= pump_ms= p_n= p_avg= p_min= p_max= T= target=` | 60 s välein (käyttäjä 20.10.2026) | releevartion 100 ms ajastimen ikkuna: lämmittimen ja pumpun päälläolo ms, paineen keskiarvo/min/max (bar), kattilan lämpö ja tavoite; `-` = ei arvoa. Keräin: `sensor.espresso_diag_heater_on_s` / `_pump_on_s` (s per 60 s, ikkuna skaalattuna), `_pressure_avg/_min/_max`, `_boiler_temp`, `state_class: measurement` |

Sarjasta tulevat valmiit rivit, joita keräin jäsentää: `GUARD_TRIP <rele> reason=…`, `<X>_END … key=value …`
(esim. `PB_END loops= max_loop_ms= reason=`), `EU_STALL …`, `EU_GC …`, `DEVSAFE …`, `Traceback`, `MemoryError`.

## Keräin (`Infra/iot/expresso/diagnet/keraaja.py`, Python 3 stdlib)

- Kuuntelee `0.0.0.0:47210/udp`. Kirjoittaa jokaisen kokonaisen rivin tiedostoon
  `~/.local/state/expresso-diag/YYYY-MM-DD.log` muodossa `<ISO-aika> <boot> <rivi>`; uutto (`DIAG_SHOT start`…`end`)
  lisäksi omaan tiedostoon `shot-<aika>-<boot>.log`.
- HA (REST `POST /api/states/<entity>`, token `~/.config/ha/token`, URL `HA_URL` oletus `http://192.0.2.12:8123`,
  sama kuin `Infra/linux/palvelin/oneplus-ha.py`). HA-kutsut omassa säikeessään jonon kautta: hidas tai
  kaatunut HA ei saa pudottaa UDP-paketteja. Sensorit (state + attribuutit):
  `sensor.espresso_diag_status` (online/offline: offline kun 150 s ilman pakettia), `_uptime` (s), `_mem_free`,
  `_drop`, `_rssi`, `_reset_cause` (viimeisin DIAG_BOOT, attribuutit rc, fw, aika), `_boots` (laskuri keräimen
  käynnistä lähtien), `_last_end` (viimeisin `*_END`-rivi: state = reason, attribuutit kaikki key=value),
  `_max_loop_ms` (viimeisimmän `*_END`:n max_loop_ms), `_last_guard_trip` (rivi ja aika), `_stalls` (EU_STALL-määrä
  viimeisimmässä uutossa), `_shot_pressure` / `_shot_temp` / `_shot_flow` (uuton aikana ≤ 1 Hz).
  Tapahtuma `POST /api/events/espresso_diag` jokaisesta `GUARD_TRIP`, `*_END`, `DEVSAFE`, `Traceback`/`MemoryError`
  ja `DIAG_BOOT`-rivistä ({kind, line, boot}). Sensori-päivitys korkeintaan kerran 5 s per entiteetti, paitsi
  tapahtumarivit heti.
- Käynnistys: `diagnet/kaynnista.sh` (cron 5 min välein kuten `scopes/palvelu/kaynnista.sh`; ei käynnistä toista,
  jos portti on jo varattu tai pid elää), loki `~/.local/state/expresso-diag/keraaja.loki`.
- Testi `testit/diagnet_keraaja_smoke.py`: lähettää paikallisesti UDP-paketteja (jaettu rivi, seq-aukko, uusi boot,
  END/GUARD_TRIP/HB/S-rivit) ja tarkistaa tiedostot ja vale-HA:n (paikallinen HTTP-palvelin) saamat kutsut.

## Firmware (`pico/diagnet.py`, `pico/main.py`, `pico/brew_logger.py`, `pico/preset.py`)

- `preset.DIAGNET = {'enabled': True, 'host': '192.0.2.11', 'port': 47210}`; `enabled: False` palauttaa vanhan
  käytöksen (Wi-Fi pois).
- Tee asennetaan heti importin jälkeen, joten käynnistyksen tulosteet päätyvät renkaaseen ja lähtevät, kun yhteys
  nousee. `write()` ei allokoi kasvavasti eikä koskaan nosta poikkeusta.
- Lähetystehtävä on `asyncio.gather`issa: kaikki poikkeukset kiinni tehtävän sisällä (poikkeus gatherissa kaataisi
  kaikki tehtävät). Yhdistää Wi-Fin uudelleen 30 s välein, jos yhteys puuttuu.
- `main.py`:n poikkeuspolku: `sys.print_exception` + estämätön `flush` ennen uudelleennostoa, jotta kaatumisen
  traceback lähtee ennen vahtikoiran nollausta.
- Testi `testit/diagnet_smoke.py` (CPython, vale-`network`/`socket`/`os`): rengas, ylivuoto, paketointi ja
  otsake, estämätön virhepolku, HB-kentät, brew_loggerin näytekoukku.

## Todennus

1. Isäntä: kumpikin smoke vihreä. 2. Flash Zeron kautta (releet alas, verify). 3. Keräimen lokissa `DIAG_BOOT` ja HB
60 s välein; HA:ssa `sensor.espresso_diag_status` = online. 4. Käyttäjän seuraava uutto: `DIAG_S`-rivit 10 Hz,
`*_END` HA:ssa, BLE-äppi toimii yhä (Wi-Fi + BLE yhtä aikaa: Wi-Fi sammutettiin aikanaan BLE:n vakauden takia —
ketjun suurin riski; jos BLE hajoaa, `enabled: False` ja flash).
