# C3: output stage — PWM noise, dead-time linearity, bridge implementation

**Date:** 2026-09-30 · **Status:** design direction settled on paper. The final numbers wait on E1 (the transducer's coil inductance) and on S2 listening.
**Scripts:**
- `sim/checks/pwm_noise.py`: quantization noise
- `sim/checks/ntf_compare.py`: noise-shaper designs
- `sim/checks/deadtime_switching.py`: dead-time distortion, switching-level model

**All three are idealized models. The bench (S2) is the arbiter.**

## Summary
1. **Quantization noise is not the problem.** v0.3 called it the top risk; that was wrong. With a 3rd-order noise shaper, PWM noise sits ~90 dB below full scale across 0.2–20 kHz. Bone-conducted ultrasound needs 55–60 dB more drive to be heard than the 2–4 kHz band does, so the 20–40 kHz residue isn't a concern either (`bone-conduction.md` §5).
2. **Low-level linearity is the real risk.** The culprit is *dead time*: the few nanoseconds per switching edge when both transistors in a bridge leg are off, which prevents a short circuit. That brief gap distorts quiet signals badly under 3-level ("BD") modulation, the scheme v0.3/v0.4 leaned toward.
3. **Fix: 2-level ("AD") modulation.** With the two legs driven as complements, the coil's ripple current crosses zero every PWM period, and the dead-time errors of the two edges cancel exactly. This holds as long as the ripple current is bigger than the signal current, which is true at quiet listening levels. The ripple costs only 0.04–0.4 mW at idle.
4. **Integrated H-bridge ICs are out.** Their fixed internal timing is 10–40× coarser than the MCU timer's. Build the bridge from two complementary MOSFET pairs driven directly by TIM1.

## 1. Quantization noise (200 kHz PWM, 201 levels, TPDF dither, −30 dBFS test tone, 0.3 mH / 8 Ω coil)

| Noise shaper | 0.2–8 kHz | 8–20 kHz | 20–40 kHz |
|---|---|---|---|
| 2nd order, zeros at DC | −90 dB | −77 dB | −69 dB |
| 2nd order, zero pair at 11 kHz | −76 | −83 | −71 |
| **3rd order, DC zero + pair at 13 kHz** | **−93** | **−90** | **−72** |

All figures are dB relative to a full-scale sine, after the coil's low-pass.

**Why 8–20 kHz matters:** at the zygomatic process, bone-conduction thresholds from 8 to 16 kHz track normal air-conduction hearing (Popelka 2010), and the owner hears unusually high. The 3rd-order shaper buys 13 dB there over plain 2nd order.

**Recommendation:** 3rd-order error-feedback shaper with an in-band zero pair (~13 kHz, tuned in C3). It costs a few more multiplies per PWM sample, already inside the C2 budget.

**While squelched, turn dither off.** A zero-signal input then quantizes exactly to the centre level, so the output is a clean 50% square wave with no noise at all (T6).

## 2. Dead time: BD vs AD (switching-level model, worst case)

In-band THD+N of the transducer current (dB relative to the signal) at 200 kHz, Vbus 3.0 V, 8 Ω, 2.5 kHz tone:

| Coil | Modulation | Dead time | −20 dBFS | −30 dBFS | −40 dBFS | Idle loss |
|---|---|---|---|---|---|---|
| 0.3 mH | BD (3-level) | 12.5 ns | −29 | −20 | **−10** | 0 |
| 0.3 mH | BD | 25 ns | −24 | −15 | −5 | 0 |
| 0.3 mH | **AD (2-level)** | 12.5–100 ns | −31 to −15 | **clean** | **clean** | 0.42 mW |
| 1.0 mH | BD | 12.5 ns | −25 | −15 | −5 | 0 |
| 1.0 mH | **AD** | 12.5 ns | −25 | −18 | **clean** | 0.04 mW |

"Clean" means the error falls to numerical zero: the edge errors cancel.

**What sets AD's clean range:** the idle ripple current, about Vbus / (4·L·f_PWM). That's 12.5 mA at 0.3 mH and 3.75 mA at 1 mH. Signals whose current peak stays below it are distortion-free. Louder ones distort about as much as BD.

**What the clean range means for listening:**
- Typical quiet listening is probably −30 to −50 dBFS (E2 will pin this down), and that range is covered.
- Loud events distort somewhat, but they're rare and mask their own distortion.

**If E1 finds a high inductance** (≥1 mH, like the one bone transducer with published data: 1.26 mH, 5.8 Ω), then:
- **(a)** drop the PWM to 100 kHz (ARR = 400). This doubles the ripple and gives 401 levels, at the cost of noise-shaping headroom; or
- **(b)** accept distortion above ~−40 dBFS.

**Firmware notes:**
- Dead time 1–2 timer ticks (12.5–25 ns), set by the MOSFETs' measured switching speed.
- Keep the PWM running (square wave, zero average) through short squelch gaps. Starting and stopping the ripple makes a small click.
- For long silences and Off, stop it with a soft start/stop: a half-width first pulse centres the ripple.

**Model limits:**
- Hard switching is assumed. Real node capacitance softens dead-time error at small currents, which helps BD more than it helps AD.
- There is no MOSFET resistance or transducer back-EMF.
- S2 measures real low-level distortion, with a current-sense resistor and a sound card.

## 3. Bridge implementation

| Option | Timing | Idle / active current | Size | Verdict |
|---|---|---|---|---|
| **Discrete: 2× complementary N+P MOSFET pairs, gates driven by TIM1 CHx/CHxN** | Dead time set by us in 12.5 ns steps; edges ~10–30 ns | Gate charge only: 4 FETs × 0.5–2.5 nC × 200 kHz = **0.4–2 mA**, so low gate charge is a B1 criterion `[Med]` | 2× SOT-563 (1.6×1.6 mm) + 4 pull resistors | **Recommended** |
| DRV8837: TI 1.8 A H-bridge IC, 2×2 mm | 160–200 ns delays, 30–188 ns edges; PWM max 250 kHz | 0.7 mA supply current at only 50 kHz PWM, rising with frequency | 2×2 mm | Too coarse and too hungry at 200 kHz |
| DRV8210: TI H-bridge, 1.6×1.6 mm | PWM max **100 kHz**, 500 ns internal dead time | nA sleep | smallest | Out |
| DRV8833: TI dual H-bridge (the v0.4 bench module) | 450 ns dead time, 450 ns input deglitch, 1.1 µs delay | — | module | **Out, even for the bench** (see §4) |

Sources: TI datasheets SLVSBA4F (DRV8837/8838, rev. Apr 2021), SLVSFY8B (DRV8210, rev. Aug 2021), SLVSAR1E (DRV8833).

**MOSFET-pair candidates in stock at JLC (2026-09-30), for task B1 to pick from:**
- **NTZD3155C**: onsemi N+P pair, SOT-563, 20 V, ~0.4–0.9 Ω, 2.5 nC. C236117, Extended, 8,788 in stock, $0.17.
- **DMC2400UV**: Diodes Inc. N+P pair, SOT-563, 0.48 Ω at 5 V, 0.5 nC gate charge. C177025 (113 in stock) or the TECH PUBLIC equivalent C2940616 (3,836 in stock).

B1 needs to check on-resistance at **3.0 V** gate drive and pick the part.

**Mandatory:** pull resistors that hold every gate "off" from reset until TIM1 takes over (`A3-clock-and-peripherals.md` §4): pull-up on P-channel gates, pull-down on N-channel gates.

## 4. Consequence for the bench plan (S2)

The DRV8833 module's timing is 30–40× coarser than the final design. S2 results on it (distortion, and whether quiet signals sound clean) wouldn't transfer. **Replace it with a small JLC-assembled discrete-bridge test board:**
- 2 MOSFET pairs and gate pulls;
- bulk capacitor (low-acoustic-noise type, see below);
- a 1 Ω current-sense resistor for measurements;
- a header to the Nucleo's TIM1 pins.

It goes in the same JLC order as the acoustic test coupons.

**Capacitor note:** ordinary X5R/X7R ceramic capacitors are slightly piezoelectric and can "sing" when voltage ripple at audio frequencies sits across them. Keep audio-rate ripple off them, or use a low-acoustic-noise type on the bridge supply. The mic datasheet separately forbids Class-2 ceramics near the mic.

## 5. Transistor-level check with a real MOSFET model (v0.13, 2026-09-30)

`sim/checks/bridge_spice.py` runs ngspice 42 on the full bridge:
- **MOSFETs:** the DMC2400UV model from Diodes' own SPICE collection (model v1.0, 2014-11-18). It stands in for the recommended PMCXB290UE, whose model is behind Nexperia's bot wall; the two have similar gate charge and on-resistance.
- **Supply and drive:** 3.0 V rail modelled as 0.3 Ω, 22 µF and 100 nF; GPIO gate drive with 2 ns edges through 30 Ω; 100 kΩ gate pulls.
- **Load:** 35 pF ESD diode per lead; coil modelled as 8 Ω plus 0.3 mH or 1.26 mH.
- **PWM:** AD modulation, 200 kHz, centre-aligned. Duty is not quantised; quantisation is the noise shaper's job (`pwm_noise.py`).

| Dead time | Idle bus current (0.3 / 1.26 mH) | THD+N, −40 dBFS | THD+N, −12 dBFS (ceiling) |
|---|---|---|---|
| 0 | **4.3 / 4.2 mA** (shoot-through) | – | – |
| 12.5 ns (1 tick) | 0.49 / 0.42 mA | **−61 dB** | **−52 dB** |
| 25 ns (2 ticks) | 0.20 / 0.10 mA | −48 dB | −38 dB |
| 37.5 ns (3 ticks) | 0.21 / 0.08 mA | −44 dB | −33 dB |

Gate drive from the GPIOs: 0.28 mA at every dead time, for 4 FETs at 200 kHz.

**What it means:**
- **Dead time is mandatory.** With none, the model's P-channel turns off slowly (~10 ns through its internal 68 Ω gate resistor) and both FETs conduct: 4.3 mA wasted at idle.
- **One tick still leaks a little.** At 12.5 ns the P-channel isn't quite off before the N-channel turns on. That's a ~2 mA spike each edge, about +0.3 mA on average. It's harmless to the parts.
- **Quiet signals stay clean** (−48 to −61 dB). This confirms the AD choice: the coil's ripple current is larger than the signal current, so each edge commutates the same way and the dead-time error doesn't depend on the signal.
- **Loud signals near the ceiling pick up odd harmonics.** Once the signal current (~85 mA peak at −12 dBFS) exceeds the ripple (~12 mA peak), the current direction stops reversing every cycle, and dead time distorts like a class-D amplifier with no dead-time correction.

**Options (a firmware register, not a hardware decision):**
1. **12.5 ns:** cleanest sound, costs ~0.3 mA (~5% runtime).
2. **25 ns plus dead-time compensation in firmware:** add or subtract the dead time to each duty according to the predicted current direction. The load is known, so the direction is too. That recovers most of the loud-signal distortion at 0.2 mA idle.
3. **25 ns, no compensation:** −38 dB at the ceiling. The ceiling is rare, and the transducer's own distortion is likely larger.

**Recommendation:** start at 12.5 ns on the bench (S2), measure the real PMCXB290UE, then try option 2. The owner doesn't need to decide anything here.

**Testbench bugs found and fixed while doing this.** They're kept here because they'd fool anyone repeating the check:
1. PWL edge times printed with 5 significant digits rounded ms-scale edges to 100 ns.
2. Centring both legs' pulses on the same instant produced BD, not AD: identical legs at zero signal, so no coil current.
3. Snapping edges to the 12.5 ns timer tick made −40 dBFS look like −17 dB THD+N. That's quantisation, not analog distortion.
4. Resampling the coil current to 400 kS/s aliased the 200 kHz sidebands into the audio band.

**ngspice notes:**
- The model's ideal "DLIM" limiter diode stalls the timestep. `sim/spice/models/DMC2400UV_ng.lib` adds RS = 10 mΩ and CJO = 1 fF to that diode only.
- The two legs switching at exactly the same instant also stalls it. A 100 ps skew between legs, realistic for GPIO pins, avoids that, and the signal runs use a 1.9 ms record.
