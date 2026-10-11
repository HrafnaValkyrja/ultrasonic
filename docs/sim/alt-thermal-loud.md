# Alt test: worst-case thermal under loud12 + loud_shape, and a guarded fold-back (2026-10-11, simulated)
**CORRECTION 2026-10-11 (long-wear limit): the earlier 48 °C TS1 (>1 min) was the wrong limit for a pod worn for hours. Against 43 °C, normal use (rail budget, real bats) PASSES (1.6-5.9 K), the dense loud12 programme is marginal (-0.3 K in the bound) and nonstop loud12 (with or without shape) FAILS in the no-airflow bound (-4.1 to -10.6 K). The shape-nonstop worst case fails even docked-like (-1.6 K).**
Scope: row 8 of docs/proof/thermal/README.md (5be4ca1; TI TPS7A20 SBVS338H θJA 166.1 °C/W, ψJT 3.0). No new measurement; scaling of that lumped model.

## 1. Worst realistic case (assumptions)
- 35 °C ambient, pod in the ear-worn shell, no airflow (bound h 5 W/m²K: shell 85 K/W; docked-like 44 K/W), VSYS 4.2 V, base 48 mW (rail-budget.yaml).
- loud12 + loud_shape (k 2.5): mean exciter current x1.74 vs loud12 alone (I-034, D-r6-crest.md, offline model). Heat = 4.2 V x extra mA (acoustic output negligible), as in row 8.
- Limit (corrected): 43 °C long contact (worn hours). Sources: IEC 60601-1:2005 Tables 23/24, applied part, contact >=10 min, 43 °C all materials (SL Power/Advanced Energy AN-G012 v0719, 2019; secondary); EN 563 8 h 43 °C (quoted in patents US 10503223/10564686; secondary); Moritz & Henriques, Am J Pathol 23(5):695-720, Sept 1947 (primary; PMC1934304, full text is page images, not read here): threshold burn near 44 °C for hours. I could NOT verify an IEC 62368-1 Table 38 '>8 h, 43 °C' row: the UL Japan brief (2010, fetched 2026-10-08/11) is abridged and shows only >1 min = 48 °C TS1; the standard is paywalled. Treat the 62368-1 claim as unconfirmed; 43 °C stands on 60601-1 + EN 563 + burn literature. 48 °C TS1 retained only as the short-contact figure. Junction abs-max 125 °C.

| Case | mean mA | Pod P | Shell °C | Margin vs 43 (vs 48) | U4 junction (shell + 7-8 K) |
|---|---|---|---|---|---|
| loud12 real bats (README) | 8.9 | 75 mW | 38.3-41.4 | 1.6-4.7 K (6.6-9.7) PASS | 42-45 |
| loud12 nonstop (README) | 24.9 | 142 mW | 41.2-47.1 | -4.1 to 1.8 K (0.9-6.8) FAIL bound | 48-55.5 |
| loud12+shape dense scene | 14.5x1.74 = 25.2 | ~144 mW | 41.3-47.2 | -4.2 to 1.7 K (0.8-6.7) FAIL bound | ~48-56 |
| **loud12+shape nonstop (worst)** | 43.3 | ~219 mW | **44.6-53.6** | **+3.4 to -5.6 K** | ~52-62 |

Hottest part: U4 (TPS7A20 LDO, 3.3 V rail), junction ~52-62 °C worst, margin to 125 °C >60 K: not a limiter. Binding limit is skin touch: worst case exceeds 43 °C by up to 10.6 K in the no-airflow bound. Normal use (rail budget 2.5 mA, shell 37.1-39.1: +3.9-5.9 K; real bats 8.9 mA: +1.6-4.7 K) passes. Dense scene is already marginal (-0.3 K, 39.3-43.3 shell); nonstop loud is not realistic for hours but long loud sessions are the case that matters.

## 2. Verdict
Normal use passes. Every nonstop-loud row fails 43 °C in the bound, dense is marginal -> the guard is needed, not optional, before loud12 ships on by default.

## 3. Fold-back (firmware, default OFF)
Knobs (fw/spec/knobs.yaml v6): `thermal_fb` (0), `thermal_tau_s` (120, ASSUMED), `thermal_thr_pm` (70 permille).
Mechanism (fw/core/dsp.c, fw_dsp_out): per hop, a one-pole mean of |drive| clipped at the limiter ceiling (duty-integral proxy for exciter mA, 70 permille ~ 14.5 mA at the 208 mA clamp). Loud gain is ramped linearly to 0 dB as the mean goes 1x -> 2x threshold. Cost: ~3 flops/sample only when on. Not used: MCU temp sensor (reads the board, ~30 K/W away from the shell; needs calibration, a later add).
Default thr 70 permille (~14.5 mA) caps the sustained mean near the dense-scene row, shell up to 43.3 °C in bound: still over 43. SUGGESTED threshold (doc only, fw default unchanged): ~45 permille (~9.3 mA, the real-bats row, shell <= 41.4 °C, 1.6 K margin); needs the worn-shell log (row 9) to confirm (owner decision; needs shell-temperature log, thermal README row 9).
Test: `test_thermal_fold` (fw/test/test_loud.c, tau 10 s test): off steady, on identical for first seconds, after ~4 tau mean output < 0.6x. fwsim all PASS (35 rows), gen --check ok, lint 0 violations.
Open: tau and the mA mapping are assumed; verify with a worn-shell temperature log before enabling.
