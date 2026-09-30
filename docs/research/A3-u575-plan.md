# A3 (U575): chip plan for the STM32U575CIU6Q: MDF/ADF, clock tree, pins, SMPS, current

**Date:** 2026-09-30 · **Status:** paper plan. It replaces the L452 plan in `A3-clock-and-peripherals.md` for the U575. Bench checks are listed in §7.

**Parts named here:**
- **STM32U575CIU6Q:** ST's Cortex-M33 microcontroller (160 MHz, DSP + FPU). "Q" means the variant with the internal core switching regulator (SMPS), in a 7×7 mm 48-pin QFN.
- **SPH0641LU4H-1:** the Knowles/Syntiant PDM MEMS microphone, which has an ultrasonic mode.
- **MDF / ADF:** the U5's two on-chip PDM-to-PCM filter blocks. They replace the L452's DFSDM. The MDF is the big six-channel "multi-function digital filter". The ADF is a one-channel "audio digital filter" with a sound-activity detector.

**Sources (primary, with dates):**
- **DS13737 Rev 8** (04-Aug-2023): STM32U575xx datasheet. Page and table numbers are the printed ones.
- **RM0456 Rev 6** (24-Jan-2025): STM32U5 reference manual. st.com blocked the download; the PDF came from the GitHub mirror `micromouseonline/minimus2/docs/stm32u585/`. PDF page = printed page.
- **ES0499 Rev 10** (04-Jul-2024): STM32U575/585 errata, from the same mirror.
- **AN5373 Rev 6** (STM32U5 hardware getting-started): read only through manualslib excerpts (pp. 13 and 37). The PDF was unreachable.
- **JLCPCB parts API**, queried 2026-09-30.

---

## 0. Summary

1. **Use the ADF, not the MDF, for the mic.** It has the same Sinc5 + reshape filter + high-pass chain, and it draws about 8× less peripheral current. It is the only filter that keeps running in Stop 2, and it has its own pins (PB3/PB4). The MDF (PB8/PB1) is the fallback.
2. **Hardware decimation straight to 200 kS/s:** CIC5 ÷5 (4.0 MHz → 800 kS/s), then the reshape filter (RSFLT) ÷4 → **200 kS/s**. The RSFLT's passband edge is 0.111 × 800 kHz = **88.8 kHz**. This removes the CPU half-band (5–10 M cycles/s) `[Med]`: the RSFLT coefficients are not published, so bench-verify.
3. **Clock:** MSI locked to the 32.768 kHz crystal (LSE) feeds PLL1. The **recommended default is 80 MHz in Range 2; 160 MHz is optional headroom.** Mic clock = HCLK/20 (80 MHz) or /40 (160 MHz); PCM rate = PWM rate = HCLK/400 (80 MHz) or /800 (160 MHz). Every divider is even.
4. **⚠️ The spec's "19.5 µA/MHz → MCU ~0.9 mA" is wrong for this design.** That figure is a `while(1)` loop at 24 MHz in Range 4, where the SMPS runs *asynchronously* (not forced-PWM). In Ranges 1–3, where the SMPS switches at a fixed 3 MHz, the U575 draws **~40–45 µA/MHz**. Realistic MCU current is **~2.5–3 mA for algorithm B at 80 MHz**, against ~4.7–5.8 mA on the L452. That is a ~45% saving, not ~75%.
5. **No register forces PWM.** The SMPS runs fixed-frequency 3 MHz PWM in Ranges 1–3 and goes asynchronous in Range 4 and in Stop modes (DS Table 35). "Forced PWM" therefore means: never run in Range 4 while on the SMPS.

---

## 1. MDF / ADF

### 1.1 Facts

