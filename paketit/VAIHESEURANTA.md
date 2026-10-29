# VAIHESEURANTA — vaiheen seuranta pumpun ohjauksen jokaisessa vaiheessa (TILAUS-K, TILAUS-L)

VAATIMUS: TILAUS-K, TILAUS-L, TILAUS-B, TILAUS-I, TILAUS-J

Tilaus: `KAYTTAJAN-TIEDOT.md` luku 2c (24.9.2026). Neljä vaihetta: (1) nosto täydellä syklillä,
syklistä kerätään tietoa; (2) esiuuttopaineen viimeinen nosto ja pito tauoilla, joiden kohdistus
yksi kerrallaan antaa vaihedataa; (3) nosto uuttopaineeseen, kello synkronoidaan; (4) uuttopaineen
tarkennus kuten (2). Pienin vaimennus 10 ms, vaikuttaa 20 ms, 50 kohtaa sekunnissa.

## Suunnitelma (24.9.2026)

1. Taukojen vaihepyyhkäisy tasanteella — tehty, alla.
2. Säätimen askel 20 ms:n jaksoon ja kelloon sidotuksi (nyt `PumpPressureController` 17 ms,
   60 Hz -oletus; mitattu verkko 50,0 Hz), hienosäätö delta-sigmana (1 % / 2 s).
3. Tauot vaihemittauksena kellon korjaukseen vaiheissa 2 ja 4; väreily-lock-in vaiheissa 1 ja 3.
4. "Korkein tunnettu piste ilman yliampumista" opitaan edellisistä ajoista.

## Askel 1: vaihepyyhkäisy, laitteella 24.9.2026 (vsweep1)

Komento `vsweep:<reps>` (`pico/functions.py` `pressure_phase_sweep_run`): purku, nousu tasanteeseen,
kellon lukko (25 ikkunaa), sitten 22 ehtoa × reps: 10 ms tauko 0–19 ms kellon reunasta, tyhjä
vertailu ja 20 ms tauko; jokaisen tauon välissä yksi kelloa päivittävä I/Q-ikkuna. Vaste =
keskipaine 30–130 ms tauon alusta − 200 ms:n trendistä jatkettu perustaso; tyhjien keskiarvo
vähennetään. Analyysi `testit/vsweep_analyysi.py`, isäntätesti `testit/vsweep_smoke.py`
(nollaylitys- ja vapaavaihe-SSR-mallit, sarjaviive, pysähdykset).

Ajo `testit/vsweep-20260924-a.log` (klamp ensin, tasanne 7,82 bar, lukko 4,0 s, sd 314 us, 66
taukoa, 50,0066 Hz):

- **Isku poistuu, kun 10 ms tauko alkaa 8,5–18,7 ms kellon reunasta** (yksittäisistä tauoista,
  väärin luokiteltuja 2/60). Lohkon leveys 10,2 ms ≈ puolijakso. Lohkossa vaste −0,61…−0,83 bar
  (20 ms tauko −0,85), sen ulkopuolella −0,03…+0,22 bar; välitasoja 0/20 → **SSR on
  nollaylitystyyppiä** (avoin asia 15: päätelty paineesta, tyyppikilpi yhä tarkistamatta) ja
  **puolijaksot erottuvat** (avoin asia 13).
- **Yksittäinen 10 ms tauko on kaksiarvoinen vaiheilmaisin**, jonka raja on verkon nollakohta
  (kellon reuna + ~8,5 ms ja + ~18,7 ms). Tämä on TILAUS-K:n vaiheen 2 perusta: kun tauko
  sijoitetaan lohkon reunan lähelle, "poistiko iskun" kertoo, kummalla puolella rajaa kello on.
- **Ajoitusvika (korjattu, ei vielä flashattu):** tauot myöhästyivät käskystä 1,4–18,6 ms (mediaani
  2,0), koska tavoite laskettiin vanhasta aikaleimasta sarjatulostuksen jälkeen ja 200 näytteen
  summat laskettiin ennen ajoitusta. Tulos pelastui, koska toteutunut kohta (`act_us`) kirjattiin.
  Korjaus: tuore aikaleima, summat tauon käynnistyksen jälkeen, ja vahti `VSWEEP_LATE_MAX_US`
  300 us: myöhässä oleva tauko siirtyy seuraavaan jaksoon (`VSWEEP_END late=`). Tuotannossa sama
  vahti on pakollinen, koska väärään kohtaan osuva tauko ei poista iskua.
- Kello: 22/66 taukoa kellon lukkorajan (2,5 sd < 1000 us) yli, sd 390–470 us; yksi I/Q-ikkuna
  taukojen välissä pitää sd:n ~390 us:ssa.

Seuraavaksi (käyttäjän valinta): tarkennettu pyyhkäisy reunojen ympäriltä (esim. 0,2 ms askelin
7,5–9,5 ja 17,7–19,7 ms) korjatulla ajoituksella, josta reunan tarkkuus ja sen käyttö
vaihemittauksena; tai askel 2.

## Esiuutto 2,5 bar vaiheilla 1–2 (EXPRESSO-ESIUUTTO-25BAR, 24.9.2026) — isännällä vihreä, ei flashattu

VAATIMUS: TILAUS-K, TILAUS-L, TILAUS-G, TILAUS-B, TILAUS-I, TILAUS-J

`pico/functions.py` `pre_infusion_phased`, valinta `pim:1` (RAM, oletus 0 = vanha PI 17 ms ikkunalla;
`TS_START` tulostaa `pim=`). Vanha polku säilyy lähtötasomittausta varten.

- **Vaihe 1:** täysi sykli, kunnes jaksokeskipaine + nousunopeus (100 ms) × opittu jälkinousu `coast_s`
  ≥ tavoite − 0,3 bar ja paine ≥ ½ tavoite (huuhtelusääntö). `coast_s` opitaan joka ajosta
  (`EU_COAST`, EMA 0,5, oletus 0,3 s varovainen; RAM). Nousun I/Q-ikkunat lokiin `gate=-1`, eivät opeta
  kelloa (päätös 24.9.2026).
- **Vaihe 2:** yksi päätöskohta jaksossa, kellon reuna + 13,6 ms (vsweep-a:n lohkon 8,5–18,7 ms keskikohta,
  ±5 ms). Delta-sigma PI:n tehosta (sama kp/ki/ff kuin ennen, ramppi 2 bar/s) päättää iskun. Poisto =
  10 ms tauko, kun 2,5·sd < 4 ms; muuten 20 ms tauko (poistaa nollaylitys-SSR:llä yhden iskun vaiheesta
  riippumatta). Pidon ikkunat opettavat kellon porteilla. Rele kytketään heti päätöskohdassa, laskenta
  vasta sen jälkeen; myöhästymisvahti 300 us (`late`), pysähdysten ohittamat jaksot `miss`.
- **Loki:** `EU_START`, `EU <t_ms> <p> <sp> <rele> <d> <vaihe> sd_us= rm= sk10= sk20= late= w= f=` 100 ms
  välein, `VKELLO`, `EU_CUT`, `EU_COAST`, `EU_HOLD`, `EU_END` (yliampuma = huippu nousussa ja pidon
  ensimmäisen 1 s; pidon keskiarvo/sd; iskut, poistot, tauot, kello, `win_low` = liian heikot ikkunat).
- **Testit:** `testit/esiuutto_smoke.py` 21/21 (iskumalli nollaylitys-SSR, viive 40 ms; laitteen iskut =
  mallin iskut, tauot passiivisen puolijakson keskellä 4,7/5,0 ms, pysähdyksissä 0/69 väärin, yliampuma
  ≤ 1 isku, huuhtelu ei katko). Analyysi `testit/esiuutto_analyysi.py <loki...>` (PI- ja EU-rivit samoin
  mittarein). Muut smoket vihreät. `shot_test.py` kaatuu jo HEADissa (`BrewData` ilman `relay_guard`ia,
  valelaite vanhentunut TURVA-TOIMILAITTEEN jälkeen) — ei tämän muutoksen vika, korjaamatta.
- **Avoin laitteella:** väreilyn amplitudi 2,5 barissa harvoilla iskuilla (jos < AMP_MIN 0,1 → `win_low`,
  kello ei opi, tauot pysyvät 20 ms:ssa); lohkon 8,5–18,7 ms paikka 2,5 barissa (mitattu 7,8 barissa;
  väreilyn viive riippuu paineesta); todellinen jälkinousu. Taukojen käyttö vaihemittauksena
  (suunnitelman kohta 3) tekemättä.

### Laitteella 24.9.2026 (esiu1, klamp-c, esiuutto-a/b/c) ja korjaus esiu2 (isännällä)

- **a, pim:0 (lähtötaso, vanha PI):** paine nousi vasta 3,3 s:n kohdalla ja jäi 1,5–2,0 bariin; ramppi
  nollautui aina paineen pudotessa alle 1,5 barin (`continuous_error`), pitoajastin ei koskaan käynnistynyt.
- **b/c, pim:1:** 10 ms tauot toimivat 2,5 barissa: kello lukittui (sd 317–329 us, 40–41 opettavaa
  ikkunaa, amplitudi 0,12–0,54, `win_low` 0–1), sk10 79–84 / sk20 0–1, paine pysyi teholla d ≈ 0,3
  (ilman poistoja tasanne 6,9 bar). Vika säädössä: yliampuma 1,09–1,27 bar (c: 3,4–3,6 bar 0,8 s).
  Juurisyyt: (1) yksittäisen jakson keskiarvo heiluu täytössä ±0,5 bar → c:n katkaisu piikistä 1,37 bar
  (rate 16,5 bar/s, todellinen ~0,3 bar); (2) integraali kertyi rampin viiveestä ja purkautui
  yliampumana; (3) pito alkoi rampin päästyä tavoitteeseen, paineen ollessa 1,34/1,09 bar
  (menetelmäohjeen vastaisesti); (4) jälkinousu opittiin piikistä (rise 0 → coast_s puolittui).
  `late` 17–20, `miss` 7 per ajo: pysähdyksiä on, vahti toimi.
- **Korjaus (esiu2, isännällä vihreä, ei flashattu):** päätökset 5 jakson keskiarvosta `p5`, nousunopeus
  kahdesta peräkkäisestä 100 ms:n keskiarvosta; pito alkaa vasta, kun ramppi on tavoitteessa ja
  p5 ≥ tavoite − 0,1; integraali ennen pitoa vain, kun |virhe| < 0,3 bar; ei jälkinousun oppia, jos
  huippu ≤ katkaisu (`learn=0`). EU-rivillä `p5=`, EU_END `over` p5:stä. Smoke tapaus 6 (täyttö 2,4 s,
  jaksokohina sd 0,3): vanha koodi kaatuu 2/4, uusi 25/25.
- Laitteen yhteysvika toistui: ensimmäinen `shot` ajoi tyhjään (hubi irtosi 0,6 s laturisyklin jälkeen,
  logcat 13:23:29), uusinta onnistui.
- **esiu2 laitteella 24.9.2026 (VERIFIED 19/19, klamp-d tasanne 9,28 bar, esiuutto-d/e):** yliampuma p5:stä
  −0,02 / +0,30 bar (b/c: +1,1…+1,3), pito alkoi paineessa 2,48 / 2,57 bar, pidon keskiarvo 2,49 / 2,53 bar,
  jaksohajonta 0,25 / 0,27 bar; jälkinousu opittiin (0,30 → 0,206 → 0,145, learn=1), sk10 79–104, kello sd
  317–324 us. Jäljellä: pidossa hidas heilunta p5 2,2–2,8 bar (~2–3 s jakso), ja lepopaine näyttää
  −0,7…−0,9 bar ajon alussa (nollapiste, avoin asia 25) — absoluuttinen 2,5 bar on yhtä epävarma kuin se.

### Pidon heilunta (EXPRESSO-ESIUUTTO-PITO, 25.9.2026) — isännällä vihreä, ei flashattu

- **"Hidas heilunta" ei ole hidas.** d/e-pidon p5-sarjan (100 ms, ei päällekkäin) autokorrelaatio yhden
  rivin viiveellä on 0,18 / 0,05: vaihtelu on pääosin alle 200 ms:n mittakaavassa, ja 0,5 s:n liukuva
  keskiarvo heiluu vain sd 0,09–0,11 bar. 2–3 s:n aalto oli harvan kuvaajan näköharha. Iskuja
  100 ms:n ikkunassa oli laitteella 0–4 (sd 0,9), vaikka duty oli 0,29–0,33 (odotus 1–2).
