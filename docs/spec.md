# Stereo Ultrasound — Project Spec v0.14

**Owner:** Valkyrie
**Status:** Concept phase. §1 MVP confirmed by owner 2026-09-30. MCU (D5) and firmware toolchain (D15) decided. v0.5 applies the full-plan sanity check (`docs/research/review-2026-09-30.md`). Next: shopping-list approval (O3) → Phase 1 simulation and first bench orders. No hardware purchased.
**Last updated:** 2026-09-30 (Claude Code session). See §15 for the changelog.

**Confidence tags:** `[High]` verified from a primary source or well established · `[Med]` reasoned estimate, likely right · `[Low]` guess, verify before relying on it.

**Everything below §1 may be revised as evidence comes in. §1 is locked.**

---

## 0. Working rules (for Claude)

1. **§1 (MVP) is owner-locked.** Never change it. If evidence says part of it can't be met, say so bluntly and propose options, but leave the text alone.
2. **Gloss every part number** in plain language on first mention in any document or message: what it is, and why it's there.
3. **Primary sources.** Datasheets for specs; distributor or JLC listings for stock and price, always with the query date. Findings go in `docs/research/`, one file per task, and get summarized here. Numeric models live in `sim/` and are cited by script name.
4. **Decisions as 2–3 options with tradeoffs plus a recommendation.** The owner picks. Nothing is final without her approval.
5. **Part-choice checklist:** smallest package JLC can assemble · lowest power · **switching regulators only as allowed by D11** · in stock or sourceable. JLC "Basic" parts carry no setup fee, "Extended" parts carry a small one; say which.
6. **Teach the why** (DSP, PDM, noise shaping, power design), briefly and without condescension.
7. **Be blunt.** If something in this spec is wrong, flag it, fix it here, bump the version, and log it in §15.
8. **Show, don't just tell.** The owner is a visual learner. When a mechanism, layout, flow or comparison is involved, draw it: author the SVG in `docs/diagrams/`, render it with `docs/diagrams/render.sh`, and send the **PNG** into the chat, where it displays inline (SVG files only appear as file cards). Label the arrows; one figure, one claim.

---

## 1. MVP — LOCKED (owner-defined; do not modify)

### 1.1 Goal
A wearable that lets the owner hear ultrasound (roughly 20–96 kHz) in real time, in stereo, by shifting it down into a comfortable audible band and delivering it by bone conduction. It mounts on her everyday prescription glasses and must feel like an extension of her body, not a gadget.

### 1.2 Owner constraints
1. **Full-time glasses wearer.** The device clips onto her main glasses via removable 3D-printed clasps.
2. **Nothing Ear (open) headphones are worn constantly and reserved for phone audio.** The device must not use them as output, must not interfere with their fit, and must not bump the driver pod (over the ear opening, between helix root and tragus; shifts slightly during wear). The counterweight bulb sits behind the ear.
3. **Unusually good high-frequency hearing** (hears some charger and LED-driver whine). So: any self-noise must be no louder than the ambient background, and PWM noise is kept well above her hearing. *(Owner change 2026-09-30: the blanket "no switching regulators" rule was removed.)*
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
                     32.768 kHz crystal ─▶ MSI (auto-trimmed) ─▶ PLL ─▶ 48–80 MHz per mode (D14) — every clock below derives from this
SPH0641LU4H-1 mic ◀── 4.0 MHz clock (SYSCLK ÷ 12…20) ──┐
      │ PDM 1-bit                                   │
      ▼                                             │
STM32L452 DFSDM (hardware PDM→PCM, sinc5 ÷10) ──────┘ 400 kS/s ──▶ half-band FIR ÷2 ──▶ 200 kS/s
      ▼
DSP: mic EQ → band select → shift or compress → transient gate → volume → safety ceiling   (output-band signal at 12.5 kS/s)
      ▼
×16 interpolation → 3rd-order noise shaper → TIM1 PWM, 200 kHz centre-aligned, 2-level (AD), 12.5–25 ns dead time
      ▼
H-bridge: 2× complementary MOSFET pairs (gates held off by pull resistors until TIM1 takes over) → RC-BC02 transducer

