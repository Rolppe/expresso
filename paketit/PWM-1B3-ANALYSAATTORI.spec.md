# PWM-1B3-ANALYSAATTORI — spec

Suunnittelijan kirjoittama sisältö. Toteuttaja ei päätä näistä mitään.

## 1. Tuloste

```text
PSKIP phase_us=<p> n=<n> fs=<x.x> Hz
PSKIP_FOLD <40 arvoa, bar, kolme desimaalia, välilyönnein>
PSKIP_DELAY <x.x> ms conf=<x.xx> amp=<x.xxx> bar
PSKIP_ASYM <x.xx>
PSKIP_SUB 25.1 Hz amp=<x.xxx> bar
PSKIP_FUND 50.1 Hz amp=<x.xxx> bar
```

`conf` alle 2,0: tulosta lisäksi rivi `PSKIP_UNDECIDED conf alle 2.0 — ajo ei riitä päätökseen`.
Jos lokin `PCAP_START` sanoo `gate=off` tai riviltä puuttuu `phase_us`, tulosta
`PSKIP_NOGATE tämä loki ei ole portitettu ajo` ja palauta epänolla paluuarvo.

## 2. Laskenta

1. Näytteet ja `dur_us` luetaan `mains_freq.parse_log`:lla (tuo se samasta hakemistosta; älä
   kopioi jäsennintä). Todellinen näytetaajuus `fs = n / (dur_us * 1e-6)`, ei nimellinen 1000 Hz.
2. `bar = gain * (raw * RAW_TO_BAR_GAIN + RAW_TO_BAR_OFFSET) + offset`, jossa `gain` ja `offset`
   luetaan `PCAP_START`-riviltä. Puuttuessa `gain=1.0`, `offset=0.0`.
3. **Jäännös**: `res[i] = bar[i] - boxcar(bar, L)[i]`, jossa `L = round(period_us * fs / 1e6)`
   (portin jakso näytteinä, ≈ 40). Boxcar on keskitetty; reunoilta pudotetaan `L//2` näytettä
   molemmista päistä. Perustelu on paketin sääntö 8: boxcar nollaa tasan portin taajuuden ja sen
   kerrannaiset, joten erotus säilyttää ne ja poistaa kaiken hitaamman. Älä käytä lineaarista
   trendinpoistoa — paine laskee portitetussa ajossa eksponentiaalisesti.
4. **Taitto**: näytteen `i` vaihe portissa on `((i * 1000 + phase_us) % period_us) / period_us`.
   Tässä käytetään **nimellistä 1000 µs:n näyteväliä**, ei `fs`:stä johdettua — firmware laskee
   portin tilan samasta järjestysnumerosta (paketin sääntö 6), joten taiton on käytettävä sen
   omaa aikakäsitystä. Spektriamplitudit (kohta 6) käyttävät sen sijaan todellista `fs`:ää.
   40 biniä, bin = `int(vaihe * 40)`; kunkin binin arvo on sen jäännösten keskiarvo.
5. **Viive ja luotettavuus**: `PSKIP_DELAY` on suurimman binin keskikohta millisekunteina
   (`(bin + 0.5) * period_us / 40 / 1000`). `amp = max(fold) - min(fold)`.
   `conf = amp / (2 * sd(res) / sqrt(näytteitä per bin))`.
6. `PSKIP_SUB` ja `PSKIP_FUND` ovat `mains_freq.goertzel_amp`:lla lasketut amplitudit taajuuksilla
   `1e6 / period_us` ja `1e6 / (period_us / 2)`, todellisella `fs`:llä, jäännöksestä `res`.

`PSKIP_ASYM` on taitoksen puoliskojen ero: `rms(fold[b] - fold[b+20]) / amp`, b = 0…19. Se
tulostetaan diagnostiikkana, **eikä siihen liitetä kynnystä** — ks. kohta 5.

`PSKIP_DELAY` on portin nousevan reunan ja vasteen huipun väli, siis paketin sääntö 5:n yhdistelmä
(A)+(B) — ei puhdas hydraulinen viive. Tiedoston docstring sanoo tämän.

## 3. Itsetesti (`--selftest`)

Synteettinen kaappaus, `random.Random(seed)`:

- `fs = 1000` Hz, `n = 1500`, verkkojakso `T = 19960` µs, portin jakso `2T = 39920` µs.
- Isku alkaa hetkillä `t_k = k*T + mains_off`, ja se pääsee läpi vain jos `((t_k + phase_us) % 2T)
  < T`. Läpi päässyt isku lisää paineeseen pulssin `0.30 * exp(-(t - t_k - D) / 3 ms)`, kun
  `t >= t_k + D`. 0,30 bar on mitattu väreily 7,7 barissa.
- Pohja: `7.7 bar` laskien eksponentiaalisesti 0,8 bar kaappauksen yli (aikavakio 0,81 s).
- Kohina: gaussinen, `sd = 0.36` bar (mitattu raakahajonta 7,69 barissa).
- Sarja muunnetaan raakaluvuiksi kääntämällä tehdaskaava, `gain=1.0`, `offset=-0.99`, ja
  kirjoitetaan `PCAP_START`/`PCAP`/`PCAP_END`-muotoon väliaikaistiedostoon, joka luetaan takaisin.

