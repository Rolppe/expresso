# EXPRESSO-WIFI-AIKAIKKUNA — Wi-Fin kuorma uuton aikana minimiin (20.10.2026)

Käyttäjä 20.10.2026: "Mietitään onko nykyinen wifi toteutus mahdollisimman pienessä aika ikkunassa toimiva. Tämä siitä
syystä että wifi ei saa häiritä picon rajallisia resursseja uuton aikana enemmän kun on välttämätöntä siihen että tieto
siirtyy hyvin." Käyttäjän valinta: kohdat 1–3, BLE ensin pois; mittaus agentin laiteajolla.

## Muutos (expresso 1b47954, flash `testit/flash-20261020-zero-wifiaika.log`, boot 908af624)

| Kohta | Muutos |
|---|---|
| BLE | `preset.BLE = {'enabled': False}`: BLE-tehtävän tilalla `brew_log_only` (uuttoloki 30 ms tahdissa). Uusi puhelin ei saa Wi-Fi-avainta (`wifi:key?` vain BLE:llä); iPhonessa avain on. |
| 1 mittaus | `task_busy('diag')`; HB:ssä `wtx wtxerr wsmax_us` (WifiLink) |
| 2 DIAGNET | pumppuajossa (`diag.in_shot()` = PB-loki tai `run_shot`in `diag.quiet`, myös TS) lähetys 500 ms välein täysinä paketteina, HB ilman `gc.mem_free`/RSSI, täysi HB heti PB-uuton jälkeen |
| 3 WifiLink | paino live-paketissa (äppi lukee avaimet erikseen, `machine_data_notifier.dart:151-180`); pumppuajossa 100 ms askel, ei asetuspaketteja; ilman tilaajaa 500 ms |

Isäntätestit: kaikki 26 `*_smoke` + `shot_test` 0 failed.

## Mittaus: kaksi 20 s testiuuttoa (`pico_dev.py shot 20`, pvent ennen, `wmax:740 wrise:200`)

| | Ennen (8cd69aaf, BLE päällä, äppi BLE:llä) | Jälkeen (908af624, BLE pois, äppi Wi-Fillä) |
|---|---|---|
| DIAGNET pkt/s uutossa | ~7 (cc51a2fc: ~9) | ~2 (txp +10 / 5 s) |
| DIAGNET `sendto` max | 20 751 µs | 1 914 µs |
| WifiLink pkt/s / `sendto` max | ei tilaajaa | ~4,6 / ≤ 569 µs |
| `max_loop_ms` (TS_END) | 92 | 104 |
| EU_VV / EB_VV stall | 103 / 117 | 60 / 162 |
| EU_STALL rivejä (k/l/s/y) | 220 (58/56/76/30) | 222 (111/61/30/20) |
| y-katkot tehtävittäin | `-` 23, scale 4, ser 2, wifi 1 | `-` 10, diag 2 (pahin 33 ms), wifi 4 (≤ 13 ms), scale 2, ser 2 |
| GC uutossa (EU_GC n / max) | 49 / 101 ms | 52 / 103 ms |

Lokit: `testit/wifiaika-20261020-ennen.log`, `testit/wifiaika-20261020-jalkeen.log`; HB:t keräimen
`~/.local/state/expresso-diag/2026-10-20.log` 13.02–13.09.

## Johtopäätös

- Wi-Fin oma kustannus laski: lähetyksiä ~9 → ~2 + 4,6 pkt/s, pahin `sendto` 20,8 → 1,9 ms.
- Kokonaiskatkot eivät muuttuneet, koska niitä hallitsee GC: ~50 keräystä 20 s:ssa, kukin jopa ~100 ms, molemmissa
  firmwareissa. Ennen-uuton HB:ssä `free=4240` (keko lähes täynnä). `diag:33 ms` -katko osuu todennäköisesti GC:hen
  diag-askeleen allokaatiossa (`sendto` max samalla jaksolla 1,9 ms).
- Yksi uutto per firmware on kohinainen vertailu: jälkeen-uutossa EB-pito kesti pidempään (hold_n 614 vs 341), mikä
  kasvattaa sec=k-katkoja säätimen omasta työstä.

## Avoinna

- Kohta 4: virransäästö (`wlan.config(pm=…)`) — "live 2,8 Hz / hello ~1 s" -oire; ei tehty (käyttäjän valinta).
- GC-katkot uuton aikana (~100 ms) ovat suurin yksittäinen syy; oma paketti (allokaatiot uuttosilmukoissa, `gc.threshold`).
- `pico_dev.py safe` katkesi `BrokenPipeError` Ctrl-C:n jälkeen (silta suljettu; tunnettu Connection refused -vika), Pico
  resetoitui devsafen vahdilla.
