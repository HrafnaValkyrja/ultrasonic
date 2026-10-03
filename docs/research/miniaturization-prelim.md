# miniaturization-prelim: Phase-2 preliminary synthesis (4 research lanes merged)

```yaml
id: MINI-SYNTH
doc: docs/research/miniaturization-prelim.md
date: 2026-10-03T01:10Z (owner-local 2026-10-02 ~21:10 EDT)
status: preliminary Phase-2 research. NO board/schematic/placement/routing/spec edit. Not committed.
inputs:
  lanes: {packages: docs/research/mini/packages.md (MINI-PKG), pcbtech: docs/research/mini/pcb-tech.md (MINI-PCBTECH), architecture: docs/research/mini/architecture.md, areamodel: docs/research/mini/area-model.md (MINI-AREA; sim/mini/area_model.py)}
  context: [docs/research/simplification-study.md (Package B, B3), docs/research/simplify/size.md, simplify/assembly.md, docs/system/integration-map.md, physical.md, reg-board.md, spec §12 O8-O23, docs/brief/queue.yaml A-PORT-SEAL]
  own_runs:
    size: "sim/checks/size_budget.py scenario() + DOCKS.flex_tail=dict(t=2.8,tail=0.5,L=25.5,g=0.9) (arch-lane definition), fenced 3G, 2026-10-03T01:0xZ; reproduces the arch-lane numbers exactly"
    stowage: "rear-zone vs wire-slack estimate, fenced 3G, 2026-10-03T01:0xZ (method in MZM-01.stowage)"
    jlc_spotcheck: "tools/jlc.py 2026-10-03T01:01Z: C5271033 STM32U575OIY6QTR 10 pcs $15.1398; C5271013 STM32U575CIU6Q 8 pcs $8.9281; C99009 X1A0000610006 48097 $0.2125; C319184 GRM033R61A225ME47D 178210 $0.0301; C282565 PMEG3005EL 43359 $0.1150; C107369 CL05A225KP5NSNC 876651 $0.0129; C409058 ERJ2BSFR10X 15928 $0.0732; C76934 GRM033R61A104KE15D 849307 $0.0039; C5832315 FTC201208S2R2MBCA 674 $0.0969 (all consistent with lane reads 00:40-00:54Z)"
baseline:
  revF: {board: "34.05x13.05x0.8 mm, 4 layers, 52 parts + 11 J wire pads + 10 TP/dots, both faces", cy_mm2: {F: 157.1, B: 82.6, sum: 239.7}, pod: "S0 7801 mm3; LxTxH 38.0x11.8x15.2 + belly 3.5; 13.6 mm off the temple; 12.42 g", src: "pcbnew probe hw/pod/draft_r1/pod_r1_routed.kicad_pcb (areamodel 2026-10-02, arch 2026-10-03); size_budget S0"}
  pkgB_mech: {what: "SIZ-01 board 28x12, SIZ-02 board hung from the lid, SIZ-03 Fgap 1.25, SIZ-04 lid 0.8, SIZ-06 dock tails bent flat, SIZ-14 rear stowage, ASM-09 hand pads to B", pod: "6829 mm3; T 11.35; H 14.5 + belly 2.05; 13.15 off temple; 11.96 g", state: "proposed in simplification-study §3 (awaits owner review); NOT in Rev F (Phase 1 kept 34x13 in the rev-1 shell)"}
guardrails: [memory/two-phase-redesign.md, "spec §1 untouched", "owner decisions: every reversal is an option needing her call, never done"]
abbrev:
  cy: courtyard area mm2 (part + assembly clearance)
  T: pod thickness off the temple axis (y), mm
  Fgap/Bgap: gap from board F surface (lid side) to the lid / from board B surface (cell side) to the cell
  env: pod outer envelope volume mm3 (size_budget v_env)
  1f/2f: parts on one face (B, cell side; SW1 alone on F) / on both faces
  U: courtyard utilisation of a face's placeable area (area-model definition)
  POFV: plated-over filled via = via-in-pad, filled with epoxy/Cu and plated flat
  HDI: high-density interconnect (laser blind microvias, sequential lamination)
  WLCSP: wafer-level chip-scale package (bare die + solder bumps)
  conf: "[V] verified primary source (url/file + date) | [E] estimate (model/judgement, method named) | [T] TBD"
  rv: "cost to reverse if wrong after the rev-1 order: S shell reprint | H hand rework on rev 1 | B board re-spin | BS board + shell re-spin | F firmware"
id_prefixes: {MZM: measure, MZ: package, MZG: guardrail, MZD: owner decision, MZV: verification, MZS: side finding}
```

## 0. Bottom line

```yaml
BL-1: "Board AREA is almost volume-free. The cell (Renata ICP501233PA-02, 175 mAh Li-po pouch with protection board, 35x12x5.3) sets pod length and height. Board length <= 35 costs 0 mm3; board HEIGHT 13 -> 12 is the only outline lever that buys volume (-282 mm3: 7111 -> 6829) [E size_budget]. mm2 saved pays only if it enables a thickness change or frees wire stowage."
BL-2: "THICKNESS is the lever: 0.1 mm of T = 60 mm3 [E]. Bgap 1.4 is pinned by the mic (SPH0641LU4H-1, 1.08 mm) + unknown cell swelling; board 0.8 is JLC's floor for assembled 4L/6L [V quote form 2026-10-03]; Fgap (1.25 in Package B) is the one free item."
BL-3: "Biggest new measure: one-face board (MZM-01): every part on B, SW1 alone on F in a 0.4 mm lid pocket. -570 mm3 vs Package B (T 11.35 -> 10.40, 13.15 -> 12.20 mm off the temple), no logic change. It fits the cell length only at U >= ~0.58 on one face (best face ever routed in this repo: 0.605) with 0201 passives + POFV/6L, and only at board L <= ~32 mm so 12 loose wires still stow [E]."
BL-4: "A WLCSP MCU (same die, same firmware) saves 28-45 mm2 of courtyard and 0 mm3/0 height. It is only an enabler (one-face board 31-32 -> 23-26 mm, stowage 2x). Costs: via-in-pad, X-ray only, no hand rework or probing, 10 in stock. Not recommended for rev 1 unless MZ-2's density trial fails."
BL-5: "Rejected on evidence: thinner laminate (0.6 not offered for 4L/6L; 0.4 cannot be panelised), rigid-flex (JLC does not make it), flex main board, flex arm tail (fatigue), bare-pad dock contacts, stacked/folded/belly boards, Bgap trim, smaller L1 package (fails ST DCR rule), STM32U535 (memory/USB/DFU)."
BL-6: "Recommend MZ-2 'Balanced' (one-face, QFN48 kept, vetted 0201 set, 6L 0.8 if quoted else 4L + POFV): 6259 mm3 (-19.8 % vs Rev F in today's shell 7801), T 10.40. Gate = placement-only density trial + stowage check + noise/acoustics/thermal re-runs. Fallbacks: MZ-2b (two-face, F parts capped at 0.65 mm: 6619) or MZ-1 (Package B as is: 6829)."
BL-7: "Side finding for the Phase-1 review (not a size item): C8/C9 are 6.3 V parts where ST requires >= 10 V (MZS-01) [V]. Same-footprint fix."
```

