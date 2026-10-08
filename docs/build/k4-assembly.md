# K4 pod: hand assembly guide (right pod, left-pod mirror at the end)

For the owner, by hand. One pod = tub + lid, board M + board P (stacked, joined by the BM28 connector), a 130 mAh cell, 4 arm wires, a button puck and a mic duct. Status: **drawn from the repo as of 2026-10-08, nothing built yet.** Items marked **[T]** are not measured yet. Read "Open items" before you start.

![order](../diagrams/k4-assembly/03-order.png)

Gates (red boxes): do not go on until the test passes. Every step has **Do**, **Check** (multimeter) and **If it fails**.

## 0. What is what

![stack](../diagrams/k4-assembly/01-stack-section.png)

1. **Lid** carries the stack. **Tub** carries the cell. Seam = lid underside.
2. **M** (against the lid): mic, SW1 button, charger U3, regulator U4, dock pads on a tab, wire pads J5 J4 J7 J8 on its lid face.
3. **P** (below M): MCU U1, coil L1, H-bridge Q1/Q2, exciter pads J1 J2.
4. **BM28**: 30-pin 0.35 mm board-to-board connector, 0.6 mm mated gap. M = receptacle J20, P = plug J21.
5. **Dock**: 4 gold half-hole pads on M's tab show through 4 belly windows; 2 magnets in belly pockets. No dock wires.

## 1. Tools and parts

| Tools | Parts (per pod) |
|---|---|
| Soldering iron, fine tip, flux, wick, loupe/microscope | Boards M and P (JLC), parts from `hw/pod/k4/bom_jlc_M.csv`, `bom_jlc_P.csv` |
| Multimeter (diode mode, mA range), thermocouple + logger | Tub, lid, 5-puck kit (1.03 to 1.23 mm), printed and reamed |
| Calipers, depth gauge, pin gauges 0.60/0.70 and a 1.0 pin | Renata ICP401230UPR 130 mAh cell (4.5 x 12.7 x 31 max) |
| Bench supply 3.70 V, 50 mA limit; USB dock head + cable | 4 x 7/44 served litz, 0.21 mm OD (arm wires) |
| Tweezers, spudger, floss, new blades | 3M VHB 4914 0.25 (die-cut), 0.10 transfer tape under the cell |
| Fire-safe LiPo bag, ceramic tile | 2 x N52 magnets D2.5 x 1.0, dock head YZP0048 (C5126845) |
| Neutral-cure RTV (never acetoxy), Kapton tape | Silicone skin 0.1, hydrophobic open mesh [T: product not chosen], M1.4 set screw (heel) |

Cell wire gauge for the 401230 is **[T]**: the repo only states AWG30 for the bigger 501233 cell. Use the cell's own leads, cut to about 8 mm of free length at the pad end.

## 2. Parts check (no electricity)

1. **Do:** print tub, lid, pucks. Ream the lid mic bore to D1.0. Measure and label every puck.
2. **Check:** 1.00 pin enters the bore, 1.03 does not. Mic hole in M: 0.60 pin enters, 0.70 does not.
3. **Do:** dry-fit the cell in the tub. Note where its leads leave (the repo does not know, PWR-I10).
4. **Do:** caliper a dock head sample: magnet pitch (design guess 13.2 mm), polarity with a compass. Fit the pod magnets opposite to the head's.
5. **If it fails:** reprint with compensation; a closed bore gets a fresh ream.

## 3. Solder the joints to M (before P exists on it)

![pads](../diagrams/k4-assembly/02-pad-map.png)

Why now: P sits below M and has no solder window over M. After mating you cannot reach what is inside.

| # | Pad (board, face) | Net | Wire | Notes |
|---|---|---|---|---|
| 1 | J5 (M, lid face) | cell BAT+ | cell lead, red | route length about 8 mm (dims_k4 wire_lengths) |
| 2 | J4 (M, lid face) | GND, cell minus | cell lead, black | same 8 mm |
| 3 | J7 (M, lid face) | LED+ (LED_A via R14) | 7/44 litz #1 | arm wire, cut about 60 mm + 5 mm loop |
| 4 | J8 (M, lid face) | LED- (LED_K, MCU sink) | 7/44 litz #2 | cut about 50 mm + 5 mm loop |
| - | J9 (M) | NTC | **leave empty** | RT1 is on M; charger reads one NTC, never both |

