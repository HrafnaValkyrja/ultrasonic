# K4 release package (P + M boards) - 2026-10-08 - gate BLOCKED (see gate.yaml)

Files (per board X in P, M): `k4_X_gerber_drill.zip` (Protel-ext Gerbers F/In1-4/B Cu, masks, paste, silk, Edge.Cuts; Excellon PTH+NPTH; drill maps; job file),
`bom_X.csv` (JLC columns Comment/Designator/Footprint/LCSC Part #), `cpl_X.csv` (Designator, Mid X, Mid Y, Layer, Rotation; absolute KiCad coordinates, y up, mm),
`pin1_check.csv`, `sourcing_dated.csv` (live JLC API per line), `build_release.py`, `src/` (BOMs matching the boards).

Board: 15.5 x 12.0 mm (bbox 15.55 x 12.05 with edge line), 6 copper layers, 0.8 mm, ENIG (BM28 0.35 mm pitch, QFN/DSBGA need flat pads), min track/space 0.09/0.088 mm (persisted JLC fine rules in .kicad_pro), parts both sides (top, from cpl_X.csv. P top: C2 C9 C11 C22 J21 Q1 R2 R3 R4 R6 R21 R22 R23; P bottom: the rest incl. U1 QFN48, Y1, L1, Q2. M top: C16 C17 C19 D4 D5 J20 R8 R9 R12 R13 R14 U2 U3 U4; M bottom: the rest incl. SW1, U6, RT1).

## Quantities (owner rule: 2 worn + 3 spares, O19)
JLC PCBA minimum is 5. Order 5 P + 5 M assembled; every BOM line = qty/board x 5. Spares are whole boards, so a P/M pair is always available.
MCU C5271013 stock was 19 on 2026-10-08 (5 needed): reserve early.

## Stack-up / impedance
No `(stackup)` block in the board files; JLC publishes 6L builds for 1.2/1.6/2.0 mm only, NOT 0.8 mm (read 2026-10-08, K4-STACK6). Order 6L 0.8 mm with JLC's default build, **no impedance control**: nothing here claims a controlled net (USB D+/D- are full speed, ~15 mm). Planes: In1 GND, In2/In3/In4 per router assignment; sim/noise assumed uniform dielectrics (0.2 dB spread to thin-outer). Copper outer 1 oz-class (35 um nominal on JLC 6L), inner 0.5 oz (15 um).

## Vias / via-in-pad
All vias 0.15 mm drill / 0.25 mm pad, through (F-B) only: P 107, M 70 (pcbnew count). That is JLC's minimum (0.15/0.25) and carries a small-via surcharge. **Via-in-pad: 67 vias land on SMD pads on P (U1 QFN48 exposed pad, R3, R5); none on M.** Order flag: **"Via-in-pad / plugged: Epoxy/copper filled and capped (POFV)"**, which JLC covers for 0.15-0.55 mm vias (capabilities page Sep 2026). Ink-plugged is NOT allowed in pads. Without POFV, solder wicks into the QFN EP vias. Drill histogram: P PTH 0.15 x107; M PTH 0.15 x70, NPTH 0.65 x1 (mic port).

## CPL rotation notes (UNVERIFIED against JLC's rotation DB; the preview decides)
CPL rotation = KiCad's orientation as-is (top and bottom). JLC's bottom-side and QFN/BGA conventions differ by footprint and are corrected only in JLC's placement preview. Check, in this order (pin-1 offsets in `pin1_check.csv`):
1. **U1 STM32U575 QFN48 (P, bottom, 90 deg):** pin 1 corner dot must match the silkscreen; JLC QFN default commonly wants +0/+270 vs KiCad; expect a possible 90/180 offset.
2. **J20/J21 BM28 (J21 P top 180, J20 M top 0):** receptacle and plug are mirror pairs; the 30P plug has a different pad 1 end. Verify the alignment arrow vs the listing, not the symmetry (the part is symmetric electrically - a wrong 180 mates pin n to pin 31-n).
3. **U3 BQ25180 DSBGA (M, top, 90):** ball A1 ID mark; offsets are common on DSBGA. 0.4 mm pitch.
4. **U2 mic LGA (M, top, 0):** port hole at the NPTH; pin 1 chamfer; U4 X2SON (EP 1 mm), U6 SOT-553, Q1/Q2 DFN1010B (Q2 bottom, 180), D4/D5 polarity.
Do not accept the preview with any part highlighted red; stop and re-export.

## Panel / rails (15.5 x 12 boards)
JLC assembly needs rails + tooling; boards this small cannot run alone. Options:
A. **(recommended) 1 P + 1 M per panel, 5 panels** = exactly 5 + 5 boards (2 worn + 3 spares); Different Design = 2, panel by customer. Side by side with 2 mm gap and mouse bites: 33 x 12; 5 mm rails on the long sides: 33 x 22; 2 mm tooling holes + 1 mm fiducials in the rails. If JLC enforces the 70 x 70 minimum seen in assembly.md, widen the rails (free FR4, same price).
B. 5 P + 5 M in one 2-row panel: fewer panels, but a single bad row blocks both; JLC min PCB qty may force 5 such panels.
C. Order loose and "Panel by JLCPCB" V-cut: not recommended (mouse-bite/V-cut leaves 0.4 mm tolerance against 0.35 mm-pitch connector edge placement and offers no fiducials).
No panel file made (needs the final board hashes).

## Cost estimate, 5 + 5 assembled (2026-10-08, JLC parts API 08:40Z; fees from JLC page read 2026-10-02: assembly.md)
| Line | USD | Basis |
|---|---|---|
| Parts (38 lines, 34 distinct LCSC, 5x each) | 78.32 | live API price at qty, `sourcing_dated.csv`; MCU alone 5 x 9.02 = 45.1 |
| Feeder loading $1.53 per part type | 52 (58 if per board line) | 34 distinct (27 Extended) |
| Setup + stencil, double-sided | 68 to 135 | $51.12 + $16.42 once for one combined order; double if P and M ordered separately |
| X-ray (QFN48, DSBGA, LGA, X2SON, DFN, X1SON) | 25 to 70 | scaled from $10-28 per 4 boards; unquoted |
| PCB 6L 0.8 ENIG, 0.15 vias, POFV, 5 panels | 60 to 160 | UNQUOTED: JLC headline "6L 5 pcs from $2" excludes ENIG, POFV, small-via fee |
| Shipping, tax | not included | |
| **Total** | **about 285 to 500** | mid ~390; over the ~$300 budget line (O13) unless the low end holds |
Live quote is required before relying on any of this. Hand-off to the upload checklist: `operate-jlcpcb-order` (not started).
