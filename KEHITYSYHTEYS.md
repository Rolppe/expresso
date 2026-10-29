# eXpresso-keitin — kehitysyhteys Mac → OnePlus → Pico

Tietopaketti skoopille `infra iot` (koottu 17.9.2026). Kertoo, miten keittimen kehitysyhteyttä
käytetään ja mitä sillä on aiemmin tehty. Lähdekoodi ja työkalut ovat Macilla; tämä tiedosto
viittaa niihin eikä kopioi niitä. Lähteet luettu `ssh dev-host` -yhteydellä vain lukien.

**Nykyinen ketju 5.10.2026 alkaen: palvelin → Zero → Pico** (ZERO-USB 1.10.2026,
EXPRESSO-ZERO-FLASH). Pico on Zeron USB-dataportissa; `pico_dev.py` puhuu ser2netin raakaa TCP:tä
192.0.2.10:2217 ja flashaa `pico_dev.py flash pico/MANIFEST.json` -komennolla (PICO-HALLINTA.md luvut 1 ja 7).
Alla oleva Mac/OnePlus-ketju ja luku "Aloitus uudessa keskustelussa" ovat historiaa (`PICO_LINK=phone`).

## Laite ja projekti

- **Keitin:** Rancilio Silvia, ohjaimena Raspberry Pi Pico W, MicroPython-firmware (ennakoiva
  termostaatti, pikalämmitys, esi-infuusio, vaaka, 10 Hz keittoloki). AMK-opinnäytetyö 2023,
  julkiset repot `github.com/Rolppe/silvia_pico`, `silvia_pico_ui`, `silvia_pico_flutter_ui`
  (`workspace/cv/cv-2026-09-09.md:267-272`).
- **Käytössä oleva versio (Mac):** `~/Documents/Koodi/Silvia pico/eXpresso_Grok/legacy/latest/`
  — `pico/` (firmware), `silvia_pico_flutter_UI/` (Android-sovellus), `tools/` ja
  `tools/dev_station/` (yhteystyökalut), `logs/`. Dokumentaatio on repojuuren `docs/`-hakemistossa
  (ei `legacy/latest/docs`). Rinnalla keskeneräinen C-portti `pico-c/`.
- **Git ei kerro historiaa:** `eXpresso_Grok`issa on yksi commit (`cf02bb7`, 7.8.2026, vaaka-
  kalibrointi); `tools/`, `docs/`, `legacy/` ovat untracked. Päivämäärät tulevat lokeista.
- Vanhemmat hakemistot `eXpresso_Claude`, `Koodi/eXpreso`, `Koodi/Grok/eXpreso` — ei tätä
  yhteysmallia.

## Yhteysmalli

```
Mac ──langaton ADB (LAN tai WireGuard, TCP 5555)──▶ OnePlus 7T Pro 192.0.2.11 (trust-VLAN)
                                                     │  sovellus com.example.silvia_pico_ui
                                                     ├─ USB-OTG (USB-CDC) ──▶ Pico W (flash, REPL, sarjasilta :2217)
                                                     └─ BLE (EspressoPico) ──▶ Pico W (ajonaikainen ohjaus ja telemetria)
```

- **Miksi langaton ADB on pakollinen:** Pico varaa puhelimen ainoan USB-portin OTG-hostina, joten
  langallista ADB:tä ei ole samaan aikaan (`docs/wireless_dev.md`).
- **BLE on paikallinen** puhelimen ja Picon välillä; Mac ohjaa vain ADB:tä, lokeja ja sarjasiltaa.
- **Palvelin (palvelin) ei ole ketjussa:** `adb` ei ole asennettu, puhelin ei ole sen USB:ssä.
  Palvelimelta ajetaan komennot Macille: `ssh dev-host '…'` (adb polussa `/opt/homebrew/bin/adb`).
- **Asetukset:** `legacy/latest/tools/dev_station/host.env` — `PHONE_IP=192.0.2.11`,
  `ADB_PORT=5555`, `BRIDGE_PORT=2217`, `APP_PKG=com.example.silvia_pico_ui`, `BRIDGE_TOKEN` tyhjä.

## Android-sovellus (Kotlin-natiiviosa)

Polku `legacy/latest/silvia_pico_flutter_UI/android/app/src/main/kotlin/com/example/silvia_pico_ui/`.

| Luokka | Tehtävä | Logcat-tagi |
|---|---|---|
| `PicoUsbManager` | USB-CDC-host (`usb-serial-for-android`); ei aseta DTR/RTS, koska DTR resetoi Picon | `PicoUsb` |
| `PicoBridgeService` | foreground-palvelu, TCP :2217, minimaalinen RFC2217 (`mpremote rfc2217://`), yksi asiakas, valinnainen token | `PicoBridge` |
| `PicoFlasher` | kirjoittaa tiedostot REPL:iin hex-paloina, tarkistaa koon `uos.stat()` | `PicoFlasher` / `PicoFlash`: `FLASH_OK n=…`, `FLASH_FAIL` |
| `MainActivity` | intent-extrat (`MainActivity.kt:326-352`) | — |

Intent-extrat (`adb shell am start -n com.example.silvia_pico_ui/.MainActivity --ez <extra> true`):
`espressopico_open_usb`, `espressopico_flash_usb`, `espressopico_start_bridge` (avaa USB:n ensin).
BLE-koodi on Flutterissa (`lib/features/ble/`); Picon puoli `pico/bluetooth_handler.py`.
Protokolla: `docs/protocol/BLE.md` — live-JSON (T, P, paino, tila), asetukset, brew_log-multipack,
komennot (`tare`, `pit:`, `srt:`, `pre:on/off`, `spr:on/off`, `fhu:on/off`, `cal:…`, `sync`).

## Työkalut (Macilla, ajetaan hakemistosta `legacy/latest`)

| Komento | Mitä tekee |
|---|---|
| `./tools/dev_station/oneplus_wireless_adb.sh bootstrap` | kerran: puhelin Macin USB:ssä (ei Picoa) → `adb tcpip 5555`, päivittää `PHONE_IP` |
| `./tools/dev_station/oneplus_wireless_adb.sh connect\|status\|disconnect` | päivittäinen ADB-yhteys |
| `./tools/dev_station/oneplus_prep.sh` | akunsäästön ja taustarajoitusten ohitus sovellukselle |
| `./tools/flash_via_phone.sh [--connect] [--force]` | firmware (`main.py brew_logger.py bluetooth_handler.py classes.py debug_log.py functions.py preset.py boot.py` + `scale_cal.json`) → sovelluksen tiedostot → flash-intentti → odottaa `FLASH_OK` 90 s; estää alle 20 % akulla |
| `./tools/ble_health.sh` | odottaa sovelluslokista `link READY` (oletus 25 s) |
| `./tools/dev_station/capture_run.sh start\|stop\|status\|analyze` | logcat + Picon sarjaloki rinnakkain (`adb forward tcp:2217` → LAN → Macin usbmodem); `stop` ajaa `analyze_run.py` |
| `./tools/dev_station/adb_capture.sh` | jatkuva logcat → `logs/app/<pvm>/flutter.log` |
| `./tools/dev_station/serial_capture_remote.sh` | Picon sarjaloki puhelimen sillan kautta |
| `./tools/dev_station/ops_probe.sh`, `ops_ask.sh <toiminto>` | tilan luotaus ja "kysytäänkö ihmiseltä" -päätös `ops_registry.yaml`:sta |
| `analyze_run.py`, `analyze_shot.py` | lokin analyysi: `SCALE_NEG`, `TRACEBACK`, `SAFETY`, `MEM_LOW`; brew_log-kierros |
| `./tools/flash_all.sh`, `flash_brew_fix.sh`, `flash_water_fix.sh` | vanha tapa: Pico suoraan Macin USB:ssä (`mpremote`) |
| `./tools/run_host_ci.sh` | laitteeton CI (Python-testit, `flutter test`) |

Sarjasilta käsin: `mpremote connect rfc2217://192.0.2.11:2217 exec "print(1)"`, tai turvallisemmin
`adb forward tcp:2217 tcp:2217` ja `rfc2217://127.0.0.1:2217`.

## Kuka tekee mitä (`tools/dev_station/ops_registry.yaml`)

- **Agentti saa:** `adb_connect`, `app_start`, `usb_open`, `bridge_start`, `capture_start`,
  `capture_stop_analyze`, `analyze_run` — sekä rekisterin mukaan `flash_core`.
- **Vain ihminen:** Picon kytkentä OTG:hen (`physical_plug_pico`), USB-luvan hyväksyntä puhelimessa
  (`accept_usb_permission`), oikea keitto (`run_brew_shot`), puhelimen lataus (`charge_phone_or_hub`),
  ADB-bootstrap USB-johdolla (`adb_bootstrap`).
- **Infran sääntö päällä:** flashaus, `cal:`/asetuskomennot ja muut keittimen tilaa muuttavat toimet
  vahvistetaan käyttäjältä ennen ajoa (infran työtapa "vahvista ennen muuttavia komentoja"), vaikka
  `ops_registry` sallii ne agentille. Keittimessä on lämmitin ja pumppu; koodiin pakotettua
  komentojen kieltolistaa ei löytynyt (`docs/flowcharts/SEC0-trust-boundaries.mmd`: OTG-flash
  korvaa firmwaren ilman allekirjoitusta).
- Tavoiteketjut: `flash` = connect → app → usb_open → flash; `diagnose_shot` = … → bridge →
  capture → keitto (ihminen) → analyysi.

## Rajoitukset ja tunnetut viat

- **Akku:** OTG-hostina puhelin syöttää Picolle 5 V eikä lataudu; flash estyy alle 20 %.
  Ratkaisu: virrallinen USB-C-hubi tai Picolle erillinen 5 V (`docs/runbooks/R6-battery-block.md`).
- **Langaton ADB nollautui** ennen 17.9.2026 puhelimen uudelleenkäynnistyksessä → `Connection
  refused` portissa 5555. Korjattu pysyvällä `persist.adb.tcp.port=5555`:llä (ks. Tila). Jos se
  katoaa (ROM-päivitys, tehdasasetukset): johto Maciin, *Rooted debugging* päälle, `adb root`,
  `adb shell setprop persist.adb.tcp.port 5555`.
- **Flash-aikakatkaisu:** 90 s ≠ epäonnistuminen; 5 tiedoston paketti kestää ~2 min, katso
  myöhempi `FLASH_OK` (`R3-flash-timeout.md`). Pysäytä kaappaus ja silta ennen flashia.
- **Flashin jälkeen** BLE katkeaa resetissä; odota `link READY`, tarvittaessa OTG irti ja kiinni.
- **Silta kiinni:** `espressopico_start_bridge`-intentti, USB auki ensin (`R5-bridge-closed.md`).
- `unauthorized` → avaa puhelimen lukitus, hyväksy RSA uudelleen. `controlTransfer failed` alussa →
  USB ei vielä asettunut, yritä uudelleen.
- **Tietoturva:** ADB 5555 ja silta 2217 eivät saa näkyä internetiin; silta oletuksena pois.
  Etäkäyttö WireGuardin kautta (`docs/wireless_dev.md` → WireGuard); puhelimella ei ole
  internetiä (`oneplus_no_wan`, `Infra/paarekisteri.md`).
- Runbookit: `docs/runbooks/R1-ble-no-connect.md` … `R6-battery-block.md`.

## Aiempi käyttö (todisteet)

- 10 kaappausajoa `legacy/latest/logs/runs/` 9.–10.8.2026; viimeisin `20260810_154340`, jonka
  `meta.json`:ssa `bridge_host: 127.0.0.1` (silta `adb forward` -reitillä).
- Onnistuneet flashit puhelimen kautta: `logs/app/2026-08-09/flutter.log` (4 `FLASH_OK`-riviä) ja
  `logs/app/2026-08-10/flutter.log:15720-15721` (`FLASH_OK n=5`).
- Viimeisin analysoitu keitto 10.8.2026 15:50 (`logs/problems_latest.txt`): Pmax 10,5, 8 ongelmariviä
  (mm. `SCALE_NEG`, `TARE_APPLY`, `TRACEBACK_OR_MEMORY`).
- Vanha erillinen polku: `legacy/tools_old/pi-zero-usb-ether/` (Pi Zero 2 W USB-Ethernet, ei Pico).

## Tila 17.9.2026

- Reititin näkee puhelimen (`ip neigh` REACHABLE, DHCP 192.0.2.11).
- Aamulla Macilta `adb connect 192.0.2.11:5555` → `Connection refused`: langaton ADB pois päältä.
- Portti 2217 kiinni Macilta ja palvelimelta: silta ei käynnissä.
- **Syy selvitetty:** hylkäyksen lähettää puhelin, ei reititin. Mac → puhelin `ping` toimii; fw4
  sallii mgmt → trust (`forwarding mgmt→trust`), `reject_to_trust`- ja `sallitut_mac_forward`-
  laskurit pysyivät nollassa yhteysyrityksen yli, `estetyt_mac` tyhjä. Puhelimen kaikki TCP-portit
  kiinni (Macin skannauksessa auki vain 53, joka on reitittimen DNS-uudelleenohjaus
  `dstnat_mgmt`). Eli puhelimen `adbd` ei kuuntele TCP:tä: `adb tcpip 5555` ei säily puhelimen
  uudelleenkäynnistyksen yli. Yhteys katkesi jo ennen 19.8.2026 (`logs/ops/state.json`:
  `adb.reachable: false`); viimeinen toimiva käyttö 10.8.2026.
