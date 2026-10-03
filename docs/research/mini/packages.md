# mini/packages: component-level shrink (Phase 2 preliminary; lane = packages)

```yaml
id: MINI-PKG
date: 2026-10-03T01:00Z (UTC; owner-local 2026-10-02 evening)
status: preliminary research; NO board/schematic/placement/routing edits; nothing committed
scope: every placed part type on Rev F (hw/pod/gen.py, bom_jlc.csv, 30 BOM lines / 52 placed parts); J pads + TP dots out of scope (size.md SIZ-10)
guardrails: memory/two-phase-redesign.md (Phase 2 only after owner review); spec §1 untouched; owner decisions listed as reversals-needing-her-call, never done
abbrev:
  cy: courtyard area mm2 (now = Rev F routed draft hw/pod/draft_r1/pod_r1_routed.kicad_pcb via pcbnew GetCourtyard; after = KiCad 10 std-lib courtyard where one exists, else body + same tight margin the draft uses)
  Ext/Bas: JLC Extended / Basic library; Standard PCBA charges $1.53 per BOM line either way (simplify/assembly.md §1.1)
  POFV: plated-over filled via (via-in-pad, epoxy/copper filled and capped)
  WLCSP: wafer-level chip-scale package (bare die + bumps)
  gmcrit: crystal critical transconductance 4*ESR*(2*pi*f)^2*(C0+CL)^2; must be <= ST Gmcritmax
  conf: [V]=verified src+date, [E]=estimate, [T]=TBD
baseline_cy: {F: 157.2, B: 82.6, total: 239.8, src: "pcbnew on pod_r1_routed.kicad_pcb (Rev F, 2026-10-02 20:23 local), run 2026-10-03T00:3xZ fenced 3G"}
```

## Sources (read 2026-10-03 UTC unless stated)

