# EXPRESSO-TURVAKATO — miksi turvaominaisuus katosi matkan varrella

| Kenttä | Arvo |
|---|---|
| Tunnus | EXPRESSO-TURVAKATO |
| Skooppi | infra expresso |
| Tila | **selvitys tehty 21.9.2026 (koodista luettu, ei laitteella ajettu)** — korjaukset avoinna, ks. "Korjauslista" |
| Kiireellisyys | korkea: käyttäjä nimesi tämän mahdollisesti hengenvaaralliseksi luokaksi |

## Laukaisija (19.9.2026)

Suunnittelija ajoi `phold 60` kahdesti peräkkäin vaiheen 1b kuristimen tasapainottamiseksi.
Käyttäjä joutui **katkaisemaan virran keittimestä**, koska tippakaukalo oli tulvimassa yli.

Kaukalon painoraja oli koodissa olemassa ja toimiva — mutta vain testiuuton polulla:

- `functions.py:152-181`, ehto `if limit_weight:`; `limit_weight=True` tulee vain `tshot`-polulta.
- Kommentti sanoo rajauksen ääneen: "Test shots only: stop before the drip tray overflows".
- Käytössä olevat arvot ovat tiedossa: `wrise:250`, `wmax:470` ilman ritilää, `720` ritilän kanssa
  (`KEHITYSYHTEYS.md:690-691`).

Uusi komento `phold` (PWM-1B1, 19.9.2026) peri keskeytysehtonsa `pcap`:lta — kytkimet, `dev_safe`,
abort, ylipaine — koska sen spec sanoi "keskeytysehdot ovat `pcap`:n ehdot". `pcap` on sekuntien
ajo, joten painoa ei ollut siellä koskaan tarvittu. `phold` on 120 sekuntiin asti pumppaava ajo.
Holdout ajoi funktion läpi valelaitteilla, mutta ei voinut keksiä ehtoa, jota spec ei nimennyt.

## Käyttäjän kanta (19.9.2026)

> "Pelkkä säiliö ongelman korjaus ei ratkaise asiaa. Kyse on siitä että turva ominaisuus hukkui
> matkan varrella. Tämmöisillä asioilla voi olla hengenvaarallinen vaikutus jossakin tapauksissa.
> Ongelma pitää perusteellisesti selvittää mutta selvitys tehdään myöhemmin."

Välitön korjaus (tiukka vaakasääntö komennoille `phold` ja `pcap`) on paketti
`EXPRESSO-KAUKALOVAHTI`. **Se ei ole tämä paketti, eikä se sulje tätä.**

## Raja, joka ei saa liikkua (käyttäjä, 19.9.2026)

> "Huomioi että vaaka sääntö ei koske omaa ajoa vaan testejä"

Vaakavahti koskee **kehitys- ja testikomentoja** (`phold`, `pcap`, `tshot`). Käyttäjän oma uutto
uuttokytkimellä ei saa katketa painoon: vaa'alla on silloin kuppi, ja kupin paino on uuton
tarkoitus eikä vika. Tämä on jo nykyisen koodin rajaus (`limit_weight=False` kytkinpolulla,
`functions.py:152-154`), ja se säilyy. Selvityksen kohta 2 ei saa muuttaa sitä "yhtenäistämällä"
rajat toimilaitteen viereen ilman tätä erottelua — polkujen ero on tässä tarkoitettu, toisin kuin
`phold`:n tapauksessa, jossa se oli unohdus.

## Mitä selvitys kattaa, kun se ajetaan

1. **Inventaario.** Mitkä turvarajat firmwaressa on, millä poluilla kukin on voimassa, ja mikä
   polku jää kunkin ulkopuolelle. Tunnetut: ylipaine 13,0 bar (`functions.py:149-151`), `pcap`:n
   11,0 bar, kaukalon `wmax`/`wrise` (vain `tshot`), vahtikoira 8 s, `dev_safe`, kytkinehdot.
   Odotus: kaukalo ei ole ainoa, joka on sidottu yhteen polkuun.
