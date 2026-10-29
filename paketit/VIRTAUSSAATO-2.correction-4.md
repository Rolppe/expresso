# VIRTAUSSAATO-2 — korjaus 4

Ajo katkesi istuntorajaan kesken virityksen. Ajoin jäljelle jääneet kaksi punaista itse ja
diagnosoin ne: toinen on lukuvirhe, toinen fysiikkaa. Kumpikaan ei ole `kp`/`ki`-asia.

## K5 — toleranssi on 0,3 g/s, ei 0,25

`band_ok`-funktion oletus on `tol = 0.25` (`testit/flow_ctrl_sim.py:114`), eikä yksikään väite anna
sille arvoa. Spesifikaation luku 4 sanoo **±0,3 g/s**. Mitattu paras poikkeama `k = 3,0` -vaiheessa
on 0,28 g/s, eli väite kaatuu pelkästään tähän. Aseta oletukseksi `tol = 0.3` tai anna se
kutsuissa; älä muuta muita `band_ok`-parametreja.

## K6 — `p_margin` 1,0 → 3,0 bar, ja se on nyt viritettävissä

`fsat` ei noussut kertaakaan, ja syy näkyy lokista: `k = 0,166` -vaiheessa paine **ei asetu vaan
heiluu 8,6–10,1 bar**. Kun `p_margin = 1,0`, katto `(p_max − p)/p_margin` on käytännössä
kytkin: yli 9,5 barissa se leikkaa dutyn lähes nollaan, sen alla se ei rajoita lainkaan
(`cap > 1`). Laitoksen aikavakio tuossa vaiheessa on `1/0,166 = 6 s`, joten paine ei ehdi
seurata — syntyy rajasykli, jossa katto sitoo vain osan ajasta ja `sat_ms` vuotaa tyhjäksi
välissä. Lippu mittasi oikeaa asiaa, mutta katto ei antanut sille vakaata tilaa.

Aseta `p_margin`-oletukseksi **3,0**. Silloin katto alkaa vaikuttaa jo 7,5 barissa ja kiristyy
pehmeästi: tasapaino on `duty = (p_max − p)/3` ja `p = 6,7·duty/0,166`, mistä `duty ≈ 0,24`,
`p ≈ 9,8 bar` — katto sitoo yhtäjaksoisesti, `sat_ms` täyttyy ja lippu nousee. Muissa vaiheissa
paine on 0,5–4,5 bar, jolloin `cap > 1` ja katto ei vaikuta mitenkään, eli muutos ei kosketa
saavutettavia vaiheita.

`p_margin` on tämän korjauksen myötä viritettävä suure kohdan 7 mielessä; `p_max` pysyy
jäädytettynä 10,5 barissa.

## K7 — viritys: suosi pienempää `kp`:tä

`k = 3,0` -vaiheessa 1 s keskiarvo heiluu 1,92–2,46 eli aivan toleranssin reunalla. Heilunta tulee
vaa'an kohinasta, joka kulkee `kp`-termin läpi suoraan dutyyn. Hae viritys, jossa pahin poikkeama
arvioitavissa ikkunoissa on selvästi alle 0,3 g/s, vaikka väite sallisi rajan.

## Ei muuta

Väitteet, `k`-aikataulu, asettumisvara 5,0 s, budjetti, `may:`-lista ja Acceptance-komennot
ennallaan. Kahden yrityksen sääntö lasketaan tästä korjauksesta alkaen.
