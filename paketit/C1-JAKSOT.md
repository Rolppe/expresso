# EXPRESSO-C1-JAKSOT — uuton jaksot ja painemittaus ytimelle 1 (suunnitelma 20.10.2026)

VAATIMUS: TILAUS-O
VAATIMUS: TILAUS-A
VAATIMUS: TILAUS-B
VAATIMUS: TILAUS-I
VAATIMUS: TILAUS-J
VAATIMUS: TILAUS-L
VAATIMUS: TILAUS-AUTONOMIA

TILAUS-O on tämän paketin syy. A, B, I, J ja L säilyvät: verkkokello ja vaihe luetaan paineesta, korjaus tehdään
tunnetulla viiveellä, ja 10 ms:n tauko vaikuttaa 20 ms. Ydin 1 vain toteuttaa ajoitukset, eikä mittausperiaate
muutu. Vaiheet 1–2 ovat ajettavissa ilman käyttäjää (AUTONOMIA). Vaiheet 3–4 pumppaavat, joten ne ilmoitetaan
etukäteen ja kuitataan (läsnäolo ja vesi).
Lähtö: `paketit/GC-UUTTO.md`. Käyttäjä 20.10.2026 valitsi: "Jaksot ytimelle 1", "Ydin 1 välienä" (lämpötila) ja
"Pysäytä uutto virheeseen" (tyhjä päätösjono).

## Miksi

Nykyään ydin 0 ajaa uuton silmukan Pythonissa (`functions.py` `_eu_loop`): 1 kHz:n näyte, verkkokello, säätö,
releen käännöt, loki ja hallittu `gc.collect()` samassa silmukassa. Mitattu 20.10.2026:
- Testiuutoissa jäi pois 26–116 jaksoa per uutto (`miss`), ja silmukka seisoi 60–200 ms.
- Ytimen 1 nukkuva lämpötilasilmukka (`sleep_ms`) hidastaa ytimen 0 keruun 18 ms:stä 98–600 ms:iin, ja lukevana se
  venyttää ytimen 0 vuoroja jopa 65 ms:iin.
- Kun ydin 1 ajaa muisti lukittuna 1 kHz:n kokonaislukusilmukkaa, se ei menettänyt yhtään näytettä 120 000
  näytteessä ytimen 0 keräessä (suurin väli 1,07 ms). Silloin ytimen 0 keruu kestää aina 17–21 ms.

## Työnjako

**Ydin 1 (toteuttaja; ei nuku, ei varaa muistia, vain kokonaislukuja, `micropython.heap_lock()`):**
1. Näyte 1 kHz:llä: `read_u16()` + `ticks_us` jaettuun näytejonoon (`array('i')`, rengas). Jaksokeskiarvon
   summa ja määrä jaksoittain (`cyc_s`, `cyc_n` kokonaislukuina raakalukemasta).
2. Releen käännöt päätösjonosta: tapahtuma = (aika `ticks_us`, pumppu 0/1). Ydin 1 kääntää raakapinnin
   täsmälleen tapahtuman ajassa ja kirjaa toteutuneen ajan ja myöhästymän. 10 ms tauko = kaksi tapahtumaa (pois, päälle).
3. Turva: ennen jokaista päällekääntöä ydin 1 lukee jaetun sallintalipun (`pump_ok`), jonka ytimen 0 vahti asettaa.
   Vahti kääntää pinnin pois myös itse kuten nyt. Ydin 1 ei kutsu `GuardedRelay`:tä, koska se laskee
   liukuluvuilla ja varaisi muistia.
4. Lämpötila välienä: MAX31865:n kolme vaihetta (`rtd_start`, 10 ms myöhemmin `rtd_convert`, 65 ms myöhemmin
   `rtd_result`) näytteiden välissä ilman odotusta. Ytimen 1 nykyinen silmukka ajaa samat kutsut jo muisti lukittuna
   (`classes.py:1698–1702`), joten ne eivät varaa. Kunkin vaiheen kesto mitataan ensin (< 0,5 ms vaaditaan).
5. Levossa ydin 1 pyörii nukkumatta (ei `sleep_ms`): se poistaa levon 0,1–0,6 s:n keruut.
6. Tyhjä päätösjono kesken uuton → rele pois, tila `C1_STARVED`, uutto päättyy virheeseen ja lokiin `EU_STARVE`.

**Ydin 0 (suunnittelija; Python, liukuluvut sallittu):**
- lukee näytejonon erissä: paine baareina, verkkokellon I/Q (`Verkkokello.iq_add`) ja jaksokeskiarvot
- säätö (delta-sigma, ff, PI/D) kuten nyt ja päätösten kirjoitus jonoon etukäteen
- loki, DIAGNET, vaaka, Wi-Fi ja keruu: mikään niistä ei enää osu jakson ajoitukseen.

## Avoimet kysymykset (mitataan, ei oleteta)

| # | Kysymys | Miten |
|---|---|---|
| K1 | Montako jaksoa etukäteen? Nyt päätös on yhden jakson edellä (`pump_next`). Ytimen 0 pahin katko on ~21 ms keruu + vuoro, joten 2 jakson (40 ms) jono riittänee. Lisäviive säätöön 0–20 ms. | `esiuutto_smoke`/`shot_test`-malli 1 vs. 2 jakson viiveellä: pidon `hold_sd`, ylitys; laitteella `miss`/`late` |
| K2 | Jakavatko ytimet lukon, joka venyttää ytimen 1 silmukkaa? Jitter-kokeessa ei näkynyt, mutta ytimen 0 Wi-Fi-, USB- ja asyncio-kuorma oli kevyt. | jitter-koe uuton kuormalla (DIAGNET uuttotahti, Wi-Fi-tilaaja, vaaka) |
| K3 | MAX31865-vaiheiden kesto ytimellä 1 | mittaus jitter-kokeen tapaan |
| K4 | Ytimen 1 käännön ja vahdin ristiriita (vahti kääntää pois, ydin 1 päälle samassa hetkessä) | lukittu järjestys: ydin 1 lukee `pump_ok`:n juuri ennen pinniä; isäntätesti rinnakkaisella säikeellä |

