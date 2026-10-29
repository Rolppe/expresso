# EXPRESSO-PUMPPU-PWM — verkkoon synkronoitu pumpun ohjaus, vaiheittain

| Kenttä | Arvo |
|---|---|
| Tunnus | EXPRESSO-PUMPPU-PWM |
| Skooppi | infra iot |
| Tila | **vaihe 1a valmis ja mitattu: 50,1 Hz**; 1a3 ja 1b avoinna |
| Konteksti | `paketit/PUMPPU-PWM-KONTEKSTI.md` (kontekstiraportti 19.9.2026) |
| Kumoaa | ei mitään vielä — `VIRTAUSSAATO-2.md` säännöt 1-2 jäävät voimaan |

## Mitä käyttäjä tilasi (19.9.2026)

1. Pumpun PWM uudella tavalla: (a) verkkotaajuus mitataan pumpun aiheuttamasta
   painevaihtelusta, (b) viive pumpulta paineanturille mitataan ohittamalla joka toinen
   sykli ja siirtämällä ohitus painetta seuraten oikeaan kohtaan, (c) etsitään syklin
   turvallinen kohta vibration pump -PWM:lle, (d) PWM testataan, (e) PWM integroidaan
   paineenhallintaan 8 bariin niin että käyttäjä kääntää kuristinta ja PWM pitää paineen,
   (f) 2 ml/s virtauskalibrointi samalla tavalla kuristinta säätäen.
2. Optio `pre infusion time auto`: esiuutto päättyy, kun vaa'alla havaitaan ensimmäisten
   kahvipisaroiden aiheuttama poikkeava muutos; erotettava tärinästä ja kohinasta.
3. `max flow rate` -säädin pumpun ohjauksen rajoituksena.
4. Höyryn lämpötilan säädin: nykyisestä arvosta mahdollisuus nostaa +10 °C.

## Sääntö 1 — 60 Hz oli virhe, ja se kantaa koko kvantisoinnin

**Käyttäjän vastaus 19.9.2026: 60 Hz oli hänen oma virheensä, ja se on korjattava kaikkialla,
missä siitä on johdettu noin 17 ms:n sykli.** Suomen verkko on 50 Hz, jolloin jakso on 20,0 ms.

`classes.py:700` sanoo `the machine runs on 60 Hz (user)`; `classes.py:919-922` kertoo, että
50 Hz:n oletus (20 ms) kokeiltiin ja **peruttiin virheenä** — tuo peruutus tehtiin väärän
lähtötiedon perusteella, eli alkuperäinen 20 ms oli oikein; `functions.py:337` toistaa saman
17 ms:n. Näiden varassa ovat:

| Vakio | Paikka | Nyt (60 Hz) | 50 Hz |
|---|---|---|---|
| `step_ms` | `classes.py:698` | 17 | 20 |
| `min_switch_ms` | `classes.py:697` | 17 | 20 |
| `PressureSensor.WINDOW_US` | `classes.py:923` | 16667 | 20000 |
| `get_pressure`-ikkuna | `classes.py:989` | 16667 | 20000 |
| `PCAL_STROKE_MS` | `functions.py:337` | 17 | 20 |

Korjaus ei ole neljän literaalin vaihto vaan **yksi lähde**: jakso määritellään kerran ja muut
johdetaan siitä, jotta vaiheen 1a mittaus muuttaa yhtä lukua. Tämä on vaihe 1a3.

Vaihe 1a mittaa taajuuden silti: mittaus antaa myös väreilyn amplitudin ja aaltomuodon, joita
vaiheet 1b-1d tarvitsevat, ja se todentaa 50 Hz:n koneelta eikä oletuksesta.

## Sääntö 2 — mittaus ei saa mennä keskiarvoikkunan läpi

`PressureSensor.sample_average` keskiarvoistaa täsmälleen yhden oletetun jakson
(`WINDOW_US=16667`, `classes.py:923`). Se on lovisuodatin juuri sillä taajuudella, joka
halutaan löytää. Vaiheen 1a kaappaus lukee `pressure_sensor.read_u16()` suoraan, ilman
keskiarvoa ja ilman kalibrointimuunnosta — kalibrointi on lineaarinen eikä muuta taajuutta,
mutta raaka luku säilyy myöhempien vaiheiden aaltomuotoanalyysille.

## Sääntö 3 — näytetaajuus ja kesto johdetaan erottelukyvystä

50 ja 60 Hz on erotettava, ja tärykalvopumppu on diodilla puoliaaltotasasuunnattu, joten sen
isku tulee kerran verkkojaksossa: perustaajuus = verkkotaajuus, ja toinen harmoninen on
80-140 Hz:n alueella. Näytetaajuus 1000 Hz (jakso 1000 µs, kun `read_u16` vie ~5 µs) ja
kesto 2,0 s antavat 0,5 Hz:n binin ja 16-kertaisen ylinäytteistyksen 60 Hz:llä. Muisti
`array('H', 2000)` = 4 kB.

## Sääntö 4 — kaappaus mahtuu vahtikoiran sisään, mutta ei saa ajaa painetta ylös

Vahtikoira on 8 s ja sitä ruokitaan 1 s välein (`main.py:318-322`). Yhtäjaksoinen 2,0 s:n
kaappaus + 1,0 s asettuminen mahtuu siihen. Kaappaus keskeytyy, jos raaka lukema ylittää
11,0 baria vastaavan rajan, jos mikä tahansa keittimen kytkin on päällä, tai jos
`dev_safe` on päällä. 13,0 barin katkaisu (`functions.py:149-151`) jää toiseksi verkoksi.

## Laitekysymys ratkaistu — SSR-40DA, ja se rajaa vaiheen 1c

**Käyttäjän vastaus 19.9.2026: pumpun kytkin on SSR-40DA.** Se on DC-ohjattu, AC-kuormainen
40 A:n puolijohdeerele, ja mallisarja on **nollaylityskytkevä** (zero cross). Tarkistettava
kyljen tekstistä samalla kun keitin on auki: nollaylityskytkevissä lukee yleensä `Zero Cross`.

Seuraukset, jos tyyppi vahvistuu nollaylityskytkeväksi:

- **Vaihekulmaohjaus on mahdoton.** Triac sytytetään vain nollakohdassa, joten "kohtaa syklistä"
  ei voi valita. Käyttäjän vaihe 1c ei toteudu siinä muodossa kuin se tilattiin.
