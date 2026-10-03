# mini/pcb-tech: PCB fab + assembly technology for a smaller pod board at JLCPCB (Phase-2 PRELIMINARY)
```yaml
id: MINI-PCBTECH
status: preliminary research; no board/schematic/placement/routing edits; nothing committed
date: 2026-10-03 (UTC; JLC pages fetched 2026-10-03T00:39-00:47Z; JLC parts API 2026-10-03T00:42Z/00:47Z)
lane: pcbtech (workflow "miniaturization preliminary research")
guardrails: memory/two-phase-redesign.md (Phase 2 only after owner board review); O8 O13 O16 O19 O20 O21 O22 respected; reversals listed as options only
abbrev:
  POFV: plated-over filled via = via-in-pad, hole filled with epoxy or Cu paste, plated flat (JLC "Epoxy/Copper paste Filled & Capped")
  HDI: high-density interconnect = laser blind microvias (+ buried vias), sequential lamination; "N-step" = N lamination+laser cycles
  WLCSP: wafer-level chip-scale package (bare die with solder bumps)
  EP: exposed (thermal/GND) pad under a QFN
  crtyd: KiCad courtyard area (part body + assembly keep-out), mm2
  Std/Eco: JLC Standard / Economic PCBA tier
  conf tags: [V]=verified primary src (url+date) · [E]=estimate/derived · [TBD]=not found, ask at quote/measure
src:
  S1: https://jlcpcb.com/capabilities/pcb-capabilities (rigid; undated page; read 2026-10-03T00:39Z)
  S2: https://jlcpcb.com/capabilities/pcb-assembly-capabilities (read 2026-10-03T00:39Z)
  S3: https://jlcpcb.com/capabilities/flex-pcb-capabilities (read 2026-10-03T00:39Z)
  S4: https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq ("Last updated Sep 07, 2026"; read 2026-10-03T00:39Z)
  S5: https://jlcpcb.com/help/article/BGA-Design-Guidelines---PCB-Layout-Recommendations-for-BGA-packages (Sep 09, 2026)
  S6: https://jlcpcb.com/help/article/pcb-via-covering (Sep 09, 2026)
  S7: https://jlcpcb.com/help/article/minimum-spacing-for-smd-components (Sep 09, 2026)
  S8: https://jlcpcb.com/help/article/pcb-design-instructions-for-edge-plating (Sep 09, 2026)
  S9: https://jlcpcb.com/help/article/what-is-castellated-holes (Sep 09, 2026)
  S10: https://cart.jlcpcb.com/quote (quote form: server-rendered tooltips + its JS bundle /shop-cart-static/js/f5edecafb14c0371fb3d.js; read 2026-10-03T00:41Z)
  S11: https://jlcpcb.com/help/article/in-what-cases-will-there-be-charged-extra (Sep 09, 2026)
  S12: https://jlcpcb.com/help/article/pcb-assembly-price (Sep 09, 2026)
  S13: https://jlcpcb.com/6-layer-pcb (undated; read 2026-10-03T00:44Z)
  S14: https://jlcpcb.com/ (home page product tiles; read 2026-10-03T00:44Z)
  S15: ST DS13737 Rev 10 (Jul 2024) STM32U575xx datasheet, local "From Valkyrie/Datasheets/DS_stm32u575ag.pdf": §6.4 Table 157/158 p318-319, Fig 13 p94, Table 26
  S16: JLC parts API via tools/jlc.py (2026-10-03T00:42Z, 00:47Z)
  S17: KiCad 10 stock footprints /usr/share/kicad/footprints (crtyd computed 2026-10-03)
  repo: docs/research/simplify/size.md (SIZ-*), simplify/assembly.md (ASM-*), simplification-study.md (Package B 28x12), docs/system/reg-board.md, hw/pod/place.py rules() L112-122, hw/pod/bom_jlc.csv
```

