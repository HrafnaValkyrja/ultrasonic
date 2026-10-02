# Physical integration: frame, stack-up, sealing, assembly
Status: rev-1 shell ("Spine", bonded, no screws) + 34 × 13 board draft, updated 2026-10-01. **O20 (2026-10-01): both were grown under O15 and must be re-sized.** · Source of truth: `hw/mech/shell_r1.py` (rev-1 numbers), `hw/mech/frame.py` (axes, arm, pad, fasteners), `hw/mech/pod.py` + `hw/mech/blade.py` (rail, catch, adapter, snap tab), `hw/mech/heel.py`, `hw/mech/pad.py`, `hw/pod/place_r1.py`, `docs/build/tolerances.md` · Owner decisions: O9, O10, O11, O12(b), O16(5)(6), O17, O19 (serviceability), O20 (re-size) · Open ECRs: ECR-0001 (frame constants), ECR-0006 (weighted dummy pair, wear + joint-flex test; R20, R24)

## Purpose
Keeps every region (pod body, board, cell, arm, pad) in one coordinate frame, so a change in one can be checked against the others: what sits where, what touches what, how water gets in, and in what order it all goes together. It carries no F-row of its own. It is the mechanical counterpart of every F-row in [integration-map.md](integration-map.md) §1 and the keep-outs in §7.

## Big picture
![physical overview](../diagrams/system-overview-physical.png)

- Panel A: the left pod from outside, lid off. Panel B: the y stack-up through the mic, with layers a–k.
- The cell lies against the pod's inner wall. The board floats above it on two foam strips (which overhang the cell: only 0.1 mm of each sits on it, issue 12), and the lid's two ribs clamp the board's edge bands. Nothing is screwed (O16-6).
- The NiTi arm leaves a heel under the rear of the pod and runs down and back to the pad on the skin.
- Four wires climb the arm's rear side into a 2.1 mm gap behind the board and land on J pads on the board's lid side.
- The dock target is glued flush into a belly under the front.
- CAD renders (right pod): `hw/mech/out/r1/spine/open.png`, `exploded.png`.

## Coordinate frame
| Item | Convention | Source |
|---|---|---|
| Pod axes | x rearward from the glasses hinge along the temple; y outward (away from the head); z up; mm | `frame.py` L8–9 |
| Origin | y = 0 at the temple arm's inner face (head side) | `frame.py` L9 |
| Handedness | Right-handed only on the RIGHT temple, so the hw/mech CAD is the right pod; the left pod is its mirror image | `pcb-mech-interface.md` §1 L44 |
| Board ↔ pod, x | pod x = 30.6 + board x (board x 0 = front edge, mic end), both pods | `place_r1.py` L10–11; `shell_r1.py` L43, L46 |
| Board ↔ pod, y | B face (cell side) at y 12.1, F face (lid side) at 12.9 | `shell_r1.py` L43 |
| Board ↔ pod, z, left pod | pod z = 4.4 − board y (KiCad "top edge" y = 0 is up) **[derived]** | see note |
| Board ↔ pod, z, right pod | pod z = board y − 8.6 (board y = 0 edge is DOWN) **[derived]** | see note |
| Board centre line | board y 6.5 = pod z −2.1 on both pods: mic port and switch sit here, so one board fits both (O16-5) | `shell_r1.py` L41, L45–46 |

**Note on the derived rows (one phrase for the whole set).** Same board, F toward the lid, mic end forward. In the right pod the TP edge (board y 0) is at the bottom: seen from outside, KiCad's top view rotated 180°. In world terms the right-pod board is the left-pod board turned over about its front–rear axis (`pcb-mech-interface.md` L50 says "rotated 180° about its long axis"). `place_r1.py` puts board x = 0 at the front, which forces this. Consequence: **anything off the board centre line lands at a different height in each pod** (TP row, U3, L1, J-pad order); only the right pod has been modelled. No source states the mapping; check it with a KiCad 3D render placed in the CAD (after the board file gets its 0.8 mm stack-up: reg-board issue 2).

