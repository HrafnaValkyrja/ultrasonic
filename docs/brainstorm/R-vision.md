# R-vision: where is the "peripheral vision" line? (2026-10-08, desk research, web search; no full-text reads)
Question: pod.py VISION_X=29.5 (pupil 11.5 behind hinge + 18). K4 front 17.65 passes only if pen-test line <= 12.6 (no margin).
## Evidence
- Temporal field, Goldmann largest isopter: ~90 deg (AAO Goldmann image page; NCBI Bookshelf NBK220 "Clinical Methods" ch. on visual fields; BMJ Pract Neurol 15(5):374, ~90 temporal/60 nasal/60 up/70 down). One patient-education page: ~100. Korean Octopus-Goldmann normative (bvsalud wpr-15041): field widest inferotemporal. No source found for 110; spec's 110 is the high tail (I did not retrieve Niederhauser&Mojon 2002 numbers; check).
- Frames: Sudmann et al., J Optom 2025 (doi 10.1016/j.optom.2025.100582, PMC12902225), n=30: thin frames/temples negligible loss; thick ones lost peripheral points in 20-37 %; larger vertex distance (VD) predicted loss. Patent perimetry background: temple side of the face is "essentially free" (unobstructed). Snap patent: bulky temples reduce peripheral vision.
- Vertex distance: ~12 mm convention (general knowledge; not confirmed from a standard in this search). Hinge sits near the frame-front plane, so pupil ~ 11-18 mm behind hinge. No primary pupil-to-hinge anthropometry found.
- Blur / near point: NOTHING primary found on whether objects on the temple arm are noticed. Optics: object 35 mm lateral is far inside the near point (~100 mm), so it is blurred, but dark blobs and motion are still detected in the periphery. Treat as "seen" for safety.
## Recompute: line = p + d*tan(theta-90), d = lateral pupil-to-arm 30-40 mm (spec 35), p = pupil behind hinge
theta 90: p | 95: p+3.1 | 100: p+6.2 | 105: p+9.4 | 110: p+12.7 (d=35; d 30-40 gives +-15 %)
p=11.5: 11.5 / 14.6 / 17.7 / 20.9 / 24.2. p=15: 15 / 18 / 21 / 24 / 28. Spec's 29.5 = p 11.5 + 13 + 5 margin = 110 deg + margin at p 11.5.
Plausible pen-test (static, eyes fixed, she is the subject): temporal edge 85-105 deg, median ~95 -> line 11.5-21 mm (p=11.5), median ~15 (no margin).
## K4 verdict
K4 needs line <= 12.6: theta <= ~92 deg at p=11.5 (and p unmeasured; at p>=13 only theta<=88). Pass chance ~15-20 % (p=11.5), ~5 % if p>=14. Do not plan on K4 passing; plan the arm-rear split that clears ~21 mm (theta 105, p 11.5) and treat 29.5 as conservative. Measure p (hinge to pupil, side photo) first; it moves the line more than theta does.