2. **Miksi raja sidottiin polkuun eikä toimilaitteeseen.** Kaukalovahti on `run_shot`:n sisällä,
   ei pumpun kytkennän yhteydessä. Kysymys: kuuluuko jokainen raja sen toimilaitteen viereen,
   jota se suojaa, niin ettei uusi komento voi ohittaa sitä unohtamalla.
3. **Miksi uusi komento sai periä ehtonsa lyhyemmältä komennolta.** Spec sanoi "kuten `pcap`",
   ja se hyväksyttiin. Kysymys prosessille: milloin ehtojen periminen on kielletty, ja kuka
   tarkistaa sen briefin kirjoittajan sijaan.
4. **Mitä muuta on kadonnut samalla tavalla.** Käy läpi `HISTORIA.md` ja `KEHITYSYHTEYS.md`
   niiden kohtien varalta, joissa turvaraja on lisätty yhteen polkuun ja polkuja on sen jälkeen
   tullut lisää.
5. **Hengenvaarallisuuden arvio.** Käyttäjä nimesi luokan; selvitys nimeää konkreettiset tapaukset
   (kuuma vesi, höyry, paine, sähkö) ja sen, mikä kussakin pysäyttää ajon tänään.

## Ensimmäinen askel

`/pura infra expresso`, valitse tämä paketti. Selvitys alkaa kohdan 1 inventaariosta, ja se
tehdään lukemalla koodi — ei muistista eikä tästä tiedostosta, joka on vain laukaisijan kirjaus.


## Selvitys 21.9.2026 — tulokset

Tehty lukemalla koodi (`pico/`), `HISTORIA.md`, `KEHITYSYHTEYS.md`, paketit ja git-historia.
Mitään ei ajettu laitteella. Merkintä **[todennettu]** = pääistunto tarkisti rivin itse lähteestä;
muut ovat ali-agentin koodiluvun tuloksia rivinumeroineen.

### Kohta 1 — inventaario: missä rajat ovat voimassa

| Toimilaitteen päälle kytkentä | Ylipaine | Kaukalo | Aikaraja | Lämpöraja | Kytkin/dev_safe/abort |
|---|---|---|---|---|---|
| `run_shot` pumppu `functions.py:198,241,243` | 13,0 bar (vain pumpun ollessa päällä) | vain `tshot` | vain `tshot` | – | kahvikytkinpolulla vain kytkin |
| `run_shot` lämmitin `:223` (1/3 teho) | – | – | vain `tshot` | **ei** | kuten yllä |
| `pcal` `:418,427,446` | 12,0 | **ei** | 90 s | lämmitin pois `:353` | kyllä |
| `pcap` `:794` | 11,0 (1 raakanäyte) | kyllä | kyllä | **lämmitin lukittuu** | kyllä |
| `psweep` `:927`, trimmaus `:876,896` | **ei trimmauksessa** [todennettu] | kyllä | kyllä | lukittuu | kyllä; `:896` kytkee pumpun takaisin myös keskeytyksen jälkeen [todennettu] |
| `pstep` `:1021,1045` | 11,0 | vain alussa ja lopussa | 14 s | lukittuu | ~1 s välein |
| `pgap` `:1169,1205` | 11,0 | vain alussa ja lopussa | **ei ylärajaa** (`commands.py:140` väli vain alarajattu) [todennettu] | lukittuu | ~1 s; sarjaportti sokea |
| `plen` `:1315,1353` | 11,0 | vain alussa ja lopussa | ≈58 s | lukittuu | ~1 s |
| `mcal` `:1452` | **ei** [todennettu] | **ei** | 5 s | lukittuu | kyllä |
| `phold` `:1523` | 11,0 | kyllä | 120 s | lukittuu | kyllä |
| `fast_heatup` `:1598–1635` | – | – | lämmitin **ei** | kynnykset 85/110/115 °C | **ei** |
| kuumavesikytkin `main.py:285-304` | **ei** | **ei** | **ei** | **ei** (lämmitin 100 %) | vain kytkin [todennettu] |
| `backflush.py:75,88` | 10 bar/pulssi | – | 4 s/pulssi | termostaatti | **ei** pulssien aikana |
| termostaatti `classes.py:1253` | – | – | – | kyllä | dev_safe pääsilmukassa |