| Item | Value | Source |
|---|---|---|
| Clock chain | kernel clock → PROCDIV (÷1…128) → `proc_ck` → CCKDIV (÷1…16) → CCK pin. F_CCK = F_ker / ((PROCDIV+1)(CCKDIV+1)) | RM0456 §39.4.5, Fig. 331, p.1528; MDF_CKGCR p.1577 |
| Max CCK out (MASTER SPI) | **25 MHz**; LF_MASTER mode ≤ 5 MHz; CKI/CCK input ≤ 25 MHz | DS Table 119 (MDF), Table 118 (ADF), pp.259–260 |
| Clock constraints | MASTER SPI: `proc_ck > 4 × F_CCK`. LF_MASTER: `proc_ck > 2 × F_CCK`. With the RSFLT enabled, additionally `proc_ck > 24 × F_CCK/(MCICD+1)`. Always `F_hclk ≥ proc_ck` | RM Table 375, p.1529 |
| **CCK duty cycle** | **Not specified anywhere.** The only spec is "output clock high and low time ≥ 2 × T_proc_ck" (MASTER) | DS Tables 118/119. ⚠️ `[Unverified]` |
| CIC | Main path Sinc4 or Sinc5 (ADF and MDF); Sinc1–3/FastSinc only in the MDF split mode. "The decimation ratio can be adjusted from 2 to 512." **Sinc5 max decimation = 32** with a 1-bit input | RM p.1536, Table 377 p.1537 |
| RSFLT (reshape filter) | Fixed IIR "mainly dedicated to the audio application". "The samples at the RSFLT output can be decimated by four or not" (RSFLTD). Cutoff **F_C = 0.111 × F_RS**. Gain ≈ 9.3 dB. Input ≤ 22 bits. "Takes 24 clock cycles of mdf_proc_ck… to process one sample" | RM pp.1540–1541, Table 380, Fig. 338 |
| RSFLT response (read from Fig. 338) | Passband 9.0–9.7 dB, peaking at +10.4 dB right at the edge (~±0.7 dB ripple). Stopband from ~0.15 × F_RS, sidelobes ≈ −60 dB absolute (≈ −70 dB relative) | RM Fig. 338 `[Med]`, figure only |
| HPF | First-order IIR. Cutoff = 0.000625 / 0.00125 / 0.0025 / **0.0095 × F_PCM** (HPFC 0–3); at 200 kS/s that is 125 Hz / 250 Hz / 500 Hz / 1.9 kHz | RM p.1542, HPFC field |
| Output rate | F_PCM = F_CCK / ((MCICD+1) × (4 if RSFLTD = 0, else 1)); an extra INT stage exists on the MDF only | RM Table 385 p.1567 (columns F_RS, F_PCM) |
| Data / DMA | 24-bit, left-aligned in DR[31:8]; 4-word RXFIFO. GPDMA1 requests: **mdf1_flt0 = 92, adf1_flt0 = 98, tim1_upd = 46**; ADF also on LPDMA1 request 10 | RM p.1672 (ADF DR); Table 137 pp.687–690 |
| Stop modes | "ADF1… Autonomous in Stop 0, Stop 1 and Stop 2"; MDF1 "Stop 0 and Stop 1 modes only" | DS Table 18 p.68; RM Table 389 p.1601 |
| CKGEN trigger | MDF: CCKDIV can start on `tim1_trgo` (mdf_trgi0, TRGSRC = 0010). ADF: only EXTI15 or software | RM Table 371 p.1520; Table 392 p.1603 |

**On-the-fly divider change (standard → ultrasonic mode): not possible while running.**
- CCKDIV: "This bitfield must not be changed if one of the filters is enabled (DFTEN = 1)."
- "PROCDIV[6:0] and CCKDIV[3:0] must be programmed when no clock is provided to the dividers (CKGDEN = 0)." (RM pp.1527, 1577)

The switch is therefore stop, re-divide, restart, the same as on the L452:
1. Set DFLTEN = 0 and SITFEN = 0.
2. Set CKGDEN = 0 and wait for CKGACTIVE = 0. This takes "two periods of AHB clock and two periods of mdf_proc_ck".
3. Write the new divider values.
4. Set CKGDEN = 1, then CCK0EN = 1.
5. Re-enable the filter, discarding the first samples with NBDIS.

