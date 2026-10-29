# EXPRESSO-WIFI-APPI — iOS-äppi ja keitin Wi-Fin kautta (suunnitelma 20.10.2026)

Käyttäjä 20.10.2026: "Suunnittele huolella expresso ios äppiin ja keittimeen yhteys wifin kautta. Pidä huoli että
kaikki toiminnot säästyy." Päätökset 20.10.2026 (AskUserQuestion):
- **P1:** "Lokit homeassistant mutta äpin yhteys suoraan iphone." — äppi ↔ Pico suoraan; diagnostiikka ja lokit
  kulkevat edelleen DIAGNET-keräimen kautta HA:han (ei siltaa äpin ja Picon välissä).
- **P2:** "Korjataan ensin" — BLE:lläkin rikki olevat toiminnot (T2, T9, T10) korjataan vaiheessa 0 ennen Wi-Fiä.

Tila: suunnitelma, ei toteutettu. Lähteet (kartoitettu 20.10.2026): firmware `pico/bluetooth_handler.py` (BH),
`commands.py` (CMD), `main.py` (M), `brew_logger.py` (BL); äppi Macilla `…/silvia_pico_flutter_UI/lib/` (git cf02bb7):
`features/ble/ble_repository.dart` (BR), `brew_log_notifier.dart`, `core/standby_timeout.dart`,
`machine_data_notifier.dart`, `demo_pico.dart`.

## 1. Lähtötilanne

- Äpin ainoa linkki on `BLERepository` (BR:20-23). UI käyttää siitä `isConnectedStream`, `dataStream` (JSON-oliot),
  `sendCommand(String)`, `requestPendingBrewLog`, `onAppResumed/Paused`, `startScan`, `disconnect`.
  Kuljetusabstraktiota ei ole; `DemoPico` (demo_pico.dart:102-190) on lähin sauma ja protokollan malli.
- Firmwarella BLE ja sarja jakavat `handle_command`-dispatcherin (CMD:12). Pico on Wi-Fissä (DIAGNET): IOT_SSID,
  kiinteä 192.0.2.13 (`dhcp.espresso_pico`), estämätön UDP keräimeen 192.0.2.11:47210 → HA.
- Verkko: iPhone `mgmt`-vyöhykkeellä (192.0.2.x), WireGuard `wg0` samassa; `mgmt → iot` auki → iPhone tavoittaa
  Picon kotona ja VPN:n läpi ilman uusia sääntöjä; Picon vastaukset kulkevat conntrackin `established`-tilassa.

## 2. Toimintoinventaario (säilytettävä joukko)

| # | Toiminto | Äppi lähettää | Pico vastaa | Tila nyt (BLE) |
|---|---|---|---|---|
| T1 | Live-arvot 5 Hz: lämpö, paine, tila, pump_ratio, standby | – | live-paketti 200 ms (BH:67-89) | toimii |
| T2 | Virtaus, paino, kaukalo, automaattitara | – | `flow`/`weight` (BH:92-102) | **rikki: äppi lukee `weight_g`/`weight_abs_g`/`flow_g_s` (V-210)** |
| T3 | Asetusten synkka yhdistettäessä | `sync` ×2 | asetuspaketit A+B (BH:165-182) | toimii |
| T4 | Uuttoasetukset | `pit:` `srt:` `bt:` `pip:` `bp:` `fhu:on/off` | `updated` → asetuspaketit | toimii |
| T5 | Valmiustila | `stby:<min>`, `stbt:<°C>` jokaisen yhteyden jälkeen | RAM | toimii |
| T6 | Uuttoloki puhelimeen | `brew_log?`, `brew_log:ack:<id>` | multipack meta/samples/end (BH:26-58, 269-344) | toimii |
| T7 | Uuton jälkeinen painokehote ja tyytyväisyys | – | lokin saapuminen | toimii (AppDelegate.swift:36-55) |
| T8 | Painekalibrointi | `pcal:run:pre|brew`, `pcal:m:…`, `pcal:save`, `pcal:end` | pcal-tila jokaisella tickillä | toimii |
| T9 | Vaa'an tara | `tare` | – | **puuttuu firmwaresta** (`scale.tare()` scale.py:258, ei komentoa) |
| T10 | Vaa'an kalibrointi | `cal:quick:<g>`, `cal:full:start`, `cal:next`, `cal:cancel` | `cal_phase`, `cal_msg`, `cal_err` | **puuttuu firmwaresta** |
| T11 | Paikalliset: uuttolokit, kaavio, näyttö päällä, asetukset | – | – | toimii, ei linkkiä |
| T12 | Taustatoiminta: loki ja kehote lukitulla puhelimella | – | – | toimii BLE:n `bluetooth-central`-taustatilalla |