Polusta riippumattomat suojat ovat vain kolme: kaatumisen `finally` (`main.py:383-389`),
`dev_safe` ajojen välissä (`main.py:171-175`) ja vahtikoira 8 s, joka havaitsee vain silmukan,
joka ei anna vuoroa.

Muut havainnot:

- **`fast_heatup` kaatuu:** `functions.py:1599` kutsuu `asyncio`:ta, jota tiedosto ei tuo
  (vain `import os`). Pumppu on juuri kytketty päälle. [todennettu]
- **`bt:` ei ole rajattu** (`commands.py:334-339`) [todennettu]. Anturivian turva palauttaa
  200 °C (`classes.py:1386-1392`); jos tavoite on ≥ 200 °C, vika jättää lämmittimen päälle.
- **Paineanturi nollassa → kaikki ylipainerajat sokeita;** `run_shot`:ssa säädin ajaa pumppua
  täysillä (`classes.py:913`), kahvikytkinpolulla niin kauan kuin kytkin on päällä.
- **Uskottava mutta väärä lämpölukema** (anturi irti kattilasta): ei uskottavuus- eikä
  lämpenemisnopeusrajaa; `fast_heatup` lämmittäisi rajatta.
- **Lämmitin lukittuu testikomentojen ajaksi:** termostaatti ei aja, joten lämmitin pysyy
  viimeisessä tilassaan (`phold` 120 s, `pgap` rajatta).
- **Ctrl-C:** `async_main` sammuttaa releet vain `except Exception`:ssa; `KeyboardInterrupt`
  voi jättää lämmittimen päälle (`KEHITYSYHTEYS.md:175-178`, suojana vain ohje).
- **`MemoryError`** otetaan kiinni ja ajoa jatketaan `phold`/`pstep`/`pgap`/`plen`/`pvent`:ssä.
- Tarkistamatta: välittääkö MicroPythonin `asyncio.gather` tehtävän poikkeuksen `asyncio.run`:lle
  (kaatumis-`finally` riippuu siitä); relepinnien tila vahtikoiranollauksen aikana; ajetaanko
  BLE-komennot kiireisten silmukoiden aikana; mekaanisen ylipaineventtiilin olemassaolo.

### Kohta 2 — miksi rajat ovat polussa eivätkä toimilaitteessa

Jokainen raja on komennon funktion sisällä. `PumpPressureController._set` (`classes.py:883`) ja
suorat `RELAY_*.value(1)`-kutsut ovat vartioimattomia. Siksi uusi komento voi ohittaa rajan
unohtamalla sen, ja jokainen uusi pumppupolku on toteuttanut ylipainerajan uudelleen omalla
arvollaan (13,0 / 12,0 / 11,0 / 10 bar / ei mitään).

### Kohta 3 — miksi ehdot saatiin periä

Kaava: spec määrittää uuden komennon turvaehdot viittaamalla sisarkomentoon ("kuten `pcap`",
"sama kuin X", "sellaisenaan kuten X"). Briefin lukulista rajataan X:ään, ja hyväksyntätokenit
tarkistavat X:n ehdot, joten aukko kulkee jokaisen tarkistuskerroksen läpi.

- `PWM-1B1-PHOLD.spec.md:32-34` "Keskeytysehdot ovat `pcap`:n ehdot"; brief: "`pcap:` on tarkka
  malli joka askeleelle"; lukulista ei kattanut `run_shot`/`tshot`:ia.
