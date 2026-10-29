# VERKKOKELLO — sisäinen verkkojaksokello, jota paine korjaa (suunnitelma 23.9.2026)

VAATIMUS: TILAUS-A, TILAUS-B, TILAUS-F, TILAUS-G, TILAUS-I, TILAUS-J

Tila: simulaatio tehty ja brief luonnoksena 23.9.2026 (`VERKKOKELLO.brief.md`, `testit/verkkokello_sim.py`); laitekoodia ei ole. Korvaa vaiheen 1a3 "yhden kirjoitettavan verkkojaksolähteen" (REKISTERI.md).

## Ongelma

Nykyinen firmware ajastaa ajon alusta kiinteällä `PCAP_MAINS_US` = 19 960 µs (50,10 Hz). Käyttäjän
alueella 49,9–50,1 Hz jakso on 20 040–19 960 µs, eli vakiojakso voi olla väärin 80 µs/jakso = 4 ms/s.
1b-hajontasarja 23.9.2026 ajautui tästä syystä noin koko jakson 14,8 s:ssa. Paine ei kerro vaihetta,
kun pumppu on pois — siksi kello, joka kulkee myös silloin (TILAUS-J).

## Rakenne: numeerisesti ohjattu kello + vaihelukko (PLL)

1. **Kello (NCO).** Picon `ticks_us`-aikaan sidottu vaiheakku ja jaksoarvio `T`. Kello ennustaa
   jokaisen verkkojakson alun. Kaikki ohitukset, tauot ja käynnistykset ajoitetaan tästä, ei ajon
   alusta. Picon kiteen virhe (±30 ppm ≈ 0,6 µs/jakso) ei vaadi omaa korjausta: `T` mitataan Picon
   omissa mikrosekunneissa, joten kiteen virhe sisältyy siihen.
2. **Vaihemittaus paineesta (TILAUS-B, -I).** Pumpun käydessä lock-in (I/Q) kellon omalla
   taajuudella, keskiarvo N jaksosta (alku N = 8). Tulos on väreilyn vaihe; siitä vähennetään
   tunnettu viive 37–41 ms (TILAUS-I), jolloin saadaan pumpun vaihe suhteessa kelloon.
3. **Korjaus (PI-silmukka).** Vaihevirhe `e` korjaa sekä vaihetta (`Kp·e`) että jaksoa (`Ki·e`).
   Kaista kapea (luokkaa 0,2–0,5 Hz), jotta yksittäinen häiriöjakso ei heilauta kelloa. Muutos
   rajoitetaan per jakso (esim. vaihe ≤ 200 µs, `T` ≤ 2 µs), ja `T` rajataan 19 950–20 050 µs:iin
   (alue + pieni marginaali). Rajan tavoittava arvio on vika, ei korjaus.
4. **Hyväksyntä.** Mittaus käytetään vain, kun väreilyn amplitudi ja signaali-kohinasuhde ylittävät
   rajan ja pumppu on käynyt täysiä jaksoja koko ikkunan (ohitetut jaksot pois ikkunasta tai
   tunnettuna kuviona mukaan). Muuten silmukka ei korjaa — kello jatkaa ennusteella.
5. **Pito pumpun ollessa pois (holdover).** Kello jatkaa viimeisellä `T`:llä. Ennustevirhe kasvaa
   kahdesta syystä: jaksoarvion virhe `df` (virhe = `df·t` jaksoa) ja verkon oma muutos `r` Hz/s
   (virhe = `r·t²/2` jaksoa).

   | Pois-aika | df 0,02 Hz | df 0,005 Hz | r 1 mHz/s | r 5 mHz/s |
   |---|---|---|---|---|
   | 1 s | 0,4 ms | 0,1 ms | 0,02 ms | 0,1 ms |
   | 2 s | 0,8 ms | 0,2 ms | 0,04 ms | 0,4 ms |
   | 5 s | 2,0 ms | 0,5 ms | 0,25 ms | 1,25 ms |
   | 10 s | 4,0 ms | 1,0 ms | 1,0 ms | 5,0 ms |

   Vertailuna vakiojakso 50,0 Hz ilman seurantaa: 0,1 Hz:n virhe = 2 ms/s. Vaiheaskel 1b:ssä oli
   832 µs, joten pito kantaa muutaman sekunnin, ei kymmeniä.
