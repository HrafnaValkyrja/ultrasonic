# I-027 Hi-Z idle (2026-10-08)
verdict: SPICE-worthy (saves 0.42-0.49 mA >> 0.15 kill line), no audible pop expected; knob `hiz_idle` added, default OFF; bench PWR-I12 / E1 still decides.

## 1. Firmware today
No Hi-Z. Squelch (fw/core/dsp.c ~L615-623) emits an exact 50 % square wave (CCR = ARR/2); the bridge keeps switching (`bridge_run = output_enable`, modes.c L196). Bridge stops only in Off/Stop2, docked, or break.

## 2. SPICE (sim/checks/bridge_hiz_idle.py; DMC2400UV, 3.0 V, 200 kHz AD, 1-tick dead time 12.5 ns, 100 k gate pulls; ngspice 45)
| coil L | 50 % duty bus avg | Hi-Z bus avg | re-enable DC step in coil I |
|---|---|---|---|
| 0.30 mH | 0.489 mA (coil ripple pk 17.7 mA) | 0.000 mA | ~3.9 mA, tau ~ L/R ~ 40 us (to ~1.3 mA by 40 us) |
| 1.26 mH | 0.423 mA (pk 5.4 mA) | 0.000 mA | ~1.0 mA, tau ~ 160 us |
Hi-Z leakage not modelled (FET off-leakage nA, ESD diodes); gate-drive 0.28 mA (GPIO) also stops with MOE=0, extra saving not counted here.
Pop: worst-case re-enable at an arbitrary phase leaves a one-shot coil-current offset, area ~0.16 uA*s (both L), about 1/6 of one half-cycle of a -40 dBFS 2 kHz tone (~1 uA*s); it lands at the onset of the signal that opened the squelch, so masked in practice. Not a bench-verified inaudibility claim; the tragus coil's acoustic coupling is unmeasured (E1).
Caveat: at 2-tick dead time idle is only 0.10-0.20 mA (C3 table); gain shrinks to ~0.1-0.2 mA, near the kill line. Default is 1 tick.

## 3. Knob
`hiz_idle` (0/1, default 0): `fw_outputs()` returns bridge_run=0, brk_armed=0 while `dsp_squelched` (DSP squelch at end of last hop) and mode != docked selftest. app.c's existing arm/start and stop/disarm path does the rest. Re-enable cost: hop-granular latency (<= one 5 ms hop? depends on port DMA), so the first hop after squelch release may start with the bridge ramping in; bench/QEMU timing not checked. Test: fw/test/test_loud.c `test_hiz_idle` (DSP stream bit-identical, outputs gate only). `fwsim all` PASS 35 rows; no golden changed.

## 4. Open
Bench PWR-I12 with real coil (kills if < 0.15 mA); listen test for the re-enable tick; re-enable latency on target.
