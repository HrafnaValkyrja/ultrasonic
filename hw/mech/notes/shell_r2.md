# shell_r2: Phase-2 pod shell (MZ-2), AI-facing

```yaml
id: MECH-SHELL-R2
date: 2026-10-03
status: draft, uncommitted, not owner-reviewed; ECR-0018 (Phase 2, owner O24/O25/O26)
src: hw/mech/shell_r2.py
run: "source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 hw/mech/shell_r2.py  (~5 s, exit 0)"
outputs: "hw/mech/out/r2/ (gitignored: hw/mech/out/) -> tub, lid, puck, puck_L0.73..0.93, pcb, vhb, cell, dock, parts_B, u2_mic, sw1, skin .stl; checks.json; parts.json; section.png; plan.png"
reuses: frame.py (Y_IN, heel datum E), blade.rail/prism_*, heel.heel_add/heel_cut (unchanged), styles.plate/slot, shell_r1.concept_spine (moved to the r2 top)
untouched: hw/mech/shell_r1.py, hw/pod/*
inputs:
  board: hw/pod/draft_r2/placement.yaml (30x12x0.8, R1 corners; all parts B except SW1 F at (18.5, 6.0); mic hole D0.6 at (1.98, 6.0); wire pads x 25-30)
  heights: tools/checks/part_heights.yaml (B max U2 1.08; SW1 0.65 nominal, no tolerance)
  stack: sim/checks/size_budget.py scenario MZ-2 (board_H 12, y_bgap 1.4, y_fgap 0.30, lid_wall 0.8, s_fixed 0.8, dock flat_tails)
  duct: docs/sim/acoustics.yaml options.B, R-ACO-P3..P6; spec O24(1)
  pocket: docs/research/mini/skeptic.md lid_pocket_tolerance (>= ~4.1 x 2.9), press_still_in_tension
  stowage_need: docs/research/miniaturization-prelim.md MZM-01.stowage (107-142 mm3 for 12 wires)

frame: {x: "29.5-67.5 (L 38.0)", y: "4.3 inner -> 14.0 body -> 14.7 plate (T 10.40)", z: "-9.7..4.8 (H 14.5), belly to -11.75 (2.05) for x < 55.0", note: "Z0, X0/X1, Y_IN kept from r1, so heel, rail, strut relief and NiTi clearances are geometrically unchanged"}
y_stack: {wall: 0.8, cell_vhb_gap: 0.3, cell: "5.4-10.7", B_gap: "10.7-12.1 (1.4)", board: "12.1-12.9", F_gap: "12.9-13.2 (0.30: VHB 4914 0.25 + 0.05)", lid: "13.2-14.0", plate: "14.0-14.7"}
z_stack: {cavity: "-8.9..4.0 (12.9)", cell: "-8.1..3.9 (0.8 under for dock tails, 0.1 over)", board: "-8.45..3.55 (0.45 free each long edge)", mic_and_SW1_axis_z: -2.45}
x_stack: {board: "30.55-60.55 (front 0.25 from the lid's front skirt wall)", mic_axis_x: 32.43, SW1_x: 49.05, rear_pads_x: "55.55-60.55", stowage: "60.55-66.7 behind the board + 65.6-66.7 behind the cell"}

decisions:
  D1_seam: "Seam at the board's B face (y 12.1); lid = shallow cap whose 1.1 mm skirt holds the board. Stepped round the belly: the whole belly (x < 55, z < -8.9) is tub, so the dock window (target centred y 9.15) lies in one part. r1's inner lid lip dropped: it would hit the board's long edges (board needs >= 12.0 of opening; r1's lip, inset 0.65 per side, leaves 11.6)."
  D2_seam_locator: "tub tongue 0.35 x 0.5 on the inner side of the wall, straight runs only, stopped 1.4 short of convex corners (1 mm chamfer leaves 0.42 wall there); lid groove +0.05. Belly-step key 0.35 x 0.35 (height capped: the hanging board's lower edge sweeps past it, 0.10 clear)."
  D3_board_retention: "full-face 3M VHB 4914 (0.25) on F, die-cut D1.0 at the mic, 4.3 x 3.1 at SW1 and one 1.8 mm square per F test pad TP1-TP6 (2026-10-07; a single box round all pads left only 31 %); ~314 mm2 = 91 % of the tape outline bonded. Nothing touches the long edges. See retention_options."
  D4_mic_duct: "O24 option B as built here: lid bore D1.0 (print undersize, ream 1.0) 0.7 long + VHB hole D1.0 0.3 -> board F face round the D0.6 hole. Duct 1.0 long total (r1 open gap gone). Hex window R1.9 x 0.8 deep from the plate top = mesh seat (as r1)."
  D5_duct_location: "the bore is the datum. Stepped gauge pin (D0.98 body / D0.50 tip, turned brass) through bore, VHB hole and board hole while the VHB grabs, then pulled. Front skirt wall = coarse x-stop at 0.25 gap; walls stay clear of the board in tolerance so they never fight the pin."
  D6_switch: "lid pocket 4.3 x 3.1, ceiling y 13.8 (0.25 over SW1 nominal); puck D2.3 (+ nub D1.0 x 0.10 on the actuator) in a D2.6 bore; silicone skin 0.25 in a D4.6 recess, flush with the plate. Puck is SELECTIVE-FIT: 5 printed lengths 0.73-0.93 step 0.05."
  D7_stowage: "rear zone only, as MZG-10: pads at board x 25-30 face B; wires fold up into 60.55-66.7. Arm wires arrive from heel CH_EXIT (66.20, 5.15, -5.50; D0.8, hole x 65.80-66.60, 2026-10-07) in the 1.1 rear gap behind the cell, climb it on the rear wall and take the UPPER stowage (z 0..2.6) to J1/J7/J2/J8 (heel.md last section)."
  D8_top: "r1 'spine' concept reused, moved -1.4 y / -0.7 z onto the r2 top; any r1 concept transfers the same way (not exported)."

checks:  # hw/mech/out/r2/checks.json, run 2026-10-03 ~00:40 local
  clashes: "PASS: 0.000 mm3 for tub/lid x {pcb, parts_B envelope at 1.08, u2_mic, sw1, cell, vhb, dock}, tub/lid, parts_B/cell, puck/lid, puck/sw1; F test pads read live from placement.yaml"
  corridors: "PASS: cell drop-in 0, lid+board drop-in 0 mm3"
  board_in_cavity: "PASS x 30.55-60.55 in 30.3-66.7; z -8.45..3.55 in -8.9..4.0"
  B_gap: "PASS 1.40 vs tallest B 1.08 -> margin 0.32"
  F_face_pads: "TP1-TP6 moved to F (placement.yaml, commit 952a3b5; place_r2.py F_ALLOWED 'bench access before the lid bond'). The shell reads F pads live; VHB gets a cut-out (pad D1.0 [A] + 0.4). Assembled, F faces the lid 0.30 away: pads are NOT reachable without peeling the board."
  duct_seat_R_ACO_P6: "PASS on hw/pod/draft_r2/out/routed.kicad_pcb (952a3b5, pcbnew read 2026-10-03 00:46): NPTH U2 D0.6 at (2.005, 6.025) from the bbox corner incl. 0.025 edge line = (1.98, 6.0); no via within 2.0 and no F track within 1.6 of the port. F now carries signal tracks (stack F sig/In1 GND/In2 +3V0/B sig): VHB sits on solder mask over 35 um copper - fine for the bond; the annulus seal relies on that P6 keep-out staying clear."
  F_gap: "PASS 0.30 vs VHB 0.25 -> 0.05 slack (VHB thickness tolerance assumed +-0.025 [A])"
  SW1_pocket: "PASS 4.3 x 3.1 >= 4.1 x 2.9 (pad span 3.8); ceiling clearance 0.25 nominal, 0.082 worst [A]"
  switch_stack: {fixed_puck: "FAIL worst case: gap -0.198..+0.287 (RSS -0.007..+0.197); -0.198 is past KMT0 min travel 0.05 -> switch held pressed", selective_fit: "PASS 0.005..0.135 (half step 0.025 + depth gauge 0.02 + puck caliper 0.02)", travel_src: "docs/system/sub-ui.md: 0.15 +-0.1 (C&K KMT0 p.B-9)"}
  duct_offset_R_ACO_P5: {limit: 0.20, nominal: 0.00, axis: "read from the routed board (U2 hole at x 1.88 since 2026-10-07)", walls_only: "FAIL 0.86 (0.25 stop gap + 0.45 free z + outline 0.2 [A] + print 0.05 [A], radial)", with_gauge_pin: "PASS 0.155 (bore 1.00-1.02 vs pin 0.98: 0.02; hole 0.52-0.73 JLC vs tip 0.50: 0.115; runout 0.02)", VHB_hole: "registered by the same pin: <= 0.03 off the bore (0.01 hole-pin + 0.02 pin-bore)"}
  stowage: "PASS 277 mm3 (198 behind board + 79 behind cell) vs need 107-142; prelim estimate for L30 was 276"
  envelope: "6211 mm3 vs size model MZ-2 6259 (live run = 6259): body 5720.9 = model 5721 exactly; plate 330.5 vs model 378.2 (r1 plate polygon re-proportioned: 472 vs 540 mm2); spine 159.6. Delta -48, all plate."
  print_volumes: {tub: 1321.5, lid_with_spine: 863.0, puck: 3.1}
  printable: "tub, lid, puck each 1 valid solid (checks.json printable)"

retention_options:  # owner decides (CLAUDE.md s0); O19 = serviceable for years
  A_full_face_VHB: {state: modelled, rec: YES, for: "0 mm height (fits the 0.30 F gap); it IS the duct seal (O24 needs the annulus anyway); spreads the press load over ~318 mm2; no edge or B-face keep-outs", against: "board removal = destructive peel (skeptic press_still_in_tension); press still loads the bond in tension (2 N on ~318 mm2; VHB normal tensile ~0.5 MPa class [A, verify 3M 4914 TDS] -> >100x margin)", O19: "cell swap (the frequent service) never touches the bond: lift lid, board rides on it. Board swap = warm 60-80 C, saw with floss/0.1 shim from the rear end (no parts on F), accept a lid reprint (863 mm3, ~1 g resin)."}
  B_two_end_clips: {state: not modelled, rec: no, for: "unclip = no peel", against: "needs ~0.8 mm part-free B strips at both short ends: rear has wire pads J1/J5/J7/J9/J10 at board x 28.9 (strip only ~0.6) and the wires leave there; front U2 at 1.43, TP6 at 1.35. Mic needs a separate compressed gasket whose preload creeps in resin (R-ACO-P5 then also loses the pin datum). Press load goes into 0.3-0.5 mm resin hooks."}
  C_VHB_zones: {state: not modelled, rec: "fallback if the owner weights O19 higher", what: "VHB only as a D3.0 annulus at the mic + two 4 x 10 pads at the ends (~35 % of the face)", for: "seal kept, peel ~1/3 of A", against: "board unsupported under SW1 (22 mm between the end pads): press bends the board into the B gap (0.32 margin over U2) unless a B-side back-stop post is added (needs a K_B keep-out, area_model 7.8 mm2) -> board change"}

assembly_sequence:  # owner builds by hand
  1: "print tub, lid, 5 pucks; ream lid bore D1.0; measure every puck (calipers), mark lengths"
  2: "solder all 12 wires to the rear B pads with the board out of the shell"
  3: "VHB 4914 die-cut (D1.0 hole, 4.3 x 3.1 window) onto the lid inner face, gauge pin through bore + VHB hole"
  4: "board onto the pin tip through its D0.6 hole, F face down onto the VHB; press through a foam pad over the B parts (3M: ~0.1 MPa -> ~30 N over the board [A]), pull the pin"
  5: "depth gauge from the skin-recess floor to the SW1 top through the D2.6 bore; pick the puck leaving 0.05-0.10; drop it in; bond the skin"
  6: "cell into the tub on its VHB (0.3 gap); dock target into the belly window; tails flat under the cell (0.8 slack)"
  7: "route dock + cell wires along the cell bottom to the 1.1 rear gap, up into the LOWER stowage; arm wires (fished and soldered before the bond, heel.md last section) climb the gap on the rear wall into the UPPER stowage"
  8: "lower lid + hanging board onto the tongue; tape for testing; bond the seam at freeze"

open_items:
  - "[A] tolerances to verify with dated sources before freeze: JLC routed outline +-0.2 and NPTH +-0.05 (capabilities page); 3M VHB 4914 thickness tol and normal tensile (TDS); resin print +-0.05 (frame.RESIN); KMT022 height tolerance (C&K gives 0.65 nominal only)"
  - "SWD after assembly: with TP1-TP6 on F and the board bonded F-to-lid, re-flashing needs a peel (option A) or unclipping (B). Needs a decision: SWD over dock/wire pads, a bootloader path, or TPs back on B (commit 36550e2 / MZD-10: lifting the lid shows B, because the board stays on the lid B-side out; F is never visible). Lead/owner."
  - "gauge pin: source or turn a D0.98/D0.50 stepped pin; alternative = 2 NPTH locating holes on the board centre line + 2 lid pins (board change, hw/pod owner = lead)"
  - "acoustics re-run with the r2 duct (bore 0.7 + VHB 0.3 = 1.0 long, window 0.8): MZV-05; duct modes move vs the 2.6 mm assumed in the prelim"
  - "dock wire route under the cell: 0.8 slack zone; 5 dock wires at OD 0.8 [prelim assumption] will not lie flat beside the tails -> wire OD <= 0.6 or route via the rear gap only; not modelled"
  - "belly step seam (z -8.9, x < 55) has no outer cut-line rebate; reopening procedure for the step to define"
  - "SW1 press puts the F-face VHB in tension; no B back-stop under SW1 in option A (bond is the support); coupon: 600k presses + drop (MZD-7)"
  - "right pod = mirror shell; board +y maps to -z there; mic/SW1 on the centre line so no shell change, rear pads unaffected"
  - "tools/checks/interfaces.py and part_heights.yaml still reference shell_r1 bands (PARTS, clamp-bands); r2 needs its own band (B 10.7-12.1 minus margin, F = SW1 only) - lead / checker owner"
  - "docs/system (reg-pod-body, sub-ui, sub-audio-in, physical) and tools/plm.py impact/status not updated (lead commits)"
  - "no 3D render dump yet (memory rule render-dump-after-design-changes); section.png only"
```

![section](../out/r2/section.png)
![plan](../out/r2/plan.png)
