# drastic/architecture: system-architecture alternatives for a drastically smaller pod (research only)

```yaml
doc: docs/research/drastic/architecture.md
lane: architecture (drastic-size research, owner request 2026-10-03)
status: research only. No spec/board/schematic/CAD edit. Not committed. Written under a hard 27-min budget (01:15-01:42 EDT).
date: 2026-10-03T01:15-01:40 EDT
baseline: "Phase-2 MZ-2 one-face board, Package-B mechanics: pod env 6259 mm3, L38.0 x T10.40 x H14.5 + belly 2.05, 12.2 mm off the temple, 11.99 g incl. pad/adapter (size_budget.py; = arch-lane ARCH-02). shell_r2 ~6.2 cm3 agrees."
own_runs:
  size: "scratchpad/drastic/arch_size.py -> arch_size.json (imports sim/checks/size_budget.scenario, adds docks pin2/none; fenced 3G, 01:17 EDT). Model caveat: plate/spine/heel are fixed adders calibrated on shell_r1, so very small pods (H1/H2) are OVER-estimated."
  power: "scratchpad/drastic/arch_power.py (imports sim/checks/power.py ACTIVE/IDLE/USABLE; LED 0.4 mA added = mid of O8 range) 01:17 EDT"
abbr:
  env: pod outer envelope mm3 (size_budget v_env)
  T: pod thickness off the temple, mm
  duty: fraction of time the full chain is awake (C9 idle-listening mode)
  PDM: 1-bit pulse-density-modulated mic stream (clock + data wires)
  PCM: protection circuit module (cell's own protection board)
  WLC: wireless charging
conf: "[V src date] verified primary/repo source | [E] estimate (method named) | [T] TBD"
parts_glossed:
  ICP501233PA-02: "Renata 3.7 V Li-ion polymer pouch pack, 175 mAh, PCM included, <=5.3x12x35 mm (spec O16) [V spec §12 O16]"
  ICP401230UPR: "Renata Li-ion polymer pack, 130 mAh, PCM, 4.5x12.7x31 mm [V docs/research/tws/battery.md L28, read 2026-10-01]"
  LP401230: "EEMB Li-polymer cell, nominal 4.0x12x30, 100 mAh, 2 g [V https://www.eemb.com/products-55 fetched 2026-10-03 01:17 EDT]; spec v0.14 max envelope 4.3x12.5x31 + ~3 mm PCM"
  LP401429: "EEMB Li-polymer, nominal 4.0x14x29, 130 mAh, 2.6 g [V same page 2026-10-03]"
  Adafruit-1570: "100 mAh pouch with PCM, 3.8x11.5x31 mm [V tws/battery.md L155, cached 2026-09-30]"
  SPH0641LU4H-1: "Knowles ultrasonic-capable bottom-port PDM MEMS mic (the project mic, spec D13)"
  STM32U575CIU6Q: "ST Cortex-M33 MCU, QFN-48, internal SMPS (spec D5); has TIM1 and TIM8 advanced timers [V RM0456 per docs/research/datasheet-provenance.md L55]"
  RC-BC02: "bone-conduction exciter module in the pad (spec D7)"
  YZT0675/YZP0048: "Xinyangze 5-pin magnetic target / pogo cable (current dock, integration-map §6)"
```

## 0. Bottom line (blunt)

