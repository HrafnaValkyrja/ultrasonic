# Stereo Ultrasound

A glasses-mounted wearable that shifts ultrasound (≈20–85 kHz) down into the audible range and plays it by bone conduction, in stereo, in real time.

- **Spec (source of truth):** [`docs/spec.md`](docs/spec.md). §1 is the owner-locked MVP.
- **Latest plan review:** [`docs/research/review-2026-09-30.md`](docs/research/review-2026-09-30.md)
- **Research findings:** [`docs/research/`](docs/research/), one file per task ID from spec §12.
- **Models and checks:** [`sim/checks/`](sim/checks/): PWM noise, noise-shaper comparison, dead-time distortion, weight balance. Run with `python3 <script>` (numpy, scipy).
- **Data:** [`sim/data/`](sim/data/): the mic's ultrasonic response, digitized from its datasheet.

Status: concept phase. Phase 1 (DSP simulation in Python) is next, pending owner decisions O1–O3 in spec §12.
