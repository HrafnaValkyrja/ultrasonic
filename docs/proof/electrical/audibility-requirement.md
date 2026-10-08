# Audibility requirement: "audible in a subdivision and in day-to-day life" (2026-10-08)
Owner ruling #3. All sources tagged [recall] = from memory, NOT re-fetched this session (no web check run); verify before citing outside the repo. Repo numbers [repo].

## 1. Requirement
**Design ambient 60 dBA (daytime, A-weighted). Alert in-band level at the ear >= ambient band level + 12.5 dB. Delivered need = 58 dB eq. SPL central (band 54.5-61.5), pure-tone 2.5 kHz alert.** Stretch tier 65 dBA (cafe, car): need 63 (59.5-66.5). Busy arterial (70+ dBA) stays out of scope: not day-to-day for a subdivision walk; covered by the haptic option (I-010).

| Place | Level (dBA) | Source |
|---|---|---|
| Residential outdoor, daytime, target | 55 Ldn/Leq (activity interference) | US EPA "Levels Document" 1974 (EPA 550/9-74-004) [recall] |
| Same, WHO | 55 serious / 50 moderate annoyance, 16 h daytime outdoor | WHO Guidelines for Community Noise 1999 [recall] |
| Subdivision with passing cars | 50-60 Leq, passing car 60-70 LAmax at ~10 m | typical measured; ISO 1996-1:2016 method [recall] |
| Office | 45-55 (open plan to 60) | ASHRAE Handbook Applications ch.48 NC/RC tables; open-plan studies [recall] |
| Cafe / shop | 60-70 | restaurant measurement studies (e.g. Rindel; Lombard-effect literature) [recall] |
| Car interior, 90-110 km/h | 65-72 | cabin measurements, widely reported [recall] |
=> 60 dBA covers subdivision + office + shop; 65 covers cafe/car. A pure-tone alert is far more detectable than the noise models here say (tone-in-noise masked threshold is band level -3..+3 dB, R-loudness-conflict item 5), so 12.5 over band is conservative.
**Margin target 12.5 dB:** ISO 7731:2003 (danger signals for work places) wants the signal >= 13 dB above ambient A-level (>= 10 dB in octave bands) [recall]; the repo's 10-15 guidance is the same family [repo: loudness.md]. Band tilt: ambient band = dBA - 11 (proof, conservative) to -18 (traffic typical, B-loud); need = dBA + 1.5 (conservative) to dBA - 5.5. Central -13 gives 60 -> 58.

## 2. Verdict re-run (loudness_fw.py chain + R-loudness-conflict corrected estimate)
`loudness_fw.py` nominal, front site, band mean 2-3 kHz: legacy -12 dBFS 51.6 dB eq. SPL; after (tone 2.5 kHz + limiter at clamp) **56.1** (= conflict doc's 58 central minus the 1.7 dB shaper margin; band about 46-66).
| Ambient | need (central, band) | fw-after margin (central, band) |
|---|---|---|
| 50 office | 52 (48-52.5) | +4 (-6 to +8) |
| **60 design** | **58 (54.5-61.5)** | **-2 (-15 to +2)** |
| 65 stretch | 63 (59.5-66.5) | -7 (-20 to -3) |
| 70 street | 68 (64.5-71.5) | -12 (-25 to 0) |
Firmware alone passes 50 dBA and fails 60. Bat chirps run 3-12 dB under pure-tone level [repo]; this requirement is the alert tone.

## 3. Cheapest combination (nominal chain; dB cumulative)
![waterfall](audibility_waterfall.png)
| # | Step | dB | Cost | Size | Thermal (U4 LDO, cell at 208 mA clamp) | Bench |
|---|---|---|---|---|---|---|
| 0 | Baseline legacy -12 dBFS | 51.6 | 0 | 0 | n/a | none |
| 1 | `lim_lookahead=1`, `alert_hz=2500` (fbfb38b; D17 option A, ceiling = clamp - shaper 0.5203) | +4.5 -> 56.1 | 0, firmware | 0 | 300 ms burst at clamp: U4 +0.3 to +3 K (tau assumed); continuous bound +33 K never reached; cell stays within the 260 mA pulse rule (clamp 208) | re-sign golden vectors + D17 ceiling (owner); U4 temp log (PWR-I12) |
| 2 | Pad stiffness 3e5 N/m (loudness.md lever 3, model) | +4 -> 60.1 | ~0 (pad durometer/geometry) | 0 | none | E1 force vs drive on a 1 N preload fixture |
| **= meets 60 dBA** | | **+2 central over need** | | | | **masked detection test on her (conflict doc)** |
| 3 | Resonant pad/exciter tuned to 2-3 kHz (Q 1.5-8) | +4 more of 6-10 -> 64.1 | ~0 to small tooling | 0 | none (same current) | E1/E2 sweep; f0 of loaded pad |
| 4 | D17: let limiter ceiling go to the clamp itself (drop 1.7 dB shaper margin) | +1.7 -> 65.8 | 0 | 0 | none (clamp unchanged) | prove shaper never exceeds clamp (fwsim) |
=> **Meets 65 dBA at +2.8 central with steps 1+2+3+4; all free or near-free, zero size.**
Rejected or deferred: raising the clamp to 270 mA (+2.3 dB) breaks the cell 260 mA rule; 12 ohm exciter gives no volume (loudness.md fix 2); BCE-1 swap (R-exciter): Bl unpublished, 0..+6 dB without basis, +1.4 mm thickness against O27 thin-first, buy one only for E1 Bl measurement; BCT-3 (+12.9 dB, 44x32 mm) does not fit; pad on tragus (conflict item 3): 0..+5 dB, comfort cost, D1 site change. Tragus 10 dB bonus and B-loud +15.5 dB are not supportable (conflict doc).

## 4. Honest uncertainty
Band is +-10 dB (threshold SD 6-9, Bl 1 N/A assumed, model may be 0-7 dB low: Aeropex anchor [repo]). Steps 1+2 give 60 dBA only at central; a 12 dB-wider real distribution means roughly even odds. Step 3 is the margin that makes 60 dBA robust (+6 vs central need at 60, i.e. 66.5 vs 54.5-61.5 upper). The single deciding bench measurement: masked detection threshold on her at the D1 site under a 60-65 dBA recording, logging drive current and pad force (E1). If detection current < 0.15 A rms at 65 dBA the requirement is met with step 1 alone.
