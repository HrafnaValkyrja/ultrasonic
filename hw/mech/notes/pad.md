# Transducer pod ("pad") + arm strut: rev 1 = the prototype (2026-09-30)

Source: `hw/mech/pad.py`, built against `hw/mech/frame.py` (worn pose).
- Rebuild: `source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0 python3 hw/mech/pad.py --render`. It takes about 19 s.
- Outputs go to `hw/mech/out/parts/pad/`:
  - STEP for every part; STL for the printed ones.
  - `checks.json`: 25 checks, **all pass** (23:40 build).
  - `pad_views.png`: assembled, exploded, centre section, strut section.
  - `pad_assembly_steps.png`: the six bench steps plus the pad-board pad map.
- The pad-board pad positions are read **live** from `hw/padboard/layout.py` (the electronics agent's file), so a change there re-checks here on the next build.

STLs are in world coordinates (worn pose). Re-orient them in the slicer.

## What it is (one paragraph)
The pad has two resin prints.
- **The CUP** holds the transducer face-down on a 0.6 mm skin wall. A 1 mm contact pad sits on the cup's skin face.
- **The CAP + STRUT** is one print and does five jobs:
  - closes the cup over the tiny pad board;
  - carries the LED ring (cast epoxy diffuser around a printed opaque centre plug, in a raised hex bezel);
  - holds the NiTi wire in a socket with a set screw, inside a hex "jack" collar;
  - shrouds the wire up to s = 3 mm with a rigid, chamfered, tapered rectangular strut whose top face is raked;
  - runs the 4 arm conductors in their own channel.

The NiTi does all the flexing. The strut never touches it in any of the four states. One M1.2 screw at the bottom end closes the pad, and a claw at the top end hooks into a window in the cup.

Styling (Blade language):
- the hex bezel round the LED ring, with a hex "pupil" dimple in the plug;
- an armour plate on the bottom end with a circuit-trace chevron groove and two "vias";
- a hex counterbore for the screw head;
- V panel lines on the cup's long sides and at the cup/cap seam;
- the hex jack collar where the strut lands;
- 0.4 chamfers on the strut and a 13° rake on its top.

The pad does not grow upward (Ear (open) side).

## Parts list
| # | Part | Qty | Made / bought | How it is fixed |
|---|---|---|---|---|
| 1 | **Cup** (`pad_cup.stl`) | 1 | printed, resin | Hooked to the cap at the top end, one screw at the bottom end |
| 2 | **Cap + strut** (`pad_cap_strut.stl`) | 1 | printed, resin, one piece | On the NiTi by the set screw; closes the cup |
| 3a | **Contact, default:** silicone disc Ø8 × 1.0 mm, Shore A 30–40, punched from sheet with an 8 mm hollow punch | 1 | bought sheet | Thin smear of RTV silicone (room-temperature-curing silicone adhesive) on the cup's skin face. Peels off to swap |
| 3b | **Contact, rigid "strut-style" variant** (`pad_contact_rigid.stl`): 6 × 8 × 0.9, chamfered | 1 | printed | 0.1 mm thin double-sided tape (not foam: foam damps the vibration). Pries off |
| 4 | **Transducer RC-BC02:** the bone-conduction exciter from spec D7, 6 × 4 × 12.6 mm per its larger listing. Leads unknown | 1 | bought | Slide fit in the cup (0.15/side), clamped by the board. Two dots of RTV on its long sides stop lateral buzz |
| 5 | **Pad board:** 5.0 × 9.3 × 0.8 mm PCB, JLC (can share the pod board's panel); layout `hw/padboard/` | 1 | JLC | Clamped between the transducer's back and the cap's recess. Six solder pads (below) |
| 6 | **LED: Everlight 16-213/BHC-AN1P2/3T,** a 0402 (1.0 × 0.5 mm) blue chip LED, JLC/LCSC part C131223 | 1 | JLC-placed at the board centre | Soldered by JLC |
| 7 | **Brass nut M1.4,** DIN 934 (the standard hex nut), 3.0 mm across flats × 1.2 thick | 1 | bought | Drops into a slot in the collar; the set screw keeps it there |
| 8 | **Set screw M1.4 × 2,** cup point, 0.7 mm hex socket | 1 | bought | Through the nut, onto a filed flat on the NiTi |
| 9 | **Eyeglass screw M1.2 × 4,** pan head. M1.2 × 5 also fits | 1 | bought | Through the cap's nose, self-tapping into a Ø0.95 pilot in the cup |
| 10 | Clear epoxy, slow-cure (30 min or 24 h), plus a speck of white pigment | ~0.02 ml | bought | Cast into the LED ring |
| 11 | PE film disc Ø7 (a scrap of sandwich bag; epoxy doesn't stick to polyethylene) | 1 | — | Laid over the LED before casting, so the cast ring releases from the board |
| 12 | 4 conductors, ~0.25–0.3 mm OD, PTFE-insulated or litz | 4 | bought | Soldered to the board's top-row pads; run up the strut's channel |
| 13 | NiTi wire Ø0.80 (arm module) | — | bought straight, superelastic | 3.5 mm in the socket; set screw on a 0.1 mm flat |

Mass per pad: about **2.1 g**, of which 1.2 g is the transducer (an estimate; E1 weighs it).
- Resin: 0.27 g cup + 0.37 g cap/strut.
- Board 0.07 g, silicone 0.06 g, hardware 0.14 g, epoxy 0.02 g.

## Pad board pads (top face): wiring
This is the layout in `hw/padboard/layout.py` as of 23:37, read live by pad.py. Picture: the right-hand panel of `pad_assembly_steps.png`.
- **Top end: one row of four SMD pads, each 0.7 × 1.8,** under the strut's channel exit.
  - From front to rear: OUT_B, LED−, LED+, OUT_A.
  - They connect 1:1 to the pod board's wire pads of the same names (`frame.WIRE_PADS`).
  - OUT_A/B are the bridge outputs.
  - LED+ goes to VSYS through R14 (VBAT before Rev D); LED− goes to PB7 (PWM), as in `docs/research/pad-led.md`.
- **Bottom end:** two plated through-holes, a Ø0.45 drill in a Ø0.85 pad, at (±1.775, 3.275) in KiCad coordinates. They take the transducer's two leads (XDCR_A/B).
- **Solder each arm wire on the TOP half of its pad,** toward the board's top edge.
  - The cap's printed dam (r 3.25 around the LED: the ring's outer wall that presses the PE film) covers the lower 0.1 mm of the pads.
  - The usable lap outside the dam is 1.36–1.8 mm per pad.
- **Joints must stay ≤ 0.45 mm tall.** The pocket roof is 0.5 above the board, so a joint that height has 0.05 mm to the cap; a higher one stops the cap seating.
  - Trim the transducer leads flush under the board and keep those joints small.
  - The PTH pad's inner edge is at r 3.30, only 0.05 outside the dam.
  - **Dry-fit the cap before driving the screw.**

## Tools
- Pin vise and drills: 0.85, 0.95, 1.0, 1.4 and 1.6 mm. For 0.75 or 0.85 mm wire (T5), use wire + 0.05.
- 0.7 mm hex key.
- Eyeglass screwdriver.
- Diamond needle file (for the flat on the NiTi).
- Fine-tip soldering iron, flux, 0.3 mm solder.
- Tweezers and toothpicks.
- 1 ml syringe with a blunt 25G needle (0.51 mm OD) for the epoxy.
- Scalpel, 8 mm hollow punch, isopropyl alcohol (IPA).

## Printing (resin, MSLA)
- **Cup:** tilt it about 30°, with the open rim toward the build plate and supports on the rim and the outer bottom end. The skin face prints last and stays clean, which matters because it touches the skin.
- **Cap + strut:** the underside (pockets, recess) faces the plate, with supports there. Tilt it so the strut runs at about 45°.
  - All channels are open at one end for drainage.
  - Flush the socket and the conductor channel with IPA from a syringe before curing.
- **Rigid contact:** the skin face prints last (no supports on it).

After curing, ream with the pin vise:
| Feature | Drill | Depth / note |
|---|---|---|
| Cup screw pilot | 1.0 | 3.4 mm, no deeper: leaves a 1.2 mm floor under the skin face (1.0 since 2026-10-07, PAD-5: 0.95 splits the boss) |
| Cap closure hole | 1.4 | Through |
| NiTi socket | 0.85 | Push the drill down the strut's channel from its top. It runs straight, 3.5 mm past the mouth |
| Conductor bore | 1.2 | From the strut top straight into the riser (~10 mm), on the strut's REAR side; then a 1.6 drill 1.7 mm deep at the top for the shrink-tube counterbore |
| Set-screw hole | 1.6 | From the collar's set-screw flat, through the wall and the nut slot, **stop when the drill reaches the socket** (feel it break through; the conductor bore lies beyond the socket: never drill past it) |

## Tolerances built in
- **Transducer:** cavity 6.3 × 12.9 for a 6.0 × 12.6 part (0.15/side).
  - Too loose: a strip of Kapton tape on one side.
  - Too tight: sand the cavity walls.
- **Board recess:** 0.15/side. Depth = board thickness, 0.8 nominal. JLC's tolerance is ±10%, so 0.72–0.88.
  - If the cap rocks: sand the recess ceiling.
  - If the board rattles: one layer of Kapton under it.
- **LED:** 0.45 tall plus 0.03 solder, so its top is at y 3.88. That height is the Everlight datasheet's, as cited in `hw/padboard/mech.py`; frame.py's 3.75 is too low.
  - The plug's underside sits 0.10 above the LED.
  - The ring is 0.6 wide: a Ø4.1 plug in a Ø5.3 cavity.
- **Socket:** Ø0.85 for a Ø0.80 wire. Lead-in Ø1.1 → 0.85 over the first 0.3 mm.
- **Nut slot:** 3.1 × 1.3 for a 3.0 × 1.2 nut. The slot walls stop it spinning.
- **Hook:** claw tip 0.45 thick in a 0.6 window; 0.1 gap between the claw and the cup's end face.
- Every wall ≥ 0.6 mm, checked: 68 wall/web measurements, minimum exactly 0.60.

## Assembly order (see `pad_assembly_steps.png`)
1. **Prepare the NiTi end:**
   - File a flat 0.1 mm deep and 1.5 mm long, starting 0.75 mm from the pad end.
   - Mark the flat's direction with a marker line along the wire.
2. **Thread the conductors** from the cap's underside: up the riser pocket (front side), into the Ø1.0 channel, and out of the strut top. Leave ~25 mm out of the top for the flex zone and heel, and ~12 mm hanging under the cap.
3. **Solder the board:**
   - 4 conductors to OUT_B, LED−, LED+, OUT_A, on the pads' top halves. The two rear wires (LED+, OUT_A) cross the centre line above the dam, or under the collar through the 0.35 mm wire path at the board's top end.
   - Transducer leads through XDCR_A/B, trimmed flush.
   - Test the LED now: 3–4 V through ~2 kΩ.
4. **Transducer into the cup**, face down, plus two RTV dots on its long sides. Then fit the contact pad on the skin face: RTV for silicone, tape for the rigid one.
5. **Board on the transducer back**, LED up. Lay the PE film disc over the LED area.
6. **Nut:** drop the brass nut into the slot on top of the collar. Its corners point up and down; the slot forces this. Put a scrap of tape over the slot so it can't fall out.
7. **Close:**
   - With the cup's bottom end tilted ~6° away from the cap, hook the claw tip into the window in the cup's top end wall.
   - Swing the bottom end shut, tucking conductor slack into the front pocket. **Dry-fit first:** the cap must sit flush with no rocking (solder joints).
   - Drive the M1.2 × 4 screw: snug, not hard (resin threads).
   - The swing is checked collision-free at 2, 4, 6 and 8°.
8. **Cast the LED ring:**
   - Prop the pad cap-face up and level.
   - Mix slow epoxy with a speck of white.
   - Inject it through the 0.6 mm ring from one side with the blunt needle until it wells up all the way round. Air leaves through the rest of the ring.
   - Top up flush with the bezel and cure 24 h.
9. **NiTi:**
   - Slide the wire's pad end into the strut's raked top opening, flat toward the **rear** (the set-screw side), down to the bottom of the socket (3.5 mm).
   - Drive the M1.4 × 2 set screw with the 0.7 key until it bites the flat, then a quarter turn more and no further.
10. **The arm's other end goes into the heel** (heel module notes).
    - The 4 conductors leave the strut top through the Ø1.6 counterbore on the **REAR side** of the NiTi and cross the 3 mm flex zone inside the pre-shrunk tube as a loose S (~2 mm slack) into the heel's counterbore (current route, fixed 2026-10-01; notes corrected 2026-10-07, reg-arm issue 7). They never cross over the NiTi.
    - Put a dab of RTV at the strut exit.
11. **Bench check:**
    - The ring glows evenly.
    - The transducer plays without buzz.
    - Pad force on a kitchen scale (T5).

## Disassembly order
1. **Off the wire:** loosen the set screw half a turn with the 0.7 key and pull the pad off the wire. It still hangs on its 4 conductors.
2. **Open the pad:** remove the M1.2 screw. Tilt the cup's bottom end away ~8°, slide the cup 0.5 mm toward its bottom end to unhook the claw, and lift it off. This path is checked collision-free.
3. **Transducer out:** lever its top end up through the hook window with a toothpick and cut the RTV dots. The board lifts out with it, on its wires.
4. **LED ring:** the cast ring stays in the cap. The PE film lets it release from the board, and the LED stays on the board.
5. **Desolder only what you're swapping:** the transducer (XDCR_A/B) or the 4 conductors.
6. **Nut:** with the set screw out, the nut drops out of its slot.
7. **Contact pad:** peel it (silicone) or pry it off (rigid).

## Where it sits (numbers)
**Thickness from the skin:**
| Point | Thickness |
|---|---|
| Cap face | 7.5 mm |
| LED bezel / armour | 7.9 mm |
| M1.2 head | 8.3 mm |
| **Collar top** | **10.6 mm** |
| Rev 2 housing + silicone, for comparison (no LED, no strut) | 6.4 mm |

**Height toward the Ear (open):**
- **Pad body top** (cup + cap + hook): world z −17.24, vs about −17.5 for rev 2's housing.
  - The top-rear corner is cut on a line of constant world z: the transducer cavity corner + 0.6 mm wall.
- **Collar's top-rear:** z −16.1, about 1.4 mm higher than rev 2's pad corner.
- **The strut's rear face** is 1.3 mm behind the wire, vs 1.1 for rev 2's sleeve.
- The integrator should re-check Ear (open) clearance with `pad_cap_strut.step`.

**Length:**
- The body runs 16.35 mm along E3 (rev 2: 14.2).
- The extra length is at the **bottom**: the hex nose that holds the closure screw. The pad's bottom is about 1 mm lower (z −33.7).
- Nothing grows upward except the hook's 0.7 mm hood, at the middle of the top end.

**Strut:**
| Point | Size |
|---|---|
| Top end (s = 3) | 4.2 wide (lateral) × 3.35 deep (outward) |
| At the collar | 4.2 × 2.65 |
| Length | 8.9 mm on the inboard edge, 8.1 on the outboard edge |

- Chamfers: 0.4 on the long edges.
- **Top face raked 13°:** its inboard edge is at s = 3 (`frame.STRUT_START`) and its outboard edge is 0.8 mm lower.
  - The rake clears the pod's lower-inner edge. That edge was 1.24 mm from the strut and is now 1.58 (heel note H3).
  - It doesn't thin any wall; it only shortens the outboard wall.

**Strut vs the heel's outputs** (heel STEPs from 20:39, read-only):
| State | Strut to heel | Strut to tub (shell edge) |
|---|---|---|
| Worst case | 1.72 | 1.58 |
| Required | 1.4 (`SHROUD_CLEARANCE`) | 1.4 |

## Checks (all in `checks.json`, all pass)
- **Parts:** every printed part is one solid. The printed STLs, re-read from disk, are closed manifolds: every edge is shared by exactly 2 triangles.
- **No overlaps** between any two parts (11 bodies), with either contact variant.
- **Fit with the cap closed** (contacts read 0):
  - transducer face on the skin wall;
  - board on the transducer;
  - board under the cap;
  - LED 0.10 below the plug, 0.02 under the epoxy (the film).
- **Pad-board solder joints vs the cap's pockets**, using the live layout:
  - SMD laps 1.36–1.8 mm outside the dam (limit ≥ 1.0).
  - PTH joints clear the dam; no joint touches the cap.
- **Socket inside material:** wall ≥ 0.86 to the outside.
- **Strut vs NiTi, all four states:**
  - Minimum gap 0.13–0.15 mm. That is the designed 0.15 at the socket mouth.
  - Top region (s = 0–6 mm): 0.21–0.25 mm. Overlap 0 in every state.
- **Screws:**
  - M1.2 × 4: 2.1 mm of thread in the cup (× 5: 3.1 mm); 1.2 mm floor under the pilot.
  - Set screw: full 1.2 mm nut engagement. Its driven end sits 0.65 below the collar flat.
- **Walls:** 68 measurements, all ≥ 0.60.
- **Swing-close and unhook:** collision-free.
- **Heel and shell clearance:** ≥ 1.4 in all states, as tabled above.
- **Mass:** listed above.

## Options (owner decides)
**A. Strut cross-section.** You asked for ~3.2 × 2.4. It does not fit, and the reason is simple geometry:
- Relative to the pad, the wire moves only outward (+b1), by up to 0.70 mm at the strut top (jaw closed). It never moves sideways.
- So the wire slot needs ~1.95 mm of depth. Add 0.6 mm walls and a separate Ø1.0 conductor channel beside it.
- **A1 (built, recommended):** conductors beside the wire, on the front side.
  - 4.2 × 3.35, tapering to 4.2 × 2.65.
  - Tidy and sealed. The rear (ear-side) face stays 1.3 mm from the wire.
- **A2:** conductors outside the strut, in a thin silicone tube alongside it.
  - The strut drops to ~2.6 × 3.15, tapering to 2.35. It can be printed 3.2 wide for the look.
  - The wires are exposed for ~9 mm.
- (Design history, superseded 2026-10-01 by the rear-side bore; not build instructions.) **A3:** conductors under the wire, on the head side.
  - 2.5 × 4.7: a deep fin that brings the inner face ~1.4 mm closer to the head. No.
- **Not done: the heel agent's request** to put the conductor exit at the strut's rear-inboard corner. I measured it.
  - Mirroring the strut so the channel sits behind the wire moves 1.6 mm of strut rearward and up.
  - It then comes within 0.20 mm of both the heel and the tub in every state; 1.4 is required.
  - The front exit plus a loose loop on the head side of the wire costs nothing.

**B. Collar height** (10.6 mm from the skin):
- **Cause:** the frame puts the socket entry T 0.7 mm *above* the cap face, and the worn wire's end tangent dives outward 19°. Anything holding a 3.5 mm socket therefore stands ~3 mm proud.
- **B1 (built):** the frame as it is.
- **B2 (recommended to evaluate):** lower T by ~1.5 mm in E2 in `frame.py`.
  - The collar drops to ~9.1 mm.
  - It costs a re-solve of the heel axis and SPAN, and the hook moves.
- **B3:** a 2.5 mm socket. It saves ~0.4 mm but grips less wire. No.

**C. Contact:**
- **Silicone Ø8 (default):** comfort.
- **Rigid printed foot:** probably better high-frequency coupling.
- Try both in E2; swapping takes a minute.

## Open risks (blunt)
1. **The transducer's leads are unknown.**
   - The design assumes they leave the transducer's back face and go straight up through the board's two PTH holes.
   - If they leave an end face, there is no room: only 0.15 mm of clearance, and the web to the screw pilot is 0.78 mm.
   - Measure the part (E1) before printing.
2. **Solder-joint height is the tightest fit in the pad.**
   - Every joint has 0.05 mm to the cap by design (≤ 0.45 tall in a 0.5 pocket).
   - The PTH pads sit 0.05 outside the dam.
   - A fat joint means a cap that rocks: re-flow it thinner or relieve the pocket with a scalpel.
3. **Stack tolerance:** the transducer's thickness tolerance is unknown, and the board's is ±0.08. Either can cause rattle (buzz) or a cap that won't close flush.
   - Shim with Kapton or sand.
   - Add the RTV dots.
   - If coupling is weak in E2, bond the face with a thin epoxy film (permanent).
4. **Resin threads for the M1.2** are good for about 10 open/close cycles.
   - Fallback: drill the pilot to 1.1 and the cap to 1.6, and use an M1.4 × 4. The counterbore already takes an M1.4 head.
5. **Filing NiTi is slow;** use a diamond file.
   - Without the flat, the cup point may not bite the hard wire.
   - The flat is also the positive pull-out stop.
   - No epoxy goes in the socket, so it stays removable.
6. **The 3 plug spokes are fragile** (0.45 × 0.5 mm) until the ring is cast. If one breaks, tack the plug with CA (superglue) on a 0.45 mm shim, then cast.
7. **Epoxy in a 0.6 mm ring:** use slow, low-viscosity epoxy, slightly warmed. It may need two top-ups.
8. **The collar and strut are bulky** (options A and B).
   - The collar's top-rear is ~1.4 mm higher than rev 2's pad corner.
   - The Ear (open) clearance must be re-checked on the real STEP.
9. **The wire model is borrowed:** `arm_geometry.json` uses an unsourced lower plateau.
   - If the real wire bends more, the slot has 0.20 mm of margin at the strut top (jaw closed), and 0.25 on the inner side in the free state.
   - If the bench (T5) shows rubbing, open the slot outward. There is 0.6 mm of wall there; going to 0.5 is a deliberate exception.
10. **The heel and tub numbers come from the heel agent's 20:39 STEPs.** Re-run `heel.py` so its own H3 check sees the raked strut. heel.py imports `build_strut()`, so it picks up the rake automatically.
