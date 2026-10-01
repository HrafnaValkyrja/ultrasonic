# Bought parts and materials: rev 1 pod (= the prototype)

**Date:** 2026-09-30. **Full evidence, options and sources:** `docs/build/hardware.md`, where every price and data-sheet number carries its 2026-09-30 access date.
**Picture:** `docs/build/hardware-map.png` shows where each bought part goes.
**Numbers:** `docs/build/hardware_checks.py` writes `hw/mech/out/parts/hardware/checks.json`. Run it inside the memory fence; it takes about 1 s.

This module has no CAD. It covers what to buy, how to prepare it on the bench before it meets a printed part, and how to get it back out. Each module note (shell, heel, pad, electronics) owns the step where its part goes in.

## 1. Order list (2 pods, with spares)

| What | Spec | Per pod | Buy | Where (price 2026-09-30) |
|---|---|---|---|---|
| NiTi wire | Ø0.75 superelastic, straight, Af 0–10 °C | 1 arm, cut 20 mm | 5 ft | Kellogg's W-NITI-0.75-SE, $13.49 |
| NiTi wire | Ø0.80 superelastic "Standard" | (T5 alternative) | 3 ft, straight lengths | Nexmetal, $1.74/ft |
| Lid screws | M1.4 × **3** pan/cheese head, A2 | 2 | 12+ | eyeglass micro-screw kit (~$14) |
| Pad closure screw | M1.2 × 4 pan | 1 | 10+ | same kit |
| Nuts | M1.4 hex, DIN 934, **brass** | 4 (lid 2, heel 1, pad 1) | 20+ | eBay packs (~$2.65), unverified |
| Set screws | M1.4 × 3 (heel), M1.4 × 2 (pad), cone-point slotted | 1 + 1 | 6 + 6 | Polar Bear Camera, £6.99/pack |
| Arm conductors | 7/44 served litz, OD 0.21 | 4 × ~80 mm | 10 m | Elecify, $0.71 |
| Charge-nut leads | 30 AWG silicone, red + black | 2 × 35 mm | 2 m each | Adafruit 2051, $0.75 each |
| Driver kit | PH000/00/0, slot 1.0/1.5, hex 0.7 | – | 1 | iFixit Mako 64, $39.95 |
| Resin | Siraya Tech Blu | – | 1 kg | siraya.tech, $32.65 |
| Dock pogo pins | Mill-Max 0906-1-15-20-75-14-11-0 | – | 8 | Digi-Key, $0.73 each |
| Consumables | clear 30-min epoxy + UVO white; neutral RTV; Sil-Poxy; CA; VHB 4914 (0.25); PORON 4701-30 (0.79); 1 mm silicone sheet 30–40A; ~1.5 mm PE foam; Kapton; IPA | – | 1 each | see `docs/build/hardware.md` §8 |

Verified core spend: **$99.36**, before shipping, tax and the unverified items.

## 2. Prepare the bought parts (bench, before assembly)

1. **Measure first.** Calipers on the NiTi (every piece), the nuts (s 3.0, m 1.2) and every drill. Ream sockets to **measured wire + 0.05**.
2. **Cut the NiTi**, 20 mm per arm.
   - Use a hard-wire cutter, or an abrasive disc used wet. Stone the ends square.
   - Roll each piece on glass to find its residual bow, and mark the bow's plane with a paint dot.
3. **File the flats on the NiTi.** Place them so the paint dot (the bow) ends up perpendicular to the bend plane.
   - About 0.1 mm deep, with a diamond needle file: 4.0 mm long at the heel end, 3.5 mm at the pad end. Draw a pen line along the flat's direction.
   - **Keep both flats inside the socket lengths.** A flat on the 11.8 mm span is where the wire would crack.
4. **Litz:** cut 4 × ~80 mm per pod.
   - Strip the yarn, burn off the enamel at 380–400 °C and tin the ends.
   - Find each conductor with a continuity tester and mark it with a paint dot at both ends (OUT_A, OUT_B, LED+, LED−).
5. **Charge nuts:**
   - Tin 2 mm of a red and a black 30 AWG lead.
   - Solder each to a flat of a brass nut, **on the bench**, never in the pocket. Use rosin flux; brass takes it, stainless doesn't.
   - **Red = VBUS = the top nut.**
