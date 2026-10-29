# PICO-DEV-LUKKO — korjaus 1

Briefin virhe (suunnittelija): `restore`-ajossa puhelimen sovelluksen flasheri kirjoittaa Picolle itsenäisesti, ja
pico_dev.py vain odottaa logcatista tuomiota (`restore()`-kommentti: laturi pysyy pois, kunnes flash on ohi; 23.9.2026
laturi kytkeytyi kesken restoren). SIGTERM-käsittelijä ajaisi `ChargerOff.__exit__`:n ja kytkisi laturin kesken flashin.

## Do
1. `pico_dev.py` `__main__`: kutsu `install_signal_exit()` vain, kun `op != 'restore'`. Kommentti rivin yläpuolelle:
   restore — sovelluksen flasheri jatkaa, laturi pysyy pois tapossa; käsin `pico_dev.py charger on` RESTORE_OK/FAIL:n jälkeen.
2. Docstringin Lock-kappaleeseen sama poikkeus yhdellä rivillä.
3. `testit/pico_dev_lukko_smoke.py` (d): lisää lähdetarkistus, että `__main__`-lohkossa on `op != 'restore'` ennen
   `install_signal_exit()`-kutsua. Tulostus pysyy `LUKKO_SMOKE OK 4/4`.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico_dev.py
timeout 90 python3 Infra/iot/expresso/testit/pico_dev_lukko_smoke.py | grep -q "LUKKO_SMOKE OK 4/4"
grep -q "op != 'restore'" Infra/iot/expresso/pico_dev.py
grep -q "op != 'restore'" Infra/iot/expresso/testit/pico_dev_lukko_smoke.py
```
