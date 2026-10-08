# k1t mic duct on the 0.6 mm lid: R14 re-run (N-K1T-DUCT, 2026-10-08)

Two different checks were conflated in k1t-vs-k4-parity gap 3. They need separate answers.

| Check | Definition | src | k1t status |
|---|---|---|---|
| R14 (acoustic) | no in-pod peak > +15 dB re median, 20-85 kHz; notch >= -10 dB; mean 20-96 kHz >= -6 dB (spec.md L608; sim/acoustics/run_port.spec_checks) | sim/acoustics/duct_options.py, k1t geometry, 3 GB fence | see below |
| R-ACO-P5 (alignment) | bore axis vs board hole <= r_duct - r_hole (0.175 mm; hw/mech/dims_k4.duct_offsets) | hw/mech/out/k1t/checks.json | walls only 1.163 FAIL, gauge pin 0.14 PASS |

## R14 acoustic, lid 0.6 (plate off), Monte Carlo n=60, tol 0.2 mm, offset 0-0.2 mm
Existing (sim/out/mech/duct_options.json, 2026-10-07): all 0.6 lid options FAIL R14-peak with no mesh. With the floor mesh (Acoustex 042, which the real build has) only flush0.1 (0.70) and seatR1.2_0.3 (0.62) pass.

New rows (this run, scratch script on duct_options.stack/score). seat = counterbore depth, R = hex seat circumradius, boss = local outer lid boss, bore ID 1.0 unless stated:

| Option | bore len mm | peak dB no mesh / mesh | R14-peak no mesh | MC all-pass no mesh / mesh |
|---|---|---|---|---|
| flush0.1 (existing) | 0.5 | 19.5 / 16.9 | FAIL (mesh PASS) | 0.63 / 0.70 |
| flush0.1, R1.2 | 0.5 | 17.0 / 15.0 | PASS | 0.67 / 0.70 |
| flush0.1 + boss0.4 | 0.9 | 18.1 / 15.2 | PASS | 0.68 / 0.72 |
| seat0.3 + boss0.4 | 0.7 | 18.4 / 16.0 | PASS | 0.75 / 0.77 |
| **seat0.3, R1.2, boss0.4** | 0.7 | 16.1 / 14.3 | PASS | **0.75 / 0.77** |
| flush0.1, R1.2, boss0.4 | 0.9 | 16.6 / 14.2 | PASS | 0.67 / 0.72 |
| seat0.3, R1.2, boss0.7 | 1.0 | 16.1 / 14.0 | PASS, notch FAIL | 0.62 / 0.62 |
| flush0.1, R1.2, bore 1.2 | 0.5 | 15.5 / 13.9 | PASS | 0.70 / 0.72 |

Reference: Phase 2 (lid 1.5 incl. plate) MC 0.63 / 0.65, so every PASS row above is at or above today's accepted baseline.
Mechanism: R14 fails when the bore under the seat is shorter than ~0.5 mm (resonance moves up into 66-82 kHz); a 0.4 mm local outer boss (bore 0.7) pulls it down to ~60 kHz and a smaller seat lowers the peak. Boss 0.7 over-lengthens and breaks the notch rule.

## Verdict
- R14 acoustic: **best = seat 0.3 deep, hex R1.2, 0.4 mm local outer boss round the seat (bore 0.7 long), mesh on the seat floor**: nominal PASS with or without mesh, MC 0.75/0.77 (> Phase 2 0.63). No gauge pin needed for the acoustics. Cost: 0.4 mm bump on the outer face (O27 thickness: local, ring only; owner to accept). Runner-up with no bump: flush0.1 + R1.2 (PASS nominal, MC 0.67/0.70).
- R-ACO-P5 alignment: **not fixed by any of these.** Walls-only 1.163 mm is driven by x stop gap and cavity z slack, not duct length; widening bore to 1.2 raises the limit only to 0.275 mm. Only a registration feature (gauge pin or equivalent) passes; stays a bench check.
- Caveat: model is the k1-derived stack (ULTRASONIC_DESIGN=k1t geometry load), unvalidated by coupon (E3). No repo files other than this doc changed; geometry/dims untouched.
