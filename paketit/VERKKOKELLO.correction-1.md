# VERKKOKELLO — korjaus 1 (suunnittelija 23.9.2026)

Ensimmäinen kierros palasi vihreänä (kaikki 6 Acceptance-komentoa ja Budget, suunnittelija ajoi
itse uudelleen). Tarkistuksessa löytyi kolme vikaa. Vika 1 on briefin: `main.py` oli `must not`
-listalla, vaikka `vkello:<bar>` ei käynnisty laitteella ilman sen kyselyhaaraa. Toteuttaja kysyi
tästä oikein eikä muuttanut tiedostoa.

## Muutokset briefiin

- `may:`-listaan lisätään `Infra/iot/expresso/pico/main.py`. `pico/MANIFEST.json` pysyy kiellettynä.
- Budget: raja 4990 riviä, ja mukaan lasketaan `pico/main.py`. Mitattu `wc -l` ennen tätä korjausta: 4520 + 424 = 4944.

## Do

1. `pico/main.py`: lisää `take_pressure_clock_request()`-haara samalla mallilla kuin
   `take_pressure_gap_request()` (rivit 218-221): `from functions import pressure_clock_run` ja
   `await dev_run(pressure_clock_run(brew_data, utime, asyncio, target))`, perään `continue`.
2. `pressure_clock_run`, kaikki näytesilmukat: kun odotus on ohi, aikaleima luetaan todellisena
   hetkenä `now = utime.ticks_us()`, kuten `pressure_gap_run`:ssa (sen rivi `now = utime.ticks_us()`
   odotuksen jälkeen). Sitä käytetään `iq_add`-, `iq_ready`- ja `iq_close`-kutsuissa. Nyt
   `now = next_t` antaa `iq_close`:n ja `print`:n jälkeisille kiriminäytteille aikataulun mukaisen
   aikaleiman, vaikka ne luetaan myöhemmin, ja vaiheeseen tulee virhe.
3. `pressure_clock_run`: `PGAP_RUN_MAX_MS`-katto (`reason = 'timeout'`) tarkistetaan myös
   taukosarjan käynti- ja taukosilmukoissa, samassa `PSTEP_FEED_MASK`-kohdassa kuin muutkin vahdit.
   Nyt se tarkistetaan vain nousussa.
4. Aja alla oleva Acceptance ja Budget ja korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance

Sama kuin briefissä. Komennot 1–5 ovat ennallaan, ja komennot 6 ja 7 korvataan näillä:
```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "pico/(verkkokello|functions|commands|classes|main)\.py$|pico_dev\.py$|PICO-HALLINTA\.md$" | wc -l | grep -qx 0
```
```bash
cd /srv/work/Infra/iot/expresso && grep -q "take_pressure_clock_request" pico/main.py
```

## Budget
```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/verkkokello.py pico/functions.py pico/commands.py pico/classes.py pico/main.py pico_dev.py PICO-HALLINTA.md | wc -l) -le 4990
```

Stop ja Report kuten briefissä. Älä koske laitteeseen.
