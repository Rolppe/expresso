# eXpresso — käyttäjän kertomat tiedot, tilaukset ja menetelmäohjeet

**Tämä tiedosto luetaan kokonaan joka purussa.** Se ei ole tiivistelmä eikä muutosloki, vaan
kokoelma sitä, minkä on aina pidettävä: käyttäjän omat sanamuodot lainauksina. Rekisteri kuvaa
sen, mikä muuttui; tämä tiedosto sen, mikä ei muutu ilman että käyttäjä sanoo niin.

**Miksi lainauksina:** tiivistelmä on juuri se muoto, jossa tieto katoaa. Kaksi todistetta
19.9.2026 — EXPRESSO-TURVAKATO (`paketit/TURVAKATO.md`: kaukalon painoraja katosi, kun spec peri
tiivistetyn ehtolistan) ja vaihereferenssin unohdus (suunnittelija suositteli optoerotinta, vaikka
tilaus määrää vaiheen luettavaksi paineväreilystä). Molemmilla kerroilla puutteen huomasi käyttäjä,
ei prosessi. Ks. `paketit/TILAUS-INVARIANTIT.md`.

**Ylläpito:** tähän **lisätään**, tästä ei kirjoiteta uusiksi eikä tiivistetä. Jos rivi osoittautuu
vanhentuneeksi, se merkitään vanhentuneeksi ja sen viereen kirjoitetaan uusi — vanha sanamuoto jää
näkyviin. Lähde on istunnon transkripti; `[id]` on istunnon tunnuksen alku.

---

## 1. Tilaus — pumpun PWM ja sen vaiheet (19.9.2026, `[eeb16a3f]`)

> "1. suunnitellaan pumpun pwm. Tämä pitää tehdä uudella tavalla. Ensin pitää etsiä sähköverkon
> taajuus siten että seurataan pumpun aiheuttamaa painevaihtelua. Tämän jälkeen pitää selvittää
> viive pumpulta painesensorille esim siten että yritetään katkoa joka toinen sykli pois ja
> **painetta seuraamalla siirretään syklin poisto oikeaan kohtaan**. Sitten selvitetään mikä kohta
> syklistä on turvallista vibration pump pwm. Tämän jälkeen testataan pwm. Tämän jälkeen
> integroidaan expresso paineen hallintaan pwm siten että optimoidaan se virtauksen ja paineen
> perusteella 8bar. Minä käännän kuristinta auki ja kiinni ja pwm huolehtii 8 bar paineesta. Tämän
> jälkeen 2ml/s virtaus kalibrointi pwm toiminnolla. Taas samoin että säätelen kuristinta"

> "2. Optio pre infusion time auto. Tämä lopettaa preinfusionin kun vaa-alla havaitaan poikkeava
> muutos. Tämä muutos tulee siitä kun ensimmäiset kahvipisarat osuvat kuppiin. Tämä pitää miettiä
> miten saadaan erotettua muusta tärinästä ja kohinasta mahdollisimman tehokkaasti."

**TILAUS-A — verkkotaajuus mitataan pumpun aiheuttamasta painevaihtelusta.** (19.9.2026 käyttäjän tilaus 1a, `paketit/PUMPPU-PWM.md:13-14`). Toteutettu vaiheessa
1a: 50,1 Hz kolmesta ajosta.

**TILAUS-B — vaihereferenssi luetaan paineesta, ei laitteistosta.** (19.9.2026 käyttäjän tilaus 1b, `paketit/PUMPPU-PWM.md:14-16`). "painetta seuraamalla siirretään
syklin poisto oikeaan kohtaan" tarkoittaa, että ohituksen kohdistus tehdään paineen perusteella.
Laitteistotunnistinta ei ole tilattu eikä se ole tarpeen. **Tähän kohtaan tehtiin virhe 19.9.2026:
suunnittelija suositteli optoerotinta.** `testit/mains_freq.py:78-89` laskee Goertzelin mutta
palauttaa vain amplitudin ja heittää vaiheen pois — juuri sen luvun, jota tämä kohta tarvitsee.

**TILAUS-C — 8 barin pito käyttäjän kääntäessä kuristinta.** (19.9.2026 käyttäjän tilaus 1e, `paketit/PUMPPU-PWM.md:16-18`). "Minä käännän kuristinta auki ja kiinni
ja pwm huolehtii 8 bar paineesta." Testin muoto on siis määrätty: käyttäjä säätää, kone pitää.

**TILAUS-D — 2 ml/s virtauskalibrointi samalla tavalla kuristinta säätäen.** (19.9.2026 käyttäjän tilaus 1f, `paketit/PUMPPU-PWM.md:18`).

**TILAUS-E — esiuuton automaattilopetus vaa'an muutoksesta**, ensimmäiset kahvipisarat kuppiin,
erotettava tärinästä ja kohinasta. (19.9.2026 käyttäjän tilaus 2, `paketit/PUMPPU-PWM.md:19-20`).

**TILAUS-S — max flow rate -säädin pumpun ohjauksen rajoituksena.** (19.9.2026 käyttäjän tilaus 3, `paketit/PUMPPU-PWM.md:21`). "3. max flow rate -säädin pumpun ohjauksen rajoituksena."

**TILAUS-T — höyryn lämpötilan säädin: nykyisestä arvosta mahdollisuus nostaa +10 °C.** (19.9.2026 käyttäjän tilaus 4, `paketit/PUMPPU-PWM.md:22`). "4. Höyryn lämpötilan säädin: nykyisestä arvosta mahdollisuus nostaa +10 °C."

