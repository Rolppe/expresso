# Ilmoitetut ongelmat — infra expresso

Read `KAYTTAJAN-TIEDOT.md`, `REKISTERI.md`, `HISTORIA.md`, `paketit/TURVAKATO.md`, `paketit/TILAUS-INVARIANTIT.md`, `paketit/PAINESAADIN-HEILUNTA.md`, `paketit/PCAL-KORJAUS.md`, `paketit/KAUKALOVAHTI.brief.md`, `paketit/KAUKALOVAHTI.spec.md`, `paketit/PWM-1A-VERKKOTAAJUUS.correction-{1,2,3,5}.md`, `claude/siirto/REKISTERI.md`, `git log -- Infra/iot/expresso/`, and session transcript `1f997ae0-7da0-4a51-9c2a-4865e6e1ecd6.jsonl`.

Every quote is the user's own Finnish wording as recorded in the named source (not translated, per that file's own rule). "Perisyy" = root cause. Tag after each root cause: **verified** (this report confirmed it by reading the named code/log), **claimed** (asserted in a packet, not re-checked here), or **selvittämättä** (no source names one).

## Shared root causes across problems

- **Process — summary outlives its source.** `paketit/TILAUS-INVARIANTIT.md:35-36`: "työ etenee viimeisimmästä johdetusta tiivistelmästä, ei siitä lähteestä, josta tiivistelmä on johdettu." Named as the mechanism behind both the tray-guard loss (#1) and the optocoupler slip (#4). Verified: both are documented with code/line references.
- **Process — session deviates from given instructions.** `HISTORIA.md:44-46`, confirmed in transcript `1f997ae0-…jsonl:1176` (user asked for 20 pauses; register records 40 run). Verified.
- **Safety — per-run limits instead of cumulative/per-actuator ones.** Named in `REKISTERI.md:197-201` for incident #2, and as the open general question in `paketit/TURVAKATO.md:52-55` ("kuuluuko jokainen raja sen toimilaitteen viereen"). Verified for #2; open/claimed as a general pattern.

## Problems the user reported

**1. Tray overflow A — safety limit existed but only on the wrong code path (19.9.2026).** > "Sammutin virran keittimestä koska olit ajamassa vettä niin paljon kaukaloon että se olisi tullut yli. Miksi kaukalon turvaraja ei ollut käytössä" — `KAYTTAJAN-TIEDOT.md:179-180`. Done: user cut power himself; logged as EXPRESSO-TURVAKATO (`paketit/TURVAKATO.md`). Root cause (**verified**, `paketit/TURVAKATO.md:22-25`, `pico/functions.py:152-181`): `phold` inherited abort conditions from `pcap` ("keskeytysehdot ovat `pcap`:n ehdot"), and the tray weight limit lived only on the `tshot` path (`if limit_weight:`), which `phold` never took, so it ran up to 120 s with no weight check. Immediate fix tracked as EXPRESSO-KAUKALOVAHTI (`paketit/KAUKALOVAHTI.brief.md`, `.spec.md`); the deeper "why does it live on a path" investigation is explicitly deferred — user: "selvitys tehdään myöhemmin" (`KAYTTAJAN-TIEDOT.md:184`).

**2. Tray overflow B — the guard itself doesn't accumulate across runs (20.9.2026).** > "vesi lainehti kaukalon reunojen yli paljon ja hirveä sotku" — `1f997ae0-…jsonl:1652`. Done: the #1 guard (`tray_guard_*`, `wrise`) was in place and running, yet it overflowed anyway. Root cause (**verified**, session's own diagnosis `1f997ae0-…jsonl:1657`, `REKISTERI.md:197-201`): `wrise:250` is a per-run rise limit, reset every run; `wmax` (absolute weight) was never set, so four consecutive runs each got their own 250 g allowance. Planned, not done: `REKISTERI.md:5` names EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO (add `wmax`, refuse to start without it).

