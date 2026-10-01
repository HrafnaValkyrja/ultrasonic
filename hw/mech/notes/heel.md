# Heel: the NiTi arm's root (rev 1 = the prototype)

**Date:** 2026-09-30 · **Source:** `hw/mech/heel.py` (run it: `source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0 python3 hw/mech/heel.py`, about 12 s)
**Outputs:** `hw/mech/out/parts/heel/`: STEP/STL, `checks.json`, `heel_sections.png`, `heel_views.png`
**Interface:** `hw/mech/frame.py` (E, A_E, SOCKET_D, HEEL_SOCKET_DEPTH, SHROUD_CLEARANCE, FASTENERS, RESIN)

![sections](../out/parts/heel/heel_sections.png)
![views](../out/parts/heel/heel_views.png)

## What it is

The heel is a block under the rear of the pod that holds the top end of the NiTi wire. It is printed as
part of the tub: the integrator does `tub + heel_add() - heel_cut()`. It replaces `blade.heel()`, so don't
union both.

- **Keel.** It hangs under the frame adapter, between the temple's inner face and the pod
  (y 0.3..4.3), and fuses into the tub's inner-lower corner. Its front face is raked at the wire's
  angle (28.6° from vertical).
- **Pivot boss.** This is a cylinder along x (r 2.8, like the old coil-spring `pivot_boss`), forming
  the heel's rounded underside. Its front disc pokes out under the keel. **Nothing pivots:** the NiTi
  does all the bending. The boss and the strut (the pad agent's rigid rectangular arm) give the
  coil-spring look.
- **Socket.** A blind Ø0.85 × 4.0 mm hole runs up from the mouth E at the wire's angle. The wire is
  straight; the hole's angle sets its direction (no heat-setting).
- **Flare and land.**
  - Below E the hole opens into a trumpet (radius 8 mm, tangent to the bore).
  - A 0.4 mm convex round takes it onto the **land**, a flat face square to the wire 1.15 mm below E.
  - The strut's top end sits 1.5 mm under the land in all four states (free, jaw open, worn, jaw
    closed). A short spur behind it finishes the keel.
- **Set screw.**
  - One M1.4 × 3 set screw, square to the socket on its FRONT side.
  - It threads through a brass nut captured in a hex pocket. The nut slides in through a slot on the
    heel's inboard (head-side) face.
  - It presses on a flat filed on the wire. The flat faces the bend's neutral axis (the wire bends
    outward), so it costs no bending strength.
- **Conductor channel.** A Ø1.2 channel carries the 4 pad wires (transducer ×2, LED ×2).
  - It starts on the land 2.25 mm behind the NiTi and goes 2.4 mm straight up.
  - It turns rearward inside the heel, then turns again and runs straight outboard through the tub's
    inner wall.
  - It comes out in the rear gap behind the PCM at x 65.75, z -5.6.

## Parts

| # | Part | Made / bought | Qty | How it is fixed | How it comes off |
|---|---|---|---|---|---|
| 1 | Heel (keel + pivot boss) | Resin, **part of the tub print** | 1 | Integral with the tub | n/a |
| 2 | NiTi wire, Ø0.80 straight, superelastic ("straight-annealed", Af ≤ 0 °C) | Bought, cut to length | 1 | 4.0 mm in the socket. The set screw lands on a filed flat; the flat's end shoulder stops it pulling out. **No glue.** | Loosen the screw ½ turn and pull the arm straight out along the wire |
| 3 | Set screw M1.4 × 3, hex socket. ISO 4026 flat point (preferred) or ISO 4029 cup point. 0.7 mm key | Bought | 1 | Threads into part 4 | 0.7 mm hex key |
| 4 | Hex nut M1.4, brass, DIN 934 (the standard metric hex nut): 3.0 mm across flats, 1.2 thick | Bought | 1 | Captured in a hex pocket by the screw through it. Slid in from the inboard slot. | Back the screw out fully, then tip the nut out of the slot |
| 5 | Conductors, 4 × ~0.3 mm OD (PTFE-insulated or litz) | Bought | 4 | Through the channel, a dab of RTV silicone at each end, soldered to the PCB pads OUT_A, OUT_B, LED+, LED- | Desolder, peel the RTV, pull out |
| 6 | RTV silicone (room-temperature-curing; seal and strain relief) | Bought | dabs | Cures in place | Peels off |
| 7 | Optional: Loctite 222 (purple, low strength, hand-removable threadlocker) | Bought | 1 drop | On the screw thread | Breaks loose with the key |

Wire length: the heel takes **4.0 mm** of it. The full cut length is socket 4.0 + span 11.8 + pad socket
3.5 ≈ **19.3 mm** (frame numbers; the pad note governs).

## Tools

