# eXpresso — skoopin `infra expresso` rekisteri

Tilanne: 27.10.2026

SEURAAVA PAKETTI: ei mitään — odottaa käyttäjää: laitetodennukset (PEQ, höyrytys, lepotila, uutto)

## Pysyvät vaatimukset (Tilauksen invariantit)

`Infra/iot/expresso/KAYTTAJAN-TIEDOT.md` **luetaan kokonaan joka purussa**, samalla tavalla kuin
tämä rekisteri. Se sisältää käyttäjän omat tilaukset, laitetiedot, turvarajat ja menetelmäohjeet
alkuperäisinä lainauksina ja viitteet `paketit/PUMPPU-PWM.md`:n riveihin. Tämä rekisteri kuvaa sen,
mikä muuttui; se tiedosto sen, minkä on aina pidettävä.

Kaikki tilauksen menetelmäkohdat ovat nimetyiksi invarianteiksi (`TILAUS-A`…`TILAUS-T`, `TILAUS-RELEET-ALAS`, `TILAUS-AUTONOMIA`).
Koneellinen tarkistin: `node claude/siirto/tools/vaatimukset.mjs --tarkista "infra expresso" <brief.md>`.
Purun tarkistus ja vaatimuslista: `node claude/siirto/tools/vaatimukset.mjs --rivi "infra expresso"`.

**Pakkaus ei kopioi sen sisältöä muistioon eikä tähän rekisteriin** — pakkaus antaa vain tiedon,
että tiedosto on olemassa ja luettava. Sisällön kopioiminen tiivistäisi sen, ja tiivistäminen on
juuri se vika, jonka takia tiedosto on olemassa (`paketit/TILAUS-INVARIANTIT.md`,
`claude/siirto/REKISTERI.md` rivi `SIIRTO-VAATIMUS-KATOAA`). Tiedostoon **lisätään**, sitä ei
kirjoiteta uusiksi: vanhentunut rivi merkitään vanhentuneeksi, sanamuoto jää näkyviin.

**Laiteajon kuristin:** TILAUS-M (`KAYTTAJAN-TIEDOT.md` 2c), ei "asentoon": `kuri:25`, käyttäjä säätää, valmis =
`KURI_END reason=switch`, paine KURI-riveiltä, `kuri:0`.

## Tarkoitus ja raja

Skooppi `infra expresso` kattaa eXpresso-kahvikeittimen (Silvia + Raspberry Pi Pico 2 W):
laiteohjelmiston, BLE-yhteyden, kehitystyökalut ja uuttoparametrit. Se irrotettiin skoopista
`infra iot` 19.9.2026, koska eXpresso-aineisto oli kasvanut isommaksi kuin koko IoT-tietopaketti
(`KEHITYSYHTEYS.md` 1055 riviä vs. `iot-tietopaketti.md` 29 riviä) ja purku joutui lukemaan
päärekisterin luvut sen vuoksi.

Rajan ulkopuolella: muu IoT (Home Assistant, IR-kaukosäädin, Bosch 6100i) pysyy skoopissa
`infra iot`, ja verkko-, palvelin- tai tietoturva-asiat skoopeissa `infra verkko|linux` ja `infra`.

## Tila 19.9.2026 — lähteet, ei kopioita

Tämä rekisteri ei kopioi alla olevien tiedostojen sisältöä, vaan nimeää ne. Rivimäärät mitattu
19.9.2026 (`wc -l`).

| Lähde | Rivejä | Mitä sisältää |
|---|---|---|
| `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md` | 235 | **luetaan joka purussa**: käyttäjän tilaukset, laitetiedot, turvarajat ja menetelmäohjeet lainauksina **23.9.2026:** Todettu 23.9.2026: Tunnettu viive (TILAUS-I:n lähde): ohituskäskystä pudotukseen 42 ms (sd 9 ms), pumpun sammutuksesta 38 ms (sd 7 ms), todellinen viive ~37–41 ms. **23.9.2026:** Käyttäjän päätös 23.9.2026: paineista, kuristimen asennosta tai kiinteästä bar-tavoitteesta ei kysellä testien esiehtoina; nousu päättyy tasanteeseen (paine ei enää nouse); Käyttäjän päätös 23.9.2026: ritilä paikallaan, kaukalovahdin raja wmax:720. **24.9.2026:** käyttäjän menetelmä kuristimen lämmitykseen: tavoite = tasanteen keskipaine jatkuvalla pumpulla, valmis kun duty_avg ≥ 0,95 3 s (pumppua ei rajoiteta); käyttäjän tilaus askeleen 1 jälkeen: tehdään ensin 2,5 barin säätö kuntoon → seuraava paketti esiuuton 2,5 barin säätö (TILAUS-K vaiheet 1–2). **26.9.2026:** Käyttäjän päätös 26.9.2026: kaikki laiteajot vain 2,5 barin pidolla (ei 8 barin uuttoa) kunnes esiuutto hyväksytty (ajot pico_dev.py hold 5); Käyttäjän päätös 26.9.2026: kaukaloa ei tarvitse tyhjentää joka ajolla (painoraja wmax 720 riittää); ajon hyväksyntä kysyy vain läsnäolon ja säiliön veden; Käyttäjän päätös 26.9.2026: himmennyksen oltava PID-tyyppinen → D-termi esiuuttoon (valinta: ensin esiuutto, 8 barin himmennys avoimessa asiassa 24, nousun PID hylätty). **26.9.2026:** Käyttäjän ohjeet 26.9.2026 (luku 6): testit tehdään TILAUS-H-purun jälkeen (pakkautunut paine ei todellinen tilanne); lähes kiinni -kuristin ei ohjaa suunnittelua liikaa → tau-lattia poistettu (kääntö avoimesta lähes kiinni yliarvioi yhden ajon, malli over 0,43 → 0,86). |
| `Infra/iot/expresso/KEHITYSYHTEYS.md` | 1055 | kehitysyhteys, BLE-protokolla, työkalut, mittaukset **23.9.2026:** Todettu 23.9.2026: Palvelin ei tavoita Shellyä (192.0.2.21) suoraan vaan ohjaus kulkee HA:n kautta; Macilta puuttuu ~/.config/ha/token, joten laturikierto antaa CHARGER FAILED. **23.9.2026:** Oletusreitti dispatch.mjs ei kelpaa Infra-briefeille; sallittuja ajajia vain toteuttaja-sonnet ja toteuttaja-opus (rd model.md); Päätös: main.py kuuluu jatkossa laitekomentobriefien may-listaan (kytkentä take_*_request-kyselysilmukkaan; ei build_set.py:n generoima). **26.9.2026:** palvelin on itse OnePlus-puhelin (`adb devices -l`: 127.0.0.1:5555, 192.0.2.11:5555, emulator-5554, OnePlus7TPro HD1911). |
| `Infra/iot/expresso/konteksti-virtaussaato.md` | 147 | virtaussäädön konteksti |
| `Infra/iot/expresso/PICO-HALLINTA.md` | 144 | Picon hallinta ja flashaus **23.9.2026:** Todettu 23.9.2026: Laturi päällä (Shelly on) puhelin latautuu (sink, PD 3 A), mutta USB2-hubi ja Pico irtoavat; laturi pois kytkettäessä Pico palautuu ~2 s (source/host); Todettu 23.9.2026: Käyttäjän testaamaton hypoteesi, jonka mukaan Picon irtoaminen laturin kytkennässä johtuisi alhaisesta akkutasosta (66 %, raja 70 %); Päätös 23.9.2026: Laturikierto on väliaikainen ja poistetaan, kun Type-C-vika on selvitetty; Päätös 23.9.2026: Shellyn Wi-Fi-verkoksi valittu IOT_SSID (sama VLAN kuin HA, ei palomuurisääntöjä). **26.9.2026:** Todettu 26.9.2026: pit on rajattu 6 s:iin (pico/commands.py:281), joten pelkkä tshot:<n> ei estä uuttoa. |
| `Infra/iot/expresso/pico/`, `testit/`, `paketit/` | — | laiteohjelmisto, testit, paketoidut ajot **23.9.2026:** Todettu 23.9.2026: q1–q4-analyysi (depth_bar vaiheittain 0,77–1,06 bar, sd 0,39–0,63, ANOVA F=0,65; depth_bar korreloi slopen kanssa r=0,85; perustaso ka 6,69–7,70 bar); Todettu 23.9.2026: Taukovälit Picon kellolla ka 301,2 ms (sd 2,96–3,25 ms, min–max 300–312 ms), viive vaiheikkunaan ka 1,2 ms kaikissa neljässä ajossa; Todettu 23.9.2026: Käsketty vaihe ei ollut verkkovaihe, koska firmware ajasti taukoja kiinteällä PCAP_MAINS_US=19960 µs ilman seurantaa (ajautuma 14,8 s:ssa 18–22 ms ≈ 1 jakso); F=0,65 ei kerro vaiheen vaikutuksesta; Päätös 23.9.2026: Verkkoajoitus toteutetaan sisäisellä kellolla ja paineesta korjaavalla lukolla (VERKKOKELLO.md); tauon jälkeen ajetaan täysiä jaksoja kunnes lukko palaa. **23.9.2026:** todettu: paineväreilyn vaihekohina mitattu täyden pumpun kaappauksista: 1 jakso 571–1441 us, 8 jaksoa 295–616 us, 32 jaksoa 98–402 us; tasanteessa korrelaatio 0,65 (hidas vaellus); vaihe perusaallosta (yliaallot eivät auta); simulaatio: PI-lukkosääntö (\|e\|<400 us) antaa luvan vain 14–25 % käyntiajasta (10 s tauon virhe p95 2,1–9,3 ms). KF3 lukkorajalla 1000 us: lupa 85 % käyntiajasta, väärä lupa 0,16 %, virhe p50 120–133 us / p99 448–900 us, lukko palaa 0,48 s:ssa, käynnistysvirhe p95 0,5 s → 0,5–0,7 ms ja 10 s → 2,8–5,2 ms; lukkorajalla 208 us lupa 0 %; kaksitilainen KF ylivarma rampissa; Käyttäjän päätös 23.9.2026: kellon lukkoraja `LOCK_US` = 1000 us (¼ vaiheaskelta 208 us ei saavutettavissa mitatulla kohinalla); tarkistetaan, kun SSR-40DA:n tyyppi on selvillä; Käyttäjän päätös 23.9.2026: jaksoarvion rajan 19 950–20 050 us osuma on tapahtuma `VKELLO_TRAJA`, ei vika (vika vain vakiotaajuudella alueen sisällä). Hylätty: vika kuten suunnitelma tai marginaalin levennys; Päätös 23.9.2026: menetelmän PI-silmukka korvattu kolmitilaisella Kalman-suotimella (vaihe, jakso, jakson muutos), lupa kellon omasta vaihe-epävarmuudesta (2,5·sd < LOCK_US) ennustettuna tauon yli (TILAUS-B, TILAUS-I, TILAUS-J); viiveen 37–41 ms epävarmuus vakio-offsetina kellon kehyksessä. **23.9.2026:** laitetesti: lukittuna z_us-hajonta sd a 950 us, b 785 us, d 889 us (simulaatio 295–616 us); lukko=1 myös ikkunoissa, joiden \|z\| > LOCK_US 1000; laitetesti: VKELLO_RESTART z1_us tauon mukaan (a/b/d): 0,5 s −588/−646/−274 us, 1 s +987/−448/−1415 us, 2 s +1123/+87/+1181 us, 5 s +3756/+3883/+3874 us; 5 s tauon virhe järjestelmällinen ~3,8 ms ja ylittää LOCK_US:n; laitetesti: VKELLO_END hz a 50,0256 (14:40), b 50,0220 (14:41), d 49,9837 (14:46); c 49,9909 ei konvergoitunut (6 s); verkkotaajuuden muutos 0,04 Hz 5 minuutissa; laitetesti: VKELLO_RISE a plateau 4,96 bar reach_ms 19243 (katto 20000 ms), b 4,95 bar 2000 ms, c 6,29 bar 2000 ms, d 8,46 bar 9158 ms; vkello ei pura painetta ennen ajoa (TILAUS-H); laitetesti: verkkokellon amplitudisignaalin mediaani 0,32–0,43; testit: turva_pika_smoke 1 failed (main.py dev_run-komentoja 11 eikä 10, 3ce72b3 lisäsi vkellon); muut smoket 0 failed. **23.9.2026:** lokit vkello-20260923-a/b/d: 5 s tauon +3,8 ms ei ole kellovirhe, vaan paineen uudelleennousun väreilyviive 3,5–5,3 ms (palautuu ~0,8 s, amp 1,0–2,5 bar); Väärät lukot olivat transientin aiheuttamia todellisia kellovirheitä (ilman porttia max 3,3–5,0 ms, 6–10 lukittua ikkunaa > 1000 us/ajo); Lukittu z-hajonta 785–950 us johtuu enimmäkseen 5 s -segmentistä; ilman sitä vakiotilan sd 476–514 us (sim 295–616), loput \|z\| > 1000 us kohinaa (~2σ); Portilla (replay): lukittuja virheitä > 1000 us 0/ajo (max 540–760 us), hylätty 11–17 ikkunaa/ajo, lupa 77–82/~120 ikkunaa; lukkosääntöä (2,5·sd < LOCK_US) ei muutettu; korjaus on mittauksen transienttiportti suhteellisella rajalla (GATE_RATIO 2,0, GATE_MAX 20); Lupaosuudelle ei asetettu hyväksyntärajaa, replay raportoi sen INFO-rivinä. **24.9.2026:** vkello-b: hz 50,0192, vakiotilan jäännöksen sd 371 us, lupa 87/181; nousunopeusanalyysi: viive −154 us per bar/s (R² 0,29), luokat 2–4 bar/s −613, 4–7 −961, 7–12 −1091 us, ≥ 6 bar nousevana −387 vs vakiona +19 us; noususta opetettu kello 3,6–6,8 ms väärässä; replay ilman paineporttia 4 lukittua > 1000 us; vsweep-a: 10 ms tauko poistaa iskun vain 8,5–18,7 ms kellon reunasta (vaste −0,61…−0,83 bar vs 20 ms −0,85) → pumppu vetää vain toisella puolijaksolla, SSR nollaylitystyyppiä; tauot myöhästyivät 1,4–18,6 ms vanhan aikaleiman ja summien takia; kello vsweepissä: lukko 25 ikkunalla sd 314 us; yksi I/Q-ikkuna taukojen välissä sd ~390–470 us, 22/66 taukoa lukkorajan yli; PumpPressureController käyttää 17 ms askelta ja painekeskiarvo 16,7 ms (mitattu verkko 50,0 Hz, TILAUS-L 20 ms); käyttäjä hyväksyi laitetestin 3 kahdella sarjalla; päätös: nousun ikkunat eivät opeta kelloa (learn=False), paineportti pidetään eikä kiinteää nousunopeuskorjausta tehdä firmwareen. **26.9.2026:** Havainto 26.9.2026: nousu näkee pumpun G:n eikä vuotoa; tarve vaihtelee kuristimen asennon mukaan (tau_obs 9–19 s), EU_TAU_S 1,8 ei toimi kaikilla asennoilla; Laiteajot 26.9.2026 (esiuff2/esiuff3): edellisen pidon tiedolla pidon 2 s keskiarvo 2,53–2,61, resetin jälkeen asetuksista 2,522 (sd 0,068); 1. ajo ilman tietoa 2,59–2,76; Mallipyyhkäisyt 26.9.2026: nousunopeuden kohina antaa ff:lle sd ~0,05 ja valintavinouman −0,04 (pidempi ikkuna ei auta); D-termi KD 0,05 pienentää kohinaisten ylitystä (max 0,64 → 0,53), KD 0,1 pahentaa; Smoke-testit 26.9.2026: esiuutto-smokessa 4 hylättyä kohinan/vaiheen vuoksi (sd 0,103, viive 0,38, kohinaiset parit), muut functions-smoket hyväksytty; Todettu 26.9.2026: pidon alussa ~0,1 bar ylitys myös ff = tarve -tilassa (katkaisun jälkinoususta/rampista); Päätös 26.9.2026: pidon ff vuodosta edellisestä pidosta, ensimmäinen ajo alakanttiin (tau 2,5–19 s); hylätty pelkkä nousun arvio, pelkkä opittu ff ja pidempi regressioikkuna. **26.9.2026:** laitetodennus (esiavoin1, hold 5 × 3, kuristin auki): purku 2 sykliä, lepopaine −0,93…−1,05, täyttö 3,5–6,7 s; aa (1. ajo) ff 0,15, tarve 0,71, pidon 0–2 s p5 2,19, 2–5 s 2,50 (todentaa integraalikaton 0,71 > 0,15 + 0,45); ab ff 0,60, 0–2 s 2,42; ac ff 0,57, 0–2 s 2,46, 2–5 s 2,51; kaukalo 564 g ac:n jälkeen; malli (12 siementä): avoin 0–2 s 2,33 → 2,49, 1. ajo 2–6 s 2,27 → 2,48; lämmin → kylmä +0,015 → +0,045 (3/24 yli ±0,1), kylmä → lämmin −0,025 → −0,039; pelkkä integraalikatto pareissa sama kuin HEAD; esiuutto_smoke: 3 failed (tapaukset 8 ja 9 1. ajo lämmin, 9 kohina kylmä → lämmin −0,13; HEAD 2 failed); muut smoket 14/14 vihreät. **26.9.2026:** Uuttojen siirto puhelimeen ei käytössä nykyisellä firmwarella (`grep brew_log pico/` vain kuollut stubi `classes.py:81`); `pim` on vain RAMissa (`commands.py:301-307`), nollautuu resetissä ja flashissa, joten uutot ajavat vanhaa esiuuttoa. |
| `Infra/paarekisteri.md` §4.6, §6 | 8 vikariviä + §6-rivit | siirtämättä, ks. SEURAAVA PAKETTI |

(21.9.2026:n TURVAKATO-selvitys ja PIKAKORJAUKSET: `HISTORIA.md` 21.9.2026.)

## Todettu 22.9.2026 — EXPRESSO-TURVA-TOIMILAITE (koodissa, ei flashattu)