```yaml
S-DS13737: {doc: "ST DS13737 Rev 10 (Jul 2024) STM32U575xx", copy: "~/Desktop/ultrasonic-scratch/st_new/ds10.txt", used: ["§5.1.6 p.153 SMPS: COUT 2x2.2uF ±20% ESR<20mohm@3MHz rated>=10V; CIN 10uF ±20% ESR<10mohm rated>=10V; L 2.2uH ±20% ISAT>0.5A DCR<200mohm", "§6.4 p.318-319 WLCSP90 B01C: 90 balls 4.20x3.95 mm, e=0.40 staggered, A max 0.59", "LSE table: Gmcritmax 0.5/0.75/1.7/2.7 uA/V for LSEDRV 00/01/10/11", "Fig.13 WLCSP90_SMPS ballout p.94"]}
S-DS14217: {doc: "ST DS14217 Rev 5 (May 2025) STM32U535xx", url: "https://datasheet.lcsc.com/datasheet/pdf/186c971171a187f8d232668e0cb07dc0.pdf?productCode=C22456595", used: ["front page: 512 KB flash, 274 KB SRAM; WLCSP56 3.38x3.38; UFBGA64 5x5", "§6.3 p.271-273 WLCSP56 B0H4: 56 balls 0.40 pitch staggered, A max 0.59, Dpad 0.250, stencil 0.325/0.100", "§6.5 UFBGA64 A019: 5x5 e=0.50, A max 0.60, Dpad 0.280", "SRAM4 16 KB + LPBAM in Stop 2 (line ~1394-1400)", "SMPS L/COUT/CIN requirements identical to DS13737 (§5.1.6)", "Fig.15 WLCSP56_SMPS ballout p.90"]}
S-AN5373: {doc: "ST AN5373 Rev 7", copy: "~/Desktop/ultrasonic-scratch/st_new/an5373.txt", used: ["VDD 10uF typ (4.7uF min) + 100nF/pin; VDD11 2x2.2uF; 2.2uH ceramic coil; VDDA 100nF+1uF"]}
S-PINDATA: {repo: "https://github.com/STMicroelectronics/STM32_open_pin_data", commit: 7d1f1514ed5583ec5007ad91236b4e1d377295b1, files: [STM32U575OIYxQ, STM32U535NEYxQ, STM32U545NEYxQ, STM32U535JEYxQ, STM32U545JEYxQ, STM32U535CEUxQ, STM32U545CEUxQ, STM32U575CGUxQ, STM32U535REIxQ, STM32U545REIxQ], fetched: 2026-10-03T00:39Z raw.githubusercontent.com, stored: "scratchpad only (not added to tools/data; add + log in SOURCE.md only if a package change is adopted)"}
S-JLC-ASM: {url: "https://jlcpcb.com/capabilities/pcb-assembly-capabilities", read: 2026-10-03, undated page, used: ["Standard PCBA min package 0201 (Economic 0402)", "min IC pin spacing 0.35 mm Standard", "min BGA spacing 0.3 mm centre-to-centre Standard (Economic 0.5)", "01005 supported", "double-sided only in Standard"]}
S-JLC-PCB: {url: "https://jlcpcb.com/capabilities/pcb-capabilities", read: 2026-10-03, undated page, used: ["multilayer via 0.15 hole / 0.25 dia min; 0.10/0.20 only if board <= 1.0 mm and ENIG/OSP", "POFV epoxy or copper filled & capped, default on 6+ layers, holes 0.15-0.55", "blind/buried HDI 1-3 step, blind 0.075-0.15", "track/space 0.09/0.09, 3 mil OK in BGA fan-out", "BGA pad min 0.2, pad-to-trace >= 0.1 (0.09 multilayer)"]}
S-JLC-API: {tool: tools/jlc.py (JLC parts API), queried: "2026-10-03T00:40Z-00:54Z", note: "stock/price per row below carry this timestamp"}
S-TPS7A20: {doc: "TI SBVS338H (rev Jul 2024)", copy: "~/Desktop/ultrasonic-scratch/ds/tps7a20.txt", used: ["DQN 1x1 X2SON, YCK 0.616x0.616 DSBGA, YCJ 0.612", "COUT effective >= 0.47uF; CIN effective >= 0.47uF recommended"]}
S-FC12M: {doc: "Epson FC-12D/FC-12M sheet (CN)", copy: "~/Desktop/ultrasonic-scratch/ds/fc12m.txt", used: ["FC-12M 2.05x1.2 x 0.6 max; ESR 90k max; C0 1.3 pF typ (column order inferred)"]}
S-FC135: {doc: "Epson FC-135", copy: "~/Desktop/ultrasonic-scratch/ds/fc135.txt", used: ["CL 12.5, ESR 70k max, C0 1 pF typ"]}
S-TPD2EUSB30: {doc: "TI SLVSAC2G (rev Jun 2021)", used: ["DRT SOT-3 1.00x0.80 mm, D+/D- 0.7 pF typ, VRWM 5.5 V"]}
S-PE0201: {doc: "Yageo PE series sheet (LCSC copy of C3984865)", used: ["PE0201 50mohm-1ohm 0.60x0.31 mm"]}
S-HEIGHTS: tools/checks/part_heights.yaml (datasheets read 2026-10-02)
```

## Pin budget (MCU package candidates) [V S-PINDATA, run 2026-10-03T00:40Z]