### K1 vastattu 20.10.2026 (malli, `testit/k1_viive.py`, tulos `testit/k1-20261020-malli.txt`)

Testissä aidon `run_shot`in pumppupinni viivästettiin N jaksoa: tasot 25b ja 26b, 20 kohinasiementä.
- **+1 jakso (jono 2 jaksoa = 40 ms) on hyväksyttävä:** pidon keskiarvo pysyy ennallaan. hold_sd kasvaa enintään
  0,014 bar, mikä on noin yhden siemenhajonnan verran. EB-ylitys kasvaa 0,05–0,12 bar ja EB max enintään 0,04 bar, molemmat siemenhajonnan sisällä.
- **+2 jaksoa on rajalla:** EB hold_sd 0,265 (25b) vs. lag 0:n max 0,265, ja pahin EB max 9,11 bar.
- Laitteen `miss`/`late`-käyttäytymistä ja K2:n lukkoa ei mallinnettu.
Valinta: jono 2 jaksoa (40 ms). Kuivakoe ajaa myös 1 jakson (bitti 256) vertailuksi.

## Vaiheet (jokainen oma committinsa, isäntätestit ja laiteajo)

1. **Ydin 1:n toteuttaja ilman relettä:** näytejono ja päätösjonon "kuiva" toteutus (pinni ei käänny, käännösajat
   kirjataan), ydin 0 lukee jonoa uuton kuormalla. Mittari: 0 puuttuvaa näytettä, käännön myöhästymä < 0,3 ms
   (`EU_LATE_MAX_US`). Ei pumppua.
2. **Lämpötila ytimelle 1 väleihin** (K3), levon pyöriminen nukkumatta, ja HB:n `lmax_us`/`l100` todentaa levon viiveiden poistumisen.
3. **Esiuutto (2,5 bar) ytimen 1 jaksoilla:** pumppu, läsnäolo- ja vesikuittaus. Mittari: `miss` = 0, `late` = 0,
   jokaisessa jaksossa `cyc_n` > 0, pidon `hold_sd` ≤ nykyinen.
4. **Uutto (8 bar) ja vanhan silmukan poisto.** Vanha `_eu_loop` säilyy valittavana (`euv:`-tapaan), kunnes vaihe 4 on hyväksytty.

Ei tässä: säätimen viritys (K1:n viive voi vaatia sitä, mutta se on oma pakettinsa), 1 kHz:n kokonaislukumuunnos
ytimellä 0 (GC-UUTTO vaihtoehto 2) tarpeeton, koska ydin 0 ei enää ole ajoituksessa.

## Vaihe 1: kuivakoe laitteella 20.10.2026 (ystall bitti 128; ydin 0 uuton kuormalla: keruu 300 ms + DIAGNET uuttotahti)

| koe | jono | näytteet / suurin väli / ylivuoto | tapahtumat / myöhässä > 0,3 ms (max) / tyhjä jono |
|---|---|---|---|
| 9455203 (täyttö kerran kierroksessa) | 40 ms | 30 001 / 1,12–1,15 ms / 0 | 2 249 / 1 (0,8 ja 4,1 ms) / 0 |
| 9455203 | 20 ms | 30 001 / 1,13–1,16 ms / 0 | 2 249 / 36–40 (9,7 ms) / 4–10 |
| 44721f2 (täyttö keruun molemmin puolin) | 40 ms | 30 000 / 1,12–1,18 ms / 0 (3 ajoa) | 2 249 / 1, 0, 1 (max 0,99 ms) / 0 |
| 44721f2 | 20 ms | 30 001 / 1,12 ms / 0 | 2 249 / 22 (4,3 ms) / 0 |

- Ydin 1 ei menettänyt näytteitä: 150 000 näytettä, suurin väli 1,18 ms, ei ylivuotoja. Ytimen 0 muunnos baareiksi
  pysyi mukana (`bar_n` ≈ `n`).
- 40 ms:n jono ja täyttö keruun molemmin puolin: tyhjää jonoa ei kertaakaan. Yksi tapahtuma per ajo myöhästyi
  0,75–1,0 ms, mikä ylittää `EU_LATE_MAX_US` 300 µs. Syy auki: ydin 1 viivästyi enintään 0,18 ms, joten tapahtuma
  kirjoitettiin jonoon todennäköisesti myöhässä. Seuraavaksi kirjataan myöhästyneen tapahtuman kirjoitusaika.
- 20 ms:n jono ei riitä.

### Myöhästymän syy (3fa436a, boot 033c1656; 4 × 30 s, 40 ms:n jono)

| ajo | näytteet | myöhässä / max | pahin tapahtuma `lidx` / kirjoitus suhteessa aikaan |
|---|---|---|---|
| 1 | 30 002 | 1 / 0,78 ms | 0 / +0,77 ms (myöhässä) |
| 2 | 29 999 | 0 / 0,12 ms | 1058 / −48,9 ms (ajoissa) |
| 3 | 30 002 | 1 / 1,14 ms | 0 / +1,14 ms |
| 4 | 30 000 | 0 / 0,10 ms | 1664 / −48,8 ms |

- Ainoa myöhästynyt oli jonon ensimmäinen tapahtuma. Testi ajoitti sen 20 ms:n päähän ja kirjoitti ytimen 0
  ensimmäisen vuoron jälkeen. Jatkuvassa tilassa myöhästymiä ja tyhjiä jonoja oli 0, ja pahin myöhästymä oli 0,10–0,12 ms.
