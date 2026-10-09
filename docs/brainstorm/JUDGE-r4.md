# Judge round 4 (2026-10-08)
Inputs: R-dbpermA.md (I-019..I-024), B-r4-playback.md (new I-025..I-027). Compared with docs/system/sub-output.md, spec D6, C3-output-stage.md, d17-cost.md.

| Row | Verdict | Why / one-line kill test |
|---|---|---|
| I-019 TEAX + lower drive | **merit** (partly confirmed) | d17-cost re-run: dense 7.8 mA/9.1 h holds; continuous 13.8 mA/6.4 h fails 8 h. Owner packet: TEAX+6 for dense (8.4 h); continuous only TEAX+0. Needs the I-014 Bl measurement. |
| I-020 energy to 2-4 kHz | needs-evidence | ISO 389-3 values recalled. Kill: read the standard's tragus/B-71 table; our output band is already 1.5-4 kHz, so gain may be ~0. |
| I-021 exciter f0 into 2-3 kHz | needs-evidence | Kill: impedance sweep under pad load (E1/I-014 rig); drop if Q<2 or f0 drifts >20 % with pad force. |
| I-022 pad force/area | needs-evidence | Kill: pad force sweep; drop if gain <2 dB at 1.5 N comfort cap. |
| I-023 compression for mA | dead | Raises mean current. |
| I-024 bridge/rail efficiency | dead | F = Bl x I, LDO 1:1; heat only. Agree with R. |
| I-025 blind 150 mAh pod | killed (as specified) | 450 Wh/L assumed; stocked cells are 54-73 mAh/cm3 (r3), so 150 mAh needs ~2-2.8 cm3, not 1.23. Load omits our 4.6-7.3 mA base. S=90 dB/W unsourced. |
| I-026 ternary PWM | killed | See below. |
| I-027 Hi-Z when gated | needs-evidence | Saves <=0.5 mA idle. Kill: bench idle bus current (PWR-I12) < 0.15 mA. |

## Ternary PWM: does our bridge do it, would it cut current?
- **No, we do not.** D6 is 2-level AD (legs complementary, 200 kHz, 201 levels, dead time 1-2 ticks). 3-level BD was the v0.3/v0.4 idea and was rejected in v0.5: dead time distorts quiet signals (-10 dB THD+N at -40 dBFS even at 12.5 ns, C3 §5, deadtime_switching.py).
- **Current cut: essentially none at our coil.** Idle ripple is 12.5 mA pp at 0.3 mH, but it recirculates through the coil and bridge; the battery pays only resistive loss. SPICE idle bus current is 0.49/0.42 mA (0.3/1.26 mH, 12.5 ns). Blind's "25-40 mA, >4 h lost" treats ripple as supply current and assumes a 20 uH coil nobody measured. Its 33 uH series parts add 2 inductors per leg to fix a problem we do not have at 0.3 mH.
- **Where it could matter:** if E1 measures L around 20-50 uH, ripple rms rises and by my calc idle loss reaches several mA (20 uH: ~8 mA). Then options are (a) raise L with series chokes, (b) drop to 100 kHz (already the ECR-0007 fallback if L is small), (c) hybrid BD above -20 dBFS. Test on measured L before building anything.
- Both blind and our design share a good idea: Hi-Z idle gating (I-027), small.

## Owner packet merit
1. I-019 (TEAX, drive +6 dB for dense scenes; continuous scenes cannot hold 8 h at equal loudness).
2. I-014 / E1: measure Bl, f0, L, |Z| together; it decides I-021, I-026, I-027 and every loudness number.
Not for the packet: I-025, I-026, I-023, I-024.
