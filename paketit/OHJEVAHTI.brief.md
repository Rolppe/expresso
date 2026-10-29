# OHJEVAHTI

## Task
Kirjoita PreToolUse-koukku `ohjevahti.py`, joka estää laitekomennon, joka poikkeaa käyttäjän
ohjekirjaan kirjatusta ohjeesta, ja näyttää ohjeen lainauksen muille laiteajoille.

## Files
may:
- `Infra/iot/expresso/ohjevahti.py` (uusi), `Infra/iot/expresso/OHJEKIRJA.json` (uusi),
  `Infra/iot/expresso/.gitignore`

must not:
- `Infra/iot/expresso/testit/` kokonaan — holdout on suunnittelijan mitta
- `Infra/iot/expresso/paketit/`, `pico/`, `pico_dev.py`
- `.claude/settings.json` ja kaikki muu `Infra/iot/expresso/`:n ulkopuolella — asennus on
  käyttäjän lupa-asia

read:
- `Infra/iot/expresso/paketit/OHJEVAHTI.spec.md` kokonaan
- `Infra/iot/expresso/testit/ohjevahti_smoke.py` kokonaan — se on hyväksynnän mitta
- `Infra/iot/expresso/pico_dev.py` rivit 325-355 (op-nimet)
- `Infra/iot/expresso/pico/commands.py` rivit 97-245 (kenttien järjestys)

## Do
1. Lue spec ja holdout.
2. `ohjevahti.py`: spec kohdat 2-3 — syöte, virheet, laiteajon tunnistus ja kentät.
3. `ohjevahti.py`: spec kohta 4 — ohjekirjan rivit ja ERO/KIELTO/VÄLIVAIHE.
4. `ohjevahti.py`: spec kohta 5 — päätös, syyteksti ja tila-tiedosto.
5. `OHJEKIRJA.json` ja `.gitignore`: spec kohta 1.
6. Aja `## Acceptance` ja `## Budget`; korjaa vain se, minkä ne sanovat punaiseksi.

## Acceptance
```bash
cd "$(git rev-parse --show-toplevel)/Infra/iot/expresso" && python3 -m py_compile ohjevahti.py
```
```bash
cd "$(git rev-parse --show-toplevel)/Infra/iot/expresso" && timeout 120 python3 testit/ohjevahti_smoke.py
```
```bash
cd "$(git rev-parse --show-toplevel)/Infra/iot/expresso" && python3 -c "import json;assert json.load(open('OHJEKIRJA.json'))=={'ohjeet':[]}"
```
```bash
cd "$(git rev-parse --show-toplevel)" && git status --porcelain -- Infra/iot/expresso .claude | grep -vE "Infra/iot/expresso/(ohjevahti\.py|OHJEKIRJA\.json|\.gitignore|testit/ohjevahti_smoke\.py|paketit/OHJEVAHTI.*|paketit/delegation\.jsonl|__pycache__/|pico/__pycache__/)$" | wc -l | grep -qx 0
```

## Budget
```bash
cd "$(git rev-parse --show-toplevel)/Infra/iot/expresso" && test $(cat ohjevahti.py | wc -l) -le 220
```
Uusi tiedosto, ei mitattavaa pohjaa; spec kohdat 2-5 ≈ 150 riviä + varaus.

## Stop
- Holdout vaatii jotain, mikä on ristiriidassa spec:n kanssa — kerro kumpi kohta ja lopeta.
  Älä muuta holdoutia.
- Spec jättää päätöksen auki niin, että kaksi tulkintaa antaisi eri päätöksen jollekin
  holdoutin tapaukselle.

Kysy yksi kysymys ja lopeta vuorosi. **Älä koske laitteeseen** äläkä `.claude/`-asetuksiin.

## Report
```text
brief: OHJEVAHTI
files: <muutetut tiedostot pilkuilla>
acceptance: <pass|fail — punaisen komennon numero>
budget: <rivit>/220
iterations: <yritysten määrä>
note: <yksi rivi: holdoutin tulosrivi OHJEVAHTI_SMOKE>
```
