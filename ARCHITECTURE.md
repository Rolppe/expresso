# Architecture

This file is a map for someone who wants to change the firmware. It names modules and concepts and avoids
line-level detail. For the wire formats see [docs/PROTOCOL.md](docs/PROTOCOL.md), for the electronics
[docs/HARDWARE.md](docs/HARDWARE.md). Identifiers and comments in the code are partly Finnish; the glossary in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) translates them.

## Bird's-eye view

The problem: replace the control electronics of a Rancilio Silvia with a Raspberry Pi Pico 2 W. The Pico must hold boiler
temperature, run the vibratory pump against a pressure target (pre-infusion, brew, soft release), steam and hot-water modes,
weigh the drip tray, and talk to a phone app. The hard part is that mains power is switched by three relays that the firmware
controls: a bug or a hang can leave the heater or pump on. The second hard part is timing: the pump delivers one stroke per
mains cycle (20 ms), the pressure sensor lags the pump by tens of milliseconds, and MicroPython's garbage collector pauses
for 15 to 28 ms.

The solution has three layers, each with its own rules:

1. **Safety layer.** Relays driven off at boot and on every exit, a hardware watchdog, and limits enforced at the relay object.
2. **Control layer.** Cooperative `asyncio` tasks on core 0, with a second program on core 1 for the parts that cannot tolerate a
   pause. Controllers are a boiler PI, a pump pressure PI and a flow PI.
3. **Link layer.** One command dispatcher with four front doors: USB serial, BLE, Wi-Fi UDP (`EXA1`), and a one-way diagnostics stream (`EXD1`).

Around the firmware sit host tools: `pico_dev.py` flashes and drives the Pico over a serial link, `diagnet/keraaja.py` collects
diagnostics, and `testit/` runs the firmware modules on a desktop Python with fake hardware.

## Codemap

`pico/` is the firmware, copied to the Pico's flash as is. `pico/MANIFEST.json` lists every file with its SHA-256.

| Module | Role |
|---|---|
| `boot.py`, `devsafe.py` | Relays off before any other import; watchdog start and feed; `enter()` used by every development operation |
| `main.py` | Builds the objects, defines the asyncio tasks (local program, serial commands, scale reader, watchdog feeder, pressure equalizer, brew-log service, diagnostics, Wi-Fi link) and wraps `asyncio.run` in `try/finally` |
| `preset.py` | The only configuration: feature flags, defaults, GPIO pin map, MAX31865 settings, target temperatures, diagnostics host |
| `classes.py` | `BrewData` (the shared state object that every task reads and writes), `Thermostat`, `PumpPressureController`, `FlowController`, `PressureSensor`, `TemperatureSensor` including the core 1 reader and executor |
| `functions.py` | The long-running procedures: `run_shot`, pre-infusion variants, hot water, fast heat-up, pressure calibration, and all development experiments (`pressure_*_run`); also load/save of `settings.txt` |
| `relayguard.py` | `RelayGuard` and `GuardedRelay`: limits at the pump and heater |
| `commands.py` | `handle_command()`: the single dispatcher; `SerialLine` parser |
| `bluetooth_handler.py` | BLE GATT service and payload builders (`live_payload`, `settings_payloads`, `brew_log_frame`) that `wifilink.py` reuses |
| `wifilink.py` | `EXA1`: HMAC-authenticated UDP command channel and telemetry subscription |
| `diagnet.py` | `EXD1`: stdout tee into a ring buffer, heartbeat lines, UDP sender |
| `brew_logger.py` | 10 Hz shot recorder, RAM only, handed to the link layer as a multipack |
| `scale.py`, `scalecal.py`, `smart_tray.py`, `water_tank.py` | Two-cell HX711 scale with flow fit and first-drop detector; calibration wizard; tray fill tracker; tank level estimate |
| `verkkokello.py` | Mains-phase clock (Kalman filter plus I/Q phase measurement from pressure ripple) |
| `backflush.py`, `ystall.py` | Backflush cleaning programme; asyncio turn-reservation test |
| `lib/` | Adafruit MAX31865 and SPI device drivers (MIT), adapted for core 1 |
| `ugit.py`, `api_functions.py`, `boot_bluetooth_test.py` | Not used by `main.py`; see the limitations in the README |

Outside `pico/`:

| Path | Role |
|---|---|
| `pico_dev.py` | Host tool: raw-REPL flash with hash verification, `CMD` sender, capture of experiment output, lock, devsafe on every entry |
| `diagnet/` | `keraaja.py` collector (UDP to log files and optional Home Assistant), `wifi_asiakas.py` reference client of `EXA1` |
| `testit/` | 41 `*_smoke.py` regression tests, 37 simulation, analysis and hardware-probe scripts, 349 device logs |
| `scale/testit/` | Scale hardware tests |
| `ohjevahti.py` | Claude Code `PreToolUse` hook that checks device commands against the owner's written instructions |
| `build_set.py`, `localenv.py` | Phone-link set builder (legacy); `local.env` loader |
| `*.md`, `paketit/` | Working notes, briefs and specs; see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |

## Architectural invariants