## 1. Ranked measures (lane duplicates merged)

Order: pod mm3 first, then enabling value for the mm3 measures, then risk. mm3 deltas vs Package-B mechanics (6829) unless stated. Lane ids in `src_lanes`.

```yaml
MZM-00: {rank: base, what: "Package-B mechanics as the Phase-2 base: board 28x12, board hung from the lid (2 pins + VHB), Fgap 1.25, lid 0.8, dock tails flat (spends the USB-C fallback O16(3), study IB-13), hand pads + TPs on B", src_lanes: [AM-01, WP-1, TP-1, "simplification-study §3.1/§3.9/§4.4"],
  mm2: "board 442 -> 336; cy ~-13 (WP-1 -9.3, TP-1 ~-4)", mm3: "-972 vs Rev F in today's shell (7801 -> 6829, -12.5 %)", cost: "0 fees",
  risk: "low-med; study gates: wear dummies before the outline freeze, lid-hung bond + SW1 press coupon", rv: BS, owner: "yes: her Package-B review (pending)", conf: "[E] size_budget; [V] probe"}
MZM-01: {rank: 1, what: "One-face board: all parts on B (cell side); SW1 (C&K KMT022NGJLHS, IP68 tact switch, 0.65 mm) alone on F, nested in a 3.3x2.9x0.4 mm lid pocket round the D3.2 plunger bore; flat F face taped full-face with VHB; VHB annulus seals the mic port", src_lanes: [ARCH-02, MINI-PT-12, AM-07],
  mm3: "-570 (6829 -> 6259); T 11.35 -> 10.40; off temple 13.15 -> 12.20; Fgap 1.25 -> 0.30 (VHB 0.25 + 0.05) [E size_budget own run = arch run]",
  reconcile: "PT-12's -0.15..-0.35 mm = no lid pocket (Fgap kept for SW1 0.65 + clearance = MZM-02 numbers, -210); AM-07's -1.0..-1.25 mm = Fgap -> 0 upper bound; use -0.95 mm / -570 mm3",
  mm2: "board GROWS. 1f length at H 12: Rev F parts 38.6 @U0.60 (no fit); QFN + vetted 0201/crystal/R21/D4 set ~31-32 @U0.60, ~34 @U0.55, ~37 @U0.50 [E: area-model scenario c 29.9 @U0.60 + ~1.5 mm for the caps the packages lane keeps at 0402/0603 and the Murata L1 kept]; with WLCSP (MZM-06) 23.3-25.7 @U0.60 [E area-model d/d_ks]",
  stowage: "rear zone (behind board + behind cell; physical.md issue 15 convention) shrinks with Fgap: y-depth 3.45 -> 2.50. Zone: B 28 2f 440 mm3; 1f L34 147, L32 212, L30 276, L28 341, L26 405. Need for 12 wires (4 arm OD 0.3, 5 dock OD 0.8, 2 cell OD 0.6, 1 NTC OD 0.5) x 10 mm slack x fold 3-4: 107-142 mm3; 31-42 without the 5 loose dock wires (MZM-03) [E: ODs except dock 0.8 assumed; slack per size.md]. => 1f board must be <= ~32 mm, or have fewer loose wires",
  benefits: "SMPS loop (U1 + L1 + C7-C9) on one face; F flat -> full-face VHB bond (removes SIZ-02 bond-in-peel and SW1-press-in-tension risk, study §4.4); mic seal by VHB annulus (A-PORT-SEAL direction); every part visible when the lid lifts (O18); U1/U3 dies face the opaque cell [E]",
  risk: "med-high: (a) one-face density U >= ~0.58 [E]; (b) stowage (above); (c) mic, bridge, L1 on one face: in-plane >= 10 mm rule (IB-10) holds at L >= 23, coupling must be re-simulated (sim/noise) [E]; (d) heat: U3 charger, U4 LDO, Q1/Q2 are ALREADY on B in Rev F; adds U1 + L1 only (mW class) [E]; (e) lid pocket depth vs KMT022 height tolerance (0.65 nominal only) [T]; (f) mic duct 3.55 -> 2.6 mm, first quarter-wave 24.2 -> 33.0 kHz (still in band) -> acoustics re-run [E]",
  cost: "0 fee delta (SW1 keeps double-sided assembly, O13 intact). Option: hand-solder SW1: -$33.77 setup+stencil, +$3.84 hand work [V assembly.md S1 / jlcpcb.com/help/article/pcb-assembly-price Sep 09 2026]",
  rv: BS, owner: "yes (big face change after her Phase-1 review; lid change)", conf: "[E] model; heights [V] tools/checks/part_heights.yaml (datasheets read 2026-10-02)"}
MZM-02: {rank: 2, what: "F-face height cap 0.65 mm (two-face kept): L1, C4, C7, Y1 to B; C11/C12 -> <= 0.55 mm C0G. ARCH-01b: cap 0.60 with SW1 excluded", src_lanes: [ARCH-01, ARCH-01b],
  mm3: "-210 (6619; T 11.00; 12.80 off temple); ARCH-01b -240 (6589) [E own run]", mm2: "0 (~20 mm2 moves F -> B)",
  risk: "medium: SMPS loop VLXSMPS (U1 on F) -> L1 (B) crosses >= 2 vias (AN5373 wants a tight same-side loop) -> noise + E11 whine re-run; JLC had no 2.2 uH inductor <= 0.65 mm stocked 2026-10-03T00:44Z [V]",
  no_move_variant: "keep faces; L1 -> cjiang FTC201208S2R2MBCA (2.2 uH, 2.0x1.2x0.8, 160 mohm) + Y1 FC-12M 0.60 + C4 0402 -> F max 0.90 (C7 0603) -> Fgap 1.15 -> 6769 (-60) [E; L1 second-tier brand next to the mic, self-noise untested (D11)]",
  note: "fallback for MZM-01, not additive", rv: B, owner: "no (layout choice; shown to her)", conf: "[E]"}
MZM-03: {rank: 3, what: "Dock FPC tail: trim the magnetic dock target's (Xinyangze YZT0675) tails and solder them into a 2-layer JLC FPC (0.11-0.12 mm) that runs the 0.8 mm under-cell channel and lap-solders to a 5-finger row on B. Replaces SIZ-06 bent tails (the study rejected ASM-12 only because it collided with SIZ-06; here it is the alternative)", src_lanes: [ARCH-07, MINI-PT-09, ASM-12],
  mm3: "-94 (belly 2.05 -> 1.70; z 16.55 -> 16.20) [E]", mm2: "-5.6 (5 pads -> finger row)", stowage: "removes 5 loose dock wires: need 107-142 -> 31-42 mm3 [E]",
  cost: "second JLC order: bare 2L FPC ENIG 'from $2 / 5 pcs' promo floor, real price [T]; lead 5-6 days [V jlcpcb.com 2026-10-03]",
  risk: "medium: 10 hand lap joints (same count as wires), static bend r >= 6-10 x t [V jlcpcb.com/capabilities/flex-pcb-capabilities 2026-10-03], target sample needed first (O21 blocks)", rv: "S + FPC reorder", owner: "yes: O16(3) 'no custom connector board' reading; O21 sample", conf: "[E] size; [V] FPC rules"}
MZM-08: {rank: 4, what: "0201 for non-bulk passives (vetted set): R2 R3 R4 R5 R6 R8 R9 R10 R12 R13 R14 R15 R16 R18 R22 + RT1 (Murata NCP03XH103 0201 NTC, same family); C1 C2 C3 C6 C10 C13 C19 (100 nF, GRM033R61A104KE15D 10 V), C11 C12 (C0G), C22 (10 nF), C8 C9 (2.2 uF 10 V GRM033R61A225ME47D C319184). KEEP 0402: C5, C15 (25 V), C16, C17, C18 (TI TPS7A20 needs >= 0.47 uF effective). KEEP 0603: C7 (ST CIN 10 uF >= 10 V, ESR < 10 mohm), C21 (TI SYS >= 10 uF). KEEP 0402 hand hooks R1 (BOOT0 DFU tack point), R20 (rail lift link) unless she trades them (+1.5 mm2)", src_lanes: [PKG-0201-R, PKG-0201-C, MINI-PT-05, AM-03],
  mm2: "-20.5 cy (vetted); upper bound -35 (area-model full sweep incl. C7/C21 -> 0402) needs DC-bias proof [T]", mm3: "0 direct; enabler for MZM-01",
  cost: "~0: all 0201 are JLC Extended, Standard PCBA charges $1.53 per BOM line Basic or Extended [V jlcpcb.com/help/article/pcb-assembly-price Sep 09 2026]; Standard PCBA minimum package 0201, 0201-0201 spacing 0.15 [V jlcpcb.com/capabilities/pcb-assembly-capabilities 2026-10-03; help/article/minimum-spacing-for-smd-components Sep 09 2026]",
  risk: "medium: tombstoning; hand rework much harder (O19 serviceability); C8/C9 0201 ESR at 3 MHz < 20 mohm [T]; ratings fine (worst R10 ~4-5 mW vs 50 mW) [E]", rv: "H (hard)", owner: "yes (repairability trade)", conf: "[V] capability + stock; [E] risk"}
MZM-04: {rank: 5, what: "6-layer 0.8 mm stack (L1 parts, L2 GND, L3 sig, L4 sig/+3V0, L5 GND, L6 parts) instead of 4L. POFV free on 6L+; two more routing layers; the B face gets an adjacent GND plane (today B.Cu references In2, a signal layer)", src_lanes: [MINI-PT-02],
  mm2: "-24..-48 per face [E]", mm3: "0 if 6L is offered at 0.8 mm; +120 if it starts at 1.0 (B 6829 -> 6949; MZ-2 6259 -> 6379) [E own run]",
  conflict: "jlcpcb.com/6-layer-pcb lists 0.8 in its table but its FAQ says 1.0-2.0 mm (read 2026-10-03) [T: live quote]", cost: "[T] live quote; lead 'as fast as 48 h' [V]",
  risk: "low process; sim/noise must re-run on the new stack (O22(4))", rv: B, owner: "yes (cost, thickness risk)", conf: "[V] capability; [E] area; [T] price/0.8 availability"}
MZM-05: {rank: 6, what: "4L 0.8 + paid POFV only where needed: U1 exposed-pad vias, inner balls of U3 (TI BQ25180 charger, 0.4 mm DSBGA-8), dense decoupling pads (lets U1 decaps sit on the opposite face under it)", src_lanes: [MINI-PT-01],
  mm2: "-10..-20 per face [E]", mm3: "0; enabler", cost: "[T] 4L POFV fee appears only on the live quote", capability: "POFV epoxy/Cu filled & capped, via 0.15-0.55; ink-plugged vias NOT allowed in pads [V jlcpcb.com/capabilities/pcb-capabilities; help/article/pcb-via-covering Sep 09 2026]",
  risk: "low-med; list filled vias in the order remark; cap dimple <= 50 um", rv: B, owner: no, conf: "[V] capability; [E] area; [T] cost"}
MZM-06: {rank: 7, what: "U1 STM32U575CIU6Q (ST Cortex-M33 MCU with core SMPS, UFQFPN-48 7x7) -> STM32U575OIY6QTR (same die, WLCSP-90 4.20x3.95x0.59 mm, 0.4 mm staggered bumps, SMPS ballout) C5271033; or STM32U585OIY6Q (same die + crypto) C5271032", src_lanes: [PKG-MCU-A, MINI-PT-04, AM-05],
  facts: "C5271033 Extended 10 pcs $15.1398 vs QFN C5271013 8 pcs $8.9281 [V JLC 2026-10-03T01:01Z]; U585OIY6Q 6 pcs $9.85 [V JLC 00:40Z, packages lane]; height 0.59 vs 0.60 [V DS13737 Rev 10 §6.4 p318-319]; every Rev F port pin and AF present [V ST STM32_open_pin_data @7d1f151 fetched 2026-10-03T00:39Z]; ball ids change -> pin-contract.yaml, system_map.py, gen.py symbol (logic unchanged); +VDDUSB/VDDIO2/VREF+ balls need +3V0 + 2-3 decaps",
  mm2: "-28.8..-44.7 cy (KiCad 1.0 mm BGA courtyard vs tight; depends on whether JLC enforces its 'recommended' 1.0 mm chip-to-BGA spacing) minus 3-5 for the extra decaps [E]", mm3: "0 direct; enabler: 1f board 31-32 -> 23-26 mm, stowage 212 -> 341-405 mm3 [E]",
  fanout: "0.15-0.175 mm copper gap between balls: no track and no dog-bone via between any two balls -> every used non-perimeter ball needs via-in-pad (16-25 balls; lanes count rings differently) via POFV (4L paid / 6L free) or HDI 1-step [E from V rules S1/S5]",
  cost: "+$6.21/pod (U575) or +$0.92 (U585) + MZM-04/05 or HDI; X-ray unchanged",
  risk: "high: no hand rework; X-ray only; MCU pins no longer probeable (O18); joint life on a worn, flexed 0.8 mm board unknown, no JLC underfill found [T]; bare die light-sensitive (opaque cover; in MZM-01 the die faces the cell) [E]; stock 10/6 (buy-once-with-spares at freeze, O19/O21)", rv: B, owner: yes, conf: "[V] part/pins; [E] fan-out, area"}
MZM-09: {rank: 8, what: "R21 bridge shunt 0.1 ohm 1206 -> 0402: Panasonic ERJ2BSFR10X (current-sense) C409058 (study OUT-02 pick) or Uni-Royal 0402WGF100LTCE C270655", src_lanes: [PKG-R21, OUT-02, AM-04, VAR-OUT-02],
  mm2: "-8.5", mm3: 0, cost: "C409058 Ext 15928 $0.0732 [V JLC 01:01Z]", risk: "9.9 mW peak vs 62.5 mW [E]; shorter Kelvin stubs help; lift-to-disconnect test hook (O15/O18) harder by hand", rv: H, owner: "yes (she kept 1206 in Phase 1 and deferred OUT-02 to Phase 2)", conf: "[V] part; [E] dissipation"}
MZM-10: {rank: 9, what: "Y1 Epson FC-135 (32.768 kHz crystal, 3.2x1.5, CL 12.5 pF) -> Epson FC-12M 7 pF 2012 X1A0000610006 C99009 (or Micro Crystal CM9V-T1A 1610 7 pF C5341288); retune C11/C12 to ~8-10 pF C0G", src_lanes: [PKG-Y1, AM-04, F2],
  mm2: "-1.9..-5.0 (by courtyard convention)", height: "F 0.90 -> 0.60 [V Epson FC-12M sheet, local fc12m.txt]", mm3: "0 alone (part of MZM-02 no-move variant)",
  margin: "gmcrit 2.16 -> ~1.0 uA/V vs ST Gmcritmax 2.7 at LSEDRV=11 [V DS13737 Rev 10 LSE table; E stray]; also fixes the CL mismatch (MZS-02)", cost: "C99009 Ext 48097 $0.2125 [V JLC 01:01Z] (+$0.04; Basic -> Extended, no fee change)", rv: B, owner: no, conf: "[V]/[E]"}
MZM-12: {rank: 10, what: "D4 Hottech 1N5819WS (SOD-323 Schottky, reverse-dock block) -> Nexperia PMEG3005EL (30 V 0.5 A Schottky, SOD882 1.0x0.6) C282565", src_lanes: [PKG-D4, AM-04 c+],
  mm2: "-4.3", height: "B 1.00 -> ~0.5", cost: "Ext 43359 $0.115 [V JLC 01:01Z]", risk: "0.5 A IF vs ~0.19 A load; ~0.07-0.1 W in 1.0x0.6 mm -> thermal check [E]", rv: B, owner: no, conf: "[V] part; [E] thermal"}
MZM-11: {rank: 11, what: "L1 Murata DFE201610E-2R2M (2.2 uH SMPS inductor) on Murata's land (KiCad L_Murata_DFE201610P) instead of the easyeda land (pads span 3.2 mm for a 2.0 mm part). Same part", src_lanes: [AM-02, PKG-L1],
  mm2: "-3.3 cy, ~-0.6 mm 2f length [E]", no_package_shrink: "Murata DFE201210U-2R2M DCR 228 mohm max and every stocked 1608 2.2 uH fail ST DS13737 Rev 10 §5.1.6 (L 2.2 uH +-20 %, ISAT > 0.5 A, DCR < 200 mohm) [V]; cjiang FTC201210S2R2MBCA (135 mohm) passes on paper, second-tier brand, -0.46 mm2 only",
  risk: "footprint swap; JLCDFM verdict", rv: B, owner: no, conf: "[V]"}
MZM-15: {rank: 12, what: "Wire attachment: (a) J pads trimmed to 1.27 mm-pitch cells (SIZ-10); (b) castellated rear-edge half-holes; (c) Hirose FH35C-11S-0.3SHW (0.3 mm-pitch 11-pin FPC ZIF connector, C5741856, 220 pcs, $1.35) for cell + dock + NTC", src_lanes: [AM-06, MINI-PT-08, WP-3],
  mm2: "(a) -17; (b) -20..-25 F; (c) ~0..+3 [E]", capacity_b: "12 mm edge - 2x1.0 corner keep-out, 0.6 hole + 0.5 web -> 8-9 holes [V jlcpcb.com/help/article/what-is-castellated-holes Sep 09 2026; capabilities page says 0.5 min: conflict, design to 0.6] vs 12 wires (Rev F/B3) -> does not fit; vs 9 (full B) -> zero margin",
  risk: "(a) solder-blob margin; (b) plating pull-off under wire strain; (c) contacts under exciter vibration, mated height [T]", rec: "(a) only", rv: B, owner: "yes (she hand-solders; (c) is an O19 serviceability-vs-reliability call)", conf: "[V] rules; [E] area"}
MZM-16: {rank: 13, what: "Via policy: default 0.3/0.4 or multilayer 0.2/0.45 (both surcharge-free); 0.15/0.25-0.35 or 0.2/0.1 only in fan-out regions; track/space >= 0.09 mm", src_lanes: [MINI-PT-07, AM-08],
  facts: "today's rule 0.35/0.15 (hw/pod/place.py rules()) already triggers JLC's small-via surcharge (hole < 0.3 AND dia <= 0.4) [V cart.jlcpcb.com/quote text 2026-10-03]; 0.1/0.2 allowed on boards <= 1.0 mm with ENIG/OSP [V]; 3.0-3.5 mil on 4-8L = +20 % of the order [V help/article/in-what-cases-will-there-be-charged-extra Sep 09 2026]",
  mm2: "via squares 22.8 -> 9.9 mm2/layer if 0.2/0.1 throughout (+0.03-0.04 U) [E]; bigger free vias cost 0..+5 mm2/face", cost: "surcharge amount [T]", rv: B, owner: no, conf: "[V] rules"}
MZM-13: {rank: 14, what: "C4 VDD bulk 10 uF 0603 -> 0402 10 V (Murata GRM155R61A106ME11D C408132)", mm2: "-2.6", risk: "effective ~4-5 uF at 3 V vs ST AN5373 '10 uF typ, 4.7 min': borderline [E] -> DC-bias curve first", rv: H, owner: no, src_lanes: [PKG-C4, AM-03], conf: "[E]"}
MZM-14: {rank: 15, what: "C14 bridge reservoir 22 uF 0603 -> 0402 22 uF 6.3 V (Murata GRM155R60J226ME11D C415703), or study OUT-05 (1 uF 0402)", mm2: "-2.6", risk: "bridge droop at ~315 mA peaks must be re-simulated (spice-sim); tied to the OUT-03/05/07 clamp decision she deferred", rv: H, owner: yes, src_lanes: [PKG-C14, VAR-OUT-05], conf: "[E]"}
MZM-17: {rank: 16, what: "Owner-reversal variants (area only): PER-07 LED to the pod lid (-5.2 mm2; arm wires 4 -> 2; pad -50..-110 mm3 outside the pod); PER-08 no LED (-7.9); PER-01D CC out of the pod (-4.8); OUT-01 R4/R6 out (-3.4); OUT-03 (-1.65); OUT-05 (-2.6)", src_lanes: [VAR-LED-CC-SELFTEST, simplification-study §2],
  mm2: "~-27 total (~-2.4 mm of 1f length @U0.60) [E]", mm3: "0 in the pod", reversals: "O8 (LED in the pad), O12(a)/O16(3) 5-contact dock, triage Q19 (R4/R6), OUT-07 clamp", rec: "keep her decisions (B3 defaults); reopen only if MZM-01's trial is short by <= ~2 mm; PER-07 is the most valuable (also -2 wires for stowage and R24)", owner: yes, conf: "[V] study rows + probe"}
MZM-18: {rank: 17, what: "Copy SWD/NRST/3V0/GND to the O9 snap-off frame through a solid tab; keep the 0.5 mm on-board dots (post-bond SWD)", mm2: "~-1", rv: B, owner: no, src_lanes: [TP-2]}
MZM-19: {rank: 18, what: "U6 TI TPD2E2U06 (2-ch USB ESD, SOT-553) -> TI TPD2EUSB30DRT (1.0x0.8, 0.7 pF) C97502 (-0.9 mm2, +$0.40); U4 TI TPS7A2030 (3.0 V LDO) X2SON-4 -> DSBGA-4 YCK 0.35 mm pitch (-0.5 mm2; exactly JLC's 0.35 mm Standard limit; active-discharge -P suffix on the YCK code [T]; 310 pcs)", rec: "U6 optional, U4 skip", rv: B, owner: no, src_lanes: [PKG-U6, PKG-U4]}
MZM-07: {rank: reject-rev1, what: "U1 -> STM32U535NEY6Q (smaller-memory U5, WLCSP56 3.38x3.38) or STM32U535REI6Q (UFBGA64 5x5, 0.5 mm, dog-bone escape)", mm2: "-33..-50", why_not: "512 KB flash / 274 KB SRAM vs 2 MB / 786 KB (FWSIM-R62 plans a 230 KB log ring); USB_DRD_FS driver, no UCPD; ROM DFU support [T AN2606]; spec D5 change; WLCSP56 has 20 used inner balls (HDI/6L); UFBGA64 0 in stock [V JLC 00:40-00:52Z]", src_lanes: [PKG-MCU-C], owner: "only if she wants it"}
```

