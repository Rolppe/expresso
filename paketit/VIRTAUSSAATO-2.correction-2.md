# VIRTAUSSAATO-2 — korjaus 2

Analyysisi on oikea ja arvokas: eristit vian ohittamalla säätimen kokonaan ja syöttämällä ihanteen
vakiodutyn. Jäljelle jäävä heilunta on sisemmän ikkunan aaltoilua, ei virityksen puutetta. Vika on
kuitenkin väitteessä, ei ikkunassa.

## K2 — väite 1 mitataan virtauksen 1,0 s liukuvasta keskiarvosta

`flow_true = k · p` on hetkellinen suure, ja paine aaltoilee jokaisen 100 ms kytkentäikkunan
sisällä. Mitä suurempi `k`, sitä suoremmin aaltoilu näkyy virtauksessa — juuri niin kuin mittasit.
Mutta **hetkellinen virtaus ei ole se suure, jota kukaan säätää tai havaitsee**: oikea pumppu on
iskupumppu, joka työntää vettä 60 Hz:n sykäyksinä, vaaka näytteistää 11,6 Hz ja virtauslukema on
pienimmän neliösumman suora 1,0 s ikkunassa. Kupissa ja lokissa näkyy keskiarvo, ei sykäys.

Korvaa luvun 4 väite 1 tällä:

> 1. Jokaisessa saavutettavassa vaiheessa (`k` = 0,50 / 0,50 / 1,5 / 3,0) virtauksen **1,0 s
>    liukuva keskiarvo** on ±0,3 g/s sisällä tavoitteesta 2,0 s kuluttua muutoksesta vaiheen
>    loppuun asti. Keskiarvo lasketaan `flow_true`-sarjasta samalla 1,0 s ikkunalla, jota vaa'an
>    oma estimaattori käyttää.

Muut väitteet (paine ≤ 12,0 bar, `fsat`, regressio) pysyvät hetkellisinä — ne ovat rajoja, eivät
tarkkuusvaatimuksia.

## K3 — `window_ms` ja `step_ms` pysyvät koskemattomina

Vastaus kysymykseesi on ei, eikä leventäminen olisi edes oikea suunta: `step_ms = 17` on yksi
60 Hz verkkojakso eli pumpun yksi isku, ja `window_ms = 100` on nykyinen viritetty käytös, jota
tämä paketti ei kyseenalaista. Ikkunan leventäminen kasvattaisi aaltoilua ja lyhentäminen veisi
dutyn erotuskyvyn. Aaltoilu kuuluu tähän laitteeseen; se suodattuu mittauksessa ja kupissa.

## Ei muuta

Viritys (`kp`, `ki`) haetaan uudelleen korjatun väitteen 1 kanssa, ja kahden yrityksen sääntö
lasketaan tästä korjauksesta alkaen. Budjetti, `may:`-lista ja Acceptance-komennot ennallaan.