## 0. Bottom line (blunt)
```yaml
B1: "JLC cannot make our assembled 4-layer board thinner than 0.8 mm. 0.6 mm is 2-layer only; 0.4 mm is ENIG-only and cannot be panelised, and a 28x12 board needs a panel for Std PCBA (min single board 70x70). [V S10 tooltip, S2]. size.md's 0.6 rejection stands, reason corrected: 0.6 IS a listed FR-4 thickness (S1) but the quote form excludes it for 4- and 6-layer."
B2: "Every other PCB technology here buys AREA, not thickness. size.md §4.2: pod height is set by the 12 mm cell and pod length by the 35 mm cell; a board under ~28x12 does not shrink the pod. So HDI/POFV/WLCSP/0201/6-layer only pay if they (a) de-risk routing the 28x12 outline (Package B), (b) cut noise coupling, or (c) let nearly all parts sit on ONE face so the other face's height band shrinks (the only board-tech path to a thinner pod, MINI-PT-12: -0.15..-0.35 mm)."
B3: "Recommended Phase-2 tech set (option A): 4-layer 0.8 mm + paid POFV (epoxy filled & capped) at U1's EP, U3's inner balls and dense 0402 pads; keep QFN48. Cheapest step that removes today's ball-escape failures (2 of 7 unrouted at U3) without HDI. Option B: 6-layer 0.8 mm (POFV free, both faces get an adjacent GND plane) if the live quote confirms 6L at 0.8 mm (S13 table says yes, its FAQ says 1.0-2.0: conflict). Option C (HDI + WLCSP90 MCU): -31 mm2 crtyd, but manual-priced/whitelisted HDI, fragile joints, unreworkable: not for a rev-1-is-final personal device (O19/O20)."
B4: "Rigid-flex: JLC does not make it [V S3 FAQ]. A separate 2-layer FPC is possible; only a static dock tail is a sane use (ASM-12). An arm flex tail is a joint-fatigue risk (R24); keep litz."
B5: "Our current via rule (0.35/0.15) already triggers JLC's small-via surcharge (hole <0.3 AND dia <=0.4) [V S10]. Free alternatives: 0.3/0.4 or, on multilayer, 0.2/0.45 [V S10]. Use small vias only where density needs them."
```

