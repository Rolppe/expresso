# PWM-1B6-PORTTIJAKSO — spec

Portin jakso mittausparametriksi (`paketit/PUMPPU-PWM.md`, sääntö 14) ja tuomio viiveen
hajonnasta. Holdoutit `testit/psweep_mult_smoke.py` ja `testit/psweep_fixture.py` ovat mitta.

## 1. Vakiot ja portin kaava

```python
PSWEEP_MULT_DEFAULT = 2      # portin jakso verkkojaksoina; 2 = entinen 1-paalla-1-pois
PSWEEP_MULT_MAX = 16


def pcap_gate(i, phase_us, period_us=None):
    """1 = pumppu päällä. Päälläolo on aina yksi verkkojakso; `period_us` päättää, kuinka
    pitkään portti on sen jälkeen kiinni (sääntö 14)."""
    p = PCAP_GATE_PERIOD_US if period_us is None else period_us
    return 1 if ((i * PCAP_RATE_US + phase_us) % p) < PCAP_MAINS_US else 0


def psweep_phases(n, period_us=None):
    p = PCAP_GATE_PERIOD_US if period_us is None else period_us
    return [k * p // n for k in range(n)]
```

Oletusarvot pitävät entisen käyttäytymisen sanatarkasti: `pcap_gate(i, phase)` ilman kolmatta
kenttää on sama funktio kuin ennen, ja `pressure_capture_run` (`pcap:`) ei muutu lainkaan.

## 2. Ajo

`pressure_sweep_run` lukee `mult = getattr(brew_data, 'psweep_mult', None) or PSWEEP_MULT_DEFAULT`
ja laskee `period_us = mult * PCAP_MAINS_US`. Sitä käytetään portitukseen, vaihesiirtoihin ja
otsikoihin. Tulosteet saavat yhden uuden kentän:

```text
PSWEEP_START segs=<n+2> n=<n> ms=<ms> target=<bar> period_us=<p> on_us=19960 mult=<m>
PCAP_START ... seg=<k> gate=on period_us=<p> on_us=19960 phase_us=<v> mult=<m>
```

Referenssisegmenttien (`gate=off`) otsikko ei muutu. Trimmausaskel, kaukalovahti ja
keskeytysehdot pysyvät ennallaan.

## 3. Komento ja jono

`psweep:<ms 200-2500>:<bar>[:<n 2-8>[:<mult 2-16>]]`. Kerroin rajataan
`min(PSWEEP_MULT_MAX, max(2, int(float(kentta))))`, ja `psweep_mult` nollataan `None`:ksi
jokaisella pyynnöllä samalla tavalla kuin `psweep_n` — myös `psweep:stop`:lla ja kelvottomalla
syötteellä, jolloin **koko pyyntö hylätään** eikä ajoa jonouteta. `classes.py` saa kentän
`psweep_mult` `psweep_n`:n viereen.

`pico_dev.py`: `psweep <ms>:<bar>[:<n>[:<mult>]]`, käyttöohjerivi ja `PICO-HALLINTA.md`:n luvun 4
taulukko päivitetään.

## 4. Analysaattorin tuomio

`psweep_read.py`:n yhteenvetorivi saa kaksi kenttää, ja tuomio luetaan niistä:

```text
PSWEEP_INV mean_ms=<inv, ympyrakeskiarvo> spread_ms=<inv-hajonta> delay_mean_ms=<d> delay_spread_ms=<s> n=<k> verdict=<vakaa|hajoaa>
```

`delay_mean_ms` ja `delay_spread_ms` lasketaan `delay_ms`-arvoista ympyräsuureina **segmentin oman
`period_us`:n yli** (ei verkkojakson). `verdict` on `vakaa`, kun
`delay_spread_ms <= 1.5 * (period_us / 40 / 1000)` eli puolitoista taitosbiniä, muuten `hajoaa`.
`mean_ms`/`spread_ms` jäävät riville kirjanpidoksi iskunvalintamallista.

Kynnys on mitattu, ei arvattu: suunnittelijan kuivaharjoitus kolmella siemenellä portin jaksolla
8 x 19,96 ms antoi ympyrähajonnaksi 3,6-4,7 ms, kun binin leveys on 3,99 ms.

## 5. Mitä ei muuteta

`pcap:`-komento ja `pressure_capture_run`, trimmausaskel, kaukalovahti, `pskip_delay.py` ja
`mains_freq.py`. Vanhat holdoutit `psweep_smoke.py`, `pskip_gate_smoke.py`, `phold_smoke.py`,
`tray_guard_smoke.py` ja `pskip_fixture.py` ovat tämän mitta.
