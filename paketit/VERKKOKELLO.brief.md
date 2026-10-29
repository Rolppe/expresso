# VERKKOKELLO — sisäinen verkkojaksokello firmwareen (vaihe 1a3)

VAATIMUS: TILAUS-A, TILAUS-B, TILAUS-F, TILAUS-G, TILAUS-I, TILAUS-J

Tila 23.9.2026: **luovutettavissa.** Suunnitelma `paketit/VERKKOKELLO.md`, simulaatio
`testit/verkkokello_sim.py` (`RESULT: 0 failed`), holdout `testit/verkkokello_holdout.py`. Holdout
on todennettu suunnittelijan viitetoteutuksella (12/12 PASS), joka ei ole repossa.

## Päätökset (käyttäjä 23.9.2026)

1. **Lukkoraja `LOCK_US` = 1000 us.** Suunnitelman ¼ vaiheaskelta (208 us) ei ole saavutettavissa
   mitatulla kohinalla: simulaatiossa lupa 0 % käyntiajasta. 1000 us:lla lupa on 85 %
   käyntiajasta ja väärä lupa 0,16 %. Arvo tarkistetaan, kun SSR-40DA:n tyyppi on selvillä
   (REKISTERI, rivi "SSR-40DA:n tyyppi").
2. **Jakson rajan 19 950–20 050 us osuma on tapahtuma `VKELLO_TRAJA`, ei vika.** Raja pitää arvion
   alueella, ja ulospäin työntävä muutos d nollataan. Vika se on vain vakiotaajuudella alueen
   sisällä, ja simulaatio tarkistaa sen.

## Menetelmä ja miksi (simulaatio 23.9.2026)

VAATIMUS: TILAUS-B, TILAUS-I, TILAUS-J

- **Kohina on mitattu, ei oletettu.** Paineväreilyn vaihetta luettiin jaksoittain I/Q-menetelmällä
  vanhoista täyden pumpun kaappauksista (`pcap-20260919-8bar`, `-tasanne`, `-verkkotaajuus`).
  Yhden jakson hajonta oli 571–1441 us, 8 jakson ikkunan 295–616 us ja 32 jakson 98–402 us.
  Nousevassa paineessa (tasanne) peräkkäisten jaksojen korrelaatio oli 0,65. Yliaallot eivät
  auta: kun ne yhdistettiin mukaan, hajonta kasvoi kaikissa kolmessa kaappauksessa (8bar 263 → 331 us),
  joten vaihe luetaan pelkästä perusaallosta.
- **Suunnitelman PI-silmukka hylätään.** Sen lukkosääntö (|e| < 400 us kolmessa ikkunassa) ei
  erota lukkoa kohinasta, koska yhden ikkunan kohina on itse noin 400 us. Se antoi luvan vain
  14–25 %:lle käyntiajasta, ja 10 s:n tauon jälkeen käynnistysvirhe oli p95 2,1–9,3 ms.
- **Valittu: kolmitilainen Kalman-suodin**, jonka tilat ovat vaihe, jakso T ja jakson muutos d.
  Sama kaava hoitaa alkulukituksen 50 Hz:stä (TILAUS-F), kapean seurannan ja paluun tauon
  jälkeen. Lupa ohitukseen annetaan kellon oman vaihe-epävarmuuden perusteella (2,5·sd < `LOCK_US`),
  ja epävarmuus ennustetaan kysymyshetkeen, myös tauon ajalle (TILAUS-J). Tila d on mukana, koska
  pelkällä vaiheella ja jaksolla (kaksitilainen suodin) väärä lupa oli 5 mHz/s:n rampissa 56–78 % (lukkoraja 500 us).
- **Tulokset, N = 8, `LOCK_US` = 1000 us, 20 ajoa per rivi.** Mitatulla kohinalla väärä lupa oli
  0 % kaikilla profiileilla paitsi 20 mHz/s:n rampissa (0,66 %). Lukittu virhe oli p50 120–133 us
  ja p99 448–900 us. Lukko palasi 0,48 s:ssa jokaisen tauon jälkeen. Käynnistysvirhe (p95) tauon
  pituuden mukaan: 0,5 s → 0,5–0,7 ms, 2 s → 0,6–1,1 ms, 5 s → 1,0–1,3 ms (8,7 ms 20 mHz/s:n
  rampissa) ja 10 s → 2,8–5,2 ms.
