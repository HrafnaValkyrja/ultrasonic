# Pod PCB ↔ mechanics: what the KiCad layout must respect (2026-09-30)

> **Superseded in parts (banner 2026-10-07, reg-arm 7 / DK-13 / UI-9 / DBG-10):** lid-screw charging (MCP7383x), the SWD header scheme (§7-8) and the 20 x 11.5 board are Rev E; the current board is the one-face 30 x 12 MZ-2 (reg-board.md). Current truth: `hw/current.yaml` and `docs/system/`. Kept as history; do not build from the superseded parts.

**Scope.** This note turns `hw/mech/frame.py` (the shared mechanical interface, 2026-09-30) into rules for the owner's KiCad layout of the pod board. It is reconciled with the shell agent's **proposed** tub + lid (`hw/mech/shell.py`, status USER_REVIEW), which holds the board differently from the frame's plan (§0 item 8). It also covers the new pad board (`hw/padboard/`), the JLC panel they share, and an electrical check of the lid-screw charge contacts and the pad LED against `hw/pod/gen.py` (schematic Rev C).

**Pictures** (dark, in `hw/mech/out/parts/electronics/`):
- `pcb_interface.png`: the board's outer face with every keep-out, plus the wire-pad options.
- `padboard_and_panel.png`: the pad board, and one JLC panel.
- `charge_led_fix.png`: the two proposed schematic changes.

**Checks:** `hw/mech/out/parts/electronics/checks.json`, written by `hw/padboard/mech.py`.

**Part numbers used here, glossed:**
- **STM32U575**: the MCU.
- **MCP73832**: the single-cell LiPo charger.
- **ESD9X5.0ST5G (D3)**: onsemi's 5 V one-way ESD clamp diode in a 1.0 × 0.6 mm package.
- **PESD5V0S1BL**: Nexperia's 5 V two-way ESD clamp.
- **1N5819WS**: a small 40 V Schottky diode.
- **16-213/BHC-AN1P2/3T**: Everlight's blue 0402 chip LED.
- **KXT321LHS**: the 0.6 mm tact switch.

## 0. Blunt summary: what doesn't fit yet

1. **`frame.py` is the right pod. The only board layout drawn so far, the `hw/pod/place.py` draft, is the left pod's board.** Seen from outside the right pod, KiCad's x axis runs from the rear (left) to the front (right). The draft puts the mic at KiCad x = 2.2, so in the right pod the mic would sit at the rear (x = 48.4).
   - **One board design can serve both pods**, but only if the second pod carries it turned over. The mic and the button are off the board's centre line, so they move in the other pod. This needs an owner decision (§3).
2. **The frame's button (x 42.5, z 1.9) sits on the MCU** where the draft centred it, overlapping it by 0.6 mm in z. Both are on the outer face. The MCU has to move (§2, §3).
3. **The frame's 8 wire pads are not hand-solder-friendly:**
   - 1.0 mm round pads, 0.3 mm apart;
   - 0.2 mm from the board edge, which is JLC's absolute minimum;
   - if `z_top` is a pad centre, the top pad pokes 0.35 mm into the clamp band; if it's the top edge, the column clears the bands by only 0.05 mm.
   - **Their order puts BAT+ next to BAT−**, so one solder bridge shorts the cell through its protection board. It also puts the LED's MCU-pin wire next to BAT+. §4 gives a better pad and a safer order.
4. **The screw charge contacts work electrically, with one real hole: upside-down docking.** Put the glasses on the dock upside down and the polarity reverses. D3 then conducts the dock's whole current, and a 150 mW part can fail short. Fix: one Basic-library Schottky diode (§5).
5. **The LED is 0.45 mm tall, not 0.35.** `frame.PAD_Y["led_top"] = 3.75` has to become ≥ 3.9 (datasheet, §6).
6. **The LED's return wire runs straight into PB7, an MCU pin, along a flexing arm.** A pinched wire or a solder bridge onto VBAT or OUT_A/B pushes tens of mA into the pin; its absolute maximum is 20 mA. Fix: split R14 into two resistors, one at each end of the LED pair (§6). It costs one 0402 resistor.
7. **The spec still says "magnetic pogo pins" for charging** (§3, §8, B6). If the owner adopts screw contacts, the spec needs that change first (owner decision).
8. **The shell agent found the frame's board mounting unbuildable and proposed another one** (`hw/mech/notes/shell.md`, USER_REVIEW). The tub's ledge ribs and the x = 60.8 nut bosses sat over the cell, so the 12.5 mm cell couldn't drop in. In the proposal:
   - the **lid** locates the board: ribs press the outer-face clamp bands, webs sit 0.2 mm beyond the top and bottom edges, and rear stops push the rear edge forward;
   - two **foam strips on the cell** press the inner-face clamp bands, springing the board up against the lid;
   - **tub front stops** hold the front edge, inside the bands only;
   - the **lid screws move behind the cell**, to (64.2, 2.7) = VBUS and (64.2, −5.6) = GND_CHG.
   - **For the layout, nothing gets worse.** Every new contact lands in the 0.6 mm bands this note already keeps clear, now on both faces. `checks.json` confirms the P2 wire pads, the 8-wire exit and the SWD pads clear every shell feature (§2 rows 3, 4, 4b, 14, 16).