- **Vaatimus toteutukselle:** jono täytetään 40 ms:n verran ennen kuin ydin 1 aseistetaan (ARMED) ja ennen ensimmäistä
  jaksoa. Uutto alkaa vasta, kun jono on täynnä.
- **Vaihe 1 hyväksyttävissä:** 270 000 näytettä 9 ajossa (44721f2 + 3fa436a) ilman ylivuotoja, suurin väli 1,18 ms.
  40 ms:n jono ei tyhjentynyt ytimen 0 keruiden aikana.

## Seuraava: vaihe 2

Lämpötila ytimelle 1 väleihin (K3: vaiheiden kesto), lepo ilman `sleep_ms`ia ja HB:n `lmax_us`/`l100`-todennus.
Vasta sitten vaihe 3 (esiuutto pumpulla, läsnäolo- ja vesikuittaus).

## Vaihe 2 laitteella 20.10.2026 (93d8d2b, boot 635d3b97 17.51 ja 11bedddf 18.11)

Keskeytetty flash 17.50 ehti kirjoittaa molemmat tiedostot: `pico_dev.py verify` → `VERIFIED 24/24`
(`testit/verify-20261020-c1lepo.log`), joten uutta flashia ei tarvittu.

| mittaus | tulos | tavoite |
|---|---|---|
| `ystall:30:643` (128 + 512 + keruu + DIAGNET), `testit/c1lepo-20261020-ys643.log` | C1T `t_n=120/120`, `bad=0`, `gap_ms=252`, 97,42 °C; **`ts_us=2011 tc_us=1153 tr_us=1129`**; C1X `gmax_us=2233`, `late=13`, `lmax_us=753` | vaiheet < 0,5 ms; väli ≤ 1,2 ms; late 0 |
| `ystall:30:2` (keruu levossa), `testit/c1lepo-20261020-ys2.log` | keruu 93 kpl, mediaani 20,2 ms, max 20,6 ms (ennen 90 ms / 600 ms) | 17–21 ms ✓ |
| DIAG_HB levossa (keräin `~/.local/state/expresso-diag/2026-10-20.log`) | `lmax_us` 174–295 ms (ennen 330–945 ms), **`l100` ≈ 328/min ennallaan** | levon viiveet pois |

- **K3 ei täyty: SPI on 50 kHz** (`pico/lib/adafruit_max31865.py:75`): tavu kestää 160 µs. `rtd_start` tekee neljä
  siirtoa (8 tavua, ~2 ms), `rtd_convert` kaksi ja `rtd_result` kolme tavua. Vaihe venyttää näytevälin 2,2 ms:iin ja
  myöhästää kääntöjä. Korjaus: konfiguraatio välimuistiin (ei luku–kirjoitus-kierroksia) ja vaiheet yhden tavun
  osiin, CS alhaalla osien välissä (~0,2 ms/osa).
- **Levon viiveiden syy ei ollut ydin 1 vaan ytimen 0 lämpötilaluku:** pääsilmukka lukee joka kierroksella kahdesti
  (`main.py:246` `get_boiler_temperature`, `:269` `thermostat.run`), ja `read_rtd` nukkuu `time.sleep` 10 + 65 ms.
  Kaksi peräkkäistä lukua ≈ 160 ms = mitattu `lmax_us`. Ystall-ajossa (`dev_run`, termostaatti ei aja) viivettä ei
  ollut (`y_max_us` 7–11 ms). Korjaus: ydin 1 lukee lämpötilan myös levossa (`WANT 1` bootista), ydin 0 ei koske SPI:hin.

### Korjaukset laitteella (8c7357b K3-osat, 4b0a529 lepoluku ytimellä 1; flash 18.35 `testit/flash-20261020-zero-c1lepo2.log`, boot bc53c270 `TEMP_C1 rest`)

| mittaus | ennen (93d8d2b) | jälkeen (4b0a529) |
|---|---|---|
| C1T `ts/tc/tr_us` (`testit/c1lepo2-20261020-ys643.log`) | 2011 / 1153 / 1129 | **469 / 479 / 858** |
| C1X `gmax_us` / `late` (max) | 2233 / 13 (753 µs) | **1151 / 1** (314 µs, `lidx=0`: jonon ensimmäinen, tunnettu käynnistysilmiö) |
| lukemat / bad / väli | 120 / 0 / 252 ms | 121 / 0 / 253 ms, 98,19 °C |
| keruu levossa `ystall:30:2` | 20,2 ms mediaani | max 22,1 ms |
| DIAG_HB levossa 10 min (`testit/c1lepo2-20261020-hb.log`) | `lmax_us` 174–295 ms, `l100` ≈ 328/min | **`lmax_us` 39–47 ms, `l100` 0** (bootin ikkuna 420 ms) |
| termostaatti (DIAG_MIN) | — | T 97,7–98,2 °C, tavoite 98, lämmitin jaksottaa |

- Vaihe 2 täyttää tavoitteensa ajoituksen osalta: näyteväli on vaiheen 1 tasolla (1,12–1,18 ms), kääntöjä ei myöhästy
  jatkuvassa tilassa, ja levon katkot poistuivat.
- **K3:n `tr` 0,86 ms ylittää 0,5 ms:n rajan**, koska `tr` sisältää osan 6 lisäksi `_c1_put`in (7 lukeman keskiarvo ja
  taulukkomuunnos). Haittaa ei näy (`gmax_us` 1151), mutta marginaali on pieni: osa 6 alkaa, kun tilaa on > 0,7 ms.
  Korjausehdotus: `_c1_put` omaksi osakseen 7.
