"""Pod board, one per side: schematic source of truth (SKiDL 2.3, KiCad 10 mode).

    source tools/env.sh && python3 hw/pod/gen.py      # -> hw/pod/pod.net, hw/pod/bom_jlc.csv
    (Rev G reference outputs; the CURRENT design is named in hw/current.yaml: Phase 2 = POD_PACKAGES=mz2 -> pod_mz2.net, bom_jlc_mz2.csv)

Blocks (spec §4, §7, §9; parts and LCSC numbers from .pcba-workflow/sourcing-lock.csv, JLC stock
2026-09-30):
  MCU     STM32U575CIU6Q on its internal SMPS (D5, D11; pins from docs/research/A3-u575-plan.md §3)
  Mic     SPH0641LU4H-1 on the ADF: clock PB3, data PB4, powered from PA5 so Off really is off (D12)
  Bridge  2x PMCXB290UE complementary pairs on TIM1 CH1/CH1N (PA8/PA7) and CH3/CH3N (PA10/PB15, Rev F), 100k gate pulls (D6)
  Power   BQ25180 I2C charger with power path -> Renata 175 mAh cell (own protection PCB) -> TPS7A2030 3.0 V LDO
  I/O     button PA0 (wake), battery sense PA4 (1M/1M, 2 uA), charger IRQ PA15 (internal pull-up), VBUS sense PA1
          (dock detect), SWD pads TP1-TP6, printf/MDF dots TP7-TP10
  (Blocks as of Rev F; the Rev A-F paragraphs below are the change history.)
Rev B (2026-09-30, audit fixes): MCP73832 instead of MCP73831 (NM-1), VBUS sense (PWR-05),
C4 10 uF 0603 (NM-7), R1 10k (NM-11), C20 at VBAT (NM-5).
Rev C (2026-09-30, owner O8): power-indicator LED in the pad housing, solid while on:
VBAT -> R14 2k2 -> J7 (LED+) ~wire~ LED ~wire~ J8 (LED-) -> PB7 (open-drain, TIM4_CH2).
~0.35-0.75 mA over the battery range; firmware holds it steady with a >20 kHz duty set from VSYS (sub-ui issue 7).
Rev D (2026-10-01, owner O12/O16): BQ25180 power-path charger (I2C PB13/PB14, /INT PA15, NTC on TS,
TS also on PA2 for the firmware's 20 C rule) replaces the MCP73832; the LDO and LED now run from VSYS;
magnetic USB dock contacts J3 VBUS / J4 GND / J10 D+ / J11 D- / J12 CC (Rd 5.1k in the pod, CC
readable on PA3 through 10k); D4 1N5819WS blocks reverse docking; U6 TPD2E2U06 ESD on D+/D-;
USB FS on PA11/PA12 for ROM DFU; IP68 switch C&K KMT022NGJLHS (1.6 N) with a 2.2k pull-down so the
contact sees >= 1 mA while pressed (KMT0 datasheet minimum); PA10 keeps R11 as a pull-up.
Rev E (2026-10-01, owner O9/O15: rev 1 is the prototype, so it carries its own test hooks):
R20 0R between the LDO and the 3V0 rail (lift it: meter in series, or a bench 3.0 V on TP4);
R21 0.1R 1206 low-side bridge shunt (lift it: bridge disconnected) sensed on PA6 = ADC1_IN11
through R22/C22 (1k/10n, 16 kHz), so the pod measures its own exciter's |Z| for the USB self-test;
test pad TP6 VSYS (the charger has no ADC; the other rails are covered by TP4, J pads and the
outer-face caps C8/C9; mic and bridge are checked over USB instead). Test pads TP1-TP6 are 0.7 mm
(hw/lib/pod.pretty, P50 pogo at 1.27 mm pitch); the hand-soldered J wire pads stay 1.0 mm.
Assembly-cost audit (2026-10-01, JLC parts API 23:20Z): C8/C9 2.2 uF -> Basic C12530 (6.3 V on a
1.1 V rail); shunt 0.33R 0603 Extended -> 0.1R 1206 Basic C25334; D1/D2 PESD5V0S1BL fitted DNP
(footprints kept): the bridge outputs only reach the sealed exciter, and the FET body diodes clamp
them to the rails with C14 behind. 14 -> 11 Extended part types.
Rev F (2026-10-02, Phase 1 "logical simplification" from docs/research/simplification-study.md, package B3 =
B on the owner-decision defaults; owner phases: Phase 1 logic, then her board review, then Phase 2 miniaturization):
- removed R11 (ROM loader pulls PA10 up itself, AN2606 Table 199; PA10 then reused as GB_P, ECR-0003), R17 (CHG_INT uses the PA15 internal
  pull-up; PB5 strapped to GND so the UCPD dead-battery 5.1k pull-down can't arm on PA15, ECR-0013 S1), R19 (CC
  sense; PA3 spare; ILIM policy by enumeration, Rd R18 + J12 stay), C20 (VBAT pin 1 shares the pin-48 100 nF placed
  <= 1.5 mm from both, PER-06), D1/D2 (DNP footprints, OUT-04).
- D3 (ESD9X5.0 on internal VBUS behind D4) replaced by D5 TPD1E10B06 (TI bidirectional 5.5 V working ESD) AT the
  exposed J3 DOCK_VBUS contact (triage Q31): strikes clamp where they land, D4 stays the reverse block.
- J4 (dock GND) and J6 (cell -) merged into one 1.0 x 2.0 mm GND pad J4, placed between J3 DOCK_VBUS and J5 VBAT
  (ASM-09: a solder bridge can no longer put the cell on an exposed contact).
- C15 (charger IN) 4.7 uF 10 V -> 25 V (TI SLUSE99C 9.2.2.1 recommends 25 V-rated caps on IN; ECR-0013 S3).
- debug/fallback dots (PER-12, O18): TP7 PB6 USART1_TX printf; TP8 PB8 MDF1_CCK0 + TP9 PB1 MDF1_SDI0 + TP10 MIC_DATA
  = hand-wire recovery to the MDF if the ADF mic-clock duty is bad (sub-audio-in issue 5).
- Q1/Q2 on the Nexperia Fig. 32 land pattern (ECR-0004, hw/lib/pod.pretty, docs/research/sot1216-footprint.md).
- bridge leg B moved from TIM1_CH2/CH2N (PA9/PB0) to TIM1_CH3/CH3N (PA10/PB15, AF1; ECR-0003): frees the jammed
  east-side escape; R5 (P pull-up) holds PA10 high for the ROM loader; PB15's UCPD dead-battery 5.1k pull-down holds
  the N gate OFF until firmware sets UCPD_DBDIS (ECR-0013 S2), a safe default.
- kept on purpose: R4/R6 N-gate pull-downs (triage Q19: robustness against firmware init bugs for a device whose
  firmware changes for years; the study's OUT-01 would drop them), TP6 VSYS (owner-accepted test pad), R22/C22 and
  C14 22 uF (OUT-03/OUT-05 depend on the OUT-07 clamp, an owner decision), R21 1206 (OUT-02 is size-only: Phase 2),
  R18 + J12 + 5-contact dock (PER-01D needs a keying sample, O21), LED on the pad board (PER-07 reverses O8).
Rev G (2026-10-02, owner O24 after the Phase-1 briefing): C8/C9 back to 10 V-rated 2.2 uF C107369 (ST DS13737 Rev 10
p.153: VDD11 COUT rated >= 10 V; the 2026-10-01 swap to 6.3 V C12530 saved an Extended type, but Standard PCBA charges
per BOM line either way); D6 TPD1E10B06 on CC at the exposed J12 contact (the last unprotected dock contact; same part
and BOM line as D5).
Change this file, never the generated netlist.
"""
from __future__ import annotations

