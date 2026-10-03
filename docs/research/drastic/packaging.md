# drastic/packaging: packaging and manufacturing levers around a given cell (2026-10-03, PRELIMINARY)
```yaml
id: DRASTIC-PKG
status: preliminary research lane (workflow "drastic size reduction"); no design/board/shell edits; nothing committed
date: 2026-10-03 01:15-01:35 EDT
lane: packaging (flex/rigid-flex, stacking, embedding, SiP/COB, thin boards, 0201/01005, WLCSP, battery-as-structure, overmold, walls, seams)
baseline: MZ-2 "Balanced" = hw/mech/shell_r2.py + sim/checks/size_budget.py scenario(board 30x12, Bgap 1.4, Fgap 0.30, lid 0.8, plate 0.7, s_fixed 0.8, flat_tails)
  -> env 6259 mm3, L 38.0 x T 10.40 x H 14.5 (+belly 2.05), 12.2 mm off the temple outer face [V model run 2026-10-03 01:17]
method: every mm3 below = size_budget.scenario() with overrides (script: scratchpad/drastic/pk.py, pk2.py; fenced 3G, ~2 s). Model = derived, not measured [E].
tags: [V src date] verified primary · [E] estimate/derived · [TBD] unknown
glossary:
  Renata ICP501233PA-02: 175 mAh Li-polymer pouch cell with protection PCM, 35 x 12 x 5.3 mm
  STM32U575CIU6Q: ST Cortex-M33 MCU, UFQFPN-48 7x7 mm; STM32U575OIY6QTR = same die, WLCSP-90 4.20x3.95x0.59 mm
  SPH0641LU4H-1: Knowles PDM MEMS mic, bottom port, 3.5x2.65x1.08 mm (ultrasonic response specified)
  BQ25180: TI 1-cell linear charger, WCSP-8; TPS7A2030: TI 300 mA LDO
  FPC: flexible printed circuit (polyimide); rigid-flex: rigid FR-4 islands laminated with shared flex layers
  COB: chip-on-board (bare die wire-bonded + glob-top); SiP: system-in-package
```

## 0. Headline (blunt)
```yaml
H1: "Packaging alone cannot make this pod drastically smaller. The cell (2226 mm3) is 36 % of the 6259 mm3 envelope; walls+plate+spine ~30 %; the whole electronics band (Bgap 1.4 + board 0.8 + Fgap 0.3 over 38 x 14.5) is ~1380 mm3 = 22 %. Even deleting the electronics band entirely saves 22 %." [E size model]
H2: "Ranked by mm3 per unit pain: (1) walls 0.8->0.6 + drop the 0.7 plate = -764 mm3 (-12 %), zero electronics change; (2) board OFF the cell's big face, onto its top edge (PK-TOP) = -347 mm3 alone, -1130 combined with (1) (-18 %), pod 1.9-3.0 mm flatter against the head but 2.7 mm taller, needs WLCSP MCU + mic/SW1 on a flag; (3) hearing-aid end-cap (rigid-flex stack behind the cell) = -586 mm3 but +5 mm long and the costliest build." [E]
H3: "The real multiplier: packaging tech pays only once the cell shrinks below the board footprint. With a smaller cell (placeholder 25x10x4.5) a one-face 30x12 board sets the pod (4943 mm3); a two-face 25x10 board (0201 + 6L/POFV, QFN48 still fits) gives 4193 (-15 %); + walls 0.6/no plate 3558 (-43 % vs today); top-board variant 3778. So: pair this lane with the cell/power lane, do not run it alone." [E pk2.py]
H4: "Rejected for a hand-built, years-worn, serviceable personal device: component embedding, COB/bare die, custom SiP, full potting/overmold of the cell, 01005, 0.4 mm laminate at JLC. No off-the-shelf module/SiP is smaller than what we have (our MCU is already 7x7 QFN; its WLCSP is 4.2x3.95)." [E reasoning; fab facts V below]
```

## 1. Where the volume is (MZ-2, for scale)
```yaml
cell_box: 35 x 12 x 5.3 = 2226 mm3 (36 %) [V datasheet dims per spec; E share]
T_stack_mm: {wall 0.8, VHB 0.3, cell 5.3, Bgap 1.4, board 0.8, Fgap 0.30, lid 0.8, plate 0.7, total 10.40} [V shell_r2.py L46-63]
sensitivity: "0.1 mm of T ~ 60 mm3; 0.1 mm of all walls ~ 190 mm3; 0.1 mm of L ~ 15 mm3" [E from runs below]
pinned_items: {Bgap 1.4: "mic 1.08 + unknown pouch swelling (MZR-06, MZV-14)", board 0.8: "JLC floor for assembled 4L/6L (MZR-01)", H 14.5: "cell 12 + 0.8 under-slack + walls", belly 2.05: "dock target 2.8 + tails"}
```