While CCK0EN = 0 with CCK0DIR = 1, "the pin is driven low" (Table 374). The gap is a few µs, far below the mic's ≤10 ms mode-change time `[Med]`.

**Duty cycle (the mic needs 48–52%):** ST's own mic examples (RM Table 385) always use an **even** CCKDIV+1 (2 or 6). A ÷2N counter normally gives 50%, but ST does not state it. **Rule: keep CCKDIV+1 even, and scope it in S1.** The fallback is the same as before: a timer-generated clock fed back in through an MDF_CKIx pin (MDF only; the ADF has no CKI pin).

### 1.2 Decimation plan for 4.0 MHz PDM → 200 kS/s

CIC5 figures are computed; RSFLT figures are read from Fig. 338.

| Option | Chain | Droop at 85 kHz | Worst alias into 0–85 kHz | CPU | Verdict |
|---|---|---|---|---|---|
| **D1 (recommended)** | CIC5 ÷5 → 800 kS/s → **RSFLT ÷4** → 200 kS/s (HPF optional) | CIC −0.78 dB; RSFLT ~+1 dB edge peak | CIC −91 dB (near 800 kHz); RSFLT ~−70 dB above ~120 kHz. 115–120 kHz only partly attenuated, folding to 80–85 kHz | **0** | Replaces the CPU half-band |
| D2 (current plan) | CIC5 ÷10 → 400 kS/s → CPU half-band ÷2 | −3.24 dB (EQ fixes) | CIC −59.7 dB; the half-band sets the rest | 5–10 M cycles/s | Fallback if the RSFLT response disappoints |
| D3 | CIC5 ÷20 alone | −13.7 dB | −26.8 dB | 0 | Rejected (as before) |

D1 register values:

| Setting | Value | Meaning |
|---|---|---|
| CICMOD | 101 | Sinc5 |
| MCICD | 4 | ÷5 |
| RSFLTBYP | 0 | RSFLT on |
| RSFLTD | 0 | ÷4 |
| HPFBYP / HPFC | 0 / 3 | 1.9 kHz DC blocker (the software band-floor high-pass still does the real work) |

D1 constraints:
- `proc_ck ≥ 24 × 800 kHz = 19.2 MHz`. The plan uses 40 MHz.
- CIC output = 5·log₂5 + 1 = 12.6 bits, so up to ~+50 dB of SCALE fits under the 22-bit RSFLT input limit `[Med]`, computed from RM p.1536. Tune SCALE on the bench with the SATF flag.
- Use **normal MASTER SPI** mode (needs proc_ck > 16 MHz), not LF_MASTER. It keeps the clock-absence detector, which "is not available in the LF_MASTER SPI mode" (RM p.1524).

**Why D1 works:** the RSFLT is specified relative to its own input rate. ST lists only audio rates (F_RS 32–192 kHz → PCM 8–48 kHz; Table 380), but the formula scales. At F_RS = 800 kHz the passband ends at 88.8 kHz, just above our ~85 kHz top. `[Unverified]`: ST publishes no coefficients and no example at F_RS = 800 kHz. **Measure a swept tone through D1 on the Nucleo in S1.**

### 1.3 Does the ADF's sound-activity detector (SAD) help as an idle wake-up?

**Only weakly.** The SAD computes "the average of the absolute value of an amount of PCM samples given by FRSIZE" (8–512 samples) and compares it against an ambient-noise estimate or a fixed threshold (RM §40.4.10, pp.1630–1633).
- It has **no band selection.** It sees whatever passes the CIC + RSFLT + first-order HPF, and the HPF corner tops out at 1.9 kHz at 200 kS/s.
- So speech, footsteps and wind trigger it as easily as a bat. As an *ultrasonic* detector it would mostly wake on audible noise.
- Nothing in RM0456 limits the SAD to audio rates. ST's slope table (Table 400, p.1634) lists only 8/16 kHz.