Tavoite: jokainen T1–T12 toimii sekä pelkällä BLE:llä että Wi-Fillä (T12 BLE:llä taustalla, luku 5.3).

## 3. Vaihe 0 — BLE:n aukot (P2)

1. **T2 / V-210**: firmware lähettää live-paketissa äpin avaimet `weight_g` (tarattu), `weight_abs_g` (raaka) ja
   `flow_g_s`; vanhat `weight`/`flow` pois, koska kukaan ei lue niitä (todennetaan `grep` äpistä ennen poistoa).
   240 t:n raja (BH:20): mitataan pisin paketti; tarvittaessa paino/virtaus omaan pakettiin kuten nyt (BH:92-102).
2. **T9**: `tare` → `scale.tare()` (scale.py:258); paluu `updated`, jotta live-arvo päivittyy.
3. **T10**: `cal:quick:<g>`, `cal:full:start|next|cancel` ja `cal_phase`-tilakone firmwareen äpin odottamilla
   vaiheilla (full_empty → full_tare_run → full_left_ready/measure → full_right_ready/measure → full_tray_ready/measure
   → full_done; quick_done; error; idle; calibration_view.dart:50-69, 130-150) ja tulos `scale_cal.json`iin.
   Malli: `DemoPico`n toteutus (demo_pico.dart) ja `scale.py`:n nykyinen kalibrointi.
4. **BLE-kirjoituspuskuri**: `gatts_set_buffer(rx, 100)` (nyt 20 t, BH:128-133) — `cal:quick:<g>` ja muut pidemmät
   komennot katkeaisivat muuten.