6. **Käynnistys tauon jälkeen.** Pumppu käynnistetään kellon ennustamassa kohdassa, mutta
   ensimmäiset jaksot ajetaan **täysinä ilman ohituksia**, kunnes lukko on palannut (vaihevirhe alle
   rajan M peräkkäisessä mittauksessa). Täysi jakso on turvallinen oletus, joten väärä ennuste ei
   aiheuta vaarallista ohitusta. Pitkän tauon jälkeen (arvioitu virhe > ½ vaiheaskelta) sama sääntö.
7. **Alkulukitus (TILAUS-F, -G).** Uuton alussa `T` = 50 Hz:n jakso; esiuuton paineennostossa leveä
   kaista (nopea taajuushaku, Goertzel/refine_peak: 5 s ≈ 0,015 Hz), sen jälkeen kapea seuranta.
   Arvio säilyy seuraavaan ajoon lähtöarvona, mutta mitataan joka ajolla uudelleen.

## Mitä ei tiedetä ja miten se mitataan

- **Verkon muutosnopeus `r`** tällä verkolla: kirjaa kellon `T` jokaisesta ajosta aikaleimoineen;
  muutaman päivän aineisto antaa `r`:n jakauman. Taulukon 5 mHz/s on oletus, ei mittaus.
- **Lock-inin vaihekohina N jaksolla** laitteella: aja lukitus kiinteällä kuristimella, katso `e`:n
  hajonta. Tämä valitsee N:n ja kaistan.
- **Viiveen 37–41 ms hajonta (9 ms / 7 ms yksittäismittauksena)** — keskiarvo on se, jota käytetään;
  hajonta kertoo, kuinka monta jaksoa lukitusikkunaan tarvitaan.

## Todennus ennen laitetta

Isäntäsimulaatio (`testit/loop_sim.py`/`flow_sim.py`-pohjalta): verkon taajuus 49,9 → 50,1 Hz
rampeilla ja askelilla, pumpputauot 0,5–10 s, paineen kohina mitatulla tasolla. Hyväksyntä: vaihevirhe
lukittuna < ¼ vaiheaskelta, ja jokaisen tauon jälkeen lukko palaa ennen ensimmäistä ohitusta.
Laitteella: sama ajo ja kellon `T` rinnan Fingridin taajuusdatan kanssa, jos se saadaan (avoin).

## Simulaation tulos 23.9.2026 — mikä muuttui suunnitelmasta

VAATIMUS: TILAUS-B, TILAUS-I, TILAUS-J

Luvut ja perustelut ovat briefissä (`VERKKOKELLO.brief.md`, luku "Menetelmä ja miksi").
Suunnitelmaan tuli neljä muutosta:

- **Kohta 2, lock-in-kohina, mitattu vanhoista kaappauksista.** 8 jakson ikkunassa hajonta on
  295–616 us. Pidempi ikkuna ei auta samassa suhteessa, koska kohinassa on hidas vaellus
  (32 jaksoa: 98–402 us). Yliaallot huonontavat arviota.
- **Kohdat 3 ja 4, PI-silmukka ja lukkosääntö, korvattu kolmitilaisella Kalman-suotimella.**
  Lupa perustuu kellon omaan vaihe-epävarmuuteen, ei yksittäisen ikkunan virheeseen, joka on yhtä
  suuri kuin kohina.
- **Kohta 5, pito tauon yli.** Taulukon arviot pitävät vakiotaajuudella, ja virhe kasvaa rampissa
  r·t²/2:n mukaan. Suotimen lupa ottaa kasvun huomioon, joten tauon jälkeen ohitukset odottavat
  lukkoa (0,48 s).
