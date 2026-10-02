"""Whole-system logical map of the pod: the cross-check every design change must pass.

    source tools/env.sh && python3 hw/pod/system_map.py     # -> docs/system/integration-map.md

Built from the SKiDL schematic itself (gen.build(), so pin NAMES are authoritative), plus the
hand-kept facts the netlist can't carry: what each function is for, rail loads, off-board wiring,
mechanical interfaces, firmware dependencies and owner decisions. A change in one domain (power,
output stage, connector, assembly) must be walked through every section here before it is proposed:
no function may lose its implementation, no net its driver, no MCU pin two jobs, no rail its budget,
no mechanical interface its counterpart. Regenerate after every schematic change.
"""
from __future__ import annotations

import builtins
import contextlib
import io
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = REPO / "docs/system/integration-map.md"
sys.path.insert(0, str(HERE))

BLOCKS = {
    "MCU": "U1 C1 C2 C3 C4 C5 C6 C7 C10 R1",
    "CORE_SMPS": "L1 C8 C9",
    "CLOCK": "Y1 C11 C12",
    "MIC": "U2 R2 C13",
    "BRIDGE": "Q1 Q2 R3 R4 R5 R6 C14",
    "SELFTEST": "R21 R22 C22",
    "ARM_PADS": "J1 J2 J7 J8",
    "DOCK_USB": "J3 J4 J10 J11 J12 D4 D5 U6 R18 R12 R13 C15",
    "CHARGER": "U3 C16 C21 RT1 J9 R15 R16",
    "CELL_PADS": "J5",
    "VBAT_SENSE": "R8 R9 C19",
    "LDO": "U4 C17 C18 R20",
    "UI": "SW1 R10 R14",
    "DEBUG": "TP1 TP2 TP3 TP4 TP5 TP6 TP7 TP8 TP9 TP10",
}
BLOCK_OF = {ref: blk for blk, refs in BLOCKS.items() for ref in refs.split()}

