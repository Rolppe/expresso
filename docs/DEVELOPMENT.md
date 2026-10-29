# Development

How this project was built, and how to read the working notes that are left in the repository.

## The workflow

The author, Mikko Paaso, set the requirements and made the design decisions. The code was written by Claude Code agents from written briefs.
Hardware runs and the test suite decided whether a piece of work was accepted.

1. **Requirement.** The owner states what the machine must do or must never do, in their own words. The agent copies those words,
   unchanged, into `KAYTTAJAN-TIEDOT.md` and gives each one a name (`TILAUS-A` to `TILAUS-T`, `TILAUS-RELEET-ALAS`, `TILAUS-AUTONOMIA`).
   A summary is not allowed to replace a quotation, because summarising is how requirements were lost earlier.
2. **Plan.** A planner session reads the notes and writes a plan or spec in `paketit/` (for example `VERKKOKELLO.md`, `WIFI-APPI.md`, `DIAGNET.md`).
   For control code it often builds a host simulation first (`testit/*_sim.py`) and a test the executor never sees (a "holdout").
3. **Brief.** One unit of work becomes `paketit/<NAME>.brief.md` with fixed sections: *Task*, *Files* (`may`, `must not`, `read` with line ranges),
   *Do* (numbered steps), *Acceptance* (shell commands that must succeed) and *Budget* (a line-count limit, measured). A brief names the requirements it
   touches. The `must not` list protects the holdout tests and files outside the task.
4. **Execution.** An executor agent (Sonnet in all 19 logged dispatches, none escalated) runs the *Do* list and the acceptance commands, and reports back.
   `paketit/delegation.jsonl` records each dispatch: model, iterations, elapsed time, and a note.
5. **Corrections.** If acceptance fails or the result is wrong, the planner writes `<NAME>.correction-N.md` and the executor tries again.
   Some briefs needed up to six corrections (`VIRTAUSSAATO-2`).
6. **Hardware gate.** Anything that changes behaviour is flashed with `pico_dev.py` and run on the machine. Raw output is kept in `testit/*.log`
   (349 files). Test shots run with a tray weight limit and relays-down-first.
7. **Review.** The owner reviews results and decides what stays. The registers record the outcome.

A guard hook, `ohjevahti.py`, was written to support step 6: a Claude Code `PreToolUse` hook that parses `pico_dev.py` commands and stops or flags a device run
that deviates from instructions recorded in `OHJEKIRJA.json`. It exists because one agent session on 20.9.2026 deviated seven times from the owner's stated
instructions (`paketit/OHJEPOIKKEAMAT-20260920.konteksti.md`). The hook has a smoke test (`testit/ohjevahti_smoke.py`). `OHJEKIRJA.json` in this repository is empty, and a check recorded in `HISTORIA.md` (25.9.2026)
found that the hook was not installed in the author's Claude Code settings.

## Working notes (Finnish)

These files are the author's and the agents' working notes. They are in Finnish and are left in the repository unedited as a record of the process.
They contain dates, session-internal names and paths from the private repository they came from, so read them as history, not as instructions.

| File | What it is |
|---|---|
| `REKISTERI.md` | The register: current state, the next work packet (`SEURAAVA PAKETTI`), open issues, and "Todettu" (established) findings by date |
| `HISTORIA.md` | Change history: what was done each day, with measurements and commit ids |
| `ARKISTO.md` | Archive of closed work moved out of the register to keep it short |
| `KAYTTAJAN-TIEDOT.md` | The owner's orders and facts about the machine, as quotations; the standing requirements |
| `KEHITYSYHTEYS.md` | The development link (earlier phone-based, then Pi Zero), tools, protocol notes and measurements |
| `PICO-HALLINTA.md` | Managing the Pico: link chain, flashing, restore, pitfalls |
| `konteksti-virtaussaato.md` | Context report for the flow-control work |
| `paketit/*.brief.md`, `*.correction-N.md` | Briefs for executor agents and their corrections (34 briefs, 24 corrections) |
| `paketit/*.spec.md` | Specs with acceptance criteria written by the planner (11) |
| `paketit/*.konteksti.md`, `PUMPPU-PWM-KONTEKSTI.md` | Context reports gathered before planning |
| `paketit/*.md` (other) | Plans and analyses per topic, such as `VERKKOKELLO.md`, `TURVAKATO.md`, `WIFI-APPI.md`, `DIAGNET.md` |
| `paketit/delegation.jsonl` | One JSON line per dispatch to an executor agent (19) |
| `OHJEKIRJA.json`, `ohjevahti.py` | Instruction book and the guard hook described above |

