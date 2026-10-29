# Picon hallinta OnePlussan kautta — kattava ohje

Lähteet tarkistettu 19.9.2026: sovelluksen Kotlin-lähde Macilla
(`legacy/latest/silvia_pico_flutter_UI/android/app/src/main/kotlin/com/example/silvia_pico_ui/`),
`eXpresso_Grok/docs/{dev_station.md,wireless_dev.md,runbooks/}`, `Infra/iot/expresso/pico_dev.py` ja
`KEHITYSYHTEYS.md`. Rivinumerot viittaavat näihin tiedostoihin.

## 1. Ketju

**Nykyinen ketju 5.10.2026 alkaen: Zero (ZERO-USB-päätös 1.10.2026, EXPRESSO-ZERO-FLASH).** Pico on
kytketty Zeron USB-dataporttiin, ei puhelimeen. Luvut 2–3 ja 6–8 kuvaavat vanhaa puhelinketjua
(`PICO_LINK=phone`).

```
palvelin ──TCP 192.0.2.10:2217 (ser2net raw)──▶ Zero ──USB-CDC /dev/hubi0──▶ Pico W
               ──ssh pico-host──▶ Zero (ser2net 2218 rfc2217, mpremote, picotool, python3-serial)
puhelin ──BLE──▶ Pico W                                                        (telemetria, sovellus)
```

- `pico_dev.py` käyttää Zero-ketjua oletuksena (`PICO_LINK=zero`): ei adb:tä, sovellusta, `ChargerOff`ia
  eikä Shellyä. Shelly (`switch.shellyplus1pm_example`) on OnePlus-hubin laturi, ei keittimen rautaa.
- **Flash:** `pico_dev.py flash pico/MANIFEST.json` (luku 7). Settiä ei rakenneta puhelimeen; lähde on
  repon `pico/` ja sen manifesti (`pico_dev.py manifest pico/MANIFEST.json` laskee sen uudelleen).
  `restore` ja `build_set.py` ovat vain puhelinketjua.
- **Ansa (5.10.2026, toistui kolmesti flashin resettien jälkeen):** Picon uudelleenenumeroinnin jälkeen ser2netin
  raaka 2217 ei välitä mitään kumpaankaan suuntaan, ennen kuin `/dev/hubi0` avataan kerran suoraan Zerolla
  (pelkkä avaus ja sulku riittää). `pico_dev.py` tekee tämän itse ennen jokaista yhteyttä (`ssh pico-host` + pyserial).
  Syy oletettu (DTR ei nouse ser2netin `local`-avauksessa), ei todennettu; pysyvä korjaus kuuluu skoopille `infra zero`.
- **Pehmeä reset (Ctrl-D) vahdin ollessa käynnissä** → laitteistovahti (8 s) nollaa Picon kesken käynnistyksen,
  koska vahti jää päälle eikä sitä ruokita ennen `watchdog_feeder`iä. Käytä `machine.reset()`ia (`safe`, `flash`).

Vanha puhelinketju (`PICO_LINK=phone`):

```
palvelin ──adb TCP 5555──▶ OnePlus 7T Pro (192.0.2.11, trust-VLAN)
                                 ├─ USB-OTG (USB-CDC) ──▶ Pico W   (flash, REPL)
                                 ├─ TCP 2217 PicoBridgeService ──▶ sama USB    (sarjasilta)
                                 └─ BLE ──▶ Pico W                             (telemetria)
```

Mac on vaihtoehtoinen ohjain, ei pakollinen: `pico_dev.py` valitsee adb:n ympäristöstä
(`PICO_ADB`, muuten Macin `/opt/homebrew/bin/adb` tai palvelimen
`~/.local/share/platform-tools/adb`, `pico_dev.py:29-31`). **Koko kehitysketju toimii palvelimelta**
(KEHITYSYHTEYS.md:449).

**Miksi langaton ADB on pakollinen:** Pico varaa puhelimen ainoan USB-portin OTG-hostina, joten
langallista ADB:tä ei voi olla samaan aikaan (`docs/wireless_dev.md`). Portti pysyy yli
uudelleenkäynnistysten asetuksella `persist.adb.tcp.port=5555`; pelkkä `service.adb.tcp.port` ei säily.