## 1. JLC capability facts used (all [V], src + read date in header)
```yaml
rigid_FR4 (S1):
  layers: 1-32; thickness list FR-4: 0.4/0.6/0.8/1.0/1.2/1.6/2.0; tol ±0.1 mm below 1.0 (0.8 -> 0.7-0.9), ±10% from 1.0
  thickness_by_layers (S10 tooltip): "0.40 mm: ENIG only; cannot be made with a panel; not 1-layer" · "0.60 mm: max 100x100; not available for 1-layer, 4-layer or 6-layer" · "0.8-1.0 mm: max 300x300"
  thickness_JS_rule (S10 JS): 0.4 disabled when Panel=Yes or castellated holes=yes
  min_dims: 3x3 mm (>=0.6 mm thick; thinner = manual review); castellated/plated-edge boards >=10x10
  track/space 1oz: 1-2L 0.10/0.10; multilayer 0.09/0.09 (3.5 mil); "3 mil acceptable in BGA fan-outs"
  fine_line_fee (S11): 3.0-3.5 mil on 4-8 layers = +20% of order amount; 10L+ = +30%
  via_min: 0.15 hole / 0.25 dia; 0.1/0.2 only for board <=1.0 mm with ENIG/OSP (our 0.8 qualifies); dia >= hole+0.1 (0.15 preferred); preferred min hole 0.2
  via_fee (S10 text): extra charge when hole <0.3 AND dia <=0.4; free at hole>=0.3 & dia>=0.4; multilayer: 0.2 hole free at dia>=0.45. Quote options: 0.3/(0.4/0.45), 0.25/(0.35/0.4), 0.2/(0.3/0.35), 0.15/(0.25/0.3), 0.1/(0.2/0.25)
  annular: PTH multilayer 1oz recommended 0.20, min 0.15; via ring = (dia-hole)/2 >= 0.05
  via_hole_to_hole: 0.2; inner-layer via-hole-to-copper 0.2; via-hole-to-track 0.2; pad-to-track 0.1 (0.09 at BGA); SMD pad-pad 0.15; min SMD pad 0.25x0.25
  BGA (S1): pad >=0.2 (0.2-0.25 needs ENIG); pad-to-trace >=0.1 (0.09 multilayer); "vias can be placed within BGA pads using filled and plated-over vias"
  soldermask: 1:1 expansion OK (LDI since Jun 2025); bridge 0.10 (green), 0.13 (black/white)
  edge: copper >=0.2 from routed edge; V-cut 0.4 (±0.4, extra fee if a board side <15 mm, S11); mouse-bite: spacing 1.6/2 mm, serrated edges remain, Std PCBA rails 5 mm + 2 mm tooling + 1 mm fiducials @3.85
  outline_tol: ±0.2 regular, ±0.1 precision (precision needs >=50x50 + 3 tooling holes)
POFV (S1, S6, S5, S13, S14):
  types: epoxy filled & capped; Cu-paste filled & capped (8 W/mK)
  via_range: 0.15-0.55 mm (S1: "via diameters 0.15 to 0.55"; S6: holes <=0.5)
  6L+: default and free ("Free POFV for 6+ layers" S14; "upgraded via-in-pad on 6-20 layer PCBs to POFV ... free" S5)
  4L: available as a paid option; price only in live quote [TBD]
  quality (S6): cap Cu >=5 um; pad dimple/protrusion within 50 um (text "127um depression and protrusion within 50um")
  ink-plugged vias: not allowed in pads or <0.35 mm from a pad opening (S6) -> via-in-pad MUST be POFV
  BGA guide (S5): ink-plugged 4L table: via 0.15/0.25, BGA pad 0.25, trace-trace 0.09, via-copper-to-pad 0.1; filled VIP example: 0.25 pads with 0.15/0.25 via in pad at 0.5 pitch, 0.09 tracks between vias on inner layers (non-functional inner pads removed); recommend VIP drill >=0.15, land >=0.35 where possible
HDI (S1, S4, S10):
  steps: 1/2/3-step offered (S1); quote JS: layers<=4 -> [1-step only]; <=6 -> [1,2]; >=8 -> [1,2,3] (S10 JS, plateType 8 = HDI)
  laser blind via: 0.075-0.15 (default 0.1), Cu-filled + planarised; aspect (dielectric:dia) <=1:1 (0.1 PP -> >=0.1 via)
  buried via: mechanical 0.15-0.55 (0.10 extreme if dielectric <=1.0), resin plugged + capped
  annular blind/buried >=0.075 -> land >= hole+0.15; hole-edge spacing different nets >=0.24
  track/space: 3/3 mil (2.7/2.7 extreme, "increase difficulty and cost"); design 3.5/3.5 when room
  min board 5x5; V-cut panel min 30x60; material NP-175F / S1000-2M (Tg170); PTH tol ±0.076
  pricing (S10 JS): separate "HDI level fee", "buried via fee", "lamination fee", shown as "price pending" -> manual engineering review [V that it is review-priced; amount TBD]
  access (S10 JS): code contains hdi_white_list + message key "i18n_cart_hdi_not_in_whitelist" -> HDI ordering may be gated per account [V code exists; actual policy TBD]
  surface finish HDI: <=4L OSP/ENIG/HASL; >4L OSP/ENIG (S10 JS); FR-4 >=6L or <=0.4 mm: no HASL (S1)
  "Limitations: complex, repair difficult, price higher, lead time longer" (S4)
six_layer (S13): thickness table 0.8/1.0/1.2/1.6/2.0; FAQ text "ranges from 1.0 up to 2.0" -> CONFLICT [TBD live quote]; VIP free; min via 0.15/0.25; "as fast as 48 h"; 4-wire tested
flex_FPC (S3, S14, S12):
  layers 1-4; 2L 0.11/0.12/0.2 mm (25 um PI); 4L 0.2-0.45 mm; ENIG 1u"/2u" only
  vias regular 0.3/0.55; extreme 2L 0.10/0.3, 4L 0.15/0.35 (extra cost)
  traces 12 um Cu 3/3 mil; 18 um 3.5/3.5; 35 um 4/4; BGA pad >=0.25, BGA pad-to-trace >=0.2
  castellated FPC holes >=0.3, >=0.5 to edge, >=0.4 hole-hole
  bend: static 6-10x t; dynamic >=10-15x t, 1-2 layers adhesive-less PI, no vias/pads in bend; 4L = static only
  stiffeners: PI 0.1-0.25; FR4 0.1-1.6; stainless 0.1-0.3 (slightly magnetic); tesa8854 / 3M tapes
  rigid-flex: "JLCPCB currently does not support Rigid-Flex PCBs" (S3 FAQ)
  lead: 5-6 days; "From $2.00 / 5 pcs" (S14 promo floor)
  FPC assembly fixture: $24.63/fixture, 1-29 pcs = 2 -> $49.25 (S12)
castellation_edgeplating (S1, S9, S8, S2):
  castellated: hole >=0.5 (S1) vs ">=0.6 hole size and space" (S9) -> CONFLICT, design 0.6; hole-to-edge(corner) >=1.0; hole-hole >=0.5; board >=10x10, >=0.6 thick; special-process extra charge if "Yes" (amount TBD); "No" = ordinary process, quality not promised
  plated edges: ENIG only; board >=10x10, >=0.6 thick; >=3 unplated breaks for support tabs (>=3 mm each, S8)
  PCBA: castellations / edge plating / gold fingers only in Std PCBA (S2)
assembly (S2, S7, S12):
  Std: single+double sided; 0201 min package; 0.35 mm min IC pitch; 0.3 mm min BGA pitch; 240±5 C; SPI+AOI; X-ray auto for BGA/QFN/LGA; >=4 days build; panel 70x70..250x250; rails + fiducials required
  Eco: single side only; 0402; 0.4 IC / 0.5 BGA pitch; 0.8-1.6 mm; 2/4/6L standard stack only
  fees Std: setup $25.56 single / $51.12 double; stencil $8.21 / $16.42; feeder $1.53 per BOM line (Basic or Extended); X-ray $1.64/pc (1-10); SMT $0.0016/joint
  SMD spacing (S7, "recommended minimum", mm): 0201-0201 0.15; 0402-0402 0.15; 0402-0603 0.18; chip-QFN 1.0; chip-BGA 1.0; QFN-QFN 1.0; BGA-BGA 2.0; SOT-chip 0.2
  component-to-board-edge (assembled, panelised): no JLC number found [TBD]; rails carry the panel; copper-to-edge 0.2 [V S1]
  bottom-side part weight / which side reflows first: no JLC rule found [TBD]
```