Väitteet:

1. `D` arvoilla 3, 9 ja 15 ms, `mains_off=0`, `phase_us=0`, siemenet 1-3: palautettu viive on
   2,0 ms sisällä oikeasta, ja `conf >= 2.0`.
2. `mains_off = 7000` µs, `D = 3` ms: palautettu viive on 2,0 ms sisällä arvosta 10 ms. Tämä
   todentaa, että mitattu suure on yhdistelmä (A)+(B), ei pelkkä hydraulinen viive.
3. Toistettavuus: `D = 9` ms siemenillä 1, 7 ja 11 antaa saman binin (erot enintään yksi
   bin, 998 µs). Verrokkiväitettä "portittamaton data tunnistetaan taitoksesta" **ei ole** — ks.
   kohta 5, se on mitattu mahdottomaksi tällä kohinatasolla.
4. `gain=1.0, offset=-0.99` -kaappauksen binien keskiarvo ei saa siirtyä offsetin verran:
   jäännös on offsetista riippumaton (boxcar poistaa DC:n). Sama data `offset=0.0`:lla antaa
   saman `PSKIP_DELAY`:n.

Tulosta lopuksi `RESULT: <n> failed` ja palauta epänolla, jos `n > 0` — sama muoto kuin
`mains_freq.py:selftest`.

## 4. `mains_freq.py`:n DRIFT-korjaus

`drift()` lukee tällä hetkellä `RAW_TO_BAR_GAIN/OFFSET`-tehdaskaavan eikä anturin elävää
kalibrointia, joten sen `alku`- ja `loppu`-arvot lukevat noin barin liian korkeina (avoin vika,
rekisteri 19.9.2026). Korjaus: `parse_log` palauttaa myös `PCAP_START`-riviltä luetut `gain` ja
`offset`, `drift()` ottaa ne argumentteina (oletukset 1.0 ja 0.0), ja `print_result` lisää
`DRIFT`-riville merkinnän `(cal=raw)`, kun lokilla ei ole kalibrointia. Ajautuma itse on erotus
eikä muutu — vanhat mittaukset pysyvät pätevinä, ja `--selftest`:n nykyinen DRIFT-väite pysyy
vihreänä.

## 4b. Invariantti, jota laiteajo mittaa

Taitto lasketaan portin nousevasta reunasta, joten vaihesiirto siirtää raportoitua viivettä tasan
itsensä verran: **mitattu viive = (todellinen viive + `phase_us`) mod `period_us`**. Suunnittelija
todensi tämän fikstuurilla: `D` = 9 ms, `phase_us` = 10 000 µs → 19,5 ms.

Laiteajossa juuri tämän invariantin säilyminen on paketin säännön 5 koe: jos
`mitattu − phase_us` pysyy vakiona vaihesiirtoa muutettaessa, viive on hydraulinen (A); jos se
hyppii noin 20 ms:n portain, SSR:n nollaylityskvantisointi (B) hallitsee.

## 5. Mitattu rajoitus — taitos ei erota portitettua ajoa portittamattomasta

Suunnittelija ajoi synteettisen kokeen ennen tämän briefin lähettämistä (generaattori on
`testit/pskip_fixture.py`, samat parametrit kuin kohdassa 3). Tulos:

| Suure | Portitettu | Portittamaton |
|---|---|---|
| `PSKIP_DELAY` | 3,5 / 9,5 / 15,5 ms (`D` = 3 / 9 / 15) | 9,5 ms (merkityksetön) |
| `amp` | 0,37-0,49 bar | 0,40-0,47 bar |
| `PSKIP_ASYM` (rms) | 0,24-0,30 | 0,17-0,21 |
| `SUB/FUND` | 0,48 / 4,18 / 0,48 | 0,26 |

Kaksi johtopäätöstä, jotka sitovat toteutusta:

1. **Viiveen lukeminen on vakaa**: huipun paikka osuu joka kerta puolen binin päähän oikeasta
   (taitos raportoi binin keskikohdan), kohinalla sd 0,36 bar ja 1,5 s kaappauksella.
2. **Portituksen toteaminen aaltomuodosta ei ole vakaa.** `PSKIP_ASYM` erottaa tapaukset vain
   0,21 vs 0,24, ja `SUB/FUND` heittelee 0,26:n ja 4,18:n välillä, koska residuaalin pituus ei ole
   kokonainen määrä jaksoja. Kumpaakaan ei siis käytetä päätökseen, ja alkuperäinen väite
   "portittamaton data antaa `conf < 2.0`" on kumottu — `conf` mittaa huipun erottumista
   kohinasta, ei portitusta.

Portituksen toteaminen jää siksi lokin otsikon varaan (`gate=on`), ja siitä analysaattori pitää
kiinni tiukasti: `PSKIP_NOGATE` ja epänolla paluuarvo, jos otsikko ei sano portitusta.
