# MINI-SKEPTIC: adversarial pass on miniaturization-prelim.md (workflow wf_b0caceb7-ce7, 2026-10-02 ~21:20 EDT)
# Status: preliminary research, owner review pending (Phase 2 starts after her Phase-1 board review)

```yaml
id: MINI-SKEPTIC
date: 2026-10-03T01:20Z (owner-local 2026-10-02 ~21:20 EDT)
scope: skeptic pass on /home/hrafnavalkyrja/Desktop/ultrasonic/docs/research/miniaturization-prelim.md (MINI-SYNTH) + docs/research/mini/*.md. I edited no files and committed nothing.
method:
  web: WebFetch hit its session limit, so I used curl and saved the pages to /tmp/claude-1000/-home-hrafnavalkyrja-Desktop-ultrasonic/759e00a7-254c-4cd3-926a-efbece430ab6/scratchpad/sk/. Read times 2026-10-03T01:14-01:16Z.
  jlc_api: tools/jlc.py at 01:16Z.
  st_pin_data: STM32U575OIYxQ.xml @7d1f151 fetched 01:16Z; parsed by scratchpad/sk/wl.py.
  size_budget: re-run fenced at 3G, 01:17Z.
tags: "[V] verified src+date | [E] estimate | [T] TBD"
top8_by_synth_rank: [MZM-01, MZM-02, MZM-03, MZM-08, MZM-04, MZM-05, MZM-06, MZM-09]

jlc_capability_claims_rechecked:   # every claim below was correct; nothing refuted
  - claim: "0.6 mm not offered for 4L/6L; 0.4 mm is ENIG-only and cannot be panelised"
    verdict: holds
    src: "cart.jlcpcb.com/quote tooltip, 01:15Z. Verbatim: '0.60 mm ... not available for 1-layer, 4-layer, or 6-layer PCBs'; '0.40 mm ... ENIG ... cannot be made with a panel'"
  - claim: "Standard PCBA needs a 70x70 single board or panel; Economic is 0.8-1.6 mm and single-sided; 0201 minimum; 0.35 mm IC pitch; 0.3 mm BGA pitch"
    verdict: holds
    src: "jlcpcb.com/capabilities/pcb-assembly-capabilities, 01:15Z"
  - claim: "Feeder fee $1.53 per BOM line, Basic or Extended, in Standard PCBA"
    verdict: holds
    src: "help/article/pcb-assembly-price (updated Sep 09 2026). Economic charges $3.07 per Extended line"
  - claim: "Small-via surcharge applies to today's 0.35/0.15 via rule"
    verdict: holds
    src: "pcb-capabilities L199: '0.1/0.15 mm hole any diameter, 0.2/0.25 hole with dia <0.45 cost more'; quote form: 'no additional charge when hole >=0.3 and dia >=0.4'"
  - claim: "POFV free on 6L+; 4L POFV is a paid option"
    verdict: holds ([T] on price)
    src: "6-layer-pcb page ('Via In Pad: Yes, free of charge'); help/article/pcb-via-covering, Sep 09 2026 ('complex process, high cost ... free for 6-layer and above')"
  - claim: "Rigid-flex not offered"
    verdict: holds
    src: "flex-pcb-capabilities: 'Rigid-flex PCBs are not yet supported'"
  - claim: "Castellation minimum hole 0.5 vs 0.6"
    verdict: conflict confirmed
    src: "pcb-capabilities 'Hole >=0.5'; help/article/what-is-castellated-holes '0.6 mm at least'"
  - claim: "HDI ordering may be gated per account (whitelist in quote JS)"
    verdict: weakened
    why: "the same JS whitelist array also lists countersink_hole and backdrill, which pcb-capabilities says 'are now available'. The list looks like feature-rollout flags; gating is unproven"
    src: "shop-cart-static/js/f5edecafb14c0371fb3d.js"
  - claim: "Recommended minimum spacing table"
    verdict: holds, and it is broader than the lanes used
    detail: "chip<->QFN 1.0, chip<->BGA 1.0, QFN<->QFN 1.0, QFN<->BGA 1.5, BGA<->BGA 2.0, chip<->SOT 0.2, 0201<->0201 0.15"
    src: "help/article/minimum-spacing-for-smd-components, updated Sep 09 2026, read 01:14Z ('recommended minimum')"

measures:
  MZM-01 (one-face board, SW1 alone on F in a lid pocket):
    verdict: WEAKENED
    holds:
      - "-570 mm3, T 10.40 mm, 12.20 mm off the temple: reproduced (size_budget y_fgap 0.30)"
      - "No logic change; mic on B, SW1 on F, both on the centre line (O16-5) [V]"
    against:
      - id: fit_margin_zero
        text: |
          The fit has no margin.
          - Back-solving area-model scenario c (29.9 mm at U0.60, 35.5 at U0.50) plus the synthesis adders (~+10 mm2) gives L ≈ 31.2 at U0.60, 32.2 at U0.58, ~34 at U0.55 [E].
          - The ≤32 mm figure also assumes R21 goes to 0402. That reverses her Phase-1 keep (MZD-4). With R21 kept at 1206 (+8.5 mm2), L ≈ 32.4 even at U0.60.
          - C4 0402 is still waiting on its DC-bias check (MZM-13).
          - So the recommended package's fit quietly depends on an owner reversal.
        src: "miniaturization-prelim.md L57; area-model.md L137; area_model.py solve_L"
      - id: jlc_spacing_not_modelled
        text: |
          The courtyards ignore JLC's recommended spacing.
          - Courtyards use KiCad c = 0.15-0.25. JLC recommends 1.0 mm chip<->QFN/BGA.
          - Haloing U1, U3, U2, Q1/Q2 and U4 (DFN/LGA/X2SON treated as QFN-class) adds ~15-54 mm2 → +2-8 mm on a one-face board at U0.60 [E].
          - Rev F already breaks this rule: the C1↔U1 courtyard overlap (reg-board.md L104).
          - Note: the ST SMPS loop wants its caps tight to U1, which pulls against the 1.0 mm rule.
        src: "jlc spacing page, 01:14Z"
      - id: u060_precedent_weak
        text: "The U 0.605 'best face' came from a board with 4 signal layers, no GND plane and a different netlist. U 0.60 is a judgement."
        src: "area-model.md L55-60, L189"
      - id: stowage_gate_soft
        text: |
          The "≤32 mm" stowage limit is a margin choice, not a hard fit.
          - By the synthesis's own numbers, L34 gives 147 mm3 against a need of 107-142.
          - The need depends on two unverified inputs:
            - slack: 10 mm assumed, against round-1 practice of ~35 mm (physical.md L117);
            - dock wire OD: 0.8 assumed, against the study gate of ≤0.35 (simplification-study.md L207).
          - The verdict can swing either way.
        src: "miniaturization-prelim.md L58"
      - id: lid_pocket_tolerance
        text: |
          The lid pocket has almost no clearance.
          - Pocket 0.4 + Fgap 0.30 = 0.70 mm against SW1 at 0.65 nominal, with no upper tolerance given (part_heights.yaml L118).
          - A 0.4 mm recess is at the resin limit: 'recesses under 0.4 mm may fuse' (physical.md L159).
          - The 3.3 mm pocket ignores the KMT0 J-lead pad span of 3.8 mm (pads at x ±1.50, 0.80 wide). The pocket or VHB cut-out needs ≥ ~4.1 x 2.9 [V].
        src: "hw/lib/lcsc/lcsc.pretty/SW-SMD_4P-L3.0-W2.6-P1.85-LS3.4.kicad_mod L16-19"
      - id: press_still_in_tension
        text: |
          The claim that full-face VHB 'removes SW1-press-in-tension risk' is wrong.
          - SW1 on F is pressed inward, so the F-face bond still takes tension.
          - Full-face VHB spreads the load; it does not remove it. The back-stop is still needed (area_model.py keeps the 7.8 mm2 K_B).
          - Not listed: full-face VHB makes removing or reworking the board a destructive peel (O19 serviceability).
        src: "simplification-study.md L316"
      - id: d11_placement_wording
        text: |
          Spec D11 says the SMPS caps go 'at the MCU, away from the mic and on the far side of the board from it'. MZM-01 puts the SMPS loop on the mic's face.
          - Above f_c ≈ 955 kHz, In1 screens cross-side pairs; the SMPS runs at ~3 MHz. Same-face placement loses that.
          - MZM-01 does not cite D11. The owner should read it.
        src: "spec.md L214; layout-noise.yaml L95, L147"
      - id: o13_letter_only
        text: "O13 ('board stays double-sided') holds in letter only: SW1 is the one F part."
  MZM-02 (cap F-face parts at 0.65 mm, two-face kept):
    verdict: HOLDS on volume, WEAKENED on electronics
    holds:
      - "-210 mm3: reproduced (6619 mm3)"
    against:
      - id: contradicts_MZG05
        text: |
          MZM-02 breaks the synthesis's own guardrail.
          - It moves L1 and C7 to B while U1 stays on F.
          - That violates MZG-05 (SMPS loop on U1's face) and ST AN5373's same-side tight loop.
          - Moving Y1 to B puts the LSE crystal through vias away from PC14/PC15.
        src: "miniaturization-prelim.md L195 vs L63-67"
      - id: no_move_variant_inductor
        text: |
          The no-move variant's inductor is unproven.
          - cjiang FTC201208S2R2MBCA (2.2 µH molded inductor, 2.0x1.2x0.8 mm, 160 mΩ, Isat 2.2 A, C5832315): Extended, 674 in stock, $0.0969 [V JLC 01:16Z]. It passes ST's DCR/ISAT rule on paper.
          - D11 asks for 'shielded, low-magnetostriction'. That is unverified, and stock is thin.
  MZM-03 (dock FPC tail):
    verdict: HOLDS as an owner-gated option
    notes:
      - "-94 mm3 rests on an invented dock row (tail 0.5 vs 0.85) [E] (architecture.md L57). It cannot be checked without the target sample, which O21 blocks."
      - "Confirmed that the study rejected ASM-12 only for colliding with SIZ-06 (simplification-study.md L322)."
  MZM-08 (0201 for the vetted non-bulk set):
    verdict: HOLDS, two weak spots
    holds:
      - "0201 is in Standard PCBA; 0201-0201 spacing 0.15; fee-neutral ($1.53 per line) [V]"
      - "GRM033R61A225ME47D (Murata 2.2 µF 0201 MLCC) is 10 V X5R, 178210 in stock [V JLC 01:16Z]"
    against:
      - id: R18_exposed
        text: |
          R18 should stay 0402 [E].
          - R18 (5k1 Rd) sits directly on J12 CC, an exposed dock contact with no ESD part. Only D5 (VBUS) and U6 (D+/D-) protect contacts (integration-map F15).
          - The packages lane kept D5 at 0402-class for 'surge margin at the only exposed contact', then moved R18 to 0201. That is inconsistent.
      - id: C13_derating
        text: "C13 (mic supply filter) in 0201 10 V X5R derates more at 3 V than the ~90 nF the noise path assumes (layout-noise.yaml L93). LN-M01 needs a re-run."
      - id: COUT_option_missed
        text: "Missed: ST also allows COUT = a single 4.7 µF (ds10.txt L18628, ESR <20 mΩ, ≥10 V). That is one part instead of C8+C9."
  MZM-04 (6-layer board at 0.8 mm):
    verdict: WEAKENED
    against:
      - id: third_jlc_source
        text: |
          A third JLC source points to 1.0 mm or more.
          - jlcpcb.com/impedance (read 01:15Z) lists 6-layer controlled stack-ups only at 1.2/1.6/2.0 mm (4-layer starts at 0.8).
          - The 6-layer page's FAQ says 1.0-2.0 mm.
          - Only that page's own table lists 0.8.
      - id: thickness_cost
        text: |
          Volume cost if 6L forces a thicker board (my runs 01:17Z):
          - at 1.0 mm: Package B 6949, MZ-2 6379 mm3;
          - at 1.2 mm: MZ-2 6499 mm3.
      - id: area_unsupported
        text: "The '-24..-48 mm2 per face' gain has no source [E]."
  MZM-05 (4-layer + paid POFV at U1 and U3):
    verdict: PARTLY REFUTED
    refuted:
      - claim: "POFV at U3 inner balls; removes today's U3 ball-escape failures (2 of 7 unrouted)"
        src: "pcb-tech.md L41, L111"
        why: |
          - U3 (BQ25180 DSBGA-8) is a 2x4 grid, balls A1-D2: every ball is on the perimeter (integration-map §3; reg-board.md L141 'every ball escapes outward').
          - 'VSYS B2 / VBUS A2 unrouted' is the Rev E draft of 2026-10-01 (git show 7c17d3e^:docs/system/reg-board.md L116). It was fixed by cap order (ECR-0002 item 2).
          - Rev F's summary.json has 2 unconnected (SWCLK, LED_K), none at U3.
    holds:
      - "POFV in U1's exposed pad: the 9 unfilled 0.15 mm vias wick solder, and ink plugging is not allowed in pads (via-covering page) [V]. This is a solder-quality fix, not a size measure (MZ-1's 28x12 has area slack)."
  MZM-06 (WLCSP90 MCU, STM32U575OIY6QTR):
    verdict: HOLDS on facts, with corrections; owner-gated
    verified:
      - "C5271033 STM32U575OIY6QTR (ST Cortex-M33 MCU, same die, WLCSP-90): 10 pcs, $15.1398 [V JLC 01:16Z]"
      - "Every Rev F port/signal is present: TIM1_CH1/1N/3/3N, ADF1_CCK0/SDI0, USB_OTG_FS_DM/DP, I2C2, ADC4, MDF1, OSC32, PH3-BOOT0 [V pin data]"
      - "All 6 nearest neighbours are at 0.400 mm, so no track or dog-bone fits between balls; every used inner ball needs a via in its pad [V]"
      - "ST Dpad 0.225, Dsm 0.290 (ds10.txt Table 158) [V]"
    corrections:
      - "Used balls 48 (incl. VREF+ H16, MonoIO), of which 25 are inner (20 signal incl. the PB5 strap, 4 VSS/VSSSMPS, VREF+). pcb-tech's 48/25 is right; packages.md L43/L59 ('46 used / 16 inner') undercounts."
      - "Supply balls added vs QFN48: 4 (4th VDD, VDDUSB, VDDIO2, VREF+), not 3. pin-contract.yaml power_pins needs VDDUSB/VDDIO2, and VREF+ needs a contract entry."
      - "Black mask (O23): JLC minimum pad spacing 0.13 mm for black/white. ST's Dsm 0.29 leaves a 0.11 mm web, so use 1:1 LDI mask or a gang opening."
      - "Spec D5 names the QFN-48 package, so WLCSP is a D5 change. The synthesis flags D5 only for U535."
  MZM-09 (R21 shunt 1206 → 0402):
    verdict: HOLDS as an owner reversal
    notes:
      - "ERJ2BSFR10X (Panasonic 0.1 Ω current-sense, 0402): 166 mW, 15928 in stock, $0.0732 [V JLC 01:16Z]. More margin than the cited 62.5 mW."
      - "Not disclosed at package level: MZ-2's ≤32 mm board length assumes this reversal."

packages:
  MZ-1 (conservative: Package B + clean-ups):
    verdict: HOLDS
    notes:
      - "6829 mm3 reproduced. 28x12 vs an area lower bound of 24.8-25.4 mm at U0.50."
      - "JLC's 1.0 mm spacing could eat ~2 of the ~3 mm margin [E]."
      - "The 'POFV at U3' member is moot (see MZM-05)."
      - "Its cross-check says conflicts_with: none, but omits that SIZ-06 spends the O16(3) USB-C fallback (simplification-study.md L371 IB-13). That is pending her Package-B review, but it should be listed."
  MZ-2 (balanced, recommended):
    verdict: WEAKENED
    why: |
      - Board ≤32 mm needs U ≥0.60 and R21 at 0402 (her keep) and C4 at 0402 (unproven).
      - JLC's 1.0 mm spacing is not modelled.
      - The D11 'far side of the board' wording conflicts.
      - The pocket depth has no tolerance.
      - Recommend only with MZV-02 re-specified to include JLC spacing and R21 kept at 1206 as the base case.
  MZ-2b (two-face, F parts ≤0.65 mm):
    verdict: HOLDS on volume (6619 mm3), WEAKENED
    why: "It breaks MZG-05."
  MZ-3 (aggressive: one-face + WLCSP + FPC tail):
    verdict: WEAKENED, near-refuted on volume
    why: |
      - Its -86 mm3 edge over MZ-2 needs a 6-layer board at 0.8 mm.
      - On 6L at 1.0 mm MZ-3 = 6291 mm3, larger than MZ-2 on 4L at 0.8 (6259). At 1.2 mm it is 6410 (my run 01:17Z).
      - Only HDI keeps it at 0.8 mm, and MZR-08 rejects HDI for rev 1.
      - Area-model scenario d assumes '0.2/0.1 vias' with via-in-pad, but POFV covers only 0.15-0.55 mm (pcb-capabilities L347).

owner_decisions_check:
  - "O8 (LED in the pad), the 5-contact dock and R4/R6 are touched only as options (MZM-17, MZD-9)."
  - "Silent dependencies on reversals:"
  - "  R21 1206 keep: needed for MZ-2's board length."
  - "  O16(3) USB-C fallback: omitted from MZ-1/MZ-2's conflicts_with."
  - "  Spec D5 (MCU package) and D11 (SMPS placement wording): not cited for MZM-06 and MZM-01."
```

