# Pod body: tub, lid, spine top, retention, dock bay
**Current design (2026-10-07): Phase 2, `hw/current.yaml` (ECR-0018); every tool and check defaults to it.** Shell `hw/mech/shell_r2.py` (constants `hw/mech/dims_r2.py`, outputs `hw/mech/out/r2/`): board hangs from the lid on full-face VHB, seam at the board's B face (y 12.1), sealed duct ID 1.0 with gauge-pin locating, SW1 pocket + puck kit, coarse x-stop 0.25; one 1.8 mm VHB cut-out per test pad keeps 91 % of the tape bonded (2026-10-07; the earlier single 6-pad box kept 31 %). The body below is the Rev F/G reference design (`ULTRASONIC_DESIGN=revg`) unless it says Phase 2; its Phase-2 rewrite is open.
Status: rev-1 shell CAD (`shell_r1.py`, last changed 2026-10-01 19:16 when the board grew to 34 mm), "Spine" top chosen (O17). Not printed yet. `checks.json`: every placeholder overlap is 0 mm³. **But the spine top is not attached to anything (open issue 1), nothing locates the board front-to-back (open issue 2), and the foam strips that are the board's only spring have almost no floor (open issue 11).** O20 (2026-10-01): the shell was grown under O15 and must be re-sized. Updated 2026-10-01.
· Source of truth: `hw/mech/shell_r1.py` (tub, lid, plunger, spine, placeholders, checks); `hw/mech/blade.py` (dovetail rail, frame adapter); `hw/mech/heel.py` (heel unioned into the tub, see [reg-arm](reg-arm.md)); `docs/build/tolerances.md` (fits)
· Owner decisions: O5, O10, O12(b), O16(3)(5)(6)(7), O17, O19 (serviceability: cell swap, owner repairs), O20 (re-size) · Open ECRs: ECR-0001 (`frame.py` still holds the pre-rev-1 pod), ECR-0006 (weighted printed dummy pair: 2 h wear test, 1000× joint flex; R20, R24)

## Purpose
- Holds and protects the board, the cell and the dock target. Clamps the board **without screws** (O16-6).
- Carries the mechanical half of several functions (`integration-map.md` §1):
  - **F1:** the mic port in the lid.
  - **F11:** the switch plunger and its skin.
  - **F5/F9/F10/F15:** the dock window in the belly.
  - **F3/F12:** the rear wire gap, the heel and the wire channel.
- Mounts to the glasses through a removable frame adapter (spec §8, v0.14).
- **Two-stage build (O10):** the test build is taped shut; the final build is bonded and must still be cut-openable for firmware work. Sealing target **IPX4 minimum, IPX5 preferred** (O12b).
- Exterior: the "Spine" top (O17), carried through the design.

## Big picture
![Rev-1 pod exploded: tub, cell, board, lid with spine and hex mic window, arm and pad](../../hw/mech/out/r1/spine/exploded.png)
![Rev-1 pod with the lid off: board on the cell, switch, dock bay below](../../hw/mech/out/r1/spine/open.png)
*Renders of the right pod (frame.py axes), 2026-10-01 19:25. The y stack-up through the mic is Panel B of `docs/diagrams/system-overview-physical.png` ([physical.md](physical.md)). The board's own map is `docs/diagrams/board-regions.png` ([reg-board](reg-board.md)).*

