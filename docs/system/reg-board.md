# The pod board (PCB region)
Status: **rough draft, not the layout.** `place_r1.py` placement plus one fenced FreeRouting pass (2026-10-01 19:44): 56 parts placed, 0 courtyard overlaps, **7 connections unrouted**, 16 DRC errors (all wire-pad courtyard rings). The real layout is done together with the owner (O14). A board simplification/cost study is about to start; this doc records the design as it stands. **O20 (2026-10-01, spec L646): the 34 × 13 outline was grown under O15 and must be re-sized for rev 1 = final device.** Updated 2026-10-01.
· Source of truth: `hw/pod/place_r1.py` (PLACE table, GND fan-out, plane) until the owner's KiCad board takes over; `hw/pod/place.py` (`outline()`, `rules()`); `hw/lib/pod.pretty/`; netlist from `hw/pod/gen.py` Rev E · Results: `hw/pod/draft_r1/summary.json`, `drc.json` (2026-10-01 19:44)
· Owner decisions: O9, O13, O14, O15 (superseded in part by O20), O16(5), O18 (spare pins to pads), O19, O20 · Open ECRs: ECR-0002 (routing fixes), ECR-0003 (bridge leg B pins), ECR-0004 (SOT1216 footprint), all on hold for the simplification study

## Purpose
- Physically carries **every** electrical function, F1–F15 (`integration-map.md` §1). Every block in `integration-map.md` §2 lives here, except the cell, dock target, exciter and pad LED.
- Must fit the rev-1 shell pocket: 34 × 13 × 0.8 mm at pod x 30.6–64.6 (`shell_r1.py` L43).
- Keeps the mic port and the switch on the centre line (y 6.5), so **one board serves both pods** (O16-5).
- Keeps the 0.6 mm top and bottom edge bands clear on both faces: the lid ribs and foam strips hold it there, with no screws (O16-6).
- Gives hand access: the J wire pads and the TP1–TP6 pogo row, both on F (O9, O15).

## Big picture
![Board regions, both faces to scale](../diagrams/board-regions.png)
*`docs/diagrams/board-regions.svg`, drawn 2026-10-01 from the draft board's real pad geometry and the PLACE table. It replaces `pcb-floorplan-rev1.png`, which was drawn for 28 × 13.*

1. **Front (x 0–9): the quiet end.** The mic U2 sits on B and ports through the board. The 32.768 kHz crystal Y1 sits on F, next to MCU pins 3/4. Nothing switches here.
2. **Middle (x 7–20): the MCU U1 on F,** with decoupling caps on all four sides. Under it on B there are no parts, only the GND fan-out vias: 9 in the exposed pad and the escapes.
3. **Middle-rear on B (x 14–23): the charger U3 (top) and the H-bridge Q1/Q2 (below).** The bridge sits "rear-middle, far from the mic" (`place_r1.py` L67), about 12 mm from the mic port.
4. **Rear on F (x 16–24): the core SMPS loop (L1, C8, C9) and the switch SW1.** The SMPS is the only switcher on the board (D11).
5. **Rear on B (x 22–29): the LDO U4, and the dock/USB protection** (D3, D4, U6 and the sense resistors).
6. **Rear edge, F: 12 wire pads in two columns.** The arm, cell and dock wires rise to them in the 2.1 mm gap behind the board.
7. **TP1–TP6 run along the top edge.**
8. **Layers:** F.Cu (parts, short signals) · In1 solid GND · In2 signals (the busiest layer, 374 mm of track) · B.Cu (parts). The left pod sees this exact view from outside. Same board, F toward the lid, mic end forward; in the right pod the TP edge (board y 0) is at the bottom: seen from outside, KiCad's top view rotated 180° ([physical.md](physical.md), derived).

## Elements

