# X-arch: informed-radical architecture challenges (2026-10-08)
Sources: docs/spec.md (D1, battery bay l.299-307, §8 weights), docs/proof/{buildability,electrical,physical,thermal}/README.md, docs/research/k1t-vs-k4-parity.md. All new numbers are [A] (my arithmetic/assumption) unless a source is named. Nothing here edits spec §1. Owner decides.

## Baseline pain (from the proofs)
- Vision: K4 front edge X0 17.65 vs line 29.5 -> 11.85 mm inside (passes only if pen-test line <= 12.6 mm). k1t clears by 4.2 mm but is 8.5 mm thick.
- Build: step 3/4 (J1/J2 wires + BM28 mate) and step 9 (cell lead fold, diff 4) are the hard ones. 6L 0.8 mm unpublished (gate B4).
- Alerts: bridge peak clamped 208 mA (-3.6 dB); exciter is a 300 Hz-19 kHz inertial part at 1 N on the tragus; office ambient masks 2-3 kHz tones.

## Ranked ideas
| # | Idea | Moves | Verdict |
|---|---|---|---|
| 1 | Electronics to the arm, front = mic-only tail | vision line, mass balance | TOP |
| 2 | Tactile alert channel (sub-300 Hz) | alert audibility | cheap, do now |
| 3 | Rigid-flex single board wrapped on the cell | 2 hard steps, B4 | high value, unverified vendor |
| 4 | One cell in the frame, wires through both hinges | thickness, mass, stereo link | big, risky |
| 5 | 4L 0.8 mm (published) via fewer layers + cell-as-lid | B4 gate | fallback |

## 1. Front module is only the mics; board + cell live together in the arm (TOP)
- Why: the vision problem is a *front-edge* problem. The spec already puts the cell along the arm (l.300) and says the electronics stay at the hinge. But the arm in front of the ear has length: ~50-60 mm cell centre behind the hinge (l.494). Put P+M+cell in that arm run, front keeps 2 PDM mics (SPH0641, a digital mic: tolerant of a few cm of cable at 2.4-3.1 MHz) + sniffer port on a ~3 mm thick flex tail. Front edge then set by a ~10 x 6 x 3 mm mic housing, not 49.85 mm of pod.
- Estimate: pod length 49.85 -> front part ~10 mm; the 11.85 mm deficit is eliminated if the front part sits >= 12 mm behind the current front, i.e. arm module starts 12+ mm further back. Mass moves back ~4-5 g from the nose pads: spec table l.505 shows cell-back already cuts nose load 3.6 -> 3.1 g (-14 %); electronics (est. 2 g) would add ~-0.5 g nose. [A]
- Cost: one 40 mm flex (2 x 2-layer, ~$1-3 JLC FPC), 4 wires (CLK, DATA x2 shared line, 3V0, GND); mic-to-MCU latency same (no change). Loses stereo baseline? No: baseline is pod-to-pod across the head; mic location only shifts ~25 mm rearward -> ~0.1 dB-level nothing, ITD-equivalent pinna offset to be re-checked.
- Risk: 2-3 MHz PDM over 40 mm (needs series R 33 ohm + ground-guarded pair); mic port/sniff geometry in the old front position was designed with the lid duct (R14 fails nominally) - a thin tail may be *easier* (no board stack under the port); arm interior thickness at the ear side must not exceed 6.4 mm.
- Kill test: 1) bench two SPH0641 on 40 mm flex pair at 3.07 MHz, FFT noise floor vs on-board baseline; fail if SNR drops > 1 dB or crosstalk spurs > -60 dBc. 2) Cardboard + weighted dummy on her glasses, 30 min, front-edge vs vision line with the pen test. ~1 h Claude + 1 owner print.

## 2. Add a tactile alert channel (sub-300 Hz pulses through the same exciter)
- Why: office noise masks 2-3 kHz tones, but skin vibration detection at the face (tragus is highly sensitive; vibrotactile threshold is lowest around 150-300 Hz) is independent of acoustic ambient. Alert = 2-3 pulses of 180 Hz, 100 ms, felt as a buzz. [A: tactile band lore; verify]
- Estimate: exciter is rated from 300 Hz, so 180 Hz is below-spec but the inertial coil still moves; force falls ~12 dB/oct below resonance (1st-order estimate), meaning ~ -7 dB at 180 Hz vs 300 Hz. At the 208 mA clamp this may still be above the skin threshold (threshold at 200 Hz ~ 0.1 m/s2 range at fingertip; face unknown). Needs measurement.
- Cost: firmware only (fw tone table + test), 0 g, 0 BOM. Risk: it is a different, annoying sense; D1 spec promises quiet by default; may buzz teeth/jaw (condyle in front of tragus). 
- Kill test: owner wears dummy exciter at 1 N, sweeps 100-400 Hz at clamp current with ambient pink noise at 65 dBA; fail if she cannot detect > 90 % at <= 208 mA or rates it uncomfortable. 20 min of her time. Stay under the existing limiter; no hardware.