- **Huonoin kohina** (korreloitu vaellus 400 us, τ = 1 s, kuten nousevassa paineessa) jättää
  väärien lupien pohjaksi 1,3–1,8 % (4,6 % 20 mHz/s:n rampissa). Suodin ei erota vaellusta
  verkosta, koska vaellus on paineväreilyssä itsessään. Pohjan suuruus mitataan laitteella
  (luku Acceptance, laitetesti).
- **Kehys.** Kellon reuna on pumpun sähköjakson alku: painevärähtelyn perusaallosta luettu vaihe
  miinus `LAG_US` = 39 000 us (TILAUS-I, 37–41 ms). Viiveen epävarmuus ±2 ms siirtää koko kehystä
  vakiolla. Se ei vaikuta seurantaan eikä tauon yli pitoon, mutta kaikki ohitusvaiheet ilmaistaan
  tässä kehyksessä, eikä kehyksen ulkopuolelta tuotua vaihetta verrata siihen suoraan.

## Task
Uusi moduuli `pico/verkkokello.py`, joka on `verkkokello_sim.py`:n `KF3Clock` MicroPythonina
ja jossa on lisäksi I/Q-mittaus. Mukaan testikomento `vkello:<bar>`, joka ajaa pumppua ja
simulaation taukosarjaa laitteella ja tulostaa kellon tilan. Olemassa olevia ajoja
(pgap, psweep, pstep, mcal) **ei** vielä siirretä kellolle, koska se on seuraava paketti.

## Files
may:
- `Infra/iot/expresso/pico/verkkokello.py` (uusi), `pico/functions.py`, `pico/commands.py`,
  `pico/classes.py`
- `Infra/iot/expresso/pico_dev.py`, `Infra/iot/expresso/PICO-HALLINTA.md`

