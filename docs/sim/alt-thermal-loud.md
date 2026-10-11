# Alt test: worst-case thermal under loud12 + loud_shape, and a guarded fold-back (2026-10-11, simulated)
Scope: row 8 of docs/proof/thermal/README.md (5be4ca1; TI TPS7A20 SBVS338H θJA 166.1 °C/W, ψJT 3.0). No new measurement; scaling of that lumped model.

## 1. Worst realistic case (assumptions)
- 35 °C ambient, pod in the ear-worn shell, no airflow (bound h 5 W/m²K: shell 85 K/W; docked-like 44 K/W), VSYS 4.2 V, base 48 mW (rail-budget.yaml).
- loud12 + loud_shape (k 2.5): mean exciter current x1.74 vs loud12 alone (I-034, D-r6-crest.md, offline model). Heat = 4.2 V x extra mA (acoustic output negligible), as in row 8.
- Limit: IEC 62368-1 TS1 48 °C for >1 min skin contact (UL Japan 'Touch Temperature' brief, re-fetched 2026-10-08, as in the thermal README). Junction abs-max 125 °C (as the README).

| Case | mean mA | Pod P | Shell °C | Touch margin vs 48 | U4 junction (shell + 7-8 K) |
|---|---|---|---|---|---|
| loud12 real bats (README) | 8.9 | 75 mW | 38.3-41.4 | 6.6-9.7 K | 42-45 |
| loud12 nonstop (README) | 24.9 | 142 mW | 41.2-47.1 | 0.9-6.8 K | 48-55.5 |
| loud12+shape dense scene | 14.5x1.74 = 25.2 | ~144 mW | 41.3-47.2 | 0.8-6.7 K | ~48-56 |
| **loud12+shape nonstop (worst)** | 43.3 | ~219 mW | **44.6-53.6** | **+3.4 to -5.6 K** | ~52-62 |

Hottest part: U4 (TPS7A20 LDO, 3.3 V rail), junction ~52-62 °C worst, margin to 125 °C >60 K: not a limiter. Binding limit is skin touch: worst case exceeds TS1 by up to 5.6 K in the no-airflow bound (nonstop loud calls with shape for tens of minutes is not a realistic bat scene, but the dense-scene row is within 0.8 K).

## 2. Verdict
Margin < 10 K in every loud row, and negative in the bound for shape-nonstop -> prototype a guard.

## 3. Fold-back (firmware, default OFF)
Knobs (fw/spec/knobs.yaml v6): `thermal_fb` (0), `thermal_tau_s` (120, ASSUMED), `thermal_thr_pm` (70 permille).
Mechanism (fw/core/dsp.c, fw_dsp_out): per hop, a one-pole mean of |drive| clipped at the limiter ceiling (duty-integral proxy for exciter mA, 70 permille ~ 14.5 mA at the 208 mA clamp). Loud gain is ramped linearly to 0 dB as the mean goes 1x -> 2x threshold. Cost: ~3 flops/sample only when on. Not used: MCU temp sensor (reads the board, ~30 K/W away from the shell; needs calibration, a later add).
Caps sustained mean near the dense-scene row (shell <= 47.2 °C in bound, 0.8 K margin) - thin, so thr 70 may want lowering (owner decision; needs shell-temperature log, thermal README row 9).
Test: `test_thermal_fold` (fw/test/test_loud.c, tau 10 s test): off steady, on identical for first seconds, after ~4 tau mean output < 0.6x. fwsim all PASS (35 rows), gen --check ok, lint 0 violations.
Open: tau and the mA mapping are assumed; verify with a worn-shell temperature log before enabling.
