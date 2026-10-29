# PWM-1B1-PHOLD — korjaus 1

Hyväksyntä oli vihreä, mutta se ei ajanut funktiota kertaakaan. Suunnittelija kirjoitti sen
jälkeen holdout-testin `testit/phold_smoke.py`, joka ajaa `pressure_hold_run`:n CPythonilla
valelaitteilla, ja se on punainen:

```text
FAIL normaali ajo nosti poikkeuksen: NameError("name 'SWITCH_BREW' is not defined")
```

Kaksi korjattavaa. Ensimmäinen on toteutuksen vika, toinen suunnittelijan briefin puute, joka
tässä korjataan samalla.

## Korjaus A — kytkimiä ei sidota

`pressure_hold_run` lukee `SWITCH_BREW/WATER/STEAM`, mutta funktio hakee vain
`brew_data.get_relays()`. Jokainen muu sama silmukka firmwaressa sitoo kytkimet erikseen
(`functions.py:343`, `557`, `873`). Ilman sitä komento kaatuu `NameError`iin heti ensimmäisellä
kierroksella — eli aina, laitteella.

Lisää funktion alkuun `SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM = brew_data.get_switches()` rivin
557 malliin.

## Korjaus B — PHOLD_END on tulostuttava myös poikkeuksessa

Nyt `PHOLD_END` tulostetaan vasta `finally`-lohkon jälkeen, joten korjauksen A vika olisi jäänyt
laitteella hiljaiseksi: isäntä `pico_dev.py phold` odottaa `PHOLD_END`-merkkiä ja olisi jäänyt
roikkumaan koko `<s> + 20` sekunnin aikakatkaisun ajaksi ilman mitään vihjettä syystä.

Siirrä `PHOLD_END`-tulostus `finally`-lohkoon releiden sammutuksen jälkeen, ja lisää silmukan
ympärille `except Exception: reason = 'error'`, joka **ei** nosta poikkeusta uudelleen — yksi
kehityskomento ei saa kaataa `main.py`:n silmukkaa. `PHOLD_END reason=error` on silloin se rivi,
joka kertoo isännälle, mitä tapahtui. `PCAP_END` ei tee näin, mutta `pcap` on enintään 2,5 s ajo
eikä isäntä jää sen varaan samalla tavalla.

## Files

may: sama lista kuin briefissä.

must not: **`Infra/iot/expresso/testit/phold_smoke.py`** — se on suunnittelijan holdout-todiste,
ei toteuttajan muokattava. Jos se on mielestäsi väärässä, sano se raportissa äläkä muuta sitä.

## Acceptance

Briefin neljä komentoa ennallaan, ja niiden lisäksi tämä:

```bash
cd /srv/work/Infra/iot/expresso && python3 testit/phold_smoke.py | tail -1 | grep -qx "RESULT: 0 failed"
```

```bash
cd /srv/work && git status --porcelain -- Infra/iot/expresso | grep -vE "(classes|functions|main|commands|pico_dev)\.py$|PICO-HALLINTA\.md$" | wc -l | grep -qx 0
```

## Report

Sama kuusirivinen muoto, `iterations` kasvaa yhdellä.