- **PWM on kokonaisten jaksojen ohitusta** (burst / cycle skipping). Pienin annos on yksi
  verkkojakso, 20,0 ms 50 Hz:llä — sama suure kuin nykyinen `step_ms`, mutta nyt oikean
  mittaisena.
- **Tärykalvopumppu on puoliaaltotasasuunnattu**, joten se iskee kerran jaksossa. Ohjattava
  suure on siis *mitkä iskut päästetään läpi*, ei *milloin jakson sisällä*. Vaihe 1b (joka
  toisen jakson ohitus ja ohituskohdan siirto) on täsmälleen oikea koe tälle, ja vaihe 1c
  supistuu kysymykseksi ohituskuviosta: tasainen jako vs. peräkkäiset iskut.
- Lähdekoodi ohjaa pumppua digitaalisena GPIO-lähtönä GP11 (`preset.py:40-42`) — tämä sopii
  SSR:ään ja pysyy ennallaan; muutos on ajoituksessa, ei laitteistorajapinnassa.

Jos kyljessä lukee `random turn-on`, vaihe 1c palautuu alkuperäiseen muotoonsa ja tämä luku
kirjoitetaan uudelleen.

**Käyttäjän päätös 19.9.2026: kyljen tarkistus poistetaan tehtävistä.** "Ei näillä ole väliä kun
vaste kuitenkin joudutaan mittaamaan testaamalla." Kytkimen tyyppi ei siis ole vaiheen 1b ehto
eikä vaiheen 1c lähtötieto: vaihe 1c saa tarvitsemansa suureen mitatusta invariantista (sääntö 9
korjattuna), ei datalehdestä. Jälleenmyyjien speksitaulut sanovat SSR-40DA:n nollaylityskytkeväksi
ja vasteajaksi 8,3 ms, mutta samaa tunnusta myydään myös random turn-on -versiona, eikä ero näy
muualta kuin kyljestä — juuri siksi asia ratkaistaan mittaamalla eikä lukemalla.

Yksi korjaus lukuun silti: suureen (B) yläraja on **0-9,98 ms**, ei 0-19,96 ms. Nollaylityksiä on
kaksi verkkojaksossa, joten odotus seuraavaan on enintään puolijakso; 19,96 ms on iskujen hila,
koska tärykalvopumppu on puoliaaltotasasuunnattu.

## Mitattu 19.9.2026 — 50 Hz:n korjaus ei ole pelkkä vakion vaihto

Suunnittelija ajoi herkkyyskokeen väliaikaisella kopiolla (`/tmp/p50`, ei repossa): viisi 60 Hz
-vakiota vaihdettiin 50 Hz:n arvoihin ja regressiosimulaatiot ajettiin.

| Koe | `shot_test.py` | `flow_ctrl_sim.py` |
|---|---|---|
| nykytila (step 17 ms, ikkuna 100 ms) | 0 punaista | 0 punaista |
| step 20 ms, ikkuna 100 ms | 0 punaista | **1 punainen** |
| step 20 ms, ikkuna 200 ms | — | 2 punaista |
| step 20 ms, ikkuna 300 ms | — | 3 punaista |
| step 20 ms, ikkuna 400 ms | — | 2 punaista |
| step 20 ms, ikkuna 500 ms | — | 4 punaista |
| step 20 ms, delta-sigma, `kp`/`ki` ennallaan | 0 punaista | 2 punaista |

Kaksi johtopäätöstä:

1. **`PAINESAADIN-HEILUNTA.md`:n halvin korjausehdokas on kumottu.** Se esitti `window_ms`
   100→300 (`PAINESAADIN-HEILUNTA.md:26-38`). Mitattuna ikkunan pidentäminen ei korjaa mitään
   vaan huonontaa tulosta joka askeleella: ikkuna on samalla säätösilmukan viive, ja laitokselle
   sovitettu aikavakio on `1/1,24 ≈ 0,8 s` (`testit/real_plant_sim.py:8`), joten 300-500 ms:n
   ikkuna syö säätökaistan nopeammin kuin lisäresoluutio tuo takaisin.
2. **Kaatuva väite on virtauksen asettuminen avoimimmassa vaiheessa** (`k=3,0`, toleranssi
   0,3 g/s). Siellä vahvistus on noin 20 g/s per yksikkö dutya (`VIRTAUSSAATO-2.md`), joten yksi
   kvantisointiaskel on 17 ms:llä 3,4 g/s ja 20 ms:llä 4,0 g/s — kumpikaan ei osu 0,3 g/s:n
   toleranssiin kvantisoinnilla, vaan vain 1,0 s:n keskiarvon yli tapahtuvalla ditheröinnillä.
   Nykyinen viritys on siis jo valmiiksi marginaalilla, ja oikea jaksonpituus työntää sen yli.

Delta-sigma-koe (päätös kerran verkkojaksossa, murto-osa kertyy jäännökseen) jätti kaksi väitettä
punaiseksi, mutta `kp`/`ki` olivat ikkuna-aktuaattorille viritetyt eikä niitä viritetty uudelleen.
Koe on siis epäselvä, ei kumoava — ja aktuaattorin vaihto on vaiheen 1c työtä, ei 1a:n.

**Seuraus järjestykseen:** vakion 60→50 Hz korjaus ei voi jäädä vihreäksi ilman säätimen
uudelleenvirittämistä, ja se viritys tehtäisiin simulaatiota vasten koneella, jonka
virtaussäädön laiteajo on yhä ajamatta (`paarekisteri.md:7,950`). Siksi mittaus tehdään ensin:
vaihe 1a-ii antaa oikean jaksonpituuden koneelta, ja vasta se luku viedään koodiin vaiheessa 1a3
yhdessä vaiheen 1c aktuaattorityön kanssa.

## Vaihe 1a mitattu 19.9.2026 — verkkotaajuus on 50,1 Hz

Kolme laiteajoa, kaikki lokeina `testit/`-hakemistossa. Taajuus toistui joka kerta.

| Ajo | Loki | Keskipaine | DRIFT | MAINS | conf | amp | HARM2 |
|---|---|---|---|---|---|---|---|
| 1 | `pcap-20260919-verkkotaajuus.log` | ~0 bar | 0,39 bar | 50,1 Hz | 6,81 | 1,788 bar | 90,6 Hz (vuotoa) |
| 2 | `pcap-20260919-tasanne.log` | nousussa | 6,55 bar | 50,1 Hz | 7,59 | 0,947 bar | 100,6 Hz |
| 3 | `pcap-20260919-8bar.log` | 7,69 bar | −0,29 bar | 50,1 Hz | 3,21 | 0,307 bar | 100,2 Hz |

