# Rev-1 tolerance review (2026-10-01)

Every fit and clearance in the current design. Values come from the CAD checks (`shell_r1.py`,
`heel.py` checks.json, `pad.py` checks.json) or the dimensions in those files. The resin rules come from
`docs/build/hardware.md`: holes under ~0.8 mm may close; recesses under 0.4 mm may fuse; self-tapping
pilots ~85 % of nominal.
**Print critical holes undersize and drill them to size after curing.**

Legend: ✅ fine · ⚠️ tight, with a note on what to do · ❌ not yet designed.

## Housing (tub + lid, bonded, no screws)
| Fit | Value | Verdict |
|---|---|---|
| Lid locating lip ↔ tub opening | 0.15 mm per side; 0.5 mm lip, 0.8 mm deep | ✅ Tape-test, then bond. A 0.15–0.3 mm bond line suits MS-polymer and neutral RTV. |
| Seam cut-guide groove | 0.4 × 0.4 mm | ⚠️ At the 0.4 mm resin minimum. Open it with a blade if it prints shallow. |
| Cell (175 mAh) ↔ tub | 0.3 mm tape gap; 0.07 mm at the strut-relief corner fill | ⚠️ The pouch's rounded corner gives more real clearance. Dry-fit the cell first. |
| Board ↔ cavity walls | 0.3 mm front, top and bottom; 2.1 mm behind the rear edge (board grown to 34 mm, 2026-10-01) | ✅ The rear 2.1 mm is the arm wires' path from the heel channel up to the J pads: 4 litz in ≤ 1.1 mm shrink tube fits. |
| Board retention | Two lid ribs press the outer-face clamp bands (0.05 mm gap when seated); 1.5 mm closed-cell foam strips on the cell, compressed to 1.4 mm, push the board up | ✅ Added 2026-10-01. Keep the 0.6 mm top/bottom edge bands free of parts on both faces (the rough layout does). |
| Switch plunger head ↔ lid bore | 0.15 mm per side (Ø2.9 in Ø3.2) | ✅ |
| Plunger stem ↔ switch | KMT0 travel is only 0.15 ± 0.1 mm | ⚠️ Stack tolerance (board ±0.1, lid ±0.1) can pre-press or miss the switch. Print the stem 0.2 mm long and sand it to a light touch. The silicone skin over it is the spring. |
| Dock target ↔ floor window | +0.1 mm per side (21.4 × 7.06 window for a 21.2 × 6.86 part) | ✅ Glued in, back potted. |
| Mic port | Ø1.0 through the lid | ✅ Above the 0.8 mm limit. Drill it to Ø1.0 after printing. |
| Frame adapter dovetail | 0.15 mm per side | ✅ Resin. On FDM use 0.25. |
| Adapter snap tab | ~1.6 % bending strain at release | ✅ Tough resin. |

## Arm joint (the wiring path, owner: "no pinched wires")
| Fit | Value | Verdict |
|---|---|---|
| Wire route | Rear side all the way: heel channel → flex zone → strut bore → rear riser → pad-board pads. **No crossing over the NiTi.** | ✅ Fixed 2026-10-01: they used to cross in the flex zone. |
| Heel channel (static) | Ø1.0 for the bare 4 × 0.21 mm litz bundle (~0.5 mm); walls ≥ 0.62 mm | ✅ |
| Heel mouth counterbore | Ø1.6 × 1.0 deep; seats the shrink-tube end | ✅ |
| Strut bore (static) | Ø1.2 bare bundle; walls 0.6 (rear face) / 0.85 (inner face) | ✅ |
| Strut-top counterbore | Ø1.6 × 1.7 deep; seats the shrink-tube end | ✅ |
| Shrink tube in the flex zone | Use a thin-wall 2:1 polyolefin that recovers to ≤ 1.1 mm OD. Leave ~2 mm of slack as a gentle S across the 3 mm flex gap. | ⚠️ The tube must not be tight between the two counterbores, or it becomes a strut. |
| Strut ↔ heel land | 1.50 mm, all 4 states | ✅ |
| Strut ↔ housing (rev 1) | 1.18–1.34 mm, all 4 states; never touches | ⚠️ Target was 1.4 mm. Locally relieved from 0.65 mm. Fine for clearance; keep hair and debris out of the joint. |
| NiTi in its flare | ≥ 0.009 mm from the R8 flare, all states | ✅ That near-touch is the strain limiter doing its job. |
| NiTi sockets (heel and pad) | Ø0.85 for 0.80 wire, blind | ✅ Print undersize, ream with a 0.85 drill in a pin vise. Re-ream to wire + 0.05 if you switch to 0.75 wire. |
| NiTi set screws | M1.4. Heel: from the front, into a brass nut. Pad: now from the front flat too | ✅ File a small flat on the wire where the screw lands. |

## Transducer pod (cup + cap, screws OK here)
| Fit | Value | Verdict |
|---|---|---|
| Wall minimum | All walls ≥ 0.6 mm except one internal web of **0.56 mm** (nut pocket ↔ front solder pocket) | ⚠️ Internal and potted, no leak path. Accepted. |
| Pad-board solder joints ↔ cap | 0.05 mm gap | ⚠️ **Tight.** Keep the joints low (≤ 0.45 mm); trim and flatten blobs before closing the cap. |
| Strut wire slot | 0.9 mm (top, the direction the wire moves) → 0.15 mm (at the socket) | ✅ From the NiTi model's four states. |
| Hex collar | Grown from 5.9 to 7.4 mm across flats, to wall the rear wire bore | ✅ Slightly bulkier pad top. **Check the Ear (open) clearance on your photos (E9).** |
| Cup closure | One M1.2 self-tapping screw, pilot Ø1.0 | ✅ |

## Two things to measure before printing for real
1. Print a **tolerance coupon** with the actual resin and printer: holes of Ø0.8/0.85/1.0/1.2/1.6 mm, slots of 0.3/0.4/0.5 mm, and a 0.15 mm slide fit. Adjust the numbers above to what really happens.
2. **Dry-fit the real cell and board** before bonding anything. The CAD uses the cell datasheet's *maximum* envelope.
