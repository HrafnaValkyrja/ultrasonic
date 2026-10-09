# D-r6-crest: kill tests I-034 (flat-top drive) and I-036 (all-pass crest reduction)
date 2026-10-08. Offline, no firmware change. Script `sim/acoustics/crest_kill.py` (raw json regenerated into git-ignored sim/acoustics/out/).
Material: `sim/out/nature/2_translated_only.wav` (Port Meadow translated calls, 7 events), per-call 200 ms sliding rms in 1.5-4 kHz (method of `audibility_reconciled.py`).
Reference chain: +12 dB drive into the real look-ahead limiter (port of `fw_lahead_hop`), ceiling 0.5203 FS = 208 mA clamp. Every variant ends in the same limiter, so equal peak.
Current: 208 mA x mean|x|/ceiling (law of `docs/proof/electrical/current-models-reconciled.md`). Reference file mean 17.8 mA (loud-mode, +12 dB).
Distortion proxy: power fraction outside 1.5-4 kHz in the call (ref 0.1 %).

| variant | per-call gain median (p10..max) dB | mA x ref | out-of-band power |
|---|---|---|---|
| flat-top tanh k=1.5 | +1.28 (+1.20..+3.93) | 1.37 | 0.2 % |
| k=2 | +1.76 (+1.65..+5.34) | 1.56 | 0.4 % |
| **k=2.5** | **+2.18 (+2.03..+6.45)** | **1.74** | **0.6 %** |
| k=3 | +2.53 (+2.35..+7.34) | 1.92 | 0.8 % |
| k=6 | +3.83 | 2.71 | 2.0 % |
| k=12 (near square) | +4.89 | 3.72 | 3.4 % |
| k=3 applied pre-limit (no +12 dB drive) | -1.23 | 0.81 | 1.4 % |
| all-pass 2 / 4 / 8 sections fixed | -0.63 / -0.18 / -0.44 | 0.88 / 0.96 / 0.92 | 0.0 % |
| all-pass 4 / 8 sections, pole search tuned ON the corpus | 0.00 / 0.00 | 1.00 | 0.1 % |

## Verdicts
- **I-034 flat-top: MERIT, loud-toggle only.** k~2.5 gives +2.2 dB median (every call >= +2.0) at 0.6 % out-of-band power (-22 dB), so it is clean in this band. Cost: current x1.7 (x1.66 per call). That is just inside the ledger's own x1.8 kill, so it survives, but only as a loud-mode option, not default. Gain only exists when the shaper sits between drive and limiter (the limiter squashes peaks; a flat-top before it with no drive is -1.2 dB). Near-square (k=12) buys +4.9 dB for x3.7 current, which is the 4/pi calc plus the limiter's own loss, not free. Caveat: measured in-band fundamental only; the 3rd harmonic of a 2.5 kHz call (7.5 kHz) is the bystander leak, 0.6 % power here, unmeasured acoustically.
- **I-036 all-pass crest reduction: KILL.** Fixed cascades lose 0.2-0.8 dB (they smear the chirps, which are already low-crest and sit in the limiter's release); a pole search tuned on this very corpus finds 0.00 dB. Kill criterion (mean < 1 dB) fails by 1 dB. Calls here are single FM sweeps, ~3 dB crest, as the brainstorm predicted; the "dense passage" 2-3 dB case does not occur in the 7 events.
- Caveats: 7 events, one corpus, search was small (40 draws x 2 sizes). Not a bench result; current is the model, not measured.