- TURVAKATO-korjauslistan kohta 1 tehty: uusi `pico/relayguard.py` (`RelayGuard`, `GuardedRelay`).
  `BrewData.get_relays()` antaa pumpun ja lämmittimen vartioituina; raakapinnejä ei ole oliossa.
  Jokainen `value(1)` kysyy `allow()`:lta, ja `machine.Timer` (100 ms) pakottaa releen pois ajon
  aikana myös silmukoissa, jotka eivät anna vuoroa.
- Rajat (kaikilla poluilla, myös käyttäjän omilla): `dev_safe` → pumppu ja lämmitin pois; paine
  > 13,0 bar 3 kyselyä peräkkäin (vartio lukee ADC:n itse) → pumppu pois; pumpun ajo > 180 s →
  pois, kunnes polku lakkaa pyytämästä 5 s:ksi; kattila ≥ 160 °C (anturivika 200) tai lukema
  > 10 s vanha → lämmitin pois; vartion oma virhe → kaikki pois pysyvästi (uudelleenkäynnistykseen).
- Kaukalo ei ole vartiossa (käyttäjän raja 19.9.2026). Testikomentojen kaukalovahti ajon aikana:
  `pstep`/`pgap`/`plen` kutsuvat `functions.tray_guard_poll`:ia ~1 s välein; se lukee vaa'an itse
  (`main.scale_poll_once` → `brew_data.scale_poll`), koska `scale_reader` ei pääse ajoon.
- Kuumavesisilmukka lukee lämpötilan 1 s välein (muuten tuoreusraja sammuttaisi lämmittimen).
- Testit: `testit/turva_toimilaite_smoke.py` 34/34 ok (A: lähteen grep-tarkistus, 28
  päällekytkentää; B: vartio valelaitteilla; C: kaukalo ajon aikana). Mutaatiotarkistus: vartio
  pois + raakapinni backflushiin → 6 FAIL. Vanhat 9 smokea 0 failed (`psweep_dryrun.py`:n
  valelaite sai `scale_poll`:n). `py_compile` ok. `mpy-cross` puuttuu, laitteella ajamatta.

## Todettu 22.9.2026 — EXPRESSO-ANTURIUSKOTTAVUUS (TURVAKATO kohta 5, koodissa, ei flashattu)

- Samaan vartioon (`pico/relayguard.py`): paineanturin raakalukema < -1,5 bar (irti/oikosulussa
  ≈ -3,5) 3 kyselyä peräkkäin → pumppu pois (palautuu, kun lukema on taas uskottava). Lämmitin
  päällä 120 s päälläoloaikaa, kun kattila on > 5 °C alle tavoitteen ja pumppu pois, eikä lukema
  noussut 2 °C → lämmitin pois uudelleenkäynnistykseen asti (`GUARD_TRIP heater reason=norise`).
- Ei havaittavissa: paineanturi jumissa uskottavassa 0 barissa (kuumavesi ja huuhtelu ilman
  kakkua pysyvät myös lähellä 0 baria pumpun ollessa päällä).
- Testit: `turva_toimilaite_smoke.py` 43/43 (D1–D9: rikki anturi, 30 min pito tavoitteen
  lähellä, lämmitys kylmästä, kuumavesi, anturi irti kattilasta); mutaatiossa 3 FAIL; vanhat 9
  smokea 0 failed. Laitteella tarkistamatta: mitä irrotettu paineanturi oikeasti lukee.

## Todettu 25.9.2026 — EXPRESSO-ESIUUTTO-PITO (luvut: `paketit/VAIHESEURANTA.md`, kaksi viimeistä lukua)

- d/e-heilunta oli 100 ms hajontaa (autokorrelaatio 0,18/0,05), ei 2–3 s aalto. Laite nousudatasta:
  iskukoko ~0,1 bar, vuoto τ 1,5–1,8 s lämpimänä, kylmänä 0,15 bar / 2,2 s ja pidon duty ~0,15 (lämmin 0,30).
- esiupito1 a/b: pidon p5 sd 0,11/0,09 (d/e 0,17/0,16). esiupito2 c (kylmä): katkaisusta pitoon 0,6 s ilman
  notkahdusta, pidon alussa +0,44 bar väärän ff:n takia (malli: syy ff, ei ramppi).
- Mittari: pito ~2,5, uutto ~7–8 bar = anturi työalueella oikein. `.claude/settings.json`:ssa ei OHJEVAHTI-hookia.

## Todettu 26.–27.9.2026 — EXPRESSO-ESIUUTTO-VUORONVARAUS (luvut: `paketit/VAIHESEURANTA.md`, luku "Vuoronvaraus")

- Syy (an, euv:0): automaattinen roskienkeruu — keko täynnä 0,5–0,8 s:ssa (~500 kt/s), keruu 15–28 ms; toinen lähde `iq_close` + VKELLO 10–11 ms (ap:n ainoa late 661 ms). `gc.mem_free()` maksaa 7,3 ms, käytetään siksi vain ajon alussa/lopussa.
- Korjaus (`euv:1` oletus): asyncio-vuoro vaiheessa 2 vain, kun rele on pois ja seuraava jakso on tauko; hallittu `gc.collect()` 300 ms välein; `iq_close` vasta ≥ 12 ms päähän seuraavasta päätöksestä, jos rele on päällä.
- Laitteella (aq–as, 27.9.2026): ei yhtään EU_STALL-riviä `rel=1`, hallittu keruu 18–19/ajo (15,1–16,0 ms); late/miss al 3/6 → aq 0/1, ar 0/1, as 0/0.
- Jäljellä oleva ylitys tulee rampin lopusta (kylmä kuristin, isku +0,35–0,45 bar): ao 1105→1207 ms p5 2,03→3,15; ar kaksi iskua p5 2,24→3,07, tau_obs 14 s. Kellon lukko jää saamatta pienellä tarpeella (aq, as: windows 5, sd_us 12 ms, 20 ms tauot). **27.9.2026 EXPRESSO-ESIUUTTO-RAMPIN-LOPPU (651afec, isännällä, ei flashattu):** syy kaasujousto (isku ∝ abs. paine², malli toistaa ao–as:n vain sillä); ramppi valmis jälkinousun jälkeen, pito alkaa kaistalla, kaasujousto rampin vahvistukseen; smoke 15 ylitys 0,50/0,55 → 0,38/0,40; kellon lukko ei korjattu (heikot ikkunat harhaisia) — luvut `paketit/VAIHESEURANTA.md` "Rampin loppu".

## Todettu 27.–28.9.2026 — EXPRESSO-UUTTO-8BAR (TILAUS-K vaiheet 3–4, laitteella todennettu 28.9.2026, kuri:25)

- 8 barin malli lokeista esiuutto-20260924-b…e, 20260925-a…c, 20260926-b (TS-nousu ja -pito): nousu 2,5→7,2 bar
  mediaani 9,5 bar/s (2,9…21, 32 paria); jousto vakio + kaasu/p_abs², c0 0,03 (rms 2,91 vs. puhdas kaasu 3,30);
  vuoto ~p^0,8 (vanhan säätimen pidon keskipaineen rms 0,19 bar); malli toistaa vanhan uuton ~1 bar pudotukset
  (min 6,1–6,6, laite 6,5–6,8). Isku 8 barissa 0,34–0,93 (mediaani 0,76) bar, tarve 8 barissa 0,26–1,01. Viivettä
  ei sovitettu (data ei riitä) → TILAUS-I 37–41 ms.
- Kello: täysi nousu opettaa harhaisesti (−0,6…−1,1 ms nousunopeudesta riippuen, ajojen välinen hajonta ~850 us);
  alle 2 bar/s nousevat ikkunat harha +8 / +128 us. Siksi vaiheissa 3–4 opettaa vain ikkuna, jonka keskipaine
  nousi < `EB_CLK_RATE` 2 bar/s: täysi nousu gate=−1, rampin loppu lukitsee ennen pitoa.
- Smoke uusi vs. vanha uutto (bim:0), mallin todellinen paine 100 ms: 16 ylitys +0,12/+0,16 vs +0,74/+1,04; pidon
  1. s pudotus ka −0,29 vs −0,57; pito 2–5 s −0,03…−0,02 vs −0,15…0; 17 kuristimen kääntö 0,3→0,6→0,2 kaistalle
  0,60/0,69 s vs 2,3/2,6 s; 18 kellon sd pidon alussa ≤ 1061 us, 10 ms tauot 100 % (ilman vaiheiden 3–4 oppia
  9,7–13 ms, 20 ms tauot 70–83 %); 19 vv=1 late 0 (vv=0 4–13); 20 esiuuton arvot ennallaan, 2. ajo käyttää
  eb_*:ia; 21 siirtymärivit 20 ms välein. Tapaukset 1–15 tavulleen HEADin tuloste. Muut smoket rc=0 (klamp, mcal,
  ohjevahti, phold, pskip_gate, psweep_mult, psweep, scale_rate, tray_guard, tray_total, turva_pika,
  turva_toimilaite, vkello_rise, vsweep, verkkokello_holdout) — ali-agentin raportti.
- Laiteajo 28.9.2026 (setti 20260928-uutto8a, kuri1–kuri6, kaikki RESTORE_OK + VERIFIED 19/19; repon
  `pico/MANIFEST.json` = kuri6), kaikki pim:1, 8 barin uutto: bim:1 pitää 8 bar kaikilla kuristimen asennoilla
  (ylitys puolet bim:0:aan verrattuna), lähes kiinni -kuristimella (tarve 0,04) molemmat tavat sahaavat (isku
  +1,5–1,8 bar):

  | ajo | kuristin | tapa | tarve | ylitys | pito ka ± sd |
  |---|---|---|---|---|---|
  | a, b | lähes kiinni (tarve 0,04) | bim:1 | 0,04 | +1,07/+1,31 | 8,12±0,57 / 8,17±0,51 |
  | c | sama | bim:0 | – | +2,00 | 8,35±0,39 |
  | a2, b2 | avattu | bim:1 | 0,28 | +0,29/+0,65 | 7,995±0,14 / 8,000±0,19 |
  | c2 | sama | bim:0 | – | +1,00 | 8,15±0,57 |
  | a3, a4, a5 | 8 bar @ kuri:24/25 | bim:1 | 0,48/0,48/0,52 | +0,30/+0,20/+0,33 | 7,995±0,26 / 8,000±0,18 / 7,999±0,25 |
  | c3 | 8 bar @ kuri:25 | bim:0 | – | +0,50 | 8,04±0,63 |
  | d1 | 7,1 bar @ 25 | bim:1 | 0,36 | +0,15 | 7,997±0,08 |
  | d2 | 9,25 bar @ 25 | bim:1 | 0,39 | +0,59 | 7,993±0,12 |

  d1:n tarve 0,36 < odotettu 0,6: kylmä kuristin päästää vähemmän (sama havainto kuin 27.9.). `GUARD_TRIP heater
  reason=tempstale` esiintyi 8 barin pidossa kaikissa bim:1-ajoissa ja c2:ssa (bim:0), a4:ssä jo esiuutossa
  (bar 2,3): lämpötilaa ei lueta 10 s (relayguard `HEATER_TEMP_STALE_MS` 10000) → lämmitin estetty pidon loppuun
  (seuraava paketti EXPRESSO-TEMPSTALE-JA-OLETUS). Verkon taajuus vaihteli päivän aikana 50,06 → 49,90 Hz
  (EB_END2 T_us 19976,9 … 20038,5). Kellon lukko pienellä tarpeella (EXPRESSO-ESIUUTTO-VUORONVARAUS) todennettu
  laitteella.
- **29.9.2026, kaikki 12 uuttolokia:** ajo b:n esiuuton hyppy (17,3 bar/s, huippu 4,82 bar) johtui lähes kiinni
  kuristimesta (tarve 0,04), ei firmwaresta; 3× a:ta nopeampi nousu selvittämättä; ei "säiliön täyttö".
  ≥ 20 g ajot (bim:1): pito ka 7,96–8,04, 0,5 s liukuvan ka:n sd 0,07–0,13, 100 % ajasta 8 ± 0,5 bar; bim:0 c3 7,10–8,84,
  80 % sisällä → uusi säädin 3–5× vakaampi. Vettä; luvut `HISTORIA.md` 29.9.2026.

## Todettu 28.9.2026 — EXPRESSO-KURISTIN-SAATO (`kuri:<n>` iskua/s -komento, TILAUS-M)

- Uusi komento `kuri:<n>` (TILAUS-M, `pico/commands.py`, `pico/main.py`, `pico/functions.py`
  `throttle_set_run`): uuttonappi ajaa pumppua n iskua/s (1–50) ilman paineensäätöä; `kuri:0` = normaali uutto;
  RAM only. `BrewData.get_pressure()` (`pico/classes.py`) juoksevalla summalla listan sijaan (kuri3) — korjaa
  MemoryError-kaatumisen (ks. Viat, vika 14). `pico_dev.py restore <set> [seconds]` oletus nyt 420 s (kuri1
  ylitti 300 s ~1 kt/s). `EU_END2`/`EB_END2` tallentavat `brew_data.mains_T_us` (opittu verkkojakso).
- kuri-säätötilan vika ja korjaus: nollaylitys-SSR + diodipumppu → isku = ohjaus päällä aktiivisen puolijakson
  nollakohdassa Z (Z = kellon reuna + ~18,6 ms, vsweep-a). kuri2–5 kytkivät vaihetta tuntematta: kuri5 late
  ~3/s, lmax 15,7–16,9 ms (hallittu keruu) → käyttäjä kuuli tupla- ja puuttuvia iskuja. kuri6 (efed272): kytkentä
  lukittu verkon vaiheeseen Verkkokellolla (täysi sykli kunnes 2,5·sd < 5 ms, sitten päätös kellon reuna + 8 600 us
  = `KURI_OFF_US` = `EU_OFF_US` − 5000), yksi raskas työ (iq_close / gc / asyncio-vuoro) per ajallaan ollut päätös
  (`KURI_SKIP_US` 2 ms), purkusykli (`_mcal_vent`) alussa ja lopussa; `KURI_END` kirjaa `lock_ms`, `win`, `learned`,
  `err`, `lmax`. Laitteella (kuri6): err=0, lmax 5,0–5,9 ms, 25,0 iskua/s, 200 ms keskiarvot 9,19–9,35 (kuri5
  8,8–9,6) — käyttäjä: "Tasainen". Smoke-ohjauskoe päätöksillä Z:ssa: 150 väärää iskua.
- kuri-säätötila ilman purkua jätti kattilaan 12,7 bar (lämpölaajeneminen suljetussa kattilassa) → seuraava
  käynnistys ylipainerajaan; kuri5+ purkaa alussa ja lopussa. Raaka `PCAP_OVER_BAR` 11,0 laukeaa kuri:25:llä, kun
  suodatettu paine on ~9,7 bar (piikit ~+1,4) — lähellä rajaa, rajaa ei muutettu (Päätökset, vika 15).
- Kuristin lopuksi (istunnon lopussa): 8,14 bar @ kuri:25 (`testit/kuri-20260928-k-8bar.log`).
- `testit/kuri_smoke.py` uudelleen esiuutto_smoke-harnessilla (virtuaaliaika, nollaylitys-SSR, keruu 15–28 ms,
  varaukset): 31 tarkistusta, 0 failed; esiuutto/klamp/tray_guard/turva_toimilaite/vkello_rise smoke 0 failed.
  `KAYTTAJAN-TIEDOT.md` luku 2c: TILAUS-M lisätty loppuun.

## Todettu 28.9.2026 — EXPRESSO-TEMPSTALE-JA-OLETUS (toinen ydin valittu, koodissa, ei flashattu)

- Juurisyy (ennallaan): `run_shot` sammuttaa lämmittimen alussa, `main`-silmukka ei lue lämpötilaa
  `run_shot`in aikana, ja `pre_infusion_phased` (vaiheet 1–4) ei lue sitä lainkaan → vaiheen 3
  ensimmäinen lämmitinpulssi (EB_HEAT 100/50 ms) osuu yli 10 s vanhaan lukemaan (relayguard
  `HEATER_TEMP_STALE_MS` 10000) ja on estetty koko uuton ajan. bim:0 (vanha uuttosilmukka, lukee
  2 s välein) on estetty vain ensimmäiset 2 s.
- **Vertailu tehty ja ratkaistu: toinen ydin valittu, pilkottu luku hylätty ja poistettu**
  (`git apply -R` commit c658f99:n `pico/functions.py`- ja `pico/classes.py`-hunkeille). Syy:
  kaikki pilkotut variantit heikensivät pumpun ohjausta systemaattisesti (ks. smoke-diagnoosi
  alla), toinen ydin ei kosketa pumppusilmukkaa lainkaan.
- Smoke-diagnoosi (scratchpad, `Max31865.COST_US` vaihdellen pilkotulle luvulle): kustannus
  0 → tapaus 10 OK (+0,054), tapaus 14 ajo 2 FAIL 4/8; 500/500/500 → FAIL 9, 9 kohina (10/24),
  10 (+0,066); 2000/1000/700 → FAIL 10 (+0,067), 14 (3/8). Perustaso ilman anturimallia: 0 failed,
  tapaus 10 +0,029, tapaus 14 piikki ka 0,589/0,584. Syy: smoken `Utime.ticks_us` lisää 20 µs/kutsu,
  joten jo "ilmainen" askel siirtää kohinatoteumaa; tapaus 10 on todellinen kustannusvaikutus
  (näytekato). Kaikki pilkotut variantit nostivat tapauksen 14 piikkiä 0,61–0,625:een.
- MicroPython v1.28.0 lähteestä (GitHub-tagi v1.28.0) varmistettu: `py/scheduler.c` ajaa ajastetut
  takaisinkutsut vain pääsäikeessä (ei GIL:iä); `py/mpstate.h` `gc_lock_depth` on säiekohtainen
  (`heap_lock` ytimellä 1 ei lukitse ydintä 0); `ports/rp2/mpthreadport.c` `core1_entry_wrapper`
  kutsuu `multicore_lockout_victim_init`, oletuspino 4096; `ports/rp2/rp2_flash.c` pysäyttää ytimen
  1 flash-kirjoituksen ajaksi.
- Uuden koodin (toinen ydin) smoke 28.9.2026: `esiuutto_smoke` RESULT 0 failed (tapaus 10 +0,029,
  14 = perustaso), `turva_toimilaite_smoke`, `kuri_smoke`, `klamp_smoke` 0 failed. `shot_test.py`
  kaatuu `AttributeError: 'BrewData' object has no attribute 'eu_g_pre'` — sama HEADillä
  (vanhentunut feikki, ei tämän muutoksen, ks. Viat).