- Seuraava: vaihe 3 (esiuutto 2,5 bar ytimen 1 jaksoilla), joka vaatii läsnäolo- ja vesikuittauksen.

### Osa 7 (bdc1ac9, flash 18.59 `testit/flash-20261020-zero-tr7.log`, boot bf882a27)

| ajo | `ts/tc/tr_us` | `gmax_us` | late (max, lidx, lwr) | n |
|---|---|---|---|---|
| 1 `testit/tr7-20261020-ys643.log` | 518 / 477 / 515 | 1209 | 1 (932 µs, 0, −5329) | 29 980 |
| 2 `testit/tr7-20261020-ys643-2.log` | 454 / 443 / 487 | 1148 | 0 (190 µs) | 30 001 |

- K3 täyttyy ajossa 2 (kaikki < 0,5 ms); ajossa 1 osat 0,48–0,52 ms. Yhden tavun osa kestää ~0,45–0,5 ms, josta
  siirto on 0,16 ms ja loput MicroPython-kutsuja, joten pienemmäksi ei päästä nopeuttamatta SPI:tä.
- **Vaatimus vaiheelle 3:** ajossa 1 ensimmäinen tapahtuma myöhästyi 0,93 ms, vaikka se kirjoitettiin 5,3 ms
  etukäteen, ja näytteitä puuttui 20. Levossa ydin 1 lukee lämpötilaa (`WANT 1`) ja katsoo `WANT`ia vasta lukujen
  välissä, joten `c1_on(3)` alkaa vasta käynnissä olevan luvun jälkeen (≤ 85 ms). Uutto saa siis täyttää jonon ja
  aseistaa (ARMED) vasta, kun suorittaja käy (`CX_N` > 0).

## Vaihe 3 — toteutussuunnitelma (20.10.2026, kartoitus `pre_infusion_phased` functions.py:255–830)

Silmukka on `pre_infusion_phased`in `while True` (functions.py:328–729), ei `_eu_loop`. Vanha polku jää oletukseksi.

**Valitsin:** `c1x:0|1` → `brew_data.eu_c1x` (vain RAM, oletus 0, kuten `euv:` commands.py:375). Vaiheessa 3 vain
`brew=False` (pelkkä esiuutto); `brew=True` ajaa vanhan polun ja kirjaa `EU_C1X off reason=brew`.

**Ydin 0 (sama silmukka, kaksi primitiiviä vaihtuu, kun `c1x`):**
1. *Näytteet renkaasta:* `read_u16` (functions.py:677–683) korvataan renkaan lukemisella: jokainen (t, raw) → bar,
   `cyc_s/cyc_n`, `clock.iq_add(t, bar)` näytteen omalla ajalla. Kohta k käsitellään, kun renkaassa on näyte, jonka
   t ≥ `slot`. Näytteet ennen sitä kuuluvat jaksoon k, ja siitä alkaen seuraavaan. `t` on nimellinen kohta, ei ytimen 0 hetki.
2. *Releen sijaan jono:* kohdan k päätös `pump_next` kirjoitetaan kohtaan k+2 (40 ms jono; K1: +1 jakso hyväksytty),
   ja 10 ms tauko kahtena tapahtumana (pois kohdassa, päälle +`EU_GAP_US`). Laskurit (`strokes`, `removed`, `sk10/20`)
   luetaan jonon FIFO:sta, joka kertoo, mitä kohdassa k toteutui. `skip_late` ja `miss` tulevat ytimen 1
   `late`/`starve`-kentistä. Jaksokeskiarvo, delta-sigma, ff, PI/D, katkaisu ja oppiminen pysyvät ennallaan.
3. *Aloitus:* `c1_on(3)` (cx: `DRY=0`, `cx_pin = RELAY_PUMP.pin`, `c1_adc = sensor`), odotetaan `CX_N > 0` (≤ 150 ms,
   muuten `EU_C1X fail` ja vanha polku), sitten jono täyteen 40 ms ja `ARMED`. Lopetus: `c1_off`, minkä jälkeen pinni on 0.
4. *Keruu:* `EU_GC_MS`-keruu sallitaan aina, kun jonon etumatka on ≥ 35 ms (keruu ~21 ms); releen tilaehdot jäävät pois.

**Turva (K4, Työnjako 3):**
- Uusi kenttä `CX_OK`, jonka ydin 0 asettaa 1:ksi aseistaessaan vain, jos `RELAY_PUMP`:n vahti sallii pumpun
  (`allow('pump')`, joka samalla käynnistää `pump_run_start`in: 180 s:n raja pätee).
- Ydin 0 kutsuu `allow('pump')`:ia joka jakso, jossa jonoon menee päälle-tapahtuma. Ilman sitä `pump_last_want`
  vanhenee, ja ajorajan laskenta katkeaisi.
- Vahdin `_trip`/`poll` nollaa ensin `CX_OK`:n ja vasta sitten pinnin (`relay.c1_ok`-viite, jonka ydin 0 asettaa
  aseistaessaan).
- Ydin 1 lukee `CX_OK`:n juuri ennen jokaista `pin.value(1)`:tä. Jos se on 0, pinni pysyy 0:ssa.
- Jäännöskilpa (ydin 1 luki 1, vahti nollasi ja käänsi pinnin, ydin 1 kääntää 1) kestää enintään vahdin seuraavaan
  pollaukseen (100 ms), joka kääntää taas pois. Tämä testataan rinnakkaisella säikeellä.
- *Nälkä:* `ARMED` ja ei tapahtumaa > 25 ms → ydin 1 kääntää pinnin 0:aan ja asettaa `CX_STARVE`. Ydin 0 lopettaa
  esiuuton syyllä `starve` ja kirjaa `EU_STARVE` (käyttäjän valinta "Pysäytä uutto virheeseen").
