# Physical integration: frame, stack-up, sealing, assembly
Rev MZ-2 2026-10-07: body rewritten to the Phase-2 build (`hw/current.yaml`, ECR-0018): one-face 30 × 12 board hung from the lid on per-pad-cut VHB, seam at the board's B face, sealed D1.0 duct + gauge pin, SW1 pocket + puck, B-face rear wire pads + stowage zone; Rev F/G stack moved to the reference section.
Status: Phase-2 shell `hw/mech/shell_r2.py` / `dims_r2.py` (checks.json all clashes 0, rebuilt for c348661 2026-10-07) + routed board `hw/pod/draft_r2/out/routed.kicad_pcb` (DRC 0, 0 unconnected, 2026-10-07). Not printed, not built; owner review pending (O25). Updated 2026-10-07. · Source of truth: `hw/mech/dims_r2.py` (Phase-2 numbers), `hw/mech/notes/shell_r2.md` (decisions, assembly sequence), `hw/mech/frame.py` (axes, arm, pad, fasteners), `hw/mech/pod.py` + `hw/mech/blade.py` (rail, catch, adapter), `hw/mech/heel.py`, `hw/mech/pad.py`, `hw/pod/draft_r2/placement.yaml` + routed board, `docs/build/tolerances.md` (Rev-1 fits) · Owner decisions: O9, O10, O11, O12(b), O16(5)(6), O17, O19, O24, O25/O26, O27 · ECR-0001 (frame constants) implemented 2026-10-07, awaiting owner review · Open ECRs: ECR-0006 (weighted dummy pair; R20, R24), ECR-0018 (Phase 2)


> 2026-10-07 (round 10, packet Q1): dims_r2.py / heel.py / dock_route.py / shell_r2.py / blade.py now take a NON-DEFAULT variant (ULTRASONIC_DESIGN=k1|k1p via hw/current.yaml blocks + hw/mech/dims.py). Phase-2 values are byte-identical (74-name dims snapshot; shell, heel, dock_route, board_in_pod, mass and interfaces outputs unchanged apart from new info fields). K1 facts: reg-pod-body.md Variants.


> 2026-10-07 round 11 (NON-DEFAULT, packet Q1/Q2): K1 duct options (K1_DUCT, sim/acoustics/duct_options.py), k1t (walls/lid 0.6), 0.6 wall coupon (hw/mech/coupon_wall06.py). Phase 2 unchanged (dims snapshot: only new names REAR_GAP; shell checks add info fields puck_feasible / puck_guide_bore / pocket_breaks_outer_face). Facts: reg-pod-body.md Variants.


> 2026-10-07 round 12 (NON-DEFAULT, packet Q2): K1-thin button concepts (sim/checks/button_concepts.py, K1_BUTTON=dome in dims_k1). Recommended: Phi4 metal dome on new F pads (board F-copper edit only); fallback: skin 0.20 proud over KMT022 (no board change). Phase 2 unchanged (dims snapshot identical; shell adds info field trace_groove).

## Purpose
Keeps every region (pod body, board, cell, arm, pad) in one coordinate frame, so a change in one can be checked against the others: what sits where, what touches what, how water gets in, and in what order it all goes together. It carries no F-row of its own; it is the mechanical counterpart of every F-row in [integration-map.md](integration-map.md) §1 and the keep-outs in §7.

## Big picture
- Section + plan (build outputs of `shell_r2.py`, gitignored): `hw/mech/out/r2/section.png`, `hw/mech/out/r2/plan.png`. `docs/diagrams/system-overview-physical.png` still draws Rev F (issue 11).
- The cell lies on VHB against the pod's inner wall. **The board hangs from the lid** on full-face VHB (F face up against the lid, every part except SW1 on B facing the cell across a 1.4 mm gap). Nothing touches the board's long edges; nothing is screwed (O16-6).
- Mic: U2 on B, its port through the board at board (1.88, 6.0), then a sealed D1.0 duct (VHB hole + reamed lid bore) to a hex mesh seat in the plate.
- SW1 alone on F, in a 4.3 × 3.1 lid pocket; a selective-fit printed puck carries the press from a silicone skin.
- The NiTi arm leaves a heel under the rear of the pod. Four arm wires, five dock wires and the cell leads (12 wires on 11 pads) land on **B-face** pads at the board's rear (board x 25-29) and fold into the stowage zone behind the board.
- The dock target sits flush in the belly, which is entirely tub.

## Coordinate frame
| Item | Convention | Source (2026-10-07) |
|---|---|---|
| Pod axes | x rearward from the glasses hinge along the temple; y outward (away from the head); z up; mm | `frame.py` L8-9 |
| Origin | y = 0 at the temple arm's inner face (head side) | `frame.py` L9 |
| Handedness | CAD = one pod, the other its mirror image. `pcb-mech-interface.md` §1 says the CAD is the RIGHT pod; `dims_r2.bpt` docstring and `notes/shell_r2.md` say "right pod = mirror shell": **conflict** (issue 5) | as cited |
| Board ↔ pod, x | pod x = 30.55 + board x (board x 0 = front edge, mic end), both pods | `dims_r2.py` PCB, bpt |
| Board ↔ pod, y | B face (parts, cell side) at y 12.1, F face (lid side) at 12.9 | `dims_r2.py` Y_B, Y_F |
| Board ↔ pod, z, CAD pod | pod z = board y − 8.45 (KiCad top edge y 0 at the bottom) | `dims_r2.bpt` |
| Board ↔ pod, z, mirror pod | pod z = 3.55 − board y **[derived]** | mirror of the row above |
| Board centre line | board y 6.0 = pod z −2.45 in both pods: mic port and SW1 sit on it, so one board fits both (O16-5) | `dims_r2.py` MIC, SW |

