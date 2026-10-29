# EXPRESSO-VALMIUSTILA — 30 min käyttämättä → kattila 90 °C:een, mikä tahansa kytkin palauttaa

VAATIMUS: ei koske — käyttäjän pyyntö 5.10.2026 koskee lämpötilatavoitetta, ei paineensäätöä (TILAUS-A…N) eikä siirtoa.
Syy (käyttäjä): pitkän levon jälkeen pumppu käy kauan ennen kuin vettä tulee; epäily: kattilan paine työntää
vettä hiljalleen pumpun läpi säiliöön. Matalampi lepolämpö pienentää kattilan painetta.

Skooppi `infra expresso`. Lue ensin: `pico/classes.py` (`BrewData.__init__`, `get_target_temperature`,
`Thermostat.run`), `pico/main.py` (`local_program`-silmukka, kytkinhaarat, tila `IDLE`/`STEAM`), `pico/commands.py`
(`handle_command`, `pim:`-haara mallina), `testit/shot_test.py` (feikki-`utime`/`machine`-rakenne mallina).

## Tee

1. **BrewData (`pico/classes.py`):** uudet kentät `standby_timeout_ms` (oletus 30 × 60 000), `standby_temperature`
   (90), `standby` (False), `last_activity_ms` (konstruktorissa `utime.ticks_ms()`, jos utime annettu, muuten 0).
   Metodit:
   - `note_activity(now_ms, reason)`: `last_activity_ms = now_ms`; jos `standby` oli tosi → `standby = False` ja
     tulosta `STBY_OFF reason=<reason>`.
   - `update_standby(now_ms)`: jos `standby_timeout_ms > 0`, ei jo valmiustilassa, `mode == 'IDLE'` ja
     `ticks_diff(now_ms, last_activity_ms) >= standby_timeout_ms` → `standby = True`, tulosta
     `STBY_ON idle_s=<s> target=<t>`. Valmiustila **pysyy** (salpa), kunnes `note_activity` purkaa sen: ticks_ms:n
     kierto (ticks_diff kelpaa vain ~6 vrk) ei saa purkaa sitä.
   - `get_target_temperature`: `IDLE`-haarassa, kun `standby` on tosi, palauta `min(brew_temperature,
     standby_temperature)`. Muut tilat ennallaan (STEAM, WATER, BREW, BACKFLUSH_* eivät koskaan laske tavoitetta).
2. **Aktiivisuus kytkimistä (`pico/main.py`):** silmukan jokaisella kierroksella, kun mikä tahansa kolmesta
   kytkimestä (`SWITCH_BREW`, `SWITCH_WATER`, `SWITCH_STEAM`) on päällä → `note_activity(now, 'switch')`; lisäksi heti
   kun uutto-, kuumavesi- tai tshot-haara palaa, jotta ajastin alkaa toiminnon lopusta. `update_standby(now)` kerran
   kierroksessa ennen `thermostat.run()`ia. Ei uusia blokkaavia kutsuja.
3. **Aktiivisuus äpistä (`pico/commands.py`):** `handle_command`in lopussa, kun `updated` on tosi →
   `brew_data.note_activity(utime.ticks_ms(), 'app')` (sama polku BLE:lle ja sarjalinjalle). Pelkät lukukomennot
   (`updated` epätosi) eivät herätä.
4. **Komento `stby:<min>`** (`commands.py`, RAM kuten `pim`): asettaa `standby_timeout_ms` (0 = valmiustila pois,
   rajaa 0…240 min), `updated = True`. `stby:on` pakottaa valmiustilan heti (laitetestiä varten, tulostaa STBY_ON),
   ja tulosta `STBY timeout_min=<m> standby=<0|1> temp=<t>` jokaisesta `stby:`-komennosta. Kirjaa komento
   `PICO-HALLINTA.md`:n komentotaulukkoon samaan muotoon kuin `pim`.
5. **Smoke `testit/valmiustila_smoke.py`** (shot_test.py:n feikkirakenne, `/tmp/fw`-esiehto samoin), tapaukset:
   (a) 29 min 59 s ilman toimintaa → ei valmiustilaa, tavoite = brew; (b) 30 min → STBY_ON, tavoite 90;
   (c) uuttokytkin päälle → STBY_OFF reason=switch, tavoite = brew; (d) `pre:on` → STBY_OFF reason=app;
   (e) lukukomento (`updated` epätosi) ei herätä; (f) brew_temperature 88 → valmiustilan tavoite 88;
   (g) STEAM-tila valmiustilassa → tavoite steam; (h) `stby:0` → ei valmiustilaa 2 h:ssa;
   (i) ticks_diff negatiivinen (kierto) valmiustilassa → pysyy valmiustilassa. Jokainen tapaus osoitetaan kaatuvaksi
   ilman korjausta, kun mahdollista.
6. Aja `timeout 300 python3 testit/valmiustila_smoke.py` ja kaikki muut `testit/*_smoke.py` erikseen aikarajalla,
   ilman putkea, paluukoodi näkyviin. Ennestään punaiset (esim. `shot_test.py`, eu_g_pre) raportoidaan, ei korjata.

## Älä

- Älä flashaa, älä aja laitetta (`pico_dev.py`, adb), älä committaa: pääistunto katselmoi ja committaa.
- Älä muuta `save_settings`/`load_settings`ia (asetus on RAM-tilainen), paineensäätöä tai uuttosilmukoita.
- Älä muuta Android-sovellusta.

## Stop

Kysy yksi kysymys ja lopeta, jos: kytkimen tila ei ole luettavissa jossain haarassa ilman blokkaavaa kutsua; tai
`get_target_temperature`ia kutsutaan muualla tavalla, jossa valmiustila laskisi uutto-/höyrytavoitetta.

## Raportoi (enintään 25 riviä)

Muutetut tiedostot rivimäärineen; smoke-tulokset komentoineen ja paluukoodeineen (uudet tapaukset: ilman korjausta
vs. korjauksella); muiden smokejen tila; avoimet riskit laiteajolle ja ehdotettu laitetesti (`stby:on`, lämpötilan
lasku lokista, kytkin herättää).
