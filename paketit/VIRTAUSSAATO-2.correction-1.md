# VIRTAUSSAATO-2 — korjaus 1

Havainto on oikea ja vika on spesifikaatiossa: laajensin `k`-aikataulun mutta jätin sanomatta,
että se koskee vain `fmode:on`-ajoa.

## K1 — regressioajo ajetaan kiinteällä kuristuksella `k = 0,50`

`fmode:off`-ajon tehtävä on osoittaa, että **paineohjaus on ennallaan** — ei se, että paineohjaus
selviäisi auki olevasta venttiilistä. Se ei selviä eikä sen kuulukaan: `k = 3,0` tarkoittaa
tasapainopainetta `6,7/3,0 ≈ 2,2 bar` täydellä dutylla, joten 8 barin tavoite on fysikaalisesti
saavuttamaton. Juuri siksi paineohjaus on korvattu.

Aja `fmode:off`-ajo **vakiolla `k = 0,50` koko keston ajan**. Käytännössä: `k_at()` saa parametrin
tai `run(False)` käyttää omaa vakiofunktiotaan; kumpi tahansa käy, kunhan `fmode:on`-ajon aikataulu
ei muutu. Regressiotarkastuksen ikkuna ja 0,5 bar toleranssi pysyvät ennallaan — `k = 0,50` pitää
8 baria dutylla ~0,60, eli ikkuna on kelvollinen.

## Ei muuta

Luvun 4 väitteet 1–4 koskevat `fmode:on`-ajoa sellaisinaan. Viritys (`kp`, `ki`) alkaa vasta tämän
jälkeen, ja kahden yrityksen sääntö lasketaan tästä korjauksesta uudelleen. Budjetti, `may:`-lista
ja Acceptance-komennot ennallaan.
