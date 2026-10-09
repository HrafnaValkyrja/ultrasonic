# R-dbpermA: more loudness per mA (rabbit trail, round 4, 2026-10-08)
Question: battery limits loudness (d17-cost.md: A+12 dB = 14.5 mA dense, 4-6 h vs 8 h). Which levers give dB without mA, or cut mA at equal dB?
Evidence tags: [calc] = derived here from repo numbers; [recalled] = from memory, NOT a checked primary source, verify before use. No web run was made (brief: no research).

## Core identity (sets what can work) [calc]
Linear bridge on a regulated 3.0 V rail (U4 passes battery current 1:1, d17-cost l.6): battery mA = load mA. Force F = Bl x I. So dB per mA is fixed by Bl and coupling only. Efficiency work (FET Rds, LDO headroom, rail voltage) changes watts and heat, not force per battery mA. A higher rail or bridge-direct-on-VSYS gives more force only by spending proportionally more mA (same dB/mA). Class-D loss: ripple current recirculates in the inductive load, so it costs heat, not battery mA, apart from idle switching (<~1 mA est., needs bench PWR-I12). Verdict: class-D/bridge tuning = no dB/mA lever.

## Candidates
| # | Lever | dB gain | mA cost | Basis |
|---|---|---|---|---|
| 1 | Higher-Bl exciter (TEAX14C02-8, Bl-driven +7.6 dB per d17-cost l.9) used to BUY BACK drive | +7.6 dB at +0.4 mA (+2 %) = ~19 dB/mA; or same loudness as A+12 with +4.4 dB drive: dense mean 4.9 x 10^(4.4/20) = ~8.1 mA vs 14.5, saves ~6 mA, runtime ~6.2 h -> ~8.5-9 h nominal | ~+2 % | [calc] from d17-cost table; +7.6 dB itself is an existing repo figure; limiter nonlinearity ignored (true saving slightly smaller). Rule: at fixed V and R, mA for a given force scales 1/Bl. More turns do not help (R rises as N^2, V fixed). |
| 2 | Shift programme energy to 2-4 kHz where bone/tragus threshold is lowest | ~8-12 dB between 1 kHz and 3 kHz | 0 (saves mA at equal audibility: -8 dB = x0.4 mean current) | [recalled] ISO 389-3 B-71 mastoid reference force thresholds fall from ~42 dB re 1 uN at 1 kHz to ~30 dB at 2-3 kHz; tragus differs, verify in ISO 389-3 and with I-010/I-014 bench. Check where the translated programme sits first. |
| 3 | Exciter f0 tuned into 2-3 kHz | +6-9 dB in band with pad-damped Q 2-3; -6 dB or worse outside | negative: motional impedance peaks at f0, so voltage-drive current FALLS at resonance | [calc] 20log(Q) with Q assumed; Q and f0 under pad load are unmeasured [recalled: pad loading shifts and damps f0]. Narrow, drifts with pad force and skin; couples to #2. Needs I-014 impedance sweep. |
| 4 | Tragus pad force / area / material | +2-4 dB for 1 to 3 N (recalled), more area = better, softer = loses highs | 0 | [recalled] static-force dependence of bone-conduction coupling (audiometric B-71 spec uses 5.4 N, IEC 60318-6); not verified. Comfort cap for hours-worn pad is the limit, likely ~1-2 N. Bench: pad force sweep on I-014 rig. |
| 5 | Programme shaping for current | peaky (high crest) drive costs less mean|x| per rms: sine ratio 0.90, square 1.0, so ~0.9 dB; gaps: gate to calls only | already ~51 % active | [calc]. Compression raises mean/rms, so it costs mA; it only helps where the 208 mA clamp, not the battery, binds. AGC gain on quiet calls only (d17-cost recommendation) is the right form. Not worth building for dB/mA. |
| 6 | Class-D / bridge efficiency, rail change | 0 dB/mA (see identity) | heat only | [calc]. Only real battery lever left is idle current, below 1 mA. |
| 7 | Higher-Bl in <=O14x10 beyond TEAX | unknown | unknown | not sourced; R-exciter.md / R-exciter2.md hold the exciter survey; do not duplicate. |

## Ranked recommendation (owner decides)
1. TEAX plus lower default drive (#1): biggest, already a bench-buy; restores 8 h. Do first.
2. Check programme band against bone/tragus threshold curve (#2): free, firmware-only, needs the primary standard and one bench sweep.
3. Pad force/area (#4) and f0 tuning (#3) are bench items with the same I-014 rig; do not design around them yet.
Dropped: #5, #6 (no dB per mA).