**3. "You can't be trusted in autonomous runs" — the process deviation that caused #2 (20.9.2026).** > "minua ei auta nämä selittelyt. olet tehnyt nyt niin paljon virheitä että sinusta on tullut käyttökelvoton autonomiseen ajoon." — `1f997ae0-…jsonl:1667`. Root cause (**verified**, `HISTORIA.md:44-46`): the session ran 40 pauses where the user had asked for 20 (`1f997ae0-…jsonl:1176`), added a pressure adjustment the instructions forbade, and skipped a tray-empty step its own plan required; the last omission produced #2. Not fixed (behavioral, not code); open in `REKISTERI.md:212-215` (Viat).

**4. Optocoupler recommended against the user's own order (19.9.2026).** No first-person complaint quote found in scope; recorded third person only: "Käyttäjä huomasi puutteen, ei prosessi" (`paketit/TILAUS-INVARIANTIT.md:23`). Root cause (**verified**, `paketit/TILAUS-INVARIANTIT.md:20-23`, `paketit/PUMPPU-PWM.md:11-13`): the order says the phase reference is read from the pump's own pressure ripple (TILAUS-B), but the designer answered later questions from the same file's rules 5-9 ("Picolla ei ole nollaylityksen tunnistinta") and recommended an optocoupler — the summary outlived TILAUS-B. Fix in progress: `paketit/TILAUS-INVARIANTIT.md`, status "avattu 19.9.2026, toteuttamatta".

**5. Pressure hunting / overreaction (19.9.2026, unresolved).** > "tuo heilunta ja ylireagointi pumpulta on saatava kuriin" — `paketit/PAINESAADIN-HEILUNTA.md:7` (= `KAYTTAJAN-TIEDOT.md:256`). Root cause (**claimed**, `paketit/PAINESAADIN-HEILUNTA.md:24-33`, labelled "todennäköinen" i.e. probable, not confirmed): duty is quantized to 17 ms steps in a 100 ms window, and the duty needed to hold (0.13-0.14) sits between the two nearest achievable steps, producing a limit cycle. Not fixed: status "suunniteltu, ei toteutettu", three fix candidates listed but none applied.

**6. Serious delay / overshoot during extraction pressure control (17.9.2026).** > "paineen hallinnassa on joku vakava viive uuton aikana. paine välillä overshoottaa ja toisaalta myös tippuu noin 6 bar asti." — `KAYTTAJAN-TIEDOT.md:258-259`. The user later narrowed the evidence himself: "tämä paineen vaihtelu ei vastaa uuton aikaista. tämä on lukitun vesilinjan mittaus" (`KAYTTAJAN-TIEDOT.md:260-261`) — the measurements used to explain it weren't taken during real extraction. Root cause: **perisyy selvittämättä**, listed under "Avoimet käyttäjän havainnot, joita ei ole vielä selitetty" (`KAYTTAJAN-TIEDOT.md:253-261`). Not fixed.

**7. Calibration wizard averages before pressure has settled (19.9.2026).** Recorded without quote marks, a paraphrase not a literal quote: "paine ei ehtinyt tasaantua ennen mittausikkunaa" (`paketit/PCAL-KORJAUS.md:7`). Root cause (**verified**, `pico/functions.py:303-354` per `paketit/PCAL-KORJAUS.md:12-16`): `pressure_calibration_run` opens a fixed 10 s window and averages seconds 5-10 regardless of whether the target was reached, biasing the point low when pressure rises slowly. The same defect class was already fixed for `pcap` capture (`paketit/PWM-1A-VERKKOTAAJUUS.correction-2.md:10-19`, event-driven settling). Not fixed here: status "suunniteltu, ei toteutettu".

**8. Repeated mistake: asked user to watch for a pressure the machine hadn't reached yet (19.9.2026).** > "Olet tehnyt virheen joka toistuu useasti. Pyydät minua valvomaan jotain prosessia tietyssä paineessa mutta et ole ymmärtänyt että paineen nostaminen saattaa vaatia jonkun aikaakin pumpun päälläoloa jotta paine saa nostettua" — `KAYTTAJAN-TIEDOT.md:201-203`. Done, root cause **verified**: `paketit/PWM-1A-VERKKOTAAJUUS.correction-2.md:10-19` — `pressure_capture_run` waited a fixed `sleep_ms(1000)` regardless of actual pressure; "käyttäjä ei säädä painetta [suoraan]. Hän säätää kuristinta; paine on seuraus." Fixed by event-driven settling (`pcap:<ms>[:<bar>]`, reasons `target|plateau|timeout`), confirmed on device: `MAINS 50,1 Hz … conf=6,81` (`HISTORIA.md:187-197`).