The numbers above are counts of files in this repository. The history has 203 commits between 2026-09-17 and 2026-10-29; 185 of them carry a `Co-Authored-By`
trailer naming a Claude model. The development material was added to this repository on 2026-10-29 from the private repository it was extracted from.

## Running the tests

```
python3 testit/<name>_smoke.py      # RESULT: <n> failed
```

The tests import the firmware from `pico/` by relative path and need only the Python standard library. Use `FW=<dir>` to point a test at another firmware copy where a test supports it.
The result of the last full run is in the README. Scripts that talk to the machine (`pcap`, `shot_*`, `scale_*`, `tray_calib`, `*_probe`) need the hardware and a configured
`local.env`. `testit/tilaus_invariantit_smoke.py` needs a tool of the private monorepo and fails here.

## Glossary

| Finnish | English | Where it appears |
|---|---|---|
| uutto | extraction, the brew shot | `functions.py`, `uuttoloki_smoke.py`, `PB_`/`TS_` log lines |
| esiuutto | pre-infusion | `esiuutto_smoke.py`, `EU_*` log lines |
| uuttoloki | brew log | `brew_logger.py`, `uuttoloki_smoke.py` |
| keitin | the machine | notes |
| lämmitin, pumppu, solenoidi/magneettiventtiili | heater, pump, solenoid valve | notes, `PINS` |
| kaukalo, vaaka | drip tray, scale | `tray_guard_smoke.py`, `vaaka_komennot_smoke.py` |
| höyry, kuumavesi | steam, hot water | `steam_paine_smoke.py`, `kuumavesi_smoke.py` |
| valmiustila | standby | `valmiustila_smoke.py`, `stby:` commands |
| verkkokello | mains clock | `verkkokello.py`, `vkello`, `VKELLO` lines |
| verkkotaajuus, verkkojakso | mains frequency, mains cycle | `PWM-1A-VERKKOTAAJUUS` briefs |
| paine, tasaus | pressure, equalisation | `paine_tasaus_smoke.py`, `peq:` |
| kuristin | throttle (flow restrictor) | `kuri:`, `klamp:`, `KURI_*` lines |
| ydin | core (of the RP2350) | `C1-JAKSOT` = core 1 cycles |
| jälkinousu | post-shot pressure rise | `c1x_lag_smoke.py`, `C1X-JALKINOUSU` |
| pyyhkäisy | sweep | `psweep`, `vsweep` |
| portitus | gating (letting selected mains cycles through) | `PWM-1B2-PORTITUS` |
| turva, turvakato | safety; "safety lost" (the analysis of the 19.9.2026 incident) | `TURVAKATO.md`, `turva_*_smoke.py` |
| toimilaite | actuator | `turva_toimilaite_smoke.py` |
| vahti, vartio | guard | `ohjevahti.py`, `relayguard.py` comments |
| releet alas | relays down | `TILAUS-RELEET-ALAS`, `devsafe.py` |
| nollausikkuna | reset window: the time after a reset before the relays are driven low | `nollausikkuna_smoke.py` |
| keräin | collector | `diagnet/keraaja.py` |
| pysyvyys | persistence | `settings_pysyvyys_smoke.py` |
| paketti | work packet: a unit of delegated work | `paketit/` |
| korjaus | correction (a follow-up brief) | `*.correction-N.md` |
| tilaus | an order: a requirement quoted from the owner | `KAYTTAJAN-TIEDOT.md`, `TILAUS-*` |
| todettu | "established": a fact checked and recorded | `REKISTERI.md` |
| viat | faults: the list of known defects | `REKISTERI.md`, `HISTORIA.md` |
| skooppi | scope: the author's name for one area of a multi-session workspace | notes |
| pakkaus, pura | pack, unpack: the hand-over of context between sessions | notes |
| ohjekirja | instruction book | `OHJEKIRJA.json` |
| laitetodennus | verification on the device | `REKISTERI.md` |
