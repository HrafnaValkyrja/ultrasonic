# A3: clock tree, DFSDM, TIM1, pin map, crystal

**Date:** 2026-09-30 · **Status:** plan settled on paper. It needs a bench check in S1: mic-clock duty cycle, and the effect of clock jitter on the noise floor.

**Sources:**
- RM0394 Rev 4 (Oct 2018), the STM32L41x–L46x reference manual (from a GitHub mirror; st.com was unreachable)
- DS11912 Rev 7 (Oct 2020), the STM32L452 datasheet
- AN4990 Rev 1 (DFSDM getting-started)
- DS11585 Rev 19 (STM32L496 datasheet), used only for its DFSDM duty-cycle characterisation
- SPH0641LU4H-1 datasheet Rev B / B-1

---

## 1. Clock tree (proposed; everything derives from one 80 MHz clock)

```
crystal-referenced clock ─▶ PLL ─▶ SYSCLK 80 MHz
   ├─ ÷20 (DFSDM CKOUT) ──────────▶ mic clock 4.0 MHz (ultrasonic mode: 3.072–4.8 MHz)
   │     DFSDM sinc filter ÷10 ───▶ 400 kS/s
   │     CPU half-band FIR ÷2 ────▶ 200 kS/s  (Nyquist 100 kHz; usable to ~80–85 kHz)
   │     DSP ... ÷16 ─────────────▶ 12.5 kS/s output-band signal (1.5–4 kHz content)
   │     ×16 interpolate + noise shaper
   └─ TIM1 centre-aligned, ARR=200 ▶ PWM carrier 200 kHz, one duty update per period (200 kS/s)
                                      3-level (BD) bridge ripple at 400 kHz
```

**Why the PWM moved from 312.5 kHz (v0.4) to 200 kHz:** any switching interference that couples into the mic path gets folded (aliased) by the input chain.
- **312.5 kHz** is not a multiple of 400 kS/s, so it folds to **400 − 312.5 = 87.5 kHz**. That's inside the processed band, where it would be mapped down to a steady audible tone.
- **200 kHz and 400 kHz** are exact multiples of the sample rates, so any coupling folds to **0 Hz**, and the band-floor high-pass removes it.

Tying the output timing to the input timing costs nothing and removes a whole class of self-generated whine (T6).

## 2. Crystal: required (new part)

The internal oscillators aren't accurate enough to keep the two unlinked sides matched (DS11912 Rev 7):

| Oscillator | Accuracy | Current |
|---|---|---|
| HSI16 (internal RC) | 15.88–16.08 MHz at 30 °C, plus ±1% drift over 0–85 °C | 155 µA |
| MSI in PLL mode, locked to a 32.768 kHz crystal (LSE) | crystal-accurate on average; period jitter ~3.5 ns (USB spec) | LSE 250–630 nA |
| HSE with an 8 MHz crystal | crystal-accurate, low jitter | 0.44 mA typ |

**Why it matters (heterodyne, algorithm A):** output = input − LO. A 1% clock error on a 38 kHz LO shifts the output by **380 Hz**, so the same bat call would come out at a different pitch in each ear. For log compression (algorithm B) a 1% clock error gives only ~0.4% pitch error, but the heterodyne case alone justifies a crystal.

Even with crystals (±20–50 ppm), heterodyne mode leaves ~1–2 Hz between sides. Together with the crosstalk in `bone-conduction.md` §2, that can cause a slow level wobble on *steady* tones. Transient-only mode suppresses steady tones anyway, and bat calls last milliseconds, so this is acceptable. It is noted in R5.

**Options:**
- **(a) Recommended:** 32.768 kHz crystal (LSE) + MSI PLL mode. Adds ~0.3 µA, a 1.6×1.0 mm crystal and 2 capacitors. LSE also clocks the RTC.
- **(b)** 8 MHz HSE crystal. Adds 0.44 mA (~4% of the total budget) and a 2.0×1.6 mm crystal. Lower jitter.
- **Decide in S1.** The Nucleo can run both: it has an LSE crystal, and ST-LINK MCO can supply 8 MHz as HSE. Compare the ultrasonic noise floor with each. Jitter matters because clock-jitter noise grows with signal frequency: at 80 kHz, 2 ns of jitter caps SNR near 60 dB for loud signals.

## 3. DFSDM facts that shape the firmware (RM0394 Rev 4)

