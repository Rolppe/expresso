# eXpresso — virtausohjaus, virtausmittaus, tshot ja firmware-palautus

Read `Infra/iot/expresso/KEHITYSYHTEYS.md` and `Infra/iot/expresso/pico_dev.py` in full, plus the
eXpresso rows of `Infra/paarekisteri.md`. No device source tree exists in this repo or on this
host; the actual firmware source (`classes.py`, `functions.py`, `commands.py`, `scale.py`,
`bluetooth_handler.py`, `devsafe.py`, `main.py`) lives only on the Mac
(`~/.../eXpresso_Grok/legacy/latest/pico/` and per-set folders such as
`legacy/pico-devsafe14-20260918/`) and on the Pico itself; not read directly here, only via the
log's descriptions and quoted code fragments.

## Pumppu: duty, ei kiinteä PID-kirjasto

- Ohjain on `classes.PumpPressureController`, oma pienoismalli, ei ulkoinen PID-kirjasto.
  `KEHITYSYHTEYS.md:346`: `duty = 0,5 + 0,2·e + 0,3·∫e` tilassa `mode='pi'` (anti-windup,
  integraali rajattu ±1,5); `mode='bang'` (on/off, hystereesi ±0,15 bar) jäi varalle
  (`KEHITYSYHTEYS.md:311,347`).
- Duty ajetaan aikasuhteisena on/off-ikkunana: 100 ms ikkuna, 20 ms askel, vähintään 20 ms
  kytkentäväli SSR:n yhden 50 Hz-jakson takia (`KEHITYSYHTEYS.md:312,347`).
- `max_duty`-katto ja `continuous_error`-parametri (oletus 1,0 bar, pitää releen yhtäjaksoisesti
  päällä kun virhe ylittää sen) lisättiin setissä `20260918-devsafe7`
  (`KEHITYSYHTEYS.md:501-508`); esiuuton kova duty-katto korvattiin 2,0 bar/s tavoiteramppilla
  (`KEHITYSYHTEYS.md:507`).
- Pumppumalli, jota vasten säädin on sovitettu: `dp/dt = 6,7·pumppu − 1,24·p`, viive ~70 ms
  (`KEHITYSYHTEYS.md:491,882`). `functions.run_shot` ajaa esiuuton, PI-uuton, soft releasen ja
  magneettiventtiilin samalla koodipolulla kytkimelle ja testiuutolle (`KEHITYSYHTEYS.md:372`).
- Uusin mitattu duty-työpiste (kuristusventtiilin säädössä, tavoite 8,0 bar): duty 0,20–0,61
  riippuen kuristuksesta (`KEHITYSYHTEYS.md:838-865`).

## Paineanturi: lukutaajuus ja yksikkö

- `PressureSensor.get_pressure` keskiarvoistaa näytteitä ikkunassa; oikea arvo on **16 667 µs
  eli 60 Hz** (50 Hz -oletus 20 ms oli mitattu virheeksi, palautettu setissä `devsafe5`,
  `KEHITYSYHTEYS.md:313,412-413`). Yksikkö on bar kaikkialla (`pip:<bar>`, `bp:<bar>`,
  `KEHITYSYHTEYS.md:209-211`).
- `adafruit_max31865.read_rtd` (lämpötila, ei paine) esti ≥75 ms per kutsu — paineensäädön
  viiveen juurisyy 17.9.2026, korjattu lukemalla lämpötila vain 2 s välein
  (`KEHITYSYHTEYS.md:304-314`).

## Virtaus: laskettu vaa'asta, ei erillinen virtausanturi

- Laitteessa **ei ole omaa virtausanturia**: "virtaus" on laskettu vaa'an (HX711-kennopari)
  painonäytteistä `scale.py`-moduulin `flow(span_ms)`-funktiolla (`KEHITYSYHTEYS.md:774-776`) —
  ks. Contradictions.
- Mitattu näytteistys: HX711-pari **86,2 ms välein eli 11,6 näytettä/s**, yksittäisnäytteen
  hajonta 0,22–0,26 g, kohina valkoista (`KEHITYSYHTEYS.md:747-749`).
- Valittu estimaattori: mediaani-3-suodatus + pienimmän neliösumman suora 1,0 s ikkunassa,
  vertailtiin viittä ehdokasta `flow_sim.py`:llä (`KEHITYSYHTEYS.md:757-764,775`). Yksikkö g/s.
  Ikkuna säädettävissä komennolla `fwin:<ms>` (200–3000 ms), ei tallennu asetuksiin
  (`KEHITYSYHTEYS.md:780-781`).
- Vanhentumisvahti: yli 500 ms vanhoista näytteistä palautuu `None`, ei virtausarvo
  (`KEHITYSYHTEYS.md:778-779`).
