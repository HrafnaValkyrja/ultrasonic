# Stereo Ultrasound — Project Spec v0.5

**Owner:** Valkyrie
**Status:** Concept phase. §1 MVP confirmed by owner 2026-09-30. MCU (D5) and firmware toolchain (D15) decided. v0.5 applies the full-plan sanity check (`docs/research/review-2026-09-30.md`). Next: owner decisions O1 and O3 in §12 → Phase 1 simulation and first bench orders. No hardware purchased.
**Last updated:** 2026-09-30 (Claude Code session). See §15 for the changelog.

**Confidence tags:** `[High]` verified from a primary source or well established · `[Med]` reasoned estimate, likely right · `[Low]` guess, verify before relying on it.

**Everything below §1 may be revised as evidence comes in. §1 is locked.**

---

## 0. Working rules (for Claude)

1. **§1 (MVP) is owner-locked.** Never change it. If evidence says part of it can't be met, say so bluntly and propose options, but leave the text alone.
2. **Gloss every part number** in plain language on first mention in any document or message: what it is, and why it's there.
3. **Primary sources.** Datasheets for specs; distributor or JLC listings for stock and price, always with the query date. Findings go in `docs/research/`, one file per task, and get summarized here. Numeric models live in `sim/` and are cited by script name.
4. **Decisions as 2–3 options with tradeoffs plus a recommendation.** The owner picks. Nothing is final without her approval.
5. **Part-choice checklist:** smallest package JLC can assemble · lowest power · **no switch-mode regulators anywhere** · in stock or sourceable. JLC "Basic" parts carry no setup fee, "Extended" parts carry a small one; say which.
6. **Teach the why** (DSP, PDM, noise shaping, power design), briefly and without condescension.
7. **Be blunt.** If something in this spec is wrong, flag it, fix it here, bump the version, and log it in §15.

---

## 1. MVP — LOCKED (owner-defined; do not modify)

### 1.1 Goal
A wearable that lets the owner hear ultrasound (roughly 20–96 kHz) in real time, in stereo, by shifting it down into a comfortable audible band and delivering it by bone conduction. It mounts on her everyday prescription glasses and must feel like an extension of her body, not a gadget.

### 1.2 Owner constraints
1. **Full-time glasses wearer.** The device clips onto her main glasses via removable 3D-printed clasps.
2. **Nothing Ear (open) headphones are worn constantly and reserved for phone audio.** The device must not use them as output, must not interfere with their fit, and must not bump the driver pod (over the ear opening, between helix root and tragus; shifts slightly during wear). The counterweight bulb sits behind the ear.
3. **Unusually good high-frequency hearing** (hears some charger and LED-driver whine). So: no audible self-noise, no switching regulators, PWM noise kept well above her hearing.
4. **Comfort and size are the top priority.** Bulky or uncomfortable means unworn means failed. Bulk goes at the front of the frame near the hinges, never near the neck or behind the ears.

### 1.3 Success tests
- **T1 House walk:** she hears ultrasonic sources (electronics, etc.) around the house. In Transient-only mode the house is tolerable, not overwhelming.
- **T2 Nature sit:** outside at dusk, bats and other ultrasonic wildlife come through as comfortable, non-shrill sound.
- **T3 Localization:** eyes closed, she can point left/right toward an ultrasonic source (e.g. a 40 kHz rangefinder emitter) better than chance.
- **T4 Coexistence:** Ear Opens worn and playing phone audio the whole time; no fit interference; both streams distinguishable.
- **T5 Wearability:** 2+ hours with no pressure pain at the transducer site or temples, including while talking and eating.
- **T6 Silence:** with no ultrasound present, the device is inaudible to her. No hiss, no whine.

---

## 2. Priorities (ranked)

1. Comfort, size, weight
2. Power draw
3. Circuit simplicity and part count
4. Cost
5. Sound pleasantness (close 5th; the reason for digital DSP over analog)

---

## 3. Architecture (per side)

```
                     32.768 kHz crystal ─▶ MSI (auto-trimmed) ─▶ PLL ─▶ 80 MHz — every clock below derives from this
SPH0641LU4H-1 mic ◀── 4.0 MHz clock (80 MHz ÷ 20) ──┐
      │ PDM 1-bit                                   │
      ▼                                             │
STM32L452 DFSDM (hardware PDM→PCM, sinc5 ÷10) ──────┘ 400 kS/s ──▶ half-band FIR ÷2 ──▶ 200 kS/s
      ▼
DSP: mic EQ → band select → shift or compress → transient gate → volume → safety ceiling   (output-band signal at 12.5 kS/s)
      ▼
×16 interpolation → 3rd-order noise shaper → TIM1 PWM, 200 kHz centre-aligned, 2-level (AD), 12.5–25 ns dead time
      ▼
H-bridge: 2× complementary MOSFET pairs (gates held off by pull resistors until TIM1 takes over) → RC-BC02 transducer

Power:    LiPo (with protection) → MCP73831 charger → low-noise 3.0 V LDO → everything
Controls: 1 button; SWD pogo pads for programming; magnetic pogo pins for charging
```

Two identical, fully independent units, one per temple arm. No wires or radio between them (D2).
Every rate in the chain is an integer ratio of one 80 MHz clock. Any switching interference that leaks into the mic path therefore folds to 0 Hz and is filtered out (D14).

---

## 4. Decisions

Each decision gives the choice, the reasoning, and what was rejected. **vX.Y** marks the version that changed it.

### D1. Output site: at the tragus (primary); root of the cheekbone arch (fallback) `[High]` — **v0.5: moved to the tragus, owner-confirmed**
- **Primary site (owner, 2026-09-30):** against the front of the tragus. The owner confirmed this is *easier* to fit than the cheekbone-arch spot alongside the Ear Opens.
  - **Why it wins:** the literature predicts ~10 dB more loudness and 25–40 dB of left/right isolation instead of ~10–15 dB. The mechanism is *cartilage conduction*: vibrating the tragal cartilage radiates sound into the ear canal (Surendran 2023).
  - **Consequences:** more loudness per milliwatt (battery, R1); much less crosstalk between sides (stereo, R5, D2).
  - **Caveat:** the jaw joint (mandibular condyle) sits directly in front of the tragus and moves when you talk or chew. Press on the tragus itself, or just above the joint, not on the soft spot over it. E2 finds the exact point, including talk-and-chew checks (T5).
  - The ear canal must stay open for the cartilage path to work. The Ear Opens don't block it.