```yaml
BL-1: "Architecture moves volume, energy deletes it. Every 'move the cell elsewhere' idea (frame clip, adapter, one shared cell, central processor) relocates the 2226 mm3 cell (5.3x12x35) instead of removing it, and the only §1-legal places for it are the same 35 mm of temple arm the pod already uses (vision line v0.9 in front, Ear-open hook behind, §1.2.2/§1.2.4 lock behind the ear and at the neck). [E]"
BL-2: "The one DRASTIC lever is the cell's THICKNESS, sized to the measured energy instead of the stacked worst case. The 175 mAh cell gives 12.9 h in the pessimistic always-awake+LED corner and 20.8 h nominal always-awake [E power.py]. A same-footprint cell 1 mm thinner saves ~600 mm3 (0.1 mm T = 60 mm3). Real catalogue options: 130 mAh 4.5 mm Renata ICP401230UPR -> 5880 mm3 (-379, -6 %); ~95-100 mAh 3.0-4.0 mm class -> 4877-5478 (-781..-1382, -12..-22 %) [E size_budget]. Cost: the 12 h-in-every-corner margin (D18/O1/O5/O16(1) are owner calls), gated on E4 current + duty measurement."
BL-3: "Second lever: the dock belly (2.05 mm x 25.5 mm under the cell) is ~496 mm3 of the envelope [E: belly 0 run]. Making the charge/DFU contacts fit the existing envelope (thinner pre-built target, 4-pin USB magnetic without CC, or end-face contacts that nest in the rear gap) saves ~230-500 mm3. O12a/O16(3) reading needed. Stacked with BL-2: 4501 mm3 (-28 %), 9.9 mm off the temple [E]."
BL-4: "A central-processor architecture (one MCU, two remote mic+exciter heads) makes the HEADS tiny (~1.7-2.7 cm3 each [E, model over-estimates]) and gives phase-coherent stereo for free, but needs ~20 cm of 6-conductor cable across the frame front and both hinges, puts ~7.6 cm3 on ONE side (asymmetric weight), saves only ~0.9 mA system-wide [E], and fights the two-frame requirement (O26) and the v0.9 vision rule. Not recommended. The neckband/behind-head variant conflicts with §1.2.4 (LOCKED): rejected."
BL-5: "Rejected for size: electronics in the ear pad (mass on the spring end, crowds the Ear-open junction: §1.2.2 risk), removing the NiTi arm (D1 tragus contact is ~35 mm from the pod; the arm is outside the pod envelope anyway, so removing it saves ~0 pod mm3), radio sync between pods (adds radio+antenna volume and current; D2 parked), wireless charging coil (net ~-150 mm3 at best, firmware path lost, [T]), replacement smart temples (conflicts §1.2.1 clip-on + two frames)."
BL-6: "Perceived-size lever (not volume): straddle the temple (cell on the head side of the temple, board/lid on the outside). Outward protrusion 12.2 -> ~6.9 mm [E], same mm3. Gated on space between temple and head on BOTH frames (O26 glasses data pending) and comfort/vision (inner side is closer to the eye). Worth a cardboard/print fit test, not a design yet."
BL-7: "Recommendation: keep the architecture (two independent pods, D2), archive nothing yet. Pursue A-1 (right-size the cell after E4-class evidence: the power-lane's current cuts compound here) + A-2 (dock in-envelope) on top of MZ-2. Target ~4.5-5.0 cm3 per pod (-20..-28 % vs 6.26), ~10 mm off the temple. A 'drastic' halving (< 3.5 cm3) is only reachable if awake current falls below ~3 mA AND the owner accepts ~8-10 h worst case: then a ~60-75 mAh, 2.5 mm cell (C3 run: 4577, still cell+board+walls bound) — i.e. the mic (1.35 mA always on) becomes the wall."
```

## 1. Energy facts that drive every option

```yaml
E-01: {fact: "Awake (algo B) 4.99 / 6.76 / 9.79 mA; idle 1.68 / 2.20 / 3.43 mA (low/nom/pess); usable 0.90/0.85/0.75", src: "sim/checks/power.py rev 2 (spec §7 v0.14)", conf: "[V repo] values themselves [E/Low] until E4"}
E-02: {fact: "mAh needed (LED 0.4 mA added): 8 h always-awake 67 nom / 109 pess; 12 h always-awake 101 / 163; 12 h at 50 % duty 69 / 112; 12 h at 18 % duty 48 / 80", src: own run arch_power.py 2026-10-03 01:17, conf: E}
E-03: {fact: "Runtime always-awake+LED (nom/pess): 175 mAh 20.8/12.9 h; 130 mAh 15.4/9.6; 100 mAh 11.9/7.4; 75 mAh 8.9/5.5. At 50 % duty: 175 30.5/18.7; 130 22.6/13.9; 100 17.4/10.7; 75 13.1/8.0", src: own run, conf: E}
E-04: {fact: "Cell volume per mAh: ICP501233PA-02 2226/175 = 12.7 mm3/mAh incl PCM; small pouches 250-330 Wh/L, no hidden 2x; HV 4.35 V pouch +14 % (Renata ICP621333HPMT)", src: "docs/research/tws-power-size.md §1 (2026-10-01/02)", conf: "V repo"}
E-05: {fact: "Mic is ~1.35 mA of the 2.2 mA idle (61 %): below ~2 mA average the ultrasonic mic, not the MCU, sets the cell", src: power.py IDLE, conf: E}
E-06: {fact: "Central 2-channel processor vs two pods, awake: 13.5 vs 14.3 mA nom; 19.4 vs 20.4 pess (MCU 1.9x for 2 channels at ~160 MHz, periph 1.3x) -> saves ~0.9 mA system (~6 %)", src: own run, conf: "E (MCU scaling guessed; 2-ch algo B ~90-130 Mcycle/s from C2-cpu-budget.md per-channel 44-65)"}
```

