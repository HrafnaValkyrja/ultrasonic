# Audibility requirement for AUDIO PLAYBACK in day-to-day life (2026-10-08, rewritten after owner correction)

## 0. REAL programme simulation (owner: simulate against what it will actually play) -- supersedes the crest-6 numbers in sections 2-4
Script `docs/proof/electrical/audibility_playback.py` (3G fence), data `docs/proof/electrical/audibility_playback.json`, plot `docs/proof/electrical/audibility_playback.png`.
![per-band](audibility_playback.png)
- **Programme:** `sim/out/nature/2_translated_only.wav` (48 kS/s, 20 s): Port Meadow AudioMoth 192 kS/s night recording, Zenodo 22079773, CC-BY-4.0, four bat passes; algorithm B transient mode, `sim/dsp/nature_demo.py` (calls scaled to 75 dB SPL at the mic: assumed). Measured: file peak **-9.5 dBFS** (not -12; the ceiling would trim 2.5 dB), crest **22.6 dB overall, 14.0 dB inside the loudest 10% of 50 ms frames**. The calls are narrow-band, so they land as a tone near **2.56 kHz**; every other 1/3-octave band is 25-30 dB lower (below threshold). The earlier "crest 6 dB programme" was optimistic by 8-16 dB for this material.
- **Chain:** sample = duty fraction of Vdd; 0.6353 = 208 mA clamp (`fw/variants.yaml`, FWSIM-R64), so i = 0.327 A per unit. Force per amp: `sim/acoustics/out/bone_tf.json` `mag_db_n_per_a` (nominal; Bl 1.0 assumed; built by `sim/acoustics/bone.py`). eq SPL = force - front-of-tragus threshold (`thr_front_measured_db_re_1uN`, Surendran 2023) + ISO 226 air threshold [recall]. Per 1/3-octave, call-active frames.
- **D17 variants (my mapping; confirm):** C = now, fixed -12 dBFS ceiling; A = look-ahead limiter at clamp minus shaper excursion (0.520, `lim_lookahead=1`); B = hard ceiling at the clamp (0.635). Playback gain is raised so the loudest peak meets each ceiling (the limiter then barely acts; fixed-gain D3 would need a user volume setting).
- **Ambient spectra** (shapes [recall], +-5 dB per band, normalised to the stated dBA): residential/subdivision = EN 1793-3 traffic spectrum; office = NC-like fall ~3 dB/oct above 500 Hz (ASHRAE); shop/cafe = long-term speech spectrum falling ~9 dB/oct above 1 kHz (Byrne 1994); car = 6 dB/oct fall. Ambient at 2.5 kHz band: residential 55 dBA 41 dB, office 50 dBA 36, subdivision with passing cars 60 dBA 46, shop 65 dBA 46, car 68 dBA 49. Need = ambient band + 8 dB (section 1 headroom).

| Case (2.5 kHz band, call-active) | eq SPL | peak I | LAeq-eq | margin over ambient band: residential 55 / office 50 / subdiv+cars 60 / shop 65 / car 68 |
|---|---|---|---|---|
| C now (-12 dBFS) | 39.8 | 82 mA | 41.4 | -0.8 / +3.6 / -5.8 / -6.5 / -9.4 |
| C + TEAX14C02-8 | 47.4 | 82 | 49.0 | +6.8 / +11.2 / +1.8 / +1.1 / -1.8 |
| A limiter at clamp-shaper | 46.2 | 170 | 47.7 | +5.5 / +9.9 / +0.5 / -0.2 / -3.1 |
| **A + TEAX** | **53.8** | 170 | 55.3 | **+13.1 / +17.5 / +8.1 / +7.4 / +4.5** |
| B ceiling = clamp | 47.9 | 208 | 49.4 | +7.2 / +11.7 / +2.2 / +1.5 / -1.3 |
| B + TEAX | 55.5 | 208 | 57.0 | +14.8 / +19.3 / +9.8 / +9.1 / +6.3 |
Need is +8 (+4 minimum). Read: **today (C) the real calls are audible but not comfortable in an office and not over a 55 dBA street; A alone gets residential/office to the +4..+10 band, not a 60 dBA subdivision with cars. A + TEAX14C02-8 meets +8 for a 60 dBA subdivision (+8.1), office and residential with 5-9 dB spare, shops 65 dBA at +7.4 (about target), car 68 at +4.5 (minimum).** B adds only 1.7 dB over A for a worse THD risk at the clamp; keep A. Pad stiffness 3e5 (+4 dB, E1) on top of A + TEAX takes shops to +11.4 and car to +8.5.
TEAX14C02-8 (Tectonic, Bl 2.4 T m, 14 dia x 9.85 mm, 7.50 EUR; `docs/brainstorm/R-exciter2.md`): +7.6 dB is applied flat (vendor claim, band flatness unverified); cost is pad size/thickness at the tragus; bench E1 for flatness, force/amp and comfort. D17 effect: C -> A is +6.4 dB (mostly gain headroom); A -> B only +1.7 dB.
**Thermal/battery with the real programme:** peak 170 mA (A) but the rms is 22.6 dB under peak, about 13 mA rms -> mean |i| roughly 10 mA, far below the 60 mA I assumed in section 4: U4 rise ~1-2 K, runtime cost small (rail budget 2.5 mA average is exceeded only during long calls; log it on the bench, PWR-I12). Cell pulse rule: peak 170 mA < 260 mA.
Caveats: eq SPL is +-10 dB; call level 75 dB SPL at the mic is an assumption (distant bats are quieter; the device gain is fixed, D3); a 1/3-octave ambient band is about 2 dB wider than the ear's critical band at 2.5 kHz, so margins are slightly conservative; masking by the ambient spectrum is only band-level, not a full masking model; THD+N at the 170 mA peak is extrapolated (-52 dB at 85 mA, section 2).