## 1. Coordinates: frame ↔ KiCad

`frame.py`: x points rearward along the temple arm, y outward, z up, in mm. That axis set is right-handed only on the **right** temple, so the CAD is the right pod. The left pod is its mirror image.

**KiCad mapping for the right pod's board.** View it from the outer (F) face, which is how you see it with the lid off:
- **KiCad x = 50.6 − x**: x = 0 at the rear edge, on the left; 20 at the front edge, on the right.
- **KiCad y = 3.75 − z**: y = 0 at the top edge.

A real board can't be mirrored: its chips have a handedness. So the left pod gets either a second layout, or the same board turned over: rotated 180° about its long axis, outer face still outward, top and bottom swapped. Every z on the board then lands at **z′ = −4.0 − z** in the left pod, a mirror about the board's centre line z = −2.0.

## 2. Diagram-ready table (right pod; world = frame.py)

| # | Feature | frame.py name | World x, z (mm) | KiCad x, y (mm) | Size | Face | Rule |
|---|---|---|---|---|---|---|---|
| 1 | Board outline | `PCB` | x 30.6–50.6, z −7.75–3.75 | (0, 0)–(20, 11.5) | 20 × 11.5 × 0.8, 4-layer | — | No copper within 0.3 mm of the edge. JLC's minimum is 0.2 (capabilities page, fetched 2026-09-30). Corners: match the tub's corner radius (shell agent) |
| 2 | Board plane | `PCB.y0/y1` | y 11.1–11.9 | — | — | — | Inner-face parts ≤ 1.2 mm tall (y 9.9–11.1, toward the cell); outer-face parts ≤ 1.2 mm (y 11.9–13.1). The lid's inner face is at 13.4 |
| 3 | Clamp bands | `PCB_CLAMP_BAND` 0.6 | z 3.15–3.75 and −7.75 to −7.15 | y 0–0.6 and 10.9–11.5, full length | 0.6 | both | **Shell (proposed): the lid's ribs press the outer-face bands** (x 31.0–50.6; the top rib has a gap at x 35.8–46.6 for the button flexure). **Foam strips on the cell press the inner-face bands** (x 32.0–49.5). No parts and no exposed pads on either face. Mask-covered copper and tented vias are fine. After depanelling, sand these edges flush (§8) |
| 4 | End keep-outs | `PCB_END_KEEPOUT` 0.5 | x 30.6–31.1 (front), 50.1–50.6 (rear) | x 19.5–20 and 0–0.5 | 0.5 | both | No parts. The front edge sits 0.3 mm from the tub's front wall. **Shell:** tub front stops (x ≤ 30.55) and lid rear stops (x 50.65–51.3) touch the board only inside the bands. The lid's webs sit 0.2 mm beyond the top and bottom edges: **sand the mouse-bite nubs to ≤ 0.1 mm proud** |
| 4b | Wire exit window | — | rear edge, z −7.2 to 3.2 (between the lid's rear stops) | x 0, y 0.55–10.95 | — | — | All 8 wires leave the board here. The bundle (z −6.85 to 2.85 at 0.6 mm OD) clears the rear stops by 0.35 |
| 5 | Mic port | `MIC_PORT` | (34.5, −1.0) | (16.1, 4.75) | Ø0.6 hole | through | Mic (SPH0641) on the inner face, porting outward. Footprint `lcsc:Knowles_LGA-5_3.5x2.65mm_Port0.6` |
| 6 | Mic seal keep-out | `MIC_SEAL.keepout_r` | circle r 1.6 at the port | circle r 1.6 at (16.1, 4.75) | Ø3.2 | outer | The lid chimney and washer seal on flat solder mask. **No parts, no vias, no silk** inside it: a via there is an acoustic leak |
| 7 | Button KXT321LHS | `BUTTON` | (42.5, 1.9) | (8.1, 1.85) | 3.0 × 2.0 × 0.6, 1.6 N | outer | The lid flexure presses it. **Conflicts with a centred MCU (0.6 mm overlap):** move the MCU ≥ 0.8 mm down, put it on the inner face, or move the button (§3 L3) |
| 8 | Wire pads, frame as drawn | `WIRE_PAD`, `WIRE_PADS` | x 49.2–50.4; pad centres z = 3.0 − 1.3k (reading `z_top` as a centre) | x 0.2–1.4; y = 0.75 + 1.3k | Ø1.0, 1.3 pitch | outer | **Replace with row 9** (§4) |
| 9 | Wire pads, proposed P2 | — | rear column x 48.7–50.3 (pads 1, 3, 5, 7); front column x 46.9–48.5 (pads 2, 4, 6, 8); centres z = 2.55 − 1.3k | x 0.3–1.9 and 2.1–3.7; y = 1.2 + 1.3k | 1.0 × 1.6 | outer | Column centred on z = −2.0, so it clears both clamp bands by 0.10. Order top→bottom: **VBUS, GND_CHG, BAT−, OUT_A, OUT_B, LED−, LED+, BAT+** (§4) |
| 10 | ESD/charge parts | gen.py D3 (+ new D4) | next to the VBUS pad | within 2 mm of pad 1 | — | either | Shortest path from the contact wire to the clamp, with its own GND via |
| 11 | Bridge outputs | Q1, Q2, D1, D2 | rear half | rear half | — | either | Near OUT_A/OUT_B; keep their 200 kHz loop away from the mic (front) |
| 12 | LED resistors | R14a/R14b (proposed) | next to the LED+ and LED− pads | — | 0402 | either | R14b sits right at the LED− pad, so a fault on the wire is current-limited before it reaches any trace to PB7 |
| 13 | SWD probe pads | TP1–TP5 | x 31.1–32.5; z 2.50, 1.23, −0.04, −1.31, −2.58 | x 18.1–19.5; y 1.25, 2.52, 3.79, 5.06, 6.33 | 1.4 × 0.8, 1.27 pitch | outer | Order top→bottom: **3V0, SWDIO, GND, SWCLK, NRST**. 0.4 mm clear of the mic keep-out. They feed the panel's SWD tab at the front edge (§8) |
| 14 | Lid screws = charge contacts | `LID_SCREWS`, then the shell's proposal | **shell: (64.2, 2.7) = VBUS; (64.2, −5.6) = GND_CHG**. The frame had x 60.8 and z −6.4, over the cell | outside the board (KiCad x −13.6) | M1.4 × 3 into brass nuts in side-entry pockets; blind holes, so the screw tips stay inside resin | lid | 30 AWG silicone wires (~35 mm) run from the nuts to pads 1 (VBUS) and 2 (GND_CHG). The bosses start 11.4 mm behind the PCB's rear edge |
| 15 | Lid front hook | `LID_HOOK` | z −5.0 to 1.0, front edge | y 2.75–8.75 at x ≈ 20 | — | lid | The hook sits in the lid plane (y ≥ 13.4). Outer-face parts under it must stay ≤ 1.2 mm tall |
| 16 | Rear free space | — | x 50.6–62.0 (the bosses start at 62.0), y 9.9–13.4 | — | — | — | **Wire service loop:** 8 × ~35 mm = 79 mm³, 15 % of the shell's 534 mm³. **Shell proposal:** the cell's protection board (PCM) folds flat at x 57.4–61.4, y 9.75–11.95, so BAT± are 7–11 mm runs. The arm's 4 wires come up through the rear wire gap between the bosses |

## 3. One board for both pods: options (owner decides)

| | How | Cost | Verdict |
|---|---|---|---|
| L1 | A second, mirrored layout for the left pod | A full second placement and route of a dense 4-layer board. Mirroring is **not** a KiCad "flip": a flip just turns the same board over. Two JLC designs | No |
| L2 | One board. The left pod carries it turned over; the left shell moves its features to z′ = −4.0 − z | No layout change. But the left pod's **mic port sits at z −3.0 and its button at z −5.9**, while the right pod has them at −1.0 and 1.9. The buttons sit at different heights on the two sides | Fallback |
| **L3 (recommended)** | One board, with **mic port and button on the board's centre line z = −2.0**. Proposed: mic (34.5, −2.0); button (45.0, −2.0), turned so it is 2.0 wide in x and 3.0 tall in z, between the MCU (x ≤ 44) and the P2 wire pads (x ≥ 46.9) | The frame changes 2 numbers; the shell moves the button flexure. **The MCU must then sit at x 36.2–43.9 on the outer face** (clear of the mic keep-out), or go on the inner face | **Recommended.** The shells are exact mirror images, the button sits in the same place on both sides, and there is one BOM and one CPL. The wire-pad order reads top-to-bottom on one side and bottom-to-top on the other; the wires don't care |

With L2 or L3, both pods keep **the top screw = VBUS**, because the mirrored shells keep z. So one dock serves both sides (§5).

## 4. The 8 rear-edge wire pads (gen.py J1–J8)

**Today:**
- gen.py uses `TestPoint:TestPoint_Pad_D1.0mm`, a 1 mm round test pad, for every wire.
- At the frame's 1.3 mm pitch that leaves 0.3 mm between pads, and only ~1 mm of lap for a 0.25–0.3 mm wire.
- These eight wires carry everything that leaves the board, including the cell.

**Options.** Footprints are in `hw/padboard/padboard.pretty/`, written by `hw/padboard/footprints.py`.

| | Footprint | Gap | Board length used | Notes |
|---|---|---|---|---|
| P0 | TestPoint_Pad_D1.0mm (today) | 0.30 | 1.2 | Easy to bridge; peels if the wire is tugged |
| P1 | `WirePad_SMD_0.9x1.9mm`, one column | 0.40 | 1.9 (x 48.4–50.3) | Long along the wire; the minimum improvement |
| **P2 (recommended)** | `WirePad_SMD_1.0x1.6mm`, two staggered columns | 0.30 at the corners, but **the joints sit 2.2 mm apart** | 3.4 (x 46.9–50.3) | Each wire to the front column runs through the 1.6 mm gap between rear-column pads. Bridging needs solder to travel 2 mm. Costs 2.2 mm of outer face, which the SMPS inductor's draft spot also wants |
| P3 | `WirePad_PTH_D0.45mm_Pad0.90mm`, staggered plated holes | ~1.0 | about 2.6, both faces | Strongest: the wire goes through the board and can't peel. Costs inner-face and plane area where the draft puts the bridge |

**Details common to all of them:**
- **Paste stays on the pads.** JLC's reflow pre-tins them, so each wire is tacked with no added solder.
- **Silk label at each pad, printed the right way up for that pod.**
- **Strain relief:** the shell needs a printed comb or a dab of RTV on the wires right behind the edge.

**Pad order.** I scored what a solder bridge between each neighbouring pair would do:
- H = damage, or a shorted cell;
- M = brown-out or battery drain;
- L = benign.

| Order (top→bottom) | Worst neighbours |
|---|---|
| frame: OUT_A, OUT_B, LED+, LED−, BAT+, BAT−, VBUS, GND_CHG | **BAT+ \| BAT− = H** (cell short through its protection board); **LED− \| BAT+ = H** (PB7 straight onto VBAT) |
| **proposed: VBUS, GND_CHG, BAT−, OUT_A, OUT_B, LED−, LED+, BAT+** | none worse than M; needs the R14 split (§6) |

The proposed order also groups the four arm wires (pads 4–7) and puts VBUS next to the top screw. The two battery wires end up 6.5 mm apart: a small price.

**Working rule:** solder the battery wire **last**, and check each neighbouring pad pair with a meter first.

## 5. Lid screws as charge contacts: electrical check

The circuit: top screw → brass nut → wire → J3 (VBUS) → D3 to GND, C15 4.7 µF, MCP73832 V_DD, R12/R13 100k/100k → PA1. Bottom screw → nut → wire → J4 (GND_CHG = system GND).

| Question | Answer | Source |
|---|---|---|
| What sits on the exposed screws while worn (undocked)? | **≤ 0.4 V.** The charger's reverse leakage from the cell is ≤ 2 µA ("during any UVLO condition, the battery reverse discharge current is less than 2 µA"; I_DISCHARGE 0.25 µA typ, 2 µA max with V_DD floating). The R12/R13 divider gives 200 kΩ to GND, and 2 µA × 200 kΩ = 0.4 V. No battery voltage reaches the skin side | MCP73831/2 DS20001984H (2020) p3, §4.1 |
| Sweat bridging the two screws while worn | Harmless electrically: neither side is driven. The only effect is slow galvanic corrosion of the brass nut if sweat wicks into the hole | — |
| Sweat across the screws while docked | 5 V across a salt film. A few hundred µA is harmless to the circuit, but it **electrolyses the VBUS screw (the anode)**. Wipe the pod before docking; use A2/A4 stainless or nickel-plated screws; gold pins on the dock | `[Med]`, chemistry |
| ESD on the VBUS screw | **D3 is adequate:** IEC 61000-4-2 ±30 kV contact and air; ESD9X5.0: V_RWM 5.0 V, V_BR ≥ 6.2 V, 107 W (8/20 µs), V_C 12.3 V at 8.7 A, I_R ≤ 1 µA. C15 is the real energy sink: an 8 kV / 150 pF hit is 1.2 µC, which raises 4.7 µF by **0.26 V**. The ~20 nH of wire slows the edge. **Layout:** D3 next to the VBUS pad, its own GND via | onsemi ESD9X3.3ST5G/D Rev 7 (Oct 2012) p1–2; checks.json |
| ESD on the GND screw | The pod floats on its battery, so there is nothing to clamp; the charge spreads over the pod's few pF. Fine | — |
| Charger abs max | V_DD 7.0 V; all pins −0.3 to V_DD + 0.3 V | DS20001984H p3 |
| **Upside-down on the dock (polarity reversed)** | **Today: D3 forward-conducts the dock's full current** (150 mW rating). On a USB supply it can burn and fail short, and then the pod never charges again until it's reworked | ESD9X sheet p1 (P_D 150 mW) |
| Dock-detect (PA1) false trigger | Undocked, PA1 reads ≤ 0.2 V, so it can't false-trigger | — |
| Both pods on one dock | Both grounds are tied through the dock. Harmless; the units are otherwise independent (D2) | — |

**Reverse-polarity options:**

| | Change | Pros | Cons |
|---|---|---|---|
| **R1 (recommended)** | **Add D4 = 1N5819WS** (C191023, **Basic**, 4,795,058 in stock, $0.0137; JLC parts API 2026-10-01T00:01Z) **in series: J3 → D4 → VBUS node**. D3 stays on the VBUS side | Reversed docking does nothing. The bare contact floats when undocked. One Basic part | ~0.3 V drop at 45 mA (listing value, `[Med]`, no datasheet on file). From a 5.0 V dock the charger still gets ~4.7 V, enough to finish at 4.2 V. PA1 reads ~2.35 V docked. SOD-323 is 2.5 × 1.25 mm; RB520S-30 (C8522, Extended, SOD-523 1.6 × 0.8) is the small alternative, datasheet not yet checked |
| R2 | Bridge rectifier (4 Schottkys) | Docks either way round | ~0.6–0.8 V drop, 2–4 parts, and the board is full |
| R3 | No change: a keyed dock cradle that only accepts the glasses upright, plus a current-limited dock | Zero board change | One mistake on a plain USB supply can kill D3 |

**Mechanical rules that are electrical too** (for the shell agent):
- **Screw tips must not stick out past the nut into the cavity.** They are live VBUS/GND metal next to the wire loop. **The shell's proposal meets this:** an M1.4 × 3 ends at y 11.2 in a blind hole (bottom at 10.5). The longest safe screw is 3.6 mm.
- **The nut pockets open sideways into the wire gap between the two bosses**, which is exactly where the arm's OUT_A/OUT_B/LED± wires come up (shell.md). shell.md makes the RTV dot at each slot mouth optional. **Electrically it is required:** it covers the live VBUS nut and its solder joint where the arm wires rub past.
- **Solder the wire to the nut before pressing it into the resin**, then insulate the joint (heat-shrink or RTV).
- **Mask the screw heads before airbrushing:** paint insulates.
- **Mark the dock:** top pin = +5 V.
- With the lid off, the contacts are gone. Charge or bench-power through the nuts or the pads directly.

## 6. Pad LED (J7/J8, R14, PB7)

**The circuit:** VBAT → R14 2k2 → J7 (LED+) → arm wire → LED on the pad board → arm wire → J8 (LED−) → PB7, an open-drain PWM output.

**What checks out:**
- **Current:** 0.3–0.65 mA over 3.4–4.2 V. The blue die needs 2.6–2.8 V at these currents. Firmware evens it out from the VBAT reading.
- **PB7 is pin 43, type FT_fhav: 5 V-tolerant.**
  - V_IN max = min(V_DD + 4.0, 6.0) V; pull-ups must be off above 4 V.
  - I_IO max 20 mA; positive injection on FT pins is not allowed.
  - Source: DS13737 Rev 8, pin table and Tables 29–30; Rev 10 pinout unchanged (`datasheet-provenance.md`).
- **The pin never sees more than V_DD in practice.** With the LED off, its forward drop at nA currents (~2 V) keeps PB7 at ≲ VBAT − 2 V.
- **After reset all GPIOs sit in analog mode** (DS13737 §3.13), so the LED stays dark until firmware drives PB7.
- **The LED never sees reverse voltage**: worst case ~3 V reversed if PB7 is driven high with the cell removed. Its V_R limit is 5 V.

**Problems:**
1. **A fault on the arm wire hits PB7 unlimited.** The LED− wire runs 25–30 mm through a flexing sleeve next to OUT_A/OUT_B, and it lands on a rear pad. If it shorts to VBAT, OUT_A or OUT_B (worn insulation, or a solder bridge on the pads), PB7 sinks through only its own driver: tens of mA, past the 20 mA limit.
   - **Fix: split R14 into R14a 1k (VBAT → J7) and R14b 1k (J8 → PB7).** Both are 0402WGF1001TCE, a 1 kΩ 0402 resistor (C11702, **Basic**, 7,255,020 in stock, $0.0018; JLC parts API 2026-10-01T00:01Z).
   - Any single short is then ≤ 4.2 mA. The total drops from 2.2k to 2.0k (+10 % current, which the PWM absorbs). The BOM line count is unchanged (the 2k2 line becomes a 1k line).
2. **The LED is ESD-fragile: 150 V HBM.** Everlight 16-213/BHC-AN1P2/3T, DSE-0008890 Rev 3, 29 May 2013, p2. Solder the arm wires with a grounded iron and a wrist strap. Once potted in the pad it is out of reach.
3. **The LED is 0.45 mm tall** (datasheet p6). On a 3.4 mm board top plus solder, its top is at **3.88**; the frame says 3.75. The wire joints on the pad board reach about the same height. The cap roof keeps 0.62 mm to its face at 4.5: OK, just.
4. **Polarity labels disagree.** Everlight numbers the anode "1"; KiCad's LED footprint makes pad 1 the cathode. The netlist is right (K → pad 1). **Check the cathode mark in JLC's placement preview.**
5. `[Low]` 200 kHz edges on OUT_A/B couple a few pF into the LED pair (~µA). The ring might glow faintly when "off" in the dark. Check on the bench; if it does, a 1 nF 0402 across J7/J8 on the pod board fixes it.

## 6b. Pad board layout (`hw/padboard/`, revised 2026-09-30 with the pad cap)

**Sources:**
- placement and tracks: `layout.py` (DRC: 0 violations, 0 unconnected);
- netlist: `gen.py` (ERC clean);
- footprints: `footprints.py`.

**Coordinates:** KiCad, origin at the board centre, which is also the LED. y negative = the top end, where the arm wires arrive. The layout is mirror-symmetric in x, so the left pad takes the same board turned over: **follow the silk labels, not the positions.**

| Ref | Net | KiCad (x, y) | Footprint | Why there |
|---|---|---|---|---|
| J1 | OUT_A | (−1.725, −4.0) | `WirePad_SMD_0.7x1.8mm` | Top row, under the strut's channel exit. 1.55 mm of lap outside the cap's epoxy dam |
| J2 | OUT_B | (+1.725, −4.0) | same | 1.80 mm lap |
| J3 | LED+ (anode) | (−0.575, −4.0) | same | Moved from y −2.9 at the pad agent's request. There, only 0.51 mm of lap lay outside the dam; now 1.36 |
| J4 | LED− (cathode) | (+0.575, −4.0) | same | 1.61 mm lap |
| J5 | OUT_A → transducer lead A | (−1.775, +3.275) | `WirePad_PTH_D0.45mm_Pad0.85mm` | Lead comes up from below. Inner edge at r 3.30 clears the dam (3.25); copper is 0.30 from both edges |
| J6 | OUT_B → transducer lead B | (+1.775, +3.275) | same | same |
| D1 | LED: Everlight 16-213 blue 0402, C131223 | (0, 0), rot 180, K = pad 1 toward +x | `LED_0402_1005Metric` | Centre of the cast ring |

**Notes on this layout:**
- **The four arm pads are 0.45 mm apart.** That's enough to hand-solder, but meter-check them for bridges before closing the pad.
- **The laps above come from the pad agent's own `joint_check`.** `hw/padboard/mech.py` runs it against the cap in pad.py as it was on disk: all 6 joints pass, 0 mm³ overlap.
- **Transducer leads:**
  - The 0.45 mm finished hole takes a lead conductor of up to ~0.35 mm.
  - If the RC-BC02's leads turn out thicker, or are flat tabs (E1), lap-solder them on top of the Ø0.85 pads instead.
  - The pocket above each hole covers the whole pad disc, so a lap joint fits too.

## 7. SWD (programming) access with the lid off

**What you can reach** once the two lid screws are out and the lid is lifted:
- the board's whole outer face, 1.5 mm below the seam;
- the 5 SWD pads at the front edge (table row 13).

The mic-seal washer may come away with the lid. Keep it.

| | How | Verdict |
|---|---|---|
| **A (recommended)** | Hand-held 5-pin, 1.27 mm-pitch pogo probe on `ProbePad_0.8x1.4mm` pads, wired to an ST-Link | Nothing stays in the pod. A 10 s flash. Probes are a common hobby item |
| B | 5 fine wires soldered to the pads, ending in a 1.27 mm header parked in the rear free space | Robust for many reflashes, but it adds wires in the space the wire loop needs |
| C | Tag-Connect TC2030 | Not common hobby hardware; also needs holes. No |

**Where the board sits while you flash.**
- In the shell's proposal, the board rests on soft foam strips once the lid is off; nothing else holds it.
- A 5-pin pogo probe pushes with a few newtons and would tilt it.
- So **lift it out by its edges and lay it outer face up on the bench beside the pod**, on its ~35 mm wires, then probe.
- The cell stays connected through BAT±, so the board is powered.

**Powering it while you flash:**
- Run the board from its cell, or from a 3.7 V bench supply on BAT+/BAT− with the current limit at ~50 mA.
- **3V0 is only the programmer's target-voltage sense.** A genuine ST-LINK uses it; on a clone, leave it unconnected.
- **Never feed the clone's 3.3 V output into the 3.0 V rail.**

## 8. One JLC panel: pod board + pad board + snap-off test strip (spec O9)

**Why a panel at all:**
- The pad board (5 × 9.3 mm) is below JLC's 10 × 10 mm minimum for assembly. JLC help: Economic PCBA minimum single board 10 × 10 mm; panels 10 × 10 to 250 × 250 (search summary of JLC help pages, 2026-09-30, `[Med]`).
- The pod board is too small to handle comfortably.
- O9 wants debug access from a snap-off frame.

**Proposed panel, 65 × 31.5 mm** (picture: `padboard_and_panel.png`):
- **Rails:** 5 mm process edges top and bottom, with 2.0 mm tooling holes and 1.0 mm fiducials 3.85 mm from the panel edge. These are JLC's SMT recommendations ("Specifications for adding process edges and positioning holes", via search 2026-09-30, `[Med]`).
- **2 pod boards** of the same design (with L2 or L3, §3), and **2 pad boards**.
- **Test strip** (6 mm) between the boards and the lower rail: one **1×5 2.54 mm SWD header** per pod board, pins 3V0, SWDIO, GND, SWCLK, NRST. That pin spacing takes Dupont leads from a cheap ST-Link V2. You hand-solder the header yourself.
- **Pod board joints:**
  - **Mouse bites** on the top and bottom edges, 2 sets each. JLC suggests 5–8 holes of 0.6 mm with 0.35–0.4 mm webs per set, and ≥ 2 sets per board under 30 mm (JLC mouse-bite guide, via search 2026-09-30, `[Med]`).
  - They land in the clamp bands, so **sand those edges flush afterwards (board height 11.5 +0/−0.05)**.
  - **The SWD traces cross a solid 1.5 mm tab at the front edge.** No holes, because holes would cut the traces. Trace order: 3V0, SWDIO, GND, SWCLK, NRST, so a copper smear never joins 3V0 to GND.
  - **Separating it:** score the tab on both faces with a scalpel, snap it with flat pliers, sand the edge flush (it sits 0.3 mm from the front wall), and seal the cut trace ends with nail varnish or UV solder mask.
- **Pad boards:** mouse bites on the long sides beside the LED, one set per side. Copper is 0.6 mm in from those edges.
- **Electrically:** the pad board is a 4-layer board in this panel with empty inner layers. That's fine.

**Cost note:**
- The pod board and the pad board are **2 different designs** in one panel. JLC: "if the traces/silkscreen/solder mask in your PCB is different, as long as it can be separated … it will be regarded as different designs" (help article "different design in your PCB files", fetched 2026-09-30).
- That brings a different-design surcharge on the board and on the SMT panel; the exact amount shows only in the quote.
- JLC also charges $4.2 per design beyond 2 for stencil panelisation ("In what cases will there be charged extra", fetched 2026-09-30).
- **L1 (a mirrored layout) would add a third design**: another reason for L3.

**Assembly split:**
- **JLC places:** every SMD part on both pod-board faces, plus the LED on each pad board. The pad board then needs no hand-soldered 0402, which was the owner's worry in `pad-led.md`.
- **You hand-solder:** the SWD header, then every wire.

## 9. Interface requests raised by this note

1. `frame.PAD_Y["led_top"]`: 3.75 → **3.9**.
2. `frame.WIRE_PAD`:
   - centre the column on z = −2.0 (pad centres z = 2.55 − 1.3k), and say that z values are centres;
   - adopt P2: columns x 46.9–48.5 and 48.7–50.3, pads 1.0 × 1.6; or P1, x 48.4–50.3;
   - copper ≥ 0.3 mm from the rear edge.
3. `frame.WIRE_PADS` order → `["VBUS", "GND_CHG", "BAT-", "OUT_A", "OUT_B", "LED-", "LED+", "BAT+"]`.
4. Owner decision L1/L2/L3. With L3: `MIC_PORT.z` → −2.0, and `BUTTON` → (45.0, −2.0) with body (2.0, 3.0).
5. `hw/pod/gen.py`:
   - add **D4 1N5819WS** (C191023) in series J3 → VBUS;
   - split **R14 → R14a 1k + R14b 1k** (C11702);
   - J1/J2 values XDCR_A/B → OUT_A/OUT_B to match the frame labels;
   - J1–J8 footprints → `WirePad_SMD_1.0x1.6mm`;
   - TP1–TP5 → `ProbePad_0.8x1.4mm` in the front-edge column.
   - Move `padboard.pretty` into `hw/lib/` if the pod uses it.
6. Shell:
   - blind nut pockets, or a screw-length limit;
   - insulated nut joints;
   - unpainted screw heads;
   - a wire comb behind the rear edge;
   - ribs must not overhang the outer face beyond the 0.6 mm band where the P2 joints stand 0.45 mm proud.
7. Pad (`hw/mech/pad.py`):
   - **Done on my side:** J3/J4 now sit at KiCad y −4.0, as asked. J5/J6 sit at **(±1.775, 3.275) with a Ø0.85 pad (0.45 drill)**, not the requested (±1.85, 3.25) / Ø0.9. The request left only 0.20 mm of copper to the long edge; this keeps 0.30 and still clears the dam by 0.05.
   - **Please set `PADBOARD_LAYOUT` to these numbers.** `hw/padboard/mech.py` already runs pad.py's own `joint_check` against them: all 6 joints pass, with 0 mm³ overlap and laps of 1.36–1.80 mm.
   - Parts envelope up to y 3.9 (LED 3.88). pad.py already uses this.
   - The LED ring is a cast clear-epoxy diffuser around an opaque plug (pad.md). That settles my earlier light-guide worry.
8. Shell (`hw/mech/shell.py`):
   - make the RTV dot at each nut-slot mouth **required** (§5);
   - keep ribs, webs, stops and foam inside the 0.6 mm bands, which they are today (checks.json);
   - leave room for ~35 mm wires, so the board can lie beside the pod for flashing (15 % of the loop space).
9. Spec: §3/§8/B6 still say magnetic pogo. Record the screw-contact scheme if the owner adopts it.
10. Frame: if the owner accepts the shell's proposal, `LID_SCREWS` → [(64.2, 2.7), (64.2, −5.6)] and the PCM moves (the shell agent's request). This note already uses those numbers.