- `turva_toimilaite_smoke` A1/A2 pysyvät: `cx_pin` on `GuardedRelay`n oma `pin`, eikä uutta `Pin(`-kutsua tule.

**Testit:**
- `esiuutto_smoke`: virtuaaliajassa toimiva ydin 1 -malli, joka toteuttaa jonon tapahtumat Plantin pinniin niiden
  ajassa ja kirjoittaa näytteet renkaaseen 1 kHz:llä. Ajetaan c1x-versiot nykyisistä pito- ja taukotapauksista.
- Vaatimukset: `miss` = 0, `late` = 0, `cyc_n` > 0 joka jaksossa, `hold_sd` ≤ vanha polku samalla siemenellä + 1
  siemenhajonta (K1).
- Nälkä → `starve` ja pinni 0. Vahdin laukaisu → pinni 0 viimeistään seuraavassa pollauksessa.
- `ystall_smoke`: `CX_OK`- ja nälkälogiikka oikealla `_c1_exec`illä säikeessä.

**Laiteajo:** `c1x:1`, sitten `pico_dev.py hold` (pelkkä esiuutto); vaatii läsnäolo- ja vesikuittauksen.

## Vaihe 3 isännällä 20.10.2026 (toteutettu suunnitelman mukaan, ei flashattu)

VAATIMUS: TILAUS-O, TILAUS-L, TILAUS-I, TILAUS-AUTONOMIA

**Toteutus** (`pico/functions.py` `pre_infusion_phased`, `EU_C1X_*`; `pico/classes.py` `_c1_exec`; `pico/relayguard.py`):
- `c1x:0|1` (`commands.py`, RAM, oletus 0). `brew=True` → `EU_C1X off reason=brew`. Aloitus `_c1x_start`: anturilla ei
  toteuttajaa → `EU_C1X fail reason=noc1`, `c1_on(3)` ei käy → `reason=want`, ei näytettä 150 ms:ssa → `reason=start`;
  vahti kieltää → `reason=guard`. Kaikissa vanha polku. `EU_START` kertoo `c1x=0|1`.
- Ydin 0: kohta k käsitellään ensimmäisen kohdan jälkeisen rengasnäytteen kohdalla (`t` = nimellinen kohta), näytteet
  omilla ajoillaan (`iq_add/iq_close(tq)`). Kohdan k päätös kirjoitetaan kohtaan k+2; kohdan k+1 10 ms tauko päätetään
  samalla (silloin k+2:n päätös tiedetään). Kirjanpito jonon FIFO:sta (`cq`: päällä, päällä ennen kohtaa, vaihe ok).
  Jokaisella kohdalla on tapahtuma; yli 22 ms:n väliin täyte samalla tilalla (`EU_C1X_FILL_US`).
- Etumatka = kohdan k+2 tauon paluu − nyt. Keruu, kun etumatka ≥ 35 ms; vuoro, kun rengas on luettu ja etumatka ≥ 30 ms.
  Releen tilaehdot eivät rajaa kumpaakaan.
- Lopetukset: `starve` (`EU_STARVE`-rivi, `miss` = nälkämäärä), `guard` (CX_OK 0), `c1dead` (ei näytettä 50 ms),
  `c1full` (jono täynnä). Lopuksi `EU_C1X n gmax_us ovf nev written lmax_us late starve lidx lwr_us lag_max_us cyc_min fill`.
- Turva (K4): `cx_ok` on oma yhden sanan taulukko (vahti ei tarvitse CX_*-indeksejä). Ydin 0 asettaa sen 1:ksi vain,
  jos `allow('pump')` sallii, ja kutsuu `allow`ia joka kohdassa, jonka jonoon menee päälle-tapahtuma (180 s:n ajoraja).
  `GuardedRelay.c1_ok` (asetetaan `guard.relays['pump']`in kautta: A5 kieltää `RELAY_PUMP.<x> =` -sidonnan): `_trip`
  nollaa sen ennen pinniä, `poll` laukaisee myös pinnin ollessa tauolla 0, ja `guarderror` nollaa sen. Ydin 1 lukee
  sen juuri ennen jokaista päällekytkentää; nälkä kääntää pinnin 0:aan ja lukitsee päällekytkennät. Toteuttajan
  lopussa pinni 0 ennen kesken jääneen lämpötilaluvun loppua (≤ 85 ms), ja `_c1_main`in virhepolku kääntää pinnin pois.
- Poikkeama suunnitelmasta: `CX_OK` on `cx_ok[0]`, ei `cx`-kenttä; `ystall` (bitti 128) asettaa sen 1:ksi, jotta kuivan
  ajon `PIN` kirjaa saman kuin ennen.

**Isäntätestit** (28 smokea, exit 0; lähtötaso HEAD:lla samat 28 vihreinä):
- `esiuutto_smoke` tapaus 23 (`C1Exec`: ydin 1 virtuaaliajassa, kuroo kiinni myös keruun ja vuoron varauksen ajan):

| ajo | tulos |
|---|---|
| perusajo (phi 7300) | done; late 0, miss 0, nälkä 0, ovf 0; cyc_min 13; iskut 107 = malli 107; sk10 94 / sk20 1; tauon alku 4,7 ms passiivisesta (puolijakso 10 ms); over 0,03, hold 2,486 / sd 0,063 (vanha 0,071) |
| pysähdykset 0,5 % (tapaus 3) | done, late 0, 92/92 tehtyä 10 ms taukoa passiivisella puolijaksolla |
| keruu + varaukset 13–28 ms 5/s + ikkunan sulku 10,5 ms, 4 siementä | kaikki done, late = miss = nälkä = 0 |
| hold_sd, sovitettu kohinainen malli, 8 siementä | c1x 0,180, vanha 0,184 ± 0,007 |
| nälkä: ydin 0 seisoo 90 ms nousussa | reason=starve, pumppu pois 60,5 ms pysähdyksestä (ydin 1) |
| vahti: ajoraja (2,5 s) ja `poll` (devsafe) | GUARD_TRIP, reason=guard, ei päällekytkentää laukaisun jälkeen |
| ydin 1 lakkaa 1,5 s | reason=c1dead, pumppu pois |
| bim:1 / ilman toteuttajaa | `EU_C1X off reason=brew` / `EU_C1X fail reason=noc1`, vanha polku |