## 2. Tilaus — pumpun tehon säätötarkkuus (19.9.2026, tämä istunto)

> "Pumpun teho pitää olla säädettävissä noin noin 1% tarkkuudella jos tästä ei aiheudu haittaa."

Ehdollinen tilaus: "jos tästä ei aiheudu haittaa". Vastattu: saavutettavissa vain aikakeskiarvona
(1 jakso = 20 ms, 1 % = 100 jaksoa = 2,0 s; laitoksen aikavakio 0,81 s), joten keino on
delta-sigma, ja vaatimus kirjataan muodossa "1 % keskitehosta ≥ 2 s ikkunan yli".

## 2b. Tilaus — taajuuden itsekorjaus ajon aikana (19.9.2026, tämä istunto)

> "Semmoinen asia mikä pitää olla tämän pwm ominaisuus. Ajon aikana pitää olla taajuuden itsensä
> korjaava toiminto. Uutto aloitetaan 50hz. Pumpun käydessä ja nostaessa paineen preinfusion
> paineeseen tarkastetaan tarkka taajuus ja samoin myös selvitetään taajuuden vaihe. Jos
> järjestelmä on paineinen valmiiksi niin paine vapautetaan solenoidia käyttämällä: päälle - 0.5s
> viive - pois 0.2s viive - syklin toisto kunnes paine on purettu"

**TILAUS-F — PWM:n on korjattava verkkotaajuus itse joka ajolla.** Taajuus ei ole vakio koodissa
eikä kertaalleen mitattu luku, vaan jokaisen uuton alussa uudelleen mitattava suure. Lähtöarvo on
50 Hz, ja mittaus korvaa sen.

**TILAUS-G — mittausikkuna on esiuuton paineennosto.** Taajuus ja **vaihe** luetaan silloin, kun
pumppu käy ja nostaa painetta esiuuttopaineeseen — ei erillisellä testikomennolla eikä uuton
jälkeen. Tämä sopii mitattuun: väreilyn amplitudi on suurimmillaan matalassa paineessa
(1,788 bar vapaassa virtauksessa vs. 0,307 bar 7,7 barissa), eli paineennosto on ajon paras
mittausikkuna.

**TILAUS-H — paineinen järjestelmä puretaan ennen mittausta, käyttäjän antamalla syklillä.**
Magneettiventtiili päälle, 0,5 s viive, pois, 0,2 s viive, toisto kunnes paine on purettu. Ajat
ovat käyttäjän antamat eikä niitä viritetä ilman häntä.

Tarkennus samassa istunnossa, kun suunnittelija kysyi, mikä lukema tarkoittaa purettua:

> "Paine on purettu tarkoittu että paine on tiputettu solenoidin jaksotuksen avulla"

Eli lopetusehto on menettelyssä, ei asetetussa rajassa: jaksotusta jatketaan niin kauan kuin
paine sen ansiosta laskee, ja se päättyy kun paine ei enää laske. Koodissa tämä luetaan
mittauksesta eikä arviosta: laskuksi lasketaan vähintään `PCAP_PLATEAU_BAR` = 0,15 bar yhden
syklin yli (johdettu suodatetun kohinan hajonnasta 0,034 bar, `functions.py:548`). Käyttäjä ei
antanut kierroskattoa, joten sellaista ei keksitä hänen puolestaan — jos jaksotus ei koskaan
pysähdy, se on vika eikä normaali tila, ja se kirjataan sellaisena.

**TILAUS-I — verkossa pysyminen mitataan paineesta, korjaus tunnetulla viiveellä (37–41 ms).**
(23.9.2026, `[3f2ea735]`)

> "taajuudessa mukana pysyminen mitata paineesta. meillä on tiedossa mikä on viive taajuuden ja
> paineen taajuuden välillä. Tämä pitää muistaa"

Syy: 1b-hajontasarja 23.9.2026 ajastettiin ajon alusta kiinteällä 19 960 µs:n jaksolla ilman
seurantaa, ja kohdistus ajautui taukojen 14,8 s:n aikana noin yhden jakson verran — käsketty vaihe
ei ollut todellinen verkkovaihe (REKISTERI.md, rivi "10 vaiheen hajontamittaus"). Siksi: ajon
aikana taajuus ja vaihe luetaan paineen väreilystä (TILAUS-A, -B, -G), ohitusten ajoitus sidotaan
siihen jatkuvasti eikä ajon alkuun, ja paineesta luettu vaihe muunnetaan pumpun vaiheeksi tunnetulla
viiveellä: **ohituskäskystä paineen pudotukseen 42 ms (hajonta 9 ms), pumpun sammutuksesta 38 ms
(hajonta 7 ms), todellinen noin 37–41 ms** (`HISTORIA.md:119-122`, `pstep-20260920-a,d,e,f`). Viivettä
ei mitata uudelleen joka ajolla eikä korvata mallin arviolla (70–90 ms kumottiin tällä mittauksella).

**TILAUS-J — sisäinen kello seuraa verkkotaajuutta rinnalla, myös pumpun ollessa pois (49,9–50,1 Hz).**
(23.9.2026, `[3f2ea735]`)

> "tämä pitää myös pitää rinnallaan sisäisen kellon taajuus seurannan jota tarkastetaan korjataan
> jatkuvasti. tämä johtuu siitä että jos joudutaan pumppua kytkemään pois päältä niin tällä aikaa
> jakso saattaa siirtyä liikaa ja seraava pumpun käynnistyksen ajankohta saattaa olla pielessä.
> taajuus vaihteluväli on 49.9 - 50.1. mieti miten saat toimimaan sen vakaasti"