```yaml
need: {GPIO_used: 24 + LSE 2 + NRST + BOOT0, src: integration-map.md §4/§8}
check: "every Rev F port pin present on the candidate WITH the same signal: PA8 TIM1_CH1, PA7 TIM1_CH1N, PA10 TIM1_CH3, PB15 TIM1_CH3N, PB3 ADF1_CCK0, PB4 ADF1_SDI0, PA11/PA12 USB DM/DP, PB13/PB14 I2C2, PA4 ADC4_IN, PA1/PA2/PA6 ADC1_IN, PA13/PA14 SWD, PA0 WKUP1, PB7 TIM4_CH2, PB6 USART1_TX, PB8 MDF1_CCK0, PB1 MDF1_SDI0, PC14/PC15 OSC32, PA5/PA15/PB5 GPIO"
result:
  STM32U575OIYxQ WLCSP90: {missing: none, io: 69, extra_supply_balls: [VDDUSB, VDDIO2, VREFBUF x2, 4th VDD], used_balls: 46/90, inner_used: 16}
  STM32U535NEYxQ WLCSP56: {missing: none, io: 39, extra_supply_balls: [4th VDD], used_balls: 44/56, inner_used: 20, note: "no UCPD peripheral; USB is USB_DRD_FS (not OTG_FS)"}
  STM32U545NEYxQ WLCSP56: {missing: none, same as U535 + crypto, JLC stock 0}
  STM32U535/545 JEYxQ WLCSP72: {missing: none, pitch 0.35 (KiCad lib name), JLC stock 0}
  STM32U535/545 REIxQ UFBGA64: {missing: none, io: 47, extra: [VDDUSB, 4th VDD], JLC stock 0}
  STM32U535/545 CEUxQ UFQFPN48: {missing: none, same 7x7 as today (stock fallback only, no area gain)}
consequence: "pin map, nets and firmware pin assignments carry over unchanged to every candidate [V]; on U535/545 the PB5 strap and the PB15 UCPD dead-battery pull-down (ECR-0013 S1/S2) become moot (R6 still holds GB_N low)"
inner_ball_rule: "0.40 mm staggered grid, 0.25 mm pads -> 0.15 mm gap between neighbours: no track (0.09+2x0.09=0.27) and no dog-bone via (triangle void 0.231 mm from ball centres vs 0.10+0.125+0.09=0.315 needed) => every used non-perimeter ball needs via-in-pad (POFV) [E geometry from S-DS13737/S-DS14217 + S-JLC-PCB]; UFBGA64 0.50 grid: void 0.354 >= 0.315 => dog-bone with 0.10/0.20 vias fits, no POFV [E]"
```

## Main table

Area = courtyard mm2 (see abbrev). Cost = per pod, part price qty 1 at JLC (S-JLC-API 2026-10-03T00:4xZ); feeder lines +/-$1.53 each.

