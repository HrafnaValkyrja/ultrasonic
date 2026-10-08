# R-loudness-conflict: why proof/loudness.md and B-loud.md differ by ~40 dB (2026-10-08)
Sources are tagged: [repo]=read in repo today; [recall]=my memory of a public source, NOT re-verified (Consensus quota exhausted, no web check). Verify before citing.

## Verdict
The ~40 dB gap is arithmetic, not physics disagreement. Corrected central estimate at a 70 dBA street: **-11 dB alert margin (band -25 to 0 dB)**; B-loud's +15.5 is not supportable. The proof's -24 is its pessimistic p05 case plus a pessimistic masking model; its nominal is -14.5.

## Decomposition (2.5 kHz, 70 dBA street)
| # | Assumption | B-loud | proof | dB of gap |
|---|---|---|---|---|
| 1 | Drive current | 0.34 A rms (3 V square fundamental 2.7 V rms / 6 ohm, "derated 25%") | 208 mA clamp **peak** = 0.147 A rms (sine) | 7.3 |
| 2 | Force per amp (Bl, coupling) | Bl 0.6 N/A [A, 10 mm class] | model 0.05 N/V rms at 8 ohm = 0.36 N/A effective (Bl 1 N/A nominal, reduced by mass/pad/tissue load) | 4.4 |
| | **Force** | 106 dB re 1 uN (0.2 N) | 94.5 dB (0.053 N) | **11.7** (observed 11.5) |
| 3 | Threshold used | mastoid 30.5 minus a flat 10 dB "tragus bonus" = 20.5 | measured front-of-tragus 34.5 (Surendran 2023, n=21, SD 6-9) | 14 |
| 4 | Air-threshold step | 0 dB SPL | -3 dB (ISO 226) | 3 |
| | **Delivered eq. SPL** | 85.5 | ~57 | **28.5** |
| 5 | Reference level | 70 dBA literal | needs band+12.5 = 71.5 | 1.5 |
| 6 | Exciter case in headline | nominal | p05 soft-coupled (-9 dB) | 9.5 |
| | Total | +15.5 | -24 | **~39.5** |
(The -12 dBFS firmware ceiling, another 8 dB, is already removed in the proof's "after" row.)

## Which side is right on each item
1. **Current:** the clamp is real (cell 260 mA pulse rule, FWSIM-R64), so proof wins. B-loud's 0.34 A rms is 0.48 A peak: 2.3x the clamp. Its "3 V bridge, 0.8 W" ignores the cell.  [repo]
2. **Bl:** both assumed, neither measured. Proof's model is anchored: Aeropex 100.5 dB re 1 uN/V vs model 93.9 (Surendran 2023 Fig 2B [repo]), so the model may be 0-7 dB low. B-loud's 0.6 N/A with 8 ohm is 0.075 N/V = 97.5 dB re 1 uN/V, inside that band but at its optimistic end. Plausible range 94-101 dB/V.
3. **Tragus vs mastoid, the biggest single item:** "tragus is 10 dB better than mastoid" comes from the brief (D1), not data. Surendran 2023 measured front-of-tragus thresholds of 30-34 dB re 1 uN, i.e. **no better than mastoid RETFL (29.5-36.5, Henry & Letowski 2007 / ISO 389-3:2016 [repo, shared-params])**. Cartilage-conduction work (Hosoi 2010; Nishimura 2012-2014 [recall]) reports a gain mainly as ear-canal SPL rise from the occlusion effect, large below ~1 kHz and small at 2-4 kHz; and that gain needs firm tragus contact that closes the canal. At D1 (1-1.5 cm in front of the tragus, not touching) it is absent. Proof wins; a 0-5 dB bonus is the most that is defensible, only for a pad that actually presses the tragus.
4. **Force-to-hearing conversion:** both use sensation level plus air threshold ("SPL-equivalent"). This is an equal-loudness estimate good to +-10 dB, and is not a calibrated SPL; threshold SD alone is 6-9 dB. Neither side is wrong in method. ISO 389-3 RETFL is a mastoid, artificial-mastoid-referenced threshold; it is a valid reference only for mastoid placement.
5. **Masking/ambient:** B-loud puts 2.5 kHz band at 52 dB (70 dBA minus 18) and a 12 dB margin over that is easy; it then reads its own 85.5 as "30 dB over masked". Proof uses dBA-11 = 59 dB and needs +12.5. Spectrum tilt of street noise is [A] in both; real traffic is ~-15 to -20 dB at 2.5 kHz relative to dBA, so B-loud's tilt is closer to typical, proof's is conservative by ~4-7 dB. Neither models critical-band masking of a tone (masked threshold is typically band level -3 to +3 dB for a tone in noise [recall, Zwicker/Fastl]); an alert at band +12.5 is already well above detection, so the required level is a design choice, not a hard limit. Range of requirement: 64.5 (band 52 + 12.5) to 71.5.

## Corrected central estimate (street 70 dBA)
Delivered eq. SPL: force 95 dB (94.5 proof, +0-7 Bl anchor, say 95-98 incl. optimistic Bl), minus threshold 34.5 (front) or 30 (small tragus bonus), plus air -3: **central ~58 dB eq. SPL, band 48-68.**
Required: 64.5-71.5 (central 68).
**Margin: -10 dB central, band -24 to +3.** (Full-scale sine, pure tone; bat chirps are another 3-12 dB lower, proof.) Office 50 dBA: about +6 central (required ~48-52 -> margin +6 to +10); that matches the proof's "marginal to OK". Street alerts need ~+10 dB beyond today's design; a plausible route is Bl (Aeropex-class, +7 dB) plus a resonant pad (+4 to +10 dB), both listed in the proof's fix list, not B-loud's current budget.

## The one bench measurement that settles it
**Masked detection threshold on her, with the real exciter, at the D1 site, under a 70 dBA street recording.** Play a 300 ms 2.5 kHz tone (and a chirp) at stepped bridge current while a street recording plays at 70 dBA; record drive current at 50% / 90% detection (adaptive 2AFC). Log in the same run, with the pad on a small force sensor in a 1 N preload fixture (E1): force vs drive current (settles items 1-2) and probe-mic canal SPL at the same drive (settles item 3). The detection current alone collapses items 1-5 into one number: if threshold sits below ~0.15 A rms, street audibility is real; if above the 0.208 A peak clamp, it fails. Costs one afternoon; no purchases beyond a force sensor.

## Doc follow-ups (not done here, owner/ECR path)
B-loud sections 1 and 6 should adopt the 0.147 A rms clamp, drop the flat 10 dB tragus bonus, and quote a band rather than 85.5. proof/loudness.md should state its nominal (-14.5) beside the p05 headline (-24) and note the dBA-11 tilt as conservative.
