# Shokz tragus listening test (A-SHOKZ-BENCH)

Goal: how translated bat calls feel and sound by bone conduction on the tragus. Qualitative only. The Shokz transducer is bigger than the RC-BC02, so this is not E1/E2 data (spec R19).

## Before you start (5 items)
1. Battery: if the cell is swollen, dented or warm, do not charge or power it. Leave it on a non-flammable surface and take it to battery recycling. Never reuse the cell in the design.
2. Play the files from a phone or laptop over Bluetooth if the headset still pairs; otherwise wire the transducer to a headphone amp only after the teardown sheet is done.
3. Start with the volume at zero. Raise it slowly; stop if anything is uncomfortable or buzzes.
4. Keep your ear open: no earplug, nothing in the canal. Ambient sound stays audible.
5. Files: `playlist/` (rebuild with `python3 docs/bench/shokz/make_playlist.py`).

## Placement and force
- Press the transducer pad on the tragus (the small flap in front of the ear canal), about 1 N: roughly the weight of a 100 g mass, a light but firm touch, not a squeeze.
- Hold by hand first. Then try a clip or tape for a hands-free run.
- Note which spot felt best (tragus centre, upper edge, lower edge).

## Run order (about 20 min)
1. `nature_audible_only` then `nature_translated_only` then `nature_both`. Which one do you notice first?
2. For each bat call set, play the three versions in order: `normal`, `loud` (+12 dB), `loud_shape` (+12 dB, flat-top). Levels between the three are kept, so loud really is louder (normal is quiet: raise the volume until normal is just clear, then do not touch it again for the set). Heads-up: loud is +12 dB, about 4x the sound power of normal, so keep a finger on the volume and turn it down at once if it is too much.
3. Repeat once with the pad off the tragus (on the cheekbone) for comparison.

## Write down (per file)
- Heard? (no / faint / clear)
- Comfort (fine / tickly / buzzy / hurts)
- Does loud feel like an improvement, or just harsher? Does loud_shape sound smoother or more distorted than loud?
- Can you still hear the room? Any leakage you hear in the open ear?
- Anything you would want changed (pitch, speed, loudness).

Source: D17 A+L (owner 2026-10-08); configs from sim/perf/port_meadow.py (A, A+loud12, A+loud12+shape). The WAVs are model output of the firmware drive, not a measured exciter response.
