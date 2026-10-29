# EXPRESSO-C1X-JALKINOUSU

## Task
Sovita C1X-jälkinousun lisäviive laitedatasta (EU_C1X_LAG_S) ja päivitä firmware:
1. `testit/sovita_c1x_lag.py`:
   - Sovita `EU_C1X_LAG_S` 20.10.2026 kerätystä laitedatasta (`testit/c1x-20261020-sarja*.log` ja `testit/c1x-20261020-sarjab*.log`, yhteensä 12 laiteuuttoa).
   - Sarja 1 (dly = 0.0): c1x ka dt 0.0904 s vs c0 0.0728 s -> viive-ero 17.6 ms, ylitysero +0.36 bar.
   - Sarja 2 (dly = 0.020): c1x ka dt 0.1049 s vs c0 0.0714 s -> viive-ero 33.4 ms, jäännösylitys +0.07 bar.
   - Kaikkien 11 täyden nopeuden ajon keskimääräinen lisäviive: c1x (0.0962 s) vs c0 (0.0721 s) = 24.1 ms.
   - Sarja 2:n jäännösylityksen (+0.07 bar @ 21.5 bar/s) poistava viivelisäys on +3.1 ms, jolloin optimaalinen viive on 23.1 ms (~0.024–0.025 s).
   - Fysikaalinen selitys: k+2-jonon 20 ms + SSR-40DA:n nollaylityksen odotusaika (tasajakautunut 0..10 ms, odotusarvo 5 ms) = 25 ms.
2. `pico/functions.py`:
   - Päivitä `EU_C1X_LAG_S = 0.025` (25 ms). Arvo vastaa tarkasti 1¼ verkkojaksoa (25 ms) ja ottaa huomioon SSR:n nollaylityksen viiveen.
3. `testit/c1x_lag_smoke.py`:
   - Luo savutesti C1–C7, joka testaa vakion arvon, koodin kytkennän (dly), laitedatan sovitustulokset, fysikaalisen mallin, katkaisun ennusteen ja jälkinousun opin algebrallisen invarianssin sekä simuloidun uuton polkuriippumattomuuden (C1Exec vs vanha polku).
4. Päivitä `pico/MANIFEST.json`, `REKISTERI.md`, `HISTORIA.md`.

VAATIMUS: TILAUS-O, TILAUS-K, TILAUS-AUTONOMIA

## Files
may:
- `Infra/iot/expresso/pico/functions.py`
- `Infra/iot/expresso/testit/sovita_c1x_lag.py`
- `Infra/iot/expresso/testit/c1x_lag_smoke.py`
- `Infra/iot/expresso/pico/MANIFEST.json`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/paketit/C1X-JALKINOUSU.brief.md`

read:
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/paketit/C1-JAKSOT.md`
- `Infra/iot/expresso/pico/functions.py`

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico/functions.py
python3 Infra/iot/expresso/testit/sovita_c1x_lag.py
python3 Infra/iot/expresso/testit/c1x_lag_smoke.py
python3 Infra/iot/expresso/testit/tilaus_invariantit_smoke.py
node claude/siirto/tools/vaatimukset.mjs --tarkista "infra expresso" Infra/iot/expresso/paketit/C1X-JALKINOUSU.brief.md
```