Ajo 3 on ainoa asettunut (`PCAP_SETTLED bar=7.92 peak=8.81 reach_ms=8578 hold_ms=3000
drift=1.92 reason=target`). **60 Hz oli väärä lähtöoletus, ja se on nyt kumottu koneelta
mitattuna, ei päätellen.**

### Väreily riippuu voimakkaasti paineesta

Amplitudi putoaa 1,788 barista (vapaa virtaus) 0,307 bariin (7,7 bar) — lähes kuusinkertaisesti.
Paineistettu piiri vaimentaa iskun. Toinen harmoninen on käyttöpaineessa 0,204 bar eli 66 %
perustaajuudesta, joten aaltomuoto on kaukana siniaallosta ja iskut ovat teräviä.

### Keskiarvoikkuna ei ole heilunnan juurisyy

Jäännösväreily liukuvan keskiarvon jälkeen, mitattuna ajon 3 datasta (7,69 bar):

| Signaali | Jäännös (sd) |
|---|---|
| raaka | 0,363 bar |
| `16 667 µs` (nykyinen, 60 Hz:n oletus) | 0,102 bar |
| `20 000 µs` (mitattu 50 Hz) | 0,082 bar |

Ikkuna on väärän mittainen ja sen korjaus vähentää säätimen näkemää kohinaa 20 %, joten se
korjataan — mutta **0,102 bar ei voi selittää mitattua heiluntaa sd 0,56-0,69 bar** 8 barin
pidoissa. Suunnittelija arvioi aiemmin vapaan virtauksen datasta (0,326 bar), että läpivuoto
olisi merkittävä osa heilunnasta; käyttöpaineen mittaus kumoaa sen. `PAINESAADIN-HEILUNTA.md`:n
alkuperäinen epäily — dutyn kvantisointi — jää johtavaksi ehdokkaaksi, ja vain sen esittämä
korjauskeino on kumottu (ks. edellinen luku).

### Aikabudjetti on mitattu, ei arvattu

Tavoitteen 6,0 bar saavuttamiseen meni **8578 ms**. Kahden sekunnin asettuminen, jolla vaihe
aloitettiin, oli neljä kertaa liian lyhyt. Pidon aikana paine ajautui vielä 1,92 bar ylöspäin:
**tällä kuristimen asennolla tasapainoa ei ole 6 barissa**, vaan paine jatkaa nousuaan kunnes
jokin muu rajoittaa. Vaiheiden 1b-1f mittaukset on tehtävä kuristin avattuna niin, että
tasapaino on olemassa, tai hyväksyttävä ajautuma ja korjattava se analyysissä.

### Avoin pikkuvika

`mains_freq.py`:n `DRIFT`-rivin absoluuttiset alku- ja loppuarvot eivät sisällä kalibroinnin
offsetia (−0,990 bar), joten ne lukevat noin barin liian korkeina. Itse ajautuma on erotus eikä
siihen vaikutu, joten mittaukset ovat päteviä. Korjataan seuraavan paketin yhteydessä.

## Vaihejako ja mitä kukin vaihe tuottaa

| Vaihe | Tilauskohdan tunnus | Sisältö | Laitteisto | Brief |
|---|---|---|---|---|
| 1a-i | `TILAUS-A`, `TILAUS-F` | `pcap:`-kaappauskomento firmwareen + isäntäanalysaattori `testit/mains_freq.py` itsetesteineen | ei | `PWM-1A-VERKKOTAAJUUS.brief.md` |
| 1a-ii | `TILAUS-A` | **tehty 19.9.2026: 50,1 Hz kolmesta ajosta** | — | — |
| 1a2 | `TILAUS-A` | **tehty**: `pico_dev.py pcap` | ei | `PWM-1A2-ISANTAKOMENTO.brief.md` |
| 1a3 | `TILAUS-A`, `TILAUS-L` | verkkojakso yhdeksi lähteeksi **mitattuun** arvoon, viisi vakiota johdetuiksi — ajetaan yhdessä vaiheen 1c kanssa | ei | — |
| 1b | `TILAUS-B`, `TILAUS-I`, `TILAUS-J` | joka toisen jakson ohitus, ohituskohdan siirto painetta seuraten → viive pumpulta anturille; säännöt 5-8 ja protokolla alla | kyllä | `PWM-1B1-PHOLD`, `PWM-1B2-PORTITUS`, `PWM-1B3-ANALYSAATTORI` |
| 1c | `TILAUS-L` | syklin turvallinen ohjauskohta (riippuu avoimesta laitekysymyksestä) | kyllä | — |
| 1d | `TILAUS-L` | PWM:n testi | kyllä | — |
| 1e | `TILAUS-C`, `TILAUS-K` | PWM paineenhallintaan, 8 bar kuristinta kääntäen | kyllä | — |
| 1f | `TILAUS-D` | 2 ml/s virtauskalibrointi PWM:llä | kyllä | — |
| 2 | `TILAUS-E` | `pre infusion time auto` vaa'an muutoksesta | kyllä | — |
| 3 | `TILAUS-S` | `max flow rate` -rajoitin | osin | — |
| 4 | `TILAUS-T` | höyryn lämpötilan säädin +10 °C | kyllä | — |

Vaiheet avataan yksi kerrallaan: seuraavan briefin kirjoittaa vasta edellisen mittaus.

## Kaappauksen sarjaprotokolla (vaihe 1a-i toteuttaa tämän)

Komento `pcap:<ms>` (200-2500, oletus 2000), lisäksi `pcap:stop`. Ajo tulostaa USB-sarjaan:

```text
PCAP_START rate=1000 n=2000 settle_ms=1000
PCAP <idx> <t_us> <v0> <v1> ... <v19>
...
PCAP_END n=<n> dur_us=<d> pmax=<bar> reason=<ok|overpressure|switch|devsafe|stop>
```

`<idx>` on rivin ensimmäisen näytteen järjestysnumero, `<t_us>` sen `ticks_us`, `<v..>`
kaksikymmentä raakaa `read_u16()`-arvoa. Rivejä on `n/20`. Isäntä kaappaa ne
`pico_dev.py capture <s> <loki>` -komennolla, joka lukee sarjaa jo nyt
(`pico_dev.py:146`).

