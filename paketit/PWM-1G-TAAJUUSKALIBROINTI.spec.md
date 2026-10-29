# PWM-1G-TAAJUUSKALIBROINTI — spec

Ajonaikainen verkkotaajuuden ja vaiheen mittaus laitteella (TILAUS-F, -G, -H;
`KAYTTAJAN-TIEDOT.md` luku 2b). Holdout `testit/mcal_smoke.py` on mitta, ja se ajaa koodin
laitosmallia vasten: testi asettaa mallin verkkotaajuuden ja kysyy, löytääkö laite sen.

## 1. Rajaus

Tämä brief tekee **mittauksen ja sen komennon**. Kytkentä esiuuton paineennostoon on vaihe 1h,
ja TILAUS-G täyttyy vasta sen jälkeen. `pre_infusion`-korutiinia ei kosketa tässä.

## 2. Purkusykli (TILAUS-H)

Ennen mittausta ajetaan käyttäjän antama sykli sellaisenaan: magneettiventtiili päälle,
**0,5 s**, pois, **0,2 s**, toisto. Vakiot `MCAL_VENT_ON_MS = 500` ja `MCAL_VENT_OFF_MS = 200`.

Sykli päättyy, kun paine ei enää laske: kierroksen lopun ja edellisen kierroksen lopun erotus
alle `PCAP_PLATEAU_BAR` (0,15 bar). Tyhjästä järjestelmästä tämä täyttyy heti, joten sykli ajetaan
tasan kerran — erillistä "onko paineinen" -kynnystä ei ole eikä sellaista keksitä. Kierroksille ei
ole käyttäjän antamaa kattoa; koodiin jää vain karkausraja 200, jonka ylitys on vika eikä normaali
lopetus. Lopuksi:

```text
MAINSCAL_VENT cycles=<k> bar=<%.2f>
```

## 3. Mittaus

```python
async def mains_calibrate(brew_data, utime, asyncio, ms=2000)
```

1. Keskeytysehdot (`switch`, `dev_safe`, `mcal_abort`) tarkistetaan ennen yhtäkään relettä ja
   jokaisella näytteellä; este tulostaa `MAINSCAL_END reason=<syy>` eikä mittausta tehdä.
2. Purkusykli kohdan 2 mukaan.
3. Magneettiventtiili auki, pumppu päälle. Näytteitä `ms` kappaletta `PCAP_RATE_US`:n välein,
   sama busy-wait-ajoitus kuin `_pcap_capture`:ssa.
4. **Goertzel lasketaan virtaavana, ilman puskuria:** jokaiselle hilataajuudelle pidetään `s1`/`s2`
   ja päivitetään ne joka näytteellä. Muistia tarvitaan kaksi liukulukua taajuutta kohti, ei
   `array('H', n)` — mittaus ei siis rajoitu 2,5 sekuntiin kuten `pcap`.
5. Hila on `MCAL_GRID = [49.0 + 0.4*k for k in range(7)]` (49,0-51,4 Hz). Huippubinin ympäriltä
   paraabelin kärki antaa taajuuden; vaihe luetaan saman binin `re`/`im`:stä
   (`atan2(-im, re)`). `conf` on suurimman ja toiseksi suurimman amplitudin suhde.
6. Näytetaajuus lasketaan toteutuneesta kestosta (`n / dur_us`), ei nimellisestä — sama sääntö
   kuin `mains_freq.py`:ssä.
7. Tulos tallennetaan `brew_data`-kenttiin `mains_hz`, `mains_period_us` (= `1e6 / mains_hz`) ja
   `mains_phase_us`, ja tulostetaan:

```text
MAINSCAL f=<%.3f> phase_us=<%.0f> amp=<%.3f> conf=<%.2f> n=<n> ms=<kesto>
```

`finally`: pumppu pois, venttiili pois.

Mitattu tarkkuus (suunnittelijan kuivaharjoitus, laitosmalli, 2,0 s ikkuna): taajuus osuu
0,1 Hz:n sisään mallin arvosta kolmella eri taajuudella. Ikkunan pidentäminen parantaa tätä
suhteessa `T^1,5`, ja vaiheessa 1h ikkuna on koko paineennosto.

## 4. Komento ja jono

`mcal:<ms 500-5000>` ja `mcal:stop`. `classes.py` saa kentät `mcal_request` ja `mcal_abort` sekä
metodit `request_mains_calibration(ms)`, `take_mains_calibration_request()` ja
`abort_mains_calibration()` täsmälleen `pcap`-kolmikon mallin mukaan; `ms` rajataan
`min(5000, max(500, int(ms)))`. Kelvoton syöte hylkää koko pyynnön. `main.py` ajaa pyynnön
`pcap`- ja `psweep`-pyyntöjen vierestä samalla kolmen rivin kuviolla.

## 5. Mitä ei muuteta

`pcap`, `psweep`, `phold`, `pre_infusion`, kaukalovahti ja analysaattorit. Vanhat holdoutit
`psweep_smoke.py`, `psweep_mult_smoke.py`, `pskip_gate_smoke.py`, `phold_smoke.py` ja
`tray_guard_smoke.py` ovat tämän mitta.