- **Juurisyy (käynnistyshistoria `persist.sys.boot.reason.history`):** `shutdown,battery`
  11.8.2026 08:19 (päivä viimeisen OTG-kehitysajon jälkeen) ja 10.9.2026 12:28. `adb tcpip 5555`
  asettaa vain `service.adb.tcp.port`-propertyn, joka ei säily käynnistyksen yli.
- **Korjattu 17.9.2026:** puhelin on LineageOS 23.2 userdebug (`hotdog`, Android 16), joten
  Kehittäjäasetuksissa *Rooted debugging* päälle (käyttäjä) → `adb root` →
  `setprop persist.adb.tcp.port 5555`. Todennettu: `adb reboot`, 10 s myöhemmin
  `adb connect 192.0.2.11:5555` → `device`, uptime 22 s, `persist.adb.tcp.port=5555`.
  Myös *Wireless debugging* (`adb_wifi_enabled=1`) on päällä. `adb root` itse ei säily
  käynnistyksen yli (ei tarvita). Yhteys vaatii Macin RSA-avaimen (`ro.adb.secure=1`).
- **Jäljellä oleva riski:** akku loppuu OTG-ajossa → puhelin sammuu eikä välttämättä käynnisty
  itse latauksessa. ADB palaa nyt heti käynnistyksen jälkeen, mutta käynnistys voi vaatia
  virtanapin. Satunnaistettu MAC: jos WLAN unohdetaan, IP ja `oneplus_no_wan` hajoavat.
- Diagnoosi uudelleen: jos `nc -z` Macilta antaa refused ja reitittimen `reject_to_trust`-laskuri ei
  kasva, vika on puhelimessa. Palvelimelta tehdyt kokeet eivät kelpaa (ufw estää lähtevän).
- **USB-yhteys Picoon todennettu 17.9.2026 11:39:** käyttäjä kytki Picon OTG:hen; `dumpsys usb`:
  `vendor_id=11914` (0x2E8A), `manufacturer_name=MicroPython`, `data_role=host`, lupa annettu
  sovellukselle. Intentti `espressopico_open_usb` → logcat `PicoUsb: USB open deviceId=1002
  baud=115200`, `auto open … ok=true try=1`. Samalla BLE-telemetria kulki: `[DATA] RX settings`
  noin 4 Hz, `boiler_temperature` 99,05, `mode: IDLE`. Keittimelle ei lähetetty komentoja.
- Akku 100 %, ei latausta (OTG-host, `power_role=source`).


## Picon firmware-varmuuskopio 17.9.2026

- **Laite:** Raspberry Pi Pico 2 W (RP2350), MicroPython v1.28.0 (2026-04-06). **Picolla on eri
  firmware kuin puhelimen `files/firmware`-kopiossa** (10.8.2026 flash: 41 300 B `main.py`,
  `brew_logger.py`, `debug_log.py`) ja Macin `legacy/latest/pico`-hakemistossa: Picon `main.py`
  on 12 407 B, eikä siinä ole `brew_logger.py`:tä eikä `debug_log.py`:tä.
- **Sisältö (16 tiedostoa):** `api_functions.py backflush.py bluetooth_handler.py boot.py
  boot_bluetooth_test.py classes.py functions.py lib/adafruit_max31865.py lib/spi_device.py main.py
  preset.py scale.py scale_cal.json secrets.py settings.txt ugit.py`. Ohitettu `pid_log.txt`
  (774 035 B, loki, ei firmwarea). `secrets.py` sisältää salaisuuksia — älä tulosta.
- **Sijainnit:** puhelin (sovelluksen yksityinen tallennus, `run-as com.example.silvia_pico_ui`)
  `files/firmware_backup/20260917-pico2w/` + `MANIFEST.json`; Mac
  `~/Documents/Koodi/Silvia pico/eXpresso_Grok/legacy/pico-backup-20260917/` + `MANIFEST.json` +
  `pico_backup.py`.
- **Todennus:** jokaisen tiedoston SHA-256 laskettu Picolla (`uhashlib`) ja luetusta datasta —
  16/16 täsmää; puhelimen kopion `sha256sum` täsmää manifestiin 16/16.
- **Miten luettiin:** keitin verkkovirrasta pois (käyttäjä), silta `espressopico_start_bridge` +
  `adb forward tcp:2217 tcp:2217`, `python3 pico_backup.py <hakemisto> 127.0.0.1 2217`: Ctrl-C →
  raw REPL → releet GP11/12/13 = 0 → luku 128 B:n paloina → Ctrl-B, Ctrl-D (soft reset). Isompi
  pala katkesi sillassa (1 024 B:n palasta perille 381 hex-merkkiä). Soft resetin jälkeen BLE-
  telemetria jatkui (`mode: IDLE`). Lopuksi `adb forward --remove tcp:2217`.
- **Turvallisuus:** firmwaren `async_main` sammuttaa releet vain `except Exception` -haarassa;
  Ctrl-C (`KeyboardInterrupt`) ei ole `Exception`, joten keskeytys jättää releet viimeiseen tilaan —
  **lämmitin voi jäädä päälle**. Keitin aina verkkovirrasta pois ennen flashia tai lukua
  (käyttäjä vahvisti riskin 17.9.2026).
  **Vanhentunut flashin osalta 19.9.2026:** saman merkinnän seuraava kohta kertoo `PicoFlasher`in
  korjauksesta, ja lähdekoodi vahvistaa sen — `flashFiles` ajaa `interruptToRepl()`:n jälkeen heti
  `relaysOff()`:n, joka pakottaa GP11/12/13 nollaan ja kutsuu `devsafe.enter()`:n (luenta takaisin +
  vahdin ruokinta), ja `restoreBackup` käyttää samaa polkua. Flashaus **ei siis vaadi verkkovirran
  katkaisua**; vaatimus on, että keitin on joutilas. Jäljelle jäävä ikkuna on `interruptToRepl`:n
  omat ~1,2 s odotukset. Koko ketju ja perustelut: `PICO-HALLINTA.md`.
- **Palautus sovelluksella (lisätty 17.9.2026):** aiempi flash kirjoitti vain `files/firmware/`:n
  viisi nimeä (`main.py brew_logger.py bluetooth_handler.py classes.py debug_log.py`) — tästä
  varmuuskopiosta 3/16. **Älä flashaa nykyistä `files/firmware`-sisältöä tälle Picolle:** se on toista
  firmware-sukupolvea. Uusi täysi palautus:
  - Sovellus: *USB Pico (dev)* → *Open USB* → **Restore backup** → valitse kansio → vahvistus
    "Machine unplugged — restore". Adb: `am start -n com.example.silvia_pico_ui/.MainActivity
    --es espressopico_restore_backup 20260917-pico2w`.
  - Toiminta (`MainActivity.restoreBackup`): kaikki kansion tiedostot alihakemistoineen paitsi
    `MANIFEST.json`; jos manifesti on, jokaisen tiedoston SHA-256 tarkistetaan ennen kirjoitusta;
    akkuraja 20 %; logcat `PicoFlash`: `RESTORE_START`, `RESTORE_OK <nimi> n=16` / `RESTORE_FAIL …`.
  - `PicoFlasher` muutettu: releet GP11/12/13 OFF heti keskeytyksen jälkeen (koskee myös vanhaa
    *Flash core* -polkua), puuttuvat hakemistot (`/lib`) luodaan, kokokuittauksen `SZ`-vertailu
    ei enää voi osua edellisen tiedoston riviin (vanha vika: `rx`-puskurin ensimmäinen osuma).
  - Lähde ennen muutosta: `legacy/app-src-backup-20260917.tgz`; vanha build-hakemisto
    `silvia_pico_flutter_UI/build.bak-20260917` (siinä 206 iCloudin `* 2.*`-kaksoiskappaletta,
    jotka kaatoivat dex-yhdistämisen: `Type androidx.core.ktx.R is defined multiple times`).
    Uusi APK asennettu `adb install -r` 17.9.2026 11:53 (data ja varmuuskopio säilyivät).
  - **Koeajo:** tehty 17.9.2026 painefirmwarella (ks. Painesäätimet): 15/15 tiivistettä.
- **BLE ja näyttö:** Android estää sovelluksen suodattamattoman BLE-haun näytön ollessa pois
  (`ScanManager: Cannot start unfiltered scan in screen-off`). Jo auki oleva yhteys säilyy, mutta
  sovelluksen uudelleenkäynnistyksen tai asennuksen jälkeen yhteys palaa vasta, kun näyttö herää:
  `adb shell input keyevent KEYCODE_WAKEUP` (todennettu 13:48, telemetria heti).


## Painesäätimet 17.9.2026 (esiuutto 1–4 bar, uutto 5–10 bar)

- **Firmware** (Picon nykyisen sukupolven päälle, kolme tiedostoa; täysi setti Macilla
  `legacy/pico-paine-20260917/` + `MANIFEST.json` + `pico_verify.py`, puhelimessa
  `files/firmware_backup/20260917-paine/`, ilman `settings.txt`:tä jotta asetukset säilyvät):
  - `bluetooth_handler.py`: komennot `pip:<bar>` (esiuuton paine) ja `bp:<bar>` (uuton paine);
    molemmat arvot `send_settings`- ja `send_data`-paketeissa (`pre_infusion_pressure`, `brew_pressure`).
  - `classes.py`: `set_pre_infusion_pressure` rajaa 1–4 bar, `set_brew_pressure` 5–10 bar;
    oletukset ennallaan 2,0 ja 8.
  - `functions.py`: `pre_infusion()` käyttää asetettua painetta (ennen kiinteä 1,9/2,0);
    `save_settings`/`load_settings` tallentavat molemmat (vanha tiedosto ilman avaimia → oletukset).
- **Sovellus:** `controls_widget.dart` liukusäätimet *Pre-infusion pressure* (1–4, 0,5 bar askel)
  ja *Brew pressure* (5–10, 0,5); `MachineStatus.preInfusionPressure/brewPressure`
  (freezed-koodi: `flutter pub run build_runner build --delete-conflicting-outputs`).
- **Todennettu 17.9.2026** (keitin irti verkkovirrasta, käyttäjän lupa): flash sovelluksen
  palautuksella `espressopico_restore_backup 20260917-paine`; Picolta luettu SHA-256 15/15
  (`pico_verify.py`); UI-napautus → `TX OK pip:3.0` / `bp:9.0` → Pico kuittasi 3.0 / 9.0;
  `settings.txt` sisälsi arvot ja ne säilyivät `machine.reset()`:n yli; palautettu 2.0 / 8.0.
- **Havaitut viat ja kiertotiet:**
  - Sovelluksen flash jätti USB-lukijan tauolle soft resetin jälkeen → silta ei palauttanut
    vastauksia. Korjattu `PicoFlasher.flashFiles`-`finally` (resumeIo aina), asennettu 14:26.
  - Soft reset (Ctrl-D) BLE-yhteyden katkettua äkillisesti jätti Picon mainostamatta BLE:tä
    (ohjelma pyöri, `adafruit_max31865.read_rtd`); **`machine.reset()` korjasi**. Käytä raw REPL
    -skripteissä lopuksi `machine.reset()` jos BLE ei palaa.
  - Puhelimen logcat-puskuri oli 256 KiB → BLE-telemetria pyyhki `RESTORE_OK`-rivin; nostettu
    `adb logcat -G 4M` (ei säily puhelimen uudelleenkäynnistyksen yli).
  - Sovelluksen vanhat liukusäätimet *Pre-infusion* (aika) ja *Soft pressure release* lähettävät
    `pit:`/`srt:`, joita Picon firmware ei tunne — ne eivät vaikuta mitään (esiuuton kesto kiinteä 5 s).
  - Puhelimen näyttölukitus on pois (`locksettings get-disabled` → true); UI-testit onnistuvat
    `input keyevent KEYCODE_WAKEUP` + `uiautomator dump` + `input tap`.


## Esiuuton ja soft releasen ajat 17.9.2026

- Sovelluksen *Pre-infusion*- ja *Soft pressure release* -liukusäätimet (0–6 s, 0 = pois) lähettävät
  `pit:`/`srt:`, joita Picon firmware ei tuntenut. Korjattu setti `20260917-aika` (Mac
  `legacy/pico-aika-20260917/`, puhelin `files/firmware_backup/20260917-aika/`, 15/15 tiivistettä
  täsmää puhelimessa):
  - `bluetooth_handler.py`: `pit:<s>` → `set_pre_infusion_time` + `pre_infusion_mode = s > 0`;
    `srt:<s>` → `set_pressure_soft_release_time` + `pressure_soft_release_mode = s > 0`; rajaus 0–6 s;
    ajat mukana asetus- ja telemetriapaketeissa.
  - `functions.py`: esiuuton kesto asetuksesta (oli kiinteä 5 s).
  - `main.py`: soft release `sleep_ms(int(t*1000))` — `range(float)` olisi kaatunut murto-sekunteihin.
