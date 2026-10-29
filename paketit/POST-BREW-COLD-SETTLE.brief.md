# EXPRESSO-POST-BREW-COLD-SETTLE

## Task
Estä uutonjälkeisen lämmönsäädön (`_post_brew`) ja asettumisvaiheen (`settle`) aktivoituminen,
kun kattila on kylmä (`boiler_temperature < target_temperature - BH_COLD_C`). Korjaa `arm 2`
(ei-oppiva huuhtelu/keskeytys) luovuttamaan ohjaus normaalille lämmitykselle 2 minuutissa
(`BH_SETTLE_MAX_MS`) tavoitteen alapuolella 10 minuutin (`BH_NOLEARN_MAX_MS`) loukun sijaan.

VAATIMUS: TILAUS-R, TILAUS-N, TILAUS-P, TILAUS-AUTONOMIA

## Files
may:
- `Infra/iot/expresso/pico/classes.py`
- `Infra/iot/expresso/pico/functions.py`
- `Infra/iot/expresso/testit/termostaatti_smoke.py`
- `Infra/iot/expresso/pico/MANIFEST.json`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/ARKISTO.md`

read:
- `Infra/iot/expresso/pico/classes.py:1865-1928`
- `Infra/iot/expresso/pico/classes.py:2000-2020`
- `Infra/iot/expresso/pico/functions.py:1345-1360`
- `Infra/iot/expresso/testit/termostaatti_smoke.py`
- `Infra/iot/expresso/REKISTERI.md`

## Do
1. `pico/classes.py`:
   - Määritä vakio `BH_COLD_C = 8.0`.
   - `Thermostat.run`: jos `boiler_temperature < target_temperature - BH_COLD_C`, nollaa `bh_arm` ja `bh_phase = None` (kylmä kattila ei siirry post-brew-vaiheeseen).
   - `Thermostat._post_brew`: jos `t < target - BH_COLD_C`, päätä vaihe välittömästi (`self._bh_end(t, target, 'cold')`) ja palauta `False`.
   - `Thermostat._bh_end`: älä opi (`_bh_learn`), jos `why == 'cold'`.
   - `Thermostat._post_brew` (`settle`): salli `arm 2` -tilassa (`not self.bh_learn`) luovutus `BH_SETTLE_MAX_MS` (2 min) kohdalla tai `why='low'`, jos lämpötila on tavoitteen alapuolella eikä nouse.
2. `pico/functions.py`:
   - Määritä vakio `BH_COLD_C = 8.0`.
   - `run_shot`: jos kattila on kylmä (`t_now < target - BH_COLD_C`), nollaa `bh_sum_us`, `bh_credit_us` ja `bh_arm = 0` (kylmä huuhtelu ei viritä uutonjälkeistä tilaa).
3. `testit/termostaatti_smoke.py`:
   - Lisää testitapaukset K1–K4 kylmälle huuhtelulle ja `arm 2` -luovutukselle.
4. `pico/MANIFEST.json`:
   - Päivitä manifesti komennolla `python3 pico_dev.py manifest pico/MANIFEST.json`.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico/classes.py
python3 -m py_compile Infra/iot/expresso/pico/functions.py
python3 Infra/iot/expresso/testit/termostaatti_smoke.py
python3 Infra/iot/expresso/testit/lampotilatilat_smoke.py
python3 Infra/iot/expresso/testit/valmiustila_smoke.py
python3 Infra/iot/expresso/testit/turva_pika_smoke.py
python3 Infra/iot/expresso/testit/turva_toimilaite_smoke.py
python3 Infra/iot/expresso/testit/nollausikkuna_smoke.py
python3 Infra/iot/expresso/testit/tilaus_invariantit_smoke.py
```
