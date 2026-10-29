# PWM-1A-VERKKOTAAJUUS — korjaus 4

Laiteajo 2 (19.9.2026, `pcap:2000` tasannetilassa) päätti asettumisen rivillä
`PCAP_SETTLED bar=-0.20 peak=2.30 ms=1000 reason=plateau` — eli ensimmäisellä tarkistuksella,
paineen ollessa nollassa. Kaappauksen aikana paine nousi 8,32 bariin. Kriteeri on siis yhä väärä,
ja tällä kertaa syy on mitattu.

`may:`-listaan lisätään `Infra/iot/expresso/pico_dev.py` (suunnittelijan päätös: firmwaren
komentomuoto `pcap:<ms>[:<bar>]` on olemassa, mutta isäntätyökalu ei osaa lähettää sitä).

## Mittaus — paineen nousu ei ole monotoninen vaan kaksivaiheinen

Laiteajon 2 lokista (`testit/pcap-20260919-tasanne.log`), suodatettu tau 0,3 s, ajat kaappauksen
alusta:

| t | paine | | t | paine |
|---|---|---|---|---|
| 0 ms | −1,30 bar | | 1400 ms | 0,66 bar |
| 600 ms | −0,38 bar | | 1800 ms | 2,49 bar |
| 1000 ms | −0,01 bar | | 1999 ms | 4,37 bar |

Nousunopeus viimeisellä 500 ms:lla on **6,89 bar/s**, mutta ensimmäisen sekunnin aikana se on
alle 0,3 bar/s. Pumppu täyttää ensin piirin, eikä paine nouse. **Täyttövaiheessa on siis aito
tasanne**, ja mikä tahansa tasannetunnistin laukeaa siellä ellei sitä estetä.

## Vika 1 — tasanne täyttövaiheessa kelpaa tasanteeksi

Ehto `(p_filt - plateau_bar) < PCAP_PLATEAU_BAR` on tosi aina, kun paine ei vielä nouse.

**Korjaus:** tasanne kelpaa vain paineen ylitettyä lattian. `PCAP_PLATEAU_MIN_BAR = 1.0`; kun
`p_filt < PCAP_PLATEAU_MIN_BAR`, tasannetta ei edes testata ja `plateau_t`/`plateau_bar`
nollataan nykyhetkeen. Aikakatto ja ylipaine ovat yhä voimassa, joten juuttumista ei synny.

## Vika 2 — mikään ehto ei saisi laueta ennen kuin täyttö on ohi

Mitattu täyttövaihe kesti yli 2 s ennen kuin nousu edes alkoi.

**Korjaus:** `PCAP_SETTLE_MIN_MS = 2000`. Ennen sitä mikään lopetusehto ei laukea — ei tavoite
eikä tasanne. Ylipaine, kytkin, `dev_safe` ja `pcap:stop` keskeyttävät yhä heti.

## Vika 3 — `plateau_bar` alustetaan yhdestä raakanäytteestä

`plateau_bar = p_filt`, missä `p_filt = first_bar` on yksi raakanäyte (sd 1,595 bar). Ensimmäinen
vertailu tehdään siis kohinanäytettä vastaan.

**Korjaus:** alusta `plateau_bar` ja `plateau_t` vasta kun `PCAP_SETTLE_MIN_MS` on täyttynyt,
suodatetusta arvosta.

## Vika 4 — isäntätyökalu ei osaa lähettää tavoitetta

`pico_dev.py:183` tekee `float(ms)`, joten `pcap 2000:6.0` kaatuu `ValueError`iin eikä
firmwaren tavoitetilaa voi käyttää lainkaan.

**Korjaus:** `pcap`-operaatio hyväksyy argumentin muodossa `<ms>[:<bar>]`. Aikakatkaisu lasketaan
vain `<ms>`-osasta, ja siihen lisätään `PCAP_SETTLE_MAX_MS`:n verran (15 s) sekä nykyinen 20 s:n
marginaali, koska asettuminen voi nyt kestää 15 s. Koko argumentti välitetään sellaisenaan
`CMD pcap:` -riville.

## Acceptance

Briefin neljä komentoa, korjausten 1-3 rakennetarkistukset, ja nämä:

```bash
cd /srv/work/Infra/iot/expresso && python3 - <<'PY'
import sys
src = open('pico/functions.py').read()
b = src[src.index('async def pressure_capture_run'):]
b = b[:b.index('if settled:')]
f = []
for c in ('PCAP_SETTLE_MIN_MS', 'PCAP_PLATEAU_MIN_BAR'):
    if c not in src: f.append('%s puuttuu' % c)
if 'PCAP_SETTLE_MIN_MS' not in b: f.append('vahimmaisaikaa ei kayteta silmukassa')
if 'PCAP_PLATEAU_MIN_BAR' not in b: f.append('painelattiaa ei kayteta silmukassa')
if 'first_bar' in b and 'plateau_bar = p_filt' in b.split('while')[0]:
    f.append('plateau_bar alustetaan yha ennen vahimmaisaikaa')
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f)); sys.exit(1 if f else 0)
PY
```

```bash
cd /srv/work/Infra/iot/expresso && python3 -m py_compile pico_dev.py && python3 - <<'PY'
import sys, importlib.util
sp = importlib.util.spec_from_file_location('pd','pico_dev.py'); m = importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)
src = open('pico_dev.py').read()
b = src[src.index('def pcap('):]
b = b[:b.index('\ndef ')]
f = []
if 'float(ms)' in b and 'split' not in b: f.append('argumenttia ei jasenneta ms:bar-muodossa')
if 'split' not in b: f.append('tavoitekenttaa ei eroteta')
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f)); sys.exit(1 if f else 0)
PY
```

```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/classes.py pico/commands.py pico/functions.py pico/main.py testit/mains_freq.py | wc -l) -le 2920 && test $(wc -l < pico_dev.py) -le 275
```

## Report

Sama kuusirivinen muoto kuin briefissä, `iterations: 5`.
