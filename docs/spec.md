# Stereo Ultrasound — Project Spec v0.4

**Owner:** Valkyrie
**Status:** Concept phase. §1 MVP confirmed by owner 2026-09-30. MCU (D5) and firmware toolchain (D15) decided. Next: Phase 1 DSP simulation, remaining P1 research, and ordering long-lead bench parts (Phase 2). No hardware purchased.
**Last updated:** 2026-09-30 (Claude Code session). See §15 for the changelog.

**Confidence tags:** `[High]` verified from a primary source or well established · `[Med]` reasoned estimate, likely right · `[Low]` guess, verify before relying on it.

**Everything below §1 may be revised as evidence comes in. §1 is locked.**

---

## 0. Working rules (for Claude)

1. **§1 (MVP) is owner-locked.** Never change it; if evidence says part of it can't be met, say so bluntly and propose options, but leave the text alone.
2. **Gloss every part number** in plain language on first mention in any document or message (what it is, why it's there).
3. **Primary sources.** Datasheets for specs; distributor or JLC listings for stock and price, always with the query date. Findings go in `docs/research/`, one file per task, and get summarized here.
4. **Decisions as 2–3 options with tradeoffs plus a recommendation.** The owner picks. Nothing is final without her approval.
5. **Part-choice checklist:** smallest package JLC can assemble · lowest power · **no switch-mode regulators anywhere** · in stock or sourceable. JLC "Basic" parts carry no setup fee, "Extended" parts carry a small one; say which.
6. **Teach the why** (DSP, PDM, noise shaping, power design), briefly and without condescension.
7. **Be blunt.** If something in this spec is wrong, flag it and fix it here, bump the version, and log it in §15.

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
SPH0641LU4H-1 digital mic ──PDM 1-bit @ 4.0 MHz──▶ STM32L452 DFSDM (hardware PDM→PCM)
                                                        │ 200 kS/s PCM via DMA
                                                        ▼
                                  DSP: band select → shift/compress → gate → volume
                                                        │
                                  noise-shaped PWM (TIM1, complementary + dead-time)
                                                        ▼
                               H-bridge (2 complementary MOSFET pairs) → RC-BC02 transducer

Power:    LiPo (with protection) → MCP73831 charger → low-noise LDO → everything
Controls: 1 button; SWD pogo pads for programming; magnetic pogo pins for charging
```

Two identical, fully independent units, one per temple arm. No wires or radio between them (D2).

---

## 4. Decisions

Each decision gives the choice, the reasoning, and what was rejected. **Changed in v0.3** marks revisions.

### D1. Output: bone conduction at the root of the cheekbone arch `[High]`
- **Site:** root of the zygomatic arch, about one finger-width above the jaw joint (mandibular condyle) and 1–1.5 cm forward of the tragus.
- **Why:** thin soft tissue over bone, close to the cochlea, the site commercial bone-conduction headsets use. Sitting above the jaw joint keeps contact steady when the jaw moves.
- **Rejected:** streaming to the Ear Opens (violates §1.2.2); temple (the temporalis muscle damps vibration, estimated 5–10 dB worse `[Low]`, and it's a glasses-pressure headache spot); air-conduction speaker (the Ear Open pod is in the way); mastoid (crowded by the Ear Open hook and counterweight).

### D2. Two independent mono units, no link `[High]`
- **Why:** at ultrasonic wavelengths (under 1 cm) the head casts a strong acoustic shadow, so the loudness difference between ears (interaural level difference) is the main direction cue. Each side processing only its own mic preserves that cue for free. It also removes wiring across the hinges (the biggest mechanical failure risk) and halves each clasp's size.
- **Cost accepted:** 2 MCUs, 2 batteries, no shared settings.

### D3. Fixed gain plus manual stepped volume; no automatic gain control `[High]`
- Independent AGC on each side would equalize the two sides and erase the loudness difference. Volume uses discrete indexed steps; volume and mode **reset to known defaults at power-on**, so both sides start matched.

### D4. Digital DSP, not analog frequency division `[High]`
- Analog division (comparator plus counter) sounds harsh and buzzy and throws away loudness. The real-time digital options are heterodyne and spectral frequency compression (§5). Time expansion, which most online bat demos use, can't run in real time.

### D5. MCU = STM32L452CEU6 (QFN-48, 7×7 mm) `[High]` — **Decided v0.4 (owner approved 2026-09-30)**
- **What it is:** an ST ultra-low-power Arm Cortex-M4F at 80 MHz with DSP instructions, a floating-point unit, 160 KB of RAM, and a **DFSDM**: a hardware block that converts the mic's PDM bitstream to PCM without CPU help.
- **Why the change:** the v0.2 pick, the STM32L432KC, **has no DFSDM.** Its datasheet (DS11451 Rev 4) never mentions it. The L452 datasheet (DS11912 Rev 7 §3.21) confirms it. The L452 also has TIM1, an advanced timer with complementary outputs and dead-time, which is what the H-bridge needs.
- **Tradeoff:** 7×7 mm instead of 5×5 mm. The alternatives were a 5×5 mm BGA (out of stock), a 3.4×3.7 mm chip-scale package (needs a pricier HDI board), or keeping the L432 and decoding PDM in software (eats CPU the DSP needs). Details and options: `docs/research/A1-A2-mcu-and-mic.md`.
- **JLC:** Extended part C222355, **16 in stock** (2026-09-30). Thin; buy early.
- **Approved by owner** (option a).

### D6. Output stage: filterless PWM into an H-bridge; no amplifier IC `[Med]`
- TIM1 generates PWM at about 312.5 kHz (80 MHz ÷ 256 = 8-bit resolution), driving an H-bridge made from two complementary MOSFET pairs, which drives the transducer directly. The coil's inductance and resistance act as a low-pass filter.
- **Removes:** the amplifier IC, its idle current, and the DAC.
- **Squelch:** hold both bridge legs at the same level, so zero current flows and there's zero noise.
- **v0.3 correction — the noise headroom is much smaller than v0.2 claimed. See §6.** Solving this is the main job of C3.

### D7. Transducer = RC-BC02 / "GD02"-class module `[Med]`
- A tiny bone-conduction exciter: 12.6 × 6 × 4 mm, 8 Ω, 0.3 W, 300–19,000 Hz, 88 dB at 1 kHz. It's the smallest part found that has a datasheet. 8 Ω draws about half the current of 4 Ω parts.
- A DIY glasses build reported it as quiet. That's acceptable (listening will be quiet) and mitigated by the D1 site and the D9 output band.
- Coil inductance is unpublished. Measure it (E1). Placeholder is 0.3 mH.
- Bench comparison part: Dayton BCE-1 (21 × 14 × 7.8 mm, 4 Ω, 2.1 kHz resonance).

### D8. Factory assembly at JLCPCB `[High]`
- All SMD parts are machine-placed. The owner hand-solders only the transducer leads, battery, and optionally the button. MEMS mics are land-grid parts that can only be reflowed, so **the mic must be JLC-assemblable.** It is: see D13.

### D9. Output band ≈ 1.5–4 kHz `[Med]`
- This is the ear's most sensitive region and near typical bone-transducer resonance, so it gives the most loudness per milliwatt. Final limits come from Phase 1 listening.

### D10. Band floor calibrated to the owner's hearing `[High]` as a principle
- Measure her upper hearing limit (C5/E5). Start the processed band just below it, so there's no gap and no doubled sounds. Stored as a firmware constant, identical on both sides.

### D11. Linear regulation only `[High]`
- Switch-mode regulators produce audible inductor whine (§1.2.3).

### D12. Modes `[High]` as requirements
- **Full:** the whole band, pitched down.
- **Transient-only (indoor default):** steady tones (charger and LED-driver whine) suppressed; changing sounds (chirps, clicks, rustles) passed through.
- **Off:** silent. MCU in Stop 2 (about 2 µA) and mic unpowered.
- Heterodyne vs compression may become a sub-mode or a build-time choice after Phase 1.

### D13. Mic = SPH0641LU4H-1 digital MEMS with ultrasonic mode `[High]` — **v0.3: sourcing confirmed**
- **What it is:** a Knowles/Syntiant microphone with a 1-bit PDM output, 3.50 × 2.65 × 0.98 mm, bottom port. In ultrasonic mode it takes a 3.072–4.8 MHz clock, draws 845 µA typical, and has a published response curve to 80 kHz, with ±1 dB sensitivity matching (good for L/R balance).
- **Why digital:** the ultrasonic response is specified; a 1-bit stream is immune to noise from the H-bridge a few mm away (an analog preamp with 40 dB gain would not be); no preamp, bias network, or ADC.
- **Datasheet rules the firmware must follow** (Rev B, 2015-04-06):
  - Never power up or wake directly into ultrasonic mode. Start in standard mode (1.024–2.475 MHz), then raise the clock. Mode change ≤10 ms, power-up ≤50 ms.
  - Clock duty cycle must be 48–52% above 2.4 MHz.
- **JLC:** Extended part C2879853, **1,076 in stock**, $1.99 (2026-09-30).
- **Still open:** lifecycle status, a backup part, and the ultrasonic noise floor (not in the datasheet; measure it, E3).
- **Fallback:** SPV0142LR5H-1 analog mic (ultrasonic response not rated; needs an analog front end).

### D14. Clock and sample-rate plan `[Med]` — **New in v0.3**
- SYSCLK = 80 MHz (must stay in voltage Range 1, since Range 2 caps peripheral clocks at 26 MHz and PWM needs 80).
- **Mic clock = DFSDM clock output = 80 MHz ÷ 20 = 4.0 MHz.** Ultrasonic mode, and an even divider, which should give a clean 50% duty cycle (confirm in the reference manual, RM0394).
- **Output rate = 4.0 MHz ÷ 20 = 200 kS/s** (Nyquist 100 kHz). Two candidate filter setups for C1/A3 to compare in simulation:
  - (i) DFSDM sinc filter decimating by 20 directly;
  - (ii) DFSDM decimates by 10 to 400 kS/s, then a CPU half-band filter decimates by 2.
  - (ii) costs a little CPU but likely gives a cleaner top octave. A decimation ratio of only 20 leaves the mic's own shaped noise rising toward 100 kHz `[Med]`.
- **Startup:** clock ÷40 (2.0 MHz, standard mode), wait ≥50 ms, switch to ÷20 (4.0 MHz), wait ≥10 ms, unmute.
- The earlier 3.2 MHz idea (÷25) is rejected. An odd divider risks breaking the 48–52% duty-cycle rule.

### D15. Firmware toolchain: bare C with CMake, CMSIS + ST LL drivers, CMSIS-DSP `[Med]` — **New in v0.4 (delegated to Claude)**
- **Stack:**
  - C11 built with `arm-none-eabi-gcc` and CMake, from the command line.
  - ST's CMSIS device headers plus the **LL (low-layer) drivers**: thin, register-level helpers from the STM32CubeL4 package.
  - **CMSIS-DSP** (Arm's optimized DSP library) for FFTs, FIR filters, and vector math.
  - STM32CubeMX is used only as a read-only checker for the pinout and clock tree; its generated code is not used.
- **Why:**
  - This project is timing-critical glue between three peripherals: DFSDM → DMA → CPU → TIM1 PWM. Register-level control makes buffer timing and latency explicit.
  - The HAL (ST's heavyweight driver layer) adds callbacks and overhead that get in the way here.
  - CMSIS-DSP is also the reference for the cycle-cost estimates in C2, so benchmarks and firmware use the same code.
  - Command-line builds are reproducible, work in CI, and work in the environment Claude builds from.
- **Owner side:** flash and debug through the Nucleo's built-in ST-LINK, using STM32CubeProgrammer, OpenOCD, or VS Code with the Cortex-Debug extension. No IDE lock-in.
- **Rejected:**
  - STM32CubeIDE + HAL: fastest to a first blink, but heavy, IDE-bound, and opaque on timing.
  - Rust (embassy / stm32 crates): DFSDM support is immature, and the DSP libraries are less proven on the M4F.
  - Zephyr RTOS: heavyweight, and DFSDM support is limited.

### Parked or rejected ideas
- **Forward "gaze distance" sensing:** redundant with stereo vision.
- **Haptic channel for >60 kHz:** optional future layer. Anything vibrating on the head is also heard by bone conduction. Nature above 60 kHz is sparse (it's mostly electronics and rodent repellers).
- **Blindspot Proximity on the glasses:** parked. Long hair blocks rear-facing time-of-flight sensors.

---

## 5. DSP

### 5.1 Sampling
- 200 kS/s single channel (D14). The mic's published curve stops at 80 kHz; expect roll-off above that.
- Local bats (big brown, eastern red) call at roughly 25–50 kHz `[Med]` (verify in C6).
- A high-pass after decimation removes audible-band content, so she doesn't hear the room twice. The corner is set by D10.

### 5.2 Algorithms (build both in simulation; choose by listening)
- **A. Heterodyne (low CPU):** multiply by a local oscillator, low-pass, decimate. Clean and tonal, but it covers one band of limited width at a time; the oscillator frequency is tunable. Estimate: low tens of MHz `[Med]`.
- **B. STFT log frequency compression ("pretty" mode):** a short-time FFT maps 20–100 kHz onto roughly 1.5–4 kHz on a log scale, with overlap-add resynthesis. Keeps timing and relative loudness across the whole band. Estimate: 60–120 MHz-equivalent `[Low]`. **It may not fit at 200 kS/s**; if not, use a smaller FFT, less overlap, or a lower rate. A 512-point frame is 2.56 ms with 390 Hz bins.
- **Transient-only gate:** in B, spectral subtraction against a slowly updated per-bin noise floor. In A, envelope squelch with a slow floor.

### 5.3 Latency
- Target ≤20 ms end to end, so sound tracks head turns `[Med]`. The STFT frame alone is ~2.6 ms, so there's room.

### 5.4 Controls
- One button: short press cycles modes; press-and-hold steps volume. Both reset at power-on (D3).

---

## 6. Output noise (owner-specific; **reframed in v0.3**)

**The requirement:** PWM quantization noise must be inaudible to her at max volume. That means nothing audible up to ~20 kHz, ideally nothing perceptible up to ~40 kHz, since bone conduction can carry ultrasound to the ear.

**What v0.2 got wrong:** it computed ~60× oversampling from the <5 kHz *signal* band. Noise shaping, though, has to keep noise out of the whole band she can *hear*, 0–20 kHz (or 40 kHz). Against 40 kHz, 312.5 kHz PWM is only about **4× oversampling**, and a noise shaper at 4× buys only a few dB. The "filterless 8-bit PWM + noise shaping" idea is not proven. It needs real modelling (C3).

**What helps:**
- The coil low-pass. With the 0.3 mH / 8 Ω placeholder, the corner is about 4.2 kHz, giving about 37 dB of first-order attenuation at the carrier. It also attenuates the 20–40 kHz band by 14–20 dB.
- The transducer's own mechanical roll-off above ~19 kHz (datasheet band edge). The actual ultrasonic leakage is C7.
- Squelch: no drive at all when nothing is present (T6).
- **3-level ("class-BD") modulation** on the H-bridge: zero differential drive at idle, and the ripple lands at 2× the PWM rate.

**What hurts:** digital volume turns the signal down but leaves the noise where it is. **The signal-to-noise ratio is worst at the low volumes she'll actually use.** Candidate fixes for C3:
- (a) Scale bridge drive so full-scale PWM equals the max loudness she needs, and spend all 8 bits on the useful range.
- (b) Higher-order shaper combined with lower resolution at a higher PWM rate.
- (c) One small series inductor (0805) plus a capacitor to make a 2nd-order filter.

C3 picks, with plots.

---

## 7. Power (per side) — **re-estimated in v0.3 from datasheet numbers**

| Block | Current | Basis |
|---|---|---|
| Mic, ultrasonic mode | ~0.9–1.1 mA | 845 µA typ at 1.8 V; rises with supply voltage and clock load `[High]` |
| MCU, algorithm A | ~3–4 mA | 84 µA/MHz run, 27 µA/MHz sleep at 80 MHz; CPU busy ~30% `[Med]` |
| MCU, algorithm B | ~5–7 mA | same, CPU busy ~70–90% `[Low]` |
| Peripherals (TIM1, DFSDM, DMA) | ~1 mA | TIM1 alone 8.1 µA/MHz ≈ 0.65 mA `[Med]` |
| Transducer, average at listening level | ~2–5 mA; ~0 squelched | `[Low]`, measure (E4) |
| LDO idle current | <0.05 mA | typical for low-Iq LDOs `[Med]` |
| **Total** | **~7–11 mA (A), ~9–14 mA (B)** | `[Low]` |

**Runtime:** ~3–5 h on a 40 mAh cell, ~8–12 h on 100 mAh. v0.2's 5–8 mA estimate for A was optimistic, because at 80 MHz the CPU alone draws ~6.7 mA when it's awake. **For all-day wear, plan for ~100 mAh per side.** Mass trade-off in B4.

**Power levers, most effective first:** squelch (and CPU sleep while squelched) · output band placement (D9) · algorithm choice · CPU sleep between DMA blocks.

**Supply rail** `[Med]`: a 3.3 V rail from a LiPo needs ≤100 mV dropout at ~400 mA bridge peaks (3.3 V ÷ 8 Ω) once the cell sags to 3.4 V. That's hard. Options for B2:
- (a) **Drop the rail to 3.0 V.** Every part is fine at 3.0 V, and it leaves ~300 mV of headroom.
- (b) 3.3 V rail plus a firmware duty cap.
- (c) Run the bridge straight from the battery. **Rejected:** gain would then track the charge state (≈1.8 dB from 4.2 V to 3.4 V), so the two sides would drift out of balance and bias perceived direction (D3).

Leaning (a).

---

## 8. Physical layout (per side)

- **Front clasp, just behind the hinge:** PCB, battery, button.
  - **PCB size estimate** `[Med]`, from a parts-area sum, not a layout:
    - ~10 × 20 mm with parts on both sides, 4-layer;
    - ~10 × 28 mm with parts on one side only.
  - The 7×7 mm MCU sets the ~10 mm minimum width. See §9 for the parts that drive the area.
  - The battery will probably be about as large as the board (B4). The mic port is on the bottom, so **the PCB needs a port hole, and the clasp an outward-facing opening covered with thin mesh.** Thick foam absorbs ultrasound.
- **Along the temple arm:** thin two-conductor lead to the transducer.
- **Drop-arm near the ear:** a short spring arm, 1–2 cm below the temple arm, pressing the transducer onto the cheekbone arch root with light, even force through a broad pad. It must keep ≥1–1.5 cm clearance from the tragus and the Ear Open pod through head turns and facial movement.
- **Skin isolation:** transducer metal and solder joints fully insulated (silicone pad plus sealed housing). Sweat can otherwise carry drive current through skin.
- **Programming:** SWD pogo pads. **Charging:** magnetic pogo connector plus a nightly dock.
- **Mass target:** under ~8 g per side `[Low]`. Glasses get uncomfortable at ~15 g added per side.

---

## 9. Parts (candidates; nothing ordered)

Stock and price as of 2026-09-30 from the JLC parts API unless noted.

| Function | Part (what it is) | JLC | Status |
|---|---|---|---|
| MCU | **STM32L452CEU6**: 80 MHz Cortex-M4F with hardware PDM decoder (DFSDM), QFN-48 7×7 mm | C222355 · Extended · 16 in stock · $6.90 | **Chosen** (D5); buy early (R10) |
| Mic | **SPH0641LU4H-1**: digital MEMS mic with ultrasonic mode, 3.5×2.65 mm | C2879853 · Extended · 1,076 in stock · $1.99 | Lifecycle/backup check open (A2) |
| H-bridge | 2× complementary dual MOSFET (one N + one P per package), SOT-363 or smaller, fully on at 3.0–3.3 V gate drive | — | B1 |
| Charger | **MCP73831**: single-cell LiPo linear charger, SOT-23-5; charge current set by one resistor | C424093 (‑2ACI/OT) · Extended · 9,478 in stock · $0.78 | Check min charge current vs cell size (B3) |
| LDO | Low-noise linear regulator, 3.0 V (or 3.3 V), ≥400 mA peak, low dropout, low idle current | — | B2 |
| Transducer | RC-BC02 / GD02-class bone-conduction exciter, 8 Ω | not JLC; hand-soldered | Inductance unknown (E1) |
| Battery | 40–100 mAh LiPo with protection circuit | not JLC; hand-soldered | B4 |
| Preamp / ADC | Not needed (digital mic) | — | — |

---

## 10. Phase plan

### Phase 1: DSP simulation (Claude, no hardware) ← **current**
1. Test corpus: openly licensed full-spectrum recordings (≥192 kS/s) of bats and katydids, plus synthetic signals (steady 25 kHz whine, chirps, clicks, mixtures) (C1).
2. Front-end model: the mic's ultrasonic response (digitized from the datasheet) plus the DFSDM decimation options from D14.
3. Algorithms A and B plus the transient gate in Python (numpy/scipy); render WAVs for listening.
4. Output model: noise-shaped PWM → H-bridge → coil low-pass; plot noise in the 0–40 kHz band (§6, C3).
5. Cycle-cost estimate for each algorithm on the Cortex-M4F (C2).
6. **Exit:** algorithm and parameters chosen by the owner; an output-stage design shown on paper to be inaudible to her.

### Phase 1b: Hearing calibration
- Tone-sweep WAVs (C5) played on decent full-range headphones, not the Ear Opens. The result sets the D10 band floor.

### Phase 2: Bench prototype — **rewritten v0.4**
Built in four stages. S1 and S2 don't depend on Phase 1, so long-lead parts get ordered now and the stages run alongside the simulation.

| Stage | Build | Answers | Needs Phase 1? |
|---|---|---|---|
| **S1: Ears** | Mic breakout → DFSDM at 4.0 MHz → capture ~0.3 s bursts of raw 200 kS/s audio to RAM, then dump to PC | Whether the D14 clock plan works; the mic's real ultrasonic noise floor (R8, E3); **real recordings of the owner's house and yard to feed back into Phase 1** | No |
| **S2: Voice** | PWM → H-bridge → transducer, playing test tones and clips from flash | E1 (coil inductance), E2 (placement with Ear Opens on), R1 (loud enough?), **R9 (hiss or whine audible with PWM running at zero signal?)** | No |
| **S3: Brain** | S1 + S2 joined, with the chosen algorithm in real time | R3 (does B fit the CPU?), E4 (current per mode), latency | Yes |
| **S4: Stereo** | Two full units on a rough head mount (old glasses or a headband), wired, battery-powered | **Exit: T1, T2, T3, T6 pass** | Yes |

S2 matters most: it tests the three shakiest assumptions (PWM noise, loudness, placement) before any DSP exists.

**Bench rules:**
- **Listening tests run on battery.** Use a LiPo plus a linear-regulator module, never laptop USB. USB ground noise would mask or fake the T6 and R9 results.
- **Use NUCLEO-L452RE, not NUCLEO-L452RE-P.** The -P variant carries an onboard switching regulator (D11).

**Shopping list** (to price and verify before ordering):
- 2× **NUCLEO-L452RE**: ST's dev board with the same MCU as the final PCB, so CPU and current numbers carry over. It has an ST-LINK debugger built in. The ST eStore and DigiKey show it in stock (web search snippet 2026-09-30; confirm at order time).
- 5× **custom mic breakouts, JLC-assembled** (Claude designs them): SPH0641LU4H-1 plus decoupling capacitor, bottom-port hole, 0.1" header. These replace the unverified Elecrow breakout and prototype the final port-hole design.
- 3× **RC-BC02** transducers and 1× **Dayton BCE-1** for comparison. Likely long shipping, so **order first**.
- 2× **DRV8833 modules**: a small dual H-bridge motor-driver IC that runs from ~2.7 V. It gets sound out fast in S2. The discrete MOSFET bridge from D6 replaces it on the PCB.
- 2× small protected LiPo cells, plus 2× linear-regulator modules.
- Test sources: **HC-SR04** (a 40 kHz ultrasonic rangefinder module) as a steady emitter for T3; keys for jingle tests.
- Optional: 1× SPV0142LR5H-1 analog-mic breakout (E3 comparison only). Deprioritized now that the digital mic is JLC-stocked.
- Owner's existing kit: LCR meter (E1), PPK2 power profiler (E4).

**Split:**
- Claude: mic-breakout PCB, all firmware (D15), capture and analysis scripts, test procedures.
- Owner: ordering, wiring, all listening and wear tests.

### Phase 3: PCB
- Schematic checked against JLC stock → owner lays out in KiCad → Claude reviews and runs DRC, generates BOM and placement files → order assembled boards.

### Phase 4: Mechanical and integration
- 3D-printed clasps and drop-arms; iterate on fit. **Exit:** T1–T6 pass while worn.

---

## 11. Risks

| # | Risk | Likelihood | Resolved by |
|---|---|---|---|
| R1 | RC-BC02 too quiet at a few mA at the cheekbone site | `[Med]` | E2 |
| R2 | RC-BC02 inductance too low for filterless PWM | `[Low]` | E1; fix is one inductor |
| R3 | Algorithm B too heavy for 80 MHz at 200 kS/s | `[Med]` | C2, then Phase 2 profiling |
| ~~R4~~ | ~~No ultrasonic MEMS mic stocked at JLC~~ | **Resolved v0.3**: C2879853, 1,076 in stock | — |
| R5 | Bone-conduction stereo too weak for T3 | `[Med]` | Phase 2 |
| R6 | Drop-arm comfort (pressure, jaw movement) | `[Med]` | Phase 2 and 4 wear tests |
| R7 | L/R mismatch (mic sensitivity, transducer coupling) biases direction | `[Low]` | Per-side gain trim set at calibration |
| R8 | **Mic ultrasonic self-noise** too high for distant bats (not in datasheet) | `[Med]` | E3, outdoor test |
| **R9** | **PWM noise audible to the owner** (only ~4× oversampling against her hearing band, §6) | `[Med]` | C3 |
| **R10** | **MCU stock is thin** (16 at JLC) | `[Med]` | Buy or pre-order early; UFBGA fallback |
| **R11** | **Battery life under ~5 h on small cells** (§7) | `[Med]` | E4 measurements, B4 |

---

## 12. Research and task list

Status: `OPEN` · `IN PROGRESS` · `DONE` (with a pointer). Priority: **P1** blocks Phase 1 or the schematic · **P2** before board order · **P3** before final assembly.

### A. Architecture (P1)
| ID | Task | Status |
|---|---|---|
| A1 | Which MCU has DFSDM; pick one | **DONE**: `docs/research/A1-A2-mcu-and-mic.md`. L432 has none; **L452CEU6 chosen** (D5). |
| A2 | Mic lifecycle, stock, JLC path; backup ultrasonic mics | **IN PROGRESS**: JLC stock confirmed. Lifecycle and backup open. |
| A3 | Clock/sample-rate plan and DFSDM filter settings | **IN PROGRESS**: plan in D14. Verify the CKOUT duty cycle in RM0394; simulate filter options (i) vs (ii). |
| A4 | Transducer options: find inductance data; anything smaller or more efficient that's buyable in 1s | OPEN |

### B. Schematic parts (P2)
| ID | Task | Notes |
|---|---|---|
| B1 | H-bridge MOSFETs (or tiny H-bridge IC with ~0 idle current) | Must be fully on at 3.0 V gate drive; smallest JLC package. TIM1 complementary outputs with dead-time confirmed. |
| B2 | LDO | 3.0 vs 3.3 V rail (§7); ≥400 mA peak; low noise; low Iq |
| B3 | Charger | MCP73831 stocked (C424093). Check its minimum programmable charge current against a 40 mAh cell (≤1C). |
| B4 | Battery | 40–100 mAh protected LiPo; L×W×T, mass, sourcing. §7 favors ~100 mAh. |
| B5 | Button | Smallest tactile switch; JLC-assemblable preferred |
| B6 | Connectors | Magnetic 2-pin charge pogo; SWD footprint (Tag-Connect vs pogo pads); ESD protection on exposed contacts |
| B7 | Costing | BOM per side; JLC assembly cost for 2/5/10 boards |

### C. DSP and firmware (P1 for Phase 1)
| ID | Task | Status |
|---|---|---|
| C1 | Test corpus (licensed recordings + synthetic signals) | OPEN |
| C2 | Cycle cost of A vs B on the M4F (CMSIS-DSP benchmarks) | OPEN |
| C3 | Output-stage noise design (§6): modulation type, shaper order, drive scaling, filtering | OPEN; **now the biggest technical unknown** |
| C4 | Transient gate tuning on whine-plus-chirp mixtures | OPEN |
| C5 | Hearing-test sweep WAVs plus procedure | OPEN |
| C6 | Local bat call frequencies from the literature | OPEN |
| C7 | Transducer response above 20 kHz (bone-conducted ultrasound leakage) | OPEN |

### D. Mechanical and materials (P3)
| ID | Task |
|---|---|
| D1 | Nitinol wire, skin-safe silicone, JLC PA12 nylon print rules |
| D2 | Acoustic mesh that passes 20–80 kHz and keeps out dust and sweat |
| D3 | Skin-contact insulation method for the transducer |

### E. Owner bench measurements (Claude writes procedures and analyzes results)
| ID | Measurement | Resolves |
|---|---|---|
| E1 | Transducer coil inductance (LCR meter) | R2, C3 |
| E2 | Placement: cheekbone arch root vs temple, with Ear Opens playing; talk and chew | R1, R6 |
| E3 | Mic comparison, digital vs analog; ultrasonic noise floor | D13, R8 |
| E4 | Current per mode (PPK2) | §7, R11 |
| E5 | Hearing sweep with the C5 files | D10 |

**Suggested order:** order long-lead bench parts (transducers, Nucleos) → design mic breakout → C1 → A3/C3 simulation → C2 → A2 finish → A4 → B-series → D-series. E-series whenever hardware arrives.

---

## 13. Program context (not in scope)
- **Northsense:** torso band, 8 LRA motors plus IMU giving a constant north cue. Next project.
- **Blindspot Proximity:** parked (hair blocks rear sensors on glasses); may reuse the Northsense torso hardware.
- **Program principles:** continuous signals rather than alerts; direction mapped to body location; adaptive normalization only where it doesn't destroy the cue (not here, D3); quiet by default; comfort first; one new sense at a time.

---

## 14. Glossary
- **PDM (pulse-density modulation):** a 1-bit stream at MHz rates where the density of 1s tracks the signal. MEMS mics output it; it has to be filtered and decimated to get normal samples.
- **DFSDM:** the STM32 hardware block that does that PDM-to-PCM filtering.
- **Decimation:** lowering the sample rate after filtering out content that wouldn't fit.
- **Heterodyne:** shifting frequencies down by multiplying by a tone, then filtering. You hear one band at a time.
- **Log frequency compression:** squeezing a wide frequency range into a narrow one on a log scale, so each octave keeps its share (hearing aids use this).
- **Squelch:** muting output below a threshold.
- **Noise shaping:** feedback in the quantizer that pushes rounding noise out of the band you care about into a band where it's filtered or inaudible.
- **Oversampling ratio:** how much faster the converter runs than twice the band it must keep clean. Higher means more room to push noise away.
- **Interaural level difference:** the loudness difference between your ears; the main cue for locating high-frequency sounds.
- **3-level (class-BD) PWM:** H-bridge modulation where both legs switch so the load sees +V, 0, or −V. Zero drive at idle, and ripple at twice the switching rate.

---

## 15. Changelog

### v0.4 (2026-09-30)
- §1 MVP confirmed by owner.
- **D5 decided:** STM32L452CEU6.
- **D15 new:** firmware toolchain (bare C, CMake, CMSIS + LL, CMSIS-DSP), decided by Claude at the owner's request.
- **§10 Phase 2 rewritten:** staged bench plan (S1–S4); NUCLEO-L452RE replaces L476RG; custom JLC mic breakout replaces the unverified Elecrow part; DRV8833 module for early output tests; battery-only listening rule.
- §8: PCB size estimate (~10×20 mm double-sided, ~10×28 mm single-sided).

### v0.3 (2026-09-30)
- **§1 MVP section created and locked** (goal, owner constraints, success tests carried over unchanged in substance from v0.2 §1, §2, §4).
- **D5 MCU changed: STM32L432KC → STM32L452CEU6.** The L432 has no DFSDM (verified in the datasheet). Pending owner OK.
- **D13 mic:** JLC stock confirmed (C2879853); datasheet firmware rules recorded; R4 resolved.
- **D14 new:** clock plan, 4.0 MHz mic clock, 200 kS/s (replaces 192 kS/s).
- **§6 new:** v0.2's 60× oversampling claim corrected to ~4× against the owner's hearing band. Output-noise design is now the top technical risk (R9, C3).
- **§7:** power re-estimated from datasheet run currents (~7–14 mA vs 5–16 mA); battery recommendation raised toward ~100 mAh; 3.0 V rail proposed.
- Removed stale analog-chain items (preamp current, preamp/ADC noise in R8).
- Added R9–R11. Research findings moved into `docs/research/`.

### v0.2
- Design-chat handoff (original document).