- **Fallback site:** root of the zygomatic arch, about one finger-width above the jaw joint and 1–1.5 cm forward of the tragus. Kept in E2 as the comparison.
- **Evidence** (`docs/research/bone-conduction.md`):
  - The condyle region is 5–10 dB more sensitive than the mastoid at 1–4 kHz, and 3–14 dB more than the temple (McBride 2005/2008).
  - Localization through condyle-placed transducers matches headphones: ~23° error vs ~20° (Wang 2022).
- **Contact force:** aim for **≥1 N** through a broad, compliant pad. Our inertial exciter loses only a few dB at ~1 N; below ~0.5 N coupling gets weaker and less repeatable. T5 comfort is the limit.
- **Rejected:**
  - Streaming to the Ear Opens (violates §1.2.2).
  - Temple: 3–14 dB worse, and a glasses-pressure headache spot.
  - Air-conduction speaker: the pod is in the way.
  - Mastoid: crowded by the Ear Open hook and counterweight.

### D2. Two independent mono units, no link `[High]` — **v0.5: phase caveat**
- **Why:**
  - At ultrasonic wavelengths the head casts a strong acoustic shadow, so the loudness difference between ears is the main direction cue. Each side processing its own mic preserves it.
  - No wiring across the hinges.
  - Each clasp is half the size.
- **Caveat (v0.5):**
  - At the fallback site (~10–15 dB of isolation), each ear also hears the other side's transducer. At the tragus site (25–40 dB) the crosstalk mostly disappears. Ren 2025 models a clean left/right cue once isolation is ≥20 dB, so the tragus site largely removes this risk.
  - The two unlinked units play with arbitrary relative phase, which changes the *size* of the left/right difference each ear receives.
  - A simple model keeps its *direction*, which is what T3 needs `[Med]`. Studies that got headphone-grade localization used phase-coherent stereo (Ren 2025; Rowan & Gray 2008).
  - **S4 measures it:** free-running units vs units sharing one clock. If the difference is large, revisit a link (see Parked ideas).
- **Cost accepted:** 2 MCUs, 2 batteries, no shared settings.

### D3. Fixed gain plus manual stepped volume; no automatic gain control `[High]` — **v0.5: controls detail**
- Independent automatic gain on each side would equalize the sides and erase the direction cue.
- Volume and mode **reset to known defaults at power-on**.
- **Because the sides can't sync (v0.5):**
  - Coarse volume steps (~4 dB).
  - Each change plays a short tick pattern saying which step you're on.
  - A long press returns that side to the default, so both sides can always be re-matched in two presses.

### D4. Digital DSP, not analog frequency division `[High]`
- Analog division (comparator plus counter) sounds harsh and buzzy and throws loudness away.
- The real-time digital options are heterodyne and spectral frequency compression (§5). Time expansion, which most bat demos use, can't run in real time.

### D5. MCU = STM32L452CEU6 (QFN-48, 7×7 mm) `[High]` — **Decided v0.4 (owner approved)**
- **What it is:** ST's ultra-low-power Arm Cortex-M4F at 80 MHz, with DSP instructions, an FPU and 160 KB RAM. It includes the **DFSDM**, a hardware PDM-to-PCM converter for the mic. The v0.2 pick (L432) lacks the DFSDM. Details: `docs/research/A1-A2-mcu-and-mic.md`.
- **Pin check (v0.5):** every needed function is available on the 48-pin package.
  - mic clock PA5, mic data PB1;
  - bridge PA8/PA7 and PA9/PB0 (TIM1 CH1/CH1N, CH2/CH2N);
  - SWD PA13/PA14; crystal PC14/PC15.
  - See `A3-clock-and-peripherals.md` §5.
- **JLC:** Extended part C222355, **16 in stock** (2026-09-30). Buy early (R10).

### D6. Output stage: 200 kHz 2-level PWM, 3rd-order noise shaping, discrete H-bridge `[Med]` — **Rewritten v0.5**
- **What it is:** TIM1, the MCU's motor-control timer, switches an H-bridge made of two complementary MOSFET pairs (each pair is one N-channel + one P-channel transistor in a 1.6 mm package). The bridge drives the transducer directly, and the transducer coil smooths the switching into sound.
- **Carrier:** **200 kHz**, centre-aligned (ARR = 200), with one duty update per period over DMA. It is synchronous with the input chain (D14), and 201 duty levels.
  - *Changed from 312.5 kHz.* That rate wasn't a multiple of the sample rate, so switching leakage would fold to 87.5 kHz and play as a tone.
- **Modulation: 2-level ("AD").** The two bridge legs are driven as complements.
  - At idle, a small ripple current (≈ Vbus / (4·L·f), e.g. 12.5 mA at 0.3 mH) flows back and forth. It costs 0.04–0.4 mW.
  - While that ripple exceeds the signal current, the bridge's **dead-time errors cancel exactly**, so quiet sounds stay undistorted.
  - *Changed from the 3-level ("BD") idea in v0.3–v0.4.* BD has no idle ripple, and dead time then distorts quiet signals badly: −10 dB THD+N at −40 dBFS even at 12.5 ns (`sim/checks/deadtime_switching.py`, `C3-output-stage.md`).
- **Dead time:** 1–2 timer ticks (12.5–25 ns), set per measured MOSFET switching speed.
- **Noise shaping:** 3rd-order error feedback with one zero at DC and a zero pair near 13 kHz, plus TPDF dither.
  - Modelled noise: −93 dB (0.2–8 kHz), −90 dB (8–20 kHz), −72 dB (20–40 kHz), relative to full scale after the coil (`sim/checks/ntf_compare.py`).
  - Dither is off while squelched, so silence is an exact 50% square wave with zero noise (T6).
- **Squelch:**
  - Short gaps: keep switching at zero signal.
  - Long silences and Off: stop with a soft start/stop, because starting the ripple abruptly makes a small click.
- **Reset safety:** TIM1 outputs float from reset until configured (RM0394). **Pull-up resistors on P-gates and pull-down resistors on N-gates are mandatory.** Configure the safe idle states (OSSI, OISx) before enabling outputs.
- **Rejected:**
  - Integrated H-bridge ICs. DRV8837 has 160–200 ns delays and 30–188 ns edges, and 0.7 mA even at 50 kHz. DRV8210 tops out at 100 kHz with 500 ns dead time. DRV8833 has 450 ns dead time, 450 ns deglitch and 1.1 µs delay.
  - Amplifier IC + DAC: quiescent current, and one more part.