**A better use of the ADF in idle-listening mode (C9)** `[Low]`:
- Leave the ADF running in **Stop 2**, clocked from MSIK at 24 MHz. "The ADF1 is functional in Stop 0, Stop 1, and Stop 2 modes only when the kernel clock is AUDIOCLK or MSIK" (RM p.595), and 24 MHz is the highest MSI range kept through Stop (RM p.509). ES0499 §2.2.8: an MSIK used as kernel clock keeps running in Stop, so switch ADF1SEL to HCLK when the ADF isn't wanted in Stop.
- Have LPDMA1 write continuously into **SRAM4 (16 KB)**. "In Stop 2 mode… ADF1, and LPDMA1… the SRAM4 can be accessed by the LPDMA1" (DS p.42).
- 16 KB is ~40 ms of 16-bit samples at 200 kS/s. That is **a free look-back buffer.**
- The CPU wakes on each LPDMA half-transfer (~20 ms), runs a short band-energy test on 20–85 kHz, and goes back to Stop 2.
- MSIK at 24 MHz (range 1, locked value 24.003 MHz) with PROCDIV+1 = 1 and CCKDIV+1 = 6 gives a 4.0005 MHz mic clock with an even divider, and the same D1 filter chain.
- SAD can optionally pre-gate this in quiet places (SADMOD = 01, fixed threshold).
- Rough MCU-side cost: Stop 2 ~4–9 µA + MSIK ~52 µA (DS Table 82: 21 µA + 1.3 µA/MHz on SMPS) + ADF ~10 µA + wake bursts ≈ **~0.1 mA**, against ~2.5–3 mA active. The mic (845 µA) still dominates.
- Unverified: LPDMA current, wake-up and PLL relock time.

### 1.4 ADF vs MDF (owner decides)

| | **A: ADF1 (recommended)** | B: MDF1 |
|---|---|---|
| Pins (48-pin SMPS) | CCK0 **PB3** (pin 39, AF3), SDI0 **PB4** (pin 40, AF3) | CCK0 **PB8** (45, AF5), SDI0 **PB1** (19, AF6) |
| Filters | 1 (all we need) | 6 |
| Stop 2 capture + SAD | Yes | No (Stop 0/1 only) |
| Current (SMPS, Range 2, DS Table 72) | 0.39 + 0.14 µA/MHz → **~40 µA at 80 MHz** | 3.12 + 0.34 µA/MHz → **~0.28 mA at 80 MHz** |
| Phase-lock mic clock to PWM | No (trigger only from EXTI15); the frequency is still locked | Yes: CKGEN can start on `tim1_trgo` |
| Costs | Loses SWO trace (PB3). PB4 is NJTRST (fine with SWD, ES0499 §2.2.20) | none |

Phase locking isn't needed for the fold-to-DC argument (D14). Only the frequency ratio matters, and both options have it. **Pick A.**

Optional: on the first PCB, route the mic clock and data to both pin pairs through 0 Ω links, which keeps B open. The cost is two pins.

---

## 2. Clock tree

**Reference:**
- MSIS range 0 locked to the LSE (MSIPLLEN = 1, MSIPLLSEL = 1).
- **In PLL mode the MSI is an integer multiple of 32.768 kHz, not a round number:** range 0 = **48.005 MHz** (1465 × LSE), range 4 = 3.998 MHz (DS Table 82, p.212).
- All ratios stay exact, and the whole tree sits +107 ppm high. That is irrelevant for pitch and identical on both sides.

**PLL1** (RM p.526, p.530, Table 115 p.498):
- Input ÷M = 3 gives 16.0017 MHz (PLL1RGE = 11, 8–16 MHz).
- N = 20 gives a VCO of 320.03 MHz (allowed range 128–544 MHz).
- DIVR accepts only 1 or even values.
- Above 55 MHz the EPOD booster is required: PLL1MBOOST ÷4 (48 → 12 MHz, within 4–16 MHz), then BOOSTEN (RM p.410).