## 2. Size runs (size_budget.scenario; deltas vs A0 6259 mm3)

| id | change | L | T | H | belly | env mm3 | d mm3 | d % | off-temple mm | mass g | nose g |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| A0 | Phase-2 MZ-2 base, 175 mAh 5.3 | 38.0 | 10.40 | 14.5 | 2.05 | 6259 | 0 | 0 | 12.20 | 11.99 | 5.75 |
| C4 | Renata ICP401230UPR 130 mAh 4.5x12.7x31 (L held by 34 mm board) | 37.0 | 9.60 | 15.2 | 2.05 | 5880 | -379 | -6.1 | 11.40 | 11.13 | 5.33 |
| C1 | 4.0 mm same footprint (~100-130 mAh class, EEMB LP401230/LP401429) | 38.0 | 9.10 | 14.5 | 2.05 | 5478 | -781 | -12.5 | 10.90 | 10.87 | 5.18 |
| C2 | 3.0 mm same footprint (~95 mAh [E], 12.7 mm3/mAh scaled; no catalogue part found yet [T]) | 38.0 | 8.10 | 14.5 | 2.05 | 4877 | -1382 | -22.1 | 9.90 | 9.99 | 4.72 |
| C3 | 2.5 mm (~75 mAh [E]) | 38.0 | 7.60 | 14.5 | 2.05 | 4577 | -1682 | -26.9 | 9.40 | 9.54 | 4.49 |
| D1 | dock in-envelope (belly 0; upper bound, no end-face boss counted) | 38.0 | 10.40 | 14.5 | 0 | 5763 | -496 | -7.9 | 12.20 | 11.37 | 5.40 |
| C4+D1 | real 130 mAh + dock in-envelope | 37.0 | 9.60 | 15.2 | 0 | 5426 | -833 | -13.3 | 11.40 | 10.52 | 4.98 |
| C2+D1 | 3.0 mm cell + dock in-envelope | 38.0 | 8.10 | 14.5 | 0 | 4501 | -1758 | -28.1 | 9.90 | 9.37 | 4.37 |
| H1 | head pod, no cell, one-face board 32x12 | 35.0 | 5.10 | 14.5 | 0 | 2668 | -3591 | -57 | 6.90 | 6.20* | - |
| H2 | head pod, mic + bridge + LDO only, board 16x10 | 19.0 | 5.10 | 14.2 | 0 | 1655 | -4604 | -74 | 6.90 | 5.39* | - |
| M1 | master pod with 2x energy (7.5 mm cell, ~350 mAh) | 38.0 | 12.60 | 14.5 | 2.05 | 7580 | +1321 | +21 | 14.40 | 14.48 | 7.04 |

`*` H1/H2 mass includes the 2.19 g pad and the adapter; fixed shell adders over-state small pods [E]. M1 + H2 = 9235 mm3 system vs 2 x 6259 = 12518 (-26 % system, but one side GROWS +21 %).

## 3. Architecture options (each: what owner wears, size, function, comfort, two frames, service, risk, effort, §1/O check)

