# EXPRESSO-OHJEVAHTI — laitekomento ei lähde, jos se poikkeaa käyttäjän ohjeesta

| Kenttä | Arvo |
|---|---|
| Tunnus | EXPRESSO-OHJEVAHTI |
| Skooppi | infra expresso (yleistys koneistoon: `claude siirto`) |
| Tila | toteutettu 21.9.2026 (holdout vihreä), **asentamatta** — `.claude/settings.json` odottaa käyttäjän lupaa |
| Ajaja | r&d — toteuttaja-sonnet |

## Laukaisija

`paketit/OHJEPOIKKEAMAT-20260920.konteksti.md`: 20.9.2026 istunnossa 7 poikkeamaa käyttäjän
ohjeesta. 6/7 mekanismi B (ohje tiedossa, ohitettu omalla harkinnalla), 1 D (paketin oma sääntö
14 ohjeen edellä), 0 A (istunnossa ei tiivistystä). Sääntö 8 (`claude/TYOTAVAT.md:17-18`) oli
voimassa ja rikottiin — tekstisääntö ei riitä. Tarvitaan kone, joka näyttää poikkeaman
käyttäjälle ennen ajoa. Käyttäjän sanat: "olet ohittanut minun ohjeen omissa säännöissäsi"
(1f997ae0:640), "rupesit taas toimimaan vastoin ohjeistustani" (1f997ae0:1347).

## Sääntö

1. Käyttäjän laiteohjeet kirjataan `Infra/iot/expresso/OHJEKIRJA.json`:iin **sanatarkkana
   lainauksena** ja koneluettavana ehtona. Ehtotyypit:
   - `arvo`: komento + kenttä = arvo (esim. `pgap` `n` = 20; `pgap` `len_ms` = 5).
   - `kielto`: komento ei saa ajaa (esim. `mcal` kun "älä huolehdi paineesta").
   - `valivaihe`: ajojen väliin vaadittu käyttäjän toimi (esim. kaukalon tyhjennys).
2. `Infra/iot/expresso/ohjevahti.py` on Claude Coden `PreToolUse`-koukku Bash-työkalulle. Kun
   komento ajaa `pico_dev.py`:n laitetta muuttavan operaation (`cmd`, `shot`, `pcap`, `psweep`,
   `plen`, `pgap`, `pstep`, `phold`), se jäsentää komennon kentät `pico/commands.py:97-245`
   nimillä ja palauttaa päätöksen, jonka käyttäjä näkee:
   - joka laiteajo: komento selkokielisin kentin + jokainen siihen osuva ohjelainaus;
   - `ERO:` rivi jokaisesta `arvo`-ehdon poikkeamasta, `KIELTO:` rivi kielletystä komennosta;
   - `VÄLIVAIHE:` rivi, kun edellisestä laiteajosta ei ole kuitattu vaadittua välivaihetta.
   Lukevat operaatiot (`verify`, `capture`) ja `safe` päästetään läpi.
3. Tyhjä tai puuttuva ohjekirja ei ole lupa: näytetään "ohjekirja tyhjä".
4. Koukku koskee vain Clauden ajamia komentoja. Käyttäjän oma käyttö ei kulje sen läpi
   (raja: `TURVAKATO.md` "vaaka sääntö ei koske omaa ajoa vaan testejä").
5. Claude ei muokkaa ohjekirjan riviä hiljaa: muutos kirjataan uutena rivinä, jossa on käyttäjän
   uusi lainaus; vanha rivi jää `korvattu`-merkinnällä.

## Hyväksyntä

Testiskripti syöttää koukulle 20.9. tapaukset ja odottaa: `pgap:7.0:40:350:5:20` vs. ohje n=20
→ `ERO`; `mcal:500` kiellon aikana → `KIELTO`; kaksi `pgap`-ajoa putkeen kaukalo-välivaiheella
→ `VÄLIVAIHE`; ohjeen mukainen ajo → ei ERO/KIELTO-riviä. Asennus `.claude/settings.json`:iin
vaatii käyttäjän luvan (pysyvä asetus).

## Päätös: deny poikkeamalle, ask muulle (suunnittelija, 21.9.2026)

Lähde: code.claude.com/docs/en/hooks-guide.md (claude-code-guide-haku 21.9.2026). `deny` peruu
kutsun ja syöttää syyn Claudelle — toimii kaikissa tiloissa. `ask` näyttää käyttäjälle kehotteen,
mutta dokumentti sanoo sen muualla muuttuvan kieltäytymiseksi, eikä auto-tilan käytös ollut
yksiselitteinen. Siksi:

- `ERO`/`KIELTO`/`VÄLIVAIHE` → `deny`. Claude ei voi ajaa komentoa, vaan joutuu kysymään.
- Ohjeenmukainen laiteajo → `ask`, jonka syy näyttää ohjelainaukset. Käytös mitataan
  työpöytäsovelluksessa asennuksen jälkeen; jos `ask` kieltäytyy auto-tilassa, vaihdetaan `allow`.
- Välivaiheen kuittaus: tiedosto `OHJEKIRJA.json` kenttä `kuitattu`, jonka Claude kirjoittaa
  **vain** käyttäjän chat-vastauksen jälkeen, lainaus mukaan.

Rajoite, sanottu ääneen: koukut ladataan tiedostosta lennossa, joten Claude voisi poistaa koukun
muokkaamalla `.claude/settings.json`:ia. Vahti ei estä tahallista ohitusta, vaan hiljaisen:
jokainen ohitus jättää jäljen gitiin ja näkyy käyttäjälle. Asetusmuutos kysytään aina (TYOTAVAT 8).