1. **Two prints.** The **tub** is the inner half, from the adapter face (y 4.3) to the seam (y 14.4). It includes the heel, the dovetail rail and the belly bay. The **lid** is the outer half, from the seam to the plate top (y 16.1). It includes the armour plate, mic port, plunger bore and clamp ribs. Plus a printed **plunger**.
2. **Stack, inside out:** cell on 0.25 mm VHB 4914 in the 0.3 mm gap against the inner wall → 1.5 mm foam strips → board (B face down) → the lid's two ribs press the board's F-face edge bands. The foam is the only spring, and **it has almost no floor:** the board is 13 wide and the cell 12, so each 0.6 mm strip at the board's edge overlaps the cell by only 0.1 mm (open issue 11).
3. **Locating and bonding:** the lid locates on a 0.5 mm lip inside the main cavity's opening (not round the belly bay, where the seam is a plain butt joint: open issue 13). It's taped for testing, then bonded (MS-polymer or neutral RTV). The cut line for reopening is a 0.2 × 0.4 mm rebate on the tub only (open issue 12).
4. **Belly bay:** a 3.5 mm-deep bay under the front 25.5 mm holds the magnetic dock target flush in the floor. A USB-C fallback keep-out is reserved at its rear step.
5. **Rear:** a 2.1 mm gap behind the board is the wire path up from the heel channel. A strut relief at the inner-bottom-rear corner keeps the NiTi strut clear.

## Elements
| Feature | Geometry (pod mm: x rearward, y outward, z up) | Source |
|---|---|---|
| Outer body | box x 29.5–67.5, y 4.3–15.4, z −9.7…5.5; all edges chamfered 1.0. Wall 0.8 | `shell_r1.py` L35–38, L55–58 |
| Cavity | x 30.3–66.7, y 5.1–14.4, z −8.9…4.7; board centre line ZC = −2.1 | L39, L41, L61–63 |
| Belly bay | outer x 29.5–55.0 down to z −13.2; bay x 30.3–54.2, z −12.4…−8.9; floor 0.8 | L37, L40, L57 |
| **Tub** | outer body below the seam y 14.4 + dovetail rail + heel − cavity − dock window − strut relief − seam groove | L72–88 |
| Dovetail rail + catch | male dovetail on the inner face, x 36–62, 1.0 tall, 5.0 → 6.4 wide; ramp bump x 31.4–32.9, z −8.9…−8.0 | `blade.py` L35–38, L75–82, L111–115 |
| Frame adapter | separate print: a 1.8 mm plate with temple clip lips and a female dovetail (0.15 fit per side, closed at the rear as an end stop), and a snap tab (~1.6 % strain at release). Reprint it for new frames | `blade.py` L118–142; spec §8 v0.14 |
| Strut relief | inside: fill the inner-bottom corner (1.0 legs, x 62–66.7). Outside: cut back to the plane y + z = −3.65 (x 62–68.5), keeping a 0.6 wall. The NiTi strut passed 0.65 mm away before the relief | L81–87 |
| Dock window | through the 0.8 floor, 21.4 × 7.06 (+0.1 per side) for the Xinyangze **YZT0675** (5-pin magnetic pogo target, 21.2 × 6.86 × 2.8, LCSC C5126848) at x 31.5–52.7, y 6.32–13.18, z −13.2…−10.4 | L47, L80; `tolerances.md` |
| USB-C keep-out | x 47.9–55.0, y 5.45–14.05, z −12.4…−9.6, for a sealed Same Sky **UJ32** (IP68 USB-C receptacle, 6.75 × 8.55 × 2.76). It overlaps the dock target's rear 4.8 mm: **either/or** | L48; `sub-dock-usb.md` |
| **Lid** | outer body above y 14.4: 1.0 thick, plus the armour plate (0.7, 0.3 chamfer, y 15.4–16.1) and a circuit-trace groove (0.7 wide, 0.45 deep) | L91–101 |
| Locating lip | ring 0.5 wall × 0.8 deep (y 13.6–14.4), 0.15 clearance per side, round the **main cavity only** (x 30.45–66.55, z −8.75…4.55). Its lower wall spans the belly bay's opening; round the bay (x 29.5–55.0, z −13.2…−8.9) the seam is a butt joint with a ~0.4 mm tub land after the rebate | L93–95, L39–40, L61–63; `tolerances.md` |
| Seam groove | `seam_groove()` is a band y 14.2–14.6, 0.4 in from the outer faces, but **only the tub subtracts it** and the tub stops at y 14.4. Real cut line: a **0.2 (y) × 0.4 mm rebate on the tub's top edge**, below the 0.4 mm resin recess minimum, so it may fuse. `lid_base()` and `main()` never cut the lid (O10 cut line) | L66–69, L73, L88, L91–110, L213 |
| Mic port | Ø1.0 bore through the lid at (34.5, ZC) = board x 3.9; the board's port NPTH is also at board 3.9 = pod 34.5 (ECR-0011: U2 origin moved to x 4.67; interfaces.py [mic-port] 0.000 mm, 2026-10-02), **aligned**. Hex window (circumradius 1.9, 0.8 deep) at the outer face. **No mesh, no seal to the board** | L45, L102–103; [sub-audio-in](sub-audio-in.md) |
| Plunger bore + skin recess | Ø3.2 bore through the lid at (52.6, ZC) = board x 22.0. Recess Ø5.2 × 0.25 in the plate for a bonded silicone skin (material TBD) | L46, L104–105 |
| Plunger | printed; head Ø2.9 × 0.9, stem Ø1.2 × 1.2, no shoulder. CAD draws it at y 14.2–16.1; seated on the switch it sits at 13.55–15.45. Presses **KMT022** (C&K IP68 SMD tact switch, 1.6 N, travel 0.15 ± 0.1, height 0.65 nominal) | L113–116; `tolerances.md`; C&K KMT0 p.B-9 |
| Clamp ribs | 2 ribs on the lid, x 31.1–64.1, 0.6 wide (z 3.8–4.4 and −8.6…−8.0), reaching y 12.95: **0.05 mm** above the board's F face | L106–109 |
| Foam strips | 1.5 mm closed-cell PE foam, compressed to 1.4 (y 10.7–12.1). **Rev-1 CAD size 0.6 × 32 mm** (x 31.6–63.6; z 3.8–4.4 and −8.6…−8.0), under the board's B-face bands. Meant to sit on the cell, but the cell spans z −8.1…3.9: **each strip has 0.1 mm of cell under it** (less with the pouch's rounded edges) and overhangs empty space to the wall. The cut size in `docs/build/hardware.md` L67 and `hw/mech/notes/hardware.md` L47 (1.1 × 17.5) is the round-1 size: stale | L42–43, L176–178 |
| Cell bed | Renata ICP501233PA-02 envelope x 30.6–65.6, y 5.4–10.7, z −8.1…3.9. 0.25 mm **VHB 4914** (3M acrylic foam tape) in the 0.3 gap to the inner wall | L42; `hardware.md` §4; `tolerances.md` |
| **Spine top (O17)** | base x 44.0–66.8, y 10.5–14.6, 0.6 tall; 6 segments 2.4 long at x 46.0 + 3.4k, y 10.2–14.9, 0.9 → 2.5 tall; top at z 8.6. Unioned into `lid.stl` | L123–132, L213 |