## 2. Measures (MINI-PT-*)
Per measure: what it enables · area · cost per order · lead time · risk · conf. Area numbers are per face unless stated; pod envelope effect of area is 0 below 28x12 (B2).
```yaml
MINI-PT-01:
  what: keep 4-layer 0.8 mm, add paid POFV (epoxy filled & capped) selectively: U1 EP (9 vias), U3 BQ25180 inner balls, via-in-pad at dense 0402/0201 pads and decoupling caps
  enables: GND vias in U1's EP with no solder wicking -> decoupling caps may sit on B directly under U1; inner-ball escape at U3 (reg-board unrouted #6 VSYS B2, #7 VBUS A2) without the WSON package change; shorter cap fan-out stubs
  area: -10..-20 mm2 per face at 28x12 [E: ~8 MCU decaps x ~0.6 mm2 stub+ring each moved under U1, plus fan-out stubs ~0.3 mm per pad]
  cost: 4L POFV fee TBD (live quote only; S10 has no static price) [TBD]
  lead: + process step; FR-4 base 24 h (S14), POFV 4L days TBD [TBD]
  risk: low-med; cap dimple <=50 um ok for 0402/QFN; must list which vias are filled in the order remark (S6)
  conf: [V] capability, [E] area, [TBD] cost
MINI-PT-02:
  what: 6-layer 0.8 mm (e.g. L1 parts/sig, L2 GND, L3 sig, L4 sig/+3V0, L5 GND, L6 parts/sig) instead of 4-layer
  enables: free POFV everywhere (S13/S14); two more routing layers -> 28x12 Package-B outline with margin; B-face parts (mic U2, bridge Q1/Q2, charger U3) get an adjacent solid GND (today B.Cu references In2 = a signal layer: reg-board Elements/"Layers")
  area: routing area -10..-15% -> ~26x12 or the 28x12 freeze with slack (-24..-48 mm2 per face) [E: 4L draft 43% crtyd density (size.md §4.2) -> ~50-55% typical for 6L+VIP]
  thickness: 0 if 6L at 0.8 is real; +0.2 mm pod thickness and +0.2 mm mic duct if 6L starts at 1.0 (S13 conflict) [TBD]
  cost: delta vs 4L on 5 small panels TBD (S13 "5pcs 6-layer from $2" is a promo floor, not our quote) [TBD]
  lead: "as fast as 48 h" (S13) vs 24 h for standard FR-4 (S14)
  risk: low (standard process); evidence O22(4): the layout-noise sim (sim/noise/) should be re-run on the 6L stack
  conf: [V] capability, [E] area, [TBD] cost + 0.8 mm availability
MINI-PT-03:
  what: HDI (laser microvias) — 1-step only on 4L, up to 2-step on 6L (S10 JS)
  enables: 0.4 mm-pitch WLCSP/DSBGA escape (MCU WLCSP90, 0.4 mm PMICs rejected elsewhere for other reasons), 3/3 mil tracks, buried vias that leave L3/L4 planes intact under the MCU
  area: -31 mm2 crtyd (via MINI-PT-04) + general -15..-25% routing area [E]
  cost: manual-priced HDI level + buried-via + lamination fees (S10 JS "price pending"); possible account whitelist [TBD]; HASL excluded >4L
  lead: longer than standard (S4) [TBD days]
  risk: high for this project: review-priced and possibly gated; repair "difficult" (S4); the owner cannot rework a WLCSP; no reorder path if the account is not whitelisted; O19 wants robust packages
  conf: [V] capability/rules, [TBD] price/lead/access
MINI-PT-04:
  what: MCU U1 STM32U575CIU6Q (ST Cortex-M33 MCU with internal SMPS, UFQFPN-48 7x7, 0.5 mm) -> STM32U575OIY6QTR (same die, WLCSP-90 4.20x3.95x0.59 mm, 0.4 mm hex-staggered bump grid, SMPS ballout)
  facts: LCSC C5271033, Extended, 10 in stock, $15.1398 vs C5271013 QFN 8 in stock, $8.9281 [V S16 2026-10-03T00:42Z]; ST land pad 0.225, mask 0.290, stencil 0.250 x 0.100 [V S15 Table 158]; height 0.59 max vs QFN48 0.60 -> no height gain [V S15]
  area: crtyd 68.2 -> 37.0 mm2 = -31 mm2 on F [V S17 KiCad QFN-48-1EP_7x7 vs ST_WLCSP-90_4.2x3.95mm_Layout18x10 (1.0 mm BGA courtyard = JLC chip-BGA 1.0, S7)]; minus ~3-5 mm2 back for 3 extra supply balls that need decaps (VDDUSB C1, VREF+ H16, VDDIO2 A11) [E]
  fanout: see §3; needs via-in-pad on every used inner ball (POFV through vias on 6L, or HDI 1-step)
  cost: +$6.21 per MCU; X-ray unchanged (both hidden-joint); PCB tech per MINI-PT-01/02/03
  risk: high: WLCSP drop/flex joint life on a worn 0.8 mm board unknown (no underfill offered by JLC found [TBD]); bare die; 0 hand rework; stock 10 (same order of risk as the QFN's 8)
  firmware: same GPIO names and AFs; the pin numbers in integration-map §4 change; more spare GPIOs (O18 "spare pins to pads")
  conf: [V] part data, [E] fanout feasibility
MINI-PT-05:
  what: 0402 passives -> 0201 (Std PCBA minimum package 0201 [V S2]); 0201-0201 spacing 0.15 [V S7]
  area: crtyd 1.71 -> 0.98 mm2 each (-0.73) [V S17 KiCad R/C_0402_1005 vs R/C_0201_0603]; 35 x 0402 in bom_jlc.csv -> -25.6 mm2 total both faces; ~27 left after Package B -> -20 mm2 [E]
  cost: fee-neutral (Std feeder fee $1.53/line Basic or Extended, S12); all 0201 checked are Extended with >10k stock: 100n C66938, 10k C106225, 1u C76929, 15p C64554 [V S16 2026-10-03T00:47Z]
  risk: med: 1 uF+ in 0201 loses most capacitance under DC bias (keep bulk caps 0402/0603) [E]; owner hand-rework much harder; tombstoning more likely [E]
  conf: [V] capability/stock, [E] risk
MINI-PT-06:
  what: thinner laminate 0.6 or 0.4 mm
  result: REJECT. 0.6 not offered for 4L/6L [V S10]; 2-layer 0.6 = 2-layer routing (assembly.md §3 rejected 2L). 0.4: ENIG only, no panel, no castellations [V S10] -> a 28x12 board cannot meet Std PCBA's 70x70 single-board minimum [V S2] -> no JLC assembly. HDI/FPC thickness floors are different products (FPC 4L 0.2-0.45, MINI-PT-11)
  saving_if_possible: pod -0.2/-0.4 mm thickness, mic duct -0.2/-0.4 mm [E]
  conf: [V]
MINI-PT-07:
  what: via rule change: default via 0.3/0.4 (or multilayer 0.2/0.45) = no surcharge; 0.15/0.25-0.35 only inside fan-out regions; keep track/space >=0.09 (3.5 mil) to avoid the +20% fine-line fee
  area: +0..+5 mm2 per face where big vias replace small ones [E]
  cost: removes the small-via surcharge (amount TBD) that the current rule (place.py rules(): via 0.35/0.15) already incurs [V rule S10, TBD amount]
  risk: low; note 0.09 mm = 3.54 mil sits on the 3.5-mil boundary of the +20% band: do not drop below [E]
MINI-PT-08:
  what: rear-edge castellated half-holes for the hand-soldered wires instead of the J1-J12 pad block (ASM-09 alternative)
  enables: wire joints on the board edge, reachable from both faces after the lid-hung bond; wires leave straight into the stowage zone (SIZ-14)
  area: J block today 2 columns x 1.6 pitch at x 30.9-33.5 = ~2.6 x 9 mm -> ~-20..-25 mm2 on F (board ~2 mm shorter or freed) [E from reg-board hand pads]
  capacity: 12 mm edge - 2 x 1.0 corner keep-out = 10 mm; pitch >=1.1-1.2 (0.6 hole + 0.5-0.6 web) -> 8-9 holes; Package B needs 9 wires -> zero margin [E]; J3 DOCK_VBUS / J5 VBAT must not be neighbours (reg-board issue 4)
  cost: castellation special-process fee TBD; Std PCBA only (we already are); not with 0.4 mm boards [V S1 S2 S9 S10]
  risk: med: half-hole plating pull-off under wire strain (needs strain relief at the wire, not the joint) [E]; castellated edge cannot carry a mouse-bite tab -> panel tabs on the other edges
  needs_owner: yes (pad style is a hand-build choice; owner builds by hand)
MINI-PT-09:
  what: dock tail as a separate 2-layer FPC (0.11-0.12 mm, 4 traces) from the dock target to the board, through the 0.8 mm under-cell channel (= ASM-12, now with JLC data)
  area: 0 on the board (replaces 4-5 J pads with 4-5 FPC lap pads, same order) [E]; channel fill: 4-5 wires -> one 0.12 x ~2.5 mm strip [E]
  cost: bare FPC, no assembly: "from $2 / 5 pcs" promo floor + separate order line [V S14 floor, TBD real]; FPC lead 5-6 days [V S14]
  risk: low-med: static bend (6-10 x t => r >= 0.7-1.2 mm) OK [V S3 rule]; solder to the target's (bent) tails by hand; ENIG pads
  needs_owner: yes (O16(3) "no custom connector board" — an FPC harness is not a connector board, but it is a custom part; O21 timing)
MINI-PT-10:
  what: arm flex tail (OUT_A/OUT_B, +LED_A/LED_K if O8 stays) replacing litz up the NiTi arm
  result: REJECT for rev 1. Jaw-driven dynamic flex for years; JLC: dynamic needs 1-2L adhesive-less PI, r >= 10-15 x t, no vias/pads in bend [V S3]; copper grade (RA vs ED) not stated [TBD]; arm joint fatigue is project risk R24; litz in the strut is the proven path (O7b, O17 "no pinched wires")
MINI-PT-11:
  what: whole pod board as a 4-layer FPC (0.2-0.45 mm) + local stiffener; or rigid-flex
  result: REJECT. Rigid-flex not offered [V S3]. 4L FPC is static-only, BGA pad-to-trace 0.2, vias 0.15/0.35 extreme (extra cost), FPC assembly fixture $49.25/order [V S3 S12]; double-sided FPC SMT at JLC not documented [TBD]; SW1 needs a rigid back -> stiffener adds back the thickness saved
MINI-PT-12:
  what: "one-heavy-face" layout: every part on B (cell side) except SW1 on F (still double-sided, O13 intact); enabled by PT-01/02 (+PT-05, optionally PT-04)
  thickness: F band 1.0 (SIZ-03, L1 1.00 mm tallest on F) -> ~0.7-0.85 (SW1 0.65 nominal + clearance) = pod -0.15..-0.35 mm [E; heights from tools/checks/part_heights.yaml via size.md]
  density: B would carry ~193 mm2 crtyd today (all placed parts 201 - SW1 7.7, assembly.md §2.1); with Package B cuts + 0201 ~140-170 mm2 = 42-50% of a 28x12 face (336) -> needs 6L/POFV; with WLCSP too ~110-140 (33-42%) [E]
  cost: 0 fee delta (already double-sided Std) [V S12]
  risk: med: all heat sources and the mic on one face (bridge-to-mic spacing gets harder; MP-01 noise); must re-run sim/noise on that layout (O22(4)); L1 2-reflow limit moot if F only has SW1 [E]
  needs_owner: yes (layout strategy for the joint layout session O14; SW1 face fixed by O16(7)/lid plunger)
MINI-PT-13:
  what: edge-plated or bare-PCB-pad dock contacts (drop the YZT0675 magnetic target)
  result: REJECT. JLC finishes are ENIG 1-2 u" gold [V S3 FPC; S11 rigid ENIG 1u"/2u" pricing] = not a mating-wear finish for daily pogo docking for years [E: connector contacts use hard gold, typ >=30 u"]; dock sits in the belly, not in the board plane (assembly.md §6.3); O12(a)/O16(3) chose a pre-built magnetic connector
```

