# Sealing and service (spec O10, O12b): research note
```yaml
id: RES-SEAL
date: 2026-10-07
author: backlog agent (session 01Wg997D)
design: hw/current.yaml phase2 (shell_r2, MZ-2 board hung from the lid on VHB)
target: {rating: "IPX4 minimum, IPX5 preferred (spec O12b: outdoor wear in light rain)", service: "final build bonded, but must stay cuttable for firmware/cell/arm service (O10); firmware normally via dock DFU (O12a)"}
standard: "IEC 60529. [A: test parameters below are from memory, not re-read; buy/read the standard before the test] IPX4 = splashing from any direction (oscillating tube or hand-held spray nozzle ~10 l/min, >= 5 min); IPX5 = 6.3 mm nozzle jet ~12.5 l/min at 2.5-3 m, >= 3 min, 1 min/m2"
pass_rule: "no water inside the cavity (indicator tape on the board B face, cell and lid inner face); mic still within 3 dB of its pre-test sweep after drying; dock contacts no corrosion after 24 h"
```

## Leak paths (current design) and the recommended seal
```yaml
- id: S1
  path: "seam straight runs (tub tongue 0.35 x 0.5 / lid groove +0.05, y 12.1)"
  rec: "neutral-cure (alkoxy/oxime) RTV silicone bead in the groove at the final build; tape only at the test build"
  why: "cuttable along the 0.2 x 0.4 rebate (reg-pod-body 12), peels for service, flexible over temperature; NEVER acetoxy RTV (acetic acid corrodes copper and the dock contacts) [A: general practice]"
  alt: ["MS-polymer (stronger, harder to cut)", "epoxy (permanent: breaks O10)"]
  open: "product + its datasheet (cure by-products, adhesion to the resin) [TBD]"
- id: S2
  path: "seam convex corners (tongue stops 1.4 short) and the belly step (0.35 key, no rebate)"
  rec: "same RTV, applied as a fillet bead inside each corner before closing; mark the belly step with a rebate (reg-pod-body 12 remaining)"
  risk: "butt joints are the likeliest IPX5 leak (reg-pod-body 13); test them first"
- id: S3
  path: "mic duct: hex mesh seat -> D1.0 bore -> VHB annulus on the board F face -> D0.6 hole -> MEMS mic port"
  finding: "the duct is sealed to the cavity, but water that passes the mesh reaches the mic membrane directly (SPH0641 has no water rating)"
  rec: "hydrophobic open mesh (Acoustex 042 class, sub-audio-in issue 3) at the hex-seat floor; water is held by surface tension: Laplace pressure ~ 4*gamma*|cos theta|/d = 4*0.072*0.4/42e-6 ~ 2.7 kPa (~28 cm water) [derived; theta ~115 deg for a hydrophobic finish, A]. Enough for IPX4 spray [A]; IPX5 jet impact may exceed it: test"
  rejected: "non-porous ePTFE vent membrane: sim/checks/membrane_loss.py (2026-10-07) on the phase2 duct: 5 g/m2 costs -5.4 dB mean at the mouth / -10.7 dB at the floor, 10-20 g/m2 costs -11.5 to -22 dB, with +-10 dB ripple: fails R14. Use only if the IPX5 test fails AND a <= 2 g/m2 membrane exists (-0.9 dB mean at the mouth, but -5.5 to -9 dB at 60-96 kHz)"
  open: "hydrophobic treatment of the chosen mesh (not on the Saati sheet: ask the distributor) [TBD]; drain: the hex seat floor should not hold a droplet over the bore (CAD check)"
- id: S4
  path: "SW1 puck bore D2.6 through the lid -> pocket (KMT022 is IP68 itself, but the bore is not)"
  rec: "silicone skin (0.2-0.3 thick) bonded in the D4.6 recess with a silicone-to-resin primer + RTV, or captured mechanically under the armour plate edge; it is seal, return spring and puck retainer (sub-ui 4)"
  open: "skin material/thickness (tolerance enters the switch stack), primer [TBD]"
- id: S5
  path: "dock window (target glued in the belly) + its 5 contact bores + the 5.03 mm tab (sub-dock-usb DK-03, DK-07)"
  rec: "glue the target with the same RTV; pot the back (tails side) with a removable silicone potting so the cell can still be lifted; the contacts are the barrier"
  risk: ["LCSC calls the pod side a 'spring pogo receptacle': if the springs are in the pod, each contact bore is a leak path (sample needed, DK-03)", "docked while wet: 5 V across thin Au electrolyses VBUS: dry before docking (user rule) [A]; firmware could refuse charge for the first seconds while VBUS current is abnormal (idea, not designed)"]
- id: S6
  path: "heel channel exit (D0.8 neck into the rear gap) + land opening"
  rec: "RTV dot at the land opening and at the exit (reg-arm, notes/heel.md build order)"
- id: S7
  path: "pad cup (separate housing): seam claw + screw, conductor bore, set-screw access (reg-pad 3)"
  rec: "reg-pad 3 option A: test build dry, final build neutral RTV bead + dab in every opening"
```

## Service with the bonded build (O10, O19)
```yaml
firmware: "dock USB DFU (boot stub, write-protected; physical.md step 8 gate); no cut needed"
open_pod: "cut along the tub rebate (0.2 x 0.4) with a fine blade; RTV peels; the lid lifts the board on its wires (slack: DBG-17, dock_route.py lengths 31-42 mm + loop)"
rebond: "clean RTV off both faces, new bead; seam survives N cycles [TBD: count on the coupon]"
not_serviceable_without_damage: "board bond to the lid (VHB): warm 60-80 C and saw, lid reprint (reg-pod-body 14)"
```

## Test plan (coupon before rev 1, hardware: blocked by O21 only for purchased parts)
```yaml
coupon: "printed tub + lid (current STLs) with the seam bonded as S1/S2, a dummy board (bare FR-4 30 x 12 on VHB with the D0.6 hole), indicator tape inside, mesh in the seat, skin in the recess, a dummy dock target block glued + potted"
steps: ["IPX4 spray 5 min per IEC 60529 (all orientations)", "open along the rebate, inspect + photograph indicator tape", "rebond, IPX5 jet 3 min", "repeat open/rebond 3x: count the cycles the rebate survives"]
order: "S2 corners and S5 dock first (most likely failures), then S3 mesh"
owner_inputs: none (printing and spraying are bench work at the test build)
```

## Sources
```yaml
- "spec O10, O12 (docs/spec.md L636-L638)"
- "reg-pod-body.md sealing paths + issues 5, 12, 13, 14; sub-dock-usb DK-03, DK-07; sub-ui 4; reg-pad 3"
- "sim/checks/membrane_loss.py, sim/checks/mesh_pick.py (2026-10-07)"
- "Saatifil Acoustex TDS (datasheet-provenance.md row)"
- "IEC 60529 [A, not re-read]"
```