## 2. Yhteyden avaus palvelimelta

```bash
A=~/.local/share/platform-tools/adb; P=192.0.2.11:5555
$A connect $P && $A devices          # odotettu: "192.0.2.11:5555  device"
```

`Connection refused` → langaton ADB on pois päältä: Macilta `adb root` →
`setprop service.adb.tcp.port 5555` → `adb unroot`, tai johto ja bootstrap
(`oneplus_wireless_adb.sh bootstrap`). Valtuutus säilyy `kill-server`in yli.

## 3. Sovelluksen intentit

```bash
$A -s $P shell am start -n com.example.silvia_pico_ui/.MainActivity --ez espressopico_open_usb true
$A -s $P shell am start -n com.example.silvia_pico_ui/.MainActivity --ez espressopico_start_bridge true
$A -s $P shell am start -n com.example.silvia_pico_ui/.MainActivity --es espressopico_restore_backup <setti>
```

`start_bridge` avaa USB:n ensin. Silta palvelee **yhtä asiakasta**: koeyhteys, joka sulkeutuu heti
oikean asiakkaan jälkeen, palauttaa vanhan USB-kuuntelijan uuden päälle eikä oikea asiakas saa mitään
(`pico_dev.py:38-41`, havaittu 17.9.2026).

## 4. `pico_dev.py`

```bash
python3 Infra/iot/expresso/pico_dev.py safe                    # releet pois + luenta takaisin, sitten reset
python3 Infra/iot/expresso/pico_dev.py cmd '<komento>' [s]     # CMD-rivi ajossa olevalle firmwarelle, ei keskeytystä
python3 Infra/iot/expresso/pico_dev.py shot <s> [loki]         # tshot ja PI/TS-rivien kaappaus
python3 Infra/iot/expresso/pico_dev.py pcap <ms>[:<bar>[:<phase_us>]] [loki]  # pcap ja PCAP-rivien kaappaus PCAP_ENDiin asti
python3 Infra/iot/expresso/pico_dev.py psweep <ms>:<bar>[:<n>[:<mult>]] [loki]  # psweep ja PSWEEP/PCAP-rivien kaappaus PSWEEP_ENDiin asti
python3 Infra/iot/expresso/pico_dev.py phold <s> [loki]        # phold ja PHOLD-rivien kaappaus PHOLD_ENDiin asti
python3 Infra/iot/expresso/pico_dev.py vkello <bar> [loki]     # verkkokello + taukosarja; nousu päättyy tasanteeseen (VKELLO_RISE), <bar> 0 = vain tasanne; VKELLO-rivit VKELLO_ENDiin asti
python3 Infra/iot/expresso/pico_dev.py vsweep <reps> [loki]  # taukojen vaihepyyhkäisy: purku, nousu tasanteeseen, kellon lukko, 10 ms tauot 0–19 ms kellon reunasta + tyhjä + 20 ms, reps kertaa (TILAUS-K/L); VSWEEP-rivit VSWEEP_ENDiin asti
python3 Infra/iot/expresso/pico_dev.py klamp <s> [loki]       # kuristimen lämmitys: jatkuva pumppu tasanteeseen, tasanteen paine pidetään kunnes pumppua ei rajoiteta (reason=done); KLAMP-rivit KLAMP_ENDiin asti
python3 Infra/iot/expresso/pico_dev.py capture <s> [loki]      # pelkkä kuuntelu
python3 Infra/iot/expresso/pico_dev.py verify <MANIFEST.json>  # SHA-256 Picolta vs. manifesti
python3 Infra/iot/expresso/pico_dev.py watchdog-test           # vahdin todennus (Pico resetoi itsensä ≤ 8 s)
```

`cmd`, `shot` ja `capture` **eivät keskeytä firmwarea** — ne kirjoittavat ja lukevat sarjalinkkiä
ajon aikana. `safe` ja `verify` menevät raakaan REPL:iin: Ctrl-C → `devsafe.enter()` (vaatii
`SAFE_OK`, eli releiden luennan takaisin `[0,0,0]`) → työ → `machine.reset()`
(`pico_dev.py:106-137`).

