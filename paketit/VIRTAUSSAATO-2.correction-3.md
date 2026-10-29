# VIRTAUSSAATO-2 — korjaus 3

Oraakkelikoe on vakuuttava: kun säädin korvataan täydellisellä vakiodutylla ja väite kaatuu silti,
kyse ei ole virityksestä. Asettumisaika oli taas minun arvaamani pyöreä luku, ja se on lyhyempi
kuin laitoksen oma.

## K4 — asettumisvara 2,0 + 0,5 s → 5,0 s, johdettuna

Laitoksen aikavakio on `tau = 1/k`. Hitain vaihe on `k = 0,50`, jossa `tau = 2,0 s`; askelvaste
asettuu noin `2·tau = 4,0 s` kuluessa. Korjauksen 2 liukuva keskiarvo syö lisäksi oman
ikkunansa, `1,0 s`. Yhteensä **5,0 s**, eikä mikään säädin voi alittaa sitä: oraakkelin pahimmat
poikkeamat osuivat kohtiin 2,6 s, 3,1 s ja 2,6 s muutoksesta.

Korvaa luvun 4 väitteen 1 aikaraja: `2,0 s kuluttua muutoksesta` → **`5,0 s kuluttua
muutoksesta`**. Toleranssi ±0,3 g/s, mitattava suure (1,0 s liukuva keskiarvo) ja `k`-aikataulu
pysyvät ennallaan — jokaiseen vaiheeseen jää 3–5 s arvioitavaa ikkunaa, mikä riittää osoittamaan
että virtaus *pysyy* tavoitteessa eikä vain käy siinä.

Kirjaa simulaatiotiedoston kommenttiin, mistä 5,0 s tulee: `2/k_hitain + keskiarvoikkuna`. Luku ei
ole valittu vaan laskettu, ja jos `k`-aikataulu joskus muuttuu, sama lasku tehdään uudelleen.

## Ei muuta

Viritys (`kp`, `ki`) haetaan uudelleen tämän kanssa; hakusi paras `kp = 0,17, ki = 0,13` on
kelvollinen lähtökohta. Väitteet 2–5, budjetti, `may:`-lista ja Acceptance-komennot ennallaan.
Kahden yrityksen sääntö lasketaan tästä korjauksesta alkaen.
