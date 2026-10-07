# Pod body: tub, lid, retention, duct, switch pocket, dock bay
Rev MZ-2 2026-10-07: body rewritten to the Phase-2 shell (`hw/current.yaml`, ECR-0018): seam at the board's B face, board hung from the lid on per-pad-cut VHB, sealed D1.0 duct + gauge pin, SW1 pocket + selective-fit puck, no ribs/foam; Rev F/G shell moved to the reference section.
Status: Phase-2 shell CAD `hw/mech/shell_r2.py` (constants `hw/mech/dims_r2.py`), last rebuilt for commit c348661 (2026-10-07 07:30): `hw/mech/out/r2/checks.json` every clash 0 mm³, tub/lid/puck each 1 valid solid. Not printed, not owner-reviewed (O25: review in 1-2 weeks). Updated 2026-10-07.
· Source of truth: `hw/mech/dims_r2.py` (every number), `hw/mech/shell_r2.py` (solids, checks), `hw/mech/notes/shell_r2.md` (decisions D1-D8, retention options, assembly), `hw/mech/blade.py` (rail, adapter), `hw/mech/heel.py` (heel unioned into the tub, [reg-arm](reg-arm.md)), `docs/build/tolerances.md` (Rev-1 fits; no Phase-2 rows yet, issue 18)
· Owner decisions: O5, O10, O12(b), O16(3)(5)(6)(7), O17, O19, O24 (sealed duct D1.0 + locating), O25/O26 (Phase 2, Claude lays out), O27 (thin > short > long) · ECR-0001 (`frame.py`/`pod.py` constants) implemented 2026-10-07, awaiting owner review · Open ECRs: ECR-0006 (weighted dummy pair, wear + joint flex), ECR-0018 (Phase 2, approved, implementation in progress)

## Purpose
- Holds and protects the board, the cell and the dock target, **without screws** (O16-6).
- Mechanical half of: **F1** sealed mic duct in the lid; **F11** SW1 pocket, puck and skin; **F5/F9/F10/F15** dock window in the belly; **F3/F12** stowage zone + heel + wire channel (`integration-map.md` §1).
- Mounts to the glasses through a removable frame adapter (spec §8; adapter work deferred, O26).
- Two-stage build (O10): taped test build, bonded final build that can be cut open. Sealing IPX4 min, IPX5 preferred (O12b).
- Exterior: "Spine" top (O17), carried over from r1 onto the Phase-2 top.

## Big picture
Renders (build outputs, gitignored; `shell_r2.py` writes them): `hw/mech/out/r2/section.png` (y-z section through mic and SW1), `hw/mech/out/r2/plan.png` (x-z plan through the lid: board, mic, SW1 pocket, dock, stowage, seam keys). No 3D render dump of r2 yet (issue 9).