import builtins
import os
import csv
import sys
from pathlib import Path

import skidl
from skidl import SKIDL, Net, Part, Pin, generate_netlist

NC = builtins.NC          # SKiDL 2.3 puts its no-connect net in builtins

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
skidl.set_default_tool(skidl.KICAD10)
# FIRST in the search path: SKiDL searches "." recursively and would otherwise pick up the stale copy
# in hw/pod/kicad-draft/lcsc.kicad_sym (found 2026-10-01).
skidl.lib_search_paths[skidl.KICAD10].insert(0, str(REPO / "hw/lib/lcsc"))

R0402, C0402, C0603 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0603_1608Metric"
R0201, C0201 = "Resistor_SMD:R_0201_0603Metric", "Capacitor_SMD:C_0201_0603Metric"

# Package set (Phase 2, owner O26; ECR-0018). Same circuit, smaller packages: env POD_PACKAGES=mz2 writes pod_mz2.net +
# bom_jlc_mz2.csv beside the Rev G files; the default stays Rev G until the Phase-2 board replaces the draft.
# Kept on purpose (docs/research/miniaturization-prelim.md MZ-2, mini/packages.md): R1/R20 0402 hand hooks (O18), C5/C15-C18
# 0402 (DC bias / 25 V), C4/C7/C14/C21 0603 (ST/TI bulk rules), C8/C9 0402 10 V (SMPS loop; 0201 ESR at 3 MHz unproven),
# L1 (ST DCR/ISAT rule), U1 QFN48, U6, D5/D6, U3, U4, Q1/Q2, U2, SW1. JLC parts API 2026-10-03T03:57Z (all in stock).
PACKAGES = os.environ.get("POD_PACKAGES", "mz2")   # k4: Phase-2 set only
MZ2 = {   # ref: (footprint, LCSC, value or None = keep)
    "R2": (R0201, "C473457", None),                                   # 33R 0201WMF330JTEE
    **{r: (R0201, "C270364", None) for r in ("R3", "R4", "R5", "R6", "R12", "R13")},   # 100k 0201WMF1003TEE
    **{r: (R0201, "C473482", None) for r in ("R8", "R9")},             # 1M 0201WMF1004TEE
    **{r: (R0201, "C473508", None) for r in ("R10", "R14")},           # 2k2 0201WMF2201TEE (R10 carries >= 1 mA: 2.2 mW of 50)
    **{r: (R0201, "C473048", None) for r in ("R15", "R16")},           # 10k 0201WMF1002TEE
    "R18": (R0201, "C270344", None),                                   # 5k1 0201WMF5101TEE (D6 now clamps the CC contact)
    "R22": (R0201, "C270365", None),                                   # 1k 0201WMF1001TEE
    "R23": (R0201, "C473482", None),                                   # 1M 0201WMF1004TEE: I_SENSE offset (OUT-1B, 2026-10-07)
    "U2": ("lcsc:Knowles_LGA-5_3.5x2.65mm_Port0.65", None, None),       # SAI-15D: port hole D0.65 at (0, 0.75), 0.2075 to pad 3; order press-fit
    "RT1": (R0201, "C98098", None),                                    # Murata NCP03XH103F05RL: same XH family/B as NCP15XH103
    "R21": (R0402, "C409058", "0.1"),                                  # Panasonic ERJ2BSFR10X 0402 current sense (OUT-02)
    **{c: (C0201, "C76934", None) for c in ("C1", "C2", "C3", "C6", "C10", "C13", "C19")},   # 100n 10 V X5R GRM033R61A104KE15D
    **{c: (C0201, "C161441", "8p2") for c in ("C11", "C12")},          # C0G GRM0335C1H8R2BA01D for the 7 pF crystal (CL = C/2 + ~3 pF)
    "C22": (C0201, "C85930", None),                                    # 10n X7R 25 V GRM033R71E103KE14D
    "D4": ("Diode_SMD:D_SOD-882", "C282565", "PMEG3005EL"),            # Nexperia 30 V 0.5 A Schottky DFN1006-2 (~0.07 W)
}


