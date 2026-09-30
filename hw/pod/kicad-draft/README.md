# Pod board: draft KiCad project (KiCad 10)

Open `pod.kicad_pro` in **KiCad 10** (the files are KiCad 10 format; KiCad 9 and older can't open them).
The project is self-contained: footprints, symbols and 3D models for the LCSC-sourced parts are in
this folder and referenced via `${KIPRJMOD}`. Standard parts use KiCad's own libraries.

## What this is
- **Board:** 20 × 11.5 mm, 4 layers, parts on both sides.
- **Placement:** by script (`hw/pod/place.py`).
- **Routing:** FreeRouting, fully routed.
- **DRC:** clean except the courtyard rings of neighbouring 1 mm test pads. Clearance is checked at JLC's 0.09 mm minimum.
- **`pod.net`:** the netlist from the schematic code (`hw/pod/gen.py`). The code is the source of truth; there is no `.kicad_sch`.
- **`bom_jlc.csv`:** every part with its LCSC number.

## What it is NOT
A proof that the parts fit and route. It is not a layout to order. Known issues to fix in the real layout:
1. **No ground plane.** The autorouter used all four layers for signals. Make In1.Cu a solid GND plane and route around it.
2. **The MCU's centre pad needs vias to ground** (thermal and ground).
3. ~~Mic port hole 0.5 mm~~ **Fixed 2026-09-30: 0.6 mm.** Spec §8 allows 0.6–1.0 mm, but the mic's ground ring has a 1.025 mm inner diameter, so 0.8 mm would leave only 0.11 mm to copper. 0.6 mm leaves 0.21 mm. Footprint `lcsc:Knowles_LGA-5_3.5x2.65mm_Port0.6`.
4. **The PMCXB290UE (Q1, Q2) footprint** comes from EasyEDA and has pads smaller than Nexperia's land pattern (datasheet Fig. 32). Redraw it before layout.
5. **SMPS loop** (U1 pin 20 → L1 → C8/C9): keep it tighter than the router did.
6. **Silkscreen** labels are shrunk to 0.4 mm so the board is readable; set real silk sizes for fabrication.

## Rev B updates (2026-09-30, after the audit)
**Done in this file:**
- **Board thickness 0.8 mm** with a real 4-layer stackup (it said 1.6 mm with no stackup). The dielectric values approximate JLC's 0.8 mm 4-layer build (7628/3313 prepreg class) `[Med]`. Pick JLC's stackup by name at order time and copy its exact numbers.
- **Mic port 0.6 mm** (item 3 above).
- DRC is unchanged at 186, all silk, text and test-pad courtyards.

**Not done here: import the new netlist** (`pod.net`, schematic Rev B) when you start the real layout (File → Import → Netlist):
- **U3 → MCP73832** (same SOT-23-5 footprint): open-drain STAT, so PA10 never sees 5 V.
- **New:** R11 100k (STAT pull-up), R12/R13 100k/100k (VBUS sense into PA1), C20 100 nF at VBAT pin 1.
- **Changed:** C4 → 10 µF **0603**; R1 (BOOT0) → 10k.
- **Also for the layout:** one 2.2 µF at **each** VDD11 pin (pin 46 has none); keep the SMPS loop tight.

**Audit claim checked and NOT upheld:** "TPS7A20 footprint pads oversized" (FP-1). The EasyEDA footprint matches KiCad's stock `Texas_X2SON-4_1x1mm_P0.65mm`, which is drawn from TI's DQN0004A drawing: signal pads 0.46 × 0.32 mm vs 0.46 × 0.31 mm, and the smallest pad gap is 0.134 mm vs 0.120 mm. The tight gap is the package's own; JLC's minimum is 0.09 mm. No change.