---
Owner: "it's an audio device not an alert system." The device plays the shifted/compressed ultrasonic scene as listening audio (spec §1.1; DSP chain ends `volume -> safety ceiling` at 12.5 kS/s, spec L66). The 2-3 kHz alert-tone move (`alert_hz`) is system-sound only and is NOT counted here. Sources: [repo] = read today; [recall] = from memory, not re-fetched (no web check run), verify before external citation.

## 1. Requirement
**Design ambient 60 dBA (daytime). Programme (playback) rms at the ear >= ambient dBA - 5 = 55 dB eq. SPL, clean (THD+N <= -40 dB), central estimate, +-10 dB.** Stretch 65 dBA (cafe/shop): 60. Subdivision walk at 55 dBA: 50. Car (65-72) and arterial street are out of scope.

Ambient places (dBA): residential outdoor day 50-55 (EPA Levels Document 1974, EPA 550/9-74-004; WHO Community Noise 1999: 55 serious / 50 moderate annoyance) [recall]; subdivision with passing cars 50-60 Leq, passing car 60-70 LAmax [recall, ISO 1996-1:2016 method]; office 45-55, open plan to 60 (ASHRAE Applications ch.48) [recall]; cafe/shop 60-70 (restaurant measurement studies, Lombard literature) [recall]; car 65-72 at highway speed [recall].

**Listening headroom (replaces the 10-15 dB alert rule):** the programme must sit about +8 dB (range +4 to +10) over the ambient in the same 1.5-4 kHz band. Basis [recall]: preferred listening levels in noise sit about 6-10 dB over the background (Airo et al. 1996, Hodgetts et al. 2007 Ear & Hearing); real-life listening SNRs about +5 to +10 dB (Smeds et al. 2015 JAAA); sentence intelligibility is near ceiling by about +4 to +6 dB SNR (Plomp 1986; ANSI S3.5 SII). +4 = "follows it", +8 = target, +10 = enjoyable. Ambient in band = dBA - 13 (range -11 proof, -18 traffic typical). So need = dBA - 13 + 8 = **dBA - 5** (range dBA - 9 to dBA + 0).

