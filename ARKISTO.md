# infra expresso — arkisto

Aktiivisesta rekisteristä poistettu tai muutettu tieto sanatarkasti, vanhin ensin (V-082, 28.9.2026).
Tästä ei poisteta mitään. Purku ei lue tätä tiedostoa: se luetaan vain vianselvityksessä, kun
halutaan tietää, mitä rekisterissä on joskus ollut. Kirjoittaja: `claude/siirto/tools/arkisto.mjs`.

## 28.9.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-UUTTO-8BAR (laiteajo) — isäntä valmis 75b8a62 (TILAUS-K vaiheet 3–4, bim:1, smoke 16–21 vihreä): flash + verify, RAM pim:1 bim:1 pit:6, pvent ennen jokaista ajoa, `pico_dev.py shot 20` ajot a (bim:1), b (eb_* opittu), c (bim:0-vertailu), d (käyttäjä kääntää kuristinta pidossa, TILAUS-C); analyysi esiuutto_analyysi.py; odottaa käyttäjää (läsnäolo + vesi) — polut: Infra/iot/expresso/pico/functions.py, Infra/iot/expresso/pico_dev.py, Infra/iot/expresso/testit/esiuutto_analyysi.py, Infra/iot/expresso/paketit/VAIHESEURANTA.md — aloitus: /pura infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Uuttovaiheen 8 bar alun ~1 bar pudotukset ja hidas integraali (EXPRESSO-PAINESAADIN-HEILUNTA) | korjattu isännällä 75b8a62 (smoke 16: ylitys +0,12/+0,16 vs vanhan +0,74/+1,04), laitteella todentamatta | todenna EXPRESSO-UUTTO-8BAR-laiteajossa. |
| Käyttöönottoketju (käyttäjä 26.9.2026, KAYTTAJAN-TIEDOT luku 7; valitsi "Myös 8 bar ensin", hylätty "Esiuutto nyt, 8 bar myöhemmin") | järjestys käyttäjän: (1) EXPRESSO-ESIUUTTO-HYVAKSYNTA: firmware-versio laitteelta, lämmin/kylmä-tila ja 6 s pito lämpimällä kuristimella esiavoin1:llä (`hold`), käyttäjän hyväksyntä esiuutolle — kohta (1) ajettu 26.9.2026, ei hyväksytty (toinen ja kolmas kerta 26.–27.9.2026: EXPRESSO-ESIUUTTO-UUTTOASENTO ja EXPRESSO-ESIUUTTO-VUORONVARAUS ajettu, ei hyväksytty); neljäs kerta 27.9.2026 rampinloppu1 = 651afec (at–aw): **hyväksytty**; (2) TILAUS-K vaiheet 3–4 8 barille toteutus + laitetestit; (3) pim:1 pysyväksi oletukseksi (nyt RAM, commands.py:301-307) ja (4) EXPRESSO-UUTTOLOKI: elokuun brew_logger + BLE-multipack + `sync`/`brew_log?`/`brew_log:ack` nykyiseen firmwareen samaan flashiin, protokolla puhelimen `files/firmware/`-kopiosta (sovellus ennallaan); (5) todennus oikealla kahvilla: brew_shots.jsonl kasvaa | (1) hyväksytty 27.9.2026 (at–aw, ylitys 0,08–0,32); (2) isännällä tehty 75b8a62 (TILAUS-K vaiheet 3–4), laiteosa seuraavaksi (EXPRESSO-UUTTO-8BAR); sitten (3) pim:1 (ja bim:1) pysyväksi, (4) EXPRESSO-UUTTOLOKI. |
| Kellon lukko pienellä tarpeella (EXPRESSO-ESIUUTTO-VUORONVARAUS) | vaiheiden 3–4 lukitus toteutettu isännällä 75b8a62 (hidas nousu < 2 bar/s + pito, `EB_CLK_RATE`), laitteella todentamatta | todenna EXPRESSO-UUTTO-8BAR-laiteajossa. |
| EXPRESSO-UUTTO-8BAR laiteosa | isännällä valmis 75b8a62 (TILAUS-K vaiheet 3–4, bim:1), ei flashattu | flash (functions, classes, commands, main, verkkokello) + verify; RAM pim:1, bim:1, pit:6, wmax:720; ennen jokaista ajoa `pico_dev.py cmd pvent`; ajot `pico_dev.py shot 20 testit/uutto8-<pvm>-a-bim1.log`, b (eb_* käytössä), c bim:0-vertailu samalla kuristimella, d käyttäjä kääntää kuristinta kesken pidon (TILAUS-C); analyysi `testit/esiuutto_analyysi.py <lokit>`. Odottaa käyttäjää (läsnäolo + vesi). |
| Laiteriskit EXPRESSO-UUTTO-8BAR | iskukoko 8 barissa ja vuodon eksponentti epävarmoja, väreilyn amplitudia 8 barissa ei mallinnettu (gate_reset todennettava); tarve ≥ ~0,85 → pumpulla ei varaa (malli −0,4…−0,5) | `pico_dev.py hold` hold_s ≥ pit ja bim:1 → EU_END pysäyttää vasta vaiheen 3 alettua: hold-ajoissa käytettävä bim:0. |

### Viat — poistettu tai muutettu

- **Uusi, avoin (laite):** laite kaatui `MemoryError: allocating 8192 bytes` pitkän käyttöajan
  jälkeen; nollaus korjasi. Isot puskurit (`pstep` varaa 28 KB) pirstovat keon.
  tarkoitukseen. Rajan muutos on käyttäjän päätös.
- **Uusi, avoin (firmware, 28.9.2026):** `BrewData.get_pressure()` keräsi 16,7 ms:n näytteet listaan (~8 kt), ja pirstoutunut
  keko kaatoi mainin (MemoryError, kuri2) → juokseva summa, kuri3 (vika 14:n välitön syy; `get_pressure_*`-pitkäversio
  classes.py:1262 käyttää yhä listaa). `GUARD_TRIP heater reason=tempstale` laukeaa 8 barin pidossa sekä bim:1:llä
  (a, b, a2, b2, a3) että bim:0:lla (c2): lämpötilaa ei lueta 10 s:iin, joten lämmitin on estetty pidon loppuun.
  `kuri:1`-kuvio (20 ms päällä / 20 ms pois) ei ole lukittu verkkokelloon → liukuu ~16 µs/jakso, käyttäjä kuuli
  syklihäiriön.

## 28.9.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-TEMPSTALE-JA-OLETUS — isännällä: kattilan lämpötilan luku pre_infusion_phased-silmukkaan (vaiheet 1–4, bim:1) ja vanhaan uuttoon niin, ettei GUARD_TRIP tempstale laukea pidossa (MAX31865 ≥ 75 ms: vain tauossa, joka sietää pysähdyksen), smoke-tapaus; sen jälkeen pim:1 ja bim:1 oletukseksi (commands.py/classes.py); flash ja laitetodennus vaativat käyttäjän — polut: Infra/iot/expresso/pico/functions.py, Infra/iot/expresso/pico/classes.py, Infra/iot/expresso/pico/commands.py, Infra/iot/expresso/testit/esiuutto_smoke.py — aloitus: /pura infra expresso — automaattinen: kyllä

## 28.9.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-TEMPSTALE-JA-OLETUS — jatka isännällä: vertaa lämpötilaluku toisella ytimellä (käyttäjän ehdotus, BLE-ydin) vs. pilkottu luku (commit tässä pakkauksessa, smoke 2 FAIL 10 ja 14) ja valitse se, joka ei heikennä pumpun ohjausta, smoke-tapaus 22, sitten pim:1 ja bim:1 oletukseksi (commands.py/classes.py); flash ja laitetodennus vaativat käyttäjän — polut: Infra/iot/expresso/pico/functions.py, Infra/iot/expresso/pico/classes.py, Infra/iot/expresso/pico/lib/adafruit_max31865.py, Infra/iot/expresso/pico/commands.py, Infra/iot/expresso/testit/esiuutto_smoke.py — aloitus: /pura infra expresso — automaattinen: kyllä

### Todettu 28.9.2026 — EXPRESSO-TEMPSTALE-JA-OLETUS (koodissa, ei flashattu, ei committoitu) — poistettu tai muutettu

- Juurisyy: `run_shot` sammuttaa lämmittimen alussa, `main`-silmukka ei lue lämpötilaa `run_shot`in
  aikana, ja `pre_infusion_phased` (vaiheet 1–4) ei lue sitä lainkaan → vaiheen 3 ensimmäinen
  lämmitinpulssi (EB_HEAT 100/50 ms) osuu yli 10 s vanhaan lukemaan (relayguard
  2 s välein) on estetty vain ensimmäiset 2 s. Vahti ei lukitu pysyvästi (block poistuu poll():ssa,
  kun lukema on tuore).
- Korjaus koodissa: `pico/lib/adafruit_max31865.py` uudet `rtd_start()`/`rtd_convert()`/
  `rtd_result()` (sama luku kuin `read_rtd` ilman `time.sleep`iä) ja `temperature_from_rtd(rtd)`;
  `pico/classes.py` `TemperatureSensor.step_reset`/`step_due`/`step` ja `BrewData.step_boiler_temperature`;
  `pico/functions.py` `EU_TEMP_ROOM_US` 5000, `pre_infusion_phased` tekee yhden askeleen ennen
  asyncio-vuoroa, kun seuraavaan tapahtumaan on > 5 ms.
- Smoke ennen muutoksia: 119 OK, RESULT 0 failed, 76 s. Uusi koodi ilman anturimallia: tuloste
  identtinen perustasoon. Anturimallin kanssa (`testit/esiuutto_smoke.py` Max31865-anturimalli,
  askelten hinta start 2000/convert 1000/result 700 µs — arvio, ei mitattu): RESULT 2 failed —
  tapaus 10 (kiinni + kohina, pidon 2 s ka ≤ +0,06, tulos +0,067) ja tapaus 14 (vv=1 pidon piikki
  ≤ +0,7 bar, ulkona 3/8 > 33 %). Syy selvittämättä: näytekato (2 ms askel = 2 painenäytettä pois
  jakson keskiarvosta) tai kohinatoteuman siirtymä.

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-TEMPSTALE-JA-OLETUS | kesken: koodi työpuussa ja tässä commitissa, smoke 2 FAIL (10, 14) anturimallilla (todenna viim. 12.10.2026) | selvitä FAILien syy (näytekato vs. kohina: aja ilman kustannusta mutta askeleet päällä, ja askel pilkottuna), korjaa niin ettei pumpun ohjaus heikkene, kirjoita smoke-tapaus 22, sitten pim:1/bim:1 oletukseksi (classes.py:194 pre_infusion_method, classes.py:207 brew_method; commands.py pim/bim-kommentit "RAM only, oletus 0"), flash + laitetodennus käyttäjän kanssa (t_max_us laitteelta) |

### Viat — poistettu tai muutettu

  `HEATER_TEMP_STALE_MS` 10000), joten lämmitin on estetty pidon loppuun; korjaus seuraavana pakettina
  (EXPRESSO-TEMPSTALE-JA-OLETUS). Osa juurisyistä korjattu tässä sessiossa: `BrewData.get_pressure()` keräsi

## 29.9.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-TEMPSTALE-JA-OLETUS — jatka isännällä: toisen ytimen lämpötilaluku on koodissa (smoke 0 failed, ei flashattu): kirjoita smoke-tapaus 22 (C1Model, lukeman ikä lämmittimen päällekytkennässä), sitten pim:1 ja bim:1 oletukseksi (commands.py/classes.py); flash ja laitetodennus (TEMP_C1 ready, PB_END c1_n/c1_gap_ms/c1_err, ei tempstale-GUARD_TRIPiä) vaativat käyttäjän — polut: Infra/iot/expresso/pico/classes.py, Infra/iot/expresso/pico/functions.py, Infra/iot/expresso/pico/commands.py, Infra/iot/expresso/testit/esiuutto_smoke.py — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-TEMPSTALE-JA-OLETUS | koodi valmis (toinen ydin), smoke 0 failed, ei flashattu (todenna viim. 12.10.2026) | isännällä: smoke-tapaus 22 (C1Model: lämmittimen päällekytkennän lukeman ikä ≤ 1 s bim:1/bim:0; ilman c1_on:ia > 10 s = virheen toisto), sitten pim:1/bim:1 oletukseksi (classes.py pre_infusion_method/brew_method, commands.py pim/bim-kommentit), sitten flash + laitetodennus käyttäjän kanssa: boot `TEMP_C1 ready`, `PB_END … c1_n>0 c1_gap_ms≤400 c1_err=0`, ei `GUARD_TRIP heater reason=tempstale`, EU_VV/EB_VV late/lmax ennallaan; lisäksi REPL-tarkistus ytimen 1 allokoimattomuudesta (c1_err=0 riittää, koska heap_lock) |

### Roskasiivous 1.10.2026 — alkuperäinen rivi Infra/iot/zero/REKISTERI.md:stä (SIIRTO-ROSKAT; seuranta V-143, ei mahtunut rekisteriin: YLITYS)

| Asia | Tila | Seuraava askel |
|---|---|---|
| USB-silta Picolle | valittu 1.10.2026: ser2net raw TCP 2217 ↔ `/dev/ttyACM0` Zerolla | SSH:n jälkeen asenna ja konfiguroi ser2net Zerolla; `pico_dev.py`:n kohdeosoite 192.0.2.10:2217 ja adb-osien ohitus omistajalle `/vika infra expresso` |

## 5.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-SHOTTEST-FEIKKI — päivitä testit/shot_test.py:n feikki BrewData nykyiseen pre_infusion_phasediin (HEADillä AttributeError: 'BrewData' object has no attribute 'eu_g_pre'; Viat: "Uusi, avoin (työkalu, pieni, 28.9.2026)"), aja shot_test.py vihreäksi — polut: Infra/iot/expresso/testit/shot_test.py — aloitus: /pura infra expresso

## 5.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-SHOTTEST-FEIKKI — päivitä testit/shot_test.py:n feikki BrewData nykyiseen pre_infusion_phasediin (HEADillä AttributeError: 'BrewData' object has no attribute 'eu_g_pre'; Viat: "Uusi, avoin (työkalu, pieni, 28.9.2026)"), aja shot_test.py vihreäksi — polut: Infra/iot/expresso/testit/shot_test.py — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| shot_test.py vanhentunut (eu_g_pre puuttuu feikistä) | uusi, avoin | päivitä feikki BrewData nykyiseen pre_infusion_phasediin |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| `pressure_len_run`:ssa on käyttämättömät muuttujat `venting` ja `vents`. | Uusi, avoin (pieni) |
| `settings.txt`, jossa brew- tai steam-lämpötila on yli 150 °C, kaataa `load_settings`:n `ValueError`-haaraan, joka poistaa koko tiedoston → oletukset palautuvat, myös `wmax` katoaa (testikomennot eivät käynnisty ennen uutta `wmax`:ia). Suunta on turvallinen (ei ylitä rajaa hiljaa), mutta tiedosto häviää kokonaan yhden kentän takia. | Uusi, avoin (pieni) |
| `main.py`:n kommentti "weight limits are deliberately not persisted" on vanhentunut — painorajat tallennetaan `devsafe12`:sta asti; kommenttia ei korjattu. | Uusi, avoin (pieni, havainto) |
| `testit/shot_test.py` kaatuu HEADillä `AttributeError: 'BrewData' object has no attribute 'eu_g_pre'` — vanhentunut feikki, ei tämän session muutoksen aiheuttama. | Uusi, avoin (työkalu, pieni, 28.9.2026) |