- Pin vise.
- Drills: 0.85 mm (socket), 1.5 mm (screw clearance), optionally 1.2 mm (channel exit).
- 0.7 mm hex L-key.
- Diamond needle file: NiTi is hard and eats steel files.
- Calipers.
- Something to cut the NiTi: a cut-off disc, or hard-wire cutters. Normal side cutters get notched.
- 0.3-0.4 mm music wire, or fishing line, as a fish for the channel.
- Tweezers, a toothpick (RTV), a soldering iron, a syringe with IPA.

## Prep (after washing and curing the tub)

1. **Flush** the socket, the channel and the nut slot with IPA from a syringe. Uncured resin hides in
   the 0.70 mm printed socket.
2. **Ream the socket.**
   - Use the 0.85 mm drill in the pin vise, following the printed hole.
   - Go to **4.0 mm full-diameter depth**: put a tape flag 4.25 mm from the tip, so the drill point
     can go 0.26 mm deeper.
   - Back out often to clear chips.
3. **Ream the screw clearance hole.**
   - Do this **before** the nut goes in.
   - Put the 1.5 mm drill in through the front access hole (the round hole in the boss's front disc,
     angled up and back). Go through the nut pocket until it breaks into the socket. The printed hole
     is Ø1.3.
4. **Prove the channel is open.**
   - Push the fish wire in from the land opening (under the heel, just behind the socket mouth) until
     it shows in the rear gap.
   - The channel has two bends (radius 0.8). Leave the fish in place.
5. **Test-fit the nut.**
   - Slide it into the inboard slot until its corner seats in the V at the far end.
   - If tight, file the slot walls lightly (pocket 3.1 across flats, nut 3.0).
   - Take it out again.

## Assembly (bench, pod off the glasses)

1. **Cut the NiTi.** Square the ends and break the edges with the diamond file.
2. **File the flat** at the heel end.
   - Make it **0.15 mm deep**: calipers read 0.80 → 0.65 across it.
   - It runs from the end down to **2.6 mm** from the end. The step at 2.6 mm is the pull-out stop.
   - Keep the flat inside those 2.6 mm. Any nick further down sits in the bending zone and starts a
     crack.
3. **Conductors through the channel.**
   - Tape the 4 conductor ends to the fish and pull them from the land opening up into the rear gap.
     Leave about 30 mm in the gap.
   - Where they leave the strut top, they cross the 1.5 mm gap to the heel. Route them round the
     **inboard (head) side** of the NiTi. The wire only ever moves outboard, so it never pinches
     them there.
   - Leave a slack loop of about 1 mm in the gap.
   - Optional: a 4 mm piece of black Ø1.0 mm ID silicone tube over the bundle in the gap, to hide it.
4. **Nut and screw.**
   - Slide the nut into the inboard slot.
   - Start the set screw in through the front access hole, 1-2 turns into the nut. It is now
     captured. Stop **before** it enters the socket.
5. **Wire in.**
   - Push the arm's heel end up through the flared mouth into the socket until it bottoms (4.0 mm).
   - The flat must face **forward-down**, toward the access hole. That's the side you see when you
     look up the access hole.
   - The pad end decides the wire's rotation, so do this **before** the pad end is glued or locked.
6. **Lock.**
   - Turn the screw in. Rock the arm slightly while you snug it: when the screw finds the flat it
     advances about ¼ turn more and the wire stops turning.
   - Snug it, then ⅛ turn more. Don't lean on a 0.7 key.
   - Optional: one drop of Loctite 222 on the thread first.
7. **Seal.**
   - Put a small dab of RTV at the land opening, around the conductors, with a toothpick.
   - **Keep RTV out of the flared mouth** (1.4 mm away). Silicone there would stiffen the root.
   - Put a dab in the rear gap where the conductors exit, as strain relief.
8. Route the conductors up the rear gap and forward to the PCB's rear-edge pads (the shell note covers
   this). Solder OUT_A, OUT_B, LED+ and LED-.
9. **Check.**
   - Press the pad: the arm springs back.
   - Look from the side: the strut's top end must not touch the land in any position, with about
     1.5 mm gap worn.
   - Pull gently on the pad along the wire: nothing moves.

## Disassembly

1. Pod off the adapter and lid off (shell note). Desolder the 4 conductors at the PCB, or cut them and
   splice later.
2. Peel the RTV in the rear gap and at the land opening.
3. Loosen the set screw **½ turn only**. If you back it fully out, the nut can drop out of its slot,
   so catch it.
4. Pull the arm straight out along the wire: down and back, 29° from vertical. The conductors slide
   out of the channel behind it.
5. To get the nut out, back the screw fully out and tip the nut out of the inboard slot.