- **Hyväksyntä: ¼ vaiheaskelta (208 us) ei ole saavutettavissa.** Tilalle ehdotetaan 1000 us:a
  (käyttäjän päätös, riippuu SSR:n tyypistä). Jakson rajan 10 us:n marginaali osuu 20 mHz/s:n
  rampissa; päätös briefissä.

## Laitetestin analyysi ja korjaus 23.9.2026 (EXPRESSO-VERKKOKELLO-KORJAUS)

VAATIMUS: TILAUS-B, TILAUS-H, TILAUS-I, TILAUS-J

Lähde: `testit/vkello-20260923-{a,b,d}.log`, analyysi `testit/vkello_replay.py`. Lokin z:t ajettiin
`KF3Clock`-luokan läpi (T täsmää lokiin ≤ 0,05 us), jolloin saatiin kellosta riippumaton mitattu
reuna. Verkon vaihekäyrä sovitettiin vakiotilan ikkunoihin.

- **5 s tauon "+3,8 ms käynnistysvirhe" ei ole kellon virhe.** Kello ennusti tauon yli oikein.
  Paineen uudelleennousussa väreilyn viive on 3,5–5,3 ms vakiotilaa suurempi ja palautuu
  ~5 ikkunassa (~0,8 s), ja amplitudi on samalla 2–5-kertainen (1,0–2,5 bar vs 0,3–0,45). 2 s tauon
  jälkeen siirtymä on 0–1 ms, lyhyemmillä alle 0,7 ms. Simulaation `rasitus`-malli oletti 500 us /
  1 s, eli todellinen on ~8-kertainen.
- **Väärät lukot olivat todellisia kellovirheitä, jotka transientti aiheutti.** Suodin otti
  transientti-ikkunat vastaan ja siirsi kelloa, jolloin seuraavat z:t olivat −3…−4 ms. Lukittu
  virhe ilman porttia oli enintään 3,3–5,0 ms (6–10 lukittua ikkunaa > 1000 us/ajo).
- **Lukittu hajonta 785–950 us** koostuu enimmäkseen tästä. Ilman 5 s -segmenttiä vakiotilan sd on
  476–514 us, eli simulaation alueella 295–616 us. Loput |z| > 1000 us -ikkunat ovat yksittäisen
  ikkunan kohinaa (~2σ), eivät kellovirheitä: z on mittaus, ei kellon virhe.
- **Lukkosääntöä ei muutettu.** Korjaus on mittauksen portti: ikkuna, jonka amplitudi ylittää
  2,0 × hyväksyttyjen liukuvan keskiarvon (`GATE_RATIO`, α 0,2), ei päivitä kelloa. 20 peräkkäisen
  hylkäyksen jälkeen viite siirtyy nykyiseen amplitudiin (`GATE_MAX`; pisin havaittu 10), jotta
  pysyvä painetason muutos ei lukitse mittausta pois. Suhteellinen eikä kiinteä raja, koska
  amplitudi riippuu paineesta (TILAUS-G: 1,8 bar vapaassa virtauksessa, 0,3 bar 7,7 barissa).
- **Tulos laitelokeilla portin kanssa:** lukittuja virheitä > 1000 us 0/ajo, lukitun virheen
  maksimi 540–760 us, hylättyjä ikkunoita 11–17/ajo, ei yhtään ennen ensimmäistä taukoa. Lupa
  77–82 ikkunaa / ~120 (ilman porttia 94–96), koska kellon epävarmuus kasvaa hylättyjen ikkunoiden
  ajan.
- **TILAUS-H:** `vkello` purkaa paineen `_mcal_vent`-syklillä (0,5 s auki / 0,2 s kiinni, kunnes
  paine ei laske) ennen pumppua; loki `VKELLO_VENT cycles bar`.