## Interfaces
| To | What crosses | Invariant / state |
|---|---|---|
| [reg-board](reg-board.md) | Pocket 34 × 13 × 0.8 at x 30.6–64.6, y 12.1–12.9, z −8.6…4.4; 0.3 mm to the front/top/bottom walls, 2.1 behind; ribs on F bands, foam on B bands; part bands B y 10.9–12.1, F y 12.9–14.1 | No parts within 0.6 of the top/bottom edges, either face. R-BOARD-BODY |
| [sub-audio-in](sub-audio-in.md) | lid bore Ø1.0 + hex window over board (3.9, 6.5) | Board port is at x 3.9: **aligned** (ECR-0011). 1.5 mm open gap board ↔ lid. R-AUDIO-BODY |
| [sub-ui](sub-ui.md) | plunger bore over SW1 at board (22.0, 6.5) | KMT0 travel 0.15 ± 0.1 vs the stack tolerance. R-UI-BODY |
| [sub-dock-usb](sub-dock-usb.md) | DOCK box, window, BAY, USBC_KEEPOUT; 5 wires target → J3/J4/J10/J11/J12 | Wire route belly → rear pads not designed. R-DOCK-BODY |
| [sub-power](sub-power.md) | CELL envelope, VHB, foam on the cell's outer face | Cell clears the strut-relief fill by ~0.07 mm (L82). R-PWR-BODY |
| [reg-arm](reg-arm.md) | heel unioned into the tub (`heel.heel_add/heel_cut`); wire channel exit at (65.75, 5.30, −5.62), Ø1.0; strut relief | Channel x 65.25–66.25 overlaps the cell's rear end (x 65.6) ([physical.md](physical.md) open issue 2). R-BODY-ARM |
| [physical](physical.md) | frame axes; `frame.py` vs `shell_r1.py` constants; assembly order (test vs bonded) | ECR-0001. R-PHYS-FRAME |
| [sub-debug-test](sub-debug-test.md) | TP row and SWD under the lid | In the bonded build SWD means cutting the seam (O10), so DFU through the dock is proven first; the 0.2 mm rebate is the cut line (issue 12) |
| [reg-pad](reg-pad.md) | no direct contact: pad pose via the arm (`frame.pad_pose`), styling | Ear (open) clearance re-check (E9); pad styling is still Blade, O17 asks for the Spine theme |
| spec | O10 (two-stage, cut-openable), O12b (IPX4/5), O16-6 (no screws), O17 (spine) | R-SPEC-BODY |
| Nets / firmware | none directly. The body only routes the dock contacts, the arm wires and the button press | — |

