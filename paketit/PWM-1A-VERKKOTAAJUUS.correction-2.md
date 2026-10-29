# PWM-1A-VERKKOTAAJUUS — korjaus 2

Laiteajo 19.9.2026 onnistui ja antoi tuloksen `MAINS 50,1 Hz amp=1,788 bar conf=6,81`
(`testit/pcap-20260919-verkkotaajuus.log`). Mittaus siis toimii. Tämä korjaus koskee sitä, **miten
kaappaus käynnistetään**, ei sitä mitä se mittaa.

Budjettikatto on nostettu 2800 → 2880 riviin, jotta korjaus mahtuu ilman rivien tiivistämistä.
`may:`-lista on ennallaan; tällä kierroksella riittää `pico/functions.py` ja `pico/commands.py`.

## Vika — asettuminen on aikaohjattu, vaikka paine nousee omaa tahtiaan

`pressure_capture_run` odottaa kiinteät `asyncio.sleep_ms(1000)` ja aloittaa kaappauksen siitä
riippumatta, mikä paine on. Se on väärä muoto kahdesta syystä:

1. **Painetta ei ehdi nousta.** Ajossa 19.9.2026 tavoitteeksi oli sanottu noin 5 bar, ja
   `PCAP_END` palautti `pmax=3.68`. Yksi sekunti ei riitä, ja kaappaus itse kestää vain kaksi.
2. **Käyttäjä ei säädä painetta.** Hän säätää kuristinta; paine on seuraus. Kiinteä viive siirtää
   ajoitusvastuun ihmiselle, jolla ei ole siihen vipua — ja kellon pitäminen on tässä sekä
   tarpeetonta että mahdotonta.

Seuraus mittaukselle: väreilyn amplitudi pätee vain siinä paineessa, johon sattumalta ehdittiin,
eikä ajoja voi verrata keskenään.

## Korjaus — asettuminen paineohjatuksi

`pcap:<ms>[:<bar>]`. Uusi valinnainen kolmas kenttä on tavoitepaine. Asettumisvaihe ajaa pumppua
ja odottaa **tapahtumaa, ei kelloa**, ja päättyy ensimmäiseen näistä:

- paine saavuttaa tavoitteen (`reason=target`), kun tavoite on annettu;
- paine lakkaa nousemasta — nousu alle 0,05 bar 1,0 sekunnissa (`reason=plateau`). Tämä on myös
  oletus, kun tavoitetta ei anneta, joten oletuskäytös ei enää ole kiinteä viive;
- `PCAP_SETTLE_MAX_MS = 15000` täyttyy (`reason=timeout`);
- ylipaine, kytkin, `dev_safe` tai `pcap:stop` — nämä keskeyttävät koko ajon kuten ennenkin.

Asettumissilmukka on **ei-estävä**: `await asyncio.sleep_ms(0)` joka kierroksella, jotta
vahtikoiran ruokkija saa vuoron (`main.py:318-322`). Vain itse kaappaus estää, ja se on yhä 2 s.
11,0 barin kalibroitu katkaisu on voimassa myös asettumisen aikana.

Tulosta asettumisen tulos omalle rivilleen ennen `PCAP`-rivejä:

```text
PCAP_SETTLED bar=<paine> ms=<kesto> reason=<target|plateau|timeout>
```

`PCAP_START`-rivin `settle_ms=1000` korvataan muodolla `settle=<target|plateau>`, koska kiinteää
asettumisaikaa ei enää ole.

## Acceptance

Briefin neljä komentoa uudelleen, korjaus 1:n rakennetarkistus uudelleen, ja tämä:

```bash
cd /srv/work/Infra/iot/expresso && python3 - <<'PY'
import re, sys
src = open('pico/functions.py').read()
b = src[src.index('async def pressure_capture_run'):]
for m in ('\ndef ', '\nasync def '):
    if m in b: b = b[:b.index(m)]
f = []
if 'sleep_ms(1000)' in b: f.append('kiintea 1000 ms asettuminen on yha jaljella')
if 'PCAP_SETTLED' not in b: f.append('PCAP_SETTLED-rivia ei tulosteta')
if 'PCAP_SETTLE_MAX_MS' not in src: f.append('asettumisen aikakattoa ei ole')
for r in ('target', 'plateau', 'timeout'):
    if "'%s'" % r not in b and '"%s"' % r not in b: f.append('syy %s puuttuu' % r)
if 'pcap:' not in open('pico/commands.py').read(): f.append('pcap-haara kadonnut')
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f)); sys.exit(1 if f else 0)
PY
```

```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/classes.py pico/commands.py pico/functions.py pico/main.py testit/mains_freq.py | wc -l) -le 2880
```

## Report

Sama kuusirivinen muoto kuin briefissä, `iterations: 3`, `budget: <rivit>/2880`.