1. **Two prints + a puck.** The **tub** is everything below the seam y 12.1 (the board's B face) **plus the whole belly** (x < 55.0, z < −8.9), so the dock window lies in one part. It carries the heel, the dovetail rail and the strut relief. The **lid** is a shallow cap y 12.1-14.7: skirt walls round the board, lid face 0.8, armour plate 0.7, spine top. Printed **puck** in the SW1 bore (5 lengths, selective fit).
2. **Stack, inside out (pod y):** wall 4.3-5.1 → cell VHB gap 0.3 → cell 5.4-10.7 → **B gap 1.4** (B parts, tallest U2 1.08) → board 12.1-12.9 → **F gap 0.30 = VHB 4914 0.25 + 0.05** → lid face 13.2-14.0 → plate 14.0-14.7. Thickness T 10.4 (dims_r2.py, 2026-10-07).
3. **Retention:** the board **hangs from the lid** on full-face 3M VHB 4914, die-cut at the duct (D1.0), the SW1 pocket (4.3 × 3.1) and one 1.8 mm square per F test pad (TP1-TP6): 91 % of the tape outline bonded, ~314 mm² (interfaces.py [clamp-bands] PASS; checks.json `vhb_area_mm2` 313.9; 2026-10-07). Nothing touches the board's long edges (0.45 free each side). Lifting the lid lifts the board on its wires and exposes the cell.
4. **Locating:** the lid's D1.0 duct bore is the datum. While the VHB grabs, a stepped gauge pin (D0.98 body in the bore / D0.50 tip in the board's D0.6 hole) registers tape and board to the bore; then it is pulled. The front skirt wall is a coarse x-stop 0.25 ahead of the board and never touches within tolerance (so it can't fight the pin).
5. **Seam:** tub tongue 0.35 × 0.5 / lid groove +0.05 on the straight wall runs, stopped 1.4 mm short of every convex corner; a 0.35 × 0.35 key on the belly step. Cut line: 0.2 × 0.4 tub-only rebate on the y 12.1 runs (0.3 before 2026-10-07); the belly step has none (issue 12).
6. **Rear:** stowage zone behind the board (pod x 60.55-66.7, cell top → lid face) + 1.1 mm behind the cell: 277 mm³ for the 12 wire loops (need 107-142).

## Elements
```yaml
# pod mm: x rearward, y outward, z up (right pod = CAD; left = mirror). src hw/mech/dims_r2.py unless noted; 2026-10-07
outer_body: {x: [29.5, 67.5], y: [4.3, 14.0], plate_to: 14.7, z: [-9.7, 4.8], chamfer: 1.0, wall: 0.8}
belly: {x: [29.5, 55.0], z_to: -11.75, depth: 2.05, why: "flat-tail dock target 2.8 + tails 0.85 - (wall + 0.8 under-cell slack)"}
cavity: {x: [30.3, 66.7], y: [5.1, 13.2], z: [-8.9, 4.0]}
bay: {x: [30.3, 54.2], z: [-10.95, -8.9]}
tub: "outer_body & (y < 12.1, + belly x < 55 / z < -8.9) + blade.rail + heel.heel_add - cavity - heel.heel_cut - dock window - strut relief + tongue + plate below the belly step - seam rebate (shell_r2.py tub())"
lid: "outer_body - tub region + plate - cavity - groove - duct bore - hex window - SW1 pocket/bore/skin recess + spine top (shell_r2.py lid_base(), top_concept())"
seam: {y: 12.1, tongue: "0.35 x 0.5, groove clearance 0.05, stops 1.4 short of convex corners (1 mm chamfer leaves 0.42 wall)", belly_step_key: "0.35 high (the hanging board's lower edge sweeps past it, 0.10 clear)", rebate: "0.2 x 0.4 (was 0.3 until 2026-10-07), tub only, y 12.1 runs; belly step unmarked"}
board_pocket: {board: "30 x 12 x 0.8 R1.0 at x 30.55-60.55, y 12.1-12.9, z -8.45..3.55", x_stop: 0.25, long_edges_free: 0.45, rear_to_wall: 6.15}
vhb: {part: "3M VHB 4914 (0.25 mm acrylic foam tape)", outline: "board inset 0.2", cut_outs: ["D1.0 duct", "4.3 x 3.1 SW1 pocket", "1.8 mm square per TP1-TP6 (TP_PAD_D 1.0 [A] + 0.4 margin; real TP copper D0.7)"], bonded: "~314 mm2, 91 % (interfaces.py clamp-bands PASS)"}
mic_duct: {axis: "pod (32.43, z -2.45) = board (1.88, 6.0), read live from the routed board (dims_r2.board_mic)", bore: "D1.0, printed undersize + reamed, lid face y 13.2 -> hex floor 13.9 (0.7)", vhb_hole: "D1.0 across the 0.30 F gap", board_hole: "NPTH D0.6", length: "1.0 total (notes/shell_r2.md D4)", hex_window: "R1.9 x 0.8 deep from the plate top = mesh seat (mesh part TBD)"}
gauge_pin: {body: 0.98, tip: 0.50, runout: 0.02, material: "turned brass [A]", state: "to source or turn (issue 16)"}
sw1_pocket: {centre: "pod (49.05, -2.45) = board (18.5, 6.0)", pocket: "4.3 x 3.1, ceiling y 13.8 (0.25 over SW1 nominal)", bore: 2.6, puck: "D2.3 + nub D1.0 x 0.10", skin: "silicone D4.6 x 0.25 recess, floor y 14.45, flush with the plate", puck_kit: [0.73, 0.78, 0.83, 0.88, 0.93]}
dock: {part: "Xinyangze YZT0675 (5-pin magnetic pogo target, 21.2 x 6.86 x 2.8, LCSC C5126848)", box: "x 31.5-52.7, y 5.72-12.58, z -11.75..-8.95", window: "+0.1 per side through the belly floor", tails: "flat, in the 0.8 under-cell slack"}
usb_c_keepout: "not carried into shell_r2 (R-DOCK-BODY)"
cell_bed: {cell: "Renata ICP501233PA-02 envelope x 30.6-65.6, y 5.4-10.7, z -8.1..3.9", tape: "VHB 4914 0.25 in the 0.3 gap to the inner wall"}
strut_relief: "identical to r1 (same Z0, CAV y0/z0): fill 1.0 legs in the inner-bottom rear corner x 62-66.7; outside cut to y + z = -3.65"
rail_adapter: "blade.rail(zc=-2.45) in shell_r2; since ECR-0001 (2026-10-07) blade.rail()/blade.adapter() default to pod.POD_ZC = the current body centre (-2.45), so the modelled adapter slot now mates the r2 rail (it sat 0.45 mm high before). The adapter itself is still redesigned with the two-frame adapter work (O26, deferred); shell_r1 pins its as-built -2.0 (RAIL_ZC)"
spine_top: "shell_r1.concept_spine moved -1.4 y / -0.7 z onto the r2 top, unioned into the lid (159.6 mm3)"
```

## Interfaces
```yaml
- to: reg-board
  crosses: "board 30 x 12 x 0.8 at x 30.55-60.55, y 12.1-12.9, z -8.45..3.55; F face on VHB; B band 1.4 (tallest U2 1.08, margin 0.32); F band 0.30 (SW1 pocket 0.90, SW1 0.65 margin 0.25); F parts only in VHB cut-outs; x-stop 0.25"
  invariant: "no F part outside a cut-out; nothing on the long edges; interfaces.py outline/inside/heights/clamp-bands PASS 2026-10-07"
  rel: R-BOARD-BODY
- to: sub-audio-in
  crosses: "duct bore D1.0 + VHB hole D1.0 over the board's D0.6 NPTH at board (1.88, 6.0) = pod 32.43"
  invariant: "nominal offset 0.000 (interfaces.py mic-port PASS); worst 0.115 <= 0.20 with the gauge pin, 0.86 FAIL walls-only (checks.json duct)"
  rel: R-AUDIO-BODY
- to: sub-ui
  crosses: "SW1 pocket 4.3 x 3.1 + D2.6 bore + puck + skin over board (18.5, 6.0) = pod 49.05"
  invariant: "selective fit puck top -> skin 0.005..0.135 (PASS); fixed puck worst -0.198 pre-presses (FAIL, why the kit exists); interfaces.py switch WARN: lateral stack 0.20 vs 0.15 limit"
  rel: R-UI-BODY
- to: sub-dock-usb
  crosses: "DOCK box + window in the tub belly, BAY; 5 dock wires target -> J3/J4/J10/J11/J12 (B, board x 25-29)"
  invariant: "wire route under the cell (0.8) undesigned (issue 7)"
  rel: R-DOCK-BODY
- to: sub-power
  crosses: "CELL envelope on 0.25 VHB in the 0.3 gap; 1.4 B gap to the hanging board"
  invariant: "B parts never touch the cell (checks.json clash parts_B/cell 0)"
  rel: R-PWR-BODY
- to: reg-arm
  crosses: "heel unioned into the tub (heel.heel_add/heel_cut, unchanged); channel exit (66.20, 5.15, -5.50) necked D0.8 into the 1.1 gap behind the cell (2026-10-07); arm bundle on the rear wall, then the upper stowage; strut relief"
  invariant: "exit hole x 65.80-66.60 behind the cell end 65.6 (rim-corner 0.36), outer wall 0.60; arm wires keep >= 0.39 to the cell, 0.68 to the rear seam (heel checks.json wire_route)"
  rel: R-BODY-ARM
- to: physical
  crosses: "frame axes; frame.py/pod.py pod names derived from dims_r2.py (frame.pod_facts(), ECR-0001); assembly order"
  invariant: "interfaces.py frame PASS: 10 of 10 shared facts agree (2026-10-07)"
  rel: R-PHYS-FRAME
- to: sub-debug-test
  crosses: "TP1-TP6 bare pads on F under the VHB cut-outs, facing the lid 0.30 away"
  invariant: "reachable only before the lid bond (checks.json F_face_pads reachable_assembled false); after it SWD = peel the board off the lid (issue 15)"
- to: reg-pad
  crosses: "no direct contact: pad pose via the arm (frame.pad_pose)"
- to: spec
  crosses: "O10, O12b, O16-6, O17, O24 (duct), O27 (thin first)"
  rel: R-SPEC-BODY
```

## Constraints
- **O16-6** no screws in the housing (cup screw and NiTi set screws allowed). **O10** taped test build, bonded cut-openable final build.
- **O12b** IPX4 min, IPX5 preferred. **O16-3** pre-built magnetic connector. **O16-7** IP68 switch (KMT022), not a printed flexure.
- **O16-5** one board for both pods: mic and SW1 on the board centre line y 6.0 = pod z −2.45; left shell = mirror.
- **O24(1)** sealed straight duct ID 1.0 between lid bore and board hole + a board locating feature (x-stop + gauge pin here) + firmware EQ notch (target moved to ~63 kHz, sub-audio-in).
- **O27** thin first, then short, then long: T 10.4 (Rev F 11.8), H 14.5 (Rev F 15.2), L 38.0 unchanged.
- **O19** serviceability: cell swap must not destroy the board bond (lid lifts the board; met by D1 seam). **R20/R24** via ECR-0006.
- **Spec §8:** port opens over the board hole, no gasket cavity, thin mesh never foam; nothing visible with the eyes straight ahead (pod x ≥ 29.5).
- **Resin** (`tolerances.md`, `hardware.md` §5): holes < ~0.8 mm may close, recesses < 0.4 may fuse; ream critical holes.

## Key numbers
```yaml
- {q: envelope T x L x H, v: "10.4 x 38.0 x 14.5 (+ belly 2.05 under x < 55; + spine)", src: "checks.json envelope; dims_r2.py; 2026-10-07"}
- {q: envelope volume, v: "6211 mm3 (body 5720.9 + plate 330.5 + spine 159.6) vs size model MZ-2 6259; Rev F 7801 (-20 %)", src: "checks.json envelope; ECR-0018 log 2026-10-03"}
- {q: print volumes, v: "tub (with heel) 1321.5, lid (with spine) 863.3, puck 3.11 mm3", src: "checks.json volumes 2026-10-07"}
- {q: shell mass, v: "~2.58 g at 1.18 g/cm3 (tub 1.56, lid 1.02)", src: derived}
- {q: pod mass lower bound, v: ">= ~9.5 g before parts, dock target, adapter, wires: shell 2.58 + cell ~4.2 + pad 2.19 + bare board 0.53 (30 x 12 x 0.8 at 1.85 g/cm3); target ~8 g", src: "derived; pad checks.json; sub-power"}
- {q: clearances, v: "board: front 0.25 (x-stop), long edges 0.45, rear 6.15 (stowage); cell: inner 0.3 (tape), top 0.1, bottom 0.8 (dock tails), rear 1.1; B gap 1.4 (margin 0.32 over U2 1.08); F gap 0.30 (VHB 0.25 + 0.05)", src: "checks.json board_in_cavity/B_gap/F_gap; dims_r2 CAV/CELL"}
- {q: duct offset, v: "nominal 0.000; gauge pin worst 0.115 PASS (limit 0.20 = (1.0-0.6)/2); walls-only 0.86 FAIL", src: "dims_r2.duct_offsets(); checks.json duct"}
- {q: switch stack, v: "puck 0.83 nominal, kit 0.73-0.93; selective fit 0.005..0.135 PASS; fixed worst -0.198..0.287 (pre-press); pocket ceiling clear 0.25 nom / 0.082 worst", src: "dims_r2.switch_stack(); checks.json SW1_pocket"}
- {q: stowage, v: "277.3 mm3 (198.3 behind board + 78.9 behind cell), zone 6.15 long, need 107-142", src: "checks.json stowage"}
- {q: interference, v: "tub/lid x {pcb, parts_B, u2_mic, sw1, cell, vhb, dock}, tub/lid, parts_B/cell, puck/lid, puck/sw1: all 0 mm3; drop-in corridors (cell, lid+board) 0", src: "checks.json 2026-10-07"}
- {q: lid thickness at duct/puck, v: "0.8 + 0.7 plate = 1.5", src: dims_r2 LID_T, PLATE_T}
```

### Sealing paths (O12b)
```yaml
- {path: seam straight runs, design: "tongue 0.35 x 0.5 / groove +0.05 + bond line (MS-polymer or neutral RTV, product TBD)", state: "designed, untested"}
- {path: seam corners, design: "tongue stops 1.4 short of each convex corner: plain butt joint there", state: "weak (issue 13)"}
- {path: belly step (z -8.9, x < 55), design: "0.35 key, no rebate", state: "weak + no cut line (issues 12, 13)"}
- {path: mic duct, design: "D1.0 bore + D1.0 VHB hole sealed onto the board F face round the D0.6 hole (VHB annulus is the seal); hex mesh seat", state: "duct sealed to the cavity by design; mesh part TBD. R-ACO-P6 keep-out (no via / F track within r 1.6 of the port, docs/sim/acoustics.yaml) HOLDS: F.Cu rule area r 1.6 on the board (place_r2 port_keepout), nearest F copper / via 1.87 mm (place_r2 --probe, 20bd842, 2026-10-07; was MDF_SDI 1.35 mm, issue 19 closed)"}
- {path: SW1 puck bore, design: "silicone skin bonded in the D4.6 recess; KMT022 itself IP68", state: "skin material TBD"}
- {path: dock window, design: "target glued in, back potted", state: "potting compound TBD"}
- {path: heel channel / arm, design: "RTV at the land opening and the exit (reg-arm)", state: "per reg-arm"}
- {path: test, design: none, state: TBD}
```

## Open issues (IDs stable; gaps = closed)
1. (closed in Phase 2) Spine top floating: unioned into the lid, lid prints as 1 valid solid (checks.json printable, 2026-10-07).
2. (closed in Phase 2) Board x location: x-stop 0.25 + gauge pin + VHB bond (checks.json duct with_gauge_pin PASS).
3. **Mic acoustic path (body side):** duct sealed and aligned; mesh product and the EQ notch (~63 kHz) open; Monte Carlo R14 all-pass 0.70 (ECR-0018 log 2026-10-07). Closes: sub-audio-in issues.
4. **Switch stack:** fixed puck pre-presses at worst case, so the kit is selective fit (PASS); lateral stack WARN in interfaces.py (0.20 worst vs 0.15 limit, 2026-10-07). KMT022 height tolerance unknown (C&K gives 0.65 nominal only). Closes: tighten lid/board position tolerance or accept, owner review; sub-ui.
5. **Sealing undesigned past the seam** (table above); `docs/research/sealing-and-service.md` (cited by O10) doesn't exist. Closes: sealing note + IPX4 spray test plan.
6. (closed 2026-10-07 in CAD; dry fit remains) **Heel wire-channel exit vs the cell's rear end.** Exit moved to x 66.20, Ø0.8 neck: hole 65.80–66.60, 0.20 behind the cell's rear plane, outer wall 0.60; tub outside the channel zone and the lid unchanged; shell_r2 rebuild valid, clashes 0, stowage 277 mm³ unchanged. The arm wires take the upper stowage (z 0..2.6), leaving the lower half for the dock/cell wires (issue 7). Remains: real-cell dry fit. Detail: [reg-arm](reg-arm.md) issue 1.
7. **Dock wire route** belly → rear pads undesigned: 5 wires in the 0.8 under-cell slack beside the flat tails; OD 0.8 won't lie flat, needs OD ≤ 0.6 or the rear-gap route (notes/shell_r2.md open items). Closes: [sub-dock-usb](sub-dock-usb.md).
8. (closed 2026-10-07, ECR-0001) **Stale frame sources.** frame.py's pod names and pod.py POD_L/W/H/ZC now come from the current design's dims (frame.pod_facts(); revg via ULTRASONIC_DESIGN); interfaces.py frame PASS 10/10 (revg too). blade.rail()/adapter() default to the body centre −2.45; shell_r1 pins −2.0. Pre-rev-1 values frozen in shell.py PRE_R1. Before/after CAD diff: shell_r2, shell_r1, heel_add/heel_cut, pad, dummies' bodies unchanged; modelled adapter slot −0.45 mm, dummies' default rail −0.45 mm (now = shell_r2's), Blade/styles concept bodies follow the r2 envelope (ECR-0001 log).
9. **No 3D render dump of r2** (section.png/plan.png only); STEP not exported. Closes: render dump (memory rule) after the owner review edits.
10. **Unknowns:** VHB 4914 thickness tolerance and normal tensile (TDS not read [A]); bond and peel cycles; pod mass now 11.2–13.2 g per side worn (pod body 8.7–10.1; `sim/checks/pod_mass.py` 2026-10-07; physical issue 8), CoM not computed (D18). Closes: TDS read + bench + CAD mass run.
11. (closed in Phase 2) Foam strips without a floor: no foam; the board hangs from the lid.
12. **Seam cut line:** rebate widened 2026-10-07 to 0.2 deep × 0.4 high (`shell_r2.REBATE_D/H`; was 0.3 high, below tolerances.md's 0.4 recess minimum); wall behind it 0.6 = resin min_wall; tub one valid solid, 1318.9 → 1317.4 mm³, no other check changed. **Remaining:** the belly step has no cut line, and the reopening procedure is undefined. Closes: mark the step; write the procedure (with issue 14).
13. **Butt joints at the seam corners and the belly step** (tongue stops 1.4 short of convex corners). Closes: corner sealant bead in the bond procedure or a corner key; spray test (issue 5).
14. **Service (O19, R24):** cell swap = cut the seam, lift lid + hanging board on its wires, desolder J5/J4 (J9), saw the cell VHB, reverse (board bond untouched). Arm swap = cut the seam, desolder J1/J2/J7/J8 on B, heel set screw. Board swap = warm 60-80 °C, saw the board VHB from the rear, accept a lid reprint (notes/shell_r2.md retention_options A). Closes: physical.md Service; cycle count the seam survives.
15. **SWD after the lid bond needs a peel:** TP1-TP6 face the lid (checks.json F_face_pads reachable_assembled false). Field recovery = ROM DFU via the dock (sub-debug-test). Closes: owner decision at review (accept, or TPs back on B).
16. **Gauge pin** (D0.98/D0.50 stepped, turned) not sourced; alternative = 2 NPTH + 2 lid pins (board change). Closes: source/turn one; else ECR.
17. **SW1 press loads the F VHB in tension** with no B back-stop (option A). Computed 2026-10-07 (`sim/checks/sw1_press_fem.py`, sub-ui issue 2): the load does not spread evenly (the old "2 N on 314 mm², >100× margin" was wrong); peak tension at the pocket edge is 12-52 kPa at 2 N = 1.6-7× under 3M's 85 kPa dynamic design factor (TDS 2024-09), 17-75× under the 900 kPa normal tensile; a 10 N jab reaches 59-261 kPa. Closes: coupon 600k presses + drop (MZD-7).
18. **[A] tolerances unverified:** JLC outline ±0.2 and NPTH ±0.05, resin ±0.05, KMT022 height (VHB thickness now sourced: 4914 0.25 ±15 % = ±0.0375, 3M TDS 2024-09, in `switch_stack()` since 2026-10-07); `docs/build/tolerances.md` has no Phase-2 rows. Closes: dated sources, then a tolerances.md Phase-2 section.

19. (closed 2026-10-07, 20bd842) R-ACO-P6 duct-seat keep-out: MDF_SDI re-routed; an F.Cu rule area r 1.6 now keeps every F track and via out (DRC-enforced); nearest 1.87 mm.

## Before you change this, check
- **Duct, SW1 pocket, lid/plate thickness:** board positions (mic (1.88, 6.0), SW1 (18.5, 6.0)) in **both** pods; duct length + acoustics scenario `phase2_r2` ([sub-audio-in](sub-audio-in.md)); puck kit + switch stack ([sub-ui](sub-ui.md)); `interfaces.py` [mic-port] [switch].
- **F gap / VHB:** F band 0.30, cut-outs for every F part (reads placement.yaml live), duct seal annulus; `interfaces.py` [clamp-bands] [heights].
- **Cavity, cell or B gap:** tallest B part (U2 1.08), cell fit, stowage volume, heel exit.
- **Belly, window:** [sub-dock-usb](sub-dock-usb.md); O12b; strut clearance (rear stays shallow).
- **Rear wall, strut relief, heel:** [reg-arm](reg-arm.md), stowage, cell rear end.
- **Seam or adhesive:** O10 (cut-openable), O16-6 (no screws), O19 (cell swap leaves the board bond intact).
- After any change: `systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 hw/mech/shell_r2.py` (checks.json), `python3 tools/checks/interfaces.py`, `python3 sim/acoustics/port.py` if the duct moved; walk `integration-map.md` §10; `python3 tools/plm.py impact file:hw/mech/dims_r2.py`.

## Reference design (Rev F/G)
`hw/mech/shell_r1.py` (env `ULTRASONIC_DESIGN=revg`), last changed 2026-10-01: seam at y 14.4 with a 0.5 lid lip round the main cavity only (butt joint round the belly); board 34 × 13 clamped by two lid ribs on 0.6 mm F edge bands over 1.5 mm foam strips with 0.1 mm of cell under each; open D1.0 lid bore over a 1.5 mm unsealed gap (no mesh, no duct); floating printed plunger Ø2.9 in a Ø3.2 bore over SW1 at board (22.0, 6.5); USB-C keep-out behind a 3.5 mm belly; spine top a separate floating solid; envelope 38.0 × 11.8 × 15.2, 7801 mm³; tub 1289 / lid 1023 / spine 160 mm³. Full text: git history of this file (before 2026-10-07).
