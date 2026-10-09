# R-tragus4k: would 4 kHz playback gain ~7 dB at the tragus? (2026-10-08, I-028)

**Verdict: GAIN IS REAL IN SIGN, SIZE UNPROVEN (0 to +7 dB, central guess +3 to +5); NOT a firm gain. Bench-only (I-020b). Naturalness for bat calls: fine, a tuning knob not a blocker.**

## Primary sources retrieved (PubMed, 2026-10-08; Consensus quota exhausted until Nov 1)
- Nishimura, Hosoi et al., Laryngoscope 2014;124(5):1214-9, doi 10.1002/lary.24485 (PMID 24166692): thresholds at 0.5/1/2/4 kHz, 8 subjects. Cartilage-conduction (CC) threshold FORCE levels "remarkably lower" than bone conduction; ear-canal airborne sound is a main path. No numbers in abstract.
- Nishimura, Hosoi et al., Auris Nasus Larynx 2015;42(1):15-9, doi 10.1016/j.anl.2014.08.001 (PMID 25199744): thresholds rise tragus < pretragus < mastoid. **At 4 kHz in the OPEN ear, stray airborne sound radiated by the transducer dominates**; with earplug the tragus advantage is below 2 kHz.
- Nishimura et al., JASA 2020;148(2):469, doi 10.1121/10.0001671 (PMID 32872979): tragus/antitragus/incisure all CC-like; only 0.5-2 kHz measured.
- Nishimura et al., Audiol Res 2021;11(2):254-62, doi 10.3390/audiolres11020023 (PMC8293084): review; aural cartilage acts as a movable plate (loudspeaker-like), so output radiates into the canal.
- Not retrieved: numeric tables (paywalled/figures). Our 31.1/33.7/34.5/30.9/29.5 dB (Surendran 2023) stays repo-secondary, unverified.

## What it means for the +7 dB claim
1. Direction supported: threshold force falls toward 4 kHz at tragus-class sites (Surendran, 2026 B81 data in D-i020-band.md) and CC is airborne-assisted.
2. **The mechanism at 4 kHz is largely airborne radiation, not tissue conduction** (Nishimura 2015). Consequences: gain depends on pod-to-pinna coupling/ seal and on the cartilage "plate" resonance, so it varies with fit, may not be captured by an artificial-mastoid force threshold, and leaks audibly to bystanders at high level (privacy). Our force-based S-gate (I-014) would mis-predict it.
3. Surendran SD 6-9 dB per frequency: +7.3 dB is about 1 SD; paired difference uncertainty unknown. A transducer whose own response falls at 4 kHz (coil L, ~2.5 kHz tuned design) can eat the gain. Net force at 4 kHz is a bench measurement (E-series), not a literature number.
Range quoted: **0 to +7 dB**, not a firm number.

## Naturalness for translated bat calls (spec §5)
- Heterodyne (A): output pitch = |f_call - f_LO|; choose LO so the call centre lands at 4 kHz instead of 2.5 kHz: free, one parameter. Shifts everything up by 1.5 kHz (about 0.68 octave); sounds higher and "chirpier", still a tonal sweep.
- Log compression (B, the intended sole mode, spec v0.11): the output range is a mapping parameter; moving the top of the range to ~4-5 kHz keeps the contour and only changes pitch scale. Ear is more sensitive and speech-like fricative zone; risk is harshness/sharpness at 4 kHz and louder bystander leak (item 2).
- Per D-i020, 95.6% of programme power already sits in 2.5 kHz third-octave, so shifting is a retune, not a rewrite. A/B listening on the Shokz salvage bench decides taste.

## Next (cheap)
Bench: swept sine through the real pod at tragus, 1/2/2.5/3/4/5 kHz, force plus ear-canal mic, with and without a sealed-ear condition (separates conduction from airborne). Kill if net gain < 2 dB or leak > ambient-acceptable.