Eli TILAUS-I:n paineesta luettu vaihe ei yksin riitä: kun pumppu on pois, painessa ei ole väreilyä
eikä siten mittausta. Picon oma kello kuljettaa verkkojaksoa (taajuus ja vaihe) koko ajan, paine
korjaa sitä aina kun pumppu käy, ja seuraava käynnistys ajoitetaan kellon ennusteesta.
Taajuusalue 49,9–50,1 Hz on käyttäjän antama. Suunnitelma: `paketit/VERKKOKELLO.md`.

## 2c. Tilaus — vaiheseuranta pumpun ohjauksen jokaisessa vaiheessa (24.9.2026)

> "opetellaan keino ottaa mahdollisimman hyvin jokaisessa vaiheessa vaihen seuranta. Tässä kuvaus
> pumpun ohjauksesta ja syklin seurannasta.
>
> 1. preinfusion paineen nosti. Pumppu toimii täydellä syklillä kunnes saavuttaa korkeimman tunnetun
> painepisteen mikä ei aiheuta yliampumista preinfusion paineeseen. Tässä vaiheessa kerätään tietoa
> syklistä.
> 2. preinfusion paineen lopullinen nosto. Pumppua jaksotetaan lisäämällä taukoja pumppuun siten että
> overshoot ei pääse tapahtumaan. tässä vaiheessa taukojen kohdistaminen yksi kerrallaan antaa
> parempaa dataa syklin vaiheesta. syklin tunnistusta parannetaan jatkuvasti. tämä jatkuu niin kauan
> kuin preinfusion aika on
> 3. paine nostetaan uutto paineeseen. yliampumisen ehkäisy samoin kun preinfusion paineen nosto
> vaiheessa. vaihe kelloa synkronoidaan.
> 4. uutto paineen viimeinen tarkennus tehdään samoin kun preinfusion kohdalla. Kellon synkronointi ja
> korjaus on jatkuvaa.
>
> pumpun vaimennus täytyy olla mahdollisimman pienillä pykälillä säädettävissä jotta paine heittely
> saadaan mahdollisimman pieneksi. eli pienin pumpun vaimennus on se 10ms. täytyy kuitenkin huomioida
> että se vaikuttaa 20ms ajan.  eli sekunnista valinnaisia vaimennus kohtia on 50kpl."

**TILAUS-K — vaiheseuranta jokaisessa uuton vaiheessa, neljä vaihetta.** (1) esiuuttopaineen nosto
täydellä syklillä korkeimpaan tunnettuun pisteeseen, josta ei tule yliampumista — syklistä kerätään
tietoa; (2) esiuuttopaineen viimeinen nosto ja pito tauoilla, joiden kohdistus yksi kerrallaan antaa
vaihedataa, tunnistus paranee jatkuvasti koko esiuuttoajan; (3) nosto uuttopaineeseen samoin
yliampumatta, vaihekello synkronoidaan; (4) uuttopaineen tarkennus kuten (2), synkronointi ja
korjaus jatkuvaa. Kohta (1) täsmentää TILAUS-G:tä: nousussa kerätään tietoa syklistä.

**TILAUS-L — vaimennuksen askel on yksi jakso: 10 ms tauko vaikuttaa 20 ms, 50 valittavaa kohtaa
sekunnissa.** Pumpun tehoa säädetään mahdollisimman pienin askelin paineheittelyn minimoimiseksi.
Liittyy luvun 2 tilaukseen (1 % keskitehosta ≥ 2 s ikkunan yli = 1 tauko 100 jaksosta).

**TILAUS-M — kuristin säädetään paineeseen pääistunnon asettamalla syklillä, ei kierroksina** (28.9.2026, tämä
istunto). Ensin: "kun aktivoit sen niin uutto nappi toimii täydellä pumpun teholla. sanot kun olet aktivoinut ja
kerrot mihinkä paineeseen haluat minun säätävän kuristimen … kun säädetty niin kuittaan sinulle että säädetty".
Tarkennus samana päivänä: "pumppu toimii säädössä joka toisella syklillä eli 25 kertaa sekunnissa". Vian jälkeen:
"asetat itse syklin keittimelle ja minä säädän paineen kuristimesta. tämä on erittäin tärkeää koska säätöruuvin
kautta vääntäminen on erittäin epätarkkaa". Toteutus `kuri:1` (RAM, uuttonappi → pumppu 20 ms päällä / 20 ms pois,
setti 20260928-kuri3). Jokainen kuristimen asento annetaan paineena, ei kierroksina. Iskutaajuus:
"silloin kun minä säädä 8 bar niin sinä annat 24 sykliä pumpulle sekunnissa. Pienemmissä paineeissa on syytä antaa
vähemmän syklejä" → `kuri:<n>` = n iskua/s (kuri4); samana päivänä "korjaa ensin säätö 25 iskua". Kuittaus: "jatkossa
tiedät että säätö on tehty kun uutto nappi on otettu pois ja tarkastat datasta että oikea paine on asetettu" →
valmis = `KURI_END reason=switch`, paine tarkistetaan KURI-riveiltä (filt viimeiset ~2 s), ei odoteta sanallista kuittausta.
Etäkäynnistys testiuutoille sallittu vain ilmoitettuna etukäteen ja käyttäjän kuitattua valmiuden.

## 2d. Tilaus — lämmitystarve lasketaan virtauksesta, ei lämpötilasta (28.9.2026, tämä istunto)

> "lämpötila sensorin luku ei ole luotettava keino laskea lämmitystä uuton aikana. tämä pitää
> laskea virtauksen kautta"

> "lämmitystarve lasketaan siis säiliössä vaihtuneen veden perusteella"