- **Sovitus:** `esiuutto_smoke` Plant, jaksokohina `cyc_sd` 0,25 ja asyncio-pysähdykset 0,8 % vuoroista
  (5–15 ms) toistavat laitteen pidon: p5 sd 0,157 (laite 0,16–0,17), iskuvaihtelu 1,0 (0,9), late 18
  (13–18), jaksohajonta 0,24 (0,25–0,27), duty 0,27 (0,29–0,33). Iskukoko 0,2 bar ja vuoto 0,8 s
  pysyivät ennallaan.
- **PI/ff ei ole syy:** sovitetussa mallissa todellisen paineen (Plant.p) hajonta pidossa on 0,17–0,18 bar
  kaikilla kokeilluilla kp 0,05–0,2 / ki 0,1–0,3 ja myös, kun P-termi lasketaan p5:stä; ilman pysähdyksiä
  0,067. Viritystä ei muutettu.
- **Juurisyy, korjattu:** myöhästynyt päätös (5–10 ms) siirsi seuraavan päätöskohdan jaksolla eteenpäin,
  koska vähimmäisväli `EU_MIN_SLOT_US` mitattiin myöhästyneestä ajasta `t`. Jakso jäi ilman päätöstä,
  rele pysyi päällä, ja isku meni läpi laskematta; delta-sigma ja `strokes` eivät tienneet siitä
  (mallissa 14–24 laskematonta iskua ajossa, `miss` laskee vain yli T/2). Nyt väli mitataan
  nimelliseen kohtaan, jolle päätös kuului. Tulos mallissa: todellinen hajonta 0,18 → 0,11 bar,
  p5 sd 0,17 → 0,12, laskemattomat iskut −2…0.
- **Kokeiltu, jätetty pois:** myöhästymisrajan löysennys 10 ms tauoille (lohkon loppu 18,7 ms − 13,6 −
  2,5 sd − marginaali) antoi 0,098–0,106, siemenvaihtelun sisällä. `EU_YIELD_US` 9–12 ms antaisi
  0,07–0,09, mutta nälkiinnyttäisi vaa'an (kaukalovahti katkaisee 2 s hiljaisuuden jälkeen): vaatii
  laitteen tehtäväajoitusten mittauksen ensin.
- **Testit:** `esiuutto_smoke.py` 27/27, uusi tapaus 7 (sovitettu malli, 3 siementä: laitteen iskut =
  mallin iskut ±4) kaatuu vanhalla koodilla (−22, −22, −15). Muut `functions`-smoket 11/11 vihreät.
- **Laitteella todennettava (flash + 2 ajoa pim:1):** EU_END `strokes` vs. toteutunut, pidon p5 sd
  (odotus ~0,12), ja käyttäjän mittarilukema esiuuttopaineessa (nollapiste, avoin asia 25).

### Laitteella 25.9.2026 (esiupito1, esiuutto-20260925-a/b) ja loppunoston korjaus esiupito2 (isännällä)

- **esiupito1 (VERIFIED 19/19, klamp-20260925-a 7,77 bar):** pito vain 2,5 s (flash palautti `pit`:n
  oletukseen; b-ajon `pit:6` epäonnistui `Connection refused`, ja ajo käynnistettiin silti — oma
  virhe). Pidon p5 sd 0,114 / 0,093 (d/e 0,17 / 0,16), iskuja 100 ms:ssä 1–2 (d/e 0–4), keskiarvo
  2,52 / 2,57, yliampuma +0,11 / +0,22. Ennusteen mukainen, mutta vain 1,5 s mitattavaa pitoa/ajo.
- **Mittari (käyttäjä, b-ajo):** pito ~2,5 bar (anturi 2,52–2,57), uutto ~7–8 bar (anturi 7,5–8).
  Anturi on työalueella oikeassa; levon −0,4…−0,8 bar on alapään virhe (avoin asia 25).
- **Uutto 8 bar (a/b):** alussa ~1 bar pudotuksia (6,8), ylitys enintään 8,3 (ikkunahuippu 8,8),
  b:ssä ~1 s 7,4–7,6 hitaan integraalin takia — EXPRESSO-PAINESAADIN-HEILUNTA, ei tämä paketti.
- **Laitteen iskumalli nousun datasta:** G = rate / (1 − p·ff/tavoite) → iskukoko 0,09–0,11 bar,
  vuoto τ 1,5–1,8 s (e-ajo 0,18 / 0,82 poikkeaa). Smoken oletus 0,2 / 0,8 s on liian nopea; sovitettu
  malli (0,1 / 1,6 s, täyttö 1 s, kohina 0,25, pysähdykset 0,8 %) toistaa katkaisun, jälkinousun
  oppimisen (0,19 → 0,14 → 0,10; laite 0,185 → 0,128) ja katkaisusta pitoon 1,0–1,4 s.
- **Notkahdus katkaisun jälkeen:** p5:ssä 0,2–0,3 bar, mutta todellinen paine (malli ilman kohinaa)
  notkahtaa vain ~0,08 bar; loput on 100 ms keskiarvon viivettä ja kohinaa. Varsinainen vika: ramppi
  2 bar/s tarvitsee 0,36–0,43 dutya pidon ff:n päälle, ja pelkkä P-termi jätti paineen ~0,4–0,6 bar
  rampin alle ~1 s ajaksi.
- **Korjaus (esiupito2):** rampin myötäkytkentä `ff·sp/tavoite + 2 bar/s / G`, G saman ajon
  katkaisuhetken noususta (ei, jos nousu < `EU_RATE_MIN`; yläraja 0,5 dutya), vain kun p5 < asetusarvo
  ja loppuen `EU_RAMP_LEAD_S` 0,1 s ennen tavoitetta. Rajaamaton versio lisäsi ylityksiä (sovitettu
  malli 48 ajoa: > 0,3 bar 17 vs. vanha 4), koska jälkinousun edellä oleva paine sai silti lisädutya.
  Rajattuna: ylitys ka 0,18 / max 0,41 (vanha 0,19 / 0,42), katkaisusta pitoon 0,91 s (1,17), p5-
  notkahdus 0,08 (0,14). Kokeiltu ja hylätty: rampin alku ennustetusta huipusta (hyppää tavoitteeseen,
  kun ennuste ylittää sen → ei myötäkytkentää), ennakko 0,2 s (hyöty katoaa).
- **Testit:** `esiuutto_smoke.py` 32/32; tapaus 8 (sovitettu malli ilman kohinaa, 2 ajoa: paine ≤ 0,3
  bar rampin alla, katkaisusta pitoon ≤ 1,1 s, ylitys ≤ 0,2) kaatuu vanhalla (0,48 / 0,39 bar, 1628 /
  1446 ms). Viimeiset 0,1–0,2 bar vievät hitaalla vuodolla ~0,4 s, eikä sitä kiirehditä.

### Pidon ff tämän ajon noususta (EXPRESSO-ESIUUTTO-FF, 26.9.2026) — isännällä kesken, ei flashattu

- **Laite (a/b/c 25.9.):** pidon toteutunut duty lämmin 0,29–0,37, kylmä 0,13–0,16 (opittu ff 0,30 → c +0,44
  bar). Katkaisun rate a 4,66 @1,31, b 3,85 @1,52, c 6,88 @1,34 bar → tau_obs 1,35 / 1,84 / 2,23 s.
- **τ ei tule kahdesta nousupisteestä:** nousu kiihtyy täytön jälkeen (c: 1,5 → 2,8 → 4,0 → 4,9 bar/s
  100 ms:n välein), joten kahden pisteen τ olisi negatiivinen; vuoto muuttaa nousua ~0,5 bar/s, kohina ~1,5.
  POIKKEAA paketin alkuperäisestä kuvauksesta tästä syystä.
- **Koodi:** katkaisussa G = rate + p5/`EU_TAU_S` (1,8 s), ff = tavoite/(G·τ) (0,05–0,9), ramp_ff = 2/G;
  hidas nousu → opittu ff. Loki `EU_CUT g= ff=`, `EU_END tau_obs=`. Laitteen luvuilla ff c 0,18 (tarve 0,15),
  a 0,26 (0,33–0,37), b 0,30 (0,29).
- **Lukkiutuminen (korjattu):** liian pieni ff → P-termi jätti paineen ~0,8 bar alle, integraali ei kertynyt
  ±0,3 bar kaistan ulkopuolella, pito ei alkanut eikä ajo päättynyt (koskee laitetta: kylmä→lämmin vanhalla
  opitulla ff:llä). Nyt kaista rajaa integraalia vain rampin noustessa (`sp < target`). Löytyi, kun kaksi
  smoke-ajoa pyöri ~80 min ilman aikarajaa; `run()` rajaa nyt jokaisen ajon 30 s:iin (lukkiutuminen → kaatuu).
- **Testit:** smoke tapaus 9 (kylmä 0,15/2,2 opitulla 0,31, lämmin 0,1/1,6 opitulla 0,15; kohinaton + 3
  kohinaista). Uusi koodi 6 failed: 8 katkaisusta pitoon 1249/1206 ms (HEAD 1026, raja 1100) — regressio;
  9 kylmä pidon alku 0,08 (0,05), kohina 0,11 (0,1), yliampuma 0,39 (0,3); 9 lämmin kohina ff −0,14 (±0,08).
  HEAD-koodi 10 failed: kylmä pidon alku +0,25…0,30, yliampuma 0,41–0,69; lämmin lukkiutuu.

### Loppulähestyminen (EXPRESSO-ESIUUTTO-FF jatko, 26.9.2026) — isännällä 3 kohinaista kaatuu, ei flashattu

- **Tapauksen 8 regression syy:** katkaisun ff 0,27 (tarve 0,31; mallin tau 1,6 vs. `EU_TAU_S` 1,8). Rampin
  myötäkytkentä loppui rampin mukaan (sp ≥ tavoite − 0,2), paine jäi ~0,25 bar alle, ja loppu vei pelkällä
  P-termillä (0,2/bar → ~0,25 bar/s) 0,4–0,6 s. Vanha opittu ff 0,30 osui sattumalta tarpeeseen.
- **Korjaus:** (1) rampin myötäkytkentä loppuu p5:n mukaan (p5 < tavoite − 2 bar/s · `EU_RAMP_LEAD_S`), myös
  rampin päätyttyä; (2) loppulähestymisessä ja pidon 1. sekunnissa `EU_KP_TAIL` 0,4 ja integraali ×3
  (`EU_KI_TAIL_X`, `EU_TAIL_HOLD_MS`): ff:n virhe korjautuu ennen pitoa eikä sen aikana.
- **Pyyhkäisy (lämmin 0,1/1,6 ja kylmä 0,15/2,2; 6 kohinatonta vaihetta + 24 kohinaista siementä; HEAD → uusi):**
  katkaisusta pitoon lämmin 1202 → 692 ms, kylmä 795 → 662; tapaus 8 ×12 max 1291 → 717 (> 1100: 8 → 0);
  pidon 2 s poikkeama kylmä kohinaton > 0,05: 6 → 0, kylmä kohinainen > 0,1: 6 → 1, lämmin kohinainen 2 → 5
  (max 0,18 → 0,15); todellinen paine (kohinaton mallipaine) katkaisusta pidon 1. sekuntiin, kylmä kohina max 0,58 → 0,44,
  lämmin 0,24 → 0,30. Katkaisun ff ei muuttunut: lämmin kohina keskivirhe −0,08, sd 0,05 (15/24 yli ±0,08).
- **Kokeiltu, hylätty:** ff:n G pidemmästä regressioikkunasta (10–25 jaksoa, myös paineen ylityksestä 0,3/0,6 bar
  alkaen): kohina ei pienene (sd 0,04–0,10), ja ikkuna ulottuu täyttöön → kylmä ff +0,06…+0,15. Nousu täytöstä
  katkaisuun on ~0,3 s, joten tietoa ei ole enempää. Rampin P 0,3/0,4: rampin viive ei pienene.