```yaml
rejected:
  MZR-01: {what: "0.6 or 0.4 mm laminate", why: "quote-form tooltip: 0.60 mm 'not available for 1-layer, 4-layer or 6-layer'; 0.40 mm ENIG only, no panel/castellations -> a 28x12 board cannot meet Standard PCBA's 70x70 single-board minimum [V cart.jlcpcb.com/quote 2026-10-03T00:41Z; pcb-assembly-capabilities]. Resolves the arch lane's ARCH-05 [T] and corrects size.md §9's reason (0.6 IS a listed FR-4 thickness, 2-layer only). Would have been -120 mm3. Re-confirm on the live quote", src_lanes: [MINI-PT-06, ARCH-05]}
  MZR-02: {what: "rigid-flex; whole board as 4L FPC + stiffeners", why: "JLC: 'does not support Rigid-Flex' [V flex FAQ 2026-10-03]; 4L FPC static-only, $49.25 fixture/order [V pcb-assembly-price], SW1 needs a rigid back, stiffener returns the thickness", src_lanes: [MINI-PT-11, ARCH-06, SH-3]}
  MZR-03: {what: "flex tail up the NiTi arm", why: "dynamic bend for years (1-2L adhesive-less PI, r >= 10-15 t [V flex page]); arm fatigue is risk R24; litz is the proven path", src_lanes: [MINI-PT-10]}
  MZR-04: {what: "PCB-pad / edge-plated dock contacts (drop the magnetic target)", why: "ENIG 1-2 u-inch gold is not a daily-mating finish [V finish; E wear]; O12(a)/O16(3)", src_lanes: [MINI-PT-13, DK-3]}
  MZR-05: {what: "stacked / folded / belly / temple-side / cell-end boards", why: "stacking >= +1.6 mm T; belly face ~231 mm2 too small; mic/SW1 must face out [E]", src_lanes: [SH-2..SH-6, DK-2]}
  MZR-06: {what: "Bgap 1.4 -> 1.2", why: "mic 0.12 mm from the pouch; no Renata swelling data", src_lanes: [ARCH-R1]}
  MZR-07: {what: "smaller L1 package (1608, Murata 2012)", why: "fails DS13737 §5.1.6 DCR < 200 mohm / ISAT > 0.5 A [V]", src_lanes: [AM-04, PKG-L1]}
  MZR-08: {what: "HDI for rev 1", why: "manual pricing ('price pending'), whitelist code in the quote JS, 'repair difficult' [V help/article/hdi-pcb-capabilities-faq Sep 07 2026; quote JS 2026-10-03]; only as MZ-3 fallback if 6L 0.8 is unavailable", src_lanes: [MINI-PT-03]}
  MZR-09: {what: "top-port mic so the board can be single-sided on F", why: "SPK0641HT4H-1 has no response spec above 20 kHz; F1 is the product", src_lanes: [CS-4]}
  keep_fixed: "Q1/Q2 Nexperia PMCXB290UE (N+P MOSFET pair, DFN1010B-6: smallest pair found); U3 BQ25180 (already DSBGA); U2 mic (D13); SW1 (O16-7); D5 TI TPD1E10B06 (VBUS ESD, X1SON): a 0201 swap saves 0.3 mm2 and costs surge margin at the only exposed contact"
```

