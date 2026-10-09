# Bench day 1 run sheet (weekend, pre-final design)

Sources: GitHub #14 (+3 comments), #1 pen test, #4 body measure, queue A-K4-VISION / A-TODAY-BODY-MEASURE. Written 2026-10-08.
Rule: you only need what you already own. Anything marked **after the freeze order** needs a part that is not bought yet (O21: nothing ordered before design freeze). Skip those; do not improvise.
Checklist picture: `bench-day-1.png` (same order).

## List A: 2-minute decisions (do first, ~15 min total)

1. **Pen test (#1).** Settles: does the K4 pod front stand, or do we go thinner (K1-thin, 8.5 mm) or you override spec s8 v0.9? Have: glasses, a pen, a helper, the printed card `docs/diagrams/pentest-card/pentest-card.pdf` at 100 % (check the 10 mm bar with a ruler). Steps: glasses on, eyes fixed on one spot ahead; helper slides the pen tip forward along the arm from your ear; say "now" when you first see it; helper marks the arm and reads mm from the hinge. Do it 3 times. **~5 min.** Write down: 3 readings and the average (mm from hinge). Read it off the card's result map: up to 12.6 K4 stands; over 19 means the 8.5 mm pod.
2. **Temple arm caliper (#4).** Settles: CAD assumes the arm is 2.5 x 5.0 mm at ~50 mm behind the hinge. Have: calipers, your glasses. Steps: measure thickness and height at 50 mm behind the hinge. **~3 min.** Write down: both numbers, plus arm material if you know it.
3. **E9 ruler shot + mouth-open photo (#4).** Settles: body numbers for the O20 resize. Have: ruler, phone, helper. Steps: photo of the ruler held beside the face/ear area as on the spec E9 sheet; one photo with mouth open. **~5 min.** Write down: file names; drop the photos in the repo inbox.
4. **E12 sideways give (#4, optional).** Settles: how much the arm flexes sideways under load. Have: 100 g weight (a full small bottle or coins on a string), ruler. Steps: hang 100 g from the arm at 50 mm behind the hinge, measure the sideways give. **~5 min.** Write down: mm of give.

## List B: listening and logging on you (need a working exciter/mic rig; if you do not have one assembled, skip)

1. **Masked detection threshold at the D1 tragus site (#14).** Settles: the street-loudness question (corrected estimate -10 dB, band -24 to +3; `docs/brainstorm/R-loudness-conflict.md`). Have: the D1 rig and a 70 dBA street recording played from speakers (check level with a phone meter). Steps: play the recording; raise the test tone from silent until you just hear it; repeat 5 times. **~30 min.** Write down: the level at each hearing, in dB re rig setting.
2. **Car noise log (#14).** Settles: the car row of `audibility-reconciled.md` (keeps its * until then). Have: the D1 mic, a car, a driver. Steps: log 30 s at about 80 km/h. **~15 min.** Write down: file name, speed, road type.
3. **I-021 exciter impedance sweep (#14).** Settles: drop the exciter if Q below 2 or f0 drifts over 20 % with pad force. Have: E1 exciter rig, the sweep tool. Steps: sweep under pad load at light, medium, 1.5 N. **~20 min.** Write down: f0 and Q at each load.
4. **I-022 pad force sweep (#14).** Settles: drop if gain is under 2 dB at the 1.5 N comfort cap. Have: E1 rig, force gauge or kitchen scale. Steps: step the pad force 0 to 1.5 N, log output. **~20 min.** Write down: dB gain per force step.
5. **Pad/resonance tuning (#14).** Settles: whether the +4 to +10 dB claim holds. Have: the E1 rig, pad variants. Steps: swap pads, repeat the sweep. **~30 min.** Write down: best pad and dB gain.

## List C: electronics and prints (most need parts from the build; mark what you have)

1. **I-027 idle bus current, bridge gated (#14).** Settles: drop if under 0.15 mA saved (PWR-I12). Have: a built pod or H-bridge board, a meter that reads uA. Steps: measure idle current with the bridge gated, then ungated. **~15 min.** Write down: both currents.
2. **U4 Zout ripple (#14).** Settles: whether the regulator output impedance gives acceptable ripple. Have: a built board and a scope. Steps: load step, read ripple at the U4 output. **~20 min.** Write down: ripple mV pk-pk and the load.
3. **BM28 TDR coupon (#14).** Settles: connector impedance continuity. Have: the coupon board with BM28 parts. Not owned yet: **after the freeze order**. **~30 min.** Write down: impedance trace screenshot.
4. **First supervised charge, G5, with thermocouple (#14).** Settles: cell temperature during charge. Have: built charger board, the cell, a thermocouple, a fire-safe tray. Not owned yet: cell and board **after the freeze order**. Stay in the room. **~45 min.** Write down: temperature every 5 min, current, stop time.
5. **Prints: jig clip fit (0.05 mm gap), 0.6 mm wall coupon (K1t), epoxy post fill (#14).** Settles: whether the printed clip, the thin wall and the epoxy fill hold. Have: printed jig and coupon (printer), calipers, epoxy already on hand. Steps: test fit the clip and measure the gap; load the 0.6 mm wall with a gentle push; fill a post and check for voids once cured. **~40 min.** Write down: gap in mm, any crack, any void.

## Suggested order

A (about 15 min) first, then the prints in C5 while epoxy cures, then B, then C1 to C4 last (they need the most setup). Total with everything: about 5 hours; A alone is under half an hour and unlocks the K4 call.

## Rig scripts (bench/rig/, CLI only)

`--dry-run` on each writes stimulus WAVs and a CSV template to `bench/rig/out/` with no hardware; live runs need `pip install sounddevice` and the sound card. Host tests: `python3 -c "import sys;sys.path.insert(0,'bench/rig');import test_rig"` (pytest style functions in `bench/rig/test_rig.py`).
- B1 masked threshold: `bench/rig/masked_threshold.py --noise street.wav --run N` (2-down-1-up).
- B3 I-021 impedance sweep: `bench/rig/imp_sweep.py --load light --rs 10` (f0, Q; wiring in its docstring). Synthetic self-check recovers f0 within 3 %, Q within about 30 % (sweep noise); trust f0 drift more than absolute Q.
- B4 I-022 force sweep: `bench/rig/force_sweep.py` (prompts per force step, gain vs 0 N).
- I-028 2.5 vs 4 kHz A/B: `bench/rig/ab_2k5_4k.py --trials 20` (matched RMS, randomised, logged).
