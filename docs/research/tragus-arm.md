# Tragus arm: how to hold ≥1 N on the skin, plus the first CAD of the pod

**Date:** 2026-09-30 · **Informs:** D1, D7, §8, E1, E2, T5 · **Checks:** `sim/checks/tragus_spring.py`, `hw/mech/pod.py`

## The problem in one line
The pad has to press the skin in front of the tragus with ≥1 N (D1). That skin moves when she
talks and chews, and several other things give way under load: the temple arm bends outward, the
temple arm twists (the pad hangs ~25 mm below it), and the pad foam squashes. A **stiff** spring
loses its force the moment any of those move. A **soft spring with a big preload** barely notices.

Assumed jaw motion: ±2 mm normal to the skin. The mouth-open photo (E9) replaces this number.

## Three ways to build the spring (arm ~20 mm long, 30° sweep)

| | A. Rigid arm on a pivot + torsion spring | B. One-piece superelastic NiTi wire | C. One-piece stainless strip |
|---|---|---|---|
| **How it works** | A small music-wire torsion spring inside the pod's rear-lower corner, pre-wound ~46° against a stop. The arm itself is rigid. | Superelastic ("memory-metal") wire bends onto a stress plateau, so the force stays about the same over many mm. The Ear (open)'s own hook is NiTi. | A flat spring-steel blade. |
| **Force over ±2 mm jaw motion** | **0.99–1.26 N** | **~1.0 N settled**, up to **~2.3 N** while putting the glasses on (hysteresis) | **Can't reach 1 N**: 0.62 N maximum below the fatigue limit |
| **Spring stress / strain** | 840 MPa in 0.65 mm wire, about 38% of its tensile strength | Strain piles up at the root; needs a curved root support so it stays under ~6% | Over its fatigue limit before it gets to 1 N |
| **Parts** | Spring Ø5.2 mm × 5 mm long, 7 turns of Ø0.65 mm wire; a pin; printed arm | Ø0.85 mm NiTi wire, heat-set to shape at ~500 °C, silicone-sleeved | 6 × 0.15 mm strip |
| **Tuning on the bench (T5)** | Easy: swap the spring, or move the preload stop | Hard: new wire, new heat-set | – |
| **Downsides** | A hinge: dirt and hair can get in, and there's a gap to seal | Force depends on history (1–2.3 N); forming NiTi is fiddly; nobody sells this shape | Doesn't work |

**Recommendation was A for the prototype; the owner chose B (see "Owner decision" below).**
- The force is predictable, it's the easiest to tune on the bench, and springs this size are
  off-the-shelf.
- B is the elegant product answer: no hinge, the same material as the Ear (open)'s hook, and a
  naturally constant force. Revisit it once T5 has shown which force she actually likes.
- C is out. It's the obvious first idea, which is why it's shown.