- **Testit:** `esiuutto_smoke.py` 3 failed (HEAD 6), kaikki 3 siemenen kohinaisia: 9 kylmä kohina yliampuma
  (p5-maksimi, kohinan sd p5:ssä ~0,11 → luonnollinen max ~0,28 rajan 0,3 alla), 9 kylmä kohina pidon alku 0,12
  yhdellä siemenellä, 9 lämmin kohina ff −0,12/−0,13 (katkaisun valintavinouma: kohinan nostama nousunopeus
  laukaisee katkaisun). Muut `functions`-smoket 11/11 vihreät.
- **Laitteella todennettava:** EU_CUT ff vs. pidon toteutunut duty, katkaisusta pitoon (odotus ~0,7 s), pidon
  alun keskiarvo, lämmin ja kylmä kuristin.

### Laitteella 26.9.2026 (esiuff1, esiuutto-20260926-a/b, pim:1, pit:6) — ff nousunopeudesta yliarvioi tarpeen

- **esiuff1 (VERIFIED 19/19, functions.py = 54e3ac9).** `pit:6` ja ajo b kaatuivat ensin `Connection refused`
  (silta ei valmis heti edellisen komennon laturisyklin jälkeen), uusinta onnistui; pumppu ei käynnistynyt
  epäonnistuneella yrityksellä.
- **a (kylmä, päivän 1. ajo):** täyttö ~5,5 s, nousu hidas (katkaisun rate 2,39 @1,55) → ff 0,43; pidon duty
  laski 0,45 → 0,08–0,11 (tarve ~0,10). Pidon 2 ensimmäisen s keskiarvo 2,73, p5 enintään 2,96, over 0,34.
  tshot:10 loppui pitoon (2,7 s, reason=stop), uutto ei alkanut. tau_obs 2,55.
- **b (heti perään):** katkaisun rate 5,48 @1,44 → ff 0,22; katkaisusta pitoon 712 ms (malli ~0,7 s ✓);
  pidon duty 1 s jälkeen ka 0,125 (tarve ~0,09); 2 s keskiarvo 2,67, sen jälkeen 2,5–2,6; over 0,25,
  hold_sd 0,132, uutto ajettu. tau_obs 2,94.
- **Tulkinta:** tarve oli tänään 0,09–0,10, 25.9. lämpimänä 0,29–0,37 ja kylmänä 0,15; nousunopeus ei seuraa
  sitä (a:n hidas nousu → suurin ff, pienin tarve). Nousu kertoo pumpun ja järjestelmän joustosta (ilma,
  täyttö), pito kuristimen vuodosta, ja kuristin voi olla eri asennossa päivästä toiseen. Yliarvio maksaa
  enemmän kuin aliarvio: vuodon tau ~2,5–3 s → 0,2 bar ylitys purkautuu vasta sekunneissa, mutta pumppu
  nostaa vajetta 5–10 bar/s.

### Vuoto edellisestä pidosta ja D-termi (EXPRESSO-ESIUUTTO-FF, 26.9.2026) — isännällä 2 kaatuu, ei flashattu

- **Syy (a-ajo):** tarpeella 0,10 ja nousulla 2,39 @1,55 vuodon tau ≈ (25 − 1,55)/2,39 ≈ 10 s: kuristin oli lähes
  kiinni. Nousu näkee pumpun G:n, ei vuotoa, joten `EU_TAU_S` 1,8 ei voi toimia kaikilla kuristimen asennoilla.
- **Koodi:** ff = min(nousun arvio, edellisen pidon tarve × G_edellinen / G_nyt); ilman edellistä (käynnistys, pito < 3 s)
  `EU_FF_FIRST_X` 0,6 × nousun arvio. Pidon tarve opitaan asettuneesta pidosta (`EU_LEARN_SKIP_MS` 2 s jälkeen, ≥ 1 s),
  ei 5 s:n liukuvasta keskiarvosta (b: jäi 0,14:ään, tarve 0,09). G talteen `eu_g_pre`. Käyttäjän pyynnöstä D-termi
  `EU_KD` 0,05 × (rampin nopeus − nousunopeus). Loki `EU_CUT ... ffr= ffc=`.
- **Pyyhkäisy (lämmin/kylmä/kiinni 0,05 / 10 s, 1. ajo + kaikki parit, 8 kohinaista siementä):** oma tila ja
  lämmin↔kylmä pidon 2 s keskiarvo ±0,05 kohinattomana; kuristimen sulkeminen ajojen välissä yliarvioi (+0,14…+0,17
  ff, pidon alku +0,2–0,3) — vain edellinen pito kertoo vuodon. D-termi: kohinaisissa ylitys max 0,64 → 0,53
  (KD 0,05), keskiarvo 0,195 → 0,184; KD 0,1 pahentaa (0,84). Hyöty pieni, laite ratkaisee.
- **Testit:** tapaus 9 kirjoitettu uudelleen (1. ajo ei yli tarpeen, parit, kiinni oppii, kohinaiset parit).
  2 failed: 8 ajo 1 rampin viive 0,36 (1. ajo alakanttiin → ramppi jää enemmän), 9 kohina lämmin → kylmä
  +0,17/+0,18 kahdella siemenellä (KD 0: +0,12/+0,13). Muut smoket vihreät.
- **Laiteajot vain 2,5 barin pidolla, kunnes esiuutto on hyväksytty (käyttäjä 26.9.2026).**

### Laitteella 26.9.2026 klo 12.3x (esiuff2, vain pito: `pico_dev.py hold 5`) — edellisen pidon tieto toimii

- **esiuff2 (VERIFIED 19/19, functions.py = 8f2ceb6).** `pit` on rajattu 6 s:iin (commands.py), joten tshot ei
  yksin estä uuttoa: uusi `pico_dev.py hold <s> [loki]` lähettää `tshot:40` ja `tshot:stop` <s> s EU_HOLDin jälkeen
  (heti, jos uuton TS-rivi tulee). Lokit c (a2, `shot 8`, pito 2,3 s), d (b2) ja e (c2); `shot`/`hold` liittää
  olemassa olevaan tiedostoon, joten kirjain on oltava uusi.
- **c (1. ajo flashin jälkeen):** ff 0,21 (0,6 × 0,35), pito vain 2,3 s → ei asettunut, G ei talteen.
- **d (1. ajon polku uudelleen):** ff 0,23 (0,6 × 0,38), tarve 0,05 (tau_obs 19 s: kuristin lähes kiinni),
  2 s keskiarvo 2,73, over 0,48. Kerroin 0,6 ei riitä, kun kuristin on näin kiinni.
- **e (edellisen pidon tieto):** ffc 0,03 → ff 0,05 (alaraja), katkaisusta pitoon 475 ms, **2 s keskiarvo 2,526**,
  hold_sd 0,083 (paras tähän asti), over 0,17, opittu 0,06.
- **Johtopäätös:** vuodon tieto edellisestä pidosta toimii laitteella; ensimmäinen ajo (ei tietoa) yliarvioi yhä.
  Seuraavaksi: opittu tarve ja G talteen asetuksiin (säilyy käynnistyksen ja flashin yli), ja 1. ajon alku alemmas.

### Opitut arvot talteen ja 1. ajo alemmas (EXPRESSO-ESIUUTTO-FF, 26.9.2026) — isännällä, ei flashattu

- `learned_ff_pre`, `eu_g_pre` ja `eu_coast_s` settings.txt:hen (`eu_ff_pre`, `eu_g_pre`, `eu_coast_s`; vanha tiedosto
  ilman avaimia → oletukset). settings.txt ei ole flash-setissä, joten arvot säilyvät flashin yli.
- Oppi vain asettuneesta pidosta (≥ 1 s 2 s:n jälkeen); lyhyt pito ei enää nollaa edellistä tietoa (c-ajo).
- `EU_FF_FIRST_X` 0,6 → 0,4: mallissa 1. ajo kiinni +0,16 → +0,07, lämmin pidon alku −0,07 → −0,10 (raja).
- Smoke 4 failed, kaikki kohinasta tai vaiheesta riippuvia (1 pidon sd 0,103, 8 ajo 1 rampin viive 0,38, 9 kohinaiset
  parit +0,13 / −0,10); samat tarkistukset vaihtuvat vihreän ja punaisen välillä asetuksesta riippumatta.
  Muut smoket vihreät.

### Laitteella 26.9.2026 klo 12.5x (esiuff3, `hold 5`) — tallennettu tieto säilyy uudelleenkäynnistyksen yli

- **esiuff3 (VERIFIED 19/19, 0308746).** Lokit f, g, h; ennen h:ta `pico_dev.py safe` (reset).
- **f (1. ajo, 0,4 × 0,27 = ff 0,11):** 2 s keskiarvo 2,59, over 0,47, pito 2,527 / sd 0,126; opittu 0,06, tallennettu.
- **g (edellisen tieto, ff 0,05):** 2 s 2,61, over 0,16, pito 2,569 / sd 0,117.
- **h (resetin jälkeen, EU_START ff=0,05 coast_s=0,079 settings.txt:stä):** katkaisusta pitoon 231 ms, 2 s 2,532,
  over 0,12, pito 2,522 / **sd 0,068** (paras). Tarve pysyi 0,05–0,06 (tau_obs 8,9–9,7 s).
- **Silta:** `Connection refused` toistui (pim ×3, shot ×2); syy `Link`: `ERR usb closed` -haaran uusi yhteys ilman
  uusintaa. Korjattu `pico_dev.py` (`_connect` molemmissa), laitteella todentamatta.
- **Jäljellä:** g:n 2 s keskiarvo 2,61 vaikka ff = tarve: ylitys tulee katkaisun jälkinoususta ja rampista, ei ff:stä
  (g: coast 0,04, ramppi 0,8 s). Pidon alun 0,1 bar ylitys on seuraava kohde.

### Pidon alun ylitys on kohinan tasasuuntausta (EXPRESSO-ESIUUTTO-ALKU, 26.9.2026) — isännällä, ei flashattu

- **Lokit f–h:** g:n 2 s keskiarvo 2,61 ei tule jälkinoususta eikä rampista. Pito alkoi 2,40:ssä, ja paine pysyi
  ~2,5:ssä 0,7 s, minkä jälkeen se ryömi 3,0–4,8 s:n kohdalla arvoihin 2,6–2,86. Pidon duty oli ~0,06–0,07, kun tarve oli 0,05.
  h (katkaisu 2,05, ei ramppia) 2,53. f:n ylitys 2,92 tuli rampin lopun iskuista (1. ajo, katkaisu 1,30), ei ff:stä.
- **Malli (kiinni-tila iskukoko 0,12 / tau 9 s, jaksokohina 0,25, pysähdykset 0,8 %)** toistaa g:n: katkaisu 1,35,
  2 s keskiarvo +0,16 (max +0,39, 24 siementä). Kohinattomana +0,016. Pelkkä jaksokohina antaa +0,125, pelkät
  pysähdykset +0,06. Loppulähestymisen integraalikerroin (`EU_KI_TAIL_X` 1) ei auta. P-termi p5:stä
  +0,14 ja anti-windup ilman P-termiä +0,09.
- **Syy:** duty rajattiin nollaan. Tarve 0,05 on lähellä nollaa, ja jaksokohinan P- ja D-termi heiluttavat u:ta sen
  molemmin puolin, joten rajaus tasasuuntaa kohinan lisäiskuiksi. Anti-windup esti integraalin laskun (u ≤ 0, e < 0), joten
  integraali ei voinut korjata virhettä.
- **Korjaus:** delta-sigma saa u:n alueella −1…1 (`acc` alaraja −1), ja anti-windup käyttää samaa aluetta. Pidon tarve ja
  duty_avg opitaan samasta u:sta. Loki-`d` pysyy välillä 0…1. Tulos mallissa: +0,04 (max +0,13).
- **Testit:** esiuutto_smoke tapaus 10 (8 siementä, 1. ajo + edellisen tiedolla): uusi ka +0,037 / max +0,12, HEAD
  +0,154 / +0,24 (kaatuu). Koko smoke 3 failed (HEAD 5): 1 pidon sd 0,102, 8 ajo 1 rampin viive 0,45 (HEAD 0,38) ja
  9 1. ajo lämmin −0,10 (rajalla, HEAD −0,10 ok). Nämä ovat tunnettuja kohinaisia tarkistuksia. Kohinaiset parit (HEAD 2 failed) ovat nyt
  vihreät. Muut functions-smoket 12/12.