## 3. Rigid-flex: one board, folded around the cell
- Why: BM28 mate, P/M pair, the 4-way pad wires and the fold all exist because two boards need joining and a cell needs leads. A rigid-flex with the cell as the mandrel (pouch cell ~4.3 x 12.5 x 31 mm) wraps the electronics: rigid island A (MCU/audio) on one face, island B (bridge/charger/pads) on the other, flex hinge across the cell end. Cell leads weld to pads in the rigid island (no hand-fold, step 9 removed). Steps 3-4 collapse to one wire step; BM28 pair (C424570/C424571) removed.
- Estimate: removes 1 connector (0.6 mm gap tolerance in chain), 1 hard-mate step (diff 3, 20 min) and the step 9 diff-4 fold (25 min) -> build time ~ -45 min of 5.6 h (~-13 %) [A from buildability table]. Stack-up: rigid sections can be 4L; 4L 0.8 mm is published at JLC (JLC04081H-3313, physical proof #1) so gate B4 may close. But rigid-flex stack-ups at JLC are a separate product line; I have NOT checked their min thickness/min bend radius. [Low]
- Cost: rigid-flex JLC price ~5-10x FR4 for this size [A, unverified]; small-qty fine (2 pods). Reflow of parts on flex-adjacent rigid areas needs stiffeners. 
- Risk: bend radius vs cell thickness 4.3 mm (r >= 6x flex thickness -> OK for 0.1 mm); DRC/layout redo (weeks); mic port through the rigid island; the K4 layout work (DRC 0) is thrown away.
- Kill test: ask JLC for the rigid-flex stack-up table (fetch, dated); if min total rigid thickness <= 0.8 mm and 1 mm bend radius is allowed, proceed to a paper fold in card at 1:1 around a dummy cell. 30 min. If JLC rigid-flex has no 4L 0.8, kill.

## 4. One cell for both arms, in the frame front, 2-wire through both hinges
- Why: today each pod carries a 130 mAh cell (5.9 g? ~2 x 4.3 mm). A single ~260 mAh cell in the frame bridge/brow (or a thin pouch along the top rim) gives more hours and takes ~3.5 g and 4.3 mm of thickness out of each pod; both pods then share ground/clock for free (spec l.307 'link between sides', parked option for phase-lock).
- Estimate: pod thickness 6.4 -> ~2.4 mm board+lid (cell removed) [A]; ~half mass at the ear (ear 3.27-3.73 g mainly cell) -> comfort. Charge once, not twice (-1 dock step).
- Cost: needs wires across hinges (0.1 mm litz in the frame) and a frame mod she accepts; battery in the bridge sits above the nose (she hates nose load: spec comfort rule) - 4-5 g on the nose pads could erase the benefit.
- Risk: single point of failure (one cell dead, both sides dead); spec §1 'two independent pods' may be locked language - check §1 before even proposing. Hinge flex life. Safety: single big cell near the face.
- Kill test: (a) read spec §1 text for 'independent'; (b) mass model: nose load with 4.5 g on bridge vs 3.1 g now (compute only, 15 min); (c) hinge cycle test with litz on her old frame 10k cycles. Kill if nose load > 4.0 g or §1 forbids.

## 5. Fallback: drop to 4L, kill the P/M split by using k1t's published stack-up
- Not unorthodox, but it is the cheap exit from B4: k1t is 33.8 mm long, 8.5 mm thick, clears vision by 4.2 mm, DRC 0 on a 4L 0.8 mm published stack. Combine with idea 1: put k1t's board *behind* the hinge in the arm, so the 8.5 mm thickness is hidden in the arm run where the cell already is (arm is 4.3 mm cell + board -> ~8.5 mm). Front = mic tail.
- Kill test: pen test (queue A-K4-VISION) first; if it passes K4, skip.

## Recommendation
1. Do idea 2 now (free, firmware, 20 min owner test).
2. Prototype idea 1 as a card mock + PDM-on-flex bench; if it passes it fixes vision, balance and mic-port difficulty without touching the cell or the loudness chain.
3. Query JLC rigid-flex tables before spending layout time on idea 3; keep idea 4 parked behind a spec §1 check.
Doc-set impact if chosen: integration-map, reg-pod-body, physical.md; run tools/plm.py impact before any ECR.
