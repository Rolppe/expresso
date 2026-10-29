# ZERO-PARITEETTI

## Task
Kirjaa Zero- ja puhelinketjun debug-kykyjen vertailu `PICO-HALLINTA.md`:hen ja tee `pico_dev.py`:n
Zero-herätyksestä aidosti ei-kaatava aikakatkaisussa.

## Files
may:
- `Infra/iot/expresso/PICO-HALLINTA.md`
- `Infra/iot/expresso/pico_dev.py`

must not:
- mikään muu tiedosto, erityisesti `Infra/iot/zero/` (skooppi infra zero) ja `pico/`

read:
- `/tmp/claude-1000/-home-user-palvelin/b1c9c8a1-0be8-4d99-803a-84875fd24be0/scratchpad/ctx-zero-parity.md` (vertailu, rivit 18-47 taulukko)
- `Infra/iot/expresso/PICO-HALLINTA.md` luvut 1 ja 4 (rivit 8-105)
- `Infra/iot/expresso/pico_dev.py:178-196`

## Do
1. `pico_dev.py` `_connect`: kääri Zero-haaran `subprocess.run([... 'ssh' ...], timeout=15)` (n. rivit 184-186)
   `try`/`except (subprocess.TimeoutExpired, OSError): pass` -lohkoon; kommentti sanoo jo
   "failure here is not fatal", nyt `TimeoutExpired` kaataisi työkalun. Ei muita muutoksia.
2. `PICO-HALLINTA.md`: lisää luvun 4 loppuun alaluku `### Debug-kyvyt: Zero vs puhelin (6.10.2026)`.
   Suomeksi, enintään 14 taulukkoriviä sarakkein `Kyky | Puhelin | Zero | Tila`, tiivistettynä
   vertailun taulukosta: cmd/capture/mittauskomennot, safe, verify/flash, restore/build_set,
   laturi ja Picon virtakatko, re-enumerointi, pysyvä sarjaloki, kaatumisen traceback, BLE/logcat,
   tiedostojen luku Picolta, BOOTSEL/picotool. Tila-sarakkeessa `on`, `osin`, `puuttuu` tai
   `ei tarvita`.
3. Taulukon alle kaksi riviä: "Zeron puolen aukot (pysyvä loki, ser2net-mykkyys, virtakatko,
   asetukset repoon): V-207 → infra zero (f37507e)." ja "Kumpikaan ketju ei lue tiedostoja
   Picolta eikä tallenna kaatumisen tracebackia; `pico_dev.py log` tehdään, kun V-207:n loki on olemassa."

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico_dev.py
grep -q "except (subprocess.TimeoutExpired, OSError)" Infra/iot/expresso/pico_dev.py
grep -q "### Debug-kyvyt: Zero vs puhelin" Infra/iot/expresso/PICO-HALLINTA.md
grep -q "V-207" Infra/iot/expresso/PICO-HALLINTA.md
test "$(git diff --name-only | grep -v -E '^Infra/iot/expresso/(PICO-HALLINTA\.md|pico_dev\.py)$' | wc -l)" -eq 0
```

## Budget
991 riviä luettavaa (`wc -l` PICO-HALLINTA.md 276 + pico_dev.py 715); muutos alle 40 riviä.

## Stop
Jos rivit 184-186 eivät vastaa kuvausta tai luku 4 puuttuu, kysy yksi kysymys ja lopeta.
Älä committaa.

## Report
Kuusi riviä: Status, Changed, Acceptance, Budget, Deviations, Questions.