def apply_packages():
    """Swap footprints/LCSC/values to the Phase-2 set; nets untouched (logic frozen at Rev G)."""
    if PACKAGES != "mz2":
        return
    by_ref = {p.ref: p for p in builtins.default_circuit.parts}
    for ref, (fp, lcsc, val) in MZ2.items():
        if ref not in by_ref:                  # Phase-2-only parts (R23) are created directly
            continue
        p = by_ref[ref]
        p.footprint = fp
        if lcsc:
            p.fields["LCSC"] = lcsc
        if val:
            p.value = val
PAD = "TestPoint:TestPoint_Pad_D1.0mm"        # J wire pads (hand-soldered)
PAD_TP = "pod:TestPoint_Pad_D0.7mm"            # TP probe / pogo pads
PAD_DOT = "pod:TestDot_D0.5mm"                 # Rev F debug / fallback dots (tack a wire, touch a probe)
PAD_GND2 = "pod:WirePad_1.0x2.0mm"             # Rev F shared GND wire pad (dock GND + cell -)

# LCSC numbers (sourcing lock + dated lookups 2026-09-30); every placed part carries one.
LCSC = {
    "R33": "C25105", "R2k2": "C25879", "R10k": "C25744", "R22k": "C25768", "R100k": "C25741", "R1M": "C26083",
    "C15p": "C1548", "C100n": "C1525", "C1u": "C52923", "C4u7": "C23733",
    "C10u_0603": "C19702", "C10u_0402": "C315248",   # C315248 Samsung CL05A106MP5NUNC 10 uF 10 V X5R 0402 T 0.5 +-0.2 (Samsung spec sheet; JLC Extended, stock 390164, JLC API 2026-10-08)
    "C22u_0603": "C59461", "R5k1": "C25905",
    # Rev E, JLC parts API 2026-10-01T22:55Z
    "R0": "C17168", "R0R1_1206": "C25334", "R1k": "C11702", "C10n": "C15195",
    # Rev F, JLC parts API 2026-10-02T23:48-50Z
    "C4u7_25V": "C2858031", "ESD_VBUS": "C48260",
    # Rev G (O24), JLC parts API 2026-09-30 (sourcing-lock row C_VDD11): ST wants >= 10 V on VDD11
    "C2u2_10V": "C107369",
    # ECR-0022 B2B-gap thin MLCCs (Samsung 0201, T 0.30 +-0.09 = 0.39 max; Samsung spec sheets C318539/C318540, read + JLC API 2026-10-08, Extended)
    "C2u2_10V_0201": "C318539", "C1u_16V_0201": "C318540",
}


def R(ref, value, key, fp=R0402):
    r = Part("Device", "R", value=value, footprint=fp, ref=ref, tag=ref)
    r.fields["LCSC"] = LCSC[key]
    return r


def C(ref, value, key, fp=C0402):
    c = Part("Device", "C", value=value, footprint=fp, ref=ref, tag=ref)
    c.fields["LCSC"] = LCSC[key]
    return c


def pad(ref, label, fp=PAD):
    p = Part("Connector", "TestPoint", value=label, footprint=fp, ref=ref, tag=ref)
    p.fields["DNP_BOM"] = "pad"      # copper only, nothing to place
    return p


def pmcxb290ue(ref):
    """Nexperia PMCXB290UE: 20 V complementary N/P pair, DFN1010B-6 (SOT1216), 1.1 x 1.0 mm.
    Pinning per the datasheet (30 May 2023) Table 2: TR1 = N, TR2 = P; pads 7/8 are the drains.
    Footprint: Nexperia Fig. 32 land pattern, hw/lib/pod.pretty (ECR-0004, Rev F); EasyEDA's SOT1216 pads were too small."""
    q = Part(tool=SKIDL, name="PMCXB290UE", ref_prefix="Q", ref=ref, tag=ref,
             footprint="pod:Nexperia_SOT1216_DFN1010B-6",   # ECR-0004: Nexperia Fig. 32 land pattern
             pins=[Pin(num=1, name="S_N", func=Pin.types.PASSIVE), Pin(num=2, name="G_N", func=Pin.types.PASSIVE), Pin(num=3, name="D_P", func=Pin.types.PASSIVE),
                   Pin(num=4, name="S_P", func=Pin.types.PASSIVE), Pin(num=5, name="G_P", func=Pin.types.PASSIVE), Pin(num=6, name="D_N", func=Pin.types.PASSIVE),
                   Pin(num=7, name="D_N", func=Pin.types.PASSIVE), Pin(num=8, name="D_P", func=Pin.types.PASSIVE)])
    q.fields["LCSC"] = "C19654206"
    q.value = "PMCXB290UE"
    return q


