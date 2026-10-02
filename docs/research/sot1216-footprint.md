# SOT1216 footprint for the H-bridge FETs (Q1, Q2)

**Date:** 2026-10-01.
- **Part:** **PMCXB290UE** (Nexperia, LCSC C19654206): a 20 V complementary MOSFET pair, one N-channel (TR1) and one P-channel (TR2) in one package. Q1 and Q2 are the two legs of the transducer H-bridge.
- **Package:** DFN1010B-6. Nexperia's outline code for it is **SOT1216**: 1.1 × 1.0 × 0.37 mm, six edge terminals at 0.35 mm pitch, plus two exposed drain pads underneath.
- **New footprint:** `hw/lib/pod.pretty/Nexperia_SOT1216_DFN1010B-6.kicad_mod`. In KiCad it's `pod:Nexperia_SOT1216_DFN1010B-6`.
- **Check:** `sim/checks/sot1216_footprint.py` (result: PASS).
- **Picture:** `docs/diagrams/sot1216-footprint.png`.

![old vs new](../diagrams/sot1216-footprint.png)

## Sources (primary, accessed 2026-10-01)

| Document | URL | Version | SHA-256 (first 16 hex) |
|---|---|---|---|
| PMCXB290UE data sheet: Table 2 pinning, Fig. 31 outline, **Fig. 32 reflow footprint** | https://assets.nexperia.com/documents/data-sheet/PMCXB290UE.pdf | v.1, 30 May 2023 (the only revision) | 4830f9a56131dd7c (the same file as in `datasheet-provenance.md`) |
| SOT1216 package information (Fig. 2 is the same footprint as Fig. 32) | https://assets.nexperia.com/documents/outline-drawing/SOT1216.pdf | 8 Sep 2022; footprint issue 17-03-31 | b4d4fc3a9935b606 |
| JLCPCB PCB capabilities | https://jlcpcb.com/capabilities/pcb-capabilities | live page | – |

- The stand-alone `reflow-soldering/SOT1216_fr.pdf` URL returned a bot-challenge page, so I didn't use it. Both PDFs above came through.
- The dimension labels say 0.2, 0.25 and so on. I also measured the land, paste and resist rectangles from the PDF's vector paths (129.17 pt/mm), and they agree to within 0.005 mm.

## What Nexperia's Fig. 32 actually says

- **Lands:** six, each 0.20 (along the pitch) × 0.25 mm, at 0.35 mm pitch. The two rows are 0.6 mm apart at the inner edges and 1.1 mm at the outer edges.
- **Solder paste:** 0.20 × 0.35 mm on the same centres. It overprints each land by 0.05 mm at both ends.
- **Solder resist (mask) opening:** 0.30 × 0.35 mm, i.e. the land plus 0.05 mm all round.
- **Occupied area:** 1.35 × 1.30 mm.
- **No land for the exposed drain pads (pins 7 and 8).** Inside the package they are the same metal as pins 6 and 3. Nexperia leaves them unsoldered, and the data sheet's Rth(j-a) of 386 K/W (typ.) is measured on this "standard footprint".

## Old vs new

| | Old: EasyEDA `lcsc:SOT1216_L1.1-W1.0-P0.35-BL-EP` (fetched via C552750 = PMCXB900UEL, a sibling pair in the same package) | New: Nexperia Fig. 32 |
|---|---|---|
| Lands 1–6, copper | 0.16 × 0.20 at y = ±0.420 | **0.20 × 0.25** at y = ±0.425 |
| Lands 1–6, resist opening | 0.16 × 0.20 (1:1) | **0.30 × 0.35** |
| Lands 1–6, paste | 0.16 × 0.20 | **0.20 × 0.35** (separate paste-only apertures) |
| Pads 7/8 (drains) | 0.35 × 0.25 at x = ∓0.280, **soldered**, 100 % paste | 0.35 × 0.25 at x = ∓0.275, **copper under resist, no paste** |
| Min copper gap | 0.19 (land to land) | **0.15** (land to land); 0.175 from a land to a drain pad |
| Min resist web | 0.19 | **0.05** (see JLC below) |
| Paste area ratio, 0.10 / 0.12 mm stencil | 0.44 / 0.37 | **0.64 / 0.53** (IPC-7525 wants ≥ 0.66) |
| Courtyard | 1.10 × 1.00 (body only) | **1.40 × 1.40**: 0.15 beyond the body and the copper, enclosing Nexperia's 1.35 × 1.30 |
| Silk | outline drawn across the pads | pin-1 dot only, 0.16 mm diameter, 0.17 mm clear of the resist opening |