- **The pump and heater pins are never switched on except through `GuardedRelay`.** `BrewData` does not keep the raw pins.
  `testit/turva_toimilaite_smoke.py` greps the firmware source to check that no code path constructs a pump or heater `Pin` outside
  a `GuardedRelay(...)`. Switching *off* always passes. The solenoid is deliberately unguarded because opening it only releases pressure.
- **Nothing runs before the relays are off.** `devsafe.relays_off()` is the first statement of `boot.py` and of `main.py`, and the last
  statement of `main.py` on any exit path.
- **Nothing in the link layer can stop the control loop.** `DiagNet.step`, `WifiLink.step` and the serial task catch every exception,
  count it and carry on, because one exception in an `asyncio.gather` task ends all tasks.
- **No control path waits for the network.** Sockets are non-blocking, destinations are IP literals, a failed send drops data and counts it.
  The radio is not reconnected while a shot records.
- **Core 1 allocates nothing.** It runs with the heap locked and integers only, and each shared word has one writer.
- **A packet that a BLE central cannot receive is never sent.** Notifications are capped at 240 bytes and trimmed in a fixed order.
- **Wi-Fi allows nothing that BLE does not allow.** The allow-list in `wifilink.py` is a subset of the dispatcher's commands,
  and the link key is handed out only over BLE.
- **Settings are written whole or not at all.** `settings.txt` and `brew_heat.json` go through a temporary file and a rename.
  Firmware files are flashed as `<name>.new`, hashed on the Pico, and renamed only after all hashes match.
- **Experiment parameters do not survive a reboot.** Flow mode, method switches and measurement knobs are runtime-only,
  so a restart always returns to pressure control and the normal shot path.
- **Test shots need a tray limit.** `tshot` refuses to start without `wmax` and a fresh scale reading.

## Boundaries

**Core 0, asyncio.** Every task is cooperative and yields with `sleep_ms`. `main.py` measures each task's busiest turn (`task_busy`)
and its lateness (`task_late`), and reports them in the diagnostics heartbeat, so a task that holds the loop is named in `EU_STALL` lines.
The shot procedures in `functions.py` run to completion inside one task and are written to the 1 ms to 20 ms budget of the pump.

**Timer interrupt.** `RelayGuard.poll` runs from a `machine.Timer` every 100 ms. It reads only the ADC and fields of `BrewData`, never SPI or
HX711, so it cannot collide with a read in progress, and it runs even inside the busy capture loops that never yield.

**Core 1, `_thread`.** One program at a time: a temperature reader (MAX31865 conversions in short allocation-free steps), or an executor that samples
the pressure ADC at 1 kHz into a ring and switches the pump relay at times that core 0 queued ahead. A shared array carries the handshake.
The relay guard can veto the executor through a one-word flag that it clears on a trip.

**Firmware and host.** The host talks to the running firmware only through the `CMD` protocol, and to the stopped firmware (flash, verify) through
the MicroPython raw REPL after a devsafe sequence. `pico_dev.py` feeds the watchdog during both.

**Firmware and app.** The app sees the machine only as JSON objects and short ASCII commands. The formats are in `docs/PROTOCOL.md`;
payload builders live in `bluetooth_handler.py` so that BLE and Wi-Fi send identical objects.

## Cross-cutting concerns

- **Error handling.** Hardware faults become relay trips (`GUARD_TRIP ... reason=`), not exceptions: overpressure, run time, sensor plausibility,
  stale or implausible temperature, a heater that does not warm the boiler. Protocol errors are counted and acknowledged or dropped;
  an unknown command is reported (`CMD_UNKNOWN`, ack `unknown`) rather than silently acknowledged.
- **Observability.** All stdout is mirrored into the diagnostics ring. `DIAG_HB` (counters, heap, longest sends, task lateness) and `DIAG_MIN`
  (heater and pump on-time, pressure statistics per minute) exist because a run on the Pico otherwise leaves no trace. `testit/*.log` holds
  captured device output from the experiments.
- **Testing.** Firmware modules are plain Python. Tests import them on a desktop interpreter with a fake clock, fake `Pin`, fake sockets, and drive
  the same code paths as the device (`testit/*_smoke.py`). Control behaviour is first designed in simulation (`*_sim.py`), then checked on the machine
  with `pico_dev.py` runs whose logs are kept.
- **Security.** The `EXA1` link authenticates commands with HMAC-SHA256 and a per-boot id; BLE has no pairing; secrets live in files that git ignores
  (`secrets.py`, `local_config.py`, `link_key.txt`, `local.env`). Details and the replay limits are in `docs/PROTOCOL.md`.
- **Performance.** Allocation is the enemy: preallocated ring and packet buffers, `ipoll` instead of a `recvfrom` that allocates on EAGAIN,
  integer arithmetic on core 1, lazy imports of rarely used experiments, `gc.mem_free()` (7 ms) avoided during shots.

## Key design decisions

### 1. Safety limits sit at the actuator, not in the commands

