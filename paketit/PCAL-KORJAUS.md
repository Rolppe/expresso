# EXPRESSO-PCAL-KORJAUS — kalibrointivelho: ensin tavoite, sitten pito

| Kenttä | Arvo |
|---|---|
| Tunnus | EXPRESSO-PCAL-KORJAUS |
| Skooppi | infra iot |
| Havainnot | käyttäjä 19.9.2026: paine ei ehtinyt tasaantua ennen mittausikkunaa; velho vaikenee sarjalinkille |
| Tila | suunniteltu, ei toteutettu |

## Vika 1 — mittausikkuna ei odota tavoitteen saavuttamista

`pressure_calibration_run` (`pico/functions.py:303-354`) avaa kiinteän 10 s ikkunan heti
käynnistyksestä ja keskiarvoistaa raaka-arvon sekunneista 5–10 **riippumatta siitä, onko tavoite
saavutettu**. Jos paine nousee hitaasti — ilmaa järjestelmässä, kylmä kone, tiukka kuristin — piste
tallentuu nousevasta paineesta, ja kalibrointi vääristyy juuri siinä suunnassa, jota kukaan ei
huomaa: lukema on sitä pienempi mitä hitaammin paine nousi.

Oikea järjestys on kaksivaiheinen:

1. **Asettuminen:** aja säädintä kunnes `|p − tavoite| <= 0,15 bar` yhtäjaksoisesti 1,0 s.
   Aikaraja 30 s; jos se ylittyy, vaihe päättyy syyhyn `not settled` eikä pistettä tallenneta.
2. **Pito:** vasta sitten 10 s pito, jonka **koko ajalta** raaka-arvo keskiarvoistetaan.

Käyttäjä lukee referenssimittarin pidon aikana, ja pito alkaa vasta kun neula on paikallaan — eli
lukuhetki ja mittaushetki ovat sama asia, mikä ne eivät nyt ole.

## Vika 1b — lähestyminen tehdään yhdellä syklillä, vaikka ne ovat eri tehtäviä

Käyttäjän vaatimus 19.9.2026: tavoitteeseen ajetaan kahdessa vaiheessa, ja mittauslaskuri alkaa
vasta kun paine on saavutettu.

1. **Karkea lähestyminen:** täysi pumpun sykli kunnes `p >= tavoite - 0,5 bar`.
2. **Hieno lähestyminen:** tästä eteenpäin pieni sykli — yksi pumpun isku (`step_ms = 17 ms`, yksi
   60 Hz verkkojakso) kerrallaan pidennetyssä ikkunassa, jolloin paine nousee portaittain eikä
   ryntää tavoitteen yli.
3. **Laskuri alkaa** vasta kun `|p - tavoite| <= 0,15 bar` on pitänyt yhtäjaksoisesti 1,0 s.
4. **Ylitys estää laskurin.** Jos `p > tavoite + 0,15 bar`, laskuri ei käynnisty eikä pistettä
   tallenneta. Suljetussa järjestelmässä ylitystä ei voi peruuttaa — pumppu vain lisää — joten ajo
   päättyy syyhyn `overshoot`, järjestelmä puretaan venttiilin kautta ja vaihe ajetaan uudelleen.
   Hienon syklin tarkoitus on tehdä tästä harvinaista.

## Mittaus — mikä sykli pitää paineen tasaisimpana

Hienon syklin ikkunapituus on **mitattava, ei valittava**. Ajetaan 30 s pito sekä 2 bar että 8 bar
tavoitteella ikkunapituuksilla 100, 200, 500 ja 1000 ms (yksi isku ikkunaa kohden), ja kirjataan
koneen oman lukeman keskihajonta ja min/max kummallakin tasolla. Valitaan pienin hajonta.

Tämän hetken vertailukohta ilman hienoa sykliä (`window_ms = 100`, oletusviritys): 5 bar
tavoitteella hajonta **0,13 bar** (4,70–5,30), 10 bar tavoitteella **0,39 bar** (9,30–11,10).