- **Nousun katto** `VKELLO_REACH_MAX_MS` = 40 000 ms (a nousi 19,2 s:ssa, vanha katto oli 20 000).
- **Loki:** ikkunariville `p_bar` (ikkunan keskipaine) ja `gate` (1 = hylätty), `VKELLO_END`:iin
  `gated` ja `rebased`.

**Avoin, TILAUS-G:** esiuuton paineennosto on tilattu mittausikkunaksi, mutta uudelleennousussa
viive poikkesi vakiotilasta 4–5 ms. Jos viive riippuu painetasosta, nousun aikana luettu vaihe
tarvitsee paineesta riippuvan viiveen. Alkunousua ei ole vielä syötetty kellolle, joten tätä ei ole
mitattu; seuraavan laiteajon `p_bar`-kenttä antaa aineiston.

## Laitetesti 2, 23.9.2026 (EXPRESSO-VERKKOKELLO-LAITETESTI2)

VAATIMUS: TILAUS-B, TILAUS-G, TILAUS-H, TILAUS-I, TILAUS-J

Flashattu setti vkello3 (43e207a): `RESTORE_OK vkello3 n=19`, `VERIFIED 19/19` puhelimen
manifestia vasten, repon pico/ = setti (0 eroa). Ajot `vkello:0`: `testit/vkello-20260923-{e,f,g,h}.log`
klo 15:36–15:43; f:ssä vesisäiliö tyhjeni kesken (paine 6,9 → 1,7 → 0,3 bar pumpun käydessä,
kello ajautui T-rajalle, 4 × `VKELLO_TRAJA`), joten ehjät ajot ovat e, g ja h. Analyysi
`testit/vkello_analyysi.py` ajaa lokit firmwaren oman `Verkkokello`-luokan läpi (T ≤ 0,05 us ja
portin päätös 0 eroa lokiin kaikissa neljässä).

- **Täyttyi kaikissa ajoissa:** `VKELLO_VENT` ennen nousua (1–4 sykliä), nousu tasanteeseen
  ilman noreachia (8,63 / 8,21 / 8,90 bar, 11,1 / 13,3 / 8,5 s), portti hylkää vain taukojen
  jälkeen (gated 11 / 13 / 14, 0 ennen ensimmäistä taukoa), rebased 0.
- **Ei täyttynyt: kellon todellinen virhe lukittuna.** e 16/81 lukittua ikkunaa > 1000 us
  (max 1659 us), g 10/79 (max 1358 us), h 0/78 (max 951 us). Ylitykset ovat tauon jälkeisissä
  ikkunoissa k 4–15, portin jälkeen, kun paine vielä nousee (6,3–7,8 bar, tasanne 7,7–8,8), ja
  kaikki ovat negatiivisia (−1,0…−1,7 ms). Portti hylkää korkean amplitudin alun (~0,8 s), mutta
  paineen palautumisen häntä läpäisee sen ja siirtää kelloa.
- **Raaka ehto "lukittuna |z| > 1000 us vain gate=1" ei ole oikea mittari:** z on yksittäisen
  ikkunan mittaus (vakiotilan jäännöksen sd 443–673 us); 7–14 tällaista ikkunaa per ajo, kaikki
  gate=0, myös h:ssa, jonka kello pysyi rajassa.
- **TILAUS-G, viive paineen mukaan (ehjät ajot, portin läpäisseet ikkunat, poikkeama vakiotilan
  käyrästä):** 3–5 bar −1,4 ms (n 18), 5–6 bar −0,8 ms (n 12), 6–7 bar −0,25 ms (n 61),
  7–8 bar −0,19 ms (n 64), 8–10 bar +0,06 ms (n 158); lineaarisesti +269 us/bar, r 0,53.
  Matalan paineen ikkunat ovat kaikki tauon jälkeistä uudelleennousua, joten paine ja aika
  tauosta eivät erotu tästä aineistosta.
