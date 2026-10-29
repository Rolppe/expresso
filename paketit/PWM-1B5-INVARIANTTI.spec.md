# PWM-1B5-INVARIANTTI — spec

Pyyhkäisyn analysaattori: invariantti, vaihereferenssi ja taajuus (`paketit/PUMPPU-PWM.md`,
säännöt 9-12). Holdout `testit/psweep_fixture.py` on tämän spec:n mitta, ja se on kirjoitettu
ennen toteutusta.

## 1. `mains_freq.py` — Goertzelin vaihe käyttöön

Nykyinen `goertzel_amp` (`testit/mains_freq.py:78-89`) laskee `s1`/`s2` mutta heittää vaiheen
pois. Lisää funktio, joka palauttaa molemmat, ja jätä vanha kutsurajapinta ennalleen:

```python
def goertzel(x, fs, freq):
    """(amplitudi, vaihe radiaaneina) — vaihe on kosinin vaihe näytteen 0 hetkellä."""
    n = len(x); w = 2.0 * math.pi * freq / fs
    coeff = 2.0 * math.cos(w); s1 = s2 = 0.0
    for v in x:
        s0 = v + coeff * s1 - s2; s2, s1 = s1, s0
    re = s1 - s2 * math.cos(w); im = s2 * math.sin(w)
    return 2.0 * math.sqrt(max(0.0, re * re + im * im)) / n, math.atan2(-im, re)


def goertzel_amp(x, fs, freq):
    return goertzel(x, fs, freq)[0]
```

`goertzel_amp`:n paluuarvo ei saa muuttua yhdelläkään syötteellä: `pskip_delay.py` tuo sen
nimellä, ja `pskip_fixture.py` on sen mitta.

Lisää samaan tiedostoon hienohaku, jota pyyhkäisyn referenssisegmentit käyttävät:

```python
def refine_peak(x, fs, lo=49.0, hi=51.2, step=0.02):
    """Goertzel-haku askeleella `step` + paraabelin huippu kolmesta pisteestä; (freq, amp)."""
```

Signaali keskiarvoistetaan nollaan ennen hakua. Mitattu tarkkuus suunnittelijan synteettisellä
kokeella (2,0 s segmentti, amplitudi 0,30 bar, kohina sd 0,36 bar, 4 siementä): **|virhe| enintään
0,07 Hz**, eikä askeleen pienentäminen 0,1 → 0,02 Hz paranna sitä — raja on kohina, ei hila.

## 2. `testit/psweep_read.py` — uusi analysaattori

```text
python3 testit/psweep_read.py <sweep.log>    lukee pyyhkäisylokin, tulostaa PSWEEP_*/PSKIP_INV
python3 testit/psweep_read.py --selftest     synteettiset lokit, tulostaa RESULT: <n> failed
```

**2.1 Segmentointi.** `parse_segments(path)` jakaa lokin `PCAP_START`-riveittäin; jokaiselle
segmentille otsikkokentät, raakanäytteet ja `PCAP_END`-rivin `n`/`dur_us`/`reason`. Näytetaajuus
lasketaan segmentin omasta `n/dur_us`-suhteesta, ja bar-muunnos segmentin **omasta**
`gain`/`offset`-kentästä (`PCAP_RAW_A`/`PCAP_RAW_B` kuten `mains_freq.py`:ssä).

**2.2 Taitos.** Portitetuille segmenteille sama menettely kuin `pskip_delay.analyze`:ssa:
boxcar-jäännös portin jakson mittaisella ikkunalla (sääntö 8), taitos 40 biniin portin
nousevasta reunasta, huippubinin keskikohta `delay_ms`.

**2.3 Invariantti — säännön 9 korjattu muoto.** Raportoi

```text
PSKIP_INV phase_us=<p> delay_ms=<d> inv_ms=<v> amp=<bar> conf=<c> width_bins=<w>
```

missä `inv_ms = (delay_ms - p/1000) mod 19.96` — **modulus on verkkojakso `PCAP_MAINS_US`, ei
portin jakso**. Tämä on paketin säännön 9 korjaus: portti päästää läpi kokonaisen verkkojakson,
joten vaihesiirto siirtää mitattua viivettä verkkojakson tarkkuudella. Suunnittelijan mittaus
(synteettinen pyyhkäisy, viive 9,00 ms, 4 siementä): portin jakson modulolla hajonta on
20,2 ms eli mittaus näyttää rikkinäiseltä, verkkojakson modulolla 1,5 ms.
`width_bins` on taitoksen huipun leveys puolikkaalla korkeudella (bineinä).

**2.4 Referenssisegmentit ja taajuus.**

```text
PSWEEP_REF seg=<k> f=<Hz> amp=<bar> phase_deg=<0-360>
PSWEEP_MAINS f=<keskiarvo> spread=<suurin ero> from=ref n=<montako>
```

`f` kohdan 1 `refine_peak`:llä, `phase_deg` samasta taajuudesta `goertzel`:lla. `spread` on
rehellinen epävarmuus: sillä kerrotaan, riittääkö mittaus vaiheen 1c jaksonpituudelle.

**2.5 Yhteenveto.**

```text
PSWEEP_SEGS n=<segmenttejä> gated=<portitettuja> ref=<referenssejä> fs=<Hz>
PSWEEP_INV mean_ms=<ympyräkeskiarvo> spread_ms=<ympyrähajonta> n=<montako> verdict=<vakaa|hajoaa>
```

Keskiarvo ja hajonta lasketaan **ympyräsuureina** modulo verkkojakso (yksikkövektorien summa),
koska invariantti elää verkkojakson kehällä: 0,2 ms ja 19,8 ms ovat 0,4 ms päässä toisistaan,
eivät 19,6 ms. Raja `verdict=vakaa` on hajonta alle **3,0 ms**; se tulee suunnittelijan
mittauksesta: nimellisellä taajuudella hajonta on 0,4-1,5 ms ja 0,1 Hz:n taajuusvirheellä
0,8-4,5 ms. `conf` alle 2,0 sanotaan tulosteessa samalla säännöllä kuin `MAINS conf`.

**2.6 Torjunta.** Loki, jossa on alle kolme segmenttiä tai ei yhtään `gate=on`- tai
`gate=off`-segmenttiä, ei ole pyyhkäisy: tulosta `PSWEEP_NOSWEEP segments=<n>` ja palaa
epänollalla. Portitusta ei päätellä aaltomuodosta (PWM-1B3:n mitattu rajoitus).

## 3. Itsetesti (`--selftest`)

Rakentaa synteettiset pyyhkäisylokit ja tarkistaa neljä väitettä; tulostaa `RESULT: <n> failed`
ja palaa epänollalla, jos yksikin on punainen:

1. vakio viive → `PSWEEP_INV spread_ms` alle 3,0;
2. viive 9 ms → 14 ms siirtää `mean_ms`:ää 5 ms (±2 ms);
3. taajuusvirhe 0,1 Hz kasvattaa `width_bins`-keskiarvoa;
4. yksisegmenttinen `pcap`-loki → `PSWEEP_NOSWEEP`, paluuarvo epänolla.

## 4. Mitä ei muuteta

`pskip_delay.py`:n tuloste ja rajapinta pysyvät ennallaan — `psweep_read.py` saa tuoda siitä
funktioita, muttei muuttaa niiden käyttäytymistä. `pskip_fixture.py` ja `pskip_gate_smoke.py`
ovat tämän mitta.