def build():
    gnd, v3, vbat, vbus = Net("GND"), Net("+3V0"), Net("VBAT"), Net("VBUS")
    gnd.drive = skidl.POWER
    v3.drive = vbat.drive = vbus.drive = skidl.POWER

    # ------------------------------------------------------------ MCU + SMPS
    u1 = Part("MCU_ST_STM32U5", "STM32U575CIUxQ", ref="U1", tag="U1")
    u1.fields["LCSC"] = "C5271013"
    v3 += u1["VDD"], u1["VBAT"], u1["VDDA"], u1["VDDSMPS"]
    gnd += u1["VSS"], u1["VSSA"], u1["VSSSMPS"]
    for i, ref in enumerate(("C1", "C2", "C3")):                     # one 100 nF per VDD pin
        c = C(ref, "100n", "C100n"); c[1] += v3; c[2] += gnd
    c = C("C4", "10u", "C10u_0603", C0603); c[1] += v3; c[2] += gnd     # MCU bulk: AN5373 wants 10 uF typ, 4.7 min after DC bias
    c = C("C5", "1u", "C1u"); c[1] += v3; c[2] += gnd                  # VDDA
    c = C("C6", "100n", "C100n"); c[1] += v3; c[2] += gnd              # VDDA HF
    c = C("C7", "10u", "C10u_0603", C0603); c[1] += v3; c[2] += gnd    # VDDSMPS input (ST: 10 uF, >=10 V)
    vlx, vdd11 = Net("VLXSMPS"), Net("VDD11")
    vlx.drive = vdd11.drive = skidl.POWER             # driven by the MCU's own SMPS
    vlx += u1["VLXSMPS"]
    vdd11 += u1["VDD11"]
    l1 = Part("lcsc", "DFE201610E-2R2M=P2", value="2u2", ref="L1", tag="L1")
    l1.fields["LCSC"] = "C337891"
    l1[1] += vlx; l1[2] += vdd11
    for ref in ("C8", "C9"):                                           # 2 x 2.2 uF on VDD11: ESR < 20 mOhm @ 3 MHz, rated >= 10 V
        c = C(ref, "2u2 10V", "C2u2_10V") if ref == "C8" else C(ref, "2u2 10V", "C2u2_10V_0201", C0201)   # C9 on P's inner face: 0201 0.39 max (ECR-0022 gap)
        c[1] += vdd11; c[2] += gnd   # (DS13737 Rev 10 p.153; Rev G, O24: was 6.3 V C12530)
    nrst = Net("NRST"); nrst += u1["NRST"]
    c = C("C10", "100n", "C100n"); c[1] += nrst; c[2] += gnd
    r = R("R1", "10k", "R10k"); r[1] += u1["PH3"]; r[2] += gnd         # BOOT0 low: boot from flash (10k as AN5373)
    # Rev F: no separate VBAT cap (was C20): VBAT (pin 1) shares the VDD pin-48 100 nF, placed <= 1.5 mm from both (PER-06)
    # 32.768 kHz crystal, LSE high drive; never toggle PC13 (ES0499 2.2.1): left unconnected
    if PACKAGES == "mz2":   # Epson FC-12M X1A0000610006: 2.05 x 1.2 mm, CL 7 pF, ESR 90k -> gmcrit ~0.98 uA/V (vs 2.16 for FC-135)
        y1 = Part("Device", "Crystal", value="32.768k 7pF", footprint="Crystal:Crystal_SMD_2012-2Pin_2.0x1.2mm", ref="Y1", tag="Y1")
        y1.fields["LCSC"] = "C99009"
        y1.fields["MPN"] = "X1A0000610006"   # generic Device:Crystal symbol: the MPN lives here (bom_check identity, 2026-10-07)
    else:
        y1 = Part("lcsc", "Q13FC1350000400", value="32.768k", ref="Y1", tag="Y1")
        y1.fields["LCSC"] = "C32346"
    osc_in, osc_out = Net("LSE_IN"), Net("LSE_OUT")
    osc_in += u1["PC14"], y1[1]; osc_out += u1["PC15"], y1[2]
    for ref, n in (("C11", osc_in), ("C12", osc_out)):
        c = C(ref, "15p", "C15p"); c[1] += n; c[2] += gnd

    # ------------------------------------------------------------ microphone (ADF1)
    u2 = Part("Sensor_Audio", "SPH0641LU4H-1", ref="U2", tag="U2",
              footprint="lcsc:Knowles_LGA-5_3.5x2.65mm_Port0.6")   # 0.6 mm port (stock is 0.5)
    u2.fields["LCSC"] = "C2879853"
    mic_vdd, mic_clk, mic_dat = Net("MIC_VDD"), Net("MIC_CLK"), Net("MIC_DATA")
    mic_vdd.drive = skidl.POWER                        # a GPIO is the supply here, on purpose
    mic_vddf = Net("MIC_VDDF")                         # K4 (2026-10-08): local RC filter at the mic; MIC_VDD (PA5 + BM28 pin 6) is the unfiltered side
    mic_vdd += u1["PA5"]                               # ~1 mA from a GPIO; off in Off mode (D12)
    r = R("R30", "33", "R33"); r[1] += mic_vdd; r[2] += mic_vddf       # 33R x 1.35 mA (params.yaml mic.r_load 2.2k @3 V) = 45 mV < 50 mV; corner 1/(2pi 33R ~70nF derated C13) = ~69 kHz, 3 MHz is 33 dB down
    mic_vddf += u2["VDD"]
    c = C("C13", "100n", "C100n"); c[1] += mic_vddf; c[2] += gnd       # X7R: no 0402 C0G at 100 nF
    r = R("R2", "33", "R33"); r[1] += u1["PB3"]; r[2] += mic_clk       # tames the 4 MHz clock edge
    mic_clk += u2["CLOCK"]
    mic_dat += u2["DATA"], u1["PB4"]
    gnd += u2["GND"], u2["SEL"]                        # SELECT tied (D13)

    # ------------------------------------------------------------ H-bridge (TIM1)
    outa, outb, brt = Net("OUT_A"), Net("OUT_B"), Net("BRIDGE_RTN")
    legs = (("Q1", outa, "PA8", "PA7", "R3", "R4", "GA"), ("Q2", outb, "PA10", "PB15", "R5", "R6", "GB"))   # Rev F: leg B on TIM1_CH3/CH3N (ECR-0003)
    for qref, out, p_pin, n_pin, rp, rn, g in legs:
        q = pmcxb290ue(qref)
        gp, gn = Net(f"{g}_P"), Net(f"{g}_N")
        gp += u1[p_pin], q["G_P"]                       # TIM1_CHx drives the P gate (polarity inverted)
        gn += u1[n_pin], q["G_N"]                       # TIM1_CHxN drives the N gate
        v3 += q["S_P"]; brt += q["S_N"]
        out += q["D_P"], q["D_N"]
        r = R(rp, "100k", "R100k"); r[1] += gp; r[2] += v3     # P off at reset (TIM1 pins float)
        r = R(rn, "100k", "R100k"); r[1] += gn; r[2] += gnd    # N off at reset
    for jref, out, lab in (("J1", outa, "XDCR_A"), ("J2", outb, "XDCR_B")):   # Rev F: D1/D2 DNP footprints removed (OUT-04)
        p = pad(jref, lab); p[1] += out
    c = C("C14", "22u", "C22u_0603", C0603); c[1] += v3; c[2] += gnd   # bridge current peaks
    # low-side shunt: 0.1R x ~315 mA peak (3.0 V into 8R + 1.2R of FETs) = 31 mV, ~170 counts on the
    # 14-bit ADC; 10 mW of 250 mW; ~1 % of the drive. Ground-referenced, so one ADC pin reads the
    # bridge SUPPLY current i*(2d-1), not the coil current: |Z| and phase sit in its 2f component (self-test sweep with
    # synchronous detection, open/short check; sub-output.md open issue 1). Rails check says ~326 mA peak (interfaces.py).
    r = R("R21", "0.1", "R0R1_1206", "Resistor_SMD:R_1206_3216Metric"); r[1] += brt; r[2] += gnd
    isns = Net("I_SENSE")
    r = R("R22", "1k", "R1k"); r[1] += brt; r[2] += isns
    c = C("C22", "10n", "C10n"); c[1] += isns; c[2] += gnd             # 16 kHz: passes 1.5-4 kHz tones, not the PWM
    isns += u1["PA6"]                                                   # ADC1_IN11
    # OUT-1 option (B), verified 2026-10-07 (sim/checks/selftest_lockin.py, R_OFF=1e6): +3.0 mV offset so the single-ended ADC
    # never clips the negative half of i*(2d-1) (min 2.7 mV); 3.0 uA from +3V0 always (+3V0 stays up in Off)
    if PACKAGES == "mz2":                                               # Phase-2 only: the Rev G reference stays frozen
        r = R("R23", "1M", "R1M"); r[1] += v3; r[2] += isns       # 1M: 3.0 mV offset, 3.0 uA (100k drew 29.7 uA, > the Off budget)

    # ------------------------------------------------------------ power + magnetic USB dock (Rev D)
    vsys, dock_vbus = Net("VSYS"), Net("DOCK_VBUS")
    vsys.drive = dock_vbus.drive = skidl.POWER
    p = pad("J3", "VBUS"); p[1] += dock_vbus
    p = pad("J4", "GND", PAD_GND2); p[1] += gnd                          # dock GND + cell -: sits between J3 and J5 (ASM-09)
    d5 = Part("lcsc", "TPD1E10B06DPYR", ref="D5", tag="D5", footprint="lcsc:X1SON-2_L1.0-W0.6-P0.65-BI-1")
    d5.fields["LCSC"] = LCSC["ESD_VBUS"]
    d5[1] += dock_vbus; d5[2] += gnd                                     # bidirectional 5.5 V working ESD at the exposed contact (Q31)
    d4 = Part("Device", "D_Schottky", value="1N5819WS", footprint="Diode_SMD:D_SOD-323", ref="D4", tag="D4")
    d4.fields["LCSC"] = "C191023"
    d4["A"] += dock_vbus; d4["K"] += vbus                               # upside-down docking can't feed the board
    # DK-17D (PA9 OTG VBUS sense via R24 1k from DOCK_VBUS): designed but NOT routable locally on the MZ-2 board
    # (2026-10-07: U1 bottom-row fan-out has no free lane for pin 30; docs/system/reg-board.md issue 22). Needs a full re-route.
    # BQ25180 (TI SLUSE99C): linear charger with power path. IN from the dock, SYS feeds the board,
    # BAT is the cell. Firmware sets ICHG 170 mA (code 44) at 20-45 C and 50 mA (code 32) below 20 C over I2C
    # (register plan: docs/system/sub-power.md).
    u3 = Part("lcsc", "BQ25180YBGR", ref="U3", tag="U3", footprint="lcsc:DSBGA-8_L1.6-W0.9-R2-C4-P0.40-BL")
    u3.fields["LCSC"] = "C3682423"
    u3["IN"] += vbus; u3["SYS"] += vsys; u3["BAT"] += vbat; u3["GND"] += gnd
    scl, sda, chg_int, ts = Net("I2C_SCL"), Net("I2C_SDA"), Net("CHG_INT"), Net("TS")
    scl += u3["SCL"], u1["PB13"]; sda += u3["SDA"], u1["PB14"]; chg_int += u3["/INT"], u1["PA15"]
    for rref, n in (("R15", scl), ("R16", sda)):                        # Rev F: CHG_INT uses the PA15 internal pull-up (R17 gone)
        r = R(rref, "10k", "R10k"); r[1] += n; r[2] += v3
    gnd += u1["PB5"]                                                     # strap: a high on PB5 would arm the UCPD 5.1k pull-down on PA15 (ECR-0013 S1)
    ts += u3["TS/MR"], u1["PA2"]                                         # firmware reads TS for the 20 C rule
    p = pad("J9", "NTC"); p[1] += ts                                    # 10k B3435 NTC taped to the cell, other lead to BAT-
    rt = Part("Device", "Thermistor_NTC", value="10k B3435", footprint=R0402, ref="RT1", tag="RT1")
    rt.fields["LCSC"] = "C77131"
    rt[1] += ts; rt[2] += gnd                                            # board NTC: DNP-able if the cell carries one
    c = C("C15", "4u7 25V", "C4u7_25V"); c[1] += vbus; c[2] += gnd     # USB attach limit <= 10 uF; 25 V per TI 9.2.2.1
    c = C("C16", "2u2 10V", "C2u2_10V_0201", C0201); c[1] += vbat; c[2] += gnd
    c = C("C21", "10u", "C10u_0402"); c[1] += vsys; c[2] += gnd  # TI: >= 10 uF on SYS; 0402 10 V (ECR-0022, lid ledge option B: 0603 0.9 -> 0402 0.70 max)
    # VBUS sense: firmware knows it is docked (DFU entry, charge mode). 2.5 V at PA1 from 5 V.
    vbs = Net("VBUS_SENSE")
    r = R("R12", "100k", "R100k"); r[1] += vbus; r[2] += vbs
    r = R("R13", "100k", "R100k"); r[1] += vbs; r[2] += gnd
    vbs += u1["PA1"]
    # USB full speed straight to the U575's FS PHY (internal pull-up); ESD at the contacts
    dp, dm = Net("USB_DP"), Net("USB_DM")
    for jref, lab, n in (("J10", "D+", dp), ("J11", "D-", dm)):      # K4/ECR-0019: J12 CC gone
        p = pad(jref, lab); p[1] += n
    u6 = Part("lcsc", "TPD2E2U06DRLR", ref="U6", tag="U6", footprint="lcsc:SOT-553-5_L1.6-W1.2-P0.50-LS1.6-TL-1")
    u6.fields["LCSC"] = "C1972959"
    u6["IO1"] += dp; u6["IO2"] += dm; u6["GND"] += gnd
    for pin in u6.get_pins("NC"):
        pin += NC
    dp += u1["PA12"]; dm += u1["PA11"]
    p = pad("J5", "BAT+"); p[1] += vbat                                 # cell - lands on the shared GND pad J4
    u4 = Part("lcsc", "TPS7A2030PDQNR", ref="U4", tag="U4"); u4.fields["LCSC"] = "C5220164"
    v3_ldo = Net("LDO_OUT")
    u4["IN"] += vsys; u4["EN"] += vsys; u4["OUT"] += v3_ldo; gnd += u4["GND"], u4["EP"]   # SYS <= 4.9 V < LDO 6 V max
    c = C("C17", "1u 16V", "C1u_16V_0201", C0201); c[1] += vsys; c[2] += gnd
    c = C("C18", "1u", "C1u"); c[1] += v3_ldo; c[2] += gnd           # stays at the LDO for stability
    r = R("R20", "0", "R0"); r[1] += v3_ldo; r[2] += v3                # lift: measure or inject the 3V0 rail
    vs = Net("VBAT_SENSE")                                              # 1M/1M: 2 uA, 2.1 V max at PA4
    r = R("R8", "1M", "R1M"); r[1] += vbat; r[2] += vs
    r = R("R9", "1M", "R1M"); r[1] += vs; r[2] += gnd
    c = C("C19", "100n", "C100n"); c[1] += vs; c[2] += gnd              # holds the node for the ADC sample
    vs += u1["PA4"]

    # ------------------------------------------------------------ button, debug
    # C&K KMT022NGJLHS: IP68, 1.6 N, 600k cycles. Pads 1-2 common and 3-4 common (datasheet layout).
    sw = Part("lcsc", "KMT022NGJLHS", ref="SW1", tag="SW1", footprint="lcsc:SW-SMD_4P-L3.0-W2.6-P1.85-LS3.4")
    sw.fields["LCSC"] = "C221707"
    btn = Net("BTN")
    v3 += sw[1], sw[2]; btn += sw[3], sw[4]; btn += u1["PA0"]          # WKUP1, active high
    r = R("R10", "2k2", "R2k2"); r[1] += btn; r[2] += gnd             # >= 1 mA through the contact when pressed
    # power-indicator LED, off-board in the pad housing (docs/research/pad-led.md). Fed from VSYS (R14):
    # a blue LED needs ~2.7 V, too close to the 3.0 V rail. PB7 is 5 V tolerant (FT, DS13737 Rev 8).
    led_a, led_k = Net("LED_A"), Net("LED_K")
    r = R("R14", "2k2", "R2k2"); r[1] += vsys; r[2] += led_a
    p = pad("J7", "LED+"); p[1] += led_a
    p = pad("J8", "LED-"); p[1] += led_k
    led_k += u1["PB7"]
    for ref, lab, n in (("TP1", "SWDIO", Net("SWDIO")), ("TP2", "SWCLK", Net("SWCLK")),
                        ("TP3", "NRST", nrst), ("TP4", "3V0", v3), ("TP5", "GND", gnd),
                        ("TP6", "VSYS", vsys)):
        p = pad(ref, lab, PAD_TP); p[1] += n
        if lab == "SWDIO":
            n += u1["PA13"]
        if lab == "SWCLK":
            n += u1["PA14"]
    # Rev F debug / fallback dots (PER-12, O18): printf on USART1_TX, and a hand-wire path to the MDF if the ADF
    # mic-clock duty is out of spec (lift R2, wire TP8 to R2's mic-side pad, TP9 to TP10; firmware moves to MDF1)
    for ref, lab, n, pin in (("TP7", "DBG_TX", Net("DBG_TX"), "PB6"), ("TP8", "MDF_CCK", Net("MDF_CCK"), "PB8"),
                             ("TP9", "MDF_SDI", Net("MDF_SDI"), "PB1")):
        p = pad(ref, lab, PAD_DOT); p[1] += n; n += u1[pin]
    p = pad("TP10", "MIC_DATA", PAD_DOT); p[1] += mic_dat
    # spare pins, left free on purpose; PC13 stays static next to the crystal (ES0499 2.2.1); PB15 carries the UCPD
    # PA3 freed in Rev F; PA9/PB0 freed when leg B moved to PA10/PB15 (ECR-0003)
    for pin in ("PC13", "PH0", "PH1", "PA3", "PA9", "PB0"):       # PA9: see DK-17D note above
        u1[pin] += NC
    return u1



