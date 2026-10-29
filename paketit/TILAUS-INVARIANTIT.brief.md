# EXPRESSO-TILAUS-INVARIANTIT

## Task
Tilauksen menetelmäkohdat nimetyiksi invarianteiksi (TILAUS-A…TILAUS-T, TILAUS-RELEET-ALAS, TILAUS-AUTONOMIA) ja koneellinen tarkistus:
1. Nimeä tilauksen menetelmäkohdat invarianteiksi `KAYTTAJAN-TIEDOT.md`:ssä käyttäjän omina lainauksina ja viittein `paketit/PUMPPU-PWM.md`:hen.
2. Täydennä takautuvassa tarkistuksessa myös kohdat 3 (`TILAUS-S`, max flow rate) ja 4 (`TILAUS-T`, höyryn lämpötilan säädin +10 °C).
3. Päivitä `paketit/PUMPPU-PWM.md`:n vaihetaulukkoon `Tilauskohdan tunnus` -sarake vaiheille 1a–1f, 2, 3, 4.
4. Päivitä `REKISTERI.md`:n luku `## Pysyvät vaatimukset (Tilauksen invariantit)`.
5. Luo kattava savutesti `testit/tilaus_invariantit_smoke.py`, joka todentaa invarianttien kattavuuden sekä `vaatimukset.mjs --tarkista` -toiminnan läpäisevällä ja hylkäävällä esimerkillä.
6. Päivitä `REKISTERI.md`, `HISTORIA.md`, `ARKISTO.md` ja `paketit/TILAUS-INVARIANTIT.md`.

VAATIMUS: TILAUS-A, TILAUS-B, TILAUS-C, TILAUS-D, TILAUS-E, TILAUS-F, TILAUS-G, TILAUS-H, TILAUS-I, TILAUS-J, TILAUS-K, TILAUS-L, TILAUS-M, TILAUS-N, TILAUS-O, TILAUS-P, TILAUS-Q, TILAUS-R, TILAUS-S, TILAUS-T, TILAUS-RELEET-ALAS, TILAUS-AUTONOMIA

## Files
may:
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md`
- `Infra/iot/expresso/paketit/PUMPPU-PWM.md`
- `Infra/iot/expresso/paketit/TILAUS-INVARIANTIT.md`
- `Infra/iot/expresso/paketit/TILAUS-INVARIANTIT.brief.md`
- `Infra/iot/expresso/testit/tilaus_invariantit_smoke.py`
- `Infra/iot/expresso/REKISTERI.md`
- `Infra/iot/expresso/HISTORIA.md`
- `Infra/iot/expresso/ARKISTO.md`

read:
- `Infra/iot/expresso/paketit/TILAUS-INVARIANTIT.md`
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md`
- `Infra/iot/expresso/paketit/PUMPPU-PWM.md`
- `claude/siirto/tools/vaatimukset.mjs`

## Do
1. `KAYTTAJAN-TIEDOT.md`:
   - Lisää viitteet `paketit/PUMPPU-PWM.md`:hen kohtiin `TILAUS-A`…`TILAUS-E`.
   - Lisää tilauksen kohdat 3 ja 4 invarianteiksi `TILAUS-S` ja `TILAUS-T`.
2. `paketit/PUMPPU-PWM.md`:
   - Lisää sarake `Tilauskohdan tunnus` vaihetaulukkoon vaiheille 1a–1f, 2, 3, 4.
3. `REKISTERI.md`:
   - Päivitä luvun otsikko muotoon `## Pysyvät vaatimukset (Tilauksen invariantit)`.
   - Kuvaa tilauksen invarianttien koneellinen tarkistus (`vaatimukset.mjs`).
   - Merkitse `EXPRESSO-TILAUS-INVARIANTIT` toteutetuksi `Avoimet asiat` -taulukossa.
   - Aseta `SEURAAVA PAKETTI: EXPRESSO-THERMAL-STABILITY`.
4. `testit/tilaus_invariantit_smoke.py`:
   - Toteuta savutesti, joka varmistaa kaikkien 22 tilausinvariantin olemassaolon, vaihetaulukon kattavuuden ja koneellisen tarkistuksen virheherkkyyden.
5. `HISTORIA.md` ja `ARKISTO.md`:
   - Dokumentoi toteutus ja arkistoi muutetut rekisteririvit.

## Acceptance
```bash
python3 Infra/iot/expresso/testit/tilaus_invariantit_smoke.py
node claude/siirto/tools/vaatimukset.mjs --tarkista "infra expresso" Infra/iot/expresso/paketit/TILAUS-INVARIANTIT.brief.md
```