# OWNER BRIEF (synthesizer, layperson)

The battery decides the pod's length and height (35 x 12 x 5.3 mm cell), so making the board smaller in area saves almost no pod volume. What can still shrink is how far the pod sticks out from your temple: every 0.1 mm thinner removes 60 mm³.
Step 1 is Package B, which you're already reviewing: a 28 x 12 board hung from the lid, a thinner lid and the dock tails bent flat. That takes the pod from 7.80 to 6.83 cm³ (-12.5 %) and from 13.6 to 13.15 mm off the temple.
The biggest new idea is to put every part on the battery side of the board and leave only the button on the lid side, sitting in a 0.4 mm pocket in the lid. That saves another 570 mm³ (6.26 cm³) and makes the pod 0.95 mm thinner (12.2 mm off the temple), and the circuit doesn't change at all.
That layout has side benefits: the core power loop stays on one side, the lid glues flat to the board, a tape ring seals the mic port, and every part is visible when the lid comes off.
The catch is crowding: that one side only fits with 0201-size resistors and capacitors (half the size of today's 0402s and much harder to fix by hand). The board must also stay 32 mm long or less so the 12 wires keep room for their slack. A computer placement trial decides whether it fits before anything is committed.
If it doesn't fit, the fallback moves only the tall parts (coil, crystal, two capacitors) off the lid side, for -0.35 mm and -210 mm³.
The same MCU comes in a tiny bare-silicon ball package (4.2 x 4.0 mm instead of 7 x 7). It saves 28-45 mm² of board but no thickness, can't be hand-repaired or probed, needs filled vias, costs about $6 more per pod, and JLC has only 10. My advice is to keep today's MCU package.
The board itself can't get thinner: JLC's order form offers no 4- or 6-layer board below 0.8 mm (checked today). JLC doesn't make rigid-flex boards, and a flex strip up the arm would wear out from the constant flexing.
A flat flex strip for the dock would replace the 5 loose dock wires and save another 94 mm³. It's a custom part and needs a dock sample first (your O16 and O21 decisions), so it's not in my recommendation.
I recommend the "Balanced" package: everything on the battery side, today's MCU, 0201 parts except the hand-test points, and a 6-layer board if JLC quotes it at 0.8 mm. That's about 6.26 cm³ and 10.4 mm thick, against 7.80 cm³ and 11.8 mm today.
Your calls: the one-side layout, 0201 parts, the shunt resistor change from 1206 to 0402 that you deferred, the MCU package, and 6 layers (that needs a free JLC quote with your login; a quote is not an order). The LED in the pad, the 5-contact dock and R4/R6 stay as you decided.
Found on the way, for your Rev F review: two capacitors on the MCU core supply (C8/C9) are 6.3 V parts where ST requires at least 10 V; the fix is a same-size swap. Nothing was edited or committed; full notes are in /home/hrafnavalkyrja/Desktop/ultrasonic/docs/research/miniaturization-prelim.md
