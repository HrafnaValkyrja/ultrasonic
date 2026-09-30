# Fit around the Nothing Ear (open): keep-out zones and transducer placement

**Date:** 2026-09-30 · **Informs:** D1 (site), §8 (drop-arm), E2, new E9 · **Owner constraint:** §1.2.2 (no contact with, and no effect on, the Ear (open))

## Sources
- **Official dimensions**, per earbud: **51.3 mm W × 41.4 mm H × 14.4 mm D, 8.1 g**. 14.2 mm dynamic driver; nickel-titanium ear-hook wire; IP54. (SoundGuys spec listing, nothing.tech product page.)
- **Product renders**: Nothing's store image feed (`checkout-us.nothing.tech/products/ear-open.json`).
- **Worn photo** (right ear, lateral view, reviewer "Dave"): SoundGuys review, https://www.soundguys.com/nothing-ear-open-review-124038/ (image `Nothing-Ear-Open_Dave`).
- **Inner-face photo** showing the speaker grille: same review (`Nothing-Ear-Open_13`).

The annotated photo is kept out of the repo because it's a third-party image. It was shared with the owner in the session.

## What the Ear (open) occupies (worn, lateral view)

**How it sits:**
1. **The hook** rides over the top of the ear. Its silver battery bulb hangs behind the ear.
2. **Hook junction** (the thickest part at the front):
   - Comes down the *front* of the ear at the helix root, above the tragus.
   - Its front edge is roughly flush with the ear's front boundary, 0–3 mm proud of it. This matches the owner's description: "it extends in front of the ear a little bit."
3. **The pod** (a transparent stadium shape, roughly 11 mm wide) angles **down and backward** at ~30° from vertical, from the junction into the concha, the bowl of the ear. That's the "then angles back into the opening."
4. **The speaker module** is a round ring of ~15 mm diameter (the 14.2 mm driver plus housing).
   - It sits in the concha, **above and behind the tragus**.
   - Its sound outlet is a kidney-shaped grille on the inner face, aimed at the ear-canal entrance just behind the tragus.

**Scale:** ~12.7 px/mm on the zoomed photo. The speaker ring (~15 mm) and a typical ~62 mm ear height agree on it. Distances are ±20% `[Low]`, and it's one reviewer's ear, not the owner's.

## The free pocket: pre-tragal skin at tragus height

- **Below the hook junction and in front of the tragus**, the skin is clear of the Ear (open).
  - This is exactly where the high-isolation, high-sensitivity bone-conduction data was measured (in front of the tragus, near the canal; `bone-conduction.md` §1, §3).
- **On this photo**, an 8 mm pad centred ~6 mm in front of the canal entrance at mid-tragus height clears the Ear (open) outline by **~4.4 mm in 2-D**.
  - In 3-D the clearance is larger: the speaker ring sits deeper in the concha, and the tragus lies between them.
  - Moving the pad ~1–1.5 mm lower and forward reaches the 5 mm target, at a small cost in loudness and isolation. Those fall off with distance from the canal.
- **The arm can't come straight down onto the pad.** The hook junction is directly above it.
  - The arm drops from the temple arm **in front of** the junction; on this photo, a vertical run ~9 mm ahead of its front edge.
  - It then turns back ~5–8 mm to the pad. That makes an "L" or "J" shape.

## Design rules (for D1 and §8)

1. **Clearance:**
   - ≥5 mm between any part of our hardware and the Ear (open) in its nominal position; ≥8 mm for the arm's vertical run.
   - The Ear (open) also shifts a few mm during wear (§1.2.2). If it moves ~3 mm forward or down, it must still never touch us.
2. **Contact point:** pre-tragal skin at the tragus's anterior base, mid-tragus height.
   - Not *on* the tragus flap. Pushing the flap backward narrows the canal entrance the Ear (open) aims into, which changes its sound and breaks T4.
3. **Force direction:** inward (medial, into the head), ≥1 N (D1), through a pad of **~8 mm** diameter, or an 8×10 mm oval, long axis vertical.
   - 1 N over ~50–60 mm² is ~17–20 kPa. That's modest, but T5 decides.
4. **Arm shape:** "L" or "J".
   - Vertical run in front of the Ear (open), then a short rearward leg to the pad.
   - Compliant: if bumped, it deflects away from the Ear (open), never into it.
   - Attached to the temple arm ~10–15 mm in front of the ear's front edge, near the rear end of the battery bay (§8).
5. **Jaw:** the jaw joint (condyle) lies directly in front of the tragus, so this skin moves when chewing or opening wide.
   - The spring must keep ≥1 N through that motion without pinching (E2: talk and chew).
6. **Long hair:** the arm's vertical run is a snag point. Keep it smooth and close to the skin (R16).

## What's still unknown, and how to get it (new E9)

The owner's own ear and fit decide everything above. **E9 photo measurement** (10 minutes, phone camera):
1. Wear the glasses and both Ear (open) as normal.
2. Tape a **mm ruler** vertically just in front of the ear, flat against the cheek, in the ear's plane.
3. **Lateral photo:** camera level with the ear canal, ~30 cm away, lens axis straight at the side of the head. Both ears.
4. **Rear-oblique photo** looking forward past the ear, to show how far the pod sits out from the head.
5. **Same lateral photo while chewing or with the mouth open wide**, to show how much the pre-tragal skin moves.
6. Optional: a front photo showing the temple arm's height above the tragus.

Claude will mark the keep-out zones on those photos at true scale. The E2 bench fit uses them as the starting point.

## The owner's own fit (E9 photos, 2026-09-30)

Three photos from the owner: right-ear lateral, left-ear angled, left profile with hair down.
There was no ruler in shot, so scale comes from the Ear (open) speaker ring (~15 mm; it measures
15.3 mm at the scale used, and the tragus height comes out a plausible 10.9 mm). Distances are
±20%. The photos stay out of the repo for privacy.

**How her fit differs from the reviewer's:**
- The pod sits **lower and more upright**. The speaker ring fills the lower concha and sits
  directly behind the tragus, not above it.
- The hook comes down the front of the ear **~2.8 mm proud** of the ear's front edge (reviewer:
  0–3 mm).
- **8.6 mm** from the bottom of the hook junction down to mid-tragus.
- The angled photo shows the pod standing out from the ear by roughly its full 14.4 mm depth.
  Our pad sits flush on the skin, so this doesn't collide, but the arm must stay close to the head.
- **The glasses temple arm crosses right over the top of the Ear (open) hook.** Attach our arm
  forward of that crossing.
- **With hair down, hair covers the ear, the arm and most of the temple arm.** The front of the
  temple arm near the hinge stays clear. That confirms the mic belongs at the hinge (§8): it
  would be under hair anywhere further back. The battery bay and the transducer arm will be
  hidden, which is good for looks but means snag risk (R16).
- Dangling earrings hang from the lobe, well below the pad. The arm must not reach down there.

**Resulting geometry (right ear):**

| Item | Value |
|---|---|
| 8 mm pad, centred ~4.5 mm in front of the tragus at mid-height | **5.3 mm** clear of the Ear (open) (target ≥5) ✓ |
| Arm vertical run, 8 mm in front of the hook's front edge | **8.0 mm** clear ✓ |
| Arm drop from temple-arm level to the pad | ~25 mm |

**Still open:** a ruler shot would firm up the scale. A mouth-open photo would show how much
the pre-tragal skin moves with the jaw. The left ear looked similar in the angled view but
wasn't measured laterally.
