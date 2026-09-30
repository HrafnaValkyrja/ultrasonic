# Pad LED ring: can the transducer's ring glow? (2026-09-30)

Owner asked: light the ring on the pad housing with an LED if current and packaging allow; otherwise airbrush it chrome.

**Verdict: it fits.**
- **Wiring:** one 0402 LED in the pad, one resistor on the board, one spare MCU pin, and two more hair-thin wires in the arm sleeve.
- **Current:** about 0.15–0.5 mA while it glows.
- **Cost:** 0.1–0.3 h of the worst-case always-awake runtime. **That pushes the pessimistic always-awake case just under the 8 h minimum (7.7–7.9 h)**, so the firmware needs a rule (below).
- **Visibility:** visible indoors and at night; invisible in daylight.

## Part
**Everlight 16-213/BHC-AN1P2/3T.** "16-213" is Everlight's 0402 (1.0 × 0.5 mm) chip-LED series; "BHC" is its blue InGaN die.
- JLC C131223, Extended, 25,783 in stock, $0.029 (JLC parts API, 2026-09-30T22:23Z).
- Datasheet: Everlight DSE-0008890 Rev 3, 2013-05-29 (via the LCSC product record).

| At I<sub>F</sub> = 5 mA | Min | Typ | Max |
|---|---|---|---|
| Luminous intensity | 28.5 mcd | — | 72 mcd |
| Forward voltage | 2.7 V | 3.3 V | 3.7 V |
| Dominant wavelength | 464.5 nm | — | 476.5 nm (blue) |
| Viewing angle | — | 120° | — |

- **Brightness at our currents:** at 0.3–0.5 mA it should give roughly 2–7 mcd `[Med]`: the rating scaled linearly, which InGaN roughly follows at low current. That's a clearly visible glow indoors or at night, spread around a ~5 mm ring. In daylight it disappears.
- **Colour:** blue, not the render's cyan. A true 505 nm cyan chip would need a separate search.
- **The dimmer bin:** 16-213/BHC-ZL1M2QY (C2987024) is 11.5–28.5 mcd; avoid it.

## Circuit
**VBAT → R (≈2 kΩ, on the board) → wire → LED (in the pad) → wire → PB7 (open-drain, TIM4_CH2 PWM).**
- **Why VBAT and not the 3.0 V rail:** the LED needs 2.6–2.7 V even at 0.5 mA (datasheet curve starts at 2.6 V). From 3.0 V the headroom is ~0.3 V, so brightness would vary a lot between parts and with temperature. VBAT (3.3–4.2 V) gives headroom, and the LED current bypasses the LDO.
- **Why PB7:** it is free (A3-u575-plan.md §3), 5 V-tolerant "FT", and has TIM4_CH2 for PWM (DS13737 Rev 8 pin table: pin 43, FT_). With the LED off, the pin sees up to VBAT minus the LED drop. That is under 4.2 V and within FT limits while VDD is up. In Stop 2 / Off the pin is high-impedance and the LED is dark.
- **Brightness vs battery:** it drifts from ~0.35 to ~0.75 mA over the battery's range. Firmware already reads VBAT (PA4), so it scales the PWM duty to hold the brightness steady.
- **New parts:** R (0402) and two solder pads. No new silicon besides the LED.

## Runtime (105 mAh; `sim/checks/power.py` rev-2 currents)
| Ring | Always awake (pessimistic–nominal) | Quiet room, 18% awake |
|---|---|---|
| none | 8.0–13.2 h | 17.2–29.5 h |
| follows activity, avg 0.15 mA while awake | 7.9–12.9 h | 17.1–29.3 h |
| follows activity, avg 0.3 mA | 7.8–12.6 h | 17.0–29.0 h |
| steady 0.5 mA while awake | 7.7–12.3 h | 16.9–28.7 h |

**Recommended firmware behaviour:**
- **Owner, 2026-09-30: solid, as a power-on indicator. No pulsing; battery cost accepted.** That's ~0.5 mA whenever the device is on, including idle. Always-awake worst case: 7.7 h; quiet room: ~15.5 h pessimistic.
- ~~Brightness follows what it hears~~ (dropped).
- The button toggles it.
- It turns off automatically below ~20% charge.

That keeps the ring mostly dark in quiet places, and the always-awake pessimistic case back at the 8 h minimum when it counts.

## Building it (the owner's concern)
The hard part is soldering fine wires to a 1.0 × 0.5 mm LED by hand. Ways to make it easy:
1. **Buy LEDs that come pre-wired.** Model-railway and scale-model shops sell 0402/0603 SMD LEDs with ~0.1 mm enamelled leads already soldered (`[Med]`: a common hobby item, no specific listing checked yet). Then the only joints are two big pads on the board.
2. **Use an 0603 (1.6 × 0.8 mm) instead of an 0402.** It is much easier to hand-solder and still fits under a 5 mm ring. Same circuit.
3. **Build the pad in this order:** LED glued face-up in its pocket → leads out through the wire hole → clear epoxy poured into the ring groove over it → transducer and wires → potting.

## Packaging options (ranked)
| | How | Wires in the sleeve | Verdict |
|---|---|---|---|
| **A** | LED in the pad housing under the ring groove. The groove is filled with clear epoxy, which diffuses the light into a ring. | 4 (2 transducer + 2 LED) | **Recommended.** One tiny part in the pad; the sleeve grows from Ø1.8 to ~Ø2.2 mm |
| B | LED on the board; a 0.25–0.5 mm plastic optical fibre runs down the sleeve to the ring | 2 + fibre | Coupling a chip LED into a fibre loses ~90%, so it needs ~5× the current. No |
| C | No LED: airbrush the ring chrome | 2 | The fallback |

Also: the ring faces outward, on the side of the head, so the wearer never sees it. The LED's PWM current flows on VBAT, not the regulated rail; run the PWM above 20 kHz so any residue is inaudible.
