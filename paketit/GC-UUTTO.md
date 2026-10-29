# EXPRESSO-GC-UUTTO — roskienkeruun katkot uuton aikana (suunnitelma 20.10.2026)

Lähtö: WIFI-AIKAIKKUNA (`paketit/WIFI-AIKAIKKUNA.md`) mittasi, että Wi-Fin osuus katkoista on pieni ja niitä hallitsee GC.
Käyttäjä 20.10.2026 valitsi: "Vain suunnitelma" — koodia ei muuteta ennen kuin laajuus valitaan.

## Nykytila (mitattu 20.10.2026, 20 s testiuutto, boot 908af624)

- Hallittu `gc.collect()` 300 ms välein (`functions.py:197` `EU_GC_MS`, ehto `:650-660`): 49–52 keruuta/uutto, mediaani
  ~19 ms, 10–16 yli 25 ms, pahin 101–103 ms → ~1,3–1,6 s keruuta 20 s:ssa (`testit/wifiaika-20261020-*.log` `EU_GC`).
- 27.9.2026 sama keruu 15–16 ms, keko 307 kt vapaana (`VAIHESEURANTA.md:616,655`); nyt `fr0` 252 kt → elävä joukko ~55 kt
  suurempi. Keko ~457 kt (Pico 2 W, RP2350, MicroPython 1.28; float = 16 B kekolohko).
- Automaattiset keruut eivät näy `EU_GC`-riveinä vaan nimeämättöminä ~18–20 ms `EU_STALL`-riveinä.
- 80–100 ms piikkien syy ei selviä koodista (ehdokkaat: IRQ-työ merkinnän aikana, merkintäpinon ylivuoto).

## Allokaatiolähteet uuton aikana (koodista arvioitu, ei mitattu)

| # | Lähde | Arvio | Halvin korjaus |
|---|---|---|---|
| 1 | 1 kHz näyte + `Verkkokello.iq_add` (`functions.py:667-669`, `verkkokello.py:142-151`) ~15 floatia/näyte | ~240 kt/s | ADC kokonaislukuna, cos/sin-taulu ×256 kokonaisluvuin, float kerran jaksossa — **koskee TILAUS-A/B/J-mittausta** |
| 2 | `Verkkokello._grow` (`verkkokello.py:65-75`) 3×3-listamatriisit, kutsut `:602`, `:621-623`, `:686-688` | ~100–250 kt/s | `sd_us` kerran jaksossa ja uudelleenkäyttö; P[0][0] suljettuna kaavana; ohita `:602`, kun `pump_next` epätosi |
| 3 | Säätimen viipaleet `hist[-5:]`/`hist[:5]` + `sum` (`:366-367`), PI/D-floatit (`:533-595`), `edge()` | ~50 kt/s | juoksevat summat; kokonaisluvut `edge()`/`_m()` |
| 4 | `scale.flow()` joka 50 ms kierroksella (`main.py:471`, `scale.py:225-255`) + `update()` | ~35 kt/s | `flow()` vain uudella näytteellä; vanhenemistarkistus erikseen (kommentti `main.py:469-470` perustelee nykyisen) |
| 5 | Lokirivit (EU ~9/s, VKELLO, EU_STALL), tee-memoryviewt, Wi-Fi `recvfrom(512)` EAGAINilla, diagnet-kopiot | ~30–40 kt/s | EU-rivi kokonaisluvuin/harvemmin; `Ring.put` ilman viipaleita; `select.ipoll` ennen `recvfrom`; esivarattu pakettipuskuri |

Elävä joukko (pidentää jokaista keruuta): kaikki moduulit lähdekoodina (`MANIFEST.json` vain `.py`; `functions.py` 189 kt,
`classes.py` 68 kt, `bluetooth_handler.py` tuodaan vaikka BLE on pois `main.py:23,101`); `_COS`/`_SIN` 512 floatia ~10 kt;
PB-uuton `pending_brew_log` ~40 kt kuittaukseen asti.

## Riski: allokaatio keskeytykset pois päältä

`diagnet.Ring.put` viipaloi memoryviewejä `disable_irq`-osiossa (`diagnet.py:52-68`). Uuton HB:issä `tmax_us` 20–50 ms →
automaattinen keruu osuu ilmeisesti IRQ-pois-osioon. Korjaus pieni (kopio ilman uusia olioita tai allokaatio ennen osiota).