## Analysaattorin sääntö — todellinen näytetaajuus, ei nimellinen

`testit/mains_freq.py` laskee näytetaajuuden `PCAP_END`-rivin `dur_us`/`n`-suhteesta, ei
nimellisestä 1000 Hz:stä. Se poistaa sarjasta lineaarisen trendin (paine nousee kaappauksen
aikana), ajaa Goertzelin 40,0-70,0 Hz alueella 0,1 Hz:n välein ja erikseen 80,0-140,0 Hz
alueella, ja tulostaa:

```text
MAINS <f> Hz amp=<bar> conf=<suhde toiseksi suurimpaan erilliseen huippuun>
HARM2 <f> Hz amp=<bar>
```

`conf` alle 2,0 tarkoittaa, ettei mittaus riitä päätökseen, ja se sanotaan tulosteessa.

## Vaihe 1b — säännöt, johdettu vaiheen 1a mittauksesta (19.9.2026)

Vaihe 1b mittaa viiveen pumpulta paineanturille. Tilaus sanoo "ohita joka toinen sykli ja siirrä
ohitus painetta seuraten oikeaan kohtaan"; nämä säännöt ratkaisevat, mitä se tarkoittaa koneella,
jossa ei ole nollaylityksen tunnistinta.

### Sääntö 5 — tuntemattomia on kaksi, ja vain toinen on viive

- **(A) Isku → paineanturi.** Hydraulinen viive siitä, kun yksi isku päästetään läpi, siihen kun
  anturi näkee sen. Tämä on tilattu suure.
- **(B) Verkon nollaylityksen vaihe Picon kellossa.** Picolla ei ole nollaylityksen tunnistinta, ja
  SSR-40DA kytkee (mallisarjan mukaan) vasta seuraavassa nollaylityksessä. Ohjauskäskyn ja läpi
  päässeen iskun väliin jää siis 0–19,96 ms tuntematonta odotusta.

Yhdestä portitetusta kaappauksesta saadaan **yhdistelmä (A)+(B)**, ei kumpikaan yksin. Ne erotetaan
toisistaan toistamalla ajo eri vaihesiirroilla: jos mitattu viive **pysyy vakiona** vaihesiirtoa
muutettaessa, se on hydraulinen (A) ja SSR:n kvantisointi ei näy tällä erottelukyvyllä; jos se
**siirtyy portaittain** noin 20 ms:n jaksoissa, (B) hallitsee ja vaihe 1c on pakotettu
kokonaisjaksojen ohitukseen. Kumpi tahansa tulos on vaiheen 1c lähtötieto; tämä on koko 1b:n
päätöskohta, ei sivuhuomio.

### Sääntö 6 — portitus johdetaan näytteen indeksistä, ei erillisestä kellosta

Verkkojakso on mitattu 50,1 Hz eli **19 960 µs**, ja portin jakso on kaksi verkkojaksoa,
**39 920 µs**. Kaappaus ottaa näytteen 1000 µs välein (`PCAP_RATE_US`), joten portin tila lasketaan
näytteen omasta järjestysnumerosta:

```text
gate(i) = ((i * 1000 + phase_us) % 39920) < 19960     # 1 = pumppu päällä, 0 = ohitettu jakso
```

Tästä seuraa kolme asiaa, joista yksikään ei ole makuasia:

1. **Isäntä laskee saman portin uudelleen** pelkästä näytteen indeksistä ja `phase_us`:stä — portin
   tilaa ei tarvitse tallentaa lokiin eikä kaappauksen tietomäärä kasva.
2. Portti ei ajaudu, koska se ei ole erillinen ajastin vaan sama aikajana kuin näytteet.
3. Reunat osuvat ±1 ms tarkkuudella, mikä on 18° verkkojaksossa. Se riittää suureelle (A), jonka
   odotettu suuruusluokka on millisekunteja, muttei erottele SSR:n sytytyskulmaa — eikä tarvitsekaan,
   koska nollaylityskytkevällä SSR:llä sytytyskulmaa ei ole.

**Jaksonpituus 19 960 µs kirjoitetaan tässä vaiheessa omaksi vakiokseen** `PCAP_MAINS_US`, ei
johdeta `step_ms`:stä: viiden 60 Hz -vakion yhdistäminen yhdeksi lähteeksi on vaihe 1a3, joka
ajetaan vasta vaiheen 1c kanssa (ks. päätökset). Vakion kommentti viittaa 1a3:een, jotta se ei jää
kuudenneksi irralliseksi literaaliksi.

### Sääntö 7 — tasapaino ennen mittausta, ja siihen tarvitaan oma komento

Vaiheen 1a ajo 3 osoitti, että nykyisellä kuristimen asennolla 6 barissa ei ole tasapainoa: paine
ajautui pidon aikana 1,92 bar ylöspäin. Portitettu ajo pudottaa pumpun tehon puoleen, joten
portituksen vaikutus ja kuristimen ajautuma menisivät samaan suuntaan eikä niitä voisi erottaa.

Siksi **kuristin avataan ensin tasapainoon**, ja siihen kirjoitetaan komento `phold:<s>`, joka ajaa
pumppua ja magneettiventtiiliä vapaasti ja tulostaa 500 ms välein paineen ja sen muutosnopeuden.
Käyttäjä kääntää kuristinta, kunnes muutosnopeus on nollassa halutussa paineessa. Tämä komento
suunniteltiin jo vaiheessa 1a mutta jätettiin kirjoittamatta (ks. päätökset); vaiheissa 1b–1f se
tarvitaan joka ajossa.

### Sääntö 8 — hidas ajautuma poistetaan liukuvalla keskiarvolla, ei suoralla

`mains_freq.py` poistaa lineaarisen trendin. Portitetussa ajossa paine ei laske lineaarisesti vaan
eksponentiaalisesti (laitoksen aikavakio 0,81 s), joten suora jättää jäännökseen kaarevuutta juuri
sille taajuusalueelle, jota mitataan. Jäännös lasketaan sen sijaan erotuksena **täsmälleen yhden
portin jakson liukuvaan keskiarvoon**: boxcar-keskiarvo, jonka pituus on portin jakso, nollaa
tasan portin taajuuden ja sen kerrannaiset (25,05 Hz, 50,1 Hz), joten erotus säilyttää ne
koskemattomina ja poistaa kaiken hitaamman. Tämä ei ole viritysparametri vaan seuraa boxcarin
nollakohdista.

