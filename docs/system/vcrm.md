# Requirement to verification matrix (VCRM)
Status: second version after an adversarial test, 2026-10-02 · Source of truth: [`vcrm.yaml`](vcrm.yaml) (hand-kept), checked by `python3 tools/checks/vcrm.py` · Requirements: [`docs/spec.md`](../spec.md), which always wins · Owner decisions: O18 (stage C before hardware), O19, O20

## What it is, and why
One row per verifiable requirement: how it will be proven, what exists today that proves part of it, and what is still missing. The tracker (`tools/plm.py`) tells you when something changed. The interface checks (`tools/checks/interfaces.py`, `bom_check.py`) tell you when two sides disagree. This matrix tells you **whether each requirement has any proof at all**, and the checker reads the live result of the interface checks the rows cite, so a row cannot say "passes" while its check fails. Under O20 (rev 1 is meant to be the final device), a requirement nothing verifies when the board order goes out is shipped unverified.

It covers all of spec section 1 (the goal, constraints 1-4, tests T1-T6, quoted verbatim) and **every decision (D1-D18) and owner item (O1-O20) of the spec**: each has a row, is carried by another row (`covers`), or has a recorded waiver with its reason (`not_verifiable`, listed at the end of this file). Where one item holds several separate claims it gets several rows (`O12-dock`, `O12-sealing`, `O12-fastcharge`), and each lettered or numbered sub-item (O12 a-c, O16 1-7) must be cited by some row.