```yaml
ARC-1:
  name: "Right-size the cell (same architecture; thinner same-footprint cell)"
  what_changes: "Cell 175 mAh 5.3 mm -> 130 mAh 4.5 mm (Renata ICP401230UPR, real catalogue part with PCM) or a 4.0 mm ~100-130 mAh class (EEMB LP401230/LP401429 nominal [V eemb 2026-10-03]; add PCM length). Pod L and board unchanged (one-face board still needs ~31-34 mm, MZM-01), so only T shrinks."
  owner_wears: "same two pods, 0.8-1.3 mm slimmer, 0.5-1.1 g lighter each"
  saving: "C4 -379 mm3 (-6 %); C1 -781 (-12.5 %); C2 (3.0 mm, no part found) -1382 (-22 %) [E size_budget]"
  function_impact: "none to the signal chain; runtime: 130 mAh = 15.4 h nom / 9.6 h pess always-awake+LED, 22.6/13.9 h at 50 % duty; 100 mAh = 11.9/7.4 h always-awake (pess misses 8 h) [E]"
  risk: "medium: runtime estimates are [Low] until E4 (transducer current is an untraced guess, power.py PWR-04); ageing (80 % at end of life) eats margin; the idle mode becomes load-bearing (it already is, spec §7 v0.14)"
  cost: "cell price similar; no board change"
  effort: "Claude 0.5 d (CAD param + size/balance/power reruns + docs); owner 0 d (decision only)"
  spec_check: "no §1 conflict. Touches D18 (12 h target 'everywhere'), O1, O5 (keep 105-175 class), O16(1) (Renata 175 chosen by owner): owner call. O22: freeze evidence must include the runtime case chosen."
  recommend: "yes, as the main drastic lever; pick the cell after the power lane's cuts + a bench current number (E4 is hardware-only; under O21/O22 the decision may need a sim-only bound accepted by the owner)"
  conf: "E (size), V (cell dims), E/Low (runtime)"
  sources: ["sim/checks/size_budget.py", "sim/checks/power.py", "docs/research/tws/battery.md L28/L155 (2026-10-01)", "https://www.eemb.com/products-55 (2026-10-03)"]

ARC-2:
  name: "Dock contacts inside the envelope (kill the belly)"
  what_changes: "The 5-pin YZT0675 target (2.8 mm + 0.85 tails) forces a 2.05 mm belly 25.5 mm long. Options: (a) thinner pre-built target (DOCKS 'thin' YZ103915020T-04025-02, t 2.0) = prior SIZ-08, belly 1.15; (b) 4-pin magnetic USB (VBUS, D+, D-, GND; CC dropped: CC is no longer sensed since Rev F, integration-map F10) in a target <= 1.6 mm so it sits in the under-cell slack; (c) target on the rear end face nesting in the rear gap/stowage zone."
  owner_wears: "same pod minus the belly bump under the cell"
  saving: "upper bound -496 mm3 (D1); realistic -230 (a) to -400 (b/c, minus an end-face boss ~80-250) [E]"
  function_impact: "none if USB data kept (b/c); (a) none. Dropping D+/D- (2-pin charge only) loses USB DFU/self-test (O12a, O15) -> not recommended"
  risk: "medium: a <=1.6 mm pre-built magnetic target is [T] (no part found in this run); end-face contacts face the ear hook side; sealing at contacts (O12b IPX4/5)"
  cost: "connector + cable ~same"
  effort: "Claude 1 d (part search + CAD + integration-map F5/F9/F10/F15 update); owner 0.5 d (pick connector)"
  spec_check: "no §1 conflict. O12a (magnetic USB dock) kept if (b/c); O16(3) 'pre-built magnetic connector, reserve USB-C fallback' -> (c) may consume the USB-C fallback keep-out: owner call"
  recommend: "yes (b) if a part exists, else (a)"
  conf: E/T

ARC-3:
  name: "Central processor + two remote heads (one MCU, one or two cells), wired through the frame"
  what_changes: "Master pod (one side): MCU, charger, LDO, cell(s), dock. Remote head (other side and/or both): mic + H-bridge (+ LDO) only. Link: ~20 cm cable (2 x ~35 mm temple + ~140 mm along the top rim of the front) [E] crossing BOTH hinges. Conductors to a mic+bridge head: VDD, GND, PDM CLK, PDM DATA, PWM A, PWM B (6) — or 4 if the bridge stays in the master and the exciter pair runs the whole way (200 kHz PWM edges alongside the PDM pair: crosstalk risk, spec §8 routing rule)."
  stereo_bonus: "Both channels on one clock = phase-coherent stereo, which removes the D2 caveat (Ren 2025, Rowan & Gray 2008 used phase-coherent stereo). Two PDM mics can share one CLK/DATA pair via the mic's L/R select: SPH0641LU4H-1 pin 2 SELECT 'Lo/Hi (L/R) Select', data valid on opposite clock edges for SELECT=VDD/GND and tri-stated otherwise (tDZ) [V Knowles SPH0641LU4H-1 datasheet Rev B 04/06/2015, sheet 8, via https://media.digikey.com/pdf/Data%20Sheets/Knowles%20Acoustics%20PDFs/SPH0641LU4H-1.pdf fetched 2026-10-03 01:21 EDT]; whether ultrasonic mode keeps L/R sharing at 4 MHz over ~20 cm of cable [T]; U575 has TIM1 + TIM8 for two bridges [V RM0456 via datasheet-provenance.md; QFN-48 pin availability T]."
  owner_wears: "one ~7.6 cm3 master pod (M1, 2x energy) on one side + one ~1.7-2.7 cm3 head on the other, plus a cable across the frame front; OR two heads (H1/H2) + a shared cell somewhere legal (there is no legal 'somewhere' beyond the same temple zones, BL-1)"
  saving: "system 12518 -> ~9235 mm3 (-26 %) [E]; per side: head -57..-74 %, master +21 %"
  function_impact: "same function; stereo improves (coherent); power -0.9 mA system [E] -> no real cell saving"
  comfort: "asymmetric mass (master 14.5 g vs head ~5.4 g incl pad): nose-pad and ear loads differ L/R; glasses tend to tilt/rotate [E]; cable at the brow rim"
  two_frames: "poor: cable route, length and clips are frame-specific; refit per frame; must survive hinge folding (daily if she folds them at night) -> flex-fatigue failure mode (O19 durability)"
  vision_rule: "v0.9: nothing visible looking straight ahead. A cable on the top rim is at the edge of the upper field; behind the rim it may hide, [T] per frame"
  serviceability: "cable is a single point of failure for BOTH sides; detachable magnetic breakaways at each hinge add 2 connectors"
  risk: "high (wiring durability, EMI over 20 cm of PDM at 4 MHz + PWM, asymmetric weight, total redesign: schematic, firmware 2-ch, CAD)"
  cost: "fewer MCUs/chargers (O19 says unit cost is not a goal)"
  effort: "Claude 8-12 d (schematic x2 boards, 2-ch firmware/sim, cable EMI sim, CAD x2); owner 3-5 d (fit tests on two frames, cable routing, review)"
  spec_check: "§1.1/§1.2 not textually violated if all parts stay on the frame in front of the ears; D2 (independent units, 'no wiring across the hinges') reversed: owner call; neckband / behind-head cell variant CONFLICTS §1.2.4 (LOCKED) -> rejected; O16(5) one-board-for-both reversed; O26 two frames strained"
  recommend: "no. Park as the answer IF S4 shows free-running phase hurts T3 (then compare with a 2-wire clock-only link, which keeps both pods' cells)"
  conf: E

ARC-3b:
  name: "Two pods, one shared cell (cells merged, MCUs kept)"
  what_changes: "one 2x cell in a master pod, power-only cable (VBAT, GND, maybe a sync line) to the other pod"
  saving: "slave pod -2226 mm3 cell region (~H1-like 2.7 cm3 + its MCU board), master +1321: system ~-2.3 cm3 [E]; same asymmetry and cable problems as ARC-3 without the stereo bonus"
  spec_check: "D2 reversed; §1.2.4 fine if cable runs over the front"
  recommend: no
  conf: E

ARC-4:
  name: "Cell in the frame adapter / clip instead of the pod"
  what_changes: "adapter (removable, O26 flexible material) carries the cell along the temple; pod carries the board only"
  saving: "pod -2226 mm3 cell + -0.3 clearance; adapter + 2226 mm3 + its walls: net ~0 to +200 mm3 (two shells instead of one) [E]"
  function_impact: none
  comfort: "same mass, same place; cell connector between adapter and pod adds a contact pair (failure point)"
  two_frames: "worse: the adapter is the part swapped per frame (O26), so a cell inside it means two cells/adapters or moving the cell; better only if the cell is clipped in"
  spec_check: "no §1 conflict; contradicts the adapter-as-cheap-swap intent (v0.14 frame adapter separate print)"
  recommend: "no (moves volume, adds a connector)"
  conf: E

ARC-5:
  name: "Straddle the temple (cell on the head side, board outside)"
  what_changes: "pod split around the temple arm: cell pocket between temple and head, board+lid outboard; adapter becomes the bridge between them"
  saving: "0 mm3 (often +100-300 for the extra walls) BUT outward protrusion 12.2 -> ~6.9 mm (H1 head-like stack outside), inner protrusion ~7 mm (5.3 cell + 2 walls) [E]"
  function_impact: none
  comfort: "depends on the gap between temple and head 35-70 mm behind the hinge on BOTH frames [T: O26 glasses data pending]; skin contact with the cell pocket (warmth while charging is off-head, fine)"
  vision_rule: "inner side is closer to the eye; check v0.9 line [T]"
  two_frames: "gap differs per frame; flexible adapter helps"
  recommend: "maybe: cheap fit test with a printed dummy once frame data arrives; perceived size is what the owner feels as 'bulky'"
  conf: E/T

ARC-6:
  name: "Electronics inside the ear pad / pod at the tragus"
  verdict: "reject. The pad sits at the tragus in the only free spot between the Ear-open junction and the jaw (D1 v0.7); adding even the mic board puts mass on the NiTi spring end (inertia under jaw motion, force budget 1.0-1.6 N, O7b) and bulk at the ear (§1.2.2 'must not bump the driver pod', §1.2.4 'bulk at the front near the hinges'). Mic must stay at the front for the head-shadow cue and hair (E9)."
  spec_check: "conflicts §1.2.2/§1.2.4 in spirit (LOCKED); D1/E9"
  conf: E

ARC-7:
  name: "Remove the NiTi arm"
  verdict: "reject for size. The arm is outside the pod envelope (0 pod mm3). Without it the exciter can only press the temple (D1 rejected: 3-14 dB worse -> more drive -> bigger cell) or the pod must move to the tragus (ARC-6). One small win: the arm carries 4 litz wires (2 exciter + 2 LED); dropping the pad LED (O8) frees 2 wires and ~0.15-0.75 mA (about 3-9 % of awake current), owner already accepted that cost."
  spec_check: "D1, O7/O7b/O8/O11 owner decisions"
  conf: E

ARC-8:
  name: "Wireless sync between pods (radio)"
  verdict: "reject for size: adds a radio IC or a radio MCU, antenna keep-out (~mm2 clear of ground) and current (continuous audio link: mA class; clock-sync beacons only: ~tens-hundreds of uA [E, no datasheet read in this run]). It can only grow the pod. Use only if S4 says coherence matters, and then prefer it over ARC-3's cable for two-frame compatibility."
  spec_check: "D2 parked idea"
  conf: E

ARC-9:
  name: "Wireless charging coil instead of contacts"
  verdict: "not for rev 1. Removes the belly (-496 upper bound) but adds coil + ferrite (~0.3-0.6 mm over a ~10x10+ mm face, +240-360 mm3 if on the T stack) and a receiver IC; net ~-150 mm3 at best [E]. Loses the USB DFU/self-test path (O12a/O15) unless a custom bootloader over another link is written (bricking risk, O18 diagnosability). Upside: sealed (O12b) with no exposed metal (removes F15 ESD parts)."
  spec_check: "O12a, O16(3) reversal"
  conf: "E; parts T"

ARC-10:
  name: "Replace the temples (smart-temple frame, Bose-Frames style long thin cell 4x9x45 in the arm)"
  verdict: "reject: §1.1/§1.2.1 'clips onto her main glasses via removable 3D-printed clasps' (LOCKED) and the two-frame requirement (O26). Noted only because it is how commercial audio glasses get thin."
  conf: V (spec text)
```