```
LSE 32.768 kHz ─lock─▶ MSIS 48.005 MHz ─÷3─▶ 16.00 MHz ─×20─▶ VCO 320.03 MHz ─÷R─▶ SYSCLK = HCLK = PCLK2 = TIM1 clock
                                                                     │
                                          ADF kernel = HCLK ─÷(PROCDIV+1)─▶ proc_ck 40 MHz ─÷10─▶ mic CCK 4.000 MHz
                                                                                        CIC5 ÷5 ─▶ 800 kS/s ─RSFLT ÷4─▶ 200.02 kS/s
                                          TIM1 centre-aligned, ARR = HCLK/400 kHz ─────────────▶ 200.02 kHz PWM, 1 DMA burst/period
```

| Mode | SYSCLK | Range | PLL | ADF PROCDIV+1 / CCKDIV+1 | proc_ck | Mic CCK | TIM1 ARR (levels) | Dead-time tick (CKD = 00) | Use |
|---|---|---|---|---|---|---|---|---|---|
| **P80 (recommended default)** | 80.009 MHz | 2 (≤110 MHz) | R = 4 | 2 / 10 | 40.0 MHz | 4.0004 MHz | 200 (201) | **12.5 ns** → DTG = 1–2 | algorithm B |
| P160 | 160.017 MHz | 1 (≤160 MHz) | R = 2 | 4 / 10 | 40.0 MHz | 4.0004 MHz | 400 (401) | **6.25 ns** → DTG = 2–4 | CPU headroom, finer PWM steps |
| P64 | 64.007 MHz | 2 | VCO 384 (N = 24), R = 6 | 2 / 8 | 32.0 MHz | 4.0004 MHz | 160 (161) | 15.6 ns | algorithm A |
| P48 (no PLL) | 48.005 MHz (MSIS direct) | 3 (≤55 MHz, no booster) | off | 1 / 12 | 48.0 MHz | 4.0004 MHz | 120 (121) | 20.8 ns → DTG = 1 | algorithm A, lowest current |
| Mic standard-mode start | any of the above | | | PROCDIV+1 doubled (e.g. 4 at 80 MHz), CCKDIV+1 = 10 | 20 MHz | **2.0 MHz** (1.024–2.475 ✓) | | | power-up, ≥50 ms |

- **Dead time:** "DTG[7:5] = 0xx ⇒ DT = DTG[7:0] × t_DTS" (RM p.2221). **New on the U5:** asymmetric dead time (TIMx_DTR2, DTAE = 1, rising edge DTG, falling edge DTGF; p.2224). It lets the P-FET and N-FET edges get different dead times.
- **DMA:** GPDMA1 has 16 channels, each able to take any request. The L452's "filter 1 shares a DMA channel with TIM1" conflict is gone.
- **Mode switches:** changing R requires the PLL off (RM p.530), so a SYSCLK mode change restarts the ADF, as in D14. Every row keeps the mic clock, the PCM rate and the PWM rate identical; only the PWM step count changes.
- **Integer relations (P80):** CCK = HCLK/20, PCM = HCLK/400, PWM = HCLK/(2·200) = HCLK/400. Any bridge interference therefore folds to 0 Hz, as in D14.

---

## 3. Pin map: UFQFPN48 **SMPS** package (DS Fig. 9 p.92, Table 26 pp.104–124, AF Table 27)

⚠️ The SMPS package is **not** pin-compatible with the plain UFQFPN48. Pins 20–25 and 46 become SMPS and VDD11 pins, so **PB2, PB9, PB10 and PB12 don't exist.** (The `stm32u585_af.csv` on GitHub is for the non-SMPS package.)

