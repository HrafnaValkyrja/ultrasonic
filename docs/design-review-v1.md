# First design review: Stereo Ultrasound, one side

**Date:** 2026-09-30 · **Spec:** v0.13 · **Status:** a complete first design on paper and in simulation. Nothing is bought or built.

This is the whole design in one place: what it is, what the simulations say, what's still a guess, and what you need to decide.
Every number links back to the script or note that produced it. Diagrams are in `docs/diagrams/`; the renders regenerate from the scripts named below.

---

## 1. What one side is

![system](diagrams/system-overview.png)

- **Listen:**
  - The **SPH0641LU4H-1** (an ultrasonic-capable digital MEMS microphone, 3.5×2.65 mm) hears 20–85 kHz.
  - The **STM32U575** (a low-power Arm Cortex-M33 microcontroller, 7×7 mm) turns the mic's 1-bit stream into samples in hardware, using its ADF filter.
  - Every 0.64 ms it measures 28 log-spaced bands.
- **Squeeze:**
  - Each band becomes a gentle tone. 20–85 kHz maps logarithmically onto 1.5–4 kHz, so every octave of ultrasound keeps its share of the audible range.
  - Steady whines (chargers, LED drivers) are gated out by default.
  - Only changing sounds come through: bats, insects, keys, rangefinders.
- **Speak:**
  - The chip's motor-control timer switches an H-bridge of two **PMCXB290UE** transistor pairs (each a tiny matched N+P switch, 1.1×1.0 mm) at 200 kHz.
  - That drives the **RC-BC02** bone-conduction exciter pressed on the skin just in front of your tragus.
- **One clock** paces everything, so switching leakage can only land at 0 Hz, where it's filtered out.

## 2. Does it work? (simulation)

| Question | Answer | Source |
|---|---|---|
| Do bats come out as usable sound? | Yes. Calls become 2–3 kHz chirps; everything stays inside 1.5–4 kHz with no clicks | `sim/dsp/run_phase1.py` (listen: `sim/out/dsp/b_transient.wav`) |
| Are whines removed? | Yes, in the default mode: charger and LED tones are completely gone | same |
| Is it silent when nothing's there? | Output −80 dBFS with only the mic's own hiss (T6) | same |
| How much of the time must the chip be fully awake? | 14% on a simulated quiet evening, catching all 4 events within 10 ms | same |
| Does the output stage stay clean? | Quiet sounds −61 dB distortion+noise; at the loudness ceiling −52 dB | `sim/checks/bridge_spice.py` (real Diodes MOSFET model) |
| Is the PWM switching audible? | No: noise is pushed above 13 kHz and the carrier sits at 200 kHz (earlier check) | `sim/checks/pwm_noise.py` |

All the test sounds are synthetic. Real recordings replace them in Phase 1 (C1, S1).

## 3. Battery life

![runtime](../sim/out/power/runtime.png)

- **Full chain awake:** 4.6–7.5 mA. **Idle** (listening for activity): 1.5–2.4 mA.
- **With the 105 mAh cell:**
  - awake all the time: **11.9–15 h**;
  - quiet evening: **29–37 h**.
- Your 8 h minimum is met in every case; 12 h is met at nominal draw even if the chain never sleeps.
- **Correction since last time:** the U5's power saving is ~45%, not ~75%. The headline figure only applies in a slow mode we can't use for audio.

## 4. Size, weight, balance

![pod](../hw/mech/out/pod_views.png)

- **Pod:** 35 × 9 × 14 mm, clipped to the outside of the temple arm, front edge on your peripheral-vision limit.
- **Inside:** a 105 mAh cell against the inner wall, the 20×10 mm board outboard of it, the mic porting outward at the front.
- **Weight:** 7.75 g per side. **3.7 g on the nose pads and 4.1 g on the ear.**
- **Arm:** sweeps back 30° to the pad. The transducer housing lies *along* the arm, which keeps it 5.8 mm from the Ear (open) hook. Upright, it would be 2 mm away.

## 5. The tragus spring (your decision: O7)

![spring](../sim/out/mech/tragus_spring.png)

| | A. Rigid arm + torsion spring at a pivot | B. Superelastic NiTi wire arm |
|---|---|---|
| Force while you talk/chew (±2 mm) | **1.0–1.3 N**, predictable | ~1.0 N settled, up to ~2.3 N while putting the glasses on |
| Tuning on the bench | Swap the spring or move its stop | New wire, new heat-set at ~500 °C |
| Downside | A small hinge (dirt, hair) | Force depends on history; fiddly to form |