| ref(s) | now | smallest viable | cy now/after mm2 | height max now/after mm | JLC status (2026-10-03) | risk added | owner? |
|---|---|---|---|---|---|---|---|
| U1 | STM32U575CIU6Q UFQFPN48 7x7 (ST Cortex-M33 MCU, SMPS pinout) | opt A STM32U575OIY6Q WLCSP90 4.20x3.95 (same die) | 65.6 / 22.8 (incl +2 0201 decaps) | 0.60 / 0.59 | C5271033 Ext 10 pcs $15.14 (+$6.21) | POFV on ~16 inner balls; 4-layer POFV availability/cost [T]; drop/flex on a worn 0.8 mm board, no hand rework; bare-die light sensitivity (opaque cover over U1) [E] | YES |
| U1 | same | opt B STM32U585OIY6Q WLCSP90 (U575 + crypto, spec D5 drop-in) | 65.6 / 22.8 | 0.60 / 0.59 | C5271032 Ext 6 pcs $9.85 (+$0.92) | as A; 6 in stock | YES |
| U1 | same | opt C STM32U535NEY6Q WLCSP56 3.38x3.38 | 65.6 / 16.1 | 0.60 / 0.59 | C22456595 Ext 87 pcs $8.03 (-$0.90) | as A but 44/56 balls used, 20 inner -> very dense, likely HDI blind vias or 6 L [E]; 512 KB/274 KB vs 2 MB/786 KB (FWSIM-R62 230 KB log ring); USB_DRD_FS driver + ROM DFU support on U535 [T AN2606]; spec D5 change | YES |
| U1 | same | opt D STM32U535REI6Q UFBGA64 5x5 e0.50 | 65.6 / 32.2 | 0.60 / 0.60 | C27035630 Ext **0 stock** $9.51 | dog-bone escape, no POFV [E]; memory/USB as C; stock 0 (global sourcing [T]) | YES |
| Y1 (+C11 C12) | Epson FC-135 Q13FC13500004 3.2x1.5, CL 12.5 pF, 70k (32.768 kHz crystal) | 1.6x1.0 7 pF: Micro Crystal CM9V-T1A or YXC X161032768KJD2SI; or Epson FC-12M 7 pF X1A0000610006 2.05x1.2 | 6.25 / 3.15 (1610) or 4.34 (2012) | 0.90 / ~0.5 [T] (1610), 0.60 [V S-FC12M] | C5341288 Ext 336 $0.65; C383845 Ext 5124 $0.53; C99009 Ext 48097 $0.21 (FC-135 C32346 is Basic) | gmcrit 2.16 -> 0.98-1.09 uA/V (better, see side finding F3); C11/C12 retune to ~8-10 pF C0G; Basic -> Ext (no fee change in Standard) | no |
| L1 | Murata DFE201610E-2R2M 2.0x1.6x1.0 (2.2 uH SMPS coil) | cjiang FTC201210S2R2MBCA 2.0x1.2 (135 mohm, Isat 2.7 A) or FTC201208S2R2MBCA 2.0x1.2x**0.8** (160 mohm) | 3.16 / 2.70 | 1.00 / 1.0 or 0.8 [T height from P/N, datasheet PDF unreadable] | C5832324 Ext 29832 $0.09; C5832315 Ext 674 $0.10 | second-source-brand coil near the mic (magnetostriction/noise D11 untested) [E]; 0603 (1608) 2.2 uH all fail DCR<200 mohm (best FTC160808S2R2MGCA 220 mohm; Murata DFE18SAN2R2 not stocked) -> 0603 NOT viable per DS13737 §5.1.6 [V] | no |
| R21 | 0.1 ohm 1206 Uni-Royal 1206W4F100LT5E (bridge low-side shunt, lift-to-disconnect hook) | 0402 0.1 ohm 1 % (0402WGF100LTCE 62.5 mW) or 0201 metal film Yageo PE0201FRF7W0R1L (100 mW, ±100 ppm) | 10.24 / 1.72 (0402) / 0.96 (0201) | 0.65 / ~0.40 / ~0.31 [E] | C270655 Ext 21777 $0.012; C3984865 Ext 39352 $0.10 | dissipation 0.1*0.315^2 = 9.9 mW peak << 62.5 mW [E]; shorter Kelvin stubs help LN-M03/LF-1; lift-by-hand harder (O15/O18 test hook); OUT-02 kept 1206 in Phase 1 by owner call | YES |
| R2 R3 R4 R5 R6 R8 R9 R10 R12 R13 R14 R15 R16 R18 R22 + RT1 | 0402 chip R / Murata NCP15XH103 0402 NTC | 0201 (e.g. Yageo RC0201 series, Murata NCP03XH103F05RL NTC same family/B) | 16x1.72=27.5 / 16x0.96=15.4 | 0.40 / ~0.26 [E] | all Ext, stock 5k-2.4M (e.g. C106225 10k, C102685 100k, C142018 2k2, C163490 5k1, C226514 33R, C102683 1k, C144007 1M, C98098 NTC) | 25 V / 50 mW ratings OK (worst R10 4.1 mW, R12 5 V) [E]; tombstoning / hand rework of 0201 hard; R4/R6 stay as parts (owner keep) only package changes | YES (repairability trade) |
| R1, R20 | 0402 (BOOT0 pull-down = DFU tack point; 0R rail link = lift-to-meter point) | 0201 possible electrically (0R 0201 jumper rated ~0.5 A [T]) | 3.44 / 1.92 | 0.40 / ~0.26 | Ext (C106227 0R, C106225 10k) | defeats the hand tack/lift test hooks (O18) | YES |
| C1 C2 C3 C6 C10 C13 C19 (100 nF), C11 C12 (15 pF C0G), C22 (10 nF), C8 C9 (2.2 uF VDD11) | 0402 | 0201: 100 nF 10 V X5R (GRM033R61A104KE15D), 15 pF C0G 50 V (GRM0335C1H150JA01D), 10 nF X7R 25 V (GRM033R71E103KE14D), 2.2 uF **10 V** X5R (GRM033R61A225ME47D) | 12x1.65=19.8 / 12x0.96=11.5 | 0.55-0.70 / ~0.33 [E] | C76934 Ext 849k; C85891 Ext 15k; C85930 Ext 514k; C319184 Ext 178k | 100 nF X5R vs X7R fine for decoupling [E]; C8/C9 0201 ESR<20 mohm@3 MHz unverified [T]; C11/C12 values change with Y1 | YES (repairability), else no |
| C5 (1 uF VDDA), C15 (4.7 uF 25 V charger IN), C16 (4.7 uF VBAT), C17 (1 uF VSYS / LDO IN), C18 (1 uF LDO OUT) | 0402 | **stay 0402** | 5x1.65 unchanged | - | - | 0201 1 uF is 6.3-10 V and loses roughly half at 3-4.5 V DC bias [E] -> C18/C17 below TPS7A20 0.47 uF effective min [V S-TPS7A20 rule]; C15 needs 25 V rating (TI 9.2.2.1, no 0201 4.7u/25V); C16 at 4.2 V | - |
| C4 (10 uF VDD bulk) | 0603 10 V | 0402 10 uF 10 V X5R (Murata GRM155R61A106ME11D) | 4.28 / 1.65 | 0.90 / ~0.55 [T] | C408132 Ext 591k $0.045 | effective C at 3 V ~4-5 uF vs AN5373 "10 uF typ, 4.7 min" [E]: borderline | no (check) |
| C7 (10 uF VDDSMPS), C21 (10 uF SYS) | 0603 | **stay 0603** | 2x4.28 unchanged | 0.90 | - | ST CIN 10 uF ±20 % ESR<10 mohm >=10 V [V]; TI SYS >= 10 uF at up to ~4.5 V: 0402 loses too much [E] | - |
| C14 (22 uF bridge reservoir) | 0603 6.3 V | 0402 22 uF 6.3 V (CL05A226MQ5QUNC / GRM155R60J226ME11D) | 4.28 / 1.65 | 1.00 / ~0.55-0.65 [T] | C105226 Ext 169k $0.21; C415703 Ext 194k $0.16 | effective C at 3 V drops ~30-40 % vs 0603 [E]; bridge droop at 315 mA peaks must be re-simulated (OUT-03/05/07 tie) | YES (OUT-07 link) |
| D4 | Hottech 1N5819WS SOD-323 (Schottky, reverse-dock block) | Nexperia PMEG3005EL SOD882 (DFN1006-2, 30 V 0.5 A Schottky) | 6.03 / 1.72 | 1.00 / 0.50 [E SOD882 class] | C282565 Ext 43359 $0.115 | IF 0.5 A vs ~0.19 A charge+system [E]; VF 0.5 V @0.5 A -> ~0.07 W in 1x0.6 mm [E]; 500 uA max leak @30 V irrelevant (charger IN reverse-blocking) [E] | no |
| U6 | TI TPD2E2U06DRL SOT-553 (2-ch ESD, D+/D-) | TI TPD2EUSB30DRT SOT 1.0x0.8 (2-ch ESD, 0.7 pF, 5.5 V VRWM) | 1.91 / 0.97 | 0.60 / [T] | C97502 Ext 6192 $0.59 (+$0.4) | small gain; clamp/surge rating to compare [T] | no |
| D5 | TI TPD1E10B06DPY X1SON 1.0x0.6 (VBUS ESD at J3) | 0201 Nexperia PESD5V0X1BCSF (DSN0603-2) | 0.58 / 0.27 | 0.50 / ~0.3 | C2443412 Ext 9905 (YL suffix lot) | gain 0.3 mm2 not worth: surge rating at the only exposed contact | **keep** |
| U4 | TI TPS7A2030PDQN X2SON-4 1x1 (3.0 V LDO) | TPS7A2030 YCK DSBGA-4 0.616x0.616, 0.35 mm pitch | 0.98 / 0.49 | 0.40 / [T] | C41589305 Ext 310 $0.33 | 0.35 mm pitch = JLC Standard limit [V S-JLC-ASM]; -P (active discharge) suffix on YCK code to confirm [T] | no |
| Q1 Q2 | Nexperia PMCXB290UE DFN1010B-6 (20 V N+P MOSFET pair, H-bridge leg) | **keep** (already the smallest complementary pair found; PMCXB900UEL same SOT1216 with worse RDSon) | 2x1.93 | 0.40 | C19654206 Ext 5000 | ECR-0004 land pattern stays | - |
| U3 | TI BQ25180YBGR DSBGA-8 1.6x0.9 (charger) | **keep** (already CSP) | 1.32 | 0.65 | C3682423 Ext 4808 | - | - |
| U2 | Knowles/Syntiant SPH0641LU4H-1 LGA-5 3.5x2.65 (ultrasonic PDM mic) | **fixed by function** (D13; only part with ultrasonic mode; port geometry, B face) | 12.57 | 1.08 | C2879853 Ext 958 | - | - |
| SW1 | C&K KMT022NGJLHS 3.0x2.6 (IP68 tact switch) | **fixed by function** (O16-7 IP68, lid plunger D3.2) | 7.74 | 0.65 | C221707 Ext 4884 | - | - |