**RAM-komento `stby:<min>`** (VALMIUSTILA, 5.10.2026; RAM kuten `pim:`, käynnistys ja flash palauttavat
30 min): `stby:<0–240>` asettaa lepoajan minuutteina (0 = valmiustila pois), `stby:on` pakottaa valmiustilan heti
(laitetesti). 30 min ilman kytkintä tai sovelluksen muutosta (`updated`-komento) → IDLE-tavoite
`min(bt, 90)`; STEAM, WATER, BREW ja BACKFLUSH eivät lasku. Mikä tahansa kytkin tai sovelluksen muutos purkaa.
Rivit: `STBY_ON idle_s=<s> target=<t>`, `STBY_OFF reason=switch|app|tshot`, `STBY timeout_min=<m> standby=<0|1> temp=<t>`
(jokaisesta `stby:`-komennosta). Smoke: `testit/valmiustila_smoke.py`.

**RAM-komento `stbt:<°C>`** (6.10.2026, expresso-ios-skoopin poikkeus käyttäjän luvalla): valmiustilan lämpötila
60–95 °C (rajataan, kokonaisluku; oletus ja käynnistys 90). IDLE-tavoite valmiustilassa on `min(bt, stbt)`. Ei aktiivisuutta:
äppi lähettää arvon jokaisen yhteyden jälkeen, eikä uudelleenyhdistys saa herättää valmiustilasta. Rivi
`STBT temp=<t> standby=<0|1> target=<t>` jokaisesta `stbt:`-komennosta. Smoke: `testit/valmiustila_smoke.py`.

`phold` ja `pcap` vaativat toimivan vaa'an ja asetetun `wmax:`- tai `wrise:`-rajan
(EXPRESSO-KAUKALOVAHTI) — ilman kumpaakaan ajo ei ala, eikä se jatka rajan ylittyessä. Syyt
lopetusrivillä: `noscale`, `nolimit`, `scalelost`, `tray`, `trayrise`.

### Debug-kyvyt: Zero vs puhelin (6.10.2026)

| Kyky | Puhelin | Zero | Tila |
|---|---|---|---|
| `cmd`, `capture`, mittauskomennot (`shot`, `hold`, `pcap`, `psweep`, `phold` jne.) | on | sama koodi, ei linkkihaaraa | on |
| `safe` | on | on | on |
| `verify` ja `flash` (SHA-256, manifesti) | `flash` koodissa, käytännössä sovelluksen kautta | `flash` on ensisijainen polku, 6 lokia | on |
| `restore` ja `build_set.py` | on | `restore` kieltäytyy, setti tulee repon `pico/`-hakemistosta | ei tarvita |
| Laturi (Shelly) ja Picon virtakatko | laturin katko enumeroi Picon uudelleen | Pico saa virran Zeron VBUSista, katkaisijaa ei löydy | puuttuu |
| Re-enumeroinnin palautus | sovelluksen pakkopysäytys + uusi forward | ssh-herätys `/dev/hubi0`:lle, ser2netin syy hoitamatta | osin |
| Pysyvä sarjaloki | ei operaatiota, Mac-skriptit eivät ole repossa | ei: ser2net ei lokita dataa | puuttuu |
| Kaatumisen traceback | vaatii asiakkaan paikalla | sama | puuttuu |
| BLE / logcat | käsin adb:llä, logcat vain `restore`ssa | sama käsin-adb, ei operaatiota | osin |
| Tiedostojen luku Picolta | ei operaatiota | ei; mpremote asennettu mutta kytkemättä | puuttuu |
| BOOTSEL / picotool | ei operaatiota | picotool asennettu, ei operaatiota | puuttuu |

Zeron puolen aukot (pysyvä loki, ser2net-mykkyys, virtakatko, asetukset repoon): V-207 → infra zero (f37507e).
Kumpikaan ketju ei lue tiedostoja Picolta eikä tallenna kaatumisen tracebackia; `pico_dev.py log` tehdään, kun V-207:n loki on olemassa.