must not:
- `Infra/iot/expresso/testit/` kokonaan — simulaatio ja holdout ovat suunnittelijan mittoja
- `Infra/iot/expresso/pico/main.py`, `pico/MANIFEST.json` (build_set.py tekee sen flashissa),
  `paketit/` kokonaan
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/testit/verkkokello_sim.py` kokonaan: `KF3Clock` on toteutuksen määrittely
- `Infra/iot/expresso/testit/verkkokello_holdout.py` kokonaan — se on hyväksynnän mitta
- `Infra/iot/expresso/paketit/VERKKOKELLO.md` kokonaan
- `pico/functions.py` rivit 529-570 (vakiot, `pcap_gate`) ja 1154-1287 (`pressure_gap_run`:
  ajastus, vahdit ja purku, joita `vkello` käyttää samoin)
- `pico/commands.py` rivit 124-153 ja `pico_dev.py` rivit 288-300: komennon ja kaappauksen malli

## Do
1. `pico/verkkokello.py`, moduulitason vakiot `N_WIN=8`, `SIGMA1=1450`, `SIGMAW=500`,
   `Q_D=0.001`, `D0=0.04`, `T_START=20000`, `T_MIN=19950`, `T_MAX=20050`, `LAG_US=39000`,
   `LOCK_US=1000` ja `AMP_MIN=0.1` (bar). Moduuli tuo `utime`:n (`import utime`), ja kaikki
   aikaerot lasketaan `utime.ticks_diff`/`ticks_add`-funktioilla, koska ticks kiertää 2^30:ssä.
   Luokka `Verkkokello(t0_us)`, jonka rajapinta holdout kutsuu:
   - `edge(t)` → lähin ennustettu jakson alku ticks-arvona; `update(t_mid, z_us)`; `sd_us(t)`;
     `locked(t)`; attribuutit `T`, `d` ja `traja` (rajaosumien määrä). `update`, kovarianssin
     kasvu, `sd_us`, `locked` ja rajasääntö ovat numeerisesti samat kuin `KF3Clock`:ssa.
   - **RP2040:n MicroPython-float on 32-bittinen.** Absoluuttinen ticks-arvo (enintään 2^30) ei
     mahdu siihen mikrosekunnin tarkkuudella. Siksi vaiheen viite pidetään kokonaislukuna
     (ticks) ja erillisenä desimaaliosana, ja liukulukuun muunnetaan vain erotuksia.
2. I/Q-mittaus: `iq_start(t)`, `iq_add(t, x)`, `iq_ready(t)` (N_WIN·T kulunut), `iq_close(t)`
   → `(z_us, amp)` tai `None`, ja `iq_abort()`. `iq_add` kerää näytteen kellon
   referenssivaiheella θ = 2π·((t − t_ref) mod T)/T. Cos/sin luetaan 256 alkion taulukosta
   pyöristetyllä indeksillä, eikä 1 kHz:n silmukassa kutsuta `cos`:ia eikä `sin`:iä. `iq_close`
   poistaa keskiarvon (DC ei saa vuotaa vaiheeseen), laskee amp = 2·|I,Q|/n ja vaiheen, muuttaa
   sen ajaksi ja vähentää `LAG_US`:n (kehys: paine c + A·cos(2π(t − e − LAG_US)/T) antaa reunan
   e). Lopuksi se kutsuu `update(t_mid, z)`:tä, jos amp ≥ `AMP_MIN`. Kutsuja hylkää ikkunan
   `iq_abort`illa, jos pumppu ei käynyt koko ikkunaa.
3. `functions.py`: `pressure_clock_run(brew_data, utime, asyncio, target)`. Rakenne on sama kuin
   `pressure_gap_run`:ssa: kaukalovahti, ylipaine, `PGAP_RUN_MAX_MS`, `devsafe.feed` ja
   `finally`-purku. Pumppu käy täysillä ensin `target`-paineeseen ja sitten simulaation
   taukosarjan 0,5 / 1 / 2 / 5 s, jokaisen jälkeen 4 s käyntiä. Tauolla pumppu on pois, eikä
   solenoidia avata tauon ajaksi. Rivit:
   `VKELLO w=<n> t_ms=<ms> z_us=<z> T_us=<T> d=<d> sd_us=<sd> amp=<bar> lock=<0|1>` jokaisesta
   ikkunasta, `VKELLO_RESTART pause_ms=<ms> z1_us=<ensimmäisen ikkunan z>` jokaisen tauon
   jälkeen, `VKELLO_TRAJA` rajaosumasta ja lopuksi
   `VKELLO_END T_us=<T> hz=<f> windows=<n> reason=<...>`.
4. `commands.py` ja `classes.py`: `vkello:<bar>` ja `vkello:stop` samalla mallilla kuin `pgap`.
5. `pico_dev.py` ja `PICO-HALLINTA.md`: `pico_dev.py vkello <bar> [loki]` kaappaa `VKELLO`-rivit
   `VKELLO_END`:iin asti.
6. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico/verkkokello.py pico/functions.py pico/commands.py pico/classes.py pico_dev.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/verkkokello_holdout.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 300 python3 testit/verkkokello_sim.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 180 python3 testit/tray_guard_smoke.py
```
```bash
cd /srv/work/Infra/iot/expresso && timeout 180 python3 testit/pskip_gate_smoke.py
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "pico/(verkkokello|functions|commands|classes)\.py$|pico_dev\.py$|PICO-HALLINTA\.md$" | wc -l | grep -qx 0
```

Laitetesti (suunnittelija ajaa käyttäjän luvalla, TYÖTAVAT 8, flash yksi kerrallaan, TYÖTAVAT 6):
`pico_dev.py vkello 7 testit/vkello-<pvm>-a.log` kolmesti. Tuloksesta luetaan: `z_us`:n hajonta
lukittuna (vertaa simulaation 295–616 us:iin per ikkuna), `VKELLO_RESTART z1_us` tauon mukaan
(vertaa simulaation käynnistysvirheeseen) ja `VKELLO_END hz`, joka kirjataan aikaleimoineen
verkon muutosnopeuden aineistoksi (VERKKOKELLO.md, "Mitä ei tiedetä").

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/verkkokello.py pico/functions.py pico/commands.py pico/classes.py pico_dev.py PICO-HALLINTA.md | wc -l) -le 4520
```
Mitattu `wc -l`, commit `ea2691a`: 0+1819+349+1441+438+223 = 4270. Varaa on 250 riviä, josta
kellomoduulille arviolta 140.

## Stop
- Holdout vaatii jotain, mikä on ristiriidassa `KF3Clock`:n kanssa: kerro kohta ja lopeta vuorosi.
  Älä muuta holdoutia äläkä simulaatiota.
- 1 kHz:n silmukka ei ehdi I/Q-päivitystä: kerro mitattu silmukka-aika ja lopeta vuorosi.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** ei adb:tä, ei flashausta.

## Report
```text
brief: VERKKOKELLO
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
```
