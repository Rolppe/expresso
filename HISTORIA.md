# infra expresso — toteutushistoria

Tämän tiedoston omistaa skooppi `infra expresso`. **Purku ei lue tätä**
(`Infra/skills/keskustelun-siirto/references/infra.md`, luku `infra expresso`): pura lukee
`Infra/iot/expresso/REKISTERI.md`:n ja rekisterin nimeämät `KEHITYSYHTEYS.md`:n luvut. Pakkaus
lisää uuden merkinnän tämän tiedoston kärkeen `## Toteutushistoria`-otsikon alle.

## Toteutushistoria

- 27.10.2026 — Käsitelty käyttäjän pyyntö: Malliton purku: lue ~/.local/state/pura/infra-expresso.md ja noudata sitä.
  - Esitetty purkuraportti ja odottavat käyttäjän päätösvaihtoehdot.
  - Käyttäjä antoi komennon /pakkaa; pakataan istunto.
  - todettu (ei rekisteriin): Git-tila: skoopin poluissa ei muutoksia tässä istunnossa.
  - todettu (ei rekisteriin): Testiajoja ei ajettu tässä istunnossa.
- 27.10.2026 — Käsitelty käyttäjän pyyntö: Myöhemmin kuitenkin olin näkevinäni oneplus pyörivän infra expresso skoopin. Tarkista virllä
  - todettu (ei rekisteriin): Git-tila: claude/charming-brahmagupta-p9hmm7, muokattuja tiedostoja yhteensä 11 kpl
  - todettu (ei rekisteriin): Testiajoja ei löytynyt transkriptista — testitulosta ei väitetä
- 27.10.2026 — Todennettu C1X oletuksena laitteella ja uuttotoiminta (EXPRESSO-C1X-TODENNUS, TILAUS-O, TILAUS-AUTONOMIA): - Todettu `BrewData.eu_c1x = 1` oletuksena firmware-tasolla (`pico/classes.py`). - Todettu `commands.handle_command` käsittelee `c1x:0` ja `c1x:1` oikein (`pico/commands.py`). - Todettu firmware-vakiot `EU_C1X_LAG_S = 0.025` ja `EB_C1X_KP_TAIL = 0.2` (`pico/functions.py`). - Analysoitu ja todennettu 21.10.2026 laiteuuttosarja (`testit/bh-20261021-s1..s4.log`, 4 uuttoa): - `EU_START` sisältää `c1x=1` oletuksena jokaisessa uutossa ilman erillistä komentoa. - `EU_END` `late=0, miss=0` ja `EB_END` `late=0, miss=0` kaikissa uutoissa. - `EB_C1X` `ovf=0, late=0, starve=0` kaikissa uutoissa. - Invariantti TILAUS-O toteutuu täydellisesti (0 pudonnutta tai lisättyä pumppujaksoa). - Laadittu brief `paketit/C1X-TODENNUS.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0). - Luotu savutesti `testit/c1x_todennus_smoke.py`, joka testaa kohdat 1–5 (RESULT: 0 failed). - Päivitetty `REKISTERI.md` ja `HISTORIA.md`. Commitoitu (9ce12aa) ja pushattu expresso-repoon.
  - ratkennut (Avoimet asiat): c1x oletuksena laitteella (kirjattu 20.10.2026) — Todennettu C1X oletuksena laitteella ja uuttotoiminta.
  - todettu (ei rekisteriin): `testit/c1x_todennus_smoke.py`: 5/5 hyväksytty, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/c1x_lag_smoke.py`: C1–C7 hyväksytty, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tilaus_invariantit_smoke.py`: 68/68 passed, RESULT: 0 failed.
  - todettu (ei rekisteriin): `vaatimukset.mjs --tarkista`: exit 0 briefille `C1X-TODENNUS.brief.md`.
- 27.10.2026 — Todennettu c1x oletuksena laitteella ja uuttotoiminta (EXPRESSO-C1X-TODENNUS, TILAUS-O, TILAUS-AUTONOMIA):
  - Todettu `BrewData.eu_c1x = 1` oletuksena firmware-tasolla (`pico/classes.py`).
  - Todettu `commands.handle_command` käsittelee `c1x:0` ja `c1x:1` oikein (`pico/commands.py`).
  - Todettu firmware-vakiot `EU_C1X_LAG_S = 0.025` ja `EB_C1X_KP_TAIL = 0.2` (`pico/functions.py`).
  - Analysoitu ja todennettu 21.10.2026 laiteuuttosarja (`testit/bh-20261021-s1..s4.log`, 4 uuttoa):
    - `EU_START` sisältää `c1x=1` oletuksena jokaisessa uutossa ilman erillistä komentoa.
    - `EU_END` `late=0, miss=0` ja `EB_END` `late=0, miss=0` kaikissa uutoissa.
    - `EB_C1X` `ovf=0, late=0, starve=0` kaikissa uutoissa.
    - Invariantti TILAUS-O toteutuu täydellisesti (0 pudonnutta tai lisättyä pumppujaksoa).
  - Laadittu brief `paketit/C1X-TODENNUS.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - Luotu savutesti `testit/c1x_todennus_smoke.py`, joka testaa kohdat 1–5 (RESULT: 0 failed).
  - Päivitetty `REKISTERI.md` ja `HISTORIA.md`.
  - todettu (ei rekisteriin): c1x_todennus_smoke.py: RESULT 0 failed.
  - todettu (ei rekisteriin): c1x_lag_smoke.py: RESULT 0 failed.
  - todettu (ei rekisteriin): tilaus_invariantit_smoke.py: 68/68 passed, RESULT 0 failed.


- 27.10.2026 — Sovitettu C1X-jälkinousun lisäviive laitedatasta (EXPRESSO-C1X-JALKINOUSU, TILAUS-O, TILAUS-K, TILAUS-AUTONOMIA): - Analysoitu laitedata `testit/sovita_c1x_lag.py`-skriptillä 20.10.2026 kootuista laiteajoista (sarja 1 [dly=0.0] ja sarja 2 [dly=0.02], yhteensä 12 uuttoa). - Sarja 1 (dly=0.0): c1x ka dt 0.0904 s vs c0 0.0728 s -> viive-ero 17.6 ms, ylitysero +0.36 bar. - Sarja 2 (dly=0.020): c1x ka dt 0.1049 s vs c0 0.0714 s -> viive-ero 33.4 ms, jäännösylitys +0.07 bar. - Kaikkien 11 täyden nopeuden ajon keskimääräinen lisäviive c1x vs c0 on 24.1 ms (~24–25 ms). - Sarja 2:n jäännösylitys (+0.07 bar @ 21.5 bar/s) poistuu 3.1 ms lisäyksellä -> optimaalinen sovitusviive 23.1 ms (~0.024–0.025 s). - Fysikaalinen malli selittää viiveen: k+2-jonon ajoitusaskel (20 ms) + SSR-40DA -puolijohdereleen nollaylityksen odotusaika (tasajakautunut 0..10 ms, odotusarvo 5 ms) = 25 ms. - Päivitetty `pico/functions.py`: `EU_C1X_LAG_S = 0.025` (25 ms = 1¼ verkkojaksoa). - Laadittu brief `paketit/C1X-JALKINOUSU.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0). - Luotu savutesti `testit/c1x_lag_smoke.py`, joka testaa C1–C7 (RESULT: 0 failed, 14/14 tarkistusta). - Päivitetty tiivisteet `pico/MANIFEST.json`:iin komennolla `pico_dev.py manifest pico/MANIFEST.json`. - Päivitetty `REKISTERI.md` ja `HISTORIA.md`. Commitoitu ja pushattu expresso-repoon (commit ac1cd5b).
  - todettu (ei rekisteriin): c1x_lag_smoke.py: C1–C7 hyväksytty, RESULT: 0 failed (14/14 tarkistusta).
  - todettu (ei rekisteriin): sovita_c1x_lag.py: 12 laiteuuttoa analysoitu, mitattu viive ka 24.1 ms, jäännösylityksen kompensoiva sovitus 23.1 ms.
  - todettu (ei rekisteriin): tilaus_invariantit_smoke.py: hyväksytty, RESULT: 0 failed (68/68 passed).
  - todettu (ei rekisteriin): vaatimukset.mjs --tarkista: exit 0 briefille C1X-JALKINOUSU.brief.md.
- 27.10.2026 — Sovitettu C1X-jälkinousun lisäviive laitedatasta (EXPRESSO-C1X-JALKINOUSU, TILAUS-O, TILAUS-K, TILAUS-AUTONOMIA):
  - Analysoitu laitedata `testit/sovita_c1x_lag.py`-skriptillä 20.10.2026 kootuista laiteajoista (sarja 1 [dly=0.0] ja sarja 2 [dly=0.02], yhteensä 12 uuttoa).
  - Sarja 1 (dly=0.0): c1x ka dt 0.0904 s vs c0 0.0728 s -> viive-ero 17.6 ms, ylitysero +0.36 bar.
  - Sarja 2 (dly=0.020): c1x ka dt 0.1049 s vs c0 0.0714 s -> viive-ero 33.4 ms, jäännösylitys +0.07 bar.
  - Kaikkien 11 täyden nopeuden ajon keskimääräinen lisäviive c1x vs c0 on 24.1 ms (~24–25 ms).
  - Sarja 2:n jäännösylitys (+0.07 bar @ 21.5 bar/s) poistuu 3.1 ms lisäyksellä -> optimaalinen sovitusviive 23.1 ms (~0.024–0.025 s).
  - Fysikaalinen malli selittää viiveen tarkasti: k+2-jonon ajoitusaskel (20 ms) + SSR-40DA -puolijohdereleen nollaylityksen odotusaika (tasajakautunut 0..10 ms, odotusarvo 5 ms) = 25 ms.
  - Päivitetty `pico/functions.py`: `EU_C1X_LAG_S = 0.025` (25 ms = 1¼ verkkojaksoa).
  - Laadittu brief `paketit/C1X-JALKINOUSU.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - Luotu savutesti `testit/c1x_lag_smoke.py`, joka testaa C1–C7 (RESULT: 0 failed, 14/14 tarkistusta).
  - Päivitetty tiivisteet `pico/MANIFEST.json`:iin komennolla `pico_dev.py manifest pico/MANIFEST.json`.
  - Päivitetty `REKISTERI.md` ja `HISTORIA.md`.
  - todettu (ei rekisteriin): c1x_lag_smoke.py: RESULT 0 failed (14/14 tarkistusta).
  - todettu (ei rekisteriin): sovita_c1x_lag.py: 12 laiteuuttoa sovitettu, ka 24.1 ms.
  - todettu (ei rekisteriin): tilaus_invariantit_smoke.py: 68/68 passed, RESULT 0 failed.

- 27.10.2026 — Toteutettu säiliön vesimäärän tunnistus lämpöstabiiliuden saavutusnopeudesta (EXPRESSO-VESIMAARA-TUNNISTUS, TILAUS-Q): - Luotu `pico/water_tank.py` (`WaterTankTracker`): - Seuraa lämpöstabiiliuden (TS) nousua kylmäkäynnistyksestä (TS <= -8.0) arviointikynnykseen (TS >= -2.0). - Laskee saavutusajan t_reach_s = (t_target - t_start). - Arvioi säiliön vesimäärän V_est = model_a * t_reach_s + model_b (oletus a=0.0020 L/s, b=-0.40 L, rajataan 0.0...capacity 2.0 L). - Lämpimässä käynnistyksessä (TS > -6.0) ei aloiteta virheellistä kylmämittausta, vaan säilytetään edellinen taso ('warm_start'). - Seuraa vedenkulutusta (consume_water_ml ja consume_water_l), ja asettaa 'low_water'-varoitustilan (<= 0.3 L). - Tallentaa tilan Picolla atomisesti tiedostoon `water_tank.json` (tmp + rename). - Päivitetty `pico/classes.py`: - `BrewData`: attribuutti `self.water_tank` ja getterit `get_tank_water_l()`, `get_tank_water_pct()`, `get_tank_status()`, `get_tank_last_reach_s()`. - `Thermostat.run`: kutsuu `wt.update(self.thermal_stability, now, mode)` jokaisella suorituskierroksella. - Päivitetty `pico/diagnet.py`: - Lisätty `tk=%s` (`_f2(bd.get_tank_water_l())`) `DIAG_MIN`-riville. - Päivitetty `pico/bluetooth_handler.py`: - Lisätty `tank_water_l`, `tank_pct`, `tank_status` reaaliaikatelemetriaan (`live_payload` ja `scale_payload`). - Päivitetty `NOTIFY_DROP_ORDER = ('tank_pct', 'tank_status', 'tank_water_l', 'thermal_stability')` MTU-ylitysten estämiseksi. - Päivitetty `pico/commands.py`: - Lisätty kyselykomento `tank?` ja ohjauskomennot `tank:fill`, `tank:set:<L>`, `tank:cal:<a>:<b>`, `tank:consume:<ml>`. - Päivitetty `pico/main.py`: - Alustetaan `brew_data.water_tank = water_tank.WaterTankTracker(utime)`. - Laadittu brief `paketit/VESIMAARA-TUNNISTUS.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0). - Luotu uusi kattava savutesti `testit/vesimaara_smoke.py`, joka testaa M1–M9 (RESULT: 0 failed, 32/32 tarkistusta). - Päivitetty tiivisteet `pico/MANIFEST.json`:iin komennolla `pico_dev.py manifest pico/MANIFEST.json`. - Päivitetty `REKISTERI.md` ja `HISTORIA.md`. Commitoitu ja pushattu expresso-repoon (commit a9c184c).
  - todettu (ei rekisteriin): termostaatti_smoke.py: kaikki testit hyväksytty, RESULT: 0 failed.
  - todettu (ei rekisteriin): smart_tray_smoke.py: kaikki testit hyväksytty, RESULT: 0 failed.
  - todettu (ei rekisteriin): Kaikki muut smoke-testit hyväksytty: lampotilatilat_smoke.py (0 failed), valmiustila_smoke.py (0 failed), turva_pika_smoke.py (0 failed), turva_toimilaite_smoke.py (0 failed), nollausikkuna_smoke.py (0 failed), tilaus_invariantit_smoke.py (0 failed, 68 passed), build_set_smoke.py (0 failed).
- 27.10.2026 — Toteutettu säiliön vesimäärän tunnistus lämpöstabiiliuden saavutusnopeudesta (EXPRESSO-VESIMAARA-TUNNISTUS, TILAUS-Q, REKISTERI.md):
  - Luotu `pico/water_tank.py` (`WaterTankTracker`):
    - Seuraa lämpöstabiiliuden nousua kylmäkäynnistyksestä (TS <= -8.0) arviointikynnykseen (TS >= -2.0).
    - Laskee saavutusajan t_reach_s = (t_target - t_start).
    - Arvioi säiliön vesimäärän V_est = model_a * t_reach_s + model_b (oletus a=0.0020 L/s, b=-0.40 L, rajataan 0.0...capacity 2.0 L).
    - Lämpimässä käynnistyksessä (TS > -6.0) ei aloiteta virheellistä mittausta, vaan säilytetään edellinen taso ('warm_start').
    - Seuraa vedenkulutusta (consume_water_ml ja consume_water_l), ja asettaa 'low_water'-varoitustilan (<= 0.3 L).
    - Tallentaa tilan Picolla atomisesti tiedostoon `water_tank.json` (tmp + rename).
  - Päivitetty `pico/classes.py`:
    - `BrewData`: attribuutti `self.water_tank` ja getterit `get_tank_water_l()`, `get_tank_water_pct()`, `get_tank_status()`, `get_tank_last_reach_s()`.
    - `Thermostat.run`: kutsuu `wt.update(self.thermal_stability, now, mode)` jokaisella suorituskierroksella.
  - Päivitetty `pico/diagnet.py`:
    - Lisätty `tk=%s` (`_f2(bd.get_tank_water_l())`) `DIAG_MIN`-riville.
  - Päivitetty `pico/bluetooth_handler.py`:
    - Lisätty `tank_water_l`, `tank_pct`, `tank_status` reaaliaikatelemetriaan (`live_payload` ja `scale_payload`).
    - Päivitetty `NOTIFY_DROP_ORDER = ('tank_pct', 'tank_status', 'tank_water_l', 'thermal_stability')` MTU-ylitysten estämiseksi.
  - Päivitetty `pico/commands.py`:
    - Lisätty kyselykomento `tank?` ja ohjauskomennot `tank:fill`, `tank:set:<L>`, `tank:cal:<a>:<b>`, `tank:consume:<ml>`.
  - Päivitetty `pico/main.py`:
    - Alustetaan `brew_data.water_tank = water_tank.WaterTankTracker(utime)`.
  - Laadittu brief `paketit/VESIMAARA-TUNNISTUS.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - Luotu uusi kattava savutesti `testit/vesimaara_smoke.py`, joka testaa M1–M9 (RESULT: 0 failed, 32/32 tarkistusta).
  - Päivitetty tiivisteet `pico/MANIFEST.json`:iin komennolla `pico_dev.py manifest pico/MANIFEST.json`.
  - Kaikki olemassa olevat savutestit vihreinä (vesimaara, termostaatti, smart_tray, lampotilatilat, valmiustila, turva_pika, turva_toimilaite, nollausikkuna, tilaus_invariantit, build_set: 0 failed).
  - Päivitetty `REKISTERI.md` ja `HISTORIA.md`. Asetettu seuraavaksi paketiksi `EXPRESSO-C1X-JALKINOUSU`.
  - ratkennut (Avoimet asiat): Säiliön vesimäärän tunnistus lämpöstabiiliuden saavutusnopeudesta (TILAUS-Q) — firmware + simulaatiototeutus ja telemetria valmis, odottaa laitetodennusta laiteajoissa.
  - todettu (ei rekisteriin): `testit/vesimaara_smoke.py`: M1–M9 ok, RESULT: 0 failed.

- 27.10.2026 — Toteutettu thermal stability (-10…+10) ylläpitotehon tarpeesta (EXPRESSO-THERMAL-STABILITY, TILAUS-Q, REKISTERI.md):
  - Lasketettu thermal stability IDLE-PI:n integraalista (`self.pi_i`), jossa opittu pitkän aikavälin vakioteho P0 (muuttumaton 30 min, tallennetaan Picolle tiedostoon `thermal_stability.json`, oletus 0.045) = 0.0, kylmäkäynnistyksen ensimmäisen tasaantumisen teho = -10.0 (skaalaus span 0.040), rajaus [-10.0, +10.0].
  - Muissa tiloissa (esim. STEAM, BREW, warming up) säilytetään edellinen IDLE-arvo (`self.thermal_stability`, oletus käynnistyksessä -10.0).
  - Lisätty `BrewData`:an attribuutti `self.thermal_stability` ja metodi `get_thermal_stability()`.
  - Päivitetty `pico/diagnet.py`: `DIAG_MIN`-riville lisätty kenttä `ts=%s` (`_f1(bd.thermal_stability)`).
  - Päivitetty `pico/bluetooth_handler.py`: lisätty `thermal_stability` reaaliaikatelemetriaan (`live_payload` ja `scale_payload`), ja asetettu `NOTIFY_DROP_ORDER = ('thermal_stability',)` jotta 240 B MTU ei ylity koskaan.
  - Päivitetty `pico/commands.py`: lisätty kyselykomento `ts?` / `thermal?` ja manuaalinen P0-asetuskomento `ts:p0:<val>`.
  - Laadittu brief `paketit/THERMAL-STABILITY.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - Lisätty testitapaukset L1–L6 tiedostoon `testit/termostaatti_smoke.py` (RESULT: 0 failed).
  - Päivitetty tiivisteet `pico/MANIFEST.json`:iin (`pico_dev.py manifest`).
  - Kaikki olemassa olevat smoke-testit vihreinä (termostaatti, lampotilatilat, valmiustila, turva_pika, turva_toimilaite, nollausikkuna, tilaus_invariantit, build_set: 0 failed).
  - Päivitetty `REKISTERI.md` ja `HISTORIA.md`. Asetettu seuraavaksi paketiksi `EXPRESSO-VESIMAARA-TUNNISTUS`.
  - ratkennut (Avoimet asiat): Thermal stability −10…+10 (TILAUS-Q) — toteutettu firmwareen, telemetriaan, sarjakomentoihin ja DIAG_MIN-lokiin.
  - todettu (ei rekisteriin): `testit/termostaatti_smoke.py`: L1–L6 ok, RESULT: 0 failed.

- 27.10.2026 — Estetty uutonjälkeisen lämmönsäädön (post_brew) ja asettumisvaiheen (settle) aktivoituminen kylmällä kattilalla (EXPRESSO-POST-BREW-COLD-SETTLE, REKISTERI.md):
  - Juurisyy selvitetty: kun keitin kytkettiin verkkovirtaan klo 07:39 ja huuhdeltiin kylmällä kattilalla (25 °C), `functions.py` asetti `bh_arm = 2` ja termostaatti siirtyi `settle`-tilaan, jossa lämmitintä pulssitetaan vain 5,6 % teholla (`pi_i = 0.056`). 25 °C:ssa 56 W nettolämmitys nostaa lämpötilaa ~0,2 °C/10 s, jolloin `avg < prev + 0.05` ei voi koskaan toteutua ja säädin jäi jumiin `BH_NOLEARN_MAX_MS` (10 min) maksimiin. Jokainen uusi huuhtelu uusi `bh_arm = 2` ja 10 min ajastimen alusta.
  - Korjaus: määritelty `BH_COLD_C = 15.0` (`target - 15.0 °C`). Kylmällä kattilalla huuhtelu/uutto nollaa `bh_arm = 0` eikä kerrytä `bh_sum_us`-arvoa (`pico/functions.py`). `Thermostat.run` ja `_post_brew` (`pico/classes.py`) poistuvat välittömästi `settle`-tilasta ilman oppia (`why == 'cold'`), jos kattila on kylmä, ja lämmitys toimii täydellä teholla (step cycler).
  - Laadittu brief `paketit/POST-BREW-COLD-SETTLE.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - Lisätty kattavat testit K1–K4 `testit/termostaatti_smoke.py`:hyn.
  - Päivitetty tiivisteet `pico/MANIFEST.json`:iin komennolla `python3 pico_dev.py manifest pico/MANIFEST.json`.
  - Kaikki olemassa olevat smoke-testit vihreinä (termostaatti, lampotilatilat, valmiustila, turva_pika, turva_toimilaite, nollausikkuna, tilaus_invariantit, build_set: 0 failed).
  - Päivitetty `REKISTERI.md` ja `HISTORIA.md`.
  - ratkennut (Avoimet asiat): EXPRESSO-POST-BREW-COLD-SETTLE — kylmän kattilan huuhtelu ei jää 5,6 %:n settle-pitoon.
  - todettu (ei rekisteriin): `testit/termostaatti_smoke.py`: K1–K4 ja H1–H10 ok, RESULT: 0 failed.

- 27.10.2026 — Tilauksen menetelmäkohdat nimetyiksi invarianteiksi (EXPRESSO-TILAUS-INVARIANTIT, REKISTERI.md):
  - Nimettiin kaikki tilauksen menetelmäkohdat (`TILAUS-A`…`TILAUS-T`, `TILAUS-RELEET-ALAS`, `TILAUS-AUTONOMIA`) `KAYTTAJAN-TIEDOT.md`:ssä käyttäjän omina lainauksina ja viittein `paketit/PUMPPU-PWM.md`:n riveihin.
  - Täydennettiin takautuvassa tarkistuksessa myös kohdat 3 (`TILAUS-S`, max flow rate) ja 4 (`TILAUS-T`, höyryn lämpötilan säädin +10 °C).
  - Päivitettiin `paketit/PUMPPU-PWM.md`:n vaihetaulukkoon `Tilauskohdan tunnus` -sarake vaiheille 1a–1f, 2, 3, 4.
  - Päivitettiin `REKISTERI.md`:n luku muotoon `## Pysyvät vaatimukset (Tilauksen invariantit)`.
  - Laadittu brief `paketit/TILAUS-INVARIANTIT.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - Luotu uusi kattava savutesti `testit/tilaus_invariantit_smoke.py`, joka todentaa kaikkien 22 tilausinvariantin olemassaolon ja viitteet, vaihetaulukon kattavuuden, purkutulosteen sekä koneellisen tarkistuksen (`vaatimukset.mjs`) läpäisevällä ja hylkäävällä esimerkillä (RESULT: 0 failed, 68/68 tarkistusta).
  - Päivitetty `REKISTERI.md`, `HISTORIA.md`, `ARKISTO.md` ja `paketit/TILAUS-INVARIANTIT.md` (valmis 27.10.2026).
  - Asetettu seuraavaksi paketiksi `EXPRESSO-THERMAL-STABILITY`.
  - ratkennut (Avoimet asiat): EXPRESSO-TILAUS-INVARIANTIT — tilauksen menetelmäkohdat nimetyiksi invarianteiksi ja koneellinen tarkistus todennettu.
  - todettu (ei rekisteriin): `testit/tilaus_invariantit_smoke.py`: 68/68 ok, RESULT: 0 failed.

- 27.10.2026 — Todettu uuton lämmitysteho virtauksesta toteutetuksi ja siivottu käyttämättömät vakiot (EXPRESSO-LAMMITYS-VIRTAUS, TILAUS-N, TILAUS-R, REKISTERI.md):
  - Uuton lämmitysteho virtauksesta (TILAUS-N) ja vaihekohtainen lämmönsäätö (TILAUS-R) on toteutettu `pico/functions.py`:ssä (`_bh_add(p)`, `hk0 - hk1 * p if p < BH_PMAX else 0.0`) ja todennettu laiteajoissa 21.10.2026 (`bh-20261021-*.log`) commitissa `2754d74`.
  - Poistettu `pico/functions.py`:stä tarpeeton ja käyttämätön pulssitusvakio `EB_HEAT_OFF_MS, EB_HEAT_ON_MS = 100, 50`.
  - Laadittu brief `paketit/LAMMITYS-VIRTAUS.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - `pico/MANIFEST.json`: päivitetty `functions.py`:n osalta `pico_dev.py manifest pico/MANIFEST.json` -komennolla.
  - Kaikki olemassa olevat smoke-testit vihreinä (shot_test, turva_pika, valmiustila, termostaatti: 0 failed).
  - Päivitetty `REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`. Asetettu seuraavaksi paketiksi `EXPRESSO-TILAUS-INVARIANTIT`.
  - ratkennut (Avoimet asiat): EXPRESSO-LAMMITYS-VIRTAUS — uuton lämmitysteho pumpun iskuista ja paineesta (TILAUS-N, TILAUS-R) toteutettu ja todennettu; käyttämätön EB_HEAT-vakio siivottu.
  - ratkennut (Avoimet asiat): EXPRESSO-TURVAKATO — valmis (nollausikkuna devsafe.relays_off() boot.py:ssä todennettu 26.10.2026).
  - todettu (ei rekisteriin): `testit/shot_test.py`: 80/80 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_pika_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/valmiustila_smoke.py`: 34/34 ok, RESULT: 0 failed.

- 27.10.2026 — Siirretty `import utime` `BrewData.update_standby`-metodista moduulitasolle (EXPRESSO-STANDBY-IMPORT-UTIME, REKISTERI.md):
  - `pico/classes.py`: tuotu `utime` moduulitasolla (`try: import utime except ImportError: utime = None`). Poistettu toistuva `import utime` `BrewData.update_standby`-kutsusta pääsilmukasta ja käytetty instanssin tai moduulitason kelloa (`clock = self.utime or utime`).
  - `paketit/STANDBY-IMPORT-UTIME.brief.md`: laadittu brief tehtävälle ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - `testit/valmiustila_smoke.py`: päivitetty savutesti tarkistamaan, että `update_standby` ei tee paikallista `import utime` -kutsua ja että `utime` on tuotu moduulitasolla (RESULT: 0 failed, 34/34 tarkistusta).
  - `pico/MANIFEST.json`: päivitetty `classes.py`:n osalta `pico_dev.py manifest pico/MANIFEST.json` -komennolla.
  - Kaikki olemassa olevat smoke-testit vihreinä (valmiustila, termostaatti, turva_pika, turva_toimilaite, nollausikkuna, eu_rivi, shot_test, steam_paine, smart_tray, settings_pysyvyys: 0 failed).
  - Päivitetty `REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`.
  - ratkennut (Avoimet asiat): `update_standby` tekee `import utime` joka kierroksella (kirjattu 5.10.2026) — siirretty moduulitasolle pico/classes.py:ssä.
  - todettu (ei rekisteriin): `testit/valmiustila_smoke.py`: 34/34 ok, RESULT: 0 failed.

- 27.10.2026 — Arvioitu EU-rivin muoto: C1-JAKSOT hoitaa 1 kHz näytteenoton ja releiden kääntöjen ajoituksen ytimellä 1 muistilukittuna (`heap_lock()`), joten ytimen 0 keruuviiveet eivät aiheuta myöhästymisiä tai syklin ohituksia (`miss = 0`, `late = 0`, TILAUS-O toteutuu). EU-rivin arvojen muuttaminen kiinteiksi kokonaisluvuiksi (kuten senttibaareiksi) rikkoisi olemassa olevat analyysit (`esiuutto_analyysi.py`, `uutto8_sovitus.py`, `esiuutto_smoke.py`) ja vertailukelpoisuuden aiempiin uuttolokeihin ilman hyötyä ytimen 1 ajoitukselle.
  - Keventetty uuttosilmukan (`pre_infusion_phased`) allokaatiot `pico/functions.py`:ssä: korvattu 50 krt/s tapahtuva `out = []` in-place-tyhjennyksellä `del out[:]` (poistaa 50 tyhjän listan allokaatiota sekunnissa).
  - Inloitu `weight_flow_log`:n paino- ja virtauskentät suoraan päämerkkijonoon ilman väliaikaista 'w=... f=...' -merkkijonoa.
  - Korvattu USB-CDC -jonon generaattorisumma `sum(len(x) + 1 for x in out)` suoralla silmukalla.
  - Laadittu brief `paketit/EU-RIVI-KOKONAISLUVUT.brief.md` ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - Luotu kattava smoke-testi `testit/eu_rivi_smoke.py` (RESULT: 0 failed, 21/21 tarkistusta).
  - Päivitetty `pico/MANIFEST.json` (`pico_dev.py manifest`).
  - Päivitetty `REKISTERI.md` ja `HISTORIA.md`, commitattu `38d7d9d` ja pushattu `origin/main`iin.
  - todettu (ei rekisteriin): `testit/eu_rivi_smoke.py`: 21/21 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): Kaikki 15 smoke-testiä ajettu ja todettu onnistuneiksi (eu_rivi, settings_pysyvyys, smart_tray, shot_test, lampotilatilat, tray_guard, tray_total, vaaka_komennot, valmiustila, termostaatti, steam_paine, kuumavesi, turva_pika, turva_toimilaite, nollausikkuna: 0 failed).
  - todettu (ei rekisteriin): Git `Infra/iot/expresso`: commitit pushattu puhtaasti `origin/main`iin (`38d7d9d`).
- 26.10.2026 — Toteutettu ja todennettu uuttosilmukan allokaatiokevennykset ja arvioitu EU-rivin muoto (EXPRESSO-EU-RIVI-KOKONAISLUVUT, REKISTERI.md):
  - Arvio: C1-JAKSOT hoitaa 1 kHz näytteenoton ja releiden kääntöjen ajoituksen ytimellä 1 muistilukittuna (`heap_lock()`), joten ytimen 0 keruuviiveet eivät aiheuta myöhästymisiä tai syklin ohituksia (`miss = 0`, `late = 0`, TILAUS-O toteutuu). EU-rivin arvojen muuttaminen kiinteiksi kokonaisluvuiksi (kuten senttibaareiksi) rikkoisi olemassa olevat analyysit (`esiuutto_analyysi.py`, `uutto8_sovitus.py`, `esiuutto_smoke.py`) ja vertailukelpoisuuden aiempiin uuttolokeihin ilman hyötyä ytimen 1 ajoitukselle.
  - `pico/functions.py`: korvattu 50 krt/s tapahtuva `out = []` in-place-tyhjennyksellä `del out[:]` (poistaa 50 tyhjän listan allokaatiota sekunnissa), inloitu `weight_flow_log`:n w- ja f-kentät suoraan päämerkkijonoon ilman väliaikaista 'w=... f=...' -merkkijonoa ja korvattu USB-CDC -jonon generaattorisumma `sum(len(x) + 1 for x in out)` suoralla silmukalla.
  - `paketit/EU-RIVI-KOKONAISLUVUT.brief.md`: laadittu brief tehtävälle ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0).
  - `testit/eu_rivi_smoke.py`: uusi kattava savutesti, joka todentaa `functions.py`:n in-place-tyhjennyksen, generaattorin poiston, listan identiteetin säilymisen ja EU-rivin yhteensopivuuden olemassa olevien parsereiden kanssa (RESULT: 0 failed, 21/21 tarkistusta).
  - `pico/MANIFEST.json`: päivitetty `functions.py`:n osalta `pico_dev.py manifest pico/MANIFEST.json` -komennolla.
  - Kaikki olemassa olevat smoke-testit vihreinä (eu_rivi, settings_pysyvyys, smart_tray, shot_test, lampotilatilat, tray_guard, tray_total, vaaka_komennot, valmiustila, termostaatti, steam_paine, kuumavesi, turva_pika, turva_toimilaite, nollausikkuna: 0 failed).
  - Päivitetty `REKISTERI.md`, `HISTORIA.md`. Asetettu seuraavaksi paketiksi `EXPRESSO-STANDBY-IMPORT-UTIME`.
  - ratkennut (Avoimet asiat): EU-rivi kokonaisluvuin (kirjattu 20.10.2026) — arvioitu C1-JAKSOTin jälkeen ja uuttosilmukan allokaatiot kevennetty pico/functions.py:ssä.
  - todettu (ei rekisteriin): `testit/eu_rivi_smoke.py`: 21/21 ok, RESULT: 0 failed.

- 26.10.2026 — Toteutettu ja todennettu releiden nollausikkunan poisto ja työkalupolkujen auditointi (EXPRESSO-TURVAKATO-NOLLAUSIKKUNA, KAYTTAJAN-TIEDOT.md §5, REKISTERI.md): - `pico/boot.py`: `devsafe.relays_off()` suoritetaan ensimmäisenä lauseena heti käynnistyksen alussa ennen mitään muita importteja tai `time.sleep(0.1)` -viivettä. Releiden nollausikkuna watchdog- ja käynnistystilanteissa poistettu: mikään rele ei jää päälle nollauksen tai vikatilanteen aikana. - `KAYTTAJAN-TIEDOT.md`: käyttäjän 7.10.2026 asettama vaatimus kirjattu tunnusrivinä `TILAUS-RELEET-ALAS` osioon 5 (Turvallisuus). - Työkalupolkujen auditointi: `pico_dev.py`:n kaikki laiteohjaus- ja reset-toiminnot (`safe`, `verify`, `flash`, `watchdog_test`) varmistavat `enter_devsafe()`-kutsulla releiden nollauksen ja tarkistavat `SAFE_OK`-tilanteen. - `paketit/RELEET-ALAS-NOLLAUSIKKUNA.brief.md`: laadittu brief tehtävälle ja tarkistettu `vaatimukset.mjs --tarkista` (exit 0). - `testit/nollausikkuna_smoke.py`: uusi kattava savutesti, joka todentaa `boot.py`:n, `main.py`:n, `devsafe.py`:n ja `pico_dev.py`:n releinvarianssit sekä simuloidun boot-ajon (RESULT: 0 failed, 20/20 tarkistusta). - `pico/MANIFEST.json`: päivitetty `boot.py`:n osalta `pico_dev.py manifest pico/MANIFEST.json` -komennolla. - Kaikki olemassa olevat smoke-testit vihreinä (settings_pysyvyys, smart_tray, shot_test, lampotilatilat, tray_guard, tray_total, vaaka_komennot, valmiustila, termostaatti, steam_paine, kuumavesi, turva_pika, turva_toimilaite: 0 failed). - Päivitetty `REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`. Asetettu seuraavaksi paketiksi `EXPRESSO-EU-RIVI-KOKONAISLUVUT`. Kaikki commitit (`27e2501`, `d2caf35`) pushattu (`origin/main`).
  - ratkennut (Avoimet asiat): Releet alas `boot.py`:n alkuun + työkalupolkujen auditointi (käyttäjän vaatimus 7.10.2026, Päätökset) — Toteutettu ja todennettu releiden nollausikkunan poisto ja työkalupolkujen auditointi (devsafe.relays_off() boot.py:n alkuun).
  - todettu (ei rekisteriin): `testit/nollausikkuna_smoke.py`: 20/20 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/settings_pysyvyys_smoke.py`: 6/6 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/smart_tray_smoke.py`: 12/12 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/shot_test.py`: 80/80 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/lampotilatilat_smoke.py`: 36/36 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_guard_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_total_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/vaaka_komennot_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/valmiustila_smoke.py`: 32/32 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/termostaatti_smoke.py`: 29/29 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/steam_paine_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/kuumavesi_smoke.py`: 21/21 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_pika_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_toimilaite_smoke.py`: 43/43 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `node claude/siirto/tools/vaatimukset.mjs --rivi "infra expresso"`: 21 vaatimusta, TILAUS-RELEET-ALAS mukana.
  - todettu (ei rekisteriin): Git Infra/iot/expresso: commitit `27e2501` ja `d2caf35` pushattu onnistuneesti `origin/main`iin.
- 26.10.2026 — Toteutettu ja todennettu releiden nollausikkunan poisto ja työkalupolkujen auditointi (EXPRESSO-TURVAKATO-NOLLAUSIKKUNA, KAYTTAJAN-TIEDOT.md §5, REKISTERI.md):
  - `pico/boot.py`: `devsafe.relays_off()` suoritetaan ensimmäisenä lauseena heti käynnistyksen alussa ennen mitään muita importteja tai `time.sleep(0.1)` -viivettä. Releiden nollausikkuna watchdog- ja käynnistystilanteissa poistettu: mikään rele ei jää päälle nollauksen tai vikatilanteen aikana.
  - `KAYTTAJAN-TIEDOT.md`: kirjattu käyttäjän vaatimus (7.10.2026) tunnusrivinä `TILAUS-RELEET-ALAS` osioon 5 (Turvallisuus).
  - Työkalupolkujen auditointi: `pico_dev.py`:n kaikki laiteohjaus- ja reset-toiminnot (`safe`, `verify`, `flash`, `watchdog_test`) varmistavat `enter_devsafe()`-kutsulla releiden nollauksen ja tarkistavat `SAFE_OK`-tilanteen.
  - `testit/nollausikkuna_smoke.py`: uusi kattava savutesti, joka todentaa `boot.py`:n, `main.py`:n, `devsafe.py`:n ja `pico_dev.py`:n releinvarianssit sekä simuloidun boot-ajon (RESULT: 0 failed, 20/20 tarkistusta).
  - `pico/MANIFEST.json`: päivitetty `boot.py`:n osalta `pico_dev.py manifest pico/MANIFEST.json` -komennolla.
  - Kaikki olemassa olevat smoke-testit vihreinä (settings_pysyvyys, smart_tray, shot_test, lampotilatilat, tray_guard, tray_total, vaaka_komennot, valmiustila, termostaatti, steam_paine, kuumavesi, turva_pika, turva_toimilaite: 0 failed).
  - Päivitetty `REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`. Asetettu seuraavaksi paketiksi `EXPRESSO-EU-RIVI-KOKONAISLUVUT`.
  - ratkennut (Avoimet asiat): Releet alas boot.py:n alkuun + työkalupolkujen auditointi — toteutettu 26.10.2026.
  - ratkennut (Avoimet viat): Nollausikkuna: releet 0:aan vasta main.py:3 — korjattu 26.10.2026.
  - todettu (ei rekisteriin): `testit/nollausikkuna_smoke.py`: 20/20 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/settings_pysyvyys_smoke.py`: 6/6 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/smart_tray_smoke.py`: 12/12 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/shot_test.py`: 80/80 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/lampotilatilat_smoke.py`: 36/36 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_guard_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_total_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/vaaka_komennot_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/valmiustila_smoke.py`: 32/32 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/termostaatti_smoke.py`: 29/29 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/steam_paine_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/kuumavesi_smoke.py`: 21/21 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_pika_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_toimilaite_smoke.py`: 43/43 ok, RESULT: 0 failed.


- 26.10.2026 — Toteutettu ja todennettu älykäs painon ja kaukalon tunnistus (EXPRESSO-ALYKAS-PAINO, KAYTTAJAN-TIEDOT.md §9 kohta 4): - `pico/smart_tray.py`: uusi `SmartTrayTracker`-moduuli, joka toteuttaa: - 1. Kaukaloon tulleen veden määrän tunnistus (`water_g`, `water_pct`, max 400.0 g, varoitus 350.0 g). Erottelee veden hitaan tai pumpun/uuton aikaisen kertymän esineiden asettamisesta. - 2. Tyhjennyksen tunnistus keittimen ollessa sammuksissa (`emptied_offline`): vertaa käynnistyksen vakaata lepopainoa tallennettuun tilaan (`tray_state.json`) ja tyhjän kaukalon perustasoon (454.5 g). - 3. Kupin (nimellinen 293.9 g, KAYTTAJAN-TIEDOT), ulkoisen vaa'an (nimellinen 130.0 g), koeastian (50.7 g) sekä yhdistelmän (vaaka + kuppi ~423.9 g) automaattinen tunnistus kaukalolle asetettaessa lepotilassa. Esineiden massaa ei lasketa kaukalon vedeksi. - 4. Kaukalon irrotuksen tunnistus (`<200.0 g -> no_tray`). - 5. Ohjauskomennot: `tray?`, `tray:empty`, `tray:cal_empty`, `tray:wmax:<g>`, `obj?`, `obj:cup:<g>`, `obj:scale:<g>`, `obj:vessel:<g>`. - `pico/classes.py`: lisätty `BrewData.smart_tray` ja getterit `get_tray_water_g()`, `get_tray_water_pct()`, `get_tray_status()`, `get_detected_object()`, `get_detected_object_weight()`, `is_tray_emptied_offline()`. - `pico/main.py`: alustetaan `SmartTrayTracker` ja kutsutaan `update()`:a `scale_poll_once()`-silmukassa. - `pico/bluetooth_handler.py`: lisätty `tray_water_g`, `tray_pct`, `tray_status`, `detected_object` ja `object_weight_g` `scale_payload`-pakettiin. - `pico/commands.py`: lisätty käsittelijät `tray?`, `tray:*`, `obj?`, `obj:*`. - `testit/smart_tray_smoke.py`: kattava yksikkötestaus kaikille vaatimuksille (RESULT: 0 failed, 12 testikohtaa).
  - Toteutettu ja todennettu wmax-pysyvyys ja atominen settings-tallennus (wmax-pysyvyys): - `pico/functions.py`: `save_settings` tehty atomiseksi (`settings.txt.tmp` kirjoitus + `os.rename`), jotta katkos tai nollaus tallennuksen aikana ei korruptoi tai katkaise tiedostoa. - `pico/functions.py`: `load_settings` ei enää koskaan poista `settings.txt`:ää virhetilanteessa (`os.remove('settings.txt')` poistettu), vaan säilyttää tiedoston levyllä ja pitää turvalliset oletukset. Lisäksi toipuminen `settings.txt.tmp`-tiedostosta, jos varsinainen tiedosto puuttuu tai on korruptoitunut. - `pico/functions.py`: kenttäkohtaiset virheet käsitellään turvallisesti, jolloin muut asetukset ja ennen kaikkea kaukalovahdin turvarajat (`weight_limit` / `wmax` ja `weight_rise_limit` / `wrise`) latautuvat häiriöttä. - `pico/MANIFEST.json`: päivitetty vastaamaan kaikkia koodimuutoksia (`pico_dev.py manifest pico/MANIFEST.json`). - `testit/settings_pysyvyys_smoke.py`: uusi erillinen savutesti (RESULT: 0 failed, 6 testikokonaisuutta). - `testit/shot_test.py`: päivitetty wmax-pysyvyystarkistuksin ja korjattu `scale_payload` `first_drop` -yhteensopivuus (RESULT: 0 failed, 80 testiä). - Kaikki olemassa olevat smoke-testit hyväksytty (lampotilatilat, tray_guard, tray_total, vaaka_komennot, valmiustila, termostaatti, steam_paine, kuumavesi, turva_pika, turva_toimilaite: 0 failed). - Päivitetty `REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`. Asetettu seuraavaksi paketiksi `EXPRESSO-TURVAKATO-NOLLAUSIKKUNA`. Kaikki commitit pushattu (`origin/main`).
  - ratkennut (Avoimet asiat): wmax-pysyvyys — wmax-pysyvyys toteutettu ja todennettu: save_settings tehty atomiseksi ja load_settings ei poista settings.txt:ää virheessä.
  - todettu (ei rekisteriin): `testit/smart_tray_smoke.py`: 12/12 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/settings_pysyvyys_smoke.py`: 6/6 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/shot_test.py`: 80/80 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/lampotilatilat_smoke.py`: 36/36 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_guard_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_total_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/vaaka_komennot_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/valmiustila_smoke.py`: 32/32 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/termostaatti_smoke.py`: 29/29 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/steam_paine_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/kuumavesi_smoke.py`: 21/21 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_pika_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_toimilaite_smoke.py`: 43/43 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): Git Infra/iot/expresso: commitit `301ad0a`, `6457e3d`, `e357ccc`, `4f53479` pushattu onnistuneesti `origin/main`iin.
- 26.10.2026 — Toteutettu ja todennettu wmax-pysyvyys ja atominen settings-tallennus:
  - `pico/functions.py`: `save_settings` tehty atomiseksi (`settings.txt.tmp` kirjoitus + `os.rename`), jotta katkos tai nollaus tallennuksen aikana ei korruptoi tai katkaise tiedostoa.
  - `pico/functions.py`: `load_settings` ei enää koskaan poista `settings.txt`:ää virhetilanteessa (`os.remove('settings.txt')` poistettu), vaan säilyttää tiedoston levyllä ja pitää turvalliset oletukset. Lisäksi toipuminen `settings.txt.tmp`-tiedostosta, jos varsinainen tiedosto puuttuu tai on korruptoitunut.
  - `pico/functions.py`: kenttäkohtaiset virheet (esim. yksittäinen virheellinen asetusarvo tai tyyppi) käsitellään turvallisesti, jolloin muut asetukset ja ennen kaikkea kaukalovahdin turvarajat (`weight_limit` / `wmax` ja `weight_rise_limit` / `wrise`) latautuvat häiriöttä.
  - `pico/MANIFEST.json`: päivitetty `functions.py`:n osalta `pico_dev.py manifest pico/MANIFEST.json` -komennolla.
  - Testit: `testit/settings_pysyvyys_smoke.py` (RESULT: 0 failed, 6 testikokonaisuutta), `testit/shot_test.py` (RESULT: 0 failed, korruption ja tmp-toipumisen testit lisätty, scale_payload first_drop -yhteensopivuus päivitetty), kaikki vanhat smoke-testit vihreinä.
  - todettu (ei rekisteriin): `testit/settings_pysyvyys_smoke.py`: 6/6 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/shot_test.py`: 80/80 ok, RESULT: 0 failed.

- 26.10.2026 — Toteutettu ja todennettu älykäs painon ja kaukalon tunnistus (EXPRESSO-ALYKAS-PAINO, KAYTTAJAN-TIEDOT.md §9 kohta 4): - `pico/smart_tray.py`: uusi `SmartTrayTracker`-moduuli, joka toteuttaa: - 1. Kaukaloon tulleen veden määrän tunnistus (`water_g`, `water_pct`, max 400.0 g, varoitus 350.0 g). Erottelee veden hitaan tai pumpun/uuton aikaisen kertymän esineiden asettamisesta. - 2. Tyhjennyksen tunnistus keittimen ollessa sammuksissa (`emptied_offline`): vertaa käynnistyksen vakaata lepopainoa tallennettuun tilaan (`tray_state.json`) ja tyhjän kaukalon perustasoon (454.5 g). - 3. Kupin (nimellinen 293.9 g, KAYTTAJAN-TIEDOT), ulkoisen vaa'an (nimellinen 130.0 g), koeastian (50.7 g) sekä yhdistelmän (vaaka + kuppi ~423.9 g) automaattinen tunnistus kaukalolle asetettaessa lepotilassa. Esineiden massaa ei lasketa kaukalon vedeksi. - 4. Kaukalon irrotuksen tunnistus (`<200.0 g -> no_tray`). - 5. Ohjauskomennot: `tray?`, `tray:empty`, `tray:cal_empty`, `tray:wmax:<g>`, `obj?`, `obj:cup:<g>`, `obj:scale:<g>`, `obj:vessel:<g>`. - `pico/classes.py`: lisätty `BrewData.smart_tray` ja getterit `get_tray_water_g()`, `get_tray_water_pct()`, `get_tray_status()`, `get_detected_object()`, `get_detected_object_weight()`, `is_tray_emptied_offline()`. - `pico/main.py`: alustetaan `SmartTrayTracker` ja kutsutaan `update()`:a `scale_poll_once()`-silmukassa. - `pico/bluetooth_handler.py`: lisätty `tray_water_g`, `tray_pct`, `tray_status`, `detected_object` ja `object_weight_g` `scale_payload`-pakettiin. - `pico/commands.py`: lisätty käsittelijät `tray?`, `tray:*`, `obj?`, `obj:*`. - `pico/MANIFEST.json`: päivitetty kaikkien muutettujen ja lisättyjen tiedostojen koot ja sha256-tiivisteet. - `testit/smart_tray_smoke.py`: kattava yksikkötestaus kaikille vaatimuksille (RESULT: 0 failed, 12 testikohtaa). - Kaikki olemassa olevat smoke-testit hyväksytty (lampotilatilat, tray_guard, tray_total, vaaka_komennot, valmiustila, termostaatti, steam_paine, kuumavesi, turva_pika, turva_toimilaite: 0 failed). - Päivitetty `REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`. Asetettu seuraavaksi paketiksi `wmax-pysyvyys`. Commitoitu ja pushattu (`301ad0a`).
  - todettu (ei rekisteriin): `testit/smart_tray_smoke.py`: 12/12 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/lampotilatilat_smoke.py`: 36/36 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_guard_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_total_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/vaaka_komennot_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/valmiustila_smoke.py`: 32/32 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/termostaatti_smoke.py`: 29/29 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/steam_paine_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/kuumavesi_smoke.py`: 21/21 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_pika_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_toimilaite_smoke.py`: 43/43 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): Git Infra/iot/expresso: commit `301ad0a` pushattu onnistuneesti `origin/main`iin.
- 26.10.2026 — Toteutettu ja todennettu älykäs painon ja kaukalon tunnistus (EXPRESSO-ALYKAS-PAINO, KAYTTAJAN-TIEDOT.md §9 kohta 4):
  - `pico/smart_tray.py`: uusi `SmartTrayTracker`-moduuli, joka toteuttaa:
    - 1. Kaukaloon tulleen veden määrän tunnistus (`water_g`, `water_pct`, max 400.0 g, varoitus 350.0 g). Erottelee veden hitaan tai pumpun/uuton aikaisen kertymän esineiden asettamisesta.
    - 2. Tyhjennyksen tunnistus keittimen ollessa sammuksissa (`emptied_offline`): vertaa käynnistyksen vakaata lepopainoa tallennettuun tilaan (`tray_state.json`) ja tyhjän kaukalon perustasoon (454.5 g).
    - 3. Kupin (nimellinen 293.9 g, KAYTTAJAN-TIEDOT), ulkoisen vaa'an (nimellinen 130.0 g), koeastian (50.7 g) sekä yhdistelmän (vaaka + kuppi ~423.9 g) automaattinen tunnistus kaukalolle asetettaessa lepotilassa. Esineiden massaa ei lasketa kaukalon vedeksi.
    - 4. Kaukalon irrotuksen tunnistus (`<200.0 g -> no_tray`).
    - 5. Ohjauskomennot: `tray?`, `tray:empty`, `tray:cal_empty`, `tray:wmax:<g>`, `obj?`, `obj:cup:<g>`, `obj:scale:<g>`, `obj:vessel:<g>`.
  - `pico/classes.py`: lisätty `BrewData.smart_tray` ja getterit `get_tray_water_g()`, `get_tray_water_pct()`, `get_tray_status()`, `get_detected_object()`, `get_detected_object_weight()`, `is_tray_emptied_offline()`.
  - `pico/main.py`: alustetaan `SmartTrayTracker` ja kutsutaan `update()`:a `scale_poll_once()`-silmukassa.
  - `pico/bluetooth_handler.py`: lisätty `tray_water_g`, `tray_pct`, `tray_status`, `detected_object` ja `object_weight_g` `scale_payload`-pakettiin.
  - `pico/commands.py`: lisätty käsittelijät `tray?`, `tray:*`, `obj?`, `obj:*`.
  - `pico/MANIFEST.json`: päivitetty kaikkien muutettujen ja lisättyjen tiedostojen koot ja sha256-tiivisteet.
  - `testit/smart_tray_smoke.py`: kattava yksikkötestaus kaikille vaatimuksille (RESULT: 0 failed, 12 testikohtaa).
  - Kaikki olemassa olevat smoke-testit hyväksytty (lampotilatilat, tray_guard, tray_total, vaaka_komennot, valmiustila, termostaatti, steam_paine, kuumavesi, turva_pika, turva_toimilaite: 0 failed).
  - Päivitetty `REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`. Asetettu seuraavaksi paketiksi `wmax-pysyvyys`.
  - todettu (ei rekisteriin): `testit/smart_tray_smoke.py`: 12/12 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/lampotilatilat_smoke.py`: 36/36 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_guard_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/tray_total_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/vaaka_komennot_smoke.py`: ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/valmiustila_smoke.py`: 32/32 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/termostaatti_smoke.py`: 29/29 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/steam_paine_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/kuumavesi_smoke.py`: 21/21 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_pika_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_toimilaite_smoke.py`: 43/43 ok, RESULT: 0 failed.

- 26.10.2026 — Toteutettu ja todennettu keittimen lämpötilatilat (EXPRESSO-LAMPOTILATILAT, KAYTTAJAN-TIEDOT.md §9 kohta 2): - `pico/classes.py`: lisätty `BrewData.is_idle()`, `BrewData.update_temperature_mode()`, `IDLE_MODES = ('IDLE', 'idle', 'warming up', 'stabilizing', 'cooling down')` ja kynnysarvot `TEMP_WARMUP_DEFICIT_C = 2.0`, `TEMP_COOLING_SURPLUS_C = 0.5`, `TEMP_SETTLE_BAND_C = 0.5`, `TEMP_SETTLE_TIME_MS = 10000`, `TEMP_SETTLE_MAX_SPEED = 0.5`. - Tilasiirtymät: - `warming up`: kattilan lämpötila > 2.0 °C alle tavoitteen. - `stabilizing`: lähestymis- tai heilahteluvaiheessa (alle 2.0 °C alituksesta +0.5 °C ylitykseen ennen kuin ehto IDLE täyttyy 10 s ajan tai kun lämpötilan muutosnopeus on liian suuri). - `IDLE`: lämpötila pysynyt tavoitteen kohdalla (±0.5 °C kaistalla) yhtäjaksoisesti vähintään 10 sekuntia ja muutosnopeus on vakaa (≤ 0.5 °C/10 s). Hystereesi (0.6 °C) estää tilojen värinän rajalla. - `cooling down`: lämpötila yli tavoitteen (> 0.5 °C tavoitteen yläpuolella, esim. höyrytyksen tai ylilyönnin jälkeen). - `BrewData.set_mode('IDLE')` ohjaa tilan suoraan `update_temperature_mode()`:n kautta. Aktiiviset käyttötilat (`BREW`, `STEAM`, `WATER`, `DEV_SAFE`, `BACKFLUSH_*`) eivät ylikirjoitu. - `Thermostat.run()` ottaa huomioon kaikki `IDLE_MODES`-tilat (lämmitys ja lepotilamittaukset toimivat saumattomasti). TILAUS-P lepotilamittaus pysyy puhtaana transienttien aikana. - `main.py`: päivitetty `scale_cal`-kutsu käyttämään `brew_data.is_idle()` ja lisätty lämpötilatilan päivitys pääsilmukkaan ennen termostaattia sekä höyrykytkimen vapautukseen. - `MANIFEST.json`: päivitetty vastaamaan koodimuutoksia. - Luotu kattavat testit `testit/lampotilatilat_smoke.py` (36/36 testiä ok, RESULT: 0 failed).
  - Päivitetty `Infra/iot/expresso/REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`. Siirretty lämpötilatilat-tehtävä tilaksi "toteutettu 26.10.2026; odottaa käyttäjää" ja asetettu uudeksi seuraavaksi paketiksi `EXPRESSO-ALYKAS-PAINO`. Commitoitu ja pushattu (`9021cbc`).
  - todettu (ei rekisteriin): `testit/lampotilatilat_smoke.py`: 36/36 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/termostaatti_smoke.py`: 29/29 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/valmiustila_smoke.py`: 32/32 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/steam_paine_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/kuumavesi_smoke.py`: 21/21 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_pika_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `testit/turva_toimilaite_smoke.py`: 43/43 ok, RESULT: 0 failed.
- 26.10.2026 — EXPRESSO-LAMPOTILATILAT: toteutettu keittimen lämpötilatilat (KAYTTAJAN-TIEDOT.md §9 kohta 2):
  - Keittimen tila IDLE kytkeytyy päälle vasta kun oikea lämpötila on asettunut kohdalleen: pysynyt tavoitteen ±0,5 °C ikkunassa yhtäjaksoisesti 10 s ajan ja muutosnopeus on vakaa (≤ 0,5 °C/10 s).
  - `warming up`: kattilan lämpötila reilusti alle tavoitteen (> 2,0 °C alle tavoitteen).
  - `stabilizing`: kattilan lämpötila heilahtelu-/lähestymisvaiheessa (alle 2,0 °C alle tavoitteen tai kun lämmitysnopeus on suuri ennen 10 s tasaantumista).
  - `cooling down`: kattilan lämpötila yli tavoitteen (> 0,5 °C yli tavoitteen, esim. höyrytyksen tai ylilyönnin jälkeen).
  - `pico/classes.py`: lisätty `IDLE_MODES`, `TEMP_WARMUP_DEFICIT_C`, `TEMP_COOLING_SURPLUS_C`, `TEMP_SETTLE_BAND_C`, `TEMP_SETTLE_TIME_MS`, `TEMP_SETTLE_MAX_SPEED`. Lisätty `BrewData.is_idle()`, `BrewData.update_temperature_mode()`, päivitetty `set_mode()`, `update_standby()`, `check_pressure_equalization()`, `get_target_temperature()` ja `Thermostat.run()`.
  - `pico/main.py`: päivitetty `scale_cal`-ehto ja lisätty `update_temperature_mode()` pääsilmukkaan ja höyrytyskytkimen vapautukseen.
  - `pico/MANIFEST.json`: päivitetty `classes.py` ja `main.py` koot ja tiivisteet.
  - `testit/lampotilatilat_smoke.py`: kattava yksikkötestaus kaikille tiloille ja siirtymille (36/36 ok). Kaikki aiemmat smoke-testit vihreinä (termostaatti, valmiustila, steam_paine, kuumavesi, turva_pika, turva_toimilaite: 0 failed).
  - Päivitetty `Infra/iot/expresso/REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`. Asetettu uudeksi seuraavaksi paketiksi `EXPRESSO-ALYKAS-PAINO`.
  - todettu (ei rekisteriin): `lampotilatilat_smoke.py`: 36/36 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `termostaatti_smoke.py`: 29/29 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `valmiustila_smoke.py`: 32/32 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `steam_paine_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `kuumavesi_smoke.py`: 21/21 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `turva_pika_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `turva_toimilaite_smoke.py`: 43/43 ok, RESULT: 0 failed.

- 26.10.2026 — Toteutettu ja todennettu äpin päänäkymän ja vaakatilan uudistukset (EXPRESSO-APPI-UI-UUDISTUKSET, Mac `silvia_pico_flutter_UI`): - Äpin yhteyden oletuskuvake: oletuksena harmaa Wi-Fi-ikoni yhteyttä etsittäessä, muuttuu punaiseksi 20 s kuluttua jos yhteyttä ei löydy; vihreä yhteyden muodostuessa (Wi-Fi tai BLE). Uudelleenetsintä ja napautus nollaavat ajastimen (`value_display.dart`). - Tare-nappi: sijoitettu suoraan painolukeman alapuolelle oikeaan reunaan (`value_display.dart`). - Vaakatilan elementtien karsinta: piilotettu T- ja P-lukuarvot (näkyvät graafissa) sekä lepotila- ja yhteysikonit (`landscape_layout.dart`). - Vaakatilan pyöreä freeze-nappi: pienempi pyöreä painike play/pause-symboleilla (`Icons.pause_rounded` piirron aikana, `Icons.play_arrow_rounded` pysäytettynä) (`landscape_layout.dart`). - Vaakatilan graafin tilankäyttö: optimoitu vaakasuuntainen ja pystysuuntainen tilankäyttö tiivistämällä reunoja ja akselien varauksia (`landscape_layout.dart` ja `graph_widget.dart`). - Flow-virtauksen piirto graafiin: lisätty Flow-lukemalle oma käyrä (`Colors.tealAccent`) reaaliaikaiseen graafiin (`graph_widget.dart`), malliin `flowData` (`machine_status.dart`) ja keruu `machine_data_notifier.dart`. - Luotu kattavat testit (`test/ui_uudistukset_test.dart`), kaikki 98 Flutter-testiä hyväksytty puhtaasti (`flutter test`). - Todennettu simulaattorissa (`iPhone 15 Pro expresso`, uutto käynnissä) ja tallennettu todistekuvakaappaukset (`portrait-live.png` ja `landscape-live.png` polkuun `~/expresso-ios-varmuus/20261026-ui-uudistukset/`). - Lähdekoodit varmuuskopioitu Macille `~/expresso-ios-varmuus/20261026-ui-uudistukset/uudet/`.
  - Päivitetty `Infra/iot/expresso/REKISTERI.md`, `HISTORIA.md` ja `ARKISTO.md`. Siirretty 6 UI-tehtävää tilaksi "toteutettu 26.10.2026; odottaa käyttäjää" ja asetettu uudeksi seuraavaksi paketiksi `EXPRESSO-LAMPOTILATILAT`. Commitoitu ja pushattu (`5f22f83`).
  - todettu (ei rekisteriin): Flutter-testit Macilla: 98/98 läpäisty hyväksytysti (`flutter test` exit 0).
  - todettu (ei rekisteriin): Simulaattorikäännös Macilla: `flutter build ios --simulator --debug --dart-define=EXPRESSO_DEMO=true` exit 0.
  - todettu (ei rekisteriin): Ohjain UI-testi ajo simulaattorissa exit 0: kuvakaappaukset tallennettu `~/expresso-ios-varmuus/20261026-ui-uudistukset/`.
  - todettu (ei rekisteriin): Git Infra/iot/expresso: commit `5f22f83` pushattu onnistuneesti `origin/main`iin.
- 26.10.2026 — EXPRESSO-APPI-UI-UUDISTUKSET toteutettu ja todennettu Macilla (`silvia_pico_flutter_UI`):
  - silvia_pico_flutter_UI: toteutettu ConnectionIcon (lib/features/ui/widgets/value_display.dart), joka näyttää oletuksena harmaan Wi-Fi-ikonin yhteyttä haettaessa, muuttuu punaiseksi 20 s timeoutin jälkeen jos yhteyttä ei löydy, ja kääntyy vihreäksi yhteyden muodostuessa (Wi-Fi- tai Bluetooth-ikoni aktiivisen linkin mukaan). Napautus käynnistää uuden haun ja nollaa aikalaskurin takaisin harmaaseen.
  - silvia_pico_flutter_UI: ValueDisplayn Tare-nappi sijoitettu suoraan painolukeman alapuolelle oikeaan reunaan (Column crossAxisAlignment: end).
  - silvia_pico_flutter_UI: LandscapeLayoutista karsittu T- ja P-lukuarvot (näkyvät graafissa) sekä yhteyden ja lepotilan symbolit. Tilalla näkyvät tiiviisti Flow, Weight, Pump ratio ja Brew Timer (ml. first drop -ilmaisin uutossa).
  - silvia_pico_flutter_UI: LandscapeLayoutin freeze-nappi muutettu pienemmäksi pyöreäksi painikkeeksi (landscape_freeze_button), jossa tekstin sijaan play/pause-symbolit (Icons.pause_rounded piirron aikana, Icons.play_arrow_rounded pysäytettynä).
  - silvia_pico_flutter_UI: GraphWidgetin tilankäyttö optimoitu vaakasuunnassa (reunavaraukset 44 -> 36 px) ja pystysuunnassa (alaotsikkovaraus 36 -> 28 px, padding 10 -> 4 px). LandscapeLayoutin ulkopadding tiivistetty 24 -> 16/10 px ja välys 16 -> 8 px, jotta graafi ottaa tilan paremmin haltuun.
  - silvia_pico_flutter_UI: MachineStatukseen lisätty flowData-sarja, machine_data_notifier tallentaa reaaliaikaiset Flow-näytteet (flow_g_s), ja GraphWidget piirtää virtaukselle oman käyrän (Colors.tealAccent).
  - Testit: luotu kattavat widget- ja yksikkötestit (test/ui_uudistukset_test.dart) yhteyden tilasymbolille 20 s timeoutilla, Tare-napin sijoitukselle, vaakatilan karsinnoille ja freeze-napille sekä flow-datan tallennukselle ja piirrolle. Kaikki 98 testiä hyväksytty puhtaasti (flutter test).
  - Todennettu simulaattorissa (iPhone 15 Pro expresso, demo uutto käynnissä) ja tallennettu todistekuvakaappaukset (portrait-live.png ja landscape-live.png).
  - todettu (ei rekisteriin): Flutter test: 98/98 läpäisty.
  - todettu (ei rekisteriin): Ohjain UI-testi ajo exit 0: kuvakaappaukset tallennettu ~/expresso-ios-varmuus/20261026-ui-uudistukset/.
- 26.10.2026 — EXPRESSO-VAPAA-VIRTAUS laitetodennus: luettiin ja analysoitiin Pico 2 W:n sarja- ja diagnet-lokit (`~/.local/state/expresso-diag/` ja `2026-10-21.log`, `2026-10-22.log`).
  - Todettiin b672e71 (flashattu 21.10. 12.35, boot 3c09b1e0) arm 2 -tasaantumisen toimivuus fyysisellä laitteella: - 21.10.2026 klo 12.41 3,4 s huuhtelu kahva irti tasaantuneesta 98,4 °C:sta (`shot-20261021-124141-3c09b1e0.log`), 146 iskua, `BH_END sum_ms=8399 arm=2 fill=146`. - Settle-vaiheen jälkeen saavutettiin `BH_SETTLED T=98.08 err=-0.08 why=target (no learning)` 12.43.20 (99 s huuhtelusta). - PI-luovutuksen jälkeinen suurin alitus oli vain −0,280 °C (12.44.50 d10_min −0,280, d10_max +0,134), mikä toteuttaa vaatimuksen alitus ≤ −0,3 °C (ennen korjausta oli −0,86 °C). - Toistui 22.10. 09.23–09.33 (`shot-20261022-092347-3c09b1e0.log`): `BH_SETTLED T=98.49`, alitus vain −0,104 °C.
  - Tallennettiin todistetiedosto `Infra/iot/expresso/testit/vapaa-20261021-c-diag.log`.
  - Ajettiin testit: `termostaatti_smoke.py` (kaikki H1–H10 ml. H9 kuollut aika 25 s ja H10 hidas kattila) 0 failed, `valmiustila_smoke.py` 0 failed, `steam_paine_smoke.py` 0 failed, `turva_pika_smoke.py` 0 failed, `pcal_test.py` 0 failed, `ctrl_real_test.py` 0 failed.
  - Äpin valmiustila-asetukset siirretty säätönäkymän Sleep-osioon Macilla (`silvia_pico_flutter_UI`): - `settings_view.dart`: poistettu 3 valmiustila-asetusta ja standby-providerit. - `controls_widget.dart`: lisätty 3 valmiustila-asetusta Sleep-osion (`section_sleep`) sisään. - Varmuuskopiot tallennettu Macille `~/expresso-ios-varmuus/20261026-sleep/`. - Ajettu Macilla `flutter analyze` (0 varoitusta) ja `flutter test` (92/92 testiä läpi).
  - Kirjattu käyttäjän 8 uutta jatkotehtävää sanasta sanaan pysyvään muistiin `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md` (§9) ja `Infra/iot/expresso/REKISTERI.md` (Päätökset & Avoimet asiat); commitoitu ja pushattu repon `origin/main`iin (`9559563`).
  - ratkennut (Avoimet asiat): Uuton jälkeinen tasaantuminen myös ilman oppia (arm 2) — Todettiin b672e71 arm 2 -tasaantumisen toimivuus fyysisellä laitteella 21.10.2026 (BH_SETTLED saavutettiin 99 s huuhtelusta).
  - todettu (ei rekisteriin): `shot-20261021-124141-3c09b1e0.log` ja `2026-10-21.log` (12.41–12.49): `BH_END sum_ms=8399 arm=2 fill=146`, `BH_SETTLED T=98.08 err=-0.08`, luovutuksen alitus −0,280 °C ≤ −0,3 °C.
  - todettu (ei rekisteriin): `shot-20261022-092347-3c09b1e0.log` ja `2026-10-22.log` (09.23–09.42): `BH_END sum_ms=7450 arm=2 fill=0`, `BH_SETTLED T=98.49 err=-0.49`, luovutuksen alitus −0,104 °C.
  - todettu (ei rekisteriin): `termostaatti_smoke.py`: 29/29 testiä ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `valmiustila_smoke.py`: 32/32 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `steam_paine_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): `turva_pika_smoke.py`: 26/26 ok, RESULT: 0 failed.
  - todettu (ei rekisteriin): Flutter UI Macilla: `flutter analyze` 0 issues, `flutter test` 92/92 passed.
  - todettu (ei rekisteriin): `expresso-asennus.sh --check`: preflight xcode=on flutter=on lahde=on agentti=on laite=unavailable.
- 26.10.2026 — purettu ja raportoitu käyttäjälle infra expresso -tilanne (purkuraportti, käyttäjä valitsi "Vain tilanne, ei töitä nyt — raportti riitti").
  - silvia_pico_flutter_UI: jaettu iOS-äpin säädöt viiteen (5) avattavaan ExpansionTile-osioon controls_widget.dartissa (Fast heatup, Preinfusion, Brew, Steam, Sleep). Kaikki osiot ovat oletuksena supistettuna (initiallyExpanded: false) ja avautuvat napauttamalla.
  - silvia_pico_flutter_UI: luotu SafeBouncingScrollPhysics ja SafeBouncingScrollSimulation (lib/core/safe_bouncing_scroll_physics.dart) korjaamaan päänäkymän nopean vierityksen joustokimpoamisvika. Fysiikka säilyttää iOS-ylivedon joustotuntuman, mutta nollaa palautusvaiheen ylimääräisen kineettisen energian ja telakoituu täsmällisesti päätyyn (min/maxScrollExtent) ilman takaisinkelausta sisällön sisään. Otettu käyttöön PortraitLayoutissa ja MaterialAppin scrollBehaviorissa.
  - silvia_pico_flutter_UI: toteutettu äpin käyttö ja asetusten säätö ilman keittimen herättämistä lepotilasta: - standby_overlay.dart: lisätty oikeaan yläkulmaan pyöreä X-suljinpainike. - home_view.dart: äpin avautuessa tai palatessa taustalta (resumed) lepotilanäkymä on esillä, jos keitin on lepotilassa. X-napista lepotilanäkymän saa suljettua pois, jolloin päänäkymä ja säätimet ovat suoraan käytettävissä ilman keittimen heräämistä. - controls_widget.dart: päänäkymässä asetusryhmien yläpuolelle toteutettu suora "Herätä lepotilasta" -painike (wake_from_standby_controls_button), joka näkyy vain keittimen ollessa lepotilassa ja lähettää stby:wake. - landscape_layout.dart: vaakatilan lepotilapainike vaihtuu herätysikoniksi (Icons.wb_sunny_rounded) keittimen ollessa lepotilassa. - controls_widget.dart: Sleep-osion "Siirry lepotilaan" -painike disabloitu lepotilassa.
  - Käännetty release-buildit ja asennettu kahdesti iPhoneen (expresso-asennus.sh, exit 0, molemmat asennukset onnistuneet laitteelle).
  - Testit: laajennettu yksikkö- ja widget-testit (safe_bouncing_scroll_physics_test.dart, machine_status_test.dart, standby_timeout_test.dart). Kaikki 92 testiä hyväksytty puhtaasti (flutter test).
  - todettu (ei rekisteriin): Flutterin oletus-BouncingScrollSimulation antaa palautuvan jousen viedä näkymän päädyn yli takaisin sisällön sisään suurella kineettisellä energialla; SafeBouncingScrollSimulation nollaa vastasuuntaisen nopeuden reunalla ja telakoituu päätyyn ilman värähtelyä.
  - todettu (ei rekisteriin): Supistettuna päänäkymän sisältö mahtuu iPhone 15 Pron näytölle (leadingExtent == trailingExtent == 0.0), jolloin oletusfysiikka kimposi heilurimaisesti yli nollan; SafeBouncingScrollPhysics pysähtyy välittömästi.
  - todettu (ei rekisteriin): Testitulokset: Kaikki 92 yksikkö- ja widget-testiä läpäisty (flutter test).
- 25.10.2026 — Tutkittu käyttäjän uuton 10 (13:54:06) juurisyyt: 1) esiuuton ennenaikainen laukeaminen 2,4 s kohdalla johtui vaa'an kohinaa kerryttävästä CUSUM-algoritmista, 2) uuton katkeaminen (EU_STARVE) 24,5 s kohdalla johtui samalla kierroksella suoritetusta GC:stä (39 ms) ja clock.iq_close():sta (12 ms), mikä ylitti 25 ms nälkärajan, 3) automaattinen uudelleenkäynnistyminen johtui fyysisen uuttokytkimen jäämisestä ON-asentoon run_shot() -funktion palattua.
  - scale.py: poistettu kohinaa keräävä CUSUM-akkumulaattori FirstDropDetectorista, korvattu suodatetulla kynnystunnistuksella kahdella vahvistetulla näytteellä.
  - functions.py: nostettu EU_C1X_GC_LEAD_US 35 ms -> 42 ms, estetty clock.iq_close() gc.collect():n aikana ja asetettu drop_allowed vähintään 3,0 s / hold_t.
  - classes.py: nostettu CX_STARVE_US 25 ms -> 35 ms. Lisätty set_idle_pressure_equalize_mode ja get_idle_pressure_equalize_mode.
  - main.py: lisätty uuton jälkeinen tarkistus silmukassa while SWITCH_BREW.value(): await asyncio.sleep_ms(50), mikä estää automaattisen uudelleenkäynnistyksen kytkimen ollessa päällä.
  - commands.py: peq:on/off kutsuu set_idle_pressure_equalize_mode() ja asettaa updated = True, jolloin asetus tallentuu automaattisesti settings.txt:hen.
  - wifilink.py: lisätty peq: ALLOWED_PREFIX -listaan ja peq? ALLOWED_EXACT -listaan Wi-Fi-tukea varten.
  - functions.py: save_settings ja load_settings tallentavat ja lataavat idle_pressure_equalize_mode -asetuksen.
  - bluetooth_handler.py: poistettu duplicate brew_temperature paketista 2 ja lisätty peq_mode (paketti 2 pysyy reilusti alle 240 B MTU-rajan).
  - Pico 2 W flashattu kahdesti Zerolla (FLASH_OK, VERIFIED 24/24) ja todennettu live-laitteella: CMD peq:on tasasi paineen 9,5 barista 0,8 bariin ja tallensi asetuksen.
  - silvia_pico_flutter_UI: lisätty pressureEqualizationOn MachineStatus-malliin, machine_data_notifier.dartiin ja controls_widget.dartiin vihreä SwitchListTile.
  - silvia_pico_flutter_UI: lisätty enterStandby() MachineDataNotifieriin ja tyylikäs violetti painike "Siirry lepotilaan" (Icons.bedtime_rounded) controls_widget.dartiin, value_display.dartiin ja landscape_layout.dartiin.
  - Testit: preinfusion_trigger_smoke.py (28/28 ok), Flutter-yksikkö- ja widget-testit (23/23 ok), koko Flutter-testisarja (84/84 ok).
  - Käännetty ja asennettu kahdesti iPhoneen (expresso-asennus.sh, exit 0).
  - todettu (ei rekisteriin): Uuton 10 painehallinta ei ollut häiriintynyt: 8,0 barin pito pysyi erittäin vakaana (hold_mean = 7.993 bar, hold_sd = 0.175 bar).
  - todettu (ei rekisteriin): GC kesti 39,1 ms Pico 2 W:llä (512 kt heap) ja clock.iq_close() 11,6 ms aiheuttaen 52,3 ms ytimen 0 pysähdyksen. Korjattu etumatka 42 ms ja starve-raja 35 ms estävät nälkäkatkaisun.
  - todettu (ei rekisteriin): FirstDropDetectorin suodatettu kynnys vaatii 2 peräkkäistä vahvistettua näytettä, ei laukea kohinasta.
  - todettu (ei rekisteriin): BLE MTU -rajat: asetuspaketti 1 227 B, paketti 2 213 B (raja 240 B).
  - todettu (ei rekisteriin): Laitetodennus Zerolla: CMD peq? -> PEQ enabled=0 p=9.5; CMD peq:on -> PEQ enabled, save_settings; CMD peq? -> PEQ enabled=1 p=0.8.
  - todettu (ei rekisteriin): Flutter-testit: 84/84 testiä läpäisty.
  - todettu (ei rekisteriin): iPhone-asennukset: molemmat onnistuneet (build ok 37 s ja 36 s, asennus valmis).
- 25.10.2026 — Lepotila-painike (Siirry lepotilaan) äppiin:
  - Käyttäjän pyyntö: "tee äppiin nappi mistä saa keittimen lepotilaan."
  - Flutter iOS -sovellus (silvia_pico_flutter_UI):
    - `MachineDataNotifier` (`machine_data_notifier.dart`): lisätty `enterStandby()` -metodi, joka lähettää komennon `stby:on` ja asettaa tilan `standby: true`.
    - `ControlsWidget` (`controls_widget.dart`): lisätty tyylikäs violetti painike "Siirry lepotilaan" (`Icons.bedtime_rounded`) suoraan paineentasauskytkimen alapuolelle.
    - `ValueDisplay` (`value_display.dart`): lisätty yläpalkkiin vasemmalle lepotilakuvake (`Icons.bedtime_rounded`, tooltip 'Siirry lepotilaan'), jolloin keittimen saa lepotilaan heti ilman skrollausta.
    - `LandscapeLayout` (`landscape_layout.dart`): lisätty yläpalkkiin lepotilakuvake (`Icons.bedtime_rounded`).
    - Kun keitin siirtyy lepotilaan, ruudulle nousee tuttu `StandbyOverlay`, josta keitin voidaan herättää takaisin ("Herätä lepotilasta", `stby:wake`).
    - Testit: `standby_timeout_test.dart` ja `machine_status_test.dart` (23/23 ok).
    - Käännetty ja asennettu iPhoneen onnistuneesti (`expresso-asennus.sh`, exit 0, build 36 s).

- 25.10.2026 — Paineen tasaus -kytkin (Pressure equalization) äppiin ja Pico-laiteohjelmistoon:
  - Käyttäjän pyyntö: "tee paineen tasaus ominaisuudelle toggle switch äppiin".
  - Flutter iOS -sovellus (silvia_pico_flutter_UI):
    - Lisätty `pressureEqualizationOn` (oletus `false`) malliin `MachineStatus` (`machine_status.dart`, `machine_status.freezed.dart`, `machine_status.g.dart`).
    - `MachineStatus.fromJson`: normalisoi `peq_mode`, `idle_pressure_equalize_mode` ja `peq` kenttään `pressureEqualizationOn`.
    - `MachineDataNotifier` (`machine_data_notifier.dart`): tunnistaa asetuspaketit, joissa on `peq_mode`, päivittää tilan ja tarjoaa metodin `setPressureEqualizationOnLocal(bool enabled)`.
    - `ControlsWidget` (`controls_widget.dart`): lisätty vihreä `SwitchListTile` otsikolla "Pressure equalization" suoraan "Fast heatup" -kytkimen alle. Kytkimen vaihto kutsuu `setPressureEqualizationOnLocal` ja lähettää komennon `peq:on` / `peq:off` (toimii sekä BLE:n että Wi-Fi:n yli).
    - Unit- ja widget-testit lisätty (`machine_status_test.dart`): 15/15 testiä läpi; koko Flutter-testisarja (84/84) läpi.
    - Käännetty ja asennettu iPhoneen onnistuneesti (`expresso-asennus.sh`, exit 0, build 37 s).
  - Pico 2 W -laiteohjelmisto:
    - `classes.py`: lisätty `set_idle_pressure_equalize_mode(enabled)` (asettaa `self.setting_changed = True`) ja `get_idle_pressure_equalize_mode()`.
    - `commands.py`: `peq:`-komennon käsittelijä kutsuu metodia `brew_data.set_idle_pressure_equalize_mode(...)` ja asettaa `updated = True`, jolloin asetus tallentuu automaattisesti `settings.txt`:hen.
    - `wifilink.py`: lisätty `'peq:'` `ALLOWED_PREFIX`-listaan ja `'peq?'` `ALLOWED_EXACT`-listaan, jotta komento toimii myös Wi-Fi-linkin yli.
    - `functions.py`: `save_settings` tallentaa avaimen `idle_pressure_equalize_mode` ja `load_settings` lataa sen käynnistyksessä.
    - `bluetooth_handler.py`: `settings_payloads`-metodissa poistettu päällekkäinen `brew_temperature` paketista 2 ja lisätty `'peq_mode'`, jolloin paketti 2 mahtuu reilusti BLE MTU -rajaan (< 240 B).
    - Smoke-testit: `testit/preinfusion_trigger_smoke.py` (28/28 ok).
    - Pico 2 W flashattu ja todennettu Zerolla: `FLASH_OK`, `VERIFIED 24/24`. Laitetodennus ajettu reaaliaikaisesti Picolle: `CMD peq?` -> `PEQ enabled=0 p=9.5`, `CMD peq:on` -> `PEQ enabled`, `save_settings`, ja `CMD peq?` -> `PEQ enabled=1 p=0.8` (paine tasattiin heti 9.5 -> 0.8 bar).
  - todettu (ei rekisteriin): Pico 2 W flashattu onnistuneesti 25.10.2026: FLASH_OK, VERIFIED 24/24. Laitteella peq:on aktivoi paineentasauksen heti ja tallentaa asetuksen settings.txt:hen.

- 25.10.2026 — Esiuuttolaukaisin (Preinfusion trigger) ja uuttovirheen (EU_STARVE) korjaus:
  - Käyttäjä teki uuton (id=10), jossa esiuutto laukesi ennenaikaisesti 2,4 s kohdalla ja uutto katkesi 24,5 s kohdalla virheeseen käynnistyen heti uudestaan (id=11).
  - Juurisyyanalyysi diagnostiikkalokista (`shot-20261025-135406-3271f5fe.log`):
    1. Esiuuton ennenaikainen laukeaminen: `FirstDropDetector` käytti CUSUM-kertymää `dev = rise - k; s = max(0, s + dev)`, jossa `k = 0.04` g. Koska vaa'an kohina on $\sigma \approx 0.25$ g, positiivinen kohina kerrytti `s`:ää jatkuvasti ja laukaisi tunnistimen ilman todellista nestemäärää jo 2,4 s kohdalla.
    2. Uuton katkeaminen: 8 barin pidossa kohdassa t=24,4s roskienkeruu (`EU_GC`) kesti 39,1 ms (RP2350:n 512 kt keolla). Samalla kierroksella suoritettiin `clock.iq_close()` (11,6 ms), jolloin ytimen 0 pysähdys oli 52,3 ms. Ytimen 1 jonossa oli vain 40 ms etumatkaa ja `CX_STARVE_US` oli 25 ms, joten ydin 1 koki tapahtumanälän (`EU_STARVE t_ms=24456 starve=1 lag_us=37992`) ja keskeytti uuton (`EB_END reason=starve`).
    3. Painehallinta: Uuton painehallinta ei ollut häiriintynyt millään tavalla. Uutto eteni tasaisesti 8,0 baariin ja pysyi siinä erinomaisen vakaasti (`hold_mean = 7.993 bar`, `hold_sd = 0.175 bar`) koko 20 sekunnin ajan.
    4. Uuton uudelleenkäynnistyminen: Kun `run_shot()` palasi ennenaikaisesti virheen jälkeen, fyysinen uuttokytkin oli edelleen ON-asennossa, jolloin `main.py` käynnisti heti uuden uuton (id=11).
  - Korjaukset:
    - `scale.py`: Poistettu kohinaa keräävä CUSUM-akkumulaattori. Tunnistus perustuu nyt suodatettuun painon nousuun yli asetetun kynnyksen (`rise >= threshold`), joka vaatii 2 (tai 3 jos kynnys < 0.15g) peräkkäistä vahvistettua näytettä.
    - `functions.py`: `EU_C1X_GC_LEAD_US` nostettu 35 ms -> 42 ms. Lisätty esto: `clock.iq_close()` ei saa koskaan suorittua samalla kierroksella kuin `gc.collect()` (`c1 == 0`), ja c1x:llä vaaditaan vähintään 25 ms etumatka jonossa. `drop_allowed` asetettu vähintään 3,0 s / `hold_t`.
    - `classes.py`: `CX_STARVE_US` nostettu 25 ms -> 35 ms (turvallinen ja antaa pelivaraa GC-kierroksille).
    - `main.py`: Lisätty silmukka `while SWITCH_BREW.value(): await asyncio.sleep_ms(50)` uuton päätyttyä, jotta keskeytynyt uutto ei koskaan käynnisty itsestään uudestaan, ennen kuin kytkin käytetään OFF-asennossa.
  - Testit ja laitetodennus: `testit/preinfusion_trigger_smoke.py` (25/25 ok), `testit/valmiustila_smoke.py` (32/32 ok), `testit/turva_pika_smoke.py` (27/27 ok), `testit/esiuutto_smoke.py` (ok), `testit/uuttoloki_smoke.py` (ok). Pico 2 W flashattu onnistuneesti (`VERIFIED 24/24`, `FLASH_OK`).
  - todettu (ei rekisteriin): Pico 2 W flashattu onnistuneesti 25.10.2026: FLASH_OK, VERIFIED 24/24. Boot id vaihtui `3271f5fe` -> `36d751ff`.

- 24.10.2026 — Erilliset lepotila-ajastimet (käynnistys vs. uutto/höyrytys) ja lepotilan herätysnäkymä:
  - Käynnistämisen jälkeinen lepotila: erillinen säätö äpissä 1h - 4h (oletus 120 min, `stby:start:<min>`). Veden laskeminen / huuhtelu (`peak_pressure < 2.5 bar` tai kesto < 5 s) ei laukaise uuton jälkeistä tilaa, vaan kone pysyy käynnistysaikakatkaisun piirissä.
  - Uuton / höyrytyksen jälkeinen lepotila: 15 min - 2 h (oletus 30 min, `stby:brew:<min>`). Vaatii oikean uuton (`peak_pressure >= 2.5 bar` ja kesto >= 5000 ms) tai höyrytystilan käytön (`SWITCH_STEAM`).
  - Äpin käynnistys ei herätä keitintä: `stby:start:`, `stby:brew:` ja `stbt:` asetettu `wake = False` komentokäsittelijässä (`commands.py`), joten synkronointi yhteyden alussa ei herätä konetta lepotilasta.
  - Lepotilan herätysnäkymä äpissä: kun keitin on lepotilassa (`standby: true`), äpissä aukeaa päälle `StandbyOverlay`-näkymä, jossa on selkeä kattilan tilatieto ja "Herätä lepotilasta" -painike. Painike lähettää `stby:wake`-komennon ja herättää keittimen normaalilämpöön.
  - Testit ja laitetodennus: `testit/valmiustila_smoke.py` (32/32 ok), Flutter-testit (78/78 ok). Pico 2 W flashattu kahdesti käyttäjän luvalla (VERIFIED 24/24, FLASH_OK). Laitetodennus ajettu reaaliaikaisesti Picolle: `stby:on`, `stby:start:180` (ei herättänyt, pysyi standby=1), `stby:wake` (herätti, STBY_OFF reason=app, standby=0). Flutter-äppi käännetty ja asennettu iPhoneen onnistuneesti (`expresso-asennus.sh` exit 0).
  - todettu (ei rekisteriin): Pico 2 W flashattu onnistuneesti 24.10.2026: FLASH_OK, VERIFIED 24/24. Laitetesteissä stby:start ei herätä lepotilasta, stby:wake herättää heti.

- 24.10.2026 — Höyrytystilan (STEAM) paine- ja lämpötilaohjaus: - Nimettiin ja laajennettiin höyryohjaus: `steam_valve_trigger` (svt:, 0.5–3.0 bar, oletus 1.8 bar), `steam_valve_release` (svr:, 0.6–3.2 bar, oletus 2.1 bar), `steam_temperature_max` (stmax:, 120–145 °C, oletus 140 °C) ja `steam_pressure_high` (sph:, 1.0–3.5 bar, oletus 2.5 bar). - Toteutettiin priorisointi Thermostat._steam_heat -metodiin: 1. Turvarajat (maksimilämpötila/paine kytkee lämmittimen pois), 2. Paineohjattu teholämmitys (paine <= trigger kytkee 100 % tehon, pysyy kunnes release saavutetaan), 3. Termostaattiohjaus steam_temperature-arvoon. - Tasapainotettiin BLE-asetuspaketit (bluetooth_handler.py): Paketti A 233 B, Paketti B 195 B (raja 240 B).
  - Flutter iOS -sovellus (silvia_pico_flutter_UI): - Päivitettiin MachineStatus-malli, notifioija ja säädinnäkymä (controls_widget.dart): liukusäätimet Steam valve trigger ja Steam valve release. - Testit (71/71 ok), käännetty ja asennettu iPhoneen (expresso-asennus.sh).
  - Paineen tasaus IDLE- ja alkulämmitystilassa (PEQ): - Toteutettiin paineentasaus: IDLE-tilassa tai fast_heatup-ohjelmassa, jos paine poikkeaa nollasta >= +-0.5 bar, solenoidia avataan 100 ms ajaksi 30 s välein. - Lisättiin käyttäjän ehto: painetta ei tasata, jos lämpötila on >= 0.1 °C yli tavoitelämpötilan. - Toteutettu asynkroninen tehtävä pressure_equalizer (main.py), logiikka classes.py:ssä, asetukset preset.py:ssä ja kyselykomento peq?.
  - Flashaus ja laitetodennus: - Flashattu kaksi kertaa Pico 2 W:lle käyttäjän luvalla (VERIFIED 24/24, FLASH_OK). - Laitetodennus: CMD svt:1.8, svr:2.1, sph:2.5, stmax:140, heat?, peq? vastasivat CMD_OK ja oikeat arvot. - Testit: steam_paine_smoke.py (26/26 ok), paine_tasaus_smoke.py (24/24 ok), kaikki smoke-testit 0 virhettä.
  - todettu (ei rekisteriin): Pico 2 W flashattu onnistuneesti 24.10.2026: FLASH_OK, VERIFIED 24/24.
  - todettu (ei rekisteriin): Laitteen vasteet: peq? -> PEQ enabled=1 p=0.0 th=0.5 int_s=30 last_s=never; heat? -> HEAT temp=97.28 age_ms=245 target=98.0 heater=0 guard=ok.
  - todettu (ei rekisteriin): BLE-paketointi: setA 233 B, setB 195 B (raja 240 B).
- 22.10.2026 — , sessio 96c12e06: käyttäjä ilmoitti painesensorin kalibroinnin pielessä: oikea 0 bar → näyttö −1,4 bar, oikea 8 bar → näyttö 8,0 bar (käyttäjän mittarilukemat).
  - Luettu laitteelta `pico_dev.py cmd pcal:st 3` → `PCAL_ST state=idle gain=1.0000 offset=-0.990`.
  - Laskettu kaksipistekorjaus (raaka r = näyttö + 0,99: r(0 bar) = −0,41, r(8 bar) = 8,99): gain = 8/9,40 = 0,8511, offset = 0,8511·0,41 = +0,349.
  - Kirjoitettu käyttäjän luvalla `pico_dev.py cmd pcalset:0.8511:0.349 3` → `PCALSET_OK gain=0.8511 offset=0.349` (tallentaa `pressure_cal.json`); takaisinluku `pcal:st` → gain=0.8511 offset=0.349. Ei koodimuutosta, ei flashia.
  - todettu (ei rekisteriin): Painekalibrointi laitteella 22.10.2026: gain 0,8511, offset +0,349 bar (ennen 1,000 / −0,990). Lähde `pcal:st`-takaisinluku.
- 21.10.2026 — 12.20–12.40, sessio 1126c688 (`/pura infra expresso`, KESKEN exit 5 → jatkettiin keskeneräistä).
  - Edellinen sessio 31d04800 jatkoi pakkauksen 690fe6e jälkeen pakkaamatta (10.33–11.14): 30b7e38 arm 2 settle-vaihe aina; 726b8d6 vapaa virtaus (BH_FREE: kaukalon nousu BH_FREE_G 10 g ohittaa täytön katon, oppi pois; testit H7–H8); ee2fa22 flash 10.49 VERIFIED 24/24 + 3 s huuhtelu; a2e22f1 toinen huuhtelu; a38ded2 marginaalikokeilu mallissa (`testit/bh-lead-sweep-20261021.log`). Rivit ovat jo REKISTERI.md:n arm 2 -rivillä; kirjaa HISTORIAan.
  - Tämä sessio: mallilaitos sovitettu laitteeseen (kuollut aika), korjaus b672e71 `pico/classes.py` `_post_brew` arm 2: `BH_HOLD_LEAD_S` 50 (pito pi_i:llä jo tavoitteen yllä, kun lasku saavuttaa tavoitteen 50 s:ssa, `bh_hold`) ja luovutus PI:lle vasta nähdyn nousun jälkeen (`bh_rise`) tai pidon pysäyttämässä tasanteessa; `testit/termostaatti_smoke.py` shots(dead_s=…), testit H9 (huuhtelu, kuollut aika 25 s) ja H10 (ei luovutusta kuopassa); MANIFEST päivitetty (`pico_dev.py manifest` tuotti saman). Sovitusloki `testit/bh-kuollut-aika-20261021.log`.
  - Flash 21.10.2026 12.35 (23f7971): FLASH_PLAN 1/24 (/classes.py), VERIFIED 24/24, FLASH_OK, DIAG_BOOT 3c09b1e0 12.35.52, DIAG_MIN 12.36.50 ok (`testit/flash-20261021-bh5.log`).
  - REKISTERI.md arm 2 -rivi päivitetty (b672e71, 23f7971).
  - todettu (ei rekisteriin): Sovitus: kuollut aika 25 s + viive 10 s + tarve 8 s: kuoppa −4,70 (laite −5,31), luovutus 137 s (138), alitus −0,85 (−0,86), IDLE-PI vakaa. Viive 20 s → IDLE-PI heiluu ±0,4–0,6 (ei laite).
  - todettu (ei rekisteriin): HEAD-koodilla hidas kattila (dead 25 lag 40 / dead 35 lag 20) luovuttaa kuopassa 27 s:ssa → ylitys +5…+7 °C.
  - todettu (ei rekisteriin): Uusi koodi mallissa (lead 50): alitus −0,85 → −0,01, 6–8 min ±0,11 → ±0,03; hidas kattila max +0,7. Lead 40 −0,25, 60 sama kuin 50, 75 heikompi (−0,24 tarpeella 7).
  - todettu (ei rekisteriin): H9 HEADilla FAIL (min 97,19–97,26), H10 HEADilla FAIL (max 104,88); uudella vihreät; smoket 29/29 rc=0.
  - todettu (ei rekisteriin): Flashin jälkeinen käynnistys 90 → 98: T 100,64 ensimmäisellä minuutilla (sama 10.51: 100,38) — olemassa oleva käynnistyksen ylitys, ei tämän muutoksen.
- 21.10.2026 — 06.20–10.10, sessio 31d04800 (`/pura infra expresso`, automaattivalinta EXPRESSO-RELEET-BOOT keskeytettiin käyttäjän pyynnöstä heti alussa; boot.py koskematon).
  - Yön kaatuminen selvitetty DIAGNETista: `PressureSensor.get_pressure()` ZeroDivisionError (classes.py:1313) 20.10. 17.42 ja 21.10. 01.57; korjaus 35bcace (vähintään yksi näyte, myös pitkäversio), flash 06.31.
  - Lepolämmityksen naksuminen (4b0a529 lyhensi kierroksen ~5 ms → heat_cycler-jakso 50–300 ms): af9cdcc aikaan sidottu jakso (IDLE 5 s käyttäjän pyynnöstä, muut 2 s), lämmitysnopeus 2 s ikkunasta; flash 07.33.
  - TILAUS-P (IDLE ±0,05 °C 10 s keskiarvoista): 53e16a0 IDLE-PI ±2 °C kaistalla (Kp 0,04, Ti 160 s, 50 ms resoluutio) + DIAG_MIN `n10 d10_min d10_max pi_i`; flash 07.51.
  - TILAUS-R/N uuton lämmitys: 2754d74 kertymä pumpun iskuista (brew_heat_k ms/isku, paineella painotettu, BH_PMAX 15), jäännöksen maksu uuton jälkeen, tasaantuminen pi_i-teholla, BH_LEARN-oppi, brew_heat.json (tmp+rename); flash 08.43. 750a2ae epäsymmetrinen oppi (tavoite −0,2, ylitys g 0,8, vaje 0,4, maksu loppuu +0,2). faedc8f peräkkäiset ajot summautuvat opin loppuun. 76c594e täytön katto (BH_FILL_MAX 120 iskua < 1,0 bar) ja ei oppia höyrystä < 20 min tai katon ylittyessä (BH_END fill=). Flashit 09.26 ja 09.47 väliaikaisella setillä, jossa brew_heat.json {"k": 67.5}.
  - Kirjattu KAYTTAJAN-TIEDOT.md: TILAUS-P, TILAUS-Q (thermal stability −10…+10), TILAUS-R (+ ylitys hidas korjata, höyry poistaa vettä), säiliö = keittimen oma säiliö. Testi `testit/termostaatti_smoke.py` (A–H), smoket 29/29 joka commitissa.
  - todettu (ei rekisteriin): TILAUS-P täyttyy laitteella: 53e16a0 07.59–08.04 kaikki 10 s keskiarvot ±0,05 (max |d| 0,038), pi_i 0,045; tasaantuminen flashista ~7 min.
  - todettu (ei rekisteriin): DIAG_MIN `T=` on minuutin hetkellinen lukema (diagnet.minute lukee bd.boiler_temperature), ei keskiarvo.
  - todettu (ei rekisteriin): Uuton lämmitys laitteella: ennen (20.10. 22.56) kuoppa 98,4→85,4, ylitys +6 °C, tasaantuminen 5–6 min; käyttäjän uutto 08.49 kuoppa 98,1→87,5, ylitys +0,7, k 70→68; s1 98,28 (k 66,9), s2 97,92 (k 67,2); kahvi 09.11 98,0→85,2, tasaantui 97,87; lokit `testit/bh-20261021-*.log`, DIAGNET `~/.local/state/expresso-diag/2026-10-21.log`.
  - todettu (ei rekisteriin): Höyryn jälkeen (käyttäjä höyrytti kahvin jälkeen, vaihtoi testikahvan): s3 täyttö 555 iskua (1 bar 9,4 s; normaali 1,2–1,4 s), kertymä 44 s, tasaantui 105,95 → k 67,5→50,8 (palautettu 67,5); s4 täyttö 152 iskua (> katto) → arm 2, ei oppia; sen jälkeen +1,9/−1,3 °C heilahdus, koska ilman oppia tasaantumisvaihe ohitetaan ja PI:n integraali valui 0,045→0,008.
  - todettu (ei rekisteriin): Plant-malli: täysteho ~0,6 °C/s, ylläpito ~5 % 98 °C:ssa, häviö ~1,4 °C/min ilman lämmitystä.
- 20.10.2026 — 19.24–22.40, sessio 46d1ae3c (`/pura infra expresso --autojatko`): EXPRESSO-C1-JAKSOT vaiheet 3 ja 4 toteutettu, laitetodennettu ja otettu käyttöön (c1x oletus 1). Kaikki tulokset `paketit/C1-JAKSOT.md` luvut "Vaihe 3 isännällä/laitteella", "Vaihe 4 …", sarjat.
  - Vaihe 3 (esiuutto ytimen 1 jaksoilla): eef7c95 (c1x:0|1, k+2-jono, CX_OK + allow joka päälle-kohdassa, nälkä → EU_STARVE, starve/guard/c1dead/c1full, EU_C1X; relayguard c1_ok; esiuutto_smoke 23 C1Exec-mallilla, ystall_smoke oikea _c1_exec säikeessä), ca29944 (1. tapahtuma kirjoitushetkellä; pico_dev hold odottaa PVENT_END-rivin loppuun), baaecac, 8568e1f (vaihe 4 suunnitelma).
  - Vaihe 4 (uutto bim:1): adf8580 (c1x kattaa uuton, EB_C1X_KP_TAIL 0,2, EB_C1X, TS_END max_loop_ms = lag), f0a7a09 (EU_C1X_LAG_S 0,02: katkaisun ennuste +20 ms, oppi −20 ms), 177e83a (c1x oletukseksi BrewData.eu_c1x = 1).
  - Bootin lukema: c5b22a4 (c1_on täyttää nollat; ei riittänyt), 409431f (_temps_avg vain luetut paikat).
  - Docs: 920578f, 181e472, 129874c (sarjat), c308415 (TILAUS-M-muistutus rekisteriin + Viat).
  - Flashit Zerolla käyttäjän luvalla: eef7c95, ca29944, adf8580, c5b22a4, 409431f, f0a7a09, 177e83a (kaikki VERIFIED 24/24, FLASH_OK; lokit testit/flash-20261020-zero-*.log).
  - Isäntätestit: 28 smokea exit 0 jokaisen commitin jälkeen (lähtötaso HEAD:lla 28/28).
  - ratkennut (Avoimet asiat): EXPRESSO-C1-JAKSOT (kirjattu 20.10.2026) — EXPRESSO-C1-JAKSOT valmis 20.10.2026 (177e83a): vaiheet 3 ja 4 toteutettu, laitetodennettu ja c1x otettu oletukseksi.
  - ratkennut (Avoimet asiat): TILAUS-O (kirjattu 20.10.2026) — TILAUS-O todennettu 20.10.2026: c1x miss 0 esiuutossa ja uutossa (2 × 3+3).
  - viat (ratkaistu, ei rekisteriin): pico_dev hold luki PVENT_END-rivin kesken (HOLD_ABORT, purku ok); korjattu ca29944
  - viat (ratkaistu, ei rekisteriin): ystall_smoke nälän alaraja: isännän RecPin-aikaleima ~40 µs toteuttajan now:n jälkeen (24 961 µs); 1 ms toleranssi 177e83a
  - todettu (ei rekisteriin): C1-JAKSOT valmis ja käytössä: laite ajaa 177e83a:ta (c1x:1 oletus, bim:1). `c1x=1` näkyy vasta seuraavan uuton EU_START-rivillä (todentamatta laitteella oletuksena).
  - todettu (ei rekisteriin): Bootin lukema 409431f:llä: heti flashin jälkeen 98,31 °C heater=0 (ennen 13,97 °C heater=1).
  - todettu (ei rekisteriin): Kuristin TILAUS-M:llä: kuri:25 → KURI_END reason=switch filt=8.21 (testit/kuri-20261020-c1x4.log).
- 20.10.2026 — 18.10–19.15, sessio 7f3871f0 (`/pura infra expresso --autojatko`, automaattivalinta): EXPRESSO-C1-JAKSOT vaihe 2 vietiin laitteelle ja valmiiksi, ja vaiheen 3 toteutussuunnitelma kirjattiin.
  - `pico_dev.py verify` → VERIFIED 24/24: keskeytetty flash 17.50 oli jo kirjoittanut 93d8d2b:n (`testit/verify-20261020-c1lepo.log`).
  - Mittaus 93d8d2b:llä (93de4c8): K3 ei täyttynyt, ja levon viiveet johtuivat ytimen 0 `read_rtd`:stä.
  - Korjaukset: 8c7357b (K3: `rtd_part`, MAX31865-luku yhden tavun osiin, konfiguraatio välimuistista; uusi `testit/max31865_osat_smoke.py` 9/9), 4b0a529 (ydin 1 lukee lämpötilan myös levossa: `c1_rest_on`, `c1_take`, `C1_RST`, `c1_log0`; ystall 64/128 ottaa anturin ytimelle 0 ja palauttaa lepoluvun), bdc1ac9 (`_c1_put` omaksi osakseen 7).
  - Flashit Zerolla (käyttäjän lupa): 4b0a529 18.35 (`testit/flash-20261020-zero-c1lepo2.log`, FLASH_OK, boot bc53c270) ja bdc1ac9 18.59 (`testit/flash-20261020-zero-tr7.log`, FLASH_OK, boot bf882a27 `TEMP_C1 rest`).
  - Tulokset: `paketit/C1-JAKSOT.md` (ca8caa9, dfd6a18). Vaiheen 3 suunnitelma: 60d77e4 (luku "Vaihe 3 — toteutussuunnitelma"). Kartoitus ali-agentilla (Explore).
  - Isäntätestit 32/32 jokaisen muutoksen jälkeen.
  - ratkennut (Avoimet asiat): Levon 0,1–0,6 s viiveet (käyttäjä, kirjattu 20.10.2026) — Korjattu 4b0a529:llä 20.10.2026: ydin 1 lukee lämpötilan myös levossa (HB l100 0), joten levon viiveet poistuivat.
  - todettu (ei rekisteriin): C1-JAKSOT vaihe 2 valmis laitteella (bdc1ac9, boot bf882a27): - ystall:30:643: `ts/tc/tr` 454/443/487 µs (93d8d2b:llä 2011/1153/1129), `gmax_us` 1148, late 0, bad 0, 120 lukemaa. - Levon DIAG_HB 10 min: `lmax_us` 39–47 ms, `l100` 0. Ennen: 174–295 ms ja ~328/min, syynä ytimen 0 `read_rtd` (`time.sleep` 10+65 ms kahdesti pääsilmukan kierroksella, main.py:246 ja :269). - Levon keruu ~20–22 ms.
  - todettu (ei rekisteriin): Termostaatti toimii ytimen 1 lukemalla (T 97,7–98,2 °C, tavoite 98).
  - todettu (ei rekisteriin): MAX31865 SPI on 50 kHz (`pico/lib/adafruit_max31865.py:75`): tavu kestää 160 µs ja yhden tavun osa ~0,45–0,5 ms. Alemmas ei päästä nopeuttamatta SPI:tä.
  - todettu (ei rekisteriin): Levossa `c1_on(3)` alkaa vasta käynnissä olevan luvun jälkeen (≤ 85 ms). Vaihe 3 aseistaa siksi vasta, kun `CX_N` > 0.
  - todettu (ei rekisteriin): Vaiheen 3 kartoitus: silmukka on `pre_infusion_phased` (functions.py:328–729), ei `_eu_loop`. `cx_pin` ei ole asetettu missään. Raakapinni ohittaa `GuardedRelay.allow()`:n, jolloin vahdin 180 s:n ajoraja ei käynnisty. `esiuutto_smoke`n `C1Model.c1_on()` ei ota `want`-argumenttia.
- 20.10.2026 — 17.54–18.04: istunto ffd3ca99 jatkettiin (`claude --resume`, tmux `siirto-infra-expresso-175403`), ja käyttäjä nimesi sen "infra expresso". Selvitettiin istunnon katoaminen (ks. Todettu). Koodia ei muutettu.
  - Pakkaamaton työ toisesta istunnosta: `34bbf933` avattiin puhelimesta 17.35 (`/pura infra expresso`, automaattinen: kyllä), ja se teki C1-JAKSOT vaiheen 2 koodin ja committasi sen expresso-repoon 93d8d2b (17.49). Ytimen 1 odotukset pyörivät `ticks_us`:lla ilman `sleep_ms`ia (levossa ja lukiessa). Toteuttaja (WANT 3, TEMP) ajaa MAX31865:n vaiheet, kun seuraava näyte ja tapahtuma ovat yli 0,7 ms:n päässä, ja kirjaa vaiheiden pisimmät kestot (ts/tc/tr). `_c1_put` on yhteinen, ja ystall-bitti 512 on lisätty. Isännällä ystall_smoke ja kaikki smoket 0 failed (commit-viestin mukaan). Käyttäjä keskeytti flashin 17.50 (`testit/flash-20261020-zero-c1lepo.log`, ei VERIFIED/FLASH_OK-riviä). Istunto arkistoi itsensä 17.55 pakkaamatta.
  - todettu (ei rekisteriin): Istunnon katoaminen 20.10.2026: käyttäjän viimeinen syöte oli 16.40.59 ("Kyllä, commit ja push"), pakkaus 1308b89 valmistui 16.41.24, ja 16.47.02 cron `sulje-istunnot.mjs --pakatut --sulje` (PAKATTU-AUTOSULKU 14.10.2026) sulki prosessin, jolloin Remote Control -istunto poistui käyttäjän listalta. Lähde: `~/.local/state/claude-palautus/sulje-pakatut.loki`.
  - todettu (ei rekisteriin): Transkriptissa ei ole silta-katkoja 13.27–16.47. Istunnon nimi oli koneen antama `palvelin-36`, kunnes käyttäjä nimesi sen 17.54. Käyttäjä 20.10.2026: korjauksia ei käsitellä tässä, aiheena oli vain katoaminen.
- 20.10.2026 — EXPRESSO-GC-UUTTO: käyttäjä valitsi vaihtoehdon 1 "Halvat korjaukset". Toteutettu 28c6685: Ring.put/take_into ei varaa IRQ-pois-osiossa, lähetin esivarattuun pakettiin, `Verkkokello.sd_us` suljettuna kaavana (MicroPythonin naiivilla sum():lla bittitarkka), hist-indeksisummat, `Scale.flow` välimuistiin, wifilink `ipoll(0)`. Flashattu ja 3 testiuuttoa (`testit/gcuutto-20261020-{a,b,c}.log`): EU_STALL 222 → 99–140, EU_GC-mediaani ~19 ms ennallaan, pahin keruu 108/197/109 ms. a1b5581.
  - Juurisyyn selvitys dev-komennolla `ystall:<s>:<bitit>` (`pico/ystall.py`; 0ace9fc–3d306e4, releetön): DIAGNET-lähetin uusi vs. vanha, vahdin kutsu tauolla (`relayguard.paused`, käyttäjän lupa), radio pois ja ydin 1 lukutilaan. Syyksi osoittautui ytimen 1 `sleep_ms`. Tulokset `paketit/GC-UUTTO.md` luvut ystall, Vahtikoe, Radiokoe ja Ydin 1 -koe.
  - HB:hen `lmax_us`/`l100` (30 ms tehtävän myöhästyminen, käyttäjän havainto pitkään päällä olleen keittimen ~0,5 s:n viiveistä) f0b0454. Levon mittauskeruu poistettiin 3ae611b (oma vika).
  - TILAUS-O kirjattu `KAYTTAJAN-TIEDOT.md`:hen (b3bbfab), ja `vaatimukset.mjs --rivi` näyttää sen.
  - EXPRESSO-C1-JAKSOT: ytimen 1 jitter-koe (1cd1bbf, korjaus 2ce3a40), suunnitelma `paketit/C1-JAKSOT.md` (186cf41). K1-malli ali-agentilla (`testit/k1_viive.py`, tulos `testit/k1-20261020-malli.txt`, tarkistettu pääistunnossa samalla komennolla). Vaihe 1: ytimen 1 kuiva toteuttaja `TemperatureSensor._c1_exec` (WANT 3), ystall-bitti 128/256, `lidx`/`lwr_us`-kirjaus (9455203, 44721f2, 3fa436a), kuivakokeet `testit/cx*-20261020-*.log`, johtopäätös e8f9acc.
  - Isäntätestit joka vaiheessa 31/31 (`testit/*_smoke.py` + shot_test + holdout + ctrl_real + pcal). Uudet: `testit/ystall_smoke.py`, staattiset ytimen 1 tarkistukset (ei tuplia eikä liukulukujakoa).
  - Laitteella nyt 3fa436a (boot 033c1656), ytimen 1 lukija toimii (`ystall:5:34` → `c1=1`), `guard=ok`.
  - ratkennut (Avoimet asiat): EXPRESSO-GC-UUTTO — Halvat korjaukset toteutettu ja flashattu 28c6685 (20.10.2026); juurisyy ytimen 1 `sleep_ms`, jatko EXPRESSO-C1-JAKSOT.
  - todettu (ei rekisteriin): Levossa ytimen 0 keruu kestää 80–600 ms (mediaani 90–98) 100 ms:n portain, kun ydin 1 nukkuu 2 ms:n silmukassa (`classes.py` `_c1_loop` WANT 0). Kun ydin 1 lukee (`c1_on`), mediaani on 18 ms, mutta ytimen 0 vuorot venyvät 13–65 ms (65 = `TEMP_C1_CONV_MS`), mikä selittää uuttojen b ja c 60 ms:n katkot. Kun ydin 1 pyörii nukkumatta, keruu on aina 17–21 ms (c1j2-lokit).
  - todettu (ei rekisteriin): Vahdin kutsun työ ja radio eivät vaikuta (vahti- ja radio-lokit).
  - todettu (ei rekisteriin): Ydin 1 muisti lukittuna: 1 kHz:n ADC-silmukka, 120 000 näytettä, suurin väli 1,07 ms ytimen 0 keräessä (c1j2). Kuiva toteuttaja 40 ms:n jonolla uuton kuormalla: 9 × 30 s, ei ylivuotoja, suurin näyteväli 1,18 ms. Jatkuvassa tilassa 0 myöhässä ja 0 tyhjää jonoa. Ainoa myöhästymä (0,77–1,14 ms) oli testin ensimmäinen tapahtuma (`lidx=0`, kirjoitettu myöhässä). 20 ms:n jono ei riitä (late 22–40).
  - todettu (ei rekisteriin): K1-malli: jono 2 jaksoa (+1 jakso) hyväksyttävä (hold_sd +≤0,014, EB-ylitys +0,05–0,12 bar), +2 rajalla.
  - todettu (ei rekisteriin): Testiuutot 20.10.2026 rikkovat TILAUS-Oa: `miss` 26–116 per uutto.
  - todettu (ei rekisteriin): Flashin jälkeinen ensimmäinen `cmd` ei saanut vastausta 90 s:ssa (1 kerta 20.10.); seuraava yhteys toimi.
- 20.10.2026 — EXPRESSO-WIFI-AIKAIKKUNA (käyttäjä: Wi-Fi ei saa häiritä Picoa uuton aikana enempää kuin tiedonsiirto vaatii). Kartoitus (Explore): wifilink 20 Hz herätys ilman uuttotietoisuutta, live+paino 5 Hz erikseen + asetukset 2 s; DIAGNET ~9 pkt/s uutossa; `task_busy('diag')` puuttui; `pm=` ei asetettu.
  - Käyttäjän valinnat: kohdat 1–3, BLE ensin pois; mittaus agentin laiteajolla.
  - Toteutus expresso 1b47954: `preset.BLE = {'enabled': False}` + `main.brew_log_only` (uuttoloki ilman BLE-tehtävää); diagnet: `in_shot()` (= brew tai `quiet`), uutossa lähetys 500 ms täysinä paketteina, HB ilman `gc.mem_free`/RSSI, `task_busy('diag')`, HB:hen `wtx wtxerr wsmax_us`, täysi HB heti PB-uuton jälkeen; wifilink: paino live-paketissa (äppi lukee avaimet erikseen, Macin `lib/features/data/machine_data_notifier.dart:151-180`), uutossa 100 ms askel ja ei asetuspaketteja, ilman tilaajaa 500 ms, `send_max_us`; `run_shot` asettaa `diag.quiet` kaikille tunnisteille (myös TS). Testit: diagnet_smoke ja wifi_suora_smoke uudet tarkistukset; kaikki 26 `testit/*_smoke.py` + `shot_test.py` 0 failed.
  - Laiteajo (käyttäjä hyväksyi ketjun): Pico uudelleen `pico_dev.py safe` (lämmitin oli lukossa `dead=1 guard=heater=norise`), pvent, `wmax:740 wrise:200`, ennen-testiuutto 20 s (boot 8cd69aaf), manifest + flash `testit/flash-20261020-zero-wifiaika.log` (FLASH_PLAN 5/23, VERIFIED 23/23, FLASH_OK, boot 908af624 `BLE off`), äppi tilasi Wi-Fillä 13.08.21, jälkeen-testiuutto 20 s. Tulokset `paketit/WIFI-AIKAIKKUNA.md` (83635e6).
  - GC-kartoitus (Explore) ja suunnitelma `paketit/GC-UUTTO.md` (905ef7d); käyttäjä valitsi "Vain suunnitelma".
  - ratkennut (Avoimet asiat): EXPRESSO-WIFI-AIKAIKKUNA (uusi) — Valmis 83635e6 (20.10.2026): Wi-Fin kuorma uuton aikana minimoitu (BLE pois, diagnet in_shot-lähetys, paino live-paketissa), mittaus laiteajolla.
  - todettu (ei rekisteriin): WIFI-AIKAIKKUNA ennen/jälkeen (20 s TS, `testit/wifiaika-20261020-{ennen,jalkeen}.log`, keräimen HB 13.02–13.09): DIAGNET ~7–9 → ~2 pkt/s; DIAGNET sendto max 20 751 → 1 914 µs; WifiLink ~4,6 pkt/s, sendto ≤ 569 µs; max_loop_ms 92 → 104; EU_VV/EB_VV stall 103/117 → 60/162; EU_STALL 220 → 222; EU_GC 49/101 ms → 52/103 ms. Wi-Fin oma kuorma laski; katkoja hallitsee GC.
  - todettu (ei rekisteriin): Yksi uutto/versio on kohinainen (EB hold_n 341 vs 614).
  - todettu (ei rekisteriin): GC: hallittu `gc.collect()` 300 ms välein (`pico/functions.py:197`, `:650-660`), mediaani ~19 ms, pahin ~100 ms; 27.9. 15–16 ms (keko 307 kt vapaa), nyt fr0 252 kt.
  - todettu (ei rekisteriin): Suurimmat allokaatiolähteet arviolta: 1 kHz float-näyte + `Verkkokello.iq_add` ~240 kt/s, `Verkkokello._grow` listamatriisit ~100–250 kt/s (`pico/verkkokello.py:65-75`), säätimen viipaleet ~50 kt/s, `scale.flow()` joka 50 ms ~30 kt/s (`pico/main.py:471`). `diagnet.Ring.put` allokoi IRQ-pois-osiossa (`pico/diagnet.py:52-68`), tee-ajat uutossa 20–50 ms.
  - todettu (ei rekisteriin): Kaikki moduulit lähdekoodina (MANIFEST vain .py).
  - todettu (ei rekisteriin): Wi-Fi-avain kulkee vain BLE:llä (`wifi:key?`, `pico/bluetooth_handler.py:243`): BLE pois → uusi puhelin ei saa avainta; iPhonessa avain on (WifiKeyStore).
  - todettu (ei rekisteriin): Äppi käytti BLE:tä, kun se oli tarjolla (ennen-uutossa ei Wi-Fi-tilaajaa); BLE:n poistuttua tilasi Wi-Fillä ~4 min flashin jälkeen, kun äppi avattiin etualalle.
- 20.10.2026 — purku ja vianselvitys (käyttäjä: vikatiloja ajossa, pumpun pitkä viive, Zero usein irti). Aamun lämmitinlukitus `norise` = Pico Zeron VBUS-virralla, kone pois verkosta (heat? 09.10–09.15; verkkovirta ~9.14, 80→99,4 °C 70 s:ssa). iPhone-äpin lokit (devicectl): 14.10 uutto 30/95 näyteväliä 200–580 ms, 20.10 8.04 puhdas.
  - Koodiauditointi (ali-agentti): aika-aritmetiikka puhdas (ticks_diff kaikkialla, verkkokello nollautuu per uutto); ehdokkaat: vv=1-silmukan vuoronanto, USB-CDC printin esto, keon täyttö (pending_brew_log ~40 kt).
  - EXPRESSO-DIAGNET (9f8d942, spec paketit/DIAGNET.md): Pico Wi-Fi IOT_SSID (`diag_wifi.py` vain Picolla, ei repossa), os.dupterm-tee + DIAG_BOOT/HB/S/SHOT estämättömänä UDP:nä 192.0.2.11:47210; keräin `diagnet/keraaja.py` + `kaynnista.sh` → `~/.local/state/expresso-diag/` ja HA `sensor.espresso_diag_*` + tapahtumat `espresso_diag`; cron (juuri 6531bc77). Reititin: `dhcp.espresso_pico` 192.0.2.13, `firewall.espresso_diag` (MAC DD:EE:FF:00:11:22 → 192.0.2.11 udp/47210).
  - DIAG_MIN (f840e96): releevartion 100 ms ikkuna → lämmitin/pumppu s/min, paine avg/min/max, kattilan lämpö → HA (state_class measurement).
  - WIFI-APPI (suunnitelma paketit/WIFI-APPI.md): vaihe 0 (831bb3d) scale_payload weight_g/weight_abs_g/flow_g_s (V-210), ohjelmallinen tare, `pico/scalecal.py` (äpin cal:*-vaiheet), BLE RX 128 t; sarjakorjaus (0cf4756); vaihe 1 (39aec74) `pico/wifilink.py` EXA1 UDP 47211, HMAC, avain `link_key.txt` vain BLE:llä (`wifi:key?`); testiasiakas `diagnet/wifi_asiakas.py`. Äppi (Macin Flutter-projekti, ei versionhallintaa, varmuuskopio `~/expresso-ios-varmuus/20261020/`): MachineLink, WifiRepository, LinkSelector, WifiKeyStore; brief expresso-ios/paketit/WIFI-APPI-AEPPI.md; asennettu iPhoneen 20.10.2026 11.17 (profiili 24.10.2026).
  - Flashit Zerolla: testit/flash-20261020-zero-{diagnet,diagnet-2,diagnet-3,diagmin,vaihe0,wifilink}.log, viimeisin VERIFIED 23/23.
  - viat (ratkaistu, ei rekisteriin): V-210 BLE-avainero korjattu firmwaresta 831bb3d; käyttäjä vahvisti paino ja tara äpissä 20.10.2026
  - todettu (ei rekisteriin): Ennen 20.10. flashia laitteella functions.py = df57524 ja main.py = 0da05b5 (5.10.): 7.10. "flashattu" aa3bb8c-kuumavesiraja ei ollut laitteella (verify 18/20). Nyt repo = laite.
  - todettu (ei rekisteriin): secrets.py:n verkkoa HOME_SSID ei ole (wlan status −2); Pico 2 W RP2350, MicroPython 1.28.0.
  - todettu (ei rekisteriin): Simulaatioajo 20.10. 9.46 (painekahva): EB hold 8,02 sd 0,36, max 9,61, miss 149; PB_END max_loop_ms 145; GC 132 kertaa, med 19 ms, max 111 ms; EU_STALL task=ble jopa 63 ms; fr0 267 kt → fr_end 165 kt; idle free 22 kt pend=1 (BLE-loki kuittaamatta, iPhone lukossa).
  - todettu (ei rekisteriin): DIAGNET sendto ≤ 0,56 ms, tee-kirjoitus ≤ 0,57–0,82 ms. DIAG_MIN levossa: lämmitin 5,5 s/min.
  - todettu (ei rekisteriin): Wi-Fi-linkki: Macilta hello ~1 s, live 2,8 Hz (tavoite 5; pääsilmukan kierros > 200 ms levossa); äpin WifiRepository oikeaa Picoa vastaan yhteys 316 ms, stbt:90 ack 45 ms; iPhone 12.02.30 `wifi:key?` BLE:llä → 12.02.31 `WIFI sub 192.0.2.15`.
  - todettu (ei rekisteriin): Testit: kaikki 27 testit/*_smoke.py + shot_test 0 failed; flutter test 62 ok, analyze samat 7 kuin ennen.
- 14.10.2026 — käyttäjä toi keittimeen tulevan Expresso-logon (kuva) ja pyysi poimimaan merkin sovelluksen ikoniksi. Merkki (kahvipapu + keskiura, vipu ylhäällä, kahva alhaalla) mitattiin kuvasta ja piirrettiin vektoriksi; ero alkuperäiseen vain reunojen antialiasointi.
  - Design-kanvaasi "Expresso-sovelluksen ikoni" https://claude.ai/artifact/LHoRZotYaaKTJGnD3LpTJD: 6 vaihtoehtoa (1 Kyltti, 2 Kerma, 3 Musta, 4 Espresso, 5 Kupari, 6 Vahvistettu) iOS-kuvakkeena + 52/36 px ja Androidin pyöreä; alkuperäinen logo ladattu assetiksi.
  - Käyttäjä valitsi 4 Espresso (tausta #3B2519, merkki #E6CFA8), vain iPhone. 1024 px PNG renderöity, Macin projektin `ios/Runner/Assets.xcassets/AppIcon.appiconset` kaikki 15 kokoa korvattu sipsillä; vanhat `~/expresso-ios-varmuus/20261014-ikoni/` (Macilla).
  - Asennus `ssh dev-host '~/expresso-ios-asennus/expresso-asennus.sh'` exit 0: build ok 16 s, asennus valmis 13.39.12, profiili 2026-10-19T04:45:25Z. Käännetyn Runner.appin AppIcon60x60@2x tarkistettu uudeksi; käyttäjä vahvisti: ikoni näkyy kotinäytöllä.
  - Muutos kirjattu omistajalle: V-375 → expresso-ios (b026738).
  - Purku 14.10.2026: `/sa` asetettu (cron ac4844dc, ba527b1a, uusinta cde9fadd 21.10. 8.45).
  - todettu (ei rekisteriin): Merkin geometria (logokuvan pikseleissä, keskipiste 120.9,130.6, kierto −51°): papu rx 67,6 ry 41,8; ura y −8,5…7,5; vipu ympyrä (12,4,−52,4) r 21; ääriviivaraot 4 px. Vertailu alkuperäiseen: ero 12,7 % tummista pikseleistä, reunoilla.
  - todettu (ei rekisteriin): Aiempaa espressologon suunnittelua ei löytynyt mistään: repo, Claude Coden transkriptit tällä koneella ja Macilla (myös taivutusmuodot). Ainoa logoartefakti "Controller logo" on remote-skoopin.
- 7.10.2026 (iltapäivä) – 12.10.2026 — EXPRESSO-KUUMAVESI-RAJAT valmis, TURVAKATO kohta 7 laitteella, Picon nollausselvitys; skoopin jako päätetty 12.10.2026 (pääistunto, opus).
  - **EXPRESSO-KUUMAVESI-RAJAT valmis 7.10.2026:** MANIFEST päivitetty (`pico_dev.py manifest`; functions.py ja main.py puuttuivat MANIFESTista aa3bb8c:n jälkeen), flash Zerolla b466b19 (FLASH_PLAN 2/20 functions.py+main.py, VERIFIED 20/20, FLASH_OK, `testit/flash-20261007-zero-kuumavesi.log`). V-154-raja tarkistettu ennen: `heat?` temp=101.71 guard=ok. Ennen flashia Picolla oli functions.py = df57524 ja main.py = 0da05b5 (hash c38a13f:n MANIFESTista), joten flashin ainoa muutos oli aa3bb8c; uuttopolku ei muuttunut tekstinä. Laitetodennus 520ef47: käyttäjä käänsi kuumavesikytkimen, pumppu pysähtyi ~1 s:ssa (käyttäjän havainto), loki `HOT_WATER_END reason=time` (`testit/kuumavesi-20261007-laite.log`); ~2 min myöhemmin `heat?` heater=0 guard=ok temp=101.61 (lämmittimen sammumishetkeä ei lokissa).
  - **EXPRESSO-TURVAKATO kohta 7 laitteella (d56d07e):** (a) mekaaninen varoventtiili: käyttäjä näki sen, on olemassa. (b) 3 Picon nollausta 10.28.47/10.29.07/10.29.28 (`testit/nollaus-20261007-laite.log`): wmax 720/wrise 250 säilyi joka kierroksella, releet [0,0,0] ennen nollausta, käyttäjä: keitin ei reagoinut. (c) gather-testi Picon MicroPython v1.28 (`testit/gather-20261007-laite.log`): poikkeus yhdessä tehtävässä → `asyncio.run` päättyy 310 ms:ssa (10 ms raisen jälkeen), finally ajetaan, muut tehtävät pysähtyvät (0 tikkiä jälkeen), releet [0,0,0]. (d) wmax-nollautumisen syy koodista: `save_settings` kirjoittaa settings.txt ei-atomisesti (open 'w' + dump, `pico/functions.py` ~3125), ja `load_settings` poistaa koko tiedoston OSError/ValueError:ssa (~3192–3200) → katkennut JSON vie wmaxin. Pelkkä nollaus ei laukaise (testi b).
  - **Picon spontaanit nollaukset (selvitys):** Zeron `journalctl -k` 4 pv: 51 `USB disconnect` -tapahtumaa 5.–7.10.2026, ~1–2 h välein myös yöllä (6.10.: 00.53, 02.27, 03.54, 05.07, …); 7.10. spontaanit 11.45.54 ja 13.41.39 (ei työkaluajoa). Traceback puuttuu, koska sarjalähtöä ei tallenneta. Zero: ser2net `/etc/ser2net.yaml` 2217 raw ja 2218 telnet(rfc2217), kumpikin `/dev/hubi0` 115200n81, kickolduser; python3 3.13.5 ja pyserial asennettu; levy 12 G vapaana, RAM 266 M available; ser2net avaa laitteen vain asiakkaan yhdistäessä. Nollausikkuna koodista: releet 0:aan vasta `main.py:3` (`devsafe.relays_off()`); ennen sitä MicroPython-käynnistys ja `boot.py` (bluetooth-tuonti, `time.sleep(0.1)`), joka ei koske relepinneihin; `devsafe.py`:n kommentti "boot drives the relays off before anything else" ei pidä paikkaansa boot.py:n osalta.
  - **Keskeytynyt:** käyttäjän viesti 7.10.2026 13.53 "korjaa picon sarjalokitus. tallennetaan zerolle" — vain selvitys tehty (Zeron journalctl, ser2net-konfiguraatio, pyserial), ei committeja; jäljellä brief + toteutus + asennus Zerolle + todennus, sen jälkeen käyttäjän viesti "uutto on rikki. tarkasta logit" (13.50).
  - **Päätökset (rekisteriin):** releet alas -vaatimus (7.10.2026), sarjaloki Zerolle (7.10.2026), skoopin jako `expresso` + 4 alaskoopia (12.10.2026; pakkauksen vaihe 2 kaatui samana päivänä muistin loppuessa, 383 Mt vapaana).
  - **Ratkennut (Avoimet asiat):** EXPRESSO-KUUMAVESI-RAJAT, Kuumavesikytkimen aika-/lämpöraja (520ef47); Laitteelta tarkistettavat: varoventtiili, gather, relepinnit, wmax-syy (d56d07e).

- 7.10.2026 — Autojatko-purku (--rd); käyttäjä valitsi EXPRESSO-TURVAKATO ja järjestyksen 4 → pcal → 7.
  - pcal: käyttäjän päätös 7.10.2026 "Ei" — pcal jää kaukalovahdin ulkopuolelle. Kirjattu 01bcfe6 (REKISTERI rivi "`pcal` kaukalovahdin piiriin?" → valmis; TURVAKATO.md kohta 2).
  - TURVAKATO kohta 4 (kuumavesikytkimen raja) tehty koodissa: aa3bb8c `functions.hot_water_run` + `HOT_WATER_MAX_MS = 1000`; main.py kuumavesilohko kutsuu sitä. Ajo katkeaa 1 s:n jälkeen (`HOT_WATER_END reason=time`), vartion pumppukatko sammuttaa myös lämmittimen (`reason=pump`, ei kuivakuumennusta), lämmitin `thermostat.run()`:lla eikä jatkuva 100 %. **Ei flashattu.**
  - r&d: brief `paketit/KUUMAVESI-RAJAT.brief.md` + suunnittelijan holdout `testit/kuumavesi_smoke.py` (01bcfe6); toteuttaja-sonnet toteutti. Holdout: punainen nykyfirmwarella, vihreä referenssillä, vanhan käytöksen mutaatio 6 FAIL. A7 (`turva_toimilaite_smoke.py`) lukee silmukan nyt functions.py:stä.
  - Suunnittelija päivitti aa3bb8c:ssä kaksi rakennetestiä uuteen rakenteeseen: `turva_pika_smoke.py` (hot_water_run sallittu suora kutsu, käyttäjän polku), `valmiustila_smoke.py` (main.py:ssä 2 note_activity + hot_water_run hoitaa kuumaveden).
  - ratkennut (Avoimet asiat): `pcal` kaukalovahdin piiriin? — käyttäjä päätti 7.10.2026: ei, pcal jää kaukalovahdin ulkopuolelle
- 7.10.2026 (klo ~08.10) — EXPRESSO-IDEAT-LUOKITTELU ajettu (autojatko-purku `--rd`, automaattivalinta): suunnittelija luokitteli 12 IDEAT-riviä, toteuttaja-sonnet teki dokumenttikorjaukset briefillä `Infra/iot/expresso/paketit/EXPRESSO-IDEAT-LUOKITTELU.brief.md` (Acceptance 8/8; suunnittelija ajoi uudelleen: vihreä; muuttamattomassa puussa 7/8 punainen). Commit 8dccbec.
  - **Tehty (8dccbec):** `KEHITYSYHTEYS.md` luku "OnePlus-akkuvahti (palvelin)" ja `PICO-HALLINTA.md:280-283`: akkuvahti ajetaan palvelimen cronista 10 min (`PUHELIN=127.0.0.1:5555`), loki `~/.local/state/oneplus-akkuvahti.loki`, rajat HA:n `input_number.oneplus_akku_varoitus`/`_kriittinen` (oletus 30/15); palvelimen systemd-reitti merkitty vanhaksi (V-062, V-197). `PICO-HALLINTA.md` §8 "kirjaamatta — täydennä tähän" → viittaus `Infra/linux/palvelin/README.md` lukuun "Hubi (USB-C, laturi ja HDMI)" (V-149 osa 2). `KAYTTAJAN-TIEDOT.md` §7: uusi tunnusrivi TILAUS-AUTONOMIA (V-214); `vaatimukset.mjs --rivi "infra expresso"` näyttää sen (16 riviä). Mittausrivi `Infra/iot/briefit/delegation.jsonl` (toteuttaja-sonnet, 38 s, 27 351 tok, acceptance 0).
  - **Todettu (luokittelu):** V-062 ja V-197 valmis 8dccbec (loki päivittynyt 7.10.2026 08.00: `AKKU: 79 % lataa=false rajat=30/60`); V-143 valmis 669d3bb (ser2net 2217 + `PICO_LINK=zero`); V-149 valmis (669d3bb: `pico_dev.py:119,135` ohittaa laturikierron Zero-linkillä; 8dccbec); V-214 valmis 8dccbec (hukka EXPRESSO-AUTONOMIA-HUKATTU korjattu, TILAUS-AUTONOMIA näkyy purun VAATIMUKSET-rivillä); V-204 ja V-205 suljettu: Android-äppi suljettu 6.10.2026 (0b0cca4), iPhonen BLE-testi läpi 6.10.2026 21.15; wakelock/shared_preferences todennetaan vain, jos Android-äppi otetaan takaisin, ja oma MicroPython-käännös (MAX_NR_HCI_CONNECTIONS 2) tarvitaan vain kahdelle samanaikaiselle asiakkaalle.
  - **Avoimina rekisteriin:** V-220 (stbt 14772b0 ei flashattu: `pico/commands.py` sha256 ≠ `pico/MANIFEST.json`, tarkistettu 7.10.2026; `relayguard.py` ja `bluetooth_handler.py` täsmäävät; seuraava flash vaatii käyttäjän kuittauksen, MANIFEST päivitetään flashin yhteydessä); V-119 ja V-128 (sama asia: `fmode` 0 osumaa rekisterissä ja HISTORIA.md:ssä, vain isäntäsimulaatio `KEHITYSYHTEYS.md:915-930` 9/9); V-122 (`grep -rli mqtt Infra/iot/expresso` 0 osumaa → oletettu syy vanhan firmwaren retained-discovery-viestit brokerissa); V-210 (avainero: `pico/bluetooth_handler.py:83` `'weight'`, `:101-102` `'flow'`/`'weight'`; äpin `machine_data_notifier.dart` ei ole tällä koneella).
  - **Päätös:** luokittelussa suljettiin vain rivit, joilla on commit-todiste tai käyttäjän 6.10.2026 päätös; V-119 ja V-128 kirjattiin yhdeksi riviksi.

- 7.10.2026 (klo ~06.11–06.15) — EXPRESSO-V154-AAMUTESTI ajettu (pääistunto, Zero-linkki `PICO_LINK=zero`, ei Android-äppiä). Käyttäjä: "Keitin kiinni verkkovirrassa. Ei rupea lämmittämään", heti perään "Eikun alkoi". V-154 todennettu.
  - **Todettu:** `pico_dev.py cmd 'heat?' 6` (06.11) palautti tyhjän tulosteen exit 0; `capture 6` tyhjä; `cmd 'heat?' 10` heti perään: `HEAT temp=25.58 heater=1 dead=0 proven=0 retries=0 dead_c=22.32 on_ms=4000 window_ms=120000 guard=ok`. Zero: `/dev/hubi0 -> ttyACM0` luotu 7.10. 05:07, lsusb `2e8a:0005 MicroPython`, ser2net active, uptime 1 d 23 h. Seuranta 40 s välein (06.12–06.15): 61,58 → 89,61 → 105,2 (heater=0) → 103,62 °C; koko ajan dead=0 retries=0 guard=ok; `proven=0` pysyi nollana myös tavoitteen (102) ylityksen jälkeen (merkitys tarkistamatta). Aamun kylmäkäynnistys lämpeni ~3 min ilman heat_dead-lukkoa eikä sovelluksen asetusmuutosta tarvittu.
  - **Ei todentunut:** PICO-DEV-LINK (aa77c57): ajo käytti Zero-linkkiä, ja korjauksen uudelleenavauspolut koskevat puhelinsiltaa. Ensimmäinen `heat?` Zero-linkillä jäi tyhjäksi (syy selvittämättä).
  - **Päätös:** PICO-DEV-LINK-todennus vaatisi `PICO_LINK=phone`-linkin, joka käynnistää Android-äpin (`pico_dev.py:171`); iOS-päätös 6.10.2026 (0b0cca4) kieltää sen kysymättä → todennus odottaa käyttäjän päätöstä.
  - 6.10.2026 klo 21.2x: expresso-ios-istunnon viesti iOS-päätöksestä (0b0cca4, REKISTERI.md Päätökset) kuitattu; ei rekisterimuutosta tästä sessiosta.

- 6.10.2026 (klo ~09.10) — Autojatko-purku (`/pura infra expresso --rd --autojatko`, ARVIO 6/6, 5dd3564) pysähtyi: heti ajettavaa työtä ei ollut, eikä koodi- tai rekisterimuutoksia syntynyt.
  - **Todettu:** purun `OMISTAJA: TEHTY: 32fb76e` oli väärä hälytys paketin osalta: 32fb76e on V-154 (a) -korjaus, joka on jo kirjattu (REKISTERI.md 3 osumaa, HISTORIA.md 7); aamutesti on tekemättä. PUMPPU-PWM vaiheet 1b–1f vaativat laiteajon (`paketit/PUMPPU-PWM.md`:202–203), MemoryError-rivi odottaa skooppia infra zero (V-207), ja purun RISTIRIIDAT 9 oli V-208:n väärä hälytys (pakkauscommitit, joiden viestissä on "siirto").
  - **Päätös:** autojatko ei aloittanut mitään: SEURAAVA odottaa 7.10.2026 ja käyttäjää, muut ajettavat rivit tarvitsevat laitteen tai toisen skoopin.

- 6.10.2026 — PICO-DEV-LINK (aa77c57) ja TESTIT-REPO-FW (25f5634). Autovaihdon purku (`/pura infra expresso --rd --autojatko`). SEURAAVA (EXPRESSO-V154-AAMUTESTI) on päivälukittu 7.10.2026, joten autojatko valitsi heti ajettavat prosessiraiteen työkaluviat (r&d-tila, sääntö 1b; PUMPPU-PWM-vaiheet ovat tuoteraidetta ja vaativat laitteen).
  - **PICO-DEV-LINK (aa77c57; toteuttaja-sonnet briefistä `paketit/PICO-DEV-LINK.brief.md`, suunnittelija todensi diffin ja ajot):** `pico_dev.py` — `LinkTimeout(RuntimeError)` ja `buf`; `Link.until` käyttää `marker in buf` ja leikkaa merkin perään tulleen kohinan (BLE-sovelluksen `Received: 'sync'`); uusi `Link.reopen()` (force-stop, ensure_bridge ja _connect; zero-linkillä pelkkä _connect), jota myös `__init__`in `ERR usb closed` -haara käyttää; `enter_devsafe` tulostaa `LINK_REOPEN raw REPL silent, reopening bridge`, avaa sillan uudelleen ja yrittää kerran uudelleen, kun raw REPL -aikakatkaisun buf on tyhjä (`tail b''`). Uusi `testit/pico_dev_link_smoke.py` (ei laitetta). Laitteella todentamatta.
  - **TESTIT-REPO-FW (25f5634; toteuttaja-sonnet briefistä `paketit/TESTIT-REPO-FW.brief.md`, suunnittelija todensi):** `testit/ctrl_real_test.py` ja `testit/shot_test.py` käyttävät repon `pico/`:ta (`FW`/`FW_PRESET`-ympäristömuuttujat valinnaisia) eivätkä hiljaa `/tmp/fw`:n vanhaa kopiota. `shot_test.py`:n valelaitteeseen `bd.relay_guard` lisättiin `user_retry` (no-op).
  - **Todettu:** `shot_test.py` repon firmwarea vasten ennen korjausta: `AttributeError: 'types.SimpleNamespace' object has no attribute 'user_retry'` (`classes.py:436` `note_activity`, 9103dc2); se oli vihreä vain `/tmp/fw`:n vanhan kopion ansiosta, joten testit eivät olleet kattaneet 9103dc2:ta. Korjauksen jälkeen: `ctrl_real_test.py` rc=0, `shot_test.py` `RESULT: 0 failed`, `pico_dev_link_smoke.py` `LINK_SMOKE OK 4/4`, `pico_dev_lukko_smoke.py` `LUKKO_SMOKE OK 4/4` (suunnittelijan ajo 6.10.2026); `pico/` pysyi puhtaana.
  - **Rekisterin vanhentunut rivi:** Viat-rivin "`pico_dev.py verify` kaatui kahdesti…" build_set-osa ("build_set.py ei päivitä repon MANIFEST.json:ia") oli jo korjattu 52f4fa6:ssa (`build_set.py`:6–8 kirjoittaa repon `pico/MANIFEST.json`:n); rivi kirjoitettiin nykytilaan (vanha sanatarkasti `ARKISTO.md`).
  - **Päätökset:** tyhjää hello-viestiä ei käytetty sillan uudelleenavauksen merkkinä, toisin kuin rekisteririvi ehdotti (ei tiedetä, lähettääkö silta normaalisti hello-viestin, joten ehto olisi voinut käynnistää sovelluksen uudelleen joka ajolla); `until` pudottaa merkin perään tulleet tavut, koska raw REPL odottaa siinä kohdassa syötettä.
  - **Purun RISTIRIIDAT:** `pura-faktat.mjs`:n 7 osumaa (6c04766, 4c2a7bb, b9df540 "siirto" → expresso-rekisterit) ovat pakkaus-committeja, joiden omistaja on infra expresso; väärä hälytys kuuluu skooppiin claude siirto (kirjattu `vika.sh`:lla omistajalle, V-208).

- 6.10.2026 — PICO-DEV-LUKKO (commit d919331): `pico_dev.py` yksi ajo kerrallaan ja laturi takaisin SIGTERM/SIGHUP-tapossa. Autovaihdon purku (`--rd --autojatko`); SEURAAVA (EXPRESSO-V154-AAMUTESTI) päivälukittu 7.10.2026, joten autojatko valitsi heti ajettavan prosessiraiteen työkaluvian (Viat: kaksi `pico_dev.py capture` -prosessia päällekkäin, 28.9.2026). r&d-tila (sääntö 1b): PUMPPU-PWM-vaiheet ovat tuoteraidetta ja 1c odottaa 1b:n päätöstä.
  - **Toteutus** (toteuttaja-sonnet briefistä `paketit/PICO-DEV-LUKKO.brief.md` + `paketit/PICO-DEV-LUKKO.correction-1.md`; suunnittelija todensi diffin): `acquire_lock(op)` — flock `PICO_DEV_LOCK` (oletus `/tmp/pico_dev.lock`); toinen ajo kaatuu `PICO_BUSY pid=.. op=.. since=..` (exit 1) ennen `ChargerOff`ia; `manifest` ja `charger` lukon ulkopuolella. Lukko on konekohtainen (Mac ja palvelin eivät näe toisiaan). `install_signal_exit()`: SIGTERM/SIGHUP → `sys.exit(128+signum)`, jolloin `ChargerOff.__exit__` (laturi takaisin) ja finally-lohkot ajetaan. Uusi `testit/pico_dev_lukko_smoke.py` (ei laitetta/verkkoa): (a) varattu lukko → PICO_BUSY, (b) vapautuu tapossa, (c) SIGTERM → __exit__ ajettu, exit 143, (d) lähdejärjestys: acquire_lock ennen ChargerOffia ja `op != 'restore'` ennen install_signal_exit-kutsua.
  - **Korjaus 1 (suunnittelijan diff-katselmointi ennen committia):** briefin Do 3 olisi asentanut käsittelijän myös `restore`lle, jolloin SIGTERM-tapossa laturi olisi kytkeytynyt kesken sovelluksen flasherin kirjoituksen (23.9.2026:n vaara, `restore()`-kommentti). `restore` ei asenna käsittelijää; restoren tapon jälkeen laturi käsin: `pico_dev.py charger on` RESTORE_OK/FAIL:n jälkeen. Juurisyy: brief kirjoitettiin lukematta `restore()`-funktiota, vaikka sen kommentti kertoi vaaran.
  - **Todennus:** `python3 -m py_compile` exit 0; `timeout 90 python3 testit/pico_dev_lukko_smoke.py` → PASS a/b/c/d, `LUKKO_SMOKE OK 4/4`; `git status` vain may-tiedostot. Laitteella ei ajettu.
  - **Prosessi:** briefin Acceptance rajattiin polkuun (`git status --porcelain -- Infra/iot/expresso`) — ZERO-PARITEETTI-vian opin soveltaminen; toimi. Kulut: siirtaja-sonnet purku 161 k tokenia / 129 s (ARVIO 6/6); toteuttaja-sonnet 24,5 k / 26 s + korjaus 27 k / 14 s; KONTEKSTI lähtötaso 89 k (konteksti-nyt.mjs 6.10.2026 05:49Z), autopack laukesi 127 k > 125 k.

- 6.10.2026 — ZERO-PARITEETTI: Zero- ja puhelinketjun debug-kykyjen vertailu ja expresso-osan toteutus, commit 465c241. Autovaihdon purku (`--rd --autojatko`), kesken jäänyt viesti (b5322860, 6.10.2026 klo 08.30) jatkettiin ensin.
  - **Kartoitus** (rd-context-raportti, ei laiteajoja, ei `ssh pico-host`): 25 kykyä, path:line-todisteet. `pico_dev.py`: 19 OPS + `charger`, vain 8 riviä haarautuu linkin mukaan (111, 127, 136, 168, 180, 181, 603, 642). Zerolla on cmd, capture, mittauskomennot (koodissa, ei Zero-ajoa kaikista), safe, verify, flash, manifest, watchdog-test; `restore`/`build_set.py` tarkoituksella puhelinketjun. Puuttuu molemmista: pysyvä sarjaloki repossa (puhelinketjun Mac-skriptit `capture_run.sh` eivät ole repossa), kaatumisen traceback (`pico/main.py:487-495` tulostaa vain), tiedostojen luku Picolta, BOOTSEL. Puhelinketjussa logcat (4 M) + sovellus piti USB:n auki. Zerolla asennettu mutta kytkemättä: mpremote, picotool, picocom, esptool (`Infra/iot/zero/REKISTERI.md:60`).
  - **465c241** (toteuttaja-sonnet briefistä `paketit/ZERO-PARITEETTI.brief.md`, suunnittelija todensi diffin): `PICO-HALLINTA.md` luvun 4 loppuun alaluku "Debug-kyvyt: Zero vs puhelin (6.10.2026)" (11 riviä, tila on/osin/puuttuu/ei tarvita); `pico_dev.py` `_connect` Zero-herätys `try/except (subprocess.TimeoutExpired, OSError)` — aiemmin 15 s aikakatkaisu kaatoi työkalun, vaikka kommentti sanoi "not fatal".
  - **V-207 → infra zero** (`vika.sh`, f37507e): (1) Picon sarjatulosteen pysyvä aikaleimattu loki puuttuu (ser2net ei lokita, avaa laitteen vain asiakkaan yhdistäessä; ehdotus: palvelu pitää /dev/hubi0:n auki, kiertävä loki, välittää TCP 2217:n), (2) ser2net 2217 mykkä re-enumeroinnin jälkeen, (3) Picon virtakatko puuttuu (uhubctl/PPPS selvitettävä), (4) /etc/ser2net.yaml ja 99-zero-hubi.rules eivät ole repossa, (5) `Infra/iot/zero/REKISTERI.md:5,58` V-163-rivi vanhentunut (korjattu 669d3bb).
  - **Päätös (käyttäjä 6.10.2026 klo 08.30, "pi zero pitäisi pystyä yhtä hyvään debuggaukseen…"):** rivin "Aamun kaatuminen 5.10.2026" käyttäjän päätöskohta: Zerolle pysyvä loki, toteutus `infra zero` (V-207, TYOTAVAT 10); `pico_dev.py log` tehdään vasta, kun V-207:n loki ja sen polku ovat olemassa.
  - **Prosessi:** briefin Acceptance-rivi 5 (`git diff --name-only` ei muita tiedostoja) ei voinut läpäistä, koska `expresso-ios/*.md` olivat toisen keskustelun likaisia; rajaus `git diff --name-only -- Infra/iot/expresso` todennettu käsin oikeaksi.

- 6.10.2026 — Vikasiivous autojatkopurussa (`/pura infra expresso --autojatko`): SEURAAVA (EXPRESSO-V154-AAMUTESTI) odottaa 7.10. aamua ja käyttäjää (keitin verkkoon), joten aloitettiin heti ajettava vika. Rekisteri 74655 t / 75000.
  - **52f4fa6:** `build_set.py` kirjoittaa puhelimeen työnnetyn ja todennetun manifestin myös repon `pico/MANIFEST.json`:iin (`os.replace` vasta `push_and_verify`:n jälkeen; epäonnistunut työntö jättää vanhan). Uusi `testit/build_set_smoke.py` (valeadb; a onnistuu, b työntö epäonnistuu): RESULT 0 failed. Puhelinketjulla todentamatta (rekisteririvi: todenna viim. 20.10.2026).
  - **26e21f2:** rekisterin vikarivi `build_set.py` ei kirjoita … → `korjattu 52f4fa6 6.10.2026`; "Oire tässä sessiossa" → "Oire 19.9.2026" (rivi asetettu 5212bca 19.9.2026), koska check-rekisteri punasi "tämä sessio"; rivi lyhennettiin katon alle (75040 → 74957 t); "Korjattiin käsin kopioimalla puhelimen manifesti; korjaus työkaluun tekemättä" → "Korjattiin ensin käsin". Vanha versio sanatarkasti `ARKISTO.md`:ssä.
  - **3344883** (käyttäjän valinta AskUserQuestionissa "Sulje 2 analysaattorivikaa"): vikarivit `verdict` ei päättele mekanismia PSKIP_SUB/PSKIP_FUND-suhteesta ja `PGAP_BEST`-rivi poimii yksittäisen suurimman lukeman → valmis 6.10.2026 (vanhentunut, ei korjausta koodiin); `arkisto.mjs` siirsi ne `ARKISTO.md`:hen.
  - **Todettu:** `PGAP_BEST` ei esiinny missään repon .py-tiedostossa eikä git-historiassa koodina (`git log --all -S PGAP_BEST` → vain 28dff60:n lokit ja rekisteri); nykyinen `pico/functions.py` tulostaa vain `PGAP_START`, `PGAP k=…`, `PGAP_END` (rivit 1921–2027). Lokeissa `testit/pgap-20260920-{a,b,c}.log` rivi näkyy, eli sen tulosti 20.9. committoimaton firmware. `testit/psweep_read.py:137` `verdict` = vakaa/hajoaa viiveen hajonnasta; PSKIP_SUB/FUND ovat vain `testit/pskip_delay.py`:ssä (ei verdictiä); portitettu pyyhkäisy hylättiin 28dff60 (20.9.2026), vastesuureen valinta jatkuu Avoimet-rivillä "Analysaattorin tuomio". `build_set.py` on 5.10.2026 alkaen vain puhelinketjun varareitti; Zero-ketjussa repomanifestin laskee `pico_dev.py manifest` (PICO-HALLINTA.md:23).

- 6.10.2026 — EXPRESSO-V154-FLASH tehty: 9103dc2 flashattu Zerolla (3f8abc8), `heat?` dead=0 guard=ok. Autojatkona (`/pura infra expresso --autojatko`); SEURAAVA EXPRESSO-V154-AAMUTESTI (7.10.2026).
  - **Manifesti:** `pico_dev.py manifest` (Zero-ketju, paikallinen laskenta) 9103dc2:n setille: muuttuivat /classes.py 68080 B, /commands.py 21050 B, /relayguard.py 15686 B (`pico/MANIFEST.json`, d6d1ddb).
  - **Smoket ennen flashia:** `testit/turva_toimilaite_smoke.py` (sis. D23 `heat?`) ja `testit/valmiustila_smoke.py` — molemmat RESULT: 0 failed.
  - **Flash:** käyttäjän kuittaus AskUserQuestionilla 6.10.2026 ("Flash now": keitin verkossa, lämmin; vanha firmware ei raportoinut mitattua lämpötilaa millään komennolla ja passiivinen `capture 8` valmiustilassa ei tulostanut mitään, joten kylmä/lämmin kysyttiin käyttäjältä) → `pico_dev.py flash` Zeron kautta: SAFE_OK, FLASH_PLAN 3/20 (classes, commands, relayguard), VERIFIED 20/20, FLASH_OK. Loki `testit/flash-20261006-zero-v154syy.log`, commit 3f8abc8.
  - **Todennus:** `pico_dev.py cmd 'heat?' 6` → `HEAT temp=100.29 age_ms=103 target=102.0 heater=0 dead=0 proven=0 retries=0 dead_c=None window_ms=120000 guard=ok`. Ensimmäinen yritys oletusdrainilla 3 s ei tulostanut mitään (Pico vielä käynnistymässä); drain ≥ 6 s heti flashin jälkeen.
  - **Päätös (käyttäjä, valvomaton kylmäkäynnistys):** nykyinen + kiertotie, ei firmware-muutosta; ks. REKISTERI.md Päätökset 6.10.2026. Avoin rivi "Kylmä käynnistys irti verkosta…" poistettu avoimista.
  - **Sivuhuomio:** autojatko pysähtyi flashin kuittausrajaan ilman jatkopyyntöä (pyyntö vain loppuyhteenvedon proosassa, ei AskUserQuestionia); käyttäjä huomautti, ja vika kirjattiin V-202:ksi skoopille `claude siirto` (vika.sh, a499585). Tässä sessiossa korjattu toimintatavaksi (seuraava pysähdys AskUserQuestionilla).

- 6.10.2026 — EXPRESSO-V154-SYY tehty koodin ja smoken osalta, commit 9103dc2 (ei flashattu). Autojatkona (automaattivalinta), käyttäjä ei paikalla. SEURAAVA EXPRESSO-V154-FLASH.
  - **Syy:** 5.10. illan flash (cae9100; rekisterin "Firmware 5.10.2026" ja valmiustilarivi "Keitin oli verkkovirrasta pois (kattila 25,9 °C), Pico Zeron USB-virralla") käynnisti Picon kylmänä irti verkosta. Ei-nouse-lukko syntyi huoneenlämmössä (heat_dead_c ≈ 25,9), jäähtymistodistetta ≥ 10 °C ei voi tulla (aamulla 23,1 °C), joten 3 uusintaa 10 min välein kuluivat ~30 min flashin jälkeen ja lukko jäi uudelleenkäynnistykseen asti. Tämä on 32fb76e:n kirjattu "Tunnettu raja" (Päätökset, Käyttäjä 5.10.2026 V-154 menetelmä): 5.10. session flash osui omaan rajaansa. Selittää myös, miksi sarjaportissa ei 06.xx näkynyt GUARD_RETRY/GUARD_TRIP: uusinnat oli käytetty, ja GUARD_TRIP tulostuu kerran per laukaisu.
  - **Hypoteesit hylätty koodista:** lepopaine −1,4 bar vs `PRESSURE_RAW_MIN_BAR` −1,5 (`relayguard.py:48`) koskee vain pumppua (`_pump_reason`), ei lämmitintä; proven-tila ei nollaudu uusinnassa — tahallista ja kunnossa (kuuma illan sammutus → todiste pysyy → uusinta 60 s välein, smoke D14–D16).
  - **Toisto:** `testit/turva_toimilaite_smoke.py` D17–D18 (kylmä käynnistys 25,9 °C, 8 h ilman verkkoa → lukko, retries=3, verkkovirta takaisin → ei lämpene) vihreänä ennen korjausta.
  - **Korjaus (valinnan (a) sisällä, valvomaton lämpöbudjetti ei löysene):** `relayguard.user_retry()`: käyttäjän toiminto (`classes.note_activity`: kytkin, sovelluksen asetusmuutos, tshot) vapauttaa lukon heti yhteen 30 s uusintaan; automaattiuusintojen budjetti ei täyty (D19–D22). Tulostaa `GUARD_RETRY heater user=<syy> n=<retries> temp=<t>`. Tilakomento `heat?` (`commands.py`, `relayguard.heat_status`): `HEAT temp=<mitattu> age_ms= target= heater= dead= proven= retries= dead_c= dead_age_s= on_ms= window_ms= guard=`; vain luku, ei aktiivisuutta (D23). STBY-raportin `temp=` → `target=` (oli asetusarvo `get_target_temperature()`).
  - **Smoke-vika:** `testit/valmiustila_smoke.py` käytti hiljaa `/tmp/fw`:tä (5.10.2026 klo 12.21 jäänyt vanha kopio), jos hakemisto oli olemassa: smoke oli vihreä vanhaa koodia vastaan. Nyt repon `pico/`, ellei `FW`/`FW_PRESET`-ympäristömuuttujaa anneta. `testit/ctrl_real_test.py` ja `testit/shot_test.py` käyttävät yhä samaa `/tmp/fw`-oletusta (ei muutettu).
  - **Todettu:** kaikki 18 `testit/*_smoke.py` exit 0 (`RESULT: 0 failed`; ohjevahti_smoke exit 0 ilman RESULT-riviä) 9103dc2:n tilassa. `/tmp/fw` erosi reposta: bluetooth_handler.py, classes.py, commands.py, functions.py, main.py (`diff -rq`); ei poistettu.
  - **Päätökset:** ks. REKISTERI.md Päätökset 6.10.2026 (hylätyt: hidas uusinta rajatta, pumppupulssi, lukon tallennus flashiin).

- 6.10.2026 — EXPRESSO-V154-TODENNUS ajettu, **epäonnistui**: korjaus 32fb76e ei riitä; syy selvittämättä. SEURAAVA EXPRESSO-V154-SYY. Käyttäjä valitsi /purussa "Aloita EXPRESSO-V154-TODENNUS" (5.10.2026). Koodia ei muutettu, laitetta ei flashattu.
  - **5.10.2026 klo 20.45 "firmware on kaatunut":** `pico_dev.py safe` (DEVSAFE relays=[0,0,0], SAFE_OK) → firmware käynnistyi, sovellus yhdisti (`sync`, `brew_log?`). Keskeytyksen traceback osui `adafruit_max31865.read_rtd`:hen (`classes.py:1561`); kaatumisen syy jäi kaappaamatta. Klo ~20.50 sovellus pysäytettiin käyttäjän pyynnöstä OnePlussalla: `adb -s 127.0.0.1:5555 shell am force-stop com.example.silvia_pico_ui` (paketin nimi: `pm list packages -3`).
  - **Virhe, 5.10. klo 22.15:** havaittiin, että `stby:`-raportin `temp=` on asetusarvo (`brew_data.get_target_temperature()`, `pico/commands.py:460`), ei mittaus. 5.10. flashin kirjaus "temp=102.0 (keitin verkkovirrassa, lämmin)" ja V-154-todennusmenetelmä nojasivat siihen, samoin pääistunnon päätelmät klo 20.36 ("lämmin") ja 20.43 ("jumissa", resetin peruste). REKISTERI.md korjattu: todennusmenetelmäksi sovelluksen lämpötila (`am start`/`monkey` + `uiautomator dump`, `KEHITYSYHTEYS.md:243`), flashin kirjaus "(asetusarvo, ei mittaus)", uusi Viat-rivi. Hukkarivi EXPRESSO-STBY-TEMP-ASETUSARVO.
  - **Todennus 6.10.2026 ~05.57–06.03:** keitin verkkovirtaan, Zeron USB kiinni koko yön; virtavalo päällä, lämmitysvalo ei. Sovellus 05.58:13, 05.58:52, 05.59:27, 06.00:46, 06.02:07, 06.02:34: 23,1 °C, −1,4 bar, sama lukema 4,5 min. `pico_dev.py cmd stby:30` 06.01:19 → `STBY_OFF reason=app`, `temp=102.0`; sarjaportin kaappaukset 05.58 (12 s), 06.00:46 (20 s): ei `GUARD_RETRY`/`GUARD_TRIP`. Sovellus käynnistetty 05.57 `monkey -p com.example.silvia_pico_ui`.
  - **Reset 06.03:** `pico_dev.py safe` → käyttäjä: lämmitysvalo palaa heti; kiertotie toimii. Pääistunto resetoi ennen syyn kaappausta, koska käyttäjä tarvitsi keittimen; tila (heat_dead, proven, retries) menetettiin. Traceback taas `adafruit_max31865.read_rtd` (rivi 183; 5.10. rivi 187), sama kohta kuin `KEHITYSYHTEYS.md:236`; ei todiste.
  - **Koodiluku (hypoteesit, ei tarkistettu):** `relayguard.py:48` `PRESSURE_RAW_MIN_BAR` −1,5 vs −1,4 bar lepopaine (`sensor_bad_n` rivi 166); `relayguard.py:225–245` proven-tila ei nollaudu uusinnassa vaan lämmön noustessa, ilman todistetta 3 uusintaa 10 min välein, sitten lukko restarttiin asti.

- 5.10.2026 — Valmiustila äppiin: firmware a741d90 flashattu Zerolla (e89d205), sovellus asennettu OnePlussaan, `IDLE · STANDBY` todennettu pystynäkymässä; vaakanäkymä todentamatta laitteella. SEURAAVA EXPRESSO-V154-TODENNUS jätettiin 6.10. aamuun (päiväsidottu, korjaus 32fb76e tehty); käyttäjä valitsi /purussa "Valmiustila äppiin (suositus)".
  - **Firmware a741d90:** `pico/bluetooth_handler.py` `live_payload` lisää `'standby': True` vain kun `brew_data.standby` (valmiustila on vain IDLE-tilassa → lyhin mode-merkkijono, paketti mahtuu 240 B:hen); live-paketti ilman avainta = pois. `testit/uuttoloki_smoke.py`: fixtureen `bd.standby = False` ja 2 uutta tarkistusta → RESULT: 0 failed, valmiustilapaketti 228 B.
  - **Sovellus (Mac, ei versionhallintaa, `~/src/eXpresso_Grok/legacy/latest/silvia_pico_flutter_UI/`):** varmuuskopio `../silvia_pico_flutter_UI-varmuus-20261005-valmiustila.tgz` (lib, test, pubspec.yaml) ennen muutoksia. `lib/models/machine_status.dart` uusi kenttä `@Default(false) bool standby` (freezed/g regeneroitu `flutter pub run build_runner build`; diff varmuuskopioon: vain 5 tarkoitettua tiedostoa + landscape_layout.dart). `machine_data_notifier.dart`: standby päivitetään vain paketista, jossa on `boiler_temperature` (`json['standby'] == true`), BLE-katkossa false. Pystynäkymä `value_display.dart` Mode = `IDLE · STANDBY`; vaakanäkymä `landscape_layout.dart` `STANDBY`-teksti lämpötilan alla (vaakanäkymässä ei ole Mode-riviä). Vain lib/-tiedostot muutettu, ios/ koskematon; BLE-protokolla kuuluu expresso-ios-rekisterin rajan mukaan skoopille `infra expresso`.
  - **Flash ja asennus (käyttäjä hyväksyi AskUserQuestionilla):** e89d205: `pico_dev.py manifest` + `flash` Zerolla → WROTE /bluetooth_handler.py, VERIFIED 20/20, FLASH_OK (`testit/flash-20261005-zero-valmiustila.log`). Debug-APK (sama debug-avain kuin 17.9. asennettu) `adb -s 127.0.0.1:5555 install -r` → Success (kahdesti; toinen vaakanäkymän lisäyksen jälkeen). Rekisterin rivi "Äppi ei näytä valmiustilaa" → todennettu (e89d205).
  - **Päätökset:** ks. REKISTERI.md Päätökset 5.10.2026 (erillinen `standby`-avain). `update_standby`:n `import utime` joka kierroksella jätettiin ennalleen: MicroPythonissa toistuva import on sys.modules-haku, eikä pelkkä se oikeuta flashia; rivi jäi pieneksi avoimeksi asiaksi.
  - **Todettu:** laitteella pystynäkymä (uiautomator dump): `stby:on` → `STBY_ON idle_s=0 target=90`, sovellus `IDLE · STANDBY`; `stby:30` → `STBY timeout_min=30 standby=0 temp=102.0`, sovellus `IDLE`; valmiustila palautettu oletukseen (30 min). `flutter analyze lib` 0 virhettä, `flutter test` 26/26 (Mac, Flutter 3.41.6). Puhelimessa herätyksen jälkeen Androidin "Mirror to external display?" -dialogi: Dismiss (ei peilausta, nykytila säilyi). Keitin oli verkkovirrasta pois (kattila 25,9 °C), Pico Zeron USB-virralla.

- 5.10.2026 — Avoimet asiat -rivit tarkistettu lähteestä; neljä riviä suljettu valmiiksi (koodia ei muutettu, laitetta ei ajettu).
  - **Vaihe 1h suljettu (käyttäjä):** verkkokello korvasi. `pre_infusion_phased` luo `Verkkokello(t0)`:n 50 Hz:stä joka ajolla ja oppii jakson (`pico/functions.py:290`), joten TILAUS-F täyttyy; `brew_data.mains_hz/mains_period_us/mains_phase_us` (asetetaan `functions.py:2593`) ei lue mikään muu koodi (grep `pico/`). TILAUS-G:n vaihe nousussa on harhainen (`paketit/VERKKOKELLO.md` 24.9.2026, käyttäjän valinta (a) 27.9.2026). Hylätty: taajuuden alkuarvo nousun Goertzelista (~0,03 Hz, kuormittaa ajoitussilmukkaa).
  - **1 %:n säätötarkkuus valmis (käyttäjä kuittasi):** delta-sigma vaiheissa 2, 3 (katkaisun jälkeen) ja 4 (`pico/functions.py:484`); pim:1/bim:1 oletuksena bdb8463, joka on flashatun 32fb76e:n esi-isä (`git merge-base --is-ancestor`); vaatimus kirjattu `KAYTTAJAN-TIEDOT.md:57`.
  - **Vesisäiliön taso ennen laiteajoa valmis:** `KAYTTAJAN-TIEDOT.md:382` "Ajon hyväksyntä kysyy läsnäolon ja säiliön veden".
  - **`psweep-20260920-1b*`-tulkinta suljettu (käyttäjä):** portti ajastettiin kiinteällä `PCAP_MAINS_US` 19960 us (`git show 28dff60:…functions.py`, `pcap_gate`), joten käsketty vaihe ei ollut verkkovaihe venttiilitilasta riippumatta; vaihekysymykseen vastasi vsweep-20260924-a. Lokit c–h: seg 0 trimmaus 3,29–5,79 bar; b ja 1b `overpressure` ennen segmenttejä.
  - **Todettu:** 17 ms `PumpPressureController` on yhä käytössä (`functions.py:55` pim:0, `:931` vanha uutto/virtaustila, `:1187` pcal-pito, `:2768` klamp), joten rivi "Säätimen 17 ms askel → 20 ms" pysyy avoimena.

- 5.10.2026 — EXPRESSO-TURVA-DEVRUN valmis (e4b9afa) ja V-154 korjattu käyttäjän valinnalla (a) (32fb76e); molemmat flashattu Zerolla (e2c0753, cae9100); V-154:n todennus aamulla 6.10.2026.
  - **e4b9afa:** `main.py` kuri-säätötila `await dev_run(throttle_set_run(...))` (oli suora kutsu dev_run:n ohi, e0fb94f); `turva_pika_smoke` odotus 13 → 14 dev_run-kutsua. `throttle_set_run` sammuttaa lämmittimen jo itse (`functions.py` `RELAY_HEATER.value(0)` funktion alussa), joten käytös ei muuttunut. turva_pika_smoke ennen 1 failed, jälkeen 0 failed; isäntätestit 18/18 (`testit/*smoke*.py`).
  - **e2c0753 (e4b9afa flashattu Zerolla käyttäjän luvalla):** FLASH_PLAN 1/20 (/main.py), VERIFIED 20/20, FLASH_OK; firmware vastaa (`pcal:st` → PCAL_ST state=idle, `stby:30` → temp=102.0). Loki `testit/flash-20261005-zero-devrun.log`.
  - **32fb76e (V-154 korjattu, käyttäjän valinta (a)):** `relayguard.py` ei-nouse-lukon (heat_dead) uusinta. Uudet vakiot HEATER_NORISE_COOL_C 10,0 / RETRY_ON_MS 30000 / RETRY_MS 600000 / RETRY_MAX 3 / RETRY_PROVEN_MS 60000; uusi metodi `_norise_retry`, sarjarivi `GUARD_RETRY heater proven=<0|1> n=<n> temp=<t>`. `turva_toimilaite_smoke` D9 muotoiltu ("ei vapaudu heti"), uudet D10–D16: ilman jäähtymistä 3 uusintaa 10 min välein, sitten pysyvä lukko; yö ilman verkkovirtaa → jäähtyminen todistaa anturin → aamulla lämmitys alkaa ≤ 90 s; nousu nollaa uusinnat ja todisteen. Isäntätestit 18/18; uudet testit kaatuvat vanhalla relayguardilla (AttributeError, vanha D9 = pysyvä lukko).
  - **cae9100 (32fb76e flashattu Zerolla käyttäjän luvalla):** FLASH_PLAN 1/20 (/relayguard.py), VERIFIED 20/20, FLASH_OK, `stby:30` → temp=102.0. Loki `testit/flash-20261005-zero-v154.log`.
  - **Päätökset:** menetelmä (a); hylätty (b) optoerotin GPIO:hon ja (c) Picon syöttö keittimestä; mitoitus (jäähtyminen ≥ 10 °C, 60 s / 3 × 10 min uusinnat, 30 s lämmitys, lisälämpö ≤ 3 × ~33 kJ) ja tunnettu raja Päätökset-luvussa (REKISTERI.md). Flashit heti, ei odoteta seuraavaa firmwaremuutosta.
  - **Todettu:** `pico_dev.py cmd` heti flashin jälkeen palautti tyhjän tulosteen molemmilla kerroilla (exit 0); seuraava yritys 15 s ikkunalla onnistui. Keitin oli verkkovirrassa ja lämmin flashien aikaan (temp=102.0).
- 5.10.2026 — EXPRESSO-ZERO-FLASH tehty (V-163 korjattu, 669d3bb) ja uuttoloki-setti flashattu Zerolla (6aff448); uutto ja valmiustila testaamatta.
  - **669d3bb:** `pico_dev.py` oletus `PICO_LINK=zero` (ser2net raw 192.0.2.10:2217; adb, sovellus, ChargerOff ja Shelly ohi), uudet komennot `flash <MANIFEST.json>` (devsafe SAFE_OK → muuttuneet tiedostot `<nimi>.new` + SHA-256 Picolla → uudelleennimeys → VERIFIED n/n → machine.reset; ei mpremotea, koska se ei ruoki devsafen 8 s vahtia) ja `manifest <MANIFEST.json>` (laskee manifestin repon pico/-tiedostoista, secrets.py säilyy). `restore` ja `build_set.py` = vain puhelinketju. PICO-HALLINTA §1/§7/§8, KEHITYSYHTEYS (alku + "Aloitus") ja build_set.py:n docstring kuvaavat Zero-ketjun. Valepico-testi (scratch): 3/20 kirjoitus, uusinta 0/20, katkos kesken kirjoituksen → vanha main.py ehjä, ei .new-jäämiä.
  - **Laiteajo käyttäjän luvalla** (läsnä, säiliössä vettä): ensimmäinen Zero-flash 8/20, VERIFIED 20/20, FLASH_OK (`testit/flash-20261005-zero.log`) → firmware kaatui käynnistyksessä `relayguard.start` → `Timer(-1)` → `OSError ENOMEM`, main poistui, releet pois, keitin ei lämmittänyt. kuri6 palautettiin gitistä (66ae5a2:n manifesti, 18/18 tiivistettä täsmäsi) `pico_dev.py flash`illä, FLASH_OK VERIFIED 19/19 (`testit/flash-20261005-zero-palautus-kuri6.log`); toistettiin diagnoosin jälkeen.
  - **6aff448:** `temperature_sensor.c1_start(utime)` siirretty main.py:n alusta `watchdog_feeder`iin `relay_guard.start()`in ja `devsafe.start_watchdog()`in jälkeen. Laitteella FLASH_OK 1/20 (main.py), vakaa 3+ min ilman uudelleenenumerointia, `CMD_OK pcal:st`, `stby:30` → `temp=102.0` kahdesti minuutin välein. Pico ajaa nyt repon pico/-settiä (uuttoloki + valmiustila + korjaus). Samassa commitissa pico_dev.py herättää sillan (`ssh pico-host` + pyserial avaa/sulkee /dev/hubi0) ennen jokaista yhteyttä.
  - **V-154-mittaus** (käyttäjä sammutti ja käynnisti keittimen): raaka paine-ADC (GPIO28, 400 näytettä) keitin päällä avg 10764 (raw_bar −0,133), keitin pois avg 10835 (raw_bar −0,111).
  - **Todettu:** rp2 MicroPython v1.28 `machine_timer.c`: ENOMEM = `alarm_pool_add_alarm_in_us` palautti −1 (oletusajastinpooli täynnä); keko ei syy (gc 309 632 vapaana). Kaatuminen toistui joka käynnistyksessä (myös Ctrl-D), mutta REPL:ssä myöhemmin Timer onnistui säikeen eläessä. REPL-kokeet kuri6:lla: nukkuva tai heap_lock-säie core 1:llä ei estänyt Timeria → tarkka mekanismi todentamatta. Pehmeä reset (Ctrl-D) vahdin ollessa päällä → laitteistovahti nollaa Picon käynnistyksen aikana (15.42.02); yksi selittämätön uudelleenenumerointi 15.42.51, sen jälkeen vakaa. Zeron ser2net-ansa toistui 3×. Isäntätestit 17/18 vihreitä.
  - **Päätökset:** flash Zerolla omalla raakaREPL-kirjoittimella, ei mpremotella (vahti 8 s, releluenta) — käyttäjän paketin "mpremote tai /dev/hubi0" -vaihtoehdon tilalle. Osa 3 (valmiustilatesti + kahvi) siirrettiin toiseen kertaan ENOMEM-selvityksen takia; käyttäjälle sanottu, ettei tarvitse odottaa.
  - Hukkarivi EXPRESSO-V154-KYTKENTA (V-154:n päätösperuste oli puhelin-OTG-ajan mittaus 17.9.; Zero-kytkennässä ero katosi) talletettu odottamaan.
- 5.10.2026 — EXPRESSO-UUTTOLOKI-LAITE aloitettu, EI flashattu; reitti väärä (Pico on Zerolla), seuraava paketti EXPRESSO-ZERO-FLASH.
  - Isäntätestit: uuttoloki_smoke, valmiustila_smoke, shot_test, kuri_smoke, esiuutto_smoke, turva_toimilaite_smoke 0 failed; turva_pika_smoke 1 failed (`main.py: ei suoria testiajokutsuja dev_run:n ohi — ['throttle_set_run']`, ennestään: tuli e0fb94f:ssä, joka on jo ajossa olevassa kuri6:ssa; käyttäjän kuri:1-uuttopolku, ei testikomento).
  - Setti `20261005-uuttoloki1` rakennettu PUHELIMEEN (`build_set.py --from 20260928-kuri6`, 19 tiedostoa + MANIFEST, 20 merkintää). Repon `pico/MANIFEST.json` päivitetty puhelimen setin manifestista (19 paikallista täsmää SHA-256:lla, `/secrets.py` vain puhelimessa). Setti sisältää myös flashaamattomat TEMPSTALE (e4c8665, bdb8463), VALMIUSTILA (f5a67c3), f17afe8 ja UUTTOLOKI (9deb88f).
  - Käyttäjä hyväksyi flashin, mutta hylkäsi `pico_dev.py restore` -ajon: flash kulkee Zeron kautta, ja Shelly on OnePlus-hubin laturi eri paikassa, ei keittimen raudassa. Picoon ei kirjoitettu mitään.
  - Pääistunto päätti järjestyksen (käyttäjä "Päätä itse"): flash-reitti Zeron kautta, V-154-korjaus samaan settiin, sitten UUTTOLOKI-LAITE-todennus; kiertotie kunnes V-154 korjattu: keittimen USB irti Zerosta illaksi tai aamulla Zero irti + keitin pois–päälle.
  - Rekisteriin kirjattu kaksi Viat-riviä (flash valmisteltiin puhelinketjuun vaikka Pico on Zerolla; V-154 toistui 5.10. aamulla) ja hukkarivi EXPRESSO-ZERO-USB-EI-LEVINNYT (talletettu odottamaan, pääistunto kirjaa). Mittaukset: Todettu 5.10.2026 — Picon yhteys kulkee Zeron kautta (REKISTERI.md).
- 5.10.2026 — EXPRESSO-UUTTOLOKI isäntäosa valmis, commit **9deb88f** (claude_local, ei vielä pushattu ennen pakkausta). Käyttöönottoketjun kohta (4) isäntäosa tehty; flash ja todennus oikealla kahvilla (kohta 5, viim. 12.10.2026) tekemättä.
  - Lähde: elokuun firmware luettiin puhelimesta `adb -s 192.0.2.11:5555 exec-out "run-as com.example.silvia_pico_ui cat files/firmware/<f>"` (10.8.2026: brew_logger.py 10 056 B, bluetooth_handler.py 28 120 B, main.py 41 300 B). Vain luku.
  - Uusi `pico/brew_logger.py`: BrewSessionLogger elokuun v3-muodossa (rivi [t_ms, T×10, P×100, F×100, hx_a, hx_b, W×10, liput bit0 pumppu bit1 lämmitin], MIN 15 s, MAX 65 s, tapahtumat session_start / phase_PRE_INFUSION|BREW|SOFT_RELEASE / log_stop / log_stop_<syy> / session_end). Erot elokuuhun: ei pumpun reunatapahtumia (vaiheohjattu pumppu kytkee joka jaksolla → tuhansia), tapahtumat max 40, export luovuttaa listat kopioimatta (elokuun syväkopio tuplasi huippumuistin), näytteet BLE-tehtävästä `brew_log_service` (main.py ble_communication, 30 ms silmukka) eikä uuttosilmukoista → hyväksyttyjen säätösilmukoiden ajoitus ei muutu; W on istuntotaarattu (paino − paino alussa).
  - `functions.run_shot`: loki alkaa vain kytkimen uutossa (label PB), loppuu ennen solenoidin purkua syyllä spr_end / switch_off / abort, finallyssä error; testiuutto TS ja kuri:1 (throttle_set_run) eivät kirjaa.
  - `commands.py`: `sync`/`get:settings`/`settings?` → settings_requested; `brew_log?`/`brew_log:get` → uudelleenlähetys metasta jos odottava loki; `brew_log:ack[:id]` vapauttaa. Ei `updated`ia → ei aktiviteettia, ei herätä valmiustilasta.
  - `bluetooth_handler.py`: multipack meta → samples 20 riviä/osa → end, yksi kehys per lähetysvuoro (200 ms), palat ≤ min(MTU−3, 240) B + rivinvaihto, MTU-tapahtuma 21, live ja asetukset tauolla koko multipackin ajan, epäonnistunut kehys uusitaan samana askeleena, uudelleenyhteys lähettää metasta, ack kesken vapauttaa ja live jatkuu.
  - `scale.py`: raw_a/raw_b (HX711-raaka) ja scale_meta() {scale, trim_b, sense 1, off_a, off_b}; `classes.py`: tilakentät (brew_logger, tray_scale, pending_brew_log, brew_log_send_requested, brew_log_tx_reset, settings_requested); `main.py`: logger + tray_scale brew_dataan, brew_log_service BLE-silmukassa.
  - Uusi `testit/uuttoloki_smoke.py` (lukee pico/ suoraan, ei /tmp/fw:tä): 41 PASS, RESULT 0 failed.
  - viat (ratkaistu, ei rekisteriin): ennestään kirjattu (HISTORIA 5.10.2026), ei tämän session aiheuttama
  - todettu (ei rekisteriin): Smoke löysi: näyte "≥ 100 ms edellisestä" 30 ms:n tehtävästä antoi 120 ms välin (8,3 Hz, 250 riviä/30 s); korjattu 100 ms ruudukkoon → 301 riviä/30 s, väli 90–120 ms.
  - todettu (ei rekisteriin): Suurin multipack-kehys 1 017 B (meta); MTU 247 → palat ≤ 240 B; MTU 23 → 20 B palat, kehykset ehjät.
  - todettu (ei rekisteriin): run_shot PB 20 s (vale-anturi): loki 210 riviä, vaiheet BREW + SOFT_RELEASE, paine ≥ 7 bar; PB 8 s hylätty lyhyenä; TS ei lokia.
  - todettu (ei rekisteriin): Regressio tuoreella /tmp/fw:llä (`timeout 600`, ei putkea): shot_test 78 PASS 0 failed; esiuutto, klamp (22), kuri, mcal, ohjevahti, phold, pskip_gate, psweep_mult, psweep, scale_rate, tray_guard, tray_total, turva_toimilaite, valmiustila (22), vkello_rise, vsweep 0 failed; turva_pika 1 failed — sama FAIL ilman muutoksia (git stash -perustaso), ennestään punainen (throttle_set_run).
  - todettu (ei rekisteriin): `build_set.py` globbaa `pico/*.py` → brew_logger.py tulee flash-settiin automaattisesti.
- 5.10.2026 — EXPRESSO-SHOTTEST-FEIKKI valmis, commit 71abe15: `testit/shot_test.py` make_brew_data saa eu_coast_s/eu_coast_fast_s/eu_g_pre/eu_tau_pre ja eb_ff/eb_x/eb_g/eb_tau/eb_coast_s (classes.BrewData-oletukset), pre_infusion_method = brew_method = 0 (PI-polku, kuten ennen getattr-oletuksella). Tuore /tmp/fw: 76 PASS, RESULT: 0 failed.
  - Kolme pientä vikaa, commit f17afe8 (ei flashattu): (a) `load_settings` (pico/functions.py): yli SETPOINT_MAX_C:n brew-/steam-lämpötila pitää oletuksensa ja muu tiedosto (myös wmax) latautuu — ennen ValueError poisti koko settings.txt:n; uusi tarkistus shot_test.py:ssä ("over-limit setpoint keeps the file and wmax"), ilman korjausta FAIL (wmax 0.0); (b) main.py:n vanhentunut kommentti "weight limits are deliberately not persisted" korjattu; (c) `pressure_len_run`:n käyttämättömät `venting`/`vents` poistettu.
  - ratkennut (Avoimet asiat): shot_test.py vanhentunut (eu_g_pre puuttuu feikistä) — Valmis commitilla 71abe15: testit/shot_test.py:n make_brew_data päivitetty nykyisiin classes.BrewData-oletuksiin (76 PASS).
  - ratkennut (Viat): `pressure_len_run`:ssa on käyttämättömät muuttujat `venting` ja `vents`. — korjattu f17afe8
  - ratkennut (Viat): `settings.txt`, jossa brew- tai steam-lämpötila on yli 150 °C, kaataa `load_settings`:n `ValueError`-haaraan, joka pois… — korjattu f17afe8 (shot_test-tarkistus; ei flashattu)
  - ratkennut (Viat): `main.py`:n kommentti "weight limits are deliberately not persisted" on vanhentunut — painorajat tallennetaan `devsafe1… — korjattu f17afe8
  - ratkennut (Viat): `testit/shot_test.py` kaatuu HEADillä `AttributeError: 'BrewData' object has no attribute 'eu_g_pre'` — vanhentunut fei… — korjattu 71abe15 (todennettu: 76 PASS, 0 failed)
  - todettu (ei rekisteriin): Smoket tuoreella /tmp/fw:llä f17afe8:n jälkeen (`timeout 600`, ei putkea): shot_test, valmiustila, esiuutto, kuri, mcal, psweep_mult, turva_toimilaite, tray_guard, phold, klamp 0 failed; turva_pika 1 failed ("ei suoria testiajokutsuja dev_run:n ohi — throttle_set_run", ennestään punainen).
  - todettu (ei rekisteriin): shot_test.py pim:1-polulla (pre_infusion_phased) jumittuu: testin laitosmalli siirtää kelloa vain sleep-kutsuissa, ja pre_infusion_phased odottaa ticks_us-silmukassa → 600 s aikaraja (RC=124). Lisäksi se kutsuu `gc.mem_free()`, jota CPythonissa ei ole. Vaiheistetun polun kattaa esiuutto_smoke.
- 5.10.2026 — käyttäjän uusi pyyntö (/pura-kysymyksen vastauksena, /rd): **EXPRESSO-VALMIUSTILA** — keitin 30 min käyttämättä (ei kytkintä, ei äppimuutosta) → lämpötilatavoite 90 °C; mikä tahansa kytkin palauttaa uuttolämmön. Syy (käyttäjä): pitkän levon jälkeen pumppu käy kauan ennen kuin vettä tulee; käyttäjän epäily: kattilan paine työntää vettä hiljalleen pumpun läpi takaisin säiliöön.
  - Brief `Infra/iot/expresso/paketit/VALMIUSTILA.brief.md` (vaatimustarkistin ok: "VAATIMUS: ei koske"), ajaja toteuttaja-sonnet (käyttäjä hyväksyi ketjun; agy-reitti ei toimi expresso-briefeille, HISTORIA:384). Toteuttaja 905 s, 87 465 tokenia, 30 työkalukutsua.
  - Commit **f5a67c3** (juurirepo, ei pushattu ennen pakkausta): `BrewData.note_activity(now, reason)` / `update_standby(now)` (salpa: ticks_ms-kierto ei pura), `get_target_temperature` IDLE → `min(brew, 90)` valmiustilassa; main.py: kytkin päällä → activity, `update_standby` ennen `thermostat.run()`ia, activity uutto-/tshot-/kuumavesihaaran paluussa; commands.py: `updated` → `note_activity('app')` (BLE ja sarja), uusi RAM-komento `stby:<min 0–240>` (0 = pois) ja `stby:on` (pakottaa heti, laitetestiin), tulostaa `STBY timeout_min= standby= temp=`; lokirivit `STBY_ON idle_s= target=` ja `STBY_OFF reason=switch|app|tshot`. PICO-HALLINTA.md §4 loppuun stby-kappale. Uusi `testit/valmiustila_smoke.py` (203 riviä, 22 PASS; ilman korjausta 10 failed). Feikit päivitetty: kuri_smoke, turva_pika_smoke, shot_test (standby-kentät).
  - Ei flashattu, ei laiteajoa, MANIFEST.json ei päivitetty.
  - viat (ratkaistu, ei rekisteriin): ei uusia
  - todettu (ei rekisteriin): Pääistunto ajoi itse tuoreella /tmp/fw-kopiolla (`timeout 600`, ei putkea): valmiustila, esiuutto, kuri, mcal, psweep_mult, turva_toimilaite, tray_guard, phold rc=0; turva_pika rc=1 (ennestään punainen: "ei suoria testiajokutsuja dev_run:n ohi — throttle_set_run", `throttle_set_run` main.py:ssä jo ennen muutosta). Toteuttajan mukaan muut smoket vihreitä, shot_test punainen ennestään (eu_g_pre).
  - todettu (ei rekisteriin): `get_target_temperature`ia kutsuvat vain Thermostat ja relayguard `_norise` (toteuttajan raportti); valmiustilan matalampi tavoite ei laukaise noriseä.
  - todettu (ei rekisteriin): Thermostat.run käyttää `brew_data.get_target_temperature()` (classes.py ~1357) → valmiustila vaikuttaa vain IDLE-tilaan.
- 29.9.2026 — EXPRESSO-UUTTO-8BAR: kaikkien 12 uuttolokin analyysi (siirtaja-sonnet, `/pura infra expresso`,
  ARVIO 6/6; sa päällä). Ei repon muutoksia: analyysiskripti vain scratchpadissa, ei repoon.
  - Aineisto: `testit/uutto8-20260928-{a,a2,a3,a4,a5,b,b2,c,c2,c3,d1-7bar,d2-9bar}-bim*.log` (12 × `tshot:20`,
    esiuutto 2,5 bar 6 s + uutto 8 bar, pim:1). Oikeista kahviuutoista ei lokia: EXPRESSO-UUTTOLOKI tekemättä,
    `pico_dev.py capture` kaappaa vain kehitysajoissa (PICO-HALLINTA.md luku 4); ainoat kokonaiset uuttolokit ovat nämä 12.
  - Kaikki 12 ajoa kestivät täydet 20 s (viimeinen näyte 19,6–19,9 s); 8 barin vaihe alkoi 7,7–12,1 s kohdalla.
  - Firmware per ajo (lokien lisäyscommitit): a–c, a2–c2, a3 = setti 20260928-uutto8a (e0fb94f); a4–a5 = kuri4
    (6381fe8); c3 ja d1 lisätty kuri6-korjauksen commitissa efed272 → kuri5 vai kuri6 ei kirjattu; d2 = kuri6 (66ae5a2).
    Uuton säätökoodi sama kaikissa: `git diff e0fb94f 66ae5a2 -- pico/functions.py` muuttaa vain `throttle_warmup_run`/
    `throttle_set_run` ja lisää `brew_data.mains_T_us`-tallennuksen `pre_infusion_phased`/`_eu_end`:iin.
  - Lokirivit: EU = t_ms p sp rele d vaihe p5= … w= f= (`pico/functions.py:621`); bim:0:n TS = t p sp on duty
    window_peak weight_a weight_b … (`pico/functions.py:981`). `w` = kaukalon vaaka.
  - Ajo b (`uutto8-20260928-b-bim1.log`, uutto8a) purettiin aikajanaksi, paineen kuvaaja piirrettiin (inline) ja vaaka
    tarkistettiin. Esiuutto nousi 17,3 bar/s (a 5,6; a2 9,9); EU_CUT 353 ms p 1,33 pred 3,05; EU_COAST peak 4,67
    (näyte max 4,82, over 2,17); EU_HOLD 2423 ms (wait 1739 ms); esiuuton pito saha 2,1–3,1, ka 2,545 sd 0,283, 22 iskua.
    Uutto EB_START 8442 ms, 27,5 bar/s, EB_CUT 8582 ms 5,11 bar pred 9,08, EB_COAST peak 9,31 (max 9,50, over 1,32),
    EB_HOLD 9127 ms; pito saha 7,3–9,3, ka 8,19 sd 0,54, 27 iskua, need 0,037. GUARD_TRIP tempstale bar 8,5 temp 102,33.
    VKELLO lock=0 koko ajon (liian vähän iskuja). Kaukalo 548,8 → 551,2 g (+2,4 g; esiuutossa 0 ± 0,5, 8 barissa ~0,2 g/s).
  - Syy b:n hyppyyn: kuristin lähes kiinni (rekisterin UUTTO-8BAR-taulu: a, b tarve 0,04), ei firmware — samalla
    uutto8a:lla a2/b2 esiuuton huiput 1,47/2,26. Miksi b nousi 3× a:ta nopeammin samalla kuristimella: ei selvitetty
    (arvaus: vähemmän ilmaa 1. ajon jälkeen).
  - Käyttäjän hypoteesi "säiliön täyttö": ei — paine 8 bar ja pumppu ~4 % → suljettu tie; 49 iskua vastaa 2,4 g:aa
    vaa'alla. Vettä 20 s:ssa: a 4,3, b 2,4, c 1,7, a2 27,2 g. Kaukalo kasvoi ajojen välissä a→b +5,1 g, b→c +8,8 g
    (arvaus: lopun purku `soft release time: 5.0`, todentamatta).
  - Vähintään 20 g ajot (bim:1 a2, a3, a4, a5, b2, d1, d2): 8 barin pito ka 7,96–8,04; 0,5 s liukuvan ka:n sd
    0,07–0,13; min–max 7,66–8,27; 100 % ajasta 8 ± 0,5 sisällä; raaka 100 ms sd 0,18–0,39; nousun huippu 8,20–8,89
    (ylitys +0,2…+0,9); esiuutto ka 2,47–2,57; virtaus 1,4–2,9 g/s. bim:0 c3 (41,6 g): 7,10–8,84, sd 0,37, 80 % sisällä.
    c2 19,6 g (juuri alle rajan). Uusi säädin 3–5× vakaampi. Kaikki vettä kuristimen läpi, ei kahvia.
  - Oma virhe (prosessi, korjattu samassa keskustelussa): pääistunto väitti kaikkien 12 uuton pysähtyneen 8–12 s
    kohdalla — väärin, 8–12 s oli vain 8 barin osuus; kaikki ajoivat 20 s. Korjaus kerrottiin käyttäjälle seuraavassa
    vastauksessa. Ratkennut, joten ei rekisterin Viat-lukuun (elinkaarisääntö; rekisteri katossa).
  - Pakkauksen valinta: ks. rekisterin Päätökset 29.9.2026 (seuraava paketti EXPRESSO-SHOTTEST-FEIKKI).
- 28.9.2026 — EXPRESSO-TEMPSTALE-JA-OLETUS jatkui (osa 1, tempstale-korjaus): vertailu pilkottu
  luku vs. toinen ydin tehty → **valittu toinen ydin (RP2350 core 1, `_thread`)**; pilkottu luku
  (c658f99) poistettu (`git apply -R` c658f99:n `pico/functions.py`- ja `pico/classes.py`-
  hunkeille). Koodi työpuussa, EI flashattu, EI laiteajoa, EI committia tässä pakkauksessa.
  - `pico/lib/adafruit_max31865.py` (CRLF säilytetty, `newline=''`): `rtd_start/rtd_convert/
    rtd_result` allokoimattomiksi (puskurit `_na/_nw/_nr1/_nr2` `__init__`:ssä,
    `_n_read_u8/_n_write_u8` suoraan chip_select + spi.write/readinto).
  - `pico/classes.py`: vakiot `TEMP_C1_*` (BIAS 10, CONV 65, EVERY 250 ms, STOP 300 ms, taulukko
    raw 4096..16384 askel 256, 2..200 °C) ja `C1_*`-kentät; `TemperatureSensor.c1_start(utime)`
    (säie kerran bootissa, stack 6144, `TEMP_C1 ready`/`TEMP_C1 none: …`),
    `c1_active/c1_on/c1_off/c1_temperature/c1_ms/c1_log`, `_c1_main` (`micropython.heap_lock`
    ytimellä 1; virhe → `C1_ERR=1`, säie loppuu, ydin 0 lukee taas), `_c1_loop` (vain kokonaisluvut,
    7 lukeman keskiarvo 0,01 °C, 6 peräkkäistä virhettä → 200 °C kuten `read_temperature`,
    IDLE/WANT-kättely: IDLE=0 ennen WANT-luentaa). `read_temperature` palauttaa ytimen 1 arvon, kun
    c1 aktiivinen. `BrewData.boiler_temperature` ja `boiler_temperature_ms` propertyiksi (uuton
    aikana ytimen 1 lukema ja sen hetki → relayguard näkee tuoreen ilman pumppusilmukan työtä);
    `get_boiler_temperature` ei lue SPI:tä c1:n aikana.
  - `pico/functions.py` `run_shot`: `tsens.c1_on()` ennen try:tä, `tsens.c1_off()` finallyssä
    releiden jälkeen; `<label>_END`-riveille loppuun `c1_n= c1_gap_ms= c1_bad= c1_err=` (tai
    `c1_n=-1`).
  - `pico/main.py`: `temperature_sensor.c1_start(utime)` anturin luonnin jälkeen.
  - Testit: `esiuutto_smoke.py` Max31865-askelmalli → `C1Model` (lukema 80 ms `c1_on`:n jälkeen,
    sitten 250 ms välein, ei kuluta silmukan aikaa); heat_age-hook lukee `c1_ms()`:n. `shot_test.py`
    ja `turva_toimilaite_smoke.py` feikeille c1-metodit.
  - Diagnoosi (scratchpad, `Max31865.COST_US` vaihdellen): syy tapaukselle 10 löytyi — smoken
    `Utime.ticks_us` lisää 20 µs/kutsu, joten jo "ilmainen" askel siirtää kohinatoteumaa; kaikki
    pilkotut variantit nostivat tapauksen 14 piikkiä 0,61–0,625:een → pilkottu luku heikentää
    pumpun ohjausta systemaattisesti. MicroPython v1.28.0 lähteestä varmistettu: ajastetut
    takaisinkutsut vain pääsäikeessä, `heap_lock` ytimellä 1 ei lukitse ydintä 0, oletuspino 4096.
  - Uuden koodin smoke 28.9.2026: `esiuutto_smoke` RESULT 0 failed (tapaus 10 +0,029, 14 =
    perustaso), `turva_toimilaite_smoke`, `kuri_smoke`, `klamp_smoke` 0 failed. `shot_test.py`
    kaatuu `AttributeError: 'BrewData' object has no attribute 'eu_g_pre'` — sama HEADillä
    (vanhentunut feikki, ei tämän muutoksen).
  - Vika V-097 kirjattu skooppiin `claude siirto` (commit 0d5a7d0): jumi ilman ilmoitusta + autopack
    ei pakannut.
- 28.9.2026 — EXPRESSO-TEMPSTALE-JA-OLETUS aloitettu isännällä (osa 1, tempstale-korjaus), KESKEN:
  smoke 2 FAIL. Ei flashia, ei laiteajoa, ei committia.
  - Juurisyy koodista: `run_shot` sammuttaa lämmittimen alussa (`functions.py` `run_shot`
    `RELAY_HEATER.value(0)`), `main`-silmukka ei lue lämpötilaa `run_shot`in aikana,
    `pre_infusion_phased` (vaiheet 1–4) ei lue sitä lainkaan → vaiheen 3 ensimmäinen lämmitinpulssi
    (EB_HEAT 100/50 ms) osuu yli 10 s vanhaan lukemaan (relayguard `HEATER_TEMP_STALE_MS` 10000) ja
    on estetty koko uuton ajan. bim:0 (vanha uuttosilmukka, lukee 2 s välein) estetty vain
    ensimmäiset 2 s. Vahti ei lukitu pysyvästi (block poistuu poll():ssa, kun lukema on tuore).
  - `pico/lib/adafruit_max31865.py`: uudet `rtd_start()`/`rtd_convert()`/`rtd_result()` (sama luku
    kuin `read_rtd` ilman `time.sleep`iä) ja `temperature_from_rtd(rtd)`; `temperature`-ominaisuus
    käyttää sitä (sama laskenta). Tiedosto on CRLF — säilytetty.
  - `pico/classes.py`: `TEMP_STEP_BIAS_MS` 12, `TEMP_STEP_CONV_MS` 70, `TEMP_STEP_EVERY_MS` 2000,
    `TEMP_STEP_LOST_MS` 1000; `TemperatureSensor.step_reset`/`step_due(utime, now_ms)`/
    `step(utime, now_ms)`/`_average` (`read_temperature` käyttää `_average`a ja nollaa
    askeltilan); 6 peräkkäistä virhelukua → 200 kuten ennen. `BrewData.step_boiler_temperature(now_ms)`
    asettaa `boiler_temperature(_ms)`.
  - `pico/functions.py`: `EU_TEMP_ROOM_US` 5000; `pre_infusion_phased` tekee yhden askeleen, kun
    seuraavaan tapahtumaan (slot/pend_on) on > 5 ms, ennen asyncio-vuoroa; `EU_STALL` sec=t;
    `EU_VV`- ja `EB_VV`-riveille `t_n` (valmiit lukemat) ja `t_max_us` (pisin askel). Vanha
    uuttosilmukka lukee lämpötilan ennen silmukkaa vain, jos lukema on ≥ 2 s vanha (pim:1:n jälkeen
    ei lue → A/B ennallaan).
  - `testit/esiuutto_smoke.py`: Max31865-anturimalli (askelten hinta start 2000, convert 1000,
    result 700 µs — arvio, ei mitattu), `temp_sensor()`, BrewData-feikki käyttää oikeaa
    `classes.TemperatureSensor`ia; heater.hook kirjaa lukeman iän jokaisella lämmittimen
    päällekytkennällä (`bd.heat_age`). Tapausta 22 (ikä ≤ 3 s bim:1/bim:0, virheen toisto ilman
    askelluskoodia) ei vielä kirjoitettu.
  - Mittaus: smoke ennen muutoksia 119 OK, RESULT 0 failed, 76 s; uusi koodi ilman anturimallia
    identtinen perustasoon; anturimallin kanssa RESULT 2 failed (tapaukset 10 ja 14, ks. REKISTERI.md
    "Todettu 28.9.2026 — EXPRESSO-TEMPSTALE-JA-OLETUS") — syy selvittämättä.
  - Käyttäjän uusi tilaus (TILAUS-N, `KAYTTAJAN-TIEDOT.md` luku 2d): lämmitystarve lasketaan
    virtauksesta (säiliössä vaihtuneesta vedestä), ei lämpötila-anturista — avattu omaksi paketiksi
    EXPRESSO-LAMMITYS-VIRTAUS, ei osa tätä korjausta.
  - työkaluvika, korjattu heti: Python `open().read()`/`write()` muutti CRLF-tiedoston
    `pico/lib/adafruit_max31865.py` rivinvaihdot LF:ksi (git diff 486 riviä); palautettu CRLF:ksi
    ennen committia (diff 21+/1−). Sääntö: CRLF-tiedostoja muokataan `newline=''`-tilassa.
- 28.9.2026 — EXPRESSO-UUTTO-8BAR laiteajo tehty (setti 20260928-uutto8a, kuri1–kuri6, kaikki RESTORE_OK +
  VERIFIED 19/19, repon `pico/MANIFEST.json` = kuri6). Commitit e0fb94f, 6381fe8, efed272, 66ae5a2, fe8eddc.
  - Uusi komento `kuri:<n>` (TILAUS-M; `pico/commands.py`, `pico/main.py`, `pico/functions.py`
    `throttle_set_run`): uuttonappi ajaa pumppua n iskua/s (1–50) ilman paineensäätöä, `kuri:0` = normaali uutto,
    RAM only. kuri6 (efed272) lukitsee kytkennän verkon vaiheeseen Verkkokellolla (täysi sykli kunnes
    2,5·sd < 5 ms, sitten päätös kellon reuna + 8 600 us = `KURI_OFF_US` = `EU_OFF_US` − 5000), yksi raskas työ
    (iq_close / gc / asyncio-vuoro) per ajallaan ollut päätös (`KURI_SKIP_US` 2 ms), purkusykli (`_mcal_vent`)
    alussa ja lopussa; `KURI_END` kirjaa `lock_ms`, `win`, `learned`, `err`, `lmax`. Laitteella err=0, lmax
    5,0–5,9 ms, 25,0 iskua/s — käyttäjä: "Tasainen".
  - `BrewData.get_pressure()` (`pico/classes.py`) juoksevalla summalla listan sijaan (kuri3) — korjaa
    MemoryError-kaatumisen (vika 14:n välitön syy); `get_pressure_*`-pitkäversio (`classes.py:1262`) käyttää
    yhä listaa. `pico_dev.py restore <set> [seconds]` oletus nostettu 420 s:iin (kuri1 ylitti 300 s ~1 kt/s).
    `EU_END2`/`EB_END2` tallentavat `brew_data.mains_T_us` (opittu verkkojakso).
  - `testit/kuri_smoke.py` uudelleen esiuutto_smoke-harnessilla (virtuaaliaika, nollaylitys-SSR, keruu 15–28 ms,
    varaukset): 31 tarkistusta, 0 failed; esiuutto/klamp/tray_guard/turva_toimilaite/vkello_rise smoke 0 failed.
  - `KAYTTAJAN-TIEDOT.md` luku 2c: TILAUS-M lisätty loppuun.
  - 8 barin laiteajojen tulokset (a–d2, kaikki pim:1): taulukko ja tulkinta `REKISTERI.md` luvussa "Todettu
    27.–28.9.2026 — EXPRESSO-UUTTO-8BAR". `GUARD_TRIP heater reason=tempstale` esiintyi kaikissa bim:1-ajoissa ja
    c2:ssa (bim:0) sekä jo esiuutossa a4:llä — avoin, seuraava paketti EXPRESSO-TEMPSTALE-JA-OLETUS.
  - oma virhe, korjattu samassa sessiossa: kuri5:n hallittu roskienkeruu joka 15. jakso lisäsi myöhästymiä
    (pääistunnon oma korjaus pahensi vikaa) — korjattu kuri6:ssa (phase-lukko + purkusykli).
  - prosessivika, avoin (käyttäjän kirjaama, klo ~9.20): kuristimen säätöohjetta ei noudatettu — ohje annettiin
    kierroksina TILAUS-M:n vastaisesti (ajo d). Sääntö: kuristimen asento aina paineena `kuri:1`-syklillä.
  - prosessivika, avoin (käyttäjän kirjaama "toinen virhe", klo ~10.10): pääistunto käynnisti pumpun etänä
    (a4) kysymättä ja ilmoittamatta. Sääntö: testiuutot etänä vain ilmoitettuna ja käyttäjän kuitattua valmiuden.
  - prosessivika, avoin (käyttäjän kirjaama "kolmas virhe", klo ~12.12): pääistunto pysäytti lokin tallennuksen
    kesken käyttäjän omaa säätöajoa, ajon loppu jäi tallentumatta, tarkistusajo tarvittiin.
  - työkaluvika, avoin: kaksi `pico_dev.py capture` -prosessia päällekkäin (vanha jatkoi TaskStopin jälkeen) →
    toinen ei saanut dataa, laturi kytkeytyi kesken; TaskStop ei aina lopeta python-lasta.
  - Päätökset: kuri-kytkentä toteutettiin Verkkokellolla eikä PWM-laitteistolla (PWM olisi vaatinut relayguardin
    muutoksen eikä silti tietäisi nollakohdan vaihetta); `PCAP_OVER_BAR` 11,0 ei muutettu (vika 15).
- 27.–28.9.2026 — EXPRESSO-UUTTO-8BAR isännällä (TILAUS-K vaiheet 3–4, commit 75b8a62, ei flashattu, ei laiteajoa): brief `paketit/UUTTO-8BAR.brief.md` (vaatimukset.mjs ok), toteutti ali-agentti (Opus, 46 min), pääistunto ajoi smoken itse: `timeout 900 python3 testit/esiuutto_smoke.py` → RC=0, "RESULT: 0 failed". Commit 75b8a62: `pico/{classes,commands,functions,main,verkkokello}.py`, `testit/{esiuutto_analyysi,esiuutto_smoke,uutto8_sovitus}.py`, `paketit/UUTTO-8BAR.brief.md`.
  - `pre_infusion_phased(..., brew=False)`: kun esiuuton pito päättyy (`end_t`), sama silmukka jatkaa vaiheeseen 3 (nousu `get_brew_pressure()`:en, täysi sykli → katkaisu ennusteesta → ramppi) ja 4 (pito delta-sigmalla ja PI(D):llä kunnes `keep_running()` epätosi). Kello, delta-sigma, vuoronvaraus, myöhästymisvahti ja keruu jatkuvat katkeamatta; lämmitin pulssitetaan kuten vanhassa uutossa, `set_pump_ratio` 1 s välein; kattilan lämpötilaa ei lueta vaiheissa 3–4 (MAX31865 blokkaa ≥ 75 ms), vaan kerran uuton jälkeen. Virtaustila → vanha silmukka.
  - Valinta: RAM `bim:<0|1>` (`pico/commands.py`, oletus 0, TS_START tulostaa `bim=`); vaiheet 3–4 vain kun pim=1, esiuutto päällä, virtaustila pois ja bim=1 (A/B-vertailu bim:0 vanhaan uuttoon).
  - Uuton opitut arvot omina settings-avaimina `eb_ff`, `eb_x`, `eb_g`, `eb_tau`, `eb_coast_s`; uuton ff = tämän ajon esiuuton tarve × (8/2,5)^0,8, kunnes `eb_x` opittu. `EB_RAMP_BAR_PER_S` 4, `EB_KI_X` 3.
  - Lokit: EU-rivit vaihesarakkeella 3/4; esiuuton EU_END/EU_END2/EU_VV siirtymässä jonosta 20 ms välein (≤ 165 merkkiä); uuton loppuun `EB_END`-rivit, vanha `<label>_END` tulostuu myös. `testit/esiuutto_analyysi.py` lukee vaiheet 3–4 ja TS-uuton A/B:tä varten. `verkkokello.py` `gate_reset()`. Uusi `testit/uutto8_sovitus.py` (8 barin mallin sovitus), smoke-tapaukset 16–21.
  - todettu (ei rekisteriin): 8 barin malli lokeista esiuutto-20260924-b…e, 20260925-a…c, 20260926-b (TS-nousu ja -pito): nousu 2,5→7,2 bar mediaani 9,5 bar/s (2,9…21, 32 paria); jousto vakio + kaasu/p_abs², c0 0,03 (rms 2,91 vs. puhdas kaasu 3,30); vuoto ~p^0,8 (pidon keskipaineen rms 0,19 bar); malli toistaa vanhan uuton ~1 bar pudotukset (min 6,1–6,6, laite 6,5–6,8); isku 8 barissa 0,34–0,93 (mediaani 0,76) bar, tarve 8 barissa 0,26–1,01; viivettä ei sovitettu (data ei riitä) → TILAUS-I 37–41 ms.
  - todettu (ei rekisteriin): Kello: täysi nousu opettaa harhaisesti (−0,6…−1,1 ms nousunopeudesta riippuen, ajojen välinen hajonta ~850 us); alle 2 bar/s nousevat ikkunat harha +8 / +128 us. Siksi vaiheissa 3–4 opettaa vain ikkuna, jonka keskipaine nousi < `EB_CLK_RATE` 2 bar/s: täysi nousu gate=−1, rampin loppu lukitsee ennen pitoa.
  - todettu (ei rekisteriin): Smoke uusi vs. vanha uutto (bim:0), mallin todellinen paine 100 ms: 16 ylitys +0,12/+0,16 vs +0,74/+1,04; pidon 1. s pudotus ka −0,29 vs −0,57; pito 2–5 s −0,03…−0,02 vs −0,15…0; 17 kuristimen kääntö 0,3→0,6→0,2 kaistalle 0,60/0,69 s vs 2,3/2,6 s; 18 kellon sd pidon alussa ≤ 1061 us, 10 ms tauot 100 % (ilman vaiheiden 3–4 oppia 9,7–13 ms, 20 ms tauot 70–83 %); 19 vv=1 late 0 (vv=0 4–13); 20 esiuuton arvot ennallaan, 2. ajo käyttää eb_*:ia; 21 siirtymärivit 20 ms välein. Tapaukset 1–15 tavulleen HEADin tuloste. Muut smoket rc=0 (klamp, mcal, ohjevahti, phold, pskip_gate, psweep_mult, psweep, scale_rate, tray_guard, tray_total, turva_pika, turva_toimilaite, vkello_rise, vsweep, verkkokello_holdout) — ali-agentin raportti.
- 27.9.2026 — EXPRESSO-ESIUUTTO-HYVAKSYNTA ajettu (autojatkolla, `--autojatko`): flash `20260927-rampinloppu1`
  (pohja vuoronvaraus3 + rampin loppu 651afec), `restore` → RESTORE_OK 4 min 51 s, `verify` → VERIFIED 19/19
  (repon MANIFEST päivitetty käsin, 2772ae2); `pim:1`, `pit:6` CMD_OK; `hold 5` × 4 (at–aw) klo 07.49–08.00.
  Tulos: ylitys 0,08–0,32 kaikissa (< yksi isku), pito kaistalla 2,45–2,55 — **käyttäjä hyväksyi esiuuton**,
  avaa käyttöönottoketjun kohdan (2) EXPRESSO-UUTTO-8BAR. Kellon lukko pienellä tarpeella: käyttäjä valitsi
  (a) vapaa kello matalan tarpeen pidossa, lukitus vaiheen 3 nousussa; hylätty (b) laitemittaus ensin. 8 barin
  laiteajot sallittu jälleen (2,5 bar -rajoitus 26.9.2026 poistettu; muisti `expresso-tests-only-25bar-hold`
  päivitetty). Commitit 2772ae2 (MANIFEST.json), 25ca132 (REKISTERI Viat), b17c131 (REKISTERI, VAIHESEURANTA,
  testilokit). Yksityiskohdat: `paketit/VAIHESEURANTA.md` luku "Laitteella 27.9.2026 klo 07.49–08.00
  (rampinloppu1 …) — hyväksytty".
  - todettu (ei rekisteriin): pidon myöhäinen alku ei ole säädintä — vaihe 1 täydellä teholla 2,2–5,7 s
    (as 0,6 s), vettä kaukaloon jo täytössä 3–6 g (as 0 g); lämmin kuristin samassa asennossa päästää enemmän
    (tarve 0,13–0,18 vs ao–as 0,02–0,09); kattila BLE 96 °C klo 07.46.
  - uusi vika, avoin: EXPRESSO-TYPEC-JUMI — av:n kaksi ensimmäistä yritystä `PICO_NOT_ON_USB`, Type-C-tilakone
    jumissa au:n laturin palautuksen jälkeen (`Type-C Sink (powered) connected` ilman edeltävää disconnectia),
    OTG-uudelleenkytkentä (`otg_switch` 0→1) purki. Korjausehdotus: `ChargerOff.__enter__` OTG-uudelleenkytkentä.
  - uusi vika, avoin (prosessi): `restore` ajettiin ulkoisella `timeout 300`:lla, vaikka työkalun oma odotus on
    300 s + laturisykli — katkaisu ohitti `ChargerOff.__exit__`:n ja laturi jäi pois (palautettu käsin). Sääntö:
    ulompi aikaraja ≥ työkalun oma raja + 60 s.
- 27.9.2026 — EXPRESSO-ESIUUTTO-RAMPIN-LOPPU ajettu (autojatkolla, autovaihto): isännän osa tehty, laiteosa (flash + hyväksyntäajo) ei — vaatii käyttäjän. Commitit 651afec (fix) ja 8e93718 (docs). Yksityiskohdat: `paketit/VAIHESEURANTA.md` luku "Rampin loppu (EXPRESSO-ESIUUTTO-RAMPIN-LOPPU, 27.9.2026)".
  - 651afec `pico/functions.py`: (1) `EU_RAMP_DONE`: ramppi valmis, kun p5 ≥ tavoite − 0,1 jälkinousun ikkunan jälkeen; (2) pito alkaa vasta kaistalla tavoite ± 0,1 myös ylhäältä (menetelmäohje: yliampuma ei aloita laskuria), varalla `EU_HOLD_WAIT_MS` 2000, EU_HOLD kirjaa `wait_ms`; (3) kaasujousto rampin vahvistukseen: kun p5 on käynyt ≥ `EU_ABOVE_BAR` 0,3 rampin yllä, myötäkytkentä ja D-raja G_katkaisu × ((1 + sp)/(1 + p_katkaisu))² (`EU_GAS_ABS` 1,0, `EU_GAS_EXP` 2). `testit/esiuutto_smoke.py`: Plant `gas_bar` (iskun vaikutus ∝ absoluuttinen paine²) ja tapaus 15 (ao–as-malli, 12 siementä × 2 ajoa).
  - 8e93718 docs: `paketit/VAIHESEURANTA.md` luku "Rampin loppu (EXPRESSO-ESIUUTTO-RAMPIN-LOPPU, 27.9.2026)" — mekanismi, malli, taulukko vanha → uusi, kellon lukon analyysi.
- 26.–27.9.2026 — EXPRESSO-ESIUUTTO-VUORONVARAUS ajettu. Commitit 0681aa3, 02a72d9, 899ab33 (koodi) ja 06d0746 (laitelokit an–as, MANIFEST.json, VAIHESEURANTA.md). Yksityiskohdat ja taulukko: `paketit/VAIHESEURANTA.md` luku "Vuoronvaraus (EXPRESSO-ESIUUTTO-VUORONVARAUS, 26.–27.9.2026)".
  - Korjaus `pico/functions.py` pre_infusion_phased, `euv:1` oletus (`euv:0` = vanha, RAM only, uusi komento `pico/commands.py`): vaiheessa 2 asyncio-vuoro vain, kun rele on pois ja seuraava jakso on tauko; hallittu `gc.collect()` 300 ms välein samassa kohdassa (`EU_GC_MS`); kellon ikkunan sulku (`iq_close`) vasta, kun seuraavaan päätöskohtaan on ≥ 12 ms (`EU_IQ_CLOSE_US`), jos rele on päällä.
  - Mittausrivit: `EU_STALL t_ms sec(y/k/s/l) us rel [task]` (> 10 ms), `EU_GC`, `EU_VV`; `pico/main.py`: `brew_data.tbusy` + `task_busy()` tehtäville ble/ser/scale/wd. EU_END jaettu riveihin `EU_END`/`EU_END2`/`EU_VV` (≤ 255 merkkiä, 20 ms väli); smoke `field()` lukee kaikki prefiksin rivit.
  - `testit/esiuutto_smoke.py`: Gc-malli (keko täynnä 0,5–0,8 s, keruu 15–28 ms), `iq_close`-hinta, tapaus 3 jaettu vv=0/vv=1, uusi tapaus 14 (uuttoasento + keruu + varaukset, vanha vs. uusi). esiuutto_smoke 0 failed; 11 muuta functions.py-smokea 0 failed.
  - Laitteella: setit 20260926-vuoronvaraus1 (an), vuoronvaraus2 (ao, ap), 20260927-vuoronvaraus3 (aq, ar, as); jokainen RESTORE_OK n=19 ja VERIFIED 19/19; `pim:1 pit:6 wmax:720 wrise:250 euv` CMD_OK jokaisen flashin jälkeen.
  - ratkennut (Avoimet asiat): Laitteen tehtäväajoitusten (asyncio-pysähdykset 5–15 ms) mittaus — valmis: syy automaattinen roskienkeruu (an, keko täynnä 0,5–0,8 s:ssa, keruu 15–28 ms), toinen lähde `iq_close` + VKELLO 10–11 ms; hallittu keruu 15–16 ms.
  - ratkennut (Avoimet asiat): EU_END-rivi ≤ 255 merkkiä — valmis 0681aa3, todennettu laitteella an–as (rivit ehjiä).
  - todettu (ei rekisteriin): Tulokset (late/miss, ylitys, pidon sd, 2–5 s p5): al 3/6, 0,74, 0,28, 2,55; am 2/3, 0,82, 0,25, 2,49; an (euv:0) 4/6, 0,38, 0,25, 2,61; ao 0/0, 1,32, 0,27, 2,50; ap 1/0, 0,52, 0,19, 2,50; aq 0/1, 0,36, 0,17, 2,50; ar 0/1, 0,65, 0,21, 2,52; as 0/0, 0,60, 0,24, 2,43. vuoronvaraus3:lla ei yhtään EU_STALL-riviä `rel=1`; hallittu keruu 18–19/ajo, 15,1–16,0 ms.
  - todettu (ei rekisteriin): ao–as 7 h tauon jälkeen: kuristin al/am-asennossa mutta kylmä (vesi −0,7…2,4 g, tarve 0,05–0,09; al/am 4,9–5,8 g, 0,14). Kattila 101–103 °C puhelimen logcatin BLE-telemetriasta (`boiler_temperature`).
  - todettu (ei rekisteriin): Malli (smoke 14): vv=0 late 13–25, piikki ka +1,5…+1,9; vv=1 late 0, automaattisia keruita 0, piikki ka +0,52…+0,55, pidon p5 sd 0,23–0,24.
  - oma virhe, korjattu samassa sessiossa: `gc.mem_free()`-kutsun hinta (7,3 ms) arvioitiin mittaamatta ja kutsu tehtiin joka 100 ms, mikä vaati ylimääräisen flashin (vuoronvaraus2); korjaus 02a72d9.
- 26.9.2026 — EXPRESSO-ESIUUTTO-UUTTOASENTO ajettu (pääistunto): kahden osan iskumalli sovitettiin af:hen, säätimen korjaus, smoke-tapaus 13, flash ja 6 laiteajoa. Commitit 417ad93 (fix: functions.py, classes.py, esiuutto_smoke.py, VAIHESEURANTA.md), d93ca55 (test: lokit ah–ak + MANIFEST.json = setti 20260926-esiuasento1), 7e23b5e (test: lokit al–am). Yksityiskohdat VAIHESEURANTA.md luvut "Uuttoasennon korjaus (EXPRESSO-ESIUUTTO-UUTTOASENTO, 26.9.2026)" ja "Laitteella 26.9.2026 klo 22.3x–22.4x (esiuasento1 …)".
  - Korjaukset (417ad93): (1) `EU_KD_G` 0,3 (ramppi) ja `EU_KD_G_HOLD` 0,1 (pito): kd = min(KD, raja / g katkaisusta); (2) pidon tarve = toteutunut iskuosuus pidon 2 s:sta loppuun, ei u:n keskiarvo; EU_END kirjaa `u_mean` ja `kd`; (3) nopean nousun (rate ≥ 8 bar/s) jälkinousu opitaan erikseen: `eu_coast_fast_s` (classes.py, settings.txt), oletus `EU_COAST_FAST_S0` 0,2.
  - esiuutto_smoke.py: Plant `delta_f`/`tau_f` (nopea osa, oletus pois), tapaus 13 uuttoasento (8 siementä × 2 ajoa), tapaus 2 tarkistaa katkaisun nousunopeuden mukaisen luokan. esiuutto_smoke 0 failed (10,7 s), muut smoket 14/14. Vanha säädin (HEAD 5e2762a) kaatuu tapauksen 13 kaikkiin tarkistuksiin.
  - Laite: setti 20260926-esiuasento1 (build_set.py), `pico_dev.py restore` → RESTORE_OK n=19, `verify` → VERIFIED 19/19, `pim:1` ja `pit:6` CMD_OK; `hold 5` × 6 (ah–am), käyttäjän hyväksynnällä.
  - ratkennut (Avoimet asiat): Opittu tarve vinossa rajasyklissä (u:n −1…1 keskiarvo) → tau_obs ja seuraavan ajon ff väärin — Korjattu commitissa 417ad93 (pidon tarve = toteutunut iskuosuus pidon 2 s:sta loppuun, ei u:n keskiarvo) ja todennettu laitteella (al/am tarve 0,14 = iskuosuus 0,13).
  - todettu (ei rekisteriin): Malli (vanha säädin, 8 siementä): hidas 0,25 bar / tau 0,8 s + nopea 0,6 bar / 0,08 s, viive 20 ms toistaa af:n: g 18,6 (laite 17,9), pidon sd 0,59 (0,62), 300 ms jakso eli p:n autokorrelaatio 3 × 100 ms 0,54 (0,62), iskuosuus 0,20 (0,19). Yksiosainen malli antoi 400–500 ms jakson.
  - todettu (ei rekisteriin): Rajasykli on D-termin takaisinkytkentä: KD = 0 poisti jakson (0,54 → −0,05) ja opitun tarpeen vinouman (0,11 → 0,19); P:n puolitus ei vaikuttanut. o–z (g 9–12,5, tarve 0,02–0,09) eivät heiluneet, ag (g 12,95, tarve 0,14) heilui: pelkkä g ei erota tiloja.
  - todettu (ei rekisteriin): Jälkinousuaika laitteella: nopeat nousut (≥ 8 bar/s) 0,12–0,195 s (o–z, ag), hitaat 0,03–0,11 s; af katkaisi hitaan ae:n arvolla 0,054.
  - todettu (ei rekisteriin): Laite ah–am (taulukko VAIHESEURANTA.md): pidon sd 0,17–0,32 (af/ag 0,61–0,71), jakso −0,40…0,01 (0,62), huippu 3,3–3,9 (4,6–5,0), 2–5 s p5 2,47–2,55, opittu tarve = iskuosuus ±0,01, jälkinousu 0,43–0,89. ah–ak kuristin kiinnempänä (vesi 0,8–2,8 g, tarve 0,07–0,10); al–am kuristin avattu (vesi 5,2 / 4,5 g, tarve 0,14 = af/ag:n tila), nousu katkaisussa 8 bar/s (af/ag 12–17).
  - todettu (ei rekisteriin): Jäljelle jäänyt ylitys 0,74 / 0,82 (al/am) ja aj:n piikit 3,3–3,6 bar osuvat `late`-laskurin kasvuun ja ~120 ms lokiväliin: vuoronvaraus pitää releen päällä, +0,8–1,0 bar. Varaukset toistuvat ~3,0 s EU_STARTista (af 3,5/3,8, aj 3,0/4,0/6,4, al 3,0, am 3,0 s).
  - todettu (ei rekisteriin): EU_END-rivi 278 merkkiä (417ad93:n lisäkentät; aiemmin ≤ 243) katkesi siirrossa: alku 20–21 merkkiä puuttuu ja loppu toistuu yhtä pitkänä → siirtotiellä 256 tavun raja. `reason` puuttuu, arvot `max`:sta eteenpäin tallessa.
  - todettu (ei rekisteriin): Sivuhavainto: af:n EU_START coast_s 0,054, vaikka ae päättyi 0,074 (ad:n ero johtui resetistä); syy selvittämättä.
- 26.9.2026 — EXPRESSO-ESIUUTTO-HYVAKSYNTA ajettu 26.9.2026 klo 21.2x–21.4x (pääistunto, käyttäjä koneella): `pico_dev.py verify`, `cmd pim:1`, `cmd pit:6`, 4 × `pico_dev.py hold 5` (ad–ag). Tulos: esiuuttoa **ei hyväksytty**. Commit 3249a8a: lokit `testit/esiuutto-20260926-{ad..ag}-pim1.log` + VAIHESEURANTA.md-luku "Laitteella 26.9.2026 klo 21.3x (esiavoin1, EXPRESSO-ESIUUTTO-HYVAKSYNTA, `hold 5` × 4) — ei hyväksytty".
  - EXPRESSO-ESIUUTTO-UUTTOASENTO aloitettu isännällä (malli, ei koodimuutosta): commit 758ff8a, VAIHESEURANTA.md-luku "Korjauksen lähtötiedot uuttoasennolle". Kokeellinen P/I/D-skaalaus `pico/functions.py`:hin palautettu (`git checkout`), ei committia.
  - todettu (ei rekisteriin): Firmware laitteelta 26.9.2026 21.2x: `pico_dev.py verify pico/MANIFEST.json` → VERIFIED 19/19 = esiavoin1 (0028dff). Flashaus-rivin "laitteelta todentamatta" koskee nyt vain TURVA-TOIMILAITE- ja ANTURIUSKOTTAVUUS-toimintoja.
  - todettu (ei rekisteriin): `verify` tekee `machine.reset()`:n → `pim` palaa 0:aan (RAM). `pim:1` ja `pit:6` asetettiin uudelleen (CMD_OK); TS_START `6.0 s … pim=1` joka ajossa. `hold` ei itse aseta eikä tarkista pim:iä.
  - todettu (ei rekisteriin): Ajot (ac vertailuna; huippu = EU_END max): ac auki/lämmin tarve 0,60, pidon 0–2 s p5 2,46, sd 0,30, huippu 3,42, vesi 34 g | ad sama asento kylmä: tarve 0,14, 0–2 s **2,77**, over 0,60, vesi 6 g | ae: tarve 0,08, 0–2 s 2,53, 2–5 s 2,50, vesi 1 g | af uuttoasento: g 17,9, pidon sd **0,61**, huippu **4,61**, over 0,78 | ag: g 13,0, sd **0,71**, huippu **4,98**, over 1,42, 0–2 s 2,89.
  - todettu (ei rekisteriin): Lämmin/kylmä-tila todennettu laitteella: lämmin → kylmä (ad) ylittää ±0,1:n rajan (+0,27); edellisen tiedolla kylmä → kylmä (ae) osuu. Mallin kylmä-tila (0,15 / 2,2 s) aliarvioi: laitteen kylmä 0,08 / 4,6 s.
  - todettu (ei rekisteriin): Uuttoasennossa pito on ~300 ms rajasykli (p 1,6 → 3,4 → 2,2 bar; isku ~0,45 bar; pudotus ~9 bar/s). Pidon duty ka af 0,26 / ag 0,22, mutta `learned_ff_pre` 0,06 / 0,05 → opittu tarve ja tau_obs vinossa.
  - todettu (ei rekisteriin): Lämmin kuristin ei synny 2,5 barin ajoilla uuttoasennossa (~7 g/ajo, tarve ei nouse) → "6 s pito lämpimällä kuristimella" jäi ajamatta.
  - todettu (ei rekisteriin): Malli (`esiuutto_smoke`-Plant, viive 100 ms): delta 0,30–0,36, tau 0,7–1,0 s toistaa nousun ylityksen (over 0,67–1,16), ei pidon rajasykliä (sd 0,30–0,38); mallin g 9,6–10,5 vs laite 13–18. P/I/D × min(1, G_REF/g) (G_REF 8/4/2) ei muuttanut mallin pidon sd:tä. Lähde 758ff8a.
  - todettu (ei rekisteriin): Kaukalo: ad:n alussa 352 g (tyhjennetty ac:n jälkeen), ag:n lopussa 456 g.
- 26.9.2026 — EXPRESSO-POLUT-JUURI valmis (cddfcf4): `testit/scale_probe.py`, `testit/flow_rate_probe.py` ja `testit/shot_measure.py` johtavat pico_dev.py:n polun skriptin sijainnista (`__file__/..`, sama idiomi kuin klamp_smoke.py) kovakoodatun `/srv/work/Infra/iot/expresso` sijaan; pico_dev.py:n docstringin lähdepolku projektijuuren suhteelliseksi. Todennus: import ja PICO_DEV ratkeavat cwd:stä `/` tiedostoon Infra/iot/expresso/pico_dev.py (ei testit/-kopioon), py_compile 5/5, ohjevahti_smoke PASS. Rekisteririvi "palvelin ajokoneena" merkitty valmiiksi (18475c1).
  - Vanha Mac-kopio `testit/pico_dev.py` (237 riviä, ADB `/opt/homebrew`, ei laturisykliä eikä hold-komennon pvent-purkua) poistettu käyttäjän päätöksellä (36da492).
  - Jäljelle jäävät tietoiset kovakoodaukset (ei tämän paketin polkuja, toimivat palvelimella): `testit/scale_log.py:9` ja `testit/tray_calib.py:14` ADB `~/...`; `oneplus-akkuvahti.sh:24` ja `.service:6` `/srv/work` (palvelimen systemd-yksikkö).
  - ratkennut (Avoimet asiat): palvelin ajokoneena: adb (`~/.local/share/platform-tools/adb` nyt olemassa), HA-token (asennettu `~/.config/ha/to… — Valmis 26.9.2026 (EXPRESSO-POLUT-JUURI, cddfcf4): testiskriptien polut korjattu suhteellisiksi ja vanha Mac-kopio pico_dev.py:stä poistettu (36da492).
  - todettu (ei rekisteriin): Explore-ali-agentin lukema (ei itse todennettu): ominaisuus on elokuun "brew_log multipack" (G1-M5): puhelimen `files/firmware/` (10.8.2026) `brew_logger.py` (`BrewSessionLogger`, 10 Hz, rivimuoto v3, `MIN_SESSION_MS=15000`, `MAX_SESSION_MS=65000`) + `bluetooth_handler.py` BLE-multipack (meta → samples 20 riviä/osa → end), loki Picon RAMissa kunnes sovellus kuittaa `brew_log:ack:<id>`, `brew_log?…
  - todettu (ei rekisteriin): Rekisterin Flashaus-rivi sanoo "laitteella nyt 20260925-esiupito2", mutta `HISTORIA.md:24` sanoo esiavoin1 = 0028dff (26.9.2026) → rivi vanhentunut; laitteelta ei vielä todennettu (sääntö 9).
  - todettu (ei rekisteriin): "Olemassa olevien ajojen siirto kellolle": "kello" = firmwaren verkkokello (`pico/verkkokello.py`, `paketit/VERKKOKELLO.md`), "ajot" = pgap/psweep/pstep/mcal-testikomennot, ei uutot eikä rannekello.
- 26.9.2026 — EXPRESSO-SMOKE-TILASTO ajettu (commitit 907b589, ec14c13; 26.9.2026). Yksityiskohdat `paketit/VAIHESEURANTA.md`, luku "Smoken tilastolliset tarkistukset ja kellon nollaus".
  - `testit/esiuutto_smoke.py`: `BrewData` nollaa virtuaalikellon (`U.us = 0`) jokaisen tapauksen alussa; tapaukset 8 ja 9 1. ajo (pidon ka, katkaisusta pitoon) 12 vaiheella, 9 kohinaiset parit 24 siemenellä; `stat()`-apu: keskiarvo rajoissa + ulkona enintään osuus (`STAT_SHARE` 25 %, `NOISE_SHARE` 1/3). ff ja opittu tarve pysyvät joka ajon tarkistuksina.
  - Tapaus 3: tarkistus rajattu kellon lukituttua alkaneisiin taukoihin, joiden jälkeen rele palaa (Plant kirjaa `pause_t`, `pause_lens`; Pin.value välittää uuden arvon hookille).
  - `pico_dev.py`: `shot`/`hold` kieltäytyvät olemassa olevasta ei-tyhjästä lokista (`LOG_EXISTS`, exit) ennen ChargerOffia ja yhteyttä; docstring päivitetty.
  - todettu (ei rekisteriin): Kellon nollaus paljasti tapauksen 3 kaksi väärää hylkäystä (lukitsemattoman kellon 20 ms tauko 213 ms:ssa, ajon lopun releen katkaisu); HEADin vaihe vältti ne sattumalta. Uusi tarkistus: 12 vaihetta 0 väärää (64–77 taukoa); vahti pois (`EU_LATE_MAX_US` 20 ms) 1–7 väärää jokaisella vaiheella.
  - todettu (ei rekisteriin): Kaksi kolmesta "kohinaisesta" hylkäyksestä oli järjestelmällisiä, ei kohinaa: 8 ajo 1 rampin viive ka +0,444 (0,43–0,47, 12/12 yli 0,3); 9 1. ajo lämmin pidon ka −0,100 (9/12 yli ±0,1). Kohinaiset parit: lämmin → kylmä +0,061, 7/24 yli ±0,1 (max +0,24); kylmä → lämmin −0,041, 1/24. 8 ajo 2 0,25–0,27.
  - todettu (ei rekisteriin): Smoke nyt 0 failed (ajoaika 10 s, oli 4 s); lähimpänä rajaa kohina lämmin → kylmä 7/24 (sallittu 8) ja 8 ajo 1 katkaisusta pitoon 2/12 (sallittu 3). Muut smoket 14/14 vihreät.
  - todettu (ei rekisteriin): `LOG_EXISTS` testattu olemassa olevalla lokilla ilman laitetta (PICO_CHARGER_CYCLE=0, adb /bin/false).
- 26.9.2026 — EXPRESSO-ESIUUTTO-AVOIN ajettu ja todennettu laitteella. Commitit: 0028dff (koodi), d9c06e8 (laitelokit aa–ac, MANIFEST.json = esiavoin1, VAIHESEURANTA.md-luku). Yksityiskohdat: `paketit/VAIHESEURANTA.md`, luku "Avoin kuristin: ff edellisen ajon tau:sta ja integraalikatto".
  - ff = tavoite / (rate · tau_edellinen + p5). `eu_tau_pre` settings.txt:hen (classes.py, save/load). Vanhassa tiedostossa, jossa avainta ei ole, käytetään vanhaa polkua. Alarajaa ei ole.
  - Integraali rajataan hitaan osan (ff + KI·integ) mukaan välille 0…1. Vanha ±1,5 salli vain +0,45.
  - `pico_dev.py hold` ajaa `pvent`-purun (TILAUS-H) ennen tshotia ja keskeyttää (exit 1), jos PVENT_END ei ole reason=ok.
  - esiuutto_smoke: uusi tapaus 12 (avoin kuristin), carry-tuplissa eu_tau_pre.
  - KAYTTAJAN-TIEDOT.md luku 6: kaksi käyttäjän ohjetta sanatarkasti (purettu järjestelmä; lähes kiinni -kuristin ei ohjaa suunnittelua).
  - Laitteella nyt **esiavoin1 = 0028dff** (RESTORE_OK n=19, VERIFIED 19/19), pim:1 asetettu (RAM).
  - päätös (ei rekisteriin): Hylätty: epäsymmetrinen integraali (vaje nopeammin, ki × 6–10), koska se tasasuuntasi kohinaa (2–6 s +0,03…+0,13).
- 26.9.2026 — EXPRESSO-ESIUUTTO-ALKU ajettu. Commitit: 6f44e70 (−1…1-delta-sigma), 35c0f35 / 86ea7f5 (i–k), 5599d38 (l–n), 5b57715 (o–q), 391aa07 (¼-katkaisu), c9142b9 (nopea alku, poistettu), 52bd0f9 (hidas osa ≥ 0, r–t), f32a57f (u–w), e91816c (nopea alku pois), 3ec1ad6 (x–z). Yksityiskohdat: `Infra/iot/expresso/paketit/VAIHESEURANTA.md`, 26.9.2026:n luvut "Pidon alun ylitys on kohinan tasasuuntausta" → "paketin tulos".
  - Laitteella nyt **esialku6 = e91816c** (RESTORE_OK, VERIFIED 19/19). `pico/MANIFEST.json` = esialku6 (oli 24.9:n setistä, classes.py MISMATCH).
  - Laiteajot `hold 5` (vain 2,5 bar): i–k ja l–n avoimella kuristimella, o–z lähes kiinni. Lokit `testit/esiuutto-20260926-{i..z}-pim1.log`.
  - Smoke-tapaukset 10 (kiinni + kohina, edellisen tieto) ja 11 (nopea nousu, 100 ms viive) lisätty; tapauksen 6 raja t > 2,44 s / p5 ≥ ¼ tavoite (vanha perustui ½-sääntöön).
  - Vika V-066 (tarpeeton pysäytys, omistaja claude) kirjattu `claude/idea/IDEAT.md`, commit 034c23a.
  - todettu (ei rekisteriin): g:n (2,61) ylitys ei tullut jälkinoususta eikä rampista: nollaan rajattu duty tasasuuntasi jaksokohinan (sd 0,25) lisäiskuiksi, ja anti-windup esti integraalin korjauksen (malli kiinni-tila +0,16 → +0,04). Laite o–q: pidon 2 s:n jälkeinen p5 2,48–2,51, eli ryömintä on poissa.
  - todettu (ei rekisteriin): Täysi järjestelmä, kuristin lähes kiinni: nousu 9–12 bar/s, iskun viive paineeseen ~100 ms (q: pumppu pois 293 ms, raaka 2,14 → 3,55). ½-tavoitteen huuhtelusääntö myöhästytti katkaisua (over 0,70–1,38, huippu 3,4–4,3).
  - todettu (ei rekisteriin): ¼-katkaisu (nousu ≥ 8 bar/s; huuhtelu vaatisi G > 16, laitteella G ≤ 12,5) laitteella s, t, u, v, x, z: over 0,32–0,44; y 1,32 (rampin kiinnikurojan ryöppy, ks. avoimet).
  - todettu (ei rekisteriin): Kuristintilat laitteella: lähes kiinni tarve 0,05–0,08 / tau 2,6–9,7 s; välitila (i–k) 0,27–0,34 / 1,4–2,7 s; avoin (l–n) 0,64–0,69 / 0,35–0,92 s. Avoimella ei ylitystä, mutta 0–2 s p5 2,28–2,37: ff:n nousuarvio olettaa `EU_TAU_S` 1,8 s.
  - todettu (ei rekisteriin): Ajon alkupaine on joka ajossa −0,55…−0,6, ja lähdössä on täyttötilavuus: pulssitettu ramppi (d 0,3–0,5) ei nostanut painetta 0,9 s:ssa (r, w).
  - todettu (ei rekisteriin): ¼-katkaisu mittaa G:n kiihtyvästä noususta: 8,9–10,1 (täydellä nostolla 12,3).
  - todettu (ei rekisteriin): Malli: sovitus o–q = iskukoko 0,25, tau 4 s, viive 100 ms, täyttö 0 (`testit/esiuutto_smoke.py` tapaus 11). Kokeilut ilman hyötyä: ramppi seuraa painetta (v17), myötäkytkentä pois paineen ohitettua rampin (v18), negatiivisen integraalin esto loppulähestymisessä (v16), P-termi p5:stä.
  - todettu (ei rekisteriin): Koko smoke: 2 failed (8 rampin viive 0,43, 9 1. ajo lämmin −0,10 rajalla), molemmat tunnettuja kohinaisia. Muut functions-smoket 12/12 vihreät.
  - todettu (ei rekisteriin): Silta: `verify` heti laturisyklin jälkeen → `bridge not reachable`; toimi 15 s odotuksen jälkeen.
  - päätös (ei rekisteriin): Delta-sigma saa u:n alueella −1…1 (`acc` ≥ −1), ja anti-windup käyttää samaa aluetta; hidas osa ff + integraali ≥ 0 (`integ ≥ −uff/EU_KI`). Ilman alarajaa integraali valui ylityksessä (laite r: pito ka 2,01).
  - päätös (ei rekisteriin): Katkaisu sallitaan p5 ≥ ¼ tavoite, kun nousu ≥ `EU_RATE_FAST` 8 bar/s (huuhtelusäännön poikkeus perusteluineen koodissa).
  - päätös (ei rekisteriin): Käyttäjä valitsi ensin "nopea alku edellisen ajon G:sta" (ramppi heti ilman täyttä pumppua + Smith-ennustin 100 ms). Laitteella se epäonnistui 2/2 (r, w) täyttötilavuuden takia, joten **käyttäjä päätti 26.9.2026 poistaa sen** (e91816c). Hylätty myös: `EU_FAST_G` 8, joka kaatoi smoke 9:n (väärä nopea alku).
  - päätös (ei rekisteriin): Laiteajoissa käyttäjä hyväksyi flashin ja pitoajot erikseen ennen jokaista kierrosta (sääntö 8).
- 26.9.2026 — EXPRESSO-ESIUUTTO-FF jatkettiin ja ajettiin laitteella 26.9.2026. Commitit 54e3ac9, aded9a4, 8f2ceb6, 56ef2fa, 0308746, c323f6f; yksityiskohdat `paketit/VAIHESEURANTA.md` luvut "Loppulähestyminen", "Laitteella 26.9.2026 (esiuff1…)", "Vuoto edellisestä pidosta ja D-termi", "Laitteella … klo 12.3x (esiuff2…)", "Opitut arvot talteen…", "Laitteella … klo 12.5x (esiuff3…)".
  - 54e3ac9: rampin myötäkytkentä loppuu p5:n mukaan (ei rampin), loppulähestymisessä ja pidon 1. s:ssa `EU_KP_TAIL` 0,4 ja integraali ×3 → mallissa katkaisusta pitoon 1,2–1,3 s → 0,66–0,72 s.
  - 8f2ceb6 + 0308746: pidon ff = min(nousun arvio, edellisen asettuneen pidon tarve × G_edellinen/G_nyt); ilman edellistä tietoa `EU_FF_FIRST_X` 0,4 × nousun arvio; tarve opitaan pidosta 2 s jälkeen (≥ 1 s); `learned_ff_pre`, `eu_g_pre`, `eu_coast_s` tallentuvat settings.txt:hen (säilyvät resetin ja flashin yli); D-termi `EU_KD` 0,05 käyttäjän pyynnöstä ("himmennys PID-tyyppiseksi"). Smoke tapaus 9 kirjoitettu uudelleen (1. ajo, parit, kiinni-tila, kohinaiset parit).
  - 56ef2fa: `pico_dev.py hold <s> [loki]` — tshot:40 + tshot:stop <s> s EU_HOLDin jälkeen tai heti uuton TS-rivistä (pelkkä esiuutto).
  - c323f6f: `pico_dev.py` Link: `ERR usb closed` -haaran uusi yhteys sai saman 10× uusinnan (`_connect`) — `Connection refused` -vian syy.
  - Flashattu esiuff1 (54e3ac9), esiuff2 (8f2ceb6), esiuff3 (0308746), kaikki VERIFIED 19/19. Laitteella nyt esiuff3.
  - Puhelin (192.0.2.11) käyttäjän pyynnöstä: värinä ja latauksen ääni/värinä pois — secure charging_sounds_enabled/charging_vibration_enabled 0, system vibrate_on, haptic_feedback_enabled, keyboard_vibration_enabled, notification/ring/haptic_feedback_intensity 0 (luettu takaisin).
  - todettu (ei rekisteriin): Laite esiuff1 (lokit a, b): katkaisusta pitoon 712 ms (malli ~0,7 s ✓), mutta nousun ff 0,22–0,43 vs. pidon tarve ~0,10 → pidon 2 s keskiarvo 2,67–2,73.
- 26.9.2026 — EXPRESSO-ESIUUTTO-FF aloitettu, kesken (isännällä, ei flashattu). `pico/functions.py` `pre_infusion_phased`: - Katkaisussa (EU_CUT) pidon ff lasketaan tämän ajon noususta: G = rate + p5/EU_TAU_S, ff = tavoite/(G·EU_TAU_S), rajat 0,05–0,9; duty_avg = ff; ramp_ff = 2 bar/s / G (ennen G = rate/(1 − p5·ff/tavoite) vanhalla ff:llä). Jos rate < EU_RATE_MIN, opittu ff kuten ennen. Uusi vakio `EU_TAU_S = 1.8`. - EU_CUT-riville `g=` ja `ff=`; EU_END-riville `tau_obs=` = (tavoite/duty_avg − p_cut)/rate_cut (vain loki, EU_TAU_S:n tarkistukseen laiteajoista). - **Lukkiutumisen korjaus:** integraalin ±0,3 bar kaista (EU_INT_BAND_BAR) rajaa ennen pitoa vain nousevaa ramppia (`sp < target`); ramppi päättynyt → integraali kertyy.
  - `testit/esiuutto_smoke.py`: `run()` rajaa jokaisen ajon 30 s:iin virtuaaliaikaa (ennen until_s=None = loputon); uusi tapaus 9: kylmä (0,15 bar / 2,2 s, tarve 0,15) opitulla 0,31 ja lämmin (0,1 / 1,6 s, tarve 0,31) opitulla 0,15, kohinaton + 3 kohinaista siementä (cyc_sd 0,25, pysähdykset 0,8 %); tarkistaa katkaisun ff:n, pidon 2 ensimmäisen s keskiarvon ja yliampuman.
  - REKISTERI.md Viat: kaksi uutta prosessivikaa (commit 7462f4f + tämän pakkauksen päivitys juurisyyllä).
  - todettu (ei rekisteriin): Laitteen pidon toteutunut duty (EU-rivit pidossa, 1 s keskiarvot): lämmin a 0,33–0,37, b 0,29; kylmä c 0,13–0,16. Katkaisun rate: a 4,66 @1,31, b 3,85 @1,52, c 6,88 @1,34 bar. Näistä tau_obs a 1,35, b 1,84, c 2,23 s.
  - todettu (ei rekisteriin): τ ei ole saatavissa kahdesta nousupisteestä (paketin alkuperäinen ajatus): nousu kiihtyy täytön jälkeen (c: 100 ms lisäykset 1,5 → 2,8 → 4,0 → 4,9 bar/s), joten kahden pisteen τ olisi negatiivinen a/b/c:ssä; vuoto muuttaa nousua ~0,5 bar/s, nousunopeuden kohina ~1,5 bar/s. POIKKEAA paketin kuvauksesta — syy tämä; ratkaisu kiinteä EU_TAU_S + tämän ajon nousunopeus.
  - todettu (ei rekisteriin): Kaavalla laitteen luvuista: ff c 0,18 (tarve 0,15; vanha menetelmä 0,30), a 0,26 (0,33–0,37), b 0,30 (0,29).
  - todettu (ei rekisteriin): Smoke uudella koodilla 26.9.2026 (`timeout 900 python3 -u testit/esiuutto_smoke.py`): RESULT 6 failed. Läpi: tapaukset 1–7, 9 kohinaton ff (kylmä +0,03, lämmin −0,03), 9 lämmin pito (poikkeama 0,01; kohinalla 0,00–0,07), yliampumat lämpimällä ≤ 0,11. Kaatuu: 8 katkaisusta pitoon 1249 / 1206 ms (raja 1,1 s; HEAD-koodilla 1026 ms) — regressio; 9 kylmä kohinaton pidon alku 0,08 (raja 0,05); 9 kylmä …
  - todettu (ei rekisteriin): Sama testi HEAD-koodilla (/tmp-kopio): 10 failed — kylmä pidon alku +0,25…0,30, yliampuma 0,41–0,69 (laitteella c +0,44); lämmin opitulla 0,15 lukkiutuu (pito ei ala, 9.00).
  - todettu (ei rekisteriin): Lukkiutuminen: liian pieni ff → P-termi jättää paineen ~0,8 bar alle, integraali ei kerry kaistan ulkopuolella → pito ei ala eikä ajo pääty ennen kytkintä. Koski myös laitetta (kylmä→lämmin vanhalla opitulla ff:llä).
  - todettu (ei rekisteriin): Simulaattoriajo on puhelimella hidas: koko smoke ~10 min.
  - päätös (ei rekisteriin): τ kiinteänä 1,8 s (laitteen 1,35–2,23 keskeltä), ei opittuna: a ja b (molemmat lämpimiä) antoivat 1,35 ja 1,84, joten EMA-oppi lisäisi vain kohinaa. tau_obs lokiin, jotta arvon voi tarkistaa.
  - päätös (ei rekisteriin): Hylätty: τ kahdesta nousupisteestä (ks. yllä); regressio koko nousun yli (nousu ei ole lineaarinen, aliarvioi rate:n katkaisussa).
- 25.9.2026 — EXPRESSO-ESIUUTTO-PITO ajettu (palvelin). Commitit: be065f0 (päätöskohdan
  vartija), 71cf877 (pico_dev puhelimella), 78b8126 (rampin myötäkytkentä + a/b-lokit), 413105d
  (klamp-b + esiuutto-c -lokit). Yksityiskohdat: `paketit/VAIHESEURANTA.md` luvut "Pidon heilunta
  (EXPRESSO-ESIUUTTO-PITO…)" ja "Laitteella 25.9.2026 (esiupito1…)".
  - Korjaus 1 (be065f0, `functions.py` `pre_infusion_phased`): seuraavan päätöskohdan
    vähimmäisväli mitataan nimelliseen kohtaan, ei myöhästyneeseen t:hen; 5–10 ms myöhästyminen
    ohitti jakson ja päästi laskemattoman iskun. Smoke-tapaus 7.
  - Korjaus 2 (78b8126): rampin myötäkytkentä `ff·sp/tavoite + 2 bar/s / G`, G =
    rate/(1 − p·ff/tavoite) katkaisuhetkeltä (ei jos rate < `EU_RATE_MIN`, yläraja
    `EU_RAMP_FF_MAX` 0,5), vain kun p5 < sp ja loppuu `EU_RAMP_LEAD_S` 0,1 s ennen tavoitetta.
    Smoke-tapaus 8. `esiuutto_smoke` 32/32, muut 11 functions-smokea vihreät.
  - `pico_dev.py` (71cf877): puhelimella ajettuna ei adb forwardia (forward varasi
    127.0.0.1:2217 sillalta → `tail b''`), adb PATHista varalla.
  - HA-token asennettu palvelimelle `~/.config/ha/token` (600) palvelimelta adb:n
    kautta, väliaikaiskopio `/data/local/tmp/ha-token` poistettu. `ha.sh raaka GET
    /api/states/<laturi>` toimii.
  - Flashit: 20260925-esiupito1 ja -esiupito2, kumpikin VERIFIED 19/19, releet [0,0,0]; `pit:6`,
    `pim:1` kuitattu CMD_OK. Laitteella nyt esiupito2.
  - Laiteajot: klamp-20260925-a (done 7,77 bar 13,7 s), esiuutto-20260925-a/b (esiupito1, pito
    2,5 s), klamp-20260925-b (overpressure), esiuutto-20260925-c (esiupito2, 6 s pito, ilman
    klampia).
  - ratkennut (Avoimet asiat): "palvelin ajokoneena" adb/HA-token/bridge-osa — korjattu ja
    todennettu 25.9.2026 (adb löytyi, HA-token asennettu, pico_dev.py toimii puhelimella ilman
    forwardia); jäljellä vain `/srv/work`-kovakoodaus (rekisterin rivi jatkuu tällä).
  - ratkennut (Viat): "OHJEVAHTI-hook committaamattomana settings.json:ssa" oli väärä tieto —
    pura-tarkistus 25.9.2026 osoitti, ettei hookia ole `.claude/settings.json`:ssa lainkaan (ei
    committoitu eikä committaamaton), `OHJEKIRJA.json` tyhjä. Rivi poistettu vikaluvusta.
  - ratkennut (Viat): kaukalovahdin `wrise`-rivin "wmax-korjaus ei vielä flashattu" on
    vanhentunut — EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO flashattiin 23.9.2026 (vkello4) ja on nyt
    laitteella myös esiupito2:ssa; `wmax`-vaatimus estää kertymän flashatussa koodissa. Rivi
    poistettu vikaluvusta.
  - todettu (ei rekisteriin): mittausten ja päätösten yksityiskohdat rekisterin luvussa "Todettu
    25.9.2026 — EXPRESSO-ESIUUTTO-PITO".
- 24.9.2026 — EXPRESSO-ESIUUTTO-25BAR (TILAUS-K vaiheet 1–2) toteutettu ja todennettu laitteella. Uusi esiuuttotapa `pre_infusion_phased` (`pico/functions.py`), valinta `pim:0|1` (RAM, oletus 0 = vanha PI; `TS_START` tulostaa `pim=`), `BrewData.pre_infusion_method`, `eu_coast_s`. Commitit 99214bc (toteutus), a596e32 (esiu1 + lokit a–c), 39b1587 (korjaus), f200ffe (esiu2 + lokit d/e), 8d086b8 (shot_test).
  - Vaihe 1: täysi sykli, katkaisu kun p5 + nousunopeus × opittu jälkinousu `coast_s` ≥ tavoite − 0,3 bar ja p5 ≥ ½ tavoite; nousun ikkunat lokiin `gate=-1` (eivät opeta kelloa). Vaihe 2: päätöskohta kellon reuna + 13,6 ms, delta-sigma PI:stä, poisto = 10 ms tauko kun 2,5·sd < 4 ms, muuten 20 ms; rele kytketään ennen laskentaa, myöhästymisvahti 300 us (`late`), ohitetut jaksot `miss`. Pito alkaa vasta, kun ramppi on tavoitteessa ja p5 ≥ tavoite − 0,1 (menetelmäohje). Kuvaus `paketit/VAIHESEURANTA.md` luku "Esiuutto 2,5 bar vaiheilla 1–2".
  - Testit: `testit/esiuutto_smoke.py` 25/25 (iskumalli nollaylitys-SSR, viive 40 ms, tapaus 6 kohinainen täyttö — vanha koodi kaatuu 2/4); analyysi `testit/esiuutto_analyysi.py <loki...>` (PI- ja EU-rivit samoin mittarein, `p5`-yliampuma). `shot_test.py` korjattu (valelaitteesta puuttui `relay_guard`, kaatui jo HEADissa): RESULT 0 failed; esiehto `/tmp/fw_preset.py` = kopio `pico/preset.py` kirjattu testiin.
  - Flashattu kahdesti tältä palvelimelta: setit `20260924-esiu1` ja `20260924-esiu2` (`build_set.py` → `pico_dev.py restore` → `verify` VERIFIED 19/19). Picolla nyt esiu2 (= 39b1587 koodi, sis. vsweep2:n ajoitusvahdin → avoin asia 29 tehty). Repon `pico/MANIFEST.json` päivitetty vastaamaan (oli jäänyt vanhaksi: esiu1:n ensimmäinen verify antoi 15/19 väärää manifestia vastaan).
  - Käyttäjän asetukset luettu Picon `settings.txt`:stä ennen ajoja (pit 2,5 s, pip 2,5 bar, bp 8,0, wmax 720, wrise 250) ja palautettu (`pit:2.5`, `pim:0`); keitin jätetty kahvivalmiuteen.
  - ratkennut (Avoimet asiat): vsweep2 (ajoitusvahti) — Flashattu Picolle firmwarepäivityksen mukana 24.9.2026 (setit 20260924-esiu1 ja 20260924-esiu2, sisältyy esiu2:een, VERIFIED 19/19).
  - todettu (ei rekisteriin): Lähtötaso `testit/esiuutto-20260924-a-pim0.log` (vanha PI 17 ms, pip 2,5, pit 6): paine nousi vasta ~3,3 s:n kohdalla ja jäi 1,5–2,0 bariin; ramppi nollautui aina paineen pudotessa alle 1,5 barin, pitoajastin ei käynnistynyt 10 s:ssa.
  - todettu (ei rekisteriin): esiu1 `-b-`/`-c-pim1.log`: 10 ms tauot toimivat 2,5 barissa (kello sd 317–329 us, 40–41 opettavaa ikkunaa, amplitudi 0,12–0,54, win_low 0–1; sk10 79–84, sk20 0–1; paine pysyi teholla d ≈ 0,3, ilman poistoja tasanne 6,9 bar). Yliampuma +1,27 / ~+1,1 bar. Juurisyyt: jakson keskiarvo heiluu täytössä ±0,5 bar → katkaisu piikistä (c: p 1,37, rate 16,5 bar/s); integraali kertyi rampissa; pito alkoi pai…
  - todettu (ei rekisteriin): esiu2 `-d-`/`-e-pim1.log`: yliampuma (p5) −0,02 / +0,30 bar, pito alkoi 2,48 / 2,57 barissa, pidon keskiarvo 2,49 / 2,53 bar, jaksohajonta 0,25 / 0,27 bar; coast_s 0,30 → 0,206 → 0,145 (learn=1); late 13–20, miss 6–7 per ajo. Jäljellä pidossa hidas heilunta: p5 2,2–2,8 bar, jakso ~2–3 s.
  - todettu (ei rekisteriin): klamp-c tasanne 6,91 bar (13.20), klamp-d 9,28 bar (14.30): kuristin oli säädetty välissä.
  - todettu (ei rekisteriin): Nollapiste (avoin asia 25): levossa purun jälkeen lukema −0,68/−0,70/−0,71/−0,86 bar (VENT-rivit). Kalibrointi on yksipisteinen (`PCALSET_OK gain=1,0000 offset=−0,990`, KEHITYSYHTEYS.md:985, sovitettu 8 barissa). Jos lepo on todellinen 0, kaksipistemalli raaka = 0,21 + 1,0975 · todellinen → lukema 2,5 bar ≈ todellinen 3,0 bar. Ei todennettu mittarilla.
  - todettu (ei rekisteriin): Yhteysvika toistui: ensimmäinen `shot` ajoi tyhjään (hubi irtosi 0,6 s laturisyklin jälkeen, logcat 13:23:29), samoin d:n 1. yritys; uusinta onnistui aina.
  - todettu (ei rekisteriin): adb toimii tältä palvelimelta: `~/.local/share/platform-tools/adb` (ei PATHissa), puhelin 192.0.2.11:5555 `device`.
  - päätös (ei rekisteriin): Vanha PI-esiuutto säilyy oletuksena (`pim:0`) kunnes käyttäjä päättää; `pim` ei säily uudelleenkäynnistyksessä.
  - päätös (ei rekisteriin): Päätökset 5 jakson (100 ms) keskiarvosta, ei yksittäisestä jaksosta; integraali ennen pitoa vain |e| < 0,3 bar; jälkinousua ei opita ilman nousua katkaisun jälkeen.
  - päätös (ei rekisteriin): Smoke-testin yliampumaraja = yksi mallin isku (0,2 bar); mallin väreilyn vaihe kalibroitu (RIPPLE_SHIFT_US 5460) vastaamaan laitteen lohkoa 8,5–18,7 ms.
  - päätös (ei rekisteriin): Nollapisteen korjausta ei tehty: menetelmäohjeen mukaan vertailulukema tulee käyttäjän mittarista.
- 24.9.2026 — LAITETESTI3 (vkello4): ajo a katkesi ylipaineeseen kylmällä kuristimella; ajo b (testit/vkello-20260924-b.log) lukittu todellinen virhe 0/87 > 1000 us, max 528 us, 2 taukosarjaa (trayrise), käyttäjä hyväksyi kahdella sarjalla. dfe96cb, paketit/VERKKOKELLO.md "Laitetesti 3".
  - Kuristimen lämmitys `klamp:<s>` käyttäjän menetelmällä (KAYTTAJAN-TIEDOT: tavoite = tasanteen paine, ei vakio; pidetään kunnes pumppua ei rajoiteta): 3b2ff5a, flashattu klamp1 (c89433c), laitteella klamp-20260924-a (tasanne 7,58 bar, done 13,7 s) ja -b (7,37 bar, done 13,1 s). `bp` palautettu 8,0:aan (fc9610f).
  - TILAUS-G-analyysi (ffaa87a): viivepoikkeama selittyy nousunopeudella, ei paineella; kiinteä korjaus ei kelpaa; nousu ei kelpaa kellon opetukseen. Skriptit testit/vkello_dpdt.py, vkello_dpdt_replay.py, vkello_rise_learn.py.
  - Uusi tilaus TILAUS-K/L kirjattu KAYTTAJAN-TIEDOT luku 2c (997c7bc).
  - Askel 1 `vsweep:<reps>` (b6587d5), flashattu vsweep1 (61b30cf, VERIFIED 19/19), laitteella testit/vsweep-20260924-a.log; tulos paketit/VAIHESEURANTA.md (bd517b2). Ajoitusvahti korjattu isännällä bd517b2:ssa, EI flashattu (Picolla vsweep1).
  - pico_dev.py `restore` tekee `am force-stop` ennen palautusta (61b30cf).
  - turva_pika_smoke odottaa 13 dev_run-komentoa (avoin asia "Turva pika smoke" ratkaistu: päivitetään kun komentoja lisätään).
  - ratkennut (Avoimet asiat): turva_pika_smoke — turva_pika_smoke odottaa 13 dev_run-komentoa; testin komentalukumäärä päivitetään jatkossa sitä mukaa kun komentoja lisätään.
  - todettu (ei rekisteriin): Flashaus: `RESTORE_FAIL … no size ack for /api_functions.py` klamp1:llä 1× ja vsweep1:llä 2× (logcat `USB get_status request failed`); force-stop korjasi. Ensimmäinen verify palautuksen jälkeen `tail b''`, uusinta 19/19.
  - siirretty rekisteristä (katto): | Vaihe 1a3 verkkokello | vkello4 (51eec34) laitetestattu 24.9.2026 (`testit/vkello-20260924-b.log`): lukittu todellinen virhe 0/87 > 1000 us, max 528 us, portti vain taukojen jälkeen; 2 taukosarjaa (trayrise), käyttäjä hyväksyi kahdella sarjalla. Ajo a katkesi ylipaineeseen kylmällä kuristimella (`paketit/VERKKOKELLO.md`, Laitetesti 3) | valmis laitteella; seuraava on olemassa olevien ajojen siirto kellolle ja TILAUS-G-viivemalli (rivit alla). |
  - siirretty rekisteristä (katto): | Kumpi puolijakso on kumpi | **vastattu 24.9.2026 (vsweep-20260924-a, `paketit/VAIHESEURANTA.md`):** 10 ms tauko poistaa iskun vain, kun se alkaa 8,5–18,7 ms kellon reunasta (vaste −0,61…−0,83 bar vs 20 ms −0,85), muualla ~0 → pumppu vetää vain toisella puolijaksolla, käyttäjän hypoteesi pitää | käyttäjän hypoteesi: tärykalvopumppu tekee jakson aikana kaksi vastakkaista liikettä ja vetää vain toisella puoliskolla diodin takia; mittaus vaatii puolijaksoa lyhyemmän tauon ja vaihepyyhkäisyn vakiopaineessa |
  - siirretty rekisteristä (katto): | 10 vaiheen hajontamittaus (1b hajontatesti 5 ms tauolla) | **ajettu 23.9.2026** q1–q4 (`testit/pgap-20260923-q1…q4.log`, 4×50 taukoa, 20/vaihe, kaikki `reason=ok`, pmax 8,28–9,38): **käsketty vaihe ei ollut todellinen verkkovaihe** — firmware ajastaa taukoja ajon alusta kiinteällä `PCAP_MAINS_US`=19960 us (50,10 Hz) ilman verkkotaajuuden seurantaa, eikä taajuutta mitattu ajon aikana; 20.9. mitatulla 50,027–50,161 Hz:n välillä kohdistus ajautuu taukojen 14,8 s:n aikana 18–22 ms eli ~1 koko jakson (26 vaiheaskelta à 832 us), joten tulos ei kerro vaiheen vaikutuksesta. Käsketyn vaiheen mukaan: depth_bar vaiheittain 0,77–1,06 bar, sd 0,39–0,63, yksisuuntainen ANOVA F=0,65 (df 9,190; ajokohtaisesti keskitettynä 0,69), 5 %:n kriittinen ≈1,9. Perustaso vaihtelee ajojen välillä yhä (ka 6,69/7,70/7,64/7,07 bar). depth_bar korreloi slope-kentän kanssa r=0,85 (base r=−0,06), ja trough_ms jakautuu 0–200 ms:iin (kasaumat ~50 ja ~190 ms: depth 0,64 vs 1,20) → depth-mittari mittaa pääosin painetrendiä, ei tauon vastetta | uusinta vasta VERKKOKELLOn jälkeen; valitse trendikorjattu vastesuure (liittyy riviin "Analysaattorin tuomio") ennen johtopäätöstä invariantin lähteestä; päivitä rivi "Vaihe 1b:n invariantti" |
  - siirretty rekisteristä (katto): | SSR-40DA:n tyyppi | **päätelty mittauksesta 24.9.2026: nollaylitys** — vsweep-20260924-a:n lohkon reunat jyrkät (välitasoja 0/20, 2/60 väärin luokiteltua); tyyppikilpi tarkistamatta (`KAYTTAJAN-TIEDOT.md:186`) | nopein varmistus on tyyppikilpi; mittauksesta päättely antaa saman vastauksen epäsuorasti; ratkaisee myös lukkorajan 1000 us tarkistuksen |
  - siirretty rekisteristä (katto): | Verkkokellon väärien lupien pohja nousevassa paineessa (sim 1,3–1,8 %) | syy löydetty (uudelleennousun viivetransientti), amplitudiportti todennettu laitteella 23.9.2026; palautumisen häntä korjattu paineportilla 51eec34; todennettu laitteella 24.9.2026 (0/87 lukittua > 1000 us, max 528 us) | valmis. |
  - siirretty rekisteristä (katto): | TILAUS-G ja nousun viivepoikkeama | 24.9.2026 analyysi (`paketit/VERKKOKELLO.md`, "TILAUS-G: viivepoikkeama"): poikkeama selittyy nousunopeudella (−154 us per bar/s, R² 0,29), ei paineella; ajojen välinen ero ~3×, sd ~850 us; kiinteä korjaus ei korvaa paineporttia (replay: 4 lukittua > 1000 us b:ssä ja h:ssa), ja nousun ikkunoista opetettu kello on 3,6–6,8 ms väärässä lukituksi ilmoitettuna | käyttäjän päätös: (a) vaihe tasanteelta (poikkeama TILAUS-G:stä), (b) lisäaineisto eri kuristinasennoilla, (c) muu. |
- 23.9.2026 — /pura infra expresso 23.9.2026 16:39 (sovitinreitti, exit 4; ajajalokin mukaan moottori agy, malli gemini-3.8-flash-medium, 33 s, pisteet 6/6). Aloitettiin EXPRESSO-VERKKOKELLO-LAITETESTI3.
  - Setti vkello4 rakennettu puhelimeen: `build_set.py --check vkello4` (adb ok, akku 80 %, pohja vkello3, push=18), sitten `build_set.py vkello4` → "Setti vkello4 valmis (18 tiedostoa + MANIFEST.json)". Repon pico/ = 51eec34 (git diff 0, puu puhdas).
  - Puhelimen manifesti (`files/firmware_backup/vkello4/MANIFEST.json`) vs repon pico/: n=19, sama 18, ero 0; `secrets.py` vain puhelimessa (pohjasetistä, odotettu).
  - Käyttäjä hyväksyi flashin ja ajon ("Valmis, aja"). Palautuskomento estyi käyttörajan vahdilla (5 h raja 99 %), jatko klo 19.11.
  - Palautus 19.12: `RESTORE_OK vkello4 n=19` klo 19:15:52 (`FLASH_OK n=19`); flash kesti ~3 min, ensimmäinen 180 s odotus ei nähnyt riviä (ansa "iso paketti kestää ~2 min", PICO-HALLINTA.md luku 9).
  - `pico_dev.py verify /tmp/vkello4-MANIFEST.json`: 3. yritys `VERIFIED 19/19`, SAFE_OK (releet [0,0,0]) joka yrityksessä. Picolla on nyt vkello4 = 51eec34.
  - `vkello 0` -ajoa EI ajettu: 5 h tauon jälkeen kysyin uudelleen (säiliö täynnä, kaukalo tyhjä, joutilas); käyttäjä sulki kysymyksen vastaamatta, sitten /pakkaa.
  - todettu (ei rekisteriin): verify 1. yritys kaatui: `timeout waiting for raw REPL, tail b''`; logcat PicoUsb `USB get_status request failed` → `USB closed` 19:16:17 — pico_dev.py:n CHARGER off/on -sykli (Shelly-laturi) osui palautuksen jälkeiseen USB:n uudelleenavaukseen.
  - todettu (ei rekisteriin): verify 2. yritys kaatui 10/19 OK jälkeen: puhelimen BLE-yhteys ("Connected - sending initial settings", `Received: 'sync'`, `Received: 'brew_log?'`) tulosti raw REPL -vastauksen `\x04>` perään, ja `Link.until` (pico_dev.py:155-167) vaatii `buf.endswith(marker)` → timeout. Hash oli jo tullut oikein.
  - todettu (ei rekisteriin): Puhelin AC powered, akku 80 % koko session (hubi syöttää).
  - päätös (ei rekisteriin): Ei käyttäjän menetelmäpäätöksiä. Ajo kysytään uudelleen ennen pumppua, koska hyväksynnästä kului ~5 h (säiliön/kaukalon tila voi muuttua; TYOTAVAT sääntö 8).
- 23.9.2026 — EXPRESSO-VERKKOKELLO-LAITETESTI2 ajettu 23.9.2026: setti vkello3 (43e207a) rakennettu (`build_set.py vkello3`), `RESTORE_OK vkello3 n=19` 15:33:57, `pico_dev.py verify` puhelimen manifestia vasten (`files/firmware_backup/vkello3/MANIFEST.json`) `VERIFIED 19/19`; repon pico/ = setti (0 eroa, secrets.py vain laitteella). Flashaus kesti ~4,5 min (~1 kt/s).
  - Neljä `vkello:0`-ajoa käyttäjän kanssa klo 15:36–15:43: `testit/vkello-20260923-{e,f,g,h}.log`. f:ssä vesisäiliö tyhjeni (käyttäjä vahvisti). Ehjät: e, g, h. Commit fd62120 (lokit, `testit/vkello_analyysi.py`, VERKKOKELLO.md luku "Laitetesti 2").
  - Käyttäjän pyynnöstä vesianalyysi (testissä liikaa täyttöä ja tyhjennystä) ja käyttäjän valinta "Protokolla + paineportti": toteutettu commit 51eec34, ei flashattu (VERKKOKELLO.md luku "Paineportti ja vettä säästävä protokolla"). - `pico/verkkokello.py`: `P_GATE_BAR` 1,0, `pgate(p)`, `accept(amp, p)` → 0/1/2, `iq_close(t, learn=True)`; `learn=False` palauttaa rivin ilman portteja/päivitystä. - `pico/functions.py` `pressure_clock_run`: nousun ikkunat `VKELLO_R w t_ms z_us amp p_bar`; taukosarja 0,5/1/2/5 s × `VKELLO_SERIES` 3 yhdessä ajossa, käynti `VKELLO_ON_MS` 3000, 5 s tauon jälkeen `VKELLO_ON_LONG_MS` 4000; ikkunarivin `gate` 0/1/2; `VKELLO_END … pgated=`. - `testit/vkello_rise_smoke.py` kohta 7 (12 taukoa, VKELLO_R ilman päivitystä, gate=2 vain taukojen jälkeen); `testit/vkello_analyysi.py` (firmwaren kello + portit uudelleen, käyrä aste 3, paineportin replay vanhoille lokeille, nousun TILAUS-G-taulukko, ≥ 3 taukosarjaa).
  - ratkennut (Avoimet asiat): vkello: paineen purku ennen ajoa (TILAUS-H) ja nousukatto — Paineen purku (VENT 1–4 sykliä) ja nousukatto (plateau 8,5–13,3 s, ei noreach) todennettu laitteella 23.9.2026.
  - todettu (ei rekisteriin): Täyttyi kaikissa ajoissa: VKELLO_VENT ennen nousua (e 2, f 2, g 1, h 4 sykliä); nousu tasanteeseen, ei noreach (e 8,63 bar/11,1 s, g 8,21/13,3 s, h 8,90/8,5 s); amplitudiportti hylkää vain taukojen jälkeen (gated 11/13/14, 0 ennen 1. taukoa), rebased 0.
  - todettu (ei rekisteriin): Ei täyttynyt: kellon todellinen lukittu virhe (E = kellon reuna + z, verkon vaihe = 3. asteen käyrä vakiotilasta): e 13/81 > 1000 us (max 1629), g 12/79 (1301), h 1/78 (1055). Ylitykset tauon jälkeisissä ikkunoissa k4–15, paine vielä nousussa (6,3–7,8 bar), kaikki negatiivisia.
  - todettu (ei rekisteriin): Raaka ehto "lukittuna |z| > 1000 us vain gate=1" oli väärä mittari: 7–14 ikkunaa/ajo, kaikki gate=0, myös h:ssa (z on mittaus, sd 441–494 us).
  - todettu (ei rekisteriin): Vertailukäyrä: 2. asteella e:n jäännös sd 673 us, 3. asteella 449 us (verkon vaellus). Paineportin tulos sama asteilla 3–6.
  - todettu (ei rekisteriin): Paineportin replay (43e207a + P_GATE_BAR): e 0/64 (max 453 us), g 0/52 (505), h 0/59 (891); lupa 52–64/119 (ilman 78–81); pisin hylkäysjakso 7, ei siirtoa. Lukko palaa 0,5–2 s tauon jälkeen k6–13, 5 s tauon jälkeen k12–16.
  - todettu (ei rekisteriin): TILAUS-G (e/g/h, portin läpäisseet, poikkeama tasanteen käyrästä, aste 2): 3–5 bar ≈ −1,4 ms, 5–6 −0,8, 6–7 −0,25, 7–8 −0,19, 8–10 +0,06 ms; +269 us/bar, r 0,53. Matalan paineen ikkunat ovat kaikki uudelleennousua: paine ja aika tauosta eivät erotu.
  - todettu (ei rekisteriin): 5 s tauon jälkeinen 1. ikkuna (portin hylkäämä) +2,7…+3,4 ms, kuten laitetesti 1.
  - todettu (ei rekisteriin): Verkkotaajuus VKELLO_END: e 50,0104 Hz 15:36, g 49,9551 15:41, h 49,9770 15:43.
  - todettu (ei rekisteriin): Purun loppupaine negatiivinen: VKELLO_VENT bar −1,08 / −0,95 / −0,67 / −0,70 (yksi raaka näyte 0,2 s venttiilin sulkemisen jälkeen); syy selvittämättä.
  - todettu (ei rekisteriin): Vesi: pumppua 28,5–33,3 s/ajo, josta nousu 8,5–13,3 s (35 %) ilman ikkunoita. Kaukalo ~520 g ajon h jälkeen (puhelimen logcat `[DATA] RX settings weight`, 15:44–15:48; nousi +5 g 4 minuutissa, jälkitippumista); tyhjä + ritilä 460 g (KAYTTAJAN-TIEDOT.md:178-180) → ~60 g/ajo ≈ 2 g/s; kaukaloon mahtuu 230–285 g. Uusi protokolla: ~54 s / ~110 g yhdessä ajossa (ennen 3 × ~30 s / ~190 g). Vaa'an teleme…
  - todettu (ei rekisteriin): `pico_dev.py verify` kaatui kerran timeoutiin, kun sovelluksen `Received: 'sync'` / `brew_log?` tuli REPL:iin; uusinta heti `VERIFIED 19/19`.
  - todettu (ei rekisteriin): Testit 51eec34:n jälkeen: vkello_rise_smoke, verkkokello_holdout, vkello_replay, `vkello_analyysi.py vkello-20260923-{e,g,h}.log` 0 failed; muut smoket 0 failed; turva_pika_smoke 1 failed kuten ennen (testikomentoja 11, odotus 10).
  - päätös (ei rekisteriin): Käyttäjä 23.9.2026: vesiprotokolla + paineportti samaan pakettiin (vaihtoehdot: pelkkä protokolla; kirjaus ilman toteutusta). Paineesta riippuva viivekorjaus (TILAUS-G/I) jää omaksi paketikseen: vaatii aineiston, jossa paine ja aika tauosta erottuvat.
  - päätös (ei rekisteriin): Käyntijakso 3 s eikä ehdotettu 2,5 s: paineportin kanssa lukko palaa vasta k6–13, 2,5 s jättäisi ~2 lukittua ikkunaa.
  - päätös (ei rekisteriin): Hyväksyntämittari on todellinen lukittu virhe (`vkello_analyysi.py`), ei raaka z.
- 23.9.2026 — EXPRESSO-VERKKOKELLO-KORJAUS tehty ja commitoitu `43e207a` (ei flashattu). Analyysi ja luvut: `paketit/VERKKOKELLO.md` luku "Laitetestin analyysi ja korjaus 23.9.2026".
  - `pico/verkkokello.py`: transienttiportti `Verkkokello.gate(amp)` — ikkuna, jonka amp > GATE_RATIO 2,0 × hyväksyttyjen liukuva keskiarvo (GATE_ALPHA 0,2), ei päivitä kelloa; GATE_MAX 20 peräkkäisen hylkäyksen jälkeen viite siirtyy nykyiseen amplitudiin (laskuri `rebased`). `iq_close` palauttaa nyt (z, amp, keskipaine, used).
  - `pico/functions.py` `pressure_clock_run`: purku ennen pumppua `_mcal_vent`-syklillä (TILAUS-H), loki `VKELLO_VENT cycles bar`, `vent_runaway` → ei pumppausta; nousun katto `VKELLO_REACH_MAX_MS` = 40000 (oli PSTEP_REACH_MAX_MS 20000); ikkunariville `p_bar` ja `gate`, `VKELLO_END`:iin `gated` ja `rebased`.
  - Uusi `testit/vkello_replay.py`: ajaa firmwaren `Verkkokello`n porttineen laitelokeilla a/b/d kellosta riippumatonta verkkokäyrää vasten + portin yksikkötarkistukset. `testit/vkello_rise_smoke.py`: laitosmalliin jäännöspaine ja venttiilipurku, tapaukset 5 (purku ennen nousua) ja 6 (nousu 0,2 bar/s > 20 s → plateau); mutaatiotarkistus: 5 ja 6 punaisia vanhalla functions.py:llä.
  - todettu (ei rekisteriin): Testit 23.9.2026 commitin 43e207a jälkeen: vkello_replay, vkello_rise_smoke, verkkokello_holdout ja muut smoket 0 failed; turva_pika_smoke 1 failed (ennestään, dev_run-komentoja 11 eikä 10 — avoin asia "Pikatestin komentomäärä"). mpy-cross ei asennettuna, MicroPython-käännöstä ei tarkistettu.
- 23.9.2026 — EXPRESSO-VERKKOKELLO-LAITETESTI ajettu 23.9.2026. Laitteella ollut setti oli `20260920-pphase2`; sen päällä 5 flashaamatonta kokonaisuutta (79b3a2a, b25b9e7, f159f12, 819bb8f, 3ce72b3). Käyttäjän päätös: kaksi flashausta (TYÖTAVAT 6), ensin turvasetti.
  - Setti `20260923-turva1` (commit 819bb8f, työpuusta): RESTORE_OK n=18, `pico_dev.py verify` VERIFIED 18/18, releet [0,0,0].
  - Kaukalovahti laitteella: `wmax:0` + `pcap 100:1` → `PCAP_END n=0 pmax=0.00 reason=nolimit`; `wmax:1` → `reason=tray`. Ei relettä kummassakaan. Ajo c (alla) päättyi `reason=tray` kolmen ajon kertymästä rajalla wmax:720 → tray_total-kohta 3 (kertymä pysähtyy rajaan) todennettu laitteella.
  - `wmax:720` asetettu (käyttäjä: ritilä paikallaan).
  - Setti `20260923-vkello1` (3ce72b3): RESTORE_OK n=19, VERIFIED 19/19; `vkello 7` wmax:1:llä → `VKELLO_END … reason=tray`.
  - Korjaus 9954c2e: `pressure_clock_run` nousu päättyy tasanteeseen (suodatettu paine, PCAP_PLATEAU_BAR/_MS/_MIN_BAR kuten pcap_settle), `vkello:0` = pelkkä tasanne, target > 0 valinnainen; uusi rivi `VKELLO_RISE bar= reach_ms= reason=plateau|target`. Testi `testit/vkello_rise_smoke.py` 0 failed (vanhalla koodilla 4 failed). PICO-HALLINTA.md luku 4 ja pico_dev.py ohje päivitetty.
  - Setti `20260923-vkello2` (9954c2e, vain functions.py): RESTORE_OK n=19, VERIFIED 19/19.
  - Korjaus bae28e4: `pico_dev.py restore` — `date` yhtenä adb-argumenttina ja `errors='replace'` adb-tulosteelle.
  - Ajot `pico_dev.py vkello 0 testit/vkello-20260923-{a,b,c,d}.log` (a 14:40, b 14:41, c 14:42, d 14:46 palvelimen aikaa). Käyttäjä tyhjensi kaukalon ennen d:tä.
  - todettu (ei rekisteriin): Puhelin: akku 80 % → 79 %; laturikierto toimi joka operaatiossa.
  - päätös (ei rekisteriin): Käyttäjä 23.9.2026: flashaus kahdessa vaiheessa (turva1 ensin, sitten vkello), ei kaikkea kerralla (sääntö 6).
  - päätös (ei rekisteriin): Lokien nimeäminen: keskeytynyt c säilytetään, uusinta nimellä d.
- 23.9.2026 — Paketti EXPRESSO-VERKKOKELLO-FW ajettiin /rd:llä, ajajana toteuttaja-sonnet (käyttäjän valinta). Landattu commitissa 3ce72b3, ei flashattu. Uusi `pico/verkkokello.py` (129 riviä) on KF3Clock MicroPythonina: ticks-viite kokonaislukuna 32-bittisen floatin takia ja I/Q-mittaus 256 alkion taulukosta. `functions.py` sai `pressure_clock_run`in: nousu targetiin, sitten taukosarja 0,5/1/2/5 s ja jokaisen jälkeen 4 s käyntiä. Rivit VKELLO, VKELLO_RESTART, VKELLO_TRAJA ja VKELLO_END. Lisäksi `vkello:<bar>|stop` (commands.py, classes.py), `main.py`:n kyselyhaara (take_pressure_clock_request), `pico_dev.py vkello <bar> [loki]` ja PICO-HALLINTA.md.
  - Korjaus 1 (`paketit/VERKKOKELLO.correction-1.md`, commit 1f786a9): suunnittelija löysi vihreän kierroksen jälkeen kolme vikaa. (1) main.py-kytkentä puuttui: brief kielsi main.py:n, ja vika oli suunnittelijan. Toteuttaja kysyi asiasta oikein. (2) I/Q-näytteiden aikaleima oli `now = next_t`, nyt todellinen `utime.ticks_us()` kuten pgap:ssa. (3) PGAP_RUN_MAX_MS tarkistettiin vain nousussa, nyt myös taukosarjassa.
  - Mittausrivi EXPRESSO-VERKKOKELLO-FW kirjattiin Automation_plugin/docs/measurements/delegation.jsonl:ään (commit da9e6a86): iterations 2, aided true, 1 273 273 ms.
  - todettu (ei rekisteriin): Suunnittelija ajoi itse jokaisen hyväksyntäkomennon korjauksen jälkeen: py_compile 0; holdout 12/12 PASS (`RESULT: 0 failed`); verkkokello_sim `RESULT: 0 failed`; tray_guard_smoke ja pskip_gate_smoke 0 failed; scope-tarkistus 0; main.py-grep 0; Budget 4952 ≤ 4990 riviä.
  - todettu (ei rekisteriin): Ensimmäinen kierros osui briefin Budgetin rajaan tasan: 4520/4520.
  - päätös (ei rekisteriin): Ajaja toteuttaja-sonnet (käyttäjä 23.9.2026). Hylätyt vaihtoehdot: toteuttaja-opus (mikään eskalointiehto ei täyttynyt) ja briefin lyhentäminen (agy-reitti vaatisi silti työkalumuutoksen).
- 23.9.2026 — EXPRESSO-VERKKOKELLO (vaihe 1a3) tehty pakettina "brief + isäntäsimulaatio ennen laitekoodia": uusi `Infra/iot/expresso/testit/verkkokello_sim.py` (jaksotason simulaatio: verkko 49,9–50,1 Hz vakio/ramppi 5 mHz/s/ramppi 20 mHz/s, pumpun tauot 0,5–10 s, mitattu kohinamalli; kellot PI, KF, KF3; `RESULT: 0 failed`), uusi `testit/verkkokello_holdout.py` (12 tarkistusta: vakiot, numeerinen vastaavuus KF3Clockiin sim-silmukassa, ticks-kierto 2^30, I/Q-kehys LAG_US:lla, amplitudiportti, pito 0,1 s / 10 s, jaksoraja, iq_add ilman cos/sin). Holdout todennettu suunnittelijan viitetoteutuksella `/tmp/ref_verkkokello.py` (12/12 PASS, ei repossa); ilman moduulia holdout kaatuu kuten pitää.
  - Uusi `paketit/VERKKOKELLO.brief.md` (luovutettavissa; `vaatimukset.mjs --tarkista` ok: 2 viittausta): moduuli `pico/verkkokello.py` (luokka `Verkkokello`, rajapinta edge/update/sd_us/locked/iq_start/iq_add/iq_ready/iq_close/iq_abort, attribuutit T/d/traja), testikomento `vkello:<bar>` (`pressure_clock_run`, rivit VKELLO/VKELLO_RESTART/VKELLO_TRAJA/VKELLO_END), `pico_dev.py vkello`. Budjetti 4520 riviä (mitattu 4270, commit ea2691a).
  - `paketit/VERKKOKELLO.md`: tila päivitetty ja uusi luku "Simulaation tulos 23.9.2026 — mikä muuttui suunnitelmasta".
  - todettu (ei rekisteriin): RP2040:n MicroPython-float on 32-bittinen → vaiheviite kokonaislukuna ticks + desimaaliosa (kirjattu briefiin).
- 23.9.2026 — EXPRESSO-1B-HAJONTA-5MS ajettu 23.9.2026: q1–q4 `pico_dev.py cmd pvent 40` + `pico_dev.py pgap 4.0:50:300:5:10:7485:14970 testit/pgap-20260923-qN.log`, kaukalo tyhjennetty välissä (käyttäjä). Kaikki PGAP_END gaps=50 reason=ok, pmax 8,28 / 9,24 / 9,38 / 8,44. Tulokset kirjattu jo REKISTERI.md rivi "10 vaiheen hajontamittaus" (tila: ajettu 23.9.2026).
  - Shelly Plus 1PM älyjatkojohdossa hubin PD-laturin katkaisijana (käyttäjä rakensi): liitetty HA:han Bluetooth-löydöllä (Shelly-integraatio provisioi Wi-Fi:n), IOT_SSID, DHCP 192.0.2.21, MAC AA:BB:CC:DD:EE:FF, entiteetti `switch.shellyplus1pm_example`, teho `sensor.shellyplus1pm_example_power`. Wi-Fi-avain luettiin `uci get wireless.wifinet4.key` suoraan HA-kutsuun, ei tulostettu. Kirjattu PICO-HALLINTA.md §8.
  - `pico_dev.py`: VÄLIAIKAINEN laturikierto (käyttäjän päätös 23.9.2026): `ChargerOff` jokaisen operaation ympärillä (otg_switch=1, Shelly pois HA:n `ha.sh` kautta, odottaa Picoa `2e8a` ≤ 30 s, lopuksi laturi päälle myös virheessä); uudet komennot `restore <setti>` (flash, odottaa RESTORE_OK/FAIL/FLASH_BLOCKED logcatista) ja `charger on|off`. Pois käytöstä: `CHARGER_CYCLE = False` tai `PICO_CHARGER_CYCLE=0`, kun Type-C-vika korjattu. Todennettu `cmd pgap:stop 3` → CHARGER off / CMD_OK pgap:stop / CHARGER on. Kirjattu PICO-HALLINTA.md §8.
  - Puhelimen latausraja 70 % → 80 % (käyttäjän pyyntö): LineageOS 23.2 (Android 16 userdebug) LineageHealth ChargingControl, tila 3, provider Toggle; `content insert --uri content://lineagesettings/system --bind name:s:charging_control_charging_limit --bind value:s:80`; `dumpsys lineagehealth` → Limit: 80. Kirjattu PICO-HALLINTA.md §8.
  - KAYTTAJAN-TIEDOT.md: uudet TILAUS-I (verkossa pysyminen paineesta, korjaus tunnetulla viiveellä 37–41 ms) ja TILAUS-J (sisäinen kello seuraa verkkotaajuutta rinnalla myös pumpun ollessa pois, 49,9–50,1 Hz), käyttäjän lainaukset. `vaatimukset.mjs --rivi` → 10 vaatimusta.
  - `paketit/VERKKOKELLO.md`: suunnitelma (NCO + paineesta korjaava PI-vaihelukko, pito pumpun ollessa pois, täydet jaksot kunnes lukko palaa, alkulukitus esiuutossa). `vaatimukset.mjs --tarkista` ok. REKISTERI.md rivi "Vaihe 1a3" päivitetty viittaamaan siihen.
  - REKISTERI.md Avoimet asiat: uusi rivi "Huoltotoiminnot sovellukseen ja HA:han" (sitruunahappokäsittely + backflush, käyttäjä 23.9.2026) — jo kirjoitettu.
  - Autonomiaohjeiden haku (käyttäjän pyyntö): palvelin + Mac (ssh dev-host) repot, git-historia, kaikki transkriptit, muisti — ei löytynyt kirjattua menetelmää USB-palautukseen eikä kaukalon tyhjennykseen; löytyi vain yleisvaatimus KAYTTAJAN-TIEDOT.md §7 (17.9.2026).
  - ratkennut (Avoimet asiat): Uuden hubin toimiva kytkentä ja järjestys — Korvattu Shelly-menettelyllä ja ChargerOffin otg_switch-tarkistuksella (PICO-HALLINTA.md §8).
  - ratkennut (Avoimet asiat): otg_switch nollautuu — Korvattu Shelly-menettelyllä ja ChargerOffin otg_switch-tarkistuksella (PICO-HALLINTA.md §8).
  - päätös (ei rekisteriin): 1b-sarja ajettiin tyhjennyksin, ei kaukalovahdin flashausta ensin (käyttäjä).
- 22.9.2026 — EXPRESSO-TURVA-TOIMILAITE (TURVAKATO kohta 1) commit f159f12, ei flashattu: pico/relayguard.py (RelayGuard, GuardedRelay), BrewData.get_relays() antaa pumpun ja lämmittimen vartioituina; machine.Timer 100 ms; pstep/pgap/plen kaukalo ajon aikana (functions.tray_guard_poll + main.scale_poll_once). Kuumavesisilmukka lukee lämmön 1 s välein. Yksityiskohdat REKISTERI.md "Todettu 22.9.2026 — EXPRESSO-TURVA-TOIMILAITE" (jo rekisterissä).
  - EXPRESSO-ANTURIUSKOTTAVUUS (TURVAKATO kohta 5) commit 819bb8f, ei flashattu: raakapaine < -1,5 bar 3x → pumppu pois; lämmitin 120 s ilman 2 °C nousua (>5 °C alle tavoitteen, pumppu pois) → pois uudelleenkäynnistykseen asti. Jo rekisterissä ("Todettu 22.9.2026 — EXPRESSO-ANTURIUSKOTTAVUUS").
  - Käyttäjä (rd-tila) käski jatkaa vaiheen 1b hajonnan selvitystä 5 ms tauolla ja ajaa 10 vaiheen testin uudestaan. Käyttäjän alkuperäinen tilaus 20.9.2026 (transkripti 1f997ae0 rivi 1549): "suunnittele 10 eri vaihe askeleella tehty hajonta testi jaettuna vaihe alueelle 7485 - 14970". Vanhat ajot pgap-20260920-q1…q4: gap_us=5000, phases=10, 7485–14970 µs, 50 taukoa/ajo, 20/vaihe; kelvoton (perustaso 0,59–6,04 bar).
  - Käyttäjä valitsi: yksi ajo kerrallaan vanhalla firmwarella, kaukalo tyhjennetään välissä. Komento: `pico_dev.py cmd pvent 40` + `pico_dev.py pgap 4.0:50:300:5:10:7485:14970 testit/pgap-20260922-qN.log`. q1 ajettu 08:4x → PGAP_FAIL reason=no_end, 0 riviä: Pico ei yhteydessä, mitään ei ajettu laitteella. Tyhjä loki poistettu.
  - PICO-HALLINTA.md §8 päivitetty: uusi hubi UGREEN Uno USB-C Hub 8-in-1 (https://www.aliexpress.com/item/1005007462882759.html), OTG-diagnoosi ja etäkorjauksen rajat.
  - Rekisteristä siirretty historiaan: 21.9.2026:n TURVAKATO-selvityksen ja PIKAKORJAUSTEN Todettu-luvut (sisältö jo alla, 21.9.2026).
  - ratkennut (Avoimet asiat): TURVAKATO kohta 1 EXPRESSO-TURVA-TOIMILAITE (juurisyy) — Toteutettu commitissa f159f12 (RelayGuard, GuardedRelay, machine.Timer 100 ms, kaukalon ja kuumaveden vartiointi); flashaus siirretty osaksi yhteistä flashaus-riviä.
  - todettu (ei rekisteriin): 22.9.2026: dumpsys usb `connected=false`, `data_role=no-data`, viimeinen USB-tapahtuma 21.9.2026 11:04. sysfs `/sys/class/power_supply/usb/otg_switch=0`; dmesg: PD=1 neuvoteltiin, roolinvaihto (`pr_swap_in_progress`) → `USB Type-C disconnect` → `typec_disable_cmd_work`, `chip->otg_switch=0` → laturitila USB_DCP.
  - todettu (ei rekisteriin): `adb root` + `echo 1 > otg_switch` toimii (dmesg `oplus_set_otg_switch_status: otg_switch=1`), mutta ei käynnistä uutta Type-C-tunnistusta. Ei toimi: typec_power_role vain luku (SELinux), `dumpsys usb set-port-roles otg_default sink host` ja `source host` "unsupported role combination", usbpd0 current_pr=none (hard_reset ei käytössä), otg_switch 0→1. `adb reboot`: otg_switch palaa 0:aan ja roolin…
  - todettu (ei rekisteriin): settings global/system/secure eikä getprop sisällä OTG-avainta.
  - todettu (ei rekisteriin): OxygenOS:n OTG-yhteyden 10 min automaattinen sammuminen: yleistieto, ei todennettu tällä puhelimella.
  - päätös (ei rekisteriin): Vianmääritys otg_switch-arvoon perustuen; fyysinen irrotus/kiinnitys otg_switch=1 aikana on jäljellä oleva askel (ei setenforce 0:aa — tietoturva-asetus).
  - päätös (ei rekisteriin): 1b-uusinta tehdään yksi ajo kerrallaan (käyttäjä), koska laitteella on yhä vanha firmware ilman ajonaikaista kaukalovahtia; 20.9.2026 juuri tämä sarja tulvi.
### 21.9.2026 — TURVA-PIKAKORJAUKSET tehty koodissa, ei flashattu (EXPRESSO-TURVA-PIKAKORJAUKSET)

TURVAKATO-korjauslistan kohta 3 toteutettiin. `fast_heatup(utime, asyncio, brew_data)` sai
`asyncio`-parametrin (ennen NameError heti pumpun päällekytkennän jälkeen) ja
`try/finally`-lohkon, joka sammuttaa pumpun, venttiilin ja lämmittimen; `main.py`:n kutsu
päivitettiin. Asetuslämpötilan katto 150 °C lisättiin `classes.py`:hen (`SETPOINT_MAX_C`,
`_check_setpoint`) `set_brew_temperature`- ja `set_steam_temperature`-asettajiin, joten `bt:`,
BLE ja `settings.txt` kulkevat sen kautta (None sallitaan, vanha settings.txt). `pgap` sai
väliraajan ≤ 2000 ms (`PGAP_SPACING_MAX_MS`, `commands.py`) ja koko ajon katon 120 s
(`PGAP_RUN_MAX_MS`, `reason=timeout`). `_psweep_trim`:n raakanäytteen ylipaineraja 11,0 bar
(`PCAP_OVER_BAR`); pumppu kytketään takaisin vain kun `reason` on ok/timeout, muuten pois.
`mains_calibrate`:n kaappaussilmukkaan sama 11,0 bar -raja (`reason=overpressure`). `main.py`:hin
uusi `dev_run(coro)`-kääre (silmukan ulkopuolella, ei allokointia kierroksella), joka sammuttaa
lämmittimen ennen jokaista kymmentä testikomentoa (pcal, pzero, pcap, psweep, pvent, plen, pgap,
pstep, mcal, phold); termostaatti asettaa lämmittimen uudelleen joka `run()`-kierroksella, joten
tila palautuu itsestään. Uusi testi `testit/turva_pika_smoke.py` (26 tarkistusta,
devsafe-valemoduuli).

Testit: `testit/turva_pika_smoke.py` 0 failed; vanhat kahdeksan smokea (phold, mcal, psweep,
psweep_mult, tray_guard, tray_total, pskip_gate, scale_rate) 0 failed; `py_compile` ok
(functions, commands, classes, main). Laitteella ajamatta. Sivuhavainnot: `api_functions.py` ei
ole importattu mistään (kuollut koodi); termostaatti (`classes.py` `Thermostat.run`) kirjoittaa
`RELAY_HEATER`-arvon joka kierroksella.

Päätökset: lämpötilaraja laitettiin asettajiin eikä vain `bt:`-komentoon, jotta mikään polku ei
ohita rajaa (TURVAKATO kohta 2 -periaate); `pgap`:lle ajonaikainen katto komennon rajan lisäksi,
120 s = `PHOLD_MAX_S`; `tshot` ja kahvikytkinpolku jätettiin `dev_run`:n ulkopuolelle, koska
`run_shot` käyttää lämmitintä tarkoituksella.

Rekisteriin: uusi Todettu-luku laajennettuna kahdella sivuhavainnolla, Päätökset-luvun kolme
uutta riviä, Viat-luvun TURVAKATO-rivi merkittiin osittain korjatuksi koodissa (ei flashattu) ja
sen jäljellä oleva osa eriteltiin, uusi Viat-rivi `settings.txt`-validoinnista, Avoimiin kaksi
uutta riviä (`fast_heatup` yhä ilman rajoja; TURVAKATO kohta 1), SEURAAVA PAKETTI vaihdettiin
EXPRESSO-TURVA-TOIMILAITTEEKSI.

Muutokset eivät olleet committoituna pakkaushetkellä: `M Infra/iot/expresso/REKISTERI.md`,
`M paketit/TURVAKATO.md`, `M pico/classes.py`, `M pico/commands.py`, `M pico/functions.py`,
`M pico/main.py`, `?? testit/turva_pika_smoke.py`.

### 21.9.2026 — TURVAKATO-selvitys valmis, KAUKALOVAHTI-KOKONAISPAINO toteutettu koodissa (EXPRESSO-TURVAKATO, EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO)

EXPRESSO-TURVAKATO-selvitys tehtiin koodiluvulla (ei laitteella). Tulokset kirjoitettiin
`paketit/TURVAKATO.md` lukuihin "Selvitys 21.9.2026 — tulokset" (kohdat 1–5 + claude siirto -tila)
ja "Korjauslista" (7 kohtaa); tila-rivi päivitettiin. Rekisteriin: TURVAKATO-rivi Avoimissa →
"selvitys tehty", Viat-lukuun kaksi riviä (turva-aukot; OHJEVAHTI-ristiriita).

EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO toteutettiin koodissa, EI flashattu laitteelle (käyttäjän
päätös: myöhemmin): `pico/functions.py`:n `tray_guard_start` vaatii nyt `wmax`:n (≤0 →
`nolimit`, pelkkä `wrise` ei riitä) ja kieltäytyy, jos paino on jo ≥ `wmax` (`tray`, ei releitä);
`mains_calibrate` (`mcal`) kutsuu `tray_guard_start`:n ennen releitä ja `tray_guard_recheck`:n
kaappauksen jälkeen; `pico/main.py`:n tshot-polku kutsuu `tray_guard_start`:n ennen ajoa eikä
enää tulosta `TS_END loops=0 max_loop_ms=0 reason=<syy>`. Uusi testi `testit/tray_total_smoke.py`
(pelkkä `wrise` → `nolimit`, täysi kaukalo → `tray`, kertymä kuudella ajolla, `mcal`);
`testit/tray_guard_smoke.py`:n `wrise`-tapaus ajetaan nyt `wmax=5000`:lla.

Testit: `tray_total_smoke.py` vanhalla (HEAD) `functions.py`:llä 11 failed, uudella 0;
`tray_guard_smoke.py` 0; `scale_rate_smoke.py` 0; ast-syntaksi ok. Rekisteriin: SEURAAVA PAKETTI
vaihdettiin EXPRESSO-TURVA-PIKAKORJAUKSIKSI, "wrise ajokohtainen" -vikarivi merkittiin korjatuksi
koodissa, Avoimiin lisättiin "KOKONAISPAINO flashaus", Tilanne-päivä 21.9.2026.

Päätökset: korjausjärjestykseksi valittiin ensin KOKONAISPAINO, ei suositellut pikakorjaukset;
`pcal` jätettiin vahdin ulkopuolelle (sovelluksen kalibrointivelho, kuuluminen testeihin on
käyttäjän päätös); kahvikytkin ja kuumavesikytkin jätettiin koskematta; flashaus lykättiin
käyttäjän päätöksellä.

Muutokset eivät olleet committoituna pakkaushetkellä: `M Infra/iot/expresso/REKISTERI.md`,
`M paketit/TURVAKATO.md`, `M pico/functions.py`, `M pico/main.py`,
`M testit/tray_guard_smoke.py`, `?? testit/tray_total_smoke.py`.

### 20.9.2026 — laiteajon yritys ei tuottanut invarianttia, mutta neljä uutta komentoa, viivemittaus ja kaksi vikakorjausta (EXPRESSO-PWM-1B-LAITEAJO)

Vaiheen 1b laiteajo yritettiin ja se ei tuottanut invarianttia. Sen sijaan istunnossa
rakennettiin neljä uutta laitekomentoa, korjattiin kaksi vikaa olemassa olevasta koodista ja
mitattiin kolme asiaa, joita ei aiemmin ollut mitattu. Kahdeksan firmware-settiä rakennettiin ja
flashattiin, jokainen `VERIFIED 17/17`. Muutokset olivat vielä committoimatta tämän pakkauksen
hetkellä (`git status`).

Uudet laitekomennot (`pico/commands.py`, `pico/classes.py`, `pico/functions.py`, `pico/main.py`):
`pstep:<bar>[:<hold_ms>[:<tail_ms>]]` (nousu tavoitteeseen, yksi ohitettu verkkojakso, merkitsee
ohituskäskyn hetken näytteen tarkkuudella), `pgap:<bar>[:<n>[:<spacing_ms>[:<len_ms>[:<phases>[:<lo_us>:<hi_us>]]]]]`
(useita taukoja kierrätetyillä vaiheilla, vaiheen aloitus mikrosekunnin tarkkuudella), `plen:<bar>[:<reps>]`
(tauon pituuden pyyhkäisy 6–36 ms, 2 ms askelin) ja `pvent` (pelkkä purkusykli ilman pumppausta,
TILAUS-H kohta 3). Isäntätyökaluun `pico_dev.py` lisättiin verbit `pstep`, `pgap`, `plen`. Uusi
analysaattori `testit/pstep_read.py` itsetestillä (`--selftest`, virhe +1…+2 ms kolmella tunnetulla
viiveellä). 46 uutta lokia `testit/`-hakemistoon.

Mittaukset (tarkat luvut alla, siirretty rekisteristä tänne 21.9.2026 rivikaton takia): viive
ohituskäskystä paineen pudotukseen 42 ms (hajonta 9 ms), pumpun sammutuksen viive 38 ms (hajonta
7 ms) — kumoaa säännön 14 mitoitusperusteen (ennuste oli 70–90 ms). Katkaisu kvantisoituu
verkkojakson (19,96 ms) kohdalla, porras 2,1-kertainen. Käsketty vaihe ei vaikuta mitattavasti
kolmessa riippumattomassa mittauksessa. `mcal`:n 0,5 s:n ikkuna on liian lyhyt — vahvistaa
vaiheen 1g:n vaatimuksen vähintään 2000 näytteestä.

Todettu / mitattu 20.9.2026 — viivemittaus, katkaisun kvantisointi, vaiheriippuvuus ja
mcal-ikkuna (rekisterin entinen tilaluku, siirretty tänne kokonaisuudessaan):

- **Viive ohituskäskystä paineessa näkyvään pudotukseen: 42 ms, hajonta 9 ms** (neljä ajoa,
  `pstep-20260920-a,d,e,f`). Sama ajo antaa riippumattoman toisen luvun pumpun sammutuksesta:
  **38 ms, hajonta 7 ms**. Kaksi eri tapahtumaa 4 ms:n sisällä toisistaan. Analysaattorin oma
  vinouma +1…+2 ms, joten todellinen viive on noin 37–41 ms. Pudotuksen signaali-kohinasuhde
  4,7–9,6, sammutuksen 53–113.
- **Tämä kumoaa säännön 14 mitoitusperusteen.** Kuivaharjoituksen laitosmalli ennusti 70–90 ms, ja
  portin jakso pidennettiin kahdeksaan verkkojaksoon sen nojalla. Todellinen viive on noin puolet
  ennustetusta; `mult = 4` (79,84 ms) riittäisi.
- **Katkaisu kvantisoituu, eikä ohjelmisto pääse valitsemaan katkaisukohtaa** (`plen-20260920-a`,
  16 pituutta × 2 toistoa). Käsketty tauon pituus vs. pudotuksen syvyys:

  | Pituus | Syvyys |
  |---|---|
  | 6–18 ms | 0,32–0,46 bar |
  | 20–36 ms | 0,77–0,88 bar |

  Porras on 2,1-kertainen ja tapahtuu tasan verkkojakson (19,96 ms) kohdalla. Vapaavaiheinen
  ajuri antaisi tasaisen ramppin; porras on kvantisoinnin allekirjoitus. Toinen toisto ajettiin
  vakiopaineessa 9,8–10,0 bar ja näyttää saman portaan yksinään.
- **Kun tauko on 20 ms tai yli, pohjan kohta on 64–68 ms** viidessätoista peräkkäisessä ajossa.
  Alle 20 ms:n tauoilla se hajoaa (5–185 ms).
- **Käsketty vaihe ei vaikuta mitattavasti.** Kolme riippumatonta mittausta:
  - 4 vaihetta × 3 toistoa, 20 ms tauko: syvyyden keskiarvot 0,750–0,796, keskivirhe 0,043.
  - 8 vaihetta × 6 toistoa, 5 ms tauko (`pgap-20260920-n`): keskiarvot 0,588–0,687, hajonta
    vaiheen sisällä 0,142–0,224. Vaiheiden välinen ero on pienempi kuin kohina vaiheen sisällä.
  - 10 vaihetta välillä 7485–14970 µs × 20 toistoa (`pgap-20260920-q1…q4`, 200 taukoa): hajonta
    0,415–0,913, suhde 2,20× ja n=20 vaatisi 2,1×. **Tulosta ei saa käyttää**: perustaso vaihteli
    näiden 200 tauon välillä 0,59–6,04 bar, eikä vertailua ehditty rajata samaan painealueeseen.

  Huom: 20 ms:n tauko ei voi vastata vaihekysymykseen lainkaan, koska se poistaa molemmat
  puolijaksot. Ensimmäinen vaihekoe tehtiin sillä, ja sen nollatulos oli väistämätön.
- **`mcal`:n 0,5 s:n ikkuna on liian lyhyt.** Kolme `mcal:500`-ajoa antoivat f = 48,804 / 50,027 /
  50,161 Hz ja `conf = 1,02` joka kerta (raja 2,0). Hajonta 1,36 Hz. Vaiheen 1g ennuste oli
  ≤ 0,07 Hz **2,0 s:n** ikkunasta, joten tämä vahvistaa sen eikä kumoa: `mcal` tarvitsee
  vähintään 2000 näytettä.
- **Tasapaino vaihteli istunnon aikana ilman että kuristinta säädettiin joka kerta:** 5,55 → 7,3 →
  9,2 → 8,8 → 4,87 bar. Vesi loppui kesken istunnon; imu palautettiin ajamalla pumppua täydellä
  teholla (`phold 25`, `phold-20260920-imu.log`).

Korjatut viat: `_psweep_trim` päättyi riviin `RELAY_SOLENOID.value(0)`, vaikka
`pressure_sweep_run` avaa venttiilin `value(1)`:llä ennen pumppua — ensimmäisen trimmauksen
jälkeen kaikki loput segmentit ajettiin eri venttiilitilassa, eikä tilaa palautettu koskaan. Sama
rivi kopioitui `pgap`:n purkuaskeleeseen ja aiheutti siellä välittömän ylipaineen (11,38 bar).
Molemmat korjattu.

Vesivahinko: kaukalovahdin `wrise` on ajokohtainen eikä estä kertymää yli ajojen; neljä
peräkkäistä ajoa sai kukin oman 250 g nousuvaransa, kaukalo ylitti reunansa ja vettä valui koneen
ympärille. Johti seuraavaan pakettiin EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO.

Prosessi: istunnossa poikettiin käyttäjän ohjeesta useasti (40 taukoa 20:n sijaan, paineen säätö
vaikka ohje kielsi, kaukalon tyhjennys ajojen välistä jäi väliin), ja viimeinen johti
vesivahinkoon. Käyttäjä totesi, ettei tähän istuntoon voi luottaa autonomisessa ajossa.

### 19.9.2026 — vaihesiirtopyyhkäisyn suunnittelu ja toteutus, mcal-taajuuskalibrointi, TILAUS-H kirjattu (EXPRESSO-PWM-1B-PYYHKAISY)

Neljäs pakkaus samassa sessiossa; edellinen (`EXPRESSO-PWM-1B-LAITEAJO`) kattaa commitin `cf1358b`
edeltävän puolen — tarkemmin: tämä pakkaus kattaa commitit `95d3e86`..`cf1358b` (16 committia)
skoopin osalta, koska edellisen pakkauksen jälkeen syntyneet commitit (`9144894`, `3d81309`) olivat
jo tuon pakkauksen ulkopuolisia ja tulevat tässä mukaan taustatietona (KAYTTAJAN-TIEDOT.md luku 2b,
tilauksen menetelmäkohdat invarianteiksi).

Vaihe 1b:n pyyhkäisy suunniteltiin, toteutettiin ja landattiin neljänä r&d-pakettina:
`PWM-1B4-PYYHKAISY` (firmware `psweep`, commit `c51de5a`), `PWM-1B5-INVARIANTTI` (analysaattori
`psweep_read.py`, commit `aa6aedc`), `PWM-1B6-PORTTIJAKSO` (portin jakso mittausparametriksi,
commit `17359ab`), `PWM-1G-TAAJUUSKALIBROINTI` (`mcal`, ajonaikainen taajuus+vaihe, commit
`cf1358b`). Paketin `paketit/PUMPPU-PWM.md` säännöt 10-14 kirjoitettiin, ja säännöt 5, 7 ja 9
korjattiin mittausten perusteella. Uudet holdoutit ennen toteutusta: `testit/psweep_smoke.py`
(22 punaista), `psweep_fixture.py`, `psweep_mult_smoke.py` (11 punaista), `mcal_smoke.py`. Uusi
työkalu `testit/psweep_dryrun.py` ajaa oikean firmware-korutiinin laitosmallia vasten
virtuaalikellolla. Neljä korjausmuistiota syntyi kierroksen aikana: 1B4 korjaus 1, 1B6 korjaus 1,
1G korjaukset 1-2 — kolmesti este löytyi suunnittelijan omasta artefaktista (rekisterin Viat-luku).

Setti `20260919-psweep1` rakennettiin ja flashattiin: `RESTORE_OK … n=17`, `pico_dev.py verify`
puhelimen manifestia vasten `VERIFIED 17/17`. Mittausajoa ei ajettu — keitin ei ollut
käytettävissä tässä sessiossa, joten sääntö 9:n invariantin kysymys jää yhä auki laitteella
(SEURAAVA PAKETTI).

Käyttäjän uusi tilaus (taajuuden itsekorjaus ajon aikana, TILAUS-H) kirjattiin lainauksina
`KAYTTAJAN-TIEDOT.md` lukuun 2b (commitit `3eb0de5`, `e8a5012`); menettely: jaksotus jatkuu
kunnes lasku syklin yli alle `PCAP_PLATEAU_BAR` 0,15 bar, ei suunnittelijan ehdottama kiinteä
0,3 barin raja tai 10 kierroksen katto.

Ratkenneet viat: portitettu `pcap` päättyi aina syyhyn `scalelost` — `tray_guard_recheck` hakee
kaappauksen jälkeen tuoreen lukeman (commit `c51de5a`). Jäännöspaine kaatoi ajot
`overpressure`-syyhyn — trimmausaskel segmenttien välissä (commit `c51de5a`).

Todettu: säännön 9 invariantin modulus on verkkojakso 19 960 µs, ei portin jakso; (A):ta ja
(B):tä ei voi erottaa tällä asetelmalla, koska paineväreily on vastaus, ei sytytys (`refdelay`
asettui nollaan); portin jakso 39,92 ms on lyhyempi kuin koneen viive, joten taitos alias
kiertää (kuivaharjoitus 8× antoi 81,8-93,8 ms tosiarvoa 79 ms vasten); `mcal` mittasi verkosta
50,298 Hz (malli 50,30 Hz), ja oikea hilasäätö on askel ≈ 1/(2T), ei "pidempi ikkuna = tarkempi"
(rekisterin Todettu/mitattu-luku).

Päätökset: kuristimen käsin tasapainotus (sääntö 7) ei ole vaiheiden 1b-1f ehto; SSR-40DA:n
kyljen tarkistus poistettiin tehtävistä (jälleenmyyjän speksit ristiriitaiset); säännön 5 suure
(B) on 0-9,98 ms, ei 0-19,96 ms; vaihe 1g rajattiin mittaukseen ja `mcal`-komentoon, kytkentä
esiuuttoon on vaihe 1h (rekisterin Päätökset-luku).

Muutokset eivät olleet committoituna pakkaushetkellä: `.gitignore`, `claude/filter/REKISTERI.md`
ja `Infra/linux/grub-windows-oletus.sh` puussa, mutta ne ovat toisen keskustelun tiedostoja — ei
koskettu. Tämän skoopin 16 committia (`95d3e86`..`cf1358b`) ovat kaikki jo tehtyjä ja pushattuja.

### 19.9.2026 — pumpun PWM vaihe 1b laiteajo: sääntö 9:n invariantti ei toteudu laitteella (EXPRESSO-PWM-1B-LAITEAJO)

Kolmas pakkaus samassa sessiossa; edellinen (`EXPRESSO-SCALE-POLL`) kattaa commitin `7335d16`
asti, tämä vain sen jälkeisen työn.

Paketti `EXPRESSO-PWM-1B-LAITEAJO` ajettiin kokonaan: setti `20260919-pskip2` rakennettiin
(`build_set.py`, 16 tiedostoa + manifesti), flashattiin (`RESTORE_OK 20260919-pskip2 n=17`) ja
todennettiin (`VERIFIED 17/17`). Kaukalovahdin rajat asetettiin ja todennettiin laitteen
`settings.txt`:stä: `weight_limit: 720.0`, `weight_rise_limit: 250.0` (ritilä paikallaan,
käyttäjän valinta). Kuristin avattiin tasapainoon `phold`-ajoilla
(`testit/phold-20260919-1b-{a,b,c,d}.log`). Viisi portitettua kaappausta vaihesiirroilla 0, 8000,
16000, 24000, 32000 µs (`testit/pcap-20260919-p{0,8000,16000,24000,32000}.log`, kaikki `n=2000`)
ja toistokoe kahdella lisäajolla vaihesiirrolla 0 (`pcap-20260919-p0-toisto{1,2}.log`). Repon
`pico/MANIFEST.json` päivitettiin puhelimen setin `20260919-pskip2` manifestista. Kireämmästä
venttiiliasennosta otettu kaappaus säilytettiin nimellä `pcap-20260919-p0-kirea.log`
(`PSKIP_DELAY 29,4 ms conf=9,35`), koska se ei ole vertailukelpoinen muiden kanssa. Isäntätestit
vihreät ennen laiteajoa: `pskip_delay`, `pskip_gate_smoke`, `tray_guard_smoke`,
`scale_rate_smoke`, `phold_smoke`, `mains_freq` — `RESULT: 0 failed`.

Tulos: sääntö 9:n invariantti (`PSKIP_DELAY(p) = (todellinen viive + p) mod 39920 µs`, mitattu
edellisessä pakkauksessa fikstuurilla) ei toteudu laitteella — `(PSKIP_DELAY − p) mod 39,92 ms`
hajoaa 39,4:stä 2,4 ms:iin viiden vaihesiirron yli sen sijaan että pysyisi vakiona tai
askeltaisi ~20 ms:n portaissa (rekisterin Todettu/mitattu-luku, Päätökset-luku). Kolme uutta
vikaa löytyi laiteajossa: `build_set.py` ei kirjoita manifestia repoon (väärä `MISMATCH`),
portitettu `pcap` päättyy aina syyhyn `scalelost`, ja jäännöspaine ajojen välissä keskeytti
yhdeksän kaappausyritystä `overpressure`-syyllä (rekisterin Viat-luku).

Muutokset eivät olleet committoituna pakkaushetkellä: `M Infra/iot/expresso/pico/MANIFEST.json`
ja 12 uutta lokitiedostoa `testit/`-hakemistossa. Puussa oli kolme tämän skoopin ulkopuolista
muutosta toisesta keskustelusta (`.gitignore`, `claude/filter/REKISTERI.md`,
`Infra/linux/grub-windows-oletus.sh`) — ei koskettu.

### 19.9.2026 — vaa'an lukutahti 20 ms → 50 ms (EXPRESSO-SCALE-POLL)

Toinen pakkaus samassa sessiossa; edellinen kattaa commitin `53994bc` asti (vaiheen 1b briefit,
laiteajo, kaukalovahti), tämä vain sen jälkeisen työn.

`EXPRESSO-SCALE-POLL` ajettiin ja landattiin (commitit `b3cf54f`, `4ed997a`, mittausrivi
`paketit/delegation.jsonl`): vaa'an lukutahti nimettiin vakioksi `SCALE_POLL_MS` ja muutettiin
20 ms:stä 50 ms:iin. Hyväksyntä 5/5, budjetti 355/365, iterations 1, ei korjauksia.
`testit/scale_rate_smoke.py` kirjoitettiin suunnittelijan holdoutiksi ennen toteutusta: se lukee
vakiot kolmesta tiedostosta tekstinä (`scale.py` ja `main.py` eivät ole tuotavissa CPythonilla,
`import machine`) ja tarkistaa neljä invarianttia.

Rekisterin `## Päätökset`-lukua muokattiin poikkeuksellisesti suoraan committiin `4ed997a`
pakkauksen jälkeen syntyneen päätöksen takia (normaalisti rekisteriä kirjoittaa vasta pakkaus).

Muutetut polut (kaikki committoitu ja pushattu, commitit `53994bc`..HEAD: `b3cf54f`, `4ed997a`,
mittausrivicommit): `Infra/iot/expresso/pico/main.py`, `REKISTERI.md`,
`paketit/SCALE-POLL.brief.md`, `paketit/delegation.jsonl`, `testit/scale_rate_smoke.py`.

Puussa oli kolme tämän skoopin ulkopuolista muutosta toisesta keskustelusta (`.gitignore`,
`claude/filter/REKISTERI.md`, `Infra/linux/grub-windows-oletus.sh`) — ei koskettu.

### 19.9.2026 — pumpun PWM vaihe 1b briefit valmiit, kaukalovahti lisätty turvakorjauksena

Vaiheen 1b säännöt 5-9 ja protokollalisäys paketoitiin `paketit/PUMPPU-PWM.md`:hyn
(commit `bb62158`, `6464ade`). Kolme briefiä ajettiin r&d-delegoinnilla, kaikki acceptance 0
(`paketit/delegation.jsonl`, commit `be1a1ad`):

- `PWM-1B1-PHOLD` (commit `8614f48`): komento `phold:<s 1-120>` ajaa pumppua ja venttiiliä
  vapaasti, tulostaa 500 ms välein `bar`, `filt` ja `slope`. Iterations 2, korjaus 1
  (`pressure_hold_run` luki `SWITCH_BREW/WATER/STEAM` sitomatta niitä `get_switches()`:llä →
  olisi kaatunut `NameError`iin laitteella).
- `PWM-1B2-PORTITUS` (commit `15850bc`): `pcap:<ms>:<bar>:<phase_us>` ohittaa joka toisen
  verkkojakson, portti funktiosta `pcap_gate(i, phase_us)`. `PCAP_START` kertoo nyt anturin
  elävän kalibroinnin. Iterations 1.
- `PWM-1B3-ANALYSAATTORI` (commit `ad8fab7`): `testit/pskip_delay.py` lukee viiveen portitetusta
  lokista; `mains_freq.py`:n DRIFT-kalibrointivika korjattu (luki noin barin liian korkeana,
  koska käytti tehdaskaavaa eikä anturin elävää kalibrointia; `parse_log` lukee nyt `gain`/
  `offset` `PCAP_START`-riviltä). Iterations 1.

Neljä suunnittelijan holdout-testiä kirjoitettiin `testit/`-hakemistoon: `phold_smoke.py`,
`pskip_gate_smoke.py`, `pskip_fixture.py`, `tray_guard_smoke.py`. Kolme viimeistä kirjoitettiin
**ennen toteutusta** ja olivat punaisia (7, 11 ja 17 väitettä). Setti `20260919-pskip1`
rakennettiin ja flashattiin, `MANIFEST.json` päivitettiin vastaamaan (commit `90ac4b8`), Pico
todennettiin `VERIFIED 17/17`. Ensimmäinen laiteajo `phold 60` lokitettiin
(`testit/phold-20260919-tasapaino.log`, commit `8018b50`).

Turvakorjaus `EXPRESSO-KAUKALOVAHTI` kirjoitettiin, ajettiin ja landattiin (commit `1ab54da`) sen
jälkeen kun laiteajo tulvitti kaukalon: kaukalon painoraja oli olemassa mutta vain testiuuton
polulla (`functions.py:152-181`, ehto `if limit_weight:`, tosi vain `tshot`-polulta), ja `phold`
sekä `pcap` pumppasivat ilman sitä. `paketit/TURVAKATO.md` avattiin selvittämään, miten
turvaominaisuus katosi uuden komennon myötä (selvitys tekemättä, käyttäjän päätös).

11 committia `ebb7eec`..`1ab54da`: `bb62158`, `7522599`, `8614f48`, `35aa737`, `15850bc`,
`6464ade`, `ad8fab7`, `be1a1ad`, `90ac4b8`, `8018b50`, `1ab54da`. Työpuu on puhdas oman työn
osalta; kolme toisen keskustelun tiedostoa (`.gitignore`, `claude/filter/REKISTERI.md`,
`Infra/linux/grub-windows-oletus.sh`) eivät ole tämän skoopin muutoksia.

### 19.9.2026 — pumpun PWM vaihe 1a valmis: verkkotaajuus mitattu koneelta 50,1 Hz

Käyttäjän tilaus 19.9.2026 oli nelivaiheinen (pumpun PWM 1a–1f, pre-infusion time auto, max flow
rate, höyryn lämpötila); tässä sessiossa tehtiin vaihe 1 kohta a kokonaan, r&d-delegointina.

- Uusi sateenvarjopaketti `paketit/PUMPPU-PWM.md`: neljä tilattua tehtävää, vaihejako 1a–1f/2/3/4,
  säännöt ja mittaustulokset.
- Kontekstiraportti `paketit/PUMPPU-PWM-KONTEKSTI.md` (rd-context, Sonnet, 144 riviä).
- Firmware: `pcap:<ms>[:<bar>]`-kaappauskomento (`pico/commands.py`, `pico/classes.py`,
  `pico/functions.py`, `pico/main.py`) — raaka ADC 1 kHz, tapahtumaohjattu asettuminen, pitovaihe,
  `PCAP_SETTLED`/`PCAP`/`PCAP_END`-protokolla.
- Isäntätyökalut: `testit/mains_freq.py` (Goertzel + `DRIFT`-rivi + `--selftest`),
  `pico_dev.py pcap <ms>[:<bar>]`, ja **`build_set.py`** — setinrakennus puhelimeen ja
  `MANIFEST.json` puhelimen `sha256sum`-tulosteesta, `--check` lukevana esitarkistuksena
  (H-067).
- Kolme laiteajoa: setit `20260919-pcap1`, `-pcap2`, `-pcap3` rakennettu, flashattu ja todennettu
  (`VERIFIED 17/17` joka kerta). Lokit
  `testit/pcap-20260919-{verkkotaajuus,tasanne,8bar}.log`.
- 29 committia, viimeisin `ed13c94`. Mittausrivit `paketit/delegation.jsonl` (6 riviä).

Ratkenneet viat:

- `build_set.py`:n `run_as` antoi `sh -c <komento>` erillisinä argumentteina, ja `adb shell`
  liittää argumentit välilyönnillä yhteen → laitteella ajettiin `sh -c ls` ja loput menivät
  positioargumenteiksi. Koski jokaista etäkomentoa (`cp -r`, `find`, `sha256sum`, `stat`). Löytyi
  `--check`-ajolla oikeaa puhelinta vasten ennen yhtäkään kirjoitusta. Korjattu `run_as_argv` +
  `shlex.quote`.
- `pcap` ei avannut magneettiventtiiliä → pumppu olisi ajanut umpinaista piiriä.
- Ylipaineraja ja `pmax` ohittivat anturin kalibroinnin → raja laukesi ~10,0 barissa 11,0:n
  sijaan.

Suunnittelijan virheet, kirjattu:

1. Pyysin käyttäjää pitämään ~5 baria, vaikka pumppu kävi vain 3 s — paine ei ehdi nousta, eikä
   käyttäjä säädä painetta vaan kuristinta; käyttäjä nimesi tämän toistuvaksi virheeksi.
2. `DRIFT`-väite `2,0 ± 0,2 bar` oli aritmeettisesti väärä, oikea on `ramp_bar*(1−w/T) = 1,80`;
   toteuttaja pysähtyi Stop-ehtoon eikä löysännyt lukua.

Työpuu on puhdas oman työn osalta; kaikki 29 committia ovat sisällä. `git status --short` näytti
vain toisen keskustelun tiedostot (`.gitignore`, `claude/filter/REKISTERI.md`,
`Infra/linux/grub-windows-oletus.sh`) — ei koskettu.

### 19.9.2026 — skooppi luotu

- Skooppi `infra expresso` luotiin reitittimeen (`Skoopin sanat`, `Skoopista viitetiedostoon`,
  polkutaulukon rivi `Infra/iot/expresso/** → infra expresso`) ja viitetiedostoon
  (`references/infra.md`, oma luku + lukulistarivi). Rekisteri ja tämä tiedosto luotiin tyhjinä
  runkoina; sisältö siirretään ensimmäisessä purussa.
- Päätökset: oma rekisteri jaetun päärekisterirvin sijaan (käyttäjän valinta), eikä skooppi lue
  infra corea; sisällön siirto tehdään vasta kun `infra iot` on pakattu, jotta siirrettävä tila
  on rekisterissä eikä keskustelussa.