**Which numbers are live.** `frame.py` says "change a number here, not in a part module" (L4). But `shell_r1.py` redefines the board, cell, seam, lid, switch and dock locally (L35–48). `frame.py` still holds the round-1 values: PCB 20 × 11.5 at y 11.1–11.9, seam 13.4, LP401230 cell, KXT321 button at x 42.5, lid screws, an 8-pad wire list, mic chimney + washer. For rev 1, trust `shell_r1.py`. `heel.py` and `pad.py` still build against `frame.py` (axes, arm, pad: still valid; cell and cavity: stale; see Open issues). **A third source:** the dovetail rail, catch bump, frame adapter and snap tab (interface 9) come from `blade.py`, which takes its centre from `pod.py` (`POD_ZC` −2.0, `TEMPLE_T/H`; blade.py L31, L41, L113–138). The rev-1 body is centred at −2.1 (`shell_r1.py` L36–37), so the rail and adapter sit 0.1 mm off it. ECR-0001 names only `frame.py`.

### Key positions (pod mm, rev 1)
| Feature | x | y | z | Source |
|---|---|---|---|---|
| Pod body | 29.5–67.5 | 4.3–15.4 (+0.7 plate) | −9.7–5.5 | `shell_r1.py` L35–37 |
| Belly (dock bay) | 29.5–55.0 | 4.3–15.4 | −13.2–(−9.7) | L37, L57 |
| Spine top (O17): a separate floating solid in `lid.stl`, resting on the tub (reg-pod-body issue 1) | 44.0–66.8 | 10.2–14.9 | 5.5–8.6 | L123–132; STL |
| Main cavity / bay | 30.3–66.7 / 30.3–54.2 | 5.1–14.4 | −8.9–4.7 / −12.4–(−8.9) | L39–40 |
| Board | 30.6–64.6 | 12.1–12.9 | −8.6–4.4 | L43 |
| Cell | 30.6–65.6 | 5.4–10.7 | −8.1–3.9 | L42 |
| Board mic port: NPTH Ø0.6 at board (3.13, 6.5) | 33.73 | 12.1–12.9 | −2.1 | draft board probe (2026-10-01) |
| Lid mic bore Ø1.0 (= U2 body origin, board 3.9): **0.77 mm behind the board port** | 34.5 | 14.4–16.1 | −2.1 | L45 |
| Switch / plunger (board 22.0, 6.5) | 52.6 | 12.9–13.55 / 14.2–16.1 | −2.1 | L46; STL |
| Dock target | 31.5–52.7 | 6.32–13.18 | −13.2–(−10.4) | L47 |
| USB-C fallback keep-out | 47.9–55.0 | 5.45–14.05 | −12.4–(−9.6) | L48 |
| TP1–TP6 / J columns | 55.0–61.35 / 62.0 and 63.6 | on F (12.9) | (see derived note) | `place_r1.py` L48–54 |
| Heel (keel + boss, as built) | 55.06–67.3 | 0.3–5.0 | −10.05…−3.78 | heel checks.json `heel_bbox` |
| NiTi socket mouth E | 61.3 | 2.0 | −8.3 | `frame.py` L72 |
| Heel wire exit into the pod | 65.75 | 5.30 | −5.62 | `heel.py` L110 |
| Pad contact centre (on the skin) | 70.6 | −3.0 | −25.0 | `frame.py` L73 |

