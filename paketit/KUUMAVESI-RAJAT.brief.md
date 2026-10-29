# EXPRESSO-KUUMAVESI-RAJAT

## Task
Siirrä kuumavesikytkimen silmukka `main.py`:stä funktioksi `functions.hot_water_run`, jossa ajo katkeaa
1 s:n jälkeen, lämmitin sammuu vartion katkaistessa pumpun ja lämmitintä ohjaa termostaatti
(TURVAKATO kohta 4, käyttäjän päätös 7.10.2026).

VAATIMUS: TILAUS-AUTONOMIA

Vain koodi ja isäntätesti, ei laiteajoa eikä flashia.

## Files
may:
- `Infra/iot/expresso/pico/functions.py`
- `Infra/iot/expresso/pico/main.py`

must not:
- `Infra/iot/expresso/testit/` (holdoutit `kuumavesi_smoke.py`, `turva_toimilaite_smoke.py`), `pico/relayguard.py`,
  `pico/classes.py`, `pico/MANIFEST.json` ja mikään muu tiedosto

read:
- `Infra/iot/expresso/pico/main.py:140-150` ja `:355-385` (nykyinen kuumavesilohko)
- `Infra/iot/expresso/testit/kuumavesi_smoke.py` (koko, määrää rajapinnan)
- `Infra/iot/expresso/pico/relayguard.py:287-311` (`GuardedRelay.value()` palauttaa pinnin tilan)

## Do
1. `functions.py` loppuun: vakio `HOT_WATER_MAX_MS = 1000` kommentilla "käyttäjä 7.10.2026, TURVAKATO kohta 4".
2. Samaan: `async def hot_water_run(brew_data, thermostat, utime, asyncio)`. Releet `brew_data.get_relays()`,
   kytkimet `brew_data.get_switches()`. Alussa `brew_data.set_mode('WATER')` ja `RELAY_PUMP.value(1)`;
   lämmitintä EI kytketä suoraan päälle.
3. Silmukka kirjoitetaan tasan muodossa `while (SWITCH_WATER.value()):`, ja sen sisällä
   `brew_data.get_boiler_temperature()` vähintään 1000 ms välein (ensimmäinen luku ennen silmukkaa).
   Niin kauan kuin syytä ei ole: jos aikaa alusta ≥ `HOT_WATER_MAX_MS` → syy `'time'`; muuten jos
   `RELAY_PUMP.value()` on 0 (vartio katkaisi) → syy `'pump'`; muuten `thermostat.run()`. Kun syy syntyy:
   `RELAY_PUMP.value(0)`, `RELAY_HEATER.value(0)`, `print('HOT_WATER_END reason=%s' % reason)`, eikä
   termostaattia eikä releitä kytketä enää ennen kytkimen vapautusta. Joka kierros `await asyncio.sleep_ms(50)`.
4. Silmukan jälkeen `RELAY_PUMP.value(0)`, `RELAY_HEATER.value(0)`,
   `brew_data.note_activity(utime.ticks_ms(), 'switch')`; palauta syy tai `'switch'`.
5. `main.py`: korvaa kuumavesilohkon (`if SWITCH_WATER.value():` … `note_activity`) runko kutsulla
   `await hot_water_run(brew_data, thermostat, utime, asyncio)`; lisää `hot_water_run` `functions`-tuontiin.
   Lohkon otsikkokommentti jää.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico/functions.py Infra/iot/expresso/pico/main.py
timeout 60 python3 Infra/iot/expresso/testit/kuumavesi_smoke.py
timeout 120 python3 Infra/iot/expresso/testit/turva_toimilaite_smoke.py
timeout 120 python3 Infra/iot/expresso/testit/turva_pika_smoke.py
timeout 120 python3 Infra/iot/expresso/testit/valmiustila_smoke.py
! grep -n "SWITCH_WATER.value()):" Infra/iot/expresso/pico/main.py
test "$(git -C Infra/iot/expresso diff --name-only | grep -v -E '^pico/(functions\.py|main\.py|MANIFEST\.json)$' | wc -l)" -eq 0
```

## Budget
4317 riviä (`wc -l` main.py 493, functions.py 3206, kuumavesi_smoke.py 183, turva_toimilaite_smoke.py 435);
luettavaa yllä olevat rivialueet; muutos alle 60 riviä.

## Stop
Jos `main.py`:n kuumavesilohko ei vastaa kuvausta, `thermostat` ei ole lohkon näkyvissä tai jokin
Acceptance-testi oli punainen jo ennen muutosta muusta syystä kuin `hot_water_run`/A7, kysy yksi kysymys
ja lopeta. Älä committaa, älä flashaa, älä aja `pico_dev.py`:tä.

## Report
Kuusi riviä: Status, Changed, Acceptance, Budget, Deviations, Questions.
