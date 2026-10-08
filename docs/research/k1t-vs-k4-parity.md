# K1-thin (k1t) vs K4: parity table (N-K1T-PARITY, 2026-10-08)
Sources: repo only. Pen test (A-K4-VISION, docs/brief/queue.yaml) picks one; this lists what each side still owes.
k1t shell checks re-run 2026-10-08: `ULTRASONIC_DESIGN=k1t python3 hw/mech/shell_r2.py` (3G fence) -> hw/mech/out/k1t/checks.json.

| Item | K4 | K1-thin (k1t) | Source |
|---|---|---|---|
| L x T x H (mm) | 49.85 x 6.4 x 15.25 (out/k4s_lift) | 33.8 x 8.5 x 14.8 | hw/mech/out/k4s/checks.json envelope; docs/system/physical.md l.221; out/k1t/checks.json envelope |
| Envelope | 5019 mm3 | 4779 mm3 | same |
| Worn mass (pod) | 9.43-10.58 g (nose 6.16-6.84 / ear 3.27-3.73) | 9.6-11.5 g | physical.md l.221; docs/system/reg-pod-body.md Variants |
| Front edge X0 vs VISION_X 29.5 (hw/mech/pod.py l.35) | 17.65 (out/k4s_lift, O34 lift default): 11.85 mm inside the estimated no-go line; passes only if the pen-test line is <= 12.6 mm | 33.7 (67.5-33.8): clear by 4.2 mm | out/k4s checks envelope.x; queue.yaml A-K4-VISION |
| Cell / battery hours | Renata ICP401230UPR 130 mAh; ~10-16 h awake (175 mAh model x 0.74: 13.4-22.0 no LED -> 10.0-16.3) | identical cell and circuit: same | docs/system/sub-power.md l.177-181; fw/variants.yaml K1_130. Spec wants >= 8 h: both pass; scaled, not re-simulated for 130 mAh |
| Charge time | 130 mA = 1C CC (~1 h) + taper; total TBD bench; <20 C is 50 mA (>= 2.6 h) | same (same U3 BQ25180, same cell) | sub-power.md l.146, l.186 |
| Boards | 2 x 6-layer (P, M) at L 15.5: DRC 0 / 0 unconnected, place PASS | 1 x Phase-2 board routed.kicad_pcb: drc.json 0 viol / 0 unconnected (drc2.json 7 unconnected is a stale alt route) | hw/pod/k4/out/summary.json; hw/pod/draft_r2/out/drc.json |
| Release files | gerber+drill zips, BOM, CPL, sourcing lock, manifest in .pcba-workflow/k4-release; gate BLOCKED (B4 6L stackup, B5 pin-1 for 7 parts; B1-B3, B7 cleared) | none: no gerbers/CPL/gate in .pcba-workflow for draft_r2; only bom_jlc_mz2.csv + older sourcing-lock.csv | .pcba-workflow/k4-release/gate.yaml |
| Shell checks | 0 clashes except tub/cell 0.14 (open); heights/ledge/post checks exist; ledge VHB 104 kPa vs 85 limit unless post gap <= 0.03 (N-POST-GAP) | 0 clashes, corridors 0, all parts 1 solid, stowage 164 mm3 (need 107-142) OK, B gap margin 0.32 OK, F gap slack 0.05, SW1 pocket ok only with the dome variant (pocket breaks outer face = True in default k1t run), duct passes only with gauge pin (walls-only worst 1.16 vs 0.175 FAIL) | out/k4s, out/k1t checks.json |

## What k1t lacks to be order-ready (effort in Claude working time; owner waits flagged)
| Gap | Why | Effort |
|---|---|---|
| 1. 0.6 mm wall proof | walls/lid 0.6 are below resin min 0.6 at the corner (0.14 under chamfer), groove lip 0.2, rebate 0.4; coupon not printed | 30 min to finalise coupon; **owner print + home tests T1-T6** (hw/mech/notes/coupon_wall06.md, backlog Q2-WALL06) |
| 2. Button | KMT022 stack breaks the 0.6 lid. Fix A: Phi4 metal dome on new F pads (HYP 600-415S, C256252/C256257) = board F-copper edit, re-route/DRC/re-release; or C: proud skin, no board change | A ~1.5 h (board edit, DRC, interfaces heights FAIL until done); C ~20 min but pre-press risk |
| 3. Duct | lid 0.6 fails R14 nominally in every option; passes only with gauge pin (flush0.1 MC 0.63-0.70) | ~1 h acoustic re-run; bench check needed |
| 4. Release package | no gerber/drill/CPL/gate for draft_r2; sourcing lock predates; 6L-vs-phase2 stackup n/a (it is 4L) | ~1.5 h (adapt build_release.py), plus pin-1 preview items shared with K4 (owner) |
| 5. Open K4-era upgrades not ported | k4 firmware notch/variants default K4 (hw/current.yaml); k1t uses r2 notch; dock under-cell and BM28 pods not in phase2 board; Phase-2 dock/arm unchanged | ~1 h to confirm fw/variants + dock for r2 |
| 6. Renders/mass roll-up | no k4-review style renders for k1t other than on-glasses-k1t-vs-k4; mass range is wider (9.6-11.5) | ~30 min |

Total k1t to order-ready: ~5-6 h Claude time plus the owner's wall-coupon print, if the pen test rules K4 out.