# function -> (blocks, chain of nets/pins, mechanical counterpart, firmware counterpart)
FUNCTIONS = [
    ("F1 Hear 20-85 kHz", "MIC, MCU", "MIC_VDD from PA5 (GPIO-switched supply, off in Off mode); MIC_CLK PB3 -> R2 33R -> U2; MIC_DATA U2 -> PB4 (ADF1)",
     "mic on B at board (3.9, 6.5), 0.6 mm port through the board, lid port D1.0 + hydrophobic mesh on the pod centre line", "ADF1 4 MHz PDM, algorithm A/B"),
    ("F2 Process", "MCU, CORE_SMPS, CLOCK", "+3V0 -> VDD/VDDA/VDDSMPS; VLXSMPS -> L1 -> VDD11 (C8/C9); LSE Y1 on PC14/PC15",
     "-", "MSI/PLL clocks, LSE (see A3-clock doc), Stop 2 / Off modes (D12)"),
    ("F3 Drive the exciter", "BRIDGE, ARM_PADS", "TIM1 CH1/CH1N PA8/PA7 -> Q1 gates (GA_P/GA_N); CH2/CH2N PA9/PB0 -> Q2 (GB_P/GB_N); P sources on +3V0, N sources on BRIDGE_RTN; OUT_A/OUT_B -> J1/J2",
     "2 litz wires up the NiTi arm (rear-side route, heel channel, strut bore) to the exciter in the pad", "complementary PWM ~200 kHz with dead time; level/volume control"),
    ("F4 Self-test exciter |Z|", "SELFTEST, BRIDGE", "BRIDGE_RTN -> R21 0.1R -> GND; BRIDGE_RTN -> R22 1k -> I_SENSE (C22 10n) -> PA6 ADC1_IN11",
     "-", "tone sweep + synchronous detection over USB self-test (O15)"),
    ("F5 Charge the cell", "DOCK_USB, CHARGER, CELL_PADS", "dock J3 DOCK_VBUS -> D4 -> VBUS -> U3 IN; U3 BAT -> VBAT -> J5 (cell +) / J4 shared GND (cell -) -> cell (PCM inside); config over I2C",
     "magnetic 5-pin target in the belly bay, wired to J3/J4/J10/J11/J12; cell under the board (B side) on foam", "I2C charge current/JEITA setup, charge state"),
    ("F6 Temperature-safe charge", "CHARGER", "TS: RT1 (on board) OR J9 cell NTC, never both -> U3 TS/MR; TS also -> PA2",
     "optional NTC taped on the cell, wire to J9", "firmware 20 C rule reads PA2"),
    ("F7 System power rail", "CHARGER, LDO", "U3 SYS -> VSYS -> U4 IN/EN -> LDO_OUT (C18) -> R20 0R -> +3V0",
     "-", "-"),
    ("F8 Battery level", "VBAT_SENSE", "VBAT -> R8 1M / R9 1M (C19) -> VBAT_SENSE -> PA4 (ADC4 works in Stop 2)", "-", "fuel estimate, low-battery cutoff"),
    ("F9 Dock detect", "DOCK_USB", "VBUS -> R12/R13 100k/100k -> VBUS_SENSE -> PA1", "-", "DFU entry, charge mode"),
    ("F10 USB data / DFU", "DOCK_USB, MCU", "J10 D+ / J11 D- -> U6 ESD -> PA12/PA11 (USB FS); CC: J12 -> R18 5k1 Rd (CC not sensed since Rev F; ILIM by enumeration)",
     "dock contacts D+/D-/CC", "ROM DFU via boot stub, CDC self-test, firmware update"),
    ("F11 Wake / button", "UI, MCU", "SW1 (3V0 <-> BTN) -> PA0 WKUP1, R10 2k2 pull-down (switch needs >= 1 mA)",
     "SW1 on F at board (22.0, 6.5) under the lid plunger (D3.2 bore, silicone skin), KMT0 travel 0.15 mm", "wake from Off/Stop, on/off, modes"),
    ("F12 Power LED (solid)", "UI, ARM_PADS", "VSYS -> R14 2k2 -> LED_A -> J7 -> wire -> LED in the pad housing -> wire -> J8 -> LED_K -> PB7 (open-drain, FT)",
     "2 more litz wires up the arm (4 total), LED on the tiny pad board (O8)", "duty set from VBAT for steady brightness"),
    ("F13 Charger link", "CHARGER, MCU", "I2C_SCL PB13, I2C_SDA PB14 (R15/R16 10k to 3V0); CHG_INT -> PA15 (internal pull-up; PB5 strapped to GND, ECR-0013 S1)", "-", "I2C2, charger IRQ"),
    ("F14 Debug / flash / test", "DEBUG, MCU", "TP1 SWDIO PA13, TP2 SWCLK PA14, TP3 NRST, TP4 3V0, TP5 GND, TP6 VSYS; BOOT0 (PH3) R1 10k low (R1 pad = DFU tack point); TP7 PB6 USART1_TX printf; TP8/TP9/TP10 MDF mic fallback dots; PA10 pulled up by the ROM loader itself (bootloader USART1_RX)",
     "0.7 mm pads in a 1.27 mm row on F, top edge; snap-off test frame (O9)", "SWD, ROM bootloader"),
    ("F15 ESD at exposed contacts", "DOCK_USB", "D5 TPD1E10B06 at J3 DOCK_VBUS (bidirectional, 5.5 V working; D4 reverse block); U6 on D+/D-", "dock contacts are the only exposed metal", "-"),
]

RAILS = {
    "+3V0": "source: U4 LDO via R20 (TPS7A2030, 300 mA rated, ICL 360 mA min). Loads: MCU ~2.4-5.8 mA run; mic ~0.9-1.1 mA via PA5; "
            "bridge P sources: avg 0.6-1.7 mA at listening level but ~315 mA peaks at full drive (8R + 1.2R FETs) buffered by C14 22 uF; "
            "pull-ups R15/R16; SW1 contact (>= 1 mA while pressed).",
    "VSYS": "source: U3 SYS (power path: VBUS when docked, else VBAT through the BATFET). Loads: U4 LDO input, R14 LED (~0.35-0.75 mA), TP6.",
    "VBAT": "cell (Renata ICP501233PA-02 175 mAh, 3.0-4.2 V, PCM inside) <-> U3 BAT. Loads: R8/R9 divider (2 uA), C16.",
    "VBUS": "dock 5 V via D4 Schottky (reverse-dock block). Loads: U3 IN, R12/R13 sense, C15 (25 V). DOCK_VBUS side: D5 ESD.",
    "VDD11": "MCU's own SMPS output via L1; MCU core only (D11 allows this switching regulator only).",
    "BRIDGE_RTN": "bridge N-FET sources -> R21 0.1R shunt -> GND (31 mV at 315 mA).",
}