## 3. MCU fanout: current QFN48 vs WLCSP90 under JLC rules
```yaml
QFN48_now (U1 UFQFPN-48 7x7, 0.5 mm, EP 5.6; draft pads 0.25 x 0.875, gap 0.25 — assembly.md §4):
  L1_between_pads: needs 0.09+0.09+0.09=0.27 > 0.25 -> no track between pads (none needed)
  escape: all 48 pins are perimeter -> every signal escapes outward on F, then vias outside the courtyard; EP GND: 9 vias 0.35/0.15 to In1
  tech_needed: standard 4L, through vias, no via-in-pad [V draft]; optional POFV on the 9 EP vias to stop solder wicking and free B under U1 (PT-01)
  reg-board unrouted at U1 (BTN pin 10, PB14 pin 27, PA10 pin 31): placement, not escape (reg-board table)
WLCSP90 (STM32U575OIY6QTR, S15):
  grid: rows A-K (10), cols 1-18 staggered; e=0.40 in-row, row step = e2/9 = 0.347 -> hex grid, nearest neighbour 0.40 mm [V S15 Table 157 e1 3.40, e2 3.12]
  pad: 0.225 (ST) -> 0.25 if a 0.15/0.25 POFV is put in it (JLC BGA min 0.25 on 4L via table S5; 0.2-0.25 needs ENIG S1)
  L1_between_balls: copper gap 0.4-0.25 = 0.15 (or 0.175 at 0.225 pads) < 0.229 (3/3 mil HDI) and < 0.27 (3.5 mil) -> NO track between any two balls, even HDI 2.7 mil (0.206 needed > 0.175) [E arithmetic from V rules]
  consequence: only the outer ring escapes on L1; every used inner ball needs a via in its pad
  used_balls (our nets, Rev F pin set mapped to Table 26 WLCSP90-SMPS column): 48 incl. power repeats; ring depth from edge: ring0 23, ring1 14, ring2 6 (BOOT0 C13, PA15 E5, PA4 H14, PA5 H12, PB15 G5, PB4 C11), ring3 4 (PA0 G11, PA8 F8, PB3 D10, PB5 D12), ring4 1 (PA6 F10) [V ball ids S15; E ring count]
  via_in_pad_options:
    a_through_POFV_0.15/0.25 (4L paid or 6L free): inner layers: keep-out radius 0.075+0.2 = 0.275 around each via -> one 0.09 track fits only between used vias >=0.8 apart (skip one unused ball); adjacent used vias (0.4) block. ~42 unused balls leave channels -> plausibly routable on 6L, tight on 4L [E]; through vias perforate In1 GND under the die (0.55 antipads at 0.4 pitch) [E]
    b_HDI_1step_microvia_0.1/0.25 (L1->L2, L4->L3): L2 lands 0.25 at 0.4 -> again no track between adjacent used lands; cleaner (no full-depth perforation) but manual-priced/whitelist (PT-03)
    c_0.1/0.2_mechanical (S1: <=1.0 mm boards, ENIG): land 0.2 fits inside a 0.225 pad, but POFV range starts at 0.15 hole (S1) -> unfilled via-in-pad wicks solder: NO
  verdict: WLCSP90 needs (a) on 6L or (b); a real fanout study (KiCad, fenced) before any commitment [E]
```