**Avoin kysymys, joka mittauksen on ratkaistava:** käyttäjän mekaaninen mittari näytti samassa
ajossa vain noin 0,2 barin liikettä, kun anturi näytti 1,8 baria. Joko anturin lukema on nopeaa
kohinaa, jota vaimennettu mittari ei näytä, tai todellinen paine todella heiluu ja mittari vaimentaa
sen. Ikkunapituuden kasvattaminen erottaa nämä: jos hajonta ei pienene ikkunaa pidennettäessä, kyse
on anturin kohinasta eikä pumpun iskuista, ja silloin kalibroinnin tarkkuutta parannetaan
keskiarvoistamalla pidempään eikä sykliä muuttamalla.

## Vika 2 — velho ei kerro sarjalinkille mitään

Koko polulla ei ole yhtään `print`iä: tila kulkee vain BLE:llä sovellukseen. Sarjalinkiltä ajettuna
komento kuittaa `CMD_OK` ja sen jälkeen ei tiedetä, ajettiinko vaihe, saavutettiinko tavoite vai
tallentuiko piste. Lisätään kolme riviä:

- `PCAL_START <stage> target=<bar>`
- `PCAL_SETTLED <stage> t=<s>` tai `PCAL_ABORT <stage> reason=<syy>`
- `PCAL_END <stage> raw=<arvo> n=<näytteet> reason=<syy|ok>`

Lisäksi `pcal:save` tulostaa `PCAL_SAVE gain=<g> offset=<o>` ja `pcal:st` tulostaa nykyisen tilan ja
tallennetut pisteet, jotta kalibroinnin voi ajaa ja todentaa ilman sovellusta.

## Vika 3 — nollaa ei saa lepolukemasta

Suljetussa järjestelmässä lepopaine on mitä tahansa: firmwaren oma kommentti kertoo lämpölaajenemisen
vievän tyhjäkäynnillä ~14 bariin (`functions.py:147`). Nolla otetaan purkamalla: lämmitin pois,
magneettiventtiiliä syklitetään 0,5 s päällä / 0,5 s pois kunnes **raaka-arvo lakkaa muuttumasta**
(muutos alle kynnyksen kolmella peräkkäisellä syklillä), ja vasta sitten keskiarvoistetaan.
Komento `pzero:` tekee tämän ja tallentaa tuloksen offsetiksi; kerroin jää kalibrointivelhon
vastuulle. Nykyinen uuton jälkeinen purku pysähtyy 1,5 bariin (`functions.py:285`) eikä kelpaa
nollaksi, koska sekin kynnys luetaan kalibroidusta lukemasta.

## Sääntö — kalibrointi ajetaan nollavirtauksessa

Keittimen anturi on vesilinjassa pumpun jälkeen, referenssimittari kahvassa ryhmän jälkeen. Niiden
välissä on painehäviö aina kun vettä virtaa, ja häviö kasvaa virtauksen mukana. Kalibrointi ajetaan
siksi **kuristin kiinni**: nollavirtauksessa paine on sama joka puolella piiriä. Tämä on
menettelysääntö, ei koodimuutos, mutta se kuuluu tähän pakettiin, koska ilman sitä koodin
korjaaminen ei riitä.

## Hyväksyntä

Isäntätestit `testit/shot_test.py`-penkissä, ei laitteistoa: valeanturi, jonka paine nousee
tavoitteeseen annetulla viiveellä. Väitteet: (1) hitaasti nouseva paine ei tallenna pistettä ennen
asettumista, (2) 30 s aikarajan ylitys päättyy `not settled` eikä tallenna pistettä, (3) asettuneen
pidon keskiarvo vastaa asetettua painetta, (4) `pzero:` palauttaa vakaan raaka-arvon vasta kun
syklitys ei enää muuta sitä, (5) `PCAL_*`-rivit tulostuvat ja sisältävät nimetyt kentät.