## 2. Max CLEAN level at her ear (repo chain; central 2.5 kHz, nominal, front site)
Force at the 208 mA clamp (0.635 of Vdd diff): 94.5 dB re 1 uN; corrected central eq. SPL **58** for a full-scale sine (R-loudness-conflict, band 48-68).
| Ceiling | Peak (sine) eq. SPL | Programme rms (crest 6 dB; chirps are 3-12 dB under sine [repo]) | THD+N [repo C3-output-stage.md] |
|---|---|---|---|
| -12 dBFS (D17 now, 0.251) | 49.9 | **43.9** | -52 dB @12.5 ns dead time; -38 @25 ns (no compensation) |
| limiter at clamp minus shaper excursion (0.520, D17 option A, `lim_lookahead=1`) | 56.3 | **50.3** | not modelled: model stops at -12 dBFS; signal current 2.1x larger, dead-time error grows with level (-61 @-40 dBFS to -52 @-12), my extrapolation -45 +-5 dB (assumed) |
| clamp itself (0.635) | 58 | 52 | extrapolated -43 +-5 |
"Clean" = THD+N <= -40 dB (assumed; the exciter's own distortion is likely larger, C3 note). It passes at 12.5 ns dead time, fails at 25 ns uncompensated at the ceiling (-38). Bench: THD at the clamp on the real bridge (E-series current probe + FFT), not modelled.

## 3. Verdict vs ambient (programme rms, margin = delivered - need)
| Ambient | Band | Need (+8; +4..+10) | Legacy -12 dBFS 43.9 | Limiter 50.3 |
|---|---|---|---|---|
| Quiet room 35 | 22 | 30 | +14 | +20 |
| Office 50 | 37 | 45 (41-47) | -1 (+3..-3) | +5 (+9..+3) |
| Subdivision 55 | 42 | 50 (46-52) | -6 (-2..-8) | **+0 (+4..-2)** |
| **Design 60** | 47 | **55 (51-57)** | -11 | **-5 (-1..-7)** |
| Cafe/shop 65 | 52 | 60 (56-62) | -16 | -10 (-6..-12) |
Honest read: today's -12 dBFS ceiling gives quiet room and a quiet office only. The limiter makes office comfortable and a 55 dBA subdivision just adequate; 60 dBA and beyond need force-per-amp, not more current (current is pinned by the clamp and the THD ceiling).

## 4. Cheapest combination (cumulative programme rms, central)
![waterfall](audibility_waterfall.png)
| # | Step | dB | Cost | Size | Thermal / battery | Bench |
|---|---|---|---|---|---|---|
| 0 | Legacy -12 dBFS | 43.9 | - | - | - | - |
| 1 | `lim_lookahead=1` (fbfb38b; D17 option A) | +6.3 -> 50.2 | 0, fw | 0 | current doubles for +6 dB (see below) | owner re-signs golden vectors + D17; THD at the ceiling |
| 2 | D17: ceiling = clamp (drop 1.7 dB shaper margin) | +1.7 -> 52.0 | 0 | 0 | +1.7 dB current | fwsim: shaper never exceeds clamp; THD |
| 3 | Playback compression: crest 6 -> 4 dB (log-compression mode B is already the intended main mode, spec L222; limiter-aware makeup) | +2 -> 54.0 | 0, fw tuning | 0 | rms current up 2 dB | listening test: pumping/artifacts |
| 4 | Pad stiffness 3e5 N/m (loudness.md lever 3) | +4 -> 58.0 | ~0 (durometer/geometry) | 0 | **lowers** current for equal level | E1 force vs drive, 1 N preload |
| 5 | Broad resonant pad, Q <= 2 (narrow Q colours playback) | +2 -> 60.0 | small tooling | 0 | as 4 | E1/E2 sweep |
| 6 | **Tectonic TEAX14C02-8** (14 mm round exciter; Bl 2.4 T m, 7.8 ohm, 14 dia x 9.85 mm, 7.50 EUR; R-exciter2.md 481fa69): +7.6 dB vs assumed Bl 1.0, same clamp current so same THD | +7.6 -> 67.6 (or 65.6 without step 5) | 7.50 EUR/pod; bench-only buy (O21) | pad-size/thickness cost at the tragus (9.85 mm deep, 14 mm dia), not pod thickness; comfort test on her | lets steps 4-5 be dropped for the same level, or halves current at equal level (runtime) | band flatness is a vendor claim only: measure force vs f 1.5-4 kHz, Bl, comfort on tragus (E1) |
| opt | Other exciters: BCE-1 Bl unpublished (0..+6), BCT-3 does not fit | - | - | - | - | - |
=> **With the TEAX14C02-8 (step 6) the force-per-amp lever is a purchased part: steps 1+2+3+6 = 54.0+7.6 = 61.6 (+6.6 over the 55 need at 60 dBA, covers 65 dBA cafes at 60 need +1.6) with no pad work; with pad steps 4-5 as well 69.6 (spare dB = lower current, longer runtime).** Software-and-pad-only fallback: **Minimal: steps 1+2+3+4 = 58.0 vs 55 need at 60 dBA (+3, band -7..+13). Meets subdivision/office/shops at 60 dBA; 65 dBA cafes need step 5 (60.0) plus luck or Bl.** Rejected: clamp to 270 mA (+2.3 dB, breaks the 260 mA cell pulse rule, worse THD); 12 ohm (no volume); BCT-3 (44x32 mm, does not fit); B-loud's +15.5 and tragus 10 dB bonus (conflict doc).

**Thermal / battery at the clamp (docs/proof/thermal row 8):** rms playback current at 50.3 dB (6 dB under the 147 mA clamp sine) is about 74 rms, ~60 mA mean|i| from the 3.0 V LDO U4: ~72 mW at 1.2 V drop docked, +12 K at theta-JA 166 K/W (cap 125 C: fine). The problem is runtime: the rail budget carries 2.5 mA average for the exciter; sustained loud playback at 60 mA with ~9 mA base is ~2 h on a 130 mAh cell. Each +6 dB of force per amp (steps 4-5, Bl) halves that current, which is the second reason to prefer force-per-amp levers over more drive. Cell stays inside its 260 mA pulse rule (clamp 208).

## 5. Open (bench)
(a) THD+N at the clamp on the real bridge; (b) force vs current, pad stiffness, Bl (E1); (c) masked-listening test on her: scene playback under 55/60/65 dBA recordings, adaptive level to "comfortable", logging drive current; one afternoon settles the +8 target, the band tilt and eq. SPL uncertainty (+-10 dB) together; (d) program crest of real bat/house material; (e) U4 temp and battery current log (PWR-I12).
