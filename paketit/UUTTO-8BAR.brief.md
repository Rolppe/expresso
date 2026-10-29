# EXPRESSO-UUTTO-8BAR — TILAUS-K vaiheet 3–4 (nousu 2,5 → 8 bar ja 8 barin pito), isännällä

VAATIMUS: TILAUS-K, TILAUS-L, TILAUS-I, TILAUS-J, TILAUS-B, TILAUS-C, TILAUS-F, TILAUS-G

Vaatimusten kohdat: TILAUS-K vaiheet 3 ja 4; TILAUS-L askel yksi jakso, delta-sigma; TILAUS-I paineesta luettu
vaihe, viive 37–41 ms; TILAUS-J kello kulkee vaiheiden yli; TILAUS-B vaihe paineesta, ei laitteistosta; TILAUS-C
8 barin pito käyttäjän kääntäessä kuristinta; TILAUS-F taajuus mitataan joka ajolla; TILAUS-G esiuuton nousu
mittausikkunana, ennallaan.

Skooppi `infra expresso`. Lue ensin kokonaan `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md` (luvut 2c, 6 ja 7 erityisesti)
ja `Infra/iot/expresso/paketit/VAIHESEURANTA.md` (koko, erityisesti luvut "Rampin loppu" ja "Laitteella 27.9.2026").

## Tausta

Esiuutto (TILAUS-K vaiheet 1–2, `pico/functions.py` `pre_infusion_phased`, `pim:1`) on käyttäjän hyväksymä
(27.9.2026, 651afec, ajot at–aw). Sen jälkeen `run_shot` siirtyy vanhaan uuttosilmukkaan (`PumpPressureController`,
17 ms askel, 100 ms ikkuna), jossa 8 barin alussa on ~1 barin pudotuksia (6,8 bar), ylitys 8,3 ja b-ajossa ~1 s
7,4–7,6 hitaan integraalin takia (`paketit/PAINESAADIN-HEILUNTA.md`, lokit `testit/esiuutto-20260925-{a,b}-pim1.log`).
Käyttäjä valitsi 26.9.2026 "Myös 8 bar ensin": vaiheet 3–4 toteutetaan ja testataan ennen käyttöönottoa. Kellosta
käyttäjä valitsi (a) 27.9.2026: vapaa kello matalan tarpeen esiuuttopidossa, **lukitus vaiheen 3 nousussa**.

## Tee

1. **Laitteen 8 barin malli olemassa olevista lokeista, ennen koodia.** Sovita `testit/esiuutto_smoke.py`:n Plant
   niin, että se toistaa 2,5 → 8 barin nousun ja 8 barin pidon: uuttovaiheen TS-rivit lokeissa
   `testit/esiuutto-2026092{4,5,6}-*-pim1.log` (ne, joissa uutto ajettiin), `testit/klamp-*.log` (7–9 bar jatkuvalla
   pumpulla) ja `testit/vsweep-20260924-a.log` (7,82 bar: 10 ms tauko −0,61…−0,83 bar). Nykyinen kaasujousto
   (isku ∝ absoluuttinen paine², kalibroitu 2,5 barissa) antaisi 8 barissa ~3 bar/isku, mikä on todennäköisesti liikaa:
   harkitse joustoa `vakio + kaasu/p_abs²`. Kirjaa sovituksen luvut (nousunopeus 2,5 → 8, iskukoko 8 barissa, vuodon
   tau, viive) raporttiin. Jos data ei riitä johonkin parametriin, sano se äläkä keksi lukua.