## Totals [E]

```yaml
non_mcu_recommended_set: {items: [Y1 1610, L1 2012, R21 0402, 16 R/NTC 0201, 12 C 0201, C4 0402, D4 SOD882, U6 DRT], cy_saved: 40.4}
with_mcu:
  A/B U575|U585 WLCSP90: {cy_saved: 83.2, pct_of_239.8: 35}
  C U535 WLCSP56: {cy_saved: 89.9, pct: 38}
  D U535 UFBGA64: {cy_saved: 73.8, pct: 31}
board_equivalent: "at the 43 % courtyard density of the 2026-09-30 routed draft (size.md §3): 279 -> ~175-193 mm2 per face; the 28x12 Package-B board (336) has slack for the cell-limited 12 mm height, so the gain shows up as a shorter board / more wire-stowage length or as single-face-ish F placement, not as pod height (size.md: pod length is cell-set) [E]; WLCSP POFV fan-out may not reach 43 % density [T]"
height: "F-face max 1.00 (L1) -> 0.90 (C7 0603) with L1 0.8 mm + crystal + C4 0402; B-face max stays 1.08 (mic) [E]"
cost: "parts per pod: MCU A +$6.21 / B +$0.92 / C -$0.90 / D +$0.58; rest ~+$1 total; feeder lines ~0 (line swaps) +$1.53 per line split (e.g. R1 kept 0402 while R15/R16 go 0201); PCB: POFV and 0.10/0.20 vias add cost [T needs JLC quote]"
```

