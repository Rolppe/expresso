# eXpresso — pumpun ohjaus, paine, vaaka ja höyry: konteksti verkkotaajuus-PWM:lle

Read `KEHITYSYHTEYS.md`, `PICO-HALLINTA.md`, `konteksti-virtaussaato.md`, `pico/main.py`,
`pico/functions.py`, `pico/classes.py`, `pico/commands.py`, `pico/preset.py`, `pico/scale.py`,
`pico/api_functions.py`, `pico/MANIFEST.json`, `paketit/VIRTAUSSAATO-2.md`, `.spec.md`,
`.correction-1..6.md`, `PAINESAADIN-HEILUNTA.md`, `PCAL-KORJAUS.md`, `testit/dead_time.py`,
`testit/flow_rate_probe.py`, `testit/real_plant_sim.py`, `testit/pi_sim.py`,
`testit/preinf_sim.py`, and the eXpresso rows of `Infra/paarekisteri.md` (7, 631-642, 950), all in
full, directly with the Read tool.

## 1. Pumpun ohjaus — laitteisto ja koodipolku

Rele on digitaalinen GPIO-ulostulo `Pin(PINS['RELAY_PUMP'])`, pinni **GP11** (`pico/preset.py:40-42`,
GP12 magneettiventtiili, GP13 lämmitin). Lähdekoodissa ei ole triac-/SSR-ajuripiirin mainintaa eikä
nollaylityksen (zero-cross) tunnistusta — grep `zero` koko `pico/*.py`:hen ei löydä toteutusta.
Ainoa "SSR"-maininta on kommentti `KEHITYSYHTEYS.md:317`, ei koodin laitteistofakta.

Ohjain on `classes.PumpPressureController` (`pico/classes.py:685-816`), ei ulkoinen PID-kirjasto.
Oletustila `mode='pi'`: `duty = ff + kp*error + ki*integral`, rajattu `[0, max_duty]`
(`classes.py:772-784`). Duty ajetaan **aikasuhteisena on/off-ikkunana**: `window_ms=100`,
`step_ms=17` ("yksi 60 Hz verkkojakso eli yksi pumpun isku", `classes.py:697-700,789`),
`min_switch_ms=17` (`classes.py:697,736`). Sovellettava päällä-aika: `int(duty*window_ms/step_ms +
0.5)*step_ms` (`classes.py:789,808`) — aikaresoluutio on **17 ms** askelin 100 ms:n ikkunassa, ei
vaihekulman/faasileikkauksen ohjausta eikä syklinohitusta verkkojakson sisällä. `continuous_error=
1.0` bar pitää releen yhtäjaksoisesti päällä suurella virheellä tai kun paine < puolet tavoitteesta
(`classes.py:713-718,762-771`). `apply_duty()` (`classes.py:793-810`) ajaa saman ikkunan ilman
PI:tä, kun ulompi `FlowController` (VIRTAUSSAATO-2) antaa dutyn suoraan (`functions.py:233-243`).
Sovitettu pumppumalli: `dp/dt = 6,7·pumppu − 1,24·paine`, viive ~70 ms
(`testit/real_plant_sim.py:8,15`, `testit/preinf_sim.py:5`).

## 2. Paineanturi — luku, näytteenotto, suodatus, kalibrointi

`classes.PressureSensor` (`classes.py:900-1011`) lukee `ADC(Pin(PINS['PRESSURE_ADC']))`, pinni
**GP28** (`preset.py:51`). `get_pressure()` (`classes.py:981-1011`) on estävä, 16 667 µs:n (60 Hz)
ikkuna; `sample_average()` (`classes.py:925-948`) ei-estävä, säätösilmukoiden käyttämä — 8 näytteen
purske/kierros, liukuva puskuri `WINDOW_US=16667` (`classes.py:923`). Muunnos:
`raw_bar=adc_avg*0.000314936-3.522929`, `bar=gain*raw_bar+offset` (`classes.py:930,948`).
Kalibrointi `pressure_cal.json`:iin (`classes.py:916,957-978`), hyväksytty `gain 0,5-1,5`,
`offset -3..3` (`classes.py:955`). Suora kirjoitus `pcalset:<gain>:<offset>` (`commands.py:62-80`);
`pzero:` ottaa nollan purkamalla venttiiliä (`commands.py:82-85`, `functions.py:480-526`). Voimassa
19.9.2026: `gain=1,0000 offset=-0,990` (`paarekisteri.md:950`).

## 3. Virtaus — laskettu vaa'asta, `fmode`/`fset`

