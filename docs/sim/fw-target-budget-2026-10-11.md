# STM32U575 target budget, fw HEAD a06bf1d (2026-10-11)

Build: `fw/tools/fwsim.py arm` (arm-none-eabi-gcc 14.2, Cortex-M33, hard-float, -O2, -Werror, -Wall -Wextra -Wconversion -Wshadow). Fenced 3G. 0 errors, 0 warnings; all 5 arm rows PASS.

## Size (part STM32U575CIU6Q: 2 MB flash, SRAM1 192 KB; linker app region 2024 KB)
| item | now | last recorded (fw/out/summary.json 2026-10-08 22:51, post-D17) | budget |
|---|---|---|---|
| flash (app) | 58,076 B | 58,076 B (identical) | 2,072,576 B -> 2.8 % |
| flash, bring-up image | 58,108 B | 58,108 B | same |
| RAM static (.data+.bss) | 30,804 B | 30,804 B | 196,608 B -> 15.7 % |
| stack region | 8,192 B, worst case 36.0 % | - | 50 % rule PASS |
| boot stub | 680 B | 680 B | 8,192 B |
No size growth since the 2026-10-08 gate run (it already contained all seven commits). No pre-D17 size is recorded in docs, so the look-ahead delta in bytes is not derivable without a rebuild of fbfb38b^.

## Cycles per 128-sample hop (static model fw/tools/cycles.py, gcov line counts x Cortex-M33 cost table, 0 wait states, FMAC interp + driver estimate; active path, idle detector off, sweep vector, 525 hops)
| config (B 28-band, high = worst) | cycles lo-hi | MHz incl. V4 overhead |
|---|---|---|
| look-ahead off | 48,032 - 58,852 | 77.8 - 99.8 |
| look-ahead on (D17 default) | 49,523 - 60,663 | 80.2 - 102.9 |
| + loud 12 dB on | 49,631 - 60,790 | 80.4 - 103.1 |
| + loud 12 + shape (worst case) | 49,991 - 61,246 | 81.0 - 103.9 |
| slim, same worst case | 33,236 - 40,655 | 54.0 - 69.1 |
Deltas: look-ahead +1,491 / +1,811 (fw_lahead_hop 1,483-1,799); loud +108 / +127; shape +360 / +456. All three together +1,959 / +2,394 over look-ahead off (+4.0 % / +4.1 %).
Hop budget: 51,200 cycles at HCLK 80.009 MHz (shared-params.yaml); 102,400 at 160 MHz.
QEMU instruction count (default config, loud/shape off) 33,602 insns/hop; qemu-corrected 67.6 - 86.7 MHz (dsp_icount.json); loud+shape add ~0.9 MHz.

## Findings
1. At the 80 MHz plan clock the B variant does not fit with margin: static upper bound 61,246 > 51,200 (120 %); qemu-corrected upper 86.7 + ~0.9 MHz also > 80. Even look-ahead alone (+1.5-1.8 k cycles) was already over at the upper bound; look-ahead off was also over (58,852). Lower bound 49,991 = 97.6 % of budget: no headroom. Fits at 160 MHz (60 % upper). Slim fits at 80 MHz (79 % upper). This is a standing clock/variant question, not a new regression from loud/shape (+0.9 MHz).
2. Static model assumes 0 wait states (55 MHz column); real flash at 80 MHz Range 2 is 2 WS with ICACHE hits at 0 WS, so cycle numbers are optimistic on cache misses.
3. fw/out/summary.json is tracked and was rewritten by this run; not committed.
4. Tool change: `fw/tools/cycdrv.c` gained pseudo-knob `loud_on=1` (toggles loud after init) so the model can cost loud/shape; the repo's default cycles.py run is unchanged (loud off). Reproduce: knobs `lim_lookahead=1 loud_db=12 loud_shape=1 loud_on=1` appended to VARIANTS["B"].