- Smoke ei mallinna säiettä itseään (GC-kilpailu, SPI-ajoitus, BLE): ne todennetaan laitteella.
- MAX31865 SPI on 50 kHz (`machine.SPI(0, baudrate=50000)`), joten yksi 2–3 tavun siirto ≈
  0,4–0,6 ms + Python-kuorma; `read_rtd` jättää biasin päälle.

## Todettu 5.10.2026 — Picon yhteys kulkee Zeron kautta; uuttoloki-setti flashattu (EXPRESSO-ZERO-FLASH)

- Pico on Zeron USB:ssä (`/dev/hubi0`, 2e8a:0005), silta 192.0.2.10:2217 raw (ser2net, `Infra/iot/zero/REKISTERI.md`). `pico_dev.py` oletus `PICO_LINK=zero`: `flash`/`manifest` Zeron kautta, `restore` ja `build_set.py` vain puhelinketju (669d3bb). Pico ajaa repon `pico/`-settiä (uuttoloki + valmiustila + ENOMEM-korjaus, 6aff448); laitteella FLASH_OK, vakaa 3+ min, `CMD_OK pcal:st`, `stby:30` → `temp=102.0`.
- rp2 MicroPython v1.28: ENOMEM = oletusajastinpooli täynnä (`alarm_pool_add_alarm_in_us` −1), keko ei syy (gc 309 632 vapaana). Korjaus: core 1 käynnistyy releevahdin ajastimen jälkeen; tarkka mekanismi todentamatta (REPL: nukkuva tai heap_lock-säie ei estänyt Timeria).
- Zeron ser2net-ansa (3×): Picon uudelleenenumeroinnin jälkeen raaka 2217 mykkä, kunnes `/dev/hubi0` avataan kerran Zerolla; `pico_dev.py` herättää sillan itse. Syy oletettu (DTR/`local`). Pehmeä reset (Ctrl-D) vahdin ollessa päällä → laitteistovahti nollaa Picon.
- Paineanturi ei kerro verkkovirrasta Zero-kytkennässä: GPIO28 raaka päällä avg 10764 (−0,133 bar), pois 10835 (−0,111), ero alle kohinan (min–max ~700); vanha −0,77 oli puhelin-OTG-ajalta 17.9. (kalibroidut lokit verkkovirralla purun jälkeen −0,83…−1,0 bar). Picossa ei ole verkkovirran tunnistuspinniä (releet 11–13, MAX31865, PRESSURE_ADC 28). pcal voimassa gain=1,0000 offset=−0,990.
- Isäntätestit 18/18 (`testit/*smoke*.py`; `turva_pika_smoke` 0 failed e4b9afa:n jälkeen). Todisteet: `testit/flash-20261005-zero*.log`, `HISTORIA.md` 5.10.2026.

## Todettu 5.10.2026 — valmiustila äppiin (a741d90, e89d205)

- Laitteella (pystynäkymä, uiautomator): `stby:on` → `STBY_ON idle_s=0 target=90`, Mode `IDLE · STANDBY`; `stby:30` → `STBY timeout_min=30 standby=0 temp=102.0`, Mode `IDLE`; asetus palautettu 30 min. Smoke 0 failed, paketti 228 B. Sovellus (Mac, ei repoa) `flutter analyze lib` 0 virhettä, `flutter test` 26/26. Keitin oli verkkovirrasta pois (kattila 25,9 °C), Pico Zeron USB-virralla.

## Todettu 6.10.2026 — V-154-syy (9103dc2 flashattu 3f8abc8)

- Syy: kylmä flash irti verkosta (32fb76e:n tunnettu raja); korjaus `relayguard.user_retry()` + `heat?`; 18 smokea exit 0. Lisää: `HISTORIA.md` 6.10.2026.
- Pico ajaa 9103dc2:n settiä (korvaa cae9100:n): manifesti d6d1ddb; Zero-flash FLASH_PLAN 3/20, VERIFIED 20/20, FLASH_OK (`testit/flash-20261006-zero-v154syy.log`, 3f8abc8); smoket 0 failed.
- `pico_dev.py cmd 'heat?' 6` flashin jälkeen (keitin verkossa, lämmin): `HEAT temp=100.29 target=102.0 heater=0 dead=0 retries=0 guard=ok`. Vanha firmware ei raportoinut mitattua lämpötilaa; `heat?` heti flashin jälkeen tarvitsee drainin ≥ 6 s (3 s palautti tyhjän).
- Isäntätestit 6.10.2026 (aa77c57, 25f5634): `ctrl_real_test.py` rc=0, `shot_test.py` `RESULT: 0 failed`, `pico_dev_link_smoke.py` `LINK_SMOKE OK 4/4`, `pico_dev_lukko_smoke.py` `LUKKO_SMOKE OK 4/4`; `pico/` puhdas. `shot_test.py` repon firmwarea vasten ennen korjausta: `user_retry` puuttui valelaitteesta (`classes.py:436`), eli 9103dc2 ei ollut testikattavuudessa. `pico_dev.py` Link: `until` käyttää `marker in buf`, `Link.reopen()`, `LINK_REOPEN` tyhjällä raw REPL -aikakatkaisulla (laitteella todentamatta). Lisää: `HISTORIA.md` 6.10.2026.

## Todettu 7.10.2026 — V-154 todennettu aamutestissä (Zero-linkki)

- Kylmäkäynnistys 06.11–06.15: 25,6 → 105,2 °C ~3 min (heater=0 tavoitteen 102 ylityksen jälkeen), dead=0 retries=0 guard=ok koko ajan; `proven=0` myös ylityksen jälkeen (merkitys tarkistamatta). Ensimmäinen `cmd 'heat?' 6` Zero-linkillä tyhjä, `cmd 'heat?' 10` heti perään toimi. PICO-DEV-LINK (aa77c57) ei todentunut (Zero-linkki, uudelleenavaus koskee puhelinsiltaa). Luvut: `HISTORIA.md` 7.10.2026.

## Todettu 7.10.2026 — kuumavesiraja flashattu ja laitetodennettu; Picon nollaukset; nollausikkuna

- Flash Zerolla b466b19: FLASH_PLAN 2/20 (functions.py, main.py), VERIFIED 20/20, FLASH_OK (`testit/flash-20261007-zero-kuumavesi.log`); MANIFEST oli jäänyt päivittämättä aa3bb8c:ssa. Laitetodennus 520ef47: kuumavesikytkin → pumppu pysähtyi ~1 s:ssa (käyttäjä), `HOT_WATER_END reason=time`; `heat?` heater=0 guard=ok temp=101.61 (`testit/kuumavesi-20261007-laite.log`).
- TURVAKATO kohta 7 laitteella (d56d07e): mekaaninen varoventtiili on olemassa (käyttäjä); 3 Picon nollausta (`testit/nollaus-20261007-laite.log`): wmax 720/wrise 250 säilyi, releet [0,0,0], keitin ei reagoinut; `asyncio.gather`-poikkeus päättää ajon 310 ms:ssa, finally ajetaan, releet [0,0,0] (`testit/gather-20261007-laite.log`). wmax-nollautumisen syy koodista: `save_settings` kirjoittaa ei-atomisesti (`pico/functions.py` ~3125), `load_settings` poistaa koko tiedoston virheessä (~3192–3200); pelkkä nollaus ei laukaise.
- Picon spontaanit nollaukset: Zeron `journalctl -k` 51 `USB disconnect` 5.–7.10.2026, ~1–2 h välein myös yöllä; 7.10. 11.45.54 ja 13.41.39 ilman työkaluajoa; traceback puuttuu (sarjalähtöä ei tallenneta). Zero: ser2net 2217 raw ja 2218 rfc2217 `/dev/hubi0` 115200, avaa laitteen vain asiakkaan yhdistäessä.
- Nollausikkuna: releet 0:aan vasta `main.py:3` (`devsafe.relays_off()`); ennen sitä MicroPython-käynnistys ja `boot.py`, joka ei koske relepinneihin. `devsafe.py`:n kommentti "boot drives the relays off before anything else" ei päde boot.py:hin.

## Päätökset

- **5.10.2026:** valmiustila erillisenä live-paketin avaimena `standby`, ei mode-merkkijonona: sovellus vertaa `'IDLE'`-arvoon uuton päättymiseksi (`machine_data_notifier.dart:216,227,385`). Hylätty asetuspaketti (päivittyy vain 2 s välein ja muutoksessa) ja `import utime` -siirto (ei oikeuta flashia).
- **Käyttäjä 28.9.2026 (anturin luku uutossa, AskUserQuestion):** "sinun pitää tarkkaan itse
  miettiä paras vaihtoehto. pumpun ohjaus on prioriteetti mitä lämmön ohjaus ei saa rikkoa. jos
  lämpötila luku onnistuu esim pilkkomalla se lyhyisiin lukuihin se toteutetaan". → Pilkottu luku
  toteutetaan (vahdin ylilämpö-/tuoreusraja), mutta se ei saa heikentää pumpun ohjausta: smoken
  2 FAILia on selvitettävä ennen hyväksyntää. Pääistunnon arvio: pilko askeleet yksittäisiin
  SPI-siirtoihin (~0,5 ms) tai ajoita ne heti näytteen jälkeen niin, ettei 1 kHz:n painenäytteitä
  jää väliin; vertaa sitten smoke samoilla siemenillä.