> "Pumpun ja paineen suhde kertoo myös virtausmäärän"

**TILAUS-N — uuton lämmitystarve lasketaan kattilaan vaihtuneesta vedestä (virtauksesta), ei
lämpötila-anturin lukemasta.** Virtaus: vaa'an virtaus näyttää alussa nollaa, kunnes kahvi tippuu
kuppiin; kun pumppu käy täysillä ja paine on alhainen, vettä virtaa vapaasti (jos säiliössä on
vettä) — uuton alussa lämmityksen pitää siis olla tehokas. Virtausmäärä arvioidaan pumpun ja
paineen suhteesta: käytä Ulka EP5:n valmistajan virtauskäyrää eri paineissa; himmennin
(vaiheohjaus) vaikuttaa merkittävästi pumppuun, joten käyrän virtaama on tarkistettava
himmennyksessä laitteella. Oma pakettinsa EXPRESSO-LAMMITYS-VIRTAUS, ei osa
EXPRESSO-TEMPSTALE-JA-OLETUS-korjausta.

**TILAUS-O — uuton aikana paine mitataan joka jaksossa, eikä yksikään pumpun jakso jää pois tai tule ylimääräisenä viiveen takia.**
Käyttäjä 20.10.2026: "ehdoton vaatimus uuton aikana on että paine saadaan mitattua joka syklin aikana ja yhtään
pumpun sykliä ei saa jäädä pois eikä tulla ylimääräisiä viiveen takia". Koskee kaikkia uuton vaiheita (esiuutto,
nousu, pito). Mittari: EU_END/EB_END `miss` ja `late` = 0, eikä jaksoissa ole aukkoja (`cyc_n` > 0 joka jaksolla).
Tilanne 20.10.2026: ei täyty — testiuutoissa `miss` 26–116 ja keruu- ja vuorokatkot 60–200 ms (`paketit/GC-UUTTO.md`).
Seuraus suunnitteluun: hallittu keruu tauon kohdalle ei riitä, jos keruu voi kestää yli jakson. Uuton ajaksi
tarvitaan keruuton (allokaatioton) silmukka tai ajoitus, johon keruu ei ylety.

**TILAUS-P — lepotilan (IDLE) kattilalämpötila pysyy tavoitteessa ±0,05 °C, mitattuna 10 s keskiarvoista.**
Käyttäjä 21.10.2026: "Iddle tilan lämpötila vaihtelu pitää olla max +-0.05 celsius astetta"; mittaustapa
AskUserQuestionilla 21.10.2026: 10 s keskiarvo (ei säätimen 250 ms lukema eikä minuuttikeskiarvo). Toteutus:
PI-säätö (käyttäjän valinta 21.10.2026), IDLE-jakso 5 s (käyttäjä 21.10.2026 "5s jaksot iddle tilassa").
Mittari: DIAG_MIN-rivin 10 s keskiarvojen min ja max tavoitteeseen nähden, tasaantuneessa lepotilassa (ei uuton,
höyryn, kuuman veden tai tavoitteen vaihdon jälkeistä tasaantumista). Tilanne 21.10.2026: ei täyty —
minuuttikeskiarvot 97,82–98,07 °C tavoitteella 98 (af9cdcc).

**TILAUS-Q — thermal stability (−10…+10) lasketaan ylläpitotehon tarpeesta ja näytetään äpissä.**
Käyttäjä 21.10.2026: "Ota huomioon että ylläpito teho tarve muuttuu keittimen ollessa pitkään päällä ja keittimen
rungon ja muiden osien lämmitessä. Tämä arvo lasketaan ja nimetään thermal stability. Asteikko 0-1. Tämä pitää myös
näkyä äpissä. Myös vesisäiliön vesi lämpiää." Vesisäiliö = keittimen oma säiliö, josta boileri ottaa uutta vettä (käyttäjä 21.10.2026). Lämmönsäätö (TILAUS-P) ei saa olettaa ylläpitotehoa vakioksi; PI:n
integraali seuraa sitä. Asteikko korjattu (käyttäjä 21.10.2026): "Thermal stability onkon -10 - +10. -10 keittimen
vaativan paljon enemmän lämmitystehoa tavoite lämpötilan ylläpitämiseen. Stabiili piste Johon lämmitystarve jää vakioksi
pitkällä aikavälillä on nolla. +10 keittimen runko on pitkästä höyryilasta lämmennyt normaalia kuumemmaksi. Keittimen
boileri jäähdytetty viileällä vedellä mutta läämitystarve pieni koska laite kokonaisuudessaa kuuma." Eli 0 = pitkän
aikavälin vakio ylläpitoteho, −10 = runko kylmä (tarve paljon suurempi), +10 = runko normaalia kuumempi (tarve pieni).
Äpin näkymä: skooppi expresso-ios.