## How to read a row
| Field | Meaning |
|---|---|
| `text` | Section 1: the spec text, word for word; the checker compares it with the spec and the spec with git. Others: a short summary, plus `spec_block` (always the row's own item) and a hash of that spec block |
| `method` | Test, Analysis, Inspection or Demonstration |
| `stage` | **C** = in a computer before hardware (simulation, analysis, firmware on a host, inspection of CAD or schematic, the owner listening on headphones). **D** = on rev 1: bench, wear, field. A row with no C says why in `c_none_reason` |
| `c_role` | `decides`: a computer-side check can settle it. `surrogate`: stage C only bounds the enabling conditions; the requirement itself (what she hears, how it feels, whether it stays dry, what it draws) is judged on rev 1. **Surrogate rows are the ones rev 1 must reveal (O18)** |
| `status` | `not-started`: nothing exists that could show pass or fail. `partial`: something real exists but does not cover the whole requirement, is blocked or stale, or is not yet on hardware. `done`: complete and passing, with evidence, no open ECR, no known failure, and no cited check that is not PASS. Per stage in `status_by_stage`; the whole row is `done` only if every stage is |
| `artefacts` | What verifies it and exists today: files (never a directory or a wide pattern; never CLAUDE.md, the spec or this matrix), E-items (spec 12.E), S-stages (spec 10), C-tasks (spec 12.C), `interfaces:<id>` and `bom_check:<id>` (ids the script's docstring lists), `ERC`, `DRC`. An E/S/C item is a defined procedure, not a result; `status` says whether it was done |
| `planned` | What is missing and would verify it (free text) |
| `evidence` | What backs the stated status: an exact file or a commit. Each file is pinned by hash in `evidence_pins`; a changed file is a WARN until someone re-reads the rows that cite it |
| `ecrs`, `related`, `covers` | Open ECRs that block the row; rows that share evidence; other spec items the row also verifies (`O7`, `O16(3)`) |
| `known_fail`, `known_fail_ref` | Set only when the design today is known not to meet the requirement. Shows as WARN, with the ECR or doc that tracks it (`none; <doc>` when no ECR does) |
| `gap`, `next` | What is missing, in plain words with the numbers; the one next action. Never write what a check currently reports: the checker runs it |

## What the checker enforces
`python3 tools/checks/vcrm.py` (about 2 s, 450 MB: it runs `interfaces.py` and `bom_check.py` in parallel, from the harness venv it finds itself; exit 1 on any FAIL; a FAIL prints its details, `-v` prints all details, `--json` for machines, `--no-live` skips the two scripts, `--root DIR` checks a scratch copy). A crash in any check is a FAIL with a reason, never a traceback.

- **schema**: the file's shape; known keys only (a misspelt key is a FAIL, not a silent loss); types; required fields; id, kind and `spec_block` agree; statuses consistent; `done` means no open ECR and no known failure; open rows say what is missing and next; a row with no stage C says why; a key written twice in one mapping, or zero rows, is a FAIL.
- **coverage**: derived from the spec, not from a list: section 1 and every D/O item need a row, a `covers` entry or a `not_verifiable` waiver; sub-items need a citing row; no row for something the spec does not have.
- **lock**: spec section 1 is byte-identical to its text at the commit in `section1_lock`. Editing section 1 and the matrix together no longer passes: git is the baseline.
- **verbatim**: each section-1 row's `text` equals the spec text.
- **artefacts**, **evidence**, **tracked**: references resolve to real, tracked, specific files, items and check ids; evidence files are pinned and WARN when they change; cited files git does not track are a WARN (a commit without them points at nothing).
- **live**: the current status of every cited check. A FAIL there fails the matrix; a WARN is listed with the rows that rest on it and the ECR the check names; a `done` row may not rest on a non-PASS check.
- **owners**: `owner_items` are plm items (`docs/system/plm/items.yaml`); `functions` are F-rows of the integration map.
- **ecrs**: cited ECRs exist and have a Status line. Open means `proposed` or `approved` (as `tools/plm.py` counts); `implemented` waits for the owner; any other status is closed (stale citation). Every open ECR must be cited by a row, or listed in `ecrs_no_row` with a reason.
- **spec-drift**: a decision/owner row stores the hash of the spec block it summarised; if the block changes, the row is WARN until someone re-reads it.
- **known-fail**, **summary**, **md**: the rows the design cannot meet today and what tracks each; the coverage numbers (`-v`) and the rows that fell out of `stage_c_baseline`; the generated tables below are current.
- **`--strict`** turns every WARN into a FAIL unless its key is in `acknowledged` (the owner accepting that exact WARN; keys are in `--json`). Today it fails, as a release gate should.

## How to update it
1. **Evidence arrived** (a check, a simulation, a measurement, a commit): in `vcrm.yaml` set the row's stage status, add the file or commit to `evidence`, rewrite `gap` and `next`. Do not write `done` without a file or commit that shows it. New evidence file: `python3 tools/checks/vcrm.py --update-pins`. A pin WARN means the file changed: re-read the rows that cite it, then `--update-pins --refresh-pin <path>` (or `all`).
2. **A spec block changed** (`spec-drift` WARN): re-read the block, update the row's summary and gap if needed, then refresh its hash: `python3 tools/checks/vcrm.py --hashes` prints the current value.
3. **A new requirement or aspect**: add a row (id `D17-<aspect>`, `O12-<aspect>`). A spec item with no row needs a `not_verifiable` reason. Section-1 rows are never added or edited by hand.
4. **The owner changes section 1** (the only way): commit the spec change with `section1_unlock: "<owner, date, why>"` in `vcrm.yaml`, copy the new text into the mvp rows, then record the new lock (`python3 tools/checks/vcrm.py --lock` prints the `commit` and `sha256`) and delete the unlock.
5. **A new check script lands**: list it in the script's docstring `Checks` block and cite `interfaces:<id>` or `bom_check:<id>` from the rows it verifies. The summary lists analysis scripts no row cites.
6. **A requirement's stage-C leg is reclassified on purpose**: update `stage_c_baseline` (`--baseline` prints the list).
7. **Always last**: `python3 tools/checks/vcrm.py --update-md` rewrites the generated block below (it refuses while the schema fails), then run the checker.

The matrix never overrides the spec. If a row shows the design cannot meet a requirement (section 1 included), it says so in `known_fail` and in the report to the owner; the spec text stays untouched.

## Today's reading (2026-10-02)
- **Nothing is verified end to end, and that is correct for a design with no board.** Every stage-D leg is `not-started` because rev 1 does not exist. What exists is stage C, mostly partial.
- **Most requirements can only be settled on rev 1.** In 34 of 49 rows stage C is a surrogate. The perception tests (T1-T3, T5, T6), self-noise (S1.2-C3, D11), sealing, current and comfort all end on hardware. The mitigation O18 already names is the point: make each one diagnosable and firmware-fixable (`O18-diagnosability`, `O18-firmware-fixable`).
- **Six requirements are known not to be met today** (WARN `known-fail`, none tracked by an ECR): the 20-96 kHz top end in the locked goal (about 85 kHz delivered; the spec text stays), mass against the 8 g target, the unsealed mic port against IPX4/5, the contact pad area against O16(4), the unreadable rails and unrouted spare pins against O18, and the board and shell size against O20. Whether to open ECRs for them is the owner's call.
- **The live interface checks are mostly WARN, each with a named issue** (ECR-0001 constants, ECR-0005 LDO rating, ECR-0011 mic port, ECR-0012 footprint identity, ECR-0013 pin hazards, and a few with no ECR yet). The matrix lists which rows rest on them.
- **Stage C holes** (`O18-stageC-classes`): pinouts, footprints, rail capacity and part of mechanics have scripts; noise coupling, thermal, ESD and assembly yield have none committed. T3 and D10 have a stage-C leg defined but not started; D7 (the exciter) has no stage C at all. Other agents are building `sim/e2e` (end-to-end chain: T1, T2, T3, T6, D17) and `sim/noise` (layout noise); cite them here when they land.
- **Twelve open ECRs hold 26 rows** and ECR-0011 awaits review; ECR-0006 (weighted dummy pair, wear test) and ECR-0001 (frame.py constants) hold the most.
- **Nine spec items have no row, by recorded waiver** (D4, D5, D8, D15, O3, O4, O5, O14, O15: choices, owner actions and superseded items), and the table at the end lists why.

<!-- vcrm:begin (generated by tools/checks/vcrm.py --update-md from docs/system/vcrm.yaml, updated 2026-10-02; do not edit by hand) -->

### Summary

| Stage | Rows | done | partial | not-started |
|---|---|---|---|---|
| C: in a computer, before hardware | 48 | 1 | 45 | 2 |
| D: on rev 1: bench, wear, field | 46 | 0 | 0 | 46 |
| whole row | 49 | 0 | 46 | 3 |

**No stage-C verification defined (rev 1 must reveal these, O18):** `D7-transducer`

**Stage C is a surrogate only; the requirement itself is judged on rev 1 (34):** `S1.1-goal`, `S1.2-C1`, `S1.2-C2`, `S1.2-C3`, `S1.2-C4`, `S1.3-T1`, `S1.3-T2`, `S1.3-T3`, `S1.3-T4`, `S1.3-T5`, `S1.3-T6`, `D1-force`, `D2-nolink`, `D6-output`, `D11-selfnoise`, `D12-off`, `D13-mic`, `D16-crystal`, `D17-popfree`, `D18-runtime`, `D18-balance`, `O8-led`, `O10-twostage`, `O12-dock`, `O12-sealing`, `O12-fastcharge`, `O16-cell`, `O16-connector`, `O16-ip68switch`, `O17-wiring`, `O18-firmware-fixable`, `O19-reliability`, `O19-serviceability`, `O20-finalsize`

**Stage C can decide (14):** `D3`, `D9`, `D10`, `D11-topology`, `D12-modes`, `D14-clocks`, `D17-ceiling`, `O9-prototype`, `O13-budget`, `O16-nohousingscrews`, `O16-oneboard`, `O16-pad`, `O18-diagnosability`, `O18-stageC-classes`

**Stage C defined but not started:** `S1.3-T3`, `D10`

### Section 1 (owner-locked)

| Row | Method | C | D | Known fail | ECRs | Next |
|---|---|---|---|---|---|---|
| `S1.1-goal` | Analysis, Test, Demonstration | partial (surrogate) | not-started | yes |  | Re-cost the CPU budget for the U575; owner decides the 85 kHz versus 96 kHz top end |
| `S1.2-C1` | Inspection, Demonstration | partial (surrogate) | not-started |  | 0001, 0006 | Print the adapter and try it on her glasses (ECR-0006 dummy pair); measure her temple section |
| `S1.2-C2` | Inspection, Analysis, Demonstration | partial (surrogate) | not-started |  | 0006 | Add an Ear (open) keep-out solid and check arm, strut and pad against it; take the ruler shot (E9) |
| `S1.2-C3` | Analysis, Test | partial (surrogate) | not-started |  |  | Model the PWM and SMPS coupling path into the mic; fix a number for 'ambient' |
| `S1.2-C4` | Analysis, Inspection, Demonstration | partial (surrogate) | not-started |  | 0001, 0006 | Set numeric size and mass targets; owner confirms the D18 reading (O4) |
| `S1.3-T1` | Analysis, Demonstration | partial (surrogate) | not-started |  |  | Owner listens to the Phase-1 WAVs; record her home (S1); tune the gate (C4) |
| `S1.3-T2` | Analysis, Demonstration | partial (surrogate) | not-started |  | 0007 | Owner judges the nature WAVs; play them through the exciter at the tragus (E2, ECR-0007) |
| `S1.3-T3` | Test | not-started (surrogate) | not-started |  |  | Land the stage-C level-difference scenario and agree the blind-trial pass rule with the owner |
| `S1.3-T4` | Inspection, Demonstration | partial (surrogate) | not-started |  | 0006, 0007 | Re-run the Ear (open) clearance on the rev-1 arm; run E2 with the Ear (open) playing |
| `S1.3-T5` | Analysis, Test, Demonstration | partial (surrogate) | not-started |  | 0006 | Bend a NiTi coupon; wear the ballasted dummy pair for 2 h (ECR-0006) |
| `S1.3-T6` | Analysis, Test | partial (surrogate) | not-started |  |  | Map dBFS to bone-conducted loudness; run E7 and E11 as soon as rev 1 runs on battery |

### Decisions

| Row | Method | C | D | Known fail | ECRs | Next |
|---|---|---|---|---|---|---|
| `D1-force` | Analysis, Test | partial (surrogate) | not-started |  | 0001, 0006 | Bend a coupon of the real wire; measure force before and after 100 cycles |
| `D2-nolink` | Inspection, Test | partial (surrogate) | not-started |  |  | Land the stage-C T3 scenario; plan the E8 A/B (free-running against one shared clock) for the first two built pods |
| `D3` | Analysis, Test | partial (decides) | not-started |  | 0010 | Write the mode and volume state machine as host-tested code (ECR-0010) |
| `D6-output` | Analysis, Test | partial (surrogate) | not-started |  | 0003, 0004, 0005 | Decide with the simplification study whether the discrete bridge stays (ECR-0003, ECR-0004), then re-run the output checks on the surviving design |
| `D7-transducer` | Test | - | not-started |  | 0007 | Order the exciters (ECR-0007); measure R and L (E1); feed the numbers into the output-stage checks |
| `D9` | Analysis, Test | partial (decides) | not-started |  |  | Assert the 1.5 kHz floor in the Phase-1 run; measure the output spectrum on the 1 ohm sense (E7) |
| `D10` | Test, Inspection | not-started (decides) | - |  |  | Write the C5 sweep WAVs and procedure; owner runs E5 on headphones |
| `D11-topology` | Inspection, Analysis | partial (decides) | not-started |  |  | Add a netlist rule 'one inductor, on VLXSMPS'; settle the L1 and C8/C9 questions |
| `D11-selfnoise` | Test, Analysis | partial (surrogate) | not-started |  |  | Run E11 on rev 1 on battery; name the room 'ambient' is measured in |
| `D12-modes` | Analysis, Demonstration | partial (decides) | not-started |  |  | Tune the gate (C4) on real recordings (S1); owner picks algorithm A or B by ear |
| `D12-off` | Inspection, Test | partial (surrogate) | not-started |  | 0010, 0013 | Write Stop 2 entry with PB3 and PB4 parking; measure the Off current with the PPK2 |
| `D13-mic` | Analysis, Inspection, Test | partial (surrogate) | not-started |  | 0011 | Print the acoustic coupons and measure the port response (E3, S1); the mesh decision comes with them |
| `D14-clocks` | Analysis, Test | partial (decides) | not-started |  |  | Write the divider-chain script; bring up the ADF and scope the mic clock on rev 1 |
| `D16-crystal` | Inspection, Test | partial (surrogate) | not-started |  |  | Check the load capacitance once the board is placed; measure the offset between two units (E8) |
| `D17-ceiling` | Analysis, Test, Inspection | partial (decides) | not-started |  | 0009, 0005 | Tie the ceiling to a coil current or vibration level; add the pest-repeller case |
| `D17-popfree` | Inspection, Test | partial (surrogate) | not-started |  | 0009 | Simulate start/stop transients; write the soft-start sequence as host-tested code |
| `D18-runtime` | Analysis, Test | partial (surrogate) | not-started |  | 0008 | Add the LED to power.py; measure current per mode (E4); run a cell down |
| `D18-balance` | Analysis, Test, Inspection | partial (surrogate) | not-started | yes | 0001, 0006 | Compute rev-1 mass and centre of mass from the CAD; weigh the dummy pair |

### Owner decisions

| Row | Method | C | D | Known fail | ECRs | Next |
|---|---|---|---|---|---|---|
| `O8-led` | Inspection, Analysis, Demonstration | partial (surrogate) | not-started |  |  | Add LED current to power.py; settle the LED PWM against the idle-mode plan |
| `O9-prototype` | Inspection | partial (decides) | - |  | 0010 | Design the snap-off test frame and pogo jig; decide the SWD probe or a BOOT0 pad |
| `O10-twostage` | Inspection, Demonstration | partial (surrogate) | not-started |  |  | Write the sealing-and-service note; cut open and re-seal a printed pod |
| `O12-dock` | Analysis, Test, Demonstration | partial (surrogate) | not-started |  | 0009, 0010, 0013 | Design the boot stub and DFU entry; fix the dock cable and pin order |
| `O12-sealing` | Inspection, Test | partial (surrogate) | not-started | yes |  | Design the mic seal and mesh, choose skin and adhesive, write the spray-test plan |
| `O12-fastcharge` | Analysis, Test | partial (surrogate) | not-started |  | 0009, 0002, 0008, 0013 | Write the charger register plan as firmware; compute charge time; plan the supervised first charge |
| `O13-budget` | Analysis, Inspection | partial (decides) | not-started |  |  | Compute the first-order total against $300 once the simplification study fixes the part list; price the TBD items |
| `O16-cell` | Inspection, Analysis, Test | partial (surrogate) | not-started |  | 0001, 0008 | Dry-fit the real pouch; re-check the heel exit against it |
| `O16-connector` | Inspection, Test | partial (surrogate) | not-started |  |  | Fix the cable-side part number and stock; cut the USB-C keep-out in the shell model and check its overlap with the target |
| `O16-nohousingscrews` | Inspection | done (decides) | not-started |  |  | Confirm on the built pod |
| `O16-ip68switch` | Inspection, Test | partial (surrogate) | not-started |  | 0012 | Regenerate the board after the footprint cleanup; set the plunger reach; press-test on a scale |
| `O16-oneboard` | Inspection, Analysis | partial (decides) | not-started |  | 0011, 0001 | Script the left-pod board mapping and check the off-centre parts in both shells |
| `O16-pad` | Inspection, Test | partial (decides) | not-started | yes |  | Search for a pre-made pad; try Sugru inserts of about 8 x 14 mm |
| `O17-wiring` | Inspection, Test, Demonstration | partial (surrogate) | not-started |  | 0006 | Check the conductor path for clearance in both arm states; include the bundle in the ECR-0006 flex test |
| `O18-diagnosability` | Inspection, Test | partial (decides) | not-started | yes | 0010, 0009, 0003 | List the hooks the simplification study keeps or drops; write the self-test firmware |
| `O18-firmware-fixable` | Inspection, Test | partial (surrogate) | not-started |  | 0010 | Write the knob register: each uncertain value and the firmware setting that moves it |
| `O18-stageC-classes` | Analysis, Inspection | partial (decides) | - |  |  | Add checks for noise coupling, thermal, ESD and assembly yield |
| `O19-reliability` | Analysis, Test, Inspection | partial (surrogate) | not-started |  | 0006, 0008 | Flex-cycle the arm joint; build the spares list; complete the sourcing lock |
| `O19-serviceability` | Inspection, Demonstration | partial (surrogate) | not-started |  |  | Time a cell swap and an arm swap on a printed pod |
| `O20-finalsize` | Analysis, Inspection, Demonstration | partial (surrogate) | not-started | yes | 0001, 0006 | Set numeric board and pod envelopes in the simplification study |

### Spec items with no row (recorded waivers, `not_verifiable`)

| Item | Why nothing verifies it |
|---|---|
| `D4` | A method choice (digital DSP, not analog division). Its outcome is proven through D12-modes and the T1 and T2 rows, not by a check of its own. |
| `D5` | A component choice (STM32U575CIU6Q). What can fail is checked elsewhere: pin functions by interfaces:pins (O18-stageC-classes), run time by D18-runtime, the core SMPS by D11-topology, stock by ECR-0008 (O16-cell). |
| `D8` | A process choice (factory assembly at JLCPCB). bom_check (jlc-bom, assembly-tier, stock-lock) checks what it needs and rows O13-budget, O18-stageC-classes and O19-reliability cite it; no separate requirement to verify. |
| `D15` | A toolchain choice (bare C, CMake, CMSIS). No testable claim until firmware exists; ECR-0010 plans host-tested code first. |
| `O3` | An owner action (approve the shopping list once priced). Nothing to verify. |
| `O4` | An owner action (confirm the D18 reading of section 1.2.4). S1.2-C4 and D18-balance carry it in their gap and next. |
| `O5` | Superseded in part by O20 (growth is acceptable if it is clearance). Its open question, a stacked thicker pod against a slimmer one, belongs to the simplification study and O20-finalsize. |
| `O14` | A process rule (the PCB layout is done together). Nothing to verify. |
| `O15` | Superseded by O20 (rev 1 is final-size). Its question about debugging over USB is carried by O18-diagnosability (F4 self-test). |

<!-- vcrm:end -->

## Change log
- 2026-10-02: created from spec v0.15, the plm items, ECR-0001 to ECR-0013, `interfaces.py` and `bom_check.py` as they stood. 40 rows.
- 2026-10-02 (later): second version after an adversarial test. The checker now holds section 1 against git, runs the interface checks live, derives coverage from the spec, pins evidence files, rejects unknown keys and weak evidence, and reports a broken input as a FAIL instead of crashing. Rows added: D2-nolink, D6-output, D7-transducer, D13-mic, D14-clocks, D16-crystal, O13-budget, O16-connector, O17-wiring (49 rows); nine spec items carry a recorded waiver.