Material data:
- 301 full-hard stainless: yield ≥965 MPa, fatigue ~552 MPa, E 200 GPa. [ATI 301 data sheet](https://www.atimaterials.com/Products/Documents/datasheets/stainless-specialty-steel/austenitic/ati_301_tds_en_v1.pdf); [MakeItFrom, full-hard 301](https://www.makeitfrom.com/material-properties/Full-Hard-301-Stainless-Steel) (both accessed 2026-09-30).
- NiTi SE508: loading plateau ≥380 MPa at 3% strain (room temperature), E 41–75 GPa, permanent set ≤0.3% after 6% strain. [Confluent Medical material data sheet](https://confluentmedical.com/wp-content/uploads/2020/05/CONF-WDS-V3.pdf) (accessed 2026-09-30).
  - The plateau rises ~6–7 MPa/°C toward skin temperature. The model uses 450 MPa loading.
  - Unloading plateau ~200 MPa at ~7% strain. [US 6,706,053](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6706053) (accessed 2026-09-30).
  - `[Med]`: bending differs from the tension tests these numbers come from, so the bench decides.
- Music wire (ASTM A228) at 0.65 mm: tensile ~2,200 MPa, E 207 GPa (textbook values). Torsion-spring rate from the Spring Manufacturers Institute form, k ≈ E·d⁴/(67.9·D·n) per radian. `[Med]`

![force vs travel](../../sim/out/mech/tragus_spring.png) *(regenerate with the script)*

## Owner decision (2026-09-30): NiTi wire arm (option B)

What that means in practice:
1. **Wire:** superelastic NiTi, Ø0.8–0.85 mm, with an **austenite-finish temperature (Af) of about 0 °C or lower**.
   - *Why Af matters:*
     - **Above Af** the wire is superelastic: it springs back by itself, with no heat.
     - **Below Af** it acts like shape-memory wire: it stays bent until warmed.
   - The wire sits on the skin (~30–33 °C) but also sees cold outdoor days, so Af must sit below the coldest wear temperature.
     - The Confluent SE508 data sheet gives a finished-product Af of −25 to 30 °C, so the grade matters: ask for Af ≤ 0 °C.
   - *Temperature changes the force a little:* the plateau stress rises ~6–7 MPa/°C above Af (Confluent), so the pad presses a bit harder when warm than on a cold morning. The bench measures it at skin temperature.
   - *The ~500 °C step is shape-setting, done once when the arm is made.* In use the wire never needs heat. It's sold by the metre by medical-wire and hobby suppliers. Buy two diameters (0.8 and 0.9 mm) so the bench can pick the force.
2. **Shaping:** NiTi only keeps a new shape after heat-setting: clamp it in a steel jig, heat to ~500 °C for 10–20 min, then quench in water. A small hobby kiln or a butane torch with a thermocouple does it. I'll design the jig: a printed template with steel pins and screws the wire wraps round.
3. **Root support:** where the wire leaves the pod, a curved printed saddle spreads the bend over a few mm. Without it, all the strain concentrates at one point and the wire takes a permanent set (the model shows the strain piling up there).
4. **Force check on the bench:** kitchen scale under the pad at the glasses' worn position. Measure while putting the glasses on (~2 N expected) and after settling (~1 N), then again after 100 on/off cycles.
5. **Pad mount:** the transducer housing clamps onto the wire end, lying along the arm (below).

## New findings from the CAD (`hw/mech/pod.py`)

1. **Transducer orientation matters.**
   - The RC-BC02 is 12.6 mm long, so its housing is ~14 mm long, much bigger than the 8 mm contact pad.
   - Stood vertically, its top end comes within **~2 mm** of the Ear (open) hook junction. The fit rule needs ≥5 mm.
   - Laid **along the arm** (30° from vertical, top end leaning forward), the top end clears the junction by **~5.8 mm**.
   - The CAD uses the along-the-arm orientation. The smaller RC-BC95 (9.5×9×4 mm) would ease this further if E1 finds it loud enough.
2. **The reaction force goes into her glasses.**
   - The pad's 1 N inward push is matched by 1 N pushing the temple arm outward.
   - It also puts ~25 N·mm of twist into the temple arm (1 N × 25 mm drop).
   - Typical temple arms are soft in both directions. Estimated for an acetate temple: ~2 mm of pad travel lost to twist, plus a few mm to outward bending.
   - The soft preloaded spring (A or B) absorbs this; a stiff one wouldn't.
   - **New cheap test (E12):** hang 100 g (≈1 N) from her temple arm ~60 mm behind the hinge, sideways and then as a twist, and measure how far it moves.
3. **The clip must resist roll.** That 25 N·mm has to be held by the clip's top and bottom lips: about 5 N of grip on a 5 mm-tall temple arm. That's a snug snap-fit, not a slide-on.
4. **The pod stands out 9 mm** beyond the temple arm's outer face: cell (4 mm), PCB with parts on both sides (3.2 mm), walls and gaps.

## CAD numbers (first cut; positions `[Low]` until the ruler photo)

| Item | Value |
|---|---|
| Pod | 35 × 9 × 14 mm (length × thickness out from the arm × height); PA12 shell 0.8 mm; front edge on the vision limit |
| Contents | 105 mAh cell 30×4×12 against the inner wall; 20×10 mm 0.8 mm PCB outboard; mic port Ø1.0 mm at the front |
| Interference check | cell / PCB-parts envelope / shell: **0 mm³** overlap |
| Arm | pivot at the pod's rear-lower corner, 30° sweep, 20.2 mm to the pad centre |
| Pad centre | 70.6 mm behind the hinge, 25 mm below the temple arm, 3 mm inboard of the temple's inner face |
| **Mass per side** | **7.75 g**: shell 1.4, arm and housing 0.8, cell 3.0, PCB 0.9, transducer 1.2 (guess), spring/wires 0.35 |
| **Centre of mass** | 52 mm behind the hinge |
| **Load split** (hinge-to-ear 100 mm) | **nose pads 3.7 g · ear 4.1 g** per side |

Outputs are written to `hw/mech/out/`: STEP for every part; STL for the printable ones (shell, arm, pad housing, pivot boss).

## Open
- **Ruler photo (E9):** absolute positions. **Mouth-open photo:** the real jaw travel.
- **E12:** the temple arm's stiffness, sideways and in twist.
- **E1:** transducer mass and size.
- **T5:** preferred force. The spring's stop sets the preload, so it can be tuned.

## Sleeve and wiring (owner, 2026-09-30: arm 20 mm / 30°, wiring cross-section A)
Two wires (four with the pad LED, `pad-led.md`) run beside the NiTi inside a silicone sleeve. Diagram: `docs/diagrams/arm-wiring.svg`.

**Order matters:** heat-set the NiTi first (~500 °C would destroy silicone and insulation), then fit the wires and sleeve.

**Making the sleeve (ranked):**
1. **Off-the-shelf silicone tubing (recommended).**
   - **Size:** ID ~1.0–1.2 mm and OD ~2.0 mm for the two-wire version; ID ~1.4 mm and OD ~2.2–2.4 mm with the LED wires. Silicone tube stretches, so a slightly undersized ID grips.
   - **Fitting it:** wet the inside with isopropyl alcohol. Silicone swells slightly in IPA, so the bundle slides in; it shrinks back as the IPA evaporates.
   - **Finishing:** seal both ends with RTV silicone adhesive where they enter the heel and the pad housing.
2. **Dip-coating** in pourable platinum-cure silicone, several dips. The result is seamless and can be pigmented, but its thickness is harder to control.
3. **Printed TPU tube:** a 2 mm OD flexible tube is at the edge of what FDM (filament printing) can do. No.

**Wires:**
- **Type:** fine PTFE-insulated or litz (multi-strand) wire, ~0.25–0.3 mm OD. The bridge's ~0.3 A peaks are fine on this.
- **Routing:** twist them loosely around the NiTi, about one turn per 10 mm, so bending doesn't stretch them.
- **Strain relief:** leave a slack loop inside the pod.