## 4. What would make it 'drastic' (halve the pod) — the honest chain

```yaml
DR-1: "Pod floor without a cell is ~2.7 cm3 (H1: one-face board 32 x 12, mic Bgap 1.4, walls) [E, over-estimate]. So cell + its walls/clearance is ~3.6 cm3 of today's 6.26. Halving the pod means a cell of ~1/3 today's thickness or less."
DR-2: "A 2.5 mm-class cell (~75 mAh [E]) gives 4577 mm3 (C3) + dock fix -> ~4.1 cm3 [E]. To keep 8 h worst-case on 75 mAh the pessimistic always-awake current must be <= ~7 mA incl LED (75 x 0.75 / 8); at 12 h nominal-duty-50 % it already works (13.1 h) [E]."
DR-3: "Below that the mic is the wall: SPH0641 ultrasonic mode 1.1-2.15 mA continuous (E-05). Any further drastic step needs a lower-power ultrasonic front end (power lane) or mic duty-cycling, which risks clipping call onsets (C9 look-back buffer depends on the mic running)."
DR-4: "Cell supply reality: thin (<=3 mm) cells with PCM at 12 x 30-35 mm were not found in this run's catalogue reads [T]. EEMB/Renata standard lists start at 4.0-4.5 mm in this footprint [V eemb 2026-10-03; tws/battery.md]. Grepow-style custom thin pouches exist for glasses (2.16-2.38 mm thick, narrow) but at 19-47 mAh [V tws/battery.md L124]."
```

