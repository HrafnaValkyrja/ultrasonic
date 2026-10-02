Source: docs/research/simplification-study.md (2026-10-02). Package A is the **floor** of the simplification study: low-risk cleanups that reverse no owner decision. It does NOT meet O20 (pod size unchanged at 7.80 cm3); the recommended package is B, which contains every A item. SCHEMATIC changes are to be batched into the next schematic revision, not applied mid-study; gen.py is untouched.

**Members (de-duplicated across the five domain studies)**
- OUT-02 R21 shunt 1206 (C25334, Basic) -> 0402 Panasonic ERJ2BSFR10X (C409058, Extended; 166 mW, 15,928 in stock at 2026-10-02T22:22Z). No Basic 0402 0.1 ohm exists (JLC API 2026-10-02T22:51Z). -8.5 mm2, thinner part under SW1.
- OUT-04 delete the D1/D2 DNP footprints (PESD5V0S1BL) and the unrouted OUT_A stub.
- PER-02 delete R11: AN2606 Rev 69 Table 199 shows the ROM loader pulls PA10 up itself. PA10 becomes a spare pin.
- PER-03 = PWR-06 delete R17 (CHG_INT pull-up): PA15 internal pull-up, EXTI falling; PB5 strapped to GND (ECR-0013 S1, mandatory) and PWR_UCPDR.UCPD_DBDIS set first in boot.
- PER-06 merge C20 into the VDD pin-48 100 nF (<= 1.5 mm from pins 1 and 48).
- PWR-03 delete R19 and net CC_SENSE; Rd R18 and J12 stay. PA3 freed.
- PER-11 drop TP6 (probe VSYS at C21); DFU-first first flash through R1's PH3 pad (TP1-TP5 stay as the SWD backup).
- OUT-07 = PWR-12 firmware duty clamp |2d-1| <= 0.5 (CCR 50-150 of ARR 200, applied after the shaper and dither, live before TIM1 first runs) and a self-test capped at -12 dBFS: closes ECR-0005.
- FW-1 firmware bundle: over-current cutoff on the F4 samples while the self-test runs (power 0; sub-output issue 6 stays OPEN, held by the OUT-07 clamp, IWDG and R3/R5; an always-on ADC1 guard is a knob at +0.15 to +0.34 mA, interpolated from DS13737 Rev 10 Table 103), daily wire-health check, ILIM step-up, interrupt/NACK counters, charge voltage as a knob (VBATREG, default 4.20 V; 4.10-4.15 V costs 1-2 h worst-case runtime, below D18's ~12 h target).
- Process: ASM-01 (Standard PCBA, 70 x 70 mm panel, rails = O9 frame, corrected fee model), ASM-05 (ENIG, rules >= 0.10 mm, EP vias filled or tented), ASM-11 (BOM lines as the cost metric), ASM-X (no-wash, mask the mic port, JLCDFM written OK, assemble 6-8 boards), SIZ-15 (wear dummies before any outline freeze; ECR-0006 is deferred by O21).

**Totals (computed by docs/research/simplify/synthesis.py)**: placed parts 56 -> 52 (R11 R17 C20 R19); BOM lines per order 30 -> 30; Extended types per order 11 -> 12 (R21); BOM $/pod +0.06; $/order +0.22 (parts), fees 0 under Standard PCBA ($1.53 per line, Basic or Extended); courtyards 246 -> 229 mm2; MCU pins listed free 8 -> 9 (PA3, PA10 freed, PB5 consumed; 4 are clean once PC13 static, PB15 hazard and the MDF-fallback pins PB1/PB8 are set aside); +3V0 peak 326 -> about 92 mA; VSYS peak 93 % -> about 27 % of the cell's 350 mA pulse rating; average current 0.

**After-state**: F1-F15 all covered. Changes: F4 (R21 0402), F10 (CC branch = R18 only), F13 (INT on the internal pull-up, I2C pull-ups kept), F14 (no TP6, no R11, DFU-first), F7 (lower peaks). Arm wires 4, hand wires 12, lid and shell unchanged. Firmware: UCPD_DBDIS first; PA15 pull-up EXTI; PA10 pull-up in the boot stub before the DFU jump; write-protected boot stub; ILIM 100 mA -> enumeration / BC1.2 / step-up watching PA1 (wall chargers never enumerate); duty clamp; self-test cap.

**Bench-verify on board 1**: DFU entry with R11 absent; INT edge and no stuck-low with UCPD_DBDIS; ILIM policy at a wall charger without D+/D-; 322 mA step on +3V0 and VBAT with a scope; |Z| calibration against an 8-12 ohm resistor.

**Owner decisions**: accept firmware-only protection for ECR-0005 and write the D17 ceiling number down; O12(c) charge-time policy for CC-less chargers; O13 (Extended count +1, fee-neutral); Standard PCBA and the corrected budget (about $270-385 per order before cell and exciter).

**Open ECRs**: CLOSES ECR-0005 (with the rail-budget.yaml edit in the same commit, else tools/checks/interfaces.py turns FAIL). SUPERSEDES ECR-0002 item 4 (R11) and item 1 for R17 (item 1 survives for R15/R16). Compatible with ECR-0003 (its R11 half is subsumed), ECR-0013 (S1 mandatory; F1 rewritten for the CC-less ILIM policy). ECR-0004 stays pending a written JLCDFM verdict. Extends ECR-0009 (capped self-test), ECR-0010 (DFU-first), ECR-0006 (dummies), ECR-0008 (reserve parts). ECR-0001 is independent in A.

**Same-commit contract edits (the tracker is blind to R11, R17, R19, C20, D1)**: pin-contract.yaml (CC_SENSE, BOOT_RX), rail-budget.yaml (pull-up row, R21 rating, ECR-0005 waiver and peak), vcrm.yaml, bom_check lock, part_heights.yaml (C409058), the files listed under 'Not watched' below (firmware-emulation.yaml, layout-noise.yaml, bom_check.py self-test, system_map.py, place_r1.py, bom.py), then regenerate integration-map.md and re-run layout-noise and e2e.

**O21/O22**: A has no hardware-only gate that needs a purchase (OUT-07 needs your acceptance), so O21 does not block it; the layout-noise and e2e re-runs on the final layout are part of the O22 freeze criteria.