- Sama mekanismi toimi oikeaan suuntaan 1B4:lle ja 1B6:lle (perivät vartioidun `pcap`:n).
- `PWM-1G-TAAJUUSKALIBROINTI.spec.md:33` (`mcal`, `cf1358b`, 3,5 h kaukalovahdin jälkeen) listasi
  omat ehtonsa ilman painoa ja ylipainetta.
- `pstep`/`pgap`/`plen`/`pvent` (`28dff60`, 20.9.) kirjoitettiin istunnossa ilman speciä.

Kukaan ei tarkista perintää: rd-, pura- ja pakkaa-taidoissa eikä agenteissa ole sääntöä, joka
kieltäisi "ehdot kuten X" tai vaatisi listaamaan turvarajat eksplisiittisesti.

### Kohta 4 — mitä muuta on kadonnut samalla tavalla

1. Kaukaloraja 18.9. (`tshot`) → `pcal`, `pcap`, `phold` ilman sitä; korjaus kattoi `phold`/`pcap`,
   `mcal`/`pcal` yhä ulkona.
2. Ylipaine 17.9. vain `run_shot`:iin → jokainen polku toteutti omansa; `mcal` ja `psweep`-trimmaus
   ilman. Kopioitu `RELAY_SOLENOID.value(0)` `pgap`:n purussa → 11,38 bar (`HISTORIA.md:34-38`).
3. Vaa'an vanhenemisvahti: ensin vain `tshot`, sitten `phold`/`pcap`.
4. Kaukalovahdin poikkeus "kaappaus enintään 2500 ms" venyi `pstep`/`pgap`/`plen`:iin, jotka
   pumppaavat 14–58 s ja tarkistavat vain alussa ja lopussa. 20.9. ylivuoto tapahtui näillä.
5. `wrise` ajokohtainen → 4 × 250 g → vesivahinko 20.9.
6. Ristiriita: `HISTORIA.md:104-105` sanoo `weight_limit: 720.0` asetetuksi 19.9.,
   `REKISTERI.md` sanoo `wmax` asettamatta 20.9.; nollautumisen syy selittämättä.
7. `wmax`/`wrise` eivät aluksi tallentuneet (korjattu devsafe12).
8. `mcal`:ia käytettiin purkukomentona 20.9. → `pvent` tehtiin jälkikäteen.

### Kohta 5 — hengenvaaralliset tapaukset ja mikä ne pysäyttää tänään

| Vaara | Mikä pysäyttää tänään | Aukko |
|---|---|---|
| Kuuma vesi yli kaukalon / palovamma | `phold`/`pcap`/`psweep`: kaukalovahti | `pstep`/`pgap`/`plen`: vain kytkin, 11 bar, BLE-stop; kuumavesikytkin: vain kytkimen vapautus |
| Höyry, kattilan ylipaine | höyrytila vain termostaatilla (125 °C) | ei kattilapaineen valvontaa; kommentti `functions.py:146-148` mainitsee ~14 bar lämpölaajenemisesta; mekaaninen varoventtiili varmistamatta |
| Pumpun ylipaine | 10–13 bar polusta riippuen | `mcal`, `psweep`-trimmaus ilman; anturi nollassa → kaikki sokeita |
| Lämmittimen karkaaminen / sähkö | termostaatti + anturivika → 200 °C | `bt:` ≥ 200 rajaamatta; väärä mutta uskottava lukema; kuumavesi 100 % rajatta; `fast_heatup`; lukittu lämmitin testeissä; Ctrl-C |
| Kaatuminen | `finally`-lohkot + `main.py:383-389` | kiinni otetut poikkeukset jatkavat; `gather`-käytös tarkistamatta |

### claude siirto -skoopin tila suhteessa juurisyyhyn (21.9.2026)