**TILAUS-R — jokaisella käyttötilalla on oma, erikseen kalibroitu lämmönsäätö.**
Käyttäjä 21.10.2026: "Keittimen eri käyttötiloilla pitää olla eri lämmön säätö asetukset. Esim brew tilan lämmitys
siten että uuton jälkeen lämpötila on mahdollisimman tasaisesti tavoite lämpötilassa ilman erityistä lisälämmitystä,
brew jälkeinen lämmitys nopeasti takaisin tavoitelämpötilaan. Nämä kaikki ovat niin merkittävästi erilaisia että ne
pitää olla erikseen kalibroituna". Tilat vähintään: lepo (IDLE, TILAUS-P), uutto (BREW: lämpötila uuton jälkeen
tavoitteessa ilman lisälämmitystä; vrt. TILAUS-N), uuton jälkeinen palautus (nopeasti tavoitteeseen), höyry,
kuuma vesi. Kalibrointi tilakohtaisesti laitteen datasta.
Käyttäjä 21.10.2026: "Huomioi että ylilämpeneminen on huomattavasti hitaampi korjata" — ylitys korjaantuu vain
häviöillä (~1,4 °C/min 98 °C:ssa), vaje lämmittimellä nopeasti: säätö ja oppi suosivat vajetta ylityksen sijaan.
Käyttäjä 21.10.2026: "Ota huomioon että höyrystyksen aikana vettä poistuu boilerista ja tämä muuttaa
lämpökäyttäytymistä" — höyryssä kattilan vesimäärä (lämpömassa) pienenee ajon aikana, ja vajaa kattila käyttäytyy
eri tavalla myös höyryn jälkeen, kunnes vettä on pumpattu takaisin. Höyryn säätö ei voi olettaa vakiomassaa, ja
lepo- ja uuttosäädön opit (PI, brew_heat_k, thermal stability) eivät saa oppia vajaan kattilan ajalta virheellisesti.

## 3. Tilaus — käyttöliittymä ja kalibrointi (17.9.2026, `[37ac4102]`)

> "Tee paineeseen esiuuttoa ja varsinaista uuttoa varten slider kuten lämpötilalla on. Esi uuton
> asteikko 1-4bar ja uuton asteikko 5-10bar"

> "Tee viellä settings sivulle paine kalibrointi. Kalibroinnille on kaksi vaihetta. Ensimmäisessä
> vaiheessa keitin antaa 10s ajan vettä esiuuttopaineella. Tämän jälkeen kysytään että mikä oli
> painelukema. Käyttäjä syöttää arvon ja keitin korjaa laskelman ja tekee uudestaan testin kunnes
> paine on oikein. Tämän jälkeen vastaava tehdään uuttopaineella ja käyttäjältä varmistetaan
> tulos"

> "tallenna puhelimeen nykyinen pico firmware joka voidaan tarvittaessa palauttaa puhelimen
> ohjelmalla"

## 4. Laitetiedot — mitä käyttäjä on kertonut koneesta

**Paineanturit, kaksi eri paikkaa** (19.9.2026, `[04103924]`):
> "Paineen referenssimittari on samassa kahvassa kuristumrn kanssa. Keittimen oma paine mittari on
> on vesilinjassa pumpun jälkeen"

Tästä seuraa, ettei kahta lukemaa voi lukea samanaikaisesti:
> "tämä testi ei ole mahdollinen jossa molemmat luettaisiin tasan samaan aikaan. silloin pitäisi
> olla molemmat mittarit kytketty mikrokontrolleriin ja se ei tässä hetkessä onnistu."

**Jäännöspaine ja lämpölaajeneminen** (19.9.2026, `[04103924]`):
> "Lepotilassa paine sattaa jäädä järjestelmään. Samoin myös valmiustilassa kuten myös paine
> saattaa hieman elää johtuen lämpötilasta ja eri osien ja veden lämpölaajenemisesta"

**Paineen purku — käyttäjän antama menetelmä** (19.9.2026, `[04103924]`):
> "Nollan saat aikaiseksi siten että sammutat lämmittimen teet solenoidilla on off cycle niin kauan
> että paine purkautuu"

Tämä on suora vastaus ongelmaan, joka kaatoi yhdeksän kaappausyritystä 19.9.2026 (`overpressure`,
`n=0`): purkuaskel oli tilattu jo aiemmin, mutta sitä ei ollut `pcap`- eikä `phold`-polulla.

**Boilerissa on ilmaa** (18.9.2026, `[3a3bf74d]`):
> "ota huomioon että boilerissa on joskus ilmaa. tämä voi vaikuttaa siihen kauanko kestää että
> vettä alkaa tulemaan pumpun käynnistämisen jälkeen."

Sama toistui 19.9.2026: "ei kerennyt nostaa painetta kunnolla. järjestelmässä oli todennäköisesti
ilmaa. tee uudestaan" ja "tyhjensin ilman jo itse."

**Solenoidi päästää vettä kaukaloon uuton lopuksi** (18.9.2026, `[3a3bf74d]`):
> "Solenoidi purskauttaa aina uuton lopussa vettä sinne vaikka uuttopään alla olisikin astia."

> "Huomioithan pois noston jälkeen että kaukalon painon kuuluu nousta koska solenoidi päästää
> lopuksi sinne vettä. Tämä on syytä erottaa kun lasketaan kuppiin mennyt todellinen paino. Myls
> syytä huomata että se vesi menee vaa-alle vasta uuton pysäytyksen jälkeen."

**Painojakauma vaa'an antureilla** (18.9.2026, `[3a3bf74d]`):
> "Keittimen kaukaloon menevä vesi jakautuu suhteellisen tasaisesti sensorien välissä kun taas
> kuppiin menevä vesi ajautuu enemmän vasempaan reunaan. Asiaa monimutkistaa se että jos kaukalossa
> on jo valmiiksi vettä niin jakauma on kaksi osainen."

**Vaa'an lukema ja virtalähteet** (18.9.2026, `[04103924]`):
> "Ota huomioon että voiko vaaka näyttää erilukemia keittimen ollessa pois päältä johtuen eri
> virtalähteiden jännite eroista mistä vaakojen vahvistinpiirit saavat virran."

**Mitatut painot** (18.9.2026, `[3a3bf74d]`): tyhjä kaukalo ilman ritilää 170,0 g; kaukalo täynnä
398,8 g / 454,5 g / 442,2 g eri ajoissa; koeastia 50,7 g; kuppi 293,9 g. 19.9.2026 mitattu tyhjä
kaukalo + ritilä 460 g.