## 4. Options for the owner (2-3, one recommended)
```yaml
A_recommended: 4L 0.8 mm + selective paid POFV (PT-01) + cost-free via rule (PT-07) + optional 0201 for non-bulk passives (PT-05). QFN48 stays. Area relief ~-30..-45 mm2 per face; 0 thickness; lowest risk; fab-standard lead time. Fits Package B 28x12 with margin; keeps O19 robust packages.
B: 6L 0.8 mm (PT-02, POFV free) + PT-05, layout as one-heavy-face (PT-12). Only route to a thinner pod from board tech (-0.15..-0.35 mm) plus better GND reference for B-face parts. Precondition: live quote confirms 6L at 0.8 mm; noise sim re-run on that stack.
C: HDI + WLCSP90 MCU (PT-03/04) on top of B. -31 mm2 more, no thickness gain, manual pricing/whitelist, fragile joints, zero rework. Not recommended for rev 1 = final (O19/O20).
rejected: PT-06 thinner laminate, PT-10 arm flex tail, PT-11 rigid-flex/FPC board, PT-13 PCB dock contacts.
```

## 5. Integration-map cross-check (docs/system/integration-map.md §1-§6)
```yaml
functions:
  F1 mic: board thickness = mic duct length; 0.8 floor holds (PT-06); PT-12 keeps U2 on B (bottom port through board) — unchanged
  F2 MCU: PT-04 changes package only; same nets/AFs; integration-map §4 pin numbers -> ball ids; +3 supply balls (VDDUSB, VREF+, VDDIO2) need +3V0 + decaps
  F3 bridge, F4 self-test: PT-12 puts bridge and mic on one face -> spacing/noise re-check (MP-01, sim/noise)
  F5/F9/F10 dock: PT-08 castellations or PT-09 FPC change only the wire attachment, not nets; J3/J5 adjacency rule (reg-board issue 4) still applies
  F11 SW1: stays on F under the plunger in all options
  F12 LED (O8): unchanged; PT-10 rejected keeps litz for LED_A/LED_K
  F14 test: TP pads unaffected; WLCSP removes probe-able MCU pins (QFN pins can be probed) -> more reliance on TP/MDF dots (O18 diagnosability: small loss under PT-04)
nets/rails: no net or rail change in any option; POFV/6L change only vias/stack
mechanical: thickness unchanged except PT-12 (-0.15..-0.35 F band, size.md SIZ-03 interacts) and PT-02 if 6L forces 1.0 mm (+0.2)
firmware: only PT-04 (pin-number bookkeeping; none for code using GPIO names)
docs that would change on adoption: reg-board.md (stack-up, rules, via policy), integration-map §4 (PT-04), sub-processing, sub-audio-in (duct), physical.md (stack), place.py rules()
plm: research only; no tools/plm.py impact run (no design change made)
```

## 6. Open items
```yaml
TBD-1: live JLC quote (owner login) for 5 panels 70x70: 4L 0.8 ENIG baseline vs +POFV vs 6L 0.8 vs via 0.15/0.35 vs 0.2/0.45 vs castellations; also whether 6L is offered at 0.8 mm (S13 conflict)
TBD-2: HDI access (whitelist code in S10 JS) and HDI min thickness / lead time
TBD-3: JLC enforcement of S7 "recommended minimum" chip-to-QFN/BGA 1.0 mm (today's decaps sit closer to U1): run JLCDFM on the Phase-2 layout
TBD-4: component-to-edge and bottom-side weight rules for Std double-sided PCBA (no JLC page found 2026-10-03); first-reflow side
TBD-5: castellation min hole 0.5 (S1) vs 0.6 (S9)
TBD-6: WLCSP90 fanout study (only if option C is ever wanted)
```
