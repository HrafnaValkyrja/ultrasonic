# Adversarial audit report, 2026-09-30 (partial, synthesised by hand)

**How this was produced.** A multi-agent audit ran on Valhalla and was stopped after it twice destabilised the machine (`docs/incidents/2026-09-30-oom.md`). By then it had finished 10 of 12 area audits and 1 of 4 independent re-derivations; skeptic verification had covered the power and layout findings plus NM-1. The results were saved to disk. This report was written by reading them in a single process, plus one small hand check of the critical finding. **Correction:** Claude's first hand check of MP-01 had a feedback-sign bug (the shaper wasn't shaping) and reported −33.8 dB by coincidence. The corrected model reproduces the project's known −87 dB audio-band figure and gives −35.0 dB in the mic band, so the finding stands, now properly verified. **Nothing here comes from the synthesis stage, which never ran.**

- **Raw results:** `../ultrasonic-scratch/done.json` (47 agent results).
- **Legend:** ✅ skeptic-verified · 🔁 reproduced by Claude during synthesis · ◻ auditor's claim, not yet independently verified.

## Verdict
The *wiring* is trustworthy; the *numbers told to the owner* are not.
- **Every connection check held:** MCU pins against the current datasheet, netlist against board, pin against pad.
- **The simulations reproduce exactly:** the same inputs give the same outputs.
- **But several headline claims are properties of how the tests were written,** not of the design: battery life, silence, "stays in 1.5–4 kHz", the NiTi spring force.
- **There is one real design problem the process missed:** shaped PWM noise in the mic's band.

## Design problems to fix (ranked)
| # | Finding | Status | Consequence | Direction |
|---|---|---|---|---|
| 1 | **MP-01. Shaped PWM noise sits in the mic band.** The 3rd-order shaper at 200 kS/s puts quantisation noise at −34 dB re FS in 20–85 kHz on the bridge output. "Switching leakage lands at 0 Hz" is true only of the PWM carrier, not this noise. | 🔁 −35.0 dB (voltage), −59 dB (coil current): `sim/checks/pwm_ultrasonic_leak.py` | If it couples back to the mic (supply, ground, or transducer vibration), the device hears itself: false wakes, a raised floor, possible feedback | PWM rate is a **firmware** setting, so no hardware decision is needed now. 800 kHz at the same 80 MHz clock gives −59 dB (24 dB better) for about +0.8 mA; 400 kHz gives −45 dB for +0.3 mA. Measure the coupling on the bench (S2) and choose then. |
| 2 | **mech-1/2/3. The NiTi force chart is not a model past ~3 mm.** The curve is a hard-coded flat line there, and the 5–9 mm operating band sits in it. A hysteretic, large-deflection re-model gives **1.1–2.7 N swinging with jaw motion** (not "~1 N"), and root strain above the 6% recovery limit. | ◻ | The owner chose NiTi (O7) partly on this chart | Reopen O7 with honest curves; NiTi may still win, but on correct numbers |
| 3 | **dsp-1/2 + PWR-01/02. Battery life is optimistic.** The idle detector's filters wake on audible speech; the synthetic scene's whines masked this. A room without electronics gives **67% awake, not 14%**. Separately, the "pessimistic" runtime varies current but never capacity, and mic current is quoted at 1.8 V / 3.072 MHz instead of our 3.0 V / 4 MHz. | PWR-01/02 ✅ major; dsp ◻ | "12–15 h always-on" is not a worst case | Steeper idle-detector filters; re-derive mic current; add a capacity/temperature derate |
| 4 | **NM-1. PA10 sees 5 V from the charger's STAT pin while relying on the MCU's internal pull-up**, which DS13737 forbids. | ✅ confirmed | Pin stress; out of spec | External pull-up to 3.0 V plus a series resistor, or a divider |
| 5 | **Board file issues:** declares 1.6 mm with no stackup (spec says 0.8 mm) (LD-04 ✅ minor); TPS7A20 footprint pads oversized, VBAT pad 0.134 mm from a neighbour (FP-1 ◻); mic port 0.5 mm, below spec (FP-3 ◻); 7 of 8 EasyEDA footprints never checked against the maker's land pattern (FP-2 ◻); the SMPS loop is a placement problem, VDD11 pin 46 has no cap (LD-05 ✅) | mixed | Manufacturability and SMPS noise | Fix in the owner's real layout; redraw footprints from maker figures |

Also confirmed, smaller: the charger can't terminate while the device runs, because system load exceeds ITERM (PWR-05 ✅ minor; ageing, not a hazard); peripheral current understated; gate pulls missing from the budget.

## Method flaws (how Claude worked)
1. **Self-referential validation** (MP-02/03 ◻). The same author wrote the scene, the model and the test. "Stays inside 1.5–4 kHz" is true by construction of the synthesiser. The 14% figure is scene timing plus hang time.
2. **Numbers quoted to the owner beyond what the method supports:**
   - The quiet-signal distortion "−61 dB" is set by solver tolerance; with realistic noise-shaped duty it's about −50 dB (SB-3/4 ◻).
   - The 12.5 ns bridge figures come from the stand-in FET's slow gate and don't transfer to the PMCXB290UE (SB-2 ◻).
3. **"DRC clean" was an error-only run,** with 163 warnings never generated, and clearance was relaxed after routing (LD-01/02 ✅ minor).
4. **The spec is stale after the MCU change** (MP-07 ◻). D5 still lists the L452 pin map; §7 leads with a superseded table.
5. **Citations:** 22 checked, mostly accurate. But the NiTi 200 MPa unloading plateau and 6–7 MPa/°C slope are **not in the cited sources** (RC-01, mech-4 ◻), and the "+10 dB at the tragus" is a cross-study derivation (RC-02 ◻).
6. **Self-caught errors were logged, not tracked** (MP-06 ◻). There's no issue list or gate, so corrections get orphaned.

## What held up (independently checked)
- **MCU:** all 49 U1 pins against DS13737 **Rev 10** and the KiCad symbol; alternate functions; SMPS component values.
- **Netlist and board:** regenerated netlist identical to `pod.net`; all 143 pad nets on the correct pads; nothing mirrored, bottom-side flips included.
- **Independent netlist from the datasheets** (repro-netlist): every supply, ground and signal pin matched.
- **Power:** every MCU current figure against DS13737 Rev 10, including the debunking of the 19.5 µA/MHz headline.
- **Simulations reproduce:** DSP numbers across 15 seed combinations; the bridge SPICE table; hand calculations of ripple and I²R.
- **Mechanics:** torsion-spring, steel-strip, mass and centre-of-mass arithmetic.

## Not covered
- Audits: "everything except the MCU" wiring (netlist-other).
- Re-derivations: bridge (repro-bridge) and the "proper sim" feasibility study.
- Skeptic verification: most findings outside power and layout.
- The completeness critic and synthesis.

## What this says about the process
Checks against a document held up; checks against Claude's own models didn't. Next time:
- Every owner-facing number needs a named, independent check before it's quoted.
- Tests must use inputs the model's author didn't design: the real Port Meadow recordings, not synthetic scenes.
- The next step for #1–#3 is **bench measurement**, not more simulation.
