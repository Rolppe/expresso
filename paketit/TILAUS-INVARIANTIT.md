# EXPRESSO-TILAUS-INVARIANTIT — tilauksen menetelmäkohdat tarkistettaviksi invarianteiksi

| Kenttä | Arvo |
|---|---|
| Tunnus | EXPRESSO-TILAUS-INVARIANTIT |
| Skooppi | infra expresso |
| Tila | **valmis 27.10.2026** |
| Kiireellisyys | korkea: sama vikaluokka on jo tuottanut yhden turvallisuuspuutteen |
| Sukua | `paketit/TURVAKATO.md` (sama vikaluokka, yksi taso alempana), `claude/siirto/REKISTERI.md` Viat (prosessin puoli) |

## Laukaisija (19.9.2026)

Käyttäjä kysyi, onko tieto vaiheen selvittämisestä hukkunut. Ei ollut hukkunut tiedostosta:
`paketit/PUMPPU-PWM.md:11-13` kirjaa tilauksen sanatarkasti —

> (a) verkkotaajuus mitataan pumpun aiheuttamasta painevaihtelusta, (b) viive pumpulta
> paineanturille mitataan ohittamalla joka toinen sykli ja **siirtämällä ohitus painetta seuraten**
> oikeaan kohtaan

— mutta suunnittelija vastasi samana päivänä kolmeen jatkokehityskysymykseen nojaten saman
tiedoston sääntöihin 5–9 ("Picolla ei ole nollaylityksen tunnistinta", rivi 242) ja suositteli
**optoerotinta nollaylityksen tunnistamiseen**. Suositus oli turha: tilauksen kohta (b) määrää
vaihereferenssin luettavaksi pumpun omasta paineväreilystä. Käyttäjä huomasi puutteen, ei prosessi.

## Vikaluokka — sama kuin TURVAKATO, yksi taso ylempänä

| | TURVAKATO (koodin ehto) | tämä paketti (vaatimus) |
|---|---|---|
| Mikä katosi | kaukalon painoraja | tilauksen menetelmäkohta (b) |
| Mistä perittiin | "keskeytysehdot ovat `pcap`:n ehdot" | "säännöt 5–9 sanovat, ettei tunnistinta ole" |
| Miksi katosi | ei ollut kantava lyhyelle `pcap`-ajolle | ei ollut kantava taitoksen lukemiselle |
| Missä ehto eli | vain kommentissa | vain proosassa, yhden tiedoston yhdessä luvussa |
| Kuka huomasi | käyttäjä | käyttäjä |

Yhteinen mekanismi: **työ etenee viimeisimmästä johdetusta tiivistelmästä, ei siitä lähteestä,
josta tiivistelmä on johdettu.** Jokainen luovutus pakkaa, ja pakkaus pudottaa sen, mikä ei ole
kantava käsillä olevalle askeleelle.

Rekisterin päätös 19.9.2026 antoi tähän jo lääkkeen yhtä tasoa alempana: *"Ehdosta tehtiin
tarkistettava invariantti, ei kommenttia. Peruste on tämän saman session TURVAKATO-löydös: vain
kommentissa elävä ehto katoaa, kun joku muuttaa naapurilukua."* Tämä paketti antaa saman lääkkeen
vaatimuksille.

## Tehtävä

1. **Nimeä tilauksen menetelmäkohdat invarianteiksi.** `paketit/PUMPPU-PWM.md`:n luvusta "Mitä
   käyttäjä tilasi" johdetaan tunnukset `TILAUS-A`, `TILAUS-B`, … jotka sisältävät käyttäjän oman
   sanamuodon **lainauksena**, ei tiivistelmänä. Lainaus on invariantin runko: tiivistelmä on
   juuri se muoto, joka tässä vikaluokassa katoaa.
2. **Vie invariantit rekisteriin omaksi luvukseen** (`REKISTERI.md`, luku "Tilauksen invariantit"),
   jotta ne kulkevat joka purussa samalla tavalla kuin `SEURAAVA PAKETTI` -rivi. Rekisteri on
   tähän asti kuvannut *muutoksia*; tämä luku kuvaa sitä, minkä on aina pidettävä.
