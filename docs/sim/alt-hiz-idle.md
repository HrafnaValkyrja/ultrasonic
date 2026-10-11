# Alternative test: hiz_idle ON vs OFF, and the re-enable pop (2026-10-11, SIMULATED)

Src: sim/perf/port_meadow.py new configs `A+hiz`, `slim+hiz` (B = "A", slim = b_variant 1 at P72); fenced 3G, 54 clips, PASS, baseline refreshed (old rows unchanged). Current model fe405bf/2370328, shipping clock P112. sim/checks/hiz_reenable_click.py (new) -> sim/out/hiz_reenable_click.json. Model, not bench. Firmware default stays hiz_idle = 0.

## 1. Runtime, 130 mAh x 0.85 usable (h): off -> on
Awake 81/40/18 %; squelched time = scene's measured 7.3 % of hops for dense, (1 - awake) for walk/dusk (idle is squelched); ripple 0.45 mA x squelched fraction.
| variant | dense 81 % | walk 40 % | dusk 18 % |
|---|---|---|---|
| B off | 10.2 | 17.1 | 27.1 |
| B on | 10.2 (+0.0) | 17.8 (+0.7) | 29.8 (+2.7) |
| slim off | 12.2 | 19.9 | 30.1 |
| slim on | 12.3 (+0.1) | 20.9 (+1.0) | 33.4 (+3.3) |
Mean mA dense (scene): B 10.91 -> 10.83, slim 9.07 -> 8.98. Gain is only at rest: nothing in dense, +4 % walk, +10 % dusk.

## 2. Pop: SPICE, DMC2400UV bridge, 3.0 V, 200 kHz AD, dead time 12.5 and 25 ns
Transducer: Re 8 + 1.52 ohm, Le 0.3 / 0.5 / 1.3 mH, series motional RLC (Bl 1, 0.45 g, f0 350 Hz, Qm 3; bone_tf.json nominals). Force = |H(f)| |I(f)|, H = bone_tf N/A (absolute level assumed, unmeasured); threshold = front-tragus Surendran (n=21, SD 6-9 dB; D-i020-band.md; the mastoid set is similar, 29.5-36.5 dB at 1.5-4 kHz). Click -> equivalent steady tone by 1/3-octave band energy over 200 ms ear integration (standard energy-integration estimate; short clicks actually need more, so this is conservative).
- Real sequence matters: hal_pwm_start presets CCR = ARR/2, UG (CNT = 0), CEN, MOE last. Centre-aligned count starts at the centre of leg A's active window, so the first edge phase is deterministic and the ideal DC offset is zero (the old note's "arbitrary phase, 3.9 mA step" was the pessimistic bound). Stop (MOE = 0) is at an arbitrary phase: 8 phases swept.
- Results (worst phase/band): start area 0.004-0.018 uA*s, stop 0.002-0.008 uA*s (old bound 0.16). Equivalent tone -17 .. +4 dB re 1 uN against thresholds of ~30-36 dB: margin 30-46 dB below threshold in every case (L, dead time, start/stop). Even the old arbitrary-phase bound (x23 area, +27 dB) stays ~6 dB below threshold at 0.3 mH.
- Cannot lift above threshold with the +6 dB Bl uncertainty (0.5-2 N/A) and threshold SD 9 dB either. Soft-start (ramped duty) is NOT needed; none added (no firmware change, no knob).

## 3. Verdict: is hiz_idle safe to default ON?
Pop: yes in simulation, ample margin. Not yet: (a) saving is 0 dense / 0.7 h walk / 2.7 h dusk (+10 % at rest) and rests on SPICE ripple 0.45 mA, bench PWR-I12 untested (kill < 0.15 mA); at 2-tick dead time the gain is 0.1-0.2 mA; (b) first hop after squelch release is output with the bridge still Hi-Z (fw_outputs reads end-of-last-hop squelch): <= 0.64 ms of signal onset lost, about 1/140 of the 90 ms p50 latency, but unmeasured; (c) RESOLVED 2026-10-11: hal_pwm_stop sets the four bridge pins analog and hal_pwm_start does not restore AF in the file read (hal_u575_periph.c L86-99); CONFIRMED BUG: nothing re-muxed them (hal_pwm_config touches TIM1 only), so after the first Hi-Z the bridge pins stayed analog (CCxE/MOE set, but no pin connected to the timer; RM0456 Rev 7 GPIO MODER=11 analog disconnects the AF, TIM1 BDTR/CCER only drive the AF path). Fixed in fw/port_u575/hal_u575_periph.c: hal_pwm_start now sets PA7/PA8/PA10/PB15 to AF (AFR before MODER) before CCR/CEN/CCER/MOE; with MOE=0 and OSSI=1 the pin sits at the idle level, no glitch. Register-level proof: fw/test/port/test_regs.c (stop -> start returns MODER=10, AFR=1, mux before MOE); fwsim all PASS (207 reg checks). Defaults unchanged (hiz_idle=0). Recommendation: keep default OFF until PWR-I12 passes (restart check now passed); then ON is justified for rest-heavy use. Owner decides.