**Kuristin on lisätty kehitystä varten** (17.9.2026, `[37ac4102]`):
> "pistän myös kiinni korin tilalle kahvan jossa on säädettävä neulaventtiili pohjassa. tämä auttaa
> sinua kun testaat uuton."

Kuristin ei aina mahdu paikalleen (18.9.2026): "kuristus venttiili ei ole ny kiinni koska se ei
mahdu paikalleen joten vesi virtaa lähes vapaasti".

Kuristin lämmitetään ennen laiteajoa (24.9.2026, laitetesti 3:n ylipainekatkon jälkeen): "kuristin
saattaa vaatia lämmityksen. aja ensin vettä siitä läpi 7bar painetta ylläpitäen kunnes 7bar
paineessa pumppua ei tarvitse enää rajoittaa". Käyttäjä säätää venttiilin itse ("säädän itse
venttiilin viellä"); säädön jälkeen "paine on nyt keskimäärin relu 8 bar kun pumppua ajetaan
jatkuvasti".
Lämmityksen tavoitepaine ei ole vakio (24.9.2026, kun lämmitys ajettiin `bp:7`:llä): "tämä ei
pitäisi olla vakio vaan tavoite paine pitää ottaa siitä kun pumppu käy jatkuvasti ja paineen
keskiarvon merkittävä kasvu pysähtyy".

**USB-hubin tarkoitus** (17.9.2026, `[37ac4102]`):
> "Koko hubin idea on ladata samalla kun puhelimella on yhteys picoon. Tämä piti olla oikeanlainen
> pd passthrough hub"

Hub on OnePlussan ja Picon välissä, ei Macin ja Picon.

## 5. Turvallisuus — käyttäjän asettamat rajat

**Lämmittimen rele voi jäädä päälle** (17.9.2026, `[37ac4102]`):
> "hyvä että huomioit että jos pysäytät pico firmware niin lämmittimen rele saattaa jäädä päälle
> asentoon ja keitin ylikuumentua mikäli keitin on päällä."

**Releet alas ennen toimenpiteitä ja heti käynnistyksessä** (7.10.2026):
> "Äärimmäisen tärkeää että releet ajetaan aina alas ennen toimenpiteitä jos on vaara että toimenpiteet
> siirtää pico pois ajosta tai pico kaatuu"

Jos rele (esim. lämmitin) on päällä nollauksen alkaessa, se jää päälle, kunnes Pico asettaa sen 0:aan.
Tämän vuoksi releet ajetaan 0:aan heti `boot.py`:n alussa ennen muita alustuksia tai viiveitä.

**TILAUS-RELEET-ALAS — releet ajetaan aina alas ennen toimenpiteitä ja heti käynnistyksen alussa (`boot.py`), jotta mikään rele ei jää päälle nollauksen tai vikatilanteen aikana.**

**Kaukalon painoraja koskee testejä, ei omaa uuttoa** (18.9.2026, `[3a3bf74d]`):
> "tehdään testejä varten turvaraja vesikaukalon painolle että kun ajat testejä et puske niin
> paljon vettä läpi että kaukalo vuotaa yli. Tämä vain siis testejä varten nyt. myöhemmin otetaan
> normaali käyttöön mutta silloin turva rajat pitää olla eri johtuen esim kupin painosta."

**Turvaominaisuuden katoaminen on oma vikaluokkansa** (19.9.2026, `[ffb87b9c]`):
> "Sammutin virran keittimestä koska olit ajamassa vettä niin paljon kaukaloon että se olisi tullut
> yli. Miksi kaukalon turvaraja ei ollut käytössä"

> "Pelkkä säiliö ongelman korjaus ei ratkaise asiaa. Kyse on siitä että turva ominaisuus hukkui
> matkan varrella. Tämmöisillä asioilla voi olla hengenvaarallinen vaikutus jossakin tapauksissa.
> Ongelma pitää perusteellisesti selvittää mutta selvitys tehdään myöhemmin."

**Vibration pump -PWM:n turvallinen kohta** on tilauksen kohta, jota ei ole vielä ratkaistu; se
riippuu SSR-40DA:n tyypistä, joka on yhä tarkistamatta.

## 6. Menetelmäohjeet — miten käyttäjä haluaa mitattavan

**Mittauksen laskuri alkaa vasta tavoitteesta** (19.9.2026, `[04103924]` ja `[eeb16a3f]`):
> "testin laskuri pitää alkaa vasta kun paine on saavutettu"

> "Ajan mittaus pitää alkaa vasta sitten kun tavoite paine asetettu. Sen mukaan pitää miettiä
> paljonko aikaa tarvitaan"

> "myös overshoot pitää huomioida siten että jos sitä tapahtuu niin se ei aloita laskuria"

**Paineen nosto vie aikaa — älä pyydä ihmistä valvomaan hetkeä, jota ei vielä ole** (19.9.2026,
`[eeb16a3f]`):
> "Olet tehnyt virheen joka toistuu useasti. Pyydät minua valvomaan jotain prosessia tietyssä
> paineessa mutta et ole ymmärtänyt että paineen nostaminen saattaa vaatia jonkun aikaakin pumpun
> päälläoloa jotta paine saa nostettua"

**Pumpun sykli pienemmäksi tavoitteen lähellä** (19.9.2026, `[04103924]`):
> "tavoite paine -0.5bar tehdään pumpun täydellä syklillä ja tästä eteenpäin pienellä syklillä. …
> Testaa mikä sykli pitää mahdollisimman tasaisena paineen sekä 2bar että 8 bar"

