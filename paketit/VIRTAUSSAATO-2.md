# EXPRESSO-VIRTAUSSAATO-2 — virtaus ohjaa dutya, paine on vain katto

| Kenttä | Arvo |
|---|---|
| Tunnus | EXPRESSO-VIRTAUSSAATO-2 |
| Skooppi | infra iot |
| Kumoaa | `VIRTAUSSAATO.md` säännön 1 (kaskadi paineen kautta) |
| Näyttö | `/tmp/tshot-flow1.log`, laiteajo 18.9.2026 klo 19:5x, `tshot:25`, `fset:2.2` |
| Tila | suunniteltu, ei toteutettu |

## Miksi kaskadi kaatui — mitattu, ei päätelty

Käyttäjä avasi kuristinta kesken ajon. Säädin **toimi ja seurasi**: asetusarvo laski 10,5 barista
2,0 bariin viidessä sekunnissa (t = 17,3 → 22,3 s). Sitten se osui lattiaan eikä voinut pyytää
vähempää:

| t (s) | paine | asetusarvo | duty | virtaus |
|---|---|---|---|---|
| 17,3 | 9,6 | 10,4 | 0,69 | 1,0 |
| 19,2 | 5,9 | 5,8 | 0,76 | 5,3 |
| 22,3 | 1,9 | **2,0 (lattia)** | 0,70 | 6,1 |
| 24,8 | 1,6 | **2,0 (lattia)** | 0,84 | 8,9 |

Avatulla venttiilillä **2,0 bar päästää 6–9 g/s**. Tavoite 2,2 g/s vaatisi ~0,6 bar. Vika ei ole
`p_min`-luvussa: paineen pitäminen matalana vaatii *korkean* dutyn, ja juuri duty on se, joka
työntää veden läpi. Kaskadi pyytää väärää suuretta.

## Sääntö 1 — virtaussäädin ohjaa dutya suoraan

Uuttovaiheessa virtaus-PI antaa **pumpun dutyn** (0–1), ei paineen asetusarvoa. Duty on suure,
jolla säätimellä on auktoriteetti koko venttiilin alueella: samassa lokissa duty 0,70 → 6,1 g/s ja
duty 0,84 → 8,9 g/s, eli noin 20 g/s per yksikkö duty avatulla venttiilillä ja noin 1 g/s per
yksikkö kiristettynä. Vahvistus vaihtelee 20-kertaisesti, joten viritys tehdään avoimen pään
(suurimman vahvistuksen) mukaan.

## Sääntö 2 — paine on ylärajaohjaus (override), ei asetusarvo

`duty_cap = (p_max − paine) / p_margin`, rajattu 0–1 (`p_max = 10,5 bar`, `p_margin = 1,0 bar`);
sovellettava duty on `min(duty_virtaus, duty_cap)`. Kiristetyllä venttiilillä tämä ottaa ohjauksen
ja pitää paineen katossa; 13 bar katkaisu säilyy koskemattomana toisena verkkona.

## Sääntö 3 — mikä pysyy ennallaan

Esiuutto, painorajat, `tshot:stop`, kytkin, aikaraja, `finally`-sammutus, `fmode:`/`fset:`-komennot,
`TS`-rivin kenttäjärjestys, vaa'an vaikenemisen kolmen lukeman sääntö ja paluu paineohjaukseen
(`fmode:off` ja `TS_FLOW_OFF`) ovat ennallaan. `fsat` säilyy tahmeana (vuotava laskuri,
Schmitt-liipaisin), mutta ehto muuttuu: lippu nousee kun tavoitetta ei saavuteta **dutyn** tai
paineikatton takia.

## Sääntö 4 — hyväksyntä kattaa koko venttiilialueen

Aiempi simulaatio testasi vain kiristyspään (`k` 0,50 → 0,30 → 0,166) eikä siksi nähnyt tätä
vikaa. Uusi ajo kattaa myös avoimen pään `k = 1,5` ja `k = 3,0`, jossa tavoitteen vaatima paine on
alle baarin. Tämä on paketin tärkein rivi: **vika oli hyväksynnän aukossa, ei toteutuksessa.**

