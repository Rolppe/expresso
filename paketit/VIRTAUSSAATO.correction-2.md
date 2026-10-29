# VIRTAUSSAATO — korjaus 2

Ajoin simulaation itse: 8 väitettä vihreänä, yksi punaisena — `fsat` nousee 29,34 s kohdalla,
määräaika 29,0 s. Toteuttaja on oikeassa: 5,0 s oli taas minun arvaamani pyöreä luku, ei
suureesta johdettu. Tämä korjaus muuttaa yhden luvun eikä mitään muuta.

## K6 — `fsat`-määräaika 5,0 s → 6,0 s, johdettuna

Lipun nousuaika on kahden peräkkäisen, jäädytetyn suureen summa:

1. Asetusarvon on noustava 4,4 barista (tasapaino 2,2 g/s, `k = 0,50`) saturaatiokynnykseen
   `p_max - 0,5 = 10,0 bar`. Rampitus `rate_bar_s = 2,2` tekee siitä `5,6 / 2,2 = 2,55 s`, eikä
   paine voi ohittaa asetusarvoaan, koska `lead` sitoo ne yhteen.
2. `sat_ms` vaatii `2,0 s` yhtäjaksoista kynnyksen ylitystä.

Alaraja on siis `4,55 s` plus sisemmän silmukan oma viive — mitattu `5,34 s`. Kumpikin termi on
jäädytetty (`p_max`, `lead`, dwell 2,0 s), joten viritys ei voi lyhentää sitä; toteuttajan 210
yhdistelmän pyyhkäisy sanoo samaa. Korvaa luvun 6 väite 3 tällä:

> 3. Viimeisessä vaiheessa `fsat` on 1 viimeistään **6,0 s** kuluttua muutoksesta ja pysyy 1:nä
>    vaiheen loppuun, ajo jatkuu loppuun asti eikä paine ylitä 12,0 bar.

6,0 s jättää mitattuun 5,34 s:aan 0,66 s marginaalin vaa'an kohinaa vastaan. Jos lipun halutaan
nousevan aidosti nopeammin, se on `rate_bar_s`:n tai dwell-ajan muutos eikä testin löysäys — se
harkitaan vasta laitteistotestin jälkeen, oikealla kahvikakulla mitattuna.

## Ei muuta

Älä viritä enää: `kp = 0,55`, `ki = 2,0`, `rate_bar_s = 2,2` jäävät voimaan. Älä koske muihin
väitteisiin, `may:`-listaan, Acceptance-komentoihin tai budjettiin (2382/2430). Aja Acceptance ja
Budget läpi ja raportoi kuusi riviä.
