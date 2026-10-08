# R-exciter: higher-Bl exciter for the 208 mA clamp (rabbit trail, 2026-10-08)

Question: loudness.md says a 70 dBA street needs ~+20 dB that firmware cannot give. Force = Bl x I at a fixed 208 mA clamp, so gain over the current model (Bl 1.0 N/A **assumed**, shared-params exciter, RC-BC02 class, E1 unmeasured) is first-order 20 log10(Bl_new / 1.0). Above f0 an exciter's reaction force on the pad is Bl x I, so equal current gives equal-ratio force. Sensation-level gain equals force gain only if pad coupling and threshold are unchanged (loudness.py chain: SL = force - threshold). Bone.py's pad/mass model was not re-run; this is a hand estimate.

## Data found (web, 2026-10-08)
Almost no vendor publishes force or Bl for small exciters. Real Bl exists only for the Dayton BCT-3.

| Part (gloss) | Bl | Re / Le | Fs | Mms | Size / mass | Price | Force @208 mA | Gain vs 1.0 |
|---|---|---|---|---|---|---|---|---|
| Dayton BCT-3, 44x32 mm bone-conducting transducer, 15 W | **4.41 T m** | 3.9 ohm / 0.34 mH | 236 Hz | 6.1 g | 44x32 mm face; depth blank on datasheet (unverified); ship wt 0.27 kg | $32.99 MSRP | 0.917 N = 119.2 dB re 1 uN | **+12.9 dB** |
| Dayton BCE-1, 22x14 mm, 1 W | N/A (not published) | 4.0 ohm / 0.56 mH @10 kHz | 2100 Hz | N/A | 21.2x14.4x7.8 mm, 2.3 g (third-party listing; Dayton: 0.85x0.57x0.31 in) | not retrieved | unknown; if Bl 1-2: 0.21-0.42 N | 0 to +6 dB, no basis |
| Tectonic TEBM65C20F-4, 65 mm full-range exciter (BMR family) | 3.75 T m (search snippet, secondary, unverified) | 4 ohm | n/a | 5.6 g | ~65 mm, tens of mm deep; not wearable | n/a | 0.78 N = 117.8 dB | +11.5 dB |

Not found: Goertek, AAC, Sonion (page lists sensitivity columns without readable values), Knowles BU-21771/BU-23173 (7.92x5.59x4.14 mm, but listed as a piezo accelerometer sensor, not an exciter), Shokz transducers (spec: 8.5 ohm +-20%, 105 +-3 dB, no Bl or size). Vendor requests would be needed.

## Shortlist
1. **BCT-3**: only part with a real Bl. +12.9 dB, closes about two thirds of the 20 dB street gap (about 7 dB short; firmware limiter's +6.3 dB is already inside loudness_fw numbers). Lower Re (3.9) needs only 0.81 V; clamp power 84 mW. **Size cost: 44x32 mm face against a pod of T 6.4 / H 14.8 / 50.65 long, and 6.1 g moving mass in a 11-13 g pod. Does not fit; reference ceiling only.**
2. **BCE-1**: fits-class (21x14x7.8 vs T 6.4: 1.4 mm thicker; sits near the current part's size) but Bl unpublished. Cheap to buy one and measure Bl on the E1 rig (LCR + shaker/accelerometer). Gain 0 to +6 dB at best guess.
3. **TEBM65C20F-4**: Bl corroborates that +11 to +13 dB needs a 45-65 mm class motor; listed only to show the size/Bl trade, not a candidate.

## Verdict
Best gain +12.9 dB (BCT-3), size cost about 7x the pod's footprint area class; no miniature (under 8 mm thick) exciter with published Bl >= 3 was found. Bl scales roughly with magnet volume, so thin pods stay in the Bl 1-2 class. A piezo bender (voltage-drive, ~tens of V) would need a boost converter, breaking D11, so not pursued. Street alert at 70 dBA looks unreachable by exciter swap inside T 6.4; more likely route is a lower-bar street alert plus resonance/pad tuning (loudness.md lever 3, +6-10 dB).

Recommended next: buy one BCE-1 for E1 (owner decides; O21 no orders until freeze, so bench-only budget call), request Bl/force data from Sonion and Goertek, and measure the actual RC-BC02 Bl first, since the 1.0 baseline is itself assumed.

Sources (all fetched 2026-10-08): daytonaudio.com BCT-3 spec sheet 295-269 (Rev 3.1.0, 2020-06-11) and product 1676; daytonaudio.com BCE-1 spec sheet 240-614 (2025-05-09); audiophonics.fr BCE-1 listing; loudspeakerdatabase.com TEBM65C20F-4; mouser/farnell Knowles listings; sonion.com bone-conduction page; i-run.com Shokz OpenRun.