## 5. Integration-map cross-check (CLAUDE.md rule; for the two recommended measures)

```yaml
ARC-1 (cell):
  functions_affected: "F5/F6/F7/F8 unchanged in topology; BQ25180 charge current/ILIM and VBATREG re-set for the new capacity (firmware/I2C); F8 fuel thresholds"
  nets_changed: none
  pins: none
  rails: "VBAT capacity only; 2C pulse rating of the new cell must cover ~315 mA bridge peaks (tws/battery.md ICP501233 note) [T for the new cell]"
  offboard: "J5/J4 cell leads unchanged; J9 NTC if the new pack has one"
  mechanical: "cell bay T 5.3 -> 4.0-4.5 (+ H 12.7 for ICP401230UPR: +0.7 mm pod height, C4 run); cell length 31 frees 4 mm of rear stowage"
  firmware: "charger config, low-battery cutoff, LED auto-off threshold (O8)"
  depends_on: "power-lane current cuts; E4/sim bound accepted by owner"
  conflicts_with: "O16(1), D18 'everywhere' reading, O5"
ARC-2 (dock):
  functions_affected: "F5, F9, F10, F15: same nets; CC contact J12 + D6 removed if 4-pin (b)"
  nets_changed: "(b) CC/J12/R18/D6 removed; USB still FS without CC on a captive cable [E]"
  pins: none
  rails: none
  offboard: "dock contacts 5 -> 4 (b) or 5 (a/c)"
  mechanical: "belly bay removed or reduced; target moves under the cell slack (b) or rear end face (c); USB-C fallback keep-out (O16(3)) affected in (c)"
  firmware: none
  depends_on: "a pre-built thin magnetic target [T]"
  conflicts_with: "O16(3) if the fallback keep-out is consumed"
```

## 6. Missing / not done (time limit)

```yaml
missing:
  - "No primary-source read for a <=3 mm 12x35 cell with PCM (C2/C3 are scaled estimates)."
  - "No datasheet read for thin magnetic targets (ARC-2 b) or WLC receivers (ARC-9)."
  - "Radio sync current (ARC-8) is an estimate; another lane fetched nRF54L15/nPM1300 pages into the shared scratchpad (not read here)."
  - "No CAD/visual; a before/after section diagram (A0 vs C2+D1 vs H1+M1) would show it in one picture."
  - "Size model over-states small pods (fixed plate/spine/heel adders)."
```
