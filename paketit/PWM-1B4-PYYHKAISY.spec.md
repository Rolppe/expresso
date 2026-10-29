# PWM-1B4-PYYHKAISY — spec

Vaihesiirtopyyhkäisy yhtenä laitekomentona (`paketit/PUMPPU-PWM.md`, säännöt 10 ja 13).
Suunnittelija on kirjoittanut holdoutin `testit/psweep_smoke.py`; se on tämän spec:n mitta.

## 0. Yhteiset apurit ennen uutta komentoa

**0.1** `functions.py`: irrota `pressure_capture_run`:n asettumis- ja pitovaihe omaksi
korutiinikseen

```python
async def pcap_settle(brew_data, utime, asyncio, sensor, gain, offset, target, tray_state)
```

joka palauttaa `(settled, reason, p_filt)`. Siirto on mekaaninen: samat vakiot, samat
keskeytysehdot, sama `PCAP_SETTLED`-tuloste, sama `await asyncio.sleep_ms(0)` joka kierroksella.
`pressure_capture_run` kutsuu sitä eikä muuta käyttäytymistään millään tavalla — holdoutit
`pskip_gate_smoke.py`, `phold_smoke.py` ja `tray_guard_smoke.py` ovat tämän mitta.

**0.2** `functions.py`: uusi vakio `TRAY_RESYNC_MS = 300` ja korutiini

```python
async def tray_guard_recheck(brew_data, utime, asyncio, state)
```

joka antaa vuoron (`await asyncio.sleep_ms(0)`), odottaa `brew_data.get_weight_ms()`-arvon
muuttumista enintään `TRAY_RESYNC_MS` (`await asyncio.sleep_ms(10)` odotuskierroksella) ja kutsuu
vasta sitten `tray_guard_check`:n. Kaappauksen jälkeinen tarkistus sekä `pressure_capture_run`:ssa
että pyyhkäisyssä käyttää tätä. **Tämä on avoimen vian korjaus:** kaappaussilmukka ei anna vuoroa,
joten lukema on sen jälkeen aina yli `TRAY_STALE_MS` vanha ja portitettu ajo päättyi joka kerta
syyhyn `scalelost`. Ennen kaappausta tehtävä tarkistus pysyy suorana `tray_guard_check`-kutsuna.

## 1. Vakiot ja vaihesiirrot

```python
PSWEEP_N_DEFAULT = 5         # vaihesiirtojen määrä, kun kenttää ei anneta (sääntö 10)
PSWEEP_N_MAX = 8
PSWEEP_TRIM_BAR = 0.3        # kuollut alue tavoitteen ympärillä (sääntö 13)
PSWEEP_TRIM_MS = 8000        # trimmausaskeleen enimmäiskesto
PSWEEP_TRIM_PRINT_MS = 500   # ei omaa tulostetta askeleen aikana; yksi rivi lopuksi


def psweep_phases(n):
    """Tasavälein portin jakson yli, ensimmäinen 0 (sääntö 10)."""
    return [k * PCAP_GATE_PERIOD_US // n for k in range(n)]
```

## 2. Ajon rakenne

`async def pressure_sweep_run(brew_data, utime, asyncio, ms)`:

1. Lue `target = getattr(brew_data, 'psweep_target_bar', None)` ja
   `n = getattr(brew_data, 'psweep_n', None) or PSWEEP_N_DEFAULT`, samalla tavalla kuin
   `pressure_capture_run` lukee `pcap_target_bar`:n.
2. Tulosta ensimmäisenä rivinä
   `PSWEEP_START segs=<n+2> n=<n> ms=<ms> target=<%.2f> period_us=<PCAP_GATE_PERIOD_US> on_us=<PCAP_MAINS_US>`.
3. Kytkimet, `dev_safe` ja `tray_guard_start` tarkistetaan ennen yhtäkään relettä, samassa
   järjestyksessä kuin `pressure_capture_run`:ssa. Este lopettaa ajon heti rivillä
   `PSWEEP_END segs=0 dur_ms=0 reason=<switch|devsafe|noscale|nolimit|...>` eikä tulosta
   yhtään `PCAP_START`-riviä.
4. Asettuminen kerran: `pcap_settle(...)` tavoitteeseen `target`. Jos se ei asetu, ajo päättyy
   `PSWEEP_END`-riville sen syyllä.
5. Segmentit järjestyksessä `seg=0` (referenssi, portitus pois), `seg=1..n`
   (vaihesiirrot `psweep_phases(n)` järjestyksessä), `seg=n+1` (referenssi). Jokainen segmentti
   on `ms` näytettä `PCAP_RATE_US`:n välein, kaappaussilmukka sellaisenaan kuten
   `pressure_capture_run`:ssa (sama keskeytysehtojen joukko, sama `pcap_gate`-kutsu, sama
   ylipaineraja `PCAP_OVER_BAR`).
6. Segmenttien **väliin** — ei ennen ensimmäistä eikä viimeisen jälkeen — trimmausaskel kohdan 4
   mukaan.
