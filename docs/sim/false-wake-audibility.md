# Does a false wake reach her ear? Port Meadow, 2026-10-11 (SIMULATED)

Src: `sim/perf/false_wake_audibility.py` (new; data `sim/perf/out/false_wake_audibility.json`), scenes and false-wake rule from `sim/perf/port_meadow.py` (54 clips + 2 quiet scenes, 222 s scored; false wake = IDLE->awake edge with no annotated call in [start-10 ms, end+30 ms]). Firmware unchanged. Run fenced 3 G.

## Method
1. Host firmware output per episode: the CCR stream AFTER squelch and limiter, averaged per 12.5 kS/s sample = signed duty (squelched = 0).
2. Same chain as `sim/acoustics/audibility_reconciled.py`: 5 third-octave bands 1.6-4 kHz, 200 ms integration (Plomp & Bouman 1959), 0.327 A at full duty, bone transfer function (`bone_tf.json`, nominal; level offset OFF from `bone_results.json`), front-of-tragus threshold (Surendran 2023, n=21, SD 6-9 dB, per `docs/brainstorm/D-i020-band.md`; the mastoid H&L set is within ~5 dB). Margin = best band minus threshold; audible if > 0. Ambient columns use the masked threshold max(q, ambient-4) of audibility_reconciled.
3. Scene scale: ONE global Pa scale, loudest 10 ms ultrasonic window = 75 dB SPL; true calibration unknown. Margins move ~1:1 with that (see caveats).

## Result (13 false-wake episodes, 3.5/min, same count in all four configs)
Every episode is awake a median 573 ms with output unsquelched a median 410-445 ms (100 % of episodes pass sound: the squelch opens, it is not a silent wake).

| config | peak (dBFS, median) | audible in quiet | median margin, quiet | office NC-35: audible / median margin if audible | street day: audible / margin | audible s per hour: quiet / office / street |
|---|---|---|---|---|---|---|
| B (A look-ahead, loud off) | -18.0 | 92 % (12/13) | +36 dB | 69 % / +13 dB | 69 % / +9 dB | 227 / 97 / 76 |
| B + loud12 | -5.9 | 100 % | +48 dB | 85 % / +22 dB | 85 % / +17 dB | 229 / 152 / 133 |
| slim, loud off | -17.7 | 92 % | +36 dB | 69 % / +15 dB | 69 % / +11 dB | 223 / 97 / 79 |
| slim + loud12 | -5.6 | 100 % | +48 dB | 85 % / +22 dB | 85 % / +17 dB | 229 / 152 / 137 |

Audible seconds per hour = time the 200 ms-integrated best band is above threshold, summed over false-wake windows, divided by scored hours. Typical audible burst 0.36-0.63 s. p90 margin (B, office) +17 dB, max +18 dB.

## Verdict
- Audible, not inaudible: in a quiet room 12 of 13 false wakes (92 %) are 20-45 dB above the tragus threshold; with loud12 all are. In an NC-35 office or on a street 69 % (B) to 85 % (loud12) still clear the masked threshold, by about 9-22 dB.
- Size of the nuisance: B = 3.5 audible-ish events/min, but audible time is only 76-97 s/h in ordinary ambients (2-3 % of the hour), 227 s/h (6 %) in silence. Each is a ~0.4-0.6 s burst of the translated sound of whatever triggered it.
- Whether that is a nuisance depends on what they are. Per alt-false-wake.md they are likely real in-band ultrasound (insects, clicks, unlabelled calls) that the device is built to translate; then they are correct output, not artefacts, and the "false" label is the annotator's. No evidence here separates the two. With genuinely spurious wakes (noise-floor trips) the same numbers apply: about 1 audible blip every 20 s.
- Call it: audible and probably noticeable in quiet, mostly masked-to-marginal (about +5 to +13 dB, i.e. a faint beep) in street/office noise. Not a showstopper; E2 listening decides. Cheap lever if it annoys: owner sensitivity setting, or keep loud off (loud12 adds 12 dB to every blip).

## Caveats
- 13 episodes only; percentages move by 8 points per event. B vs slim differences are noise.
- 75 dB scale is an assumption; at 65 dB scene level subtract 10 dB from every margin: quiet room median would still be +26 dB (audible), office would fall to ~0 (borderline).
- The transfer function is the nominal Monte Carlo centre (5-95 % band is +-15 dB at some frequencies) and the threshold has 6-9 dB subject SD; absolute margins are +-10 dB, ordering across configs is solid.
- Quiet-room column uses q (masking offset) only, no real room noise floor.