- `ystall_smoke`: oikea `_c1_exec` säikeessä oikealla pinnillä: CX_OK 0 pitää pinnin 0:ssa, nälkä aikaisintaan
  CX_STARVE_US:n jälkeen ja lukitsee, toteuttajan loppu ja ytimen 1 virhe (ADC) jättävät pinnin 0:aan; 8/8 ajoa vihreinä.
- Isännän säie seisoo GIL:n takia välillä 10–30 ms, joten testi pollaa eikä nuku kiinteitä aikoja.

**Laiteajo (seuraava, vaatii luvan, läsnäolon ja veden):** flash Zerolla (`classes.py`, `commands.py`, `functions.py`,
`relayguard.py`, `ystall.py`; keitin lämmin ja joutilas), sitten `cmd 'bim:0'`, `cmd 'c1x:1'`, `pico_dev.py hold 3`
(pvent ensin), lopuksi `cmd 'c1x:0'`, `cmd 'bim:1'`. bim:1 on oletus, ja sillä c1x ei käynnisty (vaihe 3 = vain esiuutto).
Hyväksyntä: `EU_C1X` late 0, starve 0, ovf 0, cyc_min > 0; `EU_END` miss 0; hold_sd vanhan polun tasolla.

## Vaihe 3 laitteella 20.10.2026 (eef7c95 ja ca29944, flash Zerolla käyttäjän luvalla)

Flash eef7c95: `FLASH_PLAN 5/24`, `VERIFIED 24/24` (`testit/flash-20261020-zero-c1x.log`); ca29944: 1/24
(`testit/flash-20261020-zero-c1x2.log`). Ajot `bim:0` + `c1x:1|0`, `pico_dev.py hold 3`; lopuksi `c1x:0`, `bim:1`.

| ajo | polku | miss | late (pahin) | starve / ovf | näytteet, gmax, cyc_min | ytimen 0 viive | pito ka / sd | over |
|---|---|---|---|---|---|---|---|---|
| hold2 (eef7c95, 1. ajo flashin jälkeen, täyttö 9,9 s) | c1x | 0 | 2 (1,80 ms, lidx 0) | 0 / 0 | 13 520, 1166 µs, 12 | 18,9 ms | 2,399 / 0,197 | −0,02 |
| hold3 (ca29944) | c1x | 0 | 0 (125 µs) | 0 / 0 | 4 800, 1125 µs, 12 | 14,1 ms | 2,532 / 0,112 | 0,28 |
| hold4-vanha (ca29944) | vanha | **3** | 0 (late_max 14,4 ms) | — | — | — | 2,502 / 0,116 | 0,21 |

- TILAUS-O täyttyy c1x-polulla: jaksoja ei jäänyt pois (miss 0) eikä yksikään kääntö myöhästynyt yli 300 µs
  (hold3). Vanha polku samassa tilassa: miss 3, kääntö jopa 14,4 ms myöhässä.
- hold2:n pahin myöhästyminen oli jonon ensimmäinen päällekytkentä, joka kirjoitettiin t0:aan 1,8 ms myöhässä.
  ca29944 kirjoittaa sen kirjoitushetkelle, ja hold3:ssa late on 0.
- hold2:n pito notkahti alussa noin 2,2 bariin, koska ff 0,24 jäi tarpeen 0,54 alle (säätimen ensimmäinen ajo, kuristin
  toisessa tilassa). Pidon hajonta on c1x:llä sama kuin vanhalla polulla (0,112 / 0,116).
- `EU_STALL sec=k` 10–21 ms noin 340 ms välein (VKELLO-rivin tulostus kohdan käsittelyssä) ei osu kääntöihin, koska
  etumatka riittää (`lag_max` ≤ 18,9 ms, varaus 30 ms).
- `pico_dev.py hold` luki PVENT_END-rivin kesken (hold1: `bar=-1.33 r` → HOLD_ABORT, purku oli ok). Korjattu
  ca29944:ssä odottamaan rivin loppuun.
- Seuraava: vaihe 4 (uutto `brew=True` ytimen 1 jaksoilla) suunnitellaan erikseen.

## Vaihe 4 — suunnitelma (20.10.2026, ehdotus käyttäjälle; ei toteutettu)

VAATIMUS: TILAUS-O, TILAUS-K, TILAUS-C, TILAUS-L, TILAUS-I, TILAUS-AUTONOMIA

Uutto (`bim:1`, `pre_infusion_phased(brew=True)`, vaiheet 3–4) ytimen 1 jaksoilla. Sama silmukka jatkuu esiuutosta
uuttoon, joten vaihe 3:n primitiivit (rengas, k+2-jono, CX_OK, nälkä) kantavat sellaisinaan. Muutettavat kohdat:

1. **Valitsin:** `c1x:1` kattaa myös `brew=True`:n; `EU_C1X off reason=brew` poistuu. Siirtymä vaiheeseen 3 ei koske
   jonoon: kohdat k+1 ja k+2 ovat jo jonossa esiuuton päätöksillä, ja uuton ensimmäinen päätös menee kohtaan k+2.