**Kaukalovahdin kalibrointimenetelmä** (18.9.2026, `[3a3bf74d]`):
> "kalibroidaan turvaraja siten että pistän kaukaloon vettä maksimiin asti. sinä seuraat vaakaa.
> minä liikuttelen kaukaloa hieman n. 5s välein. kun kaukalo on ollut noin 3s koskemattomana otat
> arvon ylös. liikuttelulla on se tarkoitus että sensorit voi antaa vaihtelevia arvoja joten tällä
> saadaan ne vaihtelut poimittua"

**Virtaus on laskettava reaaliaikaisesti** (18.9.2026, `[9ce73b62]`):
> "Virtaus pitää saada laskettua hyvin reaaliaikaisesti"

**Testin käynnistys uuttonapista** (18.9.2026, `[04103924]`):
> "testin kuuluu alkaa siten että minä pistän uuttonapista testin käyntiin"

**Vapaa säätö kesken ajon** (18.9.2026, `[04103924]`):
> "Säätö ei toiminut. Minun pitää saada vapaasti säätää venttiiliä ja sinä pidät tasaisesti 2,2g
> virtauksen"

**Referenssilukema tulee ihmiseltä, ei koneelta:** paineen kalibrointi tehdään eri kuristinasennoissa
niin, että kone ajaa tavoitteen ja käyttäjä kertoo mittarin lukeman (19.9.2026, `[04103924]`).

**Ei painetavoitetta eikä painekysymyksiä testien esiehtona** (23.9.2026, `[1bcdd40c]`, kun
pääistunto kysyi 7 barin ja kuristimen asennon ennen vkello-ajoja):
> "Älä kysele enään paineista. Tämä on annettu jo tieto aiemmin. Nyt me ei mitata paineita.
> Tärkeintä on se että huomaat koska paine ei enään nouse"

Eli nousuvaihe päättyy tasanteeseen, jonka kone tunnistaa itse (vkello 9954c2e, sama sääntö kuin
pcap `target|plateau`), eikä käyttäjältä kysytä painetta, kuristimen asentoa tai kiinteää
bar-tavoitetta.

**Laiteajo alkaa puretusta järjestelmästä, ei pakkautuneesta paineesta** (26.9.2026, EXPRESSO-ESIUUTTO-AVOIN,
kun pääistunto mallinsi täyttämättömän, valmiiksi paineistetun kiinni-tilan):
> "Tämmöinen tilanne jossa paine on pakkaantunut valmiiksi ei ole todellinen koska painetta täytyy
> kerätä. Testejä varten olen jo aiemmin antanut ohjeen paineen tiputtamiseen solenoidin kautta"

Eli TILAUS-H:n purku ennen jokaista esiuuttoajoa (`pico_dev.py hold` ajaa `pvent`in ensin, 0028dff).

**Lähes kiinni -kuristin ei ohjaa suunnittelua** (26.9.2026, EXPRESSO-ESIUUTTO-AVOIN, kun pääistunto
kysyi ff:n valintaa, joka yliarvioi kuristimen käännyttyä avoimesta lähes kiinni):
> "Tämä tilanne että kuristin on näin kiinni ei ole realistinen uuttotilanne. Jos vastapaine on näin
> kova niin kahvi menee jokatapauksessa pilalle. ja se ei tule määrittää toimintaa liikaa"

## 7. Työtapa — miten käyttäjä haluaa työskenneltävän

**Kehityksen on toimittava ilman käyttäjän fyysistä osallistumista** (17.9.2026, `[37ac4102]`):
> "suunnittele itse firmwareen tila missä ajat ensin releet alas ennen kuin teet operaation.
> kehitys täytyy toimia täysin ilman minun osallistumistani fyylisiin toimenpiteisiin."

**TILAUS-AUTONOMIA — kehitys toimii ilman käyttäjän osallistumista fyysisiin toimenpiteisiin.** Tunnusrivi
lisätty 7.10.2026 (V-214), jotta purun VAATIMUKSET ja vaatimukset.mjs näyttävät yllä olevan vaatimuksen
(17.9.2026).

**Flash ilman virrankatkaisua** (19.9.2026, `[04103924]`):
> "flash pitää onnistua katkaisematta virtaa. hakemasi tiedot picon hallinnasta oneplus avulla on
> puutteelliset. tee huolellinen haku vanhoista tiedoista mitenkä tämä hallinta onnistuu ja tee
> kattava ohje tiedosto"

Tuloksena `PICO-HALLINTA.md`.

