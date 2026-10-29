# OHJEVAHTI — spec

Pakettitiedosto: `paketit/OHJEVAHTI.md`. Holdout: `testit/ohjevahti_smoke.py`.

## 1. Tiedostot

- `Infra/iot/expresso/ohjevahti.py` — Python 3, vain standardikirjasto, ajettava suoraan.
- `Infra/iot/expresso/OHJEKIRJA.json` — alkusisältö tasan `{"ohjeet": []}` + rivinvaihto.
- `Infra/iot/expresso/.gitignore` — lisää rivi `.ohjevahti-tila.json` (luo tiedosto jos puuttuu).

Polut: ympäristömuuttuja `OHJEVAHTI_KIRJA` tai oletus `<skriptin hakemisto>/OHJEKIRJA.json`;
`OHJEVAHTI_TILA` tai oletus `<skriptin hakemisto>/.ohjevahti-tila.json`.

## 2. Syöte ja tuloste

Stdin: Claude Coden PreToolUse-JSON. Luetaan vain `tool_input.command` (merkkijono).

- Komennossa ei ole laiteajoa (kohta 3) → ei tulostetta, exit 0.
- Muuten tulostetaan yksi JSON-rivi ja exit 0:
  `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "<deny|ask>",
  "permissionDecisionReason": "<teksti>"}}`
- Mikä tahansa poikkeus sen jälkeen, kun komennosta on löytynyt `pico_dev.py`, → `deny`,
  syy alkaa `OHJEVAHTI VIRHE:`. Rikkinäinen tai väärän muotoinen ohjekirja → `deny`, syy alkaa
  `OHJEKIRJA rikki:`. Vahti ei koskaan päästä laiteajoa läpi virheen takia.

## 3. Laiteajon tunnistus

Jaa komento osiin erottimilla `&&`, `||`, `;`, `|` ja rivinvaihto; jokainen osa `shlex.split`.
Osa on pico-ajo, jos jokin sana päättyy `pico_dev.py`; seuraava sana on `op`, sitä seuraava `arg`.

| op | laitekomento | kenttien nimet järjestyksessä (`arg.split(':')`) |
|---|---|---|
| `pgap` | pgap | bar, n, spacing_ms, len_ms, phases, lo_us, hi_us |
| `pstep` | pstep | bar, hold_ms, tail_ms |
| `plen` | plen | bar, reps |
| `pcap` | pcap | ms, bar, phase_us |
| `psweep` | psweep | ms, bar, n, mult |
| `phold` | phold | s |
| `shot` | tshot | s |
| `cmd` | `arg`:n osa ennen ensimmäistä `:` | jäljellä oleva osa taulukon mukaan saman nimisellä komennolla; `mcal`: ms; muut: ei kenttiä |

Läpi ilman tulostetta: op `verify`, `capture`, `safe`, `watchdog`, `watchdog_test`; mikä tahansa
laitekomento, jonka ensimmäinen kenttä on `stop`; `cmd dev:safe`. Kaikki muut op:t ja `cmd`-komennot
ovat laiteajoja. Kentät ovat lukuja (`float`); puuttuva kenttä = puuttuu.

## 4. Ohjekirja

`{"ohjeet": [rivi, ...]}`. Rivin pakolliset avaimet: `id`, `lainaus`, `tyyppi`, `komento`, `tila`.
Vain `tila == "voimassa"` huomioidaan. Rivi osuu, kun `komento` on sama kuin laitekomento tai `"*"`.

- `tyyppi: "arvo"` (+ `kentta`, `arvo`): kenttä puuttuu tai `abs(kenttä − arvo) > 1e-9` →
  rivi `ERO <id>: <komento> <kentta>=<annettu|puuttuu>, ohje <arvo> — "<lainaus>"`.
- `tyyppi: "kielto"`: → rivi `KIELTO <id>: <komento> — "<lainaus>"`.
- `tyyppi: "valivaihe"` (+ `vaihe`, `kuitattu_klo` epoch-sekunnit tai null): jos tila-tiedostossa on
  `viimeisin_ajo` ja (`kuitattu_klo` on null tai `kuitattu_klo < viimeisin_ajo`) → rivi
  `VÄLIVAIHE <id>: <vaihe> kuittaamatta edellisen ajon jälkeen — "<lainaus>"`.

## 5. Päätös

- Yksikin ERO/KIELTO/VÄLIVAIHE-rivi → `deny`. Syy: kaikki rivit, sitten
  `Kysy käyttäjältä ennen ajoa. Älä muuta komentoa tai ohjekirjaa ilman hänen vastaustaan.`
- Muuten → `ask`. Syy: `Laiteajo: <komento> <kentta>=<arvo> ...` ja jokainen osuva voimassa oleva
  rivi muodossa `<id>: "<lainaus>"`. Jos ohjekirjaa ei ole tai `ohjeet` on tyhjä, lisää
  `ohjekirja tyhjä — käyttäjän ohjeita ei ole kirjattu`.
- Vain `ask`-päätös kirjoittaa tila-tiedostoon `{"viimeisin_ajo": time.time()}`. `deny` ei kirjoita.
- Monta pico-ajoa samassa komennossa: tarkista jokainen; yksikin deny → deny koko komennolle.