2. **Uuton sivutoimet ytimellä 0 ennallaan:** lämmittimen 100/50 ms -pulssi (`GuardedRelay`, ei ajoituskriittinen)
   ja `set_pump_ratio` 1 s välein. Lämpötilan lukee nyt ydin 1 myös uuton aikana (vanha polku ei lue vaiheissa 3–4).
3. **Keruu ja vuoro:** vaiheen 3 nousun keruuehto (`EB_GC_RISE_FRAC`) ja `on_run` pois c1x:llä; etumatkasääntö kattaa ne.
4. **`TS_END`:** `max_loop_ms` on nyt pisin jakson väli nimellisistä kohdista (~20 ms aina). c1x:llä raportoidaan
   tilalle ytimen 0 pisin käsittelyviive (`lag_max`), ja `EU_C1X`-rivi tulostuu myös uuton lopussa (`EB_C1X`).
5. **Turva:** `run_shot`in `running()` lukee ylipaineen `pressure_filtered`istä, jonka c1x päivittää kohdan käsittelyssä
   (viive ≤ ~20–40 ms) ja `RELAY_PUMP.value()`n raakapinnistä (toimii ytimen 1 kanssa). Vahdin 13 baria lukee
   ADC:n itse 100 ms välein. Ei muutosta; ylipaineen viive kirjataan testiin.

**Testit (`esiuutto_smoke`, `run_brew` + `C1Exec`):** c1x-versiot tapauksista 16 (8 baria, tilat 25b ja 26b), 17
(kuristimen kääntö kesken pidon, TILAUS-C), 19 (keruu + varaukset + ikkunan sulku) ja 22 (lämmittimen lukeman ikä).
Vaatimukset: miss = 0 ja late = 0 koko uutossa; uuton pidon keskiarvo ja hajonta, kääntöjen kaistalle paluu ja
ylitys enintään vanhan polun tasolla + siemenhajonta; lämmittimen lukeman ikä ≤ 1 s. Isäntä ensin, sitten laite.

**Laiteajo (läsnäolo, vesi; VAATIMUS: TILAUS-M kuristimelle, TILAUS-H purulle):** flash; kuristin TILAUS-M:llä:
`kuri:25`, käyttäjä säätää 8 bariin uuttonapilla, valmis = `KURI_END reason=switch`, paine KURI-riveiltä, `kuri:0`;
sitten `pvent` ja `c1x:1` + `pico_dev.py shot <s>`; vertailu `c1x:0`:lla samassa tilassa kuten vaiheessa 3. Lopuksi
`c1x:0`. (20.10.2026 ensimmäinen versio pyysi "kuristin 8 barin asentoon" — korjattu, ks. REKISTERI Viat.)

**Avoin päätös:** pidetäänkö `c1x` RAM-valitsimena vielä vaiheen 4 jälkeen, vai tuleeko siitä oletus (1), kun
laiteajot ovat hyväksytyt.

## Vaihe 4 isännällä 20.10.2026 (toteutettu, käyttäjän hyväksymä suunnitelma)

- `c1x:1` kattaa nyt myös uuton (`bim:1`). Uuton loppuun tulostuu `EB_C1X` (koko ajo), ja `TS_END max_loop_ms` on
  ytimen 0 pisin käsittelyviive. Vaiheen 3 nousun keruuehto ja `on_run` ovat c1x:llä pois.
- **Pidon 1. sekunnin P c1x:llä `EB_C1X_KP_TAIL` 0,2** (vanha polku 0,4). Jakson lisäviiveen kanssa korotettu P
  värähteli pidon alussa: ylitys syntyi 0,75–1,6 s katkaisusta, kun pito alkoi 0,54–0,72 s:n kohdalla. Kokeiltiin myös
  katkaisun ennusteeseen +20 ms ja virheen ennustetta jakson eteenpäin: ylitys kasvoi 0,28–0,35:een.
- `esiuutto_smoke` tapaus 24 (`run_brew` + `C1Exec`), malli:

| ryhmä | late, miss, nälkä | ylitys c1x / vanha (c1x:0) | \|pito − 8\| c1x / vanha |
|---|---|---|---|
| 25b kohinaton (6) | 0 | 0,190 / 0,189 ± 0,084 | 0,030 / 0,025 ± 0,010 |
| 25b kohina (8) | 0 | 0,221 / 0,203 ± 0,057 | 0,031 / 0,031 ± 0,018 |
| 26b kohinaton (6) | 0 | 0,146 / 0,118 ± 0,025 | 0,013 / 0,017 ± 0,008 |
| 26b kohina (8) | 0 | 0,172 / 0,160 ± 0,035 | 0,011 / 0,019 ± 0,009 |

  Kuristimen kääntö (8 siementä): kaistalle 0,61 / 0,55 s (vanha 0,60 ± 0,03 / 0,69 ± 0,17), ei lukkiutumista.
  Keruu, varaukset ja ikkunan sulku 10,5 ms: late = miss = nälkä = 0, `max_loop_ms` 22–27. Lämmittimen lukeman ikä
  pysyy alle 226 ms:n.
- Ylitys on 0–0,03 bar vanhaa suurempi, mutta alle yhden iskun (raja tarkistetaan). Käyttäjän päätös 20.10.2026:
  ylityksen vertailu vanhaan polkuun on vain tuloste, ja laiteajo ratkaisee. 28 smokea exit 0.

## Vaihe 4 laitteella 20.10.2026 (adf8580 + 409431f, kuristin TILAUS-M:llä)

Kuristin `kuri:25` → `KURI_END reason=switch filt=8.21`, filt viimeiset ~2 s 8,11–8,24 bar
(`testit/kuri-20261020-c1x4.log`). Kaukalossa jo 611 g (wmax 740), joten uutot `shot 20`. Kumpaakin ennen `pvent` (ok).

