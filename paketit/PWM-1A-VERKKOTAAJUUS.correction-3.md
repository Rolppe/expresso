# PWM-1A-VERKKOTAAJUUS — korjaus 3

Korjaus 2 teki asettumisesta tapahtumaohjatun, mikä oli oikea muoto. Mutta molemmat sen
lopetusehdot lukevat **yksittäisen raakanäytteen**, ja raakanäyte on tässä järjestelmässä
kelvoton päätöksentekoon. Budjettikatto 2880 → 2920. `may:` ennallaan; riittää
`pico/functions.py`.

## Mittaus, johon tämä korjaus nojaa

Laiteajosta 19.9.2026 (`testit/pcap-20260919-verkkotaajuus.log`, 2000 näytettä 1000,5 Hz:llä),
lineaarinen trendi poistettuna:

| Signaali | Hajonta (sd) |
|---|---|
| raaka anturi | **1,595 bar** |
| alipäästö τ = 0,2 s | 0,031 bar |
| alipäästö τ = 0,3 s | 0,034 bar |
| alipäästö τ = 1,0 s | 0,156 bar |

Yli 0,3 s:n aikavakiot alkavat seurata paineen omaa kaarevuutta eivätkä enää paranna.

## Vika 1 — tavoitetesti laukeaa kohinapiikistä

`if target is not None and bar >= target` vertaa raakanäytettä tavoitteeseen. Kun väreilyn
amplitudi on luokkaa 1,8 bar, ehto täyttyy heti kun **huippu** koskettaa tavoitetta — eli kun
keskiarvo on noin 1,8 bar sen alapuolella. Käyttäjän pyytämä 5 bar toteutuisi noin 3 barissa.

## Vika 2 — tasannetesti täyttyy puolella todennäköisyydellä heti

`(bar - plateau_bar) < PCAP_PLATEAU_BAR` vertaa kahta raakanäytettä sekunnin välein, eikä se ole
itseisarvo: **mikä tahansa lasku kelpaa tasanteeksi**. Kahden riippumattoman näytteen erotuksen
hajonta on noin 2,3 bar, joten ehto `< 0,05` täyttyy noin joka toisella tarkistuksella riippumatta
siitä, nouseeko paine. Asettuminen päättyisi siis käytännössä ensimmäisellä sekunnilla — eli
takaisin siihen kiinteään sekuntiin, joka oli korjauksen 2 alkuperäinen vika.

## Korjaus

1. Ylläpidä asettumissilmukassa yksinapaista alipäästöä `PCAP_FILT_TAU = 0.3` (s):
   `p_filt += (bar - p_filt) * min(1.0, dt / PCAP_FILT_TAU)`, missä `dt` on todellinen
   kierrosten väli sekunteina. Alusta se ensimmäisestä näytteestä.
2. **Molemmat lopetusehdot lukevat `p_filt`:iä**, eivät `bar`ia: `p_filt >= target`, ja tasanne
   `(p_filt - plateau_bar) < PCAP_PLATEAU_BAR`, missä `plateau_bar` on `p_filt` sekuntia aiemmin.
3. Nosta `PCAP_PLATEAU_BAR` arvoon `0.15`. Perustelu: suodatettu kohina on 0,034 bar, joten
   sekunnin välein otettujen suodatettujen arvojen erotuksen hajonta on noin 0,048 bar, ja 0,15 on
   sen kolminkertainen. Aito nousu on luokkaa bar sekunnissa, joten se ei osu kynnykseen.
4. **Ylipainekatkaisu pysyy raa'assa näytteessä** — se on turvaraja ja sen on reagoitava heti,
   ei suodattimen viiveellä. Sama koskee `pmax`:ia, joka raportoi huipun. Kirjoita tämä ero
   kommenttiin, jotta seuraava lukija ei "yhtenäistä" niitä.
5. `PCAP_SETTLED`-rivi raportoi suodatetun arvon, ja lisää sen perään raakahuipun:
   `PCAP_SETTLED bar=<p_filt> peak=<pmax> ms=<kesto> reason=<target|plateau|timeout>`.

## Acceptance

Briefin neljä komentoa, korjausten 1 ja 2 rakennetarkistukset, ja tämä:

```bash
cd /srv/work/Infra/iot/expresso && python3 - <<'PY'
import sys
src = open('pico/functions.py').read()
b = src[src.index('async def pressure_capture_run'):]
for m in ('\ndef ', '\nasync def '):
    if m in b: b = b[:b.index(m)]
settle = b[:b.index('if settled:')]
f = []
if 'PCAP_FILT_TAU' not in src: f.append('suodattimen aikavakiota ei ole')
if 'PCAP_PLATEAU_BAR = 0.15' not in src: f.append('tasannekynnys ei ole 0.15')
if 'p_filt >= target' not in settle: f.append('tavoitetesti ei kayta suodatettua arvoa')
if 'p_filt - plateau_bar' not in settle: f.append('tasannetesti ei kayta suodatettua arvoa')
if 'peak=' not in settle: f.append('PCAP_SETTLED ei raportoi raakahuippua')
if 'bar > PCAP_OVER_BAR' not in settle: f.append('ylipainekatkaisu ei ole raa\'assa naytteessa')
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f)); sys.exit(1 if f else 0)
PY
```

```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/classes.py pico/commands.py pico/functions.py pico/main.py testit/mains_freq.py | wc -l) -le 2920
```

## Report

Sama kuusirivinen muoto kuin briefissä, `iterations: 4`, `budget: <rivit>/2920`.