**Pin-to-position check: no mismatch.**
- Every pad number 1–8 sits at the same physical spot in both footprints. The largest move is 0.005 mm.
- The layout is the Table 2 transparent top view turned 90°: pin 1 bottom-left, 1→6 counter-clockwise, pad 7 (D1) beside pins 1/6, pad 8 (D2) beside pins 3/4. It also matches the Fig. 31 bottom view once mirrored. The chamfered drain pad sits on the pin-1 side in both views.
- So the old footprint's numbering was correct, and the pin map in `hw/pod/gen.py` carries over unchanged: 1 S_N, 2 G_N, 3 D_P, 4 S_P, 5 G_P, 6 D_N, 7 D_N, 8 D_P, with TR1 = N.
- The orientation and origin are the same as the old footprint, so Q1/Q2 keep their rotations, and the same 3D model and transform still fit.

**KiCad DRC.** I ran the footprint alone, with the pod board's rules and the pod nets on its pads:
- **0 violations.**
- 3 "unconnected" entries: pads 3, 6, 7 and 8 are all on the bridge output net, and the board has to join them. This was already true with the old footprint.
- **With a 0.10 mm minimum resist web set:** KiCad merges each row's openings. The footprint's `allow_soldermask_bridges` attribute keeps this at 0 violations; without the attribute there are 4 `solder_mask_bridge` errors.

## JLC buildability (capabilities page, 2026-10-01)

| Item | JLC's figure | This footprint |
|---|---|---|
| Copper gap | 0.09 mm (multilayer); SMD pad-to-pad for assembly 0.15 mm | 0.15 mm: meets the assembly figure exactly, no margin |
| Resist dam | holds only where pads are ≥ 0.10 mm apart (green) | Nexperia's 0.05 mm web won't survive as drawn. Expect one ganged opening per row of three lands, which is normal at 0.35 mm pitch |
| Silk width | ≥ 0.15 mm | 0.16 mm |
| Silk-to-pad clearance | 0.15 mm | 0.22 mm to copper |

## Options (owner decides)

1. **Built, and recommended: Nexperia's pattern exactly. Pads 7/8 exist only as copper under resist.**
   - The netlist maps unchanged.
   - Nothing beyond Fig. 32 gets solder, so the joint geometry is the one Nexperia qualified.
   - The copper also stops a foreign net from being routed under the bare drain metal.
   - Thermal sanity check: worst case is full-scale DC into 8 Ω, about 0.33 A, through the P-FET at 1.2 Ω max (3 V gate drive). That is 0.13 W while conducting, ≤ 65 mW averaged, and about +25 K at 386 K/W. Real bursts are far lower, so the drain pads aren't needed for heat.
2. **Solder pads 7/8 as well**: give them a resist opening and about 50 % paste. This is the EasyEDA approach.
   - It is not Nexperia's pattern.
   - Extra solder under a 0.37 mm-thick, 1 mm part risks float and tilt, and bridging across the 0.175 mm to the S/G lands.
   - Only worth it if heat ever matters.
3. **Remove pins 7/8 from the symbol in `gen.py` and delete pads 7/8.** This is the purest match to Fig. 32, with no copper under the body. The cost is a schematic-generator change, which is the lead's file.

**Resist sub-option:** if JLC's DFM flags the 0.05 mm webs, set the resist margin to 0. JLC allows 1:1 openings, and that leaves 0.15 mm dams, which JLC holds. Gate-to-source bridges would then be less likely, at the cost of departing from Fig. 32.

## Uncertain
- Nexperia's figure doesn't say anything about copper under the body. Putting pads 7/8 under resist is our choice; it is not in the drawing.
- I don't know JLC's stencil thickness for this order. At 0.12 mm the paste area ratio is 0.53, which is marginal for release. Ask for 0.10 mm, or check the paste on the JLC preview.
- I haven't seen JLC's pick-and-place rotation for C19654206. The orientation is unchanged from the EasyEDA footprint, but the placement preview still has to be checked (`operate-jlcpcb-order`).