Erillistä virtausanturia ei ole: virtaus lasketaan vaa'an HX711-näytteistä `scale.py`:n `flow()`-
funktiolla (`scale.py:222-252`), PNS-suora mediaani-3-siivotulle sarjalle `flow_window_ms` (oletus
1000 ms, `scale.py:12,50`) yli; `None` alle 4 pisteellä tai yli 500 ms vanhalla näytteellä
(`scale.py:16-18,232,247`). Ulompi kaskadi `classes.FlowController` (`classes.py:822-893`) antaa
**dutyn suoraan**, paine vain kattona `duty_cap=(p_max-paine)/p_margin` (`classes.py:873-875`,
`VIRTAUSSAATO-2.md:36-40`). `fmode:on|off`/`fset:<0,5-5,0>` (`commands.py:163-180`) eivät tallennu
— laite on aina paineohjauksessa käynnistyksen jälkeen (`classes.py:145-148`). Korjaukset 1-6
tarkensivat mittaria: vakio-kuristus regressioajolle (K1), 1,0 s liukuva keskiarvo hetkellisen
sijaan (K2), asettumisaika `2/k_hitain+1,0 s=5,0 s` (K4), toleranssi 0,3 g/s ja `p_margin` 1,0→3,0
(K5-K6), `fsat` suodatetuksi virheeksi `e_avg` (K8, `classes.py:876-893`).

## 4. Vaaka ja preinfuusio

`scale.py` ajaa kaksi HX711-kennoa bittikohtaisesti (DT GP18/GP20, SCK GP19, `scale.py:23,52-54`),
näytetaajuus **11,6 Hz** (86,2 ms), kohinan sd 0,22-0,26 g, valkoista (`KEHITYSYHTEYS.md:747-749`).
`scale_reader`-taski päivittää `brew_data.weight`ä 20 ms välein (`main.py:296-315`). Preinfuusio
(`functions.py:7-110`) avaa venttiilin, odottaa paineen laskevan, ajaa rampitetun nousun
(`RAMP_BAR_PER_S=2,0`, `functions.py:52,78`); pito alkaa rampin saavutettua tavoitteen, kesto
`pit:`-liukusäätimestä (`functions.py:85`). Testiuuttojen rajat `wmax:<g>`/`wrise:<g>`, kaksi
peräkkäistä ylinäytettä ja 2 s vanhentumisvahti (`functions.py:139-182`, `commands.py:146-190`).

## 5. Höyryn (kattilan) lämpötilaohjaus

`classes.Thermostat.run()` (`classes.py:1073-1122`) ohjaa `RELAY_HEATER`-relettä (GP13) hystereesillä
(`heat_cycler`, `classes.py:1125-1148`). Asetusarvo `BrewData.get_target_temperature()`:sta
(`classes.py:331-351`): `STEAM` 125 °C oletus (`classes.py:113`), muut `brew_temperature` 97 °C
(`classes.py:112`) tai backflush-vaiheiden kiinteät arvot (`preset.py:68-79`, tehtaan STEAM 137 °C).
Uutossa lämpötila luetaan vain 2 s välein, koska `MAX31865.read_rtd` estää ≥75 ms
(`functions.py:225-227`).

## 6. Turvarajat ja lukitukset

Paine 13,0 bar katkaisee vain pumpun ollessa päällä (`functions.py:149-151`); kalibrointivelhon oma
raja 12,0 bar (`functions.py:386-388`). `max_duty`-katto per ohjaininstanssi, esiuutossa ramppi
korvaa katon (`functions.py:55`). Watchdog 8 s `devsafe.py`:ssä, ruokitaan 1 s välein
(`main.py:318-322`) ja jokaisessa `pico_dev.py`-operaatiossa (`PICO-HALLINTA.md:52-63`).
`run_shot`:n `finally` sammuttaa kaikki releet poikkeuksesta riippumatta (`functions.py:292-296`).
`main.py`:n ensimmäinen rivi ennen muita importteja on `devsafe.relays_off()` (`main.py:1-3`).

## 7. Ajaminen ja päivitys Picolle, testien ajo

Ketju: `palvelin --adb TCP 5555--> OnePlus 7T Pro --USB-OTG--> Pico W` (`PICO-HALLINTA.md:8-20`).
Flashaus sovelluksen restore-intentillä (`--es espressopico_restore_backup <setti>`), joka
tarkistaa jokaisen tiedoston SHA-256 ennen kirjoitusta (`PICO-HALLINTA.md:93-106`); riippumaton
todennus `python3 Infra/iot/expresso/pico_dev.py verify <MANIFEST.json>`
(`PICO-HALLINTA.md:108-114`). Flashaus **ei vaadi verkkovirran katkaisua** — `PicoFlasher.flashFiles`
ajaa `relaysOff()`+`devsafe.enter()` heti keskeytyksen jälkeen (`PICO-HALLINTA.md:65-90`). Testiuutto:
`python3 Infra/iot/expresso/pico_dev.py shot <s> [loki]` (`PICO-HALLINTA.md:52-58`). Isäntätestit
ilman laitteistoa: `python3 testit/shot_test.py` ja `python3 testit/flow_ctrl_sim.py`, kumpikin
tulostaa `RESULT: 0 failed` (`paketit/VIRTAUSSAATO-2.brief.md:37,40`). `pico/MANIFEST.json` listaa
17 flashattavaa tiedostoa.

## 8. Mitä VIRTAUSSAATO-2 korjaukset 1-6 ja PAINESAADIN-HEILUNTA todistivat