- **Depends on E1** (coil inductance). If L ≥ ~1 mH, AD's clean range shrinks, so consider 100 kHz / ARR 400.

### D7. Transducer = RC-BC02 / "GD02"-class module `[Med]` — **v0.5: specs disputed**
- **What it is:** a tiny inertial bone-conduction exciter, rated 300–19,000 Hz, 0.3 W nominal / 0.8 W max.
- **The maker's own pages disagree:** 12.5×5×3.5 mm and 8 Ω on one, **12.6×6×4 mm and 12 Ω** on another. **Measure a sample** (E1).
- **No inductance data exists anywhere.** The one bone transducer with published figures (Adafruit 1674, larger) is 1.26 mH / 5.8 Ω, so the 0.3 mH placeholder may be low. Higher inductance helps filtering and shrinks AD's clean range (D6).
- A DIY glasses build reported it as quiet. That's acceptable, and the D1 findings help.
- **Alternatives with maker specs, prices unverified:**
  - RC-BC95: 9.5×9×4 mm, 8 Ω, 600–15,000 Hz.
  - RC-BC09: 10.9×8.5 mm, 8 Ω, 100–5,000 Hz.
- **Bench comparison part:** Dayton BCE-1 (21×14×7.8 mm, 4 Ω).

### D8. Factory assembly at JLCPCB `[High]`
- All SMD parts are machine-placed. The owner hand-solders only the transducer leads, the battery, and optionally the button.
- The mic is a land-grid part that can only be reflowed, and it is JLC-stocked (D13).

### D9. Output band ≈ 1.5–4 kHz `[Med]` — **v0.5: keep the floor ≥1.5 kHz**
- This is the ear's most sensitive region, near typical bone-transducer resonance, so it gives the most loudness per milliwatt.
- **Keep the floor at or above ~1.5 kHz.** Below that, the ear is sensitive to waveform phase. The two unlinked units' random phase could then scramble direction (D2).

### D10. Band floor calibrated to the owner's hearing `[High]` as a principle
- Measure her upper hearing limit (C5/E5). Start the processed band just below it, so there's no gap and no doubled sounds. Stored as a firmware constant, identical on both sides.

### D11. Linear regulation only `[High]`
- Switch-mode regulators produce audible inductor whine (§1.2.3).

### D12. Modes `[High]` as requirements
- **Full:** the whole band, pitched down.
- **Transient-only (indoor default):** steady tones (charger and LED-driver whine) suppressed; changing sounds (chirps, clicks, rustles) passed through.
- **Off:** silent. MCU in Stop 2 (~2 µA), mic unpowered, bridge stopped.
- Heterodyne vs compression may become a sub-mode or a build-time choice after Phase 1.

### D13. Mic = SPH0641LU4H-1 digital MEMS with ultrasonic mode `[High]` — **v0.5: lifecycle OK, response data**
- **What it is:** a Knowles/Syntiant microphone, 3.50×2.65×0.98 mm, bottom port Ø0.325 mm, 1-bit PDM output.
  - Ultrasonic mode takes a 3.072–4.8 MHz clock and draws 845 µA typical.
  - Sensitivity matching is ±1 dB.
- **Lifecycle:** Active at DigiKey (22k in stock). Syntiant reissued the datasheet as Rev B-1 in Dec 2024. JLC C2879853, Extended, 1,076 in stock, $1.99 (2026-09-30).
- **Response (digitized from the datasheet, `sim/data/sph0641_ultrasonic_response.json`):** relative to 1 kHz,
  - +1.6 dB at 10 kHz, **+14.7 dB at 25 kHz**, about +8 dB across 35–65 kHz, +12.7 dB at 80 kHz.
  - The mic is *more* sensitive in ultrasound than at 1 kHz, which is good for distant bats (R8).
  - The 25 kHz peak is an acoustic-path resonance **on the test fixture**. Our port hole, clasp wall and mesh will reshape it. Hence the DSP **EQ stage**, the acoustic-path rules in §8, and the coupons in S1.
- **Firmware rules:**
  - Never power up or wake straight into ultrasonic mode. Start in standard mode (1.024–2.475 MHz), then raise the clock. Mode change ≤10 ms; power-up ≤50 ms.
  - Clock duty cycle 48–52% above 2.4 MHz (see D14 for the risk).
  - The SELECT pin must be tied, not left floating.
  - **No Class-2 ceramic capacitors (X5R/X7R) near the mic.**
- **Backup:** TDK T5838, a PDM mic with an ultrasonic mode, characterized only to **50 kHz**. It covers the bat band. JLC C7230692, 684 in stock.
- ⚠️ **Don't buy the RAK18032** "ultrasonic SPH0641" board. It actually carries the SPH0655, which is audio-only.

### D14. Clock tree and sample rates `[Med]` — **Rewritten v0.5**
- **Everything from one 80 MHz clock:**
  - mic clock 80 MHz ÷ 20 = **4.0 MHz** (even divider);
  - DFSDM sinc5 ÷10 → **400 kS/s**;
  - CPU half-band ÷2 → **200 kS/s** (Nyquist 100 kHz; usable to ~80–85 kHz);
  - DSP output at **12.5 kS/s**;
  - ×16 interpolation → **200 kHz** PWM update.
  - Stays in voltage Range 1: Range 2 caps peripheral clocks at 26 MHz.
- **Why synchronous:** switching interference coupling into the mic path folds to 0 Hz, where the band-floor high-pass removes it (T6).
- **DFSDM details** (RM0394; `A3-clock-and-peripherals.md` §3):
  - The CKOUT divider can only change with DFSDM disabled. The standard→ultrasonic mode switch is therefore stop, re-divide, restart; the µs gap is harmless `[Med]`.
  - Use **filter 0** (DMA1 channel 5). Filter 1 shares channel 6 with TIM1's update request.
- **⚠️ Duty-cycle risk:** DFSDM's clock output is characterized at 45–55% on a sister chip. The mic needs 48–52%. Typical is 50%, and **S1 scopes it**. Fallback: a timer-generated clock into DFSDM's CKIN pin.
- **Decimation choice (S1 measures both):**
  - default ÷10 + CPU half-band (5–10 MHz of CPU, cleaner top octave);
  - power-saving option: DFSDM ÷20 alone (0 CPU, ~12 dB droop at 80 kHz, more folded noise near the top).