## 2. Phase-2 packages

Pod numbers from own size_budget run (2026-10-03T01:0xZ, fenced). Board length = area-model prediction at the U stated [E]. Rev F in today's shell = 7801 mm3, T 11.8, 13.6 mm off the temple.

| | **MZ-1 Conservative** | **MZ-2 Balanced (recommended)** | **MZ-2b fallback** | **MZ-3 Aggressive** |
|---|---|---|---|---|
| faces | 2f | 1f (SW1 alone on F, lid pocket) | 2f, F parts <= 0.65 | 1f |
| MCU | QFN48 | QFN48 | QFN48 | WLCSP90 (U575/U585 OIY6Q) |
| passives | 0402/0603 | vetted 0201 set (MZM-08) | 0402 (0201 optional) | vetted 0201 set |
| PCB | 4L 0.8, POFV at U1 EP + U3 only | 6L 0.8 if quoted, else 4L + POFV in fan-out | 4L 0.8 + POFV at U1/U3 | 6L 0.8 (HDI 1-step only if 6L 0.8 unavailable) |
| dock | SIZ-06 flat tails | SIZ-06 flat tails | SIZ-06 | FPC tail (MZM-03) |
| board | 28 x 12 (lower bound ~24-25) | ~31-32 x 12 @U >= 0.58 (must be <= 32) | 28 x 12 | ~23-26 x 12 @U 0.60 |
| pod env mm3 | 6829 (-12.5 %) | **6259 (-19.8 %)** | 6619 (-15.2 %) | 6173 (-20.9 %) |
| T / off temple mm | 11.35 / 13.15 | **10.40 / 12.20** | 11.00 / 12.80 | 10.40 / 12.20 |
| height incl. belly mm | 16.55 | 16.55 | 16.55 | 16.20 |
| stowage zone vs need mm3 | 440 vs 107-142 | 212 (L32) vs 107-142; 147 at L34 | 440 vs 107-142 | 341-405 vs 31-42 |
| hand rework | everything | QFN yes; 0201 hard | everything | MCU never; 0201 hard |
| owner calls | Package B review | MZD-1, -3, -4, -6, -7 | MZD-1 | MZD-1..-7 |