- **Tila:** käytössä settinä `20260917-pkal2` (ks. Painekalibrointi); todennettu 17.9.2026.


## Painekalibrointi 17.9.2026

- Syy: paineanturin virtalähteen vaihdon jälkeen painelukemat muuttuivat (käyttäjä).
- **Firmware** (setti `20260917-pkal` = `aika` + kalibrointi; Mac `legacy/pico-pkal-20260917/`,
  puhelin `files/firmware_backup/20260917-pkal/`, 15/15 tiivistettä täsmää puhelimessa):
  - `classes.PressureSensor`: `bar = gain * raw_bar + offset`, `raw_bar` = tehtaan kaava
    (`avg * 0.000314936 - 3.522929`); tallennus `pressure_cal.json`; hyväksytään vain
    gain 0,5–1,5 ja offset ±3 bar (muuten oletus 1,0 / 0,0).
  - `classes.BrewData`: velhon tila (`pcal_state` idle|queued|running|done|corrected|saved|error),
    pisteet raakapaineina: yksi piste → offset, molemmat vaiheet → kaksipistesovitus.
  - `functions.pressure_calibration_run`: 10 s vettä vaiheen tavoitepaineella (esiuutto- tai
    uuttopaineen liukusäädin), pumppu kuten uutossa (< tavoite−0,5 päällä, < tavoite 35 ms pulssi),
    lämmitin pois, raakapaineen keskiarvo viimeiseltä 5 s:lta. Keskeytys: mikä tahansa keittimen
    kytkin, `pcal:end` tai paine > 12 bar; `finally` sammuttaa pumpun ja magneettiventtiilin.
  - `main.py`: pääsilmukka ajaa pyydetyn kalibrointiajon (ei rinnakkain uuton kanssa).
  - `bluetooth_handler.py`: `pcal:run:<pre|brew>`, `pcal:m:<pre|brew>:<bar>`, `pcal:save`,
    `pcal:end`; tila erillisenä pienenä notifynä (`pcal_state`, `pcal_stage`, `pcal_msg`,
    `pcal_gain`, `pcal_offset`) vain kun velho on käynnissä, jotta telemetriapaketti ei kasva.
- **Sovellus:** *Settings → Pressure calibration* (`pressure_calibration_view.dart`): vaihe 1
  esiuuttopaine → 10 s testi → mittarilukema → *Correct and test again* toistuu kunnes
  *Reading was correct* → vaihe 2 uuttopaine samoin → *Confirm and save* -dialogi → `pcal:save`.
  Näkymästä poistuminen lähettää `pcal:end` (tallentamattomat korjaukset hylätään).
  Asennettu puhelimeen 17.9.2026 15:00; `flutter analyze` ei huomautuksia.
- **Todennettu isäntäkoneella** (CPython, tekaistu pumppu/anturi, anturi lukee `true*0.9-0.4`):
  esiuutto korjautui 2 ajolla (2,5 → 2,0 bar), uutto 2 ajolla (9,9 → 9,0), esiuuton uusintatesti
  2,1; kytkinkeskeytys → `error`, releet pois; mahdoton lukema hylätään; tallennus ja `pcal:end`
  -uudelleenluku toimivat. **Ei vielä ajettu Picolla eikä oikealla mittarilla.**
- **BLE-pakettikoon vika (juurisyy, 17.9.2026):** setit `aika` ja `pkal` lisäsivät 5 Hz
  telemetriaan kentät `pre_infusion_time` ja `pressure_soft_release_time` → paketti 309 B (`paine`
  248 B, alkuperäinen 196 B). Pico 2 W:n BLE jumittui 0–36 s:ssa yhteyden jälkeen (BLE ja USB-CDC
  kuolivat, `controlTransfer failed`, vain virtakatko auttoi; kolme kertaa sattui `pit:`-napautuksen
  kohdalle ja näytti komentoviasta, neljännellä jumi tuli ilman komentoa). **Sääntö: yksi notify
  ≤ 240 B** (yksi 251 B:n linkkikerroksen paketti). Korjaus `20260917-pkal2`:
  `BLEHandler._notify` pudottaa yli 240 B:n paketin ja tulostaa varoituksen; telemetria =
  alkuperäiset 8 kenttää (pahin 233 B); asetukset kahtena pakettina (119 B, 141 B) muutoksessa ja
  2 s välein; `pcal`-tila omana pakettina (≤ 149 B, `pcal_msg` katkaistu 40 merkkiin) samassa
  tehtävässä. Vialliset setit poistettu puhelimesta, Macilla nimetty `…-VIALLINEN-BLE309`.
- **Todennettu Picolla `pkal2`** (keitin irti verkkovirrasta): flash sovelluksella `RESTORE_OK n=15`,
  tiivisteet 15/15 (`pico_verify.py`, nyt lopuksi `machine.reset()` Ctrl-D:llä); 3 min ilman
  komentoja 794 pakettia ilman katkoa; UI-napautukset `pit:3.0`, `srt:0.0` (→ mode false), `pip:3.0`,
  `bp:9.0` kuitattu ja palautettu 5,0 s / 5,0 s / 2,0 bar / 8,0 bar; *Pressure calibration* →
  *Start 10 s test* → `mode: pressure calibration` → `IDLE`, sivu kysyi mittarilukemaa
  (raakapaine −0,77 bar ilman painetta), poistuminen lähetti `pcal:end`, telemetria jatkui.
  **Oikea kalibrointi mittarilla tekemättä** (vaatii verkkovirran ja mittarin).
- Havainto (korjattu 16:18): −0,7…−0,8 bar lepopaineessa mitattiin keitin **irti verkkovirrasta**;
  keitin verkkovirrassa lepopaine oli −0,0…−0,2 bar. Paineanturin virtalähde ilmeisesti kulkee
  keittimen verkkovirrasta → kalibroi vain keitin päällä.
- Kalibrointiajo tarvitsee keittimen verkkovirtaan (pumppu) ja painemittarin ryhmään — sen tekee
  käyttäjä sovelluksesta. Flash tehdään keitin irti verkkovirrasta.


## Uuton paineensäädön viive 17.9.2026

- **Oire (käyttäjä):** uutossa paine ylittää tavoitteen ja putoaa välillä noin 6 bariin.
- **Syy (koodista):** `adafruit_max31865.read_rtd` estää ≥ 75 ms (`time.sleep(0.01)` +
  `time.sleep(0.065)`). Uuttosilmukka luki lämpötilan joka kierroksella (arvoa ei käytetty) +
  17 ms paineikkuna + 50 ms tauko + 35 ms pulssi, ja BLE:n `send_data` luki 200 ms välein paineen ja
  lämpötilan uudelleen (≈ 97 ms esto asyncio-silmukassa). Pumpun tila päivittyi ≈ 0,2–0,3 s välein;
  alueella tavoite−1…tavoite 35 ms pulssi ja pitkä tauko → paine valui.
- **Korjaus (setti `20260917-paineohjaus` = `pkal2` + säätö; Mac `legacy/pico-paineohjaus-20260917/`,
  testit `…-testit/`, puhelin `files/firmware_backup/20260917-paineohjaus/`, 15/15 täsmää):**
  - `classes.PumpPressureController`: on/off hystereesillä ±0,15 bar tavoitteen ympärillä,
    vähintään 20 ms kytkentäväli (SSR, yksi 50 Hz jakso), päivitys joka kierroksella.
  - `PressureSensor.get_pressure`: keskiarvoikkuna muutettiin 20 ms:iin (50 Hz oletus) — **virhe**, palautettu 16 667 µs (60 Hz) setissä `devsafe5`.
  - `main.py` uuttosilmukka: ei taukoa (`sleep_ms(0)`), lämpötila vain 2 s välein, lokirivi
    `PB <ms> <paine> <tavoite> <pumppu>` 100 ms välein ja lopuksi `PB_END loops=… max_loop_ms=…`
    (USB-sarjaan, kaapattavissa sillan kautta).
  - `functions.pre_infusion`: yksi nopea silmukka (nousu + ajastettu pito samalla säätimellä,
    ajastin alkaa kun tavoite saavutetaan), lokirivi `PI …`; kalibrointiajo käyttää samaa säädintä.
  - `bluetooth_handler.send_data`: käyttää välimuistiarvoja `brew_data.pressure` /
    `brew_data.boiler_temperature`, ei lue antureita.
- **Simulaatio** (`loop_sim.py`, ajoitus koodin estoista, kolme pumppu/kakku-mallia, tavoite 9 bar,
  t > 3 s): vanha min 6,7–7,9 / max 9,7–11,1 bar (toistaa oireen), uusi min 8,7–8,8 / max 9,2–9,4,
  keskiarvo 9,00–9,04. Yksipuolinen kaista (tavoite−0,3…tavoite) jätti keskiarvon 0,15 bar alle —
  korjattu keskitetyksi, koska kalibrointi olisi tulkinnut sen anturin offsetiksi
  (`pcal_test.py`: gain 1,105 / offset 0,459 vs. tosi 1,111 / 0,444).
- **Flashattu 17.9.2026 16:16** (`RESTORE_OK 20260917-paineohjaus n=15`, tiivisteet 15/15,
  `machine.reset()`); BLE 90 s 500 pakettia ilman katkoa, lämpötila ja paine päivittyvät
  välimuistista, `pip:3.0` → `2.0` kuitattu. **Oikea uutto todentamatta:** kaappaus käynnissä Macilla
  `/tmp/pb_capture.py` → `/tmp/pb_capture.log` (30 min, silta `adb forward tcp:2217`).


### Koeuutto 1 (on/off-säätö) ja PI-säätö 17.9.2026

- **Kaappaus** `/tmp/pb_capture.log` → arkistoitu Macilla
  `legacy/pico-paineohjaus-20260917-testit/uutto-20260917-1630-bangbang.log`. Kaksi uuttoa;
  **käyttäjän mukaan oikea (kahvi) oli jälkimmäinen.**
- **Uutto 2 (tavoite 8 bar):** esiuutto 0 → 2 bar 2,5 s:ssa ja pito 1,8–2,6 bar; nousu 2,5 → 8,7 bar
  0,4 s:ssa; tavoitteen jälkeen 100 ms näytteet min 6,1 / max 10,0 / ka 8,10 / sd 0,61, pumppu vaihtoi
  tilaa 86/113 näytteellä; silmukka 574 kierrosta 13,4 s:ssa (~23 ms), `max_loop_ms=102`
  (2 s välein tehtävä lämpötilaluku). Uutto 1: 7,6–8,8, ka 8,05.
- **Tulkinta:** viive korjaantui (keskiarvo tavoitteessa), mutta kakulla on/off-säätö heilahtaa
  ~±1–2 bar ~5 Hz: paine muuttuu ~10 bar/s kumpaankin suuntaan ja pumppu+anturi reagoivat viiveellä.
- **Sovitettu malli** (`pi_sim.py`): viive 60–80 ms, mittauskohina ~0,3 bar toistaa sd 0,55–0,61.
- **PI-säätö (setti `20260917-pi` = `paineohjaus` + `classes.py`; Mac `legacy/pico-pi-20260917/`,
  testit `…-testit/`, puhelin `files/firmware_backup/20260917-pi/`, 15/15 täsmää):**
  `PumpPressureController(mode='pi')`: duty = 0,5 + 0,2·e + 0,3·∫e (anti-windup, ∫ rajattu ±1,5),
  aikasuhteinen on/off 100 ms ikkunassa 20 ms askelin; `mode='bang'` jäi varalle.
  Firmwaren oma luokka mallia vasten (`ctrl_real_test.py`, kolme pumppumallia 10/10, 14/8, 7/12 bar/s):
  todellinen paine on/off sd 0,49–0,57, ka 7,81–8,21 → PI sd 0,24–0,26, ka 8,00, vaihteluväli
  7,1–8,8; mitattu sd (sis. kohinan) 0,58–0,65 → 0,38–0,40. Kalibrointitesti PI:llä gain 1,112 /
  offset 0,476 (tosi 1,111 / 0,444).
- **Tila:** sisältyy settiin `20260917-devsafe` (ks. Kehitys ilman käyttäjää); oikea uutto todentamatta.


## Kehitys ilman käyttäjää: devsafe, vahti, testiuutto 17.9.2026

**Käyttäjän vaatimus:** kehityksen on toimittava ilman fyysisiä toimenpiteitä (ei virran katkaisua,
ei Picon irrotusta, ei kytkimiä). Releet ajetaan alas ennen jokaista operaatiota. Kahvaan vaihdetaan
kori → **säädettävä neulaventtiili pohjassa** testiuuttoja varten.