## Sääntö 5 — vaa'an nollataso riippuu virtalähteestä, virtaus ei

HX711 on ratiometrinen: se syöttää anturisillan omalla AVDD:llään ja käyttää samaa jännitettä
AD-muunnoksen referenssinä, joten **vahvistus** on ensimmäisessä kertaluvussa immuuni
syöttöjännitteen muutokselle. **Nollataso ei ole.** Se tulee tallennetuista `off_a`/`off_b`-arvoista
(`pico/scale_cal.json`, ei nollausta käynnistyksessä — `main.py:49` vain luo `Scale()`:n) ja
etuasteen omasta biasista, ja siihen vaikuttavat maavirrat: keittimen ollessa päällä mukana ovat
SSR:n kytkennät ja lämmitysrele, joka sykkii uuttosilmukassa 150 ms välein.

Seuraukset ovat eri suureille erilaiset, ja tämä on koko säännön ydin:

- **Virtaus on immuuni vakiosiirtymälle.** Se on painon derivaatta 1 s ikkunassa, ja vakio
  derivoituu nollaksi. Säätö ei siis ajaudu väärään työpisteeseen siksi, että nollataso on eri.
- **Askel ei ole vakio.** Jos virtatila vaihtuu kesken uuton, siirtymä näkyy yhden sekunnin ajan
  tekovirtauksena, jonka suuruus on `siirtymä / 1 s` — 5 g siirtymä antaa noin 5 g/s piikin, ja
  säädin reagoi siihen kuin todelliseen virtaukseen. Mediaani-3 ei poista sitä, koska askel ei ole
  yksittäinen piikki vaan pysyvä taso.
- **Absoluuttiset rajat siirtyvät mukana.** `wmax` ja tyhjän kaukalon lukema on luettava siinä
  virtatilassa, jossa uutto ajetaan.

**Mitattu 19.9.2026, A/B/A.** Vaa'an lukema virran ollessa päällä 460,1 g → pois 489,8 g →
takaisin päällä 488,4 g. Ensimmäinen hyppy oli **vettä**, ei siirtymää: magneettiventtiili tyhjentää
ryhmän kaukaloon jokaisen uuton jälkeen, eikä lukema palannut takaisin virran palatessa. Vierekkäiset
lukemat virtakytkimen molemmin puolin ovat 489,8 (pois) ja 488,4 (päällä), eli **siirtymä on noin
1,4 g** ja sekin sisältää tippumisen ja driftin. Vaaka saa käyttöjännitteensä Picolta, joka käy
puhelimen USB:stä, eikä keittimen virtatila siis juuri vaikuta siihen.

**Paineanturi sen sijaan saa virtansa keittimeltä:** levossa se lukee **1,4 bar virran ollessa pois**
ja ~0,0 bar päällä. Virrattomana lukema on roskaa, ja esiuutto päättyy heti, koska tavoite näyttää
jo täyttyvän — juuri niin kuin `tshot:5` teki virran ollessa pois (`PI_END` ilman yhtään
lokiriviä).

Säännöt: keittimen virtatilaa ei vaihdeta kesken uuton (1,4 g askel on sekunnin ajan 1,4 g/s
tekovirtausta, ja paineen lukema hyppää samalla käyttökelvottomaksi); painorajat asetetaan ajon
omassa virtatilassa; kaukalon lukemaa ei tulkita uuton jälkeen ennen kuin ryhmä on tyhjentynyt.

## Laitteistotesti

Sama kuin ennen: `tshot:25`, käyttäjä liikuttaa venttiiliä vapaasti molempiin suuntiin. Ehto
läpäisylle on käyttäjän oma: virtaus pysyy 2,2 g/s:ssa koko liikuttelun ajan, paitsi kun venttiili
on niin tiukalla ettei pumppu yllä siihen — silloin `fsat=1`. Kaukalo tyhjennetään ennen ajoa.
