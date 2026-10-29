# EXPRESSO-KAUKALOVAHTI — spec

Suunnittelijan kirjoittama sisältö. Toteuttaja ei päätä näistä mitään.

## 0. Raja, joka ei liiku

Vahti koskee **kehitys- ja testikomentoja**: `phold` ja `pcap`. **Käyttäjän oma uutto
uuttokytkimellä ei saa katketa painoon** — vaa'alla on silloin kuppi, ja kupin paino on uuton
tarkoitus. `run_shot`:n kytkinpolku (`limit_weight=False`, `functions.py:152-154`) jää
koskemattomaksi, eikä tämä brief lisää sinne mitään. Käyttäjän sanoin 19.9.2026: "vaaka sääntö ei
koske omaa ajoa vaan testejä".

## 1. Kaksi moduulitason funktiota `functions.py`:hyn

```python
TRAY_STALE_MS = 2000     # lukema vanhentuneeksi; sama arvo kuin tshot-polulla (functions.py:159-161)


def tray_guard_start(brew_data, utime):
    """Ennen releiden kytkentää. Palauttaa (state, None) tai (None, '<syy>')."""


def tray_guard_check(brew_data, utime, state):
    """Ajon aikana. Palauttaa None tai '<syy>'."""
```

`state` kantaa alkupainon, viimeksi nähdyn `weight_ms`:n ja peräkkäisten ylitysten laskurin.

### `tray_guard_start` — syyt

| Syy | Ehto |
|---|---|
| `nolimit` | sekä `get_weight_limit()` että `get_weight_rise_limit()` ovat ≤ 0 |
| `noscale` | `get_weight()` on `None`, tai lukema on yli `TRAY_STALE_MS` vanha |

Kumpikin estää ajon **ennen kuin yhtään relettä kytketään**. Tämä on koko briefin ydin: ajo, joka
ei voi nähdä kaukaloa, ei ala.

### `tray_guard_check` — syyt

| Syy | Ehto |
|---|---|
| `scalelost` | lukema on `None` tai yli `TRAY_STALE_MS` vanha |
| `tray` | `weight >= wmax` kahdella peräkkäisellä **vaakanäytteellä** |
| `trayrise` | `weight - alkupaino >= wrise` kahdella peräkkäisellä vaakanäytteellä |

Raja, jonka arvo on ≤ 0, on pois käytöstä (toinen riittää, ks. `nolimit`).

"Kahdella peräkkäisellä näytteellä" tarkoittaa samaa kuin `tshot`-polulla (`functions.py:169-176`):
laskuria kasvatetaan vain kun `get_weight_ms()` on muuttunut, koska silmukka pyörii tuhat kertaa
nopeammin kuin vaaka ja telemetriassa on nähty yksittäisiä −16 g piikkejä.

## 2. Mihin vahti kytketään

| Kohta | Tarkistus |
|---|---|
| `pressure_hold_run` ennen releitä | `tray_guard_start` |
| `pressure_hold_run` joka kierros | `tray_guard_check` |
| `pressure_capture_run` ennen releitä | `tray_guard_start` |
| `pressure_capture_run` asettumissilmukka | `tray_guard_check` joka kierros |
| `pressure_capture_run` pitosilmukka | `tray_guard_check` joka kierros |
| `pressure_capture_run` kaappaussilmukka | **ei tarkistusta silmukan sisällä** — ks. alla |
| `pressure_capture_run` juuri ennen ja heti jälkeen kaappauksen | `tray_guard_check` |

**Miksi kaappaussilmukan sisällä ei tarkisteta.** Vaaka päivittyy omassa taskissaan
(`main.py:306-326`, `sleep_ms(20)`), joten lukema on tuore vain kun ajo antaa vuoron.
Asettumis- ja pitosilmukka antavat (`sleep_ms(0)`), kaappaussilmukka ei anna lainkaan — se
kiireodottaa 1000 µs välein. Siellä lukema jäätyisi määritelmän mukaan ja `scalelost` laukeaisi
joka kerta. Kaappaus on enintään 2500 ms, eli rajattu; tarkistus tehdään sen molemmin puolin.

## 3. Miten syy näkyy

Syy menee sellaisenaan olemassa olevaan lopetusriviin: `PHOLD_END reason=<syy> bar=<x.xx>` ja
`PCAP_END n=0 dur_us=0 pmax=0.00 reason=<syy>`. Uusia tulosterivejä ei lisätä. Kun `*_start`
estää ajon, releitä ei kytketä eikä `set_mode`-tilaa vaihdeta pumppaavaksi.

## 4. Mitä ei muuteta

`run_shot`, `tshot`-polku, ylipainerajat, kytkinehdot, `dev_safe`, vahtikoira ja `pcap`:n
portitus pysyvät ennallaan. Vahti on lisäys, ei uudelleenjärjestely: mikään olemassa oleva
keskeytysehto ei saa hävitä tai muuttua.
