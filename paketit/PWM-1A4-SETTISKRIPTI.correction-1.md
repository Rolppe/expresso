# PWM-1A4-SETTISKRIPTI — korjaus 1

Hyväksyntä oli vihreä 4/4 ja budjetti 412/460 myös suunnittelijan omassa ajossa. Nämä kaksi vikaa
löytyivät koodia lukemalla, ja molemmat ovat **hiljaisia**: ne tuottavat viallisen setin ilman
yhtään virheilmoitusta. Viallinen setti on tämän työkalun vakavin seuraus — palautus kirjoittaa
Picon tiedostojärjestelmään, ja puuttuvat tiedostot jättävät sen bootkelvottomaksi.

`may:`-lista on ennallaan: vain `build_set.py` muuttuu.

## Vika 1 — pohjan kopiointia ei todenneta

`build()` ajaa `run-as('cp -r %s %s')` ja luottaa paluuarvoon (`build_set.py:186-189`). `adb shell`
ei kaikissa versioissa välitä etäkomennon paluuarvoa, joten epäonnistunut `cp -r` voi näyttää
onnistuneelta. Sen jälkeen `push_and_verify` luo puuttuvan hakemiston itse (`mkdir -p`,
`build_set.py:171-173`), joten setti syntyy — mutta siinä on vain työnnetyt tiedostot, ei
pohjasetin muita. Erityisesti `secrets.py` puuttuisi: se on puhelimella eikä repossa, ja koko
kopioimalla rakentamisen syy on juuri sen säilyttäminen.

**Korjaus:** listaa pohjan ja uuden setin tiedostot `cp -r`:n jälkeen (`find <dir> -type f`) ja
vaadi, että uudessa on **jokainen** pohjan tiedosto. Puuttuva tiedosto on virhe, joka keskeyttää
ajon ennen yhtäkään `push`ia. Tulosta vertailu yhdellä rivillä: `base=<n> new=<n>`.

## Vika 2 — `stat`in epäonnistuminen tuottaa manifestin, jossa koko on `null`

`build()` lukee koot komennolla `stat -c '%n %s'` (`build_set.py:196-197`) eikä tarkista sen
onnistumista. Jos Androidin toybox ei tue `-c`:tä tai komento kaatuu, `sizes` jää tyhjäksi,
`build_manifest` kirjoittaa `sizes.get(name)` eli `None`, ja JSON saa `"size": null`. Tätä ei jää
kiinni mihinkään: `push_and_verify` vertaa manifestin omaa tiivistettä itseensä, ei sen sisältöä.
Palautus lukee manifestin `{"name","size","sha256"}`-muotoisena (`PICO-HALLINTA.md` luku 6).

**Korjaus:** vaadi, että jokaisella manifestin merkinnällä on kokonaislukukoko. Yksikin `None` on
virhe, joka keskeyttää ajon ennen manifestin työntämistä, ja virheilmoitus nimeää puuttuvat
tiedostot. Tarkista myös `find ... stat` -ajon paluuarvo.

## Acceptance

Briefin neljä komentoa uudelleen, ja lisäksi tämä rakennetarkistus:

```bash
cd /srv/work/Infra/iot/expresso && python3 - <<'PY'
import sys, importlib.util
sp = importlib.util.spec_from_file_location('bs','build_set.py'); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
f = []
try:
    m.build_manifest({'/main.py': 'a'*64}, {})
    f.append('build_manifest hyvaksyy puuttuvan koon')
except Exception:
    pass
src = open('build_set.py').read()
if 'find' not in src.split('def build(')[1].split('def ')[0]: f.append('pohjan kopiointia ei todenneta')
for x in f: print('FAIL ' + x)
print('RESULT: %d failed' % len(f)); sys.exit(1 if f else 0)
PY
```

## Report

Sama kuusirivinen muoto kuin briefissä, `iterations: 2`.
