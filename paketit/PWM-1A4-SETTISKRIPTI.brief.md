# PWM-1A4-SETTISKRIPTI

## Task
Kirjoita `Infra/iot/expresso/build_set.py`: kopioi pohjasetin, työntää muuttuneet tiedostot ja
laskee `MANIFEST.json`:in puhelimen omasta `sha256sum`-tulosteesta.

## Files
may:
- `Infra/iot/expresso/build_set.py` (uusi)
- `Infra/iot/expresso/PICO-HALLINTA.md`

must not:
- `Infra/iot/expresso/pico/` kokonaan, `testit/` kokonaan, `pico_dev.py`
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/PICO-HALLINTA.md` luvut 2, 6, 7, 8, 9
- `Infra/iot/expresso/pico_dev.py` rivit 20-45 (adb:n valinta ympäristöstä)

## Do
1. Lue luvut. adb valitaan ympäristöstä kuten `pico_dev.py:29-31` (`PICO_ADB`, muuten
   `~/.local/share/platform-tools/adb`). Paketti `com.example.silvia_pico_ui`, setit
   `files/firmware_backup/<nimi>/`.
2. `build_set.py <uusi> [--from <pohja>] [tiedosto...]`. Ilman `--from` pohja on uusin
   (`ls -1t`). Ilman tiedostolistaa: `pico/*.py`, `pico/scale_cal.json`, `pico/lib/*.py`.
3. Kopioi pohja uudeksi (`run-as ... cp -r`), työnnä tiedostot `/data/local/tmp/`:n kautta, ja
   todenna jokainen: paikallinen SHA-256 vs. puhelimen `sha256sum`. Ristiriita on virhe.
4. Laske `MANIFEST.json` puhelimen `sha256sum`- ja `stat`-tulosteesta koko uudelle setille.
   `MANIFEST.json` itse ei ole listassa, `secrets.py` on. Kirjoita ja todenna sekin.
5. `--check` (H-067): ei yhtään muuttavaa komentoa, yksi `preflight:`-rivi (adb tavoitettavissa,
   laite `device`-tilassa, akku %, pohjasetti, työnnettävien määrä), epänolla jos esiehto estää
   ajon — akku alle 20 %, adb ei vastaa, pohjasettiä ei ole, uusi setti on jo olemassa.
6. Tulosta lopuksi valmis palautuskomento ilman paikanvaraajia ja muistutus, ettei sarjalinkkiin
   kosketa ennen `RESTORE_OK`-riviä.
7. `PICO-HALLINTA.md` luku 6: `build_set.py`:n käyttö kolmen käsin ajettavan komennon tilalle,
   käsin ajettavat jätetään näkyviin varareittinä.
8. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne raportoivat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile build_set.py
```
```bash
cd /srv/work/Infra/iot/expresso && PICO_ADB=/bin/false python3 build_set.py --check testi > /tmp/c1.out 2>&1; test $? -ne 0 && grep -q "^preflight:" /tmp/c1.out
```
```bash
cd /srv/work/Infra/iot/expresso && python3 - <<'PY'
import sys, importlib.util
sp = importlib.util.spec_from_file_location('bs','build_set.py'); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
h = 'a'*64; base = '/d/files/firmware_backup/s1/'
rows = m.parse_sha256sum('%s  %smain.py\n%s  %sMANIFEST.json\n' % (h, base, h, base))
man = m.build_manifest(rows, {'/main.py': 12})
f = [x for x in [
  None if rows.get('/main.py') == h else 'nimi ei jasenny /main.py:ksi',
  'MANIFEST.json on listassa' if any(e['name'] == '/MANIFEST.json' for e in man) else None,
  None if any(e['name'] == '/main.py' and e['size'] == 12 for e in man) else 'koko puuttuu'] if x]
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f)); sys.exit(1 if f else 0)
PY
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso > /tmp/c2.out && grep -cvE "(build_set\.py|PICO-HALLINTA\.md)$" /tmp/c2.out | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat build_set.py PICO-HALLINTA.md | wc -l) -le 480
```
Mitattu lähtötaso (`wc -l`, commit a232184): `build_set.py` 0 + `PICO-HALLINTA.md` 145 = 145 —
varaa 335 riviä.

## Stop
- Manifestin muotoa ei saa pääteltyä luvusta 6 yksikäsitteisesti.

Kysy tällöin yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** älä aja `adb`-komentoja,
älä yhdistä puhelimeen. Hyväksyntä ajaa vain `--check`:n väärällä adb-polulla.

## Report
```text
brief: PWM-1A4-SETTISKRIPTI
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/480
iterations: <yritysten määrä>
note: <yksi rivi: mitkä esiehdot --check tarkistaa>
```