## 5. Flashaus ei vaadi verkkovirran katkaisua

**Tämä korjaa aiemman säännön.** `KEHITYSYHTEYS.md:175-179` sanoo "keitin aina verkkovirrasta pois
ennen flashia tai lukua", ja perustelu on oikea: Ctrl-C nostaa `KeyboardInterrupt`in, jota firmwaren
`except Exception` ei ota kiinni, joten releet jäisivät viimeiseen tilaansa. **Mutta saman merkinnän
seuraavassa kohdassa (rivi 190) kerrotaan korjauksesta, joka poistaa juuri tuon riskin**, ja
lähdekoodi vahvistaa sen:

`PicoFlasher.flashFiles` (`PicoFlasher.kt:18-26`) ajaa järjestyksessä

1. `interruptToRepl()` — Ctrl-C kahdesti, tyhjä rivi, puskurin tyhjennys (`PicoFlasher.kt:58-72`)
2. `relaysOff()` (`PicoFlasher.kt:78-85`):
   - `[__import__('machine').Pin(n, 1, value=0) for n in (11, 12, 13)]` — pumppu, magneettiventtiili
     ja **lämmitin** suoraan nollaan
   - `import devsafe; devsafe.enter()` — ajaa releet pois, **lukee ne takaisin** ja ruokkii 8 s
     laitteistovahtia

`MainActivity.restoreBackup` käyttää samaa `flashFiles`-polkua (`MainActivity.kt:327-366`), joten
tämä koskee myös palautusta. Sovelluksen vahvistusteksti "Machine unplugged — restore" on siis
vanhentunut muistutus, ei tekninen vaatimus.

**Oikea sääntö: keittimen on oltava joutilas, ei virraton.** Ainoa jäljelle jäävä ikkuna on
`interruptToRepl()`:n omat odotukset — 100 + 250 + 150 + 400 + 100 + 200 ms eli noin **1,2 s** —
jonka ajan releet ovat siinä tilassa, jossa ne olivat keskeytyshetkellä. Joutilaalla koneella ne ovat
jo pois päältä eikä mitään tapahdu. **Jos uutto, huuhtelu tai backflush on kesken, se on
lopetettava ensin**; muuten pumppu ja lämmitin jatkavat nuo 1,2 s.

## 6. Setin rakentaminen puhelimessa

Setti rakennetaan puhelimen yksityiseen tallennukseen vanhan setin viereen, muuttuneet tiedostot
työnnetään, ja manifesti lasketaan puhelimen omasta `sha256sum`-tulosteesta (KEHITYSYHTEYS.md:449-453).
`Infra/iot/expresso/build_set.py` tekee tämän kolmen käsin ajettavan komennon sijaan:

```bash
python3 Infra/iot/expresso/build_set.py --check <uusi>              # esiehdot, ei muuttavia komentoja
python3 Infra/iot/expresso/build_set.py <uusi> [--from <pohja>] [tiedosto...]
```

Ilman `--from` pohja on uusin setti (`ls -1t`). Ilman tiedostolistaa: `pico/*.py`,
`pico/scale_cal.json`, `pico/lib/*.py`. `--check` tarkistaa adb:n tavoitettavuuden, laitteen
`device`-tilan, akun (alle 20 % estää), pohjasetin olemassaolon ja ettei uusi setti ole jo
olemassa; epänolla paluuarvo jos jokin näistä estää ajon. Työkalu tulostaa lopuksi valmiin
palautuskomennon ilman paikanvaraajia — **älä koske sarjalinkkiin ennen `RESTORE_OK`-riviä** (luku 7).

Käsin, varareittinä:

```bash
$A -s $P shell 'run-as com.example.silvia_pico_ui cp -r files/firmware_backup/<vanha> files/firmware_backup/<uusi>'
$A -s $P push <tiedosto> /data/local/tmp/<tiedosto>
$A -s $P shell 'run-as com.example.silvia_pico_ui cp /data/local/tmp/<tiedosto> files/firmware_backup/<uusi>/<tiedosto>'
```

