"""Pod board, one per side: schematic source of truth (SKiDL 2.3, KiCad 10 mode).

    source tools/env.sh && python3 hw/pod/gen.py      # -> hw/pod/pod.net, hw/pod/bom_jlc.csv

Blocks (spec §4, §7, §9; parts and LCSC numbers from .pcba-workflow/sourcing-lock.csv, JLC stock
2026-09-30):
  MCU     STM32U575CIU6Q on its internal SMPS (D5, D11; pins from docs/research/A3-u575-plan.md §3)
  Mic     SPH0641LU4H-1 on the ADF: clock PB3, data PB4, powered from PA5 so Off really is off (D12)
  Bridge  2x PMCXB290UE complementary pairs on TIM1 CH1/CH1N/CH2/CH2N, 100k gate pulls (D6)
  Power   MCP73831 charger (45 mA) -> 105 mAh cell (with its own protection PCB) -> TPS7A2030 3.0 V LDO
  I/O     button PA0 (wake), battery sense PA4 (1M/1M, 2 uA), charge status PA10 (open-drain),
          VBUS sense PA1 (dock detect), SWD pads
Rev B (2026-09-30, audit fixes): MCP73832 instead of MCP73831 (NM-1), VBUS sense (PWR-05),
C4 10 uF 0603 (NM-7), R1 10k (NM-11), C20 at VBAT (NM-5).
Change this file, never the generated netlist.
"""
from __future__ import annotations

import builtins
import csv
import sys
from pathlib import Path

import skidl
from skidl import SKIDL, Net, Part, Pin, generate_netlist

NC = builtins.NC          # SKiDL 2.3 puts its no-connect net in builtins

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
skidl.set_default_tool(skidl.KICAD10)
skidl.lib_search_paths[skidl.KICAD10].append(str(REPO / "hw/lib/lcsc"))

R0402, C0402, C0603 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0603_1608Metric"
PAD = "TestPoint:TestPoint_Pad_D1.0mm"

# LCSC numbers (sourcing lock + dated lookups 2026-09-30); every placed part carries one.
LCSC = {
    "R33": "C25105", "R10k": "C25744", "R22k": "C25768", "R100k": "C25741", "R1M": "C26083",
    "C15p": "C1548", "C100n": "C1525", "C1u": "C52923", "C2u2": "C107369", "C4u7": "C23733",
    "C10u_0603": "C19702", "C22u_0603": "C59461",
}


def R(ref, value, key):
    r = Part("Device", "R", value=value, footprint=R0402, ref=ref, tag=ref)
    r.fields["LCSC"] = LCSC[key]
    return r


def C(ref, value, key, fp=C0402):
    c = Part("Device", "C", value=value, footprint=fp, ref=ref, tag=ref)
    c.fields["LCSC"] = LCSC[key]
    return c


def pad(ref, label):
    p = Part("Connector", "TestPoint", value=label, footprint=PAD, ref=ref, tag=ref)
    p.fields["DNP_BOM"] = "pad"      # copper only, nothing to place
    return p


