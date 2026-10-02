# Design method: interfaces, changes, BOM and AI teams (FOSS only)

**Date:** 2026-10-01 · **Owner constraint:** FOSS only. Every tool below is judged by its OSI licence, read from the repository's licence file. Paid tiers, SaaS and proprietary data APIs are excluded as tools.
**Question:** how does our method compare with established hardware and systems-engineering practice? Our method is the `docs/system` set, the generated `integration-map.md`, `tools/plm.py` and the ECRs (engineering change requests). What should change, and how should parallel AI design teams work?
**Evidence:** three research notes, each re-checked by an independent fact-checker. Their corrections are applied here.
- [`methodology/method.md`](methodology/method.md): interface practice.
- [`methodology/plm-tools.md`](methodology/plm-tools.md): FOSS PLM, traceability and CI tools.
- [`methodology/bom.md`](methodology/bom.md): FOSS BOM management.

Probes re-run today, fenced: `plm.py status` at 20:52 EDT, `git tag`, and the ECR files.

**Picture:** `docs/diagrams/methodology.png` shows the proposed flow and marks, for each stage, what exists today and what is missing.

**Parts named in this note:**
- **STM32U575**: ST's Cortex-M33 MCU.
- **TPS7A2030**: TI's 300 mA, 3.0 V LDO (low-dropout linear regulator).
- **SPH0641LU4H-1**: Knowles' ultrasonic PDM mic. Its sound port is 0.77 mm off the package centre.
- **PMCXB290UE**: the Nexperia complementary MOSFET pair chosen for the H-bridge (LCSC C19654206).
- **PMCXB900UELZ**: a different Nexperia pair (C552750).
- **KMT022 / KMT031**: C&K sealed tact switches. The KMT022 needs 1.6 N to press (C221707); the KMT031 needs 3.4 N (C221708).
- **BQ25180**: TI's charger, in a 0.40 mm-pitch DSBGA (chip-scale ball-grid package).

---

## 1. Verdict

**The design of the method is ahead of most small teams. Its operation is not, and its core mechanism detects change, not disagreement.**