- **Clock output (CKOUT):**
  - Source is "system clock" (DFSDM kernel clock) or "audio clock" (SAI1). Divider = CKOUTDIV+1, from 2 to 256.
  - **CKOUTDIV can only be changed with DFSDMEN = 0.** Switching the mic from standard to ultrasonic mode therefore means: stop DFSDM, change the divider, restart. CKOUT stops "4 system clocks after DFSDMEN is cleared". The gap is µs-long, far below the mic's ~10 ms fall-asleep time `[Med]`.
- **Duty cycle:**
  - **Not specified for the L452.** The sister part L496 is characterised at **45/50/55% (min/typ/max) for even division**.
  - The mic requires **48–52%** above 2.4 MHz. Typical is fine; worst-case is outside the mic's window. **Measure with a scope in S1.**
  - Fallback if it's out of spec: generate the clock from a timer in toggle mode (exactly 50% at the logic level) and feed DFSDM from its CKIN pin.
- **Serial clock limit:** the DFSDM clock must be at least 4× the serial clock. 80 MHz ≥ 4 × 4 MHz ✓. CKOUT range is 0–20 MHz ✓.
- **Filters:**
  - Sinc1–5 or FastSinc. FOSR 1–1024 (Sinc1–3), 1–215 (Sinc4), 1–73 (Sinc5); integrator IOSR 1–256.
  - Output up to 24-bit, with a right-shift of 0–31.
  - Keep FOSR^order × IOSR ≤ 2³¹: Sinc5 with FOSR 10 is 10⁵ ✓.
- **Output rate in FAST continuous mode** = f_CKIN / (FOSR·IOSR). Sinc5, FOSR 10, IOSR 1 gives 400 kS/s ✓.
- **Filter response vs decimation ratio:**
  - Sinc5 ÷10 at 4 MHz droops ~2.9 dB at 80 kHz.
  - Sinc5 ÷20 (DFSDM alone straight to 200 kS/s) droops ~12 dB at 80 kHz. It rejects the mic's out-of-band noise only ~30 dB near 120 kHz, which folds onto 80 kHz.
  - Plan (ii) (÷10, then a CPU half-band) stays the default.
  - Plan (i) (÷20, zero CPU) is kept as a power-saving option if S1 shows the top octave doesn't matter.
- **DMA:** filter 0 → DMA1 channel 5; filter 1 → DMA1 channel 6. **Use filter 0 for the mic**, because TIM1's update DMA also uses channel 6.

## 4. TIM1 facts (RM0394 Rev 4)

- **Centre-aligned PWM:** f_PWM = f_TIM / (2·ARR); ARR = 200 gives 200 kHz with 201 duty levels per leg. With 3-level (BD) modulation the differential output has 401 levels (~8.6 bits).
- **Dead time:** set per channel in 12.5 ns steps at 80 MHz, up to 1.59 µs.
- **Duty updates:** DMA burst writes CCR1 and CCR2 once per PWM period (TIM1_DMAR, DBA = 0x0D, DBL = 1, RCR = 1). An update event fires at both overflow and underflow, so RCR = 1 gives one per period.
- **⚠️ Reset state:** "When exiting from reset, the break circuit is disabled and the MOE bit is low". With OSSI = 0 the pins fall back to GPIO, which resets to **analog (floating)**.
  - **Every bridge gate floats from reset until firmware configures TIM1.**
  - **Design rule:** pull-up resistors on the P-channel gates (off), pull-down resistors on the N-channel gates (off). Then configure OSSI = 1 with safe idle levels (OISx/OISxN) before setting MOE.

## 5. Pin map (48-pin UFQFPN, DS11912 Table 16) — all needed functions available ✓

| Function | Pin (package pin #) | Alternatives |
|---|---|---|
| Mic clock: DFSDM1_CKOUT | **PA5 (15)** | none on 48-pin (PC2/PE9 only on bigger packages) |
| Mic data: DFSDM1_DATIN0 | **PB1 (19)** | DATIN1 on PB12 (25) or PA9 (30) |
| Bridge leg A: TIM1_CH1 / CH1N | **PA8 (29) / PA7 (17)** | CH1N also on PB13 (26) |
| Bridge leg B: TIM1_CH2 / CH2N | **PA9 (30) / PB0 (18)** | CH2N also on PB14 (27) |
| TIM1 break input (optional fault) | PA6 / PB12 | |
| SWD | PA13 (34) / PA14 (37) | |
| 32.768 kHz crystal | PC14 / PC15 | |
| 8 MHz crystal (if chosen) | PH0 / PH1 | |

**Bench note:** on the Nucleo, check the board user manual for whether the user LED shares PA5. If it does, remove its solder bridge or use PC2 for CKOUT on the 64-pin chip.