```yaml
MZ-1:
  name: conservative ("Package B + clean-ups")
  members: [MZM-00, MZM-05 (U1 EP + U3 inner balls only), MZM-10, MZM-11, MZM-12, MZM-16, MZM-18, MZS-01 fix]
  optional: "MZM-02 no-move variant (Fgap 1.15, 6769, -60; second-tier L1)"
  predicted: {board: "28x12 = 336 mm2 (area lower bound 24-25 x 12 @U0.50 -> ~12-15 % margin) [E]", pod: "6829 mm3, -972 vs Rev F [E]"}
  cost: "parts ~+$0.2/pod [E]; 4L POFV fee [T]; small-via surcharge avoided where 0.3/0.4 fits"
  O19: "PASS: all 0402/QFN hand-reworkable; U3 DSBGA unchanged; MCU pins probeable"
  O20: "PARTIAL: Package-B size only; leaves -0.95 mm of thickness on the table"
  O21: "PASS: no purchase beyond the study's gates (pod-only dummies, bond coupon); live quote is free and is not an order"
  O22: "noise, acoustics, thermal re-run on the final layout; JLCDFM verdict"
  claude_time: "[E] ~0.5 day agent time + the joint layout session (O14, owner time separate)"
MZ-2:
  name: balanced (RECOMMENDED)
  members: [MZ-1, MZM-01, MZM-08, MZM-09 (owner), MZM-13 (after DC-bias check), "MZM-04 if the live quote gives 6L at 0.8 mm, else MZM-05 widened to all dense fan-out", "MZM-16 small vias in fan-out only"]
  shell: "lid pocket for SW1 (3.3x2.9x0.4), plunger re-length (R-UI-BODY), full-face VHB, VHB annulus mic seal, Fgap 0.30"
  predicted: {board: "~31-32 x 12 one face @U >= 0.58 [E]", pod: "6259 mm3 (-570 vs B, -1542 vs Rev F); T 10.40; 12.20 off temple [E]"}
  gate: "MZV-02 placement-only density trial at L <= 32 mm + MZV-03 stowage; fail -> add MZM-17 owner variants (-2.4 mm) or drop to MZ-2b, or escalate to MZ-3's WLCSP (owner)"
  cost: "parts ~+$0.5-0.8/pod [E]; PCB [T] (6L or POFV); assembly fees unchanged (SW1 on F); lid reprint"
  O19: "MOSTLY: QFN probe/rework kept; R1/R20 hooks kept 0402; R21 0402 if she agrees; 0201 rework harder (her call); every part visible on lid lift"
  O20: "STRONG: -0.95 mm thickness on top of Package B"
  O21: "PASS: no part purchase; coupons = resin + VHB (consumable question = study gate 5)"
  O22: "placement trial, noise (one-face coupling), acoustics (2.6 mm duct + VHB seal), thermal (U1/L1 join U3/U4/bridge on B), JLCDFM, wear dummy at T 10.4"
  claude_time: "[E] ~1-1.5 days agent time (trial, sims, docs) + layout session + owner coupon print"
MZ-2b:
  name: fallback (two-face, F capped at 0.65 = MZM-02)
  predicted: {board: "28x12", pod: "6619 mm3 (-210 vs B)"}
  risk: "SMPS loop crosses vias -> noise + whine re-run"
MZ-3:
  name: aggressive
  members: [MZ-2, MZM-06, "MZM-04 6L 0.8 (HDI 1-step only if 6L 0.8 unavailable)", MZM-03, "optional MZM-17 PER-07"]
  predicted: {board: "~23-26 x 12 one face @U0.60 [E]", pod: "6173 mm3 (-656 vs B, -1628 vs Rev F); belly 1.70 [E]"}
  marginal_vs_MZ-2: "-86 mm3 (FPC) and a 6-8 mm shorter board (stowage, density margin). WLCSP itself = 0 mm3"
  cost: "+$6.21/pod (U575OIY6Q) or +$0.92 (U585OIY6Q); 6L/HDI [T]; FPC order [T]"
  O19: "FAIL-ish: MCU unreworkable, joint life on a worn flexed 0.8 mm board unknown, MCU pins unprobeable (O18 loss)"
  O20: "best"
  O21: "needs a dock-target sample for the FPC (blocked); MCU stock 10/6 -> buy with spares at freeze"
  O22: "as MZ-2 + WLCSP fan-out study + FPC bend/pull check"
  claude_time: "[E] ~2-3 days agent time + quote/sample waits (owner)"
```