## Constraints
- **O16-6:** no screws in the housing. Screws are fine on the transducer cup and the NiTi set screws. **O10:** taped test build, then a bonded final build that can still be cut open.
- **O12b:** IPX4 minimum, IPX5 preferred, for outdoor wear in light rain. **O16-3:** a pre-built magnetic connector, with space reserved for a sealed USB-C. **O16-7:** an IP68 switch, not a printed flexure.
- **O16-5:** one board for both pods, so the left shell is the mirror image and the mic + switch sit on the board centre line ZC. **O17:** Spine top; arm-joint wiring must never pinch. **O5:** growth is acceptable if it's clearance.
- **O19** (spec L645): serviceability is a goal: the cell is replaced as it ages and the owner repairs. **R20** (wearability) and **R24** (joint fatigue), via ECR-0006: a weighted printed dummy pair worn 2 h and a 1000× joint flex test before the board order. **O20** (L646): rev 1 is the final device; the shell must be re-sized.
- **Spec §8:**
  - the mic port opens directly over the board hole;
  - no gasket cavity;
  - thin mesh, never foam (`spec.md` L508–512);
  - nothing visible with the eyes straight ahead (vision line, pod x ≥ 29.5).
- **Resin** (`tolerances.md`, `hardware.md` §5):
  - holes under ~0.8 mm may close; recesses under 0.4 may fuse;
  - print critical holes undersize and drill to size;
  - tough/ABS-like resin.

