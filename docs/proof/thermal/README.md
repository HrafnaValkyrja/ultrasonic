# P-THERM: is the K4 pod thermally possible? (2026-10-08)
Method: lumped transient network (`thermal.py`, numbers reproducible, 3G fence): U3 die - board - shell - 35 °C ambient, cell coupled to board (1.4 mm air gap, 113 K/W) and shell (13.9 K/W). Envelope from `hw/mech/dims_k4.py` (A_out 23.5 cm²). No 2-D FEM: the unknowns are the film coefficient and gaps, not conduction detail. Plot: `thermal.png` (dark).

## Heat sources (130 mA charge, 5 V dock, D4 drop 0.30 V -> VIN 4.7 V)
| part | dissipation | basis |
|---|---|---|
| U3 BQ25180 (TI 1-cell linear charger) | 0.19 W at VBAT 3.3 V, 0.12 W at 3.8 V, 0.07 W at 4.2 V | (VIN-VBAT) x (130+5 mA), TI SLUSE99C §8.3.7.7 formula |
| D4 PMEG3005EL (Nexperia 30 V Schottky) | 0.04 W | 0.30 V x 0.135 A |
| cell + PCM (protection circuit) | 5 mW | I²R, 0.3 Ω ASSUMED (no datasheet ESR in repo) |
| awake, worst (MCU 5.8 + audio 2.15 + bridge ctrl 1.06 + transducer avg 2.5 = 11.5 mA, VSYS 4.2 V) | 48 mW (LDO U4 14 mW) | `docs/system/rail-budget.yaml` |

## Results
| # | check | result | verdict |
|---|---|---|---|
| 1 | U3 junction, charging, 35 °C docked | 52 °C (board 47 + P x RθJB 30.3); bounds with θJA 65/107 °C/W on 0.2 W: 48-56 °C. Limit: THERM_REG 100 °C | PASS (48 K margin) |
| 2 | D4 junction | ~71 °C (existing figure, 500 K/W) | PASS |
| 3 | Cell temp, charging, **docked, still air** (h 10 W/m²K) | peak 43.5 °C at 21 min, limit 45 °C (0-45 °C charge, `sub-power.md` L134) | PASS, margin only 1.5 K |
| 4 | Cell temp, charging, **worn / covered** (h 5, bound) | peak 49.4 °C | FAIL as a bound; mitigated by U3 JEITA (TS 45 °C stop) via RT1 (reads board, hotter than the cell, so conservative) -> charge pauses, never overheats the cell. Charging worn is not a stated use |
| 5 | Skin touch, charging docked | shell 42.9 °C vs 43 °C | PASS, zero margin |
| 6 | Skin touch, charging worn bound | shell 48.9 °C | FAIL vs 43 °C; do not charge on the head |
| 7 | Awake runtime, worst | 48 mW: shell +2.1 K (docked-like) to +4.1 K (bound) -> ~39 °C at 35 °C ambient; U4 +2.3 K | PASS |
| 8 | LDO U4 under transducer drive, fw clamp 208 mA (FWSIM-R64), VSYS 4.2-4.5 V docked (drop 1.2-1.5 V) | Playback is real-time audio, not scheduled bursts (spec §5: heterodyne/compression; bat calls last ms, spec L291). Duty is signal-driven, so bounded three ways. (a) Continuous full-clamp sine (impossible bound): mean |i| = 0.637 x 208 = 132 mA -> 0.16 W (4.2 V) to 0.20 W (4.5 V) -> +26 to +33 K at θJA 166 °C/W (steady). (b) Budgeted worst average, rail-budget exciter 2.5 mA: 3.8 mW at 4.5 V -> +0.6 K (equals 1.9 % of (a)). (c) One call, 10 ms at the clamp (0.2 W mean): ΔT = P θ (1-e^(-t/τ)); τ of a small-package LDO is ~0.1-1 s (ASSUMED, no datasheet Zth in repo): +0.3 K (τ 1 s) to +3 K (τ 0.1 s). Even a 200 calls/s buzz at 10 ms is case (a). U4 junction then ~35 + 3 (shell) + 33 = 71 °C worst, far under its 125 °C | PASS (realistic +0.6 K; bound +33 K); τ and Zth OPEN until a bench log of U4 (PWR-I12) |
| 9 | Cell ESR, h, R_BS | assumed, not measured | OPEN: log board+cell temperature through a full charge (PWR-I12 / ECR-0009 item 3) |

## Limits (sources; touch text re-fetched 2026-10-08)
- Cell charge 0-45 °C: Renata ICP401230 V02 08/2019 (as in `sub-power.md`).
- Touch: IEC 62368-1 (TS1 table, Table 42 in ed. 2.0 2010; Table 38 in later editions): TS1 max 48 °C, metal and plastic, contact > 1 min; 51 °C metal / 60 °C plastic for 10-60 s; TS2 = TS1 + 10 K. Source: UL Japan tech brief 'Touch Temperature' (Copyright 2010 UL), https://japan.ul.com/wp-content/uploads/sites/27/2014/06/1_techbrief_touchtemp.pdf, fetched 2026-10-08 (secondary source; the standard text itself is paywalled). The earlier '~43 °C' is NOT the 62368-1 number: it is the IEC 60601-1 applied-part limit (recall, still unconfirmed). Project line stays 43 °C (conservative, worn on skin ~33-35 °C): rows 5/6 verdicts unchanged; against 62368-1 TS1 48 °C, row 5 has 5 K margin and row 6 (48.9 °C) is a marginal FAIL.
- U3 numbers: TI BQ25180 SLUSE99C §7.3, §8.3.7.7 (via `docs/system/audit-datasheet-claims.md` row 7, 2026-10-02).

## Verdict
Possible with thin margin: docked charge keeps the cell under 45 °C by 1.5 K and the shell at the 43 °C line. The one real lever is current: capping charge at 65 mA (0.5C, already an open owner question A-SAFETY-REVIEW) halves U3 heat and gives ~20 K margin. Recommend: ship firmware default 0.5C, 130 mA only below ~30 °C ambient (RT1 reads).

**Lead note 2026-10-08:** the owner ruled 130 mA (1C) in O34, so 1C stays the default. The hot case is already covered in hardware: U3 TS_HOT is set to 45 °C (sub-power.md register plan), so above that charging pauses and resumes once the cell cools; it never overheats. A 0.5C fallback above ~30 °C ambient (RT1) is a firmware option to raise only if the bench first charge (G5, thermocouple) shows pauses. Row 8 (LDO duty) and the touch-limit re-fetch closed 2026-10-08 (see table and limits).