2. **Vaiheet 3–4 `pre_infusion_phased`:n jatkoksi samaan silmukkaan**, jotta kello, delta-sigma, vuoronvaraus (`vv`),
   myöhästymisvahti ja hallittu keruu jatkuvat katkeamatta. Kun esiuuton pito päättyy (`end_t`) ja uutto on valittu,
   silmukka ei pääty vaan siirtyy vaiheeseen 3 tavoitteena `brew_data.get_brew_pressure()`:
   - **Vaihe 3 (nousu):** täysi sykli, kunnes ennuste p5 + nousunopeus × opittu jälkinousu ≥ tavoite − marginaali, sitten
     ramppi ja loppulähestyminen kuten vaiheessa 2 (TILAUS-K: "yliampumisen ehkäisy samoin kun preinfusion paineen
     nosto vaiheessa"). Uuton jälkinousu, ff, G ja tau opitaan **erillään** esiuuton arvoista (eri paine, eri jousto) ja
     tallennetaan settings.txt:hen omilla avaimillaan (katso `save_settings`/`load_settings`); vanha tiedosto ilman
     avaimia → oletukset.
   - **Kello lukittuu vaiheen 3 nousussa** (käyttäjän valinta a): nousun I/Q-ikkunat eivät nyt opeta (gate=−1), koska
     väreilyn viive riippuu paineesta (aq:n nousussa z 8,1 → 5,0 ms). Tutki `pico/verkkokello.py`, `testit/vkello_rise_learn.py`,
     `testit/vkello_rise_smoke.py` ja `testit/vkello_dpdt*.py`: onko painekorjattu nousuoppi jo olemassa. Valitse
     menetelmä, jolla kello lukittuu viimeistään vaiheen 4 alkuun ilman nousun harhaa, ja perustele se. Jos harhatonta
     menetelmää ei löydy, lukitse vaiheen 4 alussa pidon ikkunoista ja sano, ettei nousun lukitusta toteutettu (POIKKEAA).
   - **Vaihe 4 (pito):** delta-sigma ja PI(D) kuten vaihe 2, tavoite uuttopaine, kestää kunnes `keep_running()` on
     epätosi (uuttokytkin, `tshot`-aika, turvarajat). Pidon on seurattava kuristimen kääntöä (TILAUS-C): integraalin ja
     ff:n on sallittava tarve koko välillä 0…1 ilman lukkiutumista. Kellon korjaus jatkuu pidon ikkunoista.
   - **Uuton sivutoimet samaan silmukkaan:** lämmittimen pulssitus kuten vanhassa uuttosilmukassa (pois 100 ms, päällä
     50 ms); `set_pump_ratio` 1 s välein; kattilan lämpötilan luku (MAX31865 blokkaa ≥ 75 ms) **ei** vaiheissa 3–4 —
     lue se kerran uuton jälkeen ja kirjaa tämä koodikommenttiin. Virtaustila (`get_flow_mode()`) ohjautuu vanhaan
     silmukkaan ennallaan.
   - **Valinta:** uusi RAM-asetus `bim:<0|1>` `pico/commands.py`:hin samaan tapaan kuin `pim` (oletus 0, TS_START tulostaa
     `bim=`). Vaiheet 3–4 vain, kun `pim` = 1, esiuutto on päällä, virtaustila pois ja `bim` = 1; muuten vanha polku
     tavulleen ennallaan. `bim:0` + `pim:1` = hyväksytty esiuutto ja vanha uutto (A/B-vertailu).
   - **Lokit:** EU-rivit jatkuvat vaihesarakkeella 3/4. Esiuuton loppurivit (`EU_END`, `EU_END2`, `EU_VV`) eivät saa
     pysäyttää silmukkaa releen ollessa päällä: tulosta ne siirtymässä jonosta enintään yksi rivi jaksoa kohden, ≤ 255
     merkkiä/rivi. Uuton loppuun vastaavat `EB_END`-rivit (ylitys vaiheen 3 huipusta ja pidon 1. sekunnista, pidon
     keskiarvo/sd, iskut, poistot, late, miss, kello, opitut arvot). Vanhan polun `<label>_END`-rivi tulostuu myös uudella
     polulla samassa muodossa, jotta `pico_dev.py shot` ja analyysityökalut tunnistavat uuton lopun — tarkista, mitä
     `Infra/iot/expresso/pico_dev.py` ja `testit/esiuutto_analyysi.py` odottavat, ja päivitä analyysi lukemaan vaiheet 3–4.
   - Esiuuton vaiheiden 1–2 käytös **ei saa muuttua** (hyväksytty 651afec): kaikki nykyiset `esiuutto_smoke`-tapaukset
     pysyvät vihreinä samoilla luvuilla.
3. **Smoke:** uudet tapaukset `testit/esiuutto_smoke.py`:hin sovitetulla 8 barin mallilla (kohinaton + kohinaiset
   siemenet, pysähdykset ja keruu kuten tapaus 14):
   - siirtymä esiuutosta uuttoon: vaiheen 3 ylitys < yksi 8 barin isku, ei ~1 barin pudotuksia vaiheen 4 alussa
     (p5 ≥ tavoite − 0,5 pidon alusta), pidon 2–5 s keskiarvo ± 0,15;
   - kuristimen kääntö kesken pidon (tarve esim. 0,3 → 0,6 → 0,2): paine palaa kaistalle ~1 s:ssa, ei lukkiutumista;
   - kello: lukossa (2,5 sd < `EU_PHASE_OK_US`) viimeistään vaiheen 4 alussa, 10 ms tauot vaiheessa 4;
   - `vv=1`: late 0 releen ollessa päällä vaiheissa 3–4;
   - opitut uuttoarvot eivät muuta esiuuton arvoja, ja 2. ajo käyttää 1. ajon uuttoarvoja;
   - `bim:0` ajaa vanhan uuttosilmukan.
   Jokainen uusi tarkistus on osoitettava kaatuvaksi ilman korjausta (tai vanhalla uuttosilmukalla), kun se on mahdollista.
4. Aja kaikki smoket aikarajalla (esim. `timeout 600 python3 testit/esiuutto_smoke.py`) — jokainen erikseen, ilman
   putkea, paluukoodi näkyviin. Muut `functions`-smoket (`ls testit/*_smoke.py`) vihreinä.

## Älä

- Älä flashaa, älä aja laitetta (`pico_dev.py`, adb), älä committaa: pääistunto katselmoi ja committaa.
- Älä muuta esiuuton vaiheiden 1–2 vakioita tai logiikkaa muuten kuin siirtymän vaatimalla tavalla.
- Älä kysy käyttäjältä painetta tai kuristimen asentoa (KAYTTAJAN-TIEDOT luku 6).

## Raportoi (enintään 40 riviä)

Muutetut tiedostot; 8 barin mallin sovitetut luvut ja mistä lokeista; kellon lukitusmenetelmä ja perustelu (tai POIKKEAA);
smoke-tulokset komentoineen ja paluukoodeineen (uudet tapaukset: vanha vs. uusi luvut); avoimet riskit laiteajolle ja
ehdotettu laiteajon muoto (`pico_dev.py shot …`, mitkä RAM-asetukset ennen ajoa).
