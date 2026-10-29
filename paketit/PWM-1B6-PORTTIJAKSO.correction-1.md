# PWM-1B6-PORTTIJAKSO — korjaus 1

Toteuttaja osui Stop-ehtoon ja oli oikeassa kahdesti. Holdout `testit/psweep_mult_smoke.py`
väitti portin jaksosta kaksi asiaa, jotka eivät voi pitää yhtä aikaa paikkaansa:

1. `len(on) == 20` ikkunassa `range(400)`. Portin jakso on `8 * 19 960 µs = 159 680 µs` eli
   **159,68 näytettä**, joten 400 näytteen ikkunaan mahtuu 2,5 jaksoa ja päälläoloja on kolme,
   yhteensä 60 näytettä. Toteuttaja mittasi tämän (`len(on) == 60`, lohkot alkavat 0, 160, 320)
   ja huomasi, että sama duty-vaatimus, jonka holdout itse asettaa (1/8), pakottaa sen.
2. `pcap_gate(i, ...) == pcap_gate(i + period_us // 1000, ...)` kaikilla `i`. Jakso ei ole
   kokonaisluku näytteitä, joten siirto 159 näytteellä ei ole jaksollisuus; toteuttaja mittasi
   4 eroa 300:sta, ja ne ovat lohkojen reunoja.

Vika oli holdoutissa, ei spec:ssä eikä toteutuksessa. Korjatut väitteet mittaavat sen, mitä
alkuperäisten piti: ensimmäinen päälläolo on tasan yksi verkkojakso (20 näytettä), lohkojen väli
vuorottelee 159 ja 160 näytteen välillä, lohkoja on 8000 näytteessä 50, ja jokainen päälläolo on
19 tai 20 näytettä. Toteuttajan toteutus menee näistä läpi sellaisenaan (`RESULT: 0 failed`).