- **Setti `20260917-devsafe`** (Mac `legacy/pico-devsafe-20260917/`, testit `…-testit/`, puhelin
  `files/firmware_backup/20260917-devsafe/`, 17 tiedostoa; sisältää `pi`-säädön):
  - `devsafe.py`: `relays_off()`, `relays_state()`, `enter()` (releet alas + takaisinluku, `True` vain
    `[0, 0, 0]`), `start_watchdog()` (laitteistovahti 8 s), `feed()`.
  - `main.py`: `devsafe.relays_off()` ensimmäisenä ennen muita importteja; `asyncio.run` on
    `try/finally`-lohkossa → Ctrl-C/kaatuminen tulostaa `DEVSAFE relays off (main exited)
    relays=[0, 0, 0]`; `watchdog_feeder` ruokkii 1 s välein; `serial_commands` lukee USB:ltä rivejä
    `CMD <komento>` → `CMD_OK <komento>`; `dev:safe` pitää releet alhaalla ja ohittaa
    lämmityksen/pumpun kunnes `dev:resume`.
  - `commands.py`: yksi komentojen käsittelijä BLE:lle ja sarjalle (entiset + `tshot:<5–60 s>`,
    `tshot:stop`, `dev:safe`, `dev:resume`).
  - `functions.run_shot`: esiuutto → PI-uutto → soft release → magneettiventtiili, **sama koodi
    kytkimelle ja testiuutolle**; katkeaa kytkimeen, `tshot:stop`/`dev:safe`, aikarajaan tai
    mitattuun paineeseen > 13 bar; `finally` sammuttaa pumpun, lämmittimen ja venttiilin. Lokit
    `PI …`, `TS <ms> <paine> <tavoite> <pumppu> <duty>`, `TS_END loops=… max_loop_ms=… reason=…`.
  - `backflush.py`: 10 s tauko oli `asyncio.sleep_ms(50)` ilman `await` → koko ohjelma (myös BLE)
    jumissa 10 s ja vahti olisi resetoinut; korjattu `await`:lla.
- **Sovellus:** `PicoFlasher` ajaa keskeytyksen jälkeen `import devsafe; devsafe.enter()` ja ruokkii
  vahtia 20 kirjoitusrivin välein (vanhalla firmwarella rivit vain virheilevät). Asennettu 16:41.
- **Mac-työkalu** `Infra/iot/expresso/pico_dev.py` (kopio Macilla `legacy/pico_dev.py`):
  `safe`, `cmd <komento> [s]`, `shot <s> [loki]`, `capture <s> [loki]`, `verify <MANIFEST.json>`,
  `watchdog-test`. Jokainen REPL-operaatio: Ctrl-C → `devsafe.enter()` → vaaditaan `SAFE_OK` → työ
  (vahtia ruokitaan joka osassa) → `machine.reset()`.
  **Ansa:** silta palvelee yhtä asiakasta; toinen yhdistävä prosessi (esim. taustalle jäänyt
  `/tmp/pb_capture.py`, joka yhdisti uudelleen 3 s välein) vie sillan ja uusi asiakas ei saa mitään.
  Tarkista `ps -axo pid,command | grep pb_capture` ennen vianetsintää.
- **Testit:** `mpy-cross` (MicroPython 1.29, Macilla `~/Library/Python/3.9/bin/mpy-cross`) kääntää
  kaikki 7 muutettua tiedostoa; isäntätesti `shot_test.py` 18/18 (komennot ja rajaukset, testiuutto
  esiuutosta uuttoon ja aikarajaan, uutto ka 8,16 bar mallissa, ylipainekatkaisu, kytkinkatkaisu,
  releet 0 jokaisen lopun jälkeen, devsafe-takaisinluku, vahdin ruokinta).
- **Todennettu Picolla 17.9.2026 (keitin irti verkkovirrasta):** flash `RESTORE_OK
  20260917-devsafe n=17` (vahti ei vielä käynnissä vanhassa firmwaressa); `pico_dev.py cmd
  dev:resume` → `CMD_OK`; `verify` → Ctrl-C tulosti `DEVSAFE relays off (main exited) relays=[0, 0, 0]`,
  `devsafe.enter()` → `relays=[0, 0, 0] ok=True watchdog=True`, `VERIFIED 17/17` vahdin ollessa
  päällä; `watchdog-test` → ruokinta lopetettu 16:46:14, Pico resetoi itsensä, firmware vastasi
  `CMD_OK` ja BLE yhdisti uudelleen (`WATCHDOG_TEST PASS`).
- **Todentamatta:** testiuutto oikealla vedellä ja neulaventtiilikahvalla (vaatii verkkovirran).


### Etätestiuutot neulaventtiilikahvalla 17.9.2026 (keitin verkkovirrassa, ei käyttäjän toimia)

- **Kattilan lämpölaajeneminen:** magneettiventtiili kiinni → lepopaine nousi 1,4 → 14,3 bar ~25 s:ssa
  lämmittimen palauttaessa lämpöä (92,7 → 97,8 °C); venttiilin avaus pudotti 0,3 bariin. Myös
  käynnistyksen 8,3 bar lepopaine oli tätä. Testiuutto 2 katkesi siksi heti (`overpressure 14.5 bar`,
  `loops=0`). **Korjaus `devsafe2`:** ylipainekatkaisu (> 13 bar) vain pumpun ollessa päällä.
  Testi `shot_test.py`: jumiin jäänyt pumppu katkeaa 13,7 barissa, 14,5 bar alkupaine ei estä uuttoa.
- **Etäflashaus verkkovirta päällä** (`devsafe2` 17:06, `devsafe3` 17:11, `devsafe4` 17:16,
  `devsafe5` 17:19): `RESTORE_OK n=17`, vahti päällä ja ruokittuna flashin ajan (~112 s),
  `pico_dev.py verify` → `SAFE_OK`, `VERIFIED 17/17`.
- **`pico_dev.py shot`** käyttää nyt samaa yhteyttä komentoon ja kaappaukseen (uutto 1: toinen yhteys
  hukkasi 24 s lokia).
- **Mittausikkuna — käyttäjän tieto:** keitin on **60 Hz** verkossa; alkuperäinen 17 ms
  keskiarvoikkuna (1/60 s) oli oikein. Oma muutokseni 20 ms:iin (50 Hz oletus) ja kokeiltu 100 ms
  liukuva keskiarvo olivat virheitä. `devsafe5`: `get_pressure` 16 667 µs, säätösilmukan
  `PressureSensor.sample_average` estämätön liukuva keskiarvo viimeiseltä 16 667 µs:lta
  (`ticks_us`), säätimen askel ja pienin kytkentäväli 17 ms.
- **Tulokset** (tavoite esiuutto 2,0 / uutto 8,0 bar, 25 s, analyysi `analyze_shot.py`):

| Uutto | Firmware | Esiuuton huippu | Uutto min–max | ka | sd | pumpun duty ka |
|---|---|---|---|---|---|---|
| 3 | `devsafe2` (PI, 20 ms ikkuna) | 4,5 | 6,9–11,7 | 8,14 | 0,73 | 0,14 |
| 4 | `devsafe3` (+ mediaani, opittu ff, nousu ≤ 0,6) | 4,2 | 7,0–11,1 | 8,13 | 0,86 | 0,15 |
| 5 | `devsafe5` (60 Hz keskiarvo, 17 ms askel) | 4,1 | 6,2–10,6 | 8,01 | 0,58 | 0,22 |

  Uutto 5: 14 531 silmukkaa (~1,2 ms), `max_loop_ms=82` (lämpötilaluku 2 s välein), opittu ff
  esiuutto 0,20 / uutto 0,20 (RAM). Lokit Macilla `legacy/pico-devsafe*-20260917-testit/tshot*.log`.
- **Avoimet:** esiuuton ylitys ~2 bar (nousu liian nopea neulaventtiilin pienellä virtauksella);
  uutossa yksittäiset 10–11 bar piikit. Vettä käytetty 4 testiuuttoa (luvattu enintään 6 ennen
  astian tyhjennystä).


### USB-C-hubi (lataus + OTG) ja kehitysketju ilman Macia 17.9.2026

- **Hubi:** Genesys Logic `USB2.0 Hub` (4 porttia, `idVendor=05e3 idProduct=0608`) OnePlusin ja Picon
  välissä, laturina Applen USB-C PD -laturi ja C–C-johto.
- **Ensin ei toiminut:** puhelin ja hubi neuvottelivat Type-C-rooleja ~1 s välein
  (`smblib_handle_typec_cc_state_change` vuorotteli), ketju ehti enumeroitua (`usb 1-1.2
  Manufacturer: MicroPython`, `usb 1-1.4 USB2.0 Hub`) ja katkesi heti; `pd_active=0`,
  `real_type=USB_DCP` → puhelin näki hubin tyhmänä laturina, joten roolinvaihtoa ei tapahtunut.
  `dumpsys usb set-port-roles otg_default sink host` → "No change" (ei tuettu).
- **Ratkaisu (käyttäjä):** laturi kytketään hubiin **ensin**, puhelin vasta sen jälkeen. Tulos:
  `pd_active=1`, `real_type=USB_PD`, `typec_mode=Source attached (high current)`,
  `power_role=sink` + `data_role=host`, Pico näkyy Androidille (`vendor_id=11914`,
  `manufacturer_name=MicroPython`). Akku pysyi 70 %:ssa yli 3 min, myös 110 s flashauksen aikana
  (`current_now=0`, akun taso ei laske) — OTG-kuorma tulee hubista.
  **Kytkentäjärjestys on siis osa ohjetta.**
- Puhelimen laturipiirin tila luetaan `adb root`illa: `/sys/class/power_supply/usb/{typec_mode,
  pd_active,real_type}` ja `/sys/class/power_supply/battery/current_now`; palauta `adb unroot`.
- **Kehitysketju toimii nyt kokonaan palvelimelta** (Mac saa nukkua): `pico_dev.py` valitsee
  adb:n ympäristöstä (`PICO_ADB`, muuten Macin homebrew tai palvelimen
  `~/.local/share/platform-tools/adb`); firmware-setti rakennetaan puhelimessa
  (`run-as … cp -r <vanha setti> <uusi>`, muuttuneet tiedostot `adb push` + `run-as cp`,
  MANIFEST.json puhelimen `sha256sum`-tulosteesta) ja flashataan sovelluksen restore-intentillä.
  Todennettu 17.9.2026 23:07: `RESTORE_OK 20260917-devsafe6 n=17`, `pico_dev.py verify` → `SAFE_OK`,
  `VERIFIED 17/17`.
- **`20260917-devsafe6`:** esiuuton nousu kahdessa portaassa (80 % duty puoleen tavoitteesta, sitten
  25 %) — korjausyritys uuttojen 3–5 ylitykseen (2,0 → 4,1…4,5 bar). Isäntätestit 22/22.
  **Todentamatta oikealla uutolla** (keitin ei ollut käytettävissä).

### Ensimmäinen oikea uutto ja esiuuton korjaus 18.9.2026 (setti `20260918-devsafe7`)

Kaikki tehty lukemalla puhelimen logcatia ja puhelimessa olevaa firmware-varmuuskopiota; Picolle ei
lähetetty mitään (keitin oli käyttäjän käytössä). Loki
`legacy/pico-devsafe7-20260918-testit/uutto-20260918-0656-devsafe6-ble.log` (BLE-telemetria ~3 Hz,
klo 06:30 alkaen).

**Miten telemetria luetaan ilman siltaa:** `adb connect 192.0.2.11:5555` ja
`adb logcat -v time -s flutter | grep '\[DATA\]'`. Logcat tyhjentää ensin koko 4 M puskurin, joten
mukaan tulee ~2,5 h historiaa. Kenttä `mode` kertoo vaiheen (`IDLE`, `BREW`,
`pre-infusion pressure build-up`, `pre-infusion main`, `brew loop`, `soft pressure release`, `STEAM`).

**Huuhtelut eivät ole vika.** Klo 06:36:37, 06:36:46 ja 06:51:40 uuttokytkin oli päällä 1,7 / 0,9 /
1,4 s eikä paine noussut yli 0,82 barin. Käyttäjä: **huuhteluja**, ei kahvia korissa. Samalla näkyi
lepopaineen lämpölaajeneminen: 11,5 bar valui hitaasti ja venttiilin avaus pudotti sen 0,45 bariin
0,2 s:ssa.

**Käyttäjän vaatimus:** pumppua ei saa katkoa huuhtelussa eikä muutenkaan, kun paine on selvästi
tavoitteen alla.

**Mitattu oikea uutto klo 06:56:42** (`devsafe6`, tavoitteet 2,0 / 8,0 bar, 29,6 s) — ensimmäinen
oikealla kahvikakulla mitattu käyrä tästä firmware-sukupolvesta:

| Vaihe | Mitattu |
|---|---|
| Esiuuton rakennus | 0 → 1,0 bar nopeasti, **1,0 → 1,5 bar 2,6 s** (25 %:n porras) |
| Pito alkoi | 5,0 s kohdalla, huippu **3,84 bar** 0,6 s:ssa (tavoite 2,0) |
| Uutto | min 6,46 / max 9,41 / ka 7,90 / sd 0,94 bar (3 Hz näytteistys, aliasoi nopean heilahtelun) |
| Kattila | 98,7 → 86,8 °C uuton aikana |

**Juurisyy (mallinnettu).** `real_plant_sim.py` sovittaa pumppumallin juuri tähän käyrään
(`dp/dt = 6,7·pumppu − 1,24·p`, viive 70 ms; neulaventtiiliin sovitettu `shot_test.py`-malli nousee
25 %:n dutylla 5 bar/s, oikea kakku 0,19 bar/s). Sillä mallilla **`devsafe6`:n 25 %:n porras ei voi
saavuttaa tavoitetta**: se tasapainottuu ~1,35 bariin, kun 2,0 barin pito vaatii dutyn 0,37. Uutossa
pito käynnistyi vasta kun kohinapiikki 16,7 ms:n keskiarvossa ylitti 1,9 barin, ja silloin
`max_duty` palasi ykköseen → 3,84 bar. Ylitys ei siis ole viritysvirhe vaan rakennusvaiheen
rakennevika.