# ============================================================ K4 two-board split (ECR-0020 rev 3, spec O33, V9 option B+)
# Rule (review of d2a70d9): no switching node crosses the B2B. VLXSMPS, L1, C8/C9 (VDD11), C7 (VDDSMPS) stay on U1's board.
# Rev 3 (2026-10-08, area re-balance): rev 2 put 51 parts on P and only the mic on M (P as long as one board). Now
#   P (upper, over the mic): U1 + crystal + L1/C8/C9/C7 (same board) + bridge Q1/Q2 + shunt + C14 + SWD/test pads + J1/J2 + I2C pull-ups.
#   M (lower, carries the mic): mic U2 + C13, BQ25180 charger U3, LDO U4, dock (D4/D5/U6, own gold pads J3/J4/J10/J11 + 2 magnets, k4-dock.yaml A),
#   button SW1 + R10, VBUS/VBAT sense dividers, NTC RT1/J9, LED feed R14/J7/J8, cell wire pads J5, TP6 VSYS.
# Crossing nets: +3V0 (LDO on M feeds P; C14/C4/C7 local on P), the 3 mic nets, I2C x2, CHG_INT, TS, VBUS_SENSE, VBAT_SENSE, USB D+/D-, BTN, LED_K.
# BM28 30 contacts: P carries the plug (DP), M the receptacle (DS), pin n to pin n [T].
BOARD_OF = {r: "M" for r in (
    "U2", "C13", "R30",                            # mic + its local supply filter (R30 + C13: K4 noise fix, ECR-0020 rev 5)
    "U3", "C15", "C16", "C21", "U4", "C17", "C18", "R20", "TP6",       # charger, LDO (LDO_OUT -> R20 -> +3V0), VSYS pad
    "D4", "D5", "U6", "J3", "J4", "J10", "J11",    # dock: reverse block, ESD, 4 gold pads (VBUS, GND, D+, D-)
    "R12", "R13", "R8", "R9", "C19",               # VBUS / VBAT sense dividers (analogue nodes cross as VBUS_SENSE / VBAT_SENSE)
    "RT1", "J9", "J5",                             # NTC, NTC pad, cell BAT+ wire pad (cell - lands on dock GND pad J4, ASM-09)
    "SW1", "R10",                                  # button (+3V0 from the LDO on M; BTN crosses)
    "R14", "J7", "J8",                             # LED feed (VSYS), LED wire pads; LED_K crosses to PB7
    "TP4", "TP5", "TP10", "R15", "R16")}           # 2026-10-08 unload P->M (ECR-0020 rev 4): +3V0/GND/MIC_DATA pads, I2C pull-ups (+3V0 is on M)
