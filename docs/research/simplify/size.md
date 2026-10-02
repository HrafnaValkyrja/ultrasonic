# Simplification study: size and packaging (what makes the pod big, and how small it can get)

Date: 2026-10-02 (UTC; the run was ordered 2026-10-01 local). Read-only opportunity study: nothing in the schematic, board, CAD, spec or other docs was changed. New files only: this note, `docs/diagrams/size-stack.svg/.png`, `sim/checks/size_budget.py`.
Scoring rule (spec O19/O20): reliability and size/comfort first and co-equal, then daily convenience, diagnosability (O18), serviceability, money last. Rev 1 is meant to be the final device, so the board is the irrevocable part; the printed shell can be reprinted in hours.
Context read first: `docs/system/` README, 00-whole, integration-map (incl. §10), physical, reg-pod-body, reg-board, reg-arm, reg-pad, sub-power, sub-dock-usb, sub-ui, sub-debug-test, sub-audio-in; `docs/research/tws-power-size.md`; the sibling studies `simplify/periphery.md` and `simplify/power.md`; ECR-0001..0013; `hw/mech/shell_r1.py`, `blade.py`, `frame.py`; `docs/build/tolerances.md`, `hardware.md`; `tools/checks/part_heights.yaml`.

![Pod size: thickness stack and side views, as drawn vs the study's targets](../../diagrams/size-stack.png)
*`docs/diagrams/size-stack.svg`. Panel A: thickness stack to scale. Panel B: side views to scale (S0 as drawn, S1 core changes, S3 with the plate off and a thin dock).*

## 0. Bottom line (blunt)

1. **The pod is not a board problem. It is a cell problem plus a packaging-air problem.** As drawn the outer envelope is 7.80 cm3 (38.0 x 11.8 x 15.2 mm, +3.5 mm belly, +3.1 mm spine). The cell is 28.5 % of it, resin 29.8 %, and **air and fill 30 %**. The board is 4.5 % (laminate) plus 1.6 % (parts). The pod's length is set by the cell (35 + 3.0 mm), not by the 34 mm board.
2. **The pod weighs about 12.4 g per side, not the ~8 g target** (derived: cell 4.2, shell 3.1, pad 2.2, board + parts 1.0, dock 0.9, adapter 0.5, misc 0.5). That puts ~6.0 g per side on the nose pads (spec §8: "nose-pad pressure is the usual comfort failure"). **Size levers recover at most ~1.4 g.** Mass is a cell + shell + pad problem; say so before anyone expects the board to fix it.
3. **Recommended set (S1, no owner trade-off needed): 38.0 x 11.25 x 14.5 mm, belly 2.05 mm, 6.77 cm3 (-13 %), 11.9 g (-0.5 g), 0.55 mm less sticking out from the temple (13.6 -> 13.05 mm), board 442 -> 312 mm2 (-29 %).** It is five changes: board height 13 -> 12 mm (SIZ-01), board hung from the lid instead of floating on foam (SIZ-02), F-side stack from measured part heights (SIZ-03), lid wall 0.8 mm (SIZ-04), dock tails bent flat (SIZ-06).
4. **With the two owner calls (drop the 0.7 mm armour plate, drop the USB-C keep-out) it is 10.75 mm thick, 6.46 cm3 (-17 %), 11.6 g (S2).** With a thin dock target and an owner-built cable head it is 6.25 cm3 (-20 %, S3). Everything stacked (thin walls too): 5.94 cm3 (-24 %), 11.1 g, 12.15 mm off the temple (S6).
5. **The biggest single lever is the cell, and I do not recommend pulling it.** The 130 mAh Renata ICP501233's slimmer sibling (ICP401230UPR) saves 0.8 mm of thickness and 4 mm of length (-1.06 cm3 on today's geometry) and costs 26 % of the runtime and 0.7 mm of height. Worst-case runtime falls from 12.4 h to 9.2 h with E4 unmeasured. Under O20 (no rev 2) keep the 175 mAh cell.
6. **The belly (dock bay) is the best non-cell target.** It is 975 mm3 of envelope (12.5 %) for a 407 mm3 part. Bending the dock target's 2.0 mm solder tails flat cuts it from 3.5 to 2.05 mm deep for free (-407 mm3). A thinner target family exists (2.0 mm, no tails), but nothing in JLC's catalogue mates with it: it needs an owner-built head.
7. **The 34 x 13 board is 1.3-1.5x bigger than its parts need.** The courtyards (part footprints plus clearance) of all 76 footprints add to 246 mm2 across both faces. The routed 20 x 11.5 mm board of 2026-09-30 held 198 mm2 of them (43 % of its two faces) with 0 unrouted. At that density the current parts need ~28 x 12 mm, and ~26 x 12 mm after the periphery and power studies' cuts. **But the pod only shrinks through the board's height** (cell-limited at 12 mm), not its length; the rest of the length becomes a 10 mm wire-stowage zone (486 mm3 against 190 mm3 today), which is a reliability win (O17, physical issue 15).
8. **Four "obvious" ideas fail on checking:** a 0.6 mm board (JLC's 4-layer minimum is 0.8 mm), a single-sided board with a top-port mic (its ultrasonic response is not specified), a stepped thin rear, and a USB-C receptacle instead of the belly (owner choice O12(a)/O16(3); see section 9).
9. **Before the board is ordered, print and wear dummies at S0, S1 and S2 size and mass (ECR-0006 already asks for one pair).** The board outline is the one thing that cannot be redone; the shell can.

## 1. Today's envelope and size budget

### 1.1 Envelope and what sets each axis (pod mm; x rearward from the hinge, y outward, z up)

| Axis | As drawn | Stack | What sets it |
|---|---|---|---|
| Length x | 38.0 (29.5-67.5) | wall 0.8 + front gap 0.3 + **cell 35.0** + behind-cell gap 1.1 + wall 0.8 | The cell. The 34 mm board sits inside it (0.3 front, 2.1 rear gap). Ends: vision line (front), Ear (open) hook (rear) |
| Thickness y | 11.8 (4.3-16.1); **13.6 beyond the temple's outer face** with the 1.8 mm adapter | wall 0.8 + VHB gap 0.3 + **cell 5.3** + B band/foam 1.4 + PCB 0.8 + F band + clearance 1.5 + lid 1.0 + plate 0.7 | Cell 45 %, board stack (1.4 + 0.8 + 1.5) 31 %, walls + tape + lid + plate (0.8 + 0.3 + 1.0 + 0.7) 24 % of the pod thickness |
| Height z | 15.2 (-9.7..5.5) | wall 0.8 + gap 0.3 + **board 13.0** + gap 0.3 + wall 0.8 (the 12 mm cell has 0.8 slack each side) | The board's 13 mm, not the cell: this is the lever |
| Belly | +3.5 mm over the front 25.5 mm (z to -13.2) | target 2.8 + tails 2.0 + 0.3 under the cell (cell bottom z -8.1) - floor 0.8 - cell slack 0.8 | The dock target stacked under the cell |
| Spine | +3.1 mm on top, x 44-66.8 | styling (O17) | Owner decision |
| Heel / adapter | heel 191 mm3 under the rear; adapter 417 mm3 separate print | styling/mechanics | Outside the envelope below |

Bounding box of the pod proper: 38.0 x 11.8 x 21.8 mm (9.8 cm3); the solid envelope is 7.80 cm3 (body 7263 mm3 from `shell_r1.py`, reproduced exactly by `sim/checks/size_budget.py`, + plate 374 + spine 160).

### 1.2 Volume budget (as drawn; derived from the CAD, build123d probe 2026-10-02)

| Item | mm3 | % of 7801 | Note |
|---|---|---|---|
| Resin walls (tub + lid, excluding plate, rail, heel) | 1790 | 22.9 | 0.8 mm walls over 2436 mm2 of outer area (effective 0.70 mm after chamfers and cut-outs) |
| Armour plate (0.7 mm, 540 mm2) | 374 | 4.8 | Styling; also 0.7 mm of mic duct |
| Spine | 160 | 2.1 | Styling (O17) |
| **Cell** (35 x 12 x 5.3, maker's maximum envelope) | 2226 | 28.5 | |
| Dock target | 407 | 5.2 | 21.2 x 6.86 x 2.8 |
| PCB laminate | 354 | 4.5 | 34 x 13 x 0.8 |
| Board parts (rough: 246 mm2 of courtyards x ~0.5 mm mean height) | ~123 | 1.6 | |
| **Air, tape, foam, wires** | ~2370 | 30.4 | 42 % of the sealed cavity (5382 mm3 to the seam) |

Where the air is (cavity, mm3, rough): gap above the cell under the board ~570, gap above the board under the lid ~590, belly bay beside the target ~370, cell-to-wall slack top and bottom ~300, rear wire gaps ~175, VHB tape gap ~125, board and cell side gaps ~140.

### 1.3 Mass and balance (D18, R20), per pod, derived

| Item | g | % | Basis |
|---|---|---|---|
| Cell (Renata ICP501233PA-02, 3.7 V Li-polymer pouch with built-in protection circuit) | 4.2 | 34 | Renata UN 38.3 summary, tws-power-size |
| Shell (tub + lid + plate + spine + heel) | 3.1 | 25 | 2663 mm3 x 1.18 g/cm3 |
| Pad (exciter 1.2 g `[Low]`) | 2.19 | 18 | pad checks.json |
| Board + parts | 1.0 | 8 | 0.65 g FR4 + ~0.36 g parts (rough) |
| Dock target | 0.9 | 7 | **derived, unverified: weigh the sample** |
| Frame adapter | 0.5 | 4 | 417 mm3 x 1.18 |
| Wires, VHB, foam, silicone, epoxy | 0.5 | 4 | rough |
| **Total** | **12.4** | | reg-pod-body's "10.2 g lower bound" + the parts it excluded |

Centre of mass 51.9 mm behind the hinge: **nose pads 6.0 g, ears 6.5 g per side** (`sim/checks/balance.py` convention, hinge to ear bend 100 mm). Spec §8's older estimate was 3.1-3.7 g on the nose per side. The ~15 g "glasses start to hurt" level (D18/R20) is 83 % used. The pad (70 % of it on the ear) and the cell are the mass; the shell is the part this study can touch.

## 2. Size drivers, ranked

| Rank | Driver | Volume | Comfort effect (judgement) | Lever |
|---|---|---|---|---|
| 1 | **Cell** 35 x 12 x 5.3 | 2226 mm3 (29 %), 4.2 g (34 % of mass) | Sets length and 45 % of thickness; the heaviest part; owns the 12 h target | Section 6: keep |
| 2 | **Resin shell** (walls, plate, spine, heel) | 2663 mm3 incl. heel (30 %), 3.1 g | Silhouette, snag, 25 % of mass | SIZ-04/05/11 |
| 3 | **Air in the stack** (B band + foam 1.4, F band + gap 1.5, board-height slack) | ~1200 mm3 in the two bands, ~300 in the height slack | Thickness 31 % and height | SIZ-01/02/03 |
| 4 | **Belly** (dock bay) | 975 mm3 of envelope (12.5 %) | Hangs 3.5 mm below the pod at the front, snags hair, visible silhouette | SIZ-06/07/08 |
| 5 | Plate + spine styling | 534 mm3 (6.8 %), 0.63 g | 0.7 mm of thickness; spine adds 3.1 mm of height at the rear top | SIZ-05 (owner) |
| 6 | Adapter (1.8 mm stand-off) | not in the envelope | 13 % of the 13.6 mm off the temple; swappable for new frames (owner requirement) | SIZ-13, rejected idea 10 |
| 7 | Board (laminate + parts) | 477 mm3 (6 %) | Little directly; it gates the stack and the height | SIZ-01/10 |

Comfort order I would use for decisions: (1) mass and balance (nose pads), (2) thickness off the temple (13.6 mm: hair, hoods, look from the front), (3) belly and spine silhouettes (hair snag, R16), (4) height, (5) length (fixed by the room between the vision line and the Ear (open) hook). The wear test (ECR-0006) is how she settles it.

## 3. Levers: gain, cost, cross-check

Single levers measured against the as-drawn pod S0 (7801 mm3, 12.42 g). Model: `sim/checks/size_budget.py` (calibrated: S0 body 7263 mm3 matches `shell_r1.py`). IDs match the structured result. Each full cross-check (functions, nets, pins, rails, off-board, mechanical, firmware, relations, dependencies) is in that result; the headlines are here.

| ID | Change | Envelope | Thickness / height / belly | Mass | Board | Confidence |
|---|---|---|---|---|---|---|
| **SIZ-01** | Board 34 x 13 -> ~26 x 12 mm (28 x 12 with today's parts); pod height set by the cell | -294 mm3 (-3.8 %) | H 15.2 -> 14.5 | -0.11 g | 442 -> 312 mm2 | medium |
| **SIZ-02** | Board hangs from the lid on 2 locating pins + 4 VHB spots; foam strips, clamp ribs and B-face clamp bands go | ~0 alone (enabler) | frees +1.2 mm of usable board height on B | ~0 | +56 mm2 usable | medium |
| **SIZ-03** | F band 1.2 -> 1.0 mm and lid clearance 0.3 -> 0.15 mm, from measured part heights. B gap stays 1.4 (swelling margin) | -232 mm3 (-3.0 %) | T -0.35 | -0.03 g | 0 | medium-high |
| **SIZ-04** | Lid wall 1.0 -> 0.8 mm where the plate stays (excludes SIZ-05) | -133 mm3 (-1.7 %) | T -0.2 | -0.14 g | 0 | medium |
| **SIZ-05** | Armour plate 0.7 -> 0 (or 0.4 mm with a painted trace). **Owner aesthetic call** | -378 mm3 (-4.8 %); -162 for 0.4 mm | T -0.7 (-0.3) | -0.45 g (-0.19) | 0 | medium |
| **SIZ-06** | Bend/trim the dock target's 2.0 mm tails flat; belly 3.5 -> 2.05 mm | -407 mm3 (-5.2 %) | belly -1.45 | -0.09 g | 0 | medium |
| **SIZ-07** | Drop the USB-C keep-out: belly length 25.5 -> 23.2 mm. **Owner call (O16-3)** | -53 mm3 more | belly L -2.3 | -0.01 g | 0 | medium (low value) |
| **SIZ-08** | Thin dock family YZ103915020T-04025-02 (2.0 mm, no tails) + owner-built head; belly -> 1.15 mm | -679 mm3 (-8.7 %) incl. SIZ-06/07 | belly -2.35 | -0.24 g | 0 | low |
| **SIZ-09** | 4-pin target (same body) | 0 | 0; 5 -> 4 wires in the 0.8 mm channel | 0 | -1 pad | high (size-neutral) |
| **SIZ-10** | Wire and test pad strip: real courtyards, 1.0 mm pads on 1.27 mm pitch, TP row 5 pads | 0 | 0 | 0 | -19 mm2 courtyards | medium |
| **SIZ-11** | Walls 0.8 -> 0.7 (-0.6 mm option): coupon + drop test first | -351 (-566) mm3 (-4.5 % / -7.3 %) | T -0.4 (-0.6), H -0.2 (-0.4), L -0.2 (-0.4) | -0.42 (-0.69) g | 0 | low-medium |
| **SIZ-12** | Cell 175 -> 130 mAh (ICP401230UPR): **not recommended** | -1058 mm3 (-13.6 %) on S0; -807 on S1 | T -0.8, L -4.0, **H +0.7** | -0.93 g | 0 | low (owner trade) |
| **SIZ-13** | Adapter 1.8 -> 1.2 mm | not in envelope | thickness off temple -0.6 (-4.4 %) | -0.17 g | 0 | low (R17) |
| **SIZ-14** | Stow wire slack in the board-free rear zone (10 mm x 3.7 x 13 = 486 mm3 vs 190 mm3) | 0 | 0 | 0 | 0 | medium (reliability) |

Combinations (full scenarios, same model):

| Scenario | L x T x H (mm), belly | Envelope | Mass | Off the temple | Board |
|---|---|---|---|---|---|
| S0 as drawn | 38.0 x 11.8 x 15.2, belly 3.5 | 7801 mm3 | 12.42 g (nose 5.97) | 13.6 | 442 mm2 |
| **S1 core: SIZ-01, 02, 03, 04, 06** | 38.0 x 11.25 x 14.5, belly 2.05 | **6769 (-13.2 %)** | 11.92 g (5.75) | 13.05 | 312 |
| S2: S1 + plate off (lid back to 1.0) + no USB-C keep-out | 38.0 x 10.75 x 14.5, belly 2.05 x 23.2 long | 6461 (-17.2 %) | 11.60 g (5.58) | 12.55 | 312 |
| S3: S2 with the thin dock instead of SIZ-06/07 | 38.0 x 10.75 x 14.5, belly 1.15 | 6248 (-19.9 %) | 11.45 g (5.50) | 12.55 | 312 |
| S4: S1 + 130 mAh cell | 34.0 x 10.45 x 15.2, belly 2.05 | 5962 (-23.6 %) | 11.05 g (5.37) | 12.25 | 312 |
| S5: S1 + 0.6 mm walls | 37.6 x 10.85 x 14.1, belly 2.25 | 6370 (-18.3 %) | 11.42 g (5.50) | 12.65 | 312 |
| S6: S3 + 0.7 mm walls | 37.8 x 10.35 x 14.3, belly 1.25 | 5935 (-23.9 %) | 11.07 g (5.32) | 12.15 | 312 |

**Options for the owner (2-3, one recommended):**
- **A (recommended): S1.** All five changes are mechanical and reversible in the shell; only SIZ-01 touches the board outline, and it follows the layout session (O14). No owner trade-off beyond printing a wear dummy.
- **B: S2.** Adds the two aesthetic/risk calls: plate off (-0.7 mm, -0.45 g, and a 0.7 mm shorter mic duct) and no USB-C keep-out. The spine stays (O17 is about the top; the plate is the older Blade language).
- **C: S3 / S6.** Only if she accepts an owner-built cable head (O16-3 says pre-built connector, own magnets OK; a printed head with four spring contacts is a half step past that) and a coupon-tested thin wall. I would not do C for a final-size device without the sample in hand.

### Interactions (the part that bites)

- **Cell stays 0.8 mm above the cavity floor.** The strut-relief fill in the tub's inner-bottom rear corner clears the cell by 0.07 mm (`shell_r1.py` L81-87; physical.md). Biasing the cell up to gain 0.3 mm of height (variant "S1+": H 14.2, belly 2.4, same total z) would put the cell corner ~0.25 mm into the fill and shrink the dock-wire channel under the cell from 0.8 to 0.45 mm. Not worth it: it moves volume from the main body to the belly for zero net height. S1 keeps both.
- **SIZ-02 enables SIZ-01.** Without the clamp bands on B the board's usable height is 12.0 mm, not 10.8. The old routed board had 11.5 mm usable and no bands.
- **SIZ-03 is only as good as the heights file.** The tallest parts are L1 (Murata DFE201610E, 2.2 uH inductor) 1.00 mm on F and the mic U2 1.08 mm on B (`tools/checks/part_heights.yaml`, datasheets read 2026-10-02). Any later swap to a taller part breaks the F gap; `tools/checks/interfaces.py [heights]` is the guard.
- **SIZ-04 vs SIZ-05:** the lid is 1.5 mm with the plate (0.8 + 0.7) or 1.0 mm without (do not take both: 0.8 mm alone has the mic bore, plunger bore, skin recess and the lid-hung board's bosses in it).
- **SIZ-06/07/08 are one family:** pick one belly.
- **SIZ-11 adds belly depth (+0.1-0.2)** because the floor gets thinner while the dock stack does not.
- **SIZ-12 makes the cell, not the board, set the height** (12.7 + 0.8 + 0.1 = 13.6 mm cavity -> 15.2 mm pod): the 130 mAh cell is shorter and thinner but taller.

## 4. The board: the minimum for these parts

### 4.1 Courtyard budget (pcbnew probe of `hw/pod/draft_r1/pod_r1_routed.kicad_pcb`, 2026-10-02)

| Group | F face mm2 | B face mm2 | Note |
|---|---|---|---|
| All 76 footprints | 160.2 | 86.2 | 246.4 total; 56 placed parts + 18 copper pads + 2 DNP |
| of which wire pads J1-J12 | 37.3 | | 12 x 3.11 (2.09 mm courtyard rings; also the 16 DRC errors) |
| of which test pads TP1-TP6 | 6.7 | | |
| of which MCU U1 (QFN-48 7 x 7, STM32U575) | 65.6 | | 27 % of everything |
| Biggest others | | | mic 12.6, R21 (0.1 ohm 1206 shunt) 10.2, SW1 7.7, Y1 6.3, D4 6.0, four 0603 caps 17.1 |
| Draft board area | 442 | 442 | 34 x 13; courtyards fill 28 % of both faces |
| After periphery + power cuts (15 refs removed, BQ25186 and a lid LED added) | 141.6 | 71.3 | **218 total** (-12 %) |

### 4.2 What it needs, with the proof of density

- **Evidence:** commit 6e93246 (2026-09-30): the earlier netlist on **20.05 x 11.55 mm**, 4 layers, 52 footprints, courtyards F 120.6 + B 77.9 = 198.5 mm2 = **43 %** of its two faces, 549 tracks and 41 vias, **0 unconnected**, DRC at JLC's minimum spacing (0.09 mm) with only 1 mm test-pad courtyard errors (`hw/pod/draft/summary.json`).
- **Caveat:** that board had no 0.6 mm clamp bands, no GND fan-out rule and no 0.4 mm ball-grid charger. The current 34 x 13 draft leaves 7 unrouted at 28 % occupancy because of ball-escape and placement, not area (reg-board; ECR-0002). Density is a size estimate, not a routing promise.
- **Estimate:** 246 mm2 at 43 % -> 573 mm2 of both faces -> 286 per face. With 12 mm height and no B clamp bands (SIZ-02) the usable height is ~11.4: **28 x 12 mm (336 mm2)**. After the other studies' cuts (218 mm2 -> 507 -> 254 per face): **26 x 12 mm (312 mm2, ~10 % margin)**; 24 x 12 (288) is the stretch with ~2 % margin.
- **Why 12 mm is the ceiling:** the pod's height is cell-limited (12 + 0.8 slack + 0.1 + 2 x 0.8 walls = 14.5). A board taller than 12 mm grows the pod; a board shorter than 12 mm does not shrink it.
- **4-layer:** already in the area figure (In1 solid GND, In2 signals). No via-in-pad: the draft's 0.35/0.15 mm vias are inside JLC's 0.15 mm hole / 0.25 mm pad minimum, so there is no unused density left in the process.
- **Thickness 0.8 mm is already the minimum** standard 4-layer thickness at JLC (0.8, 1.0, 1.2, 1.6, 2.0; "0.4-4.5 mm" with manual review below 0.6): <https://jlcpcb.com/capabilities/pcb-capabilities>, read 2026-10-02. A 0.6 mm board is rejected (section 9).
- **Part heights vs the 1.2 mm bands** (`part_heights.yaml`, maxima): F: L1 1.00, 10 uF 0603 (C4, C7) 0.90, crystal Y1 0.90, SW1 (C&K KMT022 IP68 tact switch) 0.65 nominal (tolerance not given), MCU 0.60. B: mic 1.08, D4 (1N5819WS Schottky) 1.00, C14 (22 uF 0603) 1.00, 0.1 ohm shunt 0.65, charger U3 (BQ25180, 8-ball chip-scale) 0.65 (a tape-pocket bound), U4 0.40, MOSFET pair 0.40. So F band 1.0 and B band 1.1 are real; the extra 0.2 mm in each is clearance, which SIZ-03 trims only on F.
- **Test access vs size:** the TP row is 6 pads at 1.27 mm pitch (7.6 mm, 6.7 mm2). Moving it to the snap-off frame cannot work for SWD recovery after depanelling (nothing to probe on a bonded pod), so SWDIO, SWCLK, NRST, GND and +3V0 stay as pads; SIZ-10 trims them to 0.5 mm and drops TP6 (periphery PER-11). The "bulky" test items are R21 (1206, 10.2 mm2) and R20 (0 ohm link): the output and power studies own those. Total test-access area is under 5 % of one face, so O20's "must not cost size" is already met except for the J pads' oversized courtyards.

## 5. The dock: the 21.2 mm target, the belly, and the alternatives

### 5.1 Facts from the makers' drawings (LCSC PDFs fetched 2026-10-02; JLC parts API 2026-10-02T05:15-05:32Z)

| Part (what it is) | LCSC, class, stock, price | Body L x W x T | Pins / tails | Notes |
|---|---|---|---|---|
| **Xinyangze YZT0675-20048-05025-01** (pod-side 5-pin magnetic target, today) | C5126848, Extended, 51, $2.38 | 21.20 x 6.86 x 2.80 (+5.03 mm tab, outline 9.17) | 5 at 2.5 mm; Ø0.70 **through-hole tails 2.00 mm long**, Ø1.2 stubs 0.2 | Drawing A.1, 2022-03-24; PA9T housing, 2 NdFeB magnets, **no N/S marking** |
| YZT0675-20048-04025-04 (4-pin, same family) | C42463273, 19, $2.49 | same body | 4 | Periphery PER-01's pick; **no size change** |
| YZ92015035T-04025-01 (4-pin receptacle) | C5126844, 7, $2.02 | 21.20 x 6.86 x 2.80, same tab | 4 at 2.5 | Drawing A.1, 2022-03-24: **four pins in the same 21.2 mm body** |
| YZT0755-20028-02025-01 (2-pin target) | C5280828, 185, $1.11 | **15.06** x 6.86 x 2.80 | 2 | Drawing A.1, 2025-01-13: magnets marked **N and S** (keyed). 2-pin = charge only, kills DFU (O12(a)). A 4-pin sibling is listed (C55607951, 200 in stock) with no drawing: extrapolates to ~20.1 mm (unverified) |
| **YZ103915020T-04025-02** (4-pin, thin) | C6276862, 155, $1.77 | 22.30 x 7.70 x **2.00** (1.5 mm shoulder) | 4 at 2.54; pin backs flush with 0.2 mm stubs, **no tails** | Drawing D.0 dated **2015-07-08** (old); PA46 + 30 % glass; no mating head in JLC; its Ø3.0 magnet pockets are the only polarity info |
| YZR0158-20050-03025-01 / YZP0048 family | C5126841 (80), C5126845 (45), 5-pin head C5126847 **0 in stock** | 21.2 x 6.86 x 2.8 + 3.7 mm contact travel | | Cable-side heads for the 21.2 mm family (periphery §2.1) |

### 5.2 Belly arithmetic

Belly depth below the main body = target thickness + stack behind its back face to the cell bottom - (floor 0.8 + slack under the cell).
- **As drawn:** 2.8 + (2.0 tails + 0.3) = 5.1 under the cell; minus (0.8 + 0.8) = **3.5 mm**.
- **SIZ-06, tails bent flat or trimmed to ~0.5 mm, wire soldered to the stub:** 2.8 + 0.85 = 3.65; minus 1.6 = **2.05 mm** (-1.45 mm, -407 mm3). The 5 tails are Ø0.7 brass; bend them in lanes ~0.9 mm apart so the wires do not cross. Needs a spare target to try; the sample is hand-fitted anyway (not JLC-placed). The dock wires then run in the same 0.8 mm channel under the cell (the S1 geometry keeps it).
- **SIZ-08, thin 2.0 mm target, back flat:** 2.0 + 0.75 = 2.75; minus 1.6 = **1.15 mm** (-2.35 mm, -679 mm3 with its own length). Needs a cable head with four spring contacts at 2.54 mm and two matching magnets. Printed head, ~$2 of parts, the owner's bench can do it, but **unverified**: the old drawing, magnet polarity unknown, no head sold.
- **No belly at all would need** the dock stack to fit in floor 0.8 + slack 0.8 = 1.6 mm; the thinnest option (2.75) does not.

### 5.3 What a 4-pin vs 5-pin choice does to size (coordinate with the periphery study)

Nothing to the envelope: all 21.2 mm family members share one body. It removes one wire from the 0.8 mm channel (5 -> 4: 20 % less fill), one J pad and, if CC goes with it, R18/R19. It is periphery's PER-01; I record it as SIZ-09 so the budget is complete. The belly does not shrink because the body is the same.

### 5.4 Where contacts could sit without a belly (all fail or do not pay)

| Place | Why not |
|---|---|
| Lid face, rivets through the lid | Needs a free ~140 mm2 strip on the F face plus ~2.5 mm of depth under the lid; four wires to J pads under a closed lid; own magnets glued blind; no volume saved against SIZ-08 |
| Pod inner face (dovetail side), cradle charging | Contacts under the adapter; she slides both pods off every night: breaks the O12(a) "snap a cable on" convenience |
| End faces | The 21.2 mm target (or even 15.06 mm 2-pin) exceeds the 13.6 mm cavity height; the 2-pin is charge-only |
| Under the board in the board-free rear zone | The zone (10 x 3.7 mm above the cell) fits a USB-C receptacle, not the 21.2 mm target (section 9, idea 8) |
| Wireless (coil) | Loses USB DFU (O12(a), O18); coil + IC area and heat next to the cell |

### 5.5 Dock-adjacent risks this study found

- The target's mass (0.9 g) and the tail geometry are derived from the drawing; weigh and caliper the sample before freezing the belly.
- The 0.8 mm under-cell channel is the only wire route (sub-dock-usb issue 5); any lever that raises the cell into it (S1+) is rejected for that reason.
- If the tails are bent, the sealing/potting back of the target needs a smaller potting volume (good) but the wire exits must be strain-relieved.

## 6. The cell (full study: `docs/research/tws-power-size.md`; I only price the size)

| Cell | Envelope T x W x L (max) | Capacity | Mass | Runtime at 7 mA / worst case | Size effect |
|---|---|---|---|---|---|
| **Renata ICP501233PA-02 (today)** | 5.3 x 12 x 35 | 175 (170) mAh | 4.2 g | 21.2 h / 12.4 h | baseline |
| Renata ICP401230UPR | 4.5 x 12.7 x 31 | 130 mAh | 3.5 g | 15.8 h / 9.2 h | T -0.8, L -4.0, H +0.7, -0.7 g cell |
| Renata ICP621333PA-01 | 6.7 x 13 x 35 | 240 mAh | 5.5 g | 29.1 h / 17.1 h | T +1.4, H +1.0, +1.3 g |

Source: tws-power-size.md section 3 (Renata datasheets read 2026-10-02; runtimes use 85 % usable and the stacked-worst-case current of 10.55 mA). One millimetre of cell thickness is ~33 mAh, i.e. 2.3 h (worst case) to 4 h (7 mA). The cell is the only lever that trades runtime for size one for one; the E4 current measurement does not exist yet, so the 12 h target and the 8 h floor cannot be traded against it today. **Keep 175 mAh** (SIZ-12 is listed for completeness, not recommended). Swelling margin: SIZ-03 deliberately leaves the B-side gap at 1.4 mm; Renata gives no aged thickness for this pouch.

## 7. Mic port, switch and lid stack

- **Duct** (outer surface to the mic's port): today 0.8 board + 1.5 open gap + 0.9 lid bore + 0.8 hex window = 4.0 mm with a 1.5 mm unsealed gap (sub-audio-in issues 1-2). S1: 0.8 + 1.15 (a sealed chimney from the lid to the board, which SIZ-02's lid-hung board makes natural) + 0.8 lid + 0.7 plate = 3.45 mm. S2: 0.8 + 1.15 + 1.0 = 2.95 mm.
- First-order quarter-wave resonance c / (4 L) with c = 343 m/s, no end correction: 21 kHz (4.0 mm), 25 kHz (3.45), 29 kHz (2.95). **All inside the 20-85 kHz band**; the repo's own note puts the round-1 3.2 mm duct at ~24 kHz (shell.md L214) and spec D13 sees a 25 kHz fixture peak. Shorter is better (spec §8 "short, wide"), and removing the plate buys more duct than any other size lever. `[Low]`: a rough estimate; S1 coupons (R14) measure it.
- **Switch/plunger:** SW1 (0.65 mm) + printed plunger (stem 1.2, head 0.9) + skin recess 0.25 sit inside the lid wall. Lid wall 0.8 + plate 0.7 keeps the recess floor; with the plate off (lid 1.0) a 0.25 mm recess leaves 0.75 mm. The plunger gets ~0.35 mm shorter with SIZ-03 (it must re-set the "head top vs skin" gap, sub-ui issue 1). No size lever lives here beyond the plate.
- **Lid-hung board (SIZ-02):** mic port and SW1 register to the lid through two locating pins on the board centre line, fixing the 2.4 mm slide (reg-pod-body issue 2) and the 0.77 mm port/bore class of error at the root.

## 8. Cross-domain dependencies and owner questions

- **Needs from other studies:** SIZ-01's 26 mm board assumes periphery PER-01..07/11 and power PWR-01/02/08 (-28 and -4.0 -3.5 mm2). If the owner takes none of them, use 28 x 12. The output study (R21 1206, bridge layout) and processing study may shrink or grow it further.
- **Supersedes / builds on ECRs:** builds on ECR-0001 (frame.py drift: the new shell constants must land there, and `heel.py`/`pad.py` re-run), ECR-0006 (dummy pair: print S0/S1/S2 sizes), ECR-0011 (mic port offset: SIZ-02's pins make it a registration, not a tolerance). Makes ECR-0002 items 1-4 moot only with the power study's BQ25186.
- **Owner decisions touched:** O17 (spine stays), O20, O19 (serviceability: SIZ-02 keeps the cut-and-lift service), O16(3) (USB-C keep-out; own head), O12(a) (dock stays magnetic), O10 (cut line: SIZ-02 and SIZ-04 touch the lid), D18, R20.
- **Hardware-only vs firmware-fixable:** every size lever's failure mode is hardware-only (a board that will not route at 12 mm, a part taller than its band, a wire channel that pinches, a thin wall that cracks, a pod that is uncomfortable). None can be fixed by firmware. That is why the protection is the printed wear dummies and the tolerance coupon before the board order, not a firmware knob.
- **Diagnosability (O18):** no lever removes a test hook. SIZ-02 makes the board's B face (mic, charger, bridge) easier to inspect after a cut-open (the board comes up with the lid on its wires). SIZ-10 trims the TP row but keeps SWD, NRST, GND, +3V0. SIZ-01 makes the board denser to probe by hand; the pad list must keep GND pads and one row of test pads.

## 9. Rejected ideas

| Idea | Why not |
|---|---|
| **0.6 mm board** (-0.2 mm, shorter port) | JLC's standard 4-layer thickness starts at 0.8 mm; below 0.6 mm manual review, 0.6 not listed as standard (capabilities page, 2026-10-02). Not worth a custom-stackup order for 0.2 mm |
| **Single-sided board + top-port mic** (Knowles SPK0641HT4H-1: top port, 4.0 x 3.0 x 1.0 mm, JLC C5159510, 68 in stock, $2.81) | Would remove the whole B band: T -1.3 to -2.3 mm and move the heat sources off the cell (R23). But the datasheet (Rev A, 2016) specifies "flat frequency response 20-20 kHz", clock up to 4.8 MHz, **no ultrasonic mode and no response above 20 kHz**; D13 chose the SPH0641LU4H-1 because it is the only JLC-stocked mic characterised to 80 kHz. F1 is the product. Rev 1 is final: not an experiment to run on the real board. Measure it on a coupon if she wants the 2 mm later |
| **Cell beside the board** (in line) | 35 + 26 + walls = 63 mm against 38 mm between the vision line and the Ear (open) hook (spec §8 v0.9) |
| **Cell on edge** (12 mm thick, 5.3 high) | +6.7 mm lateral thickness; the wrong axis for hair and hoods |
| **Stepped thin rear** (lid drops 3.8 mm over the board-free 10 mm) | -640 mm3, but the max thickness (front) is unchanged, the lid and seam become two-plane, the spine would overhang, wire slack route gets longer. More complexity than the simplification rule allows. SIZ-14 gets the stowage benefit without it |
| **Own magnets + rivet contacts through the lid** | Section 5.4: ~140 mm2 of F face, wires under a closed lid, blind magnet pockets, and no volume win over SIZ-08 |
| **USB-C receptacle in the board-free rear zone instead of the belly** (Same Sky UJ32-C-H-G-MSMT, IP68, 6.75 x 8.55 x 2.76 mm; JLC C7136801 **0 stock**, sibling C22359755 255 in stock $2.91) | The only idea that removes the belly entirely (-975 mm3, -12.5 %, ~-1.4 g with the target). It fits the 10 x 3.7 mm zone above the cell with its mouth through the top wall, **but**: O12(a)/O16(3) chose magnetic; the mouth lands under the spine; the plug comes from above while worn; CC (Rd 5.1 kohm + sense) returns, undoing PER-01; and wet contacts on a docked wet pod are the same electrolysis risk. It is the right **fallback if the magnetic sample fails** (keying, mate, sealing): SIZ-01's board-free zone keeps that door open, which is a better use of the keep-out than 7 mm of belly |
| **Wireless charging** | Loses USB DFU (O12(a), O18), coil + IC area, heat next to the cell |
| **Merge the adapter into the tub** (-1.8 mm, 13 % of the thickness; also -0.5 g) | The adapter is her requirement (spec §8 v0.14: swap for new frames without reprinting the pod). A new frame would mean reprinting the whole bonded tub and transplanting cell and board. Revisit only if she would rather transplant than swap |
| **Three coin cells / 240-270 mAh pouches** | Covered by tws-power-size (36.6 mm of cells; +1.4 mm thick) |
| **Hollow heel and spine** | -0.2 g for drain holes in a sealed pod |

## 10. What to do, in order

1. **Print and wear (ECR-0006, extended):** dummies at S0 (as drawn), S1 and S2 sizes, ballasted to 12.4 / 11.9 / 11.6 g at the cell position. Two hours each. Ask: thickness, belly, spine, nose pressure. This costs resin and an evening and decides SIZ-05, SIZ-08, SIZ-11.
2. **Tolerance coupon (tolerances.md "two things"):** add 0.6 / 0.7 / 0.8 mm walls and a 0.15 mm F-gap boss; drop-test the 0.7 mm coupon on tile.
3. **Sample magnets (when the dock target arrives):** weigh it, caliper tails, bend one spare, test N/S keying and a 4-pin head against it, and try the YZ103915 only if she wants SIZ-08.
4. **Layout session (O14):** set the board to 12.0 mm high, 26-28 mm long, two NPTH locating holes on the centre line, four VHB spot keep-outs on F, no clamp bands on B; fix the J-pad courtyards.
5. **Then** update `shell_r1.py` (and `frame.py`/`heel.py`/`pad.py`, ECR-0001) and re-run the checks; this study leaves them untouched.

## 11. Unverified or not done

- Dock target mass (0.9 g), the thin target's tail/stub height (0.75 mm), the 4-pin YZT0755 length (~20.1 mm) and magnet keying: derived or unseen.
- The parts' mass, adapter/misc masses: rough sums. No pod has been weighed.
- Resin wall minimums are the repo's rules (>= 0.6 mm, 0.8 preferred; holes < 0.8 may close); no drop or fatigue data for 0.6-0.7 mm tough-resin walls.
- Renata aged thickness and swelling: no source. Cell lead exit and PCM position (physical issue 10) unknown, so the rear stowage zone is a plan, not a measurement.
- The 43 % density comes from a different netlist (Rev C/D) without clamp bands; layout is the test.
- Web search was not needed; all other facts are repo files, the makers' PDFs and the JLC capabilities page, read 2026-10-02.

## 12. Sources (read 2026-10-02)

- Repo: `hw/mech/shell_r1.py`, `blade.py`, `frame.py`, `heel.py`; `docs/system/physical.md`, `reg-pod-body.md`, `reg-board.md`, `reg-arm.md`, `reg-pad.md`, `sub-power.md`, `sub-dock-usb.md`, `sub-ui.md`, `sub-debug-test.md`, `sub-audio-in.md`, `00-whole.md`, `integration-map.md`; `docs/build/tolerances.md`, `hardware.md`, `bom.md`; `tools/checks/part_heights.yaml`; `hw/pod/draft/summary.json` and `hw/pod/draft_r1/*` (commit 6e93246 and later); `docs/research/tws-power-size.md`, `simplify/periphery.md`, `simplify/power.md`.
- Xinyangze (Shenzhen Xin Yang Ze Electronics) drawings, LCSC PDFs: YZT0675-20048-05025-01 A.1 2022-03-24; YZ92015035T-04025-01 A.1 2022-03-24; YZR0158-20050-03025-01 A.1 2022-03-24; YZ103915020T-04025-02 D.0 2015-07-08; YZT0755-20028-02025-01 A.1 2025-01-13 (earlier-session copy `ultrasonic-scratch/ds/yzt0755.pdf`).
- Knowles SPK0641HT4H-1 Rev A datasheet (2016), LCSC copy C5159510.
- JLCPCB PCB capabilities: <https://jlcpcb.com/capabilities/pcb-capabilities> (read 2026-10-02).
- JLC parts API (`tools/jlc.py`), 2026-10-02T05:15-05:32Z for every stock and price quoted.

## Reproduce

`source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/size_budget.py` (scenarios S0-S6; body volume 7263.2 mm3 calibrates to `shell_r1.py`). Courtyard areas: `pcbnew.LoadBoard(...).GetFootprints()` then `fp.GetCourtyard(layer).Area() / FromMM(1)**2`. Diagram: `bash docs/diagrams/render.sh docs/diagrams/size-stack.svg`.