**Recommendation: A for the prototype.** B is the product candidate once T5 tells us which force you like. A plain steel strip (the obvious idea) can't hold 1 N without fatiguing.

## 6. The board

<!-- BOARD_RESULTS -->

- **Schematic:** `hw/pod/gen.py` (code is the source of truth) → `hw/pod/pod.net`. ERC: 0 errors.
- **41 parts, every one with a JLC part number** (`hw/pod/bom_jlc.csv`, stock checked 2026-09-30).
- **Parts cost ≈ $13 per board.** The MCU is $8.93 of that. There are 10 Extended lines, each with JLC's per-order loading fee.
- **Main parts** (`docs/research/B-parts-selection.md`):
  - MCP73831: single-cell charger, 45 mA.
  - TPS7A2030: 3.0 V linear regulator, 1×1 mm, 7 µV noise.
  - DFE201610E: 2.2 µH shielded inductor for the MCU's core regulator.
  - FC-135: 32.768 kHz watch crystal.
  - KXT321LHS: 3×2 mm push button.

## 7. What's still a guess (top risks)

| Risk | Why it matters | How we find out |
|---|---|---|
| Transducer loudness and inductance (R1, R2) | Nobody publishes the RC-BC02's inductance; the sellers' specs disagree | E1: measure one (first thing we buy) |
| Comfort at ≥1 N with jaw motion (R6) | The whole T5 test | E2 with the spring on your glasses; your mouth-open photo |
| Temple arm flexes under the pad (R17) | Eats the spring's travel; the pod could roll | E12: a 100 g weight on your temple arm |
| SMPS whine (D11) | Your hearing is unusually good | E11: you listen to a running board in a quiet room |
| Mic clock and filter details (R13, R18) | ST and the mic maker leave gaps | S1: scope and sweep on the dev board |

## 8. What I need from you

1. **O7:** spring A (recommended) or B.
2. **O5:** keep the 105 mAh stacked pod (recommended; 80 mAh would miss 12 h if the chain never sleeps).
3. **O3: approve the bench shopping list.** Prices come from search results on 2026-09-30 `[Med]`; re-check at checkout.

   | Qty | Item | What it's for | Each | Where |
   |---|---|---|---|---|
   | 2 | NUCLEO-U575ZI-Q | ST dev board with our exact MCU and its SMPS: firmware, S1–S3, the E11 whine test | ~$24.08 | [DigiKey](https://www.digikey.com/en/products/detail/stmicroelectronics/nucleo-u575zi-q/15218436) (519 in stock) · [Mouser](https://gr.mouser.com/en/new/stmicroelectronics/stm-nucleo-u575zi-q-board/) |
   | 3 | RC-BC02 bone exciter, from two sellers | The transducer we designed around; E1 measures its real size, resistance and inductance | ~$4–5.50 | [maker](http://www.digitalaudioamp.com/product/bonetransducerRC-BC02-1.html) · [Alibaba](https://www.alibaba.com/product-detail/RC-BC02-thin-bone-conduction-transducer_62023855763.html) |
   | 1 | Dayton BCE-1 bone exciter | Known-good reference to compare loudness against | $11.19 | [Dayton](https://www.daytonaudio.com/product/1170/bce-1-22-x-14mm-bone-conducting-exciter) / Parts Express |
   | 2 | Elecrow SPH0641 mic board | The ultrasonic mic on a breakout, for S1 before our own boards exist | $12.50 | (spec §10) |
   | 2 | Adafruit #1570 100 mAh LiPo | Bench battery, about our size | $5.95 | [Adafruit](https://www.adafruit.com/product/1570) |
   | 1 | JLC order: 5 bridge test boards + 5 mic port coupons | S1, S2 | ~$40–60 est. | I design it; you order it |

   **Total ≈ $160–190** plus shipping. The transducers ship slowest, so they go first.
4. **O4:** confirm the reading of §1.2.4: cell along the arm, in front of the ear, nothing behind it.
5. **Photos and quick tests you can do at home:**
   - ruler photo and mouth-open photo (E9);
   - pen-tip vision check (E10);
   - 100 g temple-arm test (E12).

## 9. What happens next

1. **Phase 1:** real recordings instead of synthetic ones; firmware skeleton on the Nucleo (ADF capture → FFT → oscillators → PWM).
2. **Phase 2 bench:** transducer measurements (E1), H-bridge test board, acoustic port coupons (S1), and the SMPS listening test (E11).
3. **Phase 3:**
   - you lay out the real pod board in KiCad from `pod.net`; my draft placement shows it fits;
   - I review it, run DRC and prepare the JLC files;
   - you place the order.