# Everything not listed is P.
BM28_PINS = {    # pin -> net. Footprint numbering: pads 1-15 one row, 16-30 the other; pad n faces pad 31-n; the 180-deg reversed mate pairs n <-> n+/-15 [V: footprint geometry].
    # K4-BM28-REV (2026-10-08): checkerboard. Signals only on odd pads 1-13 and 19-29, so every signal has GND on both row neighbours and across,
    # and a reversed mate always puts a signal against a GND (never supply-vs-GND, never supply into a GPIO). Supply pairs mate themselves: 15<->30 (+3V0/+3V0),
    # the 2 power contacts (tabs 31-34, 5 A, 30 mohm [T Hirose catalog]) are +3V0 too. GND/GND pairs: all remaining.
    1: "LED_K", 2: "GND", 3: "MIC_CLK", 4: "GND", 5: "MIC_VDD", 6: "GND", 7: "MIC_DATA", 8: "GND", 9: "CHG_INT", 10: "GND",
    11: "USB_DP", 12: "GND", 13: "USB_DM", 14: "GND", 15: "+3V0", 16: "GND", 17: "GND", 18: "GND", 19: "VBAT_SENSE", 20: "GND",
    21: "TS", 22: "GND", 23: "I2C_SCL", 24: "GND", 25: "I2C_SDA", 26: "GND", 27: "VBUS_SENSE", 28: "GND",
    29: "BTN", 30: "+3V0", 31: "+3V0", 32: "+3V0", 33: "+3V0", 34: "+3V0"}