Manifesti on JSON-lista `{"name": "/polku", "size": <tavua>, "sha256": "<tiiviste>"}`; `MANIFEST.json`
itse ei ole listassa, mutta `secrets.py` on. Palautus **tarkistaa jokaisen tiedoston SHA-256:n ennen
kirjoitusta** ja keskeyttää `RESTORE_FAIL sha256 mismatch` jos tiiviste ei täsmää
(`MainActivity.kt:337-351`).

## 7. Palautus ja todennus

**Zero-ketju (oletus):**

```bash
python3 Infra/iot/expresso/pico_dev.py manifest Infra/iot/expresso/pico/MANIFEST.json  # jos pico/ muuttui
python3 Infra/iot/expresso/pico_dev.py flash Infra/iot/expresso/pico/MANIFEST.json     # FLASH_PLAN, WROTE…, VERIFIED n/n, FLASH_OK
```

`flash` tekee saman järjestyksen kuin sovelluksen `PicoFlasher` (luku 5): Ctrl-C, releet pois ja luenta
takaisin (`SAFE_OK`), sitten vain Picolla poikkeavat tiedostot nimellä `<nimi>.new`, kunkin SHA-256 Picolla,
vasta sitten uudelleennimeys, koko manifestin todennus ja `machine.reset()`. Katkos ennen uudelleennimeystä
jättää vanhan firmwaren ehjäksi. Paikalliset tiedostot tarkistetaan manifestia vasten ennen yhteyttä.
Ei mpremotea: se ei ruoki devsafen 8 s vahtia, joten Pico resetoituisi kesken kopioinnin.
`secrets.py`:tä ei ole repossa; se todennetaan Picolta, mutta sitä ei kirjoiteta.

**Puhelinketju (`PICO_LINK=phone`):**

```bash
$A -s $P shell am start -n com.example.silvia_pico_ui/.MainActivity --es espressopico_restore_backup <setti>
$A -s $P logcat -d | grep -E 'RESTORE_|FLASH_'          # odota RESTORE_OK <setti> n=<N>
python3 Infra/iot/expresso/pico_dev.py verify Infra/iot/expresso/pico/MANIFEST.json   # VERIFIED n/n
```

**Älä koske sarjalinkkiin ennen `RESTORE_OK`-riviä.** Kesken palautuksen ajettu `verify` katkaisi
flasherin istunnon kerran (`RESTORE_FAIL … no size ack`, KEHITYSYHTEYS.md:823-827) — silta palvelee
yhtä asiakasta ja Ctrl-C tappoi flasherin.

## 8. Akku ja OTG

**Koskee vain puhelinketjua (`PICO_LINK=phone`).** Zero-ketjussa Pico saa 5 V Zeron VBUS:sta
jatkuvasti, myös keittimen ollessa pois (V-154); laturisykliä, akkurajaa ja `otg_switch`iä ei ole.

OTG-hostina puhelin **syöttää Picolle 5 V eikä lataudu**. Flash estyy alle 20 %:n akulla, ellei
puhelin lataa: `MIN_FLASH_BATTERY_PCT = 20` (`MainActivity.kt:666`), esto näkyy rivinä
`FLASH_BLOCKED battery=<n>%`. Ratkaisu on virrallinen USB-C-hubi; kytkentäjärjestys on osa ohjetta
(KEHITYSYHTEYS.md:443-446 — **koskee vanhaa Genesys Logic -hubia**).