## Vaihtoehdot (käyttäjä valitsee)

1. **Halvat korjaukset** — `Ring.put`, #2, #3, #4, #5; mittausydin ennallaan. Todennus: isäntätestit, flash, 20 s testiuutto,
   vertailu `EU_GC` n/mediaani/max ja `max_loop_ms` tätä taulukkoa vastaan; sitten `EU_GC_MS` pidemmäksi kulutuksen mukaan.
2. **Myös #1** — 1 kHz kokonaisluvuiksi; isäntäsimulaatio (`testit/mains_freq.py` ym.) todistaa saman taajuuden ja vaiheen.
3. **Jäädytetyt moduulit** — oma MicroPython-käännös, `functions.py`/`classes.py` pois keosta; lyhentää jokaista keruuta.

Mittaa ennen muutosta: 2–3 testiuuttoa per versio (yksi on kohinainen, ks. WIFI-AIKAIKKUNA: EB-pito 341 vs 614).

## Toteutus: vaihtoehto 1 (käyttäjä 20.10.2026 "Halvat korjaukset")

Koodi (isäntätestit 30/30 vihreät; deterministiset tulosteet identtiset muutosta edeltävän kanssa; `shot_test` vaihtelee ajosta toiseen jo ennen muutosta):

- **Ring.put/take_into** (`diagnet.py`): keskeytykset pois -osiossa ei varata mitään. Viipaleet tehdään tilannekuvasta
  ennen osiota, ja osio vain tarkistaa ja kuittaa. Jos IRQ:n put siirsi `r`:n tai `size`:n tai ylikirjoitti dataa
  (`ov`), kierros tehdään uudelleen. Lähetin kokoaa paketin esivarattuun 1400 tavun puskuriin (ei `take()`-kopiota
  eikä `head + data` -yhdistelmää). Testi: satunnaisajo viitettä vastaan, IRQ:n put osion edellä.
- **#2** `Verkkokello.sd_us` suljettuna kaavana `_grow(m)[0][0]`:sta samassa laskujärjestyksessä: MicroPythonin
  naiivilla `sum()`:lla bittitarkka (0/1000 eroa). CPython ≥ 3.12 kompensoi `sum()`:n, joten holdoutin toleranssi on 1e-12.
  `functions.py`: `sd_us(t)` kerran jaksossa, ja `:602`:n `ok` lasketaan vain, kun sitä käytetään (`was_on or pump_next`).
  EU-rivi käyttää samaa arvoa, ja VKELLO-rivi laskee `sd_us`:n kerran (`locked(t, sd)`). `update()`:n `_grow` on ennallaan (~6/s).
- **#3** `hist`-viipaleet indeksisummiksi samassa summausjärjestyksessä (laitteella p5 ja rate eivät muutu). PI-, D- ja
  `edge()`-floatit ennallaan: kokonaislukumuunnos muuttaisi numeriikkaa.
- **#4** `Scale.flow()` palauttaa välimuistin, kunnes tulee uusi näyte tai ikkuna muuttuu. Vanhenemistarkistus ajetaan
  edelleen joka kutsulla (`main.py:469-470`:n perustelu pätee).
- **#5** `wifilink`: `ipoll(0)` ennen `recvfrom(512)`ia. CPythonissa ei ole `ipoll`ia, joten siellä käytetään vanhaa polkua.
  **Ei tehty:** EU-rivin muoto. Analyysit (`analyze_shot.py`, `esiuutto_analyysi.py`) jäsentävät sen, joten muutos on oma päätöksensä.

Todennus kesken: flash luvalla, 2–3 testiuuttoa ja `EU_GC` n/mediaani/max sekä `max_loop_ms` lähtötaulukkoa vastaan.
Sen jälkeen `EU_GC_MS` pidemmäksi kulutuksen mukaan. MicroPython-syntaksi todentuu vasta laitteella, koska palvelimella ei ole `mpy-cross`ia.

## Mittaus laitteella 20.10.2026 (28c6685, boot 4abf8353, 3 × `pvent` + `pico_dev.py shot 20`, `wmax:740 wrise:200`)