| Function | Pin (package #) | AF | Notes |
|---|---|---|---|
| Mic clock ADF1_CCK0 | **PB3 (39)** | AF3 | Also JTDO/SWO, which is lost. [B: MDF1_CCK0 PB8 (45) AF5] |
| Mic data ADF1_SDI0 | **PB4 (40)** | AF3 | NJTRST after reset; reassign. [B: MDF1_SDI0 PB1 (19) AF6] |
| Bridge A: TIM1_CH1 / CH1N | **PA8 (29) / PA7 (17)** | AF1 | CH1N alt PB13 (26). Same pins as the L452 plan |
| Bridge B: TIM1_CH2 / CH2N | **PA9 (30) / PB0 (18)** | AF1 | CH2N alt PB14 (27) |
| TIM1_BKIN (optional fault) | PA6 (16) | AF1 | |
| SWD | PA13 (34) SWDIO, PA14 (37) SWCLK | AF0 | |
| LSE crystal | PC14 (3), PC15 (4) | — | ⚠️ ES0499 §2.2.1: "LSE crystal oscillator may be disturbed by transitions on PC13" on UFQFPN, no fix. **Keep PC13 (pin 2) static.** Not the button |
| Button + wake | **PA0 (10)** | EXTI0 | Also WKUP1 (Standby/Shutdown). Any EXTI line wakes Stop 2 |
| Battery sense | **PA4 (14)** ADC1_IN9 / ADC4_IN9 | analog | ADC4 works in Stop 2. Li-ion 4.2 V > VDDA, so use a switched divider. **VREF+ is bonded to VDDA on this package** (no VREF+ pin), so VREFBUF is unavailable and the reference is the 3.0 V LDO; calibrate against VREFINT |
| SMPS | **VLXSMPS 20, VDDSMPS 21, VSSSMPS 22, VDD11 23 + 46** | — | §4 |
| Supplies | VDD 25/36/48, VSS 24/35/47 + exposed pad, VDDA 9, VSSA 8, VBAT 1 (tie to VDD) | — | |
| Boot / reset | PH3-BOOT0 (44) pull-down, NRST (7) | — | |
| USB (optional) | PA11 (32) DM, PA12 (33) DP | AF10 | ⚠️ There is no VDDUSB pin on this package (presumably bonded to VDD `[Unverified]`), and USB needs VDDUSB **3.0–3.6 V**. The 3.0 V rail is at the minimum |
| HSE (only if chosen) | PH0 (5) / PH1 (6) | — | |
| Free | PA1, PA2, PA3, PA5, PA10, PA15, PB1, PB5, PB6, PB7, PB8, PB13, PB14, PB15 | | mic power switch, bridge enable, LED… |

**Conflicts:** none blocking.
- PB3 costs the SWO trace, which isn't needed.
- USB's 3.0 V minimum sits exactly at our rail voltage.
- Bench: on the NUCLEO-U575ZI-Q, PB3 is wired to the ST-LINK SWO. Check the UM2861 solder bridges before using ADF1_CCK0 there `[Unverified]`.

---

## 4. SMPS

**Datasheet wording (DS §3.9.1 p.35):** "The SMPS generates this voltage on VDD11 (two pins), with a total external capacitor of 4.7 μF typical. SMPS requires an external coil of 2.2 μH typical… It is possible to switch from SMPS to LDO and from LDO to SMPS on-the-fly."

**Components** (DS Fig. 25 p.147): **L = 2.2 µH, C_OUT = 2 × 2.2 µF (one per VDD11 pin), C_IN = 10 µF on VDDSMPS**, plus an optional 100 nF on each VDD11.
- ⚠️ AN5373 Rev 6 Table 9 (p.37) instead lists **3.9 µF** per VDD11 pin, and calls L "2.2 µH ceramic coil" (p.13). Follow the datasheet, and derate for DC bias at 1.2 V.
- Ripple: ΔI ≈ (3.0 − 1.2)·(1.2/3.0)/(2.2 µH·3 MHz) ≈ **110 mA p-p**, so any inductor rated ≥ 300 mA suffices.

| Inductor option (2.2 µH, 0805 multilayer ferrite, closed magnetic path) | JLC # · class | Stock / price (2026-09-30) | DCR / rating |
|---|---|---|---|
| **Murata LQM21PN2R2MGHL** (reportedly the NUCLEO-U575ZI-Q part `[Unverified]`, from a search snippet, not the schematic) | C341781 · Extended | 6,100 · $0.363 | 125 mΩ / 1.3 A |
| TDK MLP2012S2R2MT0S1 | C107322 · Extended | 6,315 · $0.098 | 299 mΩ / 800 mA |
| Sunlord MPL2012S2R2MHT | C63167 · Extended | 11,990 · $0.091 | 250 mΩ / 800 mA |

Recommendation: the Murata part (the ST reference, lowest DCR).

**Class-2 capacitors vs D11:** 2.2–3.9 µF is only practical in X5R/X7R. That doesn't break D11's wording: those capacitors sit on the 1.2 V DC output, and the switching node VLXSMPS carries only the inductor. Their ripple is at 3 MHz, far above hearing.

**Forcing PWM:**
- **There is no mode bit.** PWR_CR3 has only **REGSEL** (0 = LDO, 1 = SMPS) and **FSTEN** (fast soft-start) (RM p.449).
- DS Table 35 (p.155): switching frequency **3 MHz** (VDD > 1.9 V) or 1.5 MHz (below 1.9 V) in Ranges 1, 2 and 3. Footnote: "**The SMPS is asynchronous in range 4 and low-power modes.**"
- RM p.409: "The LDO and the SMPS regulators have two modes: main regulator mode… and low-power regulator mode."
- Fixed-frequency PWM therefore holds exactly while running in **Ranges 1–3**. Rules:
  1. After reset the chip starts "the LDO, in range 4". Raise to Range 2/3 **before** setting REGSEL = 1.
  2. Never drop to Range 4 on the SMPS. Switch REGSEL = 0 first.
  3. In Stop the SMPS is asynchronous whatever you do.
- `[Unverified]`: whether the 3 MHz is derived from the system clock or free-running. If free-running, its spur isn't synchronous with the mic. It lands near the 4 MHz PDM clock's 1 MHz alias, well inside CIC rejection. **Look for spurs in S1/E11.**

**Runtime switching:** "It is possible to switch from LDO to SMPS, or from SMPS to LDO in any range, by configuring the REGSEL bit" (RM p.409). The 110 MHz / 8 µs rule applies only to U59x/5Ax/5Fx/5Gx, not the U575.

**Off mode (Stop 2):**
- Prefer staying on the SMPS: 3.9 µA (8 KB SRAM2) or 8.55 µA (all SRAM), at 3.0 V and 25 °C (DS Table 58).
- On the LDO, ES0499 §2.2.22 applies: "Device may be locked upon system reset under Stop 2 mode… on LDO regulator, with at least one RAM in power-down… (dozens of mA)". Either keep all SRAMs on, or stay on the SMPS.
- The bridge is stopped in Off, so the asynchronous SMPS has no electrical path to the transducer. E11 should still include an Off-mode listen.

---

## 5. Current (DS13737 Rev 8, typical, 25 °C)

**Run, code from flash, all peripherals off, PLL** (DS Table 39 p.160, SMPS at 3.0 V; Table 37 p.158, LDO; Table 46 p.167, Sleep on SMPS at 3.0 V):

| f_HCLK | Range | Run, SMPS | µA/MHz | Run, LDO | Sleep, SMPS |
|---|---|---|---|---|---|
| 160 MHz | 1 | **7.15 mA** | 45 | 13.5 mA | 2.50 mA |
| 110 MHz | 2 | 4.40 mA | 40 | 8.80 mA | 1.95 mA |
| **80 MHz** | 2 | **~3.3 mA** (interpolated) `[Med]` | ~41 | ~6.6 mA | ~1.45 mA |
| 72 MHz | 2 | 3.05 mA | 42 | 6.00 mA | 1.30 mA |
| 64 MHz | 2 | 2.80 mA | 44 | 5.40 mA | 1.20 mA |
| 55 MHz | 3 | 2.20 mA | 40 | 4.25 mA | 0.92 mA |
| 24 MHz, `while(1)`, SRAMs off (DS front page, Table 42) | 4 (SMPS async) | 0.47 mA at 3.3 V | **19.5** | | |

**Duty-cycled MCU estimate** (C2 cycle counts, assuming the M33 needs no more cycles than the M4 `[Unverified]`; + MSI ~80 µA):
- Algorithm B at 80 MHz (55–81% busy): **~2.5–3.0 mA**, against 4.7–5.8 mA on the L452.
- Algorithm B at 160 MHz (27–41% busy): **~3.8–4.4 mA**. Racing to sleep loses here, because sleep current scales with the clock.
- Algorithm A at 48 MHz, no PLL (40–81% busy): ~1.3–1.8 mA.

**Stop 2 on SMPS, 3.0 V** (DS Table 58 pp.178–179):
- 3.90 µA (8 KB SRAM2, RTC off).
- **4.25 µA with RTC on the LSE crystal.**
- 8.55 µA with all SRAMs retained.
- On the LDO: 9.05 µA (Table 55).
- The spec's "~2 µA" is low; the budget impact is negligible.

**Peripherals** (DS Table 72 pp.196–198, µA/MHz on SMPS, Range 1 / Range 2):

| Peripheral | Range 1 | Range 2 | At 80 MHz |
|---|---|---|---|
| TIM1 | 2.96 | 2.52 | ~0.20 mA |
| GPDMA1 | 1.80 | 1.52 | ~0.12 mA |
| ADF1 + independent clock | 0.47 + 0.17 | 0.39 + 0.14 | ~40 µA |
| MDF1 + independent clock | 3.69 + 0.40 | 3.12 + 0.34 | ~0.28 mA |

Peripherals total **~0.35 mA with the ADF**, against 0.6–1.0 mA budgeted.

---

## 6. What this changes in the spec (for the owner; spec not edited)

| Spec item | Change |
|---|---|
| §7 "19.5 µA/MHz… MCU ~3.8 → ~0.9 mA"; O6 | → **~2.5–3 mA** (algorithm B, 80 MHz) and ~1.3–1.8 mA (algorithm A, 48 MHz). The saving is ~45%, not ~75% |
| D14 "Stays in voltage Range 1" | U5 Range 2 allows 110 MHz, Range 3 55 MHz |
| D14 ÷10 + CPU half-band | → ADF CIC5 ÷5 + RSFLT ÷4 (D1), with ÷10 + half-band as fallback |
| D14 "filter 0 / DMA channel 5" | Gone: GPDMA takes any request on any channel |
| D5 pin check (PA5/PB1) | → PB3/PB4 (ADF) and bridge PA8/PA7/PA9/PB0 (unchanged) |
| D11 "forced-PWM mode" | Achieved by never using Range 4 on the SMPS; no mode bit exists |
| D12 "Stop 2 (~2 µA)" | → ~4–9 µA |

## 7. Unverified items and the checks that settle them

1. CCK duty cycle with an even CCKDIV. **S1: scope PB3 (or the Nucleo equivalent)** at 4.0 MHz; pass = 48–52%.
2. RSFLT response at F_RS = 800 kHz. **S1: swept tone or noise through D1 vs D2**, compare in-band flatness and the 80–100 kHz alias floor.
3. Where the SMPS 3 MHz clock comes from (synchronous or not). **S1/E11: spectrum of the PCM noise floor, SMPS vs LDO** (REGSEL toggled live).
4. Whether the M33 cycle counts match the M4 figures in C2. Re-benchmark on the Nucleo.
5. The 80 MHz current is interpolated. **E4** measures it.
6. VDDUSB bonding on the 48-pin SMPS package; Nucleo PB3/SWO solder bridge; the Nucleo inductor part number (UM2861/MB1549 schematic, not downloadable from here).
7. Idle-mode (ADF + LPDMA in Stop 2) currents and wake latency. **S3.**