### Outline, stack-up, rules
| Item | Value | Source |
|---|---|---|
| Outline | 34.0 × 13.0 mm rounded rectangle, corner r 1.0; x = 0 at the front (mic end), y = 0 at the KiCad top edge, centre line y 6.5 | `place_r1.py` L8–9, L30; `place.py` `outline()` L93 |
| Thickness | **0.8 mm target** (spec §8: the mic ports through the board). The generated `.kicad_pcb` has no stack-up and says **1.6** (KiCad default) | shell_r1 `PCB` y 12.1–12.9; `pod_r1_routed.kicad_pcb` line 6 |
| Layers | 4. In1 = solid GND zone (layer type "power", 0.2 clearance, 0.3 inset); In2 = signals, no plane | `place_r1.py` `gnd_plane()` L75–89; board file |
| Design rules | 0.1 mm track/space; via 0.35 / 0.15 drill; checked at 0.09 min clearance and track; via ≥ 0.30, annular ≥ 0.075; hole clearance 0.2; copper-to-edge 0.2 (JLC 4-layer capability with margin). FreeRouting routes inside an outline pulled in 0.2 mm | `place.py` `rules()` L112–122; `place_r1.py` L212, L223 |
| GND fan-out | Before routing: each GND pad gets its own via to In1, keeping 0.12 mm from other copper. 47 vias (a 3 × 3 grid of 9 in U1's exposed pad, 38 outward); the 5 MCU ring GND pins get stubs onto the exposed pad | `place_r1.py` `gnd_fanout()` L107–183; via count from the placed board |

### Floorplan regions (board mm; colours as in the diagram)
| Region | Face | Extent x / y | Parts (gloss in the subsystem docs) | Why there |
|---|---|---|---|---|
| Mic port strip | F | 0.6–5.5 / full | none. Port hole Ø0.6 at (3.13, 6.5); lid bore and hex window sit above | keep the port area flat and free |
| Mic | B | 1.8–7.2 / 4.0–9.1 | U2 SPH0641LU4H-1 (ultrasonic PDM MEMS mic), R2 33 Ω clock series, C13 | quiet front end; centre line (O16-5) |
| Clock | F | 5.6–8.9 / 2.2–6.7 | Y1 32.768 kHz crystal, C11, C12 | next to PC14/PC15 (U1 pins 3/4) |
| MCU | F | 6.7–19.7 / 1.0–11.2 | U1 STM32U575CIU6Q (QFN-48 7 × 7), C1–C7, C10, C20, R1 | centre; caps on every side |
| I_SENSE filter | F | 9.6–13.6 / 11.1–12.2 | C22, R22 (1 kΩ / 10 nF) | right under PA6 = pin 16 (`place_r1.py` L46) |
| Core SMPS | F | 16.6–22.1 / 8.0–12.1 | L1 DFE201610E 2.2 µH, C8, C9 (C7, the VDDSMPS input cap, at 18.0, 6.5) | next to VLXSMPS pin 20 and VDD11 pin 23 |
| UI | F | 20.1–24.0 / 5.1–10.1 | SW1 KMT022 (IP68 tact switch), R10 2.2 kΩ | fixed by the lid plunger at (22.0, 6.5) |
| Test pads | F | 24.1–31.1 / 0.95–1.65 | TP1–TP6, 0.7 mm, 1.27 mm pitch | one pogo row; clears the clamp band by 0.35 |
| Wire pads | F | 30.9–33.5 / 2.9–11.9 | J1–J12, 1.0 mm, 1.6 mm pitch, 2 columns | rear edge, where the wires rise |
| *Free* | F | 24.2–30.2 / 2.3–12.3 | no parts (tracks only), ~6 × 10 mm | — |
| VBAT sense | B | 9.5–12.6 / 1.0–3.0 | R8, R9 (1 MΩ / 1 MΩ), C19 | — |
| Pull-ups | B | 10.0–15.6 / 10.2–12.2 | R11 (PA10), R15, R16, R17 (I2C_SCL, I2C_SDA, CHG_INT) | far from U3: 3 of the 7 unrouted |
| Charger | B | 14.8–20.4 / 1.2–5.8 | U3 BQ25180 (DSBGA-8, 0.4 mm balls), C15, C16, C21, RT1 NTC | — |
| H-bridge | B | 14.5–22.8 / 5.3–12.2 | Q1, Q2 PMCXB290UE (N+P MOSFET pairs), R3–R6 gate pulls, C14 22 µF, R21 0.1 Ω shunt; D1/D2 footprints DNP | rear-middle, ~12 mm from the mic port |
| LDO | B | 22.4–25.2 / 5.4–12.0 | U4 TPS7A2030 (3.0 V LDO), C17, C18, R20 0 Ω link | — |
| Dock/USB protection | B | 24.8–28.9 / 1.2–12.4 | D3 ESD9X5.0 (VBUS ESD), D4 1N5819WS (reverse-dock Schottky), U6 TPD2E2U06 (D+/D− ESD), R12/R13 VBUS sense, R18 5.1k Rd / R19 CC sense, plus R14 2.2k LED resistor | next to J3/J10–J12 |
| *Free* | B | 7.4–14.3 / 3.1–10.1 (under U1); 29.1–33.5 / full (under the J pads) | no parts; GND fan-out vias under U1 | — |

**Counts:** F carries 21 placed parts plus 18 copper pads (J1–J12, TP1–TP6). B carries 35 placed parts plus 2 DNP footprints (D1, D2). 56 placed in total (`bom_jlc.csv`).

### Hand pads (F)
| Column / row | Top → bottom (KiCad y) | Source |
|---|---|---|
| x 31.4 | J3 DOCK_VBUS · J4 GND · J10 USB_DP · J11 USB_DM · J12 CC · J9 TS | `place_r1.py` L51–52 |
| x 33.0 | J5 VBAT · J6 GND · J1 OUT_A · J2 OUT_B · J7 LED_A · J8 LED_K | L53–54 |
| y 1.3, x 24.4 + 1.27k | TP1 SWDIO · TP2 SWCLK · TP3 NRST · TP4 +3V0 · TP5 GND · TP6 VSYS | L49; integration-map §6 |

## Interfaces
| To | What crosses (names as in integration-map.md) | Invariant / state |
|---|---|---|
| [sub-audio-in](sub-audio-in.md) | U2 on B, body (3.9, 6.5); port NPTH at (3.13, 6.5); N$2 → R2 → MIC_CLK, MIC_DATA, MIC_VDD from U1 on F through vias | The **port**, not the body, must line up with the lid bore (open issue 3). R-AUDIO-BOARD |
| [sub-processing](sub-processing.md) | U1 on F: pins 1–12 west, 13–24 south, 25–36 east, 37–48 north; Y1 west; SMPS loop south-east | 3 unrouted nets end at U1 (pins 10, 27, 31). R-PROC-BOARD |
| [sub-power](sub-power.md) | U3 cluster and U4 cluster on B; VBAT/VSYS/VBUS; R8/R9/C19 | 3 unrouted at U3 (VBUS, VSYS, I2C_SDA). RT1 sits 3.2 mm from U3. R-PWR-BOARD, ECR-0002 |
| [sub-output](sub-output.md) | Q1/Q2 on B; OUT_A/OUT_B run ~15 mm from x 15.8/18.6 to J1/J2 at x 33.0; BRIDGE_RTN → R21 | 200 kHz edges stay in the rear half. 1 unrouted OUT_A stub. R-OUT-BOARD, ECR-0004 |
| [sub-dock-usb](sub-dock-usb.md) | J3/J4/J10/J11/J12 (F, column x 31.4); protection on B at x 24.8–28.9 | D3 and U6 close to their pads; keep USB_DP/USB_DM as a pair. R-DOCK-BOARD |
| [sub-ui](sub-ui.md) | SW1 on F at (22.0, 6.5); R10; R14 on B (26.42, 11.8); J7/J8 | BTN unrouted (U1.10 ↔ SW1) |
| [sub-debug-test](sub-debug-test.md) | TP1–TP6 row; R20 (23.4, 11.4) B; R21 (21.6, 7.6) B | Row stays outside the clamp band, at 1.27 mm pitch. R-DEBUG-BOARD |
| [reg-pod-body](reg-pod-body.md) | Pocket 34 × 13 at pod x 30.6–64.6, z −8.6…4.4; lid ribs on the F bands (x 0.5–33.5); foam strips on the B bands (x 1.0–33.0); lid bore Ø1.0 over (3.9, 6.5); plunger bore Ø3.2 over (22.0, 6.5) | R-BOARD-BODY |
| [reg-arm](reg-arm.md) | J1/J2/J7/J8; wires rise in the 2.1 mm gap behind x 34 | R-BOARD-ARM |
| Cost | Parts on both faces = double-sided assembly; **10 Extended part types on the pod board** (U1, U2, U3, U4, U6, Q1/Q2, L1, D3, RT1, SW1) **+1 on the pad board (LED C131223) = 11 loading fees per JLC order** | JLC parts API 2026-10-02T00:44Z (audit query, every `bom_jlc.csv` line); R-COST-BOARD; simplification study pending |
| [reg-pad](reg-pad.md) | Separate 2-layer pad board (LED D1), same JLC order | Panel vs separate order (reg-pad issue 9) |
| [physical](physical.md) | Board ↔ pod mapping per pod; height bands; wire stowage behind the rear edge | The right pod's board is at a different height than the left for anything off the centre line (physical.md) |
| Firmware | None directly. Pins are fixed by the routing: ECR-0003 would move GB_P/GB_N to PA10/PB15 | — |

## Constraints
- **Spec §8:** board ≤ 0.8 mm, because the mic ports through it; port 0.6–1.0 mm, short and wide (`spec.md` L508–512).
- **D8:** JLC assembly. **D11:** the core SMPS is the only switcher. Switching parts stay at the rear, away from the mic (audit MP-01; rationale in `pcb-floorplan-rev1`).
- **O13:** double-sided; may grow a little. **O15:** rev 1 may be bigger for test access. **O9:** test pads + snap-off frame. **O14:** layout together. **O16-5:** mic + switch on the centre line.
- **Mechanical** (`shell_r1.py` L43–46, L106–109, L176–178; `integration-map.md` §7):
  - 0.6 mm clamp bands at y 0–0.6 and 12.4–13.0, both faces, free of parts.
  - Parts ≤ 1.2 mm tall on each face.
  - 0.3 mm to the cavity walls front, top and bottom; 2.1 mm wire gap behind the rear edge.
  - Mic at (3.9, 6.5) on B; SW1 at (22.0, 6.5) on F.
- **JLC capability:** the rules above (`place.py` `rules()`; edge clearance 0.2 per the JLC capabilities page, fetched 2026-09-30, `pcb-mech-interface.md` §2).
- **U3's 0.4 mm DSBGA:** the ball pads are 0.184 mm, leaving 0.216 mm between balls. A 0.1 mm track plus 2 × 0.09 clearance needs 0.28, so **no track fits between balls**. Every ball escapes outward, and the cap order around U3 decides whether it can (derived from the draft footprint).

## Key numbers
| Quantity | Value | Source (date) |
|---|---|---|
| Outline / position | 34 × 13 (r 1.0); pod x 30.6–64.6, y 12.1–12.9, z −8.6…4.4 (ZC −2.1) | `place_r1.py` L30; `shell_r1.py` L41, L43 (2026-10-01) |
| Height bands | B face: pod y 10.9–12.1. F face: pod y 12.9–14.1. Lid inner face 1.5 above F; cell top 1.4 below B | `shell_r1.py` L36, L42, L44 |
| Parts | 56 placed (F 21, B 35) + 2 DNP + 18 copper pads; ERC 0 errors / 335 warnings | `bom_jlc.csv`; `gen.erc` (2026-10-01 19:34) |
| Route (latest) | 698 track segments, 120 vias (47 GND fan-out + 73 signal); track F.Cu 214 / In2 374 / B.Cu 186 mm; 7 unrouted; 16 DRC errors, all `courtyards_overlap` J–J | `summary.json`, `drc.json`, board probe (2026-10-01 19:44) |
| Route history | 17 unrouted (Rev E, 28 × 13) → 14 (34 × 13) → 12 (baseline) → 7 (GND fan-out first) | git log eb88de7, 1c82d5c, a70b38f; `draft_r1/baseline/summary.json` |
| Mic port | NPTH Ø0.6 at board (3.13, 6.5); lid bore at board x 3.9 → **0.77 mm offset** | footprint pad in the draft board; `shell_r1.py` L45 |
| Free space | F: ~6 × 10 mm at x 24.2–30.2; B: ~7 × 7 under U1, ~4.4 × 11.5 under the J pads | diagram (2026-10-01) |
| Distances | mic port → nearest Q1 pad ≈ 12.2 mm; → nearest L1 pad ≈ 16 mm; RT1 → U3 centres 3.2 mm | derived from PLACE and the draft pads |

### Routing state: the 7 unrouted (drc.json 2026-10-01 19:44)
| # | Net | Between | Why (my reading of the draft) | Fix candidate (ECR-0002, on hold) |
|---|---|---|---|---|
| 1 | OUT_A | Q1 pad 3 (B) ↔ a 0.3 mm stub at D1's pad (16.3, 10.3) | the route to D1 (DNP, footprint kept) stops short | short hop; or drop D1/D2's footprints |
| 2 | BTN | U1.10 PA0 (F, west side) ↔ SW1 track (F, x 20.5) | crosses the whole MCU | re-route; SW1 position is fixed by the lid |
| 3 | I2C_SDA | U1.27 PB14 (F) ↔ R16 (B, 13.5, 11.2) | pull-ups far from U3 | pull-ups beside U3 on B (item 1) |
| 4 | I2C_SDA | U1.27 ↔ U3.C1 (16.8, 3.2) | U3 ball escape blocked | same + item 2 |
| 5 | N$3 | U1.31 PA10 (F, east) ↔ R11 (B, 10.5, 11.2) | R11 sits at the far west | R11 next to pin 31 (item 4), or drop R11 via ECR-0003 |
| 6 | VSYS | U3.B2 ↔ C21 track | inner-row ball B2 has no free exit | **swap C15 and C16** so each sits beside its own ball: A2 VBUS at x 17.6, C2 VBAT at x 16.8 (item 2) |
| 7 | VBUS | U3.A2 ↔ C15 (15.3, 2.2) | C15 sits on the far (west) side of A2 | same swap |

Also in ECR-0002: move C7 to (13.8, 11.4, B) to free the east escape lane (item 3).
`docs/diagrams/routing-congestion.png` shows the **baseline** (12 unrouted), not this run.

### Footprint issues
1. **Q1/Q2:** EasyEDA `SOT1216_L1.1-W1.0-P0.35-BL-EP`. Its lands are 0.16 × 0.20 and the drain pads are soldered; Nexperia's Fig. 32 wants 0.20 × 0.25 lands, with the drain pads under resist. The redrawn `pod:Nexperia_SOT1216_DFN1010B-6` exists but isn't wired in (ECR-0004; `sot1216-footprint.md`).
2. **U2 mic:** the footprint's port hole sits 0.77 mm from its origin. Both PLACE and the shell assumed port = origin.
3. **J wire pads** (`TestPoint_Pad_D1.0mm`): ~2.1 mm courtyard rings on a 1.6 mm pitch overlap → 16 DRC errors. The rear column's courtyard pokes 0.045 mm past the edge; its pads stop 0.5 mm short of it.
4. **TP pads:** `pod:TestPoint_Pad_D0.7mm` (`hw/lib/pod.pretty`, 2026-10-01). No known issue.
5. **D1/D2:** footprints kept, not fitted (`place_r1.py` L92: DNP, excluded from BOM and CPL).

## Open issues
1. **7 unrouted connections** (table above). **Closes:** the layout session (O14) after the simplification study; ECR-0002 holds the candidates.
2. **Board thickness in the KiCad file is 1.6 mm, not 0.8.** `place_r1.py` never sets a stack-up, and the older `hw/pod/kicad-draft/pod.kicad_pcb` had 0.8. Renders and any 3D fit check are wrong by 0.8 mm. **Closes:** set JLC's 0.8 mm 4-layer stack-up in the generator (or the KiCad board) before release.
3. **Mic port 0.77 mm from the lid bore** (`sub-audio-in` open issue 1). Also, `integration-map.md` §1/§7 quote the body position (3.9, 6.5) as the port. **Closes:** move U2 to board x ≈ 4.67, or move the lid bore.
4. **Wire-pad neighbours that a solder bridge turns into a fault** (0.6 mm copper gaps, `place_r1.py` L51–54):
   - **J3 DOCK_VBUS ↔ J5 VBAT (critical),** side by side at y 3.4 (drc.json also lists their courtyard overlap). A bridge puts the cell on the exposed dock contact (sweat electrolysis, shorts against the frame), and docking then feeds 5 V straight into the cell past D4 and U3, with only the PCM to stop it.
   - J5 VBAT above J6 GND: shorts the cell through its PCM. J3 DOCK_VBUS above J4 GND.
   - J10 USB_DP ↔ J1 OUT_A and J11 USB_DM ↔ J2 OUT_B: USB lines next to the 200 kHz bridge outputs. J8 LED_K ↔ J9 TS: ship mode (sub-ui issue 8).
   - `pcb-mech-interface.md` §4 proposed an order that separates them, for the old board. **Closes:** re-order in the layout session (O14), with a GND or low-risk pad between DOCK_VBUS and VBAT; meter every pair in bring-up step 1 (sub-debug-test).
5. **The wire count at the rear edge is up to 12** (4 arm, 5 dock, 2 cell, 1 NTC). Only the 4 arm litz were checked in the 2.1 mm gap (`tolerances.md`). The dock route from the belly isn't designed (`sub-dock-usb` issue 5), and the cell lead exit is unknown (`sub-power` issue 10). **Closes:** the wire-route design ([physical.md](physical.md)).
6. **Part heights are not checked** against the 1.2 mm bands. Known: U2 0.98 mm (`sub-audio-in`) and SW1 0.65 mm nominal (C&K KMT0 datasheet p.B-9, 21 Mar 2018, fetched 2026-10-01; `sub-ui`). Unknown: SW1's height tolerance and every other part. **Closes:** a height report from the footprints' 3D models.
7. **Layer use disagrees with the lesson.** `docs/learn/03-four-layer-board.svg` says L3 = "+3V0 plane + a few signals"; the draft uses In2 as a pure signal layer, with +3V0 routed as tracks. **Closes:** decide in the layout session; update the lesson or the generator.
8. **No panel or snap-off test frame for the 34 × 13 board.** `pcb-mech-interface.md` §8 covered only the old 20 × 11.5 one (O9). **Closes:** panel design before release.
9. **Which pod has the TP row facing up is derived, not checked** ([physical.md](physical.md)). **Closes:** a KiCad 3D render placed in the CAD.
10. **Stale pointers.**
    - `place_r1.py` L7 still points at `pcb-floorplan-rev1.svg` (28 × 13, outdated).
    - `routing-congestion.png` shows the baseline run, not the latest one.
    - The legend of `schematic-rev1.svg` says "58 placed parts"; it's 56 since D1/D2 went DNP.
    - **Closes:** the next commit that touches them.
11. **O20 re-size.** Owner decision O20 (2026-10-01 20:48) supersedes O15's "rev 1 may be bigger": the 34 × 13 board and the rev-1 shell were grown for test access and must be re-sized. Test access must not cost size (small pads, hooks off the board where possible). **Closes:** the simplification study sets the new outline; every mechanical doc follows (reg-pod-body, physical, reg-arm wire gap).

## Before you change this, check
- **Moving U2 or the switch:** the lid bore and plunger in **both** pods (centre line); [reg-pod-body](reg-pod-body.md), [sub-audio-in](sub-audio-in.md), [sub-ui](sub-ui.md).
- **Anything within 0.6 mm of the top or bottom edge, either face:** the ribs and foam press there. Within 0.3 mm of any edge: the cavity wall.
- **Anything over 1.2 mm tall:** the lid (F) or the cell (B).
- **U3 cluster:** the 0.4 mm escape rule above; RT1's distance from U3 (`sub-power` issue 4); ECR-0002.
- **Bridge, SMPS, or OUT_A/OUT_B routing:** keep them in the rear half, away from U2, Y1 and the mic nets (D11, MP-01); ECR-0004.
- **J pads:** wire count and order (shorts), the rear-gap route, the dock pairs (USB_DP/USB_DM together).
- **TP row:** 1.27 mm pogo pitch; stays outside the clamp band.
- **Layer stack or thickness:** the mic port duct (`sub-audio-in`) and the shell pocket.
- Walk the change through `integration-map.md` §10; run `python3 tools/plm.py impact file:hw/pod/place_r1.py`. **Never run `place_r1.py` or FreeRouting as a parallel agent** (CLAUDE.md).

## Change log
- 2026-10-01: created from `place_r1.py` (19:39), `draft_r1` route (19:44), `shell_r1.py`, `gen.py` Rev E. New diagram `board-regions.svg/png`. New findings:
  - the KiCad file thickness is 1.6;
  - no track fits between U3's balls;
  - J5/J6 adjacency;
  - free areas on both faces;
  - the In2 vs lesson mismatch.
- 2026-10-01 (editor pass): Extended count corrected to 10 on the pod board (+1 pad-board LED = 11 fees); issue 4 lists J3–J5 (critical), J10–J1, J11–J2; issue 6 cites the C&K SW1 height; issue 11 (O20 re-size); reg-pad and physical rows added to Interfaces; orientation wording unified.