**Korjaus (setti `20260918-devsafe7` — ei flashattu erikseen, sisältyy settiin `20260918-devsafe8`; Mac `legacy/pico-devsafe7-20260918/` + `MANIFEST.json`,
testit `…-testit/`, 17 tiedostoa):**

- `classes.PumpPressureController`: uusi parametri `continuous_error` (oletus 1,0 bar). Rele
  pidetään päällä yhtäjaksoisesti ilman aikasuhteista ikkunaa aina kun `tavoite − paine` ylittää sen
  **tai** paine on alle puolet tavoitteesta (pelkkä absoluuttinen raja jättäisi matalat tavoitteet —
  liukusäädin alkaa 1 barista — pätkimään huuhtelussa). Integraattoria ei kasvateta siinä haarassa.
- `classes.PumpPressureController`: anti-windup vertaa nyt *sovellettuun* rajaan `max_duty`, ei
  kiinteään 1,0:aan.
- `functions.pre_infusion`: kova duty-katto poistettu, tilalle **tavoitteen ramppi** 2,0 bar/s.
  Yhtäjaksoisen alueen ajan tavoitteena on lopullinen paine (pumppu käy tauotta); kun paine saavuttaa
  alueen rajan, ramppi lähtee siitä paineesta ja pito alkaa kun ramppi on perillä — ei kohinapiikistä.
  Ylitys maksaa silloin noin `ramppi × viive` ≈ 0,14 bar askelvasteen sijaan.

**Todisteet:**

- `shot_test.py` **26/26** (aiemmat 22 + kolme uutta: iso virhe pitää pumpun päällä myös
  `max_duty = 0.25`:llä, pieni virhe modulöi edelleen, 4 s huuhtelu ilman yhtään katkaisua).
  Uudet testit ajettu myös `devsafe6`:ta vasten: **2 punaista**, huuhtelussa **41 katkaisua**.
- `real_plant_sim.py` (sovitettu malli, 5 ajoa): tavoitteeseen 1,50 s, huippu **2,14 bar** —
  mitattu `devsafe6`-uutto 5,0 s ja 3,84 bar.
- `preinf_sim.py` (neulaventtiilimalli): huippu 3,12 bar, `devsafe6` 3,22. **Odotusarvo: testiuutto
  neulaventtiilikahvalla näyttää yhä ~3 baria eikä se ole regressio** — siinä nousu on 26 bar/s ja
  ylitys tulee pelkästä 70 ms:n viiveestä. Viiveen ennakointi (pumppu kiinni ennen rajaa nousunopeuden
  perusteella) on tekemättä.
- `mpy-cross` kääntää molemmat muutetut tiedostot.

**Sivuhavainnot:**

- `devsafe6`:n `MANIFEST.json`:issa on 18. merkintä `pid_log.txt`, jota kansiossa ei ole. Palautus meni
  silti läpi (`RESTORE_OK n=17`), koska se iteroi kansion tiedostot eikä manifestia. `devsafe7`:n
  manifesti tehtiin ilman haamuriviä (17/17).
- Soft pressure releasen aikana telemetria näytti jäätynyttä 8,20 baria 5 s: BLE lähettää
  välimuistiarvoa `brew_data.pressure`, jota mikään silmukka ei siinä vaiheessa päivitä.
- Etätestiuutot 3–5 eivät koskaan lukeneet uuttokytkintä (`tshot` antaa oman `keep_running`-ehtonsa),
  joten kytkinpolku mitattiin nyt ensimmäistä kertaa.

**Tila:** ei flashattu — keitin oli käytössä. Seuraava: flashaus ja oikea uutto, ks. alla.

**Flashaus ja mittaus kun keitin vapautuu** (palvelimelta, keitin voi olla verkkovirrassa):

```bash
A=~/.local/share/platform-tools/adb; P=192.0.2.11:5555
# 1. setti puhelimeen (uusi kansio vanhan viereen)
$A -s $P shell 'run-as com.example.silvia_pico_ui cp -r files/firmware_backup/20260917-devsafe6 files/firmware_backup/20260917-devsafe7'
# 2. muuttuneet tiedostot + manifesti sisään, tiivisteet puhelimen sha256sum:sta
# 3. palautus sovelluksella ja todennus
$A -s $P shell am start -n com.example.silvia_pico_ui/.MainActivity --es espressopico_restore_backup 20260917-devsafe7
python3 Infra/iot/expresso/pico_dev.py verify <MANIFEST.json>     # odota SAFE_OK + VERIFIED 17/17
# 4. testiuutto neulaventtiilillä (odotus: huippu ~3 bar, ks. yllä) ja sitten oikea uutto kahvilla
python3 Infra/iot/expresso/pico_dev.py shot 25 /tmp/tshot6.log
```

### Vaaka käyttöön ja kaukalon painoraja 18.9.2026 (setti `20260918-devsafe8`)

Tarve (käyttäjä): testiajoissa ei saa työntää niin paljon vettä läpi että vesikaukalo vuotaa yli.
Raja on **vain testiuuttoja varten**; normaalikäytössä vaa'alla on kuppi, joten turvalliset luvut ovat
eri ja ne päätetään erikseen.

**Lähtötilanne:** vaaka-ajuri `scale.py` (kaksi HX711-kennoa, DT 18/20, SCK 19, kalibrointi
`scale_cal.json` 2175,04 counts/g) oli flashatussa setissä mukana mutta **sitä ei alustettu
ajossa**: `main.py`:ssä ei ollut `import scale`-riviä eikä `Scale`-oliota, `preset.py`:n `PINS` ei
sisällä vaa'an pinnejä, eikä BLE-telemetriassa ollut paino-kenttää (36 551 `[DATA] RX` -riviä,
0 osumaa `weight`). Painorajaa ei siis voinut rakentaa ennen kuin vaaka luetaan.

**Luotain ennen rakentamista** (`legacy/pico-devsafe8-20260918-testit/scale_probe.py`): devsafe-tila,
`Scale()`, `link_ok()`. Tulos: `LINK_OK True`, lepolukema **772,65–773,31 g**, kennoilla 397 / 376 g,
kohina 12 näytteessä 0,66 g. Vaaka siis on kytketty ja kalibroitu — vasta tämän jälkeen firmwarea
muutettiin.

**Muutokset (5 tiedostoa, setti `20260918-devsafe8`, sisältää myös `devsafe7`:n esiuuttokorjauksen):**

- `main.py`: `Scale()` alustetaan käynnistyksessä; epäonnistuminen tai `link_ok() == False` jättää
  `tray_scale = None` eikä muu firmware muutu (kone ilman vaakaa käynnistyy ennallaan). Uusi taski
  `scale_reader` päivittää `brew_data.weight`ä 20 ms välein `Scale.update()`:lla, joka ei koskaan
  blokkaa — **ei säätösilmukoissa**, jotka on ajoitettu ~1 ms:iin.
- `classes.BrewData`: kentät `weight` (g, `None` jos vaakaa ei ole) ja `weight_limit` (0 = pois),
  `set_weight_limit` rajaa 0–5000 g.
- `commands.py`: komento `wmax:<g>`, **ei tallennu** asetuksiin — testirigin vahti ei saa jäädä
  voimaan normaalikäyttöön, jossa oikea luku on toinen.
- `bluetooth_handler.send_data`: `weight` mukaan telemetriaan välimuistiarvona (ei anturilukua).
- `functions.run_shot`: uusi parametri `limit_weight`; `running()` katkaisee kun
  `weight >= weight_limit > 0`, syy `tray <n> g >= limit <n> g`. `main.py` antaa `True` vain
  testiuutolle (`TS`) — kytkinpolku ei katkea painoon koskaan.

**Todisteet:** `shot_test.py` **35/35** (26 aiempaa + 9 uutta: `wmax` asettaa ja rajaa 0–5000,
`wmax:0` sammuttaa, testiuutto katkeaa rajaan ja releet jäävät nolliin, raja 0 ei katkaise,
kytkinpolku ei katkaise, puuttuva vaaka ei katkaise). `mpy-cross` kääntää kaikki kuusi elävää
tiedostoa. Flash `RESTORE_OK 20260918-devsafe8 n=17`, `pico_dev.py verify` → `VERIFIED 17/17`.
Telemetriassa näkyy nyt `weight: 772.493168`, mikä täsmää luotaimen lukemaan.

**Testaamatta isännällä:** `main.py`:n vaaka-alustus ja `scale_reader` — isäntätestit tuovat sisään
vain `classes`, `functions`, `commands` ja `devsafe`, eivät `main.py`:tä. Todiste niille on
telemetrian `weight`-kenttä laitteelta.

**Tunnettu aukko (korjataan seuraavaan settiin):** jos HX711 lakkaa vastaamasta kesken testiuuton,
`brew_data.weight` jää viimeiseen arvoonsa eikä raja laukea — juuri se tilanne jota vastaan raja on.
Lisätään vanhentumisvahti: raja päällä ja paino yli 2 s vanha → katkaisu.

**Kalibrointi:** `legacy/pico-devsafe8-20260918-testit/tray_calib.py` lukee telemetriaa ja poimii
tasanteet (lukema 3 s ajan ±2 g sisällä), kun käyttäjä täyttää kaukalon maksimiin ja liikuttelee
sitä ~5 s välein. Liikuttelu paljastaa, kuinka paljon sama vesimäärä lukee eri tavoin riippuen
siitä miten kaukalo istuu kahdella kennolla; turvaraja asetetaan **pienimmän** tasanteen alle.

### Vaa'an tarkkuus ja kaukalon painoraja 18.9.2026 (setti `20260918-devsafe9`)

Tehtävä (käyttäjä): testiajoissa ei saa työntää niin paljon vettä läpi että vesikaukalo vuotaa yli.
Raja on **vain testiuuttoja varten**; normaalikäytössä vaa'alla on kuppi ja luvut ovat toiset.

**Firmware `20260918-devsafe9`** (Mac `legacy/pico-devsafe9-20260918/`, sisältää `devsafe7`:n
esiuuttorampin ja `devsafe8`:n vaaka-alustuksen; flash `RESTORE_OK n=17`, `VERIFIED 17/17`):

- `main.py`: `Scale()` alustetaan käynnistyksessä (ennen tätä vaaka-ajuri oli flashatussa setissä mutta
  **sitä ei koskaan alustettu** — `main.py`:ssä ei ollut `import scale`); taski `scale_reader`
  päivittää `brew_data.weight`ä 20 ms välein ei-blokkaavalla `Scale.update()`:lla, ei säätösilmukoissa.
- `commands.py`: `wmax:<g>` absoluuttinen raja, `wrise:<g>` yhden uuton aikana kertyvä lisäys,
  molemmat 0 = pois, kumpaakaan ei tallenneta asetuksiin.
- `functions.run_shot`: `limit_weight=True` vain testiuutolle (`TS`), kytkinpolku ei katkea painoon.
  Katkaisu vaatii **kaksi peräkkäistä näytettä** rajan yli (telemetriassa nähtiin yksittäisiä −16 g
  piikkejä, 0,19 % näytteistä); **vanhentumisvahti** katkaisee jos paino on yli 2 s vanha, koska
  jäätynyt lukema tekisi rajasta näennäisen; jos raja on asetettu eikä vaakaa ole, uutto ei käynnisty.
- `bluetooth_handler`: paino pyöristetään 0,1 g:aan ja ylipitkä paketti pudottaa vain paino-kentän —
  ilman tätä `weight` nosti pisimmän tilamerkkijonon paketin 246 B:hen ja **koko paketti hävisi juuri
  uuton aikana** (`notify dropped: 246 B > 240`).
- Isäntätestit `shot_test.py` **49/49**.

**Mittausmenetelmä** (`legacy/pico-devsafe9-20260918-testit/`): `scale_log.py` kirjaa telemetrian
CSV:ksi, `scale_stats.py` ja `scale_steps.py` laskevat ikkunat ja askeleet, `shot_measure.py` mittaa
uuton toimittaman veden. Menetelmän ydin: **erotusmittaus, johon ei kosketa**, suora sovitus
molemmin puolin ja arvo luettuna uuton alku- ja loppuhetkellä. Validoitu synteettisellä datalla
±0,1 g (korjaamaton erotus olisi 5,8 g pielessä). Portti kieltäytyy mittaamasta jos ryöminta ei ole
tasaantunut (puoliskojen kulmakertoimet eroavat yli 1 g/min).

**Kaukalon nostaminen pilaa vakauden pitkäksi aikaa:** heti takaisin laskun jälkeen lukema nousi
+13 g/min ja oli yhä liikkeessä 10 minuuttia myöhemmin (+12 g yhteensä). Siksi kaikki konemittaukset
tehdään peräkkäin koskematta, ja referenssipunnitus vasta viimeisenä.

**Mitatut suureet:**

