# PICO-DEV-LINK

## Task
Korjaa `pico_dev.py`:n `Link`-luokan kaksi Viat-rivin (`verify` kaatui kahdesti, 23.9.2026) syytä: vastauksen perään
tullut kohina kaataa `until`in, ja hiljainen silta (`tail b''`) kaataa ajon ilman sillan uudelleenavausta.

## Files
may:
- `Infra/iot/expresso/pico_dev.py`
- `Infra/iot/expresso/testit/pico_dev_link_smoke.py` (uusi)

must not:
- mikään muu tiedosto, erityisesti `pico/`, `Infra/iot/zero/`, rekisterit

read:
- `Infra/iot/expresso/pico_dev.py:163-290` (`ensure_bridge`, `Link`, `enter_devsafe`, `exec`)
- `Infra/iot/expresso/testit/pico_dev_lukko_smoke.py` (tyylimalli: import-tapa, tulostus)

## Do
1. `pico_dev.py`: lisää `Link`-luokan yläpuolelle `class LinkTimeout(RuntimeError)`, jolla attribuutti `buf`.
   `until` nostaa sen (sama viestimuoto kuin nyt, `buf` talteen).
2. `until`: `buf.endswith(marker)` → `marker in buf`; palauta `buf[:buf.index(marker) + len(marker)]` (merkin perään
   tullut kohina, esim. BLE-sovelluksen `Received: 'sync'`, pudotetaan). Kommentti: syy ja päivä 23.9.2026.
3. Uusi metodi `Link.reopen()`: sulje `self.s`; jos `LINK != 'zero'`: `adb('shell', 'am', 'force-stop', APP, check=False)`,
   `time.sleep(2)`, `ensure_bridge()`; sitten `self._connect()` ja `self.drain(0.8)`. `__init__`in
   `ERR usb closed` -haara käyttää `reopen()`ia (nykyiset kommentit säilyvät).
4. `enter_devsafe`: siirrä nykyinen `\r\x03\x03` … `until(b'raw REPL; CTRL-B to exit\r\n>', 5)` -jakso sisäfunktioksi.
   Jos `until` nostaa `LinkTimeout`in ja `e.buf` on tyhjä: tulosta `LINK_REOPEN raw REPL silent, reopening bridge`,
   `self.reopen()` ja aja jakso kerran uudelleen. Ei-tyhjä `buf` tai toinen aikakatkaisu nostetaan sellaisenaan.
   Muu `enter_devsafe` (devsafe-tarkistus, `SAFE_OK`) ennallaan.
5. Uusi `testit/pico_dev_link_smoke.py` (python3, ei laitetta, ei verkkoa, ei adb:tä; älä aja `pico_dev.py`:tä
   komentorivioperaatiolla): import kuten lukko-smokessa; `Link` luodaan `object.__new__(pico_dev.Link)` ja
   `self.s` = valesoketti (jono `recv`-paloja, tyhjä jono → `socket.timeout`; `sendall` tallentaa).
   (a) `until(b'\x04>', 2)` palasta `b"OK hi\x04\x04>Received: 'sync'\r\n"` → paluu päättyy `b'\x04>'`.
   (b) `exec('print(1)')` samalla kohinalla → palauttaa `'hi'`.
   (c) `until(b'X', 0.5)` tyhjällä jonolla → `LinkTimeout`, `buf == b''`.
   (d) `enter_devsafe`: ensimmäinen soketti hiljainen; `reopen` korvattu valeella, joka laskee kutsut ja vaihtaa
   soketin sellaiseen, joka vastaa `\x01`:een bannerilla ja koodiin `b'OK SAFE_OK\r\n\x04\x04>'` → `reopen` kutsuttu
   tasan kerran, ei `SystemExit`iä. Lisäksi ei-tyhjä aikakatkaisu → `LinkTimeout`, `reopen` 0 kertaa.
   Aikaraja: koko testi ≤ 60 s. Tulosta `LINK_SMOKE OK 4/4`, virheessä exit 1.

## Acceptance
```bash
python3 -m py_compile Infra/iot/expresso/pico_dev.py
timeout 90 python3 Infra/iot/expresso/testit/pico_dev_link_smoke.py
timeout 90 python3 Infra/iot/expresso/testit/pico_dev_link_smoke.py | grep -q "LINK_SMOKE OK 4/4"
timeout 90 python3 Infra/iot/expresso/testit/pico_dev_lukko_smoke.py | grep -q "LUKKO_SMOKE OK 4/4"
test "$(grep -c 'buf.endswith(marker)' Infra/iot/expresso/pico_dev.py)" -eq 0
test "$(git status --porcelain -- Infra/iot/expresso | grep -v -E ' Infra/iot/expresso/(pico_dev\.py|testit/pico_dev_link_smoke\.py|paketit/PICO-DEV-LINK\.brief\.md)$' | wc -l)" -eq 0
```

## Budget
753 riviä luettavaa (`wc -l pico_dev.py`), luetaan vain nimetyt rivit; muutos alle 150 riviä.

## Stop
Jos `Link`, `until`, `enter_devsafe` tai `exec` ei vastaa kuvausta, tai testi vaatisi laitetta, adb:tä tai verkkoa,
kysy yksi kysymys ja lopeta. Älä committaa.

## Report
Kuusi riviä: Status, Changed, Acceptance, Budget, Deviations, Questions.