| ajo | polku | esiuutto miss | uutto miss | late (pahin) | starve | uuton pito ka / sd | over (EB_END) | max_loop_ms |
|---|---|---|---|---|---|---|---|---|
| shot1 `testit/c1x-20261020-shot1.log` | c1x | 0 | 0 | 0 (293 µs) | 0 | 8,006 / **0,158** | 0,46 | 20 (lag 20,8 ms) |
| shot2 `testit/c1x-20261020-shot2-vanha.log` | vanha | **6** | **11** | 0 (late_max 15,4 ms) | — | 8,001 / 0,213 | 0,44 | 35 |

- TILAUS-O täyttyy myös uutossa: ei yhtään pois jäänyttä jaksoa, ja yksikään kääntö ei myöhästynyt yli 300 µs.
  Vanha polku jätti samassa tilassa pois 17 jaksoa.
- Pidon hajonta on pienempi kuin vanhalla polulla (0,158 vs 0,213), ja ylitys on sama (0,46 / 0,44). Mallin
  ennustama 0–0,03 bar:n lisäylitys ei näy laitteella.
- Tarve muuttui ajojen välillä (0,40 → 0,30, kuristin lämpeni), joten vertailu on suuntaa antava (1 + 1 ajoa).
- Lopuksi `c1x:0` (oletus), `kuri:0`, `bim:1`.

### Vaihe 4: sarja 3 + 3 (20.10.2026, kuristin 8 barissa edellisestä säädöstä, käyttäjä; `testit/c1x-20261020-sarja{1..6}-c1x{1,0}.log`)

| ajo | polku | miss esi + uutto | late | pito sd | over (EB_END) | katkaisu p / nousu bar/s | jälkinousu → huippu |
|---|---|---|---|---|---|---|---|
| 1 | c1x | 0 + 0 | 0 (268 µs) | 0,170 | 0,64 | 6,35 / 20,9 | 1,90 → 8,25 |
| 2 | vanha | 1 + 11 | 2 | 0,214 | 0,17 | 6,30 / 21,8 | 1,42 → 7,72 |
| 3 | c1x | 0 + 0 | 0 (260 µs) | 0,177 | 0,39 | 6,55 / 20,8 | 1,85 → 8,39 |
| 4 | vanha | 2 + 5 | 0 | 0,192 | 0,12 | 6,30 / 21,7 | 1,51 → 7,81 |
| 5 | c1x | 0 + 0 | 0 (258 µs) | 0,185 | 0,53 | 6,57 / 21,3 | 1,95 → 8,53 |
| 6 | vanha | 0 + 4 | 0 | 0,201 | 0,19 | 6,01 / 20,5 | 1,72 → 7,73 |

- c1x: TILAUS-O täyttyy kaikissa (miss 0, late 0), ja pito on tasaisempi (sd ka 0,177 vs 0,202).
- **c1x:n ylitys on laitteella suurempi (ka 0,52 vs 0,16).** Syy on katkaisun jälkinousu eikä pidon alku:
  nousu on katkaisussa ~21 bar/s, ja päätös toteutuu jakson (20 ms) myöhemmin, eli +0,4 bar. Mallin 8 barin nousu on
  ~11 bar/s ja sen ylitys tuli pidon alusta, joten malli ei näyttänyt tätä, ja isännällä kokeiltu katkaisun +20 ms
  poistettiin (ks. EB_C1X_KP_TAIL). Lisäksi vuorottelu sekoittaa opitun jälkinousun (`eb_coast_s` 0,065–0,083
  molemmista poluista).
- Ehdotus: katkaisun ennusteeseen +20 ms c1x:llä ja oppiin −20 ms (polusta riippumaton `coast_s`), laitteella 3 + 3.
  c1x:stä ei tehdä oletusta ennen sitä.

### Vaihe 4: sarja 2 (f0a7a09, katkaisun ennuste +20 ms c1x:llä; `testit/c1x-20261020-sarjab{1..6}-c1x{1,0}.log`)

| ajo | polku | miss esi + uutto | late | pito sd | over | katkaisu p / nousu | jälkinousu → huippu |
|---|---|---|---|---|---|---|---|
| 1 | c1x | 0 + 0 | 0 (264 µs) | 0,195 | 0,44 | 6,46 / 12,7 | 0,85 → 7,31 |
| 2 | vanha | 2 + 16 | 0 | 0,202 | 0,25 | 6,46 / 24,5 | 1,42 → 7,88 |
| 3 | c1x | 0 + 0 | 0 (260 µs) | 0,194 | 0,61 | 6,38 / 21,9 | 2,23 → 8,61 |
| 4 | vanha | 4 + 5 | 1 + 2 | 0,226 | 0,59 | 6,46 / 21,3 | 1,62 → 8,07 |
| 5 | c1x | 0 + 0 | 0 (246 µs) | 0,189 | 0,31 | 6,02 / 20,2 | 2,18 → 8,20 |
| 6 | vanha | 3 + 10 | 2 | 0,241 | 0,32 | 6,36 / 24,3 | 1,95 → 8,32 |

- Ylitys ka c1x 0,45 vs vanha 0,39 (vanhan vaihtelu 0,25–0,59). Ennen korjausta ero oli 0,52 vs 0,16.
- Pito sd c1x 0,193 vs vanha 0,223. Pois jääneet jaksot: c1x 0, vanha 40 (kolmessa ajossa).
- Jälkinousu / nousunopeus on c1x:llä 0,10–0,11 s ja vanhalla 0,06–0,08 s: jakson lisäviive näkyy 0,03–0,04 s:na, ei
  0,02 s:na. Jäljelle jäävä ero ylityksessä on kohinan suuruinen.
- **Käyttäjän päätös 20.10.2026: "Ota käyttöön ja pakkaa"** → c1x oletukseksi (`BrewData.eu_c1x = 1`).