def pmcxb290ue(ref):
    """Nexperia PMCXB290UE: 20 V complementary N/P pair, DFN1010B-6 (SOT1216), 1.1 x 1.0 mm.
    Pinning per the datasheet (30 May 2023) Table 2: TR1 = N, TR2 = P; pads 7/8 are the drains.
    FOOTPRINT TODO: EasyEDA's SOT1216 pads (0.16 x 0.20) are smaller than Nexperia's Fig. 32 land
    pattern; redraw before layout (B-parts-selection.md)."""
    q = Part(tool=SKIDL, name="PMCXB290UE", ref_prefix="Q", ref=ref, tag=ref,
             footprint="lcsc:SOT1216_L1.1-W1.0-P0.35-BL-EP",
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
    for ref in ("C8", "C9"):                                           # 2 x 2.2 uF on VDD11 (DS13737 Rev 8)
        c = C(ref, "2u2", "C2u2"); c[1] += vdd11; c[2] += gnd
    nrst = Net("NRST"); nrst += u1["NRST"]
    c = C("C10", "100n", "C100n"); c[1] += nrst; c[2] += gnd
    r = R("R1", "10k", "R10k"); r[1] += u1["PH3"]; r[2] += gnd         # BOOT0 low: boot from flash (10k as AN5373)
    c = C("C20", "100n", "C100n"); c[1] += v3; c[2] += gnd              # at VBAT (pin 1), AN5373: 100 nF VBAT-to-VDD
    # 32.768 kHz crystal, LSE high drive; never toggle PC13 (ES0499 2.2.1): left unconnected
    y1 = Part("lcsc", "Q13FC1350000400", value="32.768k", ref="Y1", tag="Y1")
    y1.fields["LCSC"] = "C32346"
    osc_in, osc_out = Net("LSE_IN"), Net("LSE_OUT")
    osc_in += u1["PC14"], y1[1]; osc_out += u1["PC15"], y1[2]
    for ref, n in (("C11", osc_in), ("C12", osc_out)):
        c = C(ref, "15p", "C15p"); c[1] += n; c[2] += gnd

    # ------------------------------------------------------------ microphone (ADF1)
    u2 = Part("Sensor_Audio", "SPH0641LU4H-1", ref="U2", tag="U2")
    u2.fields["LCSC"] = "C2879853"
    mic_vdd, mic_clk, mic_dat = Net("MIC_VDD"), Net("MIC_CLK"), Net("MIC_DATA")
    mic_vdd.drive = skidl.POWER                        # a GPIO is the supply here, on purpose
    mic_vdd += u1["PA5"], u2["VDD"]                    # ~1 mA from a GPIO; off in Off mode (D12)
    c = C("C13", "100n", "C100n"); c[1] += mic_vdd; c[2] += gnd        # X7R: no 0402 C0G at 100 nF
    r = R("R2", "33", "R33"); r[1] += u1["PB3"]; r[2] += mic_clk       # tames the 4 MHz clock edge
    mic_clk += u2["CLOCK"]
    mic_dat += u2["DATA"], u1["PB4"]
    gnd += u2["GND"], u2["SEL"]                        # SELECT tied (D13)

    # ------------------------------------------------------------ H-bridge (TIM1)
    outa, outb = Net("OUT_A"), Net("OUT_B")
    legs = (("Q1", outa, "PA8", "PA7", "R3", "R4", "GA"), ("Q2", outb, "PA9", "PB0", "R5", "R6", "GB"))
    for qref, out, p_pin, n_pin, rp, rn, g in legs:
        q = pmcxb290ue(qref)
        gp, gn = Net(f"{g}_P"), Net(f"{g}_N")
        gp += u1[p_pin], q["G_P"]                       # TIM1_CHx drives the P gate (polarity inverted)
        gn += u1[n_pin], q["G_N"]                       # TIM1_CHxN drives the N gate
        v3 += q["S_P"]; gnd += q["S_N"]
        out += q["D_P"], q["D_N"]
        r = R(rp, "100k", "R100k"); r[1] += gp; r[2] += v3     # P off at reset (TIM1 pins float)
        r = R(rn, "100k", "R100k"); r[1] += gn; r[2] += gnd    # N off at reset
    for dref, jref, out, lab in (("D1", "J1", outa, "XDCR_A"), ("D2", "J2", outb, "XDCR_B")):
        d = Part("lcsc", "PESD5V0S1BL,315", ref=dref, tag=dref); d.fields["LCSC"] = "C84374"
        d[1] += out; d[2] += gnd
        p = pad(jref, lab); p[1] += out
    c = C("C14", "22u", "C22u_0603", C0603); c[1] += v3; c[2] += gnd   # bridge current peaks

    # ------------------------------------------------------------ power
    j_vbus, j_gchg = pad("J3", "VBUS"), pad("J4", "GND_CHG")
    j_vbus[1] += vbus; j_gchg[1] += gnd
    d3 = Part("lcsc", "ESD9X5.0ST5G", ref="D3", tag="D3"); d3.fields["LCSC"] = "C87910"
    d3["C"] += vbus; d3["A"] += gnd
    # MCP73832: same die as the MCP73831 but an OPEN-DRAIN status output, so PA10 never sees the charger's
    # 5 V (DS13737 Table 93 note 6 forbids >VDD+0.3 V with the internal pull enabled). Same datasheet
    # DS20001984H, same pinout. JLC C38066, Extended, 7165 in stock 2026-09-30.
    u3 = Part("Battery_Management", "MCP73832-2-OT", ref="U3", tag="U3"); u3.fields["LCSC"] = "C38066"
    u3["V_{DD}"] += vbus; u3["V_{SS}"] += gnd; u3["V_{BAT}"] += vbat
    c = C("C15", "4u7", "C4u7"); c[1] += vbus; c[2] += gnd
    c = C("C16", "4u7", "C4u7"); c[1] += vbat; c[2] += gnd
    r = R("R7", "22k", "R22k"); r[1] += u3["PROG"]; r[2] += gnd        # 1000 V / 22k = 45 mA
    chg = Net("CHG_STAT"); chg += u3["STAT"], u1["PA10"]              # open-drain: low = charging
    r = R("R11", "100k", "R100k"); r[1] += chg; r[2] += v3              # external pull-up to 3.0 V
    # VBUS sense: tells firmware it is docked. Firmware then sleeps, so the system load drops below
    # the charger's termination current and charging can finish (audit PWR-05). 2.5 V at PA1 from 5 V.
    vbs = Net("VBUS_SENSE")
    r = R("R12", "100k", "R100k"); r[1] += vbus; r[2] += vbs
    r = R("R13", "100k", "R100k"); r[1] += vbs; r[2] += gnd
    vbs += u1["PA1"]
    j_bp, j_bn = pad("J5", "BAT+"), pad("J6", "BAT-")
    j_bp[1] += vbat; j_bn[1] += gnd
    u4 = Part("lcsc", "TPS7A2030PDQNR", ref="U4", tag="U4"); u4.fields["LCSC"] = "C5220164"
    u4["IN"] += vbat; u4["EN"] += vbat; u4["OUT"] += v3; gnd += u4["GND"], u4["EP"]
    c = C("C17", "1u", "C1u"); c[1] += vbat; c[2] += gnd
    c = C("C18", "1u", "C1u"); c[1] += v3; c[2] += gnd
    vs = Net("VBAT_SENSE")                                              # 1M/1M: 2 uA, 2.1 V max at PA4
    r = R("R8", "1M", "R1M"); r[1] += vbat; r[2] += vs
    r = R("R9", "1M", "R1M"); r[1] += vs; r[2] += gnd
    c = C("C19", "100n", "C100n"); c[1] += vs; c[2] += gnd              # holds the node for the ADC sample
    vs += u1["PA4"]

    # ------------------------------------------------------------ button, debug
    sw = Part("lcsc", "KXT321LHS", ref="SW1", tag="SW1"); sw.fields["LCSC"] = "C221821"
    btn = Net("BTN")
    sw[1] += v3; sw[2] += btn; btn += u1["PA0"]                         # WKUP1, active high
    r = R("R10", "100k", "R100k"); r[1] += btn; r[2] += gnd
    for ref, lab, n in (("TP1", "SWDIO", Net("SWDIO")), ("TP2", "SWCLK", Net("SWCLK")),
                        ("TP3", "NRST", nrst), ("TP4", "3V0", v3), ("TP5", "GND", gnd)):
        p = pad(ref, lab); p[1] += n
        if lab == "SWDIO":
            n += u1["PA13"]
        if lab == "SWCLK":
            n += u1["PA14"]
    # spare pins, left free on purpose (A3-u575-plan.md §3); PC13 stays static next to the crystal
    for pin in ("PC13", "PH0", "PH1", "PA2", "PA3", "PA6", "PB1", "PB13", "PB14", "PB15",
                "PA11", "PA12", "PA15", "PB5", "PB6", "PB7", "PB8"):
        u1[pin] += NC
    return u1


def bom():
    rows = {}
    for p in builtins.default_circuit.parts:
        if "DNP_BOM" in p.fields:
            continue
        key = (p.value, p.footprint, p.fields.get("LCSC", ""))
        rows.setdefault(key, []).append(p.ref)
    lock = {r["lcsc"]: r for r in csv.DictReader(open(REPO / ".pcba-workflow/sourcing-lock.csv"))}
    with open(HERE / "bom_jlc.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Qty", "In sourcing lock"])
        for (val, fp, lcsc), refs in sorted(rows.items(), key=lambda kv: kv[1][0]):
            w.writerow([val, ",".join(sorted(refs)), fp.split(":")[-1], lcsc, len(refs), "yes" if lcsc in lock else "dated lookup"])
    return len(rows), sum(len(v) for v in rows.values())


if __name__ == "__main__":
    build()
    skidl.ERC()
    generate_netlist(file_=str(HERE / "pod.net"))
    lines, n = bom()
    missing = [p.ref for p in builtins.default_circuit.parts if "DNP_BOM" not in p.fields and not p.fields.get("LCSC")]
    print(f"BOM: {lines} lines, {n} placed parts; missing LCSC: {missing or 'none'}")