**Uusi hubi (käyttäjä 22.9.2026, saatu toimimaan):** UGREEN Uno USB-C Hub, **8-in-1 -variantti**
(käyttäjä; listauksen mukaan 8-in-1 = 6-in-1:n portit + SD/TF-lukija: PD 100 W sisään, 4K60 HDMI,
10 Gbps USB 3.2 A- ja C-portit),
<https://www.aliexpress.com/item/1005007462882759.html>. Toimiva kytkentä ja järjestys
(laturi → roolinvaihto → HDMI): `Infra/linux/palvelin/README.md`,
luku "Hubi (USB-C, laturi ja HDMI)" (V-149, 7.10.2026). Tila 22.9.2026 08:4x: puhelin `AC powered: true`, mutta
`dumpsys usb` `connected=false`, `power_role=no-power`, `pd_active=0`, `real_type=USB_DCP`;
viimeinen USB-tapahtuma 21.9. 11:04 → Pico ei näy. **Syy löytyi:** `adb root` →
`cat /sys/class/power_supply/usb/otg_switch` = `0` (dmesg: `chip->otg_switch=0`, PD neuvoteltiin
`PD=1`, sitten roolinvaihto → `Type-C disconnect`). OnePlussan *OTG-yhteys*-asetus sammuu itsestään
10 min käyttämättömänä (OxygenOS:n yleinen ominaisuus, ei vielä todennettu tällä puhelimella). Korjaus: Asetukset → Bluetooth ja laiteyhteydet → OTG-yhteys päälle
(ei `settings`-avainta eikä `getprop`-arvoa; sysfs-arvo `otg_switch`). Etänä (todennettu
22.9.2026): `adb root` → `adb shell 'echo 1 > /sys/class/power_supply/usb/otg_switch'` (dmesg
`oplus_set_otg_switch_status: otg_switch=1`). **Pelkkä kytkin ei yhdistä:** Type-C-kytkentä on jo
pudonnut laturitilaan (`USB_DCP`), eikä sitä saa uudelleen neuvoteltua ohjelmallisesti —
`typec_power_role` on vain luku (SELinux, myös rootilla), `dumpsys usb set-port-roles` hylkää
sekä `sink host` että `source host`, `usbpd0/hard_reset` vaatii PD-sopimuksen (`current_pr=none`)
ja `otg_switch` 0→1 ei käynnistä uutta tunnistusta. Tarvitaan yksi fyysinen irrotus ja kiinnitys
(hubin johto puhelimesta) **sen jälkeen**, kun `otg_switch=1`. Puhelimen uudelleenkäynnistys (`adb reboot`) ei auta: `otg_switch` palaa
arvoon 0 käynnistyksessä, ja roolinvaihto 5,8 s:n kohdalla epäonnistuu samoin (dmesg 22.9.2026). Tarkistus:
`adb -s 192.0.2.11:5555 shell dumpsys usb | grep -A4 "status={"` → odotus `connected=true`.

**Irrotus on nyt autonominen: Shelly katkaisee hubin laturin (23.9.2026, todennettu).** Käyttäjä
rakensi älyjatkojohdon hubin PD-laturille; katkaisijana Shelly Plus 1PM
(`AA:BB:CC:DD:EE:FF`, 192.0.2.21 DHCP:llä, IOT_SSID). Liitetty HA:han Bluetooth-löydöllä
(Shelly-integraatio provisioi Wi-Fi:n); entiteetti `switch.shellyplus1pm_example`, teho
`sensor.shellyplus1pm_example_power`. Palvelin ei tavoita laitetta suoraan (VLAN), ohjaus
HA:n kautta: `Infra/iot/ha/ha.sh palvelu switch.turn_on|turn_off
'{"entity_id":"switch.shellyplus1pm_example"}'`. Mitattu, `otg_switch=1`:
- **Laturi päällä** → PD-sopimus (`Type-C Source (high - 3.0A)`), `power_role=sink`, puhelin
  latautuu, mutta USB2-hubi ja Pico irtoavat (`usb 1-1.1: USB disconnect`); vain USB3-hubi jää.
- **Laturi pois** → Pico (`2e8a:0005`) takaisin ~2 s:ssa, `power_role=source`, `data_role=host`,
  puhelin akulla; `pico_dev.py cmd pgap:stop 3` → `CMD_OK pgap:stop`.

Eli kehitysajot tehdään laturi pois, lataus laturi päällä; kumpikaan ei vaadi käyttäjää. Palautus
kadonneesta yhteydestä: `adb root` → `otg_switch=1` → Shelly pois → odota `2e8a` kohteessa
`/sys/bus/usb/devices/*/idVendor`. Akku: 66 % → tyhjenemisnopeus OTG-käytössä mittaamatta;
akkuvahdin kytkentä Shellyyn (lataus ajojen välissä) toteuttamatta.