3. **Sääntö menetelmävalinnoille:** jokainen vastaus, brief tai spec, joka valitsee menetelmän,
   nimeää sen `TILAUS-x`-rivin, jota se noudattaa — tai sanoo ääneen poikkeavansa siitä ja miksi.
   Poikkeaminen on sallittua, hiljainen poikkeaminen ei.
4. **Tee tarkistuksesta koneellinen**, `Automation_plugin/tools/check-brief.mjs`:n tapaan (se
   todettiin 19.9.2026 toimivaksi tästä reposta poluilla): brief, joka esittää menetelmän
   nimeämättä `TILAUS-x`-riviä, kaatuu tarkistukseen. Ilman koneellista tarkistusta tämä paketti
   on vain yksi proosassa elävä ehto lisää — eli sama vika, jota se yrittää korjata.
5. **Takautuva tarkistus:** käy läpi avoimet briefit ja `paketit/PUMPPU-PWM.md`:n vaiheet 1c–1f,
   2, 3, 4 ja merkitse kuhunkin, mitä tilauskohtaa ne toteuttavat. Tämä paljastaa, onko muita
   kohtia kadonnut samalla tavalla kuin (b).

## Hyväksyntä

- `REKISTERI.md`:ssä on luku "Tilauksen invariantit", jossa jokainen rivi sisältää käyttäjän
  sanamuodon lainauksena ja viitteen `paketit/PUMPPU-PWM.md`:n riviin.
- Koneellinen tarkistus kaataa briefin, joka esittää menetelmän nimeämättä tilauskohtaa —
  todennettuna ajamalla se yhtä läpäisevää ja yhtä kaatuvaa esimerkkiä vasten.
- Vaiheiden 1c–1f, 2, 3, 4 riveillä on tilauskohdan tunnus.

## Mitä tämä ei tee

Tämä ei tee suunnittelijasta muistavaa. Se tekee tästä vikaluokasta äänekkäästi kaatuvan sen
sijaan, että se menisi hiljaa läpi. Molemmilla kerroilla puutteen huomasi käyttäjä, ei prosessi;
hyväksyntä mittaa nimenomaan sitä, huomaako prosessi sen jatkossa itse.

## Toteutus ja hyväksyntä (27.10.2026)

1. **Tilauksen menetelmäkohdat invarianteiksi:**
   - Kaikki käyttäjän tilaukset on nimetty invarianteiksi (`TILAUS-A`…`TILAUS-T`, `TILAUS-RELEET-ALAS`, `TILAUS-AUTONOMIA`) `KAYTTAJAN-TIEDOT.md`:ssä.
   - Jokainen invariantti sisältää käyttäjän sanamuodon lainauksena ja viitteen alkuperäiseen tilaukseen (`paketit/PUMPPU-PWM.md` tai muu käyttäjän tilaus).
   - Takautuvassa tarkistuksessa nimettiin myös tilauksen kohdat 3 (`TILAUS-S`, max flow rate) ja 4 (`TILAUS-T`, höyryn lämpötilan säädin +10 °C).
2. **Invariantit rekisterissä ja purussa:**
   - `REKISTERI.md`:ssä luku `## Pysyvät vaatimukset (Tilauksen invariantit)` nimeää `KAYTTAJAN-TIEDOT.md`:n luettavaksi kokonaan joka purussa.
   - Purkutyökalu `claude/siirto/tools/vaatimukset.mjs --rivi "infra expresso"` tulostaa kaikki 23 invarianttia sanatarkasti jokaiseen purkuraporttiin.
3. **Koneellinen tarkistus:**
   - `node claude/siirto/tools/vaatimukset.mjs --tarkista "infra expresso" <brief.md>` kaataa automaattisesti jokaisen briefin, joka valitsee menetelmän nimeämättä noudattamaansa `VAATIMUS: TILAUS-x` -riviä (tai `POIKKEAA: ...` / `VAATIMUS: ei koske — ...`).
   - Todennettu automaattisella testillä `testit/tilaus_invariantit_smoke.py` sekä läpäisevällä että kaatuvalla esimerkillä (RESULT: 0 failed).
4. **Takautuva tarkistus vaihetaulukkoon:**
   - `paketit/PUMPPU-PWM.md`:n vaihetaulukon sarakkeessa `Tilauskohdan tunnus` kaikki vaiheet 1a–1f, 2, 3, 4 on sidottu omiin tilaustunnuksiinsa. Mikään tilauskohta ei ole kadonnut.
