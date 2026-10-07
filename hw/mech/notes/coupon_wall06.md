# 0.6 mm wall coupon: print and home test (packet Q2, 2026-10-07)

**Why:** K1 at 8.5 mm thick (synthesis K1) needs 0.6 walls and a 0.6 lid. Our resin rule says the minimum wall is 0.6 (`frame.RESIN`), so nobody knows yet if it holds. This coupon answers that before anything depends on it. Each part has 0.6 walls on the left and today's 0.8 on the right, so every test compares the two in your hand.

**Files:**
- `hw/mech/out/coupon_wall06/tub.stl` and `lid.stl`: make them with `python3 hw/mech/coupon_wall06.py` (fenced).
- Picture: `coupon.png`. Numbers: `checks.json`.

Each part is 22 x 14 mm, about 0.44 cm³ (tub) and 0.29 cm³ (lid) of resin.

## What is on it (all from the real shell constants)

| feature | 0.6 side (K1-thin) | 0.8 side (Phase 2) | worry |
|---|---|---|---|
| wall / floor | 0.6 | 0.8 | stiffness: 0.6 is ~2.4x softer (t^3) |
| outer corner, 1.0 chamfer (shell today) | **0.14 mm left at the corner** | 0.42 | may print with a pinhole or crack |
| outer corner, 0.6 chamfer (back-left) | 0.42 | - | the fix if the 1.0 corner fails |
| lid groove for the tongue (0.35 + 0.05) | **0.2 mm outer lip** | 0.4 | lip may break when you press the lid on |
| seam rebate 0.2 x 0.4 (outside, under the rim) | **0.4 mm wall left** | 0.6 | cut line weak spot |
| lid plate | 0.6 with a 0.1 mesh seat + bore | 1.0 with the recommended 'rec' stack: hex seat 0.3 + bore, puck bore D2.6, skin recess 0.1, SW1 pocket | ream the bores with the 1.0 drill |

## Print
1. Same resin and settings as the pod. Orientation: the way you would print the tub (rim up) and lid (outer face down). Supports only outside.
2. Wash and cure as usual. Print **two sets** so one can be broken on purpose.

## Tests (about 20 min, tools: loupe, kitchen scale, pencil with eraser, 1.0 drill in the pin vise, a lamp)

| # | do | pass | fail means |
|---|---|---|---|
| T1 | Hold the tub in front of the lamp. Look at the corners and the rebate with the loupe. | No light through any corner or the rebate. No layer split. | A light pinhole at the front-left (1.0 chamfer) corner: 0.6 walls need the 0.6 chamfer. Light through the rebate: drop the rebate to 0.1 deep on thin walls. |
| T2 | Press the lid onto the tub with your thumb, then pry it off with a fingernail at the seam. Do this 10 times. | Both lips (0.2 on the left, 0.4 on the right) intact. Lid seats flat. | A broken 0.2 lip: on 0.6 walls the groove must move (tongue 0.25 wide) or the lid wall stays 0.8. |
| T3 | Ream all three bores with the 1.0 drill by hand. | The 0.1 mesh seat (left) and 0.3 seat (right) keep their floors. No crack from the bore. | Floor breaks through: seat too shallow to print. Write down the depth you got. |
| T4 | Put the scale on the table, the tub floor-down on it. Press the middle of the 0.6 side wall with the pencil eraser to 300 g, then 500 g, then 1 kg. Repeat on the 0.8 wall. | No white stress mark, no crack. The wall springs back fully. Model ~0.12 mm bend at 500 g (0.8: ~0.05) [A]. | A white mark or crack below 1 kg (10 N, a firm pinch): 0.6 is too thin for this resin. |
| T5 | Same as T4 on the 0.6 lid plate, the flat area. | Same as T4. | Same as T4. |
| T6 | Drop the closed coupon 3 times from 1 m onto a hard floor. | No crack and no lid pop-off. | Note where it cracked. |
| T7 | Break set 2 on purpose: pinch the 0.6 wall between your fingers until it snaps. | Only to feel the margin. Note roughly how hard it was. | - |

**Report back:** a photo against the lamp (T1), and pass/fail for T2-T6 with the gram value where anything gave way. With that, Claude sets the K1-thin walls (0.6 or 0.7) and the chamfer, groove and rebate rules.