**Set-screw access:** from the **front of the pivot boss**, going up and back at 28.6° above horizontal.
The key goes 1.9 mm into the hole before it reaches the screw.
- The key path is clear of the adapter by 4.0 mm and of the temple by 5.3 mm. You can reach it with the
  pod **on or off the adapter**, glasses off the head.
- The nut slot faces the head. It is clear of the adapter, so the nut can be fitted either way.

## Numbers (from `checks.json`)

| Check | Result | Rule |
|---|---|---|
| Socket wall, minimum (at the crown over the blind end) | **0.80** | ≥ 0.6 (0.8 preferred) ✓ |
| Nut pocket ↔ socket / front face / other walls | 0.80 / 0.80 / ≥ 0.68 | ≥ 0.6 ✓ |
| Set screw in the brass nut | 1.2 mm = **4 full threads** (M1.4 coarse pitch 0.3) | ≥ 3 ✓ |
| Wire ↔ flare, all 4 states, s 0..3 | ≥ 0.009 (jaw closed, s ≈ 0.7) | ≥ 0, no edge ✓ |
| Strut top ↔ heel (generic boxes, pad.py section, **pad.py's actual strut**) | **1.50** (pad.py actual: 1.52) | ≥ 1.4 ✓ |
| Channel wall, minimum / to the flare lip | 0.67 / 0.79 | ≥ 0.6 ✓ |
| Channel ↔ PCM / cell / PCB | 0.36 / 2.67 / 14.6 | ≥ 0.2 ✓ |
| Heel ↔ adapter: as placed, swept while sliding on | 0.40 / 0.40 | ≥ 0.4 ✓ |
| Heel ↔ temple arm | 1.28 | ✓ |
| Heel into the tub's cavity | 0 mm³ | ✓ |
| Heel top under the adapter plate (y 2.7..4.3) | -4.30 | ≤ -4.3 ✓ |
| Heel top inboard of y 2.1 (crown, under the clip lip at -3.3) | **-3.78** | ≤ -4.3 ✗, see H1 |
| Strut top ↔ the **shell's** inner-lower edge (not heel geometry) | **1.08-1.55** by strut model; pad.py actual **1.24** | ≥ 1.4 ✗, see H3 |
| Heel mass | 0.29 g (250 mm³, resin 1.15 g/cm³ [Low]) | |

**Tolerances:**
- Socket reamed to wire + 0.05. If the bench picks the 0.75 or 0.85 wire (T5), ream 0.80 or 0.90;
  nothing else changes.
- Nut pocket 3.1 across flats for a 3.0 nut (snug). Access hole Ø1.6. Screw clearance Ø1.5.
  Channel Ø1.2: the 4-wire bundle is about 0.72 mm, a 25 % fill.
- Print undersize, then ream: socket printed Ø0.70, screw clearance printed Ø1.3
  (`heel_cut(undersize=True)`).

## Decisions for you (options, my pick first)

**H1: the crown over the socket's blind end.** With E and A_E as given, a 4.0 mm socket ends at
z -4.59. A flat heel top at -4.3 would leave only 0.29 mm of wall.
- **A (built):** a local crown to z -3.78, only inboard of y 2.1. That's under the temple-clip lip,
  whose underside is -3.3, so it sits 0.48 below the lip and 0.4 from the adapter plate's chamfer.
  Wall 0.80. It changes nothing else.
- B: set frame `HEEL_SOCKET_DEPTH` to 3.4 and keep a flat -4.3 top. Retention doesn't care: the
  screw and flat do the work. Wall 0.8 and the wire 0.6 mm shorter.
- C: move E down 0.5 mm. That moves the pad, so no.

**H2: the flare is short.**
- The land can only sit 1.15 mm below E, because the strut starts at s = 3 and needs 1.4 mm
  clearance. So the R8 trumpet only wraps **5.7°** before the lip.
- The model's jaw-closed wire leaves E at about that slope, so it is fine for the four design states.
- It gives almost no protection if the pad is yanked or bent past jaw-closed. The wire would then bend
  over the 0.4 mm lip (local strain well over the ~6 % NiTi recovers from) and could take a set at
  the root.
- **A (my pick for rev 1):** build it, run the bench's 100 on/off cycles (spec T5) and look at the
  root under a loupe.
- B: frame `STRUT_START` from 3 to 4 mm. The land drops to about 2.1 mm and the flare wraps about 13°.
  Costs: a 1 mm shorter strut and a 2.5 mm visible gap under the boss.
- C: accept the risk and keep spare wire.

**H3: the strut's top corner is 1.24 mm from the shell's inner-lower edge.** That edge is the shell's,
not the heel's. The heel itself clears by 1.52.
- The closest point is at x 63.3, near (y 4.2, z -10.2) on the strut and (y 5.1, z -9.3) on the shell,
  in the free and worn states.
- The shell's 1 mm outer chamfer already leaves only 0.42 mm wall at the cavity corner there, so it
  can't be relieved from outside.
- **A (my pick):** the pad agent adds a 0.7 mm chamfer to the strut's outboard top edge, or trims
  `STRUT_B1_HI_TOP` 1.9 → 1.7. Either gives about 1.4.
- B: the shell adds a 0.45 mm 45° fill in the cavity's inner-lower corner at x 62..66, which clears the
  PCM by about 0.2. Then relieve the outside edge.
- C: accept 1.24. It is a margin, not a contact.

## Open risks (blunt)

- **The heel only fits under this adapter.**
  - Heel top -4.3 against the adapter's -3.9 underside, and crown -3.78 against the clip lip's -3.3.
  - Both come from `TEMPLE_H` = 5.0. Every extra 1 mm of real temple height lowers the adapter by
    0.5 mm.
  - At TEMPLE_H 5.6 there is about 0.1 mm left; above about 5.8 it collides. **E9 (measure the temple)
    decides.** The heel's top then has to follow the adapter down.
- **Two bugs in `blade.adapter()`** (not the heel's, but they bite it):
  1. The adapter only grips the rail's **upper** wing.
     - There is no adapter material outboard of the lower wing anywhere below z ≈ +1.1 at
       y 3.15..4.3.
     - The pad's 1 N pushes the pod's bottom outward, which is exactly the free side.
     - **Fix it by moving the rail up** (centre it near z 0, inside the adapter's -3.9..3.9).
       **Don't** extend the adapter down: at z -5.4 it would hit this heel.
  2. **The latch and the end stop disagree.**
     - The ramp only works if the adapter slides on from the front, rearward relative to the pod.
       But the channel is closed at the rear, so the rail can't enter that way.
     - Slid on the way the channel allows (pod moving rearward), the bump stops 0.1 mm in front of
       the tooth. The end stop and the tooth then both block rearward pod motion, and nothing stops
       the pod sliding forward off.
     - The heel is clear of the adapter in **either** sliding direction (checked swept, 0.4 mm), so
       fixing this doesn't touch the heel.
- **Conductors cross the 1.5 mm gap in a loop of about 4 mm.**
  - pad.py's strut puts the conductor exit on the strut's front side (lateral -1.8). The heel's
    channel starts behind the wire (+2.25).
  - I could not start the channel in front: the set-screw nut sits there, 1.6 mm above the land, and
    a Ø1.2 channel with walls needs 2.4.
  - Moving the screw up 0.9 mm and running a third bend round the outboard side of the socket would
    fit, but the pivot boss's underside leaves only 0.25 mm there unless the boss grows to r 3.0.
  - Asked the pad agent instead: put the strut's conductor exit at its rear-inboard top corner.
- **The model's root slope (a model artefact).** `frame.wire` leaves E already 2.5-3° off the socket
  axis in the worn and jaw states. A real socket forces zero slope. That makes the 0.009 mm flare
  clearance pessimistic, not optimistic.
- **Resin:** the 0.70 mm printed socket may clog; ream it. Resin creeps under a set screw only if the
  screw bears on resin, and here it bears on brass. The cup point barely bites hard NiTi: the flat's
  shoulder is the real stop.
- **The pad end must be locked after the heel end** (step 5). Otherwise the flat can't be turned to
  face the screw.
- The look: from the side the boss reads as a block, because a cylinder seen end-on along x is a
  rectangle. The barrel shows from the front and from below (`heel_views.png`). The visible gap
  between the boss and the strut top is the "hinge" line.

## For the other modules

- **Integrator:**
  - `tub = tub + heel_add() - heel_cut()`. The print STL uses `heel_cut(undersize=True)`.
  - `heel_add()` is already clipped out of `frame.CAV`.
  - Don't also union `blade.heel()`.
  - The rail's lower wing (x 55..62, z -5.2..-4.3) is buried in the heel. Fine while the adapter
    doesn't grip that wing.
- **pad.py:**
  - The land is at local h 1.153 below E, square to A_E. B_LAND 3.1 is the rear edge (lateral, toward
    the rear).
  - The channel entry on the land is at world (63.79, 2.68, -8.18).
  - `heel.py` re-derives the land from pad.py's live `STRUT_B2` / `STRUT_B1_*` numbers, and checks
    pad.py's lofted strut in all four states.
- **shell.py:**
  - Keep the rear gap clear at the channel exit: inner wall y 5.1, x 65.15..66.35, z -6.2..-5.0.
  - The shell's lower lid boss (y 9.9..13.4) is clear of it. Its note already routes the wires
    "under the lower boss (y 5.1..9.9)", which matches.