## 3. Guardrails: what Phase 2 must NOT box in

```yaml
MZG-01: "Board height <= 12.0 mm (cell-limited) and length <= 35; never trade height for area."
MZG-02: "Mic U2 stays on B on the board centre line, port registered to the lid bore (O16-5); via-free, part-free seal ring (r 1.6); sealed duct per A-PORT-SEAL (ID 1.0). Any duct length/seal change -> sim/acoustics re-run."
MZG-03: "SW1 stays on F on the centre line under the plunger (O16-5, O16-7). The one-face strategy keeps it there: the board stays double-sided (O13)."
MZG-04: "L1 and the bridge >= 10 mm from the mic (IB-10) until sim/noise says otherwise; L1 away from the left pod's dock magnets."
MZG-05: "SMPS loop (VLXSMPS -> L1 -> VDD11 C8/C9; C7 at VDDSMPS) on U1's face, tight."
MZG-06: "ST SMPS parts rule: L 2.2 uH +-20 %, ISAT > 0.5 A, DCR < 200 mohm; CIN 10 uF >= 10 V ESR < 10 mohm; COUT 2x2.2 uF >= 10 V ESR < 20 mohm [V DS13737 Rev 10 p.153]. TI: TPS7A20 caps >= 0.47 uF effective, BQ25180 IN cap 25 V, SYS >= 10 uF. No package swap may break these."
MZG-07: "Logic frozen at Rev F: package/face changes only (two-phase guardrail 1). A WLCSP changes ball ids: pin-contract.yaml, system_map.py, gen.py symbol and integration-map regenerate in the same commit."
MZG-08: "Diagnosability (O18): SWD/NRST/3V0/GND dots on the board (post-bond SWD); USB DFU path most verified; R1 (DFU tack), R20 (rail lift) and R21 (shunt lift) stay hand-reachable unless she trades them."
MZG-09: "Board 0.8 mm (JLC floor for assembled 4L/6L): the duct, the y-stack and the stiffness under the SW1 press all assume it. If 6L forces 1.0 mm, it costs +0.2 mm T / +120 mm3."
MZG-10: "Rear stowage: every package passes a stowage check (wires x OD x slack x fold 3-4, physical.md issue 15) before the outline freezes."
MZG-11: "No bare-die CSP (U3 today, U1 if WLCSP) under a translucent shell area (O23 note, Pi 2 xenon-flash precedent)."
MZG-12: "One board for both pods (O16-5); mirrored shells."
MZG-13: "Layout stays KiCad source-of-truth so sim/noise extraction and DRC re-run on it (O22(4)); layout done together (O14); no autorouter by parallel agents."
MZG-14: "Stock: anything below ~2x the build count (U575CIU6Q 8, U575OIY6Q 10, U585OIY6Q 6) is bought once with spares at freeze (O19/O21). Do not pick a part with 0 stock (UFBGA64)."
MZG-15: "Tracker blind spot: plm.py impact returns no relation for L1, C7, Y1, SW1, J3, TP1, net VLXSMPS (arch lane run 2026-10-03) -> add relations before any Phase-2 edit, so face moves turn the right docs suspect."
```

