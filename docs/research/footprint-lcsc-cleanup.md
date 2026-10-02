# Footprint library cleanup: stray `LCSC Part` properties (ECR-0012)

**Date:** 2026-10-02 (machine clock, EDT) · **Owner rule:** part identity lives in the schematic only (`hw/pod/gen.py`).
**Status:** the library is clean and committed (git `779872e`, 2026-10-02 00:40 EDT, by the session that hit the usage limit). This pass re-verified it and recorded it here. The placed board on disk still carries the old properties until the lead regenerates it.

## What was wrong

`easyeda2kicad` (the tool that fetches a footprint by LCSC number; AGPL-3.0, `docs/research/methodology.md` §3) writes one line into every footprint it imports: `(property "LCSC Part" "C...")`, the number of the part it was imported *from*. Our footprints are shared by several parts, so the baked-in number is often not ours. Any board-based BOM tool reads that field: kicad-jlcpcb-tools, Fabrication-Toolkit and KiBot all match fields named like `lcsc` (methodology §2 item 3, read 2026-10-01). The JLC BOM we order from (`hw/pod/bom_jlc.csv`) comes from `gen.py` and was correct, so nothing was ordered wrong. The board file was the trap.

## What was removed (all in `hw/lib/lcsc/lcsc.pretty/`)

One line per file, property `LCSC Part`. "Ours" is the LCSC number `gen.py` puts on the part(s) that use the footprint.

| File (`.kicad_mod`) | Old value | What that number is | Ours | Verdict |
|---|---|---|---|---|
| `SOT1216_L1.1-W1.0-P0.35-BL-EP` | **C552750** | PMCXB900UELZ, a *different* Nexperia complementary MOSFET pair | C19654206 (PMCXB290UE) on Q1, Q2 | **WRONG part** |
| `SW-SMD_4P-L3.0-W2.6-P1.85-LS3.4` | **C221708** | KMT031NGJLHS, C&K sealed tact switch, **3.4 N** | C221707 (KMT022NGJLHS, **1.6 N**) on SW1 | **WRONG part** |
| `SW-SMD_L3.0-W2.0-LS3.5` | C221821 | KXT321LHS, C&K 3.0 x 2.0 mm switch, 1.6 N (the switch before rev D) | none: footprint unused since rev D | stale, unused |
| `SOT-563_L1.6-W1.2-P0.50-LS1.6-BL` | C177025 | DMC2400UV-7, Diodes Inc. complementary pair (an ALTERNATE in the lock) | none: unused alternate | stale, unused |
| `DSBGA-8_L1.6-W0.9-R2-C4-P0.40-BL` | C3682423 | BQ25180YBGR, TI charger | C3682423 on U3 | agrees, stray |
| `FC-135R_L3.2-W1.5` | C32346 | Q13FC13500004, Seiko Epson 32.768 kHz crystal | C32346 on Y1 | agrees, stray |
| `L0806` | C337891 | DFE201610E-2R2M=P2, Murata 2.2 uH inductor | C337891 on L1 | agrees, stray |
| `SOD-882_L1.0-W0.6-BI` | C84374 | PESD5V0S1BL,315, Nexperia 5 V bidirectional ESD diode | C84374 on D1, D2 (DNP) | agrees, stray |
| `SOD-923_L0.8-W0.6-LS1.0-RD` | C87910 | ESD9X5.0ST5G, onsemi 5 V ESD diode | C87910 on D3 | agrees, stray |
| `SOT-553-5_L1.6-W1.2-P0.50-LS1.6-TL-1` | C1972959 | TPD2E2U06DRLR, TI 2-channel USB ESD array | C1972959 on U6 | agrees, stray |
| `X2SON-4_L1.0-W1.0-P0.65-TL-EP` | C5220164 | TPS7A2030PDQNR, TI 3.0 V LDO (low-dropout regulator) | C5220164 on U4 | agrees, stray |

Of eleven, two named a wrong part, seven agreed only because one part uses the footprint, and two belong to parts no longer on the board. That is why nobody saw it: the stray field only bites when a footprint is shared or the part changes. No other identity property (`LCSC`, `Manufacturer`, `Manufacturer Part`, `MPN`) was present in any library footprint. `Knowles_LGA-5_3.5x2.65mm_Port0.6` (hand-edited) and the two footprints in `hw/lib/pod.pretty` never had one.

## How it was checked (2026-10-02)

- **Byte-identical apart from the one line.** For each of the 12 files: `git show 779872e^:<file>` with the single `(property "LCSC Part" "...")` line deleted equals the current file. 12/12 equal.
- **Still loads.** `pcbnew.FootprintLoad` (KiCad 10.0.6) returns a footprint for all 12, with the same pad counts as before.
- **No identity left.** `tools/checks/bom_check.py` check `identity` scans every `.kicad_mod` under `hw/lib` for identity-named properties (`LCSC`, `MPN`, `Manufacturer`, `Supplier`, `Vendor`, `Part No`; JLC placement-offset fields such as `JLCPCB Rotation Offset` are not identity and are ignored) and for any LCSC-shaped number (C and four or more digits) anywhere in the file, descriptions and tags included: none.

## What is still open

1. **The placed board.** `hw/pod/draft_r1/pod_r1_placed.kicad_pcb` (saved 2026-10-01 21:03 EDT, before the cleanup) still carries all 11 properties on the footprints that use these library files. **Q1/Q2 carry C552750 and SW1 carries C221708.** Regenerating the board from the cleaned library removes them. Until then `bom_check` reports `WARN identity ... ECR-0012 proposed` and names each wrong ref and its library file; with `--strict` (release gate) it is a FAIL, and it turns into a FAIL by itself once ECR-0012's Status is anything but proposed, approved or implemented. The eight agreeing strays (D1, D2, D3, L1, U3, U4, U6, Y1) are no longer flagged: a value equal to the schematic's LCSC is correct, and it is exactly what the placer follow-up below would write.
2. **Superseded copies.** `hw/pod/kicad-draft/lcsc.pretty/` (the 20 x 11.5 mm draft project; its README says it is not a layout to order) still has 8 footprints carrying `LCSC Part`, including `SOT1216_...` with C552750. Outside this cleanup's scope, so untouched; `bom_check` WARNs on it. Clean or delete that folder.
3. **Recurrence.** Importing a footprint with `easyeda2kicad` writes the property again. Run `python3 tools/checks/bom_check.py` after every import: a property in `hw/lib` is a FAIL.
4. **Symbols are different.** `hw/lib/lcsc/lcsc.kicad_sym` carries `LCSC Part`, `Manufacturer` and `MPN` per symbol. That is schematic-side identity and correct by design: `bom_check` confirms the 9 symbol-based parts agree with `gen.py`, and checks every LCSC number on the schematic against `LCSC_IDENTITY` in `bom_check.py` (MPN for every part, value and package for the R/C parts; JLC parts API via `tools/jlc.py`, queried 2026-10-02T05:40Z), so a number that gen.py attaches to the wrong value now FAILs. The unused symbols KMT031NGJLHS (C221708), KXT321LHS (C221821) and DMC2400UV-7 (C177025) are not a defect.
5. **Placer follow-up (methodology §2 item 3, not done here).** Have `place_r1.py` write the netlist's LCSC into each board footprint, so a board-based BOM tool can cross-check. `bom_check` already accepts any field or text on a board footprint that carries the schematic's LCSC number (a write-back to `LCSC Part` or `LCSC` is PASS, counted as agreeing) and FAILs any LCSC number that disagrees, whatever the field is called. `JLCPCB Rotation Offset` and `JLCPCB Position Offset` fields are not identity and are never compared with the LCSC.
