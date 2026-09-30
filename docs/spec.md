# Stereo Ultrasound — Project Spec v0.2

**Owner:** Valkyrie
**Status:** Architecture decided. Next phase: DSP simulation plus parts research (no hardware purchased yet).
**Purpose of this document:** Handoff from design chat to a Claude Code implementation session. Records requirements, decisions *with reasoning*, rejected alternatives, and open questions with confidence levels. Treat decisions as settled unless new evidence contradicts the stated reasoning.

**Confidence tags:** `[High]` well-established / verified · `[Med]` reasoned estimate, likely right · `[Low]` guess, verify before relying on it.

---

## 0. Instructions for Claude Code (read first)

**Your job:** own the research and implementation. The owner has microcontroller experience but does **not** want to decode part numbers or trawl distributor catalogs. That's your work. §15 lists every open research task; work through them in priority order.

**Standing rules:**
1. **Always gloss part numbers.** Every time you name a part, say what it is and why it's there in plain language (e.g. "TLV75533 — a 3.3 V linear regulator, 500 mA, very low noise"). Never present a bare part number.
2. **Verify from primary sources.** Datasheets and manufacturer pages for specs; distributor pages (DigiKey, Mouser, LCSC/JLCPCB) for stock and price. Record the source and date for every stock or price claim; stock changes daily.
3. **Prefer JLCPCB-assemblable parts.** Check whether each part is a JLC "Basic" part (no setup fee), "Extended" (small fee), or needs global sourcing or consignment. Report which.
4. **Present decisions as 2–3 clear options with tradeoffs**, then give your recommendation. The owner picks. Don't finalize a part without approval.
5. **Update this spec** as decisions land: change the decision log, parts table, and task status, and bump the version.
6. **Teach as you go.** The owner is self-taught and wants to learn the why (DSP, PDM, noise shaping, power design). Brief explanations, no condescension.
7. **Be blunt about problems.** If a decision in this spec turns out wrong, say so and propose the fix.
8. **Constraint checklist for every part choice:** smallest practical package that JLC can assemble · lowest power · no switching regulators (owner hears coil whine) · stocked or sourceable.

---

## 1. Goal

A wearable that lets the owner hear ultrasound (roughly 20–96 kHz) in real time, in stereo, by shifting it down into a comfortable audible band and delivering it by bone conduction. It mounts on her everyday prescription glasses and must feel like an extension of her body, not a gadget.

Part of a larger sensory-augmentation program (see §13). This is project 1 of 3.

## 2. Owner constraints (non-negotiable)

1. **Full-time glasses wearer.** The device clips onto her main glasses via removable 3D-printed clasps.
2. **Nothing Ear (open) headphones are worn constantly and are reserved exclusively for phone audio.** The device must not use them as output, must not physically interfere with their fit, and must not bump the driver pod, which sits over the ear opening between the helix root and tragus and shifts slightly during wear. The counterweight bulb sits behind the ear.
3. **Unusually good high-frequency hearing.** She already hears some charger and LED-driver whine. Consequences: no audible self-noise, no switching regulators, and PWM noise kept well above her hearing (§7.4).
4. **Comfort and size are the top priority.** If it's bulky or uncomfortable it won't get worn, and the project fails. Bulk goes at the front of the frame near the hinges, never near the neck or behind the ears.

## 3. Priorities (ranked)

1. Comfort, size, and weight
2. Power draw (as low as practical)
3. Circuit simplicity and part count
4. Cost
5. Sound pleasantness (a close 5th; drives the choice of digital DSP over analog)

## 4. Success criteria (behavior tests)