### Protokollalisäys vaiheeseen 1b

Komento laajenee muotoon `pcap:<ms>[:<bar>[:<phase_us>]]`. Kolmas kenttä kytkee portituksen päälle
ja vaatii toisen kentän: portitus ilman tavoitepainetta olisi mittaus tuntemattomasta tilasta.
`PCAP_START` kertoo kaappauksen ehdot, ja siihen lisätään anturin **elävä kalibrointi**, jota
isäntäanalysaattorilla ei tähän asti ollut (ks. avoin pikkuvika):

```text
PCAP_START rate=1000 n=<n> settle=<target|plateau> gain=<g> offset=<o> gate=off
PCAP_START rate=1000 n=<n> settle=target gain=<g> offset=<o> gate=on period_us=39920 on_us=19960 phase_us=<p>
```

Analysaattori `testit/pskip_delay.py` lukee portitetun lokin ja tulostaa:

```text
PSKIP phase_us=<p> n=<n> fs=<Hz>
PSKIP_FOLD <40 arvoa, bar, yksi portin jakso taitettuna 998 µs binneihin>
PSKIP_DELAY <ms> conf=<huippu/jäännöksen rms> amp=<huipusta huippuun, bar>
PSKIP_SUB 25.1 Hz amp=<bar>
PSKIP_FUND 50.1 Hz amp=<bar>
```

`PSKIP_DELAY` on portin nousevan reunan ja taitetun vasteen huipun väli, siis sääntö 5:n
yhdistelmä (A)+(B) — ei puhdas hydraulinen viive, ja tuloste sanoo sen. `conf` alle 2,0 tarkoittaa,
ettei ajo riitä päätökseen, samalla säännöllä kuin `MAINS conf`.

### Sääntö 9 — vaihesiirron invariantti on se, mitä laiteajo lukee

Taitto lasketaan portin nousevasta reunasta, joten vaihesiirto siirtää raportoitua viivettä tasan
itsensä verran:

```text
PSKIP_DELAY(p) = (todellinen viive + p) mod 39920 µs
```

Suunnittelija todensi tämän synteettisellä fikstuurilla ennen laiteajoa (`testit/pskip_fixture.py`):
viive 9 ms, `phase_us` 10 000 → 19,5 ms. **Säännön 5 koe on siis tämä:** aja sama mittaus useilla
vaihesiirroilla ja katso suuretta `PSKIP_DELAY(p) − p`. Jos se pysyy vakiona, viive on hydraulinen
(A) eikä SSR:n kvantisointi näy tällä erottelukyvyllä; jos se hyppii noin 20 ms:n portain, (B)
hallitsee ja vaihe 1c on pakotettu kokonaisjaksojen ohitukseen.

### Mitattu rajoitus — portitusta ei voi todeta aaltomuodosta

Synteettinen koe samalla kohinatasolla kuin laiteajo (sd 0,36 bar, 1,5 s) antoi:

| Suure | Portitettu | Portittamaton |
|---|---|---|
| `PSKIP_DELAY` | osuu puolen binin päähän oikeasta | antaa lukeman, joka ei tarkoita mitään |
| taitoksen puoliskojen ero (rms/amp) | 0,24-0,30 | 0,17-0,21 |
| `SUB/FUND` | 0,48 / 4,18 / 0,48 | 0,26 |

Viiveen lukeminen on siis vakaa, mutta **portituksen toteaminen aaltomuodosta ei ole**. Siksi
analysaattori ei päättele portitusta datasta vaan vaatii sen lokin otsikosta (`gate=on`), ja
suunnittelijan alkuperäinen väite "portittamaton data antaa conf < 2,0" on kumottu mittaamalla
ennen kuin se ehti laiteajoon.

## Vaihe 1b:n pyyhkäisy — säännöt 10-13 (19.9.2026)

Vaiheen 1b ensimmäinen laiteajo tehtiin viitenä erillisenä ajona, ja se ei riittänyt sääntö 5:n
päätökseen: väreilyn amplitudi putosi ajojen välillä 0,94 barista 0,45 bariin, jäännöspaine
ylitti `PCAP_OVER_BAR`-rajan ajojen välissä (9 hylättyä kaappausyritystä) ja portitettu ajo
päättyi joka kerta syyhyn `scalelost`. Säännöt 10-13 korjaavat nämä neljä asiaa.

### Sääntö 10 — pyyhkäisy on yksi laitekomento, yhden asettumisen sisällä

Vaihesiirrot eivät ole verrattavissa, jos jokainen mitataan omasta asettumisestaan: amplitudi
riippuu paineesta voimakkaasti (1,788 bar vapaassa virtauksessa, 0,307 bar 7,7 barissa, ajot 1 ja
3 yllä). Siksi koko pyyhkäisy ajetaan **yhtenä komentona**: asettuminen kerran, ja sen jälkeen
kaikki segmentit peräkkäin samassa ajossa.

Komento on `psweep:<ms>:<bar>[:<n>]` — `<ms>` on yhden segmentin kaappauspituus (200-2500),
`<bar>` pakollinen tavoitepaine (ilman sitä portitus mittaisi tuntemattomasta tilasta, sama
perustelu kuin säännön 7 kolmannella kentällä), `<n>` vaihesiirtojen määrä 2-8, oletus 5.
Vaihesiirrot ovat tasavälein portin jakson yli: `p_k = k * PCAP_GATE_PERIOD_US / n`.

Segmenttijärjestys on `ref, p_0 … p_{n-1}, ref`. Molemmat referenssisegmentit ovat
portittamattomia (`gate=off`): niistä luetaan sääntö 11:n vaihereferenssi puhtaasta
täystehoväreilystä, ja niiden **vaihe-ero kertoo verkkotaajuuden** pyyhkäisyn koko keston yli
(sääntö 12).

### Sääntö 11 — vaihereferenssi luetaan pumpun omasta paineväreilystä

Tilauksen kohta (b) sanoo vaiheen luettavaksi painetta seuraten. `mains_freq.py:78-89`
laskee Goertzelin mutta palauttaa vain amplitudin (`2*sqrt(power)/n`), vaikka `s1`/`s2`
sisältävät myös vaiheen: `phase = atan2(-s2*sin(w), s1 - s2*cos(w))`. Vaihe otetaan käyttöön,
ja jokaisen segmentin viive raportoidaan **kahtena** suureena:

- `delay_ms` — portin nousevan reunan ja taitoksen huipun väli, kuten ennen (sääntö 9);
- `refdelay_ms` — sama huippu suhteessa segmentin **oman** väreilyn vaiheeseen 50,1 Hz:llä.

Näin sääntö 5:n erottelu ei nojaa pelkkään portin indeksiin: jos `delay_ms - p` heiluu mutta
`refdelay_ms` pysyy vakiona, ero on SSR:n odotuksessa (B); jos molemmat pysyvät, viive on
hydraulinen (A). Optoerotinta ei tarvita eikä käytetä (tilauksen vastainen menetelmä, ks.
rekisterin vika `TILAUS-B`).

### Sääntö 12 — taajuusvirhe levittää taitosta, ja pyyhkäisy mittaa sen itse

Taitto lasketaan vakiolla `PCAP_MAINS_US = 19960` (50,1 Hz). Jos todellinen taajuus poikkeaa
tästä `df`, vaihe liukuu segmentin aikana `df * T` jaksoa: 0,1 Hz:n virhe 2,0 s:n segmentissä on
0,2 jaksoa eli 4,0 ms — taitoksen 998 µs:n binneinä **4 biniä**, ja 0,05 Hz:n virhe 2 biniä.
Hypoteesi on siis mitoiltaan tarkistettavissa, ja se tarkistetaan kahdella tavalla:

1. synteettisesti analysaattorin itsetestissä (viritetty poikkeama sisään, taitoksen huipun
   leveys ulos);
2. laitteella pyyhkäisyn omista referenssisegmenteistä: vaihe-ero jaettuna niiden aikavälillä
   antaa taajuuden tarkkuudella, joka on luokkaa 0,01 Hz 60 s:n pyyhkäisyssä — kaksi
   kertaluokkaa parempi kuin Goertzelin 0,1 Hz:n askel taajuuskaistan yli.

### Sääntö 13 — segmenttien väliin kuuluu trimmaus, ja vaa'an tila on haettava uudelleen

Segmenttien väliin ajetaan **trimmausaskel**, joka palauttaa paineen tavoitteeseen ennen
seuraavaa kaappausta: yli `target + PSWEEP_TRIM_BAR` puretaan magneettiventtiilillä pumppu
pois päältä, alle `target - PSWEEP_TRIM_BAR` pumpataan portittamatta, enintään
`PSWEEP_TRIM_MS`. Ilman tätä askelta jäännöspaine kaataa ajon `overpressure`-syyhyn — mitattu
vika, 9 hylättyä kaappausyritystä.

Kaukalovahti tarkistetaan jokaisen segmentin molemmin puolin, ei kaappaussilmukan sisällä
(sama perustelu kuin `pcap`:ssa: silmukka ei anna vuoroa). Mutta juuri siksi kaappauksen
jälkeinen tarkistus näkee lukeman aina vanhempana kuin `TRAY_STALE_MS` = 2000 ms, ja
portitettu ajo päättyi siksi joka kerta syyhyn `scalelost` (avoin vika). Korjaus: kaappauksen
jälkeen annetaan vuoro ja **odotetaan tuore lukema** enintään `TRAY_RESYNC_MS`, ja vasta sitten
tarkistetaan raja. Vaaka luetaan 50 ms tahtiin (EXPRESSO-SCALE-POLL), joten tuore lukema saapuu
yhden tahdin sisällä; jos ei saavu, syy on aito `scalelost`.

## Sääntö 9 korjattu 19.9.2026 — invariantin modulus on verkkojakso

Sääntö 9 sanoi `PSKIP_DELAY(p) = (todellinen viive + p) mod 39920 µs`, ja rekisteriin jäi
avoimeksi, ettei invariantti toteudu laitteella. Suunnittelija mittasi syyn synteettisellä
pyyhkäisyllä ennen seuraavaa laiteajoa (`/tmp`, ei repossa; iskut verkkotaajuudella, portti
näytteen indeksistä, kohina sd 0,36 bar, viive 9,00 ms, neljä siementä):

| Modulus | Invariantin hajonta, nimellinen 50,10 Hz | 0,05 Hz virhe | 0,1 Hz virhe |
|---|---|---|---|
| portin jakso 39 920 µs | 20,2 ms | 20,7 ms | 19,7 ms |
| **verkkojakso 19 960 µs** | **1,5 ms** | 2,3 ms | 4,5 ms |

Syy on portin oma rakenne: portti päästää läpi kokonaisen verkkojakson, ja pumppu iskee kerran
verkkojaksossa, joten mitattu viive siirtyy vaihesiirron mukana verkkojakson tarkkuudella, ei
portin jakson. Invariantti on siis

```text
inv = (PSKIP_DELAY(p) - p) mod 19960 µs        # vakio, kun viive on vakio
```

ja se luetaan ympyräsuureena (0,2 ms ja 19,8 ms ovat 0,4 ms päässä toisistaan). Rajaksi
`vakaa`-tuomiolle asetetaan 3,0 ms, joka on mittausten 1,5-2,3 ms yläpuolella ja 0,1 Hz:n
virheen 4,5 ms alapuolella.

### Seuraus sääntöön 5: (A):ta ja (B):tä ei erota tällä koeasetelmalla

Sama mittaus kumoaa säännön 5 toiveen. Tärykalvopumppu iskee kerran verkkojaksossa joka
tapauksessa, ja portti valitsee vain *mitkä* iskut päästetään läpi. Siksi kaikki, mitä
portti-isku-vastaus-ketjusta voi lukea, on `(A)+(B)` yhden verkkojakson tarkkuudella — ja
invariantin modulus on juuri se verkkojakso. Hydraulinen viive (A) ja SSR:n odotus (B) eivät
ole erotettavissa toisistaan ilman verkosta riippumatonta vaihereferenssiä, ja sellainen
tarkoittaisi optoerotinta, jonka tilaus sulkee pois (`TILAUS-B`).

Myöskään säännön 11 vaihereferenssi ei erota niitä: paineväreily **on** vastaus, ei sytytys,
joten sen vaihe sisältää viiveen jo valmiiksi. Suunnittelija mittasi tämänkin ennen briefin
kirjoittamista: väreilystä laskettu `refdelay` asettui nollaan (0,3 ± 1 ms), ei 9 ms:n
synteettiseen viiveeseen.