- **Käyttäjä 28.9.2026:** "sitä voi myös miettiä että voiko lämpötilan luvun siirtää samalle
  corelle kuin bluetooth on" → seuraavan paketin ensimmäinen vertailu: lämpötilan kokonainen
  (blokkaava) luku toisella ytimellä (RP2040, `_thread`; `BrewData` on "Class to share data between
  the cores"), jolloin pumppusilmukka ei pysähdy lainkaan eikä pilkkomista ehkä tarvita. Tarkista:
  toisen ytimen kuorma (BLE), jaetun tilan päivitys (`boiler_temperature` + `_ms`), ettei SPI(0)/
  MAX31865:tä käytä kaksi ydintä, ja relayguardin Timer-kutsu. Valitse tämä tai pilkottu luku sen
  mukaan, kumpi ei heikennä pumpun ohjausta.
- **Pääistunto 28.9.2026 (käyttäjän kriteeri "pumpun ohjaus on prioriteetti"):** toinen ydin
  valittu (RP2350 core 1, `_thread`): pumppusilmukka ei tee lämpötilatyötä lainkaan. Hylätty
  pilkottu luku (smoke-heikennys todistettu, ks. Todettu 28.9.2026 yllä). Ydin 1 lukee vain
  `run_shot`in ajan (ei aina): pääsilmukan ja termostaatin ajoitus ennallaan (ne luottavat 75 ms:n
  blokkaavaan lukuun). Ydin 1 allokoimatta `heap_lock`illa: satunnainen GC ytimellä 1 voisi
  pysäyttää pumppusilmukan.
- **Pääistunto 28.9.2026:** lämmitystehon ohjaus virtauksesta (TILAUS-N, `KAYTTAJAN-TIEDOT.md`
  luku 2d) on oma pakettinsa EXPRESSO-LAMMITYS-VIRTAUS, ei tempstale-korjauksen osa.

- **Käyttäjä 28.9.2026 (TILAUS-M, KAYTTAJAN-TIEDOT):** kuristin säädetään aina paineeseen pääistunnon asettamalla
  `kuri:<n>`-syklillä (8 barille 25 iskua/s), ei kierroksina; valmis = `KURI_END reason=switch` + paine
  KURI-riveiltä, ei sanallista kuittausta; testiuutot etänä vain ilmoitettuna ja käyttäjän kuitattua valmiuden.
- **Pääistunto 28.9.2026:** kuri-kytkentä toteutettiin Verkkokellolla eikä PWM-laitteistolla — PWM olisi vaatinut
  relayguardin (turvakoodi) muutoksen eikä silti tiedä nollakohdan vaihetta (liukuma ylittää Z:n ~25 s välein).
- **Pääistunto 28.9.2026:** `PCAP_OVER_BAR` 11,0 ei muutettu (vika 15: käyttäjän päätös).

- **Esiuutto hyväksytty** (27.9.2026, käyttäjä): 651afec (setti 20260927-rampinloppu1), ajot at–aw: ylitys 0,08–0,32,
  pito 2,45–2,55; seuraavaksi 8 bar (EXPRESSO-UUTTO-8BAR). Kellon lukko pienellä tarpeella: käyttäjä valitsi (a) vapaa
  kello matalan tarpeen pidossa, lukitus vaiheen 3 nousussa; hylätty (b) laitemittaus ensin.
- **8 barin laiteajot sallittu jälleen** (27.9.2026, käyttäjä, esiuuton hyväksynnän myötä): normaali läsnäolo +
  vesi -hyväksyntä riittää; 26.9.2026:n rajoitus "vain 2,5 barin pidolla kunnes esiuutto hyväksytty" ei ole enää
  voimassa.

- **Käyttäjä 28.9.2026:** seuraava paketti = 8 barin laiteajo (EXPRESSO-UUTTO-8BAR jatkuu). Hylätyt:
  EXPRESSO-UUTTOLOKI ensin, ei seuraavaa pakettia.
- **Pääistunto 28.9.2026:** vaiheet 3–4 samaan silmukkaan eikä erilliseen funktioon (kello ja vuoronvaraus
  jatkuvat); oma RAM-valinta `bim` A/B-vertailua varten.
- **POIKKEAA (28.9.2026):** käyttäjän valinta (a) "lukitus vaiheen 3 nousussa" toteutuu vain nousun hitaassa
  lopussa (< 2 bar/s), ei täydellä nousulla — täyden nousun ikkunat ovat harhaisia (ks. Todettu 27.–28.9.2026).
- **28.9.2026:** vaiheissa 3–4 asyncio-vuoro ja keruu sallitaan myös releen ollessa päällä ja seuraavan jakson
  iskiessä (muuten tarpeella 0,69 ei yhtään vuoroa → vaaka/BLE nälkiintyvät); olettaa pysähdyksen < 40 ms
  (laitteen pisin mitattu 28 ms).

- **Ei-nouse-raja lukitsee uudelleenkäynnistykseen asti** (22.9.2026, pääistunto): irronnut
  anturi ei korjaannu itsestään; väärä laukaisu maksaa vain virrankatkaisun.

- **Vartion rajat löysemmät kuin polkujen omat** (22.9.2026, pääistunto): 13,0 bar = korkein
  polkuraja, 180 s > `phold` 120 s ja `pgap`-katto 120 s. Vartio on viimeinen linja; polkujen omat
  rajat pysyvät ja laukeavat ensin, joten mikään nykyinen ajo ei katkea aiemmin kuin ennen.
- **180 s:n pumppuraja koskee myös kuumavesikytkintä.** Se ei ole kohdan 19 (kuumaveden aika- ja
  lämpöraja, käyttäjän päätös) ratkaisu, vain perälauta; tiukempi raja on yhä käyttäjän päätös.
- **Ajastin eikä asyncio-tehtävä**: `pstep`/`pgap`/`plen` eivät anna vuoroa 14–58 s. 100 ms eikä
  20 ms, jottei vartio hölkytä 1 kHz:n kaappausta; kaukalon luku kaappaussilmukassa maksaa ~1 ms
  kerran sekunnissa (yksi myöhästynyt näyte).

- **Lämpötilaraja asettajiin eikä vain `bt:`-komentoon**: raja toimilaitteen asetuksen vieressä,
  jotta mikään polku ei ohita (TURVAKATO kohta 2 -periaate).
- **`pgap`-ajolle ajonaikainen katto komennon rajan lisäksi**; 120 s = `PHOLD_MAX_S`, pisin
  hyväksytty testiajo.
- **`tshot` ja kahvikytkinpolku jätettiin `dev_run`:n ulkopuolelle**: `run_shot` käyttää
  lämmitintä tarkoituksella.
- **Jaksonpituuden korjaus 60→50 Hz siirrettiin vaiheeseen 1a3 ja ajetaan yhdessä vaiheen 1c
  aktuaattorityön kanssa.** Perustelu: korjaus yksin kaataa `flow_ctrl_sim.py`:n väitteen, eikä
  säädintä kannata virittää uudelleen simulaatiota vasten ennen mittausta. Korjaus tehdään
  **yhtenä lähteenä**, ei viitenä literaalina. Verkkojakso `PCAP_MAINS_US = 19960` jätettiin
  omaksi vakiokseen, ei johdettu `step_ms`:stä: viiden 60 Hz -vakion yhdistäminen on tämä sama
  vaihe 1a3.
- Vaihe 1c supistuu kysymykseksi ohituskuviosta (mitkä iskut päästetään läpi), ei sytytyskulmasta,
  jos SSR-40DA vahvistuu nollaylityskytkeväksi.
- Asettuminen on **tapahtumaohjattu, ei aikaohjattu**, ja mittauksen aika lasketaan tavoitteen
  saavuttamisesta (käyttäjän vaatimus). `PCAP_HOLD_MS = 3000` johdettu: 3·tau = 2,42 s +
  suodattimen viive 0,3 s.
- Setinrakennus skriptattiin ennen ensimmäistä flashia (käyttäjän valinta), koska sama kuuden
  askeleen käsityö toistuu vaiheissa 1b–1f.
- **Vaihe 1b jaettiin kolmeen briefiin** (phold, portitus, analysaattori) yhden sijaan, koska
  edellinen kierros osoitti yhden ison briefin kalliiksi. Ne ajettiin peräkkäin, ei rinnakkain,
  koska kunkin hyväksyntä tarkistaa `git status`:n koko skoopin yli.
- **Jokaiselle briefille kirjoitetaan suunnittelijan holdout ennen dispatchia.** Peruste on
  mitattu: ilman holdoutia 1B1 palasi vihreänä vaikka komento olisi kaatunut laitteella,
  holdoutin kanssa 1B2 ja 1B3 menivät läpi yhdellä kierroksella.
- **Analysaattori ei päättele portitusta datasta** vaan vaatii sen lokin otsikosta (`gate=on`).
  Suunnittelijan alkuperäinen spec-väite ("portittamaton data antaa conf < 2,0") kumottiin
  mittaamalla ennen dispatchia.
- **Kaukalovahti koskee testejä, ei käyttäjän omaa uuttoa** (käyttäjä 19.9.2026: "vaaka sääntö ei
  koske omaa ajoa vaan testejä"). `run_shot`:n kytkinpolku jätettiin koskemattomaksi, koska
  vaa'alla on silloin kuppi. Vahti on tiukka: ajo ei käynnisty lainkaan, jos vaaka ei vastaa,
  lukema on yli 2 s vanha tai rajaa ei ole asetettu.
- **Turvaominaisuuden katoamisen selvitys tehdään myöhemmin**, ei nyt (käyttäjän päätös).
- **Vaa'an lukutahti 20 ms → 50 ms** (käyttäjän päätös 19.9.2026, commit `b3cf54f`). Pyydetty 1 s
  ei ollut mahdollinen: `FLOW_MIN_POINTS=4` näytettä ei mahdu `FLOW_WINDOW_MS=1000` ikkunaan
  sekunnin tahdilla, ja `FLOW_STALE_MS=500` palauttaisi `flow`:n `None`:na jo yksinään — virtaus­-
  säätö, 2 ml/s kalibrointi ja `max flow rate` olisivat jääneet ilman mittaria. 50 ms nappaa yhä
  jokaisen näytteen (anturi 11,6/s eli 86 ms väli) ja keventää herätykset 2,5-kertaisesti. Ehto on
  nyt tarkistettavissa: `testit/scale_rate_smoke.py`.
- **Ehdosta tehtiin tarkistettava invariantti**, ei kommenttia. Peruste on tämän saman session
  `TURVAKATO`-löydös: vain kommentissa elävä ehto katoaa, kun joku muuttaa naapurilukua.
- **Rekisteriä muokattiin suoraan** kerran, pakkauksen jälkeen syntyneen päätöksen takia. Jos
  tämä toistuu, oikea ratkaisu on pakata uudelleen eikä totuttautua suoraan muokkaukseen.
- Toimintapisteeksi hyväksyttiin käyttäjän valinnalla 9,37 bar paketin "noin 8 bar" sijaan, koska
  kaikki viisi vaihesiirtoa ajettiin samasta asennosta.
- `pico/MANIFEST.json` päivitettiin repoon puhelimen manifestista eikä käsin laskettuna, koska
  puhelimen `sha256sum` on se lähde, jota palautus itse tarkistaa.
- **Kuristimen käsin tasapainotus (sääntö 7) ei ole vaiheiden 1b-1f ehto**: trimmausaskel tekee
  sen koneellisesti. Käyttäjän päätös: "Ei pitäisi olla ratkaiseva tekijä vaiheen testauksessa
  mikä paine on tarkasti".
- **SSR-40DA:n kyljen tarkistus poistettiin tehtävistä** (käyttäjä: "Ei näillä ole väliä kun
  vaste kuitenkin joudutaan mittaamaan testaamalla"). Jälleenmyyjien speksit sanovat mallin
  nollaylityskytkeväksi, vasteaika 8,3 ms, mutta samaa tunnusta myydään random turn-on -versiona.
- Säännön 5 suure (B) on 0-9,98 ms, ei 0-19,96 ms: nollaylityksiä on kaksi verkkojaksossa.
- TILAUS-H:n lopetusehto on menettelyssä: jaksotus jatkuu kunnes lasku syklin yli alle
  `PCAP_PLATEAU_BAR` 0,15 bar. Suunnittelijan ehdottamaa kiinteää 0,3 barin rajaa ja 10 kierroksen
  kattoa ei toteuteta.
- Vaihe 1g rajattiin mittaukseen ja `mcal`-komentoon; kytkentä esiuuttoon on vaihe 1h, ja
  TILAUS-G täyttyy vasta sen jälkeen.
- **Vaiheen 1b viive mitataan yhdellä ohitetulla syklillä, ei portituksella.** Portitettu
  pyyhkäisy ei pidä painetta yllä (12,5 % teho), ja sen trimmaus purkaa painetta, jota portitettu
  pumppu ei palauta. Yksi ohitus jatkuvan pumppauksen keskellä antaa saman viiveen ilman tätä.
- **Syvyysmittarin trendinpoiston ikkuna on neljä verkkojaksoa, ei yksi.** Yhden jakson ikkuna
  jaettuna kahtia mittaa väreilyä eikä trendiä: mitattu `slope = −0,036 bar/näyte` eli 36 bar/s,
  ja syvyys jäi nollaksi.
- **Isäntäanalysaattorissa käytetään kausaalista suodinta**, ei keskitettyä. Keskitetty ikkuna
  näkee tulevaisuuteen ja havaitsi pudotuksen 7–8 ms ennen kuin se tapahtui — tappava virhe, kun
  mitattava suure on 40 ms.
- **`pvent` on oma komentonsa.** `mcal` ei kelpaa purkukomennoksi, koska se käynnistää pumpun heti
  purun jälkeen ja kumoaa itsensä.
- **Korjausjärjestykseksi valittiin ensin KAUKALOVAHTI-KOKONAISPAINO**, ei suositellut
  pikakorjaukset (käyttäjä 21.9.2026); pikakorjaukset jäivät SEURAAVAKSI paketiksi.
- **`pcal` jätettiin kaukalovahdin ulkopuolelle**: se on sovelluksen kalibrointivelho, ja sen
  kuuluminen testikomentoihin on käyttäjän päätös.
- **Kahvikytkin ja kuumavesikytkin jätettiin koskematta** (käyttäjän omat polut,
  `KAYTTAJAN-TIEDOT.md` luku 5); kuumavesikytkimen aika-/lämpöraja on käyttäjän päätös.
- **Flashaus lykättiin käyttäjän päätöksellä** 21.9.2026: KOKONAISPAINO-koodi on valmis,
  laitteelle viemättä.
- **25.9.2026:** PI-viritys (EU_KP 0,2, EU_KI 0,3) ennallaan (ei vaikutusta sovitetussa mallissa); pidon viimeisiä
  0,1–0,2 bar ei kiirehditä (ylitys pahempi kuin hitaus). Hylätyt vaihtoehdot perusteluineen: `paketit/VAIHESEURANTA.md`
  (myöhästymisrajan löysennys, `EU_YIELD_US` 9–12 ms, rampin alku huipusta, rajaamaton rampin ff, ennakko 0,2 s).

- **26.9.2026:** Käyttäjän päätös 26.9.2026: 1. ajolle (ei edellisen tietoa) omat smoke-rajat — rampin viive ≤ 0,5 bar (ajo 2 pysyy 0,3), pidon 2 s ka −0,15…+0,1; kohinaisten parien osuus rajan ulkopuolella ≤ 1/3, muut 25 %. Hylätyt: rajat ennallaan (smoke pysyvästi punainen) ja rajat ennallaan + säätimen paketti.

- **26.9.2026:** Käyttäjä 26.9.2026: ei kääntänyt kuristinta ac:n (19.51) jälkeen → kylmän kuristimen virtausero on todellinen. Käänsi ennen af:ää "aika lähellä uuttoa" -asentoon.

- **26.9.2026:** Käyttäjä 26.9.2026: "Korjaus ensin" — laiteajot loppuivat illalta; korjaus isännän mallissa, hyväksyntä laitteelta korjauksen jälkeen. Hylätyt: lämmitys auki-asennolla ja kääntö takaisin tänään; `hold 6` nykyisellä asennolla.

- **26.9.2026:** Pääistunto: G-skaalaus ei mene firmwareen ennen kuin malli toistaa af/ag:n rajasyklin (malli ensin).

- **26.9.2026:** Käyttäjä 26.9.2026 (ah–ak jälkeen): "Avaa kuristinta, 2 ajoa" — hylätty "Hyväksy esiuutto nyt" ja "Ei enempää tänään".

- **26.9.2026:** Käyttäjä 26.9.2026 (al–am jälkeen): "Korjaa ensin piikit" — ei hyväksyntää; seuraava paketti: rele ei saa jäädä päälle vuoronvarauksen ajaksi, sitten uusi hyväksyntäajo. Hylätyt: "Hyväksy esiuutto" (piikit erilliseksi korjaukseksi) ja "Vertaa vanhaan ensin" (esiavoin1 A/B samalla asennolla).

- **26.9.2026:** Pääistunto: KD_G 0,3 / KD_G_HOLD 0,1. Hylätty D pois pidosta (smoke 10 +0,006 → +0,056, raja 0,06; smoke 1 sd 0,098, raja 0,1), KD_G 0,2 (smoke 9 kohina lämmin → kylmä 12/24 ulkona), KD_G 0,5 (malli: jakso 0,31–0,40 jäi). Katkaisun portti p5 ≥ ¼ tavoite ennallaan (täytön kohina, esiuutto-20260924-c).

- **26.9.2026:** VAATIMUS: TILAUS-L Seuraavan paketin peruste: vaimennuksen askel on yksi jakso, ja releen päällä pysyminen varauksen ajan rikkoo sen (yksi päätös → useita iskuja).

- **26.9.2026:** Käyttäjä klo 23.1x: "Flashaa ja aja nyt" (mittaus euv:0 ensin, sitten euv:1).

- **27.9.2026:** Käyttäjä: "Flashaa korjattu" (mem_free pois) ja smoke 13:n rajasyklitarkistus normalisoidusta autokorrelaatiosta autokovarianssiin ≤ 0,3 × 0,45² bar² (hylätty: pidä ennallaan) — syy: pidon hajonta puolittui, normalisoitu luku mittasi kohinaa (3/8 yli).

- **27.9.2026:** Käyttäjä: kolmas flash, "varmista että keitin on lämmin" (tarkistettu: 103,0 °C).

- **27.9.2026:** Käyttäjä (aq–as jälkeen): "Korjaa rampin loppu ensin" — ei hyväksyntää vielä. Hylätyt: "Hyväksy esiuutto" (ylitys erilliseksi avoimeksi asiaksi) ja "Ei päätöstä nyt".

- **Käyttäjä 29.9.2026:** seuraavaksi EXPRESSO-SHOTTEST-FEIKKI (portti hylkäsi "ei seuraavaa pakettia").
  Hylätty: EXPRESSO-TEMPSTALE-JA-OLETUS-jatko (vaatii flashin).

- **5.10.2026:** Asetus RAM-tilainen (kuten pim/bim), oletus 30 min / 90 °C; save_settings ei muuttunut. Hylätty: pysyvä asetus (käyttäjä antoi kiinteät arvot).

- **5.10.2026:** Aktiivisuus = kytkin päällä tai komento, jonka `updated` on tosi; lukukomennot eivät herätä.

- **5.10.2026:** Ajaja toteuttaja-sonnet (käyttäjän valinta 5.10.2026); opus hylätty (ei eskalointiehtoa).

- **5.10.2026:** shot_test.py pidetään PI-polulla (pim:0/bim:0) eikä sitä siirretä pre_infusion_phasediin: testin kohde on painorajat, vartijat ja komennot, ja vaiheistetun polun testaa esiuutto_smoke omalla kello-/GC-mallillaan (pääistunto 5.10.2026). Hylätty: laitosmallin uudelleenkirjoitus ticks_us-pohjaiseksi.

- **5.10.2026:** load_settings: yli rajan oleva asetuslämpötila → kentän oletus säilyy, tiedosto säilyy (suunta pysyy turvallisena: rajan yli ei koskaan aseteta).

- **Pääistunto 5.10.2026 (UUTTOLOKI):** näytteet BLE-tehtävästä, ei uuttosilmukoista (ajoitus ennallaan; hylätty elokuun tick silmukoissa); ei pumpun reunatapahtumia (tila liput-kentässä); vain kytkimen uutto kirjautuu, ei TS.

- **Käyttäjä 5.10.2026:** flash hyväksytty, mutta `pico_dev.py restore` -ajo hylätty: flash kulkee Zeron kautta, ja Shelly on OnePlus-hubin laturi eikä keittimen rautaa. Hylätty: Picon siirto takaisin puhelimeen.

- **5.10.2026 (käyttäjä: "Päätä itse" → pääistunto):** järjestys (1) flash-reitti Zeron kautta (tehty 669d3bb), (2) V-154-korjaus, (3) UUTTOLOKI-LAITE-todennus. Flash Zerolla omalla raakaREPL-kirjoittimella, ei mpremotella (vahti 8 s, releluenta).

- **Käyttäjä 5.10.2026 (V-154 menetelmä):** valitsi (a) heat_dead-lukon vapautus; hylätty (b) optoerotin GPIO:hon ja (c) Picon syöttö keittimestä. Mitoitus (pääistunto): jäähtyminen ≥ 10 °C lukitushetken lukemasta todistaa anturin kattilassa → uusinta 60 s välein rajatta; ilman todistetta 3 uusintaa 10 min välein, sitten lukko uudelleenkäynnistykseen asti; uusinta lämmittää 30 s (ensimmäinen ikkuna 120 s ennallaan), joten irronneen anturin lisälämpö ≤ 3 × ~33 kJ. Tunnettu raja: Pico käynnistyy uudelleen keittimen ollessa kylmä ja irti verkosta → 3 uusintaa kuluu ja aamulla lukko on päällä → kiertotie: USB irti Zerosta illaksi tai aamulla Picon reset (`pico_dev.py safe`, toimi 6.10.2026).

- **Pääistunto 6.10.2026 (autojatko):** V-154 vapautuu vain käyttäjän toiminnosta; valvomaton kylmäkäynnistys käyttäjälle. Hylätty: hidas uusinta, pumppupulssi, lukko flashiin.
- **Käyttäjä 6.10.2026 (valvomaton kylmäkäynnistys):** nykyinen + kiertotie, ei firmware-muutosta; aamulla kytkin/sovellus (`user_retry`) tai `pico_dev.py safe`. Hylätty: hidas uusinta (lämmittäisi sokkona), pumppupulssi verkkotunnistukseen.

- **Käyttäjä 5.10.2026:** e4b9afa ja 32fb76e flashataan heti, ei odoteta seuraavaa firmwaremuutosta.

- **Käyttäjä 6.10.2026:** Zerolle pysyvä sarjaloki (toteutus `infra zero`, V-207); `pico_dev.py log` sen jälkeen.

- **Käyttäjä 6.10.2026 (expresso-ios-istunnosta):** kehitys tehdään nyt pääasiassa iOS:llä (skooppi `expresso-ios`, iPhone 15 Pro). Android-äppi `com.example.silvia_pico_ui` suljettu OnePlussassa 21.13 (`am force-stop`; `stopped=true`, ei boot-vastaanotinta, palvelua eikä hälytystä) eikä sitä käynnistetä uudelleen: `pico_dev.py:171` (silta), `pico_dev.py:672` (restore) ja `build_set.py:272` käynnistävät sen `am start`illa → kysy käyttäjältä ennen niiden ajoa ja käytä iPhonen äppiä, kun paketti vaatii sovellusta (esim. EXPRESSO-V154-AAMUTESTIN asetusmuutos). V-205 ei enää estä expresso-iosia: iPhonen BLE-testi läpäisty 21.15 Android-äppi suljettuna (connect → 180a/2a29, ei disconnectia, 31,5 °C).

- **Pääistunto 6.10.2026 (autojatko, PICO-DEV-LINK aa77c57):** sillan uudelleenavaus vain, kun raw REPL -siirtymä aikakatkeaa tyhjällä bufferilla (ei tyhjästä hello-viestistä: sillan hello-käytöstä ei tiedetä); `until` pudottaa merkin perässä tulleet tavut (raw REPL odottaa syötettä, joten ne ovat kohinaa).

- **Käyttäjä 5.10.2026:** Vaihe 1h suljettu verkkokellon korvaamana (VAATIMUS: TILAUS-F, täyttyy kellolla; POIKKEAA: TILAUS-G, vaihe nousussa harhainen). Hylätty: taajuuden alkuarvo nousun Goertzelista (~0,03 Hz, kuormittaa ajoitussilmukkaa). 1 %:n säätötarkkuus kuitattu valmiiksi; psweep-20260920-tulkintarivi suljettu vanhentuneena.

- **7.10.2026 (IDEAT-luokittelu):** IDEAT-rivi suljetaan vain commit-todisteella tai käyttäjän päätöksellä (Android-äppi suljettu 6.10.2026); muut kirjataan avoimina.
- **Pääistunto 7.10.2026 (PICO-DEV-LINK-todennus):** `PICO_LINK=phone` käynnistäisi Android-äpin (`pico_dev.py:171`), jonka iOS-päätös 6.10.2026 (0b0cca4) kieltää kysymättä → käyttäjän päätös.

- **7.10.2026:** pcal kaukalovahdin ulkopuolelle (käyttäjä 7.10.2026).

- **7.10.2026:** Kuumavesikytkin: ajoraja 1 s (käyttäjä vahvisti erikseen "Kyllä, 1 s" — kuppiin vain ~1 s vettä), ei kuivakuumennusta, termostaatti (käyttäjä valitsi kaikki kolme 7.10.2026). Kaukalon painorajaa ei lisätty (käyttäjän rajaus 19.9.: käyttäjän oma polku).

- **7.10.2026:** TURVAKATO kohta 6 kuuluu skoopille claude siirto (SIIRTO-VAATIMUS-KATOAA, TILAUS-INVARIANTIT), ei tähän.
- **Käyttäjä 7.10.2026 (VAATIMUS, ei vielä `KAYTTAJAN-TIEDOT.md`:ssä):** "Äärimmäisen tärkeää että releet ajetaan aina alas ennen toimenpiteitä jos on vaara että toimenpiteet siirtää pico pois ajosta tai pico kaatuu". Jos rele (esim. lämmitin) on päällä nollauksen alkaessa, se jää päälle, kunnes Pico asettaa sen 0:aan.
- **Käyttäjä 7.10.2026:** "korjaa picon sarjalokitus. tallennetaan zerolle" → Picon sarjaloki tallennetaan jatkuvasti Zerolle. Suunnitelma (pääistunto, ei toteutettu): Zerolle daemon, joka omistaa `/dev/hubi0`:n (avaa uudelleen uudelleenenumeroinnin jälkeen), kirjoittaa kaiken aikaleimattuna päiväkohtaiseen lokiin ja palvelee TCP 2217 raw yhdelle asiakkaalle (kick-old) `pico_dev.py`:lle; 2218 rfc2217 pois tai tcp-connectorilla daemonin kautta. Koskee Zeron palvelua (skooppi `infra zero`).
- **Käyttäjä 12.10.2026 (AskUserQuestion, hyväksytty):** `infra expresso` jaetaan yläskoopiksi `expresso` ja neljäksi alaskoopiksi: `expresso turva` (relayguard/devsafe, nollausikkuna ja releet alas -vaatimus, PCAP_OVER_BAR, kaukalovahti/wmax, kuumavesirajat, V-154, TURVAKATO), `expresso säätö` (PUMPPU-PWM, verkkokello, vaiheseuranta, esiuutto, 8 bar, kuristin, virtaussäätö; KEHITYSYHTEYS.md ja paketit/), `expresso laite` (pico_dev.py, flash/MANIFEST, Zero-linkki ja sarjaloki, PICO-HALLINTA.md, MemoryError ja spontaanit nollaukset), `expresso integraatiot` (BLE, HA/MQTT, uuttoloki äppiin, valmiustila, huoltotoiminnot; raja skooppiin expresso-ios). Pääskooppi: KAYTTAJAN-TIEDOT-vaatimukset, käyttöönottoketju, alaskooppitaulukko. Syy: rekisteri 507 riviä (Päätökset ~210), KEHITYSYHTEYS.md 1072 riviä; pakkauksen vaihe 2 kaatui 12.10.2026 muistin loppuessa (383 Mt vapaana). Nimi `expresso <ala>`, koska `luo-skooppi.mjs` tukee vain kaksiosaisia nimiä; hylätty `infra expresso <ala>` (vaatisi työkalumuutoksen).

- **14.10.2026:** Ikoniksi 4 Espresso (käyttäjä 14.10.2026), vain iPhone; Android ennallaan.

- **14.10.2026:** Käyttäjä perui /pakkaa-komennon kerran 14.10.2026 ja pyysi asentamaan ikonin ensin.

- **14.10.2026:** Pakkauksessa käyttäjä valitsi "Ei seuraavaa — pakkaa vain" ja portin hylättyä (skooppi-polusta.mjs exit 4: heti ajettavat EXPRESSO-TURVAKATO, Uutto rikki, wmax-pysyvyys) "Pakkaa vain silti": rivi kirjoitetaan "ei mitään", portin ristiriita kirjattu V-381 → claude siirto (ed4a07c). Heti ajettavat rivit pysyvät rekisterissä ennallaan.

- **20.10.2026:** Diagnostiikan siirto UDP:llä palvelimen keräimeen (käyttäjä: "valitse itse"); hylätty MQTT (HA:ssa ei brokeria, TCP voi pysäyttää silmukan) ja HTTP-webhook.

- **20.10.2026:** Käyttäjä: minuuttikooste lämmittimestä ja paineesta HA:han (DIAG_MIN).

- **20.10.2026:** WIFI-APPI P1 (käyttäjä): "Lokit homeassistant mutta äpin yhteys suoraan iphone" → suora UDP (ei TCP-palvelinta Picolle); P2: BLE-aukot korjataan ensin. Ketjut hyväksytty kerralla (flash, reititin, asennus).

- **20.10.2026:** Käyttäjä 20.10.2026: Wi-Fi-rajaus kohdat 1–3; "Ensin otetaan bluetooth toistaiseksi pois päältä picoa hidastamasta"; mittaus agentin laiteajolla.

- **20.10.2026:** Kohta 4 (virransäästö `wlan.config(pm=…)`) jätettiin pois (käyttäjän valinta).

- **20.10.2026:** GC: käyttäjä valitsi "Vain suunnitelma"; sitten "Tehdään automaattinen siirto jonka jälkeen mietitään perusteellista korjaus keinoa".

- **20.10.2026:** Käyttäjä 20.10.2026: GC-UUTTO vaihtoehto 1; jatkuva viivemittaus HB:hen; vahtikoe sallittu (vahti tauolla 30 s, lämmitin ja pumppu pois); TILAUS-O "ehdoton vaatimus"; toteutus "Jaksot ytimelle 1"; lämpötila "Ydin 1 välienä"; tyhjä päätösjono "Pysäytä uutto virheeseen"; vaihe 1 aloitettiin; "Selvitä 1 ms ja pakkaa".

- **20.10.2026:** Pääistunto: jono 2 jaksoa (40 ms) mallin ja kuivakokeen perusteella; jono täytetään keruun molemmin puolin ja ennen ensimmäistä jaksoa; vahtikoe toteutettiin `paused`-lipulla eikä Timerin pysäytyksellä (uusi `Timer(-1)` voi saada ENOMEMin, main.py 5.10.2026). Hylätyt: GC-UUTTO vaihtoehdot 2 (1 kHz kokonaisluvuiksi ytimellä 0) ja 3 (jäädytetyt moduulit) tarpeettomia, kun ajoitus siirtyy ytimelle 1.

- **20.10.2026:** Käyttäjä: C1-JAKSOT vaihe 3 uudessa sessiossa (suunnitelma 60d77e4); laiteajo kysytään erikseen.

- **20.10.2026:** Käyttäjä 20.10.2026: vaihe 4 "Toteutetaan"; ylityksen vertailu vanhaan polkuun ja kuristimen käännön vertailu ovat esiuutto_smoke 24:ssä tulosteita, ehdottomat rajat tarkistuksia ("laite ratkaisee").

- **20.10.2026:** Käyttäjä 20.10.2026: lisävertailut ennen oletusta → sarja 2 → "Ota käyttöön ja pakkaa": c1x oletus 1 (177e83a), c1x:0 = vanha polku RAM-valitsimena.

- **20.10.2026:** EB_C1X_KP_TAIL 0,2 (pidon 1. s:n P c1x:llä). Hylätty mallissa: virheen ennuste jakson eteenpäin (ylitys kasvoi).

- **20.10.2026:** Käyttäjä 20.10.2026: kuristimen säätö aina TILAUS-M:n mukaan, ei "asentoon" (muistutus rekisterin alussa).

- **21.10.2026:** Käyttäjä 21.10.2026: IDLE 5 s jaksot; ±0,05 mitataan 10 s keskiarvoista; PI-säätö; thermal stability −10…+10 laskentatavalla opittu vakioteho = 0, kylmäkäynnistys = −10 (hyväksytty AskUserQuestion); järjestys: uuton lämmitys ensin; toteutustapa iskuista + itsekorjautuva kerroin hyväksytty; kalibrointi sekä testikahvalla että oikeilla uutoilla; täytön katto + k 67,5.

- **21.10.2026:** Käyttäjä: "ylilämpeneminen on huomattavasti hitaampi korjata" → oppi suosii vajetta. Höyry poistaa vettä → opit eivät opi vajaan kattilan ajalta.

- **21.10.2026:** Kerroin kirjoitetaan Picolle väliaikaisella flash-setillä (repo-manifestiin ei lisätä brew_heat.json:ia, ettei flash kirjoita opittua yli).

- **21.10.2026:** Käyttäjä 21.10.2026 (AskUserQuestion): "Sovita malli laitteeseen (suositus)" — hylätty "Hyväksy −0,9 °C transientti".

- **21.10.2026:** Käyttäjä 21.10.2026 (AskUserQuestion): "Flashaa, testi myöhemmin" — huuhtelutesti seuraavan uuton jälkeen; hylätty "Flashaa nyt, huuhtelen" ja "Ei nyt".

- **21.10.2026:** BH_HOLD_LEAD_S = 50 (pyyhkäisy 40/50/60/75).

- **22.10.2026:** Käyttäjä 22.10.2026 (AskUserQuestion): "Agentti kirjoittaa" — pcalset 0,8511 / +0,349 suoraan laitteelle; hylätty "Ei vielä". Velhoa (pcal:run) ei käytetty, koska käyttäjä antoi kaksi mittaripistettä.

- **24.10.2026:** Käyttäjä 24.10.2026: Höyrytyksessä venttiilin avaamisen tunnistus omaksi ominaisuudekseen (steam valve trigger), ja lisäksi steam valve release lopettaa teholämmityksen paineen palauduttua.

- **24.10.2026:** Käyttäjä 24.10.2026: Korkein prioriteetti maksimilämpötilalla/paineella, seuraava minimipaineella (täysi teho), alin tavoitelämpötilalla.

- **24.10.2026:** Käyttäjä 24.10.2026: IDLE- ja alkulämmitystilassa painetta tasataan 30 s välein 100 ms solenoidipulssilla, jos paine poikkeaa +-0.5 bar; täsmennys: ei tasata jos lämpötila on >= 0.1 °C yli tavoitteen.

- **25.10.2026:** Esiuuton pisarantunnistimesta poistettu CUSUM, koska vaa'an kohina (sigma ~0.25 g) kerrytti akkumulaattoria ja aiheutti ennenaikaisen laukeamisen. Tilalle suodatettu kynnys kahdella näytteellä.

- **25.10.2026:** Ytimen 1 nälkärajaksi asetettu 35 ms ja GC-etumatkaksi 42 ms; iq_close() estetty GC-kierroksilla.

- **25.10.2026:** Uuton uudelleenkäynnistyminen estetty odottamalla fyysisen kytkimen kääntämistä pois päältä.

- **25.10.2026:** Paineentasaukselle (PEQ) toteutettu toggle switch äppiin ja lepotilalle painike "Siirry lepotilaan", joka nousee heti StandbyOverlay-näkymään.

- **26.10.2026:** Säädöt jaettu 5 suljettuun ExpansionTile-ryhmään (Fast heatup, Preinfusion, Brew, Steam, Sleep), jotta päänäkymä pysyy kompaktina ilman jatkuvaa pitkää scrollausta.

- **26.10.2026:** Päänäkymän scroll-fysiikaksi valittu SafeBouncingScrollPhysics, joka eliminoi palautusvaiheen kineettisen ylityksen ja poistaa kimpoamisvian säilyttäen natiivin iOS-tuntuman.

- **26.10.2026:** Lepotilassa päänäkymää ja säätimiä voi käyttää vapaasti sulkemalla StandbyOverlay X-napista. Herätyspainike sijoitettu asetusryhmien yläpuolelle helppoa herätystä varten.

- **26.10.2026:** Valmiustila-asetukset siirretty äpin Asetukset-näkymästä säätöjen Sleep-osioon.

- **Käyttäjä 26.10.2026:** 8 uutta jatkotehtävää rekisteröity:
  1. Äpin päätilassa yhteyskuvake oletuksena harmaa Wi-Fi, punainen vasta 20 s kuluttua jos yhteys ei löydy.
  2. Keittimen tila IDLE vasta kun lämpötila asettunut kohdalleen; heilahteluvaiheessa stabilizing; reilusti alle warming up; yli cooling down.
  3. Tare-nappi suoraan painolukeman alapuolelle.
  4. Älykäs painon ja kaukalon tunnistus (kaukalon vesi, tyhjennys sammuksissa, kupin ja ulkoisen vaa'an tunnistus kaukalolla).
  5. Vaakatilassa ei numeroita lämpötilalle/paineelle (näkyvät graafissa) eikä yhteyden/lepotilan symboleita.
  6. Vaakatilassa freeze-nappi pienempi ja pyöreä, tekstin sijaan play/pause-symbolit.
  7. Vaakatilassa graafi ottaa tilan paremmin haltuun.
  8. Flow-virtauksen piirto graafiin.

- **26.10.2026:** arm 2 -pidon laitetodennus (EXPRESSO-VAPAA-VIRTAUS) kuitattu valmiiksi mittaustodisteiden perusteella.

- **26.10.2026:** Valmiustila-asetukset siirretty äpin Asetuksista säätöjen Sleep-osioon.

- **26.10.2026:** Rekisteröity käyttäjän 8 jatkotehtävää (äpin yhteysikoni 20 s timeoutilla, keittimen lämpötilatilat, tare-napin sijoitus, älykäs painon/kaukalon tunnistus, vaakatilan karsinnat ja pyöreä freeze-nappi, graafin tilankäyttö, virtauksen flow-piirto).

- **26.10.2026:** Toteutettu ja todennettu äpin päänäkymän ja vaakatilan uudistukset (EXPRESSO-APPI-UI-UUDISTUKSET, Mac `silvia_pico_flutter_UI`):
  - Äpin yhteyden oletuskuvake: oletuksena harmaa Wi-Fi, muuttuu punaiseksi 20 s kuluttua jos yhteyttä ei löydy; vihreä yhteyden muodostuessa (Wi-Fi/BT). Napautus aloittaa haun ja nollaa aikalaskurin.
  - Tare-nappi: sijoitettu suoraan painolukeman alapuolelle oikeaan reunaan.
  - Vaakatilan elementtien karsinta: piilotettu T- ja P-lukuarvot (näkyvät graafissa) sekä lepotila- ja yhteysikonit.
  - Vaakatilan pyöreä freeze-nappi: pienempi pyöreä painike play/pause-symboleilla (Icons.pause_rounded kun piirto käynnissä, Icons.play_arrow_rounded kun pysäytetty).
  - Vaakatilan graafin tilankäyttö: optimoitu vaakasuuntainen ja pystysuuntainen tilankäyttö tiivistämällä reunoja ja akselien varauksia.
  - Flow-virtauksen piirto graafiin: lisätty Flow-lukemalle oma käyrä (Colors.tealAccent) reaaliaikaiseen graafiin ja MachineStatukseen (flowData).
  - Kaikki 98 yksikkö- ja widget-testiä hyväksytty puhtaasti (flutter test). Todennettu simulaattorilla (iPhone 15 Pro expresso) ja otettu kuvakaappaukset.

- **26.10.2026:** EXPRESSO-APPI-UI-UUDISTUKSET toteutettu ja todennettu.

- **26.10.2026:** Toteutettu ja todennettu keittimen lämpötilatilat (EXPRESSO-LAMPOTILATILAT, KAYTTAJAN-TIEDOT.md §9 kohta 2):
  - `pico/classes.py`: lisätty `BrewData.is_idle()`, `BrewData.update_temperature_mode()`, `IDLE_MODES = ('IDLE', 'idle', 'warming up', 'stabilizing', 'cooling down')` ja kynnysarvot `TEMP_WARMUP_DEFICIT_C = 2.0`, `TEMP_COOLING_SURPLUS_C = 0.5`, `TEMP_SETTLE_BAND_C = 0.5`, `TEMP_SETTLE_TIME_MS = 10000`, `TEMP_SETTLE_MAX_SPEED = 0.5`.
  - Tilasiirtymät:
    - `warming up`: kattilan lämpötila > 2.0 °C alle tavoitteen.
    - `stabilizing`: lähestymis- tai heilahteluvaiheessa (alle 2.0 °C alituksesta +0.5 °C ylitykseen ennen kuin ehto IDLE täyttyy 10 s ajan tai kun lämpötilan muutosnopeus on liian suuri).
    - `IDLE`: lämpötila pysynyt tavoitteen kohdalla (±0.5 °C kaistalla) yhtäjaksoisesti vähintään 10 sekuntia ja muutosnopeus on vakaa (≤ 0.5 °C/10 s). Hystereesi (0.6 °C) estää tilojen värinän rajalla.
    - `cooling down`: lämpötila yli tavoitteen (> 0.5 °C tavoitteen yläpuolella, esim. höyrytyksen tai ylilyönnin jälkeen).
  - `BrewData.set_mode('IDLE')` ohjaa tilan suoraan `update_temperature_mode()`:n kautta. Aktiiviset uutto-, höyrytys- ja huoltotilat (`BREW`, `STEAM`, `WATER`, `DEV_SAFE`, `BACKFLUSH_*`) eivät ylikirjoitu.
  - `Thermostat.run()` ottaa huomioon kaikki `IDLE_MODES`-tilat (lämmitys ja lepotilamittaukset toimivat saumattomasti). TILAUS-P lepotilamittaus pysyy puhtaana transienttien aikana.
  - `main.py`: päivitetty `scale_cal`-kutsu käyttämään `brew_data.is_idle()` ja lisätty lämpötilatilan päivitys pääsilmukkaan ennen termostaattia sekä höyrykytkimen vapautukseen.
  - `MANIFEST.json`: päivitetty vastaamaan koodimuutoksia.
  - Testit: luotu `testit/lampotilatilat_smoke.py` (36/36 testiä ok, RESULT: 0 failed), kattaa kaikki 4 tilaa, siirtymät, hystereesin, lepotilatavoitteen muutoksen, aktiivitilojen suojauksen ja telemetrian (`live_payload`). Kaikki olemassa olevat smoke-testit hyväksytty (termostaatti, valmiustila, steam_paine, kuumavesi, turva_pika, turva_toimilaite).

- **26.10.2026:** EXPRESSO-ALYKAS-PAINO toteutettu ja todennettu.
  - `pico/smart_tray.py` (`SmartTrayTracker`): kaukalon veden kertymä, tyhjennyksen tunnistus sammuksissa (`emptied_offline` ja `tray_state.json`), kupin (~293.9 g), ulkoisen vaa'an (~130.0 g), koeastian (50.7 g) ja yhdistelmän tunnistus lepotilassa ilman vesilaskurin vääristymistä.
  - `pico/classes.py`: lisätty `smart_tray` ja getterit `get_tray_water_g()`, `get_tray_water_pct()`, `get_tray_status()`, `get_detected_object()`, `get_detected_object_weight()`, `is_tray_emptied_offline()`.
  - `pico/main.py`: `SmartTrayTracker`-alustus ja päivitys `scale_poll_once()`-silmukkaan.
  - `pico/bluetooth_handler.py`: `scale_payload` laajennettu älykkään kaukalon tiedoilla (`tray_water_g`, `tray_pct`, `tray_status`, `detected_object`, `object_weight_g`).
  - `pico/commands.py`: komennot `tray?`, `tray:empty`, `tray:cal_empty`, `tray:wmax:<g>`, `obj?`, `obj:cup:<g>`, `obj:scale:<g>`, `obj:vessel:<g>`.
  - `pico/MANIFEST.json`: päivitetty.
  - Testit: `testit/smart_tray_smoke.py` (RESULT: 0 failed, 12 testikohtaa), kaikki muut smoke-testit vihreinä (RESULT: 0 failed).

- **26.10.2026:** wmax-pysyvyys toteutettu ja todennettu.
  - `pico/functions.py`: `save_settings` tehty atomiseksi (`settings.txt.tmp` kirjoitus + `os.rename`), jotta katkos tai nollaus tallennuksen aikana ei korruptoi tai katkaise tiedostoa.
  - `pico/functions.py`: `load_settings` ei enää koskaan poista `settings.txt`:ää virhetilanteessa (`os.remove('settings.txt')` poistettu), vaan säilyttää tiedoston levyllä ja pitää turvalliset oletukset. Lisäksi toipuminen `settings.txt.tmp`-tiedostosta, jos varsinainen tiedosto puuttuu tai on korruptoitunut.
  - `pico/functions.py`: kenttäkohtaiset virheet (esim. yksittäinen virheellinen asetusarvo tai tyyppi) käsitellään turvallisesti, jolloin muut asetukset ja ennen kaikkea kaukalovahdin turvarajat (`weight_limit` / `wmax` ja `weight_rise_limit` / `wrise`) latautuvat häiriöttä.
  - `pico/MANIFEST.json`: päivitetty `functions.py`:n osalta `pico_dev.py manifest pico/MANIFEST.json` -komennolla.
- **26.10.2026:** EXPRESSO-TURVAKATO-NOLLAUSIKKUNA toteutettu ja todennettu.
  - `pico/boot.py`: `devsafe.relays_off()` suoritetaan ensimmäisenä heti käynnistyksen alussa ennen mitään muita importteja tai viiveitä. Nollausikkuna poistettu: mikään rele ei jää päälle watchdog-nollauksen tai käynnistyksen aikana.
  - `KAYTTAJAN-TIEDOT.md`: käyttäjän 7.10.2026 asettama vaatimus kirjattu tunnusrivinä `TILAUS-RELEET-ALAS` osioon 5 (Turvallisuus).
  - Työkalupolkujen auditointi: `pico_dev.py`:n kaikki laiteohjaus- ja reset-toiminnot (`safe`, `verify`, `flash`, `watchdog_test`) varmistavat `enter_devsafe()`-kutsulla releiden nollauksen ja tarkistavat `SAFE_OK`-tilanteen.
  - `testit/nollausikkuna_smoke.py`: uusi kattava savutesti, joka todentaa `boot.py`:n, `main.py`:n, `devsafe.py`:n ja `pico_dev.py`:n releinvarianssit sekä simuloidun boot-ajon (RESULT: 0 failed, 20/20 tarkistusta).
  - `pico/MANIFEST.json`: päivitetty `boot.py`:n osalta `pico_dev.py manifest pico/MANIFEST.json` -komennolla.
  - Kaikki olemassa olevat smoke-testit vihreinä (settings_pysyvyys, smart_tray, shot_test, lampotilatilat, tray_guard, tray_total, vaaka_komennot, valmiustila, termostaatti, steam_paine, kuumavesi, turva_pika, turva_toimilaite: 0 failed).

- **26.10.2026:** EXPRESSO-TURVAKATO-NOLLAUSIKKUNA toteutettu ja todennettu.

- **26.10.2026:** EXPRESSO-EU-RIVI-KOKONAISLUVUT: EU-rivin muoto arvioitu. C1-JAKSOT siirsi 1 kHz näytteistyksen ja releiden kääntöjen ajoituksen ytimelle 1 muistilukittuna (TILAUS-O toteutuu, miss=0, late=0), joten EU-rivin lukumuodon muuttaminen kokonaisluvuiksi rikkoisi olemassa olevat analyysit ilman hyötyä ytimen 1 ajoitukselle. Uuttosilmukan (pre_infusion_phased) allokaatiot kevennetty pico/functions.py:ssä: del out[:] uuden listan luonnin sijaan, w/f inlining ilman välimerkkijonoa ja generaattorisumman poisto. Todettu testit/eu_rivi_smoke.py (0 failed) ja koko savutestisetti (0 failed). Seuraava paketti on EXPRESSO-STANDBY-IMPORT-UTIME.

- **27.10.2026:** EU-rivin ulkoista tulostemuotoa ei muuteta kokonaisluvuiksi: C1-JAKSOT hoitaa uuton ajoituskriittisen ohjauksen ytimellä 1 `heap_lock()`-tilassa (TILAUS-O toteutuu täydellisesti miss=0, late=0), joten ulkoisen tekstimuodon muutos aiheuttaisi vain tarpeettoman rikkovan muutoksen olemassa oleviin analyyseihin.

- **27.10.2026:** Allokaatiot minimoidaan uuttosilmukassa in-place-listatyhjennyksellä (`del out[:]`) ja suoralla kenttien inlinauksella.

- **27.10.2026:** EXPRESSO-STANDBY-IMPORT-UTIME: utime tuodaan moduulitasolla classes.py:ssä ja BrewData.update_standby käyttää instanssin tai moduulitason kelloa (clock = self.utime or utime) ilman toistuvaa import-kutsua pääsilmukassa. Todettu testit/valmiustila_smoke.py (0 failed).

- **27.10.2026:** EXPRESSO-LAMMITYS-VIRTAUS: uuton lämmitysteho virtauksesta (TILAUS-N, TILAUS-R) todennettu pumpun iskuista ja paineesta (EP5-käyrä, BH_PMAX 15 bar, `_bh_add(p)`), käyttämätön `EB_HEAT_OFF_MS, EB_HEAT_ON_MS` -pulssitusvakio siivottu pico/functions.py:stä; todennettu laitteella 21.10.2026 (bh-20261021-*.log) ja termostaatti_smoke.py (0 failed).

- **27.10.2026:** EXPRESSO-TILAUS-INVARIANTIT: tilauksen menetelmäkohdat nimetyiksi invarianteiksi (TILAUS-A…TILAUS-T, TILAUS-RELEET-ALAS, TILAUS-AUTONOMIA) KAYTTAJAN-TIEDOT.md:ssä käyttäjän omina lainauksina ja viittein paketit/PUMPPU-PWM.md:hen; PUMPPU-PWM.md:n vaiheet 1c–1f, 2, 3, 4 merkitty tilaustunnuksin; koneellinen tarkistus todennettu (testit/tilaus_invariantit_smoke.py 0 failed, vaatimukset.mjs --tarkista / --rivi). Seuraava paketti on EXPRESSO-THERMAL-STABILITY.

- **27.10.2026:** EXPRESSO-POST-BREW-COLD-SETTLE: uutonjälkeinen lämmitys ja asettumisvaihe (_post_brew, settle) estetään kylmällä kattilalla (BH_COLD_C 15.0 C alle tavoitteen). Kylmä huuhtelu tai uutto ei jää 5,6 %:n pito-loukkuun, vaan kattila lämpenee normaalisti täydellä teholla tavoitteeseen. Todettu testit/termostaatti_smoke.py K1–K4 (0 failed).

- **27.10.2026:** EXPRESSO-THERMAL-STABILITY: thermal stability (-10…+10, TILAUS-Q) lasketaan IDLE-PI:n ylläpitotehosta (pi_i) suhteessa opittuun vakiotehoon P0 (0.045, muuttumaton 30 min, tallennetaan thermal_stability.json) ja kylmäkäynnistyksen tasaantumistehoon (span 0.040 -> -10.0), rajaus [-10.0, +10.0], säilytetään muissa tiloissa. Lisätty DIAG_MIN ts=, live_payload/scale_payload telemetriaan ja sarjakomentoihin ts? / ts:p0:. Todettu testit/termostaatti_smoke.py L1–L6 (0 failed). Seuraava paketti on EXPRESSO-VESIMAARA-TUNNISTUS.

- **27.10.2026:** EXPRESSO-VESIMAARA-TUNNISTUS: säiliön vesimäärän tunnistus lämpöstabiiliuden saavutusnopeudesta (TILAUS-Q) toteutettu `pico/water_tank.py` (`WaterTankTracker`). Kylmäkäynnistyksessä (TS <= -8.0) mitataan saavutusaika t_reach_s arviointikynnykseen (TS >= -2.0), josta arvioidaan säiliön vesimäärä V_est = model_a * t_reach_s + model_b (oletus a=0.0020, b=-0.40, rajattu 0.0...2.0 L). Lämmin käynnistys (TS > -6.0) asettaa 'warm_start'-tilan ja säilyttää tallennetun tason. Kulutuksen seuranta (consume_water_ml/l), varoitusraja (<= 0.3 L -> low_water), tilan atominen pysyvyys tiedostoon `water_tank.json` (tmp + rename). Lisätty `DIAG_MIN tk=`, reaaliaikatelemetriaan (`live_payload` ja `scale_payload`) kentät `tank_water_l`, `tank_pct`, `tank_status`, päivitetty `NOTIFY_DROP_ORDER` ja sarjakomennot `tank?`, `tank:fill`, `tank:set:<L>`, `tank:cal:<a>:<b>`, `tank:consume:<ml>`. Todettu `testit/vesimaara_smoke.py` M1–M9 (0 failed).

- **27.10.2026:** EXPRESSO-C1X-JALKINOUSU: C1X-jälkinousun lisäviive sovitetty laitedatasta (`testit/sovita_c1x_lag.py`). Sarjan 1 (dly=0.0) viive-ero 17.6 ms (ylitys +0.36 bar), sarjan 2 (dly=0.02) viive-ero 33.4 ms (jäännösylitys +0.07 bar). Kaikkien ajojen mitattu lisäviive ka 24.1 ms ja ylityksen poistava optimaalinen viive 23.1 ms. Fysikaalinen malli: k+2-jono (20 ms) + SSR-40DA nollaylitys (ka 5 ms) = 25 ms. Päivitetty `pico/functions.py`: `EU_C1X_LAG_S = 0.025`. Todettu `testit/c1x_lag_smoke.py` C1–C7 (0 failed). Kaikki automaattiset paketit toteutettu.

- **27.10.2026:** EXPRESSO-C1X-JALKINOUSU: C1X-jälkinousun lisäviiveeksi firmwareen asetettu `EU_C1X_LAG_S = 0.025` (25 ms). Fysikaalinen perusta: k+2 tapahtumajonon 20 ms + SSR-40DA -triacin nollaylityksen keskimääräinen 5 ms viive ennen virran katkeamista = 25 ms. Sovitettu tarkasti 20.10.2026 laitedatasta.

- **27.10.2026:** EXPRESSO-C1X-TODENNUS: c1x:n oletusarvo ja laiteuuttojen toiminta todennettu laitedatasta (TILAUS-O, TILAUS-AUTONOMIA). classes.BrewData: eu_c1x = 1 oletuksena, commands.py: c1x:0/1 ohjaus. 21.10.2026 laiteuuttosarja (bh-20261021-s1..s4, 4 uuttoa): EU_START c1x=1 oletuksena kaikissa 4 uutossa, EU_END/EB_END miss=0 ja late=0 kaikissa, EB_C1X ovf=0, late=0 ja starve=0 kaikissa uutoissa. Invariantti TILAUS-O toteutuu (0 pudonnutta tai ylimääräistä jaksoa). Todettu testit/c1x_todennus_smoke.py (0 failed). Kaikki automaattiset paketit toteutettu, seuraava odottaa käyttäjää.

- **27.10.2026:** c1x:n oletustoiminta ja luotettavuus todennettu tuotantolaitteen oikealla uuttosarjalla (21.10.2026).

- **27.10.2026:** Kaikki automaattiset koodipaketit on toteutettu. Jäljellä olevat tehtävät odottavat laitetestejä ja käyttäjän fyysisiä toimia.

- **27.10.2026:** Ei kirjattuja päätöksiä: deterministinen synteesi ei tulkitse keskustelun linjauksia

- **27.10.2026:** Ei kirjattuja päätöksiä tässä istunnossa.


## Avoimet asiat

| Asia | Tila | Seuraava askel |
|---|---|---|
| EXPRESSO-LAMMITYS-VIRTAUS | toteutettu 21.10.2026 (2754d74 osana TILAUS-R/N:ää) | uuton lämmitysteho toteutettu pumpun iskuista paineella painotettuna (EP5-käyrä, BH_PMAX 15 bar) vaiheissa 1–4, kiinteä EB_HEAT-pulssitus poistettu; todennettu laitteella 21.10.2026 (bh-20261021-*.log) ja termostaatti_smoke.py (0 failed) |
| Sisällön siirto `infra iot` -skoopista tänne (EXPRESSO-SKOOPPISIIRTO) | avoin, toisen keskustelun työ | tämä sessio ei koskenut `Infra/paarekisteri.md`:hen |
| Tilaluvun sisältö | avoin | päätä siirron yhteydessä, mitkä `KEHITYSYHTEYS.md`:n luvut ovat *tilaa* (kuuluvat tähän) ja mitkä *ohjetta* (jäävät sinne) |
| `fast_heatup`: rajat | dev_safe, 160 °C, lukeman tuoreus ja ei-nouse-raja vartiosta 22.9.2026, flashattu 23.9.2026 | tarkista laitteella |
| Vaiheet 1c–1f, 2 (pre-infusion auto vaa'asta), 3 (max flow rate), 4 (höyry +10 °C) | avoin; odottaa käyttäjää (vaihe 1b on laiteajo, läsnäolo- ja vesikuittaus; 1c riippuu 1b:stä) | `paketit/PUMPPU-PWM.md` vaihetaulukko; käyttäjä valitsee laiteajon ajankohdan; 1c:n muoto riippuu yhä 1b:n päätöksestä (kirjattu 19.9.2026) |
| EXPRESSO-TILAUS-INVARIANTIT | toteutettu 27.10.2026 | Tilauksen menetelmäkohdat nimetyiksi invarianteiksi (TILAUS-A…TILAUS-T, TILAUS-RELEET-ALAS, TILAUS-AUTONOMIA) KAYTTAJAN-TIEDOT.md:ssä sanamuotoineen ja viitteineen; PUMPPU-PWM.md:n vaihetaulukko katettu tilaustunnuksin; koneellinen tarkistus todennettu (testit/tilaus_invariantit_smoke.py 0 failed) |
| EXPRESSO-POST-BREW-COLD-SETTLE | toteutettu 27.10.2026 | uutonjälkeinen lämmitys ja settle-vaihe estetty kylmällä kattilalla (BH_COLD_C 15.0 C alle tavoitteen), todennettu termostaatti_smoke.py K1–K4 (0 failed) |
| Vaihe 1b:n invariantti ja sen hajonta | ajettu laitteella 20.9.2026 (`pstep`, `pgap`, `plen`), invarianttia ei löytynyt | alkuperäinen tehtävä yhä auki; käsketty vaihe ei vaikuta mitattavasti (ks. Todettu 20.9.2026), joten invariantin lähde on vielä avoin kysymys |
| Analysaattorin tuomio | vajaa | `verdict` valitsee suureen sokeasti; valinta kuuluu tehdä `PSKIP_SUB`/`PSKIP_FUND`-suhteesta ja sanoa tulosteessa |
| Huoltotoiminnot sovellukseen ja HA:han: sitruunahappokäsittely (kalkinpoisto) ja backflush-puhdistus (käyttäjä 23.9.2026) | myöhemmin tehtäväksi; backflush on firmwaressa (`pico/backflush.py` `run_backflush`), sitruunahappokäsittelylle ei ole koodia | (1) toteuta sitruunahappokäsittely firmwareen; (2) molemmat käynnistettäviksi Android-sovelluksesta; (3) sovellukseen huoltoilmoitukset, kun huolto on ajankohtainen; (4) Home Assistantiin muistutus kummastakin huollosta, kun sen aika on — huoltovälit ja ajankohdan peruste (aika, uuttomäärä) kysytään käyttäjältä |
| Laturin Type-C-vika | kiertotie käytössä | testaa käyttäjän hypoteesi: laturi päälle akun ollessa 80 %:ssa, pysyykö 2e8a |
| Shellyn kiinteä DHCP-osoite | tekemättä | `uci`-muutos, vaatii käyttäjän luvan (sääntö 8) |
| Akkuvahdin kytkentä Shellyyn (lataus ajojen välissä) | toteuttamatta | — |
| Kaukalon tyhjennys ajojen välissä | 24.9.2026: ~110 g/ajo piti vain ~2 g/s:n kuristimella; säädetyllä kuristimella (~8 bar jatkuvalla pumpulla) kaksi sarjaa toi ≥ 250 g (`trayrise`), täysi ajo ~375 g > kaukalon 260 g | mitoita protokollan vesi kuristimen virtauksen mukaan ennen seuraavaa pitkää ajoa (sarjojen määrä tai käyntiaika). |
| Väreilyn vaiheen vaellus nousevassa paineessa (sim "huonoin": väärien lupien pohja ~2 %) | ensimmäinen aineisto lokeissa a, b, d (23.9.2026): lukittu hajonta 785–950 us > sim, 5 s tauon järjestelmällinen +3,8 ms | korjaa: 5 s tauon järjestelmällinen +3,8 ms, lukittu hajonta 785–950 us > sim; ks. seuraava paketti |
| Verkon muutosnopeus r | ensimmäinen aineisto lokeissa a, b, d (23.9.2026), +3 mittausta lokeissa e, g, h (23.9.2026), 24.9.2026 noin klo 8.30 50,0192 Hz (vkello-20260924-b) | jatka kirjausta jokaisesta ajosta (VKELLO_END hz aikaleimoineen). |
| Olemassa olevien ajojen (pgap, psweep, pstep, mcal) siirto kellolle (kello = verkkokello, ei uutot) | odottaa laitetestiä | seuraava ohjelmistopaketti laitetestin jälkeen (brief VERKKOKELLO, Task). |
| TILAUS-K/L vaiheseuranta ohjauksen jokaisessa vaiheessa (24.9.2026, KAYTTAJAN-TIEDOT 2c) | suunnitelma ja askel 1 paketit/VAIHESEURANTA.md. Askel 1 laitteella (vsweep1, vsweep-20260924-a): 10 ms tauko poistaa iskun, kun se alkaa 8,5–18,7 ms kellon reunasta (2/60 väärin), jyrkät reunat → nollaylitys-SSR, puolijaksot erottuvat. Ajoitusvika (tauot 1,4–18,6 ms myöhässä) korjattu isännällä (tuore aika, summat jälkeen, vahti 300 us), flashattu (vsweep2 24.9.2026); vaiheet 1–2 esiuutossa tehty ja todennettu (esiu2). | vaiheet 3–4 (uutto) ja taukojen käyttö vaihemittauksena tekemättä; käyttäjän valinta: tarkennettu reunapyyhkäisy korjatulla ajoituksella tai askel 2 (säädin 20 ms / kello). |
| Purun negatiivinen paine (−0,67…−1,08 bar) | 25.9.2026: mittari vahvistaa työalueen (pito ~2,5 bar, uutto ~7–8 bar) — kaksipistekalibrointi tarpeeton itse työalueella | käyttäjän päätös, poistetaanko asia. |
| Kuristimen lämmitys ennen laiteajoa (`klamp:<s>`) | 25.9.2026: kylmän kuristimen ajo todennettu — klamp ei toimi kylmällä kuristimella, jatkuva pumppu nousee tasanteeseen 10,5 bar ja `PCAP_OVER_BAR` 11,0 katkaisee 9,1 s:ssa (klamp-20260925-b.log); ks. Viat | korjaa klamp rajoittamaan paineen (esim. 9 bar säätimellä) eikä ajamaan tasanteeseen. |
| Esiuuton 2,5 bar säätö | 26.9.2026 (EXPRESSO-ESIUUTTO-FF, 54e3ac9–c323f6f, laitteella esiuff3; EXPRESSO-ESIUUTTO-ALKU, e91816c, laitteella esialku6; EXPRESSO-ESIUUTTO-AVOIN, 0028dff, laitteella esiavoin1): pidon alun ylitys korjattu ryöminnän osalta ja nousun ylitys ~0,4:ään; ff = min(nousun arvio, edellisen pidon tarve × G-suhde), 1. ajo 0,4 × arvio, tarve ja G settings.txt:ssä (säilyy resetin yli), häntävahvistus ja D (KD 0,05); edellisen tiedolla pidon 2 s ka 2,53 / sd 0,068 (h), 1. ajo 2,59–2,76 (f: 2,49 → 2,92); avoimen kuristimen alun alitus korjattu ja todennettu (ab/ac 2,42/2,46, esiavoin1), ff = tavoite / (rate · tau_edellinen + p5), eu_tau_pre settings.txt:hen, integraali rajattu 0…1, hold ajaa pvent-purun; uuttoasento korjattu ja laitteella todennettu 26.9.2026 (417ad93, ah–am); vuoronvaraus korjattu (late 0, aq–as, EXPRESSO-ESIUUTTO-VUORONVARAUS), rampin loppu korjattu isännällä 651afec (smoke 15), ei flashattu; yksityiskohdat `paketit/VAIHESEURANTA.md` **20.10.2026:** esiuutto c1x (hold3 ca29944): miss 0, late 0 (125 µs), pito 2,532/sd 0,112; vanha samassa tilassa miss 3, late_max 14,4 ms, sd 0,116. **22.10.2026:** vanhalla kalibroinnilla (gain 1,000 / offset −0,990) matalat paineet näkyivät liian pieninä (4 bar → ~3,3), joten esiuutto 2,5 osui todellisuudessa ~2,9 bar:iin ja `PCAP_OVER_BAR` 11 laukesi ~10,8 todellisessa. | (1) pidon alun ylitys korjattu ryöminnän osalta ja nousun ylitys ~0,4:ään (EXPRESSO-ESIUUTTO-ALKU ajettu); (2) käyttäjän hyväksyntä ennen 8 barin vaiheita on yhä tekemättä (avoin asia 24); (3) 1. ajo ilman tallennettua tietoa ylittää yhä (f: 2,49 → 2,92, ennallaan), avoimella nyt ali (aa 2,19) — tarvittaessa alempi alku; (4) lämmin/kylmä-tila todennettu 26.9.2026 (ad/ae): lämmin → kylmä +0,27 ei läpäise; uuttoasento korjattu ja laitteella todennettu 26.9.2026 (417ad93, ah–am, EXPRESSO-ESIUUTTO-UUTTOASENTO), vuoronvaraus korjattu (aq–as); EXPRESSO-ESIUUTTO-RAMPIN-LOPPU korjattu isännällä (651afec, smoke 15), seuraavaksi flash + hyväksyntäajo. (lisäksi 26.9.2026, EXPRESSO-ESIUUTTO-ALKU): (b) rampin kiinnikurojan ryöppy (y: sp ohitti p5:n 1,1 s:n kohdalla, d 0,42 → 3,87 bar, 1/8 ajosta, malli ei toista) → tiheämpi loki rampin loppuun ja lisää ajoja kuristin lähes kiinni (käyttäjän mukaan epärealistinen tila → matala prioriteetti). |
| 6 s pito lämpimällä kuristimella | lämmin kuristin ajettu 27.9.2026 at–aw (hold 5 s samassa asennossa kuin ao–as); 6 s pito ei erikseen todennettu | seuraa, tarvitaanko erillinen 6 s ajo, kun 8 barin vaiheet toteutetaan. |
| Tarkennettu reunapyyhkäisy (0,2 ms reunojen ympäriltä) | ehdotettu | käyttäjän valinta myöhemmin. |
| Matalan paineen vakiotilamittaus (kuristin auki, tasanne ~4 ja ~6 bar, `vkello 0`) | ehdotettu, käyttäjä ei valinnut | erottaa matalan paineen ja nousunopeuden vaikutuksen. |
| Säätimen 17 ms askel → 20 ms kelloon sidottu (TILAUS-L) | avoin | VAIHESEURANTA askel 2; `PumpPressureController` 17 ms yhä käytössä `pico/functions.py:55`, `:931`, `:1187`, `:2768` (todettu 5.10.2026); käyttäjän valinta reunapyyhkäisyn ja askeleen 2 välillä. |
| Smoken kohinainen lämmin → kylmä -pari on 7/24, sallittu 8: lähellä rajaa | avoin | seuraa, jos säätimen muutos vie yli. |
| `pico_dev.py hold` ei aseta eikä tarkista `pim:1`:tä; `verify`/`safe`/reset nollaa sen | avoin | lisää hold:iin pim-tarkistus TS_STARTista tai `pim:1` ennen tshotia |
| Yhden iskun vaste 2,5 barissa uuttoasennossa mallin sovitusta varten | kahden osan malli nyt olemassa (delta_f 0,6 / tau_f 0,08 sovitettu); aiemmin ehdotettu | mittaus vahvistaisi mallin, vaatii käyttäjän koneelle. |
| Uuttoasennon jälkinousu | mallissa ~1,9 bar (katkaisun rate jää kiihtyvässä täytössä jälkeen), laitteella 0,43–0,89; ao–as kylmällä kuristimella 7 h tauon jälkeen 1,12–1,58 bar, coast_f 0,12–0,155 **20.10.2026:** uutto 8 bar, sarja 1 (adf8580, 3+3): c1x miss 0, sd ka 0,177, ylitys 0,52; vanha miss 23, sd 0,202, ylitys 0,16. Syy: jälkinousu (21 bar/s × 20 ms ≈ +0,4 bar); Sarja 2 (f0a7a09, 3+3): c1x miss 0, late 0 (≤ 264 µs), sd 0,193, ylitys 0,45; vanha miss 40, sd 0,223, ylitys 0,39 (0,25–0,59). Jälkinousu/nousu c1x 0,10–0,11 s vs vanha 0,06–0,08 s: lisäviive näkyy 0,03–0,04 s:na; Malli (esiuutto_smoke 23/24): c1x late=miss=nälkä=0 kaikissa; ylitys 0–0,03 bar yli vanhan; mallin 8 barin nousu ~11 bar/s (laite ~21) ei näyttänyt jälkinousuvaikutusta. | seuraa hyväksyntäajossa. |
| af:n coast_s-poikkeama (0,054 vs ae 0,074) | selvittämättä | tarkista settings-tallennus seuraavan paketin yhteydessä. |
| TILAUS-C: kuristimen kääntö kesken pidon | todennettu vain paineportaina (d1 7,1 bar, a3–a5 8 bar @ kuri:24/25, d2 9,25 bar, eri ajoissa), ei kesken yhden pidon; TILAUS-M:n myötä kääntöä ei voi enää antaa ruuvin kierroksina kesken ajoa | kysy käyttäjältä, millä tavalla TILAUS-C toteutetaan TILAUS-M:n (kuri-sykli) rinnalla. |
| 9 barin kuri-säädön läheisyys raakaan ylipainerajaan | 9 bar @ kuri:25 lähellä raakaa `PCAP_OVER_BAR` 11,0 (suodatettu ~9,7 bar, piikit ~+1,4 bar); rajaa ei muutettu 28.9.2026 (Päätökset, vika 15) | käyttäjän päätös, nostetaanko rajaa vai rajataanko kuri-asetusta ylöspäin. |
| Aamun kaatuminen 5.10.2026: heat_dead vs MemoryError (toistui 6.10., ei lokia) | avoin; odottaa skooppia infra zero (V-207, f37507e); 7.10.2026 aamulla ei kaatumista | kun `/pura infra zero` on tehnyt pysyvän lokin (V-207, päätetty 6.10.2026): `pico_dev.py log` ja syy lokista; ZERO-PARITEETTI (465c241): harkitse tiedostojen lukua ja BOOTSEL-komentoa |
| `update_standby` tekee `import utime` joka kierroksella (kirjattu 5.10.2026) | toteutettu 27.10.2026 | import utime siirretty moduulitasolle pico/classes.py:ssä, valmiustilan silmukka ei enää tee importtia; todennettu testit/valmiustila_smoke.py (0 failed) |
| Zeron ser2net raaka 2217 mykkä uudelleenenumeroinnin jälkeen | korjattu 6aff448 (kierretty pico_dev.py:ssä); ser2net-asetus odottaa skooppia infra zero | ilmoita skoopille infra zero: esim. `local` pois / DTR (kirjattu 5.10.2026) |
| Selittämätön Picon uudelleenenumerointi 5.10.2026 klo 15.42.51 | avoin (yksi kerta) | seuraa seuraavissa laiteajoissa |
| PICO-DEV-LINK (`pico_dev.py` Link: kohinan sieto ja hiljaisen sillan uudelleenavaus) | korjattu aa77c57 6.10.2026; odottaa käyttäjää (aamutesti 7.10.2026 ajoi Zero-linkillä, ei todentunut) | käyttäjän päätös: todennetaanko `PICO_LINK=phone`-linkillä (käynnistää Android-äpin, iOS-päätös 0b0cca4) vai suljetaanko tarpeettomana |
| Zero-linkin ensimmäinen `cmd 'heat?'` tyhjä 7.10.2026 | avoin (toinen kutsu toimi heti) | tarkkaile seuraavissa ajoissa, toistuuko |
| V-119 ja V-128 EXPRESSO-VIRTAUSTESTI (kirjattu 7.10.2026) | avoin; odottaa käyttäjää (laiteajoa `fmode:on`, `fset:2.2` ei ole ajettu; vain isäntäsimulaatio 9/9, `KEHITYSYHTEYS.md:915-930`) | laiteajo läsnäolo+vesi-kuittauksella |
| V-231 `pico_dev.py capture 1320` päättyi ~11 min kohdalla (09.43→09.54, exit 0; stbt-laitetesti 7.10.2026, c38a13f) | avoin; odottaa käyttäjää (toisto vaatii laitteen ja läsnäolon) | lue `testit/stbt-20261007-laite*.log` ja `pico_dev.py` capture-silmukan lopetusehto; toisto läsnäolokuittauksella |
| EXPRESSO-SKOOPPIJAKO | avoin (käyttäjä hyväksyi 12.10.2026) | `/pura uusi expresso` + neljä alaskoopia (jako Päätökset-luvussa), rekisterin rivit alaskoopeille |
| EXPRESSO-PICO-SARJALOKI | avoin (kirjattu 7.10.2026; brief `paketit/PICO-SARJALOKI.brief.md` tekemättä); odottaa skooppia expresso laite | brief → toteuttaja; asennus Zerolle; todennus: loki kasvaa ilman asiakasta ja `pico_dev.py cmd` toimii; kirjaa muutos myös infra zeron rekisteriin |
| Uutto rikki (käyttäjä 7.10.2026 ~13.50) | odottaa laitetestiä sarjalokin jälkeen (syy auki) | sarjalokin jälkeen testiuutto ja lue loki |
| V-122 HA:n `Unable to parse JSON espresso_*` (kirjattu 7.10.2026) | avoin; odottaa käyttäjää (oletettu syy: vanhan firmwaren retained-viestit; `grep -rli mqtt Infra/iot/expresso` 0 osumaa) | listaa `homeassistant/+/espresso_*/config` HA-isännällä, tyhjennä luvalla |
| V-210 BLE-avainero firmware ↔ äppi (kirjattu 7.10.2026) | avoin; odottaa käyttäjää (firmware todennettu: `pico/bluetooth_handler.py:83`, `:101-102`; äpin lähde Macilla) | käyttäjän päätös: firmware (flash) vai äppi (expresso-ios) |
| Thermal stability −10…+10 (TILAUS-Q, käyttäjä 21.10.2026): ylläpitotehon tarve suhteessa pitkän aikavälin vakiotehoon, firmwareen, DIAG_MIN:iin ja äppiin | toteutettu 27.10.2026 | IDLE-PI:n integraali = nykyteho, opittu vakioteho P0 (muuttumaton 30 min, tallennetaan thermal_stability.json) = 0, kylmäkäynnistyksen tasaantumisteho = -10 (span 0.040), rajaus ±10, muissa tiloissa viimeinen lepoarvo; lisätty firmwareen (classes.py, BrewData.get_thermal_stability()), DIAG_MIN:iin (ts=), telemetriaan (live_payload ja scale_payload) ja sarjakomentoihin (ts?, ts:p0:); todennettu testit/termostaatti_smoke.py L1–L6 (0 failed) |
| Tilakohtaiset lämmönsäädöt erikseen kalibroituna (TILAUS-R, käyttäjä 21.10.2026): uutto, uuton jälkeinen palautus, höyry, kuuma vesi | IDLE tehty (TILAUS-P); uutto koodissa 21.10.2026 (käyttäjä hyväksyi toteutustavan): lämmitys pumpun iskuista paineella painotettuna (`brew_heat_k` ms/isku, `BH_PMAX` 15 bar) vaiheissa 1–4, jäännös maksetaan uuton jälkeen, sitten pito pi_i:llä tasaantumiseen ja kerroin oppii (`BH_LEARN`, `brew_heat.json` Picolla, tmp+rename); mallilaitoksella k oppii ±15 % 8 uutossa ja tasaantunut T 98 ±0,2; vanha uuttosilmukka (bim:0) ennallaan; flashattu 2754d74 21.10.2026 08.43. Laitteella: käyttäjän uutto 08.49 kuoppa 98,1→87,5, ylitys +0,7 (ennen +6 °C, 5–6 min), k 70→68; sokkokori s1 98,28 (k 66,9), s2 97,92 (k 67,2); kahvi 09.11 kuoppa 98,0→85,2, tasaantui 97,87 ilman ylitystä; sarja keskeytettiin kahvin ajaksi (`testit/bh-20261021-*.log`). Kytkimen napautus 09.12 korvasi summan → k 70,5 (vika, korjattu: summat jatkuvat opin loppuun); 750a2ae + faedc8f flashattu 09.26 (k 67,5 kirjoitettu `brew_heat.json`:iin väliaikaisella setillä). s3 09.30 höyrytyksen jälkeen (käyttäjä: höyry kahvin jälkeen, kahva vaihdettu testikahvaan): täyttö 555 iskua (normaali 89–101), kertymä 44 s, tasaantui 105,95 (+8), k 67,5→50,8 → sarja pysäytetty; korjaus: täytön katto BH_FILL_MAX 120 iskua < 1,0 bar, katon ylitys tai höyrystä < 20 min estää opin; vapaa virtaus (isäntä 21.10.2026): katto maksoi 15 s:n huuhtelusta 120/747 iskua (8,3 s vs ~52 s) → kaukalon nousu ≥ `BH_FREE_G` 10 g ohittaa katon (`BH_FREE`), oppi pois (arm 2, tasaantuminen 30b7e38); ei flashattu, testit H7–H8. Käynnistyksen ylitys 21.10.2026: flashin jälkeen 90 → 98 nousi 100,4–100,6 °C; havainto, ei toimenpidettä. | flash kuittauksella; kalibrointi: ensin sokkokori pico_dev-testiuutoin, sitten oikeat uutot (käyttäjä 21.10.2026 "Molemmat"); sitten uuton jälkeinen palautus, höyry (käyttäjä 21.10.2026: höyrystys poistaa vettä kattilasta → lämpömassa pienenee; myös höyryn jälkeiset opit), kuuma vesi |
| Säiliön vesimäärän laitetodennus (käyttäjä 21.10.2026, jatkotehtävä; säiliö = keittimen vesisäiliö, josta boileri ottaa uutta vettä) | toteutettu 27.10.2026 (firmware + simulaatio); laitetodennus odottaa laiteajoja eri vesimäärillä **27.10.2026:** vesimaara_smoke.py M1–M9 hyväksytty 27.10.2026 (32/32); VESIMAARA-TUNNISTUS.brief.md vaatimukset.mjs exit 0 27.10.2026. | kun thermal stability on laitteella: kerää saavutusajat eri vesimäärillä, sovita malli; toteutettu pico/water_tank.py (WaterTankTracker): saavutusajan t_reach_s mittaus kylmästä (TS <= -8.0) kynnykseen (TS >= -2.0), lineaarinen malli V_est = a*t_reach + b (0.0...2.0 L), kulutuksen seuranta (consume_water_ml), varoitusraja (<= 0.3 L -> low_water), tilan pysyvyys water_tank.json, DIAG_MIN tk=, telemetria tank_water_l / tank_pct / tank_status ja sarjakomennot tank?, tank:fill, tank:set, tank:cal, tank:consume; todennettu testit/vesimaara_smoke.py M1–M9 (0 failed) |
| Androidin ikoni samalla merkillä (Espresso-ikoni, iPhone valmis 14.10.2026) | avoin (ei pyydetty) | käyttäjän valinta myöhemmin. |
| Todennus oikealla uutolla | avoin; odottaa käyttäjää **27.10.2026:** 4 oikeaa laiteuuttoa (s1..s4): EU_START c1x=1 kaikissa, miss=0, late=0, starve=0, ovf=0 kaikissa uutoissa. | Wi-Fi etualalla (live+paino nyt yhdessä paketissa, loki), lukittu puhelin (BLE-tausta, painokehote), PB-uutto: brew_log Wi-Fillä ja `max_loop_ms` vs. 145 ms |
| iOS-profiili vanhenee 24.10.2026 | odottaa päivää 29.10.2026 (asennettu 24.10.2026, profiili voimassa 29.10. asti) | `expresso-asennus.sh` uusii |
| Android-käännös yhteisellä lib:llä (crypto, flutter_secure_storage) | avoin (ajamatta) | — |
| Wi-Fi live 2,8 Hz ja hello ~1 s (virransäästö?) | avoin | virransäästökoe (todennus oikealla uutolla) |
| Push: expresso-repo (9f8d942…39aec74) ja juuren 6531bc77, 68bb0be3 | kesken (expresso-repo pakkauksessa; juuren 6531bc77 ja 68bb0be3 juuren synkalla); odottaa ajoa **26.10.2026:** commit 9021cbc pushattu onnistuneesti origin/mainiin 26.10.2026. | — |
| BLE pois päältä | avoin (`preset.BLE`, 1b47954) | käyttäjän päätös, milloin BLE palautetaan; avaimen jako uudelle puhelimelle vaatii BLE:n tilapäisesti |
| EU-rivi kokonaisluvuin (kirjattu 20.10.2026) | toteutettu 26.10.2026 | arvioitu: C1-JAKSOT hoitaa ajoituksen ytimellä 1 (TILAUS-O toteutuu, miss=0, late=0), joten EU-rivin lukumuodon muutos kokonaisluvuiksi rikkoisi olemassa olevat analyysit ilman hyötyä. Uuttosilmukan allokaatiot kevennetty pico/functions.py:ssä: del out[:] uuden listan sijaan, w/f inlining ilman välimerkkijonoa ja generaattorisumman poisto; todennettu testit/eu_rivi_smoke.py (0 failed) |
| C1X-jälkinousun lisäviive (kirjattu 20.10.2026) | toteutettu 27.10.2026 (sovitus ja koodi EU_C1X_LAG_S 0.025 s); laitetodennus odottaa seuraavaa uuttoa | laitedatan sovitus testit/sovita_c1x_lag.py (24.1 ms, jäännösylitys +0.07 bar -> opt 23.1 ms, fysikaalinen k+2 + SSR nollaylitys = 25 ms); pico/functions.py EU_C1X_LAG_S = 0.025; todennettu testit/c1x_lag_smoke.py (0 failed); laitetodennus seuraavassa uutossa (c1x:1) |
| Vapaa virtaus (käyttäjä 21.10.2026: kahva irti, huuhtelu uuton jälkeen brewhead screenin puhdistukseen) | toimii laitteella (726b8d6: `BH_FREE fill=121` 10.51 ja 11.07, kertymä 12,96 / 10,3 s katon ~8 s sijaan); arm 2 -tasaantuminen omalla rivillään **21.10.2026:** laiteajo 21.10.2026 huuhtelu 11.07 (`testit/vapaa-20261021-b-diag.log`): settle-vaiheessa lämmitin ~pois 11.08–11.10 (heat 700/900 ms/min), T laski häviöillä ~1,3 °C/min (98,82 → 97,53), BH_SETTLED 97,85 11.09.59, sitten alitus −0,86. | riski: täytön katto (120 iskua < 1 bar) lopettaa kertymän, vaikka kylmää vettä virtaa paljon; erottelu kattilan täytöstä kaukalon painon nousulla (vesi ulos) tai paineella ~0; testi laitteella käyttäjän kanssa. |
| Sokkokorisarja (testikahva) | kesken (s1–s4 ajettu, s3 ja s4 höyryn jäljiltä); odottaa käyttäjää | jatka arm 2 -huuhtelutodennuksen jälkeen (läsnäolo), kun täyttö < 120 iskua; sarjaskripti /tmp/bhcal/sarja.sh (ei repossa). |
| Painekalibroinnin todennus | korjattu 22.10.2026 (pcalset 0,8511/+0,349); odottaa käyttäjää (todenna viim. 5.11.2026) | käyttäjä vahvistaa lepotilan lukeman ~0 bar ja seuraavan uuton 8 bar mittarista. |
| Höyrytystilan laitetodennus vaahdotuksessa | avoin (toteutettu ja flashattu 24.10.2026); odottaa käyttäjää | käyttäjä testaa höyrytystä ja venttiiliohjattua lämmitystä maidonvaahdotuksessa. |
| Paineentasauksen laitetodennus kylmäkäynnistyksessä | odottaa laiteajoa (toteutettu ja flashattu 24.10.2026) | havainnoidaan PEQ-tulosteita seuraavassa alkulämmityksessä. |
| Lepotila-ajastimet (käynnistys vs. uutto/höyrytys) ja herätysnäkymä | toteutettu, flashattu ja asennettu 24.10.2026; odottaa käyttäjää **26.10.2026:** asetusten säätö lähettää komennot myös lepotilassa ilman keittimen heräämistä. | käyttäjä testaa lepotilaan menon ja äpin herätyspainikkeen |
| Esiuuttolaukaisin (preinfusion trigger) ja uuttovirheen (EU_STARVE) korjaus (kirjattu 25.10.2026) | avoin; odottaa käyttäjää | käyttäjä testaa uuttoa kahvilla ja varmistaa pisaran laukaiseman siirtymän uuttoon |
| Paineentasauskytkin äpissä ja laitteella (PEQ toggle) | todennettu 25.10.2026; odottaa käyttäjää | käyttäjä testaa äpin uusia painikkeita puhelimella |
| Lepotila-painike äpissä (Siirry lepotilaan) | todennettu 25.10.2026; odottaa käyttäjää | käyttäjä testaa äpin uusia painikkeita puhelimella |
| iOS-äpin 5-osioisen säätönäkymän ja lepotilatoimintojen kokeilu käytössä | todennettu 26.10.2026; odottaa käyttäjää | Käyttäjä kokeilee supistettuja säätöjä ja lepotilan hallintaa puhelimella |
| Äpin yhteyden oletuskuvake (harmaa Wi-Fi, punainen 20 s kuluttua) | toteutettu 26.10.2026; odottaa käyttäjää | käyttäjä testaa yhteyden hakua puhelimella |
| Keittimen lämpötilatilat (IDLE, stabilizing, warming up, cooling down) | toteutettu 26.10.2026; odottaa käyttäjää | keittimen tilat toteutettu firmwareen ja todennettu testeillä: warming up (>2 °C alle tavoitteen), stabilizing (lähestymis-/heilahteluvaihe), IDLE (asettunut ±0,5 °C ikkunaan 10 s ajan vauhdilla ≤0,5 °C/10 s) ja cooling down (>0,5 °C yli tavoitteen); käyttäjä testaa keittimellä ja äpillä |
| Tare-nappi suoraan painon arvon alapuolelle | toteutettu 26.10.2026; odottaa käyttäjää | käyttäjä testaa tare-napin sijoitusta puhelimella |
| Älykäs painon ja kaukalon tunnistus | toteutettu 26.10.2026; odottaa käyttäjää | toteutettu pico/smart_tray.py (SmartTrayTracker): kaukalon veden kertymä, tyhjennyksen tunnistus sammuksissa (emptied_offline), kupin (~293.9 g), ulkoisen vaa'an (~130.0 g), koeastian (50.7 g) ja yhdistelmän tunnistus; komennot tray?, tray:empty, tray:cal_empty, tray:wmax, obj?, obj:cup, obj:scale; telemetria scale_payload; testit smart_tray_smoke.py hyväksytty; käyttäjä testaa laitteella |
| Äpin vaakatilan elementtien karsinta | toteutettu 26.10.2026; odottaa käyttäjää | käyttäjä testaa vaakatilan näkymää puhelimella |
| Äpin vaakatilan pyöreä freeze-nappi | toteutettu 26.10.2026; odottaa käyttäjää | käyttäjä testaa vaakatilan freeze-nappia puhelimella |
| Äpin vaakatilan graafin tilankäyttö | toteutettu 26.10.2026; odottaa käyttäjää | käyttäjä testaa graafin tilankäyttöä puhelimella |
| Flow-virtauksen piirto graafiin | toteutettu 26.10.2026; odottaa käyttäjää | käyttäjä testaa virtauksen piirtoa uutossa puhelimella |
| V-062 akkuvahti palvelimen cronissa | toteutettu 26.9.2026 (dc8a2ee) | — |
| V-143 Roskasiivous (USB-silta Picolle) | arkistoitu Infra/iot/expresso/ARKISTO.md | — |
| V-149 INFRA-SKOOPPISIIVOUS (hubin lataus ja otg) | kirjattu 1b7e7e0 | — |

## Viat

| Vika | Tila |
|---|---|
| `testit/phold-20260919-tasapaino.log` meni committiin `8018b50`, jonka viesti ei mainitse sitä — `git add Infra/iot/expresso` otti sen mukaan. Ei korjata historiaa. | Uusi, avoin (pieni) |
| klamp ei toimi kylmällä kuristimella: jatkuva pumppu tasanteeseen ylittää `PCAP_OVER_BAR` 11,0 (klamp-20260925-b.log: 10,5 bar, katkaisu 9,1 s). Korjausehdotus: klamp rajoittaa paineen (esim. 9 bar säätimellä) eikä aja tasanteeseen. | Uusi, avoin (laite/työkalu, 25.9.2026) |
| flash palauttaa `pit`:n oletukseen 2,5 s (havaittu esiupito1:llä) — asetukset on asetettava ja kuitattava jokaisen flashin jälkeen. | Uusi, avoin (flash, 25.9.2026) |
| laite kaatui `MemoryError: allocating 8192 bytes` pitkän käyttöajan jälkeen; nollaus korjasi. Isot puskurit (`pstep` varaa 28 KB) pirstovat keon. Välitön syy (`BrewData.get_pressure()` keräsi näytteet listaan, kuri2:n kaatuminen) korjattu kuri3:ssa (e0fb94f, juokseva summa); pirstoutuminen muista isoista puskureista (esim. `pstep`) yhä mahdollinen. | Uusi, avoin (laite), osittain korjattu 28.9.2026 |
| `PCAP_OVER_BAR` toimii yhden raakanäytteen varassa: yksi häiriönäyte kaataa 70 s:n ajon. Kaukalovahti käyttää kahden peräkkäisen näytteen sääntöä samaan tarkoitukseen. Rajan muutos on käyttäjän päätös. **28.9.2026:** raaka `PCAP_OVER_BAR` 11,0 laukeaa kuri:25:llä (suodatettu paine ~9,7 bar, piikit ~+1,4 bar); käyttäjän päätös 28.9.2026: rajaa ei muuteta (vika 15). | Uusi, avoin (turvallisuus) |
| puhelimelle kertyi 14 firmware-settiä 20.9.2026 (`20260920-*`); siivousta ei ole tehty. | Uusi, avoin (siivous) |
| turvarajat olivat komentojen sisällä (kuumavesikytkin ilman rajaa, `fast_heatup`-kaatuminen, `bt:`, `mcal`/`psweep`/`pgap`/`pstep`/`plen`-rajat). Korjattu koodissa 21.–22.9.2026 (TURVA-PIKAKORJAUKSET, TURVA-TOIMILAITE: vartio releiden vieressä, kuumavedelle 13 bar / 180 s / 160 °C) ja flashattu (vkello4 23.9., nyt esiupito2); laitteella todentamatta, tiukempi kuumavesiraja käyttäjän päätös. Yksityiskohdat `paketit/TURVAKATO.md`. | Uusi, avoin (turvallisuus, TURVAKATO-selvitys 21.9.2026) |
| hyväksyntäajo av ei käynnistynyt 2× (`PICO_NOT_ON_USB after charger off (30 s)`, pumppu ei käynyt), vaikka hubi oli kiinni eikä mitään muutettu. Kernel (dmesg): au:n laturin palautus 07:51:24 meni normaalisti (hubi pois 2 s:ssa, puhelin nieluksi), mutta 07:51:30 portti ilmoitti `Type-C Sink (powered) connected` ilman edeltävää `Type-C disconnect`ia ja hubin USB3-osa (2-1) putosi; sen jälkeen kaksi laturin katkaisua eivät tuottaneet yhtään Type-C-tapahtumaa (tilakone jumissa, `host_connected=false`). Purku: `echo 0 > …/otg_switch; sleep 2; echo 1 > …` (07:53:35), jonka jälkeen `cmd pim:1` → `CMD_OK`. Juurisyy (miksi hubin PD-ohjain neuvotteli 3,3 s myöhässä) selvittämättä. Korjausehdotus: `ChargerOff.__enter__` tekee OTG-uudelleenkytkennän ja odottaa uudelleen, kun Pico puuttuu 30 s:n jälkeen. | Uusi, avoin (laite/työkalu, 27.9.2026, EXPRESSO-TYPEC-JUMI) |
| `GUARD_TRIP heater reason=tempstale` laukeaa 8 barin pidossa sekä bim:1:llä (a, b, a2, b2, a3) että bim:0:lla (c2), jo esiuutossa a4:llä (bar 2,3): lämpötilaa ei lueta 10 s:iin (relayguard `HEATER_TEMP_STALE_MS` 10000), joten lämmitin on estetty pidon loppuun. **Muuttunut 28.9.2026 (myöhempi pakkaus):** korjaus koodissa (toinen ydin, EXPRESSO-TEMPSTALE-JA-OLETUS), ei flashattu, laitteella todentamatta. Osa juurisyistä korjattu tässä sessiossa: `BrewData.get_pressure()` keräsi 16,7 ms:n näytteet listaan (~8 kt), pirstoutunut keko kaatoi mainin (MemoryError, kuri2) → juokseva summa kuri3:ssa (vika 14:n välitön syy; `get_pressure_*`-pitkäversio `classes.py:1262` käyttää yhä listaa). `kuri:1`- kuvion vaihevaellus (20 ms päällä / 20 ms pois ei ollut lukittu verkkokelloon, liukui ~16 µs/jakso, käyttäjä kuuli syklihäiriön) korjattu kuri6:ssa (efed272): lukittu verkon vaiheeseen Verkkokellolla, laitteella err=0 (25,0 iskua/s). | Uusi, avoin (firmware, 28.9.2026) |
| Pico nollautuu itsestään ~1–2 h välein 5.10.2026 alkaen (51 USB disconnectia 4 pv:ssä, Zeron `journalctl -k`); osa syistä selvinnyt: serial_commands `sys.stdin.read(1)` -UnicodeError (0cf4756, ks. uusi vika) on todennäköinen syy osalle 5.–7.10. nollauksista, muut syyt avoimia; pysyvä loki toteutunut DIAGNETin kautta (EXPRESSO-PICO-SARJALOKI), Zeron ser2net-lokia ei tarvita; mahdollinen yhteys "uutto rikki" -havaintoon 13.41.39 | avoin (muut nollaussyyt tuntemattomia, 20.10.2026) |
| `pico/MANIFEST.json` jäi päivittämättä aa3bb8c-commitissa (koodi-commit ilman MANIFESTia) | korjattu b466b19 7.10.2026 |
| `PressureSensor.get_pressure()` (`pico/classes.py:1313`) → `ZeroDivisionError`: 16,7 ms:n keruuikkuna kului ennen ensimmäistä näytettä (`cycle_counter` 0), kun jokin (todennäköisesti gc tai ajastimen keskeytys; `free` putosi 3 kt:hen, `lmax_us` ~40–48 ms) pysäytti tehtävän `ticks_us()`:n ja silmukkaehdon välissä. Kaatoi mainin kahdesti: 20.10.2026 17.42.37 ja 21.10.2026 01.57.57 (DIAGNET; DEVSAFE releet 0, vahtikoira rc=3 19 s:ssa). Sama kuvio `classes.py:1343–1357`. Yön `GUARD_TRIP heater reason=norise` 23.57 alkaen ei ole vika: käyttäjä sammuttaa keittimen yöksi, ja Zero pitää Picon käynnissä (käyttäjä 21.10.2026). | korjattu 35bcace 21.10.2026 (kumpikin keruu ottaa vähintään yhden näytteen, MANIFEST päivitetty; flashattu 21.10.2026 06.31: FLASH_OK, VERIFIED 24/24, `testit/flash-20261021-zerodiv.log`, käynnistys f06135fb normaali; isäntätesti ajamatta (käyttäjä: "älä testaa vielä")); odottaa ajoa: todennus = ei `ZeroDivisionError`ia DIAGNETissa (todenna viim. 4.11.2026) |
| serial_commands `sys.stdin.read(1)` → UnicodeError yhdestä ei-UTF-8-tavusta kaatoi kaikki asyncio-tehtävät (DEVSAFE, vahtikoiran nollaus); DIAGNET tallensi 20.10.2026 10.18.58. Todennäköinen syy osalle 5.–7.10. spontaaneista nollauksista; muut syyt avoimia. | korjattu 0cf4756 20.10.2026 (laitteella) |
| laitteella oli 5.10. functions.py/main.py, vaikka b466b19 kirjasi 7.10. flashin VERIFIED 20/20 — mikä palautti vanhan setin, tuntematon. | avoin |
| ilman oppia (arm 2) uuton jälkeen PI ottaa ohjauksen heti ja integraali valuu ylityksessä → alitus −1,3 °C (09.56–09.59). | korjattu b672e71 21.10.2026 (myös 30b7e38; flashattu 23f7971, laitetodennus avoin; ks. Avoimet asiat "arm 2"); odottaa ajoa (todenna viim. 4.11.2026) |
| arm 2 -settle luovutti PI:lle, kun lämmitin oli ollut ~2 min pois; kuollut aika ~25 s → alitus −0,86 (11.07) / −0,94 (10.51). | korjattu b672e71 21.10.2026 (flashattu 23f7971, laitetodennus avoin); odottaa ajoa (todenna viim. 4.11.2026) |
| arm 2 -settle voi luovuttaa kuopan pohjalla ennen maksetun lämmön saapumista (avg ≤ tavoite ja ei nouse) → mallissa ylitys +5…+7 °C; laitteella ei vielä nähty. | korjattu b672e71 21.10.2026 (laitteella ei vielä nähty); odottaa ajoa |
| painekalibrointi gain 1,0 / offset −0,99 näytti 0 bar → −1,4 bar, 8 bar oikein. | korjattu 22.10.2026 (pcalset, ei commitia); odottaa käyttäjää |

Muut eXpresso-viat ovat toistaiseksi päärekisterin luvussa 4.6 ja siirtyvät tänne
EXPRESSO-SKOOPPISIIRTO-paketin mukana.

## Historia

Toteutushistoria: `Infra/iot/expresso/HISTORIA.md` (pakkaus lisää merkinnän sinne, ei tähän).
