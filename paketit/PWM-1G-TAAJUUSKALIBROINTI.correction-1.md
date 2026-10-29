# PWM-1G-TAAJUUSKALIBROINTI — korjaus 1

Toteuttaja pysähtyi ennen ensimmäistäkään riviä ja kysyi oikean kysymyksen: spec vaatii
näytteenoton "samalla busy-wait-ajoituksella kuin `_pcap_capture`", mutta briefin `read:`-lista
antoi `pico/functions.py`:stä rivit 706-760, ja anturin, vahvistuksen ja offsetin haku on
riveillä **765-767** — juuri rajauksen ulkopuolella. Toteuttaja kieltäytyi arvaamasta
laitteistorajapintaa, ja se oli oikein.

Vika on suunnittelijan briefissä, ei spec:ssä eikä toteutuksessa. Vastaus annettiin lähteestä:

```python
sensor = brew_data.pressure_sensor.pressure_sensor
gain = brew_data.pressure_sensor.gain
offset = brew_data.pressure_sensor.offset
```

sama kuvio toistuu riveillä 901-903 ja 958-960. Lukuoikeus laajennettiin väliin 706-1000, eli
`_pcap_capture`, `pressure_capture_run`, `pressure_sweep_run` ja `pressure_hold_run` kokonaan.

**Opetus briefin kirjoittajalle:** kun spec sanoo "sama kuin X:ssä", `read:`-listan on katettava
X:n *kutsuja* siihen asti, mistä X:n parametrit tulevat — ei vain X:ää itseään. Kolmesta tämän
session briefistä tämä on kolmas kerta, kun este löytyi suunnittelijan omasta artefaktista
(kahdesti holdoutista, nyt rajauksesta); jokaisella kerralla toteuttaja oli oikeassa.
