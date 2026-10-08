# Reopening a bonded pod (RPB-12, O19 service)

For the owner, by hand. Applies to cell swap, arm swap, board swap. Source: `docs/system/physical.md` Service; geometry `hw/mech/shell_r2.py` (seam_rebate, 2026-10-07). Each reopening uses one cut-and-rebond cycle; the cycle count the seam survives is unproven until the spray coupon is opened and rebonded 3x (issue 14).

## Where the cut line is

| Run | Marker | Size |
|---|---|---|
| Straight runs at y 12.1 (top, rear, bottom, front above the step) | rebate in the tub, round the outside | 0.2 deep x 0.4 high |
| Belly step (z -8.9, x < 55.0, below the lid face) | witness groove on the outer face, just under the step | 0.1 deep x 0.4 high |

The two meet at the corner of the step. Cut along the groove/rebate: the lid skirt is above it, the tub below. The tongue (0.35 x 0.5) sits inside the joint, so do not go deeper than ~0.5 mm.

## Tools

- Fine razor blade or hobby knife (new blade), thin spudger (plastic), floss, tweezers
- Hot-air gun at 60-80 C only for a board swap
- Soldering iron, flux, wick; isopropyl alcohol; the seam adhesive used at assembly (same product, physical.md step 12)

## Steps

1. **Power off, undock, unplug nothing yet.** Discharge-safe: cell stays connected until step 6.
2. **Score the line.** Run the blade point along the rebate/groove, 2-3 light passes, 0.3 mm deep at most. Do not twist; the wall behind the rebate is 0.6 mm.
3. **Open the seam.** Start at the rear straight run (the lid hinges about the rear seam edge). Slide the spudger into the scored line, work forward a few mm at a time. Never pry on the belly: the dock window and the magnet target are tub.
4. **Lift the lid and the hanging board together,** hinged about the rear edge, no more than 180 degrees. The wires have the slack for this (arm 2.65/3.04 mm, dock 0 mm worst, so keep the dock loops).
5. **Cell:** desolder J5/J4 (J9 if the NTC is fitted). Free the cell with floss through the VHB; never pry a pouch. New cell on new VHB.
6. **Arm:** desolder J1/J2/J7/J8 on B, release the M1.4 heel set screw, draw the bundle out, new arm per assembly steps 2-5.
7. **Board only:** warm to 60-80 C and saw the board VHB from the rear with floss. Accept a lid reprint (about 1 g resin).
8. **Clean the joint.** Remove old adhesive with the blade and alcohol; the tongue and groove faces must be bare resin. Re-measure: the lid must seat on the tongue dry.
9. **Rebond** per physical.md step 12, then check the seam again (spray test when available).

## What to replace

| Part | Always | Sometimes |
|---|---|---|
| Seam adhesive | yes | |
| Cell VHB (0.25) | when the cell comes out | |
| Board VHB (4914) and its D1.0 mic-duct hole | board swap | |
| Lid | | board swap (reprint) |
| Cell | | cell swap only |

## Fail lines

- Blade slips into the tub wall: stop, check wall thickness before the next pass (min 0.6).
- Belly dock wires tense when the lid lifts: stop, re-cut the wires 2 mm long as a loop (`hw/mech/dock_route.py`).
- Lid will not seat after cleaning: sand lightly the lid groove land only, not the tongue.
