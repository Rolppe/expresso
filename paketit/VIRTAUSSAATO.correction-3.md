# VIRTAUSSAATO — korjaus 3

Ajoin simulaation itse: `fsat` nousee 29,34 s eli hyvin määräajan sisällä — punaisena on
`stays 1 to the end`. Toteuttajan diagnoosi pitää: yksittäinen kohinainen virtauslukema osuu
0,1 g/s päähän tavoitteesta, ehto menee hetkeksi epätodeksi ja nollaa `sat_ms`:n.

**Tämä ei ole simulaation vika vaan firmwaren.** Vaa'an kohina on laitteessa sama 0,25 g
(`KEHITYSYHTEYS.md:747-749`), joten lippu välkkyisi lokissa täsmälleen samoin oikeassa uutossa.
Tilalipun kuuluu olla tahmea; minä kirjoitin sen hetkellisenä ehtona. Korjaus 1:n kohta 10 oli
siis oikeassa suureessa mutta väärässä muodossa.

## K7 — `sat_ms` on vuotava laskuri ja `saturated` Schmitt-liipaisin

Korvaa luvun 1 kohta 10 tällä:

> 10. Saturaatio mitataan paineesta yhdellä vuotavalla laskurilla. Ehto on
>     (`pressure >= p_max - 0.5` **ja** `e > 0.1`) tai (`pressure <= p_min + 0.5` **ja** `e < -0.1`).
>     Ehdon ollessa tosi `sat_ms += dt*1000`, epätotena `sat_ms -= 0.5 * dt*1000`; rajaa `sat_ms`
>     aina välille `[0, 2000]`. `self.saturated` nousee `True`ksi kun `sat_ms >= 2000` ja palaa
>     `False`ksi vasta kun `sat_ms <= 0`; niiden välissä se **säilyttää edellisen arvonsa**.

Yksittäinen kohinapiikki maksaa siis 50 ms kertymää eikä nollaa mitään, ja lipun laskeminen vaatii
4,0 s yhtäjaksoista rauhaa. Nousuun tarvitaan yhä 2,0 s nettoa.

## K8 — määräaika 6,0 s → 6,5 s, kohinatermi mukaan johdettuna

Korjauksen 2 johdossa oli termi, jonka oletin nollaksi: kohinan aiheuttamat katkot dwell-ajan
aikana. Budjetti: noin 10 % näytteistä putoaa ehdon ulkopuolelle, ja puolen nopeuden vuoto tekee
siitä `0,1 × 2,0 s × 2 = 0,4 s`. Kokonaisuus: rampitus 2,55 s + dwell 2,0 s + sisemmän silmukan
viive ~0,8 s + kohina 0,4 s ≈ 5,75 s. Väite 3 saa määräajakseen **6,5 s**; loput siitä säilyy
sanasta sanaan, `stays 1 to the end` mukaan lukien — hystereesin jälkeen se on aito vaatimus.

## Ei muuta

Älä viritä `kp`/`ki`/`rate_bar_s`-arvoja, älä koske muihin väitteisiin, `may:`-listaan,
Acceptance-komentoihin tai budjettiin. Aja Acceptance ja Budget läpi ja raportoi kuusi riviä.