## 4. Owner decisions this research surfaces

```yaml
MZD-1: {q: "Face strategy for Phase 2: two-face (MZ-1), one-face with SW1 in a lid pocket (MZ-2), or two-face with F parts capped at 0.65 (MZ-2b)?", rec: "MZ-2, gated by the placement-only density trial at <= 32 mm and the stowage check; fall back to MZ-2b if the gate fails", why: "-570 mm3 / -0.95 mm thickness with no logic change; one-face also fixes the lid-bond peel risk and seals the mic port", reverses: none}
MZD-2: {q: "MCU package: keep QFN48, or WLCSP90 U575OIY6Q (+$6.21) / U585OIY6Q (+$0.92), or U535?", rec: "keep QFN48 for rev 1; revisit WLCSP90 only if MZD-1's trial fails AND the live quote shows 6L 0.8 or 4L POFV; never U535 for rev 1", why: "WLCSP = 0 mm3 and 0 height; costs rework, probing, joint-life certainty"}
MZD-3: {q: "Accept 0201 for the vetted non-bulk set (~-20 mm2), keeping R1/R20 (and R21) as 0402 hand hooks?", rec: "yes for MZ-2 (it is MZ-2's density enabler); keep the hooks 0402", trade: "much harder hand rework (O19)"}
MZD-4: {q: "R21 shunt 1206 -> 0402 (OUT-02, deferred by her to Phase 2)?", rec: "yes, Panasonic ERJ2BSFR10X current-sense 0402, placed at the board edge so it can still be lifted", reverses: "her Phase-1 keep"}
MZD-5: {q: "C14 22 uF 0603: keep, 0402 22 uF, or OUT-05 1 uF?", rec: "decide the OUT-07 clamp first; then a bridge droop sim; default keep 0603 (B height is mic-pinned, so its 1.00 mm costs nothing)", reverses: "her Phase-1 keep (only if changed)"}
MZD-6: {q: "6-layer at 0.8 mm vs 4-layer + paid POFV?", rec: "get a live JLC quote with her login (free, not an order: O21-compatible); take 6L if 0.8 mm is offered at an acceptable price, else 4L + POFV", why: "6L gives free POFV and a GND plane next to the B face (mic, bridge, charger)"}
MZD-7: {q: "Shell changes that MZ-2 needs: SW1 lid pocket, full-face VHB bond, VHB-annulus mic seal instead of the printed boss/gasket of A-PORT-SEAL?", rec: "yes, proven by a resin coupon (pocket depth vs KMT022 height, 600k presses, drop) and an acoustics re-run"}
MZD-8: {q: "Dock FPC tail (MZM-03): does O16(3) 'no custom connector board' allow it? Lift O21 for a target sample?", rec: "not in MZ-2; only in MZ-3, or if stowage fails at <= 32 mm"}
MZD-9: {q: "Reopen earlier decisions for density relief: O8 LED in the pad (PER-07/08), 5-contact dock (PER-01D), R4/R6 (OUT-01)?", rec: "no by default; if MZ-2's trial is short by <= ~2 mm, PER-07 first (also halves the arm wires: R24, stowage)"}
MZD-10: {q: "Wire attachment: plain pads on B (Package B), trimmed 1.27 mm pads, castellations, or a ZIF for cell + dock?", rec: "pads on B, trimmed to 1.27 mm pitch if her iron and wire gauge allow; no castellations (12 wires do not fit a 12 mm edge); no ZIF (vibration)"}
phase1_item: {q: "MZS-01: swap C8/C9 to a 10 V part now (same 0402 footprint, Samsung CL05A225KP5NSNC C107369)?", rec: "yes, via an ECR in her Phase-1 review; it is a datasheet compliance fix, not miniaturization"}
```

## 5. Verify before committing to a package

```yaml
MZV-01: {what: "live JLC quote, 5 panels 70x70: 4L 0.8 ENIG baseline / +POFV / 6L 0.8 (availability!) / vias 0.15-0.25 vs 0.2-0.45 / castellations / HDI access", who: "owner login (no order; O21 OK)", gates: [MZD-6, MZM-04, MZM-05, MZM-06]}
MZV-02: {what: "placement-only density trial: MZ-2 parts on one 32x12 (and 30x12) face with GND fan-out at JLC rules; report U and fan-out failures", how: "single agent, pcbnew API, fenced 3G, no FreeRouting, no place_r1.py; a scratch board, not the Rev F file", gates: [MZD-1]}
MZV-03: {what: "stowage check: real wire ODs (litz, dock wire choice sub-dock-usb issue 16, cell leads) x slack x fold vs the zone of the chosen outline", gates: [MZD-1, MZM-03]}
MZV-04: {what: "sim/noise on the Phase-2 layout (one-face coupling; 6L stack if chosen)", gates: ["O22(4)"]}
MZV-05: {what: "sim/acoustics: 2.6 mm duct with VHB-annulus seal vs the A-PORT-SEAL boss", gates: [MZD-7, "O22(4)"]}
MZV-06: {what: "thermal: U1 + L1 joining U3/U4/bridge on the cell face during charge (R23); D4 SOD882 at ~0.07-0.1 W", gates: [MZD-1, MZM-12]}
MZV-07: {what: "DC-bias + ESR: 0201 2.2 uF 10 V at 1.1 V and ESR at 3 MHz (C8/C9); C4 0402 at 3.0 V; C14 0402 if chosen; C7/C21 if anyone proposes 0402 (Murata/Samsung curves)", gates: [MZM-08, MZM-13, MZM-14]}
MZV-08: {what: "LSE: FC-12M 7 pF C0/ESR, gmcrit, C11/C12 values, LSEDRV setting, ppm (A3 clock doc)", gates: [MZM-10]}
MZV-09: {what: "bridge droop sim (spice-sim) only if C14 changes", gates: [MZD-5]}
MZV-10: {what: "JLCDFM written verdict on Phase-2 footprints (0201, L1 Murata land, SOD882, WLCSP90 if chosen) incl. the 'recommended' 1.0 mm chip-to-QFN/BGA spacing", how: "free Gerber upload", gates: [all packages]}
MZV-11: {what: "resin coupon: SW1 lid pocket depth vs KMT022 (0.65 nominal, no tolerance), 600k presses at 1.2-2.0 N, drop", gates: [MZD-7]}
MZV-12: {what: "wear dummy at T 10.4 (MZ-2) next to 11.35 (B): SIZ-15 / ECR-0006, pod-only, print", gates: [MZD-1]}
MZV-13: {what: "WLCSP only: manual fan-out study at 0.4 mm staggered (fenced), JLC underfill availability, drop/flex reasoning for a worn 0.8 mm board", gates: [MZD-2]}
MZV-14: {what: "Renata ICP501233PA-02 aged swelling (sets Bgap 1.4): ask Renata or measure on rev 1", gates: ["future Bgap trim (MZR-06)"]}
MZV-15: {what: "U535 only: AN2606 ROM DFU support", gates: [MZM-07]}
```