| | |
|---|---|
| **Solid (keep)** | **Generated architecture.** The integration map comes from the SKiDL schematic, so pin names are authoritative. Functions F1–F15 each have electrical, mechanical and firmware chains, which amounts to a functional architecture with allocation. That is better than a hand-kept set of ICDs (interface control documents). |
| | **Fine-grained watches.** Suspect stamps sit on the exact net, part, placement entry or Python symbol that carries each interface. That is finer than Doorstop or any other FOSS tool we found: `plm.py impact ref:Q1` gives exactly the 2 interfaces a Q1 change touches. |
| | **Clean precedence.** The spec beats the source files, and the source files beat the docs. "Staleness is a bug." The owner acts as a one-person change board. |
| | **Real cross-check.** `integration-map.md` §10 is an 8-point check covering functions, nets, pins, rails, off-board wiring, mechanics, firmware and dependencies. |
| | **Light.** Everything is git text, needs no server, and `status` runs in about 1.5 s using 256 MB. |
| **Biggest hole** | **It detects *change*, not *inconsistency*.** A hash stamp can't tell that the two sides of an interface disagree. Two live defects were found by hand, and no tool would catch them or a recurrence. A reviewer could baseline both as green. **(1)** The mic port on the board and the lid bore are **0.75 mm apart**, because both sides assumed the port sits at the package origin (`sub-audio-in.md` Open issue 1). **(2)** H-bridge peaks of **~315–323 mA** load the **300 mA** TPS7A2030 (ECR-0005). The ECR's own formula, 3.0 V / 9.3 Ω, gives 323 mA, not the 315 mA it states. §10 points 3 (no pin with two jobs) and 4 (rail load vs rating) are exactly these checks, written as prose. |
| **Not running** | **Nothing has a baseline.** There is no `baseline.json` and no git tags. `status` at 20:52 EDT gave **0 SUSPECT, 50 UNREVIEWED, 0 MISSING-DOC**: all 14 docs are now drafted, so nothing can turn red yet. |
| | **ECRs never close.** All **10 of 10 ECRs are `proposed`, and all 10 still carry the unfilled §10 cross-check** (`_(fill in)_`). |
| | **The real PCB source is outside git.** The KiCad board (`hw/pod/draft_r1/`, 3.4 MB) is untracked and not git-ignored. No watch touches any `.kicad_pcb`, and no watch hashes footprint geometry, which is where the mic-port error lives. |
| **Missing** | **No ICD layer.** Interfaces carry no value, tolerance or owning side, and one `review --by` clears them. |
| | **No requirement-to-verification matrix.** This is the right leg of the V-model: nothing shows how each requirement will be proven met. |
| | **No enforcement.** No hook or CI checks anything. |
| | **ECR impact is rolled up to whole items.** ECR-0004 lists 14 relations; the real impact is 2. |
| | **No board-vs-netlist parity check.** `kicad-cli --schematic-parity` needs a `.kicad_sch`, which the SKiDL flow doesn't produce. |
| | **Part identity is typed in 3 places, and they have drifted.** The board carries **wrong LCSC numbers on Q1/Q2 and SW1**, so a board-side BOM tool would order the wrong parts. |
| | **No as-built records.** O18's "fail informatively" needs them. |
| **Overkill (don't)** | **A model nothing generates.** A SysML v2 or Capella model would be a third copy of the architecture. |
| | **Server-based PLM.** Any PLM or inventory server means Docker plus PostgreSQL, always on, on a shared 30 GB laptop with an OOM history. |
| | **Ceremony.** Separate ECO/ECN documents, CCB meetings and formal FCA/PCA audits add nothing for one owner. |
| | **Watching all 28 pins of +3V0.** Every new decoupling cap would flag two relations. |
| | **`review ALL`.** It invites rubber-stamping. |

**Why this matters now:**
- **O20** (rev 1 aims to be the final device) makes the rev-1 JLC order a one-shot, big-bang integration of board, shell, arm and pad.
- **O19** (a personal device, buy once with spares) means cost roll-ups and supply monitoring matter little.
- Getting interfaces and part identity *right before that order* matters a lot. The ranking below follows from that.

**Options (owner decides):**

| Option | What | Verdict |
|---|---|---|
| A | Replace `plm.py` with a FOSS PLM suite (OdooPLM + StrictDoc + KiBot) | **No.** It needs an always-on Docker + PostgreSQL stack (OdooPLM's image is 2.5–4.4 GB), and its state lives outside git. No tool in it understands SKiDL nets or build123d constants, so it gives less coverage for more weight. |
| **B** | **Keep `plm.py`, fix it, and add FOSS tools only at the edges** (KiCad's own CLI, SKiDL's `erc_assert`, git hooks) | **Recommended.** Every gap is a small local change, and nothing needs a server. |
| C | Keep everything as it is | **No.** It stays decorative, and "status clean" would mean nothing was checked. |

---

## 2. Ranked improvements

Effort is agent hours. "Now" means before the rev-1 re-size (O20) and the joint layout session (O14). "Soon" means before the next parallel-team run and the sourcing lock. "Later" means before the order or the first build.

| # | Improvement | Prevents | Effort | Priority |
|---|---|---|---|---|
| 1 | Executable interface checks (contract tests) | the two sides of an interface disagreeing silently (port miss, rail overload, pin double-booking) | 6–8 h | **now** |
| 2 | Turn the tracker on, pointed at the real sources (board, footprints) | edits to the board or footprints flagging nothing | 5–7 h | **now** |
| 3 | Board↔netlist parity and part-identity check (`bom_check.py`) + strip wrong LCSC fields | ordering the wrong parts; the hand-edited board drifting from `gen.py` | 4–5 h | **now** |
| 4 | Enforce at commit time (versioned git hooks) + `tools/ci.sh` with a KiCad jobset | rules followed only when an agent remembers | 1–2 h + 3–4 h | **now** / soon |
| 5 | ECRs that close, with honest impact | alert fatigue (14 listed vs 2 real); changes that never close | 4–5 h | **now** |
| 6 | ICDs on boundary interfaces, signed by both sides | one-sided assumptions ("port = origin") | 1–2 days, incremental | soon |
| 7 | Generated N² chart and DSM → team scopes, bus items, budgets with margins | team boundaries cutting through tight coupling; budgets that nobody holds | 4–6 h | soon |
| 8 | Requirement → verification matrix (VCRM) | shipping a requirement that nothing verifies | 4 h | soon |
| 9 | One parts catalogue; lock and BOMs generated from it | identity drift across 3 hand-kept copies | 1–1.5 days | soon |
| 10 | Baseline tags, release manifests, as-built records per pod | bench results that can't be tied to an exact build | 3–4 h + 15 min per build | later |

All ten come to about 7–9 agent-days. Items 1–5 are about 3 days, need **no new installs**, and stay inside the memory fences.

### 1. Executable interface checks *(now, 6–8 h)*
- **What.** Turn each interface's agreement into code that fails.
  - **Electrical contracts:** SKiDL's `erc_assert(assertion, fail_msg, severity)` attaches checks to parts, nets or the circuit. It is already installed (SKiDL 2.3, MIT) and runs inside the `skidl.ERC()` call that `gen.py` already makes (line 286). Use it for:
    - the +3V0 load budget, from per-part current attributes against the TPS7A2030 rating with a stated margin;
    - "every MCU pin has exactly one job";
    - "every block has exactly one owner".
  - **MCU pin contract:** check each pin against ST's own pin data, `STM32U575CIUxQ.xml` from **STM32_open_pin_data** (ST's free pin and alternate-function database; BSD-3-Clause). It already confirmed ECR-0003's PA10 = pin 31, TIM1_CH3 and PB15 = pin 28, TIM1_CH3N. Generate `firmware/pins.h` from `gen.py`, so firmware compiles against the schematic.
  - **Geometry:** read the mic port hole, switch and wire-pad positions from the board with **pcbnew** (KiCad's Python API). Compare them with the shell features in **build123d** (our Python CAD kernel, Apache-2.0), using OCCT boolean overlap and clearance. Better still, derive the lid bore *from* the board position: one geometry source, which is the ECAD–MCAD co-design practice.
  - **Tolerances** come from a worst-case stack in `frame.py`'s shared datum frame (board fab + placement + resin print + lid fit), not from guesses.
- **Why.** These checks fail today on the 0.75 mm port offset and the 315–323 mA overload, which is the point. They also settle ECR-0003's "re-verify the pins" from ST's data.
- **Practice.** Consumer-driven contracts (Robinson, 12 Jun 2006): each consumer of an interface asserts exactly what it relies on, and the check runs on every change.

### 2. Turn the tracker on, pointed at the real sources *(now, 5–7 h)*
- **Commit the board:**
  - Add ignore rules first. `draft_r1/` holds three copies of the routed board, plus `.dsn`, `.ses`, `.prl` and renders.
  - Ignore KiCad 10's Local History folder `.history/`. It is a nested git repository and would be committed by accident.
  - Then commit the `.kicad_pcb` and `.kicad_pro`.
- **Watch the real sources:**
  - Add `pcb:` watch kinds: footprint id, side, x, y and rotation per reference, plus the outline and the rules (read with `pcbnew`).
  - Add `glob:` watches on the footprint files that carry interfaces: mic, Q1/Q2, SW1, J pads.
  - Re-point REG-BOARD and the `R-*-BOARD` relations to the board.
- **Narrow the noisy watches:**
  - WHOLE's grep for every D/O ID becomes per-ID anchors.
  - Whole-file `file:` watches on `.py` files become `sym:` watches.
  - The 28-pin +3V0 net becomes its budget parameters.
- **Fix ownership.** Give ARM_PADS (J1/J2/J7/J8) an owning item, give SELFTEST one owner instead of two, and watch `PLACE[J2]` and `PLACE[J8]`.
- **Add `plm.py lint`.** It reports as UNMODELLED any inter-block net without a relation, any board footprint without an owner, and any F-chain net that no longer exists.
- **Baseline.** Review **each** item and relation against its doc (not `review ALL`), commit `baseline.json`, and tag **BL-0**.
- **Why.** Today the owner's KiCad edits (O14) or a footprint redraw (ECR-0004's SOT1216) would flag nothing.

### 3. Board↔netlist parity and part identity: `tools/bom_check.py` *(now, 3–4 h + 1 h ECR)*
- **Read-only checks:**
  - board footprints against `pod.net`: refs, footprints, nets, LCSC numbers and DNP (do-not-place) flags;
  - BOM refs equal CPL (pick-and-place file) refs, minus DNP parts and pads;
  - every BOM line has a dated lock row, and no RECOMMENDED row names a part the schematic no longer uses (8 do today);
  - rating flags, starting with the C8/C9 conflict: the lock says the 2.2 µF caps need a 10 V rating, while `gen.py` chose the 6.3 V C12530. That needs a design answer against ST's datasheet;
  - JLC assembly tier derived from pitch, BGA and sides. The board needs **Standard** PCBA, not Economic: it is double-sided, U3 is a 0.40 mm DSBGA, and Q1/Q2 are 0.35 mm-pitch SOT1216 parts;
  - recomputed `bom.md` totals (bom.py says 23 caps against the real 22, and double-counts R20/R21).
- **ECR.** Strip the `LCSC Part` property that **easyeda2kicad** (a tool that fetches footprints by LCSC number; AGPL-3.0) embedded in 11 reused footprints. Then have `place_r1.py` write the netlist's LCSC into each footprint.
- **Why.** The routed board carries **C552750 (PMCXB900UELZ) on Q1/Q2 instead of C19654206 (PMCXB290UE)**, and **C221708 (KMT031, 3.4 N) on SW1 instead of C221707 (KMT022, 1.6 N)**. kicad-jlcpcb-tools, Fabrication-Toolkit and KiBot all read footprint fields matching `lcsc`, so any of them would order these wrong parts.

### 4. Enforce at commit time *(hook now, 1–2 h; `ci.sh` soon, 3–4 h)*
- **Versioned hooks.** Put them in `tools/githooks/` and set `git config core.hooksPath tools/githooks`, so every git worktree and every agent gets the same gate. The pre-commit hook:
  - regenerates `integration-map.md` and fails on a diff;
  - runs `plm.py status`, the interface checks and `bom_check` (seconds in total);
  - fails on a *new* SUSPECT or BROKEN unless the same commit reviews it or the message carries an `ECR: ECR-nnnn` trailer (git's own `Key: value` commit-message lines).
- **`tools/ci.sh`** runs under the 3G fence. It holds:
  - a committed **`.kicad_jobset`**: KiCad 10's native list of output jobs (DRC report, Gerbers, drill, pos, IPC-2581, renders);
  - the SKiDL ERC;
  - the geometry checks.
- **DRC memory trap.** Switch off DRC's two library-parity checks. They load every global footprint library (>2 GB RSS), and the 2 GB fence killed that run on 2026-09-30 (`hw/padboard/layout.py` line 125).
- **Why.** README rules 2 and 5 rest on agent discipline today, and 10 of 10 ECRs show what that produces.
- **Tools.** git (GPL-2.0) and kicad-cli (GPL-3.0-or-later), both installed. The **pre-commit** framework (a hook manager; MIT) is optional; if used, use only `repo: local` hooks, so nothing is cloned from GitHub.

### 5. ECRs that close, with honest impact *(now, 4–5 h)*
- **Impact by target.** Compute it from the touched refs, nets and symbols (`ecr new --touches ref:Q1,ref:Q2`), not from whole items. That cuts ECR-0004 from 14 relations to 2–3.
- **Cross-check as data.** Make §10 a required YAML block, validated with **jsonschema** (a JSON/YAML schema validator; MIT; installed) and pre-filled from a netlist diff.
- **States.** `proposed → approved/rejected → implemented (SHAs) → verified → closed`. Add `ecr close`, which refuses while its relations are still SUSPECT.
- **New fields:**
  - **effectivity:** which build the change applies to (`rev1-order`, `rev1-rework`, `rev2`, `test-build`, `final-build`);
  - **class:** *major* if it affects interchangeability or an interfacing item, otherwise *minor* (NASA SE Handbook §6.5);
  - **waiver:** a record of knowingly not meeting a requirement. Accepting ECR-0005's LDO overload for rev 1 would be one.
- **Tool fixes.** Remove `review ALL`, or make it owner-only with a note. Lock the JSON writes with `fcntl.flock`.

### 6. ICDs on the boundary interfaces, signed by both sides *(soon, 1–2 days, incremental)*
- **What.** Grow the ~12 board/body/arm/pad relations, plus power↔output, into `docs/system/icd/<ID>.yaml`. Each file holds:
  - the **interaction type**: spatial, energy, information or material (Pimmler & Eppinger 1994). The type says which check applies: tolerance stack, rail budget, pin/timing contract, or sealing and acoustics;
  - each parameter's **owning side, value and tolerance**;
  - the source watches and the checks;
  - a **maturity level**, L0 (seen in the N²) to L6 (verified on hardware);
  - **a/b sign-off stamps stored in the file**. This is Doorstop's model: stamps travel with the record and merge cleanly, unlike one central `baseline.json`.
- **When it counts as green.** Only when *both* sides have signed the current stamp *and* the checks pass.
- **Gates:**
  - for the rev-1 order, every ICD crossing board, body, arm or pad must be at L5 (its check passes);
  - for the final bonded build, the sealing, acoustic and arm ICDs must be at L6.
- **Why.** NASA SE Handbook §6.3: "For interfaces that require approval from all sides, unanimous approval is required." ECSS-E-ST-10-24C Rev.1 (the European space standard for interface management, 15 Nov 2024) separates a one-sided IDD (interface definition document) from the agreed ICD. Our subsystem "Interfaces" tables are IDDs; the ICD layer is what's missing.

### 7. Generated N² chart and DSM: team scopes, buses and budgets *(soon, 4–6 h)*
- **What it is.** An **N² chart** or **DSM** (design structure matrix) is a square who-depends-on-whom matrix.
- **What to generate:**
  - a block N² from the netlist (integration-map §3 already holds the data);
  - a directed item DSM from the ICDs, with **budget rows**: +3V0 mA, mass and balance (D18), volume, board area, power and runtime (§7).
- **What to run on it:**
  - **partitioning** (Steward 1981): coupled groups that must iterate together, and the order for the rest;
  - **clustering**: team scopes;
  - **bus detection**: items every cluster touches, which the lead owns;
  - **margins by maturity** on each budget: Technical Performance Measures (NASA §6.7). The LDO case is a margin-policy failure, not just a missing ICD.
- **Expected result.** By inspection today: about 3 clusters (power/output/test; the pin-map cluster; mechanics), with **REG-BOARD (9 relations) and REG-POD-BODY (8)** as buses.
- **Tools.** **NetworkX** (Python graph library; BSD-3-Clause; needs install approval) and **Graphviz** (graph renderer; EPL-2.0; installed).

### 8. Requirement → verification matrix (VCRM) *(soon, 4 h)*
- **What.** `docs/system/verification.yaml` generates the table. It has one row per T1–T6, D11, D12, D17, D18, §7 runtime and O12 entry, with these columns:
  - the requirement, quoted (§1 is never edited);
  - allocated items and F-rows;
  - method: Test, Analysis, Inspection or Demonstration;
  - artefact: `sim/checks`, E-items, ERC/DRC or audit;
  - status;
  - evidence: commit plus output path.
- **Coverage report.** Add `# verifies: D11` tags in `sim/checks/*.py`. `plm.py trace` then lists uncovered IDs and tags that point at missing ones. This borrows from LOBSTER and OpenFastTrace; nothing to install.
- **Gate.** No baseline while an Analysis row is red.
- **Why.** Under O20, anything unverified when the order goes out is effectively shipped.

### 9. One parts catalogue; everything else generated *(soon, 1–1.5 days)*
- **The catalogue.** `hw/parts.yaml` is read by both `gen.py` files. Each part entry holds:
  - MPN, manufacturer, LCSC number, package and footprint;
  - ratings and MSL (moisture-sensitivity level) and rework notes;
  - `design_critical`;
  - alternates with status, evidence and approver;
  - for off-board parts, a source URL with the quote date.
- **Generated from it:**
  - the sourcing lock, in the vendored skill's `sourcing-lock-v1` schema. The current lock is `BLOCKED`: it is missing 30 columns;
  - DNP, from SKiDL's native `dnp` and `exclude_from_bom` attributes (it is defined twice today);
  - a **buy-once-with-spares list** (O19), including bench spares and hand-fit parts.
- **Snapshots.** `tools/jlc.py` appends dated JSONL snapshots that keep `lossNumber` (JLC's attrition), `preferredComponentFlag` and `minPurchaseNum`.
- **Cost roll-up: later, and on the right tier.**
  - JLC's pricing page (updated 9 Sep 2026) lists Standard double-side setup at $51.12 and the double-side stencil at $16.42, with a minimum panel of 70 × 70 mm with rails and fiducials.
  - The "$9.50 + $30" Economic figure in the BOM note doesn't apply.
- **Why.** 16 of 29 JLC lines have no lock row. `gen.py` labels them "dated lookup", so the gap is known, not silent. Hand copies drift within a day.

### 10. Baselines, manifests, as-built records *(later, 3–4 h + 15 min per build)*
- **Tags.** `BL-0` → `BL-alloc` (schematic + ICDs ≥ L3) → `BL-product-rev1` (the exact JLC release; the `release-pcba-fabrication` skill builds its manifest) → `BL-asbuilt-<pod serial>`.
- **Each manifest records:**
  - file hashes;
  - plm stamps;
  - **toolchain versions** (KiCad, SKiDL, build123d/OCP);
  - a **canonicalised** netlist hash. `pod.net` carries a timestamp line, so a raw hash changes on every regeneration.
- **Per-pod as-built record.** One per pod:
  - serial;
  - board SHA;
  - firmware `git describe --dirty`, readable over USB;
  - housing print;
  - cell;
  - rework log, with the owner's rework notes.
- **Why.** O18 says rev 1 must "fail informatively", which only works if every bench result points at an exact configuration (CM "status accounting", NASA §6.5).

---

## 3. Every tool evaluated

**How licences were checked.** Each licence was read from the repository's licence file on 2026-10-01 by the researcher and re-read by a fact-checker. Exceptions are marked. File URLs, release dates and footprints are in the three notes (`method.md` §8, `plm-tools.md` §4, `bom.md` §5).

**Fact-check corrections applied here:**
- OdooPLM is an open-core suite: LGPL core plus AGPL modules.
- KiCad's licence was verified as GPL-3.0-or-later.
- The SysML v2 pilot has no GPL file.
- Syside's successor is proprietary.
- Graphviz upstream is 16.1.0.
- KiBot's Python 3.14 support is unverified.

**Licence failures among the adopt or adapt tools: none.** Docker is present (`/snap/bin/docker`), so the case against the server tools rests on RAM and on running always-on services, not on whether Docker is available.

**Already ours or installed: adopt**

| Tool | Licence | Verdict | Reason |
|---|---|---|---|
| `tools/plm.py` (our tracker, ~425 lines) | project code | **adopt: keep + fix** | Finer watches than any FOSS tool; needs items 2, 4, 5 |
| git (version control) | GPL-2.0 (Debian copyright file) | **adopt** | Tags for baselines, `core.hooksPath` hooks, trailers, one worktree per team |
| KiCad 10 `kicad-cli` + `pcbnew` | GPL-3.0-or-later (`LICENSE.README`) | **adopt** | Jobsets; `pcb export pos`/`stats`/`ipc2581`/`step`; pcbnew reads pads and holes for watches and checks |
| KiCad 10 variants, BOM presets, DB/HTTP libraries | GPL-3.0-or-later | adapt ideas | Need a `.kicad_sch`; copy the semantics (DNP, exclude-from-BOM and exclude-from-pos as independent flags) |
| SKiDL 2.3 (schematic as Python) | MIT | **adopt** | `erc_assert` for contracts; native `dnp`/`exclude_from_bom`. Not its XML BOM (it writes malformed fields). `gen_schematic()` could derive a `.kicad_sch` later (watch) |
| build123d (Python CAD on OCCT) | Apache-2.0 | **adopt** | Board↔shell clash and alignment checks; mass/CoM JSON as a diffable artefact |
| jsonschema (schema validator) | MIT (installed 4.19.2) | **adopt** | Validates ECR cross-checks, ICDs and team proposals |
| Graphviz (graph renderer) | EPL-2.0 upstream / EPL-1.0 Debian package | **adopt** | Already used by `plm.py graph`; renders the N²/DSM |
| STM32_open_pin_data (ST pin/AF database) | BSD-3-Clause | **adopt** (vendor 1 XML) | Executable MCU pin contract from ST's own data |
| easyeda2kicad (footprints by LCSC number) | AGPL-3.0 | **adopt (keep), fix** | Strip the `LCSC Part` it embeds (wrong parts on Q1/Q2/SW1). Its data comes from an undocumented EasyEDA API (§4) |
| NetworkX (graph algorithms) | BSD-3-Clause | **adopt after install OK** | DSM partitioning (strongly connected components), clustering, ordering |
| pre-commit (git-hook manager) | MIT | adapt ideas | Plain versioned hooks need no install; if used, `repo: local` only |

**Requirements and traceability**

| Tool | Licence | Verdict | Reason |
|---|---|---|---|
| Doorstop (requirements as YAML in git) | LGPL-3.0 (PyPI also shows a stray "Other/Proprietary" classifier; the file governs) | adapt ideas | Per-link fingerprint stored in the record = our ICD sign-off stamps; the tool would duplicate plm.py |
| StrictDoc (requirements/docs as text) | Apache-2.0 | watch | Strong traceability and export, but 32 dependencies incl. a web server; would duplicate the locked spec |
| OpenFastTrace (tag-based tracing) | GPL-3.0 | adapt ideas | Revision numbers that void links = "semantic vs cosmetic" changes; adds a JVM |
| LOBSTER (BMW trace-coverage report) | AGPL-3.0 | adapt ideas | `# verifies:` tags → coverage report; ~50 lines in plm.py instead |
| TRLC (BMW typed requirement records) | GPL-3.0 | watch | Typed, checkable records fit ICD parameters; pulls an SMT solver (cvc5) |
| Pact / pact-python (consumer-driven contracts) | MIT | adapt ideas | The contract-test pattern; the tool is for software messages |
| sphinx-needs | MIT | skip | Needs the docs turned into a Sphinx project |
| mlx.traceability | GPL-3.0 (PyPI metadata only) | skip | Sphinx-bound |
| open-needs | MIT | skip | Dormant |
| reqif (ReqIF library) | Apache-2.0 | skip | DOORS-style interchange; not our need |
| Eclipse RMF / ProR | EPL-1.0 | skip | Last release 2016 |

**Architecture modelling (MBSE: model-based systems engineering)**

| Tool | Licence | Verdict | Reason |
|---|---|---|---|
| SysML v2 Pilot Implementation (OMG reference) | EPL-2.0 (no GPL file despite the README) | watch | Git-diffable text models; a third, ungenerated copy of the architecture today |
| RaGraph (DSM analysis library) | GPL-3.0-or-later | watch | Bus detection and DSM sequencing beyond NetworkX; one optional run |
| Eclipse Capella (Arcadia method workbench) | EPL-2.0 | adapt ideas | Take functional chains and allocation (F1–F15 already are); skip the GUI tool |
| capellambse (headless Capella API) | Apache-2.0 AND OFL-1.1 | skip | Moot without Capella |
| Eclipse SysON (web SysML v2) | EPL-2.0 | skip | Spring server + PostgreSQL 15 via Docker Compose, always on |
| Eclipse Papyrus | EPL-2.0 | skip | Hand-drawn duplicate; nothing since 2025-06 |
| Gaphor | Apache-2.0 | skip | Hand-drawn duplicate |
| OpenMBEE | Apache-2.0 | skip | Large-team servers; main authoring path targets proprietary Cameo |
| sysml-2ls (SysIDE legacy) | EPL-2.0 OR GPL-2.0 w/ Classpath | skip | Archived 2025-10 |
| Syside (successor) | LicenseRef-Proprietary (PyPI) | **excluded-not-foss** | Proprietary |

**PLM, PDM (product data management) and inventory servers**

| Tool | Licence | Verdict | Reason |
|---|---|---|---|
| OdooPLM (PLM modules on Odoo Community) | LGPL-3.0+ core, AGPL-3.0+ modules; proprietary CAD client; one module needs Odoo Enterprise | adapt ideas only, never install | Self-declared open core; where-used queries are the idea; DB-centric, 2.5–4.4 GB image |
| InvenTree (parts/stock/BOM server) | MIT | adapt ideas | BOM "validated" checksum = our STALE; always-on server, state outside git |
| Odoo `mrp_plm` (ECO/PLM) | Enterprise only | **excluded-not-foss** | Not in the LGPL repository |
| Aras Innovator | proprietary (licence key) | **excluded-not-foss** | Also needs Windows + SQL Server |
| Valispace | proprietary SaaS | **excluded-not-foss** | SaaS |
| Binner | GPL-3.0 core + paid tier | skip | Open-core; no LCSC/JLC source |
| Part-DB | AGPL-3.0-or-later | skip | Inventory server; its docs warn the LCSC API "could break at any time" |
| PartKeepr | GPL-3.0 | skip | Needs PHP 7.0–7.1; last release 2018 |
| ERPNext | GPL-3.0 | skip | An ERP; heavy server |
| OpenPLM | GPL-3.0-or-later | skip | Dead since 2014 |
| DocDokuPLM | AGPL-3.0 (GitHub detection) | skip | Dormant since 2021 |
| Ki-nTree | GPL-3.0 | skip | Requires a Digi-Key production API key |
| inventree-part-import | MIT | skip | Only with an InvenTree server |
| Tuleap, OCA Odoo modules | not verified | skip | Licence not verified; heavy servers or no PLM content |

**KiCad automation, diffs and fabrication outputs**

| Tool | Licence | Verdict | Reason |
|---|---|---|---|
| KiBot (KiCad output runner) | AGPL-3.0 (file; PyPI says GPLv3+) | watch | Supports KiCad 10 (1.9.1, 2026-07-28); its JLC BOM needs a `.kicad_sch`; never its `kicost` output (keyed APIs); install approval when layout diffs are wanted |
| KiDiff (visual PCB/SCH diff) | GPL-2.0 | watch | Board diff between release tag and HEAD; comes with KiBot |
| KiRI (revision inspector) | MIT | watch | Visual diffs; KiCad 10 unverified; not on PyPI |
| KiKit (fab + panelisation) | MIT | watch / adapt ideas | `panelize` works from the board alone and is likely needed for the ≥ 70 × 70 mm Standard-PCBA panel; copy its `--missingError` and field-fallback ideas |
| Fabrication-Toolkit (board-only JLC BOM/CPL/Gerbers) | Apache-2.0 | watch | Independent cross-check for `bom_check`, once footprint LCSC fields are correct; JLC's KiCad 10 guide recommends it |
| kicad-jlcpcb-tools (JLC plugin) | MIT | adapt ideas | Rotation corrections, variant flags; GUI only; its parts DB comes from JLC's undocumented endpoint |
| JLCKicadTools | GPL-3.0 | adapt ideas | Origin of the JLC rotation-correction table |
| InteractiveHtmlBom | MIT | watch | Clickable board + BOM page for hand assembly and rework |
| kicad-python (IPC API) | MIT | watch | Needs a running KiCad; headless pcbnew is enough |
| KiCost | MIT | skip | Every data source is a keyed proprietary API (Nexar, Digi-Key, …) |
| KiBoM | MIT | skip | Superseded; needs SKiDL's broken XML BOM |
| JLC2KiCad_lib | MIT | skip | Duplicates easyeda2kicad |
| git-lfs | MIT | watch | `.git` is 17 MB; locks need an LFS server |
| DVC | Apache-2.0 | skip | Sim outputs are regenerable |
| act (local GitHub Actions) | MIT | skip | CI stays a local script; needs Docker |
| Forgejo (self-hosted forge) | GPL-3.0 | watch | FOSS alternative to GitHub, at the cost of an always-on server (owner question) |
| pytest-regressions | MIT (PyPI metadata; file not read) | watch | Tolerant numeric fixtures for CAD regression; needs pytest installed |
| daff / csvkit (table-aware CSV diff) | MIT / MIT | watch | Cell-level BOM/lock diffs in git; install approval |
| Yamale / check-jsonschema | MIT / Apache-2.0 (per fact-checker) | skip | jsonschema, already installed, does the job |
| CycloneDX HBOM (BOM standard) | Apache-2.0 (spec) | watch | Ready export target; overkill for two boards |

**Data services (not software)**

| Service | Licence | Verdict | Reason |
|---|---|---|---|
| JLCPCB website parts endpoint (`tools/jlc.py`) | none; undocumented, proprietary | **owner question** (§4) | The data the whole FOSS JLC ecosystem leans on |
| JLCPCB Components API (`open.jlcpcb.com`) | proprietary, keyed, free on application | excluded as a tool; option in §4 | Documented and stable; terms unverified |
| jlcparts (catalogue dump) | MIT code; data licence unstated | watch; option in §4 | Daily refreshed SQLite (~116 MB compressed) built with the maintainer's keys |
| EasyEDA library API (via easyeda2kicad) | undocumented, proprietary | owner question (§4) | Same class as the JLC endpoint |
| Octopart/Nexar; Digi-Key, Mouser, Element14, TME APIs | proprietary, keyed | **excluded-not-foss** | Owner rule |

---

## 4. Owner question: the JLC public parts endpoint (data, not software)

**What it is.** `tools/jlc.py` POSTs to JLCPCB's website search endpoint (`…/smtGood/selectSmtComponentList`). The endpoint is undocumented, needs no key, and serves JLC's proprietary catalogue. It is not a FOSS tool and it isn't software we run: it's a **data source**. The FOSS-only rule doesn't settle it either way, so it's flagged here rather than silently kept or dropped.

**The blunt fact.** **No FOSS-licensed source of JLC stock and price exists.** The data belongs to JLC. jlcparts and kicad-jlcpcb-tools are MIT *code* over the *same* data:
- jlcparts uses the maintainer's keys for JLC's official API, plus the same website endpoint.
- kicad-jlcpcb-tools rebuilds its parts database through JLC's website endpoint, run on GitHub Actions (SaaS).

The **EasyEDA** library API behind easyeda2kicad is in the same class. So is the order itself, placed on jlcpcb.com. JLC is our fab, and its data is authoritative for what it will place.

**Risks:**

| Risk | Evidence | Mitigation |
|---|---|---|
| Breaks without notice | jlcparts has already moved to a `/v2` path that needs an XSRF cookie. Our v1 path still answered at 2026-10-02T00:32Z | Keep `jlc.py`'s shape guard; add a smoke test on two known parts |
| Stale data used silently | Dates survive only in prose; `jlc.py` keeps nothing | Append-only `.pcba-workflow/stock/YYYY-MM-DD.jsonl` snapshots. A lock older than its maximum age turns BLOCKED |
| Terms of use | Not checked (*unverified*) | Low volume, manual cadence: a handful of queries per decision |
| Stock risk itself | STM32U575 MCU: 8 in stock at JLC on 2026-10-02T00:25Z | ECR-0008 (reserve/consign). Under O19 this is a one-time buy, not something to monitor |

**Options:**
- **(a) Keep the endpoint, hardened as above.** Zero setup.
- **(b) Apply for JLC's documented, keyed Components API.** It's free on application, but it binds you to JLC's developer terms.
- **(c) Manual lookups on jlcpcb.com,** recorded with a date. Optionally use the jlcparts dump as an offline fallback, but it is third-party with an unstated data licence.

**Recommendation:** **(a), with (c) as the fallback** when it breaks. O19 means stock matters at only a few moments: the sourcing lock before the rev-1 order, and the spares buy. Monitoring adds nothing. Take (b) only if you're happy to hold a JLC developer account.

---

## 5. How AI design teams should work here

This is consistent with `docs/system/README.md`: read before a change, update in the same commit, the cross-check with every proposal, check-out before editing, and the spec wins. It makes those rules executable. The sources agree on the shape:
- Anthropic, 13 Jun 2025: give each subagent an objective, an output format and boundaries; have them write outputs to files.
- Cognition, 12 Jun 2025: implicit decisions conflict, so share context.
- MAST (Cemri et al. 2025): failures cluster in system design, inter-agent misalignment and verification.
- MetaGPT: structured artefacts reduce cascading errors.
- Colfer & Baldwin 2016 ("partial mirroring"): teams read widely but write narrowly.

1. **Ownership.**
   - **Owner:** the change authority for the spec and O-items. She approves ECRs and signs ICDs that touch her decisions, places every order, and builds and reworks by hand.
   - **Lead AI:** system architect and integrator. It owns the **bus items**: REG-BOARD, REG-POD-BODY, the MCU pin map, the rail, mass and volume budgets, and `frame.py`. Teams *propose* changes there and never edit them. The lead signs the side of an ICD that has no live team.
   - **Teams:** each owns the items in its DSM cluster (about 3 teams), **writes only those, reads everything**.
2. **Contracts before parallelism.**
   - Before spawning, regenerate the N²/DSM and pick scopes from the clusters, not from domain names.
   - **Freeze and tag the boundary ICDs.** Until ICDs exist, freeze the relation list plus the current values.
   - Hand each team its write scope, the frozen contracts and a return schema.
3. **Isolation.**
   - One git worktree per team.
   - Check-outs move to `$(git rev-parse --git-common-dir)/plm/`, with `fcntl.flock` and a 12 h expiry, so every worktree sees them.
   - A KiCad `*.lck` next to a watched board counts as "the owner has REG-BOARD open".
   - CLAUDE.md memory rules apply: fence every simulation at 3G, and never run FreeRouting or `place.py` in parallel.
4. **Return files, not chat.** Each team returns a patch plus `proposals/<team>.yaml`, containing:
   - the 8 §10 fields;
   - ICD parameter deltas, with reasons;
   - every implicit decision, made explicit;
   - the checks it ran.
5. **Conflict detection across *all* concurrent proposals,** before anything merges:
   - the same ICD parameter changed twice;
   - an MCU pin claimed twice;
   - rail or mass deltas summing over budget;
   - the same bus item or file region touched.

   §10 point 3 asks for this today, but no tool does it.
6. **Integration checkpoint, serial.** The lead applies one proposal at a time through the gate: plm status, interface checks, `bom_check`, ERC (plus DRC), and the VCRM analyses.
   - A failure goes back to that team.
   - An ICD change needs both sides' sign-off, and the owner's if an O-item is touched.
   - Green means a commit, and the ECR moves to `implemented`.
7. **Verify at baselines.** Run the existing adversarial-methodology-audit workflow against each baseline tag, not ad hoc.

These are proposals. `docs/system/README.md` is unchanged until you decide.

---

## 6. Owner decisions needed

1. **Method option:** B (keep and fix `plm.py`, FOSS at the edges) is recommended over A (a FOSS PLM server) and C (as-is).
2. **JLC endpoint and EasyEDA API** (§4): recommend (a) with (c) as the fallback.
3. **Installs:**
   - **Now:** NetworkX (BSD-3-Clause), and vendoring one ST pin-data XML (BSD-3-Clause).
   - **Later:** KiBot (AGPL-3.0) and KiDiff (GPL-2.0) when layout diffs are wanted; KiKit (MIT) for the panel.
4. **GitHub (SaaS) as the remote:** recommend keeping it as a plain remote, with all CI local. The alternative is a self-hosted Forgejo (GPL-3.0), always on.
5. **The unstaffed side of an ICD:** recommend the lead signs it, and you sign anything touching an O-item.

---

## 7. Sources (all accessed 2026-10-01 unless a UTC time is given)

**Standards and handbooks:**
- NASA Systems Engineering Handbook SP-2016-6105 Rev 2:
  - §6.3 Interface Management: https://www.nasa.gov/reference/6-3-interface-management/
  - §6.5 Configuration Management: https://www.nasa.gov/reference/6-5-configuration-management/
  - §6.2 Requirements Management: https://www.nasa.gov/reference/6-2-requirements-management/
  - Appendix D, Requirements Verification Matrix: https://www.nasa.gov/reference/appendix-d-requirements-verification-matrix/
  - §6.7 Technical Assessment: https://www.nasa.gov/reference/6-7-technical-assessment/
  - §5.2 Product Integration: https://www.nasa.gov/reference/5-2-product-integration/
- ECSS-E-ST-10-24C Rev.1 Interface management, 15 Nov 2024 (catalogue page only; the PDF was not read): https://ecss.nl/standard/ecss-e-st-10-24c-rev-1-interface-management-15-november-2024/
- SEBoK, Configuration Management: https://sebokwiki.org/wiki/Configuration_Management
- SEBoK, System Integration: https://sebokwiki.org/wiki/System_Integration
- Not read: SAE EIA-649C, ISO 10007 and ASME Y14.5 (paywalled). Two ideas come from them and are *unverified* against their text: "effectivity", and tolerance stacks in a shared datum frame.

**Papers** (DOIs confirmed via Crossref):
- Steward 1981, IEEE TEM 28(3), doi:10.1109/TEM.1981.6448589
- Browning 2001, IEEE TEM 48(3), doi:10.1109/17.946528
- Sosa, Eppinger & Rowles 2004, Management Science, doi:10.1287/mnsc.1040.0289
- Pimmler & Eppinger 1994, ASME DTM, doi:10.1115/detc1994-0034
- Colfer & Baldwin 2016, ICC, doi:10.1093/icc/dtw027
- Sauser et al. 2010, doi:10.3233/IKS-2010-0133 (metadata only; level wording unverified)
- Forsberg & Mooz 1991, doi:10.1002/j.2334-5837.1991.tb01484.x (metadata only)
- Conway 1968: https://www.melconway.com/Home/Committees_Paper.html
- DSM introduction: https://dsmweb.org/introduction-to-dsm/

**Contracts and multi-agent practice:**
- Robinson, Consumer-Driven Contracts, 12 Jun 2006: https://martinfowler.com/articles/consumerDrivenContracts.html
- Pact docs: https://docs.pact.io/
- Anthropic, multi-agent research system, 13 Jun 2025: https://www.anthropic.com/engineering/multi-agent-research-system
- Cognition, Don't build multi-agents, 12 Jun 2025: https://cognition.com/blog/dont-build-multi-agents
- Cemri et al., MAST: arXiv:2503.13657
- Hong et al., MetaGPT: arXiv:2308.00352

**KiCad and JLC:**
- KiCad 10 manual (jobsets, Local History `.history`): https://docs.kicad.org/10.0/en/kicad/kicad.html
- KiCad 10 schematic editor manual (variants): https://docs.kicad.org/10.0/en/eeschema/eeschema.html
- KiCad licence: https://gitlab.com/kicad/code/kicad/-/raw/master/LICENSE.README
- JLC PCBA capabilities: https://jlcpcb.com/capabilities/pcb-assembly-capabilities
- JLC PCBA price, last updated 9 Sep 2026: https://jlcpcb.com/help/article/pcb-assembly-price
- JLC PCBA FAQ: https://jlcpcb.com/help/article/pcb-assembly-faqs
- JLC KiCad 10 BOM/CPL guide: https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad
- JLC API: https://api.jlcpcb.com/
- Part-DB info providers: https://docs.part-db.de/usage/information_provider_system.html
- InvenTree BOM docs: https://docs.inventree.org/en/latest/manufacturing/bom/

**Tool licence files and release pages:** listed per tool in `methodology/method.md` §8 and §10, `methodology/plm-tools.md` §8 and `methodology/bom.md` §11.

**Local probes, 2026-10-01:**
- `plm.py status` at 20:52 EDT (fenced, 3G);
- `git tag` (empty);
- `docs/system/plm/ecr/*.md` (10 files, all `proposed`, all `_(fill in)_`);
- `hw/pod/gen.py` line 286;
- `hw/padboard/layout.py` lines 125–127;
- `which docker podman`;
- `pip show jsonschema`;
- `/usr/share/doc/git/copyright`.