Edellinen kaskadi (paine asetusarvona) kumottiin, koska laiteajo näytti asetusarvon valuvan lattiaan
10,5→2,0 bar 5 s:ssa avatulla venttiilillä (`VIRTAUSSAATO-2.md:11-26`). Korjaukset 1-6: vakio-
kuristus regressioajolle (correction-1), virtausväite 1,0 s keskiarvosta (correction-2), asettumisaika
`2/k+1,0 s=5,0 s` johdettuna (correction-3), toleranssi 0,3 g/s ja `p_margin` 1,0→3,0 rajasyklin
korjaukseksi (correction-4), `fsat` suodatetuksi virheeksi (correction-5), aloitusvaihe erotettu
väitteestä 6 (correction-6). `PAINESAADIN-HEILUNTA.md` (ei toteutettu) osoitti todennäköisen
juurisyyn pumpun heilunnalle (0,56-0,69 bar hajonta 8 barin pidoissa): dutyn kvantisointi
`int(duty*100/17+0,5)*17` sallii vain `0; 0,17; 0,34…`, ja pidon duty 0,13-0,14 osuu kahden askeleen
väliin — halvin ehdokas `window_ms` 100→300 (`PAINESAADIN-HEILUNTA.md:26-38`). `real_plant_sim.py`
ja `preinf_sim.py` sovittivat esiuuton mallia mittaukseen ja ennustivat devsafe6:n 25 %:n dutyportaan
riittämättömäksi, mikä johti rampitettuun setpointiin (`testit/real_plant_sim.py:1-10,50`).
`flow_rate_probe.py` mittasi HX711-parin todellisen näytetaajuuden (11,6 Hz) ja kohinan
(`testit/flow_rate_probe.py:1-6`). `dead_time.py` mittaa lokista pumpun käynnistyksestä veden
saapumiseen kuluvan ajan `mode`- ja `weight`-kentistä (`testit/dead_time.py:1-7`).

## Contradictions with the plan

- `konteksti-virtaussaato.md:5-9` (18.9.2026) väittää, ettei laitteen lähdekoodia ole tässä repossa
  tai tällä koneella. Vanhentunut: commit `b90be1c` (19.9.2026) toi koko firmware-lähteen repoon
  hakemistoon `pico/`, ja tämä raportti on luettu suoraan niistä tiedostoista.
- Aihe kysyy relettä/triacia/SSR:ää. Lähdekoodi (`preset.py:40-42`, `classes.py:701,730,740`)
  käsittelee pumppua pelkkänä `Pin.value()`-digitaali-ulostulona; ei triac-/SSR-ajuripiirin
  toteutusta eikä zero-cross-tunnistusta koodissa — vain kommentti "SSR" (`KEHITYSYHTEYS.md:317`).

## Unverified

- Pumpun fyysinen ajuripiiri (rele vs. SSR vs. triac) ei käy ilmi lähdekoodista — vain GPIO-pinni
  GP11 ja `Pin.OUT` (`preset.py:40`). Kytkentäkaaviota ei ole tässä skoopissa.
- `pico/api_functions.py` (169 riviä) luettiin vain listauksena, ei sisällöltään tähän raporttiin.
- `pico/boot.py`, `bluetooth_handler.py`, `devsafe.py`, `backflush.py` eivät olleet skoopissa;
  niiden sisältö nojaa vain `KEHITYSYHTEYS.md`:n ja `PICO-HALLINTA.md`:n kuvauksiin.
- Laitteistotesti uudella duty-pohjaisella virtaussäädöllä on ajamatta (`paarekisteri.md:7,950`) —
  kaikki VIRTAUSSAATO-2-luvun numerot ovat simulaatiosta.
- `PAINESAADIN-HEILUNTA.md`:n korjausehdokkaita ei ole toteutettu; tila "suunniteltu, ei toteutettu"
  (`PAINESAADIN-HEILUNTA.md:8`).

## Lue lisää

- eXpresso-pumppu-PWM → `Infra/iot/expresso/pico/classes.py` → `wc -l` 1258
- eXpresso-pumppu-PWM → `Infra/iot/expresso/pico/functions.py` → `wc -l` 710
- eXpresso-pumppu-PWM → `Infra/iot/expresso/KEHITYSYHTEYS.md` → `wc -l` 1055
- eXpresso-pumppu-PWM → `Infra/iot/expresso/PICO-HALLINTA.md` → `wc -l` 144
- eXpresso-pumppu-PWM → `Infra/iot/expresso/paketit/VIRTAUSSAATO-2.md` → `wc -l` 96
- eXpresso-pumppu-PWM → `Infra/iot/expresso/paketit/PAINESAADIN-HEILUNTA.md` → `wc -l` 52
- eXpresso-pumppu-PWM, vikarekisteri → `Infra/paarekisteri.md:631-642` → `wc -l` 1028
- eXpresso-pumppu-PWM, tilarivi 19.9.2026 → `Infra/paarekisteri.md:950` → `wc -l` 1028