- **Band-edge note (MVP says "roughly 20–96 kHz"):** realistic top is ~80–85 kHz. The mic is characterized only to 80 kHz.
  - Option if the top octave matters: 80 MHz ÷ 18 = 4.44 MHz mic clock → 247 kS/s, for +23% CPU.

### D15. Firmware toolchain: bare C with CMake, CMSIS + ST LL drivers, CMSIS-DSP `[Med]` — **Decided v0.4 (delegated to Claude)**
- **Stack:**
  - C11 built with `arm-none-eabi-gcc` and CMake from the command line.
  - ST's CMSIS device headers plus LL (thin register-level) drivers.
  - CMSIS-DSP for FFT, FIR and vector math.
  - CubeMX only as a read-only pinout and clock checker.
- **Why:** the design is timing-critical glue (DFSDM → DMA → CPU → TIM1 DMA). Register-level control keeps timing explicit. CMSIS-DSP is also what the C2 benchmarks measure. The build is reproducible.
- **Owner side:** flash and debug through the Nucleo's ST-LINK (STM32CubeProgrammer, OpenOCD, or VS Code + Cortex-Debug).
- **Rejected:**
  - CubeIDE + HAL: heavy, and hides timing.
  - Rust: immature DFSDM support.
  - Zephyr: heavyweight.

### D16. Crystal clock reference `[High]` — **New v0.5**
- **Why:** the internal oscillators are off by up to ~1–2% between units. Heterodyne output = input − oscillator frequency, so a 1% error on a 38 kHz oscillator plays the same bat call **380 Hz apart** in the two ears.
- **Recommended:** a **32.768 kHz crystal** (LSE, "watch crystal") auto-trimming the MSI oscillator, which feeds the PLL.
  - About 0.3 µA, one crystal and two capacitors.
  - JLC options: Seiko Epson **Q13FC13500004** (FC-135, 3.2×1.5 mm), C32346, **Basic part (no setup fee)**, 467k in stock, $0.17. Or Seiko Epson **X1A0000610002** (2.0×1.2 mm), C55208, Extended, 22.5k in stock, $0.24.
- **Fallback:** 8 MHz crystal (HSE). Lower clock jitter, but +0.44 mA and a slightly larger part. S1 compares the noise floor with each on the Nucleo.
- **Residual:** crystals leave ~1–2 Hz between sides in heterodyne mode. That can cause a slow level wobble on *steady* tones through bone crosstalk. Transient-only mode removes steady tones, and bat calls last milliseconds. Accepted.

### D17. Output safety: fixed ceiling and pop-free start `[High]` as requirements — **New v0.5**
- A **fixed output ceiling** (soft clip), identical on both sides. With fixed gain (D3), a loud nearby source would otherwise become a loud output. Examples: an ultrasonic pest repeller, or the HC-SR04 up close.
- Power-up, mode changes and squelch transitions must not click (D6 soft start).

### Parked or rejected ideas
- **Forward "gaze distance" sensing:** redundant with stereo vision.
- **Haptic channel for >60 kHz:** optional future layer. Anything vibrating on the head is also heard by bone conduction.
- **Blindspot Proximity on the glasses:** parked. Long hair blocks rear-facing ToF sensors.
- **Link between the two sides** (for phase-locking, shared volume, or crosstalk cancellation). Parked; revisit only if the S4 shared-clock A/B shows free-running phase hurts direction.
- **Bone-conducted ultrasound as the output** (skipping the frequency shift). Rejected: it needs ~55–60 dB more drive, has ~18 dB of usable range, and is always heard at one fixed pitch (Nakagawa 2020).

---

## 5. DSP

### 5.1 Input chain
- 200 kS/s single channel (D14). Usable band ~20–85 kHz; the mic is characterized to 80 kHz.
- **Mic EQ:** flatten the measured response (D13: a 13 dB tilt across 10–25 kHz and a +15 dB peak at 25 kHz). Free per-band gains in B; in A, one gain per oscillator setting. Final curve comes from S1 coupon measurements.
- **Band floor:** a high-pass at the D10 frequency removes audible-band content.
- Local bats (big brown, eastern red) call at roughly 25–50 kHz `[Med]`; verify in C6.

### 5.2 Algorithms (both built in simulation; chosen by listening)
- **A. Heterodyne (low CPU, ~23–48% of the MCU):**
  - Multiply by an oscillator (LO), low-pass, decimate to 12.5 kS/s.
  - Clean and tonal, one band at a time; the oscillator frequency is tunable.
- **B. Log frequency compression ("pretty" mode) — restructured v0.5 (~55–81% of the MCU):**
  - **Analysis:** a 256-point FFT at 50% overlap (0.64 ms hop, 781 Hz bins).
  - **Grouping:** bins go into ~32 log-spaced bands across ~20–85 kHz, each with its own noise floor, gate, and EQ gain. The 781 Hz bin width limits how narrow the lowest bands can be.
  - **Synthesis:** ~32 sine oscillators at 12.5 kS/s. Each band plays at its mapped frequency in ~1.5–4 kHz with the band's envelope.
  - Keeps timing and relative loudness across the whole band. The frequency map is fixed and identical on both sides.
  - *Why the change:* STFT + inverse STFT at 200 kS/s needs 85–119% of the CPU against published Cortex-M4 FFT timings (`C2-cpu-budget.md`).
  - *Sound difference:* a smooth "channel vocoder" rather than a phase-vocoder rebuild of the waveform. Phase 1 renders both for comparison.
  - **Levers if tight:** q15 FFT (~1.5× faster), 128-point FFT, fewer bands, DFSDM ÷20. The C2 budget assumed 48 oscillators, so ~32 adds margin.
- **Transient-only gate:**
  - In B, per-band spectral subtraction against a slowly updated floor.
  - In A, an envelope squelch with a slow floor.

### 5.3 Latency
- Target ≤20 ms end to end `[Med]`. Analysis frames are 1.28 ms with 0.64 ms hops, so there's plenty of room.

### 5.4 Controls
- One button: short press cycles modes; press-and-hold steps volume with tick feedback; long press resets that side (D3). Both reset at power-on.

---