**Mitä pyyhkäisy siis päättää:** vaiheen 1c tarvitsema suure on nimenomaan invariantti — kun
portti avataan hetkellä `t`, isku saapuu anturille `inv` millisekunnin päästä verkkojakson
hilalla. (A)/(B)-jaon sijaan kirjataan invariantti ja sen hajonta, ja väreilyn vaihetta
käytetään siihen, mihin se kelpaa: verkkotaajuuden mittaukseen referenssisegmenteistä
(sääntö 12) ja tarkistukseen, että vastaus on ylipäätään lukittunut verkkoon.

## Luotaus vanhalla laitedatalla 19.9.2026 — analysaattori toimii, data ei riitä

Suunnittelija kokosi vaiheen 1b ensimmäisen laiteajon lokeista pseudopyyhkäisyn (`/tmp`, ei
repossa): referenssiksi `pcap-20260919-8bar.log` ja `-verkkotaajuus.log`, portitetuiksi neljä
kaappausta, joissa oli dataa (`p0-toisto1`, `p8000`, `p24000`, `p0-toisto2`; `p0`, `p16000` ja
`p32000` päättyivät `trayrise`- tai `overpressure`-syyhyn eivätkä sisällä näytteitä).

```text
PSKIP_INV phase_us=0      delay_ms=36.43  inv_ms=16.47  amp=0.803  conf=8.45
PSKIP_INV phase_us=8000   delay_ms=33.43  inv_ms= 5.47  amp=1.002  conf=10.37
PSKIP_INV phase_us=24000  delay_ms=26.45  inv_ms= 2.45  amp=0.919  conf=9.84
PSKIP_INV phase_us=0      delay_ms=38.42  inv_ms=18.46  amp=0.450  conf=5.16
PSWEEP_MAINS f=50.116 spread=0.048 from=ref n=2
PSWEEP_INV mean_ms=0.56 spread_ms=3.82 n=4 verdict=hajoaa
```

Kolme johtopäätöstä:

1. **Analysaattori lukee oikeaa laitedataa päästä päähän** ja antaa `conf` 5,2-10,4 eli selvästi
   yli 2,0:n rajan. Se ei ole enää vain synteettisen fikstuurin varassa.
2. **Verkkotaajuus 50,116 Hz, hajonta 0,048 Hz** kahdesta referenssisegmentistä. Tämä on
   riippumaton vahvistus vaiheen 1a tulokselle 50,1 Hz, eri menetelmällä (väreilyn hienohaku)
   kuin alkuperäinen kaistahaku.
3. **Invariantti hajoaa (3,82 ms), eikä sitä voi tästä datasta lukea** — mutta juuri siksi
   pyyhkäisy kirjoitettiin: nämä neljä kaappausta ovat eri ajoista, eri asettumisista ja eri
   paineista (amplitudi 0,45-1,00 bar). Saman vaihesiirron kaksi toistoa eroavat 2,0 ms, mikä on
   vanhan menetelmän toistettavuuden yläraja. Päätös jää laiteajolle yhdellä `psweep`-komennolla.

## Sääntö 7 korvattu 19.9.2026 — kuristinta ei käännetä käsin

**Käyttäjän huomio:** "Ei pitäisi olla ratkaiseva tekijä vaiheen testauksessa mikä paine on
tarkasti." Se pitää paikkansa, ja sääntö 7 on vanhentunut siltä osin: se kirjoitettiin, kun viisi
vaihesiirtoa ajettiin viitenä erillisenä ajona, jolloin kuristimen ajautuma ja portituksen
vaikutus menivät samaan suuntaan. Säännön 13 trimmausaskel tekee saman työn koneellisesti
jokaisen segmentin välissä, joten `phold`-tasapainotus ei ole vaiheiden 1b-1f ehto.

Paineen ainoa jäljelle jäävä vaikutus on väreilyn amplitudi, ja se osoittaa matalamman paineen
**paremmaksi** mittausolosuhteeksi: 1,788 bar vapaassa virtauksessa, 0,307 bar 7,7 barissa
(vaiheen 1a ajot 1 ja 3). Tavoitepaine valitaan siis siitä, minkä kone nykyisellä kuristimella
saavuttaa, eikä kuristinta säädetä mittausta varten. `phold` jää olemassa olevaksi työkaluksi
sitä varten, kun kuristinta halutaan säätää — ei mittausten esiehdoksi.

## Laiteajon esivalmistelu tehty 19.9.2026

Setti `20260919-psweep1` rakennettu pohjasta `20260919-pskip2` ja palautettu laitteelle:
`RESTORE_OK 20260919-psweep1 n=17`, ja `pico_dev.py verify` puhelimen omaa manifestia vasten
antoi `VERIFIED 17/17`. Manifesti haettiin puhelimelta, koska `build_set.py` ei kirjoita sitä
repoon (avoin työkaluvika).

Mittausajo itse on ajamatta: `psweep` ei tulosta mitään ilman pumppua, joten firmwaren uutta
haaraa ei voi todentaa laitteella käynnistämättä ajoa. Ajo on yksi komento:

```bash
python3 Infra/iot/expresso/pico_dev.py psweep 2000:<tavoite>:5 Infra/iot/expresso/testit/psweep-20260919-1b.log
```

Ehdot ennen ajoa: kaukalo tyhjänä, `wmax:`- tai `wrise:`-raja asetettuna (kaukalovahti ei aloita
ilman), keitin joutilaana ja käyttäjä paikalla. Ajon kesto on noin 70 s.

## Kuivaharjoitus 19.9.2026 — portin jakso on lyhyempi kuin koneen viive

Ennen laiteajoa `pressure_sweep_run` ajettiin laitosmallia vasten virtuaalikellolla
(`testit/psweep_dryrun.py`): laitos `dp/dt = 6,7*pumppu - 1,24*p` ja 70 ms:n toimilaite+anturiviive
(`testit/real_plant_sim.py:8`), väreily mitatuilla amplitudeilla, kohina sd 0,36 bar, hydraulinen
viive 9 ms. Mallin tosiarvo mitattavalle viiveelle on siis **79 ms**.

Pyyhkäisy ajautui läpi virheettä (7 segmenttiä, kaikki `reason=ok`, trimmaukset 0,5 s), mutta
invariantti hajosi 3,8 ms — ja **myös nollakohinalla**, eli syy ei ollut kohina. Taitoksen muoto
näytti sen: huippu on heti portin avautumisen jälkeen ja lähes sama joka vaihesiirrolla, eli vaste
seuraa porttia eikä yksittäistä iskua. Sama näkyy oikeassa laitedatassa: 25,1 Hz:n komponentti on
kolmessa neljästä ajosta suurempi kuin 50,1 Hz:n (0,25-0,28 bar vs. 0,16-0,20 bar).

