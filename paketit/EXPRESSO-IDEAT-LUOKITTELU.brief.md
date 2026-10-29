# EXPRESSO-IDEAT-LUOKITTELU

VAATIMUS: ei koske — pelkkiä dokumenttikorjauksia, ei menetelmävalintaa eikä laiteajoa.

## Task
Korjaa kolmen IDEAT-vikarivin (V-062/V-197, V-149, V-214) vanhentuneet dokumenttikohdat expresson ohjeisiin.

## Files
may:
- `Infra/iot/expresso/KEHITYSYHTEYS.md` (vain luku "OnePlus-akkuvahti (palvelin)")
- `Infra/iot/expresso/PICO-HALLINTA.md` (vain luku "8. Akku ja OTG")
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md` (vain lisäys lukuun 7)

must not:
- mikään muu tiedosto, erityisesti `pico/`, `*.py`, `*.sh`, rekisterit, HISTORIA, `claude/`

read:
- `Infra/iot/expresso/oneplus-akkuvahti.sh:1-40`
- `Infra/iot/expresso/KEHITYSYHTEYS.md:1031-1052`
- `Infra/iot/expresso/PICO-HALLINTA.md:215-282`
- `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md:349-356`

## Do
1. `KEHITYSYHTEYS.md` luku "OnePlus-akkuvahti (palvelin)": päivitä ensimmäinen kohta ja **Tila**-kohta faktoihin:
   ajetaan palvelimen cronista 10 min välein (`PUHELIN=127.0.0.1:5555`), loki
   `~/.local/state/oneplus-akkuvahti.loki` (rivimuoto `AKKU: 79 % lataa=false rajat=30/60`, viim. 7.10.2026 08.00);
   siirretty palvelimen systemd-ajastimesta dc8a2ee 26.9.2026 (V-062), palvelimen `oneplus-akkuvahti.timer`
   poistettu käytöstä; lataus tunnistetaan `status: 2|5`:stä, ei `AC powered`ista (virrallinen hubi näyttää AC powered
   akun purkautuessa); rajat `VAROITUS_PCT`/`KRIITTINEN_PCT` luetaan HA:n `input_number.oneplus_akku_varoitus`/`_kriittinen`
   -arvoista, oletus 30/15 (V-197, 5.10.2026). Ota tarkat nimet skriptistä (`read:`), älä keksi. Jätä 17.9.2026
   käyttöönoton ansa-kuvaus ennalleen, mutta merkitse `.service`/`.timer` palvelimen vanhaksi reitiksi.
2. `PICO-HALLINTA.md:280-281`: "systemd-ajastin 10 min" → palvelimen cron 10 min; rajat HA:n input_numbereista (oletus 30/15).
3. `PICO-HALLINTA.md` luku 8: korvaa lause, jossa toimiva kytkentä ja järjestys on **kirjaamatta** ("— täydennä tähän."),
   viittauksella: järjestys laturi → roolinvaihto → HDMI on `Infra/linux/palvelin/README.md` luvussa
   "Hubi (USB-C, laturi ja HDMI)" (V-149, 7.10.2026). Älä muuta luvun muita lauseita.
4. `KAYTTAJAN-TIEDOT.md` luku 7: lisää lainauksen (rivit 351-353) perään tyhjän rivin jälkeen uusi kappale, tasan:
   `**TILAUS-AUTONOMIA — kehitys toimii ilman käyttäjän osallistumista fyysisiin toimenpiteisiin.** Tunnusrivi`
   ` lisätty 7.10.2026 (V-214), jotta purun VAATIMUKSET ja vaatimukset.mjs näyttävät yllä olevan vaatimuksen (17.9.2026).`
   (yksi kappale, rivitä ~110 merkkiin). Älä muuta mitään olemassa olevaa riviä.

## Acceptance
```bash
grep -q "oneplus_akku_varoitus" Infra/iot/expresso/KEHITYSYHTEYS.md
grep -q "dc8a2ee" Infra/iot/expresso/KEHITYSYHTEYS.md
test "$(grep -c 'systemd-ajastin' Infra/iot/expresso/PICO-HALLINTA.md)" -eq 0
test "$(grep -c 'täydennä tähän' Infra/iot/expresso/PICO-HALLINTA.md)" -eq 0
grep -q "Hubi (USB-C, laturi ja HDMI)" Infra/iot/expresso/PICO-HALLINTA.md
node claude/siirto/tools/vaatimukset.mjs --rivi "infra expresso" | grep -q "TILAUS-AUTONOMIA"
test "$(git diff --numstat -- Infra/iot/expresso/KAYTTAJAN-TIEDOT.md | cut -f2)" = "0"
test "$(git status --porcelain -- Infra/iot/expresso | grep -v -E ' Infra/iot/expresso/(KEHITYSYHTEYS|PICO-HALLINTA|KAYTTAJAN-TIEDOT)\.md$| Infra/iot/expresso/paketit/EXPRESSO-IDEAT-LUOKITTELU\.brief\.md$' | wc -l)" -eq 0
```

## Budget
~135 riviä luettavaa (`read:`-alueet); muutos alle 40 riviä.

## Stop
Jos skriptin muuttujat tai luvun 8 lause eivät vastaa kuvausta, kysy yksi kysymys ja lopeta. Älä committaa.

## Report
Kuusi riviä: Status, Changed, Acceptance, Budget, Deviations, Questions.
