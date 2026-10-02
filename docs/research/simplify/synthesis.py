#!/usr/bin/env python3
"""Synthesis of the 2026-10-02 simplification study: ranking, package arithmetic, diagram data.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 docs/research/simplify/synthesis.py            # prints the markdown tables, writes synthesis.json

Single source of truth for every number in docs/research/simplification-study.md and
docs/diagrams/simplification.svg (make_diagram.py reads synthesis.json).

Inputs are the four domain studies after their skeptic verdicts plus the integration ledgers. Nothing here is measured on
hardware. Part counts come from set arithmetic on hw/pod/bom_jlc.csv (56 placements, 29 lines) and the block map in
docs/system/integration-map.md section 2; Basic/Extended classes come from the JLC parts API (2026-10-02T22:51Z);
pod volume and mass come from sim/checks/size_budget.py (calibrated on hw/mech/shell_r1.py).

Scoring (the owner's rule, spec O19/O20: reliability and size first, money last):
    pts = 3*P + 2*W + 4*F + area_saved/5 + vol_saved/40 + r + 2*c + 2*d - 2*h - 1*g
    P placements removed (system-wide)      W hand-solder joints removed         F fragile/hidden-joint packages retired
    area_saved courtyard mm2 removed        vol_saved pod/pad volume mm3 removed r extra reliability, -3..+4 (judgement)
    c convenience in daily use, -2..+2      d diagnosability, -2..+2             h 1 if a wrong guess is hardware-only
    g number of owner/sample/bench gates the item needs
Money does not appear in the formula on purpose: at quantity 2 it is reported, never weighed.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("synthesis.json")
FEE_LINE = 1.53          # JLC Standard PCBA feeder loading per BOM line, Basic or Extended (fee page of 2026-09-09, read 2026-10-02)
BOARDS = 4               # assembled boards per order (2 panels of 2): 2 to wear + 2 spares

# ---------------------------------------------------------------------------------------------------------- opportunities
# id, short name, kind, packages, P, E, usd_pod, lines, area, vol, power, risk, W, F, r, c, d, h, g, decisions, relations
# P/E/lines: positive = removed; usd_pod/area/vol: negative = saved.  risk: FW firmware-fixable, HW hardware-only.
O = []


def o(id, name, kind, pkgs, P, E, usd, lines, area, vol, power, risk, W, F, r, c, d, h, g, dec, rel, note=""):
    O.append(dict(id=id, name=name, kind=kind, pkgs=pkgs, P=P, E=E, usd_pod=usd, lines=lines, area=area, vol=vol, power=power,
                  risk=risk, W=W, F=F, r=r, c=c, d=d, h=h, g=g, dec=dec, rel=rel, note=note))


# --- electrical cuts and enablers
o("OUT-01", "Drop N-gate pull-downs R4, R6 (P pull-ups R3/R5 stay)", "cut", "BCD", 2, 0, -0.005, 0, -3.44, 0, "-0.03 mA",
  "FW: init order", 0, 0, 0, 0, 0, 0, 1, "D6 wording", "PROC-OUT OUT-BOARD COST-BOARD PROC-DEBUG PWR-OUT-RAIL")
o("OUT-02", "R21 shunt 1206 -> 0402 (Panasonic ERJ2BSFR10X, 0.1 ohm current-sense; no Basic 0402 0.1 ohm exists)", "cut", "ABCD", 0, -1, +0.068, 0, -8.52, 0, "0",
  "benign (calibrate the impedance gain)", 0, 0, 1, 0, 1, 0, 0, "O13 Ext. count", "OUT-DEBUG OUT-BOARD COST-BOARD PROC-OUT")
o("OUT-03", "F4 by synchronous R21 sampling (TRGO2); drop C22 and offset R", "cut", "BCD", 1, 0, -0.005, 1, -1.65, 0, "0",
  "FW: sample instant", 0, 0, 0, 0, 2, 0, 1, "O15/O18, ECR-0009", "OUT-DEBUG PROC-OUT COST-BOARD OUT-BOARD",
  "needs OUT-07; real ADC noise unverified")
o("OUT-04", "Delete D1/D2 DNP footprints (and the unrouted OUT_A stub)", "cut", "ABCD", 0, 0, 0, 0, -1.16, 0, "0",
  "HW small (no ESD pads)", 0, 0, 1, 0, 0, 0, 0, "-", "OUT-BOARD COST-BOARD OUT-ARM OUT-PAD")
o("OUT-05", "C14 22 uF 0603 -> 1 uF 0402 (existing BOM line)", "cut", "BCD", 0, 0, -0.021, 1, -2.63, 0, "carrier +4 mV on 3V0",
  "HW small (scope TP4)", 0, 0, 1, 0, 0, 0, 1, "spec cap rule", "PWR-OUT-RAIL OUT-BOARD COST-BOARD SPEC-POWER",
  "needs OUT-07; tallest bridge part 1.00 -> 0.60 mm")
o("OUT-07", "Firmware duty clamp + capped self-test: closes ECR-0005 (3V0 peak 326 -> ~92 mA)", "enabler", "ABCD", 0, 0, 0, 0, 0, 0,
  "cell stress 93 -> 27 %", "FW", 0, 0, 4, 0, 1, 0, 1, "D17, ECR-0005/0009", "PWR-OUT-RAIL PROC-OUT OUT-DEBUG SPEC-POWER",
  "PWR-12 = OUT-07; ngspice by reviewer")
o("PER-02", "Delete R11 (ROM loader already pulls PA10 up)", "cut", "ABCD", 1, 0, -0.002, 0, -1.72, 0, "0",
  "FW (stub can pull up)", 0, 0, 0, 0, 0, 0, 0, "-", "PROC-DEBUG COST-BOARD")
o("PER-03", "Delete R17 (CHG_INT pull-up): PA15 internal pull-up, PB5 strapped to GND against the UCPD dead-battery pull-down (PWR-06 = PER-03)", "cut", "ABCD", 1, 0, -0.003, 0, -1.72, 0, "0",
  "FW: UCPD_DBDIS first", 0, 0, 1, 0, 0, 0, 0, "-", "PWR-PROC PROC-BOARD PWR-BOARD COST-BOARD")
o("PER-06", "Merge C20 into the VDD pin-48 100 nF (<= 1.5 mm from pins 1 and 48)", "cut", "ABCD", 1, 0, -0.004, 0, -1.65, 0, "0",
  "HW small (layout rule)", 0, 0, 0, 0, 0, 0, 1, "-", "PROC-BOARD COST-BOARD")
o("PWR-03", "Delete R19 (CC sense), free PA3; Rd R18 and J12 stay", "cut", "ABCD", 1, 0, -0.003, 0, -1.72, 0, "0",
  "FW: ILIM policy", 0, 0, 1, 0, -1, 0, 1, "O12(c) charge time", "PROC-DOCK DOCK-BOARD",
  "= PER-01 CC half; wall chargers never enumerate: write the policy")
o("PER-01D", "CC leaves the pod: delete R18 (Rd 5.1k), J12, 5th wire; 4-contact Xinyangze magnetic dock (PER-01 / PWR-04)", "cut", "BCD", 1, 0, +0.097, 1, -4.83, 0, "0",
  "HW: rotation keying", 2, 0, -1, -1, -1, 1, 2, "O12(a)/(c), O16(3); needs O21 lifted for the sample pair",
  "PROC-DOCK PWR-DOCK DOCK-BOARD DOCK-BODY PROC-DEBUG BOARD-ARM COST-BOARD",
  "audit: no rotation-safe order exists with 4 contacts (180 degrees swaps 1<->4 and 2<->3). Pass = the rotated head REPELS on the exact pair to be bought; any partial hold fails; fail = 5-contact target, VBUS on the centre pin, R18/J12 kept (50 placements)")
o("PER-07", "Power LED onto the pod lid (light pipe): arm 4 -> 2 wires, pad board deleted", "cut", "BC", 0, 0, 0, 0, -2.25, -80, "0",
  "HW: light pipe, splice", 6, 0, 1, 1, 1, 1, 2, "O8, O11, O17, O19, O20",
  "UI-ARM UI-PAD PWR-UI PROC-UI OUT-ARM OUT-PAD ARM-PAD BOARD-ARM BODY-ARM BOARD-BODY SPEC-UI COST-BOARD",
  "pad volume -50..-110 mm3, -0.15 g; needs E1 first")
o("PWR-01", "U3 BQ25180 (TI 1 A I2C linear charger, 8-ball DSBGA) -> BQ25186 (same I2C map, leadless WSON-10, adds /PG and /CE)", "option", "CD", 0, 0, -0.26, 0, +3.2, 0, "die +20 K not +31 K",
  "FW regs / HW footprint", 0, 1, 1, 0, 1, 1, 3, "O16(2)", "PWR-BOARD PWR-DOCK PWR-PROC COST-BOARD SPEC-POWER",
  "robustness swap, not a simplification; re-audit SLUSF69A")
o("PER-11", "Drop TP6 (probe VSYS at C21); DFU-first flash via R1 PH3 pad", "cut", "ABCD", 0, 0, 0, 0, -1.3, 0, "0",
  "FW: boot stub", 0, 0, 1, 0, 1, 0, 1, "O9, O13, O18", "DEBUG-BOARD PWR-DEBUG PROC-DEBUG")
o("PER-12", "PB6 USART1_TX hook + 4 via-dot escapes (PB6, MDF mic-fallback PB8 and PB1, the MIC_DATA net; not pads)", "cut", "BCD", 0, 0, 0, 0, +0.8, 0, "0",
  "FW", 0, 0, 0, 0, 2, 0, 1, "O18, O20; MDF mic fallback kept (sub-audio-in issue 5)", "PROC-BOARD DEBUG-BOARD",
  "audit: 4 dots, not 2-3, so the MDF mic-clock fallback (PB8 clock, PB1 data) stays a hand-wire fix; the clock end is R2's mic-side pad with R2 lifted")
o("FW-1", "Firmware bundle: self-test over-current cutoff, daily wire-health check, ILIM step-up, charge-voltage knob (VBATREG, default 4.20 V)", "firmware",
  "ABCD", 0, 0, 0, 0, 0, 0, "0", "FW", 0, 0, 3, 0, 2, 0, 1, "O18, R23, R24", "OUT-DEBUG PROC-OUT PWR-PROC PROC-DOCK PWR-OUT-RAIL",
  "output missed #1,#2; power missed #1,#5; periphery missed #2. Audit: the cutoff runs only while the F4 samples exist (self-test); an always-on guard is a knob costing 0.15-0.34 mA (interpolated, DS13737 Rev 10 Table 103), so sub-output issue 6 stays OPEN. 4.10-4.15 V costs 1-2 h worst-case runtime: knob, not default")
# --- options that only the aggressive package takes
o("PER-05", "Drop crystal Y1 (Epson FC-135, 32.768 kHz) + C11, C12; HSI16 with docked USB-SOF trim", "option", "D", 3, 0, -0.18, 2, -9.6, 0, "+0.067 mA awake",
  "HW: loses crystal-grade ref", 0, 0, -2, 0, -1, 1, 2, "D16, D12", "PROC-BOARD AUDIO-PROC PROC-OUT PROC-DOCK PROC-DEBUG COST-BOARD",
  "trim is mandatory: untrimmed 3-8x the accepted beat")
o("PER-04", "Drop I2C pull-ups R15/R16, use the MCU internal ones at SCL <= 50 kHz (PWR-07 = PER-04)", "option", "D", 2, 0, -0.005, 0, -3.44, 0, "0",
  "FW slow clock / HW if > 40 pF", 0, 0, -1, 0, -1, 1, 1, "TI says 10k", "PWR-PROC PWR-BOARD PROC-BOARD COST-BOARD")
o("PER-08", "No LED at all (instead of PER-07)", "option", "D", 2, 1, -0.032, 1, -7.94, -80, "-0.14..-0.73 mA",
  "HW: no board-alive light", 6, 0, 1, -2, -2, 1, 1, "O8, D3", "UI-ARM UI-PAD PWR-UI PROC-UI OUT-ARM OUT-PAD ARM-PAD SPEC-UI COST-BOARD",
  "+0.9 h always-awake pessimistic")
o("PWR-09", "Drop C17 if U4 sits within ~3 mm of C21", "option", "D", 1, 0, -0.012, 0, -1.65, 0, "0",
  "HW: layout dependent", 0, 0, -1, 0, 0, 0, 1, "O14", "PWR-BOARD")
o("OUT-06", "Q1/Q2 -> NTZD3155C (onsemi complementary MOSFET pair, SOT-563) only if JLCDFM refuses the DFN1010B-6 redraw (ECR-0004)", "option", "-", 0, 0, -0.004, 0, +4.74, 0, "+0.49 mA",
  "HW", 0, 1, 1, -2, 1, 0, 2, "D6, ECR-0004", "OUT-BOARD PROC-OUT PWR-OUT-RAIL COST-BOARD OUT-DEBUG",
  "DMC2400UV-7 sold out (stock 0 at 22:22Z); fallback costs the 800 kHz knob")
# --- mechanical
o("SIZ-06", "Bend/trim dock tails flat: belly 3.5 -> 2.05 mm (spends O16(3): the USB-C receptacle no longer fits)", "mech", "BCD", 0, 0, 0, 0, 0, -407, "0", "HW", 0, 0, 0, 0, 0, 1, 1,
  "O16(3), O12(a)", "DOCK-BODY DOCK-BOARD PWR-DOCK PWR-BODY", "spare-target bend + pull test; L1 vs magnets (left pod). Audit: the fallback survives only as a reprinted shell with the belly back at 3.5 mm (+391 mm3 on the B core)")
o("SIZ-01", "Board 34x13 -> 28x12; pod top -0.7 mm (cell sets length)", "mech", "BCD", 0, 0, 0, 0, 0, -294, "0", "HW: routing", 0, 0, 0, 0, 0, 1, 1,
  "O20, O14, O16-5", "BOARD-BODY BOARD-ARM AUDIO-BOARD AUDIO-BODY UI-BODY DOCK-BOARD PWR-BOARD OUT-BOARD PROC-BOARD DEBUG-BOARD COST-BOARD PHYS-FRAME",
  "outline is the one irrevocable item: freeze after the dummies")
o("SIZ-03", "F gap 1.5 -> 1.25 mm (parts <= 1.0 mm)", "mech", "BCD", 0, 0, 0, 0, 0, -166, "0", "HW", 0, 0, 0, 0, 0, 1, 1, "O20",
  "BOARD-BODY UI-BODY AUDIO-BODY", "1.15 not proven: fillets, lid +/-0.1")
o("SIZ-04", "Lid wall 1.0 -> 0.8 mm (armour plate kept)", "mech", "BC", 0, 0, 0, 0, 0, -133, "0", "HW", 0, 0, 0, 0, 0, 1, 1, "O12(b), O10",
  "UI-BODY AUDIO-BODY SPEC-BODY")
o("SIZ-02", "Board hung from the lid: 2 pins + 4 VHB spots; ribs, foam, bands out", "enabler", "BCD", 0, 0, 0, 0, 0, 0, "0", "HW", 0, 0, 3, 0, 0, 1, 1,
  "O10, O16(5)(6), O19", "BOARD-BODY UI-BODY AUDIO-BODY PWR-BODY SPEC-BODY", "closes reg-pod-body issues 2 and 11 (= physical 12); F face hidden: hand pads go to B; needs an SW1 back-stop (sub-ui issue 2 worsens otherwise)")
o("SIZ-14", "Wire slack stowed in the board-free rear zone", "mech", "BCD", 0, 0, 0, 0, 0, 0, "0", "HW", 0, 0, 1, 0, 0, 0, 0, "O17",
  "BOARD-ARM BODY-ARM DOCK-BODY PWR-BODY", "binding fill is the 1.1 mm gap behind the cell")
o("SIZ-05", "Armour plate off (lid 1.0)", "option", "D", 0, 0, 0, 0, 0, -378, "0", "HW", 0, 0, 0, -1, 0, 1, 2, "spec v0.14 exterior, O17",
  "AUDIO-BODY UI-BODY SPEC-BODY", "owner aesthetic call; exclusive with SIZ-04")
o("SIZ-11", "Walls 0.8 -> 0.7 mm after a coupon and drop test", "option", "D", 0, 0, 0, 0, 0, -351, "0", "HW", 0, 0, -2, 0, 0, 1, 2, "O19, O12(b)",
  "BODY-ARM PHYS-FRAME SPEC-BODY", "no data for 0.6-0.7 mm tough-resin walls")
o("SIZ-08", "Thin Xinyangze YZ103915020T-04025-02 dock, 2.0 mm, no tails (sample only)", "option", "D", 0, 0, -0.72, 0, 0, -272, "0", "HW", 0, 0, -1, 0, 0, 1, 2, "O16(3), O12(a)",
  "DOCK-BODY DOCK-BOARD PWR-DOCK COST-BOARD SPEC-BODY", "0.2 mm stubs: weaker joint on the daily contact; no mating head sold")
o("SIZ-07", "Delete the USB-C keep-out (moot once SIZ-06 is taken: the receptacle no longer fits)", "option", "-", 0, 0, 0, 0, 0, -53, "0", "HW", 0, 0, -1, 0, 0, 0, 1,
  "O16(3)", "DOCK-BODY SPEC-BODY", "SIZ-06 has already spent the fallback; this adds 0.7 %")
# --- process
o("ASM-01", "Standard PCBA in a 70x70 panel; rails are the O9 frame; corrected fee model", "process", "ABCD", 0, 0, 0, 0, 0, 0, "0", "process", 0, 0, 2, 0, 0, 0, 0,
  "O9, O13", "COST-BOARD BOARD-BODY DEBUG-BOARD", "Economic PCBA is impossible for this board")
o("ASM-05", "Fab spec: ENIG, rules >= 0.10 mm, EP vias filled/tented, +/-0.1 mm routing, flying probe", "process", "ABCD", 0, 0, 0, 0, 0, 0, "0", "process",
  0, 0, 2, 0, 0, 0, 0, "O14", "COST-BOARD PROC-BOARD AUDIO-BOARD BOARD-BODY DEBUG-BOARD", "via 0.20/0.45 is a layout call, not a rule")
o("ASM-09", "Pad order: shared GND pad between J3 (DOCK_VBUS) and J5 (VBAT); every hand pad on B", "process", "BCD", 0, 0, 0, 0, 0, 0, "0", "HW", 0, 0, 2, 0, 1, 0, 1,
  "O14, O19", "DOCK-BOARD BOARD-ARM DOCK-BODY PWR-BOARD OUT-ARM", "replaces 'split J pads by face'")
o("SIZ-15", "Wear dummies at S0/S1/S2 before the outline freeze (extends ECR-0006)", "process", "ABCD", 0, 0, 0, 0, 0, 0, "0", "process", 0, 0, 2, 0, 0, 0, 0,
  "R20, T5, O20", "BOARD-BODY PWR-BODY DOCK-BODY BODY-ARM ARM-PAD")
o("ASM-11", "Count BOM lines and hidden-joint bodies ($1.53 each), not Extended types", "process", "ABCD", 0, 0, 0, 0, 0, 0, "0", "process", 0, 0, 0.5, 0, 0, 0, 0,
  "O19", "COST-BOARD")
o("ASM-X", "Build protocol: no-wash + mask the mic port, JLCDFM written OK on footprints, assemble 6-8 boards, reflow-side note", "process", "ABCD", 0, 0, 0, 0,
  0, 0, "0", "process", 0, 0, 1.5, 0, 0, 0, 0, "O19, R22", "AUDIO-BOARD COST-BOARD", "assembly missed #2,#3,#4,#8")
o("ASM-02", "Frame header for SWD on the panel (optional; the 5 pads stay on the board)", "process", "-", 0, -1, 0, 0, 0, 0, "0", "process", 0, 0, 0, 1, 0, 0, 1,
  "O9, O13, O18", "DEBUG-BOARD PROC-DEBUG PWR-DEBUG", "no SWD probe in the kit: only worth it with the printed pogo jig rejected")


def points(x):
    area_saved = max(0.0, -x["area"]) if x["kind"] in ("cut", "option") else 0.0
    vol_saved = max(0.0, -x["vol"])
    return round(3 * x["P"] + 2 * x["W"] + 4 * x["F"] + area_saved / 5 + vol_saved / 40 + x["r"] + 2 * x["c"] + 2 * x["d"] - 2 * x["h"] - x["g"], 1)


for x in O:
    x["pts"] = points(x)
    x["usd_order"] = round(BOARDS * x["usd_pod"] - FEE_LINE * x["lines"] * 1.0 if x["lines"] else BOARDS * x["usd_pod"], 2)
    if x["id"] == "PER-08":
        x["usd_order"] = round(x["usd_order"] - 10.0, 2)
    if x["id"] == "PER-07":
        x["usd_order"] = -10.0           # pad-board design fee, DERIVED and unquoted (periphery PER-07)
    if x["id"] == "ASM-02":
        x["usd_order"] = 1.63            # frame header line: $1.53 feeder + $0.10 part (assembly ASM-02)
R = sorted(O, key=lambda x: (-x["pts"], x["id"]))
for i, x in enumerate(R, 1):
    x["rank"] = i

# check every relation id exists in the tracker
items = yaml.safe_load(open(REPO / "docs/system/plm/items.yaml"))
known = {r["id"] for r in items["relations"]}
bad = sorted({("R-" + t) for x in O for t in x["rel"].split() if ("R-" + t) not in known})
if bad:
    print("UNKNOWN RELATION IDS:", bad, file=sys.stderr)
    sys.exit(2)

# -------------------------------------------------------------------------------------------------------- package arithmetic
BLOCKS = {  # integration-map section 2, placed parts only (pads J*/TP* excluded)
    "MCU": "U1 C1 C2 C3 C4 C5 C6 C7 C10 C20 R1 R11", "Core SMPS": "L1 C8 C9", "Clock": "Y1 C11 C12", "Mic": "U2 R2 C13",
    "Bridge": "Q1 Q2 R3 R4 R5 R6 C14", "Self-test": "R21 R22 C22", "Dock / USB": "D4 D3 U6 R18 R19 R12 R13 C15",
    "Charger": "U3 C16 C21 RT1 R15 R16 R17", "VBAT sense": "R8 R9 C19", "LDO": "U4 C17 C18 R20", "UI": "SW1 R10 R14",
}
BLOCKS = {k: v.split() for k, v in BLOCKS.items()}
rows = list(csv.DictReader(open(REPO / "hw/pod/bom_jlc.csv")))
LINE_OF = {}
for r in rows:
    for ref in r["Designator"].split(","):
        LINE_OF[ref.strip()] = r["LCSC Part #"]
LINE_OF["LED1"] = "C131223"                      # pad-board LED, on the same JLC order
EXT = {"C87910", "C337891", "C19654206", "C77131", "C221707", "C5271013", "C2879853", "C3682423", "C5220164", "C1972959", "C131223"}
assert sum(len(v) for v in BLOCKS.values()) == 56

PKG = {
    "T": dict(name="Today (Rev E)", rm=[], add=[], swap={}, board=(34, 13), wires=12, pads=12, spare=8),
    "A": dict(name="A  Cleanups", rm="R11 R17 C20 R19".split(), add=[], swap={"R21": "C409058"}, board=(34, 13), wires=12, pads=12, spare=9),
    "B": dict(name="B  Final-size integration", rm="R11 R17 C20 R19 R18 R4 R6 C22".split(), add=["LED1"],
              swap={"R21": "C409058", "C14": "C52923"}, board=(28, 12), wires=9, pads=8, spare=9),
    "C": dict(name="C  B + BQ25186", rm="R11 R17 C20 R19 R18 R4 R6 C22".split(), add=["LED1"],
              swap={"R21": "C409058", "C14": "C52923", "U3": "C44639442"}, board=(28, 12), wires=9, pads=8, spare=9),
    # audit 2026-10-02: B as it stands if O21 (no orders before the freeze) is NOT lifted for the sample set
    "B1": dict(name="B without PER-01D (dock sample fails): R18 and J12 stay", rm="R11 R17 C20 R19 R4 R6 C22".split(), add=["LED1"],
               swap={"R21": "C409058", "C14": "C52923"}, board=(28, 12), wires=10, pads=9, spare=9),
    "B2": dict(name="B without PER-07 (O8 kept, LED stays on the pad board)", rm="R11 R17 C20 R19 R18 R4 R6 C22".split(), add=[],
               swap={"R21": "C409058", "C14": "C52923"}, board=(28, 12), wires=11, pads=10, spare=9),
    "B3": dict(name="B on evidence-free defaults: PER-01D and PER-07 both off", rm="R11 R17 C20 R19 R4 R6 C22".split(), add=[],
               swap={"R21": "C409058", "C14": "C52923"}, board=(28, 12), wires=12, pads=11, spare=9),
    "D": dict(name="D  Ceiling (no ECR)", rm="R11 R17 C20 R19 R18 R4 R6 C22 Y1 C11 C12 R15 R16 C17 R14 LED1".split(), add=[],
              swap={"R21": "C409058", "C14": "C52923", "U3": "C44639442"}, board=(26, 12), wires=9, pads=8, spare=12),
}
EXT_NEW = {"C409058", "C44639442"}
# BOM parts $/pod: de-duplicated sum of the row deltas by package membership. SIZ-08's -0.72 (cheaper thin target) is excluded
# because that dock is sample-only; PER-07 moves the LED between boards at no BOM change.
for k in "ABCD":
    PKG[k]["usd_pod"] = round(sum(x["usd_pod"] for x in O if k in x["pkgs"] and x["id"] != "SIZ-08"), 3)
PKG["T"]["usd_pod"] = 0.0


def summarize(k):
    p = PKG[k]
    pod_refs = [r for v in BLOCKS.values() for r in v if r not in p["rm"]]
    blk = {}
    for b, v in BLOCKS.items():
        blk[b] = dict(today=len(v), kept=len([r for r in v if r not in p["rm"]]), removed=[r for r in v if r in p["rm"]], added=0)
    if "LED1" in p["add"]:
        blk["UI"]["added"] = 1
    placements = len(pod_refs) + (1 if "LED1" in p["add"] else 0)
    # BOM lines per JLC order: every remaining ref (pod board, plus the pad-board LED while it exists) with swaps applied
    order_refs = pod_refs + ([] if "LED1" in p["rm"] else ["LED1"])
    codes = {p["swap"].get(r, LINE_OF[r]) for r in order_refs}
    ext = len([c for c in codes if c in EXT or c in EXT_NEW])
    arm = 2 if ("LED1" in p["add"] or "LED1" in p["rm"]) else 4
    return dict(key=k, name=p["name"], placements=placements, lines=len(codes), ext=ext, blocks=blk, wires=p["wires"], pads=p["pads"],
                arm=arm, spare=p["spare"], board=p["board"], usd_pod=p.get("usd_pod"), removed=p["rm"], added=p["add"], swap=p["swap"])


SUM = {k: summarize(k) for k in "TABCD"}
VAR = {k: summarize(k) for k in ("B1", "B2", "B3")}      # B variants for the O21/O22 section (study 3.9)
# MCU pins (audit 2026-10-02). listed = pins the integration ledger calls free (PB5 consumed as the PA15 strap); unassigned = listed minus
# PB6 once it carries the USART1_TX hook (B, C, D); clean = unassigned minus PB1/PB8 (reserved for the MDF mic-clock fallback), PC13 (static,
# ES0499 2.2.1) and PB15 (UCPD dead-battery pull-down: DBDIS first, ECR-0013 S2). D also frees PC14/PC15 (crystal) and PB7 (LED).
PINS = {"T": (8, 8, 4), "A": (9, 9, 5), "B": (9, 8, 4), "C": (9, 8, 4), "D": (12, 11, 7), "B1": (9, 8, 4), "B2": (9, 8, 4), "B3": (9, 8, 4)}
# average current delta, mA (negative = saves): power study; the FW-1 over-current guard is OFF in normal listening in these numbers
DAVG = {"T": (0, 0), "A": (0, 0), "B": (-0.03, -0.03), "C": (-0.03, -0.03), "D": (-0.10, -0.69)}
# runtime model: tws-power-size.md gives 21.2 h at 7 mA typical and 12.4 h worst case at 4.20 V (175 mAh): usable 148.4 mAh
USABLE_MAH, I_TYP, I_WORST = 21.2 * 7.0, 7.0, 21.2 * 7.0 / 12.4
for _d in (SUM, VAR):
    for _k, _s in _d.items():
        _s["spare_listed"], _s["spare_unassigned"], _s["spare_clean"] = PINS[_k]
        _s["spare_listed_check"] = _s["spare"]
        assert _s["spare_listed"] == _s["spare"], (_k, _s["spare"])
for _k, (_lo, _hi) in DAVG.items():
    SUM[_k]["davg"] = (_lo, _hi)
    SUM[_k]["rt_typ"] = tuple(round(USABLE_MAH / (I_TYP + d), 1) for d in (_lo, _hi))
    SUM[_k]["rt_worst"] = tuple(round(USABLE_MAH / (I_WORST + d), 1) for d in (_lo, _hi))
# FW-1 knobs, interpolated linearly in conversion rate from DS13737 Rev 10 Table 103 (14-bit single-ended, IDDA_s + IDDV_s):
# 10 ksps = 130 + 15 uA, 1 Msps = 550 + 90 uA. The datasheet gives only these points; the curve between them is NOT specified.
def adc_ua(fs):
    return 145.0 + (fs - 10e3) / (1e6 - 10e3) * (640.0 - 145.0)
GUARD_MA = {fs: round(adc_ua(fs) / 1000, 2) for fs in (25e3, 200e3, 400e3)}
GUARD_RT = {fs: (round(USABLE_MAH / (I_TYP + GUARD_MA[fs]), 1), round(USABLE_MAH / (I_WORST + GUARD_MA[fs]), 1)) for fs in GUARD_MA}
VBATREG_NOTE = "tws-power-size.md: 4.10-4.15 V gives about -14 % energy: worst case 10.7-11.5 h, typical about 18 h (derived), against D18's 12 h target"
assert SUM["T"]["placements"] == 56 and SUM["T"]["lines"] == 30 and SUM["T"]["ext"] == 11, SUM["T"]
COURT_T = 246.4                                   # pcbnew courtyard probe of pod_r1_routed.kicad_pcb, 76 footprints (size.md SIZ-01)
for k in "TABCD":
    s = SUM[k]
    s["court"] = round(COURT_T + sum(x["area"] for x in O if k in x["pkgs"]), 1) if k != "T" else COURT_T
    bx, by = s["board"]
    s["face"] = bx * by
    s["density_pct"] = round(100 * s["court"] / (2 * bx * by), 1)
    s["fees_lines_usd"] = round(FEE_LINE * (s["lines"] - SUM["T"]["lines"]), 2)

# ------------------------------------------------------------------------------------------------------------ size scenarios
sys.path.insert(0, str(REPO / "sim/checks"))
import size_budget as sb  # noqa: E402

core = dict(board_H=12.0, board_L=28.0, y_bgap=1.4, y_fgap=1.25, lid_wall=0.8, s_fixed=0.8)
SZ = {
    "T": sb.scenario("S0 as drawn"),
    "A": sb.scenario("A: as drawn"),
    "B": sb.scenario("B/C: SIZ-01,02,03@1.25,04,06", dock="flat_tails", **core),
    "D": sb.scenario("D: 26x12, F 1.15, plate off, walls 0.7, thin dock", dock="thin", plate=0.0, wall=0.7,
                     **{**core, "board_L": 26.0, "y_fgap": 1.15, "lid_wall": 0.7}),
}
SZ["C"] = SZ["B"]
for _k in ("B1", "B2", "B3"):
    SZ[_k] = SZ["B"]        # neither PER-01D nor PER-07 changes the pod envelope (the target body is the same; the pad board is outside it)
# the same B core with the tails NOT bent flat (the belly stays 3.5 mm): what keeping the in-shell USB-C fallback costs
SZ["B_belly35"] = sb.scenario("B core, belly kept at 3.5 mm (USB-C fallback fits)", dock="as_built", **core)
for k in list("TABCD") + ["B1", "B2", "B3"]:
    z = SZ[k]
    (SUM if k in SUM else VAR)[k]["size"] = dict(L=z["L"], T=z["T"], H=z["H"], belly=z["belly_d"], z=z["z_total"], vol=z["v_env"], mass=z["mass_g"],
                          nose=z["nose_g"], off_temple=z["from_temple_outer"], dvol_pct=round(100 * (z["v_env"] / SZ["T"]["v_env"] - 1), 1))

# --------------------------------------------------------------------------------------------------------------- order money
for k in "ABCD":
    s = SUM[k]
    parts = BOARDS * s["usd_pod"]
    s["usd_order_parts"] = round(parts, 2)
    s["usd_order_fees"] = s["fees_lines_usd"]
    s["usd_order_legacy_ext"] = round(3.0 * (s["ext"] - SUM["T"]["ext"]), 2)           # the old bom.md '$3 per Extended type' model
    padboard = -10.0 if k in "BC" else (-10.0 if k == "D" else 0.0)                       # derived, unquoted (periphery PER-07)
    s["usd_order_padboard_est"] = padboard
    s["usd_order_total"] = round(parts + s["fees_lines_usd"] + padboard, 2)

if __name__ == "__main__":
    json.dump(dict(opps=R, pkg=SUM, var=VAR, guard_ma={str(int(k)): v for k, v in GUARD_MA.items()},
                   guard_rt={str(int(k)): v for k, v in GUARD_RT.items()}, belly35=dict(vol=SZ["B_belly35"]["v_env"], z=SZ["B_belly35"]["z_total"], belly=SZ["B_belly35"]["belly_d"],
                                                          dvol=SZ["B_belly35"]["v_env"] - SZ["B"]["v_env"])), open(OUT, "w"), indent=1, default=list)
    print("## RANKED")
    print("| # | id | what | kind | pkgs | pts | P | E | $/order | $/pod | area mm2 | vol mm3 | power | risk | gates | decisions | relations |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for x in R:
        print(f'| {x["rank"]} | {x["id"]} | {x["name"]} | {x["kind"]} | {x["pkgs"]} | {x["pts"]} | {x["P"]} | {x["E"]} | {x["usd_order"]:+.2f} | '
              f'{x["usd_pod"]:+.3f} | {x["area"]:+.2f} | {x["vol"]:+d} | {x["power"]} | {x["risk"]} | {x["g"]} | {x["dec"]} | {x["rel"]} |')
    print()
    print("## B VARIANTS (O21/O22)")
    for k, s in VAR.items():
        print(k, s["name"], "placements", s["placements"], "lines", s["lines"], "ext", s["ext"], "wires/pads", s["wires"], s["pads"], "arm", s["arm"])
    print("FW-1 guard mA at 25/200/400 kS/s:", GUARD_MA, "runtime typ/worst:", GUARD_RT)
    for k in "TABCD":
        print("runtime", k, SUM[k]["rt_typ"], SUM[k]["rt_worst"], "spare", SUM[k]["spare_listed"], SUM[k]["spare_unassigned"], SUM[k]["spare_clean"])
    print("belly 3.5 on the B core:", SZ["B_belly35"]["v_env"], "vs", SZ["B"]["v_env"], "mm3")
    print("## PACKAGES")
    for k in "TABCD":
        s = SUM[k]
        print(k, s["name"], "placements", s["placements"], "lines", s["lines"], "ext", s["ext"], "court", s["court"], "dens", s["density_pct"],
              "usd_pod", s["usd_pod"], "order(parts/fees/pad/total)", s.get("usd_order_parts"), s.get("usd_order_fees"), s.get("usd_order_padboard_est"),
              s.get("usd_order_total"), "legacy", s.get("usd_order_legacy_ext"), "size", s["size"], "blocks", {b: (v["kept"], v["added"]) for b, v in s["blocks"].items()})
