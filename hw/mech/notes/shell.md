# Pod shell: tub + lid (two resin prints)

> **Superseded in parts (banner 2026-10-07, reg-arm 7 / DK-13 / UI-9 / DBG-10):** this is the pre-rev-1 shell (shell.py, frozen as PRE_R1); the current shell is shell_r2 (notes/shell_r2.md). Current truth: `hw/current.yaml` and `docs/system/`. Kept as history; do not build from the superseded parts.

2026-09-30 · source `hw/mech/shell.py` · interface `hw/mech/frame.py` · numbers `hw/mech/out/parts/shell/checks.json`

![sections](../out/parts/shell/shell_sections.png)
![lid slide-on](../out/parts/shell/shell_lid_slide.png)

## Blunt summary

**As specified, the shell can't be built.** The task put PCB ledge ribs in the tub and nut bosses at
`frame.LID_SCREWS` x = 60.8. Both sit over the cell's footprint, above the cell (y >= 9.9). The cell
(LP401230, an EEMB ~105 mAh LiPo pouch, MAX envelope 12.5 mm tall) has to drop in from the open side:
- the ledges leave only **10.4 mm** for a **12.5 mm** cell;
- the x = 60.8 bosses hang over the cell's rear end and the PCM (protection circuit module, the small
  board welded to the cell's tabs).

The printed tub would therefore trap the cell; there's no order of assembly that gets it in.
`checks.json` → `as_frame.cell_insertion_corridor`: 148 mm³ of tub inside the cell's drop-in path.
That variant is still exported, to `out/parts/shell/as_frame/`, so you can see it.

**What I built instead ("proposed", the top-level STEP/STL):**
- The **tub is an empty box**, apart from features outside the cell's path: a front cap (the hook), two
  tiny PCB front stops in front of the cell, and the two nut bosses **behind** the cell.
- The **lid locates the PCB**: ribs press its outer-face clamp bands, webs locate its edges, and rear
  stops set it in x.
- Two **foam strips on the cell** push the PCB up against the lid.
- The lid goes on **0.45 mm behind its seat** and slides forward, so a tongue hooks under the tub's front
  cap. The PCB rides along, so the chimney, washer, button nub and tongue never scrape across the board.

This needs two frame changes you have to approve (status **USER_REVIEW**):
1. **PCM folded flat on the cell's rear top face** (placeholder x 57.4..61.4, y 9.75..11.95). Measure the
   real PCM first (B4).
2. **Lid screws move behind the cell**, to (x, z) = (64.2, 2.7) and (64.2, -5.6). The lower one rises
   0.8 mm so its counterbore clears the armour edge. The circuit-trace groove now ends in the VBUS screw
   head, which looks intentional.

## Parts