## 5.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-UUTTOLOKI — käyttöönottoketjun kohta (4) isäntäosa: elokuun brew_logger + BLE-multipack + `sync`/`brew_log?`/`brew_log:ack` nykyiseen firmwareen smoke-testein, ei flashia (flash ja todennus oikealla kahvilla erikseen käyttäjän luvalla) — polut: Infra/iot/expresso/pico/**, Infra/iot/expresso/testit/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Käyttöönottoketju (käyttäjä 26.9.2026, KAYTTAJAN-TIEDOT luku 7; valitsi "Myös 8 bar ensin", hylätty "Esiuutto nyt, 8 bar myöhemmin") | järjestys käyttäjän: (1) EXPRESSO-ESIUUTTO-HYVAKSYNTA: firmware-versio laitteelta, lämmin/kylmä-tila ja 6 s pito lämpimällä kuristimella esiavoin1:llä (`hold`), käyttäjän hyväksyntä esiuutolle — kohta (1) ajettu 26.9.2026, ei hyväksytty (toinen ja kolmas kerta 26.–27.9.2026: EXPRESSO-ESIUUTTO-UUTTOASENTO ja EXPRESSO-ESIUUTTO-VUORONVARAUS ajettu, ei hyväksytty); neljäs kerta 27.9.2026 rampinloppu1 = 651afec (at–aw): **hyväksytty**; (2) TILAUS-K vaiheet 3–4 8 barille toteutus + laitetestit; (3) pim:1 pysyväksi oletukseksi (nyt RAM, commands.py:301-307) ja (4) EXPRESSO-UUTTOLOKI: elokuun brew_logger + BLE-multipack + `sync`/`brew_log?`/`brew_log:ack` nykyiseen firmwareen samaan flashiin, protokolla puhelimen `files/firmware/`-kopiosta (sovellus ennallaan); (5) todennus oikealla kahvilla: brew_shots.jsonl kasvaa (todenna viim. 12.10.2026) | (1) hyväksytty 27.9.2026 (at–aw, ylitys 0,08–0,32); (2) valmis — isäntä 75b8a62 + laiteajo todennettu 28.9.2026 (a–d2, EXPRESSO-UUTTO-8BAR); ennen (3):a tempstale-korjaus (EXPRESSO-TEMPSTALE-JA-OLETUS, muuten lämmitin estetty koko pidon ajan oikeassa uutossa); sitten (3) pim:1 ja bim:1 pysyväksi oletukseksi, (4) EXPRESSO-UUTTOLOKI. |
| EXPRESSO-UUTTOLOKI | ei aloitettu | ketjun kohta (4) |
| EXPRESSO-VALMIUSTILA-LAITETESTI (kirjattu 5.10.2026) | koodi valmis f5a67c3, ei flashattu | vaatii käyttäjän luvan ja läsnäolon (sääntö 8, 21): päivitä MANIFEST.json, flash + verify, `stby:on` → loki STBY_ON ja kattilan lasku kohti 90 °C ilman GUARD_TRIPiä; uuttokytkin → `STBY_OFF reason=switch`, lämmitys käynnistyy; toista kuumavesi- ja höyrykytkimellä; `stby:on` + `pre:on` → reason=app; `stby:1` → luonnollinen STBY_ON idle_s=60. |

## 5.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-UUTTOLOKI-LAITE — ketjun kohdat (4) flash ja (5) todennus: yksi setti 9deb88f + valmiustila f5a67c3, flash + verify, oikea kahvi ≥ 15 s → `BREW_LOG ready` ja brew_shots.jsonl kasvaa (viim. 12.10.2026), `stby:on` → STBY_ON; käyttäjän lupa ja läsnäolo (sääntö 8, 21) — polut: Infra/iot/expresso/pico/**, Infra/iot/expresso/testit/** — aloitus: /pura infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-UUTTOLOKI | isäntäosa valmis 9deb88f (5.10.2026), ei flashattu | laiteosa EXPRESSO-UUTTOLOKI-LAITE (käyttäjän lupa, sääntö 8, 21); todenna myös muisti 650 rivillä (MemoryError-vika avoin) ja riviaukot: lokin `BREW_LOG ready n=` |

## 5.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-ZERO-FLASH — V-163: pico_dev.py Zeron siltaan (192.0.2.10:2217, adb/ChargerOff/Shelly ohi Zero-tilassa) + flash Zerolla (mpremote rfc2217://127.0.0.1:2218 tai /dev/hubi0, SHA-256 manifestia vasten) + PICO-HALLINTA §1/§8 ja KEHITYSYHTEYS Zero-ketjuun; sitten V-154-korjaus samaan settiin ja UUTTOLOKI-LAITE-todennus (viim. 12.10.2026); flash vaatii käyttäjän luvan (sääntö 8, 21) — polut: Infra/iot/expresso/pico_dev.py, Infra/iot/expresso/build_set.py, Infra/iot/expresso/PICO-HALLINTA.md, Infra/iot/expresso/KEHITYSYHTEYS.md, Infra/iot/expresso/pico/** — aloitus: /pura infra expresso

### Todettu 5.10.2026 — Picon yhteys kulkee Zeron kautta (ZERO-USB-päätös 1.10.2026; EXPRESSO-ZERO-FLASH) — poistettu tai muutettu

- Pico on Zeron USB:ssä, ei puhelimessa: `ssh pico-host` → `/dev/hubi0 -> ttyACM0` 5.10. 06.09, `lsusb` 2e8a:0005;
  puhelimen `lsusb` ei näytä 2e8a:ta (vain 05e3:0625 hubi). Zerolla ser2net 2217 raw + 2218 rfc2217 →
  `/dev/hubi0`, silta 192.0.2.10:2217; mpremote, picotool ja python3-serial asennettu (`Infra/iot/zero/REKISTERI.md:60`).
- Expresson omat tiedostot (REKISTERI, `PICO-HALLINTA.md`, `KEHITYSYHTEYS.md`, `pico_dev.py` `PHONE` /
  127.0.0.1:2217 / `ChargerOff` / `CHARGER_ENTITY switch.shellyplus1pm_example`, `build_set.py`) eivät
  mainitse Zeroa (grep 5.10.2026). Shelly on OnePlus-hubin laturi eri paikassa, ei keittimen raudassa.
- Puhelimen `brew_shots.jsonl`: 8 riviä, muutettu 2026-08-30 (lähtötaso). Setti `20261005-uuttoloki1`
  puhelimessa (`build_set.py --from 20260928-kuri6`, 19 tiedostoa + MANIFEST, 20 merkintää; sisältää
  flashaamattomat e4c8665, bdb8463, f5a67c3, f17afe8, 9deb88f); repon `pico/MANIFEST.json` täsmää 19 tiedostolta
  SHA-256:lla, `/secrets.py` vain puhelimessa. Picoon ei kirjoitettu.
- Isäntätestit ja V-154:n todisteet (CDC-puskuri, lokittomuus, relayguard-rajat): `HISTORIA.md` 5.10.2026 ja Viat-rivi "V-154 toistui".

### Päätökset — poistettu tai muutettu

