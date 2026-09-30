# C2: CPU budget on the STM32L452 (80 MHz Cortex-M4F)

**Date:** 2026-09-30 · **Status:** estimate from published benchmarks. Re-measure on the L452 with the cycle counter (DWT->CYCCNT) in S3.
**Budget:** 80 M cycles/s. Target ≤ ~70% busy, to leave margin and because an idle CPU sleeps and saves current.

## Published Cortex-M4F cycle counts

| Operation | Cycles | Source |
|---|---|---|
| Real FFT (f32), 256 points | **14,285–16,534** | [A] ARM white paper (Lorenser 2016); [B] Stenzel FFT4CM4F, measured on STM32F446 |
| Real FFT (f32), 512 points | **30,457–36,324** | [A], [B] |
| Complex FFT (f32), 1024 points | 95,551–121,801 | [B], [C] |
| Complex FFT q15 vs f32, 1024 points | 82,174 vs 121,801 (q15 ~1.5× faster) | [C] (older library) |
| FIR filter, per tap per sample | f32 ~4.2 · q31 fast ~2.1 · q15 ~1.7 | [C], [D] |

- [A] Lorenser, "DSP capabilities of Cortex-M4 and Cortex-M7", ARM white paper, Nov 2016.
- [B] github.com/Stenzel/FFT4CM4F, measured on STM32F446 with the CMSIS_5 GCC library.
- [C] ST training "STM32F4 Core, DSP, FPU & Library" (2014).
- [D] ST Community measurement, STM32F412 (Dec 2019).

**These are ~4× slower than the v0.3 guess** (I had assumed ~4k cycles for a 256-point real FFT). One MSP432 user measured far worse still, with no resolution. Treat all FFT numbers as ±50% until measured on our chip.

## Budget by stage (M cycles/s)

**Shared by both algorithms**

| Stage | Cost | Notes |
|---|---|---|
| Half-band FIR, 400 → 200 kS/s | 5–10 | 12 non-zero taps. 0 if DFSDM decimates by 20 alone (A3 §3). |
| Output: ×16 interpolation, 2nd-order noise shaper, dither, bridge duty | 6–10 | runs at the 200 kHz PWM rate. **Missing from the v0.3 budget.** |
| DMA and interrupt overhead | 2–3 | |

**Algorithm A: heterodyne**

| Stage | Cost |
|---|---|
| Oscillator + mixer at 200 kS/s | 1–2 |
| Decimating low-pass, 200k → 12.5k (multi-stage, or one 242-tap FIR in q15/f32) | 4–13 |
| Envelope / squelch | ~0.5 |
| **Total including shared stages** | **~19–39 → 23–48% busy** ✓ |

**Algorithm B as written in v0.4: STFT analysis + inverse-STFT resynthesis at 200 kS/s**

| Configuration | FFT cost alone | Total |
|---|---|---|
| 256-point, 50% overlap (1,562 frames/s, forward + inverse) | 45–52 | **~68–95 → 85–119%** ✗ |
| 256-point, 75% overlap | 90–103 | ✗ |
| 512-point, 50% / 75% overlap | 48–57 / 95–113 | ✗ |

**It does not fit.** It also wastes work: it resynthesises a 200 kS/s signal whose content sits in 1.5–4 kHz, then decimates it only to interpolate it again for the PWM.

**Algorithm B restructured (proposed v0.5): FFT for analysis only, with synthesis at the low output rate**

| Stage | Cost |
|---|---|
| Forward 256-point real FFT, 50% overlap (0.64 ms hop, 781 Hz bins) | 22–26 |
| Window, magnitudes of the ~100 in-band bins | 2–4 |
| Group into ~32–48 log-spaced bands; noise floor, transient gate, mic EQ (all per band, nearly free) | 2–5 |
| Synthesis: ~32–48 sine oscillators at 12.5 kS/s, each placed at its band's mapped output frequency, amplitude following the band envelope | 3–7 |
| **Total including shared stages** | **~44–65 → 55–81% busy** — fits, tight at the top end |

**Levers if it's tight:**
- q15 FFT: ~1.5× faster.
- 128-point FFT: 1.56 kHz bins, 0.32 ms hop.
- Fewer bands.
- DFSDM ÷20: saves 5–10.

The restructure changes the *sound* slightly. Output is a smooth sum of tones at fixed band frequencies (a "channel vocoder"), not a phase-vocoder rebuild of the waveform. Phase 1 renders both, so the choice is made by listening. A side benefit: each band's frequency is fixed and identical on both units, which keeps the pitch mapping matched between ears.

## Current draw implied

MCU current ≈ busy × 6.7 mA + idle × 2.2 mA (84 µA/MHz run, 27 µA/MHz sleep at 80 MHz; DS11912):
- **A:** ~3.2–4.4 mA
- **B (restructured):** ~4.7–5.8 mA

Both are within the v0.4 power table, so the §7 totals stand.