## 6. Output stage: noise and linearity — **rewritten v0.5** (details: `docs/research/C3-output-stage.md`)

- **Noise is fine.** Quantization noise with the 3rd-order shaper sits ~90 dB below full scale across 0.2–20 kHz, and zero when squelched.
  - Bone-conducted ultrasound needs ~55–60 dB more drive than the 2–4 kHz band, so 20–40 kHz residue at −72 dB is irrelevant.
  - The band to protect is **8–16 kHz**: bone-conduction thresholds there track normal hearing (Popelka 2010), and the owner hears high. That's why the shaper's zeros sit near 13 kHz.
  - *v0.3 overstated this as the top risk. It was wrong.*
- **Linearity at low levels is the real risk.** Handled by 2-level modulation (D6), which is exactly clean while the ripple current exceeds the signal current. Quiet listening (≲ −30 dBFS at 0.3 mH) falls in that range. Louder signals get some distortion, masked by their own loudness.
- **Measured in S2, not assumed:**
  - idle silence (T6) with the bridge running;
  - low-level distortion via a 1 Ω sense resistor and a sound card;
  - 8–16 kHz noise by ear with squelch forced open.
- **Capacitor rule:** keep audio-rate voltage ripple off Class-2 ceramic caps on the bridge rail (they can "sing"), or use low-acoustic-noise types.

---

## 7. Power (per side) — **v0.5: runtime tied to battery options**

| Block | Current | Basis |
|---|---|---|
| Mic, ultrasonic mode | ~0.9–1.1 mA | 845 µA typ at 1.8 V; rises with supply and clock load `[High]` |
| MCU, algorithm A | ~3.2–4.4 mA | 23–48% busy at 80 MHz; 84 µA/MHz run, 27 µA/MHz sleep (`C2-cpu-budget.md`) `[Med]` |
| MCU, algorithm B (restructured) | ~4.7–5.8 mA | 55–81% busy `[Med]` |
| Peripherals (TIM1, DFSDM, DMA) | ~1 mA | TIM1 alone ≈ 0.65 mA `[Med]` |
| Bridge idle ripple + gate charge | ~0.4–2 mA | ripple loss 0.04–0.4 mW; gate charge 4 FETs × 0.5–2.5 nC × 200 kHz, **so pick a low-gate-charge MOSFET pair (B1)** `[Med]` |
| Transducer, average at listening level | ~2–5 mA; ~0 in long silence | `[Low]`, measure (E4) |
| LDO idle, crystal | <0.05 mA | `[Med]` |
| **Total** | **~7.5–13.5 mA (A), ~9–15 mA (B)** | `[Low]` |

**Runtime by battery** (usable ≈ 85% of rated; `[Low]` until E4):

| Option | Cell | Size (incl. protection) | Mass | Algorithm A | Algorithm B |
|---|---|---|---|---|---|
| (a) | ~40 mAh | ~20×8×3.5 mm | ~1.1 g | ~2.5–4.5 h | ~2.3–3.8 h |
| (b) | ~60 mAh | ~20×12.5×5.4 mm | ~2 g | ~4–7 h | ~3.5–5.5 h |
| (c) | ~100 mAh | ~30×12×4 mm | ~3 g | ~6.5–11 h | ~6–9.5 h |

- The MVP needs 2+ h (T5). All options meet it; (a) only just, in algorithm B.
- (c) is bigger than the PCB and fights priority #1.
- **Recommendation: (a) or (b). The owner decides** (§12, O1).

**Power levers, most effective first:** squelch with CPU sleep · output band placement (D9) · algorithm choice · DFSDM ÷20 · CPU sleep between DMA blocks.

**Supply rail** `[Med]`:
- **3.0 V from a low-dropout LDO**, leaving ~300 mV of headroom at the LiPo's 3.3–3.4 V knee.
- Bridge supply stays on the regulated rail. Running it straight from the battery would make gain track charge by ≈1.8 dB and unbalance the sides.
- 2-level modulation *prefers* the full 3.0 V: more ripple means a wider clean range.

---

## 8. Physical layout (per side)