- **5.10.2026 (käyttäjä: "Päätä itse" → pääistunto):** järjestys (1) flash-reitti Zeron kautta (V-163 + flash Zerolla; ilman sitä korjausta ei saa Picoon), (2) V-154-korjaus samaan settiin, (3) UUTTOLOKI-LAITE-todennus (kahvi, `stby:on`). Väliaikainen kiertotie kunnes V-154 korjattu: keittimen USB irti Zerosta illaksi, tai aamulla Zero irti + keitin pois–päälle.

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-UUTTOLOKI / EXPRESSO-UUTTOLOKI-LAITE | isäntäosa valmis 9deb88f (5.10.2026); setti `20261005-uuttoloki1` puhelimessa, ei flashattu, puhelinreitti ei yllä Picoon (Pico on Zerolla) (todenna viim. 12.10.2026) | flash Zeron reitillä EXPRESSO-ZERO-FLASH:n jälkeen (käyttäjän lupa ja läsnäolo, sääntö 8, 21); todenna myös muisti 650 rivillä (MemoryError-vika avoin) ja riviaukot: lokin `BREW_LOG ready n=` |
| EXPRESSO-ZERO-FLASH (V-163, kirjattu 5.10.2026) | avoin; ZERO-USB-päätös ei ole expresson papereissa (`pico_dev.py`, `build_set.py`, PICO-HALLINTA §1/§8, KEHITYSYHTEYS) | pico_dev.py Zeron siltaan (192.0.2.10:2217, adb/ChargerOff/Shelly ohi) + flash Zerolla (mpremote rfc2217://127.0.0.1:2218 tai /dev/hubi0, SHA-256 manifestia vasten) + dokumentit; käyttäjän lupa ja läsnäolo (sääntö 8, 21) (viim. 12.10.2026) |
| EXPRESSO-VALMIUSTILA-LAITETESTI (kirjattu 5.10.2026) | koodi valmis f5a67c3, ei flashattu | flash yhdessä UUTTOLOKI-LAITE:n kanssa; vaatii käyttäjän luvan ja läsnäolon (sääntö 8, 21): päivitä MANIFEST.json, flash + verify, `stby:on` → loki STBY_ON ja kattilan lasku kohti 90 °C ilman GUARD_TRIPiä; uuttokytkin → `STBY_OFF reason=switch`, lämmitys käynnistyy; toista kuumavesi- ja höyrykytkimellä; `stby:on` + `pre:on` → reason=app; `stby:1` → luonnollinen STBY_ON idle_s=60. |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| **flash valmisteltiin puhelinketjuun, vaikka Pico on Zerolla:** EXPRESSO-UUTTOLOKI-LAITE 5.10.2026 — pääistunto rakensi setin `20261005-uuttoloki1` puhelimeen (`build_set.py`) ja yritti `pico_dev.py restore` -komentoa, jonka `ChargerOff` olisi katkaissut Shellyn (`switch.shellyplus1pm_example`, OnePlus-hubin laturi eri paikassa, ei keittimen raudassa); käyttäjälle sanottiin "Shelly-laturin rele naksahtaa" keittimen reaktiona (sääntö 21 väärin). Käyttäjä hylkäsi ajon. Juurisyy: ZERO-USB-päätös (1.10.2026) on vain `Infra/iot/zero/REKISTERI.md`:ssä ja V-163/V-154:ssä (IDEAT); tämän skoopin REKISTERI, `PICO-HALLINTA.md` §1/§8, `KEHITYSYHTEYS.md`, `pico_dev.py` (127.0.0.1:2217, `PHONE`, `ChargerOff`) ja `build_set.py` eivät mainitse Zeroa kertaakaan (grep 5.10.2026), ja SEURAAVA-rivi sanoi "flash + verify" nimeämättä ketjua. Pääistunto luki V-163:n "nyt irti V-154-kiertotienä" nykytilaksi ja selitti puhelimen tyhjän `lsusb`:n (ei `2e8a`) laturikierron ominaisuudeksi eikä vastanäytöksi; Zerolla Pico oli kiinni (`/dev/hubi0`, 06.09 alkaen). | Uusi, avoin (pääistunto 5.10.2026) |
| **V-154 toistui 5.10.2026 aamulla:** keitin verkkovirtaan → "firmware kaatunut" (käyttäjä); korjaantui Zeron irrotuksella ja keittimen uudelleenkäynnistyksellä. Zeron journal ei ole pysyvä (`--list-boots`: vain boot 06.09.54, Pico `2e8a:0005` enumeroitui käynnistyksessä), ser2net ei lokita, sovelluksella ei aamun lokia, HA:ssa ei keitintä → syy päätelty, ei todennettu: Zeron VBUS piti Picon päällä keittimen ollessa pois, termostaatti piti lämmitinreleen päällä ilman verkkovirtaa ja `relayguard` `heat_dead` (`HEATER_NORISE_ON_MS` 120000) lukitsi lämmityksen; vaihtoehto pitkän käyttöajan `MemoryError` (avoin vika). Picon CDC-puskurissa 5.10. klo 12.3x: `PI … -0.6 2.5 …` (paine −0,6 bar = ilman verkkovirtaa) ja `PB_END loops=0 reason=stopped` → uutto käynnistyi verkkovirrattomana. Pico on yhä Zerolla, joten seuraava aamu toistaa vian, kunnes V-154 korjataan tai johto irrotetaan. | Uusi, avoin (laite, 5.10.2026) |

### Viat — valmis

| Vika | Tila |
|---|---|
| **flash valmisteltiin puhelinketjuun, vaikka Pico on Zerolla:** EXPRESSO-UUTTOLOKI-LAITE 5.10.2026 — pääistunto rakensi setin `20261005-uuttoloki1` puhelimeen (`build_set.py`) ja yritti `pico_dev.py restore` -komentoa, jonka `ChargerOff` olisi katkaissut Shellyn (`switch.shellyplus1pm_example`, OnePlus-hubin laturi eri paikassa, ei keittimen raudassa); käyttäjälle sanottiin "Shelly-laturin rele naksahtaa" keittimen reaktiona (sääntö 21 väärin). Käyttäjä hylkäsi ajon. Juurisyy: ZERO-USB-päätös (1.10.2026) on vain `Infra/iot/zero/REKISTERI.md`:ssä ja V-163/V-154:ssä (IDEAT); tämän skoopin REKISTERI, `PICO-HALLINTA.md` §1/§8, `KEHITYSYHTEYS.md`, `pico_dev.py` (127.0.0.1:2217, `PHONE`, `ChargerOff`) ja `build_set.py` eivät mainitse Zeroa kertaakaan (grep 5.10.2026), ja SEURAAVA-rivi sanoi "flash + verify" nimeämättä ketjua. Pääistunto luki V-163:n "nyt irti V-154-kiertotienä" nykytilaksi ja selitti puhelimen tyhjän `lsusb`:n (ei `2e8a`) laturikierron ominaisuudeksi eikä vastanäytöksi; Zerolla Pico oli kiinni (`/dev/hubi0`, 06.09 alkaen). | todennettu 5.10.2026 (669d3bb: paperit ja työkalu Zero-ketjussa; FLASH_OK, CMD_OK Zerolla) |

## 5.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-TURVA-DEVRUN — turva_pika_smoke punainen: throttle_set_run (main.py:307–308) dev_run:n kautta tai testin poikkeus perusteltuna, isäntätestit 18/18; flash erikseen käyttäjän luvalla — polut: Infra/iot/expresso/pico/main.py, Infra/iot/expresso/pico/functions.py, Infra/iot/expresso/testit/turva_pika_smoke.py — aloitus: /pura infra expresso — automaattinen: kyllä

### Todettu 5.10.2026 — Picon yhteys kulkee Zeron kautta; uuttoloki-setti flashattu (EXPRESSO-ZERO-FLASH) — poistettu tai muutettu

- Isäntätestit 17/18; `testit/turva_pika_smoke.py` punainen (ks. Viat). Todisteet: `testit/flash-20261005-zero*.log`, `HISTORIA.md` 5.10.2026.

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Aamun kaatuminen 5.10.2026: heat_dead vs MemoryError | syy päätelty, ei todennettu (ei lokia) (todenna viim. 12.10.2026) | ehdota: Zerolle Picon sarjatulosteen pysyvä loki (ser2net ei lokita; `infra zero` -skoopin asia) ja kysy käyttäjältä oire (ei lämmennyt vs sovellus ei yhteyttä) |
| V-154 menetelmä | avoin; paineanturin syöttö ei erota verkkovirtaa Zero-kytkennässä (mittaus 5.10.2026); odottaa käyttäjää | käyttäjän päätös uudesta menetelmästä: (a) heat_dead-lukon vapautus jäähtymisen jälkeen rajatulla uusintamäärällä, (b) laitteistotunnistin (5 V keittimen virtalähteestä GPIO:hon optoerottimella), (c) Zeron VBUS-katko / Picon syöttö keittimestä; kiertotie ennallaan |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| **V-154 toistui 5.10.2026 aamulla:** keitin verkkovirtaan → "firmware kaatunut" (käyttäjä); korjaantui Zeron irrotuksella ja keittimen uudelleenkäynnistyksellä. Zeron journal ei ole pysyvä (`--list-boots`: vain boot 06.09.54, Pico `2e8a:0005` enumeroitui käynnistyksessä), ser2net ei lokita, sovelluksella ei aamun lokia, HA:ssa ei keitintä → syy päätelty, ei todennettu: Zeron VBUS piti Picon päällä keittimen ollessa pois, termostaatti piti lämmitinreleen päällä ilman verkkovirtaa ja `relayguard` `heat_dead` (`HEATER_NORISE_ON_MS` 120000) lukitsi lämmityksen; vaihtoehto pitkän käyttöajan `MemoryError` (avoin vika). Picon CDC-puskurissa 5.10. klo 12.3x: `PI … -0.6 2.5 …` (paine −0,6 bar = ilman verkkovirtaa) ja `PB_END loops=0 reason=stopped` → uutto käynnistyi verkkovirrattomana. Pico on yhä Zerolla, joten seuraava aamu toistaa vian, kunnes V-154 korjataan tai johto irrotetaan. Mittaus 5.10.: paineanturi ei erota verkkovirtaa Zero-kytkennässä (−0,133 vs −0,111 bar raw), joten paineeseen perustuva korjausmenetelmä ei toimi; päätös Avoimet asiat "V-154 menetelmä". | avoin (laite, 5.10.2026); odottaa käyttäjää (menetelmäpäätös) |
| `turva_pika_smoke` punainen: `throttle_set_run` kutsutaan main.py:307–308 suoraan dev_run:n ohi (e0fb94f, 28.9.2026), joten testikomentoa ei kääritä lämmittimen sammutukseen; ollut laitteella kuri6:sta asti. | avoin (turvallisuus, 5.10.2026) |

## 5.10.2026 — infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Pumpun tehon 1 %:n säätötarkkuus | osittain; delta-sigma nyt käytössä esiuutossa (pim:1) | laajenna vaiheisiin 3–4; kirjaa vaatimus muodossa "1 % keskitehosta ≥ 2 s ikkunan yli" |
| Vaihe 1h | avattu, briefaamatta | kytke `mains_calibrate` esiuuton paineennostoon ja johda `MCAL_GRID` ikkunasta (askel ≈ 1/(2T)) |
| Tämän päivän pyyhkäisyajojen (`psweep-20260920-1b*`) tulkinta | tarkistettava | selitettiin portituksen ja paineiskun syyksi, mutta `_psweep_trim`:n (nyt korjattu) venttiilivika tarkoittaa, että segmentit 1→ ajettiin eri venttiilitilassa kuin segmentti 0 — selitys voi olla väärä |
| Vesisäiliön taso ennen laiteajoa | ajo f menetettiin tyhjään säiliöön 23.9.2026 | laiteajon valmistelukysymykseen "säiliössä vettä". |
| Säätimen 17 ms askel → 20 ms kelloon sidottu (TILAUS-L) | avoin | VAIHESEURANTA askel 2. |

### Avoimet asiat — valmis

| Asia | Tila | Seuraava askel |
|---|---|---|
| Pumpun tehon 1 %:n säätötarkkuus | valmis 5.10.2026 (käyttäjä kuittasi) | ei askelta |
| Vaihe 1h | valmis 5.10.2026 (käyttäjä: verkkokello korvasi) | ei askelta |
| Tämän päivän pyyhkäisyajojen (`psweep-20260920-1b*`) tulkinta | valmis 5.10.2026 (käyttäjä sulki, vanhentunut) | ei askelta |
| Vesisäiliön taso ennen laiteajoa | valmis 5.10.2026 (ajon hyväksyntä kysyy säiliön veden) | ei askelta |

## 5.10.2026 — infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-UUTTOLOKI-LAITE + EXPRESSO-VALMIUSTILA-LAITETESTI | kesken (flashattu 5.10.2026, 6aff448; toimii joutokäynnillä, uuttoa ja valmiustilaa ei testattu) (todenna viim. 12.10.2026) | käyttäjän läsnäollessa: `stby:on` → STBY_ON ja lasku kohti 90 °C ilman GUARD_TRIPiä; uutto-, kuumavesi-, höyrykytkin → STBY_OFF reason=switch; yksi kahvi → `BREW_LOG ready n=`; muisti 650 rivillä |
| V-154 menetelmä | korjattu 32fb76e 5.10.2026 (menetelmä (a)), flashattu cae9100; odottaa päivää 6.10.2026 (todenna viim. 12.10.2026) | aamulla 6.10.2026: keitin verkkovirtaan ilman Zeron irrotusta → lämpeneekö ~1,5 min sisällä; kysy käyttäjältä ja lue `pico_dev.py cmd stby:30` (temp nousee). Todennettu → V-154 ja kiertotie (USB irti illaksi / Zero irti aamulla) pois |

## 6.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-V154-TODENNUS — aamulla 6.10.2026 keitin verkkovirtaan ilman Zeron irrotusta: lämpeneekö ~1,5 min sisällä (käyttäjän havainto + `pico_dev.py cmd stby:30` temp nousee); todennettu → V-154 ja kiertotie pois — polut: Infra/iot/expresso/pico/relayguard.py, Infra/iot/expresso/REKISTERI.md — aloitus: /pura infra expresso

### Todettu 5.10.2026 — Picon yhteys kulkee Zeron kautta; uuttoloki-setti flashattu (EXPRESSO-ZERO-FLASH) — poistettu tai muutettu

- Firmware 5.10.2026: Pico ajaa cae9100:n settiä (e4b9afa kuri-säätötila dev_run:n kautta, 32fb76e relayguardin ei-nouse-lukon uusinta); Zero-flashit FLASH_OK 1/20, VERIFIED 20/20, `stby:30` → temp=102.0 (keitin verkkovirrassa, lämmin); lokit `testit/flash-20261005-zero-devrun.log`, `…-zero-v154.log`. `pico_dev.py cmd` heti flashin jälkeen palautti tyhjän (exit 0) kahdesti, 15 s ikkunalla onnistui: odota/uusi kerran ennen kuin päättelet firmwaren kaatuneen.

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Aamun kaatuminen 5.10.2026: heat_dead vs MemoryError | avoin (syy päätelty, ei todennettu, ei lokia); odottaa päivää 6.10.2026 (todenna viim. 12.10.2026) | 6.10. aamun todennus kertoo osaltaan: jos keitin lämpenee, heat_dead oli syy; muuten ehdota: Zerolle Picon sarjatulosteen pysyvä loki (ser2net ei lokita; `infra zero` -skoopin asia) ja kysy käyttäjältä oire (ei lämmennyt vs sovellus ei yhteyttä) |
| V-154 menetelmä | korjattu 32fb76e 5.10.2026 (menetelmä (a)), flashattu cae9100, relayguard.py ennallaan e89d205-flashissa; odottaa päivää 6.10.2026 (todenna viim. 12.10.2026) | aamulla 6.10.2026: keitin verkkovirtaan ilman Zeron irrotusta → lämpeneekö ~1,5 min sisällä; kysy käyttäjältä ja lue `pico_dev.py cmd stby:30` (temp nousee). Todennettu → V-154 ja kiertotie (USB irti illaksi / Zero irti aamulla) pois |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| **V-154 (toistui 5.10.2026 aamulla):** keitin verkkovirtaan → "firmware kaatunut"; syy päätelty (Zeron VBUS piti Picon päällä, lämmitinrele päällä ilman verkkovirtaa, `relayguard` `heat_dead` lukitsi lämmityksen), ei todennettu. Korjaus 32fb76e: lukon uusinta (Päätökset 5.10.2026), flashattu cae9100. | korjattu 32fb76e 5.10.2026; odottaa päivää 6.10.2026 (todenna viim. 12.10.2026) |

## 6.10.2026 — infra expresso

### Päätökset — poistettu tai muutettu

- **5.10.2026 (käyttäjä: "Päätä itse" → pääistunto):** järjestys (1) flash-reitti Zeron kautta (tehty 669d3bb), (2) V-154-korjaus, (3) UUTTOLOKI-LAITE-todennus. Flash Zerolla omalla raakaREPL-kirjoittimella, ei mpremotella (vahti 8 s, releluenta). Väliaikainen kiertotie kunnes V-154 korjattu: keittimen USB irti Zerosta illaksi, tai aamulla Zero irti + keitin pois–päälle.
- **Käyttäjä 5.10.2026 (V-154 menetelmä):** valitsi (a) heat_dead-lukon vapautus; hylätty (b) optoerotin GPIO:hon ja (c) Picon syöttö keittimestä. Mitoitus (pääistunto): jäähtyminen ≥ 10 °C lukitushetken lukemasta todistaa anturin kattilassa → uusinta 60 s välein rajatta; ilman todistetta 3 uusintaa 10 min välein, sitten lukko uudelleenkäynnistykseen asti; uusinta lämmittää 30 s (ensimmäinen ikkuna 120 s ennallaan), joten irronneen anturin lisälämpö ≤ 3 × ~33 kJ. Tunnettu raja: Pico käynnistyy uudelleen keittimen ollessa kylmä ja irti verkosta → 3 uusintaa kuluu ja aamulla lukko on päällä → kiertotie Zeron irrotus / Picon reset.

## 6.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-V154-SYY — selvitä koodista ja smokeilla, miksi heat_dead-lukko jäi 6.10. aamulla päälle ilman lämmittävää uusintaa, korjaa ja lisää firmwareen tilakomento (mitattu lämpötila + lukon tila); flash vasta käyttäjän kuittauksella — polut: Infra/iot/expresso/pico/relayguard.py, Infra/iot/expresso/pico/commands.py, Infra/iot/expresso/REKISTERI.md — aloitus: /pura infra expresso — automaattinen: kyllä

### Todettu 6.10.2026 — V-154-todennus epäonnistui — poistettu tai muutettu

- Keitin verkkovirtaan ~05.57 (Zeron USB kiinni koko yön): virtavalo päällä, lämmitysvalo ei; sovellus (`uiautomator dump`) 05.58–06.02 ennallaan 23,1 °C, −1,4 bar; `stby:30` 06.01 → `STBY_OFF reason=app`, tavoite 102, ei lämmitystä; sarjaportissa ei `GUARD_RETRY`/`GUARD_TRIP`. Reset (`pico_dev.py safe` 06.03) → lämmitysvalo palaa heti, tila menetetty ennen syyn kaappausta.
- Hypoteesit, ei tarkistettu: −1,4 bar lepopaine lähellä `PRESSURE_RAW_MIN_BAR` −1,5:tä (`relayguard.py:48`); proven-tila ei nollaudu uusinnassa vaan lämmön noustessa (`relayguard.py:225–245`).

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| V-154 menetelmä | avoin (todennus epäonnistui 6.10.2026, korjaus 32fb76e ei riitä; syy selvittämättä, ks. Todettu 6.10.2026) | EXPRESSO-V154-SYY: selvitä koodista ja smokeilla, miksi lukko jäi ilman lämmittävää uusintaa; lisää firmwareen tilakomento (mitattu lämpötila, lukon tila); flash vain käyttäjän kuittauksella |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| **`stby:30`:n `temp=` luettiin mitatuksi lämpötilaksi:** STBY-raportti tulostaa `get_target_temperature()` (`pico/commands.py:460`); 5.10. flashin todennus ja V-154-menetelmä nojasivat siihen. Menetelmä korjattu: sovelluksen lämpötila `uiautomator dump`illa. | avoin (5.10.2026 klo 22.15; EXPRESSO-V154-SYY lisää tilakomennon) |
| **V-154 (toistui 5.10. ja 6.10.2026):** keitin verkkovirtaan → lämmitysvalo pois; syy päätelty, ei todennettu (Päätökset 5.10.2026). Korjaus 32fb76e (lukon uusinta), flashattu cae9100, ei todentunut 6.10.2026: sama oire, reset korjasi. | avoin (korjaus 32fb76e ei todentunut 6.10.2026; syy selvittämättä) |

## 6.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-V154-FLASH — päivitä pico/MANIFEST.json ja flashaa 9103dc2 Zerolla käyttäjän kuittauksella (VERIFIED), aja `heat?`; aamutesti: keitin verkkoon, `heat?`, tarvittaessa sovelluksen asetusmuutos → GUARD_RETRY user=app ja lämmitysvalo; kysy samalla valvomattoman kylmäkäynnistyksen ratkaisu — polut: Infra/iot/expresso/pico/MANIFEST.json, Infra/iot/expresso/REKISTERI.md — aloitus: /pura infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| V-154 menetelmä | korjattu 9103dc2, ei flashattu; odottaa käyttäjää (todenna viim. 13.10.2026) | EXPRESSO-V154-FLASH; älä flashaa keittimen ollessa kylmä ja irti verkosta |
| Kylmä käynnistys irti verkosta jättää lukon aamuksi, kunnes käyttäjä koskee kytkimeen/sovellukseen | avoin; odottaa käyttäjää (kirjattu 6.10.2026) | päätös: hidas uusinta (30 s / 60 min), pumppupulssi verkkotunnistukseen tai nykyinen + kiertotie |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| **`stby:30`:n `temp=` luettiin mitatuksi lämpötilaksi:** se oli `get_target_temperature()`; 5.10. todennus nojasi siihen. 9103dc2: `target=` + `heat?`. | korjattu 9103dc2; odottaa ajoa (todenna viim. 13.10.2026) |
| **V-154 (toistui 5.10. ja 6.10.2026):** syy kylmä flash irti verkosta (32fb76e:n tunnettu raja); korjaus 9103dc2 `user_retry`. | korjattu 9103dc2; odottaa käyttäjää (todenna viim. 13.10.2026) |

## 6.10.2026 — infra expresso

### Todettu 5.10.2026 — Picon yhteys kulkee Zeron kautta; uuttoloki-setti flashattu (EXPRESSO-ZERO-FLASH) — poistettu tai muutettu

- Firmware 5.10.2026: Pico ajaa cae9100:n settiä (e4b9afa kuri-säätötila dev_run:n kautta, 32fb76e relayguardin ei-nouse-lukon uusinta); Zero-flashit FLASH_OK 1/20, VERIFIED 20/20, `stby:30` → temp=102.0 (asetusarvo, ei mittaus: `commands.py:460`); lokit `testit/flash-20261005-zero-devrun.log`, `…-zero-v154.log`. `pico_dev.py cmd` heti flashin jälkeen palautti tyhjän (exit 0) kahdesti, 15 s ikkunalla onnistui: odota/uusi kerran ennen kuin päättelet firmwaren kaatuneen.

## 6.10.2026 — infra expresso

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| `build_set.py` ei kirjoita rakentamansa manifestia repoon, joten `pico_dev.py verify Infra/iot/expresso/pico/MANIFEST.json` vertaa laitetta vanhentuneeseen manifestiin ja antaa väärän `MISMATCH`-tuloksen. Oire tässä sessiossa: `VERIFIED 15/17`, `/functions.py MISMATCH` ja `/main.py MISMATCH`, vaikka laitteen tiivisteet täsmäsivät paikallisiin lähdetiedostoihin (6592c81f40cc, c00e9c500b2a). Korjattiin käsin kopioimalla puhelimen manifesti; korjaus työkaluun tekemättä. | Uusi, avoin (työkalu) |

## 6.10.2026 — infra expresso

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| `verdict` ei päättele mekanismia `PSKIP_SUB`/`PSKIP_FUND`- suhteesta, vaikka laskee molemmat. | Uusi, avoin (analysaattori) |
| `PGAP_BEST`-rivi poimii yksittäisen suurimman lukeman, ei keskiarvoa. Se nimesi "parhaaksi" vaiheen, jonka toinen toisto oli keskitasoa. | Uusi, avoin (analysaattori) |

### Viat — valmis

| Vika | Tila |
|---|---|
| `verdict` ei päättele mekanismia `PSKIP_SUB`/`PSKIP_FUND`- suhteesta, vaikka laskee molemmat. | valmis 6.10.2026 — vanhentunut: `psweep_read` lukee portitettua pyyhkäisyä, joka hylättiin 28dff60:ssä; suureen valinta jatkuu rivillä "Analysaattorin tuomio" |
| `PGAP_BEST`-rivi poimii yksittäisen suurimman lukeman, ei keskiarvoa. Se nimesi "parhaaksi" vaiheen, jonka toinen toisto oli keskitasoa. | valmis 6.10.2026 — vanhentunut: `pico/functions.py` ei tulosta `PGAP_BEST`-riviä (vain `PGAP k=`, `PGAP_END`) |

## 6.10.2026 — infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Aamun kaatuminen 5.10.2026: heat_dead vs MemoryError | avoin (6.10.2026 sama oire, syy auki, ei lokia); odottaa käyttäjää | Zerolle Picon sarjatulosteen pysyvä loki (`infra zero` -skoopin asia): todiste puuttunut kahdesti (5.10., 6.10.); käyttäjän päätös |

## 6.10.2026 — infra expresso

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| `restore` ajettiin `timeout 300`:lla, vaikka sen oma odotus on 300 s + laturisykli: flash onnistui (RESTORE_OK 4 min 51 s), mutta katkaisu ohitti `ChargerOff.__exit__`:n ja laturi jäi pois (palautettu käsin). Sääntö: ulompi aikaraja ≥ työkalun oma raja + 60 s. | Uusi, avoin (prosessi, pääistunto 27.9.2026) |
| kaksi `pico_dev.py capture` -prosessia päällekkäin (vanha jatkoi TaskStopin jälkeen) → toinen ei saanut dataa, laturi kytkeytyi kesken; TaskStop ei aina lopeta python-lasta. | Uusi, avoin (työkalu, 28.9.2026) |
| ZERO-PARITEETTI-briefin Acceptance 5 (`git diff --name-only`) ei läpäissyt toisen keskustelun likaisten tiedostojen takia; rajaa polkuun. | avoin (prosessi, 6.10.2026) |

## 6.10.2026 — infra expresso

### Viat — valmis

| Vika | Tila |
|---|---|
| PICO-DEV-LUKKO-brief olisi kytkenyt laturin restore-flashin aikana (`restore()` lukematta). | korjattu d919331, todennettu diff-katselmoinnissa ennen committia |

## 6.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-V154-AAMUTESTI — aamulla 7.10.2026 (viim. 13.10.2026): keitin verkkoon, `pico_dev.py cmd 'heat?' 6`; jos dead=1, sovelluksen asetusmuutos → GUARD_RETRY user=app ja lämmitysvalo; todenna V-154 — polut: Infra/iot/expresso/REKISTERI.md — aloitus: /pura infra expresso

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| `pico_dev.py verify` kaatui kahdesti vkello4:n palautuksen jälkeen ennen `VERIFIED 19/19`:ää: (1) CHARGER off/on -sykli osui USB:n uudelleenavaukseen (`tail b''`, PicoUsb `USB closed` 19:16:17) — `Link.__init__` tunnistaa vain `ERR usb closed`in, ei tyhjää helloa; (2) BLE-sovelluksen `Received: 'sync'`/`'brew_log?'`-rivit tulivat raw REPL -vastauksen `\x04>` perään, ja `Link.until` (pico_dev.py:155-167) vaatii `endswith(marker)` → timeout 10/19 jälkeen. Kiertotie uusintayritys; korjaus (`marker in buf`, tyhjä hello → force-stop + ensure_bridge) tekemättä. **24.9.2026:** `restore` kaatui kahdesti heti (`RESTORE_FAIL … no size ack for /api_functions.py`, logcat `USB get_status request failed`: sovellus piti laturisyklin jälkeen kuollutta USB-kahvaa) → `pico_dev.py restore` tekee nyt `am force-stop` ennen palautusta (vsweep1 meni läpi sillä). Ensimmäinen `verify` palautuksen jälkeen antoi yhä `tail b''` (uusinta 19/19); `Link`-korjaus tekemättä. **Uusi, avoin 24.9.2026:** komento jäi ilman vastausta (`cmd bp:8` 1×, `klamp 60` → `KLAMP_FAIL reason=no_end` ja tyhjä `testit/klamp-20260924-b.log`, `cmd klamp:stop` 1×), PicoBridge `bridge client closed` heti yhteyden jälkeen; käyttäjä kokeili toista virtalähdettä ja palautti alkuperäisen, sen jälkeen ajot toimivat — juurisyy selvittämättä. **24.9.2026 (esiu1/esiu2):** yhteysvika toistui 2× (ensimmäinen `shot` laturisyklin jälkeen tyhjään, hubi irtosi 0,6 s:ssa, logcat 13:23:29), uusinta auttoi. **Uusi, avoin 24.9.2026:** `build_set.py` ei päivitä repon `pico/MANIFEST.json`:ia, joten `verify` vertaa vanhaan manifestiin (esiu1: 15/19 MISMATCH juuri muuttuneille); kiertotie: tiivisteet paikallisista tiedostoista manifestiin ennen verifyä (a596e32, f200ffe); korjaus: build_set kirjoittaa repon manifestin. **25.9.2026:** yhteysvika toistui satunnaisesti 2× (`pit:6` → `Connection refused`, `shot c` → sama laturisyklin jälkeen); uusinta auttoi molemmilla kerroilla. | Uusi, avoin (työkalu, 23.9.2026) |
| `testit/valmiustila_smoke.py` testasi hiljaa `/tmp/fw`:n vanhaa kopiota repon sijaan (5.10.2026); `ctrl_real_test.py` ja `shot_test.py` käyttävät samaa oletusta. | korjattu 9103dc2 (valmiustila_smoke; muut avoin, työkalu) |

### Viat — valmis

| Vika | Tila |
|---|---|
| `testit/valmiustila_smoke.py` testasi hiljaa `/tmp/fw`:n vanhaa kopiota repon sijaan (5.10.2026); `ctrl_real_test.py` ja `shot_test.py` käyttävät samaa oletusta. `shot_test.py` oli vihreä vain siksi (valelaitteesta puuttui `user_retry`, joten 9103dc2:n `note_activity`-polkua ei testattu). | korjattu 25f5634 6.10.2026 (valmiustila_smoke 9103dc2; ctrl_real_test, shot_test 25f5634) |

## 7.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-V154-AAMUTESTI — aamulla 7.10.2026 (viim. 13.10.2026): keitin verkkoon, `pico_dev.py cmd 'heat?' 6`; jos dead=1, sovelluksen asetusmuutos → GUARD_RETRY user=app ja lämmitysvalo; todenna V-154; samalla ajossa PICO-DEV-LINK (aa77c57) todentuu laitteella — polut: Infra/iot/expresso/REKISTERI.md — aloitus: /pura infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Vaiheet 1c–1f, 2 (pre-infusion auto vaa'asta), 3 (max flow rate), 4 (höyry +10 °C) | avoinna | `paketit/PUMPPU-PWM.md` vaihetaulukko; 1c:n muoto riippuu yhä 1b:n päätöksestä |
| Aamun kaatuminen 5.10.2026: heat_dead vs MemoryError (toistui 6.10., ei lokia) | avoin; odottaa skooppia infra zero (V-207, f37507e) | pysyvä loki päätetty 6.10.2026; sen jälkeen `pico_dev.py log` ja syy lokista; ZERO-PARITEETTI (465c241): harkitse tiedostojen lukua ja BOOTSEL-komentoa |
| V-154 menetelmä | korjattu 3f8abc8 6.10.2026 (9103dc2 flashattu, `heat?` dead=0 guard=ok); odottaa päivää 7.10.2026 (aamutesti; todenna viim. 13.10.2026) (todenna viim. 20.10.2026) | EXPRESSO-V154-AAMUTESTI (ks. SEURAAVA PAKETTI) |
| PICO-DEV-LINK (`pico_dev.py` Link: kohinan sieto ja hiljaisen sillan uudelleenavaus) | korjattu aa77c57 6.10.2026; odottaa ajoa (todenna viim. 13.10.2026) | seuraavassa laiteajossa: `LINK_REOPEN`-rivi ja ajo jatkuu `tail b''`:n sijaan; verify ei kaadu kohinaan |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| **V-154 (toistui 5.10. ja 6.10.2026):** syy kylmä flash irti verkosta (32fb76e:n tunnettu raja); korjaus 9103dc2 `user_retry`. | korjattu 3f8abc8 6.10.2026 (flashattu); odottaa päivää 7.10.2026 (aamutesti; todenna viim. 13.10.2026) (todenna viim. 20.10.2026) |

### Avoimet asiat — valmis

| Asia | Tila | Seuraava askel |
|---|---|---|
| V-154 menetelmä | valmis 7.10.2026 (todennettu aamutestissä: Zero-linkki, 25,6 → 105 °C ~3 min, dead=0 retries=0, sovellusta ei tarvittu) | — |

### Viat — valmis

| Vika | Tila |
|---|---|
| **V-154 (toistui 5.10. ja 6.10.2026):** syy kylmä flash irti verkosta (32fb76e:n tunnettu raja); korjaus 9103dc2 `user_retry`. | valmis 7.10.2026 (todennettu laitteella 7.10.2026 klo 06.11–06.15, Todettu 7.10.2026) |

## 7.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-IDEAT-LUOKITTELU — luokittele infra expressolle reititetyt 12 IDEAT-riviä (V-062, V-119, V-122, V-128, V-143, V-149, V-197, V-204, V-205, V-210, V-214, V-220): kirjaa kukin rekisteriin tiloineen tai sulje; V-205 ei enää estä expresso-iosia (Android-äppi suljettu, iPhonen BLE-testi läpi 6.10.2026 21.15, 0b0cca4) — polut: Infra/iot/expresso/REKISTERI.md — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — valmis

| Asia | Tila | Seuraava askel |
|---|---|---|
| V-062 akkuvahti palvelimen cronissa | valmis 8dccbec 7.10.2026 (loki 7.10. 08.00 `AKKU: 79 % lataa=false rajat=30/60`) | — |
| V-197 akkuvahdin HA-rajat | valmis 8dccbec 7.10.2026 | — |
| V-143 USB-silta Picolle (ser2net 2217) | valmis 669d3bb 7.10.2026 | — |
| V-149 laturikierto Zero-linkillä ja PICO-HALLINTA §8 | valmis 8dccbec 7.10.2026 (669d3bb ja 8dccbec) | — |
| V-214 TILAUS-AUTONOMIA-tunnusrivi | valmis 8dccbec 7.10.2026 | — |
| V-204 Flutter lib/ Android-build | valmis 7.10.2026 (Android-äppi suljettu 6.10.2026, 0b0cca4) | — |
| V-205 Picon yksi BLE-yhteys | valmis 7.10.2026 (Android-äppi suljettu, iPhonen BLE-testi läpi 0b0cca4) | — |

## 7.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: ei mitään — odottaa käyttäjää: EXPRESSO-TURVAKATO (korjauslistan järjestys), PUMPPU-PWM vaiheet 1c–4 (laiteajon ajankohta), EXPRESSO-VIRTAUSTESTI (V-119/V-128, laiteajo), stbt-flash (V-220), V-210 avainero (firmware vai äppi); aamun kaatuminen odottaa skooppia infra zero (V-207)

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-TURVAKATO | selvitys tehty 21.9.2026 (koodiluku, ei laitteella), korjaukset avoinna | `paketit/TURVAKATO.md` luvut "Selvitys 21.9.2026" ja "Korjauslista": 7 kohdan korjauslista, järjestys käyttäjän päätettävä. Juurisyy: jokainen turvaraja on komennon sisällä, ei toimilaitteen vieressä. Käyttäjä nimesi luokan mahdollisesti hengenvaaralliseksi |
| `pcal` kaukalovahdin piiriin? | päätetty 7.10.2026: **ei** (käyttäjä) — `pcal` jää kaukalovahdin ulkopuolelle | valmis; rivi pois pakkauksessa |
| Kuumavesikytkimen aika-/lämpöraja | käyttäjän päätös | — |
| V-220 stbt-flash (14772b0) | avoin; odottaa käyttäjää (ei flashattu: `pico/commands.py` sha256 ≠ `pico/MANIFEST.json`, 7.10.2026) | flash käyttäjän kuittauksella, MANIFEST päivitetään flashissa |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| kolme kertaa este löytyi suunnittelijan omasta artefaktista — kahdesti holdoutin mahdottomasta väitteestä, kerran briefin liian kapeasta `read:`-rajauksesta. Joka kerta toteuttaja oli oikeassa ja pysähtyi oikein. Opetus kirjattu `PWM-1G-…correction-1.md`:hen: kun spec sanoo "sama kuin X:ssä", lukulistan on katettava myös X:n kutsuja. | Uusi, avoin (prosessi) |

## 12.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: ei mitään — odottaa käyttäjää: EXPRESSO-KUUMAVESI-RAJAT flash + laitetodennus (aa3bb8c), EXPRESSO-TURVAKATO kohta 7 (laitetarkistukset), PUMPPU-PWM vaiheet 1c–4 (laiteajon ajankohta), EXPRESSO-VIRTAUSTESTI (V-119/V-128, laiteajo), V-210 avainero (firmware vai äppi); V-231 havainto: `pico_dev.py capture 1320` päättyi ~11 min kohdalla exit 0, syy selvittämättä; aamun kaatuminen odottaa skooppia infra zero (V-207)

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-TURVAKATO | kohdat 1,2,3,5 flashattu (vkello4 23.9.), kohta 4 koodissa aa3bb8c ei flashattu, pcal päätetty, kohta 6 claude siirto | jäljellä kohta 7 laitteella (mekaaninen varoventtiili, asyncio.gather-poikkeus, relepinnit nollauksessa, wmax-nollautumisen syy) + kohdan 4 flash ja laitetodennus (kuumavesikytkin: HOT_WATER_END reason=time 1 s:ssa) — vaatii käyttäjän läsnäolon/kuittauksen. |
| Kuumavesikytkimen aika-/lämpöraja | korjattu aa3bb8c; odottaa käyttäjää (päätetty ja tehty koodissa aa3bb8c, odottaa flashia) **7.10.2026:** Ennen korjausta lämmitin 100 % ilman termostaattia, pumppu katkesi 180 s:ssa mutta lämmitin jatkoi 160 °C:een, kattilan laajeneminen ~14 bar; aa3bb8c acceptance ajettu: py_compile ok, smoket exit 0, main.py 0 kytkinsilmukkaa. | flash käyttäjän kuittauksella (V-154-raja: keitin lämmin ja verkossa), sitten kuumavesikytkimen painallus laitteella: odotus `HOT_WATER_END reason=time`, pumppu ja lämmitin pois ~1 s:ssa. |
| Laitteelta tarkistettavat: mekaaninen varoventtiili, `asyncio.gather`-poikkeuksen kulku, relepinnit nollauksessa, wmax-nollautumisen syy | avoin | tarkista laitteella/koodista (`HISTORIA.md:104-105` vs rekisteri) |
| EXPRESSO-KUUMAVESI-RAJAT | korjattu aa3bb8c; odottaa käyttäjää (ei flashattu) | flash käyttäjän kuittauksella (V-154-raja: keitin lämmin ja verkossa), sitten kuumavesikytkimen painallus laitteella: odotus `HOT_WATER_END reason=time`, pumppu ja lämmitin pois ~1 s:ssa. |

### Avoimet asiat — valmis

| Asia | Tila | Seuraava askel |
|---|---|---|
| V-220 stbt-flash (14772b0) | valmis — flashattu Zeron kautta ja laitetodennettu iPhone-äpillä 7.10.2026 (c38a13f, toinen keskustelu, V-231): VERIFIED 20/20, FLASH_OK; STBT temp=70, STBY_ON idle_s=900, kytkin → STBY_OFF reason=switch (`testit/stbt-20261007-laite*.log`) | — |

| Asia | Tila | Seuraava askel |
|---|---|---|
| Kuumavesikytkimen aika-/lämpöraja | valmis 520ef47 (7.10.2026; flashattu b466b19, `HOT_WATER_END reason=time`) | — |
| Laitteelta tarkistettavat: mekaaninen varoventtiili, `asyncio.gather`-poikkeuksen kulku, relepinnit nollauksessa, wmax-nollautumisen syy | valmis d56d07e (7.10.2026; varoventtiili olemassa, gather 310 ms ja releet [0,0,0], nollauksessa wmax säilyi) | wmax-syy: ks. rivi "wmax-pysyvyys" |
| EXPRESSO-KUUMAVESI-RAJAT | valmis 520ef47 (7.10.2026; flash b466b19 VERIFIED 20/20) | — |

## 14.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-SKOOPPIJAKO — jaa infra expresso yläskoopiksi expresso ja alaskoopeiksi turva, säätö, laite, integraatiot (käyttäjä hyväksyi 12.10.2026; jako Päätökset-luvussa), sitten EXPRESSO-PICO-SARJALOKI skoopissa expresso laite — polut: Infra/iot/expresso/REKISTERI.md, Infra/iot/expresso/ — aloitus: /pura infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-TEMPSTALE-JA-OLETUS | isäntä tehty bdb8463 (todenna viim. 12.10.2026) | flash + laitetodennus käyttäjän kanssa: `TEMP_C1 ready`, `PB_END … c1_n>0 c1_gap_ms≤400 c1_err=0`, ei tempstale-GUARD_TRIPiä, EU_VV/EB_VV late/lmax ennallaan; REPL: ydin 1 ei allokoi (c1_err=0 riittää, heap_lock) |
| Flashaus (KAUKALOVAHTI-KOKONAISPAINO + PIKAKORJAUKSET + TURVA-TOIMILAITE + ANTURIUSKOTTAVUUS) | esiavoin1 todennettu laitteelta 26.9.2026 (VERIFIED 19/19; HISTORIA.md:24 mukaan esiavoin1 = 0028dff, sisältää kaukalovahdin ym. korjaukset, kumpikin flashi VERIFIED 19/19, releet [0,0,0]) (todenna viim. 12.10.2026) | TURVA-TOIMILAITE ja ANTURIUSKOTTAVUUS yhä todentamatta laitteella. |
| Käyttöönottoketju (käyttäjä 26.9.2026, KAYTTAJAN-TIEDOT luku 7; valitsi "Myös 8 bar ensin", hylätty "Esiuutto nyt, 8 bar myöhemmin") | järjestys käyttäjän: (1) EXPRESSO-ESIUUTTO-HYVAKSYNTA: firmware-versio laitteelta, lämmin/kylmä-tila ja 6 s pito lämpimällä kuristimella esiavoin1:llä (`hold`), käyttäjän hyväksyntä esiuutolle — kohta (1) ajettu 26.9.2026, ei hyväksytty (toinen ja kolmas kerta 26.–27.9.2026: EXPRESSO-ESIUUTTO-UUTTOASENTO ja EXPRESSO-ESIUUTTO-VUORONVARAUS ajettu, ei hyväksytty); neljäs kerta 27.9.2026 rampinloppu1 = 651afec (at–aw): **hyväksytty**; (2) TILAUS-K vaiheet 3–4 8 barille toteutus + laitetestit; (3) pim:1 pysyväksi oletukseksi (nyt RAM, commands.py:301-307) ja (4) EXPRESSO-UUTTOLOKI: kohta (4) isäntä valmis 9deb88f (elokuun brew_logger + BLE-multipack + `sync`/`brew_log?`/`brew_log:ack` nykyiseen firmwareen samaan flashiin, protokolla puhelimen `files/firmware/`-kopiosta, sovellus ennallaan); (5) todennus oikealla kahvilla: brew_shots.jsonl kasvaa (todenna viim. 12.10.2026) | (1) hyväksytty 27.9.2026 (at–aw, ylitys 0,08–0,32); (2) valmis — isäntä 75b8a62 + laiteajo todennettu 28.9.2026 (a–d2, EXPRESSO-UUTTO-8BAR); ennen (3):a tempstale-korjaus (EXPRESSO-TEMPSTALE-JA-OLETUS, muuten lämmitin estetty koko pidon ajan oikeassa uutossa); sitten (3) pim:1 ja bim:1 pysyväksi oletukseksi; (4) flash + (5) todennus oikealla kahvilla: brew_shots.jsonl kasvaa, todenna viim. 12.10.2026. |
| EXPRESSO-UUTTOLOKI-LAITE + EXPRESSO-VALMIUSTILA-LAITETESTI | kesken (flashattu 5.10.2026, 6aff448 + valmiustila e89d205; `stby:on` → STBY_ON ja `stby:30` → temp=102.0 todennettu laitteella 5.10.2026, uuttoa ei testattu) (todenna viim. 12.10.2026) | käyttäjän läsnäollessa: lasku kohti 90 °C ilman GUARD_TRIPiä; uutto-, kuumavesi-, höyrykytkin → STBY_OFF reason=switch; yksi kahvi → `BREW_LOG ready n=`; muisti 650 rivillä |
| Uutto käynnistyi verkkovirrattomana (`PB_END reason=stopped`, −0,6 bar, 5.10.2026) | todentamatta (todenna viim. 12.10.2026) | selvitä uuttokytkimen tulon käytös keittimen ollessa pois |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| **`stby:30`:n `temp=` luettiin mitatuksi lämpötilaksi:** se oli `get_target_temperature()`; 5.10. todennus nojasi siihen. 9103dc2: `target=` + `heat?`. | korjattu 9103dc2 6.10.2026 (flashattu 3f8abc8); odottaa ajoa (todenna viim. 13.10.2026) |

## 20.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: ei mitään — käyttäjä valitsi pakkaa vain 14.10.2026

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Käyttäjän hypoteesi (vesi valuu pumpun läpi säiliöön paineen vuoksi) | todentamatta (todenna viim. 19.10.2026) | mittaa: painelukema levossa ennen/jälkeen valmiustilan ja pumpun käyntiaika ensimmäiseen veteen pitkän levon jälkeen (valmiustilan kanssa vs. ilman); mahdollisesti takaiskuventtiilin tarkistus. |
| Äppi ei näytä valmiustilaa (kirjattu 5.10.2026) | todennettu 5.10.2026 (a741d90 + flash: FLASH_OK, VERIFIED 20/20, `testit/flash-20261005-zero-valmiustila.log`): live-paketissa `standby: true` vain valmiustilassa (228 B ≤ 240); sovellus (Macin `silvia_pico_flutter_UI`, varmuuskopio `../silvia_pico_flutter_UI-varmuus-20261005-valmiustila.tgz`) `MachineStatus.standby`, pystynäkymän Mode `IDLE · STANDBY`, vaakanäkymässä `STANDBY` lämpötilan alla; APK asennettu OnePlussaan `adb install -r`; laitteella `stby:on` → `IDLE · STANDBY`, `stby:30` → `IDLE` (pystynäkymä) (todenna viim. 19.10.2026) | vaakanäkymän `STANDBY`-teksti todentamatta laitteella (vain `flutter analyze` 0 virhettä); seuraavassa vaakatilan käytössä katso. |
| ENOMEM-mekanismi (relayguard Timer) | korjattu 6aff448 (järjestys; syy todentamatta) (todenna viim. 19.10.2026) | ei toimenpidettä ellei toistu |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| Pico nollautuu itsestään ~1–2 h välein 5.10.2026 alkaen (51 USB disconnectia 4 pv:ssä, Zeron `journalctl -k`); syy tuntematon, ei tracebackia; mahdollinen yhteys "uutto rikki" -havaintoon 13.41.39 | avoin; odottaa skooppia expresso laite (sarjaloki, EXPRESSO-PICO-SARJALOKI) |

## 20.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-WIFI-AIKAIKKUNA — Wi-Fin (wifilink 47211 + diagnet 47210) kuorma uuton aikana minimiin niin, että tieto siirtyy yhä hyvin: kartoita mitä lähetetään ja kuinka usein uuton vaiheissa, mittaa EU_STALL task=wifi/diag, sendto-ajat ja max_loop_ms ennen/jälkeen, ehdota ja toteuta rajaus (käyttäjä 20.10.2026) — polut: Infra/iot/expresso/pico/**, Infra/iot/expresso/testit/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-WIFI-AIKAIKKUNA (uusi) | avoin (käyttäjä 20.10.2026) | arvioi ja minimoi Wi-Fin (wifilink + diagnet) kuorma uuton aikana: mitä lähetetään, kuinka usein, milloin radio/soketti toimii; mittaa `EU_STALL` task=wifi/diag ja `max_loop_ms` ennen/jälkeen |
| Todennus oikealla uutolla | avoin; odottaa käyttäjää | Wi-Fi etualalla (live, paino, loki), lukittu puhelin (BLE-tausta, painokehote), `max_loop_ms` vs. 145 ms |
| Wi-Fi live 2,8 Hz ja hello ~1 s (virransäästö?) | avoin | selvitys aikaikkunapaketissa (EXPRESSO-WIFI-AIKAIKKUNA) |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| `pico_dev.py` yhteysvika: satunnainen `Connection refused` / `bridge client closed` laturisyklin jälkeen (24.–25.9.2026: `cmd bp:8`, `klamp 60` → `KLAMP_FAIL reason=no_end`, `cmd klamp:stop`, esiu1/esiu2 `shot`, `pit:6`); uusinta auttoi, juurisyy selvittämättä (käyttäjä vaihtoi virtalähdettä ja palautti, ajot toimivat). Korjattu: Link-osat (`endswith` → `marker in buf`; hiljainen silta → reopen ja uusinta) aa77c57 6.10.2026, build_set-manifesti 52f4fa6, `restore` tekee `am force-stop`in. | kesken aa77c57 6.10.2026 (Link korjattu, manifest 52f4fa6; Connection refused avoin); odottaa ajoa (todenna viim. 20.10.2026) |

## 20.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-GC-UUTTO — roskienkeruun katkot uuton aikana (52 keruuta/20 s, pahin ~100 ms): mietitään käyttäjän kanssa perusteellinen korjauskeino suunnitelman paketit/GC-UUTTO.md pohjalta, suunnittelukeskustelu ensin ennen koodimuutoksia (käyttäjä 20.10.2026) — polut: Infra/iot/expresso/paketit/GC-UUTTO.md, Infra/iot/expresso/pico/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-GC-UUTTO | avoin (suunnitelma `paketit/GC-UUTTO.md`) | suunnittelukeskustelu käyttäjän kanssa perusteellisesta korjauskeinosta (vaihtoehdot: halvat korjaukset, 1 kHz kokonaisluvuiksi, jäädytetyt moduulit); mittaus 2–3 testiuuttoa per versio |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| **Oma (pääistunto 20.10.2026):** 1cd1bbf:n ytimen 1 jitter-koe (`_c1_jitter`) sijoitti tulokset 5 kohteen monisijoituksella, joka rakentaa tuplen. Muisti oli lukittuna, joten tuli MemoryError, ja ytimen 1 lämpötilasäie päättyi (`c1_err=1`). Laitteella (boot 061bcebb) uutto lukee lämpötilan ytimellä 0, ja vahti estää lämmittimen 10 s:n jälkeen (tempstale). Käyttäjän uutto 15.36 näytti `PB_END … c1_err=1`. Koe ei tuottanut C1J-riviä. | korjattu 2ce3a40, flashattu (boot 7efedc62); ytimen 1 lukija todennettu elossa (`ystall:5:34` → `c1=1`) |
| **Oma (pääistunto 20.10.2026):** f0b0454 lisäsi levon DIAG_HB:hen mittauskeruun (`gc.collect` + `mem_alloc`), ja levossa keruu kestää 80–600 ms. Diag-tehtävä vei siksi kerran 771 ms (`testit/vahti-20261020-4-m10.log`, `task=diag:770997`): minuutin välein jopa ~0,5–0,8 s:n katko, jonka mittaus itse aiheuttaa. Todiste ja tausta: `paketit/GC-UUTTO.md` luku Vahtikoe. | korjattu (HB:n keruu pois, `lmax_us`/`l100` jäävät; käyttäjä 20.10.2026 "Molemmat") — flash ja todennus tässä sessiossa |
| `pico_dev.py` yhteysvika: satunnainen `Connection refused` / `bridge client closed` laturisyklin jälkeen (24.–25.9.2026: `cmd bp:8`, `klamp 60` → `KLAMP_FAIL reason=no_end`, `cmd klamp:stop`, esiu1/esiu2 `shot`, `pit:6`); uusinta auttoi, juurisyy selvittämättä (käyttäjä vaihtoi virtalähdettä ja palautti, ajot toimivat). Korjattu: Link-osat (`endswith` → `marker in buf`; hiljainen silta → reopen ja uusinta) aa77c57 6.10.2026, build_set-manifesti 52f4fa6, `restore` tekee `am force-stop`in. **20.10.2026 12.59:** `pico_dev.py safe` → `BrokenPipeError` (pico_dev.py:272 `sendall`) Ctrl-C:n jälkeen; main päättyi releet pois, devsafen vahti resetoi Picon (boot 8cd69aaf). Sama oireluokka; todiste `testit/wifiaika-20261020-safe.log`. | kesken aa77c57 6.10.2026 (Link korjattu, manifest 52f4fa6; Connection refused ja BrokenPipeError avoin); odottaa ajoa (todenna viim. 20.10.2026) |

## 20.10.2026 — infra expresso

### Viat — valmis

| Vika | Tila |
|---|---|
| **Oma (pääistunto 20.10.2026):** f0b0454 lisäsi levon DIAG_HB:hen mittauskeruun (`gc.collect` + `mem_alloc`), ja levossa keruu kestää 80–600 ms. Diag-tehtävä vei siksi kerran 771 ms (`testit/vahti-20261020-4-m10.log`, `task=diag:770997`): minuutin välein jopa ~0,5–0,8 s:n katko, jonka mittaus itse aiheuttaa. Todiste ja tausta: `paketit/GC-UUTTO.md` luku Vahtikoe. | todennettu 3ae611b 20.10.2026 (boot 0f17d6ed ja 033c1656: HB ilman gc_us-kenttää, 0/59 HB:tä) |

## 20.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-C1-JAKSOT — vaihe 2: kattilan lämpötila ytimen 1 toteuttajaan näytteiden väleihin (MAX31865-vaiheiden kesto < 0,5 ms mitataan ensin, K3) ja ydin 1 pyörimään levossa ilman sleep_ms:ia (poistaa levon 0,1–0,6 s keruut); HB lmax_us/l100 todentaa; suunnitelma paketit/C1-JAKSOT.md — polut: Infra/iot/expresso/pico/**, Infra/iot/expresso/testit/**, Infra/iot/expresso/paketit/C1-JAKSOT.md — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-C1-JAKSOT (kirjattu 20.10.2026) | kesken (vaihe 1 valmis e8f9acc) | vaihe 2 (`paketit/C1-JAKSOT.md`): lämpötila ytimelle 1 väleihin, lepo ilman `sleep_ms` |

## 20.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-C1-JAKSOT — vaihe 2 loppuun: koodi on 93d8d2b (ydin 1 ei nuku, lämpötila näytteiden väleihin), flash keskeytyi 20.10. 17.50 → ensin pico_dev.py verify (laitteen tila), sitten flash 93d8d2b ja mittaus ystall-bitillä 512 (K3-kestot < 0,5 ms, levon keruut 17–21 ms, HB lmax_us/l100); suunnitelma paketit/C1-JAKSOT.md — polut: Infra/iot/expresso/pico/**, Infra/iot/expresso/testit/**, Infra/iot/expresso/paketit/C1-JAKSOT.md — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-C1-JAKSOT (kirjattu 20.10.2026) | kesken (vaihe 2 koodi 93d8d2b; flash keskeytyi 20.10. 17.50, laitteella todennäköisesti 3fa436a) | `pico_dev.py verify`, flash 93d8d2b, mittaus ystall 512 |
| Levon 0,1–0,6 s viiveet (käyttäjä, kirjattu 20.10.2026) | avoin (syy ytimen 1 sleep_ms) | C1-JAKSOT vaihe 2 |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| 25a41b8 (C1-JAKSOT osa 7) committiin, vaikka ystall_smoke näytti `FAIL bit 512` (bad 2): testisarja ja commit ketjutettiin yhteen komentoon lukematta tulosta väliin. `_c1_put` ajettiin myös osissa 4 ja 5. Ei flashattu. | korjattu bdc1ac9 20.10.2026 (smoke tarkistaa bad=0); prosessi: commit vasta, kun sarjan tulos on luettu |

## 20.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-C1-JAKSOT — vaihe 3 toteutus suunnitelman mukaan (paketit/C1-JAKSOT.md luku "Vaihe 3 — toteutussuunnitelma", 60d77e4): c1x-valitsin, pre_infusion_phased lukee näytteet ytimen 1 renkaasta ja kirjoittaa päätöksen kohtaan k+2, CX_OK + vahdin ajoraja, nälkä → EU_STARVE, esiuutto_smoke virtuaaliajan ydin 1 -mallilla; laiteajo (läsnäolo + vesi) kysytään erikseen — polut: Infra/iot/expresso/pico/**, Infra/iot/expresso/testit/**, Infra/iot/expresso/paketit/C1-JAKSOT.md — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Esiuuton 2,5 bar säätö | 26.9.2026 (EXPRESSO-ESIUUTTO-FF, 54e3ac9–c323f6f, laitteella esiuff3; EXPRESSO-ESIUUTTO-ALKU, e91816c, laitteella esialku6; EXPRESSO-ESIUUTTO-AVOIN, 0028dff, laitteella esiavoin1): pidon alun ylitys korjattu ryöminnän osalta ja nousun ylitys ~0,4:ään; ff = min(nousun arvio, edellisen pidon tarve × G-suhde), 1. ajo 0,4 × arvio, tarve ja G settings.txt:ssä (säilyy resetin yli), häntävahvistus ja D (KD 0,05); edellisen tiedolla pidon 2 s ka 2,53 / sd 0,068 (h), 1. ajo 2,59–2,76 (f: 2,49 → 2,92); avoimen kuristimen alun alitus korjattu ja todennettu (ab/ac 2,42/2,46, esiavoin1), ff = tavoite / (rate · tau_edellinen + p5), eu_tau_pre settings.txt:hen, integraali rajattu 0…1, hold ajaa pvent-purun; uuttoasento korjattu ja laitteella todennettu 26.9.2026 (417ad93, ah–am); vuoronvaraus korjattu (late 0, aq–as, EXPRESSO-ESIUUTTO-VUORONVARAUS), rampin loppu korjattu isännällä 651afec (smoke 15), ei flashattu; yksityiskohdat `paketit/VAIHESEURANTA.md` | (1) pidon alun ylitys korjattu ryöminnän osalta ja nousun ylitys ~0,4:ään (EXPRESSO-ESIUUTTO-ALKU ajettu); (2) käyttäjän hyväksyntä ennen 8 barin vaiheita on yhä tekemättä (avoin asia 24); (3) 1. ajo ilman tallennettua tietoa ylittää yhä (f: 2,49 → 2,92, ennallaan), avoimella nyt ali (aa 2,19) — tarvittaessa alempi alku; (4) lämmin/kylmä-tila todennettu 26.9.2026 (ad/ae): lämmin → kylmä +0,27 ei läpäise; uuttoasento korjattu ja laitteella todennettu 26.9.2026 (417ad93, ah–am, EXPRESSO-ESIUUTTO-UUTTOASENTO), vuoronvaraus korjattu (aq–as); EXPRESSO-ESIUUTTO-RAMPIN-LOPPU korjattu isännällä (651afec, smoke 15), seuraavaksi flash + hyväksyntäajo. (lisäksi 26.9.2026, EXPRESSO-ESIUUTTO-ALKU): (b) rampin kiinnikurojan ryöppy (y: sp ohitti p5:n 1,1 s:n kohdalla, d 0,42 → 3,87 bar, 1/8 ajosta, malli ei toista) → tiheämpi loki rampin loppuun ja lisää ajoja kuristin lähes kiinni (käyttäjän mukaan epärealistinen tila → matala prioriteetti). |
| Uuttoasennon jälkinousu | mallissa ~1,9 bar (katkaisun rate jää kiihtyvässä täytössä jälkeen), laitteella 0,43–0,89; ao–as kylmällä kuristimella 7 h tauon jälkeen 1,12–1,58 bar, coast_f 0,12–0,155 | seuraa hyväksyntäajossa. |
| EXPRESSO-C1-JAKSOT (kirjattu 20.10.2026) | kesken (vaihe 2 laitteella bdc1ac9; vaihe 3 suunniteltu 60d77e4) | vaihe 3 toteutus (`paketit/C1-JAKSOT.md` luku "Vaihe 3 — toteutussuunnitelma") |
| TILAUS-O (kirjattu 20.10.2026) | avoin (miss 26–116) | C1-JAKSOT vaiheet 3–4 |
| EU-rivi kokonaisluvuin (kirjattu 20.10.2026) | avoin | arvioidaan C1-JAKSOTin jälkeen |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| C1-JAKSOT vaihe 4:n uuttovertailun valmiuskysymys pyysi "kuristin 8 barin asentoon" (20.10.2026), vaikka TILAUS-M oli purun VAATIMUKSET-listalla: laiteajon suunnitelma kirjoitettiin vaatimuksia lukematta. Käyttäjä: "Kuristimen säätöön on otettu uusi tapa. Tämä ei ole se." | Korjattu: muistutus rekisterin alkuun ja `paketit/C1-JAKSOT.md` vaiheen 4 laiteajoon; laiteajot nimeävät noudattamansa TILAUS-tunnuksen (VAATIMUS-rivi) |

## 20.10.2026 — infra expresso

### Luettava joka purussa — poistettu tai muutettu

**Laiteajon kuristin (muistutus; sääntö TILAUS-M, `KAYTTAJAN-TIEDOT.md` 2c):** kuristinta ei pyydetä "asentoon".
Agentti asettaa `kuri:<n>` (8 barille 25 iskua/s, pienemmille vähemmän) ja kertoo tavoitepaineen; käyttäjä
painaa uuttonappia ja säätää; valmis = `KURI_END reason=switch`, ja agentti tarkistaa paineen KURI-riveiltä (filt,
viimeiset ~2 s); lopuksi `kuri:0`. 20.10.2026 C1-JAKSOT vaihe 4 kysyi "kuristin 8 barin asentoon" (Viat).

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| Bootissa kattilan lukema 13,92 °C ja lämmitin päällä (`heat?` heti adf8580:n flashin jälkeen 20.10.2026, seuraava lukema 97,34): `temps` alkaa nollina, ja seitsemän lukeman keskiarvo laski ensimmäisen lukeman kuuden nollan kanssa (13,97 = 97,8 / 7). Ensimmäinen korjaus c5b22a4 (`c1_on`, ytimen 1 alku) ei riittänyt: sama keskiarvo syntyy jo ytimen 0 `read_temperature`ssa ennen ytimen 1 käynnistystä (c5b22a4:n flashin jälkeen yhä 13,97). | Korjattu isännällä 20.10.2026: `_temps_avg` laskee vain luetut paikat (`ystall_smoke` boot-tarkistukset). Todennettu laitteella 409431f: `heat?` heti flashin jälkeen 98,31 °C, heater=0 (`testit/flash-20261020-zero-c1boot2.log`) |

### Viat — valmis

| Vika | Tila |
|---|---|
| Bootissa kattilan lukema 13,92 °C ja lämmitin päällä (`temps` alkoi nollina; c5b22a4 ei riittänyt, 409431f `_temps_avg`). | todennettu 20.10.2026 (409431f: `heat?` heti flashin jälkeen 98,31 °C, heater=0) |

## 21.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-RELEET-BOOT — releet alas `boot.py`:n alkuun + työkalupolkujen auditointi (EXPRESSO-TURVAKATO:n avoin kohta, käyttäjän vaatimus 7.10.2026): kirjaa vaatimus KAYTTAJAN-TIEDOT.md:hen tunnusrivinä, toteutus ja smoke isännällä; flash käyttäjän kuittauksella — polut: Infra/iot/expresso/pico/boot.py, Infra/iot/expresso/KAYTTAJAN-TIEDOT.md, Infra/iot/expresso/testit/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Thermal stability −10…+10 (TILAUS-Q, käyttäjä 21.10.2026): ylläpitotehon tarve suhteessa pitkän aikavälin vakiotehoon, firmwareen, DIAG_MIN:iin ja äppiin | avoin; laskentatapa hyväksytty 21.10.2026 (AskUserQuestion): IDLE-PI:n integraali = nykyteho, opittu vakioteho (integraali muuttumaton 30 min, tallennetaan Picolle) = 0, skaala = kylmäkäynnistyksen ensimmäisen tasaantumisen teho − vakioteho (= −10), rajaus ±10, muissa tiloissa viimeinen lepoarvo; järjestys: uuton lämmitys ensin (käyttäjä 21.10.2026) | firmware + DIAG_MIN; äppi skoopissa expresso-ios |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| `build_set.py` ei kirjoita rakentamansa manifestia repoon, joten `pico_dev.py verify Infra/iot/expresso/pico/MANIFEST.json` vertaa laitetta vanhentuneeseen manifestiin ja antaa väärän `MISMATCH`-tuloksen. Oire 19.9.2026: `VERIFIED 15/17`, `/functions.py MISMATCH` ja `/main.py MISMATCH`, vaikka laitteen tiivisteet täsmäsivät paikallisiin lähdetiedostoihin (6592c81f40cc, c00e9c500b2a). Korjattiin ensin käsin. | korjattu 52f4fa6 6.10.2026 (build_set_smoke 0 failed; puhelinketjulla todentamatta) (todenna viim. 20.10.2026) |
| `pico_dev.py` yhteysvika: satunnainen `Connection refused` / `bridge client closed` laturisyklin jälkeen (24.–25.9.2026: `cmd bp:8`, `klamp 60` → `KLAMP_FAIL reason=no_end`, `cmd klamp:stop`, esiu1/esiu2 `shot`, `pit:6`); uusinta auttoi, juurisyy selvittämättä (käyttäjä vaihtoi virtalähdettä ja palautti, ajot toimivat). Korjattu: Link-osat (`endswith` → `marker in buf`; hiljainen silta → reopen ja uusinta) aa77c57 6.10.2026, build_set-manifesti 52f4fa6, `restore` tekee `am force-stop`in. **20.10.2026 12.59:** `pico_dev.py safe` → `BrokenPipeError` (pico_dev.py:272 `sendall`) Ctrl-C:n jälkeen; main päättyi releet pois, devsafen vahti resetoi Picon (boot 8cd69aaf). Sama oireluokka; todiste `testit/wifiaika-20261020-safe.log`. **Uusi havainto 20.10.2026:** flashin jälkeinen ensimmäinen `cmd pvent` ei saanut vastausta 90 s:ssa (`testit/gcuutto-20261020-a-pvent.log` tyhjä ensimmäisellä ajolla), toinen yhteys toimi. | kesken aa77c57 6.10.2026 (Link korjattu, manifest 52f4fa6; Connection refused, BrokenPipeError ja flashin jälkeinen `cmd pvent` -vastaamattomuus avoin); odottaa ajoa (todenna viim. 20.10.2026) |
| `restore` ajettiin `timeout 300`:lla (oma raja 300 s + laturisykli): flash onnistui, mutta katkaisu ohitti `ChargerOff.__exit__`:n ja laturi jäi pois. Sääntö: ulompi aikaraja ≥ työkalun oma + 60 s. | korjattu d919331 6.10.2026 (ei `restore`); odottaa ajoa (todenna viim. 20.10.2026) |
| kaksi `pico_dev.py capture` -prosessia päällekkäin (vanha jatkoi TaskStopin jälkeen) → toinen ei saanut dataa, laturi kytkeytyi kesken; TaskStop ei aina lopeta python-lasta. | korjattu d919331; odottaa ajoa: 2 × `cmd` → `PICO_BUSY` (todenna viim. 20.10.2026) |
| Levon lämmitys levoton (käyttäjä 21.10.2026): `Thermostat.heat_cycler` (`pico/classes.py:1443`) laskee 10 askeleen jakson pääsilmukan kierroksina, ei millisekunteina; 4b0a529 (ydin 1 lukee lämpötilan levossa) poisti ytimen 0 2 × 75 ms:n odotuksen, joten kierros ~5 ms ja relejakso ~50–300 ms (ennen ~1,5–3 s), ilman minimi-on/off-aikaa. Lisäksi `get_heating_speed` kutsutaan kahdesti kierroksella ja nollaa lähtötasonsa, ja 250 ms:n lukeman muuttuessa nopeus piikkaa → kynnys pudottaa lämmittimen pois. Minuuttitasolla T 97,5–98,3 °C (ei poikkea eilisestä). | korjattu koodissa 21.10.2026: jakso aikaan sidottu (IDLE 5 s / 500 ms askel, käyttäjä 21.10.2026; muut tilat 2 s / 200 ms), päätös pidetään askeleen ajan (minimi-on/off), nopeus 2 s ikkunasta; `testit/termostaatti_smoke.py` 10/10, smoket 29/29; flashattu af9cdcc 21.10.2026 07.33 (minuuttilukema 97,82–98,07). Jatko TILAUS-P (±0,05 °C 10 s keskiarvoista): IDLE-PI ±2 °C kaistalla (Kp 0,04/°C, Ti 160 s, 50 ms resoluutio) ja DIAG_MIN `n10 d10_min d10_max pi_i`; mallilaitoksella max |d| 0,017–0,031, flashattu 53e16a0 21.10.2026 07.51; laitteella 07.59–08.04 kaikki 10 s keskiarvot ±0,05 (max |d| 0,038), tasaantuminen flashista ~7 min (ylitys +0,45), pi_i 0,045 |
| `PressureSensor.get_pressure()` (`pico/classes.py:1313`) → `ZeroDivisionError`: 16,7 ms:n keruuikkuna kului ennen ensimmäistä näytettä (`cycle_counter` 0), kun jokin (todennäköisesti gc tai ajastimen keskeytys; `free` putosi 3 kt:hen, `lmax_us` ~40–48 ms) pysäytti tehtävän `ticks_us()`:n ja silmukkaehdon välissä. Kaatoi mainin kahdesti: 20.10.2026 17.42.37 ja 21.10.2026 01.57.57 (DIAGNET; DEVSAFE releet 0, vahtikoira rc=3 19 s:ssa). Sama kuvio `classes.py:1343–1357`. Yön `GUARD_TRIP heater reason=norise` 23.57 alkaen ei ole vika: käyttäjä sammuttaa keittimen yöksi, ja Zero pitää Picon käynnissä (käyttäjä 21.10.2026). | korjattu koodissa 21.10.2026 (kumpikin keruu ottaa vähintään yhden näytteen, MANIFEST päivitetty); flashattu 21.10.2026 06.31 (FLASH_OK, VERIFIED 24/24, `testit/flash-20261021-zerodiv.log`; käynnistys f06135fb normaali); isäntätesti ajamatta (käyttäjä: "älä testaa vielä"); todennus: ei `ZeroDivisionError`ia DIAGNETissa |

### Viat — todennuksen määräpäivä 20.10.2026 ohi

| Vika | Tila |
|---|---|
| `pico_dev.py` yhteysvika: satunnainen `Connection refused` / `bridge client closed` laturisyklin jälkeen (24.–25.9.2026: `cmd bp:8`, `klamp 60` → `KLAMP_FAIL reason=no_end`, `cmd klamp:stop`, esiu1/esiu2 `shot`, `pit:6`); uusinta auttoi, juurisyy selvittämättä (käyttäjä vaihtoi virtalähdettä ja palautti, ajot toimivat). Korjattu: Link-osat (`endswith` → `marker in buf`; hiljainen silta → reopen ja uusinta) aa77c57 6.10.2026, build_set-manifesti 52f4fa6, `restore` tekee `am force-stop`in. **20.10.2026 12.59:** `pico_dev.py safe` → `BrokenPipeError` (pico_dev.py:272 `sendall`) Ctrl-C:n jälkeen; main päättyi releet pois, devsafen vahti resetoi Picon (boot 8cd69aaf). Sama oireluokka; todiste `testit/wifiaika-20261020-safe.log`. **Uusi havainto 20.10.2026:** flashin jälkeinen ensimmäinen `cmd pvent` ei saanut vastausta 90 s:ssa (`testit/gcuutto-20261020-a-pvent.log` tyhjä ensimmäisellä ajolla), toinen yhteys toimi. **Toistunut 21.10.2026:** yhteyden avauksen jälkeinen ensimmäinen CMD jäi ilman vastausta (06.4x `heat?`, 08.57 ja 09.52 `tshot`); uusinta toimi. | kesken aa77c57 6.10.2026 (Link korjattu, manifest 52f4fa6; Connection refused, BrokenPipeError ja yhteyden avauksen/flashin jälkeinen ensimmäinen CMD -vastaamattomuus (`cmd pvent` 20.10.2026, `heat?`/`tshot` 21.10.2026) avoin); odottaa ajoa (todenna viim. 20.10.2026) |

### Viat — valmis

| Vika | Tila |
|---|---|
| kytkimen napautus heti uuton jälkeen korvasi kertymän summan → k 67,2→70,5. | korjattu faedc8f 21.10.2026 |
| höyryn jälkeinen kattilan täyttö kerrytti lämmitystä → +8 °C ylitys, k 50,8. | korjattu 76c594e 21.10.2026 |

## 21.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-VAPAA-VIRTAUS — uuton lämmityksen testi vapaalla virtauksella (kahva irti, huuhtelu; käyttäjä 21.10.2026 "Testataan viellä ennen vapaa virtaus"): täytön katon (BH_FILL_MAX) vaikutus, erottelu kattilan täytöstä kaukalon painolla, sekä arm 2 -tasaantuminen aina; testi isännällä, flash ja laitetesti käyttäjän läsnä ollessa — polut: Infra/iot/expresso/pico/functions.py, Infra/iot/expresso/pico/classes.py, Infra/iot/expresso/testit/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Tilakohtaiset lämmönsäädöt erikseen kalibroituna (TILAUS-R, käyttäjä 21.10.2026): uutto, uuton jälkeinen palautus, höyry, kuuma vesi | IDLE tehty (TILAUS-P); uutto koodissa 21.10.2026 (käyttäjä hyväksyi toteutustavan): lämmitys pumpun iskuista paineella painotettuna (`brew_heat_k` ms/isku, `BH_PMAX` 15 bar) vaiheissa 1–4, jäännös maksetaan uuton jälkeen, sitten pito pi_i:llä tasaantumiseen ja kerroin oppii (`BH_LEARN`, `brew_heat.json` Picolla, tmp+rename); mallilaitoksella k oppii ±15 % 8 uutossa ja tasaantunut T 98 ±0,2; vanha uuttosilmukka (bim:0) ennallaan; flashattu 2754d74 21.10.2026 08.43. Laitteella: käyttäjän uutto 08.49 kuoppa 98,1→87,5, ylitys +0,7 (ennen +6 °C, 5–6 min), k 70→68; sokkokori s1 98,28 (k 66,9), s2 97,92 (k 67,2); kahvi 09.11 kuoppa 98,0→85,2, tasaantui 97,87 ilman ylitystä; sarja keskeytettiin kahvin ajaksi (`testit/bh-20261021-*.log`). Kytkimen napautus 09.12 korvasi summan → k 70,5 (vika, korjattu: summat jatkuvat opin loppuun); 750a2ae + faedc8f flashattu 09.26 (k 67,5 kirjoitettu `brew_heat.json`:iin väliaikaisella setillä). s3 09.30 höyrytyksen jälkeen (käyttäjä: höyry kahvin jälkeen, kahva vaihdettu testikahvaan): täyttö 555 iskua (normaali 89–101), kertymä 44 s, tasaantui 105,95 (+8), k 67,5→50,8 → sarja pysäytetty; korjaus: täytön katto BH_FILL_MAX 120 iskua < 1,0 bar, katon ylitys tai höyrystä < 20 min estää opin; vapaa virtaus (isäntä 21.10.2026): katto maksoi 15 s:n huuhtelusta 120/747 iskua (8,3 s vs ~52 s) → kaukalon nousu ≥ `BH_FREE_G` 10 g ohittaa katon (`BH_FREE`), oppi pois (arm 2, tasaantuminen 30b7e38); ei flashattu, testit H7–H8 | flash kuittauksella; kalibrointi: ensin sokkokori pico_dev-testiuutoin, sitten oikeat uutot (käyttäjä 21.10.2026 "Molemmat"); sitten uuton jälkeinen palautus, höyry (käyttäjä 21.10.2026: höyrystys poistaa vettä kattilasta → lämpömassa pienenee; myös höyryn jälkeiset opit), kuuma vesi |
| Vapaa virtaus (käyttäjä 21.10.2026: kahva irti, huuhtelu uuton jälkeen brewhead screenin puhdistukseen) | avoin (testaamatta) | riski: täytön katto (120 iskua < 1 bar) lopettaa kertymän, vaikka kylmää vettä virtaa paljon; erottelu kattilan täytöstä kaukalon painon nousulla (vesi ulos) tai paineella ~0; testi laitteella käyttäjän kanssa. |
| Uuton jälkeinen tasaantuminen myös ilman oppia (arm 2) | korjattu koodissa 21.10.2026 (ei flashattu) | `_post_brew`: maksun jälkeen aina settle-vaihe; arm 2:lla lämmitin pois tavoitteen yllä ja PI saa ohjauksen vasta, kun lämpötila ei enää nouse ja on ≤ tavoite + 0,05 (`BH_SETTLED`, katto `BH_NOLEARN_MAX_MS` 10 min); mallilaitoksella min 97,05 → 97,83 (testit H4–H6). Flashattu 21.10.2026 10.49 (726b8d6, VERIFIED 24/24). Laitteella 3 s huuhtelu kahva irti 10.51: `BH_FREE fill=121 tray_g=21.1`, 186 iskua, sum 12,96 s (katolla ~8,1 s), arm 2; `BH_SETTLED T=98.03` 10.54; sen jälkeen PI: 10 s keskiarvot −0,94…−0,26 (10.55), −0,46…+0,48, +0,28…+0,50 (`testit/vapaa-20261021-a*.log`). Alitus pieneni (ennen −1,3), mutta ei poistunut; mittausta sotkee flashin jälkeinen käynnistys (valmiustila 90 → 98, T 100,4 jo ennen huuhtelua). Toisto tasaantuneesta 98:sta 11.07 (`testit/vapaa-20261021-b*.log`): `BH_FREE fill=121 tray_g=14.2`, 147 iskua, sum 10,3 s, kuoppa −5,3, ylitys +0,9, `BH_SETTLED T=97.85` 11.10, sitten PI −0,86…−0,33 ja +0,41 → alitus toistuu ilman käynnistyksen häiriötä: luovutus laskun aikana kylmällä vastuksella, lämpö tulee viiveellä. Palautus ±0,14:ään 11.14 (noin 4 min huuhtelusta). Mallikokeilu (`testit/bh-lead-sweep-20261021.log`): luovutus 0,3–0,8 °C tavoitteen yllä parantaa alitusta vain 0,1–0,2 °C, eikä malli toista −0,86:ta edes 60 s:n viiveellä → mallilaitos väärä tässä kohdassa, ei muutosta koodiin. Käyttäjä 21.10.2026 valitsi: sovita malli laitteeseen. Sovitus (`testit/bh-kuollut-aika-20261021.log`): laite toistuu vasta lämmittimen kuolleella ajalla ~25 s (+ viive 10 s): kuoppa −4,7, luovutus 137 s (laite 138), alitus −0,85 (laite −0,86). Korjaus `classes.py` `_post_brew` arm 2: pito pi_i:llä alkaa jo tavoitteen yllä, kun lasku saavuttaa tavoitteen `BH_HOLD_LEAD_S` 50 s:ssa (`bh_hold`), ja luovutus PI:lle vasta nähdyn nousun jälkeen (`bh_rise`; hidas kattila luovutti kuopassa → +6,9 °C) tai pidon pysäyttämässä tasanteessa. Mallissa alitus −0,85 → −0,01, 6–8 min heilunta ±0,11 → ±0,03; testit H9 (huuhtelu, kuollut aika) ja H10 (ei luovutusta kuopassa) punaiset HEADilla, vihreät nyt; smoket 29/29. Flashattu 21.10.2026 12.35 (b672e71, FLASH_PLAN 1/24, VERIFIED 24/24, `testit/flash-20261021-bh5.log`), käynnistys DIAG_BOOT 3c09b1e0. Seuraava (käyttäjä 21.10.2026 "Flashaa, testi myöhemmin"): 3 s huuhtelu kahva irti seuraavan uuton jälkeen tasaantuneesta 98:sta; agentti lukee `~/.local/state/expresso-diag/` (odotus: `BH_SETTLED`, alitus ≤ −0,3). |
| Sokkokorisarja (testikahva) | kesken (s1–s4 ajettu, s3 ja s4 höyryn jäljiltä) | jatka, kun täyttö < 120 iskua; sarjaskripti /tmp/bhcal/sarja.sh (ei repossa). |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| ilman oppia (arm 2) uuton jälkeen PI ottaa ohjauksen heti ja integraali valuu ylityksessä → alitus −1,3 °C (09.56–09.59). | korjattu koodissa 21.10.2026, ei flashattu (ks. Avoimet asiat "arm 2") |

## 22.10.2026 — infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Esiuuton 2,5 bar säätö | 26.9.2026 (EXPRESSO-ESIUUTTO-FF, 54e3ac9–c323f6f, laitteella esiuff3; EXPRESSO-ESIUUTTO-ALKU, e91816c, laitteella esialku6; EXPRESSO-ESIUUTTO-AVOIN, 0028dff, laitteella esiavoin1): pidon alun ylitys korjattu ryöminnän osalta ja nousun ylitys ~0,4:ään; ff = min(nousun arvio, edellisen pidon tarve × G-suhde), 1. ajo 0,4 × arvio, tarve ja G settings.txt:ssä (säilyy resetin yli), häntävahvistus ja D (KD 0,05); edellisen tiedolla pidon 2 s ka 2,53 / sd 0,068 (h), 1. ajo 2,59–2,76 (f: 2,49 → 2,92); avoimen kuristimen alun alitus korjattu ja todennettu (ab/ac 2,42/2,46, esiavoin1), ff = tavoite / (rate · tau_edellinen + p5), eu_tau_pre settings.txt:hen, integraali rajattu 0…1, hold ajaa pvent-purun; uuttoasento korjattu ja laitteella todennettu 26.9.2026 (417ad93, ah–am); vuoronvaraus korjattu (late 0, aq–as, EXPRESSO-ESIUUTTO-VUORONVARAUS), rampin loppu korjattu isännällä 651afec (smoke 15), ei flashattu; yksityiskohdat `paketit/VAIHESEURANTA.md` **20.10.2026:** esiuutto c1x (hold3 ca29944): miss 0, late 0 (125 µs), pito 2,532/sd 0,112; vanha samassa tilassa miss 3, late_max 14,4 ms, sd 0,116. | (1) pidon alun ylitys korjattu ryöminnän osalta ja nousun ylitys ~0,4:ään (EXPRESSO-ESIUUTTO-ALKU ajettu); (2) käyttäjän hyväksyntä ennen 8 barin vaiheita on yhä tekemättä (avoin asia 24); (3) 1. ajo ilman tallennettua tietoa ylittää yhä (f: 2,49 → 2,92, ennallaan), avoimella nyt ali (aa 2,19) — tarvittaessa alempi alku; (4) lämmin/kylmä-tila todennettu 26.9.2026 (ad/ae): lämmin → kylmä +0,27 ei läpäise; uuttoasento korjattu ja laitteella todennettu 26.9.2026 (417ad93, ah–am, EXPRESSO-ESIUUTTO-UUTTOASENTO), vuoronvaraus korjattu (aq–as); EXPRESSO-ESIUUTTO-RAMPIN-LOPPU korjattu isännällä (651afec, smoke 15), seuraavaksi flash + hyväksyntäajo. (lisäksi 26.9.2026, EXPRESSO-ESIUUTTO-ALKU): (b) rampin kiinnikurojan ryöppy (y: sp ohitti p5:n 1,1 s:n kohdalla, d 0,42 → 3,87 bar, 1/8 ajosta, malli ei toista) → tiheämpi loki rampin loppuun ja lisää ajoja kuristin lähes kiinni (käyttäjän mukaan epärealistinen tila → matala prioriteetti). |

## 24.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-VAPAA-VIRTAUS — arm 2 -pidon (b672e71, flashattu 12.35) laitetodennus: käyttäjä ajaa 3 s huuhtelun kahva irti seuraavan uuton jälkeen tasaantuneesta 98:sta, agentti lukee DIAGNETin (BH_SETTLED, alitus ≤ −0,3; ennen −0,86); sitten sokkokorisarjan jatko — polut: Infra/iot/expresso/pico/classes.py, Infra/iot/expresso/testit/** — aloitus: /pura infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| iOS-profiili vanhenee 24.10.2026 | avoin; odottaa päivää 24.10.2026 | `expresso-asennus.sh` uusii |

## 26.10.2026 — infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| iOS-profiili vanhenee 24.10.2026 | avoin; odottaa päivää 24.10.2026 **24.10.2026:** asennettu (expresso-asennus.sh exit 0), profiili 29.10.2026 asti. | `expresso-asennus.sh` uusii |
| Lepotila-ajastimet (käynnistys vs. uutto/höyrytys) ja herätysnäkymä | toteutettu, flashattu ja asennettu 24.10.2026; odottaa käyttäjää | käyttäjä testaa lepotilaan menon ja äpin herätyspainikkeen |

## 26.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-VAPAA-VIRTAUS — arm 2 -pidon (b672e71, flashattu 12.35) laitetodennus: käyttäjä ajaa 3 s huuhtelun kahva irti seuraavan uuton jälkeen tasaantuneesta 98:sta, agentti lukee DIAGNETin (BH_SETTLED, alitus ≤ −0,3; ennen −0,86); sitten sokkokorisarjan jatko — polut: Infra/iot/expresso/pico/classes.py, Infra/iot/expresso/testit/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Uuton jälkeinen tasaantuminen myös ilman oppia (arm 2) | korjattu b672e71 21.10.2026 (flashattu 12.35, todentamatta); odottaa käyttäjää **21.10.2026:** ilman kuollutta aikaa malli (1. kertaluvun viive 10–80 s, tarve 7–9 s) antaa alitusta enintään −0,53, joten edellisen session malli ei toistanut laitetta. (todenna viim. 4.11.2026) | `_post_brew`: maksun jälkeen aina settle-vaihe; arm 2:lla lämmitin pois tavoitteen yllä ja PI saa ohjauksen vasta, kun lämpötila ei enää nouse ja on ≤ tavoite + 0,05 (`BH_SETTLED`, katto `BH_NOLEARN_MAX_MS` 10 min); mallilaitoksella min 97,05 → 97,83 (testit H4–H6). Flashattu 21.10.2026 10.49 (726b8d6, VERIFIED 24/24). Laitteella 3 s huuhtelu kahva irti 10.51: `BH_FREE fill=121 tray_g=21.1`, 186 iskua, sum 12,96 s (katolla ~8,1 s), arm 2; `BH_SETTLED T=98.03` 10.54; sen jälkeen PI: 10 s keskiarvot −0,94…−0,26 (10.55), −0,46…+0,48, +0,28…+0,50 (`testit/vapaa-20261021-a*.log`). Alitus pieneni (ennen −1,3), mutta ei poistunut; mittausta sotkee flashin jälkeinen käynnistys (valmiustila 90 → 98, T 100,4 jo ennen huuhtelua). Toisto tasaantuneesta 98:sta 11.07 (`testit/vapaa-20261021-b*.log`): `BH_FREE fill=121 tray_g=14.2`, 147 iskua, sum 10,3 s, kuoppa −5,3, ylitys +0,9, `BH_SETTLED T=97.85` 11.10, sitten PI −0,86…−0,33 ja +0,41 → alitus toistuu ilman käynnistyksen häiriötä: luovutus laskun aikana kylmällä vastuksella, lämpö tulee viiveellä. Palautus ±0,14:ään 11.14 (noin 4 min huuhtelusta). Mallikokeilu (`testit/bh-lead-sweep-20261021.log`): luovutus 0,3–0,8 °C tavoitteen yllä parantaa alitusta vain 0,1–0,2 °C, eikä malli toista −0,86:ta edes 60 s:n viiveellä → mallilaitos väärä tässä kohdassa, ei muutosta koodiin. Käyttäjä 21.10.2026 valitsi: sovita malli laitteeseen. Sovitus (`testit/bh-kuollut-aika-20261021.log`): laite toistuu vasta lämmittimen kuolleella ajalla ~25 s (+ viive 10 s): kuoppa −4,7, luovutus 137 s (laite 138), alitus −0,85 (laite −0,86). Korjaus `classes.py` `_post_brew` arm 2: pito pi_i:llä alkaa jo tavoitteen yllä, kun lasku saavuttaa tavoitteen `BH_HOLD_LEAD_S` 50 s:ssa (`bh_hold`), ja luovutus PI:lle vasta nähdyn nousun jälkeen (`bh_rise`; hidas kattila luovutti kuopassa → +6,9 °C) tai pidon pysäyttämässä tasanteessa. Mallissa alitus −0,85 → −0,01, 6–8 min heilunta ±0,11 → ±0,03; testit H9 (huuhtelu, kuollut aika) ja H10 (ei luovutusta kuopassa) punaiset HEADilla, vihreät nyt; smoket 29/29. Flashattu 21.10.2026 12.35 (b672e71, FLASH_PLAN 1/24, VERIFIED 24/24, `testit/flash-20261021-bh5.log`), käynnistys DIAG_BOOT 3c09b1e0. Seuraava (käyttäjä 21.10.2026 "Flashaa, testi myöhemmin"): 3 s huuhtelu kahva irti seuraavan uuton jälkeen tasaantuneesta 98:sta; agentti lukee `~/.local/state/expresso-diag/` (odotus: `BH_SETTLED`, alitus ≤ −0,3). Käyttäjä kirjoittaa "huuhdeltu" huuhtelun jälkeen; agentti lukee lokit `~/.local/state/expresso-diag/2026-10-*.log`. |

## 26.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-APPI-UI-UUDISTUKSET — toteutetaan äpin päänäkymän ja vaakatilan parannukset (harmaa Wi-Fi 20s timeoutilla, tare-nappi painon alle, vaakatilan karsinnat, pyöreä play/pause freeze-nappi, vaakatilan graafin tilankäyttö, virtauksen flow-piirto) — polut: Infra/iot/expresso/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Äpin yhteyden oletuskuvake (harmaa Wi-Fi, punainen 20 s kuluttua) | avoin (kirjattu 26.10.2026) | Päätilassa oletuksena harmaa Wi-Fi-ikoni yhteyttä etsittäessä; punainen vasta jos yhteys ei löydy 20 s kuluttua |
| Tare-nappi suoraan painon arvon alapuolelle | avoin (kirjattu 26.10.2026) | Äpin UI: Tare-painike sijoitetaan heti painolukeman alle |
| Äpin vaakatilan elementtien karsinta | avoin (kirjattu 26.10.2026) | Vaakatilassa piilotetaan T- ja P-lukuarvot (näkyvät graafissa) sekä yhteyden ja lepotilan symbolit |
| Äpin vaakatilan pyöreä freeze-nappi | avoin (kirjattu 26.10.2026) | Pienempi ja pyöreä nappi, jossa tekstin sijaan play/pause-symbolit |
| Äpin vaakatilan graafin tilankäyttö | avoin (kirjattu 26.10.2026) | Graafi optimoidaan ottamaan tila paremmin haltuun vaakasuunnassa |
| Flow-virtauksen piirto graafiin | avoin (kirjattu 26.10.2026) | Uusi piirto/käyrä flow-lukemalle reaaliaikaisessa graafissa |

## 26.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-LAMPOTILATILAT — toteutetaan keittimen lämpötilatilat (IDLE vasta kun lämpötila asettunut kohdalleen; heilahteluvaiheessa stabilizing; reilusti alle warming up; yli cooling down) — polut: Infra/iot/expresso/pico/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Keittimen lämpötilatilat (IDLE, stabilizing, warming up, cooling down) | avoin (kirjattu 26.10.2026) | IDLE vasta kun lämpötila suurinpiirtein asettunut kohdalleen; heilahteluvaiheessa stabilizing; reilusti alle warming up; yli cooling down |

## 26.10.2026 — infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Push: expresso-repo (9f8d942…39aec74) ja juuren 6531bc77, 68bb0be3 | kesken (expresso-repo pakkauksessa; juuren 6531bc77 ja 68bb0be3 juuren synkalla); odottaa ajoa | — |

## 26.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-ALYKAS-PAINO — kaukaloon tulleen veden määrän tunnistus, tyhjennys sammuksissa, kupin ja ulkoisen vaa'an tunnistus kaukalolla — polut: Infra/iot/expresso/pico/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Älykäs painon ja kaukalon tunnistus | avoin (kirjattu 26.10.2026) | Kaukaloon tulleen veden määrän tunnistus; tyhjennys sammuksissa; kupin ja ulkoisen vaa'an tunnistus kaukalolla |

## 26.10.2026 — infra expresso

### Avoimet asiat — poistettu tai muutettu

| wmax-pysyvyys | toteutettu 26.10.2026 | save_settings atominen (tmp + rename), load_settings ei poista settings.txt:ää virheessä vaan säilyttää tiedoston ja oletukset, toipuu tmp-tiedostosta; todennettu testit/settings_pysyvyys_smoke.py (0 failed) ja shot_test.py (0 failed) |

## 26.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-TURVAKATO-NOLLAUSIKKUNA — releet alas boot.py:n alkuun (Pico-releet 18, 19, 20 nollaksi heti boot.py:n alussa) — polut: Infra/iot/expresso/pico/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Releet alas `boot.py`:n alkuun + työkalupolkujen auditointi (käyttäjän vaatimus 7.10.2026, Päätökset) | avoin | kirjaa vaatimus `KAYTTAJAN-TIEDOT.md`:hen tunnusrivinä; brief; flash käyttäjän kuittauksella |

### Viat — poistettu tai muutettu

| Nollausikkuna: releet 0:aan vasta `main.py:3`; watchdog-nollaus jumissa jättää päällä olleen releen päälle käynnistyksen ajaksi (turvallisuus) | avoin (kirjattu 7.10.2026) |

## 26.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-EU-RIVI-KOKONAISLUVUT — EU-rivi kokonaisluvuin (merkkijonojen ja allokointien keventäminen uuttosilmukassa) — polut: Infra/iot/expresso/pico/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Releet alas `boot.py`:n alkuun + työkalupolkujen auditointi (käyttäjän vaatimus 7.10.2026, Päätökset) | toteutettu 26.10.2026 | boot.py:n alkuun devsafe.relays_off(); vaatimus TILAUS-RELEET-ALAS; brief paketit/RELEET-ALAS-NOLLAUSIKKUNA.brief.md; todennettu testit/nollausikkuna_smoke.py (0 failed); flash käyttäjän kuittauksella |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| Nollausikkuna: releet 0:aan vasta `main.py:3`; watchdog-nollaus jumissa jättää päällä olleen releen päälle käynnistyksen ajaksi (turvallisuus) | korjattu 26.10.2026 (boot.py ajaa devsafe.relays_off() ensimmäisenä ennen muita importteja tai viiveitä; todennettu nollausikkuna_smoke.py (0 failed)) |

### Avoimet asiat — valmis

| Asia | Tila | Seuraava askel |
|---|---|---|
| Nollausikkuna: releet 0:aan vasta `main.py:3` | korjattu 26.10.2026 | boot.py ajaa devsafe.relays_off() ensimmäisenä ennen muita importteja tai viiveitä; todennettu nollausikkuna_smoke.py (0 failed) |

## 27.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-STANDBY-IMPORT-UTIME — siirrä utime-import update_standby-kutsusta moduulitasolle ja varmista valmiustila_smoke — polut: Infra/iot/expresso/pico/** — aloitus: /pura infra expresso — automaattinen: kyllä

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| `update_standby` tekee `import utime` joka kierroksella (kirjattu 5.10.2026) | pieni | tarkista silmukka-ajoitus laitteella; voi siirtää moduulitasolle. |

### Avoimet asiat — valmis

| Asia | Tila | Seuraava askel |
|---|---|---|
| `update_standby` tekee `import utime` joka kierroksella | toteutettu 27.10.2026 | import utime siirretty moduulitasolle pico/classes.py:ssä, valmiustilan silmukka käyttää instanssin tai moduulitason kelloa; todennettu testit/valmiustila_smoke.py (0 failed) |

## 27.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-LAMMITYS-VIRTAUS — uuton lämmitysteho kattilaan vaihtuneesta vedestä (TILAUS-N) — polut: Infra/iot/expresso/pico/** — aloitus: /pura infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-LAMMITYS-VIRTAUS (uusi) | avattu 28.9.2026 käyttäjän tilauksesta (TILAUS-N) | uuton lämmitysteho kattilaan vaihtuneesta vedestä: virtausarvio pumpun iskuista ja paineesta (Ulka EP5 -käyrä, tarkistus himmennyksessä laitteella), vaa'an virtaus vasta tippumisen alettua; korvaa kiinteän EB_HEAT 100/50 ms -pulssituksen (functions.py EB_HEAT_OFF_MS/EB_HEAT_ON_MS) ja vanhan uuttosilmukan saman pulssin; pumpun ohjaus etusijalla |
| EXPRESSO-TURVAKATO | kesken; kohdat 1–5 ja 7 flashattu/laitteella (kohta 4 520ef47, kohta 7 d56d07e 7.10.2026), pcal päätetty, kohta 6 claude siirto | nollausikkuna: releet alas `boot.py`:n alkuun (ks. rivi "Releet alas") |

### Avoimet asiat — valmis

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-LAMMITYS-VIRTAUS | toteutettu 21.10.2026 (2754d74 osana TILAUS-R/N:ää) | uuton lämmitysteho toteutettu pumpun iskuista paineella painotettuna (EP5-käyrä, BH_PMAX 15 bar) vaiheissa 1–4, kiinteä EB_HEAT-pulssitus poistettu; todennettu laitteella 21.10.2026 (bh-20261021-*.log) ja termostaatti_smoke.py (0 failed) |
| EXPRESSO-TURVAKATO | valmis 26.10.2026 | kohdat 1–5 ja 7 flashattu/laitteella, pcal päätetty, nollausikkuna (releet alas boot.py:n alkuun) toteutettu ja todennettu 26.10.2026 (a19f79c, nollausikkuna_smoke.py) |

## 27.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-TILAUS-INVARIANTIT — tilauksen menetelmäkohdat nimetyiksi invarianteiksi (TILAUS-A…TILAUS-R) ja koneellinen tarkistus — polut: Infra/iot/expresso/paketit/** — aloitus: /pura infra expresso

## Luettava joka purussa

`Infra/iot/expresso/KAYTTAJAN-TIEDOT.md` **luetaan kokonaan joka purussa**, samalla tavalla kuin
tämä rekisteri. Se sisältää käyttäjän omat tilaukset, laitetiedot, turvarajat ja menetelmäohjeet
alkuperäisinä lainauksina. Tämä rekisteri kuvaa sen, mikä muuttui; se tiedosto sen, minkä on aina
pidettävä.

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-TILAUS-INVARIANTIT | avattu 19.9.2026, toteuttamatta | `paketit/TILAUS-INVARIANTIT.md`: tilauksen menetelmäkohdat nimetyiksi invarianteiksi (`TILAUS-A`, `TILAUS-B`, …) käyttäjän omana lainauksena, oma luku rekisteriin, ja koneellinen tarkistus joka kaataa menetelmävalinnan, joka ei nimeä noudattamaansa tilauskohtaa |

### Avoimet asiat — valmis

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-TILAUS-INVARIANTIT | toteutettu 27.10.2026 | Tilauksen menetelmäkohdat nimetyiksi invarianteiksi (TILAUS-A…TILAUS-T, TILAUS-RELEET-ALAS, TILAUS-AUTONOMIA) KAYTTAJAN-TIEDOT.md:ssä sanamuotoineen ja viitteineen; PUMPPU-PWM.md:n vaihetaulukko katettu tilaustunnuksin; koneellinen tarkistus todennettu (testit/tilaus_invariantit_smoke.py 0 failed) |

## 27.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: EXPRESSO-C1X-JALKINOUSU — C1X-jälkinousun lisäviiveen sovitus laitedatasta (EU_C1X_LAG_S) — polut: Infra/iot/expresso/pico/**, Infra/iot/expresso/testit/** — aloitus: /pura infra expresso

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Säiliön vesimäärän tunnistus lämpöstabiiliuden saavutusnopeudesta (käyttäjä 21.10.2026, jatkotehtävä; säiliö = keittimen vesisäiliö, josta boileri ottaa uutta vettä) | toteutettu 27.10.2026 (firmware + simulaatio); laitetodennus odottaa laiteajoja eri vesimäärillä | toteutettu pico/water_tank.py (WaterTankTracker): saavutusajan t_reach_s mittaus kylmästä (TS <= -8.0) kynnykseen (TS >= -2.0), lineaarinen malli V_est = a*t_reach + b (0.0...2.0 L), kulutuksen seuranta (consume_water_ml), varoitusraja (<= 0.3 L -> low_water), tilan pysyvyys water_tank.json, DIAG_MIN tk=, telemetria tank_water_l / tank_pct / tank_status ja sarjakomennot tank?, tank:fill, tank:set, tank:cal, tank:consume; todennettu testit/vesimaara_smoke.py M1–M9 (0 failed) |

### Viat — poistettu tai muutettu

| Vika | Tila |
|---|---|
| kylmällä kattilalla tehty huuhtelu viritti arm 2 -tilan, joka jäi settle-vaiheeseen (5,6 % pito) eikä lämmittänyt kattilaa | korjattu 27.10.2026 (EXPRESSO-POST-BREW-COLD-SETTLE: BH_COLD_C 15.0 C, ei post-brew-tilaa kylmällä kattilalla; todennettu termostaatti_smoke.py K1–K4) |

## 27.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: ei mitään, odottaa käyttäjää

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Uutto rikki (käyttäjä 7.10.2026 ~13.50) | avoin (syy auki; epäily Picon spontaanit nollaukset, 13.41.39) | sarjalokin jälkeen testiuutto ja lue loki |
| Todennus oikealla uutolla | avoin; odottaa käyttäjää | Wi-Fi etualalla (live+paino nyt yhdessä paketissa, loki), lukittu puhelin (BLE-tausta, painokehote), PB-uutto: brew_log Wi-Fillä ja `max_loop_ms` vs. 145 ms |
| iOS-profiili vanhenee 24.10.2026 | avoin; odottaa päivää 24.10.2026 **24.10.2026:** asennettu (expresso-asennus.sh exit 0), profiili 29.10.2026 asti. **26.10.2026:** kaksi release-asennusta onnistunut, profiili voimassa 29.10.2026 asti. | `expresso-asennus.sh` uusii |
| c1x oletuksena laitteella (kirjattu 20.10.2026) | todennettu 27.10.2026 | uuttosarja 21.10.2026 (bh-20261021-s1..s4) ajettu c1x:1:llä oletuksena (EU_START c1x=1, miss=0, late=0, starve=0 kaikissa 4 uutossa); todennettu testit/c1x_todennus_smoke.py (0 failed, TILAUS-O toteutuu) |
| Paineentasauksen laitetodennus kylmäkäynnistyksessä | avoin (toteutettu ja flashattu 24.10.2026) | havainnoidaan PEQ-tulosteita seuraavassa alkulämmityksessä. |

### Avoimet asiat — valmis

| Asia | Tila | Seuraava askel |
|---|---|---|
| V-154 Keittimen kylmäkäynnistys ja norise-lukko Zero kiinni | todennettu aamutestissä 7.10.2026 (Zero-linkki, dead=0) | — |
| V-163 pico_dev.py siltaosoite Zeron kautta (192.0.2.10:2217) | todennettu 1.10.2026 | — |

## 30.10.2026 — infra expresso

### (alku) — poistettu tai muutettu

SEURAAVA PAKETTI: ei mitään — odottaa käyttäjää: laitetodennukset (PEQ, höyrytys, lepotila, uutto)

### Avoimet asiat — poistettu tai muutettu

| Asia | Tila | Seuraava askel |
|---|---|---|
| Verkkovirta ei tullut kuormille aamun 1. kytkennässä (käyttäjä 30.10.2026: "keitin ei alkanut lämmetä"; katkaisi verkkovirran, irrotti Zeron, kytki verkkovirran → lämpeni) | todettu 30.10.2026 DIAGNET-lokista (`~/.local/state/expresso-diag/2026-10-30.log`): Pico ei kaatunut yöllä (boot f32ce17b 28.10. 6.15 → 30.10. 8.02, up_s 179204); 8.02.10 huuhtelussa pumppu 71 iskua, paine −0,09 bar koko ajan (muut aamut 0,76–1,23 bar), T 21,2 °C ei noussut 30 s:n lämmitysjaksoissa → kuormat ilman verkkovirtaa; 8.02.38 nollaus rc=1 (virtakatko: Zero irti + verkkovirta pois), sen jälkeen paine 1,23 bar ja lämpeneminen heti; syy (pistoke, jatkojohto, pääkytkin) auki | käyttäjä kertoo, toistuuko; tunnistus mahdollinen firmwareen (pumppu käy, paine ei nouse → NO_MAINS), ei pyydetty |
| `smart_tray.py` tallentaa flashille kesken uuton → uutto voi katketa `reason=starve` | todettu 30.10.2026 10.17 sokkokorin pilottiajossa: `EU_STALL sec=y us=137874 task=scale`, `EU_STARVE starve=2`, EU_END reason=starve 5,3 s:ssa. `SmartTrayTracker.update` kutsuu `save_state()` 30 s:n välein (`smart_tray.py:330`), myös uuton aikana scale_poll_once-tehtävässä; flash-kirjoitus pysäyttää ytimen 1. Ei johdu pisarakorjauksesta (y_max 8–22 ms muissa ajoissa). Koskee myös oikeaa uuttoa | korjaus: ei tallennusta kun `is_idle` on epätosi; flash käyttäjän kuittauksella |

### Viat — valmis

| Vika | Tila |
|---|---|
| Oma virhe 30.10.2026: esitin suunnitelmassa vaa'an siemenyksen poistoa selvittämättä sen tarkoitusta, vaikka käyttäjä oli pyytänyt huolellisen taustaselvityksen, ja väitin sen palauttavan 24.10. asti toimineen suodatuksen (ikkuna oli silloin 8, ei 12). Poisto yksin olisi voinut rikkoa liukumasuojan (P7a). Lisäksi väitin todisteetta 1,1 g:n pudotusta pumpun katkaisussa pelkäksi siemenyksen aiheuttamaksi, ja simulaatio oletti tasaisen painon. Käyttäjä pysäytti: "Mitenkä olet huomioinut että alkuperäinen tarkoitus ei rikkoudu" | korjattu suunnitelmassa ja koodissa (kertasiemenys + katve, P7a–c); käytäntö: koodin poistoa ei esitetä ennen kuin sen tarkoitus on selvitetty ja mitattu |

| Vika | Tila |
|---|---|
| Oma virhe 30.10.2026: 10 ajon sokkosarja suunniteltiin ja 5 ajoa ajettiin ilman TILAUS-H-purkua (`pvent`), vaikka vaatimus oli purun VAATIMUKSET-listalla; käyttäjä huomautti. Lisäksi väitin pisarakynnyksen rajaksi 0,25 g, vaikka laitteella se on 0,50 g | korjattu 30.10.2026 (sarja pysäytetty, ptrig palautettu, kynnys korjattu viestissä ja riviltä Pisaratunnistus laukesi ilman tippaa); jatko EXPRESSO-SOKKO-NOLLA |