- Laitteella todennettu harha ≤0,1 g/s viidessä regiimissä 0,3–10,4 g/s, tehollinen viive 0,30 s
  (`KEHITYSYHTEYS.md:806-809,841,851,871-872`). BLE:ssä virtaus kulkee omassa ~35 B paketissa
  (`{"flow":…, "weight":…}`), koska live-paketti oli jo 250 B ilman sitä
  (`KEHITYSYHTEYS.md:782-787`).
- Kuristusventtiilin nykyinen mitattu tila (18.9.2026, viides todennus): virtaus 0,79 g/s, duty
  0,20 — liian tiukka, tavoite 2,2–2,5 g/s (`KEHITYSYHTEYS.md:863-865`); tämä on
  `paarekisteri.md:7`:n `SEURAAVA PAKETTI EXPRESSO-VIRTAUSSAATO`-rivin lähtötila.

## `tshot` — mitä komento ajaa

- `commands.py` käsittelijä ottaa BLE:ltä tai sarjalta komennon `tshot:<5–60 s>` (ja
  `tshot:stop`) (`KEHITYSYHTEYS.md:370`), ajaa `functions.run_shot`-polun (esiuutto → PI-uutto →
  soft release → magneettiventtiili), sama koodi kuin fyysinen kytkin, mutta
  `limit_weight=True` vain `tshot`-polulla (`KEHITYSYHTEYS.md:372,579,615,691`).
- Katkeaa: kytkimeen, `tshot:stop`/`dev:safe`, aikarajaan, paineeseen >13 bar, tai (vaaka+rajat
  asetettu) kahteen peräkkäiseen `wmax`/`wrise`-ylitykseen; `finally` sammuttaa pumpun,
  lämmittimen ja venttiilin (`KEHITYSYHTEYS.md:373-375,405,615`).
- `pico_dev.py shot(seconds, out_path)` lähettää `CMD tshot:<seconds>\r\n` samalla yhteydellä
  jolla se kaappaa vastauksen (`pico_dev.py:169-174`; erillinen uudelleenyhteys hukkasi kerran
  ensimmäiset 24 s, kommentti samalla rivillä).

## Loki: rivimuoto ja kohde

- Sarjalokirivit uuton aikana: `PI …` (esiuutto) ja
  `TS <ms> <paine> <tavoite> <pumppu> <duty>` 100 ms:n välein, päättyen
  `TS_END loops=… max_loop_ms=… reason=…` (`KEHITYSYHTEYS.md:375`). Setistä `devsafe14` alkaen
  rivit päättyvät kenttiin `w=<g> f=<g/s>` (`-` jos vaakaa ei ole, `KEHITYSYHTEYS.md:788`);
  `TS_START`-rivi kertoo painorajojen tilan kentässä `limits=` (`KEHITYSYHTEYS.md:700`).
- Loki tulee USB-sarjaan; `pico_dev.py shot`/`capture` kirjoittavat sen annettuun
  `out_path`-tiedostoon binäärisenä append-kirjoituksena (`pico_dev.py:146-166`,
  `open(out_path, 'ab')`); ilman `out_path`-argumenttia tuloste menee vain stdoutiin. Arkistoidut
  ajolokit ovat Macilla, esim. `legacy/pico-devsafe14-20260918-testit/…`
  (`KEHITYSYHTEYS.md:464,833`) — ei tässä repossa.
- Rinnakkainen BLE-telemetria (10 Hz keittoloki, `KEHITYSYHTEYS.md:10,797,869`) kulkee
  sovelluksen kautta; sitä analysoivat Macin `analyze_run.py`/`analyze_shot.py`
  (`KEHITYSYHTEYS.md:69`).

## Firmwaren päivitys ja palautus (SHA-256)

- Flash normaalisti: `./tools/flash_via_phone.sh` (Macilla) kirjoittaa nimetyn tiedostojoukon,
  sovellus laskee koon (`uos.stat()`), logcat `FLASH_OK`/`FLASH_FAIL` (`KEHITYSYHTEYS.md:63,47`).
- Täysi palautus: sovelluksen *Restore backup* / adb-intentti
  `--es espressopico_restore_backup <setti>`; `MainActivity.restoreBackup` kirjoittaa kansion
  kaikki tiedostot paitsi `MANIFEST.json`; jos manifesti löytyy, **jokaisen tiedoston SHA-256
  tarkistetaan ennen kirjoitusta**; logcat `RESTORE_START`, `RESTORE_OK <nimi> n=<N>` /
  `RESTORE_FAIL …` (`KEHITYSYHTEYS.md:187-189`).