6. **Punch the soft parts:**
   - Mic washer Ø3.0 / Ø1.0 from 0.79 mm PORON.
   - Contact disc Ø8 from 1 mm silicone.
   - Foam strips 1.1 × 17.5 from ~1.5 mm PE foam.
7. **Printed parts:** wash, dry and fully post-cure **before** any drilling. Under-cured resin smears and stops epoxy and platinum silicone curing.

## 3. How each bought part is fixed, and how it comes out

| Part | Fixed by | Removed by |
|---|---|---|
| Lid screws (charge contacts) | thread into the captured brass nuts; snug only | eyeglass driver |
| Brass nuts | captured in side-entry or slotted pockets; the screw through them holds them | back the screw out, then tip or slide the nut out with tweezers |
| Set screws | through their nut, onto the filed flat | ½ turn with the 0.7 key or 1.0 slot is enough to pull the wire |
| M1.2 pad screw | forms its own thread in a **Ø1.0** pilot (not 0.95) | driver; good for ~10 cycles (pad note) |
| NiTi | set screw on a flat; the flat's shoulder stops pull-out; **no glue** | loosen, pull along the wire axis |
| Litz | solder at both ends, RTV dabs at channel exits | desolder; peel the RTV |
| Cell | VHB 4914 | **dental floss sawn through the tape, or IPA soak.** Never pry a LiPo |
| Mic washer, foam strips | own adhesive | peel; the washer is a consumable |
| Contact disc | Sil-Poxy or thin RTV | peel |
| LED diffuser | cast epoxy (PE film underneath for release) | permanent in the cap; reprint the cap |

## 4. Tools

- Pin vise with HSS 0.3–1.6 mm in 0.1 steps, plus a single 0.85. Sizes used: 0.85, 1.0, 1.2, 1.4, 1.5, 1.6.
- Diamond needle files, hard-wire cutter or abrasive disc, calipers (0.01 mm).
- Punches Ø1.0 / Ø3.0 / Ø8.0, 1 ml syringe with a blunt 25G needle, music-wire fish (0.3–0.4 mm).
- Fine-tip iron at 380–400 °C, rosin flux, insulated tweezers, loupe, ESD strap.
- Kitchen scale (0.1 g) for the T5 force check.

## 5. Tolerances that come from the bought parts

- NiTi socket: **measured wire + 0.05**, drilled after cure.
- Nut pocket: 3.1 across flats for the 3.0 nut. 1.2 mm nut = 4 full M1.4 threads.
- M1.2 into resin: **Ø1.0 pilot ≈ 74 % thread engagement**; 0.95 is ≈ 92 % (tapping-drill size, risks splitting).
- Lid screw ≤ 3.6 mm long, so **buy 3 mm**.
- 4 litz wires bundle to Ø0.51: 0.49 mm spare in the pad's Ø1.0 channel, 0.69 in the heel's Ø1.2.
- VHB 4914 is 0.25 mm in the 0.3 mm `frame.TAPE` allowance.

## 6. Open risks (blunt)

1. **NiTi force is a guess until T5.**
   - Neither hobby seller publishes plateaus. Fort Wayne Metals' minimums at 32 °C give unloading 184–253 MPa, so the model's 200 is a floor.
   - Loading is 517–598 MPa against the model's 450, so the put-on force will run ~15–33 % higher than modelled.
2. **Af ≤ 0 °C and Ø0.85 are not stock items.** Buy 0.75 + 0.80; 0.838 mm is by quote.
3. **Brass M1.4 nuts and M1.4 set screws are the supply risks.** The nuts are marketplace-only. Cheap set screws are cone-point slotted, not the hex cup point the frame drew.
4. **Loctite 222** is not recommended on plastics (Henkel TDS, May 2022). Skip it in rev 1.
5. **A2 lid screws are non-magnetic.** The dock needs a cradle, a clip or a hidden steel disc. The spec still says magnetic pogo charging.
6. **Resin heat:** Siraya Blu's HDT is 70 °C. A car dashboard in summer can exceed that.