- Mikään valmis työ ei korjaa juurisyytä. KAUKALOVAHTI (`1ab54da`) korjaa oireen;
  SIIRTO-HUKKAKIRJAUS (`2da3d8d`) kirjaa menetykset jälkikäteen; SIIRTO-OMIN-PAIN-TIIVISTETTY koskee
  vain pakkausmuistioita; OHJEVAHTI (`dfd7933`) valvoo käyttäjän ohjeita, ei specien turvaehtoja;
  SIIRTO-MALLINEUTRAALI ei liity.
- Syyhyn osuisivat: tämä paketti, `TILAUS-INVARIANTIT.md` ja `SIIRTO-VAATIMUS-KATOAA`
  (`claude/siirto/REKISTERI.md`). Kaikki avoinna.
- Havainto: OHJEVAHTI-hook on committaamattomana `.claude/settings.json`:ssa, vaikka
  `OHJEVAHTI.md:7` sanoo "asentamatta"; `OHJEKIRJA.json` on tyhjä, joten hook ei tarkista mitään.

## Korjauslista (ehdotus 21.9.2026 — järjestys ja rajaus käyttäjän päätettäviä)

Rajaus säilyy: käyttäjän oma uutto kahvikytkimellä ei katkea painoon (ks. yllä). Kuumavesikytkin
on samoin käyttäjän polku; sille ehdotetaan vain aika- ja lämpörajaa, ei painorajaa.

1. **EXPRESSO-TURVA-TOIMILAITE** (juurisyy, koodi): rajat pumpun/lämmittimen kytkennän viereen
   yhteen kohtaan (vartioitu `pump_on`/`heater_on`), joka tarkistaa polusta riippumatta ylipaineen,
   aikarajan ja `dev_safe`:n; testikomentojen kaukalovahti ajon aikana eikä vain alussa ja lopussa.
   Testi: jokainen `RELAY_PUMP.value(1)` / `RELAY_HEATER.value(1)` lähteessä kulkee vartion kautta
   (koneellinen grep-tarkistus).
   **Tehty koodissa 22.9.2026, ei flashattu:** `pico/relayguard.py`; `BrewData.get_relays()` antaa
   pumpun ja lämmittimen `GuardedRelay`-olioina (raakapinnejä ei pidetä oliossa). Rajat: `dev_safe`;
   > 13,0 bar kolmesti peräkkäin (vartio lukee ADC:n itse); pumpun ajo > 180 s (ajo päättyy 5 s
   tauolla, jonka aikana pumppua ei pyydetä); lämmitin ≥ 160 °C tai lukema > 10 s vanha; vartion
   virhe → kaikki pois. Vartio kysyy `value(1)`:ssä ja `machine.Timer`-kyselyssä 100 ms välein
   (toimii myös vuoroa antamattomissa silmukoissa). Rajat ovat löysempiä kuin polkujen omat, joten
   ne ovat perälauta eivätkä muuta nykyisiä ajoja. Kaukalo ei ole vartiossa (raja yllä); se
   tarkistetaan `pstep`/`pgap`/`plen`:ssä ~1 s välein `tray_guard_poll`:lla, joka lukee vaa'an
   itse. Todiste: `testit/turva_toimilaite_smoke.py` 34/34 ok, mutaatiossa 6 FAIL; vanhat 9 smokea
   0 failed. Laitteella tarkistettavaa: `Timer(-1)` käynnistyy, `GUARD_TRIP`-rivit, normaali uutto,
   kuumavesi ja backflush eivät laukaise vartiota.
2. **EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO** — **tehty koodissa 21.9.2026** (ei flashattu):
   `wmax` pakollinen, ajo ei ala täydellä kaukalolla, `mcal` ja `tshot` mukana. `pcal` jää ulkopuolelle
   (käyttäjän päätös 7.10.2026). Avoinna: `pstep`/`pgap`/`plen`:n tarkistus ajon aikana (kuuluu kohtaan 1).