- **T1 House walk:** walking around the house, she hears ultrasonic sources (electronics, etc.). In Transient-only mode, the house is tolerable rather than overwhelming.
- **T2 Nature sit:** sitting outside at dusk, she hears bats and other ultrasonic wildlife as comfortable, non-shrill sound. Reference point: pitched-down bat recordings in online demos (noting those are usually *time-expanded*, which can't be done in real time; see D4).
- **T3 Localization:** eyes closed, she can point left or right toward an ultrasonic source (for example a 40 kHz rangefinder emitter) better than chance.
- **T4 Coexistence:** Ear Opens are worn and playing phone audio the whole time, with no fit interference and both audio streams distinguishable.
- **T5 Wearability:** worn for 2+ hours with no pressure pain at the transducer site or temples, including while talking and eating.
- **T6 Silence:** with no ultrasound present, the device is inaudible to her. No hiss, no whine.

---

## 5. Decision log

### D1. Output = bone conduction on the root of the cheekbone arch, in front of the ear `[High]`
- **Site:** the root of the zygomatic arch, about 1 finger-width *above* the mandibular condyle (jaw joint), about 1–1.5 cm forward of the tragus.
- **Why this site:** bone is close to the surface with little soft tissue, near the cochlea, and it's the site commercial bone-conduction headsets use. Placing it above the condyle avoids contact shifting when the jaw opens.
- **Rejected:**
  - *Stream to Ear Opens over Bluetooth:* violates constraint 2.
  - *Temple (squamous temporal bone):* the temporalis muscle damps vibration, I estimate 5–10 dB worse `[Low]` on the exact figure. It's also a common spot for glasses-pressure headaches.
  - *Air-conduction microspeaker aimed at the ear canal:* the Ear Open pod occupies the path over the ear opening.
  - *Mastoid:* crowded by the Ear Open hook and counterweight.

### D2. Two independent mono units, no link between them `[High]`
- Each side has its own mic, MCU, driver, battery, and transducer.
- **Why:** stereo localization at these frequencies relies on the loudness difference between ears, and the head strongly shadows ultrasound (wavelength under 1 cm). Each side processing its own mic preserves that difference naturally. This eliminates wiring across the hinges, the biggest mechanical failure risk, and halves the size of each clasp.
- **Accepted cost:** two MCUs and two batteries, and no shared settings between sides.

### D3. Fixed gain plus manual volume; no automatic gain control `[High]`
- **Why:** independent automatic gain would normalize each side separately and erase the loudness difference between them, which destroys localization.
- **Requirement:** volume uses discrete, indexed steps and **resets to a known default at power-on**, so both sides start matched. Same for mode.

### D4. Digital DSP, not analog frequency division `[High]`
- Analog frequency division (comparator plus counter) sounds harsh and buzzy and loses loudness information. It fails the pleasantness requirement, and it would save only about 3 mA, since the preamp and transducer draw the same either way.
- Time expansion (what most demo videos use) is impossible in real time. The real-time options are heterodyne and spectral pitch or frequency compression (§7).

### D5. MCU = STM32L432KC (QFN-32, 5×5 mm) `[Med]`
- Cortex-M4F at 80 MHz with DSP instructions, a low-power family, and a fast on-chip 12-bit ADC (samples the ultrasonic signal directly, so no external ADC). Hand-solderable in principle, but will be factory-assembled (D8).
- **Rejected:** ESP32 variants (the radio isn't needed and they draw more power); RP2040 (higher active current and no fast ADC with good analog performance for this use `[Med]`); Ambiq Apollo (excellent efficiency but hard-to-assemble packages, reconsider only for a future revision).
- **Verify:** ADC performance at ≥192 kS/s single-channel with DMA; JLCPCB stock.

### D6. Output stage = filterless firmware PWM driving an H-bridge; no amplifier IC `[Med]`
- MCU timer PWM at roughly 312.5 kHz (80 MHz / 256, so 8-bit resolution) drives a small H-bridge made from complementary MOSFETs, which drives the transducer directly.
- **Why it works:** the transducer coil's inductance plus its resistance forms a low-pass filter. The output band is narrow and low (under 5 kHz), so the effective oversampling ratio is about 60× and noise shaping recovers good in-band resolution from 8-bit PWM.
- **Removes:** the amplifier IC, its quiescent current, and the DAC.
- **Risk:** the RC-BC02's inductance is not on its datasheet. If it's too low, add a small series inductor (one 0805-size part). Measure it with an LCR meter.
- **Squelch implementation:** stop the PWM and hold both bridge legs at the same level, so zero current flows.

### D7. Transducer = RC-BC02 / "GD02"-class module `[Med]`
- 12.6 × 6 × 4 mm, 8 Ω, 0.3 W nominal, 300–19,000 Hz, rated 88 dB at 1 kHz.
- The smallest off-the-shelf part with a datasheet found so far. Smaller parts appear to be OEM-only in the hearing-aid supply chain `[Med]`.
- 8 Ω draws about half the current of 4 Ω parts at the same drive voltage.
- **Known weakness:** a DIY glasses build using this module reported it was quiet. That's acceptable, even preferred, and mitigated by D1's site choice and D9's output band.
- **Bench comparison part:** Dayton BCE-1 (21 × 14 × 7.8 mm, 4 Ω, resonance 2.1 kHz).

### D8. Factory PCB assembly (JLCPCB) `[High]`
- All SMD parts are machine-placed. The owner hand-solders only the transducer leads, battery, and optionally the button.
- **Hard constraint:** MEMS microphones are land-grid parts that must be reflowed and can't be hand-soldered, so **the mic must be available through JLCPCB's parts service.** Check this before designing the schematic.

### D9. Output band ≈ 1.5–4 kHz `[Med]`
- **Why:** it matches the ear's peak sensitivity region (about 2–4 kHz) and sits near typical bone-transducer resonance, giving the most perceived loudness per milliwatt. That serves the power, size, and pleasantness priorities together.
- Final limits are set by listening tests in Phase 1.

### D10. Band floor calibrated to the owner's hearing `[High]` as a principle
- Measure her upper hearing limit with a tone sweep. Start the processed band slightly below that limit, not at a fixed 20 kHz, so there's no gap and no doubled sounds.
- Stored as a firmware constant (per side, but it should be identical on both).

### D11. Linear regulator only; no switch-mode supplies anywhere `[High]`
- Switching regulators produce audible inductor whine, the exact artifact the owner already hears from chargers.

### D12. Modes `[High]` as requirements
- **Full:** everything in the band, pitched down.
- **Transient-only:** steady tones (charger and LED-driver whine) suppressed; changing sounds (chirps, clicks, rustles) passed through. The expected default indoors.
- **Off:** silent, with the MCU in a low-power state.
- The processing algorithm (heterodyne vs. log compression) may be a sub-mode or a build-time choice. Decide after Phase 1 listening.

### D13. Mic = purpose-built digital ultrasonic MEMS (Syntiant/Knowles SPH0641LU4H-1) `[Med]`
- PDM output with a dedicated **ultrasonic mode** (clock 3.072–4.8 MHz), rated 100 Hz–80 kHz, with a published ultrasonic response curve, 3.50 × 2.65 mm, bottom port, ±1 dB sensitivity matching.
- **Why:** (1) its ultrasonic performance is specified, not inferred; (2) **noise immunity**: a 40 dB analog preamp sitting millimeters from a ~300 kHz H-bridge switching hundreds of mA is the analog design's biggest hidden risk, and a digital bitstream largely eliminates it; (3) fewer parts (no preamp, bias network, or ADC); (4) tight sensitivity matching helps the two independent units stay balanced (R7).
- **Costs:** the MCU needs a DFSDM peripheral (hardware PDM decoding) or a software decoder; mode-sequencing rule (**the datasheet says: don't power up or wake directly into ultrasonic mode**; start in standard mode, then raise the clock); about 1 mA supply, roughly the same as the analog chain it replaces.
- **Verify:** lifecycle (DigiKey lists it as Active; one distributor lists "Not For New Designs"); LCSC/JLC stock or global sourcing.
- **Rejected:** analog SPV0142LR5H-1. Its ultrasonic response isn't in the rated spec, and it needs a noise-sensitive analog front end. Kept as a fallback only.

### Parked or rejected ideas (for context)
- **Forward "gaze distance" sensing:** redundant with stereo vision, so it adds no new information.
- **Haptic channel for above 60 kHz:** optional future layer. Note that anything vibrating on the head is also *heard* through bone conduction, so it wouldn't be pure touch. Local nature above about 60 kHz is sparse; that band is mostly electronics and rodent repellers.
- **Blindspot Proximity (sensors on the glasses):** parked. The owner has long hair, which blocks rear-facing time-of-flight sensors at the temple tips.

---

## 6. Architecture (per side)

```
[SPH0641LU4H-1 PDM mic, ultrasonic mode, clock 3.072–4.8 MHz]
      → [MCU DFSDM (hardware PDM filter) → ≥192 kS/s PCM, DMA]
      → [DSP: band select → shift/compress → squelch/transient gate → volume]
      → [Noise-shaped PWM ~312 kHz] → [H-bridge, 2× complementary MOSFET pairs]
      → [RC-BC02 transducer]

Power: [LiPo w/ protection] → [MCP73831 charger] → [low-noise LDO 3.3 V, ≥300 mA] → all
Controls: 1 button (mode / volume), SWD pads for programming
```

**Why digital (D13):** the mic outputs a digital bitstream, so there's no analog signal for the nearby H-bridge switching to corrupt, and no preamp, bias network, or ADC to build. Audible-band content is removed by a digital high-pass filter after decimation.

## 7. DSP specification

### 7.1 Sampling
- Single channel per unit at 192 kS/s baseline (Nyquist 96 kHz) `[Med]`. The mic response probably rolls off around 60–80 kHz anyway. Could go to 250 kS/s if the mic supports it.
- Local bats (big brown and eastern red, common in the region) call roughly 25–50 kHz `[Med]`, well inside the band.

### 7.2 Algorithms (implement both in simulation; choose after listening)
- **A. Digital heterodyne (low CPU):** multiply by a local oscillator, low-pass, decimate. Clean tonal output but only a band of limited width at a time; the oscillator frequency is tunable. Estimated CPU need: low tens of MHz.
- **B. Short-time FFT log frequency compression (the "pretty" mode):** map 20–96 kHz onto about 1.5–4 kHz on a logarithmic scale, with overlap-add resynthesis. Keeps timing and relative loudness across the whole band. Estimated about 60–120 MHz-equivalent of work `[Low]`. **This must be profiled; it may not fit 80 MHz at 192 kS/s**, in which case reduce the FFT size or overlap, or sample at a lower rate.
- **Transient-only gate:** in B, subtract each frequency bin's slowly updated noise floor (spectral subtraction), which kills steady tones. In A, use an envelope-based squelch with a slowly updated floor.

### 7.3 Latency
- Target ≤20 ms end-to-end so the sound tracks head turns naturally `[Med]` on the threshold. An STFT frame at 512 points and 192 kHz is about 2.7 ms, so there's plenty of room.

### 7.4 PWM noise shaping (owner-specific requirement)
- Quantization noise must be **inaudible to the owner at max volume.** Shaped noise must not land in the audible range up to roughly 20 kHz (and ideally stays below threshold up to 40 kHz), with bone-conducted ultrasound perception as an extra caution.
- **Verify in simulation:** compute the shaped noise spectrum through the transducer's electrical low-pass (coil inductance and resistance). Choose noise-shaper order and PWM resolution accordingly (9-bit at ~156 kHz is a fallback option).

### 7.5 Controls
- One button: short press cycles modes; press-and-hold ramps volume through discrete steps. Both reset to defaults at power-on (D3).

## 8. Physical layout (per side)

- **Front clasp, just behind the hinge on the temple arm:** PCB (about 10×20 mm `[Med]`) with the mic facing outward, plus battery and button. Most ultrasonic MEMS mics have their sound port on the bottom, so the **PCB needs a port hole and the clasp needs an outward-facing acoustic opening covered by thin mesh** (thick foam absorbs ultrasound).
- **Along the temple arm:** thin 2-conductor lead to the transducer.
- **Drop-arm near the ear:** a short spring arm hanging 1–2 cm below the temple arm, pressing the transducer onto the cheekbone arch root with light, even force through a broad pad. Must keep ≥1–1.5 cm clearance from the tragus and the Ear Open pod through head turns and facial movement.
- **Electrical isolation from skin:** the transducer's metal parts and solder joints must be fully insulated (silicone pad plus sealed housing). Sweat can otherwise conduct drive current through the skin.
- **Programming:** SWD pogo pads. **Charging:** magnetic pogo connector plus nightly dock.
- **Weight target:** under about 8 g per side total `[Low]`. Glasses start hurting at roughly 15 g per side added.

## 9. Candidate parts (verify stock at JLCPCB before schematic)

| Function | Candidate | Confidence | Verify |
|---|---|---|---|
| MCU | STM32 with **DFSDM**. Check first: does STM32L432KC/L442KC (QFN-32, 5×5 mm) have DFSDM? ST's own listings are inconsistent. Confirmed fallback: STM32L452CE (UFQFPN-48, 7×7 mm) | `[Med]` | DFSDM presence in the datasheet; JLC stock |
| Mic | **Syntiant SPH0641LU4H-1** (PDM, ultrasonic mode, 3.50 × 2.65 mm) — see D13. Fallback: SPV0142LR5H-1 analog | `[Med]` | Lifecycle; LCSC/JLC stock or global sourcing |
| Preamp | Not needed with the digital mic (TLV9061 only if falling back to analog) | `[High]` | — |
| H-bridge | 2× complementary dual MOSFET, SOT-363 or similar, logic-level at 3.3 V | `[Med]` | On-resistance, gate threshold |
| Charger | MCP73831 (SOT-23-5) | `[High]` | — |
| LDO | Low-noise 3.3 V, ≥300 mA | `[Med]` | Current headroom for transducer peaks |
| Transducer | RC-BC02 / GD02 class | `[Med]` | Measure coil inductance |
| Battery | 30–100 mAh LiPo with protection circuit | `[Med]` | Fit in clasp; choose after Phase 2 current measurements |

H-bridge supply: the 3.3 V rail, with firmware capping maximum duty cycle to limit peak current. That's fine at the intended quiet listening levels `[Med]`.

## 10. Power budget (per side, estimates)

| Block | Current |
|---|---|
| MEMS mic | ~0.15 mA |
| Preamp | ~0.5 mA |
| MCU, algorithm A | ~2–3 mA |
| MCU, algorithm B | ~8–10 mA `[Low]` |
| Transducer, average at listening level | ~2–5 mA; about 0 when squelched |
| **Total** | **~5–8 mA (A), ~12–16 mA (B)** `[Low]` |

About 3–8 hours on 40 mAh, roughly double on 100 mAh. **Power levers, most effective first:** squelch, output band placement (D9), algorithm choice.

## 11. Phase plan

### Phase 1: DSP simulation (Claude Code, no hardware) ← START HERE
1. Find openly licensed full-spectrum bat and insect recordings (sample rate ≥192 kHz). Also generate synthetic test signals: steady 25 kHz "charger whine", chirps, and clicks.
2. Implement algorithms A and B plus the transient-only gate in Python (numpy/scipy).
3. Render WAV files for listening. The owner picks the algorithm, band limits (D9), and gate behavior.
4. Model 8-bit noise-shaped PWM through a coil low-pass filter (placeholder inductance of about 0.3 mH for 8 Ω, updated once measured) and plot the audible-band noise (§7.4).
5. Estimate processing cost per sample for each algorithm against the L432's 80 MHz budget.
6. **Exit:** chosen algorithm and parameters; noise-shaping design shown to be inaudible on paper.

### Phase 1b: Hearing calibration
- Tone sweep to find the owner's upper hearing limit, which sets the band floor (D10). Use decent full-range headphones, not the Ear Opens, which may roll off at the top.

### Phase 2: Bench hardware (in parallel once parts arrive)
- Order: 2× RC-BC02, 1× Dayton BCE-1, **NUCLEO-L476RG** (DFSDM confirmed; Elecrow publishes an SPH0641 example for it), **Elecrow SPH0641LU4H-1 digital mic breakout** ×2, MOSFETs, plus one analog SPV0142 breakout as a comparison.
- Measure the RC-BC02's coil inductance.
- Placement test: exciter on the cheekbone arch root vs. the temple, while wearing Ear Opens playing phone audio; talk and chew; check clearance.
- Port the chosen DSP to firmware. Measure CPU load and current per mode.
- **Exit:** T1, T2, T3, and T6 pass on the bench rig (wired, not wearable yet).

### Phase 3: PCB
- Schematic (checked against JLC stock), then the owner does layout in KiCad, then Claude reviews layout, runs design-rule checks, and generates BOM and placement files, then order assembled boards.

### Phase 4: Mechanical and integration
- 3D-print clasps and drop-arms, iterating on fit.
- **Exit:** all of T1–T6 pass while worn.

## 12. Open questions and risks

| # | Question / risk | Confidence it's a real problem | Resolved by |
|---|---|---|---|
| R1 | RC-BC02 too quiet at a few mA at the cheekbone site | `[Med]` | Phase 2 placement test |
| R2 | RC-BC02 inductance too low for filterless PWM | `[Low]` | LCR measurement; fix is one inductor |
| R3 | Algorithm B too heavy for 80 MHz at 192 kS/s | `[Med]` | Phase 1 cost estimate, Phase 2 profiling |
| R4 | No suitable ultrasonic MEMS mic stocked at JLC | `[Med]` | Parts check before schematic |
| R5 | Bone-conduction stereo too weak for T3 | `[Med]` | Phase 2 test; weak left/right is partly inherent |
| R6 | Drop-arm contact comfort (pressure, jaw movement) | `[Med]` | Phase 2 and 4 wear tests |
| R7 | Small mismatches between sides (mic sensitivity, transducer coupling) bias perceived direction | `[Low]` | Per-side gain trim constant set at calibration |
| R8 | Preamp or ADC noise floor too high for distant bats | `[Med]` | Phase 2 outdoor test |

## 13. Program context (other projects, not in scope here)

- **Northsense:** torso band with 8 LRA motors plus IMU providing a constant north cue. Next project.
- **Blindspot Proximity:** parked (hair blocks rear sensors on the glasses). The torso band hardware from Northsense would be reused if it's revived with a different sensor placement.
- **Design principles for the whole program:** continuous rather than alert-style signals; direction mapped to body location; adaptive normalization only where it doesn't destroy the cue (not here, per D3); quiet by default; comfort first; add senses one at a time.

## 14. Glossary

- **Heterodyne:** shifting frequencies down by multiplying the signal with a tone, then filtering. Hears one band at a time.
- **Log frequency compression:** squeezing a wide frequency range into a narrow one on a logarithmic scale, so every octave keeps a proportional share of the output. Hearing aids use this.
- **Squelch:** muting output when the signal is below a threshold.
- **Noise shaping:** feedback in the quantizer that pushes rounding noise out of the band you care about and into frequencies you can't hear, where it gets filtered.
- **Oversampling ratio:** how many times faster the PWM runs than the audio band needs; more oversampling means more room to push noise out of the way.
- **Interaural level difference:** the loudness difference between your two ears, the main cue for locating high-frequency sounds.

---

## 15. Research task list (for Claude Code)

Status key: `OPEN` · `IN PROGRESS` · `DONE` (with a pointer to the result). Priority: **P1** blocks the schematic or Phase 1 · **P2** needed before board order · **P3** needed before final assembly.

For every task, the output is a short written finding: sources with dates, 2–3 options with tradeoffs, a recommendation, and the confidence level. Part numbers always come with plain-language descriptions (§0 rule 1).

### A. Blocking architecture questions (P1)

| ID | Task | Why it matters | Output |
|---|---|---|---|
| A1 | **Does the STM32L432KC or STM32L442KC have a DFSDM peripheral?** Check the datasheet's feature list and block diagram, not marketing blurbs (ST's product listings contradict each other). If neither does, compare: (a) STM32L452CC/CE in UFQFPN-48 7×7 mm (DFSDM confirmed), (b) software PDM decoding via SPI and DMA on the L432 (estimate CPU load and current), (c) any other low-power MCU with hardware PDM decoding that fits a ≤7×7 mm package. | Decides the MCU and board size. | MCU recommendation plus DFSDM evidence |
| A2 | **Mic sourcing.** SPH0641LU4H-1: lifecycle status (DigiKey says Active; one distributor says "Not For New Designs"), stock at DigiKey, Mouser, and LCSC, and the JLC path (Basic, Extended, global sourcing, or consignment). Also survey newer purpose-built ultrasonic digital MEMS mics (Syntiant's selection guide covers ultrasonic parts; check TDK, Infineon, and others). | The whole input chain depends on it. | Primary plus backup mic, with evidence |
| A3 | **Clock and sample-rate plan.** The mic's ultrasonic mode needs a 3.072–4.8 MHz clock. Find a clock the MCU can generate from its system clock that divides cleanly down to an output sample rate of about 192–250 kS/s. Specify the DFSDM filter settings (sinc order, decimation ratio) plus any CPU cleanup filter. Pull the ultrasonic-mode noise floor and response curve from the datasheet. | A mismatched clock plan means awkward sample rates or no ultrasonic mode. | Clock tree, sample rate, filter configuration |
| A4 | **Transducer options.** Find a datasheet with coil inductance for RC-BC02/GD02-class modules (needed for the filterless PWM design, D6). Search for anything smaller or more efficient that's purchasable in single quantities. List current, buyable listings with stated dimensions. | Sets output efficiency, size, and whether an extra inductor is needed. | 2–3 buyable options with specs |

### B. Parts selection for the schematic (P2)

| ID | Task | Constraints |
|---|---|---|
| B1 | **H-bridge switches.** Complementary MOSFET pairs, or a tiny H-bridge IC with near-zero idle current. Must switch fully with 3.3 V gate drive and have low resistance at that voltage. Confirm the chosen MCU has an advanced timer with complementary outputs and dead-time insertion for driving the bridge. | Smallest package JLC assembles; idle current ≈ 0 |
| B2 | **Linear regulator (LDO).** 3.3 V, low noise, ≥300 mA, low idle current, low dropout so the LiPo is usable down to about 3.4 V. | No switching regulators, ever (constraint 3) |
| B3 | **LiPo charger.** MCP73831 or better; check JLC stock; set charge current to ≤1C for 30–100 mAh cells. | Small package; silent operation |
| B4 | **Battery.** LiPo cells with built-in protection, 30–100 mAh. List candidates with L×W×T dimensions, mass, and sourcing. | Must fit the front clasp; mass budget §8 |
| B5 | **Button.** Smallest tactile switch suitable for a glasses clasp (side- or top-actuated). | JLC assemblable preferred |
| B6 | **Connectors.** 2-pin magnetic pogo connector for charging; SWD programming footprint (Tag-Connect vs. plain pogo pads); ESD protection on exposed contacts. | Tiny; exposed contacts must survive sweat |
| B7 | **Costing.** Full BOM cost per side, plus JLC assembly cost for 2, 5, and 10 boards. | — |

### C. DSP and firmware research (P1 for Phase 1)

| ID | Task | Output |
|---|---|---|
| C1 | **Test recordings.** Find openly licensed full-spectrum recordings (sample rate ≥192 kHz) of regionally relevant species: big brown bat, eastern red bat, katydids. Record the license terms. Generate synthetic test signals too (steady 25 kHz whine, chirps, clicks, mixtures). | Test corpus plus license notes |
| C2 | **Algorithm cost.** Estimate cycles per sample for heterodyne vs. STFT log compression on a Cortex-M4F (use CMSIS-DSP benchmarks where available). | Does algorithm B fit the MCU budget? (R3) |
| C3 | **Noise-shaping design.** PWM resolution and frequency options on the chosen MCU's timers; noise-shaper design; model the audible-band noise through the transducer coil (§7.4). | Parameters that keep noise inaudible to the owner |
| C4 | **Transient-only gate.** Spectral subtraction parameters; evaluate on a whine-plus-chirp mixture. | Tuned parameters plus listening WAVs |
| C5 | **Hearing test files.** Generate calibrated sweep WAVs for the owner's upper-limit test (D10), with instructions. | WAV files plus procedure |
| C6 | **Local bat frequencies.** Verify call frequency ranges for local bat species from the literature. | Band limits sanity check |
| C7 | **Transducer ultrasonic leakage.** Quantify the RC-BC02's response above 20 kHz from datasheet or literature, relevant to bone-conducted ultrasound perception (§7.4). | Is extra output filtering needed? |

### D. Mechanical and materials sourcing (P3)

| ID | Task | Output |
|---|---|---|
| D1 | **Materials.** Superelastic nitinol wire (diameter options, suppliers); skin-safe silicone sheet (thickness, hardness); JLC PA12 nylon printing rules (minimum wall, tolerances, cost). | Sourcing list |
| D2 | **Acoustic mesh for the mic opening.** Must pass 20–80 kHz with little loss, keep out dust and sweat. Check attenuation data for hydrophobic acoustic vents and membranes; many are specified only for voice frequencies. | Mesh part or design rule |
| D3 | **Skin-contact insulation.** Approach for sealing the transducer and solder joints (silicone pad plus potting or conformal coat); materials that are skin-safe for all-day wear. | Build method |

### E. Owner bench measurements (Claude Code supports with procedures and analysis)

| ID | Measurement | Resolves |
|---|---|---|
| E1 | RC-BC02 coil inductance with an LCR meter | R2 |
| E2 | Placement test: cheekbone arch root vs. temple, with Ear Opens playing; talk and chew | R1, R6 |
| E3 | Mic comparison: SPH0641 (digital) vs. SPV0142 (analog), using the HC-SR04, keys, and outdoor recordings | Validates D13 |
| E4 | Current profiling per mode with the PPK2 | §10 power budget |
| E5 | Hearing sweep with the C5 files | D10 band floor |

**Suggested order:** A1 → A2 → A3 (in parallel with C1 → C2 for Phase 1) → A4 → B-series → C3/C4 → D-series. E-series tasks run whenever hardware arrives.
