# NEXT 5 (ranked; 2026-10-08 ~16:45 ET)
Four proofs landed (docs/proof/): electrical PASS with the fw clamp (b1501b0), thermal PASS thin (1b15176), physical PASS with 3 open items (a20ec65), buildability PASS with 2 hard steps (4cabf8c). Pen test: weekend bench day. Both pods alive.

1. P-ELEC-OPEN: close the electrical OPEN rows (K4 rail ripple, USB D+/D- through BM28, BM28 SI, cap DC-bias derating); sync ECR-0020 noise text (26.4/26.2 vs 34.8 dB on the re-routed boards). ~1.5 h.
2. P-THERM-BURST: LDO transducer-burst duty from firmware (thermal row 8) -> U4 temperature rise at the clamped 208 mA; re-fetch the touch-limit standard text. ~1 h.
3. P-PHYS-GRAZE: tub/cell 0.145 mm3 graze in the K4 shell; part_heights entries for C16/C17/C21. ~45 min.
4. P-BUILD-EASY: ease the 2 hard build steps (cell with welded tab leads: sourcing; printed alignment jig for the lid stack: model + STL). ~1.5 h.
5. N-K1T-BUTTON (guess, model both): KMT022 breaks the K1-thin 0.6 lid; dome on new F pads (board edit + re-route, serial heavy job) or proud skin. ~1.5 h.
Done: N-K4-TOOLS 56cf4fd (K4 flip = hw/current.yaml default line + fw/gen regen; old WIP in stash@{0}), N-K1T-RELEASE (r2-release in 6eba28a, gate BLOCKED), N-K1T-DUCT, N-6L-STACKUP, N-K1T-PARITY, N-PENTEST-CARD, N-POST-GAP.

Ruling-needed (hers): A-K4-VISION (weekend bench day), A-TODAY-BODY-MEASURE, A-IDLE-TRADE, A-6L-QUOTE (optional), A-CAP-CURVES (optional). Orders/payments: owner-only.
