# A1 + A2 findings: MCU (DFSDM) and mic sourcing

**Date:** 2026-09-30 · **Status:** A1 DONE (L452CEU6 chosen) · A2 DONE (lifecycle, breakouts and backups checked)

---

## A1. Which STM32 has DFSDM?

**DFSDM** ("digital filter for sigma-delta modulators") is a hardware block that turns a PDM mic's 1-bit, multi-MHz bitstream into ordinary numbers (PCM samples) with no CPU work. Without it, the CPU has to do that conversion in software.

### Evidence (primary sources: ST datasheets)

| Part | DFSDM? | Evidence |
|---|---|---|
| **STM32L432KC** (Cortex-M4F, 80 MHz, QFN-32 5×5 mm) | **No** | DS11451 Rev 4 (May 2018): the string "DFSDM" appears 0 times in the full 156-page datasheet. The feature list shows 1× SAI and 2× SPI, with no PDM interface mentioned. |
| **STM32L452xx** (same core and speed, more RAM) | **Yes** | DS11912 Rev 7 (Oct 2020) §3.21: "one DFSDM with 2 digital filters modules and 4 external input serial channels… PDM microphone input support… maximum input clock frequency up to 20 MHz… clock output 0..20 MHz… Sinc^x filter order 1..5, oversampling ratio up to 1024; integrator oversampling 1..256; up to 24-bit output." |
| **STM32L451xx** (the L452 without USB) | **Yes** | DS11910 Rev 5 (Oct 2020): same DFSDM section (76 mentions). |

The v0.2 spec's worry was justified. **The L432 can't be used with the digital mic unless the PDM decoding is done in software.**

Other things confirmed from DS11912 that matter elsewhere:
- **TIM1 is an advanced-control timer with complementary outputs** ("1x 16-bit advanced motor-control"). This is what drives the H-bridge with dead-time insertion (B1).
- **Run current is 84 µA/MHz** (LDO mode, Range 1). **At 80 MHz that's about 6.7 mA for the CPU alone.** Sleep mode is 27 µA/MHz. This makes v0.2's "MCU 2–3 mA for algorithm A" too optimistic; see spec §7.
- **Range 2 (low-power voltage mode) caps *all* peripheral clocks at 26 MHz.** The PWM timer needs 80 MHz for 8-bit resolution at ~312 kHz, so the chip must stay in Range 1. The power lever is to sleep the CPU between DMA blocks, not to lower the clock.

### JLCPCB stock (JLC parts API, queried 2026-09-30)

| LCSC # | Part | Package | JLC library | Stock | Unit price (qty 1) |
|---|---|---|---|---|---|
| C222355 | STM32L452CEU6 | UFQFPN-48, 7×7 mm | Extended | **16** | $6.90 |
| C1337137 | STM32L451CEU6 | UFQFPN-48, 7×7 mm | Extended | 0 | — |
| C1340780 / C1340153 | STM32L452REI6 / REI3 | UFBGA-64, 5×5 mm | Extended | 0 / 4 | — |
| C2053579 | STM32L452REY6TR | WLCSP-64, 3.4×3.7 mm | Extended | 26 | $11.88 |
| C1337280 | STM32L432KCU6 (reference) | UFQFPN-32, 5×5 mm | Extended | 202 | $6.47 |

Stock of 16 is enough for this project (2 per build), but it's thin. **Buy early, or pre-order through JLC's global sourcing.**

### Options

| Option | Size | Pros | Cons |
|---|---|---|---|
| **(a) STM32L452CEU6, QFN-48 7×7 mm** | 49 mm² | Hardware PDM decoding, so the CPU is free for DSP. Leaded QFN is easy for JLC and easy to inspect. In stock (thinly). | 2× the area of the L432. Board grows a few mm. |
| (b) STM32L452 in UFBGA-64 5×5 mm | 25 mm² | Same footprint as the L432. | Almost no stock. BGA needs fine-pitch routing (probably via-in-pad, which is a pricier PCB). |
| (c) STM32L452 in WLCSP-64 3.4×3.7 mm | 13 mm² | Smallest. 26 in stock. | 0.4 mm ball pitch, so HDI PCB with via-in-pad and much higher board cost. Bare silicon is fragile, and the chip is light-sensitive. |
| (d) Keep STM32L432, decode PDM in software (SPI + DMA capture, CPU runs the CIC/FIR decimation) | 25 mm² | Smallest leaded package. Plenty of stock. | Costs an estimated ~10–20 MHz of CPU time `[Low]`, taken from the budget that algorithm B needs, and runs the CPU harder, which draws more current. More firmware risk. |

**Recommendation: (a) STM32L452CEU6** `[High]` on the DFSDM question, `[Med]` on the size trade-off. The 7×7 QFN still fits the ~10×20 mm board estimate. A few mm² is worth giving up to avoid a software decoder that competes with the DSP for cycles. Move to (b) in a later revision if the BGA comes back into stock and the board is area-limited.