**VÄLIAIKAINEN: laturi pois USB-operaatioiden ajaksi (käyttäjä 23.9.2026).** `pico_dev.py`
katkaisee laturin jokaisen operaation ajaksi (`ChargerOff`: `otg_switch=1`, Shelly pois, odottaa
`2e8a`:ta ≤ 30 s) ja palauttaa virran lopuksi, myös virheessä. Uudet komennot: `pico_dev.py
restore <setti>` (flash sovelluksen kautta, odottaa `RESTORE_OK/FAIL`/`FLASH_BLOCKED` logcatista,
laturi pois koko ajan) ja `pico_dev.py charger on|off`. Todennettu 23.9.2026: `cmd pgap:stop 3`
→ `CHARGER off` / `CMD_OK pgap:stop` / `CHARGER on`, sen jälkeen puhelin `Charging`, Pico irti.
**Poistetaan käytöstä, kun Type-C-vika on selvitetty ja korjattu:** `CHARGER_CYCLE = False`
(`pico_dev.py`) tai `PICO_CHARGER_CYCLE=0`. Macilla `ha.sh`:lla ei ole tokenia → `CHARGER … FAILED`.

**Latausraja 80 % (käyttäjä 23.9.2026; oli 70 %).** Puhelimessa LineageOS 23.2 (Android 16,
userdebug); rajoitin on LineageHealthin ChargingControl, tila 3 (raja), provider `Toggle`.
Asetus: `adb shell content insert --uri content://lineagesettings/system --bind
name:s:charging_control_charging_limit --bind value:s:80` (`content update` hylkää: "Invalid
setting: null"); tarkistus `adb shell dumpsys lineagehealth` → `Limit: 80`. Käyttäjän hypoteesi:
laturi toimi aiemmin Picon kanssa hubissa, ja 23.9. irtoaminen johtuu alhaisesta akkutasosta
(66 %, raja 70 %) — testaamatta: laturi päälle akun ollessa rajalla ja katso, pysyykö `2e8a`.

Palvelimella on akkuvahti (`oneplus-akkuvahti.sh`, palvelimen cron
10 min), joka ilmoittaa varoitus- ja kriittisen rajan alituksesta; rajat luetaan HA:n
input_numbereista (oletus 30/15).

## 9. Ansat

| Oire | Syy ja korjaus |
|---|---|
| `Timeout` 90 s eikä `FLASH_OK` | Ei epäonnistuminen: iso paketti kestää ~2 min. Katso myöhempi `FLASH_OK` logcatista (R3) |
| Silta ei vastaa flashin jälkeen | Korjattu: `resumeIo` aina `finally`-haarassa (`PicoFlasher.kt:45-51`); vanhassa buildissa USB-lukija jäi tauolle |
| `RESTORE_OK` katosi logcatista | Puskuri 256 KiB täyttyi BLE-telemetriasta; nostettu (KEHITYSYHTEYS.md:228) |
| `controlTransfer failed` heti alussa | USB ei ole asettunut — odota ja yritä uudelleen, ei pysyvä vika |
| Portti 2217 kiinni | `start_bridge`-intentti, USB auki ensin (R5) |
| BLE ei yhdisty näytön ollessa pois | Android estää suodattamattoman haun; herätä näyttö (`input keyevent KEYCODE_WAKEUP`) |
| Kaappaus päällä flashin aikana | Avoin sarjayhteys voi jumittaa USB-flashin — pysäytä kaappaus ensin (R3) |

## 10. Lokitunnisteet

`PicoFlash` (flash ja palautus), `PicoFlasher`, `PicoUsb`, `PicoBridge`. Picon oma sarjatuloste:
`PI`/`TS`-rivit uuton aikana, `TS_START`/`TS_END`, `PCAL_START`/`PCAL_SETTLED`/`PCAL_END`/`PCAL_ABORT`,
`PZERO_OK`/`PZERO_ABORT`, `CMD_OK`, `PCAP_START`/`PCAP`/`PCAP_END`,
`PHOLD_START`/`PHOLD`/`PHOLD_END`.