- **Jäljellä:** 1. ajon rampin lopun ylitys (f: over 0,47) ja laitetodennus: flash ja `pico_dev.py hold 5` (vain 2,5 bar).

### Laitteella 26.9.2026 klo 17.4x (esialku2, `hold 5` × 3) — eri kuristintila, korjauksen kohdetilaa ei tavoitettu

- **esialku2 (RESTORE_OK, VERIFIED 19/19 setin manifestia vasten, functions.py 3c16fd99).** Paikallinen MANIFEST.json oli
  24.9:n setistä (classes.py MISMATCH) → päivitetty esialku2:n manifestiin. Ensimmäinen build_set-yritys (`pico/functions.py`
  väärä polku) jätti puhelimeen osittaisen kopion `20260926-esialku1` (= esiuff3), käyttämättä.
- **Tila eri kuin f–h:** tarve 0,27–0,34, tau_obs 1,4–2,7 s (f–h 0,05 / 9 s). Kohinan tasasuuntaus koskee pientä tarvetta,
  joten tämä ei todenna korjausta.
- **i (ff 0,11 → nousu hidas, katkaisu 2,14 @ 1,99 bar/s):** 2 s ka 2,42 (p5 2,39), pito 2,51 / sd 0,33, over p5 +0,03.
- **j (ff 0,34 → 0,18, katkaisu 1,97 @ 4,84):** 2 s ka 2,59 (p5 2,45), pito 2,59 / sd 0,31, over p5 +0,35.
- **k (ff 0,29 → 0,25, katkaisu 1,97 @ 4,42):** pito alkoi p5 2,79:ssä, 2 s ka 2,55, pito 2,45 / sd 0,27, over p5 +0,26.
- **Tulkinta:** pidon raaka-sd 0,27–0,33 on avoimella kuristimella samaa luokkaa kuin 24.9. d/e (0,25–0,27). j/k:n `over`
  (p5 +0,26…+0,35) ei ole erillinen rampin lopun ylitys: p5 heiluu koko pidon ajan 100 ms:n välein ±0,3 bar (j 2,24↔2,85,
  k 3,4 s:n kohdalla 2,88), ja 2 s:n p5-keskiarvo on 2,45 / 2,56. Järjestelmällinen ylitys puuttuu avoimella kuristimella;
  i jäi alle (1. ajo tallennetulla ff 0,11, tarve 0,34). Rampin lopun ylitys näkyy vain f:ssä (1. ajo, pieni tarve, 2,49 →
  2,92). Korjauksen todennus vaatii f–h:n kuristintilan (tarve ~0,05), ja kuristimen asento on käyttäjän käsissä.

### Laitteella 26.9.2026 klo 18.xx (esialku2, `hold 5` × 3, kuristin käyttäjän mukaan "huomattavasti enemmän auki")

- **l / m / n:** tarve 0,64–0,69, tau_obs 0,35–0,92 s. over 0,02–0,06, eli ylitystä ei ole. Pidon 0–2 s p5 on 2,37 / 2,28 / 2,31 ja
  2 s:n jälkeen 2,50 / 2,51 / 2,49. Raaka-sd 0,28–0,30.
- **Alitus alussa:** ff = min(nousun arvio, edellisen tarve × G-suhde). Nousun arvio olettaa `EU_TAU_S` 1,8 s, joten näin
  avoimella kuristimella se aliarvioi: m 0,35 ja n 0,21 (ffc 0,49 / 0,40, tarve ~0,65). Integraali korjaa sen ~2 s:ssa. Yläraja on tehty
  tarkoituksella (yliarvio purkautuu hitaasti), mutta nopea vuoto (tau < 1 s) purkaa yliarvion yhtä nopeasti kuin
  pumppu korjaa vajeen.
- **Kolme kuristintilaa laitteella (tarve 0,05 / 0,3 / 0,65):** pidon alun ylitys oli vain lähes kiinni -tilassa (g). Korjaus
  (-1…1-delta-sigma) on laitteella ajossa, mutta sitä tilaa ei ajettu korjauksen jälkeen.

### Laitteella 26.9.2026 (esialku2, `hold 5` × 3, kuristin lähes kiinni, kaukalo tyhjennetty)

- **o / p / q:** tarve 0,05–0,08, tau_obs 2,6–6,5 s. **Pito 2 s:n jälkeen p5 2,48 / 2,51 / 2,51** (g ennen korjausta 2,57, ja
  paine ryömi 2,6–2,86:een). Pidon aikaista ryömintää ei näy, eli -1…1-delta-sigma toimii laitteella. Pidon 0–2 s p5 2,54 / 2,45 / 2,47.
- **Uusi ylitys ennen pitoa:** täyttöä ei ollut (järjestelmä täynnä), ja nousu oli 11,5 bar/s (f–h 4,5–6). Katkaisu tehtiin
  ensimmäisessä mahdollisessa kohdassa (2 × 5 jaksoa, 250–290 ms), kun raakapaine oli jo ~2,1. q: −0,2 → 0,6 → 2,1 → 3,55 bar
  100 ms:n välein. over p5 +1,38 / +0,70 / +1,08, huippu 3,4–4,3 bar. p5:n viive ja täyden dutyn iskut ennen katkaisua
  vievät yli: nousu 11,5 × (coast 0,13 + p5-viive ~0,05) ≈ 2 bar.
- **Seuraavaksi:** vaiheen 1 katkaisu nopealla nousulla, esim. katkaisu jo ennen täyttä 2 × 5 jakson historiaa tai raakajaksopaineesta,
  kun nousu on nopea. Sovitetaan malliin (täyttö 0, iskukoko ~0,25) ennen laiteajoa. Lisäksi avoimen kuristimen alun
  alitus (l–n).

### Nopea nousu: huuhtelusäännön poikkeus (EXPRESSO-ESIUUTTO-ALKU, 26.9.2026) — isännällä, ei flashattu

- **Malli o–q:** täyttö 0, iskukoko 0,25, tau 4 s, **iskun viive 100 ms** (laite q: pumppu pois 293 ms, raakapaine silti
  2,14 → 3,55). Tulos: over 0,64–1,31 (laite 0,70–1,38), katkaisu 1,25–1,55 (laite 1,28–1,62). Viive 40 ms antaa over 0,26–0,73.
- **Syy:** katkaisu vaati p5 ≥ ½ tavoite (huuhtelusääntö). 12 bar/s nousulla raakapaine oli silloin ~2,1, ja lennossa oli ~5 iskua (1,25 bar).
- **Korjaus:** katkaisu sallitaan myös, kun p5 ≥ ¼ tavoite ja nousu ≥ `EU_RATE_FAST` 8 bar/s. Huuhtelu (tasapaino G·tau < ½
  tavoite) nousee ¼ tavoitteessa enintään G/2 bar/s, joten ≥ 8 bar/s vaatisi G > 16. Laitteella G ≤ 12,5. Smoke 5 (huuhtelu) pysyy vihreänä.
- **Tulos mallissa:** kohinaton katkaisu 1,46 → 1,05, over 1,07 → 0,61, pidon 2 s −0,02 (oli +0,18). Kohinaisena ketjutettuna
  over ka 1,05 → 0,85.
- **Kokeiltu, ei otettu:** ramppi seuraa painetta ylöspäin (over 0,67, mutta pito alkaa jälkinousun huipussa, p 3,46) ja
  lennossa olevat iskut virheeseen (Smith, 100 ms: over 0,75).
- **Raja:** 100 ms:n viiveellä ja viiden jakson (100 ms) historialla katkaisu ehtii aikaisintaan ~200 ms:n kohdalla, joten
  ~0,6 bar jää. Loput vaativat menetelmävalinnan: täysi pumppu alussa vain, jos edellinen ajo ei ollut nopea, tai lyhyempi
  keskiarvo vaiheessa 1. Kohinapiikit rajoittavat jälkimmäistä (tapaus 6).
- **Testit:** smoke tapaus 11 (nopea nousu, viive 100 ms): katkaisu 1,12, over 0,61 (HEAD 1,46 / 1,07). Tapauksen 6 raja
  p5 ≥ 1,0 / t > 2,6 s perustui vanhaan sääntöön → t > 2,44 s (täytön loppu + viive) ja p5 ≥ ¼ tavoite. Uusi katkaisee 2593 ms / 0,92
  todellisessa nousussa, over −0,00. Koko smoke 2 failed (8 ja 9, tunnetut kohinaiset). Muut functions-smoket 12/12.

### Nopea alku edellisen ajon G:sta (EXPRESSO-ESIUUTTO-ALKU, käyttäjän valinta 26.9.2026) — isännällä

- **Valinta:** "edellisestä ajosta". Jos edellisen ajon G ≥ `EU_FAST_G` 10 bar/s (o–q 12,2–12,5, muut tilat 2,8–6,8), vaihe 1
  (täysi pumppu) ohitetaan. Ramppi alkaa heti nykyisestä paineesta, ff ja G tulevat edellisestä ajosta, ja `EU_START`/`EU_CUT` saavat
  kentän `fast=1`. Nopeassa tilassa lennossa olevat iskut (`EU_INFLIGHT_US` 100 ms, G/50 bar kukin) vähennetään virheestä, eli käytössä on Smithin ennustin.
- **Paluu:** jos p5 on yli 0,5 bar rampin alla, G ei pidä, ja `g_cut` 0 saa seuraavan ajon mittaamaan sen. Jos lisäksi ramppi ≥ ½
  tavoite ja p5 < ¼ tavoite (huuhtelu tai täyttö), `EU_FAST_OFF` palauttaa vaiheeseen 1 (pumppu jatkuvasti, normaali katkaisu).
  Ennen paluuta huuhtelussa tulee taukoja (smoke 12: 18 poistoa 0,54 s:ssa); käyttäjä hyväksyi tämän valinnan yhteydessä.
- **Malli (100 ms viive, laitteen ff 0,06 / G 12,3, 12 siementä, kohina):**

  | versio | over ka / max | pidon 2 s ka |
  |---|---|---|
  | HEAD (aamu) | 1,12 / 1,52 | +0,32 |
  | ¼ tavoitteen katkaisu | 0,74 / 1,04 | +0,05 |
  | nopea alku | 0,39 / 0,75 | +0,03 |
  | nopea alku + ennustin | 0,42 / 0,70 | +0,03 |

  Kohinattomana 1,07 / 0,61 / 0,29 / 0,07. tau 10: 1,18 / 0,87 / 0,56 / 0,48. Katkaisusta pitoon ~1,2 s (oli 0,6–0,8).
- **Testit:** smoke 12 (nopea alku: fast=1, over 0,05, pito 2,44; huuhtelu: EU_FAST_OFF 539 ms, sen jälkeen ei poistoja).
  Koko smoke 2 failed (8 ja 9, tunnetut), muut functions-smoket vihreät.

### Laitteella 26.9.2026 klo 18.3x (esialku4, `hold 5` × 3, kuristin lähes kiinni) ja korjaus esialku5 (isännällä)

- **esialku4 (RESTORE_OK, VERIFIED 19/19).** MANIFEST.json = esialku4.
- **r (fast=1, G 12,33 q:sta):** flashin jälkeinen tauko → alkupaine −0,55 ja täyttö. Ramppi ei noussut 0,9 s:ssa, joten `EU_FAST_OFF`
  930 ms (p5 −0,08, sp 1,28) palautti vaiheeseen 1, jossa ¼-katkaisu tapahtui 1,06:ssa, huippu p5 2,79, over 0,47. **Pito ka 2,01**: paine
  laski 2,7 → 1,44 3 s:ssa d:llä 0–0,15. Syy: −1…1-anti-windup antoi integraalin valua ylityksen aikana (loppulähestyminen ki × 3)
  syvälle negatiiviseksi, minkä vanha 0…1-raja esti. Tämä on regressio aiemmasta korjauksestani (6f44e70).
- **s / t (fast=0; G ¼-katkaisusta 9,71 → 8,90 / 9,28):** katkaisu 1,17 / 0,94, over 0,32 / 0,40 (o–q 0,70–1,38), pito 0–2 s p5
  2,52 / 2,46, 2 s:n jälkeen 2,50 / 2,58. **¼-katkaisu toimii laitteella.**