## 2. Model runs (all vs MZ-2 6259 mm3)
| id | change | L x T x H(+belly) | env mm3 | delta | off temple |
|---|---|---|---|---|---|
| base | MZ-2 | 38.0 x 10.40 x 14.5 (16.55) | 6259 | 0 | 12.2 |
| PK-W6 | walls+lid 0.6 | 37.6 x 10.0 x 14.1 | 5873 | -386 (-6.2 %) | 11.8 |
| PK-W5 | walls+lid 0.5 | 37.4 x 9.8 x 13.9 | 5686 | -573 (-9.2 %) | 11.6 |
| PK-P0 | drop 0.7 plate | 38.0 x 9.7 x 14.5 | 5880 | -379 (-6.1 %) | 11.5 |
| PK-W6P0 | W6 + P0 | 37.6 x 9.3 x 14.1 | 5495 | -764 (-12.2 %) | 11.1 |
| PK-B6 | board 0.6 (other fab) | 38.0 x 10.2 | 6139 | -120 (-1.9 %) | 12.0 |
| PK-B4 | board 0.4 (other fab) | 38.0 x 10.0 | 6018 | -241 (-3.9 %) | 11.8 |
| PK-CW | temple-side tub wall -> adapter-backed film (T -0.8) | 38.0 x 9.6 | 5778 | -481 (-7.7 %) | 11.4 |
| PK-LP | tall-part relief (Bgap-equivalent -0.4) | 38.0 x 10.0 | 6018 | -241 (-3.9 %) | 11.8 |
| PK-TOP | board on cell's top edge, two-face stack 2.7, swell gap 0.6 | 38.0 x 8.5 x 17.2 (19.25) | 5912 | -347 (-5.5 %) | 10.3 |
| PK-TOP1 | same, one-face stack 2.0 | 38.0 x 8.5 x 16.5 (18.55) | 5706 | -553 (-8.8 %) | 10.3 |
| PK-END | hearing-aid end-cap, 5 mm behind cell | 43.0 x 8.5 x 14.5 | 5673 | -586 (-9.4 %) | 10.3 |
| PK-TOP+W6P0 | TOP + walls 0.6 + no plate | 37.6 x 7.4 x 16.8 (19.05) | 5129 | -1130 (-18.1 %) | 9.2 |
| PK-2F | two-face board, F band 0.75 (MZ-2b-like) | 38.0 x 10.85 | 6529 | +270 | 12.65 |

Small-cell coupling (placeholder cell 25 x 10 x 4.5; the real cell comes from the power/cell lane) [E pk2.py]:
| id | change | L x T x H | env mm3 | vs today |
|---|---|---|---|---|
| SC-1F | one-face 30x12 board (board sets L and H) | 33.0 x 9.6 x 14.2 | 4943 | -21 % |
| SC-2F | two-face 25x10 board, F band 0.75 | 28.0 x 10.05 x 12.5 | 4193 | -33 % |
| SC-TOP | top-edge board 25 x 5.1, two-face, mic flag | 28.0 x 7.7 x 15.2 | 3778 | -40 % |
| SC-2F+W6P0 | SC-2F + walls 0.6 + no plate | 27.6 x 8.95 x 12.1 | 3558 | -43 % |
note: "model belly (dock 25.5 long) is kept in every SC row; a smaller dock target would add more. SC rows only show the coupling, not a cell choice."

