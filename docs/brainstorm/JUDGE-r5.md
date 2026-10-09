# JUDGE-r5 (2026-10-08, Opus judge, desk review vs docs/system, D-k4trim, R-vision; nothing run)
Ledger fix: X-r5-vision rows renumbered I-029 (slide rearward), I-030 (BTE split), I-031 (overlap). I-028 stays tragus 4k (R-tragus4k).

| ID | Rank | Packet merit |
|---|---|---|
| I-028 tragus 4 kHz | needs-evidence | Bench-only (I-020b); 0..+7 dB unproven. No packet. Kill: tragus-force sweep + canal mic, kill if < 2 dB net |
| I-029 slide pod rearward | needs-evidence, strongest of the three, but NOT "least change" | Packet-worthy ONLY after the ear-geometry test below; as written the claim is wrong in places |
| I-030 BTE split | needs-evidence, weak | No packet. Redesign of both pods |
| I-031 overlap under 3 mm cell | killed | The proposal's own number: 80 mAh = 7.5 mA vs 10.55 mA budget (-29 %). Fails 8 h; R-loudness-conflict forbids buying it back with loudness |

## I-029 hard check (what the idea gets wrong)
1. **Pad/arm reach (the real blocker).** The arm is not a wire from the pod end to a free pad. Heel exit E = pod x 61.3 (hole 65.8-66.6), NiTi span 11.8 mm bends to pad socket (66.8), contact at x 70.6, z -25 (reg-arm, physical.md). Sliding the pod +12.35 puts the heel at ~78-79, i.e. BEHIND the pad (70.6). A "12-15 mm litz lead running forward" does not move the pad; the NiTi spring arm (superelastic, force set by span a=11.5, lever b=7.6, 19.3 deg sockets, no heat set) must now run forward and under the pod rear, where the strut-to-tub clearance is already 1.18 mm worn vs 1.4 target (reg-arm issue 6, reg-pad issue 6b). Alternative: keep heel at E and the pad, make pod a long tail rearward: that is I-030, not this. Net: arm, strut, heel, pad pose are all redone (3 regions + ECR), not "zero electrical, one test".
2. **Tragus pad reach.** Pad stays at 70.6, so tragus contact is preserved only if the arm geometry is rebuilt as above. Pod rear then overhangs the pad by ~9 mm lateral to the NiTi arm: the NiTi sweep (30 deg, jaw open/close) must clear the pod belly. Unquantified.
3. **Mic port.** Port at pod x 32.43 -> 44.8 (X0 +12.35). Still lateral and ahead of the ear, stereo spacing unchanged in pairs; acoustic sim (sim/acoustics, head-shadow geometry.py) reads dims_r2 so needs a re-run, but ~12 mm more toward the pinna is mildly good for pinna cues and bad for nothing obvious. Low risk, but not tested.
4. **Arm bend / does the frame reach.** Needs ~80 mm straight arm under X 0-79.8 (outside face clamp bands, VHB). Typical temples bend ~95-110 mm from hinge on 135-145 arms [A, unsourced]; the claim "79 mm" is plausible but fails on short/curved arms. Her frame measure decides. Unmeasured.
5. **Helix comfort / pressure.** The claim "over the ear helix" is overstated: pod end at 79.8 is still in front of the helix attach (tragus at ~70.6, helix root ~15-25 mm behind that, so ~85-95). The pod sits over temple/preauricular skin, on the outer face; pressure on the helix is not the issue, the 6.4 outside thickness against a hat/hair/mask strap is. Also: pad tilt (+-7 deg over jaw) and ear-top clearance for the 6.4 stack are unmeasured.
6. **Moment sign.** The proposal says moment on the ear rises 20 %. Moving mass toward the ear fulcrum REDUCES nose load (it says so too, 3.6->3.1 g); rear-of-ear sag is the thing to check (mass behind the pad), not nose load. Net weight balance: probably better.
7. **Vision.** Front X 30.0 clears 29.5 (R-vision line 11.5-21 mm, median 15). Real benefit: raises pass chance from ~15-20 % to ~100 % at theta 105 and absorbs p uncertainty, with zero thickness/runtime change. That is why it ranks first despite the cost.

Kill test (one line, 30 min, owner): tape a 49.85 x 14 x 6.4 cardboard block at x 30-80 on her frame outer face, hold the NiTi path with a cardboard strut at 70.6: fail if straight arm < 80 mm, block contacts the ear/helix, or the dummy arm cannot clear the block belly by 1.4 mm.

## I-030 (BTE split)
Merit in margin (front ~33), but two bodies, flex, relay redo, 4-wire PDM on 50 mm at 3.07 MHz (SNR risk, shared with X-arch kill), mastoid contact at 6.4 mm. It is the retreat if I-029 fails the arm-reach test, not a parallel candidate. Kill: PDM-on-flex SNR drop > 1 dB or behind-ear clearance < 6.4 mm.

## Owner packet
Recommend: no packet yet. Ask her for one thing: the I-029 block test + pen-test p/theta in a single sitting (R-vision wants these anyway). If it passes: open an ECR for arm/heel/pad rebuild (run tools/plm.py impact; touches reg-arm, reg-pad, reg-pod-body, physical, dock X0-relative pads). Options for her: (A) block test then ECR (recommended), (B) accept K4 at X 17.65 and bet on a 15-20 % pass, (C) go straight to custom-cell D-k4trim 24.2 (still short of 29.5). Integration-map cross-check was not run (judge scope).
