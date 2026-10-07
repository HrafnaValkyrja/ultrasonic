"""Flexible BOM for rev 1 (one pair of pods). Edit ITEMS / OPTIONS / QTY here, then:

    python3 docs/build/bom.py        # -> docs/build/bom.csv + docs/build/bom.md

Prices: JLC parts API 2026-10-01T04:05Z (tools/jlc.py) or the sourcing lock 2026-09-30, unit price at
low quantity. 'TBD' = not yet priced. Board parts are per pod; the pair needs 2x.
Status: rev C / rev D / rev E = in hw/pod/gen.py (Rev E 2026-10-01); O16 = owner-approved, off-board or not yet built;
option = alternative; off-board = hand-built/bought, not on the JLC board.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
PODS = 2

# block, part, ref/role, LCSC or source, qty per pod, unit USD (None = TBD), status, note
ITEMS = [
    # --- MCU, mic, clock
    ("MCU", "STM32U575CIU6Q", "U1", "C5271013", 1, 8.9281, "rev C", "ONLY 8 IN STOCK at JLC 2026-10-01: buy/reserve early"),
    ("Mic", "SPH0641LU4H-1", "U2", "C2879853", 1, 1.9915, "rev C", "ultrasonic PDM mic"),
    ("Clock", "32.768 kHz crystal 2012 7 pF X1A0000610006", "Y1", "C99009", 1, 0.2125, "phase 2", "MZ-2 (ECR-0018); Rev G C32346 $0.1717; JLC API 2026-10-07T11:31Z, Extended, stock 23426"),
    ("MCU", "2.2 uH inductor DFE201610E", "L1 (SMPS)", "C337891", 1, 0.1366, "rev C", ""),
    # --- output stage
    ("Bridge", "PMCXB290UE N+P pair", "Q1, Q2", "C19654206", 2, 0.1706, "rev C", "footprint must be redrawn (Nexperia Fig. 32)"),
    # --- power (O16)
    ("Charger", "BQ25180YBGR (NTC/JEITA, power path, I2C)", "U3", "C3682423", 1, 2.0419, "rev D", "replaces MCP73832"),
    ("Charger", "MCP73832-2-OT", "U3 (old)", "C38066", 0, 0.9492, "rev C (removed)", "qty 0 after O16"),
    ("Charger", "NTC 10k B3435 0201 NCP03XH103F05RL", "RT1 (+ J9 pad for a cell NTC)", "C98098", 1, 0.0166, "phase 2", "MZ-2 (ECR-0018); Rev G C77131 $0.0199; JLC API 2026-10-07T11:31Z, Extended, stock 175122"),
    ("Power", "TPS7A2030 3.0 V LDO", "U4", "C5220164", 1, 0.2175, "rev C", "input moves to VSYS"),
    ("Protect", "PMEG3005EL SOD-882 (reverse docking)", "D4", "C282565", 1, 0.1150, "phase 2", "MZ-2 (ECR-0018); Rev G 1N5819WS C191023 $0.0137; JLC API 2026-10-07T11:31Z, Extended, stock 43342"),
    ("Protect", "TPD1E10B06DPYR (TI bidirectional ESD, 5.5 V working) at the J3 DOCK_VBUS contact", "D5, D6", "C48260", 2, 0.0417, "rev G", "D5 at J3 DOCK_VBUS replaces D3 (Rev F); D6 at J12 CC (Rev G, O24); JLC API 2026-10-02T23:48Z, 299k stock"),
    ("Protect", "PESD5V0S1BL (bridge outputs)", "D1, D2", "C84374", 0, 0.0334, "rev F removed", "Rev F: DNP footprints deleted (OUT-04)"),
    ("USB", "TPD2E2U06DRLR (D+/D- ESD)", "U6", "C1972959", 1, 0.3224, "rev D", "USB FS on PA11/PA12"),
    ("UI", "C&K KMT022NGJLHS IP68 switch, 1.6 N, 600k cycles", "SW1", "C221707", 1, 0.3902, "rev D", "replaces KXT321; 2.2k pull-down for >= 1 mA contact current"),
    # --- rev-1 test hooks (Rev E)
    ("Test", "0.1 ohm 1% 0402 bridge shunt ERJ2BSFR10X", "R21", "C409058", 1, 0.0732, "phase 2", "MZ-2 (ECR-0018); Rev G 1206 C25334 $0.0055 Basic; JLC API 2026-10-07T11:31Z, Extended, stock 15878; lift it to disconnect the bridge"),
    ("Test", "0 ohm 0402 link (LDO -> 3V0)", "R20", "C17168", 1, 0.0025, "rev E", "lift it to meter or inject the 3V0 rail"),
    # --- passives (approx. counts after O16)
    ("Passives", "0402/0603 capacitors (Basic)", "C*", "various", 18, 0.012, "rev G", "18 parts (Rev F: C20 removed; C15, C8/C9 itemised below)"),
    ("Passives", "Samsung CL05A225KP5NSNC 2.2 uF 10 V X5R 0402 (VDD11; ST DS13737 Rev 10 p.153: rated >= 10 V)", "C8, C9", "C107369", 2, 0.0129, "rev G", "Extended; was 6.3 V C12530 (O24); sourcing-lock 2026-09-30, 878k stock"),
    ("Passives", "Murata GRM155R61E475ME15D 4.7 uF 25 V X5R 0402 (charger IN, TI 25 V recommendation)", "C15", "C2858031", 1, 0.0833, "rev F", "Extended; JLC API 2026-10-02T23:50Z, 135k stock"),
    ("Passives", "0402 resistors (Basic)", "R*", "various", 16, 0.003, "rev F", "16 parts (Rev F: R11, R17, R19 removed; R20 and R21 itemised under Test)"),
    # --- pad board (same panel)
    ("Pad board", "Everlight 16-213/BHC-AN1P2 blue 0402 LED", "LED1", "C131223", 1, 0.0291, "O8", "on the tiny pad board"),
    # --- off-board
    ("Cell", "Renata ICP501233PA-02, 175 mAh, PCM", "BT1", "Renata distributor quote", 1, None, "O16", "NO public price: not on Digi-Key, Mouser blocks reads, Renata shows no price (2026-10-01); request a quote"),
    ("Cell", "Adafruit #1570 105 mAh (bench stand-in)", "BT1 alt", "Adafruit / Digi-Key", 0, 5.95, "option", "set qty 1 for early bench tests"),
    ("Transducer", "RC-BC02 bone-conduction exciter", "XDCR", "marketplace", 1, None, "rev C", "listing URLs were never saved; price unknown; buy 3+ from two listings"),
    ("Connector", "Xinyangze YZT0675 5-pin magnetic TARGET (pod side, magnets built in)", "J-dock", "LCSC C5126848", 1, 2.40, "O16", "21.2 x 6.86 x 2.8 mm; 51 in stock 2026-10-01; fits the bigger rev-1 bottom face"),
    ("Connector", "Xinyangze YZP0048-20048-05025-01 5-pin magnetic POGO head (cable side; mates the 5-pin YZT0675 target)", "dock", "LCSC C5126847", 0.5, 1.39, "O16", "one per cable; JLC stock 0 (JLC API 2026-10-07T17:14Z): buy from LCSC/Xinyangze at order time; was wrongly C5126845 = the 4-pin -04025-03 head (DK-01)"),
    ("Connector", "Adafruit 5358 + 5412 magnetic pair (bench alt)", "J-dock alt", "adafruit.com", 0, 11.45, "option", "$6.50 + $4.95, 21 x 7 face; for early tests"),
    ("Connector", "sealed USB-C receptacle (fallback, space reserved)", "J-usbc", "Same Sky UJ32-C-H-G-MSMT IP68", 0, None, "option", "6.75 x 8.55 x 2.76; price not retrieved"),
    ("Arm", "NiTi superelastic wire 0.75 mm", "arm", "Kellogg's W-NITI-0.75-SE", 0.1, 13.49, "O7b", "$13.49 per 5 ft (~76 arms)"),
    ("Arm", "Litz 7/44 served, 0.21 mm", "4 conductors", "elecify.com", 0.05, 0.71, "O11", "$0.71 per 10 m"),
    ("Arm", "M1.4 set screw", "NiTi lock", "Polar Bear / FastenerMart", 2, 0.16, "O16", "pack price spread"),
    ("Pad", "M1.2 cup screw", "cup closure", "micro-screw kit", 1, 0.10, "O16", "screws OK on the cup"),
    ("Pad", "Sugru (or pre-made pad)", "contact face", "retail", 0.1, 20.0, "O16", "~$20 per pack; tiny amount per pad"),
    ("Housing", "Tough/ABS-like resin", "tub, lid, adapter, pad", "Siraya Tech Blu 1 kg", 0.01, 32.65, "O16", "owner already prints resin"),
]

# one-time, per order (rough, NOT a quote): set to your best estimate
ONE_TIME = [
    ("JLC 4-layer PCB, 5 boards, 0.8 mm", 15, 35),
    ("JLC assembly setup + stencil (double-sided)", 25, 60),
    ("JLC loading fee per Extended part type (11 types x ~$3, after the 2026-10-01 audit)", 33, 40),
    ("Shipping (+ duties, country-dependent)", 20, 60),
]


def main():
    rows, per_pod, tbd = [], 0.0, []
    for blk, part, ref, src, q, u, st, note in ITEMS:
        ext = None if u is None else q * u
        if ext is None and q:
            tbd.append(part)
        per_pod += ext or 0
        rows.append(dict(block=blk, part=part, ref=ref, source=src, qty_per_pod=q,
                         unit_usd="TBD" if u is None else f"{u:.4f}",
                         per_pod_usd="TBD" if ext is None else f"{ext:.2f}", status=st, note=note))
    with open(HERE / "bom.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    lo = sum(a for _, a, _ in ONE_TIME)
    hi = sum(b for _, _, b in ONE_TIME)
    md = ["# Rev 1 BOM (flexible)", "",
          "Generated by `docs/build/bom.py`; edit that file, not this one. Prices: JLC parts API 2026-10-01 or the "
          "sourcing lock 2026-09-30. Board parts are per pod; totals are for **one pair (2 pods)**.", "",
          "| Block | Part | Ref | Source | Qty/pod | Unit $ | Per pod $ | Status | Note |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append("| " + " | ".join(str(r[k]) for k in r) + " |")
    md += ["", f"**Priced parts: ${per_pod:.2f} per pod, ${per_pod * PODS:.2f} per pair**, plus TBD items: "
           + ", ".join(tbd) + ".", "",
           "## One-time costs per JLC order (rough estimate, not a quote)", "",
           "| Item | Low $ | High $ |", "|---|---|---|"]
    md += [f"| {a} | {b} | {c} |" for a, b, c in ONE_TIME]
    md += [f"| **Total** | **{lo}** | **{hi}** |", "",
           "Rough rev-1 milestone: one JLC order (5 boards, 2-3 assembled) + one pair's parts. "
           f"Known parts ${per_pod * PODS:.0f} + one-time ${lo}-{hi} + TBD items (cells, transducers, connector).",
           "", "**Risk: the STM32U575CIU6Q had only 8 in stock at JLC on 2026-10-01.**"]
    (HERE / "bom.md").write_text("\n".join(md) + "\n")
    print(f"per pod ${per_pod:.2f}, pair ${per_pod * PODS:.2f}; one-time ${lo}-{hi}; TBD: {tbd}")


if __name__ == "__main__":
    main()