Flash: `VERIFIED 23/23`, `FLASH_OK` (`testit/flash-20261020-zero-gc.log`). Ensimmäinen `cmd pvent` flashin jälkeen ei
saanut vastausta 90 s:ssa (ei `CMD_OK`ia, ei PVENT-riviä DIAGNETissa), mutta seuraava yhteys toimi. Tämä vastaa
PICO-HALLINTA §1:n ser2net-ansaa, vaikka `pico_dev.py` avaa `/dev/hubi0`:n itse.

| | jälkeen (WIFI, 908af624) | a | b | c |
|---|---|---|---|---|
| EU_GC n / mediaani / max | 52 / 19,0 / 103 ms | 51 / 18,8 / 108 ms | 54 / 18,9 / **197 ms** | 55 / 18,9 / 109 ms |
| EU_GC > 25 ms / summa | 16 / 1,59 s | 7 / 1,44 s | 16 / 2,22 s | 16 / 1,79 s |
| EU_STALL yht. (k/l/s/y) | 222 (111/61/30/20) | 123 (23/54/17/29) | 140 (19/62/19/40) | 99 (7/53/10/29) |
| `max_loop_ms` | 104 | 113 | 200 | 119 |
| EB_END max / over / hold_sd / miss | 9,43 / 0,69 / 0,313 / 56 | 9,61 / 0,19 / 0,380 / 29 | 10,45 / 1,08 / 0,605 / 116 | 9,42 / 0,43 / 0,321 / 100 |
| `fr_end` (kt) | 189 | 193 | 226 | 215 |

Tulkinta:
- Allokaatio väheni: k-katkot putosivat 111:stä 7–23:een (`sd_us`), EU_STALL-rivejä on 99–140 eikä 222, ja `fr_end` on suurempi.
- Keruiden määrä ei muutu, koska hallittu keruu ajetaan 300 ms:n ajastimella (`EU_GC_MS`). Kesto (mediaani ~19 ms)
  ei muutu, koska se riippuu keosta eikä kulutuksesta.
- Pahimmat keruut, 100–197 ms, eivät johdu kulutuksesta: b:n 197 ms on uusi ennätys, ja se nosti `max_loop_ms`:n
  200:aan ja huipun 10,45 bariin (raaka raja 11,0). Syy on yhä auki. Ehdokkaat: merkintäpinon ylivuoto (koko keon
  uudelleenkäynti) tai IRQ-työ merkinnän aikana.
- Kolme ajoa vaihtelevat paljon (b vs. a/c), kuten jo WIFI-AIKAIKKUNAssa.

Lokit `testit/gcuutto-20261020-{a,b,c}.log` ja `-pvent.log`; kaukalo 565 → 615 g.

## Avoin: 60 ms:n vuorokatko 500 ms:n ruudukossa (20.10.2026)

Testiuutoissa b ja c oli 16 ja 20 kpl `EU_STALL sec=y` ≥ 55 ms (task=-:0), osumat tasan 500 ms:n välein (b x194/x694,
c x217/x717). Ajossa a niitä oli 1, ennen muutosta (WIFI-AIKAIKKUNA) 0–1. Kaikki tehtävät merkitsevät itsensä,
joten aika kului muualla kuin tehtävissä (radion ajuri tai lwIP?). Uuton aikana 500 ms:n tahdissa toimii DIAGNET-lähetin,
jota 28c6685 muutti. Äppi tilasi Wi-Fi-linkin a:n ja b:n välissä (wtx 0 → 151).
Mittaus: `ystall` (0ace9fc, `pico/ystall.py`): `cmd 'ystall:30:3' 45` (uusi lähetin) vs. `ystall:30:7` (vanha) sekä `:2`/`:0`.
Laitteella on yhä 28c6685; 0ace9fc on flashaamatta (käyttäjä 20.10.2026: "Ei nyt").

### Käyntiaika ja Zero (käyttäjä 20.10.2026)

Käyttäjä: kun keitin on pitkään päällä, viiveet kasvavat ajoittain jopa noin 0,5 s:iin, mahdollisesti myös ilman
Zeroa (ei varma). Keräimen historia ei riitä todentamaan tätä: DIAGNET on kerännyt dataa vasta 20.10. ja pisin
boot oli 1,8 h. Jatkuva mittaus: HB:n `lmax_us` (30 ms tehtävän pisin myöhästyminen ikkunassa) ja `l100`
(> 100 ms kpl) sekä levossa `gc_us` (yksi hallittu keruu minuutissa) ja `live_kb` (keko keruun jälkeen). Analyysi
käyntiajan (`up_s`) mukaan; Zero irti -jaksot käyttäjän ilmoituksesta.