- **Korjaus esialku5:** hidas osa (ff + integraali) ≥ 0, eli `integ ≥ −uff/EU_KI`. Mallin r-tyyppi (täyttö 0,9 s, fast): pidon 2 s
  −0,31 → −0,16. Loppulähestymisen negatiivisen integraalin esto (v16) oli huonompi (nopea alku +0,21), joten sitä ei otettu.
- **Nopea alku ei laukea laitteella:** ¼-katkaisu mittaa G:n vielä kiihtyvästä noususta (8,9–9,7, kun täydellä nostolla 12,3).
  `EU_FAST_G` 8 kaatoi smoke 9:n (kylmän tilan G ylittää 8:n → väärä nopea alku lämpimällä, −0,54), joten raja pysyy 10:ssä.
  Nopea alku jää käytännössä lepoon, kunnes G mitataan luotettavasti. Laitteen parannus tulee ¼-katkaisusta.
- **Testit:** smoke 2 failed (8 ja 9, tunnetut); tapaus 10 ka −0,078 / max +0,05; muut functions-smoket vihreät.

### Laitteella 26.9.2026 klo 18.4x (esialku5, `hold 5` × 3, kuristin lähes kiinni)

- **esialku5 (RESTORE_OK, VERIFIED 19/19 toisella yrityksellä: silta ei vastannut heti laturisyklin jälkeen).**
- **u / v (fast=0):** katkaisu 1,11 / 1,02, over 0,44 / 0,35, pito 0–2 s p5 2,51 / 2,48, 2 s:n jälkeen 2,59 / 2,50, ka 2,555 / 2,492.
  Pidon valumista ei näy (r:n 2,01).
- **w (fast=1, v:n G 10,12):** nopea alku epäonnistui kuten r:ssä. Pulssitettu ramppi (d 0,3–0,5) ei nostanut painetta
  lähtötasosta −0,6: 0,9 s:ssa −0,59 → 0,44, ja `EU_FAST_OFF` 935 ms. Sen jälkeen täysi pumppu 100 ms → 2,76. Pito ka 2,388.
- **Johtopäätös:** laitteella on joka ajon alussa täyttötilavuus (lepopaine −0,6), jonka vain täysi pumppu ohittaa nopeasti.
  "Nopea alku edellisestä ajosta" ei toimi laitteella (2/2 epäonnistui), ja se maksaa ~0,9 s. ¼-katkaisu yksin: over 0,32–0,44
  (s, t, u, v), ennen 0,70–1,38.
- **Päätös 26.9.2026 (käyttäjä): nopea alku poistetaan.** Koodi palautettiin 391aa07:n tilaan (¼-katkaisu), ja siihen lisättiin hidas osa ≥ 0.
  Smoke-tapaus 12 poistettiin. Koko smoke 2 failed (8 ja 9, tunnetut); tapaus 10 +0,017 / max +0,09 ja 11 katkaisu 0,86 / over 0,38.
  Muut functions-smoket vihreät.

### Laitteella 26.9.2026 klo 18.5x (esialku6 = e91816c, `hold 5` × 3, kuristin lähes kiinni) — paketin tulos

- **esialku6 (RESTORE_OK, VERIFIED 19/19).** MANIFEST.json = esialku6.
- **x / y / z:** katkaisu 1,19 / 1,18 / 1,26 (nousu 9,1–11,5 bar/s), over 0,39 / **1,32** / 0,42, pito 0–2 s p5 2,51 / 2,93 / 2,54,
  2 s:n jälkeen 2,54 / 2,49 / 2,52, ka 2,526 / 2,657 / 2,527.
- **y:n ryöppy:** katkaisu osui kohdalleen (jälkinousun huippu p5 2,49), mutta ramppi jäi 1,34:stä paineen alle. Kun ramppi ohitti
  paineen (1,1 s, p5 2,19, sp 2,36), d oli 0,42: rampin myötäkytkentä 0,2 + D:n rampin nopeusosa +0,1 + P. Paine nousi 3,87:ään,
  mikä on enemmän kuin d:stä ja G:stä odottaisi. Malli ei toista tätä erillisenä ilmiönä. Kokeilut "ramppi seuraa painetta" (v17)
  ja "myötäkytkentä ja D:n ramppiosa pois, kun paine on ohittanut rampin" (v18) eivät parantaneet mallia (over 0,76 / 0,82 vs 0,84), joten niitä ei otettu.
- **Paketin tulos kuristin lähes kiinni (s–z, 7 ajoa ilman nopean alun epäonnistumista):** over 0,32–0,44 (y 1,32), ennen 0,70–1,38.
  Pidon ryömintä (g 2,57–2,86) on poissa, ja 2 s:n jälkeen p5 on 2,49–2,59.
- **Avoinna:** (1) y-tyyppinen rampin kiinnikurojan ryöppy (1/8), jonka lähde on selvittämättä: tarvitaan lisää ajoja tai tiheämpi loki
  rampin loppuun. (2) Avoimen kuristimen alun alitus (l–n, p5 2,28–2,37 ensimmäiset 2 s). (3) 1. ajon rampin lopun ylitys (f).

### Avoin kuristin: ff edellisen ajon tau:sta ja integraalikatto (EXPRESSO-ESIUUTTO-AVOIN, 26.9.2026) — laitteella esiavoin1

- **Syy (l–n):** ff = min(nousuarvio EU_TAU_S 1,8:lla, edellisen tarve × G-suhde). Molemmat aliarvioivat, kun tau < 1 s:
  ffr 0,21–0,50 ja ffc 0,40–0,54, kun tarve oli 0,64–0,69. Katkaisun nousunopeus ei erota tiloja: sama kuristin m→n ja
  suljettu n→o antoivat G-suhteen 1,42 ja 1,45.
- **Korjaus 1:** ff = tavoite / (rate · tau_edellinen + p5). Tämä on sama kuin edellisen tarve × G-suhde, kun molemmat G:t
  lasketaan edellisen tau:lla. `eu_tau_pre` lasketaan rajatusta tarpeesta (0,05–0,9) ja rajataan välille 0,1–30 s. Se
  tallennetaan settings.txt:hen. Ilman sitä (vanha tiedosto) käytetään vanhaa polkua. Loki `EU_CUT … tau=`.
- **Korjaus 2:** integraali rajataan hitaan osan (ff + KI·integ) mukaan välille 0…1. Vanha ±1,5 salli vain +0,45, joten
  avoimen kuristimen tarve 0,65 jäi 1. ajon ff 0,09:llä saavuttamatta (malli: pito 2,27 koko ajan).
- **Korjaus 3:** `pico_dev.py hold` ajaa `pvent`-purun (TILAUS-H) ennen tshotia ja keskeyttää, jos purku ei ole ok.
  o–z ajettiin ilman purkua paineistetusta järjestelmästä. Käyttäjä 26.9.2026: pakkautunut paine ei ole todellinen
  tilanne, koska painetta täytyy kerätä.
