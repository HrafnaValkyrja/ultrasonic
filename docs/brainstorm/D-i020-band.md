# D-i020: shift programme energy to 2-4 kHz (kill test, 2026-10-08)

**Verdict: KILL as stated (<2 dB).** Premise false: 95.6% of translated-programme power already sits in the 2.5 kHz third-octave; 0.2% is outside 2-4 kHz.
Residual (not the ledger claim): front-of-tragus data prefer 4 kHz over 2.5 kHz by ~7 dB -> new row I-020b, bench-only.

## Sources (what was and was not verified)
- ISO 389-3 (1994 withdrawn; 2016 renamed RETVFL, mastoid reference, forehead offsets in Annex C): standard pages confirmed 2026-10-08 (iso.org/standard/22495.html); **numeric 1.5-4 kHz table is paywalled, not retrieved.**
- Henry & Letowski, ARL-TR-4138 (May 2007): low rows seen in excerpt 2026-10-08 (67.0/64.0/61.0/58.0 dB re 1 uN at 250/315/400/500 Hz). The 1.5-4 kHz values used here (36.5/31.0/29.5/30.0/35.5 at 1.5/2/2.5/3/4 kHz) come from repo `shared-params` (secondary, unverified against the PDF).
- Surendran 2023 front-of-tragus, n=21, SD 6-9 dB: 31.1/33.7/34.5/30.9/29.5 (repo, `bone_tf.json`).
- Context: 2026 B81 toneburst thresholds 68/60.5/47.5/44.5 dB re 1 uN at 0.5/1/2/4 kHz (Int J Audiol 2026, different transducer, not RETFL): thresholds keep falling to 4 kHz.

## Result (sim/acoustics/i020_band.py -> out/i020_band.json; 7 calls, 200 ms peak window, same chain as audibility_reconciled)
Margin = band force (exciter N/A at band) - threshold; shift = all current into best band within 2-4 kHz.
| Threshold set | Best band | Gain vs today (median, range) | Gain vs power-sum |
|---|---|---|---|
| Mastoid RETFL (H&L) | 2.5 kHz | **+0.2 dB** (0.1-0.4) | 0.04 dB |
| Front tragus (Surendran) | 4 kHz | **+7.3 dB** (7.2-7.4) | 6.6 dB |
Band power share (1/3-oct 1.0/1.25/1.6/2.0/2.5/3.15/4.0/5.0 k): 0/0/0.3/0.2/95.6/3.8/0.0/0.1 %.
Trap: letting 5 kHz compete gives +11 dB, but that is extrapolation beyond the measured threshold range; excluded.

## Reading
- ISO-type mastoid curve: 2.5 kHz is already the minimum (29.5): nothing to gain. Kill.
- Front site: the 7 dB is 5 dB threshold (34.5 vs 29.5, inside the 6-9 dB subject SD, n=21) plus 2 dB exciter transfer. Real but soft; moving the difference tone changes the heterodyne carrier plan and mic band, so it is a bench test (E-series), not a firmware mapping.
- If real, 7 dB = x0.45 current. Do not bank it.