### ystall levossa 20.10.2026 (f0b0454, boot 3346273f, 6 × 30 s, lämmitin pois, pumppu ei käy)

| ajo | bitit | vuoro y > 10 ms | hallittu keruu: kpl / mediaani / > 100 ms / > 300 ms / max |
|---|---|---|---|
| 1 | 3 (DIAGNET uuttotahti + keruu) | 0 | 63 / 97 ms / 25 / 17 / 599 ms |
| 2 | 7 (sama, vanha lähetin) | 0 | 65 / 93 ms / 24 / 16 / 500 ms |
| 3 | 2 (keruu) | 0 | 70 / 90 ms / 25 / 6 / 400 ms |
| 4 | 0 (ei mitään) | 2 (213 ms, task=scale: automaattinen keruu) | — |
| 5 | 3 | 1 (19 ms) | 72 / 84 ms / 21 / 6 / 400 ms |
| 6 | 7 | 0 | 66 / 94 ms / 22 / 18 / 402 ms |

- 60 ms:n vuorokatko ei toistunut kummallakaan lähettimellä. Uutoissa b ja c sen aiheutti muu kuin lähetin.
- **Levossa keruu kestää 80–600 ms (mediaani ~90), uutossa ~19 ms.** Kestot asettuvat 100 ms:n portaille
  (300 099, 300 741, 301 160, 398 585, 400 005, 400 222, 402 115, 500 491, 599 087 µs). 100 ms on releen vahdin
  `Timer(-1, period=POLL_MS=100)` jakso (`relayguard.py:62,318`). Ehdokas: keruu odottaa vahdin kutsua tai kutsu
  osuu keruun keskelle. Todentamatta.
- HB:n levossa ajettu keruu: 82 ms käynnistyksessä (`live_kb=177`), 294 ms 6 min kohdalla (`live_kb=182`).
  Tämä sopii käyttäjän havaintoon jopa 0,5 s:n viiveistä.
Lokit `testit/ystall-20261020-*.log`.

### Vahtikoe 20.10.2026 (1d9ceec, boot f8d85045; vahdin kutsu tauolla `paused`, ajastin käynnissä)

| ajo | bitit | hallittu keruu > 10 ms / mediaani / > 100 ms / > 300 ms / max |
|---|---|---|
| 1 | 2 | 68 / 91 ms / 25 / 12 / 501 ms |
| 2 | 10 (vahti tauolla) | 60 / 98 ms / 29 / 20 / 600 ms |
| 3 | 2 | 68 / 89 ms / 26 / 11 / 404 ms |
| 4 | 10 (vahti tauolla) | 69 / 93 ms / 21 / 12 / 500 ms |

- Vahdin kutsun työ ei selitä hidasta keruuta: kestot ovat samat kutsun ollessa tauolla. Vahti `guard=ok` kokeen jälkeen.
  Itse ajastinkeskeytys tuli kokeen aikana edelleen, joten sitä ei suljettu pois. Muut 100 ms:n ehdokkaat: radio (cyw43/lwIP), ydin 1.
- Ajossa 4 `task=diag` vei 771 ms. Kyse on levon HB:stä, jonka f0b0454 laajensi: `mem_free` + `mem_alloc` + `gc.collect` + `mem_alloc` + RSSI.
  Levossa ajettu mittauskeruu tuo siis minuutin välein jopa ~0,5–0,8 s:n katkon diag-tehtävään. Automaattinen keruu
  tapahtuisi levossa joka tapauksessa (HB `free` laskee 256 tavuun), mutta tämä katko on mittauksen oma.

### Radiokoe 20.10.2026 (3ae611b, boot 0f17d6ed; bitti 16 = `wlan.active(False)` ajon ajan)

| ajo | bitit | keruu > 10 ms / mediaani / > 100 ms / > 300 ms / max |
|---|---|---|
| 1 | 2 | 65 / 96 ms / 27 / 16 / 500 ms |
| 2 | 18 (radio pois) | 63 / 100 ms / 30 / 13 / 503 ms |
| 3 | 2 | 66 / 95 ms / 26 / 15 / 501 ms |
| 4 | 18 (radio pois) | 65 / 99 ms / 17 / 10 / 502 ms |