## 3. Measures
```yaml
PK-01 walls 0.8 -> 0.6 (tub + lid), seams kept:
  saving: -386 mm3 (-6.2 %); 0.5 mm walls -573 [E model]
  function: none electrical; impact strength and drop toughness lower; seam tongue/groove gets thinner (r2 already stops 1.4 mm short of corners because the chamfer leaves 0.42 mm wall, shell_r2.py L15-16)
  risk: med. Resin limit noted in repo: "recesses under 0.4 mm may fuse" (physical.md L159 via skeptic.md L86). 0.6 walls in a tough/ABS-like resin are normal for SLA [E]; fab/printer min wall [TBD: JLC3DP / owner printer]. Sweat + UV ageing of resin over years (O19) [TBD]
  build: owner-printable if her printer holds 0.6 (test coupon first)
  cost: ~0; effort: Claude 0.5 d (param change + clash re-run + coupon STL); owner 0.5 d print + drop/press test
  conf: E
  sources: [sim/checks/size_budget.py, hw/mech/shell_r2.py, docs/research/simplify/size.md SIZ-11]

PK-02 drop the 0.7 armour plate (owner call already open in size.md S2; the plate is owner styling: "gunmetal armour plate with an engraved circuit-trace groove ... shell, plate, fin and heel print as one part" [V spec L458-461]; a 0.2-0.3 mm engraved skin instead of 0.7 keeps the look for ~-215..-270 mm3 [E linear]):
  saving: -379 mm3 (-6.1 %); also shortens the mic duct by 0.7 (acoustic gain, PIN-4)
  function: none; styling/scuff layer lost
  risk: low; cost 0; effort Claude 0.2 d; owner decision only
  conf: E · owner_call: true

PK-03 board on the cell's TOP EDGE ("spine board"), not on its big face:
  what: "board ~35 x 5.6 (inner T) lies in the x-y plane above the cell; parts both faces. The cell face against the lid gets a 0.6 swell gap. Mic SPH0641LU4H-1 + SW1 move to a small 'flag' (2-layer rigid 0.6 mm, JLC-assembled, or FPC) on the lid inner face, wired/flexed to the main board (PDM CLK/DATA/VDD/GND/SEL ~10 mm)."
  saving: -347 mm3 alone (-5.5 %); -553 with a one-face stack; -1130 with PK-01+02 (-18 %) [E]
  shape: pod T 10.4 -> 8.5 (1.9 mm less off the head: 12.2 -> 10.3) but H +2.7 (16.55 -> 19.25 incl. belly) [E]; the bulk moves upward along the temple's top edge -> vision-line / O20 fit check needed
  blockers:
    - "U1 QFN48 7x7 does not fit a 5.6 mm-wide board -> needs WLCSP90 (4.20x3.95) [V pcb-tech S15/S16]: X-ray only, no hand rework, 10 in stock at LCSC 2026-10-03 [V pcb-tech.md S16], 0.4 mm hex grid escape needs 6L/POFV or HDI (pcb-tech.md L199-206)"
    - "mic port faces out through the lid as today (flag on the lid) -> acoustic duct unchanged; PDM wire run adds EMI exposure next to the H-bridge leads [TBD noise model]"
    - "SW1 press force goes into the flag/lid, not the main board (fine) [E]"
    - "two-face 35x5.6 = 2 x 196 = 392 mm2 vs ~209 mm2 courtyard needed today (one-face U 0.58 x 360) -> U ~0.53 [E]; tight but routable only with 0201 + 6L/POFV"
  function: none if WLCSP + flag work; degraded serviceability (WLCSP)
  risk: high (WLCSP on a worn 0.8 board, O19/O20; O18 wants rev 1 instrumented to fail informatively: WLCSP balls cannot be probed, so test pads must be fanned out [V spec L644]; new mech architecture; vision line)
  build: owner can hand-solder the flag wires (5 x 0.1 mm litz); main board still machine-assembled
  cost: +$6.2/MCU [V pcb-tech S16]; 6L or POFV per pcb-tech PT-01/02 [TBD quote]; 2L flag board ~ small [E]
  effort: Claude 4-6 d (new placement, shell_r3, noise + acoustic re-runs); owner 1-2 d (review, print, build)
  conf: E

PK-04 hearing-aid end-cap (rigid-flex fold behind the cell):
  what: "3 rigid islands ~11 x 5.5 mm (both faces) joined by flex, folded into a 5 mm stack at the rear of the cell; T loses the whole electronics band"
  saving: -586 mm3 (-9.4 %) but L 38 -> 43 [E]
  blockers: "QFN48 does not fit 5.5 wide -> WLCSP90; island-to-island fold needs rigid-flex: JLC 'does not support Rigid-Flex' [V jlcpcb.com/capabilities/flex-pcb-capabilities 2026-10-03, per pcb-tech S3]; PCBWay does: rigid-flex 0.25-6.0 mm, up to 26 layers, 0.065/0.065 mm track, 0.10/0.35 hole/pad [V pcbway.com/fpc-rigid-flex-pcb/rigid-flex-pcb.html 2026-10-03]; bend radius multilayer 10-15 x t [V pcbway.com/fpc-rigid-flex-pcb.html 2026-10-03]; price quote-only [TBD]; prototype rigid-flex typically hundreds of USD for 5 pcs [E, unverified]"
  function: none if it works; mic must sit on the outward-facing island; rear-end bulk shifts mass toward the ear (balance re-check)
  risk: high (new fab, no repair, longer pod may hit the ear hook)
  build: owner cannot rework; folding + spacer glue by hand is feasible [E]
  effort: Claude 6-10 d; owner 2-3 d + fab wait (PCBWay rigid-flex lead [TBD])
  conf: E
  verdict: "worse than PK-03 per unit pain on THIS cell; only interesting if a much thinner cell makes the end-cap the natural place"

PK-05 temple-side wall: adapter-backed, or adapter and tub merged:
  what: "the tub face that rests on the glasses adapter (1.8 mm, from_temple_outer = 1.8 + T) is backed full-face by the adapter; thin it to 0.4 (or make tub+adapter one print and the cell-side wall disappears into the adapter)"
  saving: -241 (0.4 mm thinner, the only spec-compatible variant) .. -481 mm3 (merge, T -0.8, blocked by spec) [E]; also brings the pod 0.4-0.8 mm closer to the head
  function: "MERGE VARIANT VIOLATES AN OWNER REQUIREMENT: 'Frame adapter is a separate print ... swap it for new frames without reprinting the pod' [V docs/spec.md L462-463] and O26 'adapter must fit TWO different frames, possibly in a flexible material ... removable' [V spec L652]. Only the 0.4 mm adapter-backed wall (-241) survives, and only if the adapter is rigid where it backs the cell (a flexible adapter cannot be the cell's armour)."
  risk: med (pouch puncture protection now = adapter; cell swap path must still work: r2 swaps the cell from the lid side, shell_r2.py L10-14, so merge is compatible) [E]
  build: owner-printable; cost 0; effort Claude 1 d, owner 0.5 d
  conf: E (needs adapter geometry check)

PK-06 thinner laminate at another fab (PCBWay):
  facts: "PCBWay standard list 0.2/0.4/0.6/0.8... mm, tol ±0.1 below 1.0 [V pcbway.com/capabilities.html 2026-10-03]; layer-count limits for 4L/6L at 0.4/0.6 not stated on the page [TBD quote]. PCBWay assembly: passives down to 01005, BGA 0.3 mm pitch rigid / 0.4 flex, min order 5 pcs, min board 10x10 else panelize [V pcbway.com/assembly-capabilities.html 2026-10-03]. JLC: 0.6 not for 4L/6L, 0.4 cannot be panelised [V pcb-tech.md B1]"
  saving: -120 (0.6) / -241 (0.4) mm3 [E]; mic duct shorter by 0.2/0.4 (acoustic gain)
  function: none; stiffness falls as t^3 (0.6: 2.4x, 0.4: 8x deflection under SW1 press / lid-hung bond, architecture.md ARCH-05) -> moving SW1 off the board (PK-03 flag) removes the main load
  risk: med (second fab, parts consigned or PCBWay turnkey, no JLC Basic-part pricing; 0.4 4L planes thin -> noise model re-run)
  cost: PCBWay assembly quote [TBD]; likely several x JLC for 5 pcs [E]
  effort: Claude 1-2 d (stack-up, rules, sourcing lock redo); owner: second account + order (O21: at freeze)
  conf: V fab list / E saving / TBD price
  verdict: "small on its own; worth folding in only if the order moves to PCBWay anyway (e.g. for rigid-flex)"

PK-07 relieve tall parts instead of sizing the whole band to them:
  what: "Bgap 1.4 is set by the 1.08 mic over the whole 30x12 area. Options: (a) mic in a board cut-out is NOT possible (bottom port needs board under it); (b) put the mic on the lid flag (as PK-03) so the B band drops to the next tallest part (L1 ~1.0 [E]) -> no gain unless L1 also leaves; (c) cell-side relief impossible (pouch face cannot be pocketed)"
  saving: up to -241 mm3 for -0.4 mm of band [E] if both mic and L1 leave the B face; swelling allowance stays the real floor (MZV-14)
  risk: med; conf E; verdict: "only as part of PK-03; on its own blocked by unknown pouch swelling"

PK-08 0201 / 01005 / WLCSP everywhere:
  facts: "JLC Std PCBA min 0201 [V pcb-tech S2]; PCBWay accepts 01005 [V 2026-10-03]; 0402->0201 = -0.73 mm2 courtyard each, -20..-26 mm2 total [V/E pcb-tech PT-05]; WLCSP MCU -28..-45 mm2, 0 height [V/E BL-4]"
  saving: 0 mm3 on today's cell (area is volume-free, BL-1); enabler only for PK-03/04 and for a smaller cell (SC rows: -750 mm3 between SC-1F and SC-2F)
  risk: 01005 = no owner rework, tombstoning, DC-bias loss -> reject 01005 [E]
  conf: V facts / E saving

PK-09 component embedding (cavity/embedded passives), COB/bare die, custom SiP:
  verdict: REJECT for rev 1. "No hobby/proto fab path for embedded components found in this session [TBD]; bare U575 die not sold to individuals [E]; custom SiP (e.g. Octavo Systems' custom SiP service; their OSD32 parts are Linux-class AM335x SiPs, far bigger and hungrier than this MCU) has engineering NRE and MOQ far beyond 2 pods [E]. ST/Nordic modules (e.g. STM32WB5MMG, a 7.3x11 mm BLE module) are BLE radios, larger than our QFN48 and add nothing we need [E]. Saving would be area only (0 mm3 on this cell)."
  conf: E

PK-10 overmold / potting instead of shell + air:
  what: "low-pressure hot-melt moulding or cast urethane/silicone around the electronics"
  saving: "air in MZ-2 is already small (Bgap/Fgap/stowage); potting replaces air with fill, not with nothing: ~0 mm3 unless walls also go (then ~PK-01-like) [E]"
  function: kills cell swap and board rework (O19 serviceability), traps pouch swelling (safety) -> REJECT for the cell; acceptable only for a sealed flag sub-assembly
  conf: E

PK-11 seams:
  what: "r2 seam = tongue/groove on straight runs (shell_r2.py L15-16). A glued or ultrasonic-welded seam saves the tongue (~0.3-0.4 mm locally) but blocks cell swap. Keep the serviceable seam; a gasket-less snap at 0.6 walls needs a test coupon."
  saving: ~0-100 mm3 [E]; conf E; verdict: keep
```