- **Context.** On 19.9.2026 a new development command (`phold`) pumped for up to 120 s without the drip-tray limit, because the limit lived inside one
  command's function and the new command copied its stop conditions from another one. The tray began to overflow and the owner cut the machine's power.
  Two other commands lacked an overpressure limit for the same reason.
- **Decision.** `BrewData.get_relays()` hands out `GuardedRelay` objects. Every `value(1)` on the pump or heater asks `RelayGuard.allow()`, and a 100 ms timer
  forces a relay off while a limit is hit: pressure above 13 bar, pump run over 180 s, boiler at 160 C or reading older than 10 s, a pressure sensor reading
  far below zero, and a heater that is on for 120 s without warming the boiler.
- **Consequences.** A command written next year gets the limits without knowing about them. The limits are deliberately looser than each path's own,
  so they are a last line and never change a working run. The tray-weight limit stays in test paths, because a real shot has a cup on the scale.
  The no-rise latch needed a retry rule, because the Pico stays powered while the machine is off the mains.

### 2. Relays off first, and a hardware watchdog

- **Context.** The owner pointed out that stopping the firmware can leave the heater relay on, and that a hang (a BLE stack hang on 17.9.2026) needed a power
  cycle. Development runs without anyone at the machine.
- **Decision.** Relays go low before any import in `boot.py`; `main.py` repeats it in `finally`; an 8 s `WDT` is fed once a second by a task; every host
  operation starts with Ctrl-C and a read-back that must report all three relays at 0 (`devsafe.enter()`).
- **Consequences.** A crash ends in a watchdog reset 8 s later with the relays already low. The watchdog runs once started, so a soft reset (Ctrl-D) during
  boot can trip it; tools use `machine.reset()`, and `pico_dev.py` does not use `mpremote`, which would not feed the watchdog.

### 3. A second core for the parts that cannot pause

- **Context.** A MAX31865 reading blocks for 75 ms or more, which the shot loops cannot take. Without a fresh temperature the relay guard blocks the heater
  after 10 s. Reading in small steps inside the shot loop made pressure control worse in the smoke test. Automatic garbage collection took 15 to 28 ms.
- **Decision.** Core 1 reads the temperature, and in the pre-infusion and brew phases also acts as an executor: 1 kHz sampling and relay edges at their due times,
  from a queue that core 0 fills ahead. It never sleeps (a sleep on core 1 stretched core 0's collections), never allocates, and shares integer arrays with one writer per field.
- **Consequences.** Core 0 no longer sleeps for the sensor (the heartbeat had shown its main loop 175 to 295 ms late), at the price of a second execution model that is hard to debug. The executor refuses to
  switch anything on unless core 0 and the guard have armed it, and it turns the pin off after 35 ms without an event.

### 4. A mains-phase clock built from pressure ripple

- **Context.** The vibratory pump produces one pressure stroke per mains cycle, and the best control skips or gates individual cycles. There is no zero-cross detector in the hardware.
  A fixed 19 960 us period is wrong by up to 80 us per cycle across the 49.9 to 50.1 Hz range, which is 4 ms per second; a measurement series drifted a whole cycle in 14.8 s.
- **Decision.** `Verkkokello` is a numerically controlled clock whose phase, period and period drift are estimated by a three-state Kalman filter. The measurement is an I/Q (lock-in)
  phase estimate of the pressure ripple at the clock's own frequency, averaged over 8 cycles, minus a known pump-to-sensor delay. Windows with abnormal amplitude or low pressure are rejected.
  The clock was first built and validated in a host simulation (`testit/verkkokello_sim.py`), and the firmware port is checked against a holdout (`testit/verkkokello_holdout.py`).
- **Consequences.** The clock can only be corrected while the pump runs and produces ripple; between runs it holds the last period. It needs transient and pressure gates, which were
  added after device runs showed locks 1.4 to 1.7 ms off.

### 5. UDP with HMAC for the app link, not TCP

- **Context.** The owner wanted the phone to talk to the machine directly over Wi-Fi, with logs still going to Home Assistant. The Pico's latency was already being hunted (a shot-time
  collection of 111 ms, a BLE task turn of 63 ms), and TCP means connection state, lwIP buffers and stream allocations on that heap.
- **Decision.** One datagram per message, non-blocking, reliability in the protocol (sequence number, repeat-safe ack). Commands are signed with a hand-written HMAC-SHA256
  (MicroPython has `hashlib.sha256` but no `hmac`) over `boot seq command`; the key is handed over once through BLE.
- **Consequences.** Nothing new is exposed that BLE did not already expose. Replay protection is the boot id plus a per-address sequence number, and telemetry is not encrypted.

### 6. Diagnostics as a never-blocking ring buffer

- **Context.** Failures appeared late in a run (pump control with a long delay after hours of uptime) and left no trace when no computer was attached, since the Pico keeps no log.
- **Decision.** Tee all stdout into a preallocated 8 KiB ring, send it as UDP from a task that never waits, and count what is lost. The ring updates with interrupts off,
  because the relay guard prints from a timer callback, and nothing is allocated inside that section.
- **Consequences.** A collector sees the same text a serial terminal would, plus counters. When the ring overflows, the oldest bytes are lost, and the loss is visible in the `drop` field.