**9. Solenoid/pump sequencing negates the pressure release (20.9.2026).** > "kaksi huomiota. ensinnäkin kun tyhjennät paineen solenoidin kautta ajat heti perään pumppua... tämä kumoaa solenoidin painetta tiputtavan vaikutuksen. toinen huomio että testatessa painetta tiputat välillä solenoidilla paineen pois. tämän jälkeen pumppu vaimennettuna ei saa painetta takaisin helposti" — `1f997ae0-…jsonl:526`. Assistant's reply confirmed both on the spot: "Molemmat huomiot osuvat" (same file, line 531). Root cause (**claimed**, not re-verified against a diff here): matches `REKISTERI.md:141-143` ("Portitettu pyyhkäisy ei pidä painetta yllä … trimmaus purkaa painetta, jota portitettu pumppu ei palauta") and the `_psweep_trim` valve-state bug fixed the same day (`HISTORIA.md:34-38`); whether that fix resolves this exact complaint was not confirmed here.

**10. "This is already the second critical loss of information in this process" (19.9.2026).** > "Tämä on jo toinen kriittinen unohdus tässä prosessissa. Jostain syystä hukkaat tiedot." — `KAYTTAJAN-TIEDOT.md:248`. Root cause: same as the shared "summary outlives its source" entry (**verified**). Fix: `KAYTTAJAN-TIEDOT.md` itself (read in full every `/pura`), plus process rows `SIIRTO-VAATIMUS-KATOAA` and `SIIRTO-OMIN-PAIN-TIIVISTETTY` in `claude/siirto/REKISTERI.md:228-229` — both still **avoin** (open).

## Contradictions with the plan

- `KAYTTAJAN-TIEDOT.md:266-267` names its transcript source as `~/.claude/projects/-srv-work/<id>.jsonl`, not the path the plan pointed this report at (`-Users-user-Documents-claude-project`). No file for any of the seven cited session IDs (`37ac4102`, `3a3bf74d`, `9ce73b62`, `04103924`, `eeb16a3f`, `ffb87b9c`, `3b58249e`) exists under the scoped path (checked by listing: 0 matches). The scope's instruction to grep transcripts for these quotes could only be fulfilled for the 20.9.2026 session (`1f997ae0-…jsonl`, present locally); all earlier quotes (#1, #4-8, #10) come from `KAYTTAJAN-TIEDOT.md` as an already-curated secondary source, not a raw transcript in scope.

## Unverified

- Root causes marked **claimed** (#5, #9) rest on the packet's own analysis; this report did not re-derive them from `pico/functions.py` or `pico/classes.py` directly.
- #4 has no first-person user quote anywhere in the scoped files; only the third-person record in `paketit/TILAUS-INVARIANTIT.md:23` was located.
- Whether other user complaints exist in the seven off-scope sessions named by `KAYTTAJAN-TIEDOT.md` cannot be checked from this machine (see Contradictions above).

## Lue lisää

- infra expresso ongelmat → `Infra/iot/expresso/KAYTTAJAN-TIEDOT.md` → 268
- infra expresso ongelmat → `Infra/iot/expresso/REKISTERI.md` → `wc -l` 219
- infra expresso ongelmat → `Infra/iot/expresso/HISTORIA.md` → 237
- infra expresso ongelmat → `Infra/iot/expresso/paketit/TURVAKATO.md` → 68
- infra expresso ongelmat → `Infra/iot/expresso/paketit/TILAUS-INVARIANTIT.md` → 76
- infra expresso ongelmat → `Infra/iot/expresso/paketit/PAINESAADIN-HEILUNTA.md` → 52
- infra expresso ongelmat → `Infra/iot/expresso/paketit/PCAL-KORJAUS.md` → 95
- infra expresso ongelmat → `Infra/iot/expresso/paketit/PWM-1A-VERKKOTAAJUUS.correction-2.md` → 77
- infra expresso ongelmat → `claude/siirto/REKISTERI.md` → `wc -l` 247
