# D-onechip: can one charger+LDO chip replace U3 + U4 on K4? (ledger I-005, 2026-10-08)

Verdict: **no chip wins. Keep U3 BQ25180 + U4 TPS7A2030.** Saves 1-5 small parts, costs area and LDO current; the mic-rail noise is unproven.

## K4 power parts today (hw/pod/k4/bom_jlc_{P,M}.csv, docs/system/sub-power.md)
- U3 BQ25180 (TI linear charger, power path, I2C, JEITA, ship mode; DSBGA-8, ~1.6 x 1.0 mm), C3682423, $2.04.
- U4 TPS7A2030 (300 mA, ultra-low-noise 3.0 V LDO; X2SON-4, 1 x 1 mm), C5220164, $0.22. The sole mic/MCU rail, ~7 uVrms.
- Support: C15 VBUS, C16 VBAT, C21 VSYS, C17 (U4 in), C18 (U4 out), D4 reverse-dock diode, R12/R13 VBUS divider, RT1 NTC, R8/R9 + C19 VBAT divider (PA4).
- "SMPS" = MCU-internal core SMPS (D11): L1 2.2 uH + C8/C9. Not replaceable by a charger chip.
- No separate fuel gauge exists: SOC comes from the R8/R9 divider on the MCU ADC.

## Candidates (TI product pages, fetched 2026-10-08; datasheets not opened)
| | BQ25180 (now) | BQ25155 | BQ25120A |
|---|---|---|---|
| LDO / load switch | none (U4 external) | I2C load switch or LDO **<= 150 mA** + 10 mA 1.8 V always-on | 100 mA LDO + **300 mA buck** |
| LDO noise | n/a | not on page; unverified | not on page; unverified |
| JEITA/TS | yes | yes | yes |
| Ship mode | yes | 10 nA | < 50 nA |
| Package | DSBGA-8 ~1.6 x 1.0 (about 1.6 mm^2) | DSBGA-20, 2.0 x 1.6 = 3.96 mm^2 | DSBGA-25, 2.5 x 2.5 = 6.76 mm^2 |
| JLC (2026-10-08) | 4225 in stock, $2.04 | C2861172, **stock 25**, $1.76 | C2866577, stock 10, $3.90 |
| Gauge | no | no; 16-bit ADC can gauge | no |

## Checks
- Current: the clamped peak is 208 mA + ~11 mA = ~219 mA. BQ25155's LDO tops out at 150 mA and BQ25120A's at 100 mA, so **both fail**. sub-power.md already warns that the rail peak is 326 mA against U4's 300 mA.
- D11: BQ25120A's buck is a switcher that is not the MCU core SMPS, so it is not allowed. It is out on that alone.
- Noise: the mic sits directly on +3V0 and the design relies on U4's 7 uVrms (LN-M01 margin 26.5 dB pessimistic). A charger-embedded LDO is typically far noisier; no figure was found, so it is unproven.

## Parts and area (board M/P)
- Best case (BQ25155 as both): remove U4 (1.0 mm^2), C17 and C18, and possibly R8/R9/C19 (ADC gauging): **up to 6 parts of ~75**.
- Area: U3 1.6 + U4 1.0 = ~2.6 mm^2 becomes 3.96 mm^2. **The area grows by ~1.4 mm^2.** Only 3 caps and 2 resistors shrink the layout, ~1 mm^2.
- Lost: LDO headroom (150 vs 300 mA), mic-rail noise, existing validated layout and the PA2/TS plumbing; stock of 25 is too thin for a build.

## Recommendation
A) Keep the two-chip split (recommended). B) Swap U3 for BQ25155 and keep U4: no gain, as it is bigger. C) One chip: fails current and noise. Owner decides.
Unverified: LDO noise in both datasheets; the exact BQ25180 package area.
