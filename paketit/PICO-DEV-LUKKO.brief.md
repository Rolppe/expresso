# PICO-DEV-LUKKO

## Task
Estä kaksi päällekkäistä `pico_dev.py`-ajoa (Viat: "kaksi `pico_dev.py capture` -prosessia päällekkäin",
28.9.2026) ja aja `ChargerOff.__exit__` myös SIGTERM/SIGHUP-tapossa (Viat: `restore` + `timeout 300`, 27.9.2026).

## Files
may:
- `Infra/iot/expresso/pico_dev.py`
- `Infra/iot/expresso/testit/pico_dev_lukko_smoke.py` (uusi)

must not:
- mikään muu tiedosto, erityisesti `pico/`, `Infra/iot/zero/`, rekisterit

read:
- `Infra/iot/expresso/pico_dev.py:1-135` (docstring, asetukset, `ChargerOff`) ja `:655-718` (`main`, `__main__`)

## Do
1. `pico_dev.py`: lisää `import fcntl, signal` ja vakio `LOCK_PATH = os.environ.get('PICO_DEV_LOCK', '/tmp/pico_dev.lock')`.
2. Lisää funktio `acquire_lock(op)`: avaa `LOCK_PATH` (`a+`), `fcntl.flock(fd, LOCK_EX | LOCK_NB)`. Jos lukko on
   varattu: lue tiedoston sisältö ja `sys.exit('PICO_BUSY %s: toinen pico_dev.py-ajo on kesken; odota tai lopeta se' % sisältö.strip())`
   — exit-koodi 1 (sys.exit merkkijonolla). Muuten tyhjennä tiedosto, kirjoita `pid=<os.getpid()> op=<op> since=<time.strftime('%Y-%m-%d %H:%M:%S')>`,
   flush, ja palauta tiedosto-olio (pidetään auki prosessin loppuun; lukko vapautuu prosessin kuollessa).
3. Lisää funktio `install_signal_exit()`: SIGTERM ja SIGHUP → käsittelijä, joka kutsuu `sys.exit(128 + signum)`,
   jotta `with`-lohkojen `__exit__` (laturi takaisin) ja `finally`-lohkot ajetaan.
4. `__main__`-lohkossa heti `LOG_EXISTS`-tarkistuksen jälkeen ja ennen `with ChargerOff():`: `_lock = acquire_lock(op)`
   ja `install_signal_exit()`. `manifest`- ja `charger`-polut (jo ennen tätä) jäävät lukon ulkopuolelle.
5. Docstringin loppuun kaksi riviä: lukko `PICO_DEV_LOCK` (oletus `/tmp/pico_dev.lock`) ja `PICO_BUSY`-viesti;
   SIGTERM/SIGHUP ajaa laturin palautuksen. Lukko on konekohtainen: Macin ja palvelimen ajot eivät näe toisiaan.
6. Uusi `testit/pico_dev_lukko_smoke.py` (python3, ei laitetta, ei verkkoa; älä koskaan aja `pico_dev.py`:tä
   komentorivioperaatiolla): `PICO_DEV_LOCK` väliaikaistiedostoon, `sys.path`-lisäys ja `import pico_dev`.
   (a) aliprosessi `python3 -c` joka importtaa ja kutsuu `acquire_lock('capture')` ja nukkuu 5 s; odota kunnes
   tiedostossa on `op=capture`; toinen aliprosessi kutsuu `acquire_lock('cmd')` → exit ≠ 0 ja stderrissä `PICO_BUSY pid=`.
   (b) tapa ensimmäinen, uusi `acquire_lock('cmd')` onnistuu. (c) aliprosessi: `install_signal_exit()`, `with`-lohko,
   jonka `__exit__` kirjoittaa merkkitiedoston, `time.sleep(10)`; lähetä SIGTERM → merkkitiedosto olemassa, exit 143.
   (d) lähdetarkistus: `__main__`-lohkossa `acquire_lock(op)` esiintyy ennen `with ChargerOff():`. Kaikki aliprosessit
   `timeout`-parametrilla ≤ 20 s. Tulosta lopuksi `LUKKO_SMOKE OK 4/4`, virheessä exit 1.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico_dev.py
timeout 90 python3 Infra/iot/expresso/testit/pico_dev_lukko_smoke.py
timeout 90 python3 Infra/iot/expresso/testit/pico_dev_lukko_smoke.py | grep -q "LUKKO_SMOKE OK 4/4"
test "$(git status --porcelain -- Infra/iot/expresso | grep -v -E ' Infra/iot/expresso/(pico_dev\.py|testit/pico_dev_lukko_smoke\.py|paketit/PICO-DEV-LUKKO\.brief\.md)$' | wc -l)" -eq 0
```

## Budget
718 riviä luettavaa (`wc -l pico_dev.py`), luetaan vain nimetyt rivit; muutos alle 120 riviä.

## Stop
Jos `__main__`-lohko tai `ChargerOff` ei vastaa kuvausta, tai testi vaatisi laitetta tai verkkoa, kysy yksi
kysymys ja lopeta. Älä committaa.

## Report
Kuusi riviä: Status, Changed, Acceptance, Budget, Deviations, Questions.
