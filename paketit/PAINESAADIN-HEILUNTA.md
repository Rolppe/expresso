# EXPRESSO-PAINESAADIN-HEILUNTA — pumpun ylireagointi kuriin

| Kenttä | Arvo |
|---|---|
| Tunnus | EXPRESSO-PAINESAADIN-HEILUNTA |
| Skooppi | infra iot |
| Havainto | käyttäjä 19.9.2026: "tuo heilunta ja ylireagointi pumpulta on saatava kuriin" |
| Tila | suunniteltu, ei toteutettu |

## Mitattu tila

Kaikki tämän päivän pidot samalla tavoitteella 8,0 bar:

| Ajo | keskiarvo | hajonta | min | max |
|---|---|---|---|---|
| Lukittu linja, PI-pito | 8,32 | — | 7,17 | 10,30 |
| Virtaava 0,88 g/s | 8,19 | 0,69 | 6,4 | 11,2 |
| Virtaava 0,65 g/s, korjattu asteikko | 8,10 | 0,56 | 6,8 | 10,6 |

Keskiarvo osuu tavoitteeseen hyvin; **hajonta on ongelma**. Käyttäjän mekaaninen mittari näytti
samassa ajossa noin 1,0 barin liikettä, kun anturi näytti 3,6 — osa on siis anturin kohinaa, mutta
ei kaikki.

## Todennäköinen juurisyy: dutyn kvantisointi

`PumpPressureController` ajaa dutya aikasuhteisena 100 ms ikkunassa 17 ms askelin
(`classes.py:669`, yksi 60 Hz verkkojakso eli yksi pumpun isku). Sovellettava on-aika on
`int(duty·100/17 + 0,5)·17`, joten **mahdollisia dutyja on vain 0, 0,17, 0,34, …**

Pidossa tarvittava duty on mitattu **0,13–0,14**. Se osuu tasan kahden askeleen väliin: säädin
vuorottelee arvojen 0,17 (yksi isku) ja 0,00 (ei iskua) välillä, ja paine nousee ja laskee sen
mukana. Rajasykli ei siis synny virityksestä vaan erotuskyvystä — `kp`, `ki` tai `ff` eivät voi
sitä poistaa.

## Korjausehdokkaat, halvin ensin

1. **Pidempi ikkuna.** `window_ms` 100 → 300 antaa askeleen 17/300 = 0,057, eli kolminkertaisen
   erotuskyvyn samalla iskukoolla. Hinta: hitaampi vaste häiriöön, mikä uutossa tuskin haittaa.
2. **Ikkunan liukuva jako (dither).** Vuorotellaan tietoisesti 0 ja 1 iskun ikkunoita niin, että
   *keskimääräinen* duty osuu haluttuun — sama idea kuin sigma-delta-modulaatiossa. Ei muuta
   laitteistoa, mutta vaatii tilan säilyttämisen ikkunoiden yli.
3. **Integraalin hidastus** vain siltä osin kuin se vahvistaa rajasykliä; ei poista syytä.

Mittaustapa on valmis: aja `tshot:35` kiinteällä venttiilin asennolla ja vertaa hajontaa ja
min/max-arvoja yllä olevaan taulukkoon. Vertailukelpoisuuden vuoksi virtaus on kirjattava samalta
ajolta, koska hajonta riippuu siitä.

## Rajaus

Tämä on **uuttovaiheen painesäädin**, ei kalibrointiajon oma annostelu (`PCAL-KORJAUS`) eikä
virtaussäätö (`VIRTAUSSAATO-2`). Ne käyttävät samaa luokkaa, joten korjaus vaikuttaa kaikkiin
kolmeen — se on syy tehdä se omana pakettinaan eikä minkään niistä sivutuotteena.