OFFBOARD = [
    ("J1 / J2", "OUT_A / OUT_B", "litz wire up the arm -> bone-conduction exciter RC-BC02 (8 or 12 ohm) in the pad"),
    ("J7 / J8", "LED_A / LED_K", "litz wire up the arm -> blue 0402 LED on the pad board"),
    ("J3 / J4 / J10 / J11 / J12", "DOCK_VBUS / GND / USB_DP / USB_DM / CC", "Xinyangze YZT0675 5-pin magnetic target in the belly bay (pogo YZP0048 on the cable)"),
    ("J5 / J4", "VBAT / GND (J4 shared with dock GND, between J3 and J5)", "cell leads (PCM inside the cell)"),
    ("J9", "TS", "optional NTC taped on the cell (then RT1 not fitted)"),
    ("TP1-TP6", "SWDIO, SWCLK, NRST, +3V0, GND, VSYS", "probe / pogo only"),
]

MECH = [
    "Board 34 x 13 x 0.8 mm, 4 layers (In1 solid GND), parts on BOTH faces today; pod x 30.6-64.6 in hw/mech/shell_r1.py.",
    "F faces the lid (outside); B faces the cell. Part height bands: B 10.9-12.1, F 12.9-14.1 (y, pod coords) = ~1.2 mm each side.",
    "Mic MUST be on B at board (3.9, 6.5): bottom-port, ports through the board and the lid (D1.0 + mesh). Same spot on both pods (one board for both, O16-5).",
    "Switch MUST be on F at board (22.0, 6.5) under the lid plunger (D3.2 bore + silicone skin): changing the button changes the lid.",
    "0.6 mm top and bottom edge bands free of parts on BOTH faces: the lid's clamp ribs and the foam strips press there (board retention, no screws).",
    "Wire pads J* on F at the rear edge; the arm wires come up a 2.1 mm gap behind the board from the heel channel (exit x 65.75).",
    "Dock target sits in the belly bay (pod x 31.5-52.7), wired to J3/J4/J10/J11/J12; USB-C fallback keep-out reserved.",
    "Cell 35 x 12 x 5.3 mm under B on foam; nothing tall on B over the cell beyond the 1.2 mm band.",
    "Arm: 4 litz wires (2 exciter + 2 LED) in shrink tube through heel channel D1.0 and strut bore D1.2: the wire count sets those bores.",
]

FIRMWARE = [
    "TIM1 complementary PWM with dead time on PA8/PA7/PA9/PB0 (bridge).",
    "ADF1 (audio digital filter) on PB3 clock / PB4 data, 4 MHz PDM; PA5 is the mic's supply pin.",
    "ADC: PA4 VBAT (ADC4, works in Stop 2), PA1 VBUS sense, PA2 TS, PA6 bridge current (PA3 spare since Rev F).",
    "I2C2 on PB13/PB14 to the charger, EXTI on PA15 (CHG_INT).",
    "USB FS on PA11/PA12 (HSI48 + CRS), ROM DFU (the ROM loader pulls PA10 up itself, AN2606 Table 199); PB6 USART1_TX debug printf (TP7).",
    "Wake: PA0 = WKUP1 (button). LED: PB7 open-drain, PWM duty set from VBAT.",
    "SWD on PA13/PA14. Low-power modes Stop 2 / Off (D12).",
]

CONSTRAINTS = [
    "Spec section 1 (MVP) is owner-locked.",
    "D11: switching regulators ONLY the MCU core SMPS; self-noise no louder than ambient.",
    "Power budget ~5-8.5 mA total (algorithm A) / 7.5-10.5 mA (B); runtime targets in spec.",
    "O8 power LED in the pad housing, solid. O9 rev 1 IS the prototype (test pads + snap-off frame).",
    "O12 magnetic USB dock (charge + DFU), IPX4 min / IPX5 preferred, outdoor wear in light rain, fast charge.",
    "O16: Renata 175 mAh cell, BQ25180 charger, pre-built magnetic connector, one board for both pods, no screws in the housing, IP68 switch.",
    "Owner rule for this study: one expensive component beats five half-price ones.",
]

PROTOCOL = """Every proposed change must state, and check against the sections above:
1. functions_affected: which F-rows change, and the NEW implementation chain for each (no function may be left without one; say explicitly if a function is dropped and that it needs an owner decision).
2. nets_changed: nets removed, added or re-driven; every remaining net still has exactly one driver and its loads.
3. pins: MCU pins freed and pins newly needed, with the alternate function used; no pin may end up with two jobs (check the pin map, including other domains' proposals).
4. rails: load change per rail (mA avg and peak) vs its source's rating; new rails need a source that respects D11.
5. offboard: changes to J pads, wire counts up the arm, dock contacts, cell wiring.
6. mechanical: which face each moved/added part is on, height band, keep-outs (mic port, switch/plunger, clamp bands, wire path), lid/shell features that must change.
7. firmware: peripherals/features added, removed or re-pinned.
8. depends_on / conflicts_with: other domains' changes this one needs or excludes."""


