# PWM-1B4-PYYHKAISY — korjaus 1

Toteuttaja osui Stop-ehtoon ja kysyi oikean kysymyksen: holdoutin testi 6 vaati syyn
`scalelost` tilanteessa, jossa vaa'an lukema oli vanhentunut **jo ennen ajoa**. Sen nappaa
`tray_guard_start` syyllä `noscale`, ja niin kuuluukin: raja tarkistetaan ennen yhtäkään
relettä, eikä siinä kohtaa ole vielä mitään, minkä voisi menettää.

Vika on holdoutissa, ei spec:ssä eikä toteutuksessa. Spec kohta 2.3 pysyy sanatarkasti
ennallaan.

Korjattu `testit/psweep_smoke.py`:

- testi 6 mittaa nyt sen, mitä sen piti mitata: vaaka elää asettumisen ja pidon läpi ja
  lakkaa päivittymästä vasta ensimmäisen segmentin alettua (`scale_die_s=5.2`, segmentti
  2500 ms). Silloin kaappauksen jälkeinen uudelleenhaku ei saa tuoretta lukemaa, ja syyn on
  oltava `scalelost`. Testi vaatii lisäksi, että ainakin yksi segmentti ehti alkaa — muuten
  se ei koskisi uudelleenhakupolkua lainkaan;
- uusi testi 6b lukitsee toteuttajan havainnon paikalleen: ennen ajoa vanhentunut lukema
  torjutaan syyllä `noscale` eikä yhtäkään kaappausta aloiteta.

Ajo pitenee noin 55 s:sta noin 75 s:iin. Muut väitteet ennallaan.