5. Testit: `testit/vaaka_komennot_smoke.py` (tare, cal-tilakone valevaa'alla), live-avaimet; laitteella äpin
   kalibrointinäkymä ja tara-nappi BLE:llä (XCUITest + käyttäjän kuittaus kaukalon painoista).

## 4. Pico: suora Wi-Fi-kanava (UDP, skooppi infra expresso)

Miksi UDP eikä TCP: Picolla ei yhteystilaa, ei lwIP-yhteyspuskureita eikä asyncio-streamien allokointeja keossa,
jonka viiveitä jäljitetään (uutossa GC 111 ms, BLE-tehtävä 63 ms, 20.10.2026), ja sama estämättömyyssääntö kuin
DIAGNETissä. Luotettavuus hoidetaan protokollassa (seq + ACK + uudelleenyritys), kuten BLE:n write-with-response.

1. **Portti 47211**, `setblocking(False)`, `recvfrom` diag-tehtävässä 100 ms välein (enintään 4 pakettia per kierros),
   `task_busy('diag')`, jotta EU_STALL nimeää tehtävän.
2. **Paketti äpiltä**: `EXA1 <seq> <mac16> <komento>`; `mac16` = HMAC-SHA256(avain, boot|seq|komento) 16 heksaa
   (`hashlib.sha256`, HMAC käsin). Avain Picolla `diag_wifi.py`:ssä (ei repossa). `boot` = DIAGNET-boot-id, jonka äppi
   saa `hello`-vastauksesta (uudelleenkäynnistys mitätöi vanhat komennot). Toistettu seq → sama ACK uudelleen
   (idempotentti). Sallittu joukko = täsmälleen äpin komennot (luku 2 + `hello`, `sub`); kehityskomennot
   (`tshot`, `phold`, `dev:*`…) vain sarjaan.
3. **Avaimen jako**: kerran BLE:n kautta (`wifi:key?` → avain notifyna). Turvataso = BLE:n nykyinen (fyysinen
   läheisyys, ei parittamista); avain Keychainiin. Wi-Fi ei siis avaa mitään, mitä BLE ei jo salli, ja verkossa
   komentoja voi lähettää vain avaimen haltija.
4. **Tilaus**: `sub` (äppi uusii 5 s välein) → Pico lähettää lähettäjän osoitteeseen 15 s ajan: live 5 Hz, asetuspaketit
   A+B (yhdistettäessä, `updated`in jälkeen ja 2 s välein), pcal- ja cal-tila — samat JSON-oliot kuin BLE-notify,
   yksi olio per datagrammi. Enintään 2 tilaajaa. Live-dict rakennetaan kerran tickiä kohti ja jaetaan BLE:n kanssa.
5. **Uuttoloki**: `brew_log?` Wi-Fillä → sama multipack (meta, samples ≤ 20 riviä, end) datagrammeina tilaajalle;
   äpin kokoaja (brew_log_assembler.dart) pyytää `brew_log?` uudelleen, jos osa puuttuu — sama kuin BLE:llä.
   Sama `pending_brew_log`; kumman tahansa linkin `brew_log:ack` vapauttaa.
6. **ACK**: `{"type":"ack","seq":n,"r":"ok|updated|unknown|denied"}`.
7. **Ajoitus**: ei estävää kutsua; ei uudelleenliittymistä uuton aikana; laitemittaus ennen/jälkeen: `max_loop_ms`,
   `gc_max_us`, `EU_STALL task=diag|ble`. Raja: ei pahene yli 10 % simulaatioajosta 20.10.2026 (145 ms / 111 ms).
8. **Testit**: `testit/wifi_suora_smoke.py` — HMAC ja väärä avain, vanha boot, toisto, kielletty komento, `updated` →
   asetuspaketit, tilaus ja vanhentuminen, kaksi tilaajaa, multipack sama kuin BLE:n, kuittaus kummaltakin linkiltä.

## 5. Äppi (skooppi expresso-ios; `lib/` on yhteinen Androidin kanssa)

1. **Rajapinta `MachineLink`** (`isConnectedStream`, `dataStream`, `sendCommand`, `requestPendingBrewLog`,
   `onAppResumed/Paused`, `connect/disconnect`, `deviceSummary`). `BLERepository` toteuttaa sen ilman
   logiikkamuutoksia; uusi `WifiRepository` (`dart:io` `RawDatagramSocket`) toteuttaa saman: `hello` → boot-id,
   `sub` 5 s välein, komennot seq + HMAC + ACK-odotus 300 ms + 3 uudelleenyritystä, vastaanotetut oliot `dataStream`iin.
   Osoite oletuksena 192.0.2.13:47211 (asetuksissa muutettavissa).
2. **`LinkSelector`** (Riverpod; kuluttajat saavat sen `bleRepositoryProvider`in tilalle): asetus
   "Yhteys: Automaattinen / Wi-Fi / Bluetooth" (oletus Automaattinen = Wi-Fi etualalla, kun `hello` vastaa; muuten
   BLE). Vaihto hystereesillä (3 s), ei kesken uuttolokin siirron. Yhteyden alkusarja (`sync`, `sync`, `brew_log?`,
   `stby`, `stbt` — BR:912-920, standby_timeout.dart) ajetaan selectorissa aktiivisen linkin vaihtuessa.
3. **BLE pysyy yhdistettynä rinnalla**: iOS keskeyttää UDP-soketin taustalla, BLE:n `bluetooth-central` ei. T12 jatkuu
   BLE:llä kuten nyt. Duplikaatit: `BrewLogNotifier` ohittaa jo tallennetun lokin (`id` + `duration_ms`).
4. **iOS**: `Info.plist` `NSLocalNetworkUsageDescription` (paikallisverkon lupa), avain `flutter_secure_storage`iin.
5. **UI**: yhteysikoni näyttää linkin (Wi-Fi/BT) ja tilan; asetuksiin yhteysvalinta. Ei muita näkymämuutoksia.
6. **Testit**: Dart-yksikkötestit `WifiRepository`lle (vale-Pico UDP:llä, DemoPicon protokolla) ja `LinkSelector`ille;
   XCUITest simulaattorissa oikeaa Picoa vastaan Wi-Fillä (simulaattori on Macin verkossa → Pico tavoitettavissa):
   T1, T3–T5, T8–T10; BLE-rivit iPhonella.

## 6. Lokit Home Assistantiin (P1)

DIAGNET-keräin jatkaa ennallaan (stdout, DIAG_S, DIAG_HB, DIAG_MIN → tiedostot + `sensor.espresso_diag_*`).
Lisäys: valmis uuttoloki (`BREW_LOG ready`) → HA-tapahtuma `espresso_shot` (kesto, paino, max/keskipaine, lämpö,
`max_loop_ms`) ja `sensor.espresso_last_shot`, jotta HA:n historiassa on jokainen uutto myös ilman puhelinta.

## 7. Vikatilanteet

| Tilanne | Käytös |
|---|---|
| Pico ei Wi-Fissä (AP, reititin) | `hello` ei vastaa → BLE; DIAGNET liittyy uudelleen 30 s välein (ei uuton aikana) |
| UDP-paketti katoaa | komento: ACK + 3 uudelleenyritystä; live: seuraava 200 ms; loki: kokoaja pyytää `brew_log?` |
| Pico käynnistyy uudelleen | uusi boot-id → `hello` uudelleen, seq alusta, alkusarja (`sync`…) |
| Puhelin taustalla | Wi-Fi keskeytyy, BLE jatkaa (T12) |
| Kotiverkon ulkopuolella | WireGuard päällä → Wi-Fi-linkki toimii; ilman VPN:ää → BLE, jos lähellä |
| Keräin/palvelin alhaalla | äpin yhteys ei riipu siitä; vain HA-lokit katkeavat |
| BLE ja Wi-Fi yhtä aikaa | Pico palvelee molempia; asetusmuutos kummaltakin → asetuspaketit molempiin |

## 8. Vaiheet ja todennus

| Vaihe | Työ | Todennus | Hyväksyntä |
|---|---|---|---|
| 0 | BLE-aukot: live-avaimet, `tare`, `cal:*`, RX-puskuri | smoke + äppi iPhonella BLE:llä (paino, tara, kalibrointi) | flash, äpin asennus |
| 1 | Pico suora UDP-kanava + avaimen jako BLE:llä | `wifi_suora_smoke`, kaikki `*_smoke`, uutto: viiveet eivät pahene | flash |
| 2 | Äpin `MachineLink` + `BLERepository`-sovitus | nykyiset testit, XCUITest-kierros BLE:llä (ei toiminnallista muutosta) | – |
| 3 | `WifiRepository` + `LinkSelector` + asetus | Dart-testit, XCUITest simulaattorissa Picoa vastaan (inventaarion rivit) | – |
| 4 | HA-uuttotapahtuma keräimeen | keräimen smoke | – |
| 5 | Asennus iPhoneen | uutto Wi-Fillä etualalla, uutto lukitulla puhelimella (BLE-tausta), BLE pakotettuna, VPN:n kautta | asennus |

Skoopit: vaiheet 0 (firmware), 1 ja 4 kuuluvat skooppiin `infra expresso`; 0 (äppi), 2, 3 ja 5 skooppiin
`expresso-ios` (`lib/` yhteinen: muutos näkyy myös Android-käännöksessä, ks. expresso-ios/REKISTERI.md:34-35).