## 6. Side findings (route outside Phase 2)

```yaml
MZS-01: {sev: compliance, what: "C8/C9 (VDD11 2x2.2 uF) are C12530 = Samsung CL05A225MQ5NSNC 6.3 V (hw/pod/gen.py L86 'C2u2': 'C12530', L152; L31 audit note 'Basic C12530 (6.3 V on a 1.1 V rail)'). ST requires COUT rated voltage >= 10 V (DS13737 Rev 10 §5.1.6 p.153; local ~/Desktop/ultrasonic-scratch/st_new/ds10.txt L18783-18785, read 2026-10-03)", fix: "Samsung CL05A225KP5NSNC 2.2 uF 10 V 0402 C107369 (Ext, 876651, $0.0129 [V JLC 01:01Z]) or 0201 GRM033R61A225ME47D C319184", route: "ECR into the Phase-1 review", conf: V}
MZS-02: {sev: margin, what: "Y1 FC-135 CL 12.5 pF with 15 pF C11/C12 -> CL ~10 pF incl. ~2-3 pF stray -> runs ~+20-30 ppm fast; gmcrit 2.16 vs Gmcritmax 2.7 (ratio 1.25)", fix: "MZM-10 (7 pF crystal) or retune C11/C12 to ~18-20 pF", conf: "V numbers, E stray", src: "packages.md F2"}
MZS-03: {sev: doc-drift, what: "integration-map.md §8 says 'TIM1 ... PA8/PA7/PA9/PB0'; Rev F leg B is PA10/PB15 (§1 F3, gen.py L49). Source: hw/pod/system_map.py L107 (stale string; commit 9480e4c fixed other text only)", fix: "edit system_map.py L107 and regenerate", conf: V}
MZS-04: {sev: cost, what: "today's via rule 0.35/0.15 already pays JLC's small-via surcharge", fix: MZM-16, conf: V, src: pcb-tech.md B5}
MZS-05: {sev: doc, what: "size.md §9 rejects 0.6 mm for the wrong reason; real reason: not offered for 4L/6L (quote form 2026-10-03)", conf: V, src: pcb-tech.md B1}
MZS-06: {sev: tracker, what: "plm.py impact blind spot for L1, C7, Y1, SW1, J3, TP1, VLXSMPS", fix: MZG-15, src: architecture.md §3}
```

## 7. Integration-map cross-check (integration-map.md §10), per package

```yaml
MZ-1:
  functions_affected: "F2 (Y1 part + C11/C12 values; L1 land), F5 (D4 part), F10 (U6 only if MZM-19); chains unchanged"
  nets_changed: none
  pins: none
  rails: "VDD11 caps to 10 V rating (MZS-01); +3V0 bulk unchanged (C4 stays 0603 in MZ-1)"
  offboard: "Package B: hand pads on B; wire count 12 / 11 pads (B3 defaults)"
  mechanical: "Package-B shell (28x12, lid-hung, Fgap 1.25, lid 0.8, flat tails); F max 1.00 (L1); B max 1.08 (mic)"
  firmware: "LSEDRV for the 7 pF crystal"
  depends_on: [Package-B review, MZV-01, MZV-10]
  conflicts_with: none
MZ-2:
  functions_affected: "none removed. F1 duct 3.55 -> 2.6 mm + VHB annulus; F2 SMPS loop on B with U1; F11 SW1 alone on F; F3/F4 R21 0402 (if MZD-4), C14 only if MZD-5; F14 hooks R1/R20 kept 0402"
  nets_changed: none
  pins: none
  rails: "none electrically; C4 0402 lowers +3V0 effective bulk to ~4-5 uF [E -> MZV-07]; C8/C9 10 V"
  offboard: "J pads all on B; count unchanged (12 wires / 11 pads); rear zone shrinks -> MZV-03"
  mechanical: "every part on B except SW1; Fgap 0.30; lid pocket + plunger re-length; full-face VHB; board ~31-32 x 12; B band 1.4 unchanged; shell_r1.py y-stack, lid features, R-UI-BODY, R-BOARD-BODY, R-AUDIO-BODY change; SIZ-03 and the study's chimney boss superseded"
  firmware: "LSEDRV only"
  depends_on: [MZ-1, MZV-02, MZV-03, MZV-04, MZV-05, MZV-06, MZV-11]
  conflicts_with: "SIZ-03 (replaced), A-PORT-SEAL boss form (replaced by VHB annulus if MZD-7), R-PROC-BOARD text 'MCU on F centre'"
MZ-3:
  functions_affected: "as MZ-2; F5/F10 dock wiring via FPC (MZM-03); F14 loses MCU-pin probing (TP dots remain)"
  nets_changed: none
  pins: "U1 ball ids replace QFN pin numbers (same ports/AFs [V open pin data]); +VDDUSB/VDDIO2/VREF+ balls tied to +3V0/VDDA with decaps"
  rails: "+2-3 decaps on +3V0"
  offboard: "5 dock wires -> 1 FPC strip; 7 loose wires remain"
  mechanical: "as MZ-2; belly 2.05 -> 1.70; board ~23-26 x 12; opaque cover over U1 if any translucent part is above it"
  firmware: "pin-number bookkeeping only (GPIO names unchanged)"
  depends_on: [MZ-2, MZV-01, MZV-13, "dock target sample (O21)"]
  conflicts_with: "SIZ-06 (replaced by the FPC); O16(3) reading"
plm: "research only, no design change: impact not re-run here. Lane runs: architecture 2026-10-03 (place_r1.py -> 11 relations, shell_r1.py -> 8; blind spot MZS-06); areamodel 2026-10-02 (gen.py, place_r1.py)"
```

## 8. Reproduce

```
source tools/env.sh
# pod volumes (all MZ rows): size_budget.scenario(**B, override); B = dict(board_H=12, board_L=28, y_bgap=1.4, y_fgap=1.25, lid_wall=0.8, s_fixed=0.8, dock="flat_tails")
#   MZ-2: y_fgap=0.30, board_L=34 -> 6259 | MZ-2b: y_fgap=0.90 -> 6619 | MZ-3: + DOCKS["flex_tail"]=dict(t=2.8, tail=0.5, L=25.5, g=0.9) -> 6173 | 6L at 1.0: board_t=1.0
systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 -c "import sys; sys.path.insert(0,'sim/checks'); import size_budget as S; print(S.scenario('x', board_H=12, board_L=34, y_bgap=1.4, y_fgap=0.30, lid_wall=0.8, s_fixed=0.8, dock='flat_tails')['v_env'])"
# stowage zone [E]: (36.1 - board_L) * (Bgap + 0.8 + Fgap) * cav_z + 1.1*5.6*cav_z; cav_z 12.9 (B mechanics), 13.6 (S0); need = sum(n * pi/4 * OD^2 * 10 mm) * 3..4
# board lengths: python3 sim/mini/area_model.py (fenced) -> sim/mini/out/area_model.json
# stock: python3 tools/jlc.py <Cxxxx>
```