- **Front clasp, just behind the hinge:** PCB, battery, button.
  - **PCB size** `[Med]` (parts-area estimate): ~10×20 mm with parts on both sides (4-layer), or ~10×28 mm single-sided. It includes the crystal and gate resistors. The 7×7 mm MCU sets the ~10 mm width.
  - **Battery** sits beside the PCB: 20–30 mm long depending on option (§7).
  - **Acoustic path rules (v0.5):**
    - The mic ports through the PCB, so use a **thin board (≤0.8 mm)**.
    - Keep the port hole short and wide (≥ the mic's Ø0.325 mm port, ~0.6–1.0 mm).
    - No gasket cavity; the clasp opening directly over the hole; thin mesh, never foam.
    - Every added mm of channel shifts the 25 kHz resonance (D13), so the S1 coupons test real geometries.
- **Along the temple arm:** thin two-conductor lead to the transducer. It carries a 200 kHz switching waveform, so route it away from the mic port and clock/data lines.
- **Drop-arm near the ear:** a short spring arm pressing the transducer on with **≥1 N** (D1) through a broad compliant pad.
  - Keep ≥1–1.5 cm clearance from the Ear Open pod through head turns and facial movement.
  - Target: against the front of the tragus (D1), so the arm is short and sits right at the ear.
- **Skin isolation:** transducer metal and solder joints fully insulated (silicone pad plus sealed housing).
- **Programming:** SWD pogo pads. **Charging:** magnetic pogo connector plus a nightly dock.
- **Mass target:** under ~8 g per side `[Low]`.
  - Rough budget: battery 1–3 g · PCB with parts ~0.8 g · transducer ~1–1.5 g `[Low]` · clasp and arm 1.5–2.5 g · wire and silicone ~0.3 g.
  - That's ~5–8 g depending on battery option.

---

## 9. Parts (candidates; nothing ordered)

Stock and price as of 2026-09-30 from the JLC parts API unless noted.

| Function | Part (what it is) | JLC | Status |
|---|---|---|---|
| MCU | **STM32L452CEU6**: 80 MHz Cortex-M4F with hardware PDM decoder, QFN-48 7×7 mm | C222355 · Extended · 16 · $6.90 | **Chosen** (D5); buy early |
| Mic | **SPH0641LU4H-1**: digital MEMS mic with ultrasonic mode, 3.5×2.65 mm | C2879853 · Extended · 1,076 · $1.99 | **Chosen** (D13); lifecycle OK |
| Mic backup | **TDK T5838**: PDM mic, ultrasonic mode to ~50 kHz | C7230692 · Extended · 684 · $3.47 | Backup only |
| Crystal | **Q13FC13500004**: 32.768 kHz watch crystal, 3.2×1.5 mm (or X1A0000610002, 2.0×1.2 mm) | C32346 · **Basic** · 467k · $0.17 (C55208 · Extended · 22.5k) | Recommended (D16) |
| H-bridge | 2× complementary N+P MOSFET pair, SOT-563 1.6×1.6 mm: **NTZD3155C** (onsemi, ~2.5 nC) or **DMC2400UV** (Diodes Inc., ~0.5 nC) | C236117 · Ext · 8,788 · $0.17 / C177025 · Ext · 113 (clone C2940616 · 3,836) | B1: on-resistance at 3.0 V gate drive and gate charge |
| Gate pulls | 4× resistors (P-gate pull-ups, N-gate pull-downs) | Basic | Mandatory (D6) |
| Charger | **MCP73831**: single-cell LiPo linear charger, SOT-23-5 | C424093 · Extended · 9,478 · $0.78 | B3 |
| LDO | Low-noise 3.0 V linear regulator, low dropout, low idle current | — | B2 |
| Transducer | RC-BC02 / GD02 bone exciter (8 or 12 Ω, to be measured) | not JLC; hand-soldered | E1 |
| Battery | 40–100 mAh LiPo with protection circuit (§7 options) | not JLC; hand-soldered | Owner decision O1 |

---

## 10. Phase plan

### Phase 1: DSP simulation (Claude, no hardware) ← **current**
1. **Test corpus:** licensed full-spectrum recordings (≥192 kS/s) of bats and katydids, plus synthetic signals (C1). S1 recordings of the owner's own environment join later.
2. **Front-end model:** digitized mic response + EQ, and DFSDM ÷10 + half-band vs ÷20.
3. **Algorithms:** A, restructured B (and the original STFT-B for a listening reference), and the transient gate. Render WAVs.
4. **Output model:** 3rd-order shaper + 2-level PWM + coil. Checks already in `sim/checks/`; refine after E1.
5. **Cycle counts** for the chosen design (C2); confirm on hardware in S3.
6. **Exit:** algorithm and parameters chosen by the owner.

### Phase 1b: Hearing calibration
- Tone-sweep WAVs (C5) on decent full-range headphones, not the Ear Opens. The result sets the D10 band floor.

### Phase 2: Bench prototype — **revised v0.5**

| Stage | Build | Answers | Needs Phase 1? |
|---|---|---|---|
| **S1: Ears** | Elecrow mic board → Nucleo DFSDM at 4.0 MHz; stream 200 kS/s audio to the PC over USB (L452 USB device on PA11/PA12), not just RAM bursts | D14 clock plan; **mic-clock duty cycle on a scope**; crystal choice (LSE vs HSE noise floor); mic ultrasonic noise floor (R8); **acoustic coupons** (response vs port geometry); **real recordings of the owner's home and yard**, including self-noise (own speech, chewing, hair on the clasp, frame creaks) | No |
| **S2: Voice** | JLC discrete-bridge test board → transducer; tones and clips from flash | E1 (inductance, resistance); **E2 placement: tragus (primary) vs cheekbone-arch fallback, at ≥1 N, Ear Opens playing**; R1 (loud enough?); **low-level distortion (1 Ω sense resistor + sound card); idle silence (T6); 8–16 kHz noise by ear** | No |
| **S3: Brain** | S1 + S2 joined, chosen algorithm in real time | R3 (CPU, measured with the cycle counter), E4 (current per mode), latency, no clicks (D17) | Yes |
| **S4: Stereo** | Two full units on a rough head mount, battery-powered | **Exit: T1, T2, T3, T6 pass.** Plus **A/B: free-running vs shared clock** (does phase matter for direction? D2) | Yes |

**Bench rules:**
- Listening tests run on battery, never laptop USB. USB streaming is for recording only.
- Use **NUCLEO-L452RE**, not -P: the -P variant has an onboard switching regulator.
- Check whether the Nucleo's user LED shares PA5; if so, remove its solder bridge.

**Shopping list v0.5** (to price and verify before ordering; owner approves):
- 2× **NUCLEO-L452RE**: ST dev board with the same MCU. ST eStore / DigiKey list it in stock.
- 2–3× **Elecrow CCB50641P** SPH0641LU4H-1 mic boards: $12.50 each, in stock.
- **One JLC order** (Claude designs it):
  - ~5× discrete-bridge test boards (final MOSFETs, gate pulls, sense resistor, headers);
  - ~5× acoustic coupons: the mic on 0.6/0.8/1.0 mm boards with different port-hole sizes.
- 3× **RC-BC02** (buy from two listings, since the specs disagree) + 1× **Dayton BCE-1**. Longest shipping, so **order first**.
- 2× small protected LiPo cells + 2× linear-regulator modules. A USB breakout cable for S1 streaming.
- Test sources: **HC-SR04** (40 kHz ultrasonic rangefinder) as a T3 emitter; keys.
- Owner's kit: LCR meter (E1), PPK2 power profiler (E4). A cheap USB scope or logic analyzer is needed for the duty-cycle check.
- *Removed from v0.4:* DRV8833 modules (far too slow, D6); custom mic breakouts (Elecrow exists).

**Split:**
- Claude: JLC board designs, all firmware (D15), capture and analysis scripts, test procedures.
- Owner: ordering, wiring, all listening and wear tests.

### Phase 3: PCB
- Schematic checked against JLC stock → owner lays out in KiCad → Claude reviews and runs DRC, generates BOM and placement files → order assembled boards.

### Phase 4: Mechanical and integration
- 3D-printed clasps and drop-arms; iterate on fit. **Exit:** T1–T6 pass while worn.

---

## 11. Risks

| # | Risk | Likelihood | Resolved by |
|---|---|---|---|
| R1 | Transducer too quiet at the chosen site | `[Low]` (v0.5: tragus site, predicted +~10 dB) | E2 |
| R2 | Coil inductance outside the range where filterless 2-level PWM works well | `[Low]` | E1; fixes: 100 kHz PWM, or one series inductor |
| R3 | Algorithm B too heavy for 80 MHz | `[Med]` (restructured; 55–81% on published timings) | S3 measurement; levers in §5.2 |
| ~~R4~~ | ~~No ultrasonic MEMS mic stocked at JLC~~ | Resolved v0.3 | — |
| R5 | Stereo too weak or unstable for T3 (crosstalk + unlinked phase) | `[Low]` (v0.5: tragus site gives 25–40 dB isolation) | S4 incl. shared-clock A/B |
| R6 | Contact comfort at ≥1 N on the tragus; jaw movement | `[Med]` | E2, Phase 4 wear tests |
| R7 | L/R mismatch (mic sensitivity ±1 dB, coupling) biases direction | `[Low]` | Per-side trim at calibration; D3 re-match |
| R8 | Mic ultrasonic self-noise too high for distant bats | `[Low]` (mic is 8–15 dB *more* sensitive in ultrasound) | S1 |
| R9 | PWM noise audible | **`[Low]`** (v0.5: ~−90 dB with a 3rd-order shaper; 8–16 kHz is the band to watch) | S2 by ear |
| R10 | MCU stock is thin (16 at JLC) | `[Med]` | Buy or pre-order early |
| R11 | Battery life vs clasp size | `[Med]` | Owner decision O1; E4 |
| **R12** | Low-level distortion from dead time exceeds the model (node capacitance, MOSFET behaviour) | `[Med]` | S2 measurement |
| **R13** | DFSDM clock duty cycle outside the mic's 48–52% | `[Low]` | S1 scope; timer-clock fallback |
| **R14** | Acoustic path (port, wall, mesh) cuts ultrasonic sensitivity or adds resonances | `[Med]` | S1 coupons; §8 rules; DSP EQ |
| **R15** | Self-noise (own speech, chewing, hair) makes transient mode busy | `[Med]` | S1 recordings; gate tuning (C4) |

---

## 12. Tasks and decisions

### Owner decisions (open)
| ID | Decision | Recommendation |
|---|---|---|
| **O1** | Battery and runtime target (§7 table) | (a) ~40 mAh or (b) ~60 mAh |
| ~~O2~~ | ~~Test a spot nearer the tragus?~~ | **Resolved 2026-09-30:** the tragus is the primary site, and the owner says it fits more easily (D1) |
| **O3** | Approve the v0.5 shopping list once priced | — |

Status key: `OPEN` · `IN PROGRESS` · `DONE`. Priority: **P1** blocks Phase 1 or the schematic · **P2** before board order · **P3** before final assembly.

### A. Architecture (P1)
| ID | Task | Status |
|---|---|---|
| A1 | MCU with DFSDM | **DONE**: `A1-A2-mcu-and-mic.md`. L452CEU6 chosen. |
| A2 | Mic lifecycle, stock, backups | **DONE**: Active, JLC-stocked; backup T5838; Elecrow board for the bench. |
| A3 | Clock plan and DFSDM settings | **DONE on paper**: `A3-clock-and-peripherals.md`. Bench checks in S1 (duty cycle, crystal). |
| A4 | Transducer options and inductance | **IN PROGRESS**: no inductance data exists anywhere; specs disputed; measure (E1). Alternatives listed in D7. |

### B. Schematic parts (P2)
| ID | Task | Notes |
|---|---|---|
| B1 | H-bridge MOSFET pair | **IN PROGRESS**: discrete chosen (D6). Pick NTZD3155C vs DMC2400UV on on-resistance at 3.0 V gate drive **and gate charge**, which sets 0.4–2 mA of switching current. |
| B2 | 3.0 V LDO | Low noise, low dropout at bridge peaks, low Iq |
| B3 | Charger | MCP73831 (C424093); program ≤1C for the chosen cell |
| B4 | Battery | After O1: concrete cell, size, mass, sourcing |
| B5 | Button | Smallest tactile switch; JLC-assemblable preferred |
| B6 | Connectors | Magnetic 2-pin charge pogo; SWD footprint; ESD on exposed contacts |
| B7 | Costing | BOM per side; JLC assembly for 2/5/10 boards |
| B8 | Crystal | **New.** Choose FC-135 (Basic) vs 2012 (Extended); check LSE drive margin (AN2867) |

### C. DSP and firmware (P1 for Phase 1)
| ID | Task | Status |
|---|---|---|
| C1 | Test corpus | OPEN |
| C2 | CPU budget | **DONE on paper**: `C2-cpu-budget.md`. B restructured. Measure in S3. |
| C3 | Output stage | **DONE on paper**: `C3-output-stage.md`. 2-level PWM, 3rd-order shaper, discrete bridge. Refine after E1. |
| C4 | Transient gate tuning (incl. self-noise) | OPEN |
| C5 | Hearing-test sweep WAVs + procedure | OPEN |
| C6 | Local bat call frequencies | OPEN |
| C7 | Transducer response above 20 kHz | **Mostly moot** (bone-conducted ultrasound thresholds, D6/§6). Check 8–16 kHz response in S2. |
| C8 | Mic EQ from coupon measurements | **New.** After S1 |

### D. Mechanical and materials (P3)
| ID | Task |
|---|---|
| D1 | Nitinol wire, skin-safe silicone, JLC PA12 nylon print rules |
| D2 | Acoustic mesh that passes 20–80 kHz and keeps out dust and sweat |
| D3 | Skin-contact insulation method for the transducer |
| D4 | **New.** Drop-arm spring design for ≥1 N with a compliant pad (after E2) |

### E. Owner bench measurements (Claude writes procedures and analyzes results)
| ID | Measurement | Resolves |
|---|---|---|
| E1 | Transducer coil inductance and resistance (LCR meter) | R2, D6, D7 |
| E2 | Placement: tragus (primary; find the exact point clear of the jaw joint) vs cheekbone-arch fallback, at ≥1 N, Ear Opens playing; talk and chew; judge left/right separation by ear | R1, R5, R6, D1 |
| E3 | Mic ultrasonic noise floor; acoustic coupons | R8, R14 |
| E4 | Current per mode (PPK2) | §7, R11 |
| E5 | Hearing sweep with the C5 files | D10 |
| E6 | **New.** Mic-clock duty cycle (scope) | R13 |
| E7 | **New.** Low-level distortion and idle silence on the bridge test board | R9, R12 |
| E8 | **New.** Stereo A/B: free-running vs shared clock (S4) | R5, D2 |

**Suggested order:** O1 and O3 → order transducers and Nucleos → JLC board designs → C1 → Phase 1 algorithms → S1/S2 as parts arrive → B-series → D-series.

---

## 13. Program context (not in scope)
- **Northsense:** torso band, 8 LRA motors plus an IMU giving a constant north cue. Next project.
- **Blindspot Proximity:** parked (hair blocks rear sensors on glasses); may reuse the Northsense torso hardware.
- **Program principles:** continuous signals rather than alerts; direction mapped to body location; adaptive normalization only where it doesn't destroy the cue (not here, D3); quiet by default; comfort first; one new sense at a time.

---

## 14. Glossary
- **PDM (pulse-density modulation):** a 1-bit stream at MHz rates where the density of 1s tracks the signal. MEMS mics output it, and it must be filtered and decimated into normal samples.
- **DFSDM:** the STM32 hardware block that does that PDM-to-PCM filtering.
- **Decimation / interpolation:** lowering / raising the sample rate, with filtering so nothing folds (aliases) into the wrong frequency.
- **Aliasing / folding:** a frequency above half the sample rate reappearing at a lower one. It's why the PWM rate is locked to the sample rate.
- **Heterodyne:** shifting frequencies down by multiplying with a tone (the local oscillator, LO), then filtering. You hear one band at a time.
- **Log frequency compression:** squeezing a wide frequency range into a narrow one on a log scale, so each octave keeps its share (hearing aids use this).
- **Channel vocoder / oscillator bank:** measuring the loudness in many bands, then replaying each band as a tone at a new frequency. This is how restructured algorithm B synthesizes.
- **EQ (equalization):** frequency-dependent gain that flattens the mic's uneven response.
- **Squelch:** muting output below a threshold.
- **Noise shaping:** feedback in the quantizer that pushes rounding noise away from the frequencies you care about. Its "zeros" are the frequencies where it pushes hardest.
- **Dither:** a tiny deliberate noise added before rounding, so rounding errors don't form tones.
- **Dead time:** a few nanoseconds per switching edge when both transistors in a bridge leg are off, so they never short the supply. It distorts quiet signals unless the modulation cancels it.
- **2-level (AD) PWM:** the two bridge legs switch as opposites. The load always sees +V or −V; a small ripple current flows at idle and cancels dead-time errors.
- **3-level (BD) PWM:** legs switch in step, so the load sees +V, 0 or −V. No idle ripple, but dead time distorts quiet signals. Rejected in v0.5.
- **Crystal / ppm:** a quartz timing part accurate to tens of parts per million, vs ~1–2% for on-chip oscillators.
- **Interaural level difference:** the loudness difference between your ears, the main cue for locating high-frequency sounds.
- **Transcranial attenuation:** how much quieter one side's bone-conducted sound is at the opposite ear. Low values mean more crosstalk between sides.
- **Cartilage conduction:** vibrating the ear-canal cartilage so it radiates sound into the canal. Louder and more one-sided than bone conduction.

---

## 15. Changelog

### v0.5 (2026-09-30) — full-plan sanity check (`docs/research/review-2026-09-30.md`)
- **D16 new: crystal clock reference.** Internal oscillators (±1–2%) would put the two ears up to ~380 Hz apart in heterodyne mode.
- **D14 rewritten:** one synchronous clock tree; PWM moved to 200 kHz so switching leakage folds to 0 Hz instead of an audible 87.5 kHz tone. DFSDM register constraints recorded; DMA filter 0; duty-cycle risk (R13).
- **D6 rewritten:** **2-level (AD) modulation** replaces the 3-level (BD) idea (dead-time distortion model). 3rd-order noise shaper. Discrete MOSFET bridge (integrated H-bridge ICs rejected on timing). Mandatory gate pull resistors (TIM1 outputs float from reset).
- **§5.2 algorithm B restructured** to analysis FFT + low-rate oscillator-bank synthesis. The original needs 85–119% of the CPU on published M4 FFT timings. Mic EQ stage added.
- **§6 rewritten:** PWM noise downgraded (R9 → Low). v0.3's alarm was wrong. Low-level linearity is the real output risk (R12).
- **D1: primary site moved to the tragus** (owner: easier fit; literature: ~10 dB louder, 25–40 dB isolation). Cheekbone-arch root is now the fallback; ≥1 N contact force; avoid pressing over the jaw joint. R1 and R5 lowered; O2 resolved. **D2:** unlinked-phase caveat and S4 A/B test. **D9:** floor stays ≥1.5 kHz.
- **D13:** lifecycle confirmed; response curve digitized; backup mic (T5838); RAK18032 warning; no Class-2 caps near the mic.
- **D7:** vendor spec contradictions noted (8 vs 12 Ω, two sizes); no inductance data exists.
- **D3:** tick feedback and long-press re-match. **D17 new:** output ceiling and pop-free transitions.
- **§7:** power re-derived from C2; runtime table per battery option; the v0.3 "~100 mAh for all day" is now an owner decision (O1), because a 100 mAh cell is bigger than the PCB.
- **§8:** acoustic-path rules (thin PCB, short wide port, no foam); transducer lead routing; mass budget.
- **§10:** S1 uses the Elecrow board (it exists; v0.4 wrongly called it unverified) plus USB streaming and coupons. S2 uses a JLC discrete-bridge board (DRV8833 removed). New tests E6–E8.
- New risks R12–R15; new tasks B8, C8, D4; owner decisions O1–O3.
- New research notes: `bone-conduction.md`, `A3-clock-and-peripherals.md`, `C2-cpu-budget.md`, `C3-output-stage.md`, `review-2026-09-30.md`. New checks: `sim/checks/ntf_compare.py`, `sim/checks/deadtime_switching.py`.

### v0.4 (2026-09-30)
- §1 MVP confirmed by owner. **D5 decided:** STM32L452CEU6. **D15 new:** firmware toolchain.
- §10 Phase 2 rewritten as staged bench plan S1–S4. §8 PCB size estimate.

### v0.3 (2026-09-30)
- §1 MVP section created and locked. **D5:** STM32L432KC → STM32L452CEU6 (the L432 has no DFSDM). **D13:** JLC stock confirmed. **D14 new:** clock plan. §6 output-noise section (overstated; corrected in v0.5). §7 power re-estimate. R9–R11 added.

### v0.2
- Design-chat handoff (original document).