## 4. What the owner can still build by hand (owner-builds-by-hand rule)
```yaml
yes: [PK-01 walls (print + test coupon), PK-02 plate, PK-05 adapter merge (print), PK-03 flag wiring (hand-soldered litz), PK-04 fold + glue]
no_rework: [WLCSP MCU (PK-03/04), 01005, rigid-flex islands, COB, embedded]
```

## 5. Integration-map cross-check (not run: no time)
```yaml
not_done:
  - "tools/plm.py impact not run (read-only lane, no edits). PK-03/04/05 touch: mech shell, board placement, mic duct acoustics, noise model (PDM wire), balance (mass moves up/back), dock belly, vision-line fit (O20)."
  - "docs/system/integration-map.md not read in this lane (time)."
  - "spec checked late (01:20): adapter separate + removable (L462, O26) -> PK-05 merge blocked; plate is owner styling (L458) -> PK-02 owner call; O18 diagnosability -> WLCSP needs fanned-out test pads."
  - "no adapter geometry read (PK-05 saving is a stack-up estimate)."
  - "PCBWay 4L/6L at 0.4/0.6 and rigid-flex prices: quote-only [TBD]."
  - "resin min wall for the owner's printer / JLC3DP [TBD]."
  - "no diagram rendered (parent can draw: T-stack today vs PK-03 vs PK-04, to scale)."
```

## 6. Recommendation for this lane (owner decides)
```yaml
A_cheap: "PK-01 + PK-02 (+ PK-05 thin-wall variant if the adapter is rigid there): -764..-1005 mm3 (-12..-16 %), no electronics change, owner-buildable. Do regardless of what else is chosen."
B_architecture: "PK-03 top-edge board: another ~-370 mm3 on this cell; it pays much more if the cell lane picks a thinner/smaller cell (SC-TOP 3778). Costs WLCSP + mic flag."
C_holdoff: "PK-04 end-cap, PCBWay thin laminate, embedding/COB/SiP: not worth it on this cell."
coupling: "Decide the cell first (other lane). Packaging tech then sets how close the pod gets to cell + ~1.3 cm3."
```