**Keitin on myös käytössä:** kone irrotetaan kehityksestä kahvinkeittoa varten ("Irroitin jeittimen
puhelimesta koska sillä pitää keittää kahvia"), ja kehitys jatkuu vasta kun käyttäjä ilmoittaa.

**Todellinen arvo korjataan, ei asetusta kierretä** (19.9.2026, `[04103924]`):
> "en halua säilyttää nykyistä asetusta vaan haluan että todellinen paine muuttu 8bar kohdalle"

**Tiedon hukkaaminen on vika, ei kitka** (19.9.2026, tämä istunto):
> "Tämä on jo toinen kriittinen unohdus tässä prosessissa. Jostain syystä hukkaat tiedot."

Tämän tiedoston olemassaolo on vastaus siihen. Prosessin puoli on kirjattu skooppiin
`claude siirto` riveinä `SIIRTO-VAATIMUS-KATOAA` ja `SIIRTO-OMIN-PAIN-TIIVISTETTY`.

**Laiteajot vain 2,5 barin pidolla, kunnes esiuutto on hyväksytty** (26.9.2026, `[7dac0472]`):
> "kaikki testit tehdään ensin 2.5 bar pidolla kunnes tämä osuus on valmis ha hyväksytty"

Toteutus: `pico_dev.py hold <s>` (pysäyttää ennen 8 barin uuttoa). Poistuu vasta käyttäjän hyväksynnällä.

**Kaukaloa ei tarvitse tyhjentää joka ajolla** (26.9.2026, `[7dac0472]`):
> "Säiliössä on riittävästi tilaa. Sen ei tarvi olla joka kerta tyhjä. Turvaraja on asetettu"

Ajon hyväksyntä kysyy läsnäolon ja säiliön veden; kaukalon raja on `limits=wmax:720`.

**Himmennys PID-tyyppiseksi** (26.9.2026, `[7dac0472]`):
> "kuulen ajosta että siinä on aika pitkiä pumppu jaksoja. Tämä kertoo minulle siitä että pumpun
> ohjaus on viellä hieman liian on/off tyyppinen eikä "himmennys" toiminta ole viellä otettu kunnolla käyttoon"
> "himmennys toiminnolla pitää olla pid tyyppinen ratkaisu"

Toteutus 26.9.2026: esiuuton PI + D (`EU_KD`); nousu on yhä täysi teho ja 8 barin uutto vanha säädin
(avoin asia 24). Puhelimen värinä ja latausääni pois käyttäjän pyynnöstä samana päivänä.

**Pumpun ohjaus käyttöön oikeissa uutoissa, sitten uuttojen siirto puhelimeen** (26.9.2026, `[59482d2c]`):
> "Pumpun ohjaustestit pitää tehdä loppuun ja ottaa käyttöön ajossa. Tämän jälkeen viellä varmistetaan
> että jatkossa kun keitän kahvia niin kaikki uutot siirtyvät puhelimeen. Tämä on jo aiemmin tehty
> ominaisuus"

Laajuus samassa istunnossa: käyttäjä valitsi "Myös 8 bar ensin" — TILAUS-K vaiheet 3–4 toteutetaan ja
testataan ennen kuin mitään otetaan käyttöön (hylätty "Esiuutto nyt, 8 bar myöhemmin"). Uuttojen siirto
ei toiminut 26.9.2026: elokuun `brew_logger` puuttuu nykyisestä firmwaresta (rekisteri, Käyttöönottoketju).

## 8. Avoimet käyttäjän havainnot, joita ei ole vielä selitetty

- **Paineen heilunta ja ylireagointi** (19.9.2026): "Paine oli riittävän tarkka. Tuo heilunta ja
  ylireagointi pumpulta on saatava kuriin." Johtava ehdokas on dutyn kvantisointi; keskiarvoikkunan
  pidentäminen on kumottu mittauksella.
- **Paineen hallinnan viive uuton aikana** (17.9.2026): "paineen hallinnassa on joku vakava viive
  uuton aikana. paine välillä overshoottaa ja toisaalta myös tippuu noin 6 bar asti." Huomaa
  käyttäjän tarkennus 19.9.2026: "tämä paineen vaihtelu ei vastaa uuton aikaista. tämä on lukitun
  vesilinjan mittaus" — lukitun linjan mittaukset eivät siis todista uuton aikaisesta käytöksestä.
- **Jeweller-vaaka hienosäätöön** (18.9.2026): käytettävissä, jos tarkkuudesta tulee järkevä.

## 9. Tilaus — Äpin ja keittimen jatkotehtävät (26.10.2026, `[e7b99f66]`)

> "1 Äpissä päätilassa näkyy nyt oletuksena punainen bluetooth logo kun yhteyttä ei ole viellä saavutettu. Tässä pitäisi olla wifi ikoni mutta harmaana. Se muuttuu punaiseksi jos yhteys ei löydy 20s kuluttua.
> 2 keittimen tila iddle kuuluu olla vasta silloin päällä kun oikea lämpötila on suurinpiirtein asettunut kohdilleen. Jos lämpötila ob viellä heilahtelu vaiheessa se kuuluu olla stabilizing. Jos se on reilusti alle niin warming up. Jos se on yli se on cooling down.
> 3 tare nappi kuuluu olla suoraan painon arvon alapuolella.
> 4 painon tunnistus pitää kehittää älykkäämmäksi siten että se tunnistaa paljonko vettä on tullut kaukaloon. Myös jos keittimen kaukalo on tyhjennetty keittimen ollessa sammuksissa.  Myös kupin paino ja ulkoisen vaan paino täytyy olla tuttu ja tunnistettu kun ne lisätään keittimen kaukalon päälle.
> 5 vaakatilassa ei kuulu näkyä: - lämpötilaa eikä painetta lukuna. Nämä näkyy graafissa. - yhteyden tila symboli ja lepotila symboli.
> 6 vaakatilassa freeze nappi pitää olla pienempi ja pyöreä. Siinä kuuluu olla tekstin sijaan play ja pause symbolit.
> 7 vaakatilassa graafin pitää ottaa tila paremmin haltuun.
> 8. Graafiin pitää tehdä uusi piirto flow lukemalle"

## Lähteet

Istuntotranskriptit `~/.claude/projects/-srv-work/<id>.jsonl`: `37ac4102` (17.9.), `3a3bf74d`,
`9ce73b62`, `04103924` (18.–19.9.), `eeb16a3f`, `ffb87b9c`, `3b58249e` (19.9.). Lainaukset on
poimittu käyttäjän omista viesteistä, kirjoitusasu mukaan lukien.