1. **Do:** pre-tin each pad and wire end. Iron at about 300 C, under 3 s per joint; litz strands burn their enamel off in the solder, so check that all 7 strands wet.
2. **Do, order:** J7, J8 first (arm wires). **Cell leads J4 then J5 last** (see gate below). Keep the free cell end taped, never let the two leads touch.
3. **Check, bare M (before the cell leads):** diode mode and ohms: J5-J4, J4-J7, J8-J7, J5-J8 all above 1 kohm or a diode drop (0.3 to 0.8 V), none under 5 ohm (bringup B2).
4. **Check, after the cell leads:** J5 to J4 reads 3.5 to 4.2 V. 0 V means the cell's protection circuit tripped: stop.
5. **If it fails:** a short = bridge under the loupe, wick it off. Lifted pad: stop, use the other board.

## 4. Solder the joints to P

| # | Pad (board, face) | Net | Wire | Notes |
|---|---|---|---|---|
| 6 | J1 (P, outer face, away from M) | OUT_A, exciter | 7/44 litz #3 | cut about 58 mm + 5 mm loop |
| 7 | J2 (P, **inner** face, faces M) | OUT_B, exciter | 7/44 litz #4 | cut about 57 mm + 5 mm loop; **solder it before the mate** |

1. **Do:** solder J2 first (inner face, hardest), then J1. Dress both wires flat and out toward the board edge. Keep each joint under about 0.4 mm of height (gap is 0.6 mm and M parts hang in it).
2. **Check:** J1 to J2 above 1 kohm (a bridge and its 8 to 12 ohm exciter will read low only once the exciter is on). Neighbour pair J2-J8 is across boards: check after the mate.
3. **If it fails:** if J2's wire will not lie flat under 0.6 mm, stop and read Open items 1.

## 5. Mate P to M

**BM28 warning (Hirose catalogue, per coordinator b18670c):** no polarity key, so it can mate 180 degrees reversed. Rated for only **10 mating cycles**. **Mate it once**, after testing each board alone where you can (M alone: step 3 checks; P alone: loupe + shorts only, it has no supply pad of its own).

1. **Do (marks):** before anything else, put a pin-1 dot (paint pen or marker) on M next to J20 pin 1 and on P next to J21 pin 1, on the board edge where you can see it from the side. Pin n mates pin n. Which end is pin 1 comes from the KiCad footprint, so confirm it on the board silkscreen or in KiCad first **[T]**.
2. **Do (photo check before pressing):** lay P over M with the dots on the same side, 2 mm apart, not touching. Take a photo from above and one from the side. Both dots must be on the same end. Wrong = turn P around. Only then press.
3. **Do:** press with a flat tool at the connector only. Soft stop; mated gap about 0.6 mm. Do not unplug and re-mate for casual probing.
4. **Check:** loupe along the gap: even all round. Then meter J5-J4 again (cell connected, board now live): 3.5 to 4.2 V, no warm part by touch after 30 s.
5. **Check:** TP4 (+3V0) to TP5 (GND) on M: 0 V or about 3.0 V, never a short (above 1 kohm unpowered).
6. **Gate G1/G2:** no 5 V on the dock pads until the cell side is quiet.
7. **If it fails:** unplug, re-seat (counts as a cycle); a part getting warm = unplug the cell lead at J5 and look for a short.

## 6. Bench power-up and bring-up (stack on the mat, no lid)

Follow `docs/build/bringup.md` stages B to E. Short version for this pod:

1. **Flash (D1):** P's R1 pad (outer face) is the DFU tack point: tack it to +3V0, 5 V at a 100 mA limit on M's dock pads J3/J4, D+/D- on J10/J11, power-cycle, `dfu-util`, remove the tack.
2. **SWD is gone:** P's SWD pads TP1 to TP3 face the gap. Firmware goes in over the dock only. Write and protect the boot stub (G3).
3. **Button (E3):** press SW1 directly; LED lights on J7/J8 (test with any LED).
4. **Gate G3:** no lid bond until the boot stub passes ROM DFU and a full re-flash (bringup D4).

## 7. Cell into the tub