3. **Pikakorjaukset** (pienet, erillinen paketti): `fast_heatup` `asyncio`-kaatuminen; `bt:`-raja
   (esim. ≤ 150 °C); `pgap`-välin yläraja; `psweep`-trimmauksen ylipaineraja ja `:896`
   keskeytyksen jälkeinen pumppu; `mcal`:n ylipaineraja; lämmitin pois testikomentojen ajaksi.
   **Tehty koodissa 21.9.2026 (EXPRESSO-TURVA-PIKAKORJAUKSET), ei flashattu:**
   - `fast_heatup(utime, asyncio, brew_data)` saa `asyncio`:n parametrina; `finally` sammuttaa
     pumpun, venttiilin ja lämmittimen. (Aika-, dev_safe- ja uskottavuusraja puuttuu yhä → kohdat 1 ja 5.)
   - Asetuslämpötila ≤ 150 °C (`classes.py` `SETPOINT_MAX_C`, tarkistus `set_brew_temperature`- ja
     `set_steam_temperature`-asettajissa, joten `bt:`, BLE ja `settings.txt` kulkevat sen kautta).
     Sivuvaikutus: `settings.txt`, jossa arvo > 150, kaatuu `load_settings`:n `ValueError`-haaraan,
     joka poistaa tiedoston → oletukset, myös `wmax` pois (testikomennot eivät silloin käynnisty).
   - `pgap`: väli ≤ 2000 ms (`PGAP_SPACING_MAX_MS`) ja koko ajon katto 120 s (`PGAP_RUN_MAX_MS`,
     `reason=timeout`), tarkistetaan ajossa.
   - `_psweep_trim`: raakanäytteen ylipaineraja 11,0 bar; pumppu kytketään takaisin vain, kun ajo
     jatkuu (`ok`/`timeout`).
   - `mcal`: raakanäytteen ylipaineraja 11,0 bar kaappaussilmukassa.
   - `main.py`: kaikki 10 testikomentoa kulkevat `dev_run`:n kautta, joka sammuttaa lämmittimen ensin.
   - Todiste: `testit/turva_pika_smoke.py` 26/26 ok; vanhat `phold`, `mcal`, `psweep`, `psweep_mult`,
     `tray_guard`, `tray_total`, `pskip_gate`, `scale_rate` -smoket 0 failed.
4. **Kuumavesikytkimen aika- ja lämpöraja** — käyttäjän päätös, koska polku on käyttäjän oma.
5. **Anturien uskottavuus:** paineanturi nollassa / lämpölukema ei nouse lämmittäessä → pysäytys.
   **Tehty koodissa 22.9.2026 (EXPRESSO-ANTURIUSKOTTAVUUS), ei flashattu:** vartiossa. Paineanturin
   raakalukema < -1,5 bar kolmesti → pumppu pois. Lämmitin 120 s päälläoloaikaa > 5 °C alle
   tavoitteen, pumppu pois, nousu < 2 °C → lämmitin pois uudelleenkäynnistykseen asti. Ei
   havaittavissa: anturi jumissa uskottavassa 0 barissa. Todiste `turva_toimilaite_smoke.py` D1–D9.
6. **Prosessi (skooppi `claude siirto`):** spec ei saa määrittää turvaehtoja viittauksella
   ("kuten X"); jokaisen toimilaitetta ohjaavan komennon specissä on eksplisiittinen turvarajataulu,
   ja tarkistus kaataa briefin, josta se puuttuu. Kytkeytyy `SIIRTO-VAATIMUS-KATOAA`:han ja
   `TILAUS-INVARIANTIT`:iin.
7. **Laitteelta tarkistettavat:** mekaaninen varoventtiili; `asyncio.gather`-poikkeuksen kulku;
   relepinnien tila nollauksessa; `wmax`-nollautumisen syy.