| # | Part | Made / bought | Fixed by | Removed by |
|---|---|---|---|---|
| 1 | **Tub**: inner face + top/bottom/front/rear walls to y 13.4, dovetail rail + catch bump (`blade.rail`), front cap, 2 PCB front stops, 2 nut bosses | resin print | slides onto the frame adapter's dovetail; the adapter's snap tab clicks over the catch bump | push the adapter tab's foot toward the head, slide the pod forward |
| 2 | **Lid**: 0.9 wall + Blade armour + trace groove + dorsal fin + button flexure + mic chimney + PCB ribs/webs/rear stops + front tongue | resin print | front tongue under the tub's front cap (0.35 mm), 2 screws at the rear | 2 screws out, slide back 0.45, lift |
| 3 | 2 × **M1.4 × 3 mm** pan/cheese-head eyeglass screws | bought | thread into the brass nuts; heads flush in Ø2.8 × 0.9 counterbores | eyeglass screwdriver |
| 4 | 2 × **M1.4 brass hex nut, DIN 934** (the standard metric hex nut; s 3.0 across flats, m 1.2 thick) | bought | captured in side-entry pockets; the screw pulls each nut against a 0.8 mm roof | slide out of its slot with tweezers |
| 5 | **Cell** LP401230 + PCM | bought | 0.3 mm double-sided foam tape to the tub's inner wall; nothing in the tub overhangs it, by design | plastic spudger from the rear, never metal |
| 6 | 2 × **foam strips**, closed-cell PE foam about 1.5-1.6 mm thick, cut 1.1 × 17.5 mm | bought sheet, hand cut | own adhesive, on the cell's top face along its top and bottom edges, x 32..49.5 | peel |
| 7 | **Mic washer**, Ø3.0 / Ø1.0 punched from 0.8 mm adhesive closed-cell foam | hand punched | stuck to the chimney tip, squeezed 0.2 onto the PCB around the port | peel, replace (it's a consumable) |
| 8 | 2 × 30 AWG silicone wire, about 35 mm | bought | soldered to each nut **on the bench**, then to VBUS / GND_CHG pads on the PCB's rear edge | desolder at the PCB |
| 9 | PCB (20 × 11.5 × 0.8) | JLC | located by the lid (ribs 0.05, webs 0.2, rear stops 0.05), sprung by item 6 | lift out by its edges once the lid is off |

Glosses: **KXT321LHS** is the C&K KXT3-series SMD tact switch (3.0 × 2.0 × 0.6 mm, 0.25 mm travel,
1.6 N). The **screw heads are the charge contacts**: the upper one is VBUS, the lower one is GND_CHG.

## How the lid works (section x = 64.2 and the slide figure)

- **Nut pockets.** The hex pocket has a **roof (0.8 mm) toward the lid** and opens **sideways** into the
  wire gap between the two bosses (z -3.4..0.5): the upper nut slides **up** into place, the lower one
  **down**.
  - The task asked for pockets "open toward the lid". That doesn't work: the screw pulls its nut
    *toward* the head, so a nut in a pocket open to the lid would lift out and clamp only the lid. The
    tub would just hang there.
  - A side-entry pocket is the only shape where tightening clamps lid to tub. It also keeps the nut and
    its wire replaceable.
- **Screw.** M1.4 × 3: full 1.2 mm thread engagement (4 pitches). Tip at y 11.2, blind hole to y 10.5.
  The longest safe screw is 3.6 mm. The bosses are behind the cell, so a too-long screw cannot reach the
  LiPo.
- **Front hook.** The tongue (0.65 thick, 5.7 wide) sits 0.35 mm under the cap. The cap is 0.9 thick and
  overhangs the front wall by 0.5. The screws' 0.1 mm radial play can't unhook it.
- **Button flexure.** The small upper armour plate is the tongue, behind a 0.4 mm U-slot through lid +
  armour. Its front 1.6 mm is thinned to a 0.6 mm hinge from the inside, so the outer surface stays whole.
  - Pressing it: nub gap 0.05 + switch travel 0.25 = 0.30 mm. Hinge strain **1.0%**. Finger force at the
    button about **2.1 N** (0.5 N hinge + 1.6 N switch). The tail of the tongue dips 0.47 mm, a clear
    "press here".
  - The underside is relieved 0.45 mm, so even fully pressed it stays 0.28 mm off the 1.2 mm part
    envelope.
  - **Print the lid in tough / ABS-like resin.** Standard brittle resin may fatigue at the hinge.
  - The upper plate grew 1.1 mm rearward and its top dropped 0.1 mm so it covers the switch. The slot
    stays 0.78 mm from the mic's hex window.
- **Mic.** Ø1.0 port through the lid with a chimney (OD 2.6) down to y 12.5. The foam washer seals
  chimney to PCB with no open cavity (spec §8). Nothing slides across it during assembly.

## Assembly order (bench)

0. **Prep.**
   - Wash and cure both prints.
   - Ream with a pin vise: lid screw holes and boss holes **Ø1.6** (boss holes are blind; stop at the
     floor), mic port **Ø1.0** through lid + chimney.
   - Clear the button slot with a 0.3 mm shim; the tongue must flex freely.
   - Test-fit both nuts in their pockets (file the slot mouth if tight). Test-slide the tub on the frame
     adapter.
1. **Arm / heel** (heel.py's note). Route the transducer and LED wires up the rear wire gap
   (x 62..66.7, under the lower boss, then between the bosses).
2. **Charge nuts.**
   - Tin about 2 mm of each wire. Solder it to a flat next to one vertex of a brass nut, **on the bench**
     (resin softens at about 60-80 °C).
   - Push the VBUS nut up into the upper boss and the GND_CHG nut down into the lower boss, wire
     trailing into the gap. Optional: a dot of RTV at each slot mouth so they stay put with the lid off.
3. **Cell.**
   - PCM folded flat on the cell's rear top face, with Kapton under it. **Short-circuit risk: insulated
     tweezers, one tab at a time.**
   - Foam tape on the cell's inner face.
   - Lower the cell about 0.3 mm behind its seat so its front end clears the front cap's 0.2 mm lip.
     Slide it forward (0.3 mm gap to the front wall stays) and press it onto the inner wall.
4. **Foam strips** on the cell's top face, flush with its top and bottom edges, x 32..49.5.
5. **PCB.**
   - Solder all 8 rear-edge wires on the bench (OUT_A/B, LED±, BAT±, VBUS, GND_CHG). Leave enough length
     that the board can lie flipped beside the pod.
   - Lay it on the foam strips, MCU side out, mic end forward, about 0.5 mm back from the front stops.
6. **Mic washer.** Push a Ø1.0 drill shank through the lid's port from outside, thread the washer on,
   stick it to the chimney tip, pull the shank.
7. **Lid.**
   - Lower it about 0.45 mm behind its seat: the webs straddle the PCB edges, the washer lands around
     the port, the nub sits over the switch.
   - Press lightly (the foam gives) and **push forward** until it stops (0.15 mm seam at the front cap).
     The tongue goes under the cap, and the lid's rear stops push the PCB onto the tub's front stops.
8. **Screws.** M1.4 × 3 into the counterbores. **Snug only**: resin creeps, and the nut does the work.
9. **Test.**
   - The switch clicks once per press and never with the lid just closed.
   - Continuity: VBUS head ↔ PCB VBUS, GND_CHG head ↔ GND_CHG.
   - The seam is even all round.
10. Slide the pod onto the frame adapter from the front until the tab clicks.

## Disassembly order

1. Fingernail on the adapter tab's foot, slide the pod forward off the adapter.
2. Remove both screws.
3. Pull the lid **rearward 0.45 mm** (thumbnail on the fin), then lift. The PCB stays on its foam.
4. Lift the PCB by its edges and lay it flipped beside the pod on its wires.
5. Nuts slide out sideways with tweezers.
6. Cell: plastic spudger from the rear. Lift it 0.3 mm rearward to clear the front lip.

## Tools

Pin vise with Ø1.0 and Ø1.6 drills; eyeglass screwdriver (fits M1.4 heads); fine tweezers (one pair
insulated); fine-tip iron, flux, 30 AWG silicone wire; Ø1.0 and Ø3.0 punches (leather or biopsy);
steel rule and fresh blade (foam strips); 0.3 mm feeler/shim; needle files and 400-800 paper; Kapton
tape (0.05-0.1 mm); RTV.

## Fits and tolerances (resin, frame.RESIN)

| Interface | Nominal | Tune if needed |
|---|---|---|
| Lid on tub rims (y 13.4) + boss roofs | contact | sand rims flat |
| Front cap ↔ lid face (outer seam) | 0.15 | n/a |
| Tongue ↔ cap underside / front wall | 0.05 / 0.15 | file the tongue's top if the lid won't slide |
| Lid rib ↔ PCB outer face | 0.05 | Kapton on rib tips if the PCB rattles |
| Lid web ↔ PCB top/bottom edge | 0.20 | n/a |
| PCB ↔ tub front stops / lid rear stops | 0.05 / 0.05 | file stops |
| Nub ↔ KXT321 top | 0.05 | sand nub if it pre-presses; 0.05 Kapton dot if dead |
| Nut pocket | AF 3.1 / 1.35 tall for s 3.0 / m 1.2 | file slot mouth |
| Screw clear / counterbore | Ø1.6 / Ø2.8 × 0.9 | ream |
| Fin underside ↔ tub top | 0.05 | n/a |
| Chimney tip ↔ PCB | 0.6 (0.8 washer squeezed 0.2) | thinner or thicker foam |

**Foam strips are the one "spring" in the stack.**
- Too soft: the button press sinks the PCB and feels mushy. The cell is the last stop, 0.2 mm under the
  inner-face parts.
- Too firm or too thick: the lid bows and the mid-seam opens. With its ribs the lid is stiff
  (estimated 0.05 mm bow at about 4 N), but start with about 1.5 mm closed-cell PE foam and adjust.

**Printing.**
- Tub: rear/bottom outer faces toward the plate, tilted about 30°. Never support the rail, the seam rims
  or inside the nut slots.
- Lid: inner face toward the plate, tilted 30-45°. Supports on the flat inner areas and the front edge
  only, never on the nub, the chimney tip, the rib tips or in the 0.4 slot. Sand support marks flat.

## Checks (`checks.json`, proposed variant)

| Check | Result |
|---|---|
| Tub/lid overlap with cell, PCM, tape, PCB, PARTS_IN, PARTS_OUT, button, washer, foam | **0 mm³** (all) |
| Tub ∩ lid, seated | **0 mm³**. Lid sits on rims; fin 0.05 above the tub |
| Lid slide-on (lowered 0.45 behind, slid to 0) vs tub, cell, PCM, nuts, foam | **0 mm³** at 0.45 / 0.30 / 0.15 / 0 |
| Cell drop-in corridor | clear if lowered 0.3 behind its seat (0.2 lip of the front cap at its seat) |
| Min gaps | lid ↔ PARTS_OUT 0.05, lid ↔ PARTS_IN 0.55, tub ↔ cell 0.3, nub ↔ switch 0.05 |
| Nut-pocket walls | roof 0.8, floor 1.35 (0.6 under the blind hole), sides 0.65, closed end ≥ 1.0 |
| Thread engagement | 1.2 mm = full nut, 4 pitches |
| Hinge | 0.6 thick × 1.6 long, strain 1.0%, 2.1 N finger force |
| Heel region (x 50..68, z < -4.3, y < 6.3) | no bosses. The dovetail rail (blade) does reach in: 6.6 mm³, flagged to heel.py |
| Frame adapter (`blade.adapter`) | 0 overlap with tub and lid |
| Mass | tub 1.59 g, lid 1.11 g (resin 1.18 g/cm³ [Low]) |
| Service-loop space behind the PCB | 534 mm³ |

The `as_frame` variant, for comparison:
- cell corridor blocked: 148 mm³ (ledges plus bosses);
- with the PCB in the tub, the 0.45 mm hook slide drags lid features through PARTS_OUT (1.06 mm³ at
  the start);
- status **BLOCKED**.

## Decisions for you (options, my pick first)

**S1 (blocking): getting the cell past the screw bosses.**
- A **(recommended, built):** fold the PCM flat onto the cell's rear top face and move the screws to
  x = 64.2, behind the cell. One frame change; the tub prints in one piece.
- B: buy the bare cell and put protection on the pod PCB: a DW01A-class single-cell Li-ion protection
  chip plus a dual N-MOSFET. That's a schematic change (`hw/pod/gen.py`), and nobody has checked
  whether the board has room.
- C: keep the frame and add a third print, a nut-and-PCB carrier dropped in after the cell and hooked
  under the front cap and a rear-wall ledge. More parts, more tolerance stack, a weaker load path. Not
  recommended.

**S2: what holds the PCB.**
- A **(built):** lid locates it, foam strips on the cell spring it.
- B: snap fingers in the lid hold it inside the lid. 2.7-4% strain, the finger sits 0.05 mm from the
  top wall, and you need tough resin.

**S3: nut pocket.**
- A **(built):** side entry with a roof.
- B: pocket open toward the lid, nut epoxied in. Permanent, and the screw then pulls against the glue
  bond.

## Open risks

- **Acoustic duct is 3.2 mm long** (PCB 0.8 + washer 0.6 + chimney 0.9 + lid 0.9). That's a
  quarter-wave resonance near **24 kHz** and three-quarter-wave near **71 kHz**, both inside the
  20-85 kHz band (R14). The S1 coupons must test this exact stack; the DSP EQ can flatten it. The
  frame fixes the stack, not this module.
- **Exposed charge contacts.**
  - Sweat can bridge VBUS and GND_CHG (heads 8.3 mm apart) and slowly corrode the heads.
  - Brass nuts and stainless eyeglass screws aren't magnetic, so a "magnetic pogo" dock needs its own
    magnet target.
  - Reverse-polarity behaviour on the dock is the circuit's job.
- **PCM refold:** the tabs are welded nickel. Bending them by hand risks a short. Ask the vendor for
  "PCM on the face" if you can.
- **KXT321 orientation is assumed** with its 3.0 mm side along x. The flexure nub is centred on
  `frame.BUTTON` either way.
- **Draft board (`hw/pod/place.py`)** has Y1/C12 inside the r1.6 mic keepout. The real layout must
  respect it, and must keep the clamp bands and the rear-edge pad row free of parts.
- **Styling deltas from blade2:**
  - the fin's inner half starts at x 53, because thinner slivers over the tub were trimmed;
  - the upper armour plate is 1.1 mm longer;
  - there's a front seam line 1.45 mm behind the front edge (the cap);
  - the x = 41 panel line is 0.2 deep, which keeps the top wall ≥ 0.6.
- **Washer OD 3.0 > chimney OD 2.6**, as `frame.MIC_SEAL` specifies, so the washer overhangs the tip
  by 0.2. Fine, but a 2.6 washer would be tidier.
- **Resin properties** (E about 2 GPa, 1.18 g/cm³) are typical datasheet ranges, not measured [Low].
  Hinge force scales with E; strain doesn't.