| Suure | Arvo |
|---|---|
| Kohina rauhallisessa tilassa | sd 0,11–0,5 g |
| Kaukaloon mahtuu vettä | 355 g (tyhjä 417,8 g ritilän kanssa, täysi 769–780 g) |
| Virtaus testiuutossa (neulaventtiili, ei vastusta) | **8,7 g/s** |
| Kuollut aika, seisonut kone (ilmaa boilerissa) | **yli 5 s** — 5 s uutto toimitti vain 3,46 g |
| Kuollut aika, heti edellisen jälkeen | **0,7 s** |
| 25 s uutto toimitti | 218–219 g |

**Vaa'an tarkkuus — ratkaiseva löydös.** Sama tunnettu 293,9 g kuppi kolmessa kohdassa kaukaloa:

| `trim_b` | oikea | vasen | keski | suurin virhe |
|---|---|---|---|---|
| 1,0000 | 293,25 | 275,93 | 275,78 | 18,12 g |
| 1,0525 (nykyinen) | 296,69 | 286,77 | 282,42 | 11,48 g |
| 1,1230 (sovitettu kahdesta) | 301,30 | 301,30 | 291,33 | 7,40 g |

Kerroin sovitettiin tuhannesosan välein 1,0–1,4: **paras mahdollinen jättää 9,98 g sijaintivirhettä.**
Kahden kennon malli ei kuvaa mekaniikkaa — kaukalo ei voi seistä kahden pisteen varassa, ja kolmas
tukipiste vie vaihtelevan osuuden painosta ohi kennojen. **Sijaintivirhettä ei voi kalibroida pois.**

Jakautuneella kuormalla virhe on sen sijaan johdonmukainen: kaukalo 170,0 g → kone 164,10 g
(−3,47 %), vesi 228,8 g → kone 222,32 g (−2,83 %). **Vesi on jakautunut kuorma**, joten sen mittaus
on toistettava.

**Suositukset:** `trim_b` ennalleen (sovitettu arvo parantaisi keskittyneitä massoja mutta siirtäisi
jakautuneita); `scale` 2175,04 → noin **2107** (+3 %) jos jakautuneet mittaukset halutaan absoluuttisesti
oikeiksi; turvaraja ensisijaisesti `wrise` (immuuni absoluuttiselle virheelle ja ryöminnälle),
`wmax` karkeana varmistuksena; **jalokivivaakaa ei kannata ottaa käyttöön** ennen kuin tuenta on
korjattu mekaanisesti — 0,01 g referenssi ei auta kun sijaintivirhe on 7–10 g.

**Rajojen todennus laitteessa 18.9.2026 (setti `20260918-devsafe10`):**

Ensimmäinen todennusyritys **epäonnistui ja paljasti kaksi vikaa**. `wrise:40` kuitattiin `CMD_OK`,
mutta uutto ajoi loppuun ja toimitti **246,7 g**. Syyt:

1. Setti `devsafe9` oli koottu ja flashattu **ennen** kuin `wrise`-koodi oli kirjoitettu, joten
   laitteessa oli eri koodi kuin työkopiossa. **Sääntö: setti kootaan vasta kun muutokset on tehty
   ja testattu.**
2. `main.py` tulosti `CMD_OK` **jokaiselle** luetulle riville riippumatta siitä tunnistiko
   `handle_command` sen. Kuittaus ei siis todistanut mitään, ja tuntematon komento näytti
   hyväksytyltä. Korjattu: `handle_command` asettaa `brew_data.command_known`, ja main tulostaa
   `CMD_UNKNOWN` kun komentoa ei tunnisteta. Kolme isäntätestiä.

Toinen todennus meni läpi: `CMD_UNKNOWN eitallaista:1` mutta `CMD_OK wrise:20`, ja uutto katkesi
`TS_END reason=shot added 22 g >= 20 g`. Käyrästä mitattu todellinen nousu **+28,6 g**, eli
**jälkivalumaa 6,6 g** katkaisun jälkeen 8,7 g/s virtauksella.

**Käytössä olevat arvot:** `wrise:250` (yhden uuton katto; normaali 25 s uutto toimittaa 218 g),
`wmax:470` (ilman ritilää). **Ritilä painaa ~254 g**, joten ritilän kanssa oikea arvo on `wmax:720` —
väärä kokoonpano tekee rajasta joko turhan tai jatkuvasti laukeavan.

**Rajat tallennetaan asetuksiin (`20260918-devsafe12`).** Alkuperäinen päätös olla tallentamatta
niitä perustui virheelliseen oletukseen, että testirigin raja voisi vuotaa normaalikäyttöön: rajat
luetaan vain kun `run_shot` saa `limit_weight=True`, mikä tapahtuu vain `tshot`-polulla eikä koskaan
uuttokytkimellä. Tallentamattomuus tarkoitti käytännössä, että suoja oli hiljaa pois päältä jokaisen
käynnistyksen ja flashin jälkeen — muistikuorma käyttäjälle, ei turvatoiminto. Nyt `save_settings` ja
`load_settings` käsittelevät `weight_limit`- ja `weight_rise_limit`-avaimet, setterit merkitsevät
asetuksen muuttuneeksi, ja vanha `settings.txt` ilman avaimia pitää rajat pois päältä. Neljä
isäntätestiä. **Todennettu laitteella:** rajat asetettiin, `machine.reset()`, ja käynnistyksen
jälkeinen ensimmäinen testiuutto tulosti `limits=wmax:470 wrise:250` ilman että niitä asetettiin
uudelleen.

**Setti `20260918-devsafe11`** teki rajojen tilan näkyväksi: `TS_START`-rivi päättyy kenttään `limits=`, joka on `OFF` tai lueteltu arvo. Todennettu
laitteella flashin jälkeen (`limits=OFF`) ja rajojen asettamisen jälkeen
(`limits=wmax:470 wrise:250`). `main.py` ei ole isäntätestien kattama, joten laitteen loki on ainoa
todiste tälle.

**Lämpöharha selitetty (kolmas referenssi 18.9.2026).** Käyttäjän punnitus 454,5 g (kaukalo + vesi,
kuiva kaukalo 170,0 g) antoi vedeksi 284,50 g. Koneen **toimitusmittaus** 275,30 g → −3,23 %, mutta
koneen **taso nostohetkellä** 260,40 g → −8,47 %: lukema oli valunut 14,9 g sillä aikaa kun vesi
seisoi, vaikka vesi oli tallella. Sama toistui ensimmäisellä kerralla (18 g). Kuiva 293,9 g kuppi ei
tee niin 12 minuutissa. **Syy on lämpö:** kuuma vesi lämmittää kaukalon ja kennot ja lukema valuu
lämpötilan mukana — ei haihtumista eikä kuormavirumaa. **Mittaus on siis tehtävä heti uuton jälkeen**,
kuten `shot_measure.py` tekee (sovitus takaisin uuton loppuhetkeen).

**Kalibrointi neljällä pisteellä — yksi kerroin ei riitä.** 57,3 → 58,60 (**+2,26 %**),
170,0 → 164,10 (−3,47 %), 228,8 → 222,32 (−2,83 %), 284,5 → 275,30 (−3,23 %). Kolme isointa antaisivat
keskiarvon −3,18 % ja `scale`-korjauksen 2175,04 → 2108, mutta **pienellä massalla merkki kääntyy**:
vaaka näyttää liikaa. Suora sovitus antaa muodon `kone ≈ 3,9 g + 0,954 × tosi` eli vahvistusvirhe
−4,6 % ja ~4 g nollapistesiirtymä. Neljä eri tavalla mitattua pistettä ei riitä laitteen pysyväksi
asetukseksi, joten **kalibrointia ei kirjoitettu**. Kunnollinen sarja: ≥ 5 pistettä 20–300 g väliltä,
kaikki vettä, kaikki erotuksena, kaukaloa nostamatta välissä ja samalla asennolla.

### Esiuuton ramppi ja PI-säätö todennettu laitteella 18.9.2026

Aiemmat testiuutot eivät koskaan poistuneet esiuutosta (`loops=0`), koska neulaventtiili päästi
vapaasti eikä paine noussut (−0,1 bar). Käyttäjä asetti virtausta rajoittavan venttiilin paikalleen,
minkä jälkeen uutto kulki koko polun (`loops=12735`, `max_loop_ms=83`).

| Mittaus | `devsafe5` (sama rigi) | `devsafe10` |
|---|---|---|
| Esiuuton huippu (tavoite 2,0) | 4,1–4,5 bar | **3,00 bar** |
| Uuton vaihteluväli (tavoite 8,0) | 6,2–10,6 bar | **7,2–8,7 bar** |
| Uuton keskiarvo | 8,01 bar | **7,90 bar** |
| Uuton hajonta | 0,58 bar | **0,31 bar** |

Rekisterin avoin kohta "yksittäiset 10–11 bar piikit" ei esiintynyt kertaakaan. Rampin toiminta näkyy
`PI`-rivien tavoitesarakkeessa (1,00 → 1,30 → 2,00). Ennusteet osuivat: simulaatio antoi
neulaventtiilille esiuuton huipuksi 3,12 bar (mitattu 3,00) ja PI:lle mitatun hajonnan 0,38–0,40
(mitattu 0,31). **Varaus:** venttiilin asento ei ole sama kuin `devsafe5`-testeissä, joten vertailu ei
ole täysin kontrolloitu.

Kuristettu virtaus **2,3 g/s** (56,9 g / 25 s); ilman kuristusta 8,7 g/s.

### Reaaliaikainen virtaus 18.9.2026 (setti `20260918-devsafe14`)

Tehtävä (käyttäjä): virtaus pitää saada laskettua hyvin reaaliaikaisesti.

**Mitattu raja ensin** (`legacy/pico-devsafe14-20260918-testit/flow_rate_probe.py`, lukee vain,
devsafe + `machine.reset()`): HX711-pari antaa näytteen **86,2 ms välein eli 11,6 näytettä/s**
(pari luetaan samalla kellolla, ei erikseen), yksittäisnäytteen hajonta **0,22–0,26 g**, ja
peräkkäisten näytteiden erotuksen hajonta on `sd·√2`. Kohina on siis **valkoista**, mikä on hyvä
uutinen: sovitus saa täyden `√N`-hyödyn. Nämä kaksi lukua rajaavat kaiken, mitä reaaliaikaisuudesta
voi luvata — pienimmän neliösumman kulmakertoimen hajonta `T` sekunnin ikkunassa on
`0,25·√12/(T·√(11,6·T))` g/s ja 90 %:n vaste tulee noin `T`:ssä.

**Ehdokkaat vertailtiin ennen koodia** (`flow_sim.py`, synteettinen uutto mitatuilla luvuilla, viisi
siementä):

| Estimaattori | Kohina | 90 %:n viive | Pahin virhe yhdestä −16 g piikistä |
|---|---|---|---|
| nykyinen `flow()`: mediaani-8 → LS 16 näytettä | 0,12 g/s | 1,67 s | 0,63 g/s |
| LS raaka 0,5 s | 0,69 g/s | 0,64 s | **27,98 g/s** |
| LS raaka 1,0 s | 0,23 g/s | 1,07 s | 7,97 g/s |
| **LS + mediaani-3, 1,0 s (valittu)** | **0,22 g/s** | **1,07 s** | **1,00 g/s** |
| α-β, τ = 0,35 s | 0,17 g/s | 1,38 s | 9,14 g/s |
| α-β + mediaani-3, τ = 0,35 s | 0,16 g/s | 1,53 s | 0,66 g/s |

Kolme johtopäätöstä: **mediaani-3 on pakollinen** (ilman sitä yksi −16 g piikki — 0,19 % näytteistä —
heittää virtauksen 8–28 g/s, eli mikä tahansa virtaukseen perustuva katkaisu reagoisi kohinaan);
**α-β ei voita ikkunasovitusta** samalla viiveellä, joten yksinkertaisempi voitti; ja
**viive × kohina on vakio** — 0,5 s viive maksaa ±0,7 g/s, mikä on 30 % kuristetusta 2,3 g/s
virtauksesta.

**Toteutus (6 tiedostoa, setti `20260918-devsafe14`, sisältää `devsafe13`:n kennokohtaisen lokin):**

- `scale.py`: `update()` pitää nyt myös **suodattamattoman** näytesarjan ja siitä mediaani-3:lla
  siivotun sarjan; `flow(span_ms)` sovittaa suoran ikkunan yli. Suodatetusta lukemasta
  derivoiminen olisi hukannut sekä `√N`:n että lisännyt mediaanin ryhmäviiveen sovituksen päälle.
  Painorajat käyttävät entiseen tapaan mediaanisuodatettua `update()`:n arvoa — niitä ei muutettu.
  **Vanhentumisvahti:** yli 500 ms vanhoista näytteistä ei palauteta virtausta vaan `None` —
  jäätynyt lukema ei ole virtaus (sama vika, jota vastaan painon 2 s vahti on `run_shot`issa).
- `commands.py`: `fwin:<ms>` säätää ikkunan 200–3000 ms. **Ei tallennu asetuksiin:** mittausnuppi,
  ei turvaraja — päinvastoin kuin `wmax`/`wrise`, joiden tallentamattomuus oli virhe (devsafe12).
