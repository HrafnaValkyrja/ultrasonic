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
3. **Mic port hole is 0.5 mm** (the library footprint); the spec wants 0.8 mm.
4. **The PMCXB290UE (Q1, Q2) footprint** comes from EasyEDA and has pads smaller than Nexperia's land pattern (datasheet Fig. 32). Redraw it before layout.
5. **SMPS loop** (U1 pin 20 → L1 → C8/C9): keep it tighter than the router did.
6. **Silkscreen** labels are shrunk to 0.4 mm so the board is readable; set real silk sizes for fabrication.
