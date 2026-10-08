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
| 8 | LDO transducer bursts (327 mA at VSYS 4.2 V = 0.39 W) | burst-only; avg already in 7; θJA 166 °C/W x 0.39 = 65 K if continuous | OPEN (needs duty from firmware; tied to ECR-0005) |
| 9 | Cell ESR, h, R_BS | assumed, not measured | OPEN: log board+cell temperature through a full charge (PWR-I12 / ECR-0009 item 3) |

## Limits (sources; NOT re-fetched this session, verify before citing outward)
- Cell charge 0-45 °C: Renata ICP401230 V02 08/2019 (as in `sub-power.md`).
- Touch: IEC 62368-1 Table 38 (TS1) and IEC 60601-1 Table 24 applied-part limits: ~43 °C for contact beyond ~10 min (recall, 2026 knowledge, OPEN to confirm against the standard text). Skin ~33-35 °C worn, so a 43 °C surface is the line.
- U3 numbers: TI BQ25180 SLUSE99C §7.3, §8.3.7.7 (via `docs/system/audit-datasheet-claims.md` row 7, 2026-10-02).

## Verdict
Possible with thin margin: docked charge keeps the cell under 45 °C by 1.5 K and the shell at the 43 °C line. The one real lever is current: capping charge at 65 mA (0.5C, already an open owner question A-SAFETY-REVIEW) halves U3 heat and gives ~20 K margin. Recommend: ship firmware default 0.5C, 130 mA only below ~30 °C ambient (RT1 reads).