# Current budget [V sim/checks/k4_checks: bridge peak 315 mA, mean < 0.1 A, charger/VSYS never crosses]: +3V0 on 2 signal contacts + 2 power contacts (5 A):
# worst contact 0.16 A at signal contacts if the tabs carried nothing, vs 0.3 A rating; GND return over 15 pins + shield. USB D+/D- and the MIC trio are GND-shielded both sides.
# Reversal (n <-> n+/-15): signal-GND x13, +3V0-+3V0 x2 (+4 tabs pairwise), GND-GND x15: no short, nothing driven into a GPIO.

# Placed-area estimate (V9 method): courtyard areas from hw/pod/draft_r2/out/routed.kicad_pcb (same mz2 package set), mm2.
CY = {"C_0201_0603Metric": 0.959, "R_0201_0603Metric": 0.959, "C_0402_1005Metric": 1.647, "R_0402_1005Metric": 1.72,
      "C_0603_1608Metric": 4.277, "D_SOD-882": 1.892, "X1SON-2_L1.0-W0.6-P0.65-BI-1": 0.584, "L0806": 3.164,
      "Nexperia_SOT1216_DFN1010B-6": 1.932, "SW-SMD_4P-L3.0-W2.6-P1.85-LS3.4": 7.744, "TestPoint_Pad_D0.7mm": 1.109,
      "TestDot_D0.5mm": 0.488, "TestPoint_Pad_D1.0mm": 3.105, "QFN-48-1EP_7x7mm_P0.5mm_EP5.6x5.6mm": 65.6,
      "Knowles_LGA-5_3.5x2.65mm_Port0.65": 12.569, "DSBGA-8_L1.6-W0.9-R2-C4-P0.40-BL": 1.317,
      "X2SON-4_L1.0-W1.0-P0.65-TL-EP": 0.98, "SOT-553-5_L1.6-W1.2-P0.50-LS1.6-TL-1": 1.914,
      "Crystal_SMD_2012-2Pin_2.0x1.2mm": 6.548, "WirePad_1.0x2.0mm": 3.71, "BM28B0.6-10DP_2-0.35V": 0,
      "BM28B0.6-30": 7.0 * 2.6}   # BM28 30-pin: ~7.0 x 2.6 mm courtyard [E; ECR-0020 'about 7 mm along the row']
