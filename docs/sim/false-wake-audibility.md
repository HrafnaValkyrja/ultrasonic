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

## What are the 13 episodes? Spectrogram triage (2026-10-11, SIMULATED/offline analysis)
Src: raw `receiver_3.wav` + `events_3.csv` (BatDetect2 machine labels: det_prob, start/end, high/low freq, species; the sim keeps det_prob >= 0.5 only, `port_meadow.load_clips`). Episodes re-found with config A (`false_wake_audibility.episodes`); per episode: STFT 1024/768 overlap, level over the clip median in 5 bands (2-15, 15-25, 25-40, 40-70, 70-95 kHz) within +-30 ms of onset, spectral flatness 15-30 kHz, 40-70 kHz pulse count. Scratch scripts not kept (fenced 3 G, ~1 min).
**Finding 1: 2 of the 13 are not corpus sound at all.** They are the synthetic `house_walk` quiet scene (3.2-3.5 s, 4.21-4.79 s) = simulated footsteps/handling. 11 are real Port Meadow clips (2025-10-21 dusk). Both are in the 3.5/min.

| # | clip, onset (s), awake | onset evidence (dB over clip median) | class |
|---|---|---|---|
| 1 | 172912, 0.04, 0.30 s | 40-70k +11; labelled Pipistrellus call (det 0.67) starts 0.072, 27 ms after onset | bat, label-tolerance artefact (rule allows 10 ms) |
| 7 | 174106, 0.88, 0.57 s | 40-70k +20; labelled call (det 0.71) ends ~0.833, onset 17 ms past end+30 ms | bat, label-tolerance artefact |
| 11 | 175718, 5.00, 4 ms | 40-70k +16, 4 ms long, at the clip-loop splice (clip is 5 s) | simulation splice artefact |
| 2, 4, 5 | 173155 / 174003 / 174035; 1.06 / 3.12 / 3.47 s | onset +1 to +5 dB, flat noise (flatness 0.8), 12-39 pulses in 40-70k during the episode; 2 and 4 run to clip end | wake held/retriggered inside an active bat pass (labelled Pipistrellus 45-55 kHz every ~0.1 s), the gaps and quiet calls between labels; not a blip |
| 8 | 174242, 0.64, 0.30 s | 25-40k +12, nothing 40-70k, between labelled calls | weak, faint call or noise trip (undecidable) |
| 3 | 173324, 1.08, 1.92 s (to clip end) | 15-25k +27, 40-70k +20; 20.4 kHz tonal (flatness 0.04), 24 pulses 40-70k | unlabelled low call (noctule-like 20 kHz) plus bat tail |
| 6 | 174048, 3.51, 0.45 s | 15-25k +32, 25-40k +24, 40-70k +8; flatness 0.19 | broadband 15-40 kHz burst: stridulation (bush-cricket-like) or low bat |
| 9 | 174242, 1.07, 0.32 s | 15-25k +34, 25-40k +13; flatness 0.10; label det 0.39 (below the 0.5 cut) at 58 kHz | as 6; a faint labelled call is also present |
| 10 | 174648, 3.86, 0.74 s | 15-25k +30, 25-40k +19; flatness 0.14 | as 6 |
| 12, 13 | house_walk 3.2 / 4.21 s (synthetic) | simulated footsteps | mechanical (sim input), not corpus |

Tally: real 15-40 kHz non-bat-labelled sound 4 (3, 6, 9, 10); bat-pass tail/noise 4 (2, 4, 5, 8); label-tolerance 2 (1, 7); splice 1 (11); synthetic mechanical 2. Nothing looks like wind or handling in the real clips (2-15 kHz within +-5 dB on all 11).

Limits: (a) one mic channel, 192 kS/s, no ground truth; 3/6/9/10 cannot be told apart as orthopteran vs noctule/serotine-type bat by these stats alone (needs a repetition/FM look at the clip, or a listening pass). Late October in Oxfordshire makes bush-crickets unlikely but not excluded; I assert neither. (b) Counts are 11 clips, so +-1 event is 9 points.

## Verdict on the 13
- Roughly 6-8 of 13 (1, 7, 3, 6, 9, 10, plus the bat-pass tails 2, 4, 5) are real in-band sound, mostly bat or bat-adjacent; 3 are simulation artefacts (11, 12, 13); 1 undecidable (8). The "false wake" tag is mostly a labelling/scoring artefact, not a detector fault.
- Would she want to hear them: bat-pass tails and labelled-call edges, yes (it is the §1 product: translating ultrasound she can't hear). The 15-40 kHz bursts (3, 6, 9, 10), if insect or a low bat, are also sound a bat/ultrasound listener would reasonably welcome; a 15-25 kHz tonal burst is partly audible to a young ear anyway. Her call, not mine, whether insects count as wanted.
- Recommendation: leave the firmware as is. Targeted fix on the metric, not the device: (1) relabel/score with a +-50 ms tolerance and det_prob >= 0.3 in `port_meadow.score` (removes #1, #7 and likely #8/#9), (2) exclude splice edges and report `house_walk` separately (removes 11, 12, 13), (3) the residual 15-40 kHz bursts become a "non-bat in-band" class, checked at the E2 listening session. Net false-wake rate on real corpus after 1+2 is about 0.4/min-equivalent (6 of 13 left) instead of 3.5; not simulated, estimate only.