The **NUCLEO-L476RG** dev board (v0.2 Phase 2 plan) has an STM32L476 with a larger DFSDM, and the same core and peripherals, so it's still a valid bench platform.

---

## A2. Mic: SPH0641LU4H-1 (partial)

**What it is:** a Knowles (now Syntiant) digital MEMS microphone. It has a 1-bit PDM output, is 3.50 × 2.65 × 0.98 mm with the port on the bottom, and has a dedicated ultrasonic mode.

### Datasheet facts (Knowles SPH0641LU4H-1 Rev B, 2015-04-06)
- **Ultrasonic mode:** 3.072–4.8 MHz clock, **845 µA typical / 1000 µA max** at 1.8 V and 3.072 MHz. Supply 1.62–3.6 V. The current rises with clock and load: ΔI = 0.5·V·ΔC·f.
- **Clock duty cycle must be 48–52%** above 2.4 MHz. This constrains the clock plan (see spec D-clock).
- **Power-up rule:** "Do not power up into ultrasonic mode. Do not wake-up from sleep mode into ultrasonic mode." Start the clock in standard mode (1.024–2.475 MHz), then raise it. Mode change takes ≤10 ms, and power-up takes ≤50 ms.
- Ultrasonic response curve: published, 10–80 kHz, normalized to 1 kHz. The datasheet gives it only as a plot, so the numbers still need digitizing for the simulation.
- SNR 64.3 dB(A), specified only in the audio band. **The ultrasonic noise floor isn't specified**, so it has to be measured (E3).
- Sensitivity −26 dBFS ±1 dB, which is good for L/R matching (R7).

### JLCPCB stock (JLC parts API, queried 2026-09-30)

| LCSC # | Part | JLC library | Stock | Unit price |
|---|---|---|---|---|
| **C2879853** | **SPH0641LU4H-1** | Extended | **1,076** | $1.99 |
| C497724 | SPH0641LM4H-1 (sibling, different spec) | Extended | 386 | $1.66 |

**Risk R4 ("no suitable mic stocked at JLC") is resolved for now.** The part is directly assemblable as an Extended part.

### Lifecycle (checked 2026-09-30) — A2 DONE
- **DigiKey:** **Active**, 22,134 in stock, $3.22, manufacturer shown as Syntiant.
- **Syntiant** reissued the datasheet as **Rev B-1, dated 2024-12-02**. Same ultrasonic mode and the same 10–80 kHz curve (+15 dB peak near 25 kHz, ~+8 dB across 35–65 kHz). A vendor that reissues a datasheet in late 2024 is still supporting the part.
- **Mouser:** "NRND" (not recommended for new designs), seen only in a search snippet; the page itself was blocked. Unverified.
- **Verdict:** fine for this project `[Med]`. Buy spares with the first order: they're $2–3 each, and one reel-cut covers every board this project will ever need.

### Ready-made breakout boards (for the bench, S1)
| Board | Price, stock | Notes |
|---|---|---|
| **Elecrow CCB50641P** | $12.50 ($9 at 5+), in stock | 15×20 mm. Fastest route to S1. |
| Switch Science #3379 | ¥1,527, 17 in stock | Japan |
| Syntiant KAS-700-0164 eval board | $31.35, 22 at DigiKey | 14-week lead time listed |
| ⚠️ **RAK18032** | $7.50 | **Don't buy.** Sold as an "ultrasonic SPH0641" board but carries the **SPH0655LM4H-1**, whose datasheet only plots to 20 kHz. |

The v0.4 plan called the Elecrow board "unverified". It exists and is in stock, so v0.5 uses it for S1.

### Backup mics (no newer purpose-built part exists)
| Part (what it is) | Ultrasonic spec | JLC (2026-09-30) | Verdict |
|---|---|---|---|
| **TDK T5838**: PDM digital MEMS mic with a low-power ultrasonic mode | Plot stops at **50 kHz**, +17 dB peak near 26 kHz | C7230692, Extended, 684 in stock, $3.47 | **Backup.** Covers the bat band (25–50 kHz) but not 50–80 kHz. |
| TDK ICS-41352: PDM mic | Response to 85 kHz | C3019173, 0 in stock; **Obsolete** at DigiKey | Not viable |
| TDK ICS-41350: PDM mic | To 40 kHz | C3171856, 87 in stock | Too narrow |
| ST IMP23ABSU: **analog** MEMS mic | To 80 kHz | C3171746, 154 in stock, $4.93 | Analog fallback (needs a preamp and ADC) |
| Infineon / Vesper | No ultrasonic parts found | — | — |

Checking whether the SPH0641LM4H-1 (C497724) also has an ultrasonic mode is no longer needed: the LU4H-1 is Active and stocked.