- **5 s tauon jälkeinen 1. ikkuna** (portin hylkäämä): +2,6…+4,0 ms, sama kuin laitetestissä 1.
- **Verkkotaajuus (VKELLO_END):** e 50,0104 Hz (15:36), g 49,9551 (15:41), h 49,9770 (15:43);
  f 49,8753 on T-rajan arvo, ei mittaus.
- **Purun loppupaine negatiivinen:** `VKELLO_VENT bar` −1,08 / −0,95 / −0,67 / −0,70 (yksi raaka
  näyte 0,2 s venttiilin sulkemisen jälkeen). Ylipaine ei voi olla −1 bar; anturin nollapiste
  tai venttiilin sulkemisen painetransientti, selvittämättä.

Seuraava korjaus on käyttäjän valinta: (a) paineportti — ikkuna ei päivitä kelloa, kun `p_bar`
on yli ~1 bar ajon tasanteen alapuolella; tai (b) paineesta riippuva viivekorjaus (TILAUS-G,
TILAUS-I), jolloin nousun ikkunatkin kelpaavat. (b) vaatii aineiston, jossa paine ja aika
tauosta erottuvat (esim. eri kuristimen asennot vakiotilassa).

## Paineportti ja vettä säästävä protokolla 23.9.2026 (EXPRESSO-VERKKOKELLO-PAINEPORTTI)

VAATIMUS: TILAUS-B, TILAUS-G, TILAUS-H, TILAUS-I, TILAUS-J

Käyttäjän valinta laitetestin 2 jälkeen: paineportti ja protokolla samaan pakettiin. Ei flashattu.

- **Paineportti** (`pico/verkkokello.py` `pgate`, `accept`, `P_GATE_BAR` = 1,0 bar): amplitudiportin
  läpäisevä ikkuna ei päivitä kelloa, jos sen keskipaine on yli 1,0 bar hyväksyttyjen liukuvan
  keskiarvon (α 0,2) alapuolella; `GATE_MAX` peräkkäisen hylkäyksen jälkeen viite siirtyy. Loki:
  `gate` 0 = päivitti, 1 = amplitudi, 2 = paine; `VKELLO_END pgated`.
- **Hyväksyntä vanhoilla lokeilla** (`testit/vkello_analyysi.py`, E ei riipu kellosta, käyrä aste 3):
  e 0/64 lukittua > 1000 us (max 453 us, ilman porttia 13/81), g 0/52 (505 us, ilman 12/79), h 0/59
  (891 us, ilman 1/78). Tulos pysyy samana käyrän asteilla 3–6; toisella asteella e:n jäännös
  jätti verkon vaelluksen sisään (sd 673 vs 449 us). Pisin paineportin hylkäysjakso 7 ikkunaa, ei
  siirtoa. Hinta: lupa 52–64 / 119 ikkunaa (ilman 78–81).
- **Protokolla** (`pico/functions.py`): yksi ajo, taukosarja 0,5/1/2/5 s kolmesti
  (`VKELLO_SERIES`), käynti 3 s (`VKELLO_ON_MS`) ja 5 s tauon jälkeen 4 s (`VKELLO_ON_LONG_MS`).
  Paineportin kanssa lukko palaa 0,5–2 s tauon jälkeen ikkunassa k6–13, 5 s tauon jälkeen k12–16.
  Pumppua ~54 s / ~110 g yhdessä ajossa (ennen 3 ajoa × ~30 s / ~190 g, kaukalo tyhjennettiin
  joka ajon välissä). Ajon katto `PGAP_RUN_MAX_MS` 120 s riittää hitaallakin 40 s:n nousulla.
- **Nousun ikkunat lokiin** (`VKELLO_R w t_ms z_us amp p_bar`, `iq_close(learn=False)`): ei
  portteja eikä kellon päivitystä; analyysi vertaa niitä käynnin alun lineaariseen käyrään
  taaksepäin jatkettuna (TILAUS-G-aineisto nousun ajalta, jota ei aiemmin kirjattu).
