# VIRTAUSSAATO-2 — korjaus 5

Hakusi osoittaa, ettei `kp`/`ki`-paria ole olemassa: `fsat` vaatii `ki ≳ 0,2` ja virtausväitteet
`ki ≈ 0,13–0,18`. Alueet eivät leikkaa, koska lippu on sidottu väärään suureeseen. Se on minun
vikani, ja korjaan sen — en pyydä sinua virittämään sen ympäri.

## K8 — `fsat` mittaa suodatettua virhettä, ei rajoittavaa mekanismia

Ehto `cap <= duty + 0.01` kysyy "sitooko katto juuri nyt". Se on havaitsematon suure lokissa ja
kohinan armoilla: duty heiluu katon ympärillä, ja jokainen notkahdus vuodattaa laskurin. Lipun
merkitys on kuitenkin yksinkertainen — **tavoitetta ei saavuteta** — ja se mitataan virheestä.

Korvaa luvun 1 kohta 7 tällä:

> 7. Pidä yllä suodatettua virhettä: `self.e_avg += (e - self.e_avg) * min(1.0, dt / 1.0)`
>    (aikavakio 1,0 s; ensimmäisellä näytteellä `e_avg = e`). Saturaatioehto on **`e_avg > 0.2`**.
>    Tosi → `sat_ms += dt*1000`, epätosi → `sat_ms -= 0.5 * dt*1000`, rajaus `[0, 2000]`;
>    `saturated` nousee 2000:ssa, laskee 0:ssa, välissä säilyttää arvonsa (ennallaan).

Kynnys 0,2 g/s on kolme kertaa suodatetun virheen hajonta: vaa'an kohina on 0,21 g/s, ja 1,0 s
suodatin pudottaa sen noin 0,07 g/s:aan. Suodattamattomalla virheellä 0,1 g/s kynnys olisi alle
puolen hajonnan päässä nollasta, jolloin laskuri täyttyisi pelkästä kohinasta myös silloin kun
säätö osuu tavoitteeseen.

Alapuolinen ehto (`e < -0.1`, duty nollassa) poistetaan kokonaan: pumppu on ainoa veden lähde,
joten nolladuty tarkoittaa nollavirtausta eikä tila voi jäädä päälle.

## K9 — uusi väite: lippu myös laskee

Pelkkään virheeseen sidottu lippu voi nousta hetkeksi suuren venttiilimuutoksen transientissa. Se
on totta eikä haitallista, mutta se on todistettava itsestään palautuvaksi. Lisää luvun 4 väitteisiin:

> 6. Jokaisessa saavutettavassa vaiheessa `fsat` on 0 vaiheen **kolmen viimeisen sekunnin** ajan.

## K10 — viritys

Palaa alueelle `kp ≈ 0,15–0,17`, `ki ≈ 0,13–0,18`, joka jo täytti virtausväitteet; `fsat` ei enää
kilpaile niiden kanssa. `p_margin = 3,0` ja `tol = 0.3` jäävät voimaan korjauksesta 4.

## Ei muuta

`k`-aikataulu, asettumisvara 5,0 s, `may:`-lista ja Acceptance-komennot ennallaan. Budjetti on nyt
1928/2000, eli tilaa on 72 riviä. Kahden yrityksen sääntö lasketaan tästä korjauksesta alkaen.