## Stack-up through the pod (y, at the board; panel B)
| y (mm) | Thick | Layer | Source |
|---|---|---|---|
| 0–2.5 | 2.5 | a · temple arm (glasses) | `frame.py` L23 |
| 2.5–4.3 | 1.8 | b · frame adapter (separate print; dovetail + snap tab; clips the temple) | `frame.py` L24, L27; spec §8 L462–466 |
| 4.3–5.1 | 0.8 | c · tub inner wall | `shell_r1.py` L36, L38 |
| 5.1–5.4 | 0.3 | d · 3M VHB 4914, 0.25 mm, in a 0.3 mm gap (cell to wall) | `frame.py` L38 (TAPE 0.3); `hardware.md` L297; tolerances L16 |
| 5.4–10.7 | 5.3 | e · cell | `shell_r1.py` L42 |
| 10.7–12.1 | 1.4 | f · foam strips (1.5 closed-cell, compressed; 0.6 × 32) under the B clamp bands at z 3.8–4.4 and −8.6…−8.0. **Only 0.1 mm of each overlaps the cell** (z −8.1…3.9): the rest has no floor (reg-pod-body issue 11). Elsewhere B parts ≤ 1.2 (10.9–12.1), 0.2 above the cell | L42–44, L176–178 |
| 12.1–12.9 | 0.8 | g · PCB, 4 layers, In1 solid GND | L43; `place_r1.py` L8 |
| 12.9–14.1 | 1.2 | h · F parts ≤ 1.2 | L44 |
| 14.1–14.4 | 0.3 | i · clearance to the lid; the ribs fill 12.95–14.4 over the clamp bands | L108–109 |
| 14.4 | – | seam (tub \| lid); the lid lip sits at 13.6–14.4 inside the main cavity's opening (none round the belly) | L36, L93–94 |
| 14.4–15.4 | 1.0 | j · lid wall | L36 |
| 15.4–16.1 | 0.7 | k · armour plate | L99 |

The heel sits under the temple and adapter (z ≤ −3.78), at y 0.3–5.0 (heel checks.json). The pad sits further inboard still: its contact face is at y −3.0, the skin, below the temple.