1. **Do:** 0.10 transfer tape on the cavity floor, press the cell on (front end at pod x 31.0, 4.5 thick max). Wire gap behind the stack is 0.8 mm; the cell's own 0.2 mm lid clearance is for swell.
2. **Do:** dock tab: set the M tab onto the belly windows later with the stack (step 8). Dummy-check it now: the 4 pads must sit behind the 4 windows (1.3 x 1.2).
3. **Do:** pull the arm litz (4 wires) out of the heel channel exit (pod x 66.2, z -5.5) with the tub empty, set screw M1.4 in the heel, RTV dot at the exit. See `hw/mech/notes/heel.md`.
4. **Check:** cell flat, heel exit not covered, no wire pinched.

![routes](../diagrams/k4-assembly/04-wire-routes.png)

## 8. Stack onto the lid

![lid](../diagrams/k4-assembly/05-lid-features.png)

1. **Do:** die-cut VHB onto the lid ledge tip only (ledge 0.70 high, 0.5 wide, with notches round J5/J7/J8 and the mic tube). Mic: slide a 0.60 pin gauge through the lid bore, VHB hole and M's hole; press M down; pull the pin last.
2. **Do:** press through a foam pad over P (about 30 N), hold 30 s. M's pads stay in the ledge notches.
3. **Do (button):** depth-gauge from the skin recess floor to SW1's top, puck length = depth - 0.07, pick from the kit (1.03 to 1.23). Skin on unbonded, press 10 times: one click each, none at rest. Then bond the skin.
4. **Do (peel layer):** stick a 3 x 3 mm square of Kapton tape on U1's top (the big QFN on P's outer face, centre of the BM28 line). The post dab will bond to this, never to the chip.
5. **Check:** J5-J4 still 3.5 to 4.2 V; mic hole clear to a 0.60 pin.
6. **If it fails:** puck too long = click at rest, take the next shorter; peel VHB (warm 60 to 80 C, floss).

## 9. Close and seal (O12, IPX4 minimum, IPX5 preferred)

0. **Do (gap-filling post, ECR-0023 add.2, final build only):** the tub post is printed 0.59 short of U1 on purpose (air gap 0.05 to 1.125 mm). Mix about 10 uL (a 3 mm blob) of 30-minute low-shrink two-part epoxy and put it on the post top; keep it off the cell side. Close the pod (step 9.1 to 9.4) within 15 min; the dab squeezes out to the real gap against the Kapton. Clamp the closed pod 1 h flat, no press on SW1 for 24 h. Check: epoxy skirt visible only at the post, nothing on the BM28. Rework: warm the pod to 60 to 80 C and the dab lets go from the Kapton, not from U1. Dry-close builds get no dab.

![post](../diagrams/k4-assembly/08-gap-fill-post.png)

1. **Do:** fold the cell leads forward to the cell front lead and solder them (cell + to J5's lead, cell - to J4's). Arm wires run flat under the cell in the 0.9 mm lane (z -8.8), then up to the heel exit. Kapton tape across.
2. **Do:** dry-close first with tape round the seam (test build). Look through the seam that nothing is pinched.
3. **Do:** 2 magnets into the belly pockets (opposite to the head), plus one RTV dab at each of the 4 dock windows. Neutral-cure RTV only (acetoxy corrodes copper).
4. **Do (final build):** RTV bead in the tongue/groove and at each corner, bond the seam, hex mesh in the seat, skin over the button last.
5. **Check:** cell + to J5 and the arm wires still read as in steps 3 and 4. Docs: `docs/research/sealing-and-service.md`. Test plan: IPX4 spray 5 min with indicator tape inside.

## 10. First charge (gate G5, supervised)

![charge](../diagrams/k4-assembly/06-first-charge.png)

1. **Do:** pod in the fire-safe bag, bag on the ceramic tile, thermocouple taped to the cell through the open seam. Lid taped, not bonded yet.
2. **Do:** dock head on, USB source with a USB meter in line. Defaults: charge 10 mA, 4.20 V end; cell limit 65 mA normal (130 mA max).
3. **Check, every 5 min:** write time, cell temp, VBAT, USB current, LED. Pass: cell 45 C or less, ends at 4.20 V.
4. **Stop:** above 45 C, any swelling, hiss or sweet smell. Unplug, close the bag, take it outside.
5. **Then:** firmware charger plan (E6): TS_HOT 45 C. Only after it passes do you bond the seam and wear it.

## 11. How to reopen or rework

Same cut-and-rebond pattern as `docs/build/reopen.md`. K4 differences:

1. Score the rebate (0.1 deep x 0.4 high, with a 0.1 inward ridge so the wall stays 0.6): 2 to 3 light passes, 0.3 mm total depth at most.
2. Open from the rear straight run with a spudger. The stack hangs on the lid and lifts with it on the wires (slack: 5 mm loops).
3. **Cell swap:** desolder J5/J4, peel the 0.10 tape (floss), new cell on new tape. **Arm swap:** desolder J7 J8 (M) and J1 J2 (P), release the heel set screw.
4. **P off M:** costs one of the 10 BM28 cycles; needs the lid off the tub first, then pull P from the BM28 (it is not glued). Re-solder J2 before re-mating.
5. **Always replace:** seam adhesive, cell tape; **sometimes:** lid (stack VHB is destroyed on a board swap, 60 to 80 C and floss).

## 12. Left pod (mirror)

![mirror](../diagrams/k4-assembly/07-mirror.png)

1. Same boards. Print the mirrored tub and lid.
2. Mic, SW1, BM28 are on the board centre line, so nothing moves; pad heights flip (J5 J4 J7 J8 J1 J2 trade up/down).
3. Arm wire order at the heel changes; the repo's left-pod wire route is not valid for K4. Redo the dry fit (step 7).
4. Dock pad order runs along x and stays the same; the magnets and head key identically.

## Open items (blunt)

1. **J2 sits on P's inner face** (placement_P.yaml, `J2: [1.68, 3.58, 0, F]`), inside the 0.6 mm gap, where M parts reach 0.5 to 0.7 mm. The gap side already fails the height check (C16 -0.10, C17/C9 -0.05). A wire may not fit. Needs a layout call before ordering.
2. **Pads J5 J4 J7 J8 are on M's lid face (B), so P does not cover them** in the current layout (reg-board and k4_heights). The "solder before mating" order is safe anyway; the safer option is **cell leads last** (after step 6 on a 3.70 V / 50 mA bench supply at J5/J4, bringup C1). Recommended: use the cell-last order. Owner decides.
3. **Arm wire route under the cell is a placeholder** (dims_k4 wire_routes; reg-pod-body K4 note: 0.111 / 0.140 mm3 clash with tub and cell). Dry-fit first.
4. **Not measured:** cell lead gauge, lead exit position, dock head magnet pitch/polarity, mesh product, RTV product, mated BM28 height 0.6 [T].

<!-- NOTES (hidden; sources, read 2026-10-08)
stack/layers: hw/mech/dims_k4.py (LID_STANDOFF 0.70, LEDGE_W 0.5, F_GAP, STACK_T 3.2, STACK_L from routed boards 15.5, PCB_T 0.8, TAPE 0.10, CELL_SPEC, CELL_X0 31.0, PUCK_KIT, DUCT, wire_routes/wire_lengths 8.1/7.8/58.4/57.3/60.5/50.0).
ECR-0020 (BM28 split, J20/J21, pin map, P/M parts), ECR-0021 (dock pads, magnets D2.5x1.0, windows 1.3x1.2), ECR-0022 (ledge, notches J3 J5 J9 RT1 TP5, C21 0402, gap-side fail).
Pad faces: hw/pod/k4/placement_M.yaml (J5 J4 J7 J8 J9 B), placement_P.yaml (J1 B, J2 F). Face meaning: sim/checks/k4_heights.py header (M file-B = LID face, P file-B = OUTER).
LED O8: docs/spec.md O8 (R14 + J7/J8 on PB7); reg-arm.md (LED_A J7, LED_K J8, 4 x 7/44 litz 0.21 OD).
Seal: docs/research/sealing-and-service.md (neutral RTV, no acetoxy, IPX4/5, indicator tape); physical.md assembly order + DBG-16 gate.
Bring-up gates/steps: docs/build/bringup.md (G1-G5, B2, C1, D1, D4, E3, E6: ICHG 10 mA, VBATREG 4.20, TS_HOT 45 C, thermocouple).
Cell: docs/research/V2-cells.yaml ICP401230UPR (charge 65/130 mA, 4.2 V, PCM, 3.5 g).
Reopen: docs/build/reopen.md pattern; dims_k4 REBATE 0.1x0.4; shell_k4.py seam_ridge; physical.md Service (60-80 C, floss).
Left pod: physical.md coordinate frame mirror note; reg-pod-body.md line 195 (left pod, K4 wire route placeholder).
Assembly order cross-check: hw/mech/shell_k4.py docstring (steps 1-6).
Diagrams: docs/diagrams/k4-assembly/make_k4_assembly.py.
-->
