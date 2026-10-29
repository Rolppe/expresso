# PWM-1A2-ISANTAKOMENTO

## Task
Lisää `pico_dev.py`:hyn operaatio `pcap`, joka lähettää `CMD pcap:<ms>`:n ja kaappaa vastauksen
**samalta yhteydeltä**, koska silta palvelee vain yhtä asiakasta.

## Files
may:
- `Infra/iot/expresso/pico_dev.py`
- `Infra/iot/expresso/PICO-HALLINTA.md`

must not:
- `Infra/iot/expresso/pico/` kokonaan, `testit/` kokonaan
- mikään tiedosto hakemiston `Infra/iot/expresso/` ulkopuolella

read:
- `Infra/iot/expresso/pico_dev.py` rivit 1-20, 140-200, 220-240
- `Infra/iot/expresso/PICO-HALLINTA.md` luvut 3, 4, 9
- `Infra/iot/expresso/paketit/PUMPPU-PWM.md` luku "Kaappauksen sarjaprotokolla"

## Do
1. Lue yllä luetellut rivivälit. `shot()` (`pico_dev.py:169-175`) on tarkka malli: yksi `Link()`,
   `link.send(...)`, sitten `capture(..., link=link)`. Sillan yhden asiakkaan rajoitus on
   `PICO-HALLINTA.md` luku 3, ja kahden yhteyden avaaminen menetti kerran ensimmäiset 24 s.
2. Kirjoita `def pcap(ms, out_path=None)`: yksi `Link()`, lähetä `CMD pcap:<ms>`, sitten
   `capture(<ms>/1000.0 + 20, out_path, stop_marker=b'PCAP_END', link=link)`. Marginaali 20 s
   kattaa 1 s asettumisen ja enintään 125 rivin tulostuksen sarjalinkillä.
3. Lisää `pcap` `main()`:n operaatiovalintaan (`pico_dev.py:224-236`) muiden tyyliin:
   `pcap <ms> [loki]`, ja lisää rivi käyttöohjeeseen tiedoston alussa (`pico_dev.py:10-17`).
4. Palauta lopusta epänollainen paluuarvo, jos kaapatusta tulosteesta ei löydy `PCAP_END`-riviä
   tai jos sen `reason=` on muu kuin `ok` — laiteajo ei saa näyttää onnistuneelta, kun kaappaus
   katkesi ylipaineeseen tai kytkimeen. Tulosta silloin yksi rivi `PCAP_FAIL reason=<syy>`.
5. Lisää `PICO-HALLINTA.md`:n luvun 4 komentotaulukkoon rivi `pcap <ms> [loki]` ja luvun 10
   lokitunnisteisiin `PCAP_START`/`PCAP`/`PCAP_END`.
6. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne raportoivat punaiseksi.

## Acceptance
```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico_dev.py
```
```bash
cd /srv/work/Infra/iot/expresso && python3 pico_dev.py > /tmp/b1.out 2>&1; grep -q "pcap <ms>" /tmp/b1.out
```
```bash
cd /srv/work/Infra/iot/expresso && python3 - <<'PY'
import re, sys
s = open('pico_dev.py').read()
b = s[s.index('def pcap('):]
b = b[:b.index('\ndef ')] if '\ndef ' in b else b
f = []
if b.count('Link()') != 1: f.append('ei tasan yhta Link()-yhteytta')
if "stop_marker=b'PCAP_END'" not in b and 'stop_marker=b"PCAP_END"' not in b: f.append('ei PCAP_END-pysaytysmerkkia')
if 'link=link' not in b: f.append('capture ei kayta samaa linkkia')
if 'PCAP_FAIL' not in b: f.append('ei epaonnistumisen raportointia')
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f))
sys.exit(1 if f else 0)
PY
```
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso > /tmp/b2.out && grep -cvE "(pico_dev\.py|PICO-HALLINTA\.md)$" /tmp/b2.out | grep -qx 0
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico_dev.py PICO-HALLINTA.md | wc -l) -le 420
```
Mitattu lähtötaso (`wc -l`, commit 9e9b871): `pico_dev.py` 240 + `PICO-HALLINTA.md` 144 = 384 —
varaa 36 riviä. Katto on väljä tarkoituksella: edellinen brief pakotti toteuttajan tiivistämään
rivejä mahtuakseen 2800:aan.

## Stop
- `pico_dev.py` ei käänny jo ennen ensimmäistä muokkausta.
- `capture()`:n allekirjoitus ei salli `link`- tai `stop_marker`-argumenttia.

Kysy tällöin yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen:** älä ota adb-yhteyttä, älä
aja `pico_dev.py`:n operaatioita, älä flashaa. Hyväksyntä ajaa vain `--help`-tulosteen.

## Report
```text
brief: PWM-1A2-ISANTAKOMENTO
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit yhteensä>/420
iterations: <yritysten määrä>
note: <yksi rivi: mikä aikakatkaisu jäi voimaan>
```