## Clearances (full list: [tolerances.md](../build/tolerances.md))
| Fit | Value | Verdict | Source |
|---|---|---|---|
| Lid lip ↔ tub opening | 0.15 per side; lip 0.5 × 0.8 deep | OK | tolerances L14 |
| Board ↔ walls | 0.3 front/top/bottom; 2.1 behind (arm-wire gap) | OK | L17 |
| Board ↔ lid ribs | 0.05 when seated | OK | L18 |
| Cell ↔ tub | 0.3 tape side; 0.07 at the strut-relief corner fill | tight: dry-fit first | L16 |
| Cell ↔ rear wall | 1.1 (66.7 − 65.6) | **derived; see Open issue 2** | `shell_r1.py` L39, L42 |
| B parts ↔ cell / F parts ↔ lid | 0.2 / 0.3 | derived from the bands | L42–44 |
| Plunger head ↔ bore | 0.15 per side (Ø2.9 in Ø3.2) | OK | tolerances L19 |
| Plunger head ↔ skin | no shoulder, so the plunger rests on SW1: head top 15.45 vs skin recess floor 15.85 = **0.40 the skin spans**; travel 0.15 ± 0.1. (The CAD's 0.65 stem gap assumes a floating plunger.) | not set: fix the head length in CAD (sub-ui issue 1) | L20; `shell_r1.py` L105, L114–115, L174 |
| Dock target ↔ window | +0.1 per side on the CAD box | **envelope incomplete** (5.03 mm tab, 2.0 mm tails): see sub-dock-usb issue 3 | L21; sub-dock-usb |
| Dock target back ↔ cell bottom | 2.3 (z −10.4 → −8.1) for 2.0 mm tails + wires + potting | tight | `shell_r1.py` L42, L47 |
| Under-cell channel (dock wires) | 0.8 (z −8.9 → −8.1) | fill unchecked (sub-dock-usb issue 16) | L39, L42 |
| Foam strip ↔ cell | 0.1 of each 0.6 strip | **no floor** (reg-pod-body issue 11) | L42–43, L177–178 |
| Strut ↔ housing | 1.18–1.34 in all 4 arm states (target 1.4) | accepted | L36 |
| Pad-board joints ↔ cap | 0.05 | tight: joints ≤ 0.45 mm | L45 |
| Seam cut line | a 0.2 (y) × 0.4 rebate on the **tub only** (the lid is never cut) | below the 0.4 resin minimum: may fuse (reg-pod-body issue 12) | L66–69, L73, L88; tolerances L5 |

## Sealing paths (target IPX4 minimum, IPX5 preferred: O12(b), spec L638)
| Path | Rev-1 design | Test build | Final build | State |
|---|---|---|---|---|
| Lid seam, main cavity | Lip, 0.15 per side; a 0.2 × 0.4 tub rebate marks the cut line | taped (tape type TBD) | MS-polymer or neutral RTV, 0.15–0.3 bond line | designed (`shell_r1.py` L6–7, L66–69, L93–94; tolerances L14) |
| Lid seam, round the belly bay | **plain butt joint, no lip**, ~0.4 mm tub land after the rebate | taped | bonded | **weak** (reg-pod-body issue 13) |
| Mic port | Board hole Ø0.6 → **1.5 mm open gap** → lid hole Ø1.0 → hex recess 0.8 deep in the plate (mesh seat) | – | mesh: part TBD (spec task D2, L688) | **open**: nothing seals the gap, so water through the mesh reaches the cavity, and the gap is the "gasket cavity" spec §8 forbids (L511). The round-1 shell had a chimney + PORON washer (`notes/shell.md` L79–80) |
| Plunger bore | Ø3.2 bore through the lid; skin recess Ø5.2 × 0.25 in the plate; KMT022 itself is IP68 | TBD | bonded silicone skin (material and thickness TBD) | partly designed (`shell_r1.py` L13–14, L104–105) |
| Dock window | Window 21.4 × 7.06 in the belly floor | TBD | glued in, back potted | designed (tolerances L21) |
| Arm entry | Heel channel Ø1.0 through the tub's inner wall into the rear gap; NiTi sockets are blind | RTV dabs at the land opening and the exit | same | designed (`heel.md` assembly step 7) |
| USB-C fallback | keep-out only, not cut | – | sealed IP68 receptacle if ever used | reserved |

The research note that should set the IP target and test (`sealing-and-service.md`, cited in O10) doesn't exist. No sealing path has been tested.

## Assembly order (O10 two-stage build, O16-6 no screws in the housing)
Screws stay only where O16(6) allows them: the M1.2 cup screw and the two M1.4 NiTi set screws. **`pad.md` steps 1–9 and the `heel.md` assembly are stale on the wire route** (front riser, Ø1.0 channel, set screw on the rear flat, loop on the head side: reg-arm issue 7). The current route is rear side end to end: rear riser → strut bore Ø1.2 → Ø1.6 × 1.7 counterbore → shrink tube → Ø1.6 × 1.0 heel counterbore → heel channel Ø1.0 → exit (tolerances L29–34).

| # | Step | Test build (taped, reachable) | Final build (bonded, cut-openable) | Source |
|---|---|---|---|---|
| 0 | Print a tolerance coupon; wash and cure; ream the NiTi sockets to Ø0.85 and the mic hole to Ø1.0; dry-fit the cell and board | same | same | tolerances L7, L50–52 |
| 1 | Flash and bench-test the board outside the pod: pogo on TP1–TP6, power on J5/J6; meter the J-pad neighbours first (J3–J5 critical) | same | same | `place_r1.py` L48–54; sub-debug-test bring-up |
| 2 | Pad: wires through the cap first; solder the pad board (litz on the pads' top halves, exciter leads flush); exciter into the cup; contact face; close with the M1.2 screw; cast the LED ring (24 h) | same | same | `pad.md` steps 1–8 (route text stale) |
| 3 | Slide a **pre-shrunk** tube (recovered off the arm, ≤ 1.1 OD, ~5 mm) onto the bundle's free ends. It can't pass Ø1.0/Ø1.2 later. **Never heat it on the arm** | same | same | tolerances L30–34; reg-arm issue 12 |
| 4 | Heel end: file the flat; fish the 4 conductors through the heel channel into the rear gap; seat the tube ends in both Ø1.6 counterbores with ~2 mm slack; NiTi into the heel socket, flat toward the access hole (forward-down); nut + M1.4 × 3 set screw; lock | same | same | `heel.md` steps 3–6 (route stale); tolerances L33–34 |
| 5 | Pad end, **after** the heel end: NiTi into the strut socket, turned so the front flat faces its screw; M1.4 × 2 set screw; lock. Then RTV at the land opening and the exit | same | same | `heel.md` L250–251; reg-pad Interfaces |
| 6 | Dock target into the belly window; 5 wires (gauge TBD) under the cell (0.8 mm) to the rear gap, toward J3/J4/J10/J11/J12 | fixing TBD | glued, back potted | tolerances L21; sub-dock-usb issues 5, 16 |
| 7 | Cell on 3M VHB 4914 (0.25 mm in the 0.3 mm gap) against the inner wall; optional NTC taped on (then RT1 not fitted) | same | same | `hardware.md` L297; integration-map F6 |
| 8 | Foam strips under the board's B clamp bands. CAD size 0.6 × 32 mm, but they have no floor today: cut size and seat follow reg-pod-body issue 11 | same | same | `shell_r1.py` L176–178 |
| 9 | Solder every J wire on the bench; cell lead (J5) last, then meter-check neighbours. **Slack length TBD:** round 1 left ~35 mm so the board could lie beside the pod, but rev 1 must fold all 12 loops into ~190 mm³ (open issue 15) | same | same | electronics.md L113–117 (round-1 practice) |
| 10 | Board onto the foam, F (MCU) toward the lid, mic end forward; fold the wires into the rear gap (2.1 behind the board, 1.1 behind the cell) | same | same | tolerances L17 |
| 11 | Lid parts: mesh at the mic port, plunger in its bore, silicone skin; set the plunger so the skin just touches its head with SW1 unpressed | mesh/skin fixing TBD | skin bonded | sub-ui issue 1; `shell_r1.py` L13–14 |
| 12 | Spine top: per reg-pod-body issue 1 (A: printed with the tub, nothing to do; B: lid feature; C: bond on after closing) | TBD | TBD | reg-pod-body issue 1 |
| 13 | Lid onto the lip; ribs land on the clamp bands | tape round the seam | bond the seam (0.15–0.3 line) | tolerances L14 |
| 14 | Slide the pod onto the frame adapter (dovetail, snap tab) | same | same | spec §8 L462–465; `blade.py` |
| 15 | Check: one click per press and none with the lid just closed; charge on the dock; LED glows; pad force on a kitchen scale (T5) | same | same | `notes/shell.md` L118; `pad.md` step 11 |

**Reopening.** Test build: peel the tape. Final build: firmware goes over the dock (USB DFU, O12a). The pod is opened for SWD, repair and service: cut along the tub rebate and re-bond.

## Service (O19: the cell is replaced as it ages; the owner repairs)
| Job | Sequence | Cut-and-rebond cycles | Time |
|---|---|---|---|
| Cell swap | cut the seam → lift the lid → lift the board on its 12 wires → desolder J5/J6 (J9) → saw the VHB with dental floss (never pry a pouch) → new cell on new VHB → reverse | 1 per swap | unknown |
| Arm swap (R24 predicts joint fatigue) | cut the seam → desolder J1/J2/J7/J8 → release the heel set screw → draw the bundle out of the heel channel → new arm per steps 2–5 → rebond | 1 per swap | unknown |
| Firmware | dock, USB DFU; SWD (cut open) only for a bricked application | 0 | – |

No connector or service seam exists outside the sealed volume, and how many cut/rebond cycles the seam survives is unknown (reg-pod-body issues 10, 12, 14). ECR-0006 flex-tests the joint on a printed dummy before the board order.

## Interfaces between regions (numbers match the diagram)
| # | Between (docs) | What crosses | Geometry | Nets / F-rows |
|---|---|---|---|---|
| 1 | [reg-board](reg-board.md) ↔ [reg-pod-body](reg-pod-body.md) ↔ air ([sub-audio-in](sub-audio-in.md)) | sound | U2 on B; board hole Ø0.6 at pod x 33.73; 1.5 mm open gap; lid Ø1.0 at pod x 34.5 + mesh recess: **0.77 mm offset** | F1 (MIC_DATA, MIC_CLK on board) |
| 2 | [reg-pod-body](reg-pod-body.md) ↔ [reg-board](reg-board.md) ([sub-ui](sub-ui.md)) | finger force | plunger Ø2.9 / bore Ø3.2, skin → SW1 at board (22.0, 6.5); the skin spans 0.40 over the seated plunger | F11: BTN → PA0 |
| 3 | [reg-pad](reg-pad.md) ↔ [reg-arm](reg-arm.md) ↔ [reg-pod-body](reg-pod-body.md) ↔ [reg-board](reg-board.md) ([sub-output](sub-output.md), [sub-ui](sub-ui.md)) | 4 litz wires | strut bore Ø1.2, 3 mm flex zone in a pre-shrunk tube between Ø1.6 counterbores, heel Ø1.0, exit (65.75, 5.30, −5.62), rear gap 2.1 (1.1 behind the cell) | F3: OUT_A/OUT_B → J1/J2 · F12: LED_A/LED_K → J7/J8 |
| 4 | [reg-pod-body](reg-pod-body.md) (heel) ↔ [reg-arm](reg-arm.md) ↔ [reg-pad](reg-pad.md) | spring force (≥ 1 N at the skin) | NiTi Ø0.80; sockets 4.0 (heel) and 3.5 (pad) deep; M1.4 set screws | – |
| 5 | [sub-dock-usb](sub-dock-usb.md) ↔ [reg-pod-body](reg-pod-body.md) ↔ [reg-board](reg-board.md) | charge + USB | YZT0675 target flush in the belly; 5 wires under the cell (0.8 mm) to the rear gap (route and gauge TBD) | F5, F9, F10, F15: DOCK_VBUS, GND, USB_DP, USB_DM, CC → J3/J4/J10/J11/J12 |
| 6 | [sub-power](sub-power.md) (cell) ↔ [reg-board](reg-board.md) | battery | leads to J5/J6; optional NTC to J9 | F5–F8: VBAT, GND, TS |
| 7 | [reg-pod-body](reg-pod-body.md) ↔ [reg-board](reg-board.md) | retention | ribs on F clamp bands; foam on B clamp bands, **with only 0.1 mm of each strip on the cell** (no floor); 0.6 mm part-free bands on both faces | – |
| 8 | [reg-pod-body](reg-pod-body.md) (tub ↔ lid) | seal + access | lip round the main cavity, butt joint round the belly, seam at y 14.4, cut line a 0.2 × 0.4 tub rebate | – |
| 9 | [reg-pod-body](reg-pod-body.md) ↔ glasses | mounting | `blade.py` adapter dovetail + snap tab, 1.8 mm stand-off (centred on `pod.py`'s −2.0, body at −2.1) | §1.2.1 |
| 10 | [reg-pad](reg-pad.md) ↔ skin | vibration + preload | contact face at (70.6, −3.0, −25.0), pressing −y | D1 |
| 11 | [reg-board](reg-board.md) ↔ [reg-pod-body](reg-pod-body.md) ([sub-debug-test](sub-debug-test.md)) | test access | TP1–TP6 on F under the lid: board top edge, which is up in the left pod and down in the right; final build: SWD = cut the seam | F14 |

## Constraints
- §1.2 (locked): clip-on clasps, Ear (open) untouched, comfort first ([spec L31](../spec.md#1-mvp--locked-owner-defined-do-not-modify)).
- §8 v0.9: nothing forward of ~18 mm behind the pupil plane (L476–481). The pod front x 29.5 rests on this estimate until E10 measures it.
- §8 acoustic rules (L508–512): board ≤ 0.8 mm, short wide port, no gasket cavity, thin mesh, never foam.
- D18 (L297): balance, cell along the arm in front of the ear. O4 (L647, open) confirms that reading.
- O19 (L645): serviceability (cell swap, owner repairs) and durability are goals. O20 (L646): rev 1 is the final device; the shell and board must be re-sized. R20 (L613) wearability and R24 (L617) joint fatigue: ECR-0006.
- O10/O16(6): no screws in the housing; final build bonded and cut-openable. O16(5): one board, mic and switch on its centre line.
- O12(b): IPX4 minimum. O11: printed strut, Sugru contact. O17: Spine top; arm wiring never pinched.
- Resin: holes under ~0.8 mm may close, recesses under 0.4 mm may fuse; print critical holes undersize and ream them (tolerances L3–7).

## Key numbers
| Number | Value | Source (date) |
|---|---|---|
| Pod envelope | 38.0 × 11.8 × 15.2 (+3.5 belly, +3.1 spine) | `shell_r1.py`; STL bounding boxes (2026-10-01) |
| Stack from the temple's inner face to the armour top | 16.1 | `shell_r1.py` L36, L99 |
| Board-to-lid gap at the mic | 1.5 (12.9 → 14.4) | `shell_r1.py` L36, L43 |
| Rear wire gap behind board / behind cell | 2.1 / 1.1 | L39, L42–43 |
| Part height per face | ≤ 1.2 | L44 |
| Clamp bands | 0.6, both faces, top and bottom edges | L106–109; integration-map §7 |
| Pad contact below the temple centre | z −25.0 (skin at y −3.0) | `frame.py` L73 |
| Mass per pod | **≥ ~10.2 g lower bound [derived]** (shell, heel, cell, pad, bare board; before parts, dock target, adapter and wires) vs the ~8 g target | reg-pod-body Key numbers (2026-10-01) |

## Open issues
1. **Mic port is unsealed and breaks the spec's acoustic rule.** The 1.5 mm board-to-lid gap opens into the cavity. Close it: add back a chimney + washer (round-1 design) or a gasket on the 3.2 mm seal keep-out, then measure on coupons (S1/E3). A gasket must press round the **board port** (pod x 33.73), not the lid bore, and loads the board through the floorless foam (issue 12).
   - **1b. Board port and lid bore are 0.77 mm apart** (pod x 33.73 vs 34.5; overlap 0.03 mm). Panel B of the diagram draws them in line and says so. Close it: move U2 to board x 4.67 or the lid bore to pod x 33.73 (sub-audio-in issue 1).
2. **Heel wire exit vs the rev-1 cell.** The Ø1.0 exit spans x 65.25–66.25. The cell now ends at x 65.6 (1.1 mm from the rear wall). `heel.py`'s exit check (L540) still tests `frame.py`'s old cell and PCM. Close it: re-run the heel checks against `shell_r1.py`'s cell, or move the exit; dry-fit the real pouch.
3. **Dock wire route not designed.** 5 wires from the belly bay to the J column at x 62.0. Space: 1.5 mm above the dock in the bay, 0.8 mm under the cell. Close it with a route and a wire-count check (reg-pod-body / sub-dock-usb).
4. **`frame.py` is stale** for rev 1 (see "Which numbers are live"). Close it by moving the rev-1 numbers into the frame and re-running heel, pad and shell.
5. **Board orientation per pod is derived, not shown.** Close it with a KiCad 3D render in the CAD (both pods).
6. **Sealing is unverified.** No IP test plan; mesh, skin, tape and adhesive products not chosen; `sealing-and-service.md` missing.
7. **Plunger reach.** Seated on SW1, the plunger's head is 0.40 mm below the skin recess floor; no doc or CAD sets head ↔ skin. Fix the head length in CAD (sub-ui issue 1).
8. **Rev-1 mass: ≥ ~10.2 g before parts, against ~8 g.** Pad 2.19 g (`pad.py`, resin 1.15 g/cm³); shell at 1.18 g/cm³ (reg-pod-body): two densities in one sum. No doc owns the total. Compute it from the STLs with one density plus parts, dock target, adapter and wires (D18, R20; ECR-0006's ballast target).
9. **Contact face** Ø8 (≈ 50 mm²) vs O16(4)'s 100–150 mm², near-flat, 2 mm edge radius.
10. **Cell lead exit and PCM position** inside the Renata pouch are unknown, so the J5/J6 lead route is unknown.
11. **Diagrams:** `system-overview-physical.png` text corrected 2026-10-01 (port offset, VHB, foam, seam, orientation), but Panel B still draws the board hole and lid bore in line, and the foam strips sitting on the cell. `pcb-floorplan-rev1.svg` is drawn for 28 × 13; `arm-wiring.png` shows 2 wires, a silicone sleeve and Ø0.75, all superseded (O8, O11); `docs/build/hardware-map.png` and `hardware.md` §0.5/§6 still show lid-screw charge contacts.
12. **The foam strips have no floor** (0.1 mm of cell under each). Options and recommendation in reg-pod-body issue 11; then add a "foam ∩ support" check to `shell_r1.py`.
13. **Seam:** the cut line is a 0.2 mm tub-only rebate (may fuse), and round the belly the seam is a butt joint with no lip (reg-pod-body issues 12, 13).
14. **Service (O19) costs a cut-and-rebond cycle per cell or arm swap** (Service table). Times and the cycle limit are unknown.
15. **Wire stowage and dock wire gauge.** All 12 slack loops must fold into ~190 mm³ (2.1 × 3.7 × 13.6 behind the board + 1.1 × 5.6 × 13.6 behind the cell, derived from `shell_r1.py` L39–44); folded loops take 3–4× their wire volume. The dock wires have no gauge (the only charge lead specified, Adafruit 30 AWG silicone, OD 0.8, fills the 0.8 mm under-cell channel). Close it: choose the dock wire (sub-dock-usb issue 16), then a fill check for the under-cell channel and the behind-cell gap, and a stowage check (count × gauge × slack); or hinge the board on its wires along the rear edge with ~10 mm slack.
16. **USB-C fallback may be unusable.** The keep-out sits behind the belly's 3.5 mm rear step (x 55, z −13.2…−9.7); a plug overmold (~6.5 mm typical, no drawing checked) can't engage with the main body bottom directly behind it and the heel, strut and pad just inboard. `USBC_KEEPOUT` is never used in a check.
17. **Three frame sources** (`frame.py`, `shell_r1.py`, `pod.py`/`blade.py`): the rail and adapter sit 0.1 mm off the rev-1 body centre. Close it: extend ECR-0001 to `pod.py`.
18. **O20 re-size** (2026-10-01): the shell and board must shrink; every number in this doc moves with them.

## Before you change this, check
- Mic or switch off the board centre line: breaks one board for both pods (O16-5) and moves lid features. See [sub-audio-in](sub-audio-in.md), [sub-ui](sub-ui.md).
- Any part over 1.2 mm on either face, or any part in the 0.6 mm clamp bands, hits the cell, lid, ribs or foam. See [reg-board](reg-board.md).
- Growing the board rearward eats the 2.1 mm wire gap. A different cell changes the y stack, the heel-exit clearance, the foam's floor and the balance (D18). See [reg-pod-body](reg-pod-body.md), [sub-power](sub-power.md).
- Anything off the board centre line (pads, TP row, U3, L1) lands at a different height in each pod. Check both pods, not only the CAD (right) pod.
- Changing the arm wire count changes the heel channel Ø1.0, strut bore Ø1.2, counterbores and J pads. See [reg-arm](reg-arm.md), [reg-pad](reg-pad.md).
- Changing lid or plate thickness changes the plunger length and the mic duct length.
- The belly must stay shallow at the rear for the NiTi strut clearance (`shell_r1.py` L11–12).
- Editing `frame.py` changes what `heel.py` and `pad.py` build. Re-run their checks.
- Then walk [integration-map.md §10](integration-map.md#10-required-cross-check-for-every-proposed-change).

## Change log
- 2026-10-01: created. Board-to-pod z mapping derived per pod. Heel-exit/cell collision, mic-seal gap and plunger gap found while compiling.
- 2026-10-01 (editor pass): mic port split into board port (pod x 33.73) and lid bore (34.5); heel row from checks.json; VHB 4914 0.25 in a 0.3 gap; foam strips have no floor; seam is a tub-only 0.2 rebate with a butt joint round the belly; plunger stack as seated; dock envelope verdict withdrawn; assembly order rewritten (pre-shrunk tube before fishing, heel end before pad end, rear-side route, spine step, slack TBD); Service section (O19); interfaces name their docs; third frame source (`pod.py`/`blade.py`); one orientation phrase; spec refs moved to v0.15; issues 1b, 12–18.