def build():
    import gen                                           # noqa: E402  (sets SKiDL lib paths)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        gen.build()
    return builtins.default_circuit


def main():
    circ = build()
    nets = defaultdict(list)
    for p in circ.parts:
        for pin in p.pins:
            for n in pin.nets:
                if n.name and not n.name.startswith("__NOCONNECT"):
                    nets[n.name].append((p.ref, str(pin.num), pin.name))
    refs = sorted({p.ref for p in circ.parts}, key=lambda r: (r.rstrip("0123456789"), int(r[len(r.rstrip("0123456789")):] or 0)))
    unassigned = [r for r in refs if r not in BLOCK_OF]
    L = ["# Integration map: the pod as one system (generated)", "",
         "Generated by `hw/pod/system_map.py` from the SKiDL schematic (`hw/pod/gen.py`) plus hand-kept facts. "
         "Do not edit by hand; regenerate. Part of the living big-picture set (`docs/system/README.md`). "
         "The block diagram is `docs/diagrams/schematic-rev1.png`.", "",
         "**Use:** before proposing any change, walk it through every section. The required cross-check is at the end.", "",
         "## 1. Functions (what the pod must keep doing)", "",
         "| Function | Blocks | Electrical chain (nets / pins) | Mechanical counterpart | Firmware counterpart |", "|---|---|---|---|---|"]
    L += [f"| {f} | {b} | {c} | {m} | {fw} |" for f, b, c, m, fw in FUNCTIONS]
    L += ["", "## 2. Blocks (every placed or copper-only part)", "", "| Block | Parts |", "|---|---|"]
    L += [f"| {blk} | {' '.join(r for r in BLOCKS[blk].split() if r in refs)} |" for blk in BLOCKS]
    if unassigned:
        L += ["", f"**Unassigned parts (update BLOCKS in system_map.py):** {', '.join(unassigned)}"]
    L += ["", "## 3. Inter-block nets (the logical connections a domain change can break)", "",
          "| Net | Blocks | Pins (ref.pin name) |", "|---|---|---|"]
    for name in sorted(nets):
        pins = nets[name]
        blks = sorted({BLOCK_OF.get(r, "?") for r, _, _ in pins})
        if name == "GND":
            L.append(f"| GND | all | {len(pins)} pins |")
            continue
        if len(blks) > 1:
            L.append(f"| {name} | {', '.join(blks)} | {', '.join(f'{r}.{n} {pn}' for r, n, pn in pins)} |")
    L += ["", "Nets inside one block only: " + ", ".join(sorted(n for n in nets if n != "GND" and len({BLOCK_OF.get(r, '?') for r, _, _ in nets[n]}) == 1)), ""]
    u1 = next(p for p in circ.parts if p.ref == "U1")
    L += ["## 4. MCU pin map (STM32U575CIU6Q, QFN48)", "", "| Pin | Name | Net | Other end |", "|---|---|---|---|"]
    free = []
    for pin in sorted(u1.pins, key=lambda q: int(q.num)):
        ns = [n for n in pin.nets if n.name]
        if not ns or ns[0].name.startswith("__NOCONNECT"):
            free.append(f"{pin.num} {pin.name}")
            continue
        n = ns[0].name
        other = sorted({f"{r}" for r, _, _ in nets[n] if r != "U1"})
        L.append(f"| {pin.num} | {pin.name} | {n} | {', '.join(other) if n not in ('GND', '+3V0') else '(rail)'} |")
    L += ["", f"**Free MCU pins:** {', '.join(free)}", "",
          "## 5. Rails and loads", "", "| Rail | Source and loads |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in RAILS.items()]
    L += ["", "## 6. Off-board interfaces", "", "| Pads | Nets | Goes to |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in OFFBOARD]
    L += ["", "## 7. Mechanical interfaces and keep-outs", ""] + [f"- {m}" for m in MECH]
    L += ["", "## 8. Firmware dependencies", ""] + [f"- {m}" for m in FIRMWARE]
    L += ["", "## 9. Constraints and owner decisions", ""] + [f"- {m}" for m in CONSTRAINTS]
    L += ["", "## 10. Required cross-check for every proposed change", "", PROTOCOL, ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L))
    print(f"wrote {OUT.relative_to(REPO)}: {len(refs)} parts, {len(nets)} nets, {len(free)} free MCU pins, unassigned: {unassigned or 'none'}")


if __name__ == "__main__":
    main()
