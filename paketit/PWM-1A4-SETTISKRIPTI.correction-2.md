# PWM-1A4-SETTISKRIPTI — korjaus 2

`--check` ajettiin oikeaa puhelinta vasten ja se **esti ajon ennen yhtäkään kirjoitusta**. Juuri
sitä varten briefin kohta 5 vaati H-067:n muotoisen lukevan esitarkistuksen: tämän työkalun oikea
työ ajetaan siellä, missä sen testit eivät aja. Esto oli oikea, mutta sen syy oli väärä väite —
pohjasetti on olemassa.

Budjettikatto on nostettu 460 → 480 riviin, jotta korjaus mahtuu ilman rivien tiivistämistä.

`may:`-lista on ennallaan: vain `build_set.py` muuttuu.

## Vika — `adb shell` ei säilytä argumenttirajoja, joten `sh -c` saa vain ensimmäisen sanan

`run_as` (`build_set.py:40-41`) rakentaa argumenttilistan
`[adb, -s, PHONE, shell, run-as, APP, sh, -c, <komento>]`. `adb shell` **liittää argumentit
välilyönnillä yhteen** ja antaa tuloksen laitteen kuorelle, joten lainausmerkit katoavat matkalla.
Laitteella ajetaan siis `run-as APP sh -c ls -1t files/firmware_backup`, jossa `sh -c` saa
komennokseen pelkän `ls`:n ja `-1t` sekä polku menevät positioargumenteiksi `$0`, `$1`.

Mitattu 19.9.2026, sama komento kahdella tavalla:

```text
$A -s $P shell run-as APP sh -c 'ls -1t files/firmware_backup'
  → app_flutter  cache  code_cache  files  shared_prefs      (sovelluksen datahakemisto)
$A -s $P shell "run-as APP sh -c 'ls -1t files/firmware_backup'"
  → 20260919-flow7  20260919-flow6  …                        (setit, oikea tulos)
```

Vika ei rajoitu `list_sets`:iin. Sama muoto on jokaisessa muuttavassa ja lukevassa etäkomennossa:
`cp -r` (`build()`), `find … -exec sha256sum`, `find … -exec stat`, `mkdir -p`, `cp`, `sha256sum`
(`push_and_verify`). `cp -r A B` olisi ajanut laitteella `sh -c cp` — eli ei mitään — ja koska
korjauksen 1 tiedostolistaus käyttää samaa rikkinäistä polkua, sekään ei olisi kertonut totuutta.

## Korjaus

Anna koko etäkomento `adb shell`:lle **yhtenä argumenttina** ja lainaa sisältö laitteen kuorta
varten. Erota argumenttilistan rakentaminen omaksi puhtaaksi funktiokseen, jotta se on
testattavissa ilman laitetta:

- `run_as_argv(shell_cmd)` palauttaa listan, jonka viimeinen alkio on yksi merkkijono muotoa
  `run-as <APP> sh -c <lainattu komento>`; käytä `shlex.quote`a lainaukseen.
- `run_as` kutsuu sitä ja ajaa tuloksen.

Älä kierrä ongelmaa pilkkomalla komentoja yksinkertaisemmiksi — `find … -exec` ja putket
tarvitaan, ja seuraava lisäys toisi saman vian takaisin.

## Acceptance

Briefin neljä komentoa uudelleen, korjauksen 1 rakennetarkistus uudelleen, ja tämä:

```bash
cd /srv/work/Infra/iot/expresso && python3 - <<'PY'
import sys, shlex, importlib.util
sp = importlib.util.spec_from_file_location('bs','build_set.py'); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
argv = m.run_as_argv("ls -1t files/firmware_backup")
f = []
if argv[-2:-1] != ['shell'] and 'shell' not in argv: f.append('shell puuttuu argumenteista')
tail = argv[-1]
if not isinstance(tail, str) or 'sh -c' not in tail: f.append('etakomento ei ole yksi argumentti')
if shlex.quote('ls -1t files/firmware_backup') not in tail: f.append('komentoa ei ole lainattu')
if any(a == '-c' for a in argv[:-1]): f.append('sh -c on yha eri argumentteina')
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f)); sys.exit(1 if f else 0)
PY
```

```bash
cd /srv/work/Infra/iot/expresso && test $(cat build_set.py PICO-HALLINTA.md | wc -l) -le 480
```

## Report

Sama kuusirivinen muoto kuin briefissä, `iterations: 3`, `budget: <rivit>/480`.
