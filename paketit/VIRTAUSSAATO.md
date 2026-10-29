# EXPRESSO-VIRTAUSSAATO — virtauspohjainen uuton ohjaus

| Kenttä | Arvo |
|---|---|
| Tunnus | EXPRESSO-VIRTAUSSAATO |
| Skooppi | infra iot |
| Lähtötila | Paineohjaus: `classes.PumpPressureController`, `duty = 0,5 + 0,2·e + 0,3·∫e` (`KEHITYSYHTEYS.md:346`) |
| Virtauslähde | Laskettu vaa'asta, `scale.py: flow(span_ms)`, 11,6 Hz, mediaani-3 + PNS 1,0 s ikkuna (`KEHITYSYHTEYS.md:747-776`) |
| Firmware-setti | `pico-devsafe14-20260918` (17 tiedostoa), työkopio `Infra/iot/expresso/pico/` |
| Testipenkki | `Infra/iot/expresso/testit/` (`shot_test.py`, `real_plant_sim.py`, `flow_sim.py`) |
| Tila | suunniteltu, ei toteutettu |

## Tavoite

Uuttovaiheen säädettävä suure on **virtaus g/s**, ei paine bar. Kun käyttäjä muuttaa kuristusta
kesken uuton, keittimen on palautettava virtaus asetusarvoon pumpulla ilman että paine ylittää
rajansa.

## Sääntö 1 — kaskadi, ei suoraa virtaus→duty-säätöä

Ulompi virtaussäädin antaa **paineen asetusarvon**, jonka nykyinen paine-PI ajaa dutyksi.

- Ulompi silmukka: PI virhe `e = f_sp − f_meas`, päivitys 10 Hz, anti-windup, lähtö
  `p_sp ∈ [p_min, p_max]` (oletus 2,0–10,5 bar), rampitus ≤ 2,0 bar/s (sama katto kuin esiuuton
  tavoiteramppi, `KEHITYSYHTEYS.md:507`).
- Sisempi silmukka: nykyinen `PumpPressureController` muuttumattomana.

Perustelu: virtausestimaatin tehollinen viive on 0,30 s ja näytetaajuus 11,6 Hz
(`KEHITYSYHTEYS.md:806-809`), eli ulomman silmukan kaistanleveys on joka tapauksessa alle 0,5 Hz —
sisemmän silmukan lisäviive on merkityksetön. Vastineeksi paine pysyy rajattuna suureena
(asetusarvon saturaatio), sisemmän silmukan viritys ja `learned_ff_brew` säilyvät, ja paluu
nykyiseen käytökseen on yksi lippu.

## Sääntö 2 — kaikki turvarajat säilyvät

Paineen >13 bar katkaisu, `wmax`/`wrise`-painorajat, `tshot:stop`, kytkin, aikaraja ja
`finally`-sammutus (`KEHITYSYHTEYS.md:373-375`) pysyvät muuttumattomina. Virtaussäätö ei saa
ohittaa yhtäkään niistä eikä koskea esiuuttoon — se vaikuttaa vain uuttovaiheeseen.

## Sääntö 3 — vanhentunut virtauslukema ei saa ohjata

`scale.flow()` palauttaa `None`, kun näytteet ovat yli 500 ms vanhoja (`KEHITYSYHTEYS.md:778`).
`None` jäädyttää `p_sp`:n viimeiseen arvoonsa. Kolme peräkkäistä `None`-lukemaa (≈260 ms) palauttaa
uuton kiinteään paineasetusarvoon ja kirjaa syyn lokiriville. Ilman vaakaa virtaustila ei käynnisty
lainkaan.

## Sääntö 4 — asetusarvo voi olla saavuttamaton, ja se sanotaan lokissa

Kuristus voi olla niin tiukka, ettei tavoitevirtaus ole saavutettavissa `p_max`:lla (18.9.2026
mitattu tila: 0,79 g/s 8,07 barilla, `KEHITYSYHTEYS.md:863-865`). Kun `p_sp` on ollut saturoituneena
> 2 s, lokirivi kertoo sen kentässä `fsat=1`; uutto jatkuu, ei katkea.

## Sääntö 5 — lokirivi laajenee, ei muutu

`TS`-rivin nykyiset kentät säilyvät paikoillaan (`KEHITYSYHTEYS.md:375,788`); virtaussäätö lisää
loppuun kentät `fsp=<g/s> fsat=<0|1>`. `TS_START` kertoo tilan kentässä `fmode=`. Vanhat
analyysityökalut (`analyze_shot.py`) eivät saa rikkoutua.

## Sääntö 6 — komennot ajonaikaisia, eivät tallentuvia

`fmode:on|off` ja `fset:<0,5–5,0>` `commands.py`:hen, samaan tapaan kuin `fwin:<ms>`
(`KEHITYSYHTEYS.md:780-781`). Asetukset eivät tallennu; käynnistyksen jälkeen laite on
paineohjauksessa. Näin laite ei voi jäädä virtaustilaan flashauksen jälkeen.

## Hyväksyntä (simulaatio ennen laitteistoa)

Isäntäsimulaatio `Infra/iot/expresso/testit/` -penkissä, ei laitteistoa: pumppumalli
`dp/dt = 6,7·u − k·p`, ulosvirtaus `c·k·p`, viive 70 ms, vaa'an kohina 0,25 g ja 11,6 Hz
näytteistys estimaattorin läpi. Ajossa kuristusta muutetaan kesken uuton (`k` kertoimella 0,4
alas ja takaisin), ja vaaditaan:

1. virtaus palaa ±0,25 g/s sisään asetusarvosta ≤ 2,0 s kuluessa muutoksesta;
2. paine ei ylitä `p_max + 0,5 bar` missään kohtaa eikä 13 bar koskaan;
3. `fmode:off` tuottaa nykyisen paineohjauksen tuloksen muuttumattomana (regressio).

## Laitteistotesti (erikseen, käyttäjän luvalla)

`tshot:25` virtaustilassa, käyttäjä muuttaa kuristinta ajon aikana. Aloitetaan vasta kun
simulaatio on vihreä, firmware flashattu ja `pico_dev.py verify` antanut `VERIFIED n/n`. Keitin on
irti verkkovirrasta flashauksen ajan (`KEHITYSYHTEYS.md:175-179`).
