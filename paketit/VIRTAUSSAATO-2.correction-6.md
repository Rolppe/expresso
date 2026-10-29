# VIRTAUSSAATO-2 — korjaus 6

Ajosi pysähtyi kesken yön; tarkistin levyn ja ajoin simulaation itse. Korjaus 5 on toteutettu
oikein ja **vain yksi väite on punaisena**: `fsat` on 1 aloitusvaiheen kolmen viimeisen sekunnin
ajan. Se on minun väitteeni aritmeettinen mahdottomuus, ei toteutuksen vika.

## K11 — väite 6 ei koske aloitusvaihetta, ja tilalle tulee myönteinen väite

Aloitusvaiheessa virtaus lähtee nollasta: tavoite **ei todella täyty**, joten lipun kuuluukin
nousta. Sen jälkeen asettuminen vie johdetut 5,0 s (korjaus 3) ja lipun laskeminen puolen nopeuden
vuodolla vielä 4,0 s — yhteensä 9,0 s vaiheessa, jonka pituus on 8,0 s. Väite ei voi toteutua
millään virityksellä.

Muuta luvun 4 väite 6 koskemaan **vain venttiilimuutosvaiheita** (16 s, 26 s, 35 s) ja lisää
aloitusvaiheelle oma väite:

> 7. Aloitusvaiheessa `fsat` on 1 jossakin kohtaa ensimmäisen 5,0 s aikana: virtaus lähtee
>    nollasta, tavoite ei täyty, ja lipun on kerrottava se.

Näin aloitusvaihetta ei vapauteta tarkastuksesta vaan sille asetetaan oikea vaatimus: lippu ei saa
vaieta silloin kun kone ei todella anna tavoitetta.

## K12 — `check`-tulosteen lisäteksti valehtelee vihreillä riveillä

Kaikki neljä väitteen 6 riviä tulostavat lisätekstin `fsat=1 seen in last 3.0 s`, myös ne kolme
jotka menevät läpi. Lisäteksti annetaan ilmeisesti ehdollisesti laskematta. Korjaa niin, että
lisäteksti kertoo rivin oman tuloksen — tai jätä se pois vihreiltä riveiltä. Vihreä rivi, joka
tulostaa punaisen perustelun, on juuri se tapa jolla vihreä fence lakkaa olemasta todiste.

## Ei muuta

Viritys (`kp = 0,17`, `ki = 0,13`), `p_margin = 3,0`, `tol = 0,3`, `k`-aikataulu, asettumisvara
5,0 s, budjetti, `may:`-lista ja Acceptance-komennot ennallaan.
