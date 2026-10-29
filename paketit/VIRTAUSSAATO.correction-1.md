# VIRTAUSSAATO — korjaus 1

Vika on spesifikaatiossa, ei toteutuksessa. Ajoin `testit/flow_ctrl_sim.py`:n itse: 3 väitettä
punaisena, ja kaksi niistä on mahdotonta täyttää speksin omilla määrittelyillä. Korjaus kumoaa
ne kohdat `paketit/VIRTAUSSAATO.spec.md`:stä. Kaikki muu spesifikaatiossa pysyy voimassa.

## K1 — saturaation tunnistus mitataan paineesta, ei asetusarvosta

Speksin luvun 1 kohta 10 sitoi `fsat`-lipun siihen, että **asetusarvo** `sp` yltää `p_max`:iin.
Luvun 1 kohta 8 (etäisyysraja `lead`) estää sen: `sp` on aina ≤ `pressure + 0.8`, joten sisemmän
silmukan heilahdus katon tuntumassa katkaisee `sat_ms`-laskennan ennen kahta sekuntia. Lippu mittasi
väärää suuretta: kyse ei ole siitä, mihin säädin pyytää, vaan siitä, että **paine on katossa ja
virtaus jää silti tavoitteesta**.

Korvaa luvun 1 kohta 10 tällä:

> 10. Saturaatio mitataan paineesta. Jos `pressure >= p_max - 0.5` **ja** `e > 0.1` (virtaus jää
>     tavoitteesta), tai `pressure <= p_min + 0.5` **ja** `e < -0.1` (virtaus yli tavoitteen),
>     kasvata `sat_ms += dt*1000`, muuten `sat_ms = 0`; `self.saturated = sat_ms >= 2000`.

## K2 — paineväite koskee turvamarginaalia ja asettumista, ei transienttia

Luvun 6 väite 2 (`p` ≤ 11,0 bar aina) oli mielivaltainen: se rankaisi katon ylityksestä
transientissa, jonka mikään sallituista viritysarvoista ei poista, ja oli siksi suorassa
ristiriidassa väitteen 1 kanssa. Todellinen turvaraja on firmwaren oma 13,0 bar katkaisu
(`functions.py:148-151`). Korvaa väite 2 tällä:

> 2. `p` ei ylitä **12,0 bar** missään kohtaa (eikä siten lähesty 13,0 bar katkaisua), ja
>    saavuttamattoman tavoitteen vaiheessa paine asettuu välille `p_max ± 0.5` viimeistään 6,0 s
>    kuluttua muutoksesta ja pysyy siellä vaiheen loppuun.

## K3 — `fsat`-ikkuna 3,0 s → 5,0 s, ajo 32 s → 34 s

Väitteen 3 ikkuna oli fysikaalisesti mahdoton: paineen on ensin noustava 4,4 barista katolle ja
vasta sitten `sat_ms` kerää kaksi sekuntia. Korvaa väite 3 tällä, ja pidennä ajo 34 sekuntiin
(viimeinen vaihe 24–34 s):

> 3. Viimeisessä vaiheessa `fsat` on 1 viimeistään **5,0 s** kuluttua muutoksesta ja pysyy 1:nä
>    vaiheen loppuun, ajo jatkuu loppuun asti eikä paine ylitä 12,0 bar.

## K4 — viritysvara

Kohdan 7 viritys aloitetaan uudelleen näiden väitteiden kanssa. Arvot `kp=0.55, ki=2.0,
rate_bar_s=2.2`, jotka jo täyttivät väitteen 1, ovat kelvollinen lähtökohta. `p_min`, `p_max` ja
`lead` pysyvät jäädytettyinä.

## K5 — rivibudjetti 2370 → 2430

Budjetti oli täynnä rivilleen (2370/2370), eikä korjaus mahtuisi siihen. Uusi `## Budget`-komento:

```bash
cd /srv/work/Infra/iot/expresso && test $(cat pico/classes.py pico/functions.py pico/commands.py pico/main.py testit/flow_ctrl_sim.py | wc -l) -le 2430
```

## Stop

Ennallaan, paitsi että väitteen 1 kahden yrityksen sääntö lasketaan tästä korjauksesta alkaen
uudelleen. Jos jokin näistä kolmesta väitteestä on yhä mahdoton, kysy yksi kysymys ja lopeta —
älä löysää väitettä itse.
