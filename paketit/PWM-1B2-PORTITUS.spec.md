# PWM-1B2-PORTITUS — spec

Suunnittelijan kirjoittama sisältö. Toteuttaja ei päätä näistä mitään.

## 1. Vakiot (`functions.py`, `pcap`-luvun vakioiden joukkoon)

```python
PCAP_MAINS_US = 19960        # mitattu verkkojakso: 50,1 Hz kolmesta laiteajosta 19.9.2026.
                             # Oma vakionsa tarkoituksella — viiden 60 Hz -vakion yhdistäminen
                             # yhdeksi lähteeksi on vaihe 1a3, joka ajetaan vaiheen 1c kanssa.
PCAP_GATE_PERIOD_US = 2 * PCAP_MAINS_US   # joka toisen verkkojakson ohitus (paketin sääntö 6)
```

## 2. Portti on moduulitason puhdas funktio

```python
def pcap_gate(i, phase_us):
    """1 = pumppu päällä, 0 = ohitettu jakso, näytteen järjestysnumerolle i (paketin sääntö 6)."""
    return 1 if ((i * PCAP_RATE_US + phase_us) % PCAP_GATE_PERIOD_US) < PCAP_MAINS_US else 0
```

Se on erillinen funktio eikä silmukan sisään kirjoitettu lauseke, jotta isäntä ja holdout voivat
laskea saman portin. Älä käytä `utime`-ajastinta: portti johdetaan näytteen järjestysnumerosta,
koska juuri se tekee siitä isännällä uudelleenlaskettavan ilman lisädataa lokissa.

## 3. Missä porttia sovelletaan

Vain **kaappaussilmukassa** (`functions.py`, `for i in range(n)`), ei asettumisessa eikä
pitovaiheessa: kuristin säädetään ja paine saavutetaan täydellä pumpulla, ja vasta mittaus
portitetaan. Silmukassa kutsutaan `RELAY_PUMP.value(g)` vain kun `g` eroaa edellisestä arvosta.
Kaappauksen päätyttyä `finally` sammuttaa releet kuten ennenkin.

Kun `phase_us` on `None` (portitusta ei pyydetty), silmukka käyttäytyy **tavulleen kuten ennen**:
pumppu pysyy päällä koko kaappauksen, eikä `RELAY_PUMP.value()`:a kutsuta silmukassa lainkaan.

## 4. Komento ja `PCAP_START`

`pcap:<ms>[:<bar>[:<phase_us>]]`. Kolmas kenttä kytkee portituksen ja **vaatii toisen kentän**:
portitus ilman tavoitepainetta olisi mittaus tuntemattomasta tilasta. Arvo rajataan välille
`0 … PCAP_GATE_PERIOD_US - 1` (`% PCAP_GATE_PERIOD_US`). Se kulkee `brew_data`:lla samalla tavalla
kuin `pcap_target_bar`, kenttänimenä `pcap_gate_phase_us`; arvo nollataan `None`:ksi joka
pyynnöllä, myös `pcap:stop`:lla ja virheellisellä syötteellä — vanha vaihesiirto ei saa jäädä
voimaan seuraavaan ajoon.

`PCAP_START` saa uudet kentät. Ilman portitusta:

```text
PCAP_START rate=1000 n=<n> settle=<target|plateau> gain=<x.4f> offset=<x.3f> gate=off
```

Portitettuna:

```text
PCAP_START rate=1000 n=<n> settle=target gain=<x.4f> offset=<x.3f> gate=on period_us=39920 on_us=19960 phase_us=<p>
```

`gain` ja `offset` ovat anturin elävä kalibrointi (`brew_data.pressure_sensor`). Ne lisätään, koska
isäntäanalysaattorilla ei tähän asti ollut niitä lainkaan ja sen DRIFT-rivi luki noin barin liian
korkeana (avoin vika, rekisteri 19.9.2026).

## 5. Mitä ei muuteta

Asettumisen, pidon, keskeytysehtojen, `PCAP`-rivien ja `PCAP_END`:n muoto pysyy ennallaan.
`pcap:<ms>` ja `pcap:<ms>:<bar>` tuottavat saman ajon kuin ennen tätä briefiä, `PCAP_START`-rivin
uusia kenttiä lukuun ottamatta.