- **Vesilaskelma, josta protokolla tuli:** nousu 8,5–13,3 s/ajo (35 % pumppuajasta) ei tuottanut
  ikkunoita; kolme erillistä ajoa toisti nousun ja alkulukituksen; 4 s käynnistä ~1,5 s jäi
  lukon palautumisen jälkeen hyödyttä. Ajo h toi kaukaloon ~60 g (kaukalo ~520 g ajon jälkeen,
  tyhjä + ritilä 460 g 19.9.2026) eli ~2 g/s; kaukaloon mahtuu 230–285 g.

Testit: `vkello_rise_smoke.py` (kohta 7: 12 taukoa, VKELLO_R ennen tasannetta ilman päivitystä,
gate=2 vain taukojen jälkeen), `verkkokello_holdout.py`, `vkello_replay.py`, `vkello_analyysi.py`
e/g/h: 0 failed. `turva_pika_smoke.py` 1 failed kuten ennen (testikomentoja 11, odotus 10).
Laitetesti: flashaa ja aja `pico_dev.py vkello 0` kerran; hyväksyntä `vkello_analyysi.py <loki>`
(todellinen lukittu virhe ≤ 1000 us, ≥ 3 taukosarjaa).

## Laitetesti 3, 24.9.2026 (EXPRESSO-VERKKOKELLO-LAITETESTI3)

VAATIMUS: TILAUS-B, TILAUS-G, TILAUS-H, TILAUS-I, TILAUS-J

Pico: vkello4 (51eec34), kaikki 19 tiedostoa täsmäävät HEAD-lähteisiin (`verify` repon manifestia
vastaan 13/17, koska manifesti on 19.9.2026 setistä — tunnettu vika; HEAD-lähteistä laskettua
manifestia vastaan 18/19, `main.py`-rivin tilalla BLE-kohinaa `Connected -`, ensimmäisellä
kierroksella sama tiedosto täsmäsi).

- **Ajo a (`testit/vkello-20260924-a.log`) katkesi ylipaineeseen:** nousu 7,95 bar 10,1 s:ssa,
  9,44 bar 10,6 s:ssa ja nousi yhä, raaka näyte > `PCAP_OVER_BAR` 11,0 → `reason=overpressure`,
  0 ikkunaa. Releet pois `finally`-lohkossa. Käyttäjä: kuristin kaipaa lämmityksen.
- **Lämmitys (`testit/lammitys-20260924-a.log`):** `bp:7` + `tshot:60`; lopussa `duty` 0,56–0,59
  7 barissa (pumppua rajoitettiin yhä), virtaus 3,5–4,3 g/s. Käyttäjä sääti venttiilin itse:
  jatkuvalla pumpulla keskimäärin ~8 bar. `bp` jäi 7:ään (alkuperäinen 8,0), palautus käyttäjän
  luvalla.
- **Ajo b (`testit/vkello-20260924-b.log`), hyväksytty kahdella sarjalla (käyttäjän päätös):**
  `VKELLO_VENT` 3 sykliä −0,71 bar, nousu tasanteeseen 7,35 bar 6,8 s:ssa, 8 taukoa (2 sarjaa),
  sitten `reason=trayrise` (ajon kertymä ≥ `wrise` 250 g). `vkello_analyysi.py`: lukittu todellinen
  virhe 0/87 > 1000 us, **max 528 us** (PASS); portti hylkää vain taukojen jälkeen (53, ennen 0);
  vakiotilan jäännöksen sd 371 us; lupa 87/181; hz 50,0192 (noin klo 8.30). FAIL vain "≥ 3 sarjaa ehjissä
  ajoissa" (reason ≠ ok).
- **Vesi:** säädetyllä kuristimella täysi ajo tuottaisi ~375 g, kaukaloon mahtuu 260 g; protokolla
  laskettiin ~2 g/s:lle. Kahden sarjan ajo mahtuu.