- `bluetooth_handler.py`: virtaus **omassa ~35 B paketissaan** `{"flow": …, "weight": …}`.
  Live-paketti on pahimmalla tilamerkkijonolla **250 B** jo ilman virtausta ja joutuu pudottamaan
  painon mahtuakseen 240 B:hen, joten virtaus ei siihen mahtunut; paino tulee mukana, jotta pari
  saadaan yhdestä paketista silloinkin. Paketin kasaus ja karsinta siirrettiin moduulitason
  funktioihin (`live_payload`, `flow_payload`, `trim_payload`), jotta **paketin koko on
  isäntätestattava** — juuri se testi, joka olisi estänyt 246 B:n paketin katoamisen.
- `functions.py`: `PI`- ja `TS`-rivit päättyvät kenttiin `w=<g> f=<g/s>` (`-` kun vaakaa ei ole).
  Numerokentät pysyivät paikoillaan, joten `analyze_shot.py` lukee rivit ennallaan.

**Todisteet isännällä:** `shot_test.py` **76/76** (pohja 56 + 20 uutta: virtauksen tarkkuus, kohina,
askelvaste, piikki-immuniteetti, alle neljä pistettä, vanhentuminen, `fwin`:n rajaus, live-paketin
karsinta, virtauspaketin sisältö ja koko, lokirivin muoto vaa'atta ja vaa'an kanssa).

**Todennus laitteella:** flash `RESTORE_OK 20260918-devsafe14 n=17`, `pico_dev.py verify` →
`VERIFIED 17/17`. Testiuutto (`tshot:20`, rajat `wmax:740 wrise:45`) katkesi oikein
`reason=shot added 46 g >= 45 g`. Lokin 10 Hz virtaus verrattuna samasta painosarjasta laskettuun
**keskitettyyn** (viiveettömään) 1 s referenssiin:

| Suure | Mitattu |
|---|---|
| Virtaus levossa | **+0,14 ± 0,36 g/s** (ennuste ±0,23) |
| Paino alkaa nousta | t+0,80 s |
| Raportoitu ylittää 50 % huipusta | 0,50 s nousun alusta |
| Raportoitu ylittää 90 % huipusta | 1,00 s nousun alusta |
| Tasainen virtaus, viimeiset 2 s | **10,40 ± 0,53 g/s**, referenssi 10,37 → harha **+0,03 g/s** |
| Paras yhteensopivuus referenssiin | **viiveellä 0,30 s** (rms 0,42 g/s) |

Eli virtaus on käytännössä harhaton ja sen tehollinen viive on **0,3 s**, mikä on ikkunan
puolikasta parempi. Kohina 0,53 g/s tasaisella virtauksella on suurempi kuin synteettinen 0,22 —
osa siitä on oikeaa vaihtelua, koska pumppu sykkii.

**Sivuhavainnot:**

- **Kuristusventtiili on auki:** uutto antoi 10,4 g/s, ei 2,3 g/s. Virtauksen tarkkuus on siis
  mitattu vain nopeassa päässä; kuristettu 2,3 g/s on mittaamatta.
- **Setti `devsafe13` on vain puhelimessa.** Se tehtiin toisessa istunnossa klo 13:02 (kennokohtaiset
  painot `weight_a`/`weight_b` lokiriveille sijaintivirheen tutkimista varten), flashattiin ja
  todennettiin `VERIFIED 17/17`, mutta sitä ei arkistoitu Macille eikä sen muutos ole
  isäntätestien kattama: `shot_test.py` **kaatui** `AttributeError: weight_a`, koska testin
  `BrewData`-runko ei tuntenut kenttiä. Korjattu tässä setissä. `devsafe14` sisältää sen muutokset;
  `devsafe13`:n oma arkistointi on tekemättä.
- **Flashausta ei saa koskettaa kesken:** ensimmäinen palautusyritys **epäonnistui**
  (`RESTORE_FAIL … no size ack for /bluetooth_handler.py`), koska ajoin `pico_dev.py verify`:n 12 s
  palautuksen käynnistämisen jälkeen — silta palvelee yhtä asiakasta, ja Ctrl-C tappoi flasherin
  istunnon. Laite jäi ehjäksi (`VERIFIED 17/17` devsafe13:a vasten, mitään ei ollut kirjoitettu).
  **Sääntö: odota `RESTORE_OK` logcatista ennen kuin kosket sarjalinkkiin.**
- `bluetooth_handler.py`:ssä on **kaksi `send_data`-määrittelyä** samassa luokassa; ensimmäinen
  (neljä kenttää) on kuollutta koodia, koska myöhempi korvaa sen. Ei korjattu tässä.
- **Kaukalo on nyt 713 g** (täysi ~770–780 g) ja rajat tallennettuina `wmax:740 wrise:45`.
  Seuraava testiuutto katkeaa ~27 g:n jälkeen; kaukalo pitää tyhjentää ja rajat asettaa uudelleen.

**Toinen todennus kuristimella, tyhjä kaukalo 18.9.2026** (`tshot:25`, rajat `wmax:720 wrise:120`,
tyhjä kaukalo ritilän kanssa lukee 423,8 g; koko uutto meni läpi, `loops=7938`):

| Vaihe | Paine | Duty | Virtaus raportoitu | Painosta laskettu | Ero |
|---|---|---|---|---|---|
| Esiuutto (tavoite 2,0 bar) | 1,76 ± 0,37 bar | 0,21 | 0,83 ± 0,63 g/s | 0,89 g/s | **−0,06 g/s** |
| Uutto (tavoite 8,0 bar) | 8,15 ± 0,46 bar | 0,61 (max 1,00) | 4,29 ± 0,88 g/s | 4,23 g/s | **+0,07 g/s** |

Virtausmittari on siis todennettu kolmessa regiimissä — 0,8, 4,3 ja 10,4 g/s — ja harha on joka
kerta alle 0,1 g/s. **Kuristus on liian löysä:** 8 barin pitäminen vaatii dutyn 0,61 ja se saturoituu
välillä ykköseen, kun aiemmalla kuristuksella sama paine hoitui dutylla 0,30 (`learned_ff_brew`).
Kahvimaiseen 2–2,5 g/s virtaukseen venttiiliä pitää **kiristää** noin puoleen nykyisestä
läpäisystä. Uutto käytti 57 g vettä (423,8 → 480,4 g).

**Kolmas todennus, kuristusta lisätty 18.9.2026.** Käyttäjä kiristi säätimen rullaa niin että
ulkokehä liikkui 2–3 mm. Vaikutus uuttovaiheeseen (tavoite 8,0 bar): virtaus **4,29 → 2,72 g/s**,
duty **0,61 → 0,46**, paine 7,91 ± 0,54 bar, `learned_ff_brew` 0,63 → 0,44. Esiuutto saavutti nyt
tavoitteensa (1,95 bar / 2,0 bar, virtaus 1,30 g/s) — löysällä kuristuksella se jäi 1,76 bariin.
Virtausmittarin harha oli taas alle 0,1 g/s (uutto −0,03, esiuutto +0,09 g/s), eli viisi regiimiä
välillä 0,8–10,4 g/s. **Kalibrointisuhde:** 2–3 mm kehäliikettä vei virtauksesta 37 %, joten
2,3 g/s:aan riittää noin 1 mm lisää. Duty saturoituu ykköseen yhä 4 % ajasta.

**Neljäs todennus, 1 mm lisää 18.9.2026 — kehäliikkeen vaikutus ei ole lineaarinen.** Odotus oli
−15 % virtausta; mitattu **2,72 → 2,64 g/s eli −3 %**, duty 0,46 → 0,43, saturaatio 4 % → 1 %,
paine **7,99 ± 0,45 bar** (paras tähän asti), `learned_ff_brew` 0,43. Eli 2–3 mm vei 37 % ja
seuraava 1 mm vain 3 %: ensimmäinen liike osui jyrkälle osuudelle tai rullan kehäliike ei käänny
neulan liikkeeksi yksi yhteen (välys). Säätöpiiri on nyt parhaassa tilassaan mitatuista
(saturaatio 1 %, paineen hajonta 0,45 bar), joten tämä on käyttökelpoinen työpiste vaikka virtaus
on 0,1–0,4 g/s tavoitteen yli.

**Viides todennus, 2–3 mm lisää 18.9.2026 — sama liike vei nyt 70 %.** Virtaus **2,64 → 0,79 g/s**,
duty 0,43 → 0,20, paine 8,07 ± 0,31 bar ilman saturaatiota, `learned_ff_brew` 0,21, vettä vain
22 g koko uutosta. Kuristus on nyt **liian tiukka** (tavoite 2,2–2,5 g/s). Yhteenveto vasteesta:
2–3 mm kiristystä −37 %, seuraava 1 mm −3 %, seuraava 2–3 mm −70 %. **Rullan kehäliike ei ole
käyttökelpoinen mitta-asteikko** tälle venttiilille: vaste on epälineaarinen ja siinä on välys,
joten säätöä pitää hakea virtauslukemasta eikä millimetreistä — nyt se onnistuu, koska virtaus
näkyy lokissa 10 Hz.

Virtausmittarin harha oli tässä uutossa **+0,01 g/s** (uutto) ja +0,02 g/s (esiuutto) eli mittari on
nyt todennettu välillä **0,3–10,4 g/s**, joka on koko käytettävä alue.




**Mitä reaaliaikaisuudelle voi vielä tehdä.** 0,3 s tehollinen viive ±0,4 g/s:n tarkkuudella on
tämän vaa'an raja kahdella tavalla: näytetaajuus 11,6 Hz ja kohina 0,25 g. Alle sen pääsee vain
kahdella tavalla, ja kumpikaan ei ole tehty: **HX711:n 80 SPS** (RATE-jalka maahan, juotostyö;
näytekohtainen kohina kasvaa, joten netto on mittaamatta) tai **mallifuusio**, jossa pumpun duty ja
paine kantavat nopean dynamiikan ja vaaka korjaa hitaasti — pumppumalli on jo sovitettu
(`dp/dt = 6,7·pumppu − 1,24·p`) ja `learned_ff_brew` oppii kakun vastuksen uuton aikana.
Sovellus ei myöskään vielä näytä virtausta: uusi paketti menee läpi `_dataController`iin, mutta
mikään kuluttaja ei lue `flow`-avainta.

## Virtausohjaus (VIRTAUSSAATO, 18.9.2026) — kaskadi, simuloitu, ei vielä ajettu laitteella

**Arkkitehtuuri.** Uuttovaiheen säädettävä suure voi nyt olla virtaus g/s. Ulompi `FlowController`
(`classes.py`) antaa **paineen asetusarvon**, jonka nykyinen `PumpPressureController` ajaa dutyksi
muuttumattomana. Kaskadi eikä suora virtaus→duty-säätö siksi, että virtausestimaatin tehollinen
viive on 0,30 s ja näytetaajuus 11,6 Hz: ulompi silmukka jää joka tapauksessa alle 0,5 Hz:n, joten
sisemmän lisäviive ei maksa mitään, ja vastineeksi paine pysyy rajattuna suureena, `learned_ff_brew`
säilyy ja paluu vanhaan on yksi lippu.

**Säädin.** Nopeusmuotoinen PI (`sp += kp·Δe + ki·e·dt`, `kp=0,55`, `ki=2,0`), asetusarvo rajattu
2,0–10,5 bar, rampitus 2,2 bar/s ja **etäisyysraja** `|sp − p| ≤ 0,8 bar`. Etäisyysraja on se, joka
pitää sisemmän säätimen pois `continuous_error = 1,0` -tilasta, jossa duty pakotetaan ykköseen.
Nopeusmuoto + rajaus on samalla anti-windup: integraattoria ei ole.

**Turva ennallaan.** Esiuutto, 13 bar katkaisu, `wmax`/`wrise`, `tshot:stop`, kytkin, aikaraja ja
`finally`-sammutus eivät muutu. Vaa'an vaietessa kolme peräkkäistä `None`-lukemaa (≈260 ms) palauttaa
uuton kiinteään paineasetusarvoon ja kirjaa `TS_FLOW_OFF reason=scale silent`; ilman vaakaa
virtaustila ei käynnisty lainkaan.

**Komennot ja loki.** `fmode:on|off` ja `fset:<0,5–5,0>`, kumpikaan ei tallennu — laite on
käynnistyksen ja flashauksen jälkeen aina paineohjauksessa. `TS`-rivin kolmas kenttä tulostaa nyt
*voimassa olevan* tavoitteen (liikkuva asetusarvo), ja riville on lisätty loppuun `fsp=<g/s>` ja
`fsat=<0|1>`; `TS_START` kertoo tilan kentässä `fmode=`. Kenttäjärjestys ennen `w=`-häntää ei
muuttunut, joten `analyze_shot.py` lukee rivit entiseen tapaan.