Portin jakson pidentäminen ratkaisi asian:

| Portin jakso | `delay_ms` viidestä segmentistä | Tulkinta |
|---|---|---|
| 2 x 19,96 ms = 39,92 ms | 2,5 / 2,5 / 13,5 / 16,5 / 11,5 | kiertänyt ympäri |
| 4 x = 79,84 ms | 3,0 / 15,0 / 11,0 / 9,0 / 5,0 | yhä rajalla |
| **8 x = 159,68 ms** | **81,8 / 89,8 / 81,8 / 85,8 / 93,8** | viive luettavissa suoraan |

**Sääntö 14 — portin jakson on oltava pidempi kuin mitattava viive.** Sääntö 6 lukitsi portin
kahteen verkkojaksoon, koska tilaus sanoo "ohita joka toinen sykli". Se on oikea *ohjauskuvio*
vaiheelle 1c, mutta väärä *mittausikkuna* vaiheelle 1b: 39,92 ms on lyhyempi kuin koneen oma
70-90 ms:n viive, ja taitos alias kiertää. Mittauksessa portin jakso on siis parametri
(`mult` = montako verkkojaksoa portin jakso kattaa, pumppu päällä yhden), ja viive luetaan
`mult = 8`:lla. Kun viive tunnetaan, vaihe 1c voi palata kuvioon 1-päällä-1-pois.

Samalla korjautuu invariantin tulkinta: kun vaste seuraa porttia, oikea invariantti on
`delay_ms` sellaisenaan, ei `(delay_ms - p) mod 19960` — vaihesiirto siirtää porttia ja vastetta
yhdessä. `inv_ms` jää raportille kertomaan iskunvalintamallin lukeman, mutta tuomio luetaan
`delay_ms`:n hajonnasta.

## Tilauslisäys 19.9.2026 — taajuuden itsekorjaus ajon aikana (TILAUS-F, -G, -H)

Käyttäjä lisäsi vaatimuksen, joka koskee valmista PWM-ominaisuutta, ei mittausvaiheita: taajuus
on korjattava itse joka ajolla. Sanamuoto lainauksena `KAYTTAJAN-TIEDOT.md` luvussa 2b.

Seuraukset tämän paketin vaiheisiin:

1. **Vaihe 1a3 muuttuu luonteeltaan.** Verkkojakson yksi lähde ei ole enää vakio, jonka mittaus
   asettaa kerran, vaan ajonaikaisesti päivittyvä arvo. 1a3:n työ on sama — yksi lähde viiden
   literaalin sijaan — mutta lähteen on oltava kirjoitettavissa ajon aikana.
2. **Uusi vaihe 1g — ajonaikainen taajuus- ja vaihemittaus.** Esiuuton paineennoston aikana
   kerätään näytteet ja lasketaan Goertzel laitteella. Isäntäpuolen vastine on jo olemassa ja
   mitattu: `refine_peak` antaa 2,0 s:n ikkunasta enintään 0,07 Hz:n virheen, ja ikkuna pitenee
   `T^1,5`-suhteessa, joten 5 s:n paineennosto antaa luokkaa 0,015 Hz. Vaihe luetaan samasta
   Goertzelista (`goertzel` palauttaa nyt amplitudin ja vaiheen).
3. **Purkusykli on oma komentonsa ennen mittausta.** Venttiili päälle 0,5 s, pois 0,2 s, toisto
   kunnes paine on purettu. Tämä korvaa nykyisen trimmausaskeleen purkuhaaran *uuton alussa*;
   pyyhkäisyn segmenttien välinen trimmaus on eri asia eikä muutu.
4. **Vaiheen 1b tulos syötetään tähän.** Kuivaharjoitus osoitti, että vaste seuraa porttia ja
   viive on 70-90 ms:n luokkaa; ajonaikainen vaihelukema on vasteen vaihe, ei verkon nollakohta,
   ja se on juuri se suure, jolla ohitukset kohdistetaan (TILAUS-B).

**Vastattu 19.9.2026:** "paine on purettu" tarkoittaa, että paine on tiputettu jaksotuksen
avulla — lopetusehto on menettelyssä, ei asetetussa rajassa. Jaksotus jatkuu niin kauan kuin
paine sen ansiosta laskee, ja päättyy kun lasku yhden syklin yli jää alle `PCAP_PLATEAU_BAR`
= 0,15 bar. Ehdotukseni kiinteästä 0,3 barin rajasta ja kymmenen kierroksen katosta **ei**
toteuteta: kumpaakaan ei tilattu, ja kiinteä raja olisi juuri se keksitty luku, jota tämä
paketti välttää. Pysähtymätön jaksotus on vika, ei normaali tila.

## Avoin kohta säännössä 14 — tuomio on mallista riippuvainen

`psweep_read.py` antaa nyt sekä `inv_ms`- että `delay_ms`-hajonnan, ja `verdict` luetaan
jälkimmäisestä (sääntö 14). Kumpi on oikea, riippuu siitä, kumpi mekanismi hallitsee:

- **portti hallitsee** (paine nousee portin auki ollessa ja laskee kiinni ollessa) → oikea suure
  on `delay_ms`; näin on kuivaharjoituksessa ja kolmessa neljästä laiteajosta (25,1 Hz:n
  komponentti suurempi kuin 50,1 Hz:n);
- **iskunvalinta hallitsee** (yksittäinen läpi päässyt isku näkyy piikkinä) → oikea suure on
  `(delay_ms - p) mod 19960`; näin on analysaattorin synteettisessä fikstuurissa, jossa
  `delay_spread_ms` on 5,9 ms ja `verdict=hajoaa`, vaikka iskumallin oma invariantti on tasan
  vakio.

Analysaattori ei vielä päättele kumpi hallitsee, vaikka se laskee tarvittavat suureet
(`PSKIP_SUB` 25,1 Hz ja `PSKIP_FUND` 50,1 Hz). **Seuraava korjaus:** tuomio valitsee suureen
näiden amplitudien suhteesta ja sanoo valintansa tulosteessa. Tähän asti laiteajon lukija
(suunnittelija) lukee molemmat luvut eikä nojaa pelkkään `verdict`-kenttään.