7. `finally`: pumppu pois, magneettiventtiili pois, `set_mode('IDLE')`,
   `brew_data.psweep_abort = False`. Viimeinen rivi on aina
   `PSWEEP_END segs=<tulostettujen segmenttien määrä> dur_ms=<asettumisen jälkeinen kesto>
   reason=<ok|switch|devsafe|stop|overpressure|scalelost|tray|trayrise>`.
8. Ensimmäinen este segmentin sisällä lopettaa koko pyyhkäisyn: keskeneräiseltä segmentiltä
   tulostetaan sen omat `PCAP`-rivit ja `PCAP_END` syyllä, sitten `PSWEEP_END` samalla syyllä.

## 3. Segmentin tuloste — jokainen segmentti on kelvollinen pcap-loki

```text
PCAP_START rate=1000 n=<ms> settle=target gain=<%.4f> offset=<%.3f> seg=<k> gate=off
PCAP_START rate=1000 n=<ms> settle=target gain=<%.4f> offset=<%.3f> seg=<k> gate=on period_us=39920 on_us=19960 phase_us=<p>
PCAP <idx> <t_us> <v0> ... <v19>
PCAP_END n=<count> dur_us=<d> pmax=<%.2f> seg=<k> reason=<...>
```

`<idx>` ja `<t_us>` alkavat jokaisessa segmentissä nollasta. Kenttien nimet ja järjestys ovat
`pressure_capture_run`:n kanssa yhteensopivat, jotta `mains_freq.parse_log` lukee yksittäisen
segmentin sellaisenaan (`testit/mains_freq.py:parse_log` nollaa tilan joka `PCAP_START`-rivillä).
Rivit tulostetaan segmentin päätyttyä samalla silmukalla kuin `pressure_capture_run`:ssa, ja
vuoro annetaan vahtikoiralle joka kymmenennellä rivillä.

## 4. Trimmausaskel (sääntö 13)

Pumppu ja magneettiventtiili ajetaan niin, että paine palaa tavoitteeseen:

- `p_filt > target + PSWEEP_TRIM_BAR`: pumppu pois, magneettiventtiili auki;
- `p_filt < target - PSWEEP_TRIM_BAR`: pumppu päälle portittamatta, venttiili kiinni;
- muuten askel päättyy heti syyllä `ok`.

Suodatin on sama yksinapainen `PCAP_FILT_TAU`-suodin kuin asettumisessa, alkuarvona segmentin
viimeinen lukema. Askel antaa vuoron joka kierroksella (`await asyncio.sleep_ms(2)`), tarkistaa
kytkimet, `dev_safe`, `psweep_abort` ja `tray_guard_check`:n, ja päättyy kun paine on kuolleessa
alueessa, kun `PSWEEP_TRIM_MS` täyttyy (`reason=timeout`) tai esteeseen (sen oma syy). Lopuksi
venttiili suljetaan, pumppu kytketään päälle ja tulostetaan

```text
PSWEEP_TRIM seg=<edellisen segmentin k> bar=<%.2f> ms=<kesto> reason=<ok|timeout|switch|devsafe|stop|scalelost|tray|trayrise>
```

`timeout` **ei** lopeta pyyhkäisyä — se on mittausolosuhde, ei vika, ja se näkyy lokissa.
Muu syy kuin `ok` tai `timeout` lopettaa pyyhkäisyn kohdan 2.8 mukaan.

## 5. Komento ja jono

`commands.py`, `pcap:`-haaran vieressä:

```text
psweep:<ms 200-2500>:<bar>[:<n 2-8>] | psweep:stop
```

Toinen kenttä on pakollinen: ilman tavoitepainetta portitus mittaisi tuntemattomasta tilasta
(sama perustelu kuin `pcap`:n kolmannella kentällä). Puuttuva tai kelvoton kenttä ei jätä
vanhaa arvoa voimaan — `psweep_target_bar` ja `psweep_n` nollataan `None`:ksi jokaisella
pyynnöllä, myös `psweep:stop`:lla ja virheellisellä syötteellä.

`classes.py`: `psweep_request`, `psweep_abort`, `psweep_target_bar`, `psweep_n` alustetaan
`pcap`-kenttien viereen, ja niille kirjoitetaan `request_pressure_sweep(ms)`,
`take_pressure_sweep_request()` ja `abort_pressure_sweep()` täsmälleen `pcap`-kolmikon mallin
mukaan (`classes.py:478-489`): `ms` rajataan `min(2500, max(200, int(ms)))`, `n` rajataan
`min(PSWEEP_N_MAX, max(2, int(n)))` komennossa.

`main.py`: `pcap`-pyynnön vieressä (`main.py:189-196`) sama kolmen rivin kuvio pyyhkäisylle.

## 6. Isäntä

`pico_dev.py`: `psweep <ms>:<bar>[:<n>] [out.log]`, joka lähettää `CMD psweep:<...>` ja kaappaa
rivit `PSWEEP_END`-riviin asti — sama kuvio kuin `pcap()` (`pico_dev.py:180-198`), mutta
lopetusehto on `PSWEEP_END` ja aikakatkaisu vähintään 180 s (pyyhkäisy on seitsemän segmenttiä
ja kuusi trimmausaskelta). Käyttöohjerivi ja `PICO-HALLINTA.md`:n luvun 4 taulukko päivitetään.