**Todennus isäntäsimulaatiolla** (`testit/flow_ctrl_sim.py`, ajetaan palvelimella ilman laitteistoa):
malli `dp/dt = 6,7·u − k·p`, ulosvirtaus `k·p`, toimilaitteen viive 70 ms, vaakanäyte 86 ms välein
kohinalla sd 0,25 g **oikean `scale.Scale`-estimaattorin läpi**, ja väitteet luetaan firmwaren omista
lokiriveistä. Ajossa kuristusta muutetaan kesken uuton (`k`: 0,50 → 0,30 → 0,50 → 0,166). Tulos 9/9:
virtaus palaa ±0,25 g/s sisään alle 2 s:ssa kummastakin muutoksesta, paine ei ylitä 12,0 bar (huippu
11,24), saavuttamattomassa tavoitteessa paine asettuu katolle ja `fsat` nousee 5,34 s kohdalla, uutto
ei katkea, ja `fmode:off` toistaa vanhan paineohjauksen (poikkeama 0,14 bar). `shot_test.py` pysyy
vihreänä muuttumattomana.

**Simulaatio löysi kolme suunnitteluvirhettä**, joista yksi olisi näkynyt vasta laitteella:
`fsat`-lippu oli kirjoitettu hetkellisenä ehtona, jolloin **yksi** kohinainen virtauslukema nollaa
kahden sekunnin kertymän — sama 0,25 g kohina on laitteessa, joten lippu olisi välkkynyt lokissa
koko uuton ajan. Lippu on nyt vuotava laskuri ja Schmitt-liipaisin (nousu 2,0 s nettoa, lasku 4,0 s).
Kaksi muuta olivat testin mielivaltaisia lukuja, jotka korvattiin johdetuilla.

**Tekemättä:** flashaus ja laitteistotesti. Testi on `tshot:25` virtaustilassa niin, että kuristinta
muutetaan kesken ajon; odotus on, että **virtaus pysyy ja paine liikkuu** — päinvastoin kuin
paineohjauksessa, jossa sama kiristys vei virtauksen 4,29 → 0,79 g/s. Viritysarvot ovat
simulaatiosta, eivät kahvikakusta: `kp`, `ki` ja `rate_bar_s` haetaan uudelleen ensimmäisestä
oikeasta uutosta. Lähteet: `paketit/VIRTAUSSAATO.md`, `.spec.md`, `.brief.md`, korjaukset 1–3.

## Paineen hallinta ja kalibrointi 19.9.2026

**Lähtökohta:** käyttäjä vaihtoi paineanturin virtalähteen, ja anturi on ratiometrinen — syöttö
siirtää ennen kaikkea **kerrointa**, ei nollaa. Kalibrointi oli siis tehtävä uudelleen.

### Mittarien sijainti ratkaisee mitä saa verrata

Keittimen oma anturi on **vesilinjassa pumpun jälkeen**, referenssimittari on kahvassa eli
**säiliön toisella puolella veden ulostulossa** (käyttäjä). Niiden välissä on painehäviö aina kun
vesi liikkuu, ja häviö kasvaa virtauksen mukana. Tästä seuraa kaksi sääntöä:

- **Lukitussa linjassa mitattu aaltoilu ei kerro uutosta mitään.** Suljetussa piirissä vedellä ei
  ole ulospääsyä, joten yksi pumpun isku nostaa painetta kokonaisen baarin; uutossa sama isku
  työntyy kakun läpi ja vaikutus on murto-osa.
- **Kalibrointia ei saa sitoa yhteen virtaukseen** ennen kuin on osoitettu, ettei ero riipu
  virtauksesta.

### Lukitun linjan mittaukset (eivät kelpaa uuton arviointiin)

Yksi isku ≈ 1 bar. Tavoitteessa 2 bar pito sahasi 1,05–2,82; tavoitteessa 8 bar kaikki kolme
ensimmäistä ajoa keskeytyivät rajaan `overshoot 9,0–9,25`. Iskujen **ikkunapituus ei vaikuta
aaltoiluun**: 100 / 200 / 500 / 1000 ms antoivat heilahdukset 1,79 / 1,41 / 1,77 / 1,16 bar, eli
ajojen välinen hajonta on samaa luokkaa kuin ikkunoiden välinen. Aaltoilun määrää **annos**, ei
annosteluväli — käyttäjän hypoteesi pienemmästä syklistä ei pidä pidossa paikkaansa. Raaka
keskiarvo sen sijaan toistui hyvin: kolme peräkkäistä ajoa 8 barissa antoivat 8,316 / 8,348 /
8,315 eli hajonta 0,4 %.

### Virtaava mittaus on se, joka erottaa anturin virheen hydrauliikasta

Käyttäjän suunnittelema koe: ajetaan sama koneen lukema 8,0 bar eri kuristimen asennoissa ja
kirjataan mittarin lukema kussakin. Virtaus mitataan vaa'alta, joten x-akseli on mitattu suure eikä
venttiilin asento (joka ei ole asteikko: 18.9.2026 sama 2–3 mm kierros vei virtauksesta ensin 37 %
ja sitten 70 %).

| Virtaus | Kone | Mittari | Duty | Hajonta |
|---|---|---|---|---|
| 0,88 g/s | 8,19 | 7,2 | 0,13 | 0,69 |
| 0,65 g/s (korjattu asteikko) | 8,10 | — | 0,14 | 0,56 |
| 2,04 g/s (korjattu asteikko) | 8,02 | "hyvä" | 0,24 | 0,63 |

Virtausestimaatti todennettiin riippumattomasti punnitsemalla: kaukalo keräsi 55 g 27 sekunnissa
eli tasan 2,04 g/s.

**Johtopäätös:** ero ei kasvanut virtauksen kasvaessa 0,9 → 2,0 g/s, joten se on **anturin vakio
eikä hydraulinen paine-ero** tällä alueella. Kalibrointi kirjoitettiin siksi yhtenä offsetina.

### Voimassa oleva kalibrointi

`PCALSET_OK gain=1,0000 offset=−0,990`, tallennettu laitteelle 19.9.2026. Kone luki siis noin
baarin liikaa 8 barin tienoilla; asetus `bp:8.0` tarkoittaa nyt todellista kahdeksaa baria, mikä on
noin bar enemmän kuin ennen korjausta — **kahvin maku muuttuu tämän myötä**, ja vanha tulos
vastaisi nykyistä asetusta ~7,0.

### Mikä kalibrointiajossa muuttui

Vanha velho avasi kiinteän 10 s ikkunan heti ja keskiarvoisti sekunnit 5–10 **riippumatta siitä,
oliko tavoite saavutettu** — hidas nousu tallensi pisteen keskeltä nousua, ja virhe osoitti aina
samaan suuntaan. Uusi ajo (`PCAL-KORJAUS`):

- karkea lähestyminen täydellä syklillä tavoitteeseen −1,5 bar, sitten yksi isku per ikkuna
  (`pcalw:<ms>`, oletus 500);
- **kolme aikatasoa**: raaka lukema on 12 bar hätäraja, 0,3 s suodatin ohjaa pumppua (yksi
  kohinapiikki laukaisi ennen kokonaisen iskun), 1,0 s suodatin tuomitsee asettumisen;
- asettuminen ei tarkoita "tavoitteessa" vaan **"lakannut ajautumasta"** (< 0,15 bar / 2 s)
  tavoitteen tuntumassa (< 1,5 bar) — kapeampaan ei voi osua, kun pienin annos on baari;
- ylitys yli 1,5 bar päättää ajon tallentamatta pistettä;
- pito annetaan tavalliselle painesäätimelle, joka on mitatusti tasaisempi kuin oma annostelu
  (2,85 bar heilahdus vastaan 4,65);
- sarjalinkkiin tulostuvat `PCAL_START`, `PCAL_SETTLED`, `PCAL_ABORT`, `PCAL_END` (mukana
  `p_min`/`p_max`) ja `pcal:st`. Aiemmin koko polku vaikeni ja ajo lennettiin sokkona.

**Velho on silti lukitun linjan työkalu.** Virtaavassa tilassa se ei asetu (hajonta 0,69 > raja) ja
sen lähestymisannostelu on aivan liian pieni (duty 0,034 vastaan tarvittava 0,13). Siksi lisättiin
`pcalset:<gain>:<offset>`, joka kirjoittaa kalibroinnin suoraan tavallisista uutoista mitatuista
luvuista.

### Nolla

`pzero:` ottaa nollan **purkamalla**: lämmitin pois, magneettiventtiili syklissä kunnes raaka-arvo
ei enää muutu, sitten keskiarvo ja offset. Lepolukema ei ole nolla — suljettuna lämpölaajeneminen
vie ~14 bariin, ja uuton jälkeinen purku pysähtyy 1,5 bar **ilmoitettuun**, joka luetaan juuri siitä
kalibroinnista jota epäillään.

### Avoin: pumpun ylireagointi

Keskiarvo osuu, hajonta ei: 0,56–0,69 bar ja huiput 6,1–11,2. Todennäköinen juurisyy on dutyn
kvantisointi — 100 ms ikkuna ja 17 ms askel antavat vain arvot 0, 0,17, 0,34…, ja pidossa tarvittava
duty on 0,13–0,14 eli tasan kahden askeleen välissä. Oma pakettinsa: `paketit/PAINESAADIN-HEILUNTA.md`.

## OnePlus-akkuvahti (palvelin)

- Lähteet: `Infra/iot/expresso/oneplus-akkuvahti.sh`; ajetaan palvelimen cronista 10 min
  välein (`PUHELIN=127.0.0.1:5555`, puhelimen oma root-adbd). `.service` + `.timer` ovat
  palvelimen vanha reitti (systemd --user, 10 min; poistettu käytöstä, ks. **Tila**). Lukee akun
  adb:llä (`~/.local/share/platform-tools/adb`, asennettu 17.9.2026 ilman sudoa, avain
  `~/.android/adbkey`) ja ilmoittaa `ha.sh palvelu notify.mobile_app_iphone`. Lataus tunnistetaan
  `status: 2|5`:stä, ei `AC powered`ista (virrallinen hubi näyttää AC powered akun purkautuessa).
  Rajat `VAROITUS_PCT`/`KRIITTINEN_PCT` luetaan HA:n `input_number.oneplus_akku_varoitus` /
  `input_number.oneplus_akku_kriittinen` -arvoista, oletus 30/15 (V-197, 5.10.2026). Hälytykset:
  akku < varoitusraja ei lataa, < kriittinen raja kriittinen, ei vastaa 2 ajoa (20 min), palautui.
  Tila `~/.local/state/oneplus-akkuvahti/tila`. `--dry-run` testaa.
- Todennettu: logiikka 11 simuloidulla tilalla (`ADB`-tynkä), HA-testi-ilmoitus iPhoneen exit 0.
- HA:n `sensor.one_battery_level` (puhelimen HA-sovellus) on jäässä 27.7.2026 — ei käytettävissä.
- **Käyttöönotto 17.9.2026:** ufw `allow out to 192.0.2.11 port 5555 proto tcp` (käyttäjä ajoi
  Macilta `ssh -t palvelin "sudo ufw …"`). Palvelimen avaimen lisäys suoraan
  `/data/misc/adb/adb_keys`:iin root-adb:llä oli luokittimen estämä (Unauthorized Persistence), joten
  valtuutus tehtiin RSA-dialogista. **Ansa:** dialogi sulkeutui heti itsestään, koska
  `service.adb.tcp.port` oli tyhjä (vain `persist.adb.tcp.port` säilyy käynnistyksen yli) ja
  puhelin on OTG-host-tilassa (ei USB-laitetta) → systemui:n `UsbDebuggingActivity` sulkee
  dialogin USB-irtikytkennän vastaanottimella. Kiertotie: Macilta `adb root` →
  `setprop service.adb.tcp.port 5555` → `adb unroot` → palvelimelta `adb connect` → dialogi pysyi
  auki, käyttäjä hyväksyi. Valtuutus säilyi `kill-server` + uudelleenyhdistyksen yli.
- **Tila:** käytössä palvelimen cronissa (10 min, `PUHELIN=127.0.0.1:5555`). Loki
  `~/.local/state/oneplus-akkuvahti.loki`, rivimuoto `AKKU: 79 % lataa=false rajat=30/60`
  (viim. 7.10.2026 08.00). Siirretty palvelimen systemd-ajastimesta dc8a2ee 26.9.2026 (V-062);
  palvelimen `oneplus-akkuvahti.timer` poistettu käytöstä. Vanha reitti (17.9.2026):
  `~/.config/systemd/user/oneplus-akkuvahti.{service,timer}` → symlinkit repoon,
  `systemctl --user enable --now oneplus-akkuvahti.timer` (Linger=yes); ensimmäinen ajo
  16:04 `AKKU: 81 % lataa=false`, loki `journalctl --user -u oneplus-akkuvahti.service`.

## Aloitus uudessa keskustelussa

Zero-ketju (oletus 5.10.2026): `python3 Infra/iot/expresso/pico_dev.py cmd pcal:st 3` → `CMD_OK pcal:st`.
Mykkä vastaus Picon uudelleenenumeroinnin jälkeen: PICO-HALLINTA.md luku 1, "Ansa". Puhelinketju (historia):

```bash
ssh dev-host 'cd "$HOME/Documents/Koodi/Silvia pico/eXpresso_Grok/legacy/latest" && PATH=/opt/homebrew/bin:$PATH ./tools/dev_station/oneplus_wireless_adb.sh status'
```

Odotettu: `192.0.2.11:5555 device`. Tyhjä lista → `connect`; `Connection refused` → käyttäjä
tekee bootstrapin USB-johdolla.