DOCK_STRIP = 37.0   # M outer face: 4 gold pads on 2.0 pitch (8 x 2.4) + 2 magnet seats (2 x 3 x 3) [E, k4-dock.yaml option A; magnet size [T]]
ROUTING = 1.3
H = 12.0


def area(board):
    """courtyard sum, two-face L at H=12 (x1.3 routing) and the QFN-face bound for P."""
    tot, items = 0.0, []
    for p in builtins.default_circuit.parts:
        if "DNP_BOM" in p.fields and p.ref.startswith("TP") is False and p.ref not in ("J1", "J2", "J3", "J4", "J5", "J7", "J8", "J9", "J10", "J11"):
            continue
        fp = str(p.footprint).split(":")[-1]
        if p.ref in ("J3", "J4", "J10", "J11"):
            continue                                   # counted once in DOCK_STRIP
        a = CY.get(fp)
        if a is None and fp.startswith("BM28"):
            a = CY["BM28B0.6-30"]
        assert a is not None, (p.ref, fp)
        tot += a
        items.append((p.ref, a))
    if board == "M":
        tot += DOCK_STRIP
    placed = tot
    L2 = placed * ROUTING / (2 * H)
    return placed, L2


def board_of(ref):
    return BOARD_OF.get(ref, "P")


def b2b_part(ref, lcsc, mpn):
    pins = [Pin(num=n, name=f"{n}_{net}", func=Pin.types.PASSIVE) for n, net in sorted(BM28_PINS.items())]
    j = Part(tool=SKIDL, name="BM28_30", ref_prefix="J", ref=ref, tag=ref, pins=pins,
             footprint="lcsc:BM28B0.6-30DP_2-0.35V", value=mpn)    # footprint to be fetched at placement [T]
    j.fields["LCSC"] = lcsc
    return j


def crossing_nets():
    out = {}
    for n in builtins.default_circuit.nets:
        bs = {board_of(p.part.ref) for p in n.pins}
        if len(bs) > 1 and n.name not in ("NC", "__NOCONNECT") and not str(n.name).startswith("N$"):
            out[n.name] = n
    return out


def split(board):
    u1 = build(); apply_packages()
    cross = crossing_nets()
    pinnets = set(BM28_PINS.values())
    assert set(cross) == pinnets, ("B2B net list mismatch", sorted(set(cross) ^ pinnets))
    j = b2b_part("J20" if board == "M" else "J21", "C424571" if board == "M" else "C424570",
                 "BM28B0.6-30DS/2-0.35V(51)" if board == "M" else "BM28B0.6-30DP/2-0.35V(51)")
    for num, nname in BM28_PINS.items():
        j[num] += cross[nname]
    for p in list(builtins.default_circuit.parts):
        if p is not j and board_of(p.ref) != board:
            p.rmv_from_circuit() if hasattr(p, "rmv_from_circuit") else builtins.default_circuit.rmv_parts(p)
    return j


def bom(board):
    rows = {}
    for p in builtins.default_circuit.parts:
        if "DNP_BOM" in p.fields:
            continue
        rows.setdefault((p.value, p.footprint, p.fields.get("LCSC", "")), []).append(p.ref)
    lock = {r["lcsc"]: r for r in csv.DictReader(open(REPO / ".pcba-workflow/sourcing-lock.csv"))}
    with open(HERE / f"bom_jlc_{board}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Qty", "In sourcing lock"])
        for (val, fp, lcsc), refs in sorted(rows.items(), key=lambda kv: kv[1][0]):
            w.writerow([val, ",".join(sorted(refs)), str(fp).split(":")[-1], lcsc, len(refs), "yes" if lcsc in lock else "dated lookup"])
    return len(rows), sum(len(v) for v in rows.values())


if __name__ == "__main__":
    import sys
    boards = sys.argv[1:] or ["M", "P"]
    for b in boards[:1]:               # ONE board per process (SKiDL keeps global state); "python3 gen.py M" then "python3 gen.py P"
        split(b)
        skidl.ERC()
        generate_netlist(file_=str(HERE / f"pod_k4_{b}.net"))
        lines, n = bom(b)
        pa, L2 = area(b)
        print(f"BOARD {b}: courtyards {pa:.1f} mm2, x{ROUTING} two faces at H{H:g} -> L {L2:.1f} mm")
        print(f"BOARD {b}: BOM {lines} lines, {n} placed parts, B2B pins {len(BM28_PINS)}")