## Side findings (not package choices; route to the owning lanes)

```yaml
F1: {sev: compliance, what: "C8/C9 (VDD11 2.2 uF) are Samsung CL05A225MQ5NSNC 6.3 V (C12530); DS13737 Rev 10 §5.1.6 p.153 and DS14217 Rev 5 §5.1.6 both say COUT rated voltage >= 10 V", fix: "10 V part, same 0402 (CL05A225KP5NSNC C107369 Ext 876651) or 0201 (GRM033R61A225ME47D C319184)", src: [S-DS13737, gen.py assembly-cost audit note 'C8/C9 -> Basic C12530 (6.3 V on a 1.1 V rail)'], conf: V}
F2: {sev: margin, what: "Y1 FC-135 12.5 pF / 70k: gmcrit = 2.16 uA/V vs Gmcritmax 2.7 (LSEDRV=11): passes, ratio 1.25; C11/C12 15 pF give CL ~= 7.5 + stray 2-3 = ~10 pF < 12.5 -> runs ~+20-30 ppm fast [E]", fix: "7 pF crystal (gmcrit 0.76-1.09, ratio 2.5-3.5, could even run LSEDRV=10) with retuned C11/C12; or keep FC-135 and retune C11/C12 to ~18-20 pF", conf: "V numbers (S-DS13737, S-FC135), E for stray"}
F3: {sev: stock, what: "U575CIU6Q JLC stock 8 (2026-10-03T00:40Z); WLCSP90 U575 10, U585 6; U535 WLCSP56 87; U535 QFN48 75; all UFBGA64 0", note: "O21 accepts stock risk until freeze"}
F4: {sev: info, what: "U535/545 have no UCPD: ECR-0013 S1 (PB5 strap) / S2 (PB15 dead-battery pull-down holds N gate) rationale disappears; R6 keeps GB_N low regardless", src: S-PINDATA}
F5: {sev: info, what: "FWSIM-R62 plans a 230 KB charger-log RAM ring; U535/545 total SRAM 274 KB", src: "docs/sim/firmware-emulation.yaml FWSIM-R62; S-DS14217"}
F6: {sev: info, what: "no 0603-size 2.2 uH at JLC meets DCR < 200 mohm AND Isat > 0.5 A (2026-10-03 queries: MPH160809S 375 mohm, CMH160808B 240, MBKK1608 345, FTC160808S2R2MGCA 220, LQM18PZ 470)", src: S-JLC-API}
```