**Note on the mirror.** Same board, F toward the lid, mic end forward in both pods; seen from outside, one pod shows KiCad's top view, the other that view rotated 180°. Anything off the centre line (TP pads, U3, L1, the J-pad order) lands at a different height in each pod. The mic and SW1 are on the line, so the shell needs no per-pod change; the rear pads stay in the stowage zone either way (`notes/shell_r2.md` open items).

**Which numbers are live.** For Phase 2 trust `dims_r2.py` (CAD-free; read by `shell_r2.py`, `tools/checks/interfaces.py`, `sim/acoustics/geometry.py`). Since ECR-0001 (2026-10-07) `frame.py`'s pod names (X0, X1, Z0, Z1, ZC, Y_OUT, Y_SPLIT, WALL, TAPE, CAV, CELL, PCB, MIC_PORT, BUTTON) are not stored there: `frame.pod_facts()` reads them from the selected design's shell dims (`hw/current.yaml` `shell_dims`; env `ULTRASONIC_DESIGN=revg` gives shell_r1's). `pod.py` POD_L/W/H/ZC follow them (Phase 2: 38.0 × 9.7 × 14.5, centre −2.45), so `blade.rail()`/`blade.adapter()` now default to the body centre; `shell_r1.py` pins its as-built −2.0 (RAIL_ZC). interfaces.py [frame] PASS 10/10. The pre-rev-1 pod (PCB 20 × 11.5, LP401230 + PCM, KXT321, lid screws, mic chimney) lives only in `shell.py` PRE_R1 (historical). `heel.py` and `pad.py` keep axes, arm and pad from `frame.py` (unchanged: heel and pad solids have identical volume, bounding box and centroid before and after); heel's checks now see the real cell and board.

### Key positions (pod mm, Phase 2; CAD pod for z)
| Feature | x | y | z | Source (2026-10-07) |
|---|---|---|---|---|
| Pod body | 29.5-67.5 | 4.3-14.0 (+0.7 plate to 14.7) | −9.7-4.8 | dims_r2 X0/X1, Y_OUT/Y_TOP, Z0/Z1 |
| Belly (dock bay, all tub) | 29.5-55.0 | 4.3-14.0 | −11.75-(−9.7) | dims_r2 X_BELLY, Z_BELLY |
| Cavity / bay | 30.3-66.7 / 30.3-54.2 | 5.1-13.2 | −8.9-4.0 / −10.95-(−8.9) | dims_r2 CAV, BAY |
| Cell | 30.6-65.6 | 5.4-10.7 | −8.1-3.9 | dims_r2 CELL |
| Board 30 × 12 × 0.8 | 30.55-60.55 | 12.1-12.9 | −8.45-3.55 | dims_r2 PCB; checks.json board_in_cavity |
| Board VHB (0.25) | 30.75-60.35 | 12.95-13.2 | −8.25-3.35 | dims_r2 vhb (inset 0.2) |
| Mic port NPTH D0.6 = duct axis | 32.43 | 12.1-14.7 | −2.45 | dims_r2 MIC (read from routed board U2 (2.65, 6.0) r90, hole at local −0.77) |
| Lid duct bore D1.0 (reamed) + hex window R1.9 × 0.8 | 32.43 | 13.2-13.9 / 13.9-14.7 | −2.45 | shell_r2.lid_base |
| SW1 / pocket / puck / skin | 49.05 | 12.9-13.55 / to 13.8 / 13.65-14.38 / 14.45-14.7 | −2.45 | dims_r2 SW, POCKET, PUCK_L, SKIN_FLOOR |
| TP1-TP6 (F, in VHB cut-outs) | TP5 32.15, TP2 33.65, TP4 35.15, TP1 36.65 (z 2.85; TP2/TP4 swapped 2026-10-07, DBG-2); TP3 39.85 (z −5.55); TP6 54.55 (z 2.45) | 12.9 | see x | placement.yaml via dims_r2 F_PADS + bpt [derived] |
| Rear wire pads (B), board x 25.1-28.9 | 55.65-59.45 | 12.1 | J1 1.45, J2 2.5, J7 −0.75, J8 0.3 (CAD pod) | routed board probe 2026-10-07 + bpt [derived] |
| Stowage zone | 60.55-66.7 (+ 65.6-66.7 behind the cell) | 10.7-13.2 (+ 5.1-10.7 behind the cell) | −8.9-4.0 | shell_r2.stowage_zone |
| Dock target | 31.5-52.7 | 5.72-12.58 | −11.75-(−8.95) | dims_r2 DOCK |
| Heel (keel + boss, as built) | 55.06-67.3 | 0.3-5.0 | −10.05…−3.78 | heel checks.json `heel_bbox` (unchanged) |
| NiTi socket mouth E | 61.3 | 2.0 | −8.3 | `frame.py` E |
| Heel wire exit into the pod (Ø0.8 neck) | 66.20 | 5.15 | −5.50 | `heel.py` CH_EXIT (2026-10-07) |
| Pad contact centre (on the skin) | 70.6 | −3.0 | −25.0 | `frame.py` PAD_CONTACT |

## Stack-up through the pod (y, at the board)
| y (mm) | Thick | Layer | Source (2026-10-07) |
|---|---|---|---|
| 0-2.5 | 2.5 | a · temple arm (glasses) | `frame.py` L23 |
| 2.5-4.3 | 1.8 | b · frame adapter (separate print; dovetail + snap tab) | `frame.py` L24, L27; `blade.py` |
| 4.3-5.1 | 0.8 | c · tub inner wall | dims_r2 W |
| 5.1-5.4 | 0.3 | d · 3M VHB 4914 0.25 in a 0.3 gap (cell to wall) | dims_r2 TAPE |
| 5.4-10.7 | 5.3 | e · cell | dims_r2 CELL_T |
| 10.7-12.1 | 1.4 | f · B gap: every part except SW1 (tallest U2 1.08, margin 0.32); rear wire-pad joints and wire ends | dims_r2 B_GAP; interfaces.py [heights] PASS |
| 12.1 | – | seam (tub \| lid) = board B face; tongue 0.35 × 0.5 up into the lid groove | dims_r2 Y_SPLIT, TONGUE_* |
| 12.1-12.9 | 0.8 | g · PCB 4 layers: F sig / In1 GND plane / In2 +3V0 plane / B sig | routed board (4 Cu, 0.8) |
| 12.9-13.2 | 0.30 | h · F gap: VHB 4914 0.25 + 0.05 slack; SW1 0.65 rises into its pocket (to 13.8) | dims_r2 F_GAP, VHB_T, POCKET |
| 13.2-14.0 | 0.8 | i · lid face | dims_r2 LID_T |
| 14.0-14.7 | 0.7 | j · armour plate (spine top above) | dims_r2 PLATE_T |

Total T 10.4 (Rev F 11.8; O27 thin first). The heel sits under the temple and adapter (z ≤ −3.78) at y 0.3-5.0; the pad's contact face is at y −3.0, below the temple.

## Clearances (Rev-1 list: [tolerances.md](../build/tolerances.md); its Phase-2 rows are open, issue 18)
| Fit | Value | Verdict | Source (2026-10-07) |
|---|---|---|---|
| Board ↔ front skirt wall (x-stop) | 0.25 | coarse stop; never touches within tolerance | dims_r2 X_STOP_GAP; checks.json |
| Board long edges ↔ cavity | 0.45 each | free (nothing clamps the edges) | checks.json side_gap_z |
| Board rear edge ↔ rear wall | 6.15 | stowage zone | checks.json stowage zone_len_x |
| B parts ↔ cell | 1.4 − 1.08 = 0.32 | OK | checks.json B_gap |
| F face ↔ lid | 0.30 for VHB 0.25 | 0.05 slack nominal, 0.0125 at the thickest tape (VHB 4914 ±15 % = ±0.0375, 3M TDS 2024-09) | checks.json F_gap |
| SW1 ↔ pocket ceiling | 0.25 nominal, 0.082 worst | OK | dims_r2.switch_stack |
| Puck top ↔ skin underside | selective fit 0.005-0.135 (fixed puck worst −0.198 = pre-pressed) | OK with the kit | dims_r2.switch_stack |
| Duct axis ↔ board hole | 0.000 nominal; 0.155 worst with the gauge pin; 0.86 walls-only | PASS with pin (limit 0.20) | dims_r2.duct_offsets |
| Cell ↔ tub | 0.3 tape side; 0.1 top; 0.8 bottom (dock tails); 1.1 rear; ~0.07 at the strut-relief fill | tight: dry-fit | dims_r2 CAV/CELL; tolerances L16 |
| Dock target top ↔ cell bottom | 0.85 (z −8.95 → −8.1) for flat tails + wires | tight (issue 3) | dims_r2 DOCK, CELL |
| Lid groove ↔ tub tongue | 0.05 | – | dims_r2 GROOVE_CL |
| Belly-step key ↔ hanging board lower edge | 0.10 as the lid comes down | OK | notes/shell_r2.md D2 |
| Strut ↔ housing | 1.18-1.34 in all 4 arm states (target 1.4) | accepted (relief unchanged from r1) | tolerances L36 |
| Seam cut line | 0.2 × 0.4 tub-only rebate (wall 0.6 behind it); belly step none | OK (= 0.4 resin recess min); step open | shell_r2.seam_rebate (2026-10-07) |

## Sealing paths (target IPX4 min, IPX5 preferred: O12(b))
| Path | Phase-2 design | Test build | Final build | State |
|---|---|---|---|---|
| Seam, straight runs | tongue/groove + bond line | taped | MS-polymer or neutral RTV (TBD) | designed, untested |
| Seam, corners + belly step | butt joint (tongue stops 1.4 short of corners); 0.35 key on the step | taped | bonded | **weak** (reg-pod-body issue 13) |
| Mic | board hole D0.6 → VHB hole D1.0 (tape annulus seals onto the F mask) → reamed bore D1.0 → hex mesh seat | – | mesh part TBD | duct sealed by design; R-ACO-P6 keep-out holds (nearest F copper / via 1.87 mm, rule area on the board, 2026-10-07) |
| SW1 | puck in D2.6 bore; skin in D4.6 recess; KMT022 IP68 | TBD | bonded silicone skin (TBD) | partly designed |
| Dock window | target glued in, back potted | TBD | same | designed |
| Arm entry | heel channel D1.0 through the tub's inner wall; blind NiTi sockets | RTV at land opening and exit | same | designed (reg-arm) |

No sealing path has been tested; `sealing-and-service.md` (cited in O10) doesn't exist.

## Assembly order (Phase 2; O10 two-stage, O16-6 no screws in the housing)
Sequence from `hw/mech/notes/shell_r2.md` assembly_sequence (2026-10-07), merged with the unchanged arm/pad steps. Screws only where O16(6) allows: M1.2 cup screw, two M1.4 NiTi set screws.

| # | Step | Test build | Final build | Source |
|---|---|---|---|---|
| 0 | Print tub, lid, the 5-puck kit and a tolerance coupon; wash, cure; ream the lid bore D1.0 and the NiTi sockets Ø0.85; measure every puck (calipers) and mark its length | same | same | notes/shell_r2.md step 1; tolerances L7 |
| 1 | Flash and bench-test the bare board: pogo/probe on TP1-TP6 (F, bare 0.7 pads), power on J5/J4; meter the J-pad neighbours (wire-pad gaps ≥ 0.8 by rule, MZD-10) | same | same | sub-debug-test bring-up; ECR-0018 MZD-10 |
| 2 | Pad: wires through the cap; pad board; exciter; contact; M1.2 screw; cast the LED ring (24 h) | same | same | `pad.md` (route text stale, reg-arm issue 7) |
| 3 | Slide a pre-shrunk tube (≤ 1.1 OD, ~5 mm) onto the bundle's free ends; never heat it on the arm | same | same | reg-arm issue 12 |
| 4 | Heel end: fish the 4 conductors through the heel channel into the pod; seat the tube ends in both Ø1.6 counterbores; NiTi into the heel socket; nut + M1.4 × 3 set screw | same | same | `heel.md` steps 3-6 |
| 5 | Pad end after the heel end: NiTi into the strut socket; M1.4 × 2 set screw; RTV at the land opening and exit | same | same | `heel.md` L250-251 |
| 6 | Solder all 12 wires (arm 4, dock 5, cell 2, NTC 1 optional) to the rear **B** pads with the board out of the shell; cell lead (J5) last; meter neighbours | same | same | notes/shell_r2.md step 2 |
| 7 | VHB 4914 die-cut (D1.0 duct hole, 4.3 × 3.1 SW1 window, 1.8 mm squares at TP1-TP6) onto the lid inner face; gauge pin through bore + VHB hole | VHB as final (the board bond is the retention) | same | notes/shell_r2.md step 3; shell_r2.vhb |
| 8 | **Gate (DBG-16): only after bring-up step 6 passed on this board** (boot stub written and write-protected, ROM DFU entered and a full image flashed over the dock, sub-debug-test). Then: board onto the pin tip through its D0.6 hole, F face down onto the VHB; press through a foam pad over the B parts (~30 N [A]); pull the pin. **TP1-TP6 are now unreachable** | same | same | notes/shell_r2.md step 4; sub-debug-test DBG-16 |
| 9 | **Puck fit (selective, UI-1):** (a) depth-gauge from the skin-recess floor to SW1's top through the D2.6 bore, 3 readings, ±0.02; (b) puck length = depth − 0.07 (PRE_GAP); pick the kit puck (0.73/0.78/0.83/0.88/0.93, each measured in step 0) nearest without going over; residual must be 0.005-0.135 (`switch_stack()`); (c) drop it in, lay the skin on **unbonded**, press 10×: one click per press, no click from laying the skin on, release returns; (d) a click at rest = too long, take the next shorter; no click on a firm press = too short, next longer; (e) bond the skin, repeat (c); mesh into the hex seat. Firmware flags a button held > 10 s as stuck (sub-ui issue 1) | skin/mesh fixing TBD | bonded | notes/shell_r2.md step 5; dims_r2.switch_stack |
| 10 | Cell into the tub on its VHB (0.3 gap); optional NTC taped on (then RT1 not fitted); dock target into the belly window, tails flat under the cell | same | target glued, back potted | notes/shell_r2.md step 6 |
| 11 | Route the dock ribbon per `hw/mech/dock_route.py` v2: flat under the cell (tails side), up the rear gap in y while LOW, over the cell's rear-top edge, then up in z against the lid side (y ~12.5) behind the board, down to each pad at its own height. **Hold:** Kapton tape across the ribbon on the cell bottom and on the cell's rear face, one RTV dot where it turns over the rear-top edge (enamel must not rub that edge [A]). **Check before the lid closes:** in the left pod the ribbon must pass ABOVE (lid side of) the arm bundle, never between bundle and cell; lower the lid once dry and look through the open seam that nothing is pinched. Cell leads + NTC wait on the cell lead exit (issue 10); arm wires from the heel exit as in heel.md | same | same | dock_route.py v2 (≥ 0.58 to the arm bundle); notes/shell_r2.md step 7 |
| 12 | Lower lid + hanging board onto the tongue (board drop-in corridor clear, checks.json); wires fold behind the board | tape round the seam | bond the seam | notes/shell_r2.md step 8 |
| 13 | Slide the pod onto the frame adapter (dovetail, snap tab) | same | same | `blade.py` |
| 14 | Check: one click per press, none with the lid just closed; charge on the dock; LED; pad force (T5) | same | same | `pad.md` step 11 |

**Reopening.** Test build: peel the seam tape; the lid lifts the board on its wires. Final build: firmware over the dock (USB DFU, O12a); cut along the tub rebate to open. SWD needs the board peeled off the lid (reg-pod-body issue 15).

## Service (O19)
| Job | Sequence | Cut-and-rebond cycles | Board bond |
|---|---|---|---|
| Cell swap | cut the seam → lift lid + hanging board → desolder J5/J4 (J9) → saw the cell VHB with floss (never pry a pouch) → new cell on new VHB → reverse | 1 | untouched |
| Arm swap (R24) | cut the seam → lift lid + board → desolder J1/J2/J7/J8 (B, rear) → release the heel set screw → draw the bundle out → new arm per steps 2-5 → rebond | 1 | untouched |
| Board swap / SWD on a bricked board | as cell swap, then warm 60-80 °C and saw the board VHB from the rear (no parts on F except SW1); accept a lid reprint (~1 g resin) | 1 | destroyed |
| Firmware | dock, USB DFU | 0 | – |

Wire slack for lifting the lid with the board on its wires (DBG-17, computed 2026-10-07): lid opened 180° about the rear seam edge. Arm wires need 2.65 (right) / 3.04 mm (left) extra: the 5 mm service loop in heel.md covers it. Dock ribbon, anchored at the cell's rear-top edge (step 11): 0.0 mm extra in the worst case (right J3), others −0.1 to −4.6, so the routed length already suffices; cut each dock wire 2 mm long as a loop so the lid never tensions a pad (`hw/mech/dock_route.py` lid_open_extra_mm). Tools: fine blade for the rebate, floss for the cell VHB, hot-air 60-80 °C only for a board swap. Cycle count the seam survives: unknown until the spray coupon is opened and rebonded 3× (sealing-and-service.md test plan).

## Interfaces between regions
| # | Between (docs) | What crosses | Geometry | Nets / F-rows |
|---|---|---|---|---|
| 1 | [reg-board](reg-board.md) ↔ [reg-pod-body](reg-pod-body.md) ↔ air ([sub-audio-in](sub-audio-in.md)) | sound | U2 on B; NPTH D0.6 at board (1.88, 6.0) = pod 32.43; VHB hole D1.0 + reamed bore D1.0 (1.0 long) + hex mesh seat; gauge pin at bonding | F1 |
| 2 | [reg-pod-body](reg-pod-body.md) ↔ [reg-board](reg-board.md) ([sub-ui](sub-ui.md)) | finger force | skin → puck D2.3 (selective fit) → SW1 at board (18.5, 6.0) = pod 49.05; press loads the VHB in tension | F11: BTN → PA0 |
| 3 | [reg-pad](reg-pad.md) ↔ [reg-arm](reg-arm.md) ↔ [reg-pod-body](reg-pod-body.md) ↔ [reg-board](reg-board.md) ([sub-output](sub-output.md), [sub-ui](sub-ui.md)) | 4 litz wires | strut bore Ø1.2 → tube → heel Ø1.0 → exit Ø0.8 (66.20, 5.15, −5.50) → 1.1 gap behind the cell (on the rear wall) → upper stowage → B pads J1/J2 (board 28.9/27.0) and J7/J8 | F3: OUT_A/OUT_B → J1/J2 · F12: LED_A/LED_K → J7/J8 |
| 4 | [reg-pod-body](reg-pod-body.md) (heel) ↔ [reg-arm](reg-arm.md) ↔ [reg-pad](reg-pad.md) | spring force (≥ 1 N) | NiTi Ø0.80; sockets 4.0 / 3.5 deep; M1.4 set screws (unchanged) | – |
| 5 | [sub-dock-usb](sub-dock-usb.md) ↔ [reg-pod-body](reg-pod-body.md) ↔ [reg-board](reg-board.md) | charge + USB | YZT0675 flush in the belly; 5 enamelled wires (32/36 AWG, DK-16) flat under the cell (0.8), up the rear gap low, over the cell's rear-top edge, up behind the board, to J3/J4/J10/J11/J12 (B, board x 25.1-28.9); both pods routed (`hw/mech/dock_route.py` v2) | F5, F9, F10, F15 |
| 6 | [sub-power](sub-power.md) (cell) ↔ [reg-board](reg-board.md) | battery | leads to J5 (28.9, 1.1) / J4 (27.0, 1.9); optional NTC to J9 (28.9, 3.3) | F5-F8 |
| 7 | [reg-pod-body](reg-pod-body.md) ↔ [reg-board](reg-board.md) | retention | full-face VHB on F (91 % bonded), x-stop 0.25, long edges free 0.45 | – |
| 8 | [reg-pod-body](reg-pod-body.md) (tub ↔ lid) | seal + access | seam y 12.1, tongue/groove, belly all tub, rebate tub-only | – |
| 9 | [reg-pod-body](reg-pod-body.md) ↔ glasses | mounting | `blade.py` dovetail + snap tab, centred on pod.POD_ZC = body centre −2.45 (ECR-0001) | §1.2.1 |
| 10 | [reg-pad](reg-pad.md) ↔ skin | vibration + preload | contact face at (70.6, −3.0, −25.0), pressing −y | D1 |
| 11 | [reg-board](reg-board.md) ↔ [reg-pod-body](reg-pod-body.md) ([sub-debug-test](sub-debug-test.md)) | test access | TP1-TP6 on F under VHB cut-outs: bench only, before step 8 | F14 |

## Constraints
- §1.2 (locked): clip-on clasps, Ear (open) untouched, comfort first.
- §8: nothing forward of ~18 mm behind the pupil plane (pod front x 29.5 until E10); acoustic rules: board ≤ 0.8, short wide port, no gasket cavity, thin mesh, never foam.
- D18 balance (cell along the arm in front of the ear). O27 thin > short > long.
- O19 serviceability (cell swap must not destroy the board bond); R20/R24 via ECR-0006.
- O10/O16(6): no housing screws, final build bonded and cut-openable. O16(5): mic and switch on the board centre line. O24: sealed duct + locating.
- O12(b) IPX4 min. O11 printed strut, Sugru contact. O17 Spine top; arm wiring never pinched.
- Resin: holes < ~0.8 may close, recesses < 0.4 may fuse; ream critical holes.

## Key numbers
```yaml
- {q: pod envelope, v: "38.0 x 10.4 (y 4.3-14.7) x 14.5 (z -9.7..4.8), + belly 2.05 under x < 55, + spine; 6211 mm3 (Rev F 7801)", src: "dims_r2.py; checks.json envelope 2026-10-07"}
- {q: board-to-lid gap at the mic, v: "0.30 (VHB 0.25), duct 1.0 long total (bore 0.7 + VHB-gap 0.3)", src: "dims_r2 F_GAP; notes/shell_r2.md D4"}
- {q: part height per face, v: "B <= 1.4 (tallest U2 1.08); F = SW1 0.65 in a 0.90 pocket band; other F copper only", src: "interfaces.py heights PASS 2026-10-07"}
- {q: stowage, v: "277 mm3 (198 behind board + 79 behind cell) vs need 107-142 for 12 loops", src: "checks.json stowage"}
- {q: VHB bonded, v: "~314 mm2 = 91 % of the tape outline", src: "interfaces.py clamp-bands; checks.json vhb_area_mm2 313.9"}
- {q: pad contact below the temple centre, v: "z -25.0 (skin at y -3.0)", src: "frame.py PAD_CONTACT"}
- {q: mass per side worn, v: "11.2-13.2 g (pod body 8.7-10.1) vs ~8 g target", src: "sim/checks/pod_mass.py 2026-10-07 (issue 8)"}
- {q: mass per side worn, K4 variant (ULTRASONIC_DESIGN=k4), v: "9.05-10.15 g, CoM 36 mm behind hinge, nose 5.8-6.5 / ear 3.2-3.7 g (K1 same method: 10.08-12.04, CoM 28, 7.3-8.7 / 2.8-3.4)", src: "sim/checks/pod_mass.py 2026-10-08, sim/out/mech/pod_mass_k4.json"}
```

## Open issues (IDs stable; gaps = closed)
1. (closed in Phase 2) Mic port unsealed: sealed D1.0 duct (O24); 1b board port vs lid bore: nominal 0.000, gauge pin worst 0.155 (dims_r2.duct_offsets, 2026-10-07). R-ACO-P6 keep-out holds since 2026-10-07 (reg-pod-body issue 19 closed).
2. (closed 2026-10-07 in CAD) **Heel wire exit vs the cell.** Exit moved to x 66.20 with a Ø0.8 neck (hole 65.80-66.60, 0.20 behind the cell end 65.6, rim-corner 0.36); arm wires 0.39 from the cell; build order in notes/heel.md. Remains: dry fit with the real pouch ([reg-arm](reg-arm.md) issue 1).
3. **Dock wire route not designed.** 5 wires from the belly to the B pads at board x 25-29: 0.8 under the cell beside the flat tails (0.85 tail-to-cell) or the rear gap; OD ≤ 0.6 needed under the cell (notes/shell_r2.md). Wire picked 2026-10-07 (sub-dock-usb DK-16): 32 AWG VBUS/GND + 36 AWG D+/D−/CC enamelled, flat bundle 0.98 × 0.25 mm: fits the 0.8 under-cell slack (≥ 0.48 left) or the 1.1 rear gap. Route: routed 2026-10-07 in BOTH pods (`hw/mech/dock_route.py`, out/dock_route.json, plot sim/out/mech/dock_route.png): tails' end [A x 52.9] → flat ribbon under the cell (z −8.5) → cell-side half of the 1.1 rear gap (x 65.85; the arm bundle keeps the wall side) → climb to each pad's z → up to y 11.55 → under the board's rear edge → pad. Right pod: dock pads low (z −6.75..−1.9), arm high; worst clearance to the arm bundle 0.19 mm, to the cell 0.13, lengths 31-35 mm. **Left pod (board flipped in the mirrored shell): dock pads high (z −3.0..+1.85), arm pads low**, so the dock wires climb past the arm exit: worst 0.11 mm (VBUS vs arm bundle), lengths 34-42 mm. **v2 2026-10-07 (clearance ≥ 0.3):** the ribbon climbs in y while low (z −8.5, ~3 mm under the arm exit), then climbs in z ABOVE the cell in the stowage behind the board at y 12.55 (cell top 10.7, lid 13.2), where the arm bundle (y ≤ 11.6) never is, and drops to the edge level only at its pad's z. Worst clearances: right pod arm bundle 2.41, arm wires 0.98; left pod arm bundle 0.58, arm wires 0.98; cell 0.28, cavity walls 0.28 (= centred in the 0.8 under-cell channel); lengths 27-38 mm. Superseded: v1 climbed inside the rear gap (0.19 right / 0.11 left). heel.py models only the right pod's arm route (new backlog ARM-LEFT).
4. (closed 2026-10-07, ECR-0001) `frame.py` / `pod.py` derive the pod from the current dims; rail and adapter default to the body centre.
5. **Which pod the CAD is**, and board orientation per pod, are stated two ways (pcb-mech-interface §1 "right"; dims_r2/notes "right = mirror"). Close: one statement in dims_r2 + a KiCad 3D render placed in the CAD for both pods. Board placement in both pods checked against the KiCad 3D export 2026-10-07 (reg-board issue 9, `hw/mech/board_in_pod.py`): PASS.
6. **Sealing unverified.** No IP test plan; mesh, skin, tape and adhesive products not chosen. Note written 2026-10-07: `docs/research/sealing-and-service.md` (leak paths S1-S7 with a seal each, service, IPX4/IPX5 coupon plan; finding: a non-porous vent membrane fails R14, so the mic path relies on a hydrophobic open mesh).
7. (closed in Phase 2) Plunger reach: selective-fit puck kit (switch_stack PASS); residual lateral WARN in sub-ui / reg-pod-body issue 4.
8. **Mass 11.2–13.2 g per side worn vs ~8 g** (computed 2026-10-07, `sim/checks/pod_mass.py`, resin 1.15–1.18 as one range; pod body 8.7–10.1, cell 4.2 of it). Remaining unknowns are weighed, not computed: dock target [A 0.8–1.6 g] and exciter [Low 1.0–1.5 g]. The gap to 8 g is an owner call (backlog PHYS-8D; A-TODAY-MASS-TARGET wear test).
9. **Contact face** Ø8 (≈ 50 mm²) vs O16(4)'s 100-150 mm².
10. **Cell lead exit and PCM position** in the Renata pouch unknown, so the J5/J4 lead route is unknown.
11. **Diagrams stale:** `system-overview-physical.png` (Rev F stack, ribs, foam, open gap); `arm-wiring.png`; `hardware-map.png`. No Phase-2 physical overview yet. **Phase-2 overview drawn 2026-10-07:** `docs/diagrams/phase2-overview.svg` (section through the dock + plan through the lid, generated from dims_r2 by make_phase2_overview.py); arm-wiring redrawn (reg-arm 11). hardware-map.png still stale.
12. (closed in Phase 2) Foam strips: none.
13. **Seam:** rebate now 0.2 × 0.4 (2026-10-07); belly step unmarked, butt joints at corners (reg-pod-body issues 12, 13).
14. **Service** costs one seam cut per cell or arm swap; a board swap or SWD also destroys the board bond (Service table).
15. **Wire stowage fill** is volume-checked (277 vs 107-142 mm³) but not routed: 12 loops, wires enter the 1.4 B gap to reach pads at board x 25-29 (up to 4.9 mm in front of the board's rear edge, J3 at board x 25.1). Close: a wire-route sketch with gauges (sub-dock-usb, sub-power). Dock wires routed in both pods 2026-10-07 (issue 3, `hw/mech/dock_route.py`); cell leads J5/J4 + NTC J9 wait on the cell lead exit (issue 10).
16. (closed, O31 2026-10-08) USB-C fallback dropped: no keep-out; ECR-0019 (proposed) removes J12/R18/D6 and takes the dock wires 5 -> 4 when the board is re-planned.
17. (closed 2026-10-07, ECR-0001) One pod source: `dims_r2.py` (via `frame.pod_facts()`); `frame.py` owns axes, adapter, arm and pad only.
18. **Phase-2 tolerances sourced 2026-10-07** (`docs/build/tolerances.md` Phase-2 section: JLC outline ±0.2, hole +0.13/−0.08, position ±0.075, board ±0.1; VHB ±15 %). Still [A]: resin ±0.05, KMT022 height.

## Before you change this, check
- Mic or SW1 off the board centre line y 6.0: breaks one board for both pods (O16-5) and moves lid features. See [sub-audio-in](sub-audio-in.md), [sub-ui](sub-ui.md).
- Any B part > 1.4 mm hits the cell; any F part outside a VHB cut-out lifts the board off the tape. See [reg-board](reg-board.md); `interfaces.py` [heights] [clamp-bands].
- Growing the board rearward eats the stowage zone; a different cell changes the y stack, heel-exit clearance and balance (D18).
- Anything off the centre line lands at a different height in each pod.
- Changing the arm wire count changes the heel channel Ø1.0, strut bore Ø1.2, counterbores and J pads ([reg-arm](reg-arm.md), [reg-pad](reg-pad.md)).
- Changing lid/plate thickness changes the duct length (acoustics scenario `phase2_r2`) and the puck kit.
- Editing `frame.py` changes what `heel.py` and `pad.py` build; editing `dims_r2.py` changes shell, interfaces.py, sim/acoustics and (via `frame.pod_facts()` / `pod.py`) heel's checks and blade's rail/adapter default together.
- Then walk [integration-map.md §10](integration-map.md#10-required-cross-check-for-every-proposed-change) and `python3 tools/plm.py impact PHYSICAL`.

## Reference design (Rev F/G)
`hw/mech/shell_r1.py` + `hw/pod/place_r1.py` (env `ULTRASONIC_DESIGN=revg`): board 34 × 13 at pod x 30.6-64.6, parts on both faces (bands 1.2 each), clamped at y 12.1-12.9 between two lid ribs (F edge bands) and 1.5 mm foam strips with 0.1 mm of cell under each; seam y 14.4 with a lid lip round the main cavity, butt joint round a 3.5 mm belly; open 1.5 mm gap board → lid bore Ø1.0 at pod 34.5; floating plunger at pod 52.6; J pads on F in two columns at pod 62.0/63.6, wires up a 2.1 mm gap behind the board; pod 38.0 × 11.8 × 15.2. Board ↔ pod z: pod z = board y − 8.6 (CAD pod), centre line board 6.5 = pod −2.1. Full text: git history of this file (before 2026-10-07).

## K4 dock envelope (ECR-0021, proposed)
- Pod envelope T 6.4 x H 14.8 x L 50.65 (was 49.15): the extra 1.5 mm is at the front for the dock magnet; stack moves to pod x 17.7-28.7, wire gap 0.8 -> 2.3.
- Dock pads: M tab x 21.05-30.45, y mid 6.8, 0.8 thick, bottom z -9.0 (0.7 recessed from the outer belly); magnets x 19.15 / 32.35. M mid-plane pinned at y 6.8; its parts on the floor face (1.3 high), lid face flat. **SUPERSEDED/CONFLICT (2026-10-08, sim/checks/k4_mplane.py):** after ECR-0022 M is the lid-side board with mid-plane y 8.35 (F 8.75 / B 7.95) and parts on both faces; the pads miss the y-6.8 windows by 1.55 mm. Options (owner decides; rec A): A) move DOCK_YC (windows, magnets, tab) to 8.35 - shell-only; the 6.86 head then spans y 4.92-11.78 and overhangs the lid side by 1.1 mm (never docked while worn, O32), belly flat y 5.3-9.7 so pockets fit. B) swap the stack (P lid-side, M floor-side: mid-plane 6.95, inside the 1.2 window) - moves SW1, mic port, ledge, heights: a re-do. C) keep 6.8 and add a stepped 0.8 tab board - extra part, rejected. Tracked: backlog K4-DOCK-YALIGN.
- Replaces the `Dock target` row (YZT0675 21.2 x 6.86 x 2.8) when adopted. src `hw/mech/dims_k4.py`, `docs/research/k4-dock.yaml`.

## K4 stack chain after the lid ledge (ECR-0022)
- From the lid down: ledge 0.70 | VHB 0.25 | M 0.8 | gap 0.6 | P 0.8 | L1 1.0 | floor; STACK_T 3.2 (dims_k4); floor clear 0.65 nominal, 0.163 worst-case. Pod T/H/L unchanged.

- K4 arm-wire lane moved (2026-10-08): z -8.8 single level, y 8.85-9.51, drop column x 30.86; clears the rear dock boss (x 27.9-30.8) and magnet. Floor-post chain: Y_F 8.75 puts U1 top 1.05 above the tub floor; compressible pad alternatives fail (ECR-0023 addendum).

- K4 shell default K4_RELIEF=lift (O34, ECR-0024, 2026-10-08): T 6.4 x H 15.25 x L 49.85 at stack 15.5 (len 14.8 x 53.65); worn 9.43-10.58 g, nose 6.16-6.84 g / ear 3.27-3.73 g, COM 34.7-35.3 mm behind the hinge.
