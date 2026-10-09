# X-r5-vision: three ways to keep the front out of the vision zone (2026-10-08, RADICAL, calc only, nothing run)
Problem (R-vision.md): line 11.5-21 mm from hinge (median ~15, p=11.5), K4 front X 17.65 passes only if line <= 12.6 (~15-20 %). D-k4trim: best X0 24.2 with custom cell. Target: front X >= 21 (theta 105 clears), ideally 29.5 (spec). Constraints: T <= 6.4, >= 8 h worst (112.5 mAh usable, 10.55 mA), 130 mAh Renata 4.5x12.7x31 kept.
Key fact from dims_k4.py: the pod is 49.85 long, rear end pinned at 66.6 only because the heel exit (wire to the tragus pad) is frame-fixed. Nothing says the pod must END there; only the pad must.

## I-029 Slide the whole pod rearward over the ear helix (TOP: least change)
- Idea: pod stays one piece, X0 17.65 -> 30.0 (shift 12.35 mm, rear end 66.6 -> 79). The arm passes over the helix there; the pod sits on the outer face of the arm above the ear. Heel exit becomes a 12-15 mm litz lead running forward along the arm to the pad. Nose load falls further (spec l.505: 3.6 -> 3.1 g already).
- Numbers: front X 30.0 (clears 29.5, theta 110 + margin); T 6.4 unchanged; 130 mAh = 9.2 h unchanged; +12.4 mm litz (0.1 mm, ~0.1 ohm, negligible vs 8 ohm-class exciter); mass +0.05 g wire; pod centre moves ~12 mm back (moment on ear +~20 %: 5 g x 12 mm).
- Costs/risk: arm bend/ear height must allow 79 mm of straight arm (assumed ~85-95 on typical 135-145 temples [A]); pod rear sits on ear top, so outer-face thickness 6.4 adds to head-side clearance of nothing but may press the helix if arm is cheek-close; charging dock pads/magnets at X0-relative positions move with the pod (fine); mech redo: wire route, dims_k4 exit.
- Kill test (30 min, owner): measure her frame hinge-to-ear-bend distance and the arm-to-helix gap, 6.4 mm cardboard block 49.85 x 14 at X 30-79.8 taped on, wear 30 min: fail if bend < 80 mm, block touches/pushes the helix, or it slides forward (CoG). Plus pen test at same time (R-vision p measure).

## I-030 Cell forward, stack behind the ear (BTE tail), 4-wire flex
- Idea: cell stays X 34.8-65.8; the 15.5 mm stack (P+M) moves behind the ear root at X ~67-85 (hearing-aid style, like Bose Frames battery-behind-ear precedent [recalled]); heel lead only ~5 mm. Front element = cell + 0.6 wall + stop gap: X ~33.
- Numbers: front X ~33 (margin +3.5 over spec line); T 6.4; 9.2 h; mics: still need to sit forward (stereo): keeps X-arch idea 1 flex tail (2 PDM mics ~10x6x3 at X ~33-40, now behind the line so no tail visible), 4 wires x 50 mm, 33 ohm series R. Nose load: stack ~2 g moves back -> -0.5 g.
- Cost: two bodies + flex + BM28 relay redo; behind-ear tail thickness 6.4 against the mastoid, comfort risk; P/M layout redo (weeks) vs I-029 none. Rated second because it gives the most margin and keeps the cell where the arm is straightest.
- Kill test: 1) as I-029 but measure straight arm >= 85 mm and mastoid clearance behind ear >= 6.4 mm with a 15.5 x 14 block; 2) PDM on 50 mm flex pair at 3.07 MHz: fail if SNR drop > 1 dB (shared with X-arch kill).

## I-031 Stack UNDER a 3 mm cell (overlap, single-face stack) — probably fails 8 h
- Idea: remove stack length by overlap. One-face 0.8 mm board, parts <= 1.0 -> stack 1.8; cell 3.0; walls 0.6+0.6, tape 0.4: sum 6.4 exactly. Pod L = 0.6 + 1.1 + 31 + 0.6 = 33.3, X0 = 66.6 - 33.3 = 33.3.
- Numbers: front X 33.3. Cell 3.0 x 13.2 x 31 = 1.23 cm3 x ~65 mAh/cm3 [A, thin cells are less dense than the 73 quoted] ~ 80 mAh. 8 h needs 112.5 -> runtime 80 x 0.75 / 8 h = 7.5 mA vs 10.55 (-29 %); I-027 only 0.4 mA. 2C pulse 160 mA < 219 peak clamp: needs clamp 160.
- Verdict: only if mean current falls to 7.5 mA AND peak clamps; both lose loudness (see R-loudness-conflict). Stays as the "overlap" probe. Pass chance ~10 %.
- Kill test (calc, 1 h): sum mA from sub-power.md with every saving taken; kill unless <= 7.5 mA with no loudness loss; also needs a real 3.0 mm cell datasheet at >= 2C.

## Ranking (thin first, wearable wins)
1. I-029 (X 30.0, zero thickness change, no electrical change, one kill test). Do first; measure p and theta in the same session.
2. I-030 (X ~33) if I-029 fails the bend/helix test.
3. I-031 only as a research probe.
Free add-on: mount pod on the INNER face (toward temple): d 35 -> ~29, saves ~1.5 mm of line at theta 105 [calc: 6 x tan15 = 1.6]; compatible with all three.

Integration-map cross-check (docs/system): touches mech/dims_k4 exit route, sub-power (unchanged), battery (unchanged), dock X0-relative pads; need ECR + `tools/plm.py impact` before any change. Not run here.