## Phase-1 guardrail record (small-package alternative per IC, so Phase 2 can swap without reopening logic)

```yaml
U1: [STM32U575OIY6Q WLCSP90 (same die, pins verified), STM32U585OIY6Q WLCSP90, STM32U535NEY6Q WLCSP56 (pins verified; memory/USB differ), STM32U535REI6Q UFBGA64]
U3: already DSBGA-8
U4: TPS7A2030 YCK DSBGA-4 (same die family, SBVS338H)
U6: TPD2EUSB30DRT
D4: PMEG3005EL SOD882
D5: PESD5V0X1BCSF 0201 (not recommended)
Q1/Q2: none smaller found
U2/SW1: fixed by function
```

## Integration-map cross-check (§10) for the recommended non-MCU set + MCU options

```yaml
functions_affected: "none removed; F2 (Y1 retune C11/C12, L1 part), F3/F4 (C14 if 0402; R21 package), F5 (D4 part), F10 (U6 part), F14 (R1/R20 only if owner allows 0201) keep their chains"
nets_changed: none (package/part swaps only; same nets, same drivers)
pins: "none for package swaps; MCU options keep every port pin (S-PINDATA run); WLCSP90 adds VDDUSB/VDDIO2/VREF+ balls -> tie to +3V0/VDDA + 100 nF; U535 frees PB5 strap need"
rails: "+3V0 bulk: C4 0402 lowers effective C (~4-5 uF) [E]; C14 0402 lowers bridge reservoir [E -> needs sim]; LDO caps unchanged; VDD11 caps to 10 V rating (F1)"
offboard: none (J pads, wire counts, dock, cell wiring untouched)
mechanical: "F max height 1.00 -> 0.90 if L1 0.8 mm; B unchanged (mic 1.08); WLCSP needs an opaque lid over U1 if translucent shell parts are used (commit e25f35f considered them) [E]; mic port, switch, clamp bands untouched"
firmware: "Y1 7 pF -> LSEDRV choice; MCU opt C/D -> USB_DRD_FS driver, ROM DFU table check, memory budget; opt A/B -> none"
depends_on: [JLC quote for 4-layer POFV / 0.10-0.20 vias (pcb-tech lane), fan-out trial for WLCSP (no autorouter), bridge droop sim for C14 (spice-sim), owner review of Phase 1]
conflicts_with: "owner keeps: R21 1206 (OUT-02 deferred to Phase 2), R4/R6, C14 22 uF value, test hooks R1/R20 (O15/O18) -> listed as needs-owner, not done"
```

## Reproduce

```yaml
courtyards: "source tools/env.sh; systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 <script: pcbnew.LoadBoard(pod_r1_routed.kicad_pcb); fp.GetCourtyard(F_CrtYd|B_CrtYd).Area()>"
pin_check: "parse STM32_open_pin_data XMLs at commit 7d1f151; port->signal regex table above"
jlc: "python3 tools/jlc.py <MPN|Cxxxx> (timestamps above)"
gmcrit: "4*ESR*(2*pi*32768)^2*(C0+CL)^2"
```