Radio ei selitä hidasta keruuta. DIAGNET liittyi takaisin itse, ja vahti oli `guard=ok`. HB:stä on poistettu
mittauskeruu (3ae611b; vika cacb2a1 korjattu). Seuraava ehdokas on ydin 1: levossa se nukkuu 2 ms:n silmukassa,
uutossa se lukee lämpötilaa (`c1_on`), ja uutossa keruu on ~19 ms. ystall-bitti 32 (`c1_on`/`c1_off`) odottaa flashia.

### Ydin 1 -koe 20.10.2026 (3d306e4, boot 472797b3; bitti 32 = `c1_on` kuten uutossa)

| ajo | bitit | keruu > 10 ms / mediaani / > 100 ms / > 300 ms / max | vuoro y > 10 ms / > 50 ms / max |
|---|---|---|---|
| 1 | 2 (ydin 1 levossa) | 62 / 98 ms / 31 / 17 / 500 ms | 0 / 0 / 9 ms |
| 2 | 34 (ydin 1 lukee) | 88 / **18 ms** / 5 / 0 / 206 ms | 43 / 8 / 65 ms |
| 3 | 2 | 64 / 98 ms / 30 / 14 / 502 ms | 2 / 0 / 18 ms |
| 4 | 34 | 89 / **18 ms** / 5 / 0 / 193 ms | 32 / 1 / 96 ms |

- **Ydin 1 selittää levon hitaan keruun.** Kun ydin 1 on levossa (2 ms:n `sleep_ms`-silmukka, `classes.py:1695`),
  keruu kestää mediaanina 98 ms ja enimmillään 500 ms. Kun se lukee kuten uutossa, mediaani on 18 ms.
- **Lukeva ydin 1 tuo vuorokatkot:** ydin 0:n `sleep_ms(0)` venyy 13–65 ms:iin (25/43 task=-). 65 ms on
  `TEMP_C1_CONV_MS`. Tämä selittänee uuttojen b ja c 60 ms:n katkot. Ytimet jakavat jonkin lukon (GIL tai muu?), todentamatta.
- Uutonkin aikaiset 100–200 ms:n keruut (5/30 s) jäävät myös ydin 1:n lukiessa.
- TILAUS-O ei täyty, kun ydin 0 ajaa jaksot Pythonissa ja ydin 1 lukee lämpötilaa: ytimet häiritsevät toisiaan
  molempiin suuntiin, ja keruu voi kestää yli jakson.

### Ydin 1:n jitter-koe 20.10.2026 (2ce3a40, boot 7efedc62; bitti 64)

| ajo | bitit | ydin 1: näytteitä / suurin väli / > 1,5 ms | ydin 0: keruita / max |
|---|---|---|---|
| 1 | 66 (keruu 300 ms) | 30 000 / 1,072 ms / 0 | 93 / 21 ms |
| 2 | 67 (+ DIAGNET uuttotahti) | 30 000 / 1,061 ms / 0 | 93 / 21 ms |
| 3 | 66 | 30 000 / 1,068 ms / 0 | 93 / 21 ms |
| 4 | 64 (ei hallittua keruuta) | 30 000 / 1,042 ms / 0 | — |
| 5 | 34 (5 s, `c1_on`) | ydin 1:n lukija elossa (`c1=1`), korjaus toimii | 15 / 108 ms |

- **TILAUS-O on toteutettavissa ytimellä 1.** Muisti lukittuna ajettu 1 kHz:n kokonaislukusilmukka, joka lukee paineen
  ADC:ta, ei menettänyt yhtään näytettä 120 000 näytteessä, vaikka ydin 0 keräsi 279 kertaa. Suurin näyteväli oli 1,07 ms.
- Kun ydin 1 pyörii eikä nuku, ytimen 0 keruu kestää aina 17–21 ms. 100–600 ms:n keruut tulevat ytimen 1 `sleep_ms`:stä.
- Seuraava askel: suunnitelma `paketit/C1-JAKSOT.md` ennen koodia (käyttäjä 20.10.2026).