Power:    ~105–150 mAh LiPo along the temple arm (with protection) → MCP73831 charger → low-noise 3.0 V LDO → everything
Controls: 1 button; SWD pogo pads for programming; magnetic pogo pins for charging
```

Two identical, fully independent units, one per temple arm. No wires or radio between them (D2).
Every rate in the chain is an integer ratio of one 80 MHz clock. Any switching interference that leaks into the mic path therefore folds to 0 Hz and is filtered out (D14).

---

## 4. Decisions

Each decision gives the choice, the reasoning, and what was rejected. **vX.Y** marks the version that changed it.

### D1. Output site: at the tragus (primary); root of the cheekbone arch (fallback) `[High]` — **v0.5: moved to the tragus, owner-confirmed**
- **Primary site (owner, 2026-09-30; refined v0.7):** the skin **just in front of the tragus, at its base, at mid-tragus height**. The owner confirmed the tragus area is *easier* to fit than the cheekbone-arch spot alongside the Ear Opens. Geometry: `docs/research/ear-open-fit.md`.
  - **Why it wins:** the literature predicts ~10 dB more loudness and 25–40 dB of left/right isolation instead of ~10–15 dB. The mechanism is *cartilage conduction*: vibrating the tragal cartilage radiates sound into the ear canal (Surendran 2023).
  - **Consequences:** more loudness per milliwatt (battery, R1); much less crosstalk between sides (stereo, R5, D2).
  - **Fit with the Ear (open) (v0.7):**
    - Its hook junction comes down the front of the ear at the helix root, *above* the tragus, sitting 0–3 mm proud of the ear's front edge.
    - Its pod angles down and back into the ear bowl (concha), and its speaker grille aims at the canal entrance behind the tragus.
    - The only free contact spot near the canal is therefore **in front of the tragus, below the junction**. "Above the jaw joint" (v0.6 advice) is taken by the junction.
  - **Press inward (into the head), not backward.** Pushing the tragus flap back narrows the canal entrance the Ear (open) aims into, which breaks T4.
  - **Jaw:** the condyle is directly in front of the tragus, so this skin moves when you chew or open wide. The spring must hold ≥1 N through that motion (E2: talk and chew; T5).
  - The ear canal must stay open for the cartilage path to work. The Ear Opens don't block it.
- **Fallback site:** root of the zygomatic arch, about one finger-width above the jaw joint and 1–1.5 cm forward of the tragus. Kept in E2 as the comparison.
- **Evidence** (`docs/research/bone-conduction.md`):
  - The condyle region is 5–10 dB more sensitive than the mastoid at 1–4 kHz, and 3–14 dB more than the temple (McBride 2005/2008).
  - Localization through condyle-placed transducers matches headphones: ~23° error vs ~20° (Wang 2022).
- **Contact force:** aim for **≥1 N** through a compliant pad of **~8 mm** diameter (or an 8×10 mm oval, long axis vertical), which fits the pocket. That's ~17–20 kPa. Our inertial exciter loses only a few dB at ~1 N; below ~0.5 N coupling gets weaker and less repeatable. T5 comfort is the limit.
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

### D5. MCU = STM32U575CIU6Q (QFN-48, 7×7 mm, internal SMPS) `[High]` — **Changed v0.12 (was STM32L452CEU6, decided v0.4)**
- **v0.14 note (audit MP-07):** the pin map and text below are the L452 history. The current pin map is `hw/pod/gen.py` and `A3-u575-plan.md` §3: mic on ADF1 (PB3 clock, PB4 data), bridge on TIM1 (PA8/PA7/PA9/PB0).
- **What it is:** ST's ultra-low-power Arm Cortex-M4F at 80 MHz, with DSP instructions, an FPU and 160 KB RAM. It includes the **DFSDM**, a hardware PDM-to-PCM converter for the mic. The v0.2 pick (L432) lacks the DFSDM. Details: `docs/research/A1-A2-mcu-and-mic.md`.
- **Pin check (v0.5):** every needed function is available on the 48-pin package.
  - mic clock PA5, mic data PB1;
  - bridge PA8/PA7 and PA9/PB0 (TIM1 CH1/CH1N, CH2/CH2N);
  - SWD PA13/PA14; crystal PC14/PC15.
  - See `A3-clock-and-peripherals.md` §5.
- **JLC:** Extended part C222355, **16 in stock** (2026-09-30). Buy early (R10).

- **v0.12: moving to STM32U575CIU6Q** (owner removed the SMPS rule; D11). It's a Cortex-M33 at up to 160 MHz with DSP and FPU and an internal core SMPS, in the **same 7×7 mm UFQFPN-48**. MCU run current ~19.5 µA/MHz vs 84. The 160 MHz headroom also removes the CPU risk for log compression (R3).
  - Drop-in alternative: STM32U585CIU6Q (same chip plus crypto).
  - JLC (2026-09-30): U575CIU6Q C5271013, 8 in stock, $8.93; U585CIU6Q C5271021, 15 in stock, $12.52. Stock is thin, so buy early.
  - **Must re-verify before the schematic (A1/A3 reopened):** the U5 replaces DFSDM with the **MDF/ADF** digital filters, so the clock plan, filter orders and pin map need redoing. Also the advanced timer with complementary outputs and dead time for the bridge, and the SMPS inductor layout.
- **v0.13: U5 plan done** (`docs/research/A3-u575-plan.md`; DS13737 Rev 8, RM0456 Rev 6, ES0499 Rev 10).
  - **Correction:** ~19.5 µA/MHz applies only in voltage Range 4. In Ranges 1–3 on the SMPS it's **~40–45 µA/MHz**, so algorithm B at 80 MHz draws **~2.5–3 mA**, not ~0.9 mA. That's ~45% less than the L452, not ~75%.
  - **Pins (SMPS package):**
    - mic on the **ADF**, which draws ~8× less current than the MDF and keeps running in Stop 2: clock **PB3**, data **PB4**;
    - bridge PA8/PA7/PA9/PB0 (TIM1 CH1/CH1N/CH2/CH2N, unchanged);
    - button PA0; battery sense PA4; SWD PA13/PA14; crystal PC14/PC15. Never toggle PC13, which sits next to the crystal (ES0499 §2.2.1).
    - Using PB3 costs the SWO trace pin. Fallback is the MDF on PB8/PB1.
  - SMPS parts: 2.2 µH inductor (Murata LQM21PN2R2MGHL, a 0805 chip inductor; C341781, Extended, 6,100 in stock on 2026-09-30), 2 × 2.2 µF on VDD11, 10 µF at the SMPS input.
### D6. Output stage: 200 kHz 2-level PWM, 3rd-order noise shaping, discrete H-bridge `[Med]` — **Rewritten v0.5**
- **What it is:** TIM1, the MCU's motor-control timer, switches an H-bridge made of two complementary MOSFET pairs (each pair is one N-channel + one P-channel transistor in a 1.6 mm package). The bridge drives the transducer directly, and the transducer coil smooths the switching into sound.
- **Carrier:** **200 kHz**, centre-aligned (ARR = 200), with one duty update per period over DMA. It is synchronous with the input chain (D14), and 201 duty levels.
  - *Changed from 312.5 kHz.* That rate wasn't a multiple of the sample rate, so switching leakage would fold to 87.5 kHz and play as a tone.
- **v0.14, audit MP-01: the shaper's noise lands in the mic band.** "Coherent clocks put leakage at 0 Hz" holds for the carrier and its harmonics, **not** for the noise shaper's broadband quantisation noise. At 200 kHz that noise sits at **−35 dB re full scale across 20–85 kHz** on the bridge voltage (−59 dB in coil current), which is exactly the band the mic processes. If any of it couples back (rail, ground, mechanical), the device hears itself. `sim/checks/pwm_ultrasonic_leak.py`, same timer clock (80 MHz):

  | PWM rate / levels | mic band (V) | audio band 3–16 kHz | extra gate current |
  |---|---|---|---|
  | 200 kHz / 201 (today) | −35 dB | −87 dB | — |
  | 400 kHz / 101 | −45 dB | −102 dB | +0.3 mA |
  | **800 kHz / 51** | **−59 dB** | **−117 dB** | **+0.8 mA** |

  **Recommendation:** leave the hardware as is. The PWM rate is a firmware setting, and all three rows run on the same timer and bridge. Measure the real coupling on the bench (S2), then pick the lowest rate that keeps the self-noise below the mic's own floor.
- **Modulation: 2-level ("AD").** The two bridge legs are driven as complements.
  - At idle, a small ripple current (≈ Vbus / (4·L·f), e.g. 12.5 mA at 0.3 mH) flows back and forth. It costs 0.04–0.4 mW.
  - While that ripple exceeds the signal current, the bridge's **dead-time errors cancel exactly**, so quiet sounds stay undistorted.
  - *Changed from the 3-level ("BD") idea in v0.3–v0.4.* BD has no idle ripple, and dead time then distorts quiet signals badly: −10 dB THD+N at −40 dBFS even at 12.5 ns (`sim/checks/deadtime_switching.py`, `C3-output-stage.md`).
- **Dead time:** 1–2 timer ticks (12.5–25 ns), set per measured MOSFET switching speed.
  - **v0.13, SPICE with the Diodes DMC2400UV model** (`C3-output-stage.md` §5):
    - no dead time means shoot-through: 4.3 mA at idle;
    - 12.5 ns: 0.49 mA idle, THD+N −61 dB at −40 dBFS and −52 dB at the −12 dBFS ceiling;
    - 25 ns: 0.20 mA idle, −48 / −38 dB.
    - Start at 12.5 ns; try 25 ns plus firmware dead-time compensation in S2. Gate drive is 0.28 mA.
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
- **Gate charge matters for battery life (v0.6):** 4 FETs × Qg × 200 kHz is 0.4 mA at ~0.5 nC but 2 mA at ~2.5 nC. B1 prefers the low-gate-charge pair (DMC2400UV class).

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

### D11. Switching regulator for the MCU core; linear for everything else `[Med]` — **Changed v0.12 (owner)**
- The owner removed the no-switching rule. The limit is now that self-noise is no louder than the ambient background (§1.2.3).
- **Use:** the MCU's internal SMPS for its ~1.2 V core only. That's where the efficiency gain is: the core's LDO throws away about 60% of its input.
  - Keep it in fixed-frequency (PWM) mode, never burst/skip mode, which is the usual source of audible whine at light load. **v0.13:** the U5 has no mode bit for this. Its SMPS switches at a fixed ~3 MHz in voltage Ranges 1–3 and runs asynchronously only in Range 4. **Rule: never run Range 4 on the SMPS.** Stop 2 stays on the SMPS (ES0499 §2.2.22: Stop 2 on the LDO with RAM partly off can lock the part).
  - Use a shielded, low-magnetostriction inductor. **v0.13:** the switching pin itself carries no capacitor. ST requires 2 × 2.2 µF on the core rail and 10 µF at the SMPS input, and no C0G part comes in those values. So those are X5R, placed at the MCU, away from the mic and on the far side of the board from it. Parts: Murata DFE201610E-2R2M (a shielded 2.2 µH metal-alloy inductor, 2.0×1.6 mm; C337891); `B-parts-selection.md`.
- **Main 3.0 V rail stays a linear LDO.** A battery-to-3.0 V buck would save only ~10%, and the mic and bridge supply benefit from a quiet rail.
- **Check:** the owner's listening test on the bench (E11). If whine is audible over a quiet room's background, fall back to the LDO. The chip can switch regulators on the fly.

### D12. Modes `[High]` as requirements
- **Full:** the whole band, pitched down.
- **Transient-only (indoor default):** steady tones (charger and LED-driver whine) suppressed; changing sounds (chirps, clicks, rustles) passed through.
- **Off:** silent. MCU in Stop 2 (~4–9 µA on the U5, v0.13), mic unpowered, bridge stopped.
- **v0.11 (owner):** if log compression (B) sounds better in Phase 1 listening, it becomes the **only** processing mode. The always-on current difference is ~1.6 mA, and with idle-listening mode ~0.4 mA. Heterodyne (A) stays in the code only as a fallback if B won't fit the CPU (R3).

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
- **Per-mode system clock (v0.6, power):** the tree works at any clock that's a multiple of 8 MHz. The mic divider becomes f/4 MHz (always even) and the PWM period ARR = f/400 kHz: 48 MHz → ARR 120; 64 MHz → ARR 160; 80 MHz → ARR 200.
  - Algorithm A runs at **48–64 MHz**, saving ~0.8–1 mA. Algorithm B needs **80 MHz**.
  - Mic clock and PWM rate stay the same; only the PWM step count changes (121–201 levels, fine with the 3rd-order shaper). Switch clocks only at mode changes, since DFSDM must restart.
- **DFSDM details** (RM0394; `A3-clock-and-peripherals.md` §3):
  - The CKOUT divider can only change with DFSDM disabled. The standard→ultrasonic mode switch is therefore stop, re-divide, restart; the µs gap is harmless `[Med]`.
  - Use **filter 0** (DMA1 channel 5). Filter 1 shares channel 6 with TIM1's update request.
- **v0.13, STM32U575 (`A3-u575-plan.md`):**
  - Clock: MSI locked to the 32.768 kHz crystal, **80 MHz in voltage Range 2** (allows up to 110 MHz). Actual 80.009 MHz; mic clock 4.0004 MHz; PWM period 200 counts; dead time in 12.5 ns steps, set separately for rising and falling edges.
  - Mic decimation in hardware: ADF sinc5 ÷5 → 800 kS/s, then its reshape filter ÷4 → **200 kS/s** (passes to ~89 kHz, rejects ~70 dB above ~120 kHz). The CPU half-band disappears. Fallback: ÷10 + CPU half-band, as before. ST publishes no response at this rate, so S1 sweeps it.
  - GPDMA takes any request on any channel, so the L452's DMA conflict is gone.
  - **Errata firmware rules (ES0499 Rev 12, checked 2026-09-30):**
    - handle the MSI PLL unlock interrupt by disabling and re-enabling PLL mode (spurious unlocks, §2.2);
    - switch PLL2/PLL3/HSI48/SHSI off before Stop 2 (§2.2.5);
    - never use TIM1 ocref_clr with combined or asymmetric PWM (no workaround); faults go through BKIN.
  - Idle mode: ADF + low-power DMA keep filling a ~40 ms look-back buffer in Stop 2. The ADF's built-in sound-activity detector is broadband: speech and footsteps trip it as easily as bats. So band detection stays in software (C9).
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

### D18. Runtime and weight balance `[High]` as requirements — **New v0.6 (owner, 2026-09-30)**
- **Runtime:** ≥8 h per charge, target ~12 h. Nightly charging.
- **Battery:** bay sized for a ~150 mAh cell (~4.5 g); a ~105 mAh cell is the minimum. The exact cell is picked after E4 current measurements (§7).
- **Balance (owner: "design for balance as needed"):** the cell sits along the temple arm behind the front module, centred as far back as the Ear Open hook allows. This splits the added weight between nose pads and ears instead of loading the nose (§8 table).
- **Interpretation of §1.2.4** ("bulk at the front near the hinges, never near the neck or behind the ears"): nothing goes behind the ear or toward the neck. The electronics stay at the hinge; only the cell moves rearward along the arm, in front of the ear. §1 text unchanged. **The owner should confirm this reading** (O4).

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

## 7. Power (per side) — **v0.6: sized for 8 h minimum, ~12 h target (owner, O1)**

**Requirement (D18):** at least 8 h of wear per charge, ideally ~12 h. Nightly charging.

**Budget after v0.6 optimizations** (tragus site, low-gate-charge MOSFETs, per-mode clock):

| Block | Current | Basis |
|---|---|---|
| Mic, ultrasonic mode | ~0.9–1.1 mA | 845 µA typ at 1.8 V; rises with supply and clock load `[High]` |
| MCU, algorithm A at 48–64 MHz | ~2.4–3.9 mA | 19–39 M cycles/s; 84 µA/MHz run, 27 µA/MHz sleep (`C2-cpu-budget.md`, D14) `[Med]` |
| MCU, algorithm B at 80 MHz | ~4.7–5.8 mA | 44–65 M cycles/s `[Med]` |
| Peripherals (TIM1, DFSDM, DMA) | ~0.6–1.0 mA | TIM1 8.1 µA/MHz `[Med]` |
| Bridge: gate charge + idle ripple | ~0.4–0.6 mA | 4 FETs × ~0.5 nC × 200 kHz with a low-gate-charge pair (B1); ripple loss 0.04–0.4 mW `[Med]` |
| Transducer, average at listening level | ~0.6–1.7 mA | was 2–5 mA; the tragus site needs ~10 dB less drive (D1) `[Low]`, measure (E4) |
| LDO, crystal, battery protection | <0.05 mA | `[Med]` |
| **Total** | **~5–8.5 mA (A), ~7.5–10.5 mA (B)** | `[Low]` until E4 |

**Runtime** (usable ≈ 85% of rated capacity):

| Cell | Algorithm A | Algorithm B | Meets |
|---|---|---|---|
| ~105 mAh | ~10.5–18 h | ~8.5–12 h | 8 h everywhere; 12 h in A |
| ~120 mAh | ~12–20 h | ~9.5–13.5 h | 12 h in A, most of B |
| **~150 mAh** | **~15–25 h** | **~12–17 h** | **12 h everywhere, even at the pessimistic end** |

**Recommendation:** design the battery bay for a ~150 mAh cell (≈4×12×40–45 mm, ≈4.5 g). Fit anything from ~105 mAh up once E4 measures real current.
- The estimates are `[Low]`, and the extra ~1.5 g costs little when placed for balance (§8).
- Charge at ≤0.5C (MCP73831 set to ~50–75 mA): ~2.5–3 h, overnight.

**Power levers, most effective first:**
1. Transducer at the tragus (D1, done).
2. Squelch with CPU sleep.
3. Algorithm choice (A is ~2.5 mA cheaper).
4. Lower clock for A (D14).
5. Low-gate-charge MOSFETs (B1).
6. DFSDM ÷20 (saves 0.3–0.6 mA of CPU).
7. **Idle-listening mode** (C9, `[Low]` estimate): when nothing ultrasonic is happening, run only a cheap band-energy detector at a low clock and keep a ~10 ms look-back buffer. Wake to full processing on activity, with the buffer covering the wake-up, so call onsets aren't clipped. Could save ~1–2 mA in quiet periods. Evaluate in S3.

**v0.10 power findings (2026-09-30):**
- ~~STM32U575: 19.5 µA/MHz on its internal SMPS … MCU ~3.8 → ~0.9 mA~~ **Corrected v0.13:** that figure is Range 4 only. At 80 MHz in Range 2 on the SMPS the MCU draws ~2.5–3 mA with algorithm B (DS13737 Rev 8 Table 39; `A3-u575-plan.md` §5) `[Med]`.
- **The big allowed lever is the idle-listening mode (C9), now the top power item.**
  - When the ultrasonic band is quiet, the CPU clock is divided down, a few band-energy detectors (each with a slowly tracking floor, so steady whines don't count) run on the DFSDM stream, and the bridge stops. The mic clock never changes, so there's no DFSDM restart.
  - A ~10 ms look-back buffer covers the wake-up, so call onsets aren't clipped.
  - Estimated draw at 75% quiet time: ~3.3 mA (A) and ~3.7 mA (B), against 7.2 and 8.8 mA always-on, so 8 h needs ~35 mAh instead of ~70–85 mAh `[Low]`.
  - Worst case, when the band is always busy, falls back to full draw. So the cell should still be sized for the always-on case, or for a measured duty cycle from E4.

**v0.14 budget: supersedes v0.13 below** (`sim/checks/power.py` rev 2; audit PWR-01..04, dsp-1/2/8):
- **Mic current re-derived at our 3.0 V / 4 MHz:** 1.1 / 1.35 / 2.15 mA. It was quoted at the datasheet's 1.8 V / 3.072 MHz point. Bridge 0.77 mA from our own SPICE; gate pulls added; transducer range widened (still an untraced guess until E1/E4).
- **The pessimistic case now also shrinks capacity:** 90% / 85% / 75% usable.
- **Full chain awake:** 5.0 / 6.8 / 9.8 mA. **Idle:** 1.7 / 2.2 / 3.4 mA.
- **Idle detector rev 2** (FFT snapshot every 5 ms plus a narrowband test; `sim/checks/idle_detector.py`). The old detector woke on audible speech: 95% awake on speech alone, and 67% in a room without electronics. Its 14% was the synthetic whines masking this. Rev 2 results:
  - awake time: speech only 5%, quiet room 18%;
  - Port Meadow (real AudioMoth recordings, 270 files): 95.5% of 10,024 annotated bat calls caught within 10 ms, and no pass missed entirely;
  - CPU: ~3.4 Mcycle/s, down from ~12. It fits the 16 MHz idle clock.
- **Runtime with 105 mAh:**
  - awake all the time: **8.0–13.2 h**;
  - half the time: 11.9–19.9 h;
  - quiet room: 17–30 h.
- **So the 8 h minimum holds even never sleeping, with no margin.** The idle mode is now load-bearing; keep 105 mAh (O5).

**v0.13 budget (superseded by v0.14 above; U575 on SMPS + idle-listening mode; `sim/checks/power.py`):**
- **Full chain awake:** 4.6 / 6.0 / 7.5 mA (low / nominal / high). **Idle:** 1.5 / 1.9 / 2.4 mA; the mic (~1 mA) is now the biggest idle load.
- **Awake time** from the Phase-1 DSP model (`sim/dsp/run_phase1.py`): **14%** on a simulated quiet evening, with all 4 events caught within 10 ms; 93% on a deliberately busy scene.
- **Runtime with a 105 mAh cell:**
  - awake all the time: **11.9–15 h**;
  - half the time: 18–23 h;
  - quiet evening: 29–37 h.
  - So 105 mAh meets 8 h everywhere and 12 h at nominal draw even if the chain never sleeps. An 80 mAh cell drops to 9.1 h at the pessimistic always-awake end, so keep 105 mAh (O5).

**Supply rail** `[Med]`:
- **3.0 V from a low-dropout LDO**, leaving ~300 mV of headroom at the LiPo's 3.3–3.4 V knee.
- Bridge supply stays on the regulated rail. Running it from the battery would make gain track charge by ≈1.8 dB and unbalance the sides.
- 2-level modulation *prefers* the full 3.0 V: more ripple means a wider clean range.

---

## 8. Physical layout (per side) — **v0.6: split along the arm for balance (D18)**

> **v0.8 (owner, 2026-09-30): one pod between the eye and the ear, swept-back arm.**
> Measured on the owner's photos (`docs/research/ear-open-fit.md`; scale ±20% until the ruler shot):
> - **Pod:** a single pod on the temple arm, from just behind the hinge to ≥5 mm ahead of the
>   Ear (open) hook. That's **~60 mm** of usable length, and it holds both the electronics and the battery.
> - **Arm (owner's aesthetic request):** swept **back** from the pod's rear-lower edge to the pad.
>   - Any sweep of 11° or more clears the Ear (open) by ≥5 mm.
>   - **25–35°** looks clearly swept and clears by 8–9 mm; the arm is ~22–24 mm long.
>   - Starting the arm further forward lengthens it (softer spring, more snag risk) without adding clearance.
> - **Fit:** PCB (~20 mm) + ~105 mAh cell (~30 mm) + walls ≈ 54 mm fits in line. A 150 mAh cell
>   (40–45 mm) does not fit in line; it would sit beside or under the PCB (a thicker pod), or
>   needs a shorter, fatter cell. B4 decides.
> - **Balance:** with the pod centred ~35 mm behind the hinge, the nose pads carry 3.9 g per side
>   (105 mAh) or 4.9 g (150 mAh), against 3.1–3.7 g for the cell-further-back layout below.
>   That's the price of keeping everything in front of the ear hook. The owner's call (O5).
>
> The v0.6 text below remains the fallback.
>
> **v0.14: CAD rev 2** (`hw/mech/pod.py`; sketches `hw/mech/out/pod_sketches.png`):
> - **Pod grows to 38 × 10 × 15 mm** (was 35 × 9 × 14). The cell is now modelled at the EEMB LP401230 spec sheet's **maximum** envelope (31 × 4.3 × 12.5), plus a ~3 mm protection board `[Low]`, with 0.3 mm assembly clearance. The v0.13 box fitted only the nominal cell with zero clearance. All 8 checked part pairs clear by ≥0.2 mm. ~7.1 g per side.
> - **Arm drawn as the real NiTi wire** in two variants for the reopened O7 (A: 20 mm on the plateau; B: 30 mm elastic, anchor moved forward, pad unchanged). Owner kept A's geometry (O7b).
> - **Exterior, owner 2026-09-30: "Blade"** (`hw/mech/blade.py`):
>   - gunmetal armour plate with an engraved circuit-trace groove (airbrush chrome if wanted);
>   - a tapered dorsal fin growing out of the plate, and a matching heel under the rear that holds the arm root;
>   - a hex pad whose ring is either LED-lit (O8) or chrome.
>   - **No UV or glow prints** (owner). Pod shell, plate, fin and heel print as one part.
> - **Frame adapter is a separate print (owner requirement: swap it for new frames without reprinting the pod).**
>   - It slides onto a dovetail rail on the pod's inner face from the front, stops at the rear, and a printed snap tab clicks over a ramp.
>   - To release it, push the tab's foot with a fingernail and slide it forward.
>   - It is parametric in the temple-arm section (`pod.TEMPLE_T/H`).
>   - Cost: **1.8 mm more stand-off** between temple and pod. The pad position is unchanged.
> - **Exterior history:** not final (owner): 3D-printed, cyberpunk ("Night City"), not a brick. Three concepts on the same insides: `hw/mech/styles.py`, rendered by `hw/mech/render_styles.py` (Blender, CPU). Glow parts are separate prints (UV-reactive/glow filament, no power).
>
> **v0.13: first CAD and spring study** (`hw/mech/pod.py`, `sim/checks/tragus_spring.py`, `docs/research/tragus-arm.md`):
> - **Pod:** 35 × 9 × 14 mm. The 105 mAh cell sits against the inner wall; the 0.8 mm PCB (**20 × 11.5 mm**, raised from 10 mm so the MCU's wiring can escape; `hw/pod/place.py` routes it completely, DRC clean) is outboard, with the mic porting outward at the front. Zero interference.
> - **Mass:** 7.75 g per side, centre of mass 52 mm behind the hinge: **nose pads 3.7 g, ear 4.1 g**.
> - **Spring:** a one-piece steel strip can't hold 1 N at this length without fatigue. **Recommended: rigid arm on a pivot with a preloaded torsion spring** (Ø0.65 mm wire, 7 turns, Ø5.2 mm): 0.99–1.26 N over ±2 mm of jaw travel. Alternative: superelastic NiTi wire, ~1.0 N settled, ~2.3 N while putting the glasses on. **O7 resolved: the owner chose NiTi.**
> - **Transducer orientation:** the RC-BC02 housing (~14 mm long) must lie **along the arm**. Stood vertically, its top end comes within ~2 mm of the Ear (open) hook junction; along the arm it clears by ~5.8 mm.
> - **Reaction:** the pad's 1 N pushes the temple arm outward and twists it (~25 N·mm). The clip needs ~5 N of grip on the arm's top and bottom edges. New E12 measures her temple arm's stiffness.
>
> **v0.9 (owner): peripheral vision is a hard no-go zone. No part of the device may be visible
> with the eyes looking straight ahead.**
> - **Estimate:** the temporal visual field reaches ~100–110° from straight ahead. For an object
>   ~35 mm out to the side of the pupil, that's visible up to ~6–13 mm *behind* the pupil plane.
>   The design limit is a 110° field plus a 5 mm margin: **nothing forward of ~18 mm behind the
>   pupil plane.** On the owner's photo that leaves **~35 mm** of temple arm for the pod, not 60 mm.
> - **Consequences:**
>   - The in-line PCB + cell layout no longer fits. The pod becomes ~35 mm long, with the PCB
>     stacked beside or under a ~30 mm (~105 mAh) cell, so it's thicker (~8–10 mm).
>   - Balance improves: the pod is centred ~47 mm behind the hinge, putting 3.2 g per side on
>     the nose pads (105 mAh) or 4.0 g (150 mAh).
>   - The swept-back arm (25–35°) is unchanged.
> - **Hard rule:** the owner's measured field (E10) overrides this estimate. The mic stays in
>   front of the hair (E9) *and* behind the vision line, so it goes at the pod's front end.

- **Front module, at the hinge:** PCB, mic, button, crystal.
  - **PCB size** `[Med]` (parts-area estimate): ~10×20 mm with parts on both sides (4-layer), or ~10×28 mm single-sided. The 7×7 mm MCU sets the ~10 mm width.
  - The mic faces outward here: the head-shadow cue needs it on the side of the head, and the front keeps it clear of hair and the Ear Open.
- **Battery bay, behind the front module along the temple arm:** the cell lies along the arm (long axis front-to-back), centred ~50–60 mm behind the hinge. It ends before the Ear Open hook, so nothing is behind the ear (§1.2.4). A 2-wire link runs from the front module.
- **Transducer arm (v0.7, `docs/research/ear-open-fit.md`):** an **"L" or "J" spring arm** attached to the temple arm ~10–15 mm in front of the ear.
  - It drops **in front of** the Ear (open)'s hook junction, then turns back to an ~8 mm pad on the skin just in front of the tragus, pressing inward with ≥1 N.
  - **Clearance:** ≥5 mm from every part of the Ear (open) in nominal fit; ≥8 mm for the vertical run. It must stay clear if the Ear (open) shifts ~3 mm.
  - If bumped, it deflects *away* from the Ear (open). Smooth, low profile against long hair (R16).
- **Balance** (`sim/checks/balance.py`; added load per side, estimated masses):

  | Layout | ~105 mAh cell (7.3 g) | ~150 mAh cell (8.8 g) |
  |---|---|---|
  | Everything in one pod at the hinge (v0.5) | nose 4.9 g · ear 2.4 g | nose 6.1 g · ear 2.7 g |
  | Cell centred mid-arm | nose 3.6 g · ear 3.6 g | nose 4.4 g · ear 4.4 g |
  | **Cell just before the Ear Open hook** | **nose 3.1 g · ear 4.2 g** | **nose 3.7 g · ear 5.1 g** |

  Moving the cell back lets the bigger battery load the nose pads *less* than the small one did at the hinge. **Nose-pad pressure is the usual comfort failure for glasses**, so this is the main lever.
- **Acoustic path rules (v0.5):**
  - The mic ports through the PCB, so use a **thin board (≤0.8 mm)**.
  - Keep the port hole short and wide (~0.6–1.0 mm, larger than the mic's Ø0.325 mm port).
  - No gasket cavity; the clasp opening directly over the hole; thin mesh, never foam.
  - The S1 coupons test real geometries.
- **Wiring along the arm:** battery (2 wires) and transducer (2 wires, a 200 kHz switching waveform). Route the transducer pair away from the mic port and clock/data lines.
- **Skin isolation:** transducer metal and solder joints fully insulated (silicone pad plus sealed housing).
- **Programming:** SWD pogo pads. **Charging:** magnetic pogo connector plus a nightly dock.
- **Mass:** ~7.3–8.8 g per side total `[Low]`, near the ~8 g target and well under the ~15 g "glasses start hurting" level, with the load split between nose and ear as above.

---

## 9. Parts (candidates; nothing ordered)

Stock and price as of 2026-09-30 from the JLC parts API unless noted.

| Function | Part (what it is) | JLC | Status |
|---|---|---|---|
| MCU | **STM32U575CIU6Q**: 160 MHz Cortex-M33 with internal core SMPS and MDF/ADF PDM filters, QFN-48 7×7 mm (v0.12; was STM32L452CEU6) | C5271013 · Extended · 8 · $8.93 | **Chosen** (D5, D11); re-verify MDF plan (A1/A3) |
| Mic | **SPH0641LU4H-1**: digital MEMS mic with ultrasonic mode, 3.5×2.65 mm | C2879853 · Extended · 1,076 · $1.99 | **Chosen** (D13); lifecycle OK |
| Mic backup | **TDK T5838**: PDM mic, ultrasonic mode to ~50 kHz | C7230692 · Extended · 684 · $3.47 | Backup only |
| Crystal | **Q13FC13500004**: 32.768 kHz watch crystal, 3.2×1.5 mm (or X1A0000610002, 2.0×1.2 mm) | C32346 · **Basic** · 467k · $0.17 (C55208 · Extended · 22.5k) | Recommended (D16) |
| H-bridge | 2× complementary N+P MOSFET pair, SOT-563 1.6×1.6 mm: **NTZD3155C** (onsemi, ~2.5 nC) or **DMC2400UV** (Diodes Inc., ~0.5 nC) | C236117 · Ext · 8,788 · $0.17 / C177025 · Ext · 113 (clone C2940616 · 3,836) | B1: on-resistance at 3.0 V gate drive and gate charge |
| Gate pulls | 4× resistors (P-gate pull-ups, N-gate pull-downs) | Basic | Mandatory (D6) |
| Charger | **MCP73831**: single-cell LiPo linear charger, SOT-23-5 | C424093 · Extended · 9,478 · $0.78 | B3: set ~50–75 mA (≤0.5C) |
| LDO | Low-noise 3.0 V linear regulator, low dropout, low idle current | — | B2 |
| Transducer | RC-BC02 / GD02 bone exciter (8 or 12 Ω, to be measured) | not JLC; hand-soldered | E1 |
| Battery | ~105–150 mAh LiPo with protection circuit, long and low (≈4×12×40–45 mm) to lie along the arm | not JLC; hand-soldered | B4 (after E4) |

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

### Phase 2: Bench prototype — **revised v0.5; superseded in part by O9 (rev 1 pod board = prototype, no separate test boards)**

| Stage | Build | Answers | Needs Phase 1? |
|---|---|---|---|
| **S1: Ears** | Elecrow mic board → Nucleo DFSDM at 4.0 MHz; stream 200 kS/s audio to the PC over USB (L452 USB device on PA11/PA12), not just RAM bursts | D14 clock plan; **mic-clock duty cycle on a scope**; crystal choice (LSE vs HSE noise floor); mic ultrasonic noise floor (R8); **acoustic coupons** (response vs port geometry); **real recordings of the owner's home and yard**, including self-noise (own speech, chewing, hair on the clasp, frame creaks) | No |
| **S2: Voice** | JLC discrete-bridge test board → transducer; tones and clips from flash | E1 (inductance, resistance); **E2 placement: tragus (primary) vs cheekbone-arch fallback, at ≥1 N, Ear Opens playing**; R1 (loud enough?); **low-level distortion (1 Ω sense resistor + sound card); idle silence (T6); 8–16 kHz noise by ear** | No |
| **S3: Brain** | S1 + S2 joined, chosen algorithm in real time | R3 (CPU, measured with the cycle counter), E4 (current per mode), latency, no clicks (D17) | Yes |
| **S4: Stereo** | Two full units on a rough head mount, battery-powered | **Exit: T1, T2, T3, T6 pass.** Plus **A/B: free-running vs shared clock** (does phase matter for direction? D2) | Yes |

**Bench rules:**
- Listening tests run on battery, never laptop USB. USB streaming is for recording only.
- Use **NUCLEO-U575ZI-Q** (SMPS variant, v0.12). E11: owner listens for whine with the board against her temple in a quiet room.
- Check whether the Nucleo's user LED shares PA5; if so, remove its solder bridge.

**Shopping list v0.5** (to price and verify before ordering; owner approves):
- 2× **NUCLEO-U575ZI-Q**: ST dev board with the new MCU and its SMPS (v0.12; replaces NUCLEO-L452RE). Check stock at order time.
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
| R11 | Real current above estimate, so 150 mAh doesn't reach 12 h | `[Med]` | E4; power levers in §7 (idle-listening mode C9) |
| **R16** | A 12 mm-tall battery bay along the arm looks bulky or snags hair | `[Med]` | B4 (find the lowest-profile cell); Phase 4 fit tests |
| **R12** | Low-level distortion from dead time exceeds the model (node capacitance, MOSFET behaviour) | `[Med]` | S2 measurement |
| **R13** | DFSDM clock duty cycle outside the mic's 48–52% | `[Low]` | S1 scope; timer-clock fallback |
| **R14** | Acoustic path (port, wall, mesh) cuts ultrasonic sensitivity or adds resonances | `[Med]` | S1 coupons; §8 rules; DSP EQ |
| **R15** | Self-noise (own speech, chewing, hair) makes transient mode busy | `[Med]` | S1 recordings; gate tuning (C4) |
| **R17** | **New v0.13.** Temple arm bends and twists under the pad's reaction force, so the pad loses force or the pod rolls | `[Med]` | E12; soft preloaded spring (O7); snug clip |
| **R18** | **New v0.13.** Mic duty cycle / ADF reshape-filter response at 800 kS/s not as assumed (unpublished) | `[Low]` | S1 scope and sweep; ÷10 + half-band fallback |

---

## 12. Tasks and decisions

### Owner decisions (open)
| ID | Decision | Recommendation |
|---|---|---|
| ~~O1~~ | ~~Battery and runtime target~~ | **Resolved 2026-09-30:** ≥8 h, target ~12 h, design for balance (D18) |
| ~~O2~~ | ~~Test a spot nearer the tragus?~~ | **Resolved 2026-09-30:** the tragus is the primary site, and the owner says it fits more easily (D1) |
| **O3** | Approve the v0.5 shopping list once priced | — |
| **O5** | **v0.14, owner:** the growth is acceptable if it's clearance. Height/width +1 mm each are tolerance + clearance; the +3 mm length is the cell's protection board (a real part, previously unmodelled; measure the bench cell). Was: Pod layout inside the ~35 mm between the vision line and the ear keep-out (v0.9): stacked, thicker pod with a ~105 mAh cell vs a slimmer pod with a smaller cell (runtime cost) | One pod if the 105–120 mAh class meets the runtime after E4 |
| ~~O6~~ | **Resolved 2026-09-30: owner removed the rule; see D11, D5.** Was: allow a switch-mode regulator only as the MCU core's internal SMPS (STM32U575/U585 "Q" variants, same 7×7 mm QFN-48): forced-PWM (fixed frequency, MHz range, never burst mode), shielded low-magnetostriction inductor, no Class-2 caps on it, and it **must pass the owner's own listening test on the bench** before adoption. Saves ~3 mA always-on (MCU ~3.8 → ~0.9 mA) or ~1.2 mA with idle mode. §1.2.3 is owner-locked, so this needs her explicit change | Bench-test it (buy one NUCLEO-U575ZI-Q alongside the L452 board); decide by ear |
| ~~O7~~ | **Resolved 2026-09-30: owner chose (B), a superelastic NiTi wire arm** (no hinge; same material as the Ear (open) hook). Was: (A) pivot + torsion spring vs (B) NiTi | Plan in `tragus-arm.md` "Owner decision": **straight pre-set superelastic wire, no heat-setting (owner 2026-09-30); direction from angled holes in the heel and pad**, curved root support; the bench measures force before and after 100 on/off cycles |
| ~~O7b~~ | **Resolved 2026-09-30 (owner): 20 mm arm, 30° sweep, wiring cross-section A** (two litz wires in the silicone sleeve; `tragus-arm.md` "Sleeve and wiring"). Wire diameter per the proposal below, pending the coupon bend. History: keep the 20 mm arm and 30° sweep (variant A geometry); she cares about enough pad pressure for good conduction without discomfort, not about the on/off history. **Claude's proposal (awaiting OK): Ø0.75 mm wire, free shape set ~3–4 mm into the skin (≈10° inward lean, her idea): 1.0–1.3 N while wearing, and the plateau caps it at ~1.6 N however far it's pushed.** Caveat: after a wide jaw opening the force may sit near ~0.7 N (unsourced lower plateau), so a coupon bend on the bench comes first. Wires: two litz wires inside the sleeve (`docs/diagrams/arm-wiring.svg`, option A). Was: **Reopened v0.14 (audit mech-1..4).** The NiTi chart O7 was decided on was not a model past ~3 mm. On the plateau, a 20 mm × Ø0.85 mm arm pushes **2.3 N while loading and ~1.0 N while unloading**, so the force swings with jaw motion, and root strain reaches 4–7%. Two independent models agree within 3% (`sim/checks/niti_closed_form.py`, the auditor's elastica). Options: **(A) keep the 20 mm arm**: 1.0–2.3 N, history-dependent, strain near NiTi's 6% recovery limit. **(B) a 30 mm arm, kept elastic**: 0.7/1.0/1.3 N at 5/7/9 mm, linear, ~1.3% strain, but a 54° sweep instead of 30°. **(C) the pivot + torsion spring** (v0.13 option A): 0.99–1.26 N | **B**, if the 54° look is acceptable: it trades a superelastic "flat force" that doesn't exist for a predictable spring. Either way, bend a coupon on the bench first: NiTi's modulus is uncertain ±30% |
| ~~O8~~ | **Resolved 2026-09-30 (owner): yes, SOLID as a power-on indicator (no pulsing); battery cost accepted; thicker sleeve welcome.** Schematic Rev C adds R14 + J7/J8 on PB7. Was: **Pad LED ring** (`docs/research/pad-led.md`): an 0402 blue LED under a clear-epoxy ring, fed from VBAT through ≈2 kΩ, PWM from PB7. About 0.15–0.5 mA while glowing; costs 0.1–0.3 h in the always-awake worst case (7.7–7.9 h vs 8.0 h). Visible indoors and at night only. Fallback: airbrushed chrome ring | **Yes, with activity-driven brightness, a button toggle and auto-off below ~20%**, which keeps the worst case at 8 h when it matters |
| ~~O9~~ | **Owner decision (made early; reconfirmed 2026-09-30): rev 1 of the final pod board IS the prototype.** No dev boards or separate bridge test boards. Debug access comes from the board itself: test pads, plus a snap-off test frame on the same JLC panel. Phase 2 below is superseded where it calls for separate bench boards | — |
| ~~O10~~ | **Owner decision 2026-09-30: two-stage build.** TEST build: screws where needed, everything reachable. FINAL build (once confirmed working): adhesives everywhere except the NiTi wire fasteners, and water/sweat resistant, but it must stay possible to cut it open to change firmware etc. Research in progress: `docs/research/sealing-and-service.md` (target IP rating, ultrasonic-transparent mic vent, sealed firmware path vs designed cut seam) | — |
| ~~O11~~ | **Owner decision 2026-09-30:** the arm's cover is a printed rectangular strut in the coil-spring option's look (not a silicone sleeve); the NiTi does all the flexing. Skin contact stays silicone, likely moulded Sugru; flat vs gentle curve is being researched (`docs/research/contact-face-and-preload.md`) and settled on the bench with swappable mould inserts. Owner: tilt the arms inward so wearing preloads the NiTi onto its superelastic plateau | — |
| ~~O12~~ | **Owner decisions 2026-09-30:** (a) firmware + charging through a **magnetic USB dock/cable** (USB FS on PA11/PA12, ST ROM DFU); "we have space and budget". The lid screws no longer need to be charge contacts. (b) **Sealing is critical:** outdoor wear in light rain (hair/hood help) → target **IPX4 minimum, IPX5 preferred**. (c) **Fastest practical charge:** fast-charge-rated cell + temperature-qualified (NTC/JEITA) power-path charger; research in `docs/research/battery-and-charging.md` (also cell sourcing) | — |
| **O4** | Confirm the D18 reading of §1.2.4: cell along the arm, in front of the ear, nothing behind it | Yes; it's what makes the 12 h battery comfortable |

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
| B3 | Charger | MCP73831 (C424093); program ~50–75 mA (≤0.5C for 105–150 mAh) |
| B4 | Battery | 105–150 mAh protected LiPo, **long and low** (target ≤4.5 mm thick, ≤12 mm tall, ≤45 mm long); mass; sourcing. Final pick after E4. |
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
| C9 | Idle-listening power mode (band-energy detector + look-back buffer + wake) | **New v0.6.** Simulate in Phase 1, measure in S3 |

### D. Mechanical and materials (P3)
| ID | Task |
|---|---|
| D1 | Nitinol wire, skin-safe silicone, JLC PA12 nylon print rules |
| D2 | Acoustic mesh that passes 20–80 kHz and keeps out dust and sweat |
| D3 | Skin-contact insulation method for the transducer |
| D4 | **New.** Drop-arm spring design for ≥1 N with a compliant pad (after E2) |
| D5 | **New v0.6.** Pod layout and balance: front module + battery bay along the arm; check with `sim/checks/balance.py` and CAD mass properties |

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
| E10 | **New v0.9.** Peripheral-vision boundary: glasses on, eyes fixed on a point straight ahead, a helper slides a pen tip forward along the temple arm from the ear until the owner first detects it. Mark the spot and measure from the hinge; repeat 3×, both eyes; also check just above and below the arm. The pod's front end goes ≥5 mm behind the mark | Vision no-go line (§8) |
| E11 | **New v0.12.** SMPS whine: board running the real load pattern, pressed against the temple in a quiet room; owner listens. Pass = not louder than the room's background. **v0.13:** test the idle-listening mode (16 MHz, Range 3) and Stop 2 too, not just full processing | D11 |
| E12 | **New v0.13.** Temple-arm stiffness: glasses on a table, hang 100 g (≈1 N) from the temple arm ~60 mm behind the hinge. Measure how far it moves sideways; then hang it from a 25 mm stick taped under the arm and measure the twist | R17, O7 spring preload |
| E9 | **Partly done 2026-09-30** (no ruler; scale from the speaker ring, see `ear-open-fit.md`; still wanted: ruler shot and mouth-open shot). Photo measurement: glasses + Ear (open) worn, mm ruler at the ear; lateral view of both ears, rear-oblique view, and mouth-open view (procedure in `ear-open-fit.md`) | D1 pad location, D4 arm geometry, keep-out at true scale |

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

### v0.14 (2026-09-30) — audit fixes (Claude, autonomous; owner decisions pending)
- **Audit:** `docs/audit/2026-09-30-audit-report.md` (partial). Every change below comes from a finding there, and each was re-checked by a different method before it was applied.
- **Schematic Rev B** (`hw/pod/gen.py`):
  - MCP73832 (open-drain STAT) with a 100k pull-up. Fixes NM-1: the MCP73831 put 5 V on PA10.
  - VBUS sense on PA1, so the firmware can sleep when docked and the charger can terminate (PWR-05).
  - C4 10 µF 0603, BOOT0 10k, 100 nF at VBAT.
  - Mic footprint with a 0.6 mm port.
  - ERC 0 errors; 45 parts, all with LCSC numbers.
- **D6:** shaped PWM noise in the mic band (MP-01), options table; the decision waits for bench coupling data.
- **§7:** power budget rev 2 and idle detector rev 2 (validated on real Port Meadow recordings). Always-awake runtime drops to 8.0–13.2 h.
- **§8 / O7b:** NiTi reopened on corrected numbers; CAD rev 2 (38 × 10 × 15 mm pod, max cell envelope, gap checks).
- **Board draft:** 0.8 mm with a real stackup; mic port 0.6 mm. FP-1 (oversized TPS7A20 pads) was checked and **not upheld**.
- **D5:** title corrected to the U575 (MP-07).


### v0.13 (2026-09-30) — U5 plan, DSP model, first CAD
- **Owner: O7 → superelastic NiTi wire arm.**
- D5/D11/D12/D14: STM32U575 plan (`A3-u575-plan.md`). MCU current corrected to ~2.5–3 mA (was ~0.9). Mic on ADF PB3/PB4 with hardware decimation to 200 kS/s. "Forced PWM" means never Range 4 on the SMPS.
- §7: new budget from `sim/checks/power.py` and the Phase-1 DSP model (14% awake on a quiet evening). 105 mAh: 11.9–15 h even always awake.
- §8: first CAD, spring study and transducer orientation. New O7, E12, R17, R18.
- Pod board: SKiDL schematic (`hw/pod/gen.py`, ERC 0 errors, 41 parts all with LCSC, ≈$13/board), draft placement + full autoroute on 20 × 11.5 mm, 4 layers (DRC clean at JLC minimums). Design review: `docs/design-review-v1.md`.
- Phase-1 DSP (`sim/dsp/`): band envelopes (1.5 ms attack / 15 ms release) and a gain limiter keep the output inside 1.5–4 kHz without clicks; transient mode also gates on calibrated mic self-noise.

### v0.12 (2026-09-30) — switching regulator unlocked
- **Owner changed §1.2.3:** the no-switching-regulator rule is removed. The limit is now "self-noise no louder than ambient background."
- D11 rewritten: internal core SMPS in forced-PWM mode; main rail stays linear. D5: moving to STM32U575CIU6Q (same package, ~4× lower MCU current, 160 MHz); A1/A3 reopened for its MDF/ADF filters. Bench boards: NUCLEO-U575ZI-Q. New E11 (whine listening test).

### v0.11 (2026-09-30)
- Owner: log compression becomes the only mode if it sounds better (D12). New O6: a narrowly scoped SMPS option (MCU core only, forced PWM, owner listening test) proposed; §1.2.3 unchanged pending her decision.

### v0.10 (2026-09-30) — power levers
- STM32U5 checked: its low µA/MHz needs its internal SMPS; on LDO it matches the L452, so no MCU swap. The idle-listening mode (C9) becomes the main power lever (~50% cut at 75% quiet time).

### v0.9 (2026-09-30) — peripheral vision is a no-go zone
- Owner: no part of the device may enter her peripheral vision. Estimated limit ~18 mm behind the pupil plane (110° field + 5 mm), which shrinks the pod space to ~35 mm; the pod becomes stacked and thicker; balance improves. New E10 (measure her actual field); O5 reframed.

### v0.8 (2026-09-30) — pod between eye and ear, swept-back arm
- Owner request: one pod on the temple arm between her deep-set eyes and the Ear (open) keep-out, with the transducer arm swept back. Measured on her photos: ~60 mm usable; 25–35° sweep clears the Ear (open) by 8–9 mm. New O5 (layout versus battery size and nose load).

### v0.7 (2026-09-30) — fit around the Nothing Ear (open)
- Analyzed Ear (open) geometry from official dimensions (51.3×41.4×14.4 mm, 8.1 g, 14.2 mm driver) and review photos (`docs/research/ear-open-fit.md`). Its hook junction sits above the tragus and slightly proud of the ear's front edge; its pod angles back into the concha; its speaker aims at the canal behind the tragus.
- **D1 refined:** contact on the skin just in front of the tragus, at its base, below the junction, pressing inward (not backward: T4). ~8 mm pad. The v0.6 hint "above the jaw joint" collides with the junction and is withdrawn.
- **§8:** "L/J" transducer arm dropping in front of the Ear (open); ≥5 mm clearance (≥8 mm for the vertical run); deflects away if bumped.
- **E9 new:** owner photo measurement to set the keep-out zones at true scale.

### v0.6 (2026-09-30) — runtime and balance
- **O1 resolved (owner):** ≥8 h per charge, target ~12 h, design for balance. **D18 new.**
- **§7 re-budgeted** with the tragus site (transducer drive ÷~3), low-gate-charge MOSFETs, and a 48–64 MHz clock for algorithm A (D14): ~5–8.5 mA (A), ~7.5–10.5 mA (B). The battery bay is sized for ~150 mAh (12 h in both algorithms at the pessimistic end); ≥105 mAh fits.
- **§8 re-laid-out:** electronics at the hinge, cell along the arm in front of the Ear Open hook. `sim/checks/balance.py` shows the 150 mAh layout loads the nose pads *less* (3.7 g/side) than v0.5's small battery at the hinge (4.9 g/side).
- New: C9 idle-listening power mode; D5 layout task; R16; O4 (confirm the §1.2.4 reading). R11 reworded.

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
