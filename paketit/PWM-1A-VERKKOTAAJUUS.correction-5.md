# PWM-1A-VERKKOTAAJUUS — korjaus 5

Käyttäjän vaatimus 19.9.2026: **mittauksen aika lasketaan siitä hetkestä, kun tavoitepaine on
saavutettu**, ei pumpun käynnistyksestä, ja tarvittava aika johdetaan siitä. Nykyinen koodi laskee
kaiken pumpun käynnistyksestä eikä pidä tavoitteessa lainkaan: kaappaus alkaa samalla
millisekunnilla kun ehto laukeaa, jolloin se osuu yhä nousun loppuosaan.

`may:` kuten korjauksessa 4 (`pico/functions.py`, `pico_dev.py`) ja lisäksi `testit/mains_freq.py`.
Budjettikatot: viisi firmware-/testitiedostoa 2920 → 2990, `pico_dev.py` 275 → 300.

## Johdettu aikabudjetti

Laitokselle sovitettu malli on `dp/dt = 6,7·pumppu − 1,24·paine` (`testit/real_plant_sim.py:15`,
`GAIN, LEAK = 6.7, 1.24`), eli aikavakio `tau = 1/1,24 = 0,806 s`. Ketjussa on lisäksi 70 ms
toimilaite- ja anturiviive (`real_plant_sim.py:8`) ja korjauksen 3 suodattimen `PCAP_FILT_TAU
= 0,3 s`.

| Vaihe | Aika | Johto |
|---|---|---|
| tavoite saavutettu | 0 | nollakohta |
| pito | **3000 ms** | `3·tau = 2,42 s` viiden prosentin sisään, plus suodattimen viive 0,3 s = 2,72 s, pyöristys ylös |
| kaappaus | 2000 ms | 100 jaksoa 50 Hz:llä: 0,5 Hz binit ja sata iskua aaltomuodon keskiarvoon |

Kaappausta ei pidennetä: taajuus on jo ratkaistu (conf 6,81 ja 7,59 kahdessa ajossa) ja puskuri on
rajattu 2500 näytteeseen. Pahin yhtäjaksoinen pumppausaika on `15 s + 3 s + 2 s = 20 s`.

## Korjaus 1 — pitovaihe tavoitteen ja kaappauksen väliin

Uusi vakio `PCAP_HOLD_MS = 3000`. Kun `settle_reason` laukeaa, **kaappaus ei ala heti**: pumppu
jää päälle ja suodatettua painetta seurataan `PCAP_HOLD_MS`:n ajan, ja vasta sitten kaappaus
alkaa. Pitosilmukka on ei-estävä (`await asyncio.sleep_ms(0)`) ja siinä ovat voimassa samat
keskeytysehdot kuin asettumisessa: kytkin, `dev_safe`, `pcap:stop`, ylipaine.

Mittaa pidon aikana suodatetun paineen ajautuma: `drift = p_filt(lopussa) − p_filt(alussa)`.

## Korjaus 2 — kaksi erillistä aikaa, molemmat raportoituna

`PCAP_SETTLE_MAX_MS = 15000` koskee **vain tavoitteen saavuttamista**, ei pitoa eikä kaappausta.
Korvaa `PCAP_SETTLED`-rivi tällä:

```text
PCAP_SETTLED bar=<p_filt> peak=<pmax> reach_ms=<aika pumpun kaynnistyksesta> hold_ms=<pidon kesto> drift=<bar> reason=<target|plateau|timeout>
```

`reach_ms` on aika käynnistyksestä ehdon laukeamiseen; `hold_ms` on pidon toteutunut kesto.
Rivi tulostetaan **pidon jälkeen**, juuri ennen kaappausta, jotta `drift` on siinä mukana.

## Korjaus 3 — analysaattori kertoo, oliko paine todella asettunut

`testit/mains_freq.py` tulostaa `MAINS`- ja `HARM2`-rivien väliin uuden rivin:

```text
DRIFT <bar> bar kaappauksen yli, alku <bar> loppu <bar>
```

Arvot lasketaan näytesarjan ensimmäisen ja viimeisen 200 ms:n keskiarvoista. Tämä on se luku,
joka kertoo onko amplitudi vertailukelpoinen; ilman sitä jokainen ajo pitää tulkita käsin.
`--selftest` saa yhden uuden väitteen, ja se on **johdettu, ei kovakoodattu**. Ikkunoiden
keskikohdat ovat `w/2` ja `T - w/2`, joten niiden väli on `T - w` eikä koko `T`. Lineaarisella
nousulla odotusarvo on siis `ramp_bar * (1 - w/T)`, missä `w = 0,2 s` on ikkunan leveys ja
`T = n * dt_s` kaappauksen kesto. Testin on laskettava tämä samoista muuttujista, joilla
synteettinen sarja rakennetaan; toleranssi on `± 0,2 bar`.

Alkuperäinen väite tässä korjauksessa oli `2,0 ± 0,2 bar`, mikä oli suunnittelijan aritmeettinen
virhe: 2 bar/2 s nousulla ikkunakeskiarvojen erotus on `2,0 * 1,8/2,0 = 1,80 bar`. Toteuttaja
mittasi 1,78-1,85 kymmenellä siemenellä ja pysähtyi kysymään sen sijaan että olisi löysännyt
lukua. Johdettu muoto korjaa syyn eikä oiretta: se pysyy oikeana, jos `ramp_bar`, ikkuna tai
näytemäärä muuttuu.

## Acceptance

Briefin neljä komentoa, korjausten 1-4 rakennetarkistukset, ja nämä:

```bash
cd /srv/work/Infra/iot/expresso && python3 - <<'PY'
import sys
src = open('pico/functions.py').read()
b = src[src.index('async def pressure_capture_run'):]
f = []
if 'PCAP_HOLD_MS = 3000' not in src: f.append('pitoaikaa ei ole tai se ei ole 3000')
if 'reach_ms=' not in b: f.append('reach_ms puuttuu')
if 'hold_ms=' not in b: f.append('hold_ms puuttuu')
if 'drift=' not in b: f.append('drift puuttuu')
i_hold = b.find('PCAP_HOLD_MS')
i_settled = b.find('PCAP_SETTLED')
if i_hold < 0 or i_settled < 0 or i_hold > i_settled: f.append('PCAP_SETTLED ei tulostu pidon jalkeen')
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f)); sys.exit(1 if f else 0)
PY
```

```bash
cd /srv/work/Infra/iot/expresso && python3 testit/mains_freq.py --selftest > /tmp/d1.out 2>&1 && grep -qx "RESULT: 0 failed" /tmp/d1.out && grep -q "^DRIFT " /tmp/d1.out
```

```bash
cd /srv/work/Infra/iot/expresso && python3 testit/mains_freq.py testit/pcap-20260919-tasanne.log > /tmp/d2.out 2>&1 && grep -q "^DRIFT " /tmp/d2.out && grep -q "^MAINS 50.1 Hz" /tmp/d2.out
```

```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/classes.py pico/commands.py pico/functions.py pico/main.py testit/mains_freq.py | wc -l) -le 2990 && test $(wc -l < pico_dev.py) -le 300
```

## Report

Sama kuusirivinen muoto kuin briefissä, `iterations: 6`, ja `note:`-riville pidon toteutunut
kesto ja ajautuma vanhasta lokista.