- Riippumaton todennus laitteelta: `pico_dev.py verify <MANIFEST.json>` laskee jokaisen
  tiedoston SHA-256 Picolla `uhashlib`:llä ja vertaa manifestiin, tulostaa
  `VERIFIED <ok>/<n>` (`pico_dev.py:177-194`); ennen sitä `enter_devsafe()` vaatii `SAFE_OK`
  (releet luettu takaisin `[0,0,0]`, `pico_dev.py:106-121`).
- Sääntö: **odota `RESTORE_OK` logcatista ennen kuin kosket sarjalinkkiin** — kesken ajettu
  `verify` katkaisi flasherin istunnon kerran (`RESTORE_FAIL … no size ack`,
  `KEHITYSYHTEYS.md:823-827`).

## Laitteistovahti (watchdog) ja sen rajoitus ajolle

- `devsafe.py`: `start_watchdog()` käynnistää **8 sekunnin laitteistovahdin**, `feed()` ruokkii
  sitä (`KEHITYSYHTEYS.md:364`). `pico_dev.exec()` ruokkii vahtia jokaisen suoritettavan
  koodilohkon alussa (`pico_dev.py:123-125`); sovelluksen `PicoFlasher` ruokkii 20
  kirjoitusrivin välein (`KEHITYSYHTEYS.md:379`); firmwaren `watchdog_feeder`-taski 1 s välein
  (`KEHITYSYHTEYS.md:367`).
- Ruokinnan loppuminen resetoi Picon itsestään ≤8 s:ssa; todennettu `watchdog-test`-komennolla
  (`pico_dev.py:203-220`, `KEHITYSYHTEYS.md:395-396`, `WATCHDOG_TEST PASS`).
- Tämä rajoittaa ajoa: jokainen `pico_dev.py`-operaatio on ketju Ctrl-C → `devsafe.enter()`
  (vaatii `SAFE_OK`) → työ (ruokinta joka osassa) → `machine.reset()`
  (`KEHITYSYHTEYS.md:382-383`, `pico_dev.py:106-137`).
- Ctrl-C (`KeyboardInterrupt`) ei laukaise firmwaren `except Exception`-relekatkaisua — releet
  voivat jäädä päälle keskeytyksestä; siksi keitin pidetään irti verkkovirrasta flashauksen tai
  luvun ajan (`KEHITYSYHTEYS.md:175-179`).

## Contradictions with the plan

- Aihe olettaa erillisen "virtausanturin" ("miten virtausanturi luetaan"). Lähteiden mukaan
  laitteessa ei ole erillistä virtausanturia: virtaus on laskettu jälkikäteen vaa'an
  (kuormituskenno-HX711) painonäytteistä `scale.py`:n `flow()`-funktiolla, ei mitattu suoraan
  (`KEHITYSYHTEYS.md:774-776,747-749`).

## Unverified

- Pumppumallin ja PI-säätimen kaavat on luettu vain `KEHITYSYHTEYS.md`:n kuvauksesta; itse
  `classes.py`/`ctrl_real_test.py`-koodia ei luettu, koska se on vain Macilla. Vastaavasti
  `scale.py`:n `flow()`-toteutusta, `commands.py`:n täyttä komentolistaa ja
  `functions.run_shot`:n täyttä logiikkaa ei ole luettu suoraan — vain lokin tekstikuvaukset.
- Loki-tiedoston tarkkaa polkua/nimeä Picon tai puhelimen tallennuksessa ei ole vahvistettu;
  `KEHITYSYHTEYS.md` mainitsee vain USB-sarjan kaapatuksi kohteeksi.
- `pico_dev.py`:n kommentti sanoo tiedoston olevan kopio Macin `legacy/pico_dev.py`:stä
  (`KEHITYSYHTEYS.md:380`) — kahden kopion ajantasaisuutta ei ole verrattu tässä ajossa.

## Lue lisää

- eXpresso-virtausohjaus → `Infra/iot/expresso/KEHITYSYHTEYS.md` → `wc -l` 915
- eXpresso-virtausohjaus → `Infra/iot/expresso/pico_dev.py` → `wc -l` 240
- eXpresso-virtausohjaus, paarekisteri-rivit → `Infra/paarekisteri.md:7` → `wc -l` 1028
- eXpresso-virtausohjaus, vikarekisteri-rivit → `Infra/paarekisteri.md:631-642` → `wc -l` 1028
- eXpresso-virtausohjaus, tilarivi 18.9.2026 → `Infra/paarekisteri.md:950` → `wc -l` 1028
- Firmware-lähdekoodi (ei tässä repossa) → `~/.../eXpresso_Grok/legacy/latest/pico/` → 16