## Key numbers
| Quantity | Value | Source (date) |
|---|---|---|
| Envelope | 38.0 × 11.8 (y 4.3–16.1) × 15.2 (z −9.7…5.5); belly adds 3.5 under x 29.5–55.0; spine adds 3.1 on top (z 8.6) | `shell_r1.py` L35–37, L126–129 (2026-10-01) |
| Part bounding boxes | tub x 29.5–67.5, y 3.3–14.4, z −13.2…5.5; lid + spine x 29.5–67.5, y 10.2–16.1, z −13.2…8.6 | build123d probe of `tub()`/`lid_base()`+`concept_spine()` (2026-10-01) |
| Volumes / mass | tub (no heel) 1289 mm³ ≈ 1.52 g; lid 1023 mm³ ≈ 1.21 g; spine 160 mm³ ≈ 0.19 g (at 1.18 g/cm³; 1.48 / 1.18 / 0.18 g at pad.py's 1.15). Heel 0.26 g; adapter not included. The resin density differs between sources (1.18 here, `hw/mech/notes/shell.md` [Low]; 1.15 in `pad.py`): pick one | same probe; heel checks.json |
| Pod mass, lower bound **[derived]** | **≥ ~10.2 g** before parts, dock target, adapter and wires: shell 2.92 + heel 0.26 + cell ~4.2 + pad 2.19 + bare FR4 board ~0.65 (34 × 13 × 0.8 at 1.85 g/cm³). Spec target ~8 g; ~15 g is where glasses start to hurt (D18, R20) | this row; sub-power; pad checks.json |
| Clearances | board ↔ walls 0.3 front/top/bottom, 2.1 rear; cell ↔ walls 0.8 top/bottom, 0.3 inner (tape), 1.1 rear; lid ↔ F parts 0.3; B parts ↔ cell 0.2 | `shell_r1.py` L39–44 (derived) |
| Fits | lid lip 0.15/side; rib ↔ board 0.05; plunger head ↔ bore 0.15/side; dock window +0.1/side; dovetail 0.15/side | `tolerances.md` (2026-10-01) |
| Plunger stack | no shoulder, so the plunger rests on SW1: head top 15.45 vs skin recess floor 15.85 = **0.40 mm the skin must span**. (The CAD's 0.65 mm stem-to-switch gap assumes the plunger floats.) | `shell_r1.py` L105, L113–116, L174 (derived) |
| Lid thickness | 1.0 + 0.7 plate = 1.7 at the plunger and mic | L36, L99 |
| Interference checks | tub/lid vs cell, pcb, parts_in, parts_out, switch, foam_top, foam_bot, lid vs dock, tub vs lid: **all 0 mm³** | `hw/mech/out/r1/checks.json` (2026-10-01 19:16) |
| Extra probe | plunger ∩ lid 0 mm³; **lid + spine = 2 separate solids** | build123d probe (2026-10-01, this doc) |

### Sealing paths (O12b)
| Path | Rev-1 design | Status |
|---|---|---|
| Seam, main cavity | lip + bond line 0.15–0.3 mm (MS-polymer / neutral RTV; product TBD) | designed; untested |
| Seam, round the belly bay | **plain butt joint, no lip**, ~0.4 mm tub land after the rebate | **weak path** (open issue 13) |
| Mic port | open Ø1.0 bore; the board-to-lid gap is open to the cavity | **not sealed**: no mesh, no chimney (`sub-audio-in` issues 2–3) |
| Plunger | silicone skin bonded in the Ø5.2 recess; KMT022 itself is IP68 | skin material and thickness TBD |
| Dock window | target glued in, back potted | potting compound TBD |
| Heel channel / arm | RTV at the land opening and the rear gap (`hardware.md` §0.5 table) | per [reg-arm](reg-arm.md) |
| Test | none planned | TBD |

## Open issues
1. **The spine top is a floating solid.** It sits on the **tub's** top face (y 10.2–14.4) and touches the lid only along the line y 14.4, z 5.5, where the lid's top edge is the 1.0 chamfer. `lid.stl` therefore holds two disjoint bodies, and the exploded render shows the spine moving with the lid. Options (owner, O17):
   - **(A, recommended)** Make it part of the tub print. Trim it to y ≤ 14.0 so the top seam groove stays open for cutting.
   - (B) Make it a lid feature: extend its base onto the plate (y 15.4–16.1). The spine then overhangs the tub and covers the top seam.
   - (C) Print it separately and bond it on after closing.
   - **Closes:** pick one; re-run `checks.json` plus a solid-count check.
2. **Nothing locates the board front-to-back.** The rev-1 shell has no front or rear stops (the round-1 shell had both). The board can slide ~2.4 mm in x (0.3 front gap + 2.1 rear gap), held only by rib/foam friction, which moves the mic port and SW1 off their lid holes. Options:
   - **(A, recommended)** Two short rear-stop ribs on the lid at x ≈ 64.7, inside the clamp bands, so the wires still pass between them.
   - (B) Push the board against the front wall and tape it.
   - (C) Add a front stop on the tub.
   - **Closes:** a CAD change + check.
3. **Mic acoustic path** (body side): the lid bore is aligned with the board port since ECR-0011; the 1.5 mm gap is unsealed; there's no mesh. **Closes:** see `sub-audio-in` issues 1–3 (chimney/boss + mesh seat in the lid).
4. **The plunger floats.** The bore is a straight Ø3.2 hole with no shoulder, so the plunger rests on SW1 and its head top sits 0.40 mm below the skin recess floor (Key numbers). The quantity that sets pre-press or no-click is head top ↔ skin underside; no doc or CAD sets it (`tolerances.md` says "stem 0.2 mm long, sand to a light touch"). The KMT022 height is 0.65 mm nominal (C&K KMT0 datasheet p.B-9, 21 Mar 2018, fetched 2026-10-01; sub-ui); **its tolerance is unknown**. **Closes:** set the head length so that "skin just touching the head = SW1 just not pressed", add a retaining shoulder or rely on the skin, and say which (sub-ui issue 1).
5. **Sealing is undesigned past the seam** (table above). The spec cites `docs/research/sealing-and-service.md` (O10), but it doesn't exist. **Closes:** the sealing note + an IPX4 spray test plan.
6. **Heel wire-channel exit overlaps the cell's rear end** (x 65.25–66.25 vs 65.6): heel.py still checks against the old cell ([physical.md](physical.md) open issue 2). **Closes:** [reg-arm](reg-arm.md).
7. **Dock:** the wire route from the belly to the rear pads isn't designed. The USB-C keep-out overlaps the target (either/or). **Closes:** [sub-dock-usb](sub-dock-usb.md) issue 5.
8. **Stale sources.**
   - `frame.py` holds the pre-rev-1 pod (ECR-0001).
   - `hw/mech/notes/shell.md` and `notes/electronics.md` describe the round-1 **screwed** lid with screw charge contacts and a 20 × 11.5 board.
   - There's no rev-1 shell note, so no owner build sheet for this shell. The assembly order is only in [physical.md](physical.md).
   - **Closes:** ECR-0001 + a `notes/shell_r1.md`.
9. **Outdated outputs.**
   - `assembled.png` (01:32) and `top.png` (00:53) predate the 34 mm board (19:25).
   - `pod_rev1_shell.step` / `.FCStd` and `concepts_r1.png` (00:22) predate the retention ribs and the 34 mm board.
   - Missing diagram: a dark-mode section through the ribs, foam, lip, seam and plunger.
   - **Closes:** re-export and render once issues 1–2 are fixed.
10. **Unknowns:**
    - foam spring force on the board (foam stiffness unmeasured);
    - bond strength and how many cut/rebond cycles the seam survives;
    - pod mass and centre of mass for rev 1 (D18 balance; `sim/checks/balance.py` was run for older pods). The known parts already sum to ≥ ~10.2 g (Key numbers) against the ~8 g target; ECR-0006 needs the full figure for its ballast.
    - **Closes:** bench + CAD mass run.
11. **The foam strips have almost no floor.** The board (z −8.6…4.4) is 1 mm wider than the cell (z −8.1…3.9), so each 0.6 mm strip under the B clamp bands overlaps the cell by only 0.1 mm and overhangs empty space to the inner wall (`shell_r1.py` L42–43, L177–178). In round 1 the board was narrower than the cell and the strips sat on it (`frame.py` L39/L41; `notes/shell.md` L104). `checks.json` only tests for zero overlap, not for support. Consequences: the button press (sub-ui issue 2) and any mic gasket load push the board ~0.2 mm down until B parts (R21 under SW1, Q1/Q2, U3's DSBGA) land on the pouch. Options (owner):
    - **(A, recommended)** Two ledges on the tub's top and bottom cavity walls, z 3.9–4.7 and −8.9…−8.1, y 5.1–10.7, flush with the cell's outer face, as foam floors. The bottom ledge needs a gap for the dock-wire route under the cell (sub-dock-usb issue 5).
    - (B) Wider strips moved inboard (≤ 0.95 mm wide, clearing B parts: R14 ends at board y 12.05).
    - (C) One cell-width foam pad.
    - **Closes:** the choice, then a "foam ∩ support" check in `shell_r1.py` `main()`, then the rev-1 cut size here and in physical's assembly order.
12. **The seam cut line is a 0.2 mm rebate on the tub only.** `seam_groove()` is never subtracted from the lid, and the tub stops at y 14.4, so the "0.4 × 0.4 groove" is really 0.2 (y) × 0.4: below the 0.4 mm resin recess minimum (tolerances.md L5), so it may fuse. **Closes:** subtract `seam_groove()` in `lid_base()` too, or widen the tub rebate to 0.4; re-run checks.
13. **No lip round the belly bay.** The lip follows the main cavity only; round the bay (x 29.5–55.0, z −13.2…−8.9) the seam is a butt joint with ~0.4 mm of tub land after the rebate. **Closes:** extend the lip into the bay outline (or add a bay-perimeter lip), re-run checks, then the sealing test (issue 5).
14. **Service (O19, R24) costs a cut-and-rebond cycle every time.** A cell swap means cutting the seam, lifting the board on its 12 wires and sawing the VHB (permanent; dental floss, `hardware.md` L298). An arm swap (the joint fatigue R24 predicts) means cutting the seam to desolder 4 conductors at J1/J2/J7/J8. No connector or service seam exists outside the sealed volume. **Closes:** physical.md "Service" sequences; the cycle count the bond survives (issue 10); a decision on whether rev 1 needs a service joint.

## Before you change this, check
- **Mic port, plunger bore or lid thickness:** the board positions in **both** pods ([reg-board](reg-board.md), centre line); the duct length and §8 rules ([sub-audio-in](sub-audio-in.md)); the plunger stack ([sub-ui](sub-ui.md)).
- **Ribs, foam or cavity size:** the board's clamp bands and height bands; the cell fit; the button feel (foam is the spring, and it needs a floor: issue 11).
- **Belly, window or keep-out:** [sub-dock-usb](sub-dock-usb.md); O12b sealing; the strut clearance (the rear stays shallow).
- **Rear wall, strut relief or heel:** [reg-arm](reg-arm.md), the wire gap, the cell's rear end.
- **Seam or adhesive:** O10 (cut-openable), O16-6 (no screws).
- **Spine or exterior:** O17; that the part prints as one solid.
- After any change: re-run `python3 hw/mech/shell_r1.py` (checks.json) and render; walk `integration-map.md` §10; run `python3 tools/plm.py impact file:hw/mech/shell_r1.py`.

## Change log
- 2026-10-01: created from `shell_r1.py` (19:16), `blade.py`, `heel.py`, `tolerances.md`, `checks.json`. New findings:
  - the spine is a separate solid;
  - the board has no x location;
  - the plunger leaves a 0.65 mm CAD gap;
  - volumes and mass;
  - stale notes and renders.
- 2026-10-01 (editor pass): issues 11 (foam strips have 0.1 mm of cell under them), 12 (seam rebate tub-only, 0.2 mm), 13 (no lip round the belly), 14 (service cycles, O19/R24); plunger stack restated as seated (0.40 mm skin span); KMT022 height cited from C&K; mic bore vs board port 0.77 mm; mass lower bound ≥ ~10.2 g; O19/O20/ECR-0006 in the status line.