- **Kauppa (malli, 12 siementä, purettu tila):** tau-lattia ei / 0,5 / 1,0 / vanha: sama avoin kuristin 0–2 s p5 2,50 /
  2,45 / 2,36 / 2,33. Avoimesta lähes kiinni -tilaan käännetyn kuristimen ensimmäinen ajo: over 0,86 / 0,79 / 0,59 / 0,43.
  **Käyttäjä 26.9.2026:** lähes kiinni -kuristin ei ole realistinen uuttotilanne ("jos vastapaine on näin kova niin kahvi
  menee joka tapauksessa pilalle"), eikä se saa määrittää toimintaa liikaa. Siksi alarajaa ei ole.
  Lämmin↔kylmä-parit (24 siementä): lämmin → kylmä +0,015 → +0,045 (3/24 yli ±0,1), kylmä → lämmin −0,025 → −0,039. Pelkkä
  integraalikatto on pareissa sama kuin HEAD.
- **Kokeiltu, hylätty:** epäsymmetrinen integraali (vaje korjataan nopeammin, ki × 6–10, kynnys 0–0,15 bar) korjasi alun
  (0–2 s 2,46–2,55), mutta tasasuuntasi kohinaa: 2–6 s +0,03…+0,13 kaikissa tiloissa.
- **Testit:** esiuutto_smoke 3 failed: 8 ja 9 1. ajo lämmin (tunnetut, samat kuin HEAD) sekä 9 kohina kylmä → lämmin −0,13
  yhdellä siemenellä (virtuaalikello siirtyy aiempien tapausten mukana, joten kohinan toteuma vaihtuu). Uusi tapaus 12
  (avoin kuristin: 1. ajo 2–6 s ≥ 2,42 ja edellisen tiedolla 0–2 s ≥ 2,42) on vihreä: 2,48–2,49 / 2,485. Muut smoket 14/14.
- **Laitteella (esiavoin1 = 0028dff, RESTORE_OK, VERIFIED 19/19, `hold 5` × 3, kuristin auki kuten l–n):** purku 2
  sykliä, lepopaine −0,93…−1,05 ja täyttö 3,5–6,7 s.

  | ajo | ff (vanha valinta) | tarve / tau_obs | pidon 0–2 s p5 | 2–5 s | over |
  |---|---|---|---|---|---|
  | l–n (esialku2) | 0,50 / 0,35 / 0,21 | 0,64–0,69 / 0,35–0,92 | 2,37 / 2,28 / 2,31 | 2,49–2,51 | 0,02–0,06 |
  | aa (1. ajo, ei tau:ta) | 0,15 | 0,71 / 0,66 | 2,19 | 2,50 | −0,04 |
  | ab | 0,60 (0,32) | 0,65 / 0,57 | **2,42** | 2,50 | 0,09 |
  | ac | 0,57 (0,26) | 0,60 / 0,53 | **2,46** | 2,51 | 0,27 |

  aa todentaa integraalikaton: tarve 0,71 on yli vanhan katon (0,15 + 0,45 = 0,60), ja 2–5 s osui silti 2,50:een. ab ja ac
  todentavat uuden ff:n: 0–2 s ka 2,44, kun l–n:ssä se oli 2,32. Kaukalo on 564 g ac:n jälkeen.
- **Jäljellä:** 1. ajo ilman tau-tietoa (aa 2,19). Kuristimen kääntö kiinni → yksi ajo yliarvioi (hyväksytty). Lämmin/kylmä-
  tila tällä versiolla on todentamatta laitteella.

### Smoken tilastolliset tarkistukset ja kellon nollaus (EXPRESSO-SMOKE-TILASTO, 26.9.2026)

- **Kellon nollaus:** `BrewData` nollaa virtuaalikellon (`U.us = 0`), joten verkon vaihe ajon alussa riippuu vain `phi_us`:sta.
  Aiemmin kello jatkui edellisestä tapauksesta, ja minkä tahansa tapauksen muutos vaihtoi muiden vaiheen ja kohinatoteuman.
- **Tilastolliset tarkistukset:** vaiheesta riippuvat kohinattomat (8, 9 1. ajo: pidon keskiarvo ja katkaisusta pitoon) ajetaan
  12 vaiheella ja kohinaiset parit 24 siemenellä (`N_PHASE`, `N_NOISE`). Hyväksyntä: keskiarvo rajan sisällä ja rajan ylittäviä
  enintään 25 % (`STAT_SHARE`). Rajat ovat samat kuin yhden ajon tarkistuksessa. ff ja opittu tarve pysyvät jokaisen ajon
  tarkistuksina, koska niiden hajonta vaiheiden välillä on alle 0,01.
- **Tapaus 3:** nollaus paljasti kaksi väärää hylkäystä. Toinen oli lukitsemattoman kellon 20 ms tauko, joka poistaa iskun
  vaiheesta riippumatta, ja toinen ajon lopun releen katkaisu. Tarkistus kattaa nyt vain kellon lukituttua alkaneet tauot
  (2,5 sd < `EU_PHASE_OK_US`), joiden jälkeen rele palaa. 12 vaiheella tuli 0 väärää (64–77 taukoa). Kun vahti poistettiin
  (`EU_LATE_MAX_US` 20 ms), jokainen vaihe antoi 1–7 väärää.
- **Löydös:** kaksi kolmesta "kohinaisesta" hylkäyksestä on järjestelmällisiä:

  | tarkistus (raja) | ka | min … max | yli rajan |
  |---|---|---|---|
  | 8 ajo 1: paine rampin alla (≤ 0,3) | +0,444 | +0,43 … +0,47 | 12/12 |
  | 9 1. ajo lämmin: pidon 2 s ka (± 0,1) | −0,100 | −0,127 … +0,006 | 9/12 |
  | 9 kohina lämmin → kylmä (± 0,1) | +0,061 | −0,07 … +0,24 | 7/24 |
  | 9 kohina kylmä → lämmin (± 0,1) | −0,041 | −0,10 … +0,05 | 1/24 |

  8 ajo 2 (edellisen tiedolla) on 0,25–0,27. Kaksi ensimmäistä ovat 1. ajoja ilman edellisen tietoa, joiden ff valitaan
  alakanttiin (päätös 26.9.2026). Syy-yhteyttä ei ole mitattu. Kohinainen lämmin → kylmä on siirtynyt HEADin pyyhkäisystä
  (+0,045, 3/24), koska siemenet ja vaiheet vaihtuivat nollauksen mukana.
- **`pico_dev.py`:** `shot` ja `hold` kieltäytyvät olemassa olevasta, ei-tyhjästä lokista (`LOG_EXISTS`, exit) ennen laturia
  ja yhteyttä. Tämä on testattu olemassa olevalla lokilla ilman laitetta.
- **Käyttäjän päätös 26.9.2026 (omat rajat 1. ajolle):** 1. ajo ilman edellisen tietoa: rampin viive ≤ 0,5 bar (ajo 2
  pysyy 0,3:ssa) ja pidon 2 s ka −0,15…+0,1. Kohinaisten parien osuus rajan ulkopuolella ≤ 1/3 (`NOISE_SHARE`), muut 25 %.
  Hylätyt vaihtoehdot: rajat ennallaan (smoke pysyvästi punainen) ja rajat ennallaan + säätimen paketti.
- **Testit:** esiuutto_smoke 0 failed, ajoaika 10 s. Lähimpänä rajaa: kohina lämmin → kylmä 7/24 (sallittu 8) ja 8 ajo 1
  katkaisusta pitoon 2/12 (sallittu 3). Muut smoket 14/14. Ennen rajapäätöstä 3 failed (taulukon kolme ensimmäistä).

### Laitteella 26.9.2026 klo 21.3x (esiavoin1, EXPRESSO-ESIUUTTO-HYVAKSYNTA, `hold 5` × 4) — ei hyväksytty

- **Firmware laitteelta:** `pico_dev.py verify pico/MANIFEST.json` → VERIFIED 19/19 (esiavoin1 = 0028dff). Reset nollasi
  RAM-asetukset, joten `pim:1` ja `pit:6` asetettiin uudelleen (`CMD_OK`); TS_START `6.0 s … pim=1`. Purku joka ajossa
  2 sykliä, lepopaine −0,78…−1,09.
- **Ajot** (lokit `testit/esiuutto-20260926-{ad..ag}-pim1.log`; ac vertailuna; huippu = EU_END `max`, vesi = kaukalon
  paino pidon aikana):

  | ajo | kuristin | ff | tarve / tau_obs | katkaisu rate / jälkinousu | pidon 0–2 s p5 | 2–5 s | pidon sd | huippu | vesi |
  |---|---|---|---|---|---|---|---|---|---|
  | ac 19.51 | auki, lämmin | 0,57 | 0,60 / 0,53 | 4,19 / 0,28 | 2,46 | 2,51 | 0,30 | 3,42 | 34 g |
  | ad 21.35 | sama, kylmä | 0,52 | 0,14 / 2,97 | 5,30 / 0,41 | **2,77** | 2,41 | 0,29 | 3,49 | 6 g |
  | ae 21.36 | sama, kylmä | 0,12 | 0,08 / 4,55 | 6,70 / 0,59 | 2,53 | 2,50 | 0,22 | 3,41 | 1 g |
  | af 21.39 | lähellä uuttoa | 0,05 | 0,06 / 2,18 | 16,91 / 1,42 | 2,46 | 2,48 | **0,61** | **4,61** | 7 g |
  | ag 21.40 | lähellä uuttoa | 0,09 | 0,05 / 5,36 | 12,18 / 2,19 | **2,89** | 2,48 | **0,71** | **4,98** | 7 g |

- **Kylmä kuristin (ad, ae):** käyttäjä ei kääntänyt kuristinta ac:n jälkeen. Sama asento päästi kylmänä 6 g ja 1 g,
  lämpimänä 34 g, ja tarve putosi 0,60 → 0,14 → 0,08. Lämmin → kylmä -siirtymä (ad, ff lämpimän ajon tiedosta) ylitti
  ±0,1:n rajan: pidon 0–2 s p5 2,77 ja ylitys 0,60. Malli (+0,015…+0,061) aliarvioi tilojen eron: sen kylmä tila on
  0,15 / 2,2 s, laitteen 0,08 / 4,6 s, eli lähempänä mallin kiinni-tilaa (0,05 / 10 s). Edellisen tiedolla (ae) pito
  osui: 2,53 / 2,50.
- **Lähes uuttoa vastaava kuristin (af, ag; käyttäjä käänsi ennen af:ää):** pidon keskiarvo osuu (2–5 s 2,48), mutta
  pito heiluu p5 2,1…3,9 bar (sd 0,61–0,71) ja huippu on 4,6–5,0 bar. Tarve on ~0,05, joten yksi isku nostaa painetta
  paljon. Nousu 12–17 bar/s, jälkinousu katkaisun jälkeen 1,4–2,2 bar (aiemmin hyväksytty ylitys ~0,4).
- **Lämmin kuristin:** ei saavutettu. Tällä asennolla vettä kulkee ~7 g/ajo, eikä tarve nouse (af → ag 0,06 → 0,05).
  Lämmitys vaatii kuumaa vettä kuristimen läpi (klamp tai uutto on 8+ bar, kielletty ennen hyväksyntää). 6 s pito
  lämpimällä kuristimella jäi ajamatta.
- **Käyttäjän päätös 26.9.2026:** korjaus ensin. Seuraava paketti korjaa pidon ja nousun lähes uuttoa vastaavalle
  kuristimelle (tarve ~0,05, tau 2–5 s, nousu 12–17 bar/s) isännän mallissa; esiuuton hyväksyntä laitteelta korjauksen
  jälkeen. Hylätyt: lämmitys auki-asennolla ja kääntö takaisin tänään, `hold 6` nykyisellä asennolla.

### Korjauksen lähtötiedot uuttoasennolle (EXPRESSO-ESIUUTTO-UUTTOASENTO, 26.9.2026) — isännällä kesken, ei koodimuutosta

- **Laitteen heilunta on rajasykli:** af:n pidossa p (jakson ka) kiertää ~300 ms jaksolla 1,6 → 3,4 → 2,2 → 1,6 bar;
  pohjalla duty 0,6–0,83 (≈ 4 iskua → +1,8 bar, eli isku ~0,45 bar), sen jälkeen 200 ms duty 0 ja pudotus ~9 bar/s.
  Pudotus on paljon nopeampi kuin vuoto tau_obs 2–5 s:llä.
- **Opittu tarve on vinossa:** pidon 1–5 s rivien duty ka af 0,26 / ag 0,22 (ac 0,59, ad 0,13, ae 0,10), mutta
  `learned_ff_pre` 0,06 / 0,05. Opittu tarve on u:n (−1…1) keskiarvo, ja rajasyklin negatiiviset u:t painavat sen alas;
  myös tau_obs (tavoite / (G · tarve)) on siksi liian suuri. Todellinen vuoto uuttoasennossa on nopea (tau ~0,7–1 s).
  G katkaisussa: avoin 3,5–5,3, kylmä 6,5–7,7, o–z 8,7–12,5, af 17,9, ag 13,0.
- **Malli (`esiuutto_smoke`-Plant, 4 siementä, edellisen tiedolla, viive 100 ms):** delta 0,30–0,36 ja tau 0,7–1,0 s
  toistaa nousun ylityksen (over 0,67–1,16, laite 0,78–1,42), mutta ei pidon rajasykliä (sd 0,30–0,38, laite
  0,61–0,71). Mallin g jää 9,6–10,5:een (laite 13–18). Tau 2,5–5 s ja delta 0,45 antaa sd 0,57, mutta syy on nousun
  ylitys (huippu 4,7–5,0, hidas lasku), ei rajasykli.
- **Kokeiltu, ei auttanut mallissa:** P-, I- ja D-termin skaalaus min(1, G_REF / g) katkaisun g:llä (G_REF 8 / 4 / 2).
  Pidon sd pysyi samana (0,36–0,65), koska mallin heilunta ei tule takaisinkytkennästä. Muutos palautettu.
- **Seuraavaksi:** sovita malli af/ag:hen (nopea pulssin purku tai kahden aikavakion kuristin, g 13–18, pidon duty ka
  0,2–0,26, 300 ms jakso) ja vasta sitten korjaus. Laitteelta voisi mitata yhden iskun vasteen 2,5 barissa
  uuttoasennossa, mutta se on laiteajo (vaatii käyttäjän).

### Uuttoasennon korjaus (EXPRESSO-ESIUUTTO-UUTTOASENTO, 26.9.2026) — laitteella esiuasento1 (ah–am), ei hyväksytty

- **Malli sovitettu af:hen (`esiuutto_smoke`-Plant, `delta_f`/`tau_f`):** isku nostaa hidasta osaa (0,25 bar, vuoto
  tau 0,8 s) ja nopeaa osaa (0,6 bar, purku 0,08 s), viive 20 ms, täyttö 0,6 s. Vanhalla säätimellä (8 siementä, 1. ajo
  ae:n opituilla arvoilla kuten af): g 18,6 (laite 17,9), pidon sd 0,59 (0,62), 300 ms jakso eli p:n autokorrelaatio
  3 × 100 ms 0,54 (0,62), iskuosuus 0,20 (0,19), opittu tarve 0,11 (0,06), huippu 4,6 (4,61). Yksiosainen malli antoi
  jakson 400–500 ms ja sd:n 0,3–0,5. Haku: `delta` 0,1–0,3, `tau` 0,6–1,8, `delta_f` 0,3–0,8, `tau_f` 0,05–0,15, viive 10–100 ms.
- **Rajasykli on D-termin takaisinkytkentä:** KD = 0 poisti jakson (autokorrelaatio 0,54 → −0,05) ja opitun tarpeen
  vinouman (0,11 → 0,19). P:n puolitus ei vaikuttanut. D laskee nousunopeudesta, joka on 5 jakson keskiarvojen erotus
  (~0,1 s viive), joten silmukka KD·G ≈ 0,9 heiluu 2 × viive -jaksolla. Laitteella o–z (g 9–12,5, tarve 0,02–0,09) eivät
  heiluneet, ag (g 12,95, tarve 0,14) heilui: pelkkä g ei erota tiloja, koska iskun nopea vaste on uuttoasennossa suurempi
  kuin katkaisun g näyttää.
- **Korjaukset (`pico/functions.py`):**
  1. `EU_KD_G` 0,3 ja `EU_KD_G_HOLD` 0,1: kd = min(KD, raja / g) katkaisun g:llä, rampilla ja pidossa erikseen. g ≤ 6
     (ramppi) ja g ≤ 2 (pito) ennallaan. D:n poisto pidosta kokonaan poisti jakson, mutta heikensi hitaita tiloja
     (smoke 10 +0,006 → +0,056, raja 0,06; smoke 1 sd 0,082 → 0,098, raja 0,1).
  2. Pidon tarve = toteutunut iskuosuus pidon 2 s:sta loppuun (iskut / (iskut + poistot)), ei u:n keskiarvo: kertymä
     rajataan −1:een, joten heilunnan negatiiviset u:t veivät keskiarvon alle iskuosuuden (laite af/ag 0,06 / 0,05 vs.
     0,19 / 0,14). EU_END kirjaa vertailuksi `u_mean` ja `kd`.
  3. Nopean nousun (katkaisun rate ≥ `EU_RATE_FAST` 8 bar/s) jälkinousu opitaan erikseen (`eu_coast_fast_s`, oletus
     `EU_COAST_FAST_S0` 0,2, settings.txt:hen). Laitteella nopeat 0,12–0,195 s (o–z, ag), hitaat 0,03–0,11 s; yhteinen arvo
     periytyi hitaasta tilasta (af katkaisi ae:n 0,054:llä 1,79 barissa, jälkinousu 1,42 → huippu 3,21).
- **Malli, kohina ja ketju (8 siementä, 2. ajo edellisen tiedolla), vanha → uusi:**

  | tila | pidon p5 sd | 300 ms jakso | ylitys | pidon 0–2 s p5 |
  |---|---|---|---|---|
  | uuttoasento (ua1) | 0,49 → 0,35 | 0,51 → 0,10 | 1,68 → 1,23 | 2,63 → 2,48 |
  | lämmin (0,2 / 0,8 s) | 0,15 → 0,13 | −0,01 → 0,02 | 0,29 → 0,33 | 2,53 → 2,51 |
  | lähes kiinni, nopea nousu (0,25 / 4 s) | 0,20 → 0,20 | 0,01 → 0,01 | 0,76 → 0,76 | 2,60 → 2,53 |
  | kiinni (0,12 / 9 s) | 0,13 → 0,14 | 0,02 → 0,12 | 0,32 → 0,28 | 2,56 → 2,53 |
  | avoin (0,128 / 0,6 s) | 0,13 → 0,12 | 0,10 → 0,05 | 0,18 → 0,17 | 2,45 → 2,45 |

- **Jäljellä mallissa:** uuttoasennon jälkinousu ~1,9 bar ja huippu p5 ~3,7. Katkaisun nousunopeus jää täytön lopun
  kiihtyvässä nousussa jälkeen (mallissa mitattu 8 bar/s, todellinen ~25), ja katkaisu tapahtuu portilla p5 ≥ ¼ tavoite.
  Portin laskeminen on täytön kohinan vuoksi riski (esiuutto-20260924-c), joten sitä ei muutettu.
- **Testit:** esiuutto_smoke 0 failed; uusi tapaus 13 (uuttoasento, 8 siementä × 2 ajoa: jakso ≤ 0,3, p5 sd ≤ 0,45,
  pidon 2–5 s ± 0,1, opittu tarve = iskuosuus ± 0,03) on vihreä (jakso 0,12 / −0,01, sd 0,37 / 0,38). Vanha säädin kaatuu
  tapauksen 13 kaikkiin tarkistuksiin (jakso 0,49 / 0,45, sd 0,48 / 0,53, tarve pielessä 0,15 / 0,13). Tapaus 2 tarkistaa
  nyt katkaisun nousunopeuden mukaisen luokan. Muut smoket 14/14.

### Laitteella 26.9.2026 klo 22.3x–22.4x (esiuasento1 = 417ad93, `hold 5` × 6) — ei hyväksytty

- **Setti 20260926-esiuasento1:** RESTORE_OK n=19, VERIFIED 19/19, `pim:1` ja `pit:6` `CMD_OK`. Lokit
  `testit/esiuutto-20260926-{ah..am}-pim1.log` (d93ca55, 7e23b5e); vesi = kaukalon paino pidon aikana.

  | ajo | kuristin | nousu bar/s | jälkinousu | pidon 0–2 s / 2–5 s p5 | pidon sd | 300 ms jakso | huippu | tarve / iskut | late / miss | vesi |
  |---|---|---|---|---|---|---|---|---|---|---|
  | af (vanha) | af/ag | 16,9 | 1,42 | 2,46 / 2,48 | 0,61 | 0,62 | 4,61 | 0,06 / 0,19 | 2 / 2 | 5,8 g |
  | ag (vanha) | af/ag | 12,2 | 2,19 | 2,89 / 2,48 | 0,71 | 0,34 | 4,98 | 0,05 / 0,14 | 2 / 3 | 3,8 g |
  | ah | af/ag | 9,7 | 0,43 | 2,52 / 2,51 | 0,17 | −0,40 | 3,29 | 0,10 / 0,10 | 0 / 3 | 1,3 g |
  | ai | af/ag | 7,1 | 0,86 | 2,51 / 2,51 | 0,19 | −0,27 | 3,40 | 0,10 / 0,10 | 1 / 3 | 2,5 g |
  | aj | af/ag | 7,8 | 0,56 | 2,51 / 2,47 | 0,32 | 0,01 | 3,90 | 0,08 / 0,07 | 3 / 6 | 0,8 g |
  | ak | af/ag | 7,4 | 0,89 | 2,45 / 2,49 | 0,22 | −0,14 | 3,76 | 0,09 / 0,09 | 0 / 4 | 2,8 g |
  | al | avattu | 8,3 | 0,67 | 2,40 / 2,55 | 0,28 | −0,03 | 3,42 | 0,14 / 0,13 | 3 / 6 | 5,2 g |
  | am | avattu | 8,0 | 0,73 | 2,43 / 2,49 | 0,25 | −0,05 | 3,68 | 0,14 / 0,13 | 2 / 3 | 4,5 g |

- **Rajasykli poissa:** p:n autokorrelaatio 3 × 100 ms −0,40…0,01 (af 0,62), pidon sd 0,17–0,32 (0,61–0,71), huippu
  3,3–3,9 (4,6–5,0). Opittu tarve = iskuosuus (±0,01; `u_mean` samaa luokkaa, koska jaksoa ei ole). Jälkinousu 0,43–0,89.
- **Kuristin ah–ak kiinnempänä kuin af/ag:** vettä 0,8–2,8 g, tarve 0,07–0,10. Käyttäjä avasi kuristinta ennen al:ää;
  al/am vesi 4,5–5,2 g ja tarve 0,14 vastaavat af/ag:ta. Nousu katkaisussa 8 bar/s (af/ag 12–17): katkaisu tapahtui
  aiemmin (p5 1,4–1,7, jälkinousu 0,1 s), joten mitattu g ei ole suoraan vertailukelpoinen.
- **Jäljelle jäänyt ylitys on vuoronvaraus:** al/am p5 3,2 bar ~0,6 s pidon alusta (ylitys 0,74 / 0,82) ja aj:n piikit
  3,3–3,6 osuvat kukin `late`-laskurin kasvuun ja ~120 ms lokiväliin. Rele jää päälle varauksen ajaksi, ja tällä
  kuristimella isku on suuri (+0,8–1,0 bar). Varaukset toistuvat ~3,0 s EU_STARTista (af 3,5 / 3,8 s, aj 3,0 / 4,0 /
  6,4 s, al 3,0 s, am 3,0 s).
- **EU_END-rivi katkesi siirrossa:** 417ad93 pidensi rivin 278 merkkiin (aiemmin ≤ 243). Alku puuttuu 20–21 merkkiä
  (`EU_END reason=stop ma`) ja loppu toistuu yhtä pitkänä, eli siirtotiellä on 256 tavun raja. Arvot `max`:sta eteenpäin
  ovat tallessa; `reason` puuttuu. Korjaus: uudet kentät omalle rivilleen seuraavassa flashissa.
- **Käyttäjän päätös 26.9.2026:** ei hyväksyntää, vaan piikit korjataan ensin: rele ei saa jäädä päälle vuoronvarauksen
  ajaksi. Sen jälkeen uusi hyväksyntäajo. Hylätyt: "Hyväksy esiuutto" (piikit erilliseksi) ja "Vertaa vanhaan ensin"
  (esiavoin1 A/B samalla asennolla).

### Vuoronvaraus (EXPRESSO-ESIUUTTO-VUORONVARAUS, 26.–27.9.2026) — laitteella vuoronvaraus3 (aq–as): late 0

VAATIMUS: TILAUS-L (tauko on yksi jakso: myöhästynyt tauko jäi tekemättä ja isku meni läpi), TILAUS-K.

- **Lokien pysähdykset (ah–am):** EU-rivien väli 113–128 ms 100 ms:n sijaan, eli silmukka pysähtyi 13–28 ms, 0,4–1,2 s
  välein, myös vaiheessa 1. `late` kasvoi vain, kun rele oli päällä pysähdyksen aikana (al 2974 ms: rele 1, p5 2,36 →
  3,24).
- **Mitattu syy (an, `euv:0`, setti vuoronvaraus1): automaattinen roskienkeruu.** Keko 307 kt vapaana heti keruun
  jälkeen ja täynnä 0,5–0,8 s:ssa (~500 kt/s; 1 kHz:n näytteenoton float-laskut), ja jokainen `fr`-hyppy (+230…+270 kt)
  osui 15–28 ms:n pysähdykseen. Vaa'an 17 ms "tehtäväpysähdykset" (`task=scale:16888`, 4747 / 6059 / 8076 ms) olivat
  keruita vaakatehtävän sisällä, samoin `task=-:0` 16,7 ms. an: late 4 / miss 6, joista 3 pidossa releen ollessa päällä.
  Toinen, pienempi lähde (ap): kellon ikkunan sulku (`iq_close` + VKELLO-rivi) 10–11 ms näytteenotossa.
- **Mittausrivit (`pico/functions.py`, `pico/main.py`):** `EU_STALL t_ms sec us rel [task]`, kun asyncio-vuoro (y), jakson
  käsittely (k), näytteenotto (s) tai myöhästyminen (l) ylittää 10 ms (`EU_STALL_US`); vuorolle tehtävä, jonka kierros
  oli pisin (`brew_data.tbusy`: ble, ser, scale, wd). `EU_GC t_ms us rel` jokaisesta hallitusta keruusta. `EU_VV` ajon
  lopussa: `stall gc_n gc_max_us fr0 fr_end k_max_us s_max_us y_max_us late_max_us`. `gc.mem_free()` käy keon läpi
  7,3 ms (an), joten sitä kutsutaan vain alussa ja lopussa.
- **Korjaus (`euv:1`, oletus; `euv:0` = vanha, RAM only kuten pim):** vaiheessa 2 asyncio-vuoro vain, kun rele on pois,
  seuraava jakso on tauko eikä 10 ms tauon paluuta odoteta. Roskienkeruu hallitusti samassa kohdassa 300 ms välein
  (`EU_GC_MS`: 300 ms × 500 kt/s jättää ~150 kt varaa), vaiheessa 1 vain, kun p5 < 0,1 × tavoite. Kellon ikkunan sulku
  vasta, kun seuraavaan päätöskohtaan on ≥ 12 ms (`EU_IQ_CLOSE_US`), jos rele on päällä tai seuraava jakso iskee.
  Pysähdys vain pidentää taukoa: sen yli jäänyt isku siirtyy, eikä rele jää päälle.
- **EU_END kolmeen riviin (`EU_END`, `EU_END2`, `EU_VV`, ≤ 255 merkkiä, 20 ms väli):** USB-CDC:n lähetysjono on 256 tavua
  ja ylikirjoittuu, kun DTR puuttuu (sovellus ei aseta sitä), joten 278 merkin rivi katkesi. `esiuutto_smoke.field`
  lukee avaimen ensimmäiseltä prefiksin riviltä, jolla se on.
- **Malli (`esiuutto_smoke`: Gc = keko täynnä 0,5–0,8 s:ssa ja keruu 15–28 ms kuten an; tehtävävaraukset 0,8 % vuoroista
  13–28 ms; kellon ikkunan sulku 9 ms), tapaus 14, uuttoasento 8 siementä × 2 ajoa:** vv=0 late 13–25 ja pidon piikki
  ka +1,5…+1,9 bar; vv=1 late 0, automaattisia keruita 0, piikki ka +0,52…+0,55 (max +0,81), pidon p5 sd 0,23–0,24.
  Ilman sulun siirtoa vv=1 late 0–3/ajo (toisti ap:n). Tapaus 13 (5–15 ms varaukset): pidon p5 sd 0,37 → 0,17; sen
  rajasyklitarkistus on nyt autokovarianssi ≤ 0,3 × 0,45² bar² (käyttäjän päätös 27.9.2026: normalisoitu korrelaatio
  mittasi puolittunutta kohinaa, 3/8 yli). Tapaus 3 jaettu: vv=0 vahti toimii (late 8), vv=1 late 0.
- **Laitteella** (lokit `testit/esiuutto-2026092{6,7}-{an..as}-pim1.log`; kattila 101–103 °C BLE-telemetriasta; ao–as
  7 h tauon jälkeen, kuristin al/am-asennossa mutta kylmä: vesi −0,7…2,4 g, tarve 0,05–0,09, al/am 4,9–5,8 g ja 0,14):

  | ajo | setti / euv | late / miss | ylitys | pidon sd | 0–2 s p5 | 2–5 s p5 | p5 max 1–5 s | tarve |
  |---|---|---|---|---|---|---|---|---|
  | al | esiuasento1 | 3 / 6 | 0,74 | 0,28 | 2,40 | 2,55 | 3,40 | 0,14 |
  | am | esiuasento1 | 2 / 3 | 0,82 | 0,25 | 2,43 | 2,49 | 2,77 | 0,14 |
  | an | vuoronvaraus1 / 0 | 4 / 6 | 0,38 | 0,25 | 2,79 | 2,61 | 3,03 | 0,05 |
  | ao | vuoronvaraus2 / 1 | 0 / 0 | 1,32 | 0,27 | 2,59 | 2,50 | 2,80 | 0,09 |
  | ap | vuoronvaraus2 / 1 | 1 / 0 | 0,52 | 0,19 | 2,52 | 2,50 | 2,78 | 0,05 |
  | aq | vuoronvaraus3 / 1 | 0 / 1 | 0,36 | 0,17 | 2,53 | 2,50 | 2,84 | 0,05 |
  | ar | vuoronvaraus3 / 1 | 0 / 1 | 0,65 | 0,21 | 2,57 | 2,52 | 2,79 | 0,05 |
  | as | vuoronvaraus3 / 1 | 0 / 0 | 0,60 | 0,24 | 2,58 | 2,43 | 2,86 | 0,05 |

  vuoronvaraus3:lla ei yhtään `EU_STALL`-riviä releen ollessa päällä (`rel=1`), ja aq/ar:n miss osui taukoon. Hallittu
  keruu 18–19 kertaa ajossa, 15,1–16,0 ms. ap:n ainoa late (661 ms, heti katkaisun jälkeen) oli kellon ikkunan sulku.
- **Jäljellä oleva ylitys ei ole vuoronvarausta:** ao:n 1,32 syntyi rampilla (1105 → 1207 ms, p5 2,03 → 3,15
  iskuryöpystä, ensimmäinen ajo 7 h jälkeen an:n opituilla arvoilla), ar:n ja as:n 0,60–0,65 rampin lopussa (ar 1204 → 1404
  ms kaksi iskua, p5 2,24 → 3,07, purku hidas: tau_obs 14 s). Kylmällä, lähes kiinni olevalla kuristimella yksi isku on
  +0,35–0,45 bar. Myös kellon lukko jää ajoittain saamatta (aq, as: `windows=5`, `sd_us` 12 ms → 20 ms tauot), koska
  tarpeella 0,05 iskuja on vähän (`win_low` 33–34).

### Rampin loppu (EXPRESSO-ESIUUTTO-RAMPIN-LOPPU, 27.9.2026) — isännällä 651afec, ei flashattu

VAATIMUS: TILAUS-K (vaihe 2: esiuuttopaineen viimeinen nosto ilman yliampumista), TILAUS-L.

- **Mekanismi (laite ao–as):** jälkinousu vei paineen rampin ylle (huippu 2,55–2,93, ramppi ~1,7), paine putosi rampille
  2,0–2,3 bariin 0,3–0,4 s:ssa, ja rampin myötäkytkentä 2 bar/s / G (G katkaisusta 9–10 → 0,2) + D (rate −1…−2 bar/s) + P
  antoivat d 0,34–0,46 eli 2–3 iskun ryöpyn. Isku pidossa +0,35–0,45 bar. ao:n pito alkoi 3,45:ssä (ryöpyn keskellä).
- **Malli: kaasujousto.** Vakiojoustoinen Plant ei toistanut laitetta: jälkinousu 2,8 bar (laite 1,1–1,6) tai lasku liian
  hidas. `esiuutto_smoke`-Plant `gas_bar`: iskun vaikutus ∝ absoluuttinen paine² (isoterminen ilma, käyttäjä 18.9.: "boilerissa
  on joskus ilmaa"), isku 0,45 bar 2,5 barissa ≈ 0,2 bar katkaisussa → G 9–10 ja pidon isku samasta mallista. Satunnaishaku
  (120 kokoonpanoa, vanhalla koodilla, 6 siementä) laitteen keskiarvoihin: kaasujousto kärjessä kaikissa. Valittu isku 0,45 /
  tau 2,5 s / viive 10 ms iskun puolijakson jälkeen (≈ 40 ms käskystä, TILAUS-I) / täyttö 0,3 s. Vanha koodi mallissa:
  ylitys 0,53 / 0,65 (laite ka 0,69), huippu jälkinousun jälkeen 0,49 / 0,58 (laite 0,32–1,18, ka 0,61), pito alkoi ka 2,72.
- **Korjaukset (`pico/functions.py`):**
  1. `EU_RAMP_DONE`: kun p5 ≥ tavoite − 0,1 jälkinousun ikkunan (EU_COAST_MS) jälkeen, asetusarvo on tavoite eikä ramppi.
     Ikkunan ehto on välttämätön: uuttoasennossa nopea osa nosti p5:n tavoitteeseen 60 ms katkaisusta, ja pito alkoi
     transientista (smoke 14, piikki 1,05).
  2. Pito alkaa vasta, kun p5 on tavoite ± 0,1 myös ylhäältä (menetelmäohje: yliampuma ei aloita laskuria); varalla
     `EU_HOLD_WAIT_MS` 2000 (kuristin ilman vuotoa). EU_HOLD kirjaa `wait_ms`.
  3. Kaasujousto rampin vahvistukseen: kun p5 on käynyt ≥ 0,3 bar rampin yllä (`EU_ABOVE_BAR`), rampin myötäkytkentä
     jaetaan ja D-raja lasketaan G:llä × ((1 + sp) / (1 + p_katkaisu))² (`EU_GAS_ABS` 1,0, `EU_GAS_EXP` 2). Ilman ehtoa
     alhaalta nouseva ramppi hidastui vakiojoustoisessa mallissa: smoke 8 ajo 1 paine 0,64 bar rampin alla (raja 0,5),
     katkaisusta pitoon 1,16–1,18 s (raja 1,1), 9 lämmin samoin.
- **Malli (smoke 15, ao–as-malli, 12 siementä × 2 ajoa, 1. ajo ao–as:n opituilla arvoilla), vanha → uusi:**

  | ajo | ylitys ka (max, yli 0,45) | huippu jälkinousun jälkeen ka (max) | pidon alkupaine |
  |---|---|---|---|
  | 1 | 0,50 (0,89, 8/12) → 0,38 (0,59, 2/12) | 0,43 (0,80) → 0,30 (0,47) | 2,42–2,73 → 2,42–2,59 |
  | 2 | 0,55 (0,99, 7/12) → 0,40 (0,60, 3/12) | 0,49 (0,93) → 0,33 (0,54) | 2,43–3,34 → 2,40–2,54 |

  Jäljelle jää ~yksi isku (0,45 bar): pidon tarve 0,05 kylmällä, lähes kiinni olevalla kuristimella on tämän iskukoon alaraja.
- **Testit:** esiuutto_smoke 0 failed (uusi tapaus 15: HEAD kaatuu kaikkiin kuuteen tarkistukseen). Tapaus 14 pito alkaa nyt
  aiemmin, joten "1 s pidon alusta" -ikkuna osuu siirtymän loppuun: piikki ka 0,52 / 0,55 → 0,59 / 0,58, sd 0,24 / 0,23 →
  0,26 / 0,23 (rajat 0,7 ja 0,3 pitävät). Muut smoket 14/14.
- **Kellon lukko pienellä tarpeella (ei korjattu, analyysi):** ao–as:ssa lukko (2,5 sd < 1000 µs) ei syntynyt kertaakaan.
  Ainoa oppiva ikkuna on katkaisussa (w=5, sd ~735 µs); nousun ikkunat eivät opeta (gate=−1, viive riippuu paineesta: z 8,1 →
  5,0 ms aq:n nousussa). Pidossa tarpeella 0,05 väreily on ~0,4 iskua / 8 jakson ikkuna: aq ja as amp < AMP_MIN 0,1 koko
  pidon (win_low 33–34), sd kasvaa 12 ms:iin ja tauot ovat 20 ms. ar:n viisi heikkoa ikkunaa (amp 0,10–0,20) mittasivat
  z +0,5…+1,4 ms järjestelmällisesti — sama suunta kuin tauon jälkeinen viiveharha (`verkkokello.py` transienttiportti). Siksi
  heikkojen ikkunoiden hyväksyntä (AMP_MIN alas tai r ∝ 1/amp²) toisi harhan kelloon. Ohjaukseen vaikutus pienellä tarpeella
  on vähäinen (20 ms tauko poistaa saman iskun), mutta TILAUS-K (2) "syklin tunnistusta parannetaan jatkuvasti" ja TILAUS-J
  eivät täyty pidossa. Päätös käyttäjälle: (a) hyväksytään vapaa kello matalan tarpeen pidossa ja lukitus vaiheen 3 nousussa,
  (b) laitemittaus yksittäisen iskun väreilyn vaiheesta 2,5 barissa ennen kuin heikot ikkunat otetaan käyttöön.

### Laitteella 27.9.2026 klo 07.49–08.00 (rampinloppu1 = 651afec, EXPRESSO-ESIUUTTO-HYVAKSYNTA, `hold 5` × 4) — hyväksytty

VAATIMUS: TILAUS-K (vaihe 2), TILAUS-L.

- **Firmware:** setti `20260927-rampinloppu1` (build_set vuoronvaraus3:n päälle), `restore` → RESTORE_OK 4 min 51 s,
  `verify` → VERIFIED 19/19 (repon MANIFEST päivitetty käsin, 2772ae2); `pim:1`, `pit:6` → `CMD_OK`. Kattila lämmin
  (BLE 96 °C klo 07.46), kuristin käyttäjän mukaan ao–as-asennossa.
- **Ajot** (lokit `testit/esiuutto-20260927-{at..aw}-pim1.log`; as vertailuna; pito alkoi = EU_HOLD, tarve = EU_END2 u_mean):

  | ajo | ylitys | pidon sd | 0–2 s p5 | 2–5 s p5 | p5 max 1–5 s | pito alkoi | tarve | vesi täytössä / pidossa | late / miss |
  |---|---|---|---|---|---|---|---|---|---|
  | as | 0,60 | 0,24 | 2,58 | 2,43 | 2,86 | 1,2 s | 0,05 | 0 / 2 g | 0 / 0 |
  | at | 0,08 | 0,26 | 2,47 | 2,55 | 2,78 | 6,2 s | 0,18 | 3 / 6 g | 1 / 1 |
  | au | 0,09 | 0,19 | 2,46 | 2,51 | 2,84 | 2,8 s | 0,16 | 6 / 6 g | 0 / 0 |
  | av | 0,32 | 0,22 | 2,54 | 2,52 | 2,75 | 4,3 s | 0,14 | 6 / 4 g | 0 / 1 |
  | aw | 0,30 | 0,18 | 2,45 | 2,54 | 2,71 | 2,9 s | 0,13 | 6 / 5 g | 0 / 0 |

- **Tulos:** ylitys < yksi isku (0,45) kaikissa, ei katkaisun jälkeistä ryöppyä; pito kaistalla. Käyttäjä hyväksyi esiuuton.
- **Pidon myöhäinen alku ei ole säädintä:** vaihe 1 täydellä teholla 2,2–5,7 s (as 0,6 s), vettä kaukaloon jo täytössä
  3–6 g (as 0) — lämmin kuristin samassa asennossa päästää enemmän (tarve 0,13–0,18 vs 0,02–0,09). Katkaisun rate 2,35–9,04.
- **Kello:** tarpeella 0,13–0,18 lukko syntyi (av, aw `sd_us` 650–662, windows 21–44); käyttäjän valinta (a): vapaa kello
  matalan tarpeen pidossa, lukitus vaiheen 3 nousussa.
- **Yhteysvika (EXPRESSO-TYPEC-JUMI, REKISTERI Viat):** av:n kaksi ensimmäistä yritystä `PICO_NOT_ON_USB`; USB-C-tilakone
  jumissa au:n laturin palautuksen jälkeen, OTG-uudelleenkytkentä purki; av ja aw ajettiin sen jälkeen.
