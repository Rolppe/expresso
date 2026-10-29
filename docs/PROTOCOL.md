# Wire protocols

This file describes every protocol the firmware speaks, derived from the code in `pico/`. It is the
reference for the companion app [expresso_control](https://github.com/Rolppe/expresso_control)
(Flutter, iPhone), which talks to the Pico over BLE and over Wi-Fi.

| Channel | Transport | Direction | Purpose | Source |
|---|---|---|---|---|
| USB serial | USB-CDC, text lines | host to Pico, Pico to host | development: commands, log output | `pico/main.py` (`serial_commands`), `pico/commands.py` |
| Diagnostics `EXD1` | UDP, Pico to collector, port 47210 | Pico to host | stdout and shot samples as text | `pico/diagnet.py` |
| App link `EXA1` | UDP on the Pico, port 47211 | both ways | commands (HMAC-signed) and live JSON | `pico/wifilink.py` |
| BLE GATT | service `0x180A` | both ways | same commands and JSON as `EXA1`, no signing | `pico/bluetooth_handler.py` |

All four feed the same dispatcher, `handle_command()` in `pico/commands.py`. A command is a short
ASCII string such as `bt:94.5`. `EXA1` accepts only an allow-list of commands (section 3.4);
BLE and USB serial accept all of them.

In the shipped `pico/preset.py`, BLE is switched off (`BLE = {'enabled': False}`) and the app is expected to use
`EXA1`. Setting `enabled` to `True` brings the BLE task back. Everything below about BLE applies to that case.

## 1. USB serial (`CMD`)

- The host writes one line per command: `CMD <command>` terminated by CR or LF.
- The parser (`SerialLine` in `pico/commands.py`) keeps only printable ASCII (32 to 126) and at most
  80 characters per line. Anything else is dropped without an error. A line without the `CMD ` prefix is ignored.
- The firmware polls stdin every 50 ms and answers with one line on stdout:
  - `CMD_OK <command>`: the dispatcher recognised the command.
  - `CMD_UNKNOWN <command>`: it did not (`brew_data.command_known` is false).
  - `SER_ERR <repr>`: the serial task caught an exception; the parser is reset.
- `CMD_OK` means "recognised", not "applied". A recognised command with a bad argument is usually swallowed silently.
- Known quirk: the commands that return early (`tare`, `cal:`, `tray?`, `tray:`, `tank?`, `tank:`, `obj?`, `obj:`)
  do not refresh `command_known`, so their `CMD_OK`/`CMD_UNKNOWN` repeats the previous command's verdict.
- Everything else on stdout is free-form log text: `TS_START`/`TS_END` (test shot), `STBY`, `STBT`, `PEQ`,
  `PCAL_ST`, `PCALSET_OK`, `TARE`, `SCALE_CAL`, `TRAY_*`, `TANK_*`, `BREW_LOG ...`, `WIFI ...`, `DEVSAFE ...`
  and the per-experiment lines (`PCAP_*`, `PHOLD_*`, `KLAMP_*`, ...) that `pico_dev.py` captures until a `*_END` marker.

## 2. Diagnostics `EXD1` (UDP, port 47210)

Pico to collector. Fire and forget: the collector sends nothing back.

```
EXD1 <boot> <seq> <up_ms> <drop>\n<data>
```

| Field | Meaning |
|---|---|
| `boot` | 8 hex digits, random per boot (`os.urandom(4)`) |
| `seq` | packet counter within the boot, starts at 0 |
| `up_ms` | `ticks_ms()` at send time |
| `drop` | bytes lost so far because the ring overflowed or a send failed |
| `<data>` | the oldest bytes of the text ring, up to 1400 bytes per datagram in total |

- The Pico tees its whole stdout (`os.dupterm`) into an 8192-byte ring buffer, plus network-only `DIAG_*` lines.
  The ring never blocks; a full ring overwrites the oldest bytes and counts them in `drop`.
- The sender task wakes every 100 ms (500 ms during a shot) and sends at most 2 datagrams per wake.
  The socket is non-blocking and addressed by an IP literal (no DNS). A send error drops the data.
- The destination is `DIAGNET['host']:DIAGNET['port']` in `pico/preset.py`. The host comes from
  `pico/local_config.py` (`DIAGNET_HOST`) when that file exists. Wi-Fi credentials come from
  `pico/secrets.py`, or from `pico/diag_wifi.py` if present.
- A collector reassembles lines from the byte stream and reports gaps from `seq`
  (the reference collector is `diagnet/keraaja.py`).

Network-only lines (`DiagNet` in `pico/diagnet.py`):

| Line | When | Content |
|---|---|---|
| `DIAG_BOOT` | once per boot | `rc=` reset cause, `fw=` MicroPython version string, `mac=` |
| `DIAG_HB` | every 60 s idle, 5 s during a shot | `up_s free alloc drop txp txerr smax_us tmax_us rssi brew pend err wtx wtxerr wsmax_us lmax_us l100`: uptime, heap, ring/socket counters, longest send, Wi-Fi RSSI, `EXA1` counters, longest asyncio-task lateness |
| `DIAG_MIN` | every 60 s | `win_ms heat_ms pump_ms p_n p_avg p_min p_max T target n10 d10_min d10_max pi_i ts tk`: heater and pump on-time in the window, pressure statistics, boiler temperature, PI integral, thermal stability, tank level |
| `DIAG_SHOT` | shot start and end | `start` / `end reason=<r> n=<rows>` |
| `DIAG_S` | 10 Hz during a shot | `t= T= p= f= w= r=`: ms, temperature x10, pressure x100, flow x100, weight x10, flags |

## 3. App link `EXA1` (UDP, port 47211)

The Pico binds `0.0.0.0:47211` once it has joined Wi-Fi. Every message is one ASCII datagram.

### 3.1 App to Pico

```
EXA1 hello
EXA1 <boot> <seq> <mac16> <command>
```

- `boot`: the Pico's current boot id (the same 8 hex digits as in `EXD1`). Learn it from the `hello` reply.
  A restart changes it, which invalidates every command signed for the old boot.
- `seq`: integer chosen by the sender, strictly increasing per sender address.
- `mac16`: the first 16 hex digits (8 bytes) of `HMAC-SHA256(key, "<boot> <seq> <command>")`. The signed string uses
  the `seq` text exactly as sent. `command` may contain spaces; the datagram is split into at most 5 fields.
- `key`: 32 random bytes made on first use and stored as 64 hex digits in `link_key.txt` on the Pico's flash.
  It is not in the repository or in `MANIFEST.json`. The app obtains it over BLE (section 4.3).
  Without BLE, read `link_key.txt` over the serial REPL.
- Datagrams are read with `recvfrom(512)`. At most 4 datagrams are handled per task pass.

### 3.2 Pico to app

```
{"type":"hello","boot":"<8 hex>","name":"EspressoPico","v":1}
{"type":"ack","seq":<n>,"r":"<code>"}
```

Both are single JSON objects. After `sub` (below), the telemetry objects of section 5 follow, one JSON object per datagram.

| Ack `r` | Meaning |
|---|---|
| `ok` | command accepted; nothing persistent changed |
| `updated` | accepted and a persisted setting changed (settings packets are resent) |
| `unknown` | HMAC valid, command on the allow-list, but the dispatcher did not recognise it |
| `denied` | HMAC valid, command not on the allow-list |
| `stale` | HMAC valid but signed for another boot id; re-run `hello` |

Silent drops (no ack, logged as `WIFI_DENY <why>` at most every 10 s): `bytes` (not UTF-8), `proto` (first word is
not `EXA1`), `format` (wrong field count or non-integer `seq`), `auth` (HMAC mismatch; an unauthenticated sender
learns nothing). A `seq` lower than the last accepted one from that address is dropped silently.
The same `seq` again re-sends the stored ack without running the command twice, so a lost ack is safe to retry.

### 3.3 Subscription

`sub` is itself a signed command. The sender that issued it receives the telemetry stream until 15 s pass without
another `sub`, so the app repeats it periodically. At most 2 subscribers are kept; a third evicts the one that
subscribed longest ago. A new subscriber gets the settings packets immediately.

The task wakes every 500 ms with no subscriber, every 50 ms with one, and every 100 ms during a shot.

### 3.4 Allow-list

Exact: `sync`, `get:settings`, `settings?`, `brew_log?`, `brew_log:get`, `tare`, `sub`, `stby?`, `peq?`.

Prefixes: `brew_log:ack`, `stby:`, `stbt:`, `pit:`, `srt:`, `bt:`, `steam:`, `pip:`, `bp:`, `spl:`, `sph:`, `spmin:`,
`spmax:`, `stmax:`, `stm:`, `svt:`, `svr:`, `fhu:`, `pcal:`, `cal:`, `ptrig:`, `pitrig:`, `peq:`.

Development commands (`tshot`, `phold`, `pcap`, `dev:*`, ...) are serial-only over this channel.

### 3.5 Security properties

- Commands are authenticated, but not encrypted. Telemetry is plain JSON, and acks and hello replies are unauthenticated.
- Replay protection is the boot id plus a per-source-address `seq`. A captured valid datagram replayed from a
  different source address within the same boot would run again. Only allow-listed commands are reachable.
- The key is handed out over BLE only (`wifi:key?`), on the same proximity trust as BLE itself.
  That trust has no pairing or allow-list in this code (section 4.4).

A Python reference client is `diagnet/wifi_asiakas.py` (`hello`, `sub`, signed commands, summary of what arrives).

## 4. BLE GATT

### 4.1 Service

| Item | Value |
|---|---|
| Advertised name | `EspressoPico` |
| Advertising | connectable, interval 500 ms, 16-bit service UUID in the advertisement |
| Service | `0x180A` (the standard Device Information UUID, reused) |
| Data characteristic | `0x2A29`, flags READ and NOTIFY: Pico to app, JSON |
| Command characteristic | `0x2A2A`, flag WRITE: app to Pico, one command per write, UTF-8 |

The command write buffer is set to 128 bytes. Advertising restarts after a disconnect.

### 4.2 Notifications

- One notification carries one JSON object, at most 240 bytes. A longer one is shortened by dropping, in order,
  `tank_pct`, `tank_status`, `tank_water_l`, `thermal_stability`. If it is still too long it is not sent
  (`notify dropped` on stdout). The limit exists because a 309-byte packet hung the BLE stack on the Pico 2 W.
- Live telemetry goes out at most every 200 ms (5 Hz). Settings go out on connect, after a change, on `sync`,
  and every 2 s.
- Brew-log multipack frames can be longer than one notification. They are split into pieces of
  `min(240, MTU-3)` bytes (at least 20), 12 ms apart, and the frame ends with a newline. The app joins pieces until
  the JSON closes. No other notification is sent between the pieces of one frame, so live data and settings pause for
  the whole multipack.

### 4.3 Wi-Fi key hand-over

The write `wifi:key?` (BLE only, never over `EXA1`) is answered to the asking connection only, as
`{"type":"wifi_key","key":"<64 hex>","host":"<Pico IP or ?>","port":47211}` followed by a newline, chunked like a multipack frame.
The command is not printed, because stdout is mirrored to the diagnostics stream.

### 4.4 Trust

BLE writes go straight to `handle_command()`. There is no allow-list and no pairing in the firmware, so a BLE
client can issue every command in section 6, including the development commands.

## 5. Telemetry fields

JSON keys as sent. Units follow the code (`bar`, degrees Celsius, grams). Fields marked optional are only present when
the feature exists.

### 5.1 Live packet

| Key | Type | Meaning |
|---|---|---|
| `boiler_temperature` | float | boiler PT100 reading |
| `pressure` | float | calibrated pressure, bar |
| `mode` | string | state text: `IDLE`, `STEAM`, `WATER`, `DEV_SAFE`, `fast_heatup`, `pre-infusion ...`, `brew loop ...`, `soft pressure release ...`, and the names of development runs |
| `brew_temperature` | float | brew target |
| `pre_infusion_mode`, `pressure_soft_release_mode`, `fast_heatup_mode` | bool | feature flags |
| `pump_ratio` | number | pump duty reported by the controller |
| `thermal_stability` | float, optional | PI-integral based stability figure, 1 decimal |
| `tank_water_l`, `tank_pct`, `tank_status` | optional | estimated water-tank state (`pico/water_tank.py`) |
| `standby` | `true`, optional | present only while standby holds; absence means off |

### 5.2 Scale packet

Present only when a scale is attached and has a reading. On `EXA1` its keys are merged into the live packet.
On BLE it is a separate notification.

| Key | Meaning |
|---|---|
| `weight_g` | weight minus the app's tare (`tare`), 0.1 g resolution |
| `weight_abs_g` | calibrated absolute mass; the app uses `abs < 200 g` as "no tray" |
| `flow_g_s` | least-squares flow; a stale flow is `0.0`, not null |
| `first_drop` | true once the CUSUM first-drop detector has fired |
| `tray_water_g`, `tray_pct`, `tray_status`, `detected_object`, `object_weight_g` | smart-tray tracker (`pico/smart_tray.py`), optional |

### 5.3 Settings packets

Packet A: `brew_temperature`, `steam_temperature`, `steam_temperature_max`, `steam_valve_trigger`, `pre_infusion_mode`,
`pre_infusion_trigger_mode`, `pressure_soft_release_mode`, `fast_heatup_mode`.

Packet B: `steam_valve_release`, `steam_pressure_high`, `brew_pressure`, `pre_infusion_pressure`, `pre_infusion_time`,
`pressure_soft_release_time`, `pre_infusion_trigger_threshold`, `peq_mode`.

### 5.4 Calibration state

Sent with the live data only while a wizard is active.

- Pressure wizard: `pcal_state` (`idle`, `queued`, `running`, `done`, `corrected`, `saved`, `error`), `pcal_stage`,
  `pcal_msg` (40 characters at most), `pcal_gain`, `pcal_offset`.
- Scale wizard: `cal_phase` (`idle`, `quick_tare`, `quick_wait`, `quick_done`, `full_empty`, `full_left_ready`, `full_right_ready`,
  `full_tray_ready`, `full_done`, `error`, and the `*_measure`/`*_run` phases), `cal_msg`, `cal_err`.

## 6. Brew log multipack

A shot of at least 15 s that ends normally produces a log. It is held in RAM as `pending_brew_log` until the app acknowledges it.
The format is the "v3" of an earlier firmware that the app already knew (`pico/brew_logger.py`).

Frames, in order, each one JSON object:

1. Meta: `{"type":"brew_log","part":"meta","v":3,"id":<n>,"sample_hz":10,"duration_ms","n_samples","n_events","n_parts","truncated","scale_at_end_g","events":[[name,t_ms],...]}` plus `scale_meta` (`scale`, `trim_b`, `sense`, `off_a`, `off_b`) when a scale exists, so the app can rebuild grams from the raw cell counts.
2. Samples, `n_parts` frames: `{"type":"brew_log","part":"samples","id","i":<0..n_parts-1>,"of":n_parts,"rows":[...]}`, 20 rows each.
3. End: `{"type":"brew_log","part":"end","id","n_samples"}`.

Row: `[t_ms, T_x10, P_x100, F_x100, hx_a_raw, hx_b_raw, W_x10, flags]`. That is milliseconds since shot start,
temperature x10, pressure x100, flow x100, the two raw HX711 counts, weight minus the session tare x10, and flags
(bit 0 pump relay on, bit 1 heater relay on).

Events: `session_start`, `phase_PRE_INFUSION`, `phase_BREW`, `phase_SOFT_RELEASE`, `log_stop`, `log_stop_<reason>`, `session_end`.
At most 40 are kept. Pump edge events are not logged, because a phase-controlled pump switches every mains cycle.

Rules:

- Sampling is a 10 Hz grid from shot start; a late call skips the slots it missed. A session is capped at 65 s (`truncated: true`);
  one shorter than 15 s is discarded as an accidental tap.
- A new shot replaces an unacknowledged log.
- Sending starts by itself when a shot finishes, on connect (BLE), on `brew_log?` or `brew_log:get` (resend from meta), and on a new log (`EXA1`).
  `brew_log:ack:<id>` frees the RAM copy (any ack clears it).
- BLE sends one frame per 200 ms transmission tick; after 8 failed meta sends it waits for the next request.
  `EXA1` sends one frame per 100 ms to every subscriber and does not pause the live stream.

## 7. Command reference

Arguments in angle brackets are numbers. Ranges are those the code clamps to. `W` marks commands that `EXA1` accepts.
Commands that persist a setting return "updated" to the caller and are written to `settings.txt`.

### 7.1 Settings and app commands

| Command | Meaning |
|---|---|
| `sync`, `get:settings`, `settings?` (W) | resend both settings packets |
| `bt:<C>` (W) | brew temperature |
| `steam:<C>` (W), `stmax:<C>`/`stm:<C>` (W) | steam temperature, steam temperature maximum |
| `svt:<bar>`/`spl:<bar>`/`spmin:<bar>` (W) | steam valve trigger pressure |
| `svr:<bar>`/`svrel:<bar>` (`svr:` W), `sph:<bar>`/`spmax:<bar>` (W) | steam valve release pressure, steam pressure high limit |
| `pip:<bar>` (W), `bp:<bar>` (W) | pre-infusion pressure, brew pressure |
| `pit:<s>` (W) | pre-infusion time 0 to 6 s; 0 switches pre-infusion off |
| `srt:<s>` (W) | soft pressure release time 0 to 6 s; 0 switches it off |
| `pre:on\|off`, `spr:on\|off` | pre-infusion and soft release on/off (the app uses `pit`/`srt`) |
| `fhu:on\|off` (W) | fast heat-up mode |
| `ptrig:on\|off\|<g>`, `pitrig:...` (W) | pre-infusion trigger by first drop; threshold 0.05 to 0.50 g |
| `peq:on\|off` (W), `peq?` (W) | idle pressure equalisation on/off, status |
| `stby:on`, `stby:wake`/`stby:off` (W) | enter standby now, wake now |
| `stby:start:<min>`/`stby:boot:<min>`, `stby:brew:<min>`, `stby:<min>` (W) | standby timeout after start-up, after a shot, generic; clamped to 0 to 240 min |
| `stby?` (W), `stbt:<C>` (W) | standby status; standby temperature 60 to 95 |
| `tare` (W) | tare the scale |
| `cal:quick:<g>`, `cal:full:start`, `cal:next`, `cal:cancel` (W) | scale calibration wizard (quick: known mass 5 to 5000 g) |
| `pcal:run:<pre\|brew>`, `pcal:m:<stage>:<bar>`, `pcal:save`, `pcal:end`, `pcal:st` (W) | pressure calibration wizard; `pcal:st` prints state |
| `pcalset:<gain>:<offset>` | write the pressure calibration directly (gain 0.5 to 1.5, offset -3 to 3) |
| `brew_log?`, `brew_log:get`, `brew_log:ack:<id>` (W) | see section 6 |
| `sub` (W, `EXA1` only) | subscribe to the stream |
| `wifi:key?` | BLE only, section 4.3 |

### 7.2 Status and inspection (print to serial, change nothing)

`stby?`, `heat?` (relay guard and no-rise latch state), `ts?`/`thermal?`, `ts:p0:<v>` (writes the thermal-stability baseline),
`tray?`, `tray:empty`, `tray:cal_empty`, `tray:wmax:<g>`, `tank?`, `tank:fill`, `tank:set:<l>`, `tank:consume:<ml>`,
`tank:cal:<a>:<b>`, `obj?`, `obj:<cup\|scale\|vessel>:<g>`.

### 7.3 Development commands (serial or BLE, not `EXA1`)

| Command | Meaning |
|---|---|
| `tshot:<s>` / `tshot:stop` | test shot of 5 to 60 s through the same code path as the brew switch; refused unless `wmax` is set and the scale has a fresh reading |
| `wmax:<g>`, `wrise:<g>` | tray weight limits for test shots (absolute, rise per shot); 0 = off; persisted |
| `dev:safe` / `dev:resume` | relays off and no heating or pumping until resumed |
| `fmode:on\|off`, `fset:<g/s>`, `fwin:<ms>` | flow-control cascade, flow target, flow fit window (runtime only) |
| `pim:<0\|1>`, `bim:<0\|1>`, `euv:<0\|1>`, `c1x:<0\|1>` | pre-infusion method, brew method, turn-reservation fix, core-1 relay timing; runtime only |
| `kuri:<n>` | throttle-setting mode: pump at `n` strokes per second without pressure control (1 to 50; 0 = normal) |
| `klamp:<s>` / `klamp:stop` | throttle warm-up run, 10 to 120 s |
| `pzero:`, `pvent` | vented pressure zero; one vent cycle |
| `pcap:<ms>[:<bar>[:<phase_us>]]` / `pcap:stop` | raw 1 kHz pressure capture, 200 to 2500 ms, for mains-frequency analysis |
| `psweep:<ms>:<bar>[:<n>[:<mult>]]`, `plen:<bar>[:<reps>]`, `pgap:<bar>[:<n>[:<spacing_ms>[:...]]]`, `pstep:<bar>[:<hold_ms>[:<tail_ms>]]` | mains-cycle skipping experiments |
| `vkello:<bar>`, `vsweep:<reps>`, `mcal:<ms>` | mains-clock lock, phase sweep, mains calibration |
| `phold:<s>` / `phold:stop` | free pump and valve run, 1 to 120 s |
| `ystall:<s>[:<mode>]` | asyncio turn-reservation test without the pump |
| `pcalw:<ms>` | pressure calibration stroke window |

Experiment commands have a `:stop` form, and `dev:safe` ends them. Pump and heater switching in every one of them passes the
relay guard (see `ARCHITECTURE.md`).