- **TILAUS-G, nousun ikkunat (`VKELLO_R`, käyrä jatkettu taaksepäin; analysaattori ohittaa ne
  reason ≠ ok -ajoissa, laskettu `analyse()`:lla suoraan):** 1–3 bar −2,0 ms (n 3), 3–4 −1,2 ms,
  4–5 −0,8 ms, 5–6 −0,6 ms (n 2), 6–7 +0,19 ms (n 7), 7–8 −0,20 ms (n 12); alle 1 bar (täyttö)
  kohinaa (sd 1,9 ms). Viive riippuu paineesta myös ilman taukoa, sama suunta ja koko kuin
  laitetestin 2 tauon jälkeisissä ikkunoissa (3–5 bar −1,4 ms): esiuuton nousussa luettu vaihe
  tarvitsee paineesta riippuvan viivekorjauksen alle ~6 barissa. Portin läpäisseissä 6–8 barin
  ikkunoissa riippuvuutta ei ole (+176 us/bar, r 0,10).
- **Purun loppupaine** taas negatiivinen: −0,68 (a) ja −0,71 (b).

## TILAUS-G: viivepoikkeama ja nousun ikkunat, analyysi 24.9.2026

VAATIMUS: TILAUS-G, TILAUS-I, TILAUS-B. POIKKEAA ei vielä: nousua ei oteta kellon opetukseen
ennen käyttäjän päätöstä (alla).

Aineisto: vkello-20260923-e/g/h ja -20260924-b, 510 ikkunaa, jäännös = E − vakiotilan käyrä
(= todellinen viive − `LAG_US`). Skriptit `testit/vkello_dpdt.py`, `vkello_dpdt_replay.py`,
`vkello_rise_learn.py`.

- **Poikkeama selittyy paineen nousunopeudella, ei painetasolla.** Taaksepäin laskettu dp/dt:
  R² 0,29, −154 us per bar/s; paine, vaje tasanteesta ja aika tauosta 0,10–0,15, eivätkä lisää
  mitään dp/dt:n rinnalla (paineen kerroin 11 us/bar). Luokittain: < 2 bar/s ~0, 2–4 bar/s
  −613 us, 4–7 −961 us, 7–12 −1091 us. Laitetestin 2 "viive paineen mukaan" oli siis nousunopeutta:
  matala paine esiintyi vain nousussa.
- **Ei I/Q-ikkunan trendivuoto:** ennuste 2·dp/(A·ω²) selittää R² 0,10 ja väärällä kertoimella.
- **Ajojen välinen ero on suuri:** 4–7 bar/s e −1370, g −990, h −366, b −1121 us; luokan sisäinen
  sd ~850 us. Kiinteä korjaus ei kata tätä.
- **Replay, kerroin toisen päivän ajoista:** porttien kanssa korjaus ei muuta lukittuja virheitä
  (0 > 1000 us kaikissa; max e 453→430, g 505→383, h 891→815, b 528→665 us). Ilman paineporttia
  lupa +14…+26 ikkunaa, mutta b ja h 4 lukittua > 1000 us (max 1430 / 1249 us).
- **Nousu kellon opetuksena (TILAUS-G:n käyttö), ajo b:** 26 nousuikkunaa (p ≥ 1 bar) → kello
  ilmoittaa lukon, mutta virhe nousun lopussa −3,9 ms ilman korjausta, +3,6 ms korjauksella
  (T rajalle 19 950), −6,8 ms 23.9.-sovituksella. Lukkosääntö antaa väärän varmuuden, kun virhe on
  järjestelmällinen. Nykyinen `learn=False` nousussa on siksi oikea, ja paineportti jää.

Avoin, käyttäjän päätös: TILAUS-G:n vaihe nousun aikana ei ole näillä menetelmillä saavutettavissa.
Vaihtoehdot: (a) vaihe tasanteelta, nousu vain taajuudelle tai ei lainkaan (poikkeama TILAUS-G:stä);
(b) lisäaineisto eri kuristinasennoista, jotta ajojen välinen ero selittyy (virtaus?); (c) muu.
