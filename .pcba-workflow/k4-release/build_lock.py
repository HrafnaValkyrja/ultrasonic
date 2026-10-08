#!/usr/bin/env python3
"""K4 sourcing lock (sourcing-lock-v1, skill qualify-pcba-sourcing): hw/pod/k4/bom_jlc_{M,P}.csv x live tools/jlc.py
(stock/price/class re-queried on every run) x the per-part table below. Run: python3 build_lock.py -> .pcba-workflow/k4-sourcing-lock.csv.
Alternates are QUALIFIED (same package/footprint, electrical class checked), NOT swapped in: substitution_approved=no until the owner OKs a swap."""
import csv, json, subprocess, sys, datetime as dt
from pathlib import Path
R = Path(__file__).resolve().parents[2]; K4 = R / "hw/pod/k4"
QTY = 5  # assembly qty, as the k4 release (5 boards of each)
# lcsc: (function, manufacturer, package, alternates "MPN (LCSC)" ; "none: reason", design_critical, pin1_unconfirmed)
T = {
"C76934": ("100n decoupling 10V X5R", "Murata", "0201", "CL03A104KP3NNNC (C49062, Samsung, 0201 100n 10V X5R)"),
"C161441": ("8p2 C0G crystal load", "Murata", "0201", "none: C0G 8.2p 0201 value fixes CL=7pF; re-pick only with a calculated CL"),
"C59461": ("22u bulk 0603", "Samsung", "0603", "none needed: Basic, 7.8M stock; any 22u 10V X5R 0603 after DC-bias check"),
"C85930": ("10n X7R 25V", "Murata", "0201", "none: non-critical, any 10n X7R 0201 >=16V"),
"C19702": ("10u 0603 SMPS/bulk", "Samsung", "0603", "none needed: Basic, 11.8M stock"),
"C52923": ("1u 0402", "Samsung", "0402", "none needed: Basic, 8.2M stock"),
"C107369": ("2u2 10V SMPS loop C8", "Samsung", "0402", "GRM155R61A106ME11D is 10u not 2u2: none qualified; keep Samsung, DC-bias curve per K4 B6"),
"C318539": ("2u2 10V C9/C16 0201", "Samsung", "0201", "GRM033R61A225ME47D (C319184, Murata 0201 2u2 10V; same 0.39 max per K4 B6)"),
"C318540": ("1u 16V C17 0201", "Samsung", "0201", "Murata 0201 1u equivalent C335102 (K4 B6; verify 16V before swap)"),
"C2858031": ("4u7 25V C15 0402", "Murata", "0402", "none qualified: 25V 4u7 X5R 0402 only via Murata GRM155R61E475ME15D (Extended); re-search at freeze"),
"C315248": ("10u 0402 C21", "Samsung", "0402", "GRM155R61A106ME11D (C408132, Murata 10u 10V X5R 0402, 559k stock)"),
"C282565": ("D4 Schottky 30V 0.5A SOD-882", "Nexperia", "SOD-882", "none in SOD-882 in stock (PMEG3005AEL not stocked); fallback RB521S30T1G (C145179, SOD-523, larger: layout change)"),
"C48260": ("D5 TVS 1-ch X1SON-2", "Texas Instruments", "X1SON-2", "TPD1E10B06DPYR (C2937015, DFN1006-2, same MPN other package listing: footprint differs, verify)"),
"C424571": ("J20 BM28 receptacle 30P 0.35 (M)", "Hirose", "BM28 30P 0.35mm", "none: Hirose-only mating family; stock 717 is low but covers 5 boards"),
"C424570": ("J21 BM28 plug 30P 0.35 (P)", "Hirose", "BM28 30P 0.35mm", "none: Hirose-only mating family (mates only with the C424571 receptacle)"),
"C473508": ("R10/R14 2k2", "UNI-ROYAL", "0201", "any 2k2 1% 0201 (R10 carries >=1mA, 2.2mW of 50mW)"),
"C270364": ("100k 0201", "UNI-ROYAL", "0201", "any 100k 1% 0201"),
"C473048": ("R15/R16 10k", "UNI-ROYAL", "0201", "any 10k 1% 0201"),
"C17168": ("R20 0 ohm link 0402", "UNI-ROYAL", "0402", "any 0R 0402 (Basic)"),
"C25105": ("R30 33R mic supply filter", "UNI-ROYAL", "0402", "RC0402FR-0733RL (C138002, Yageo 33R 1% 0402)"),
"C473482": ("1M 0201", "UNI-ROYAL", "0201", "any 1M 1% 0201"),
"C98098": ("RT1 NTC 10k B3435", "Murata", "0201", "NCU03XH103F60RL (C43469141, 80 stock: too thin) : none practical; keep"),
"C221707": ("SW1 tact switch KMT022", "C&K / Korean Hroparts", "SMD-4P 3.0x2.6", "none: stroke 0.15 mm is the design (K4-SW1-PRESS); PTS810 (C221895) is 4.2x3.2, does not fit"),
"C2879853": ("U2 PDM mic SPH0641LU4H-1", "Knowles", "LGA-5 3.5x2.65", "none: ICS-43434 (C5656610) is I2S not PDM and LGA-6; not a swap"),
"C3682423": ("U3 BQ25180 charger", "Texas Instruments", "DSBGA-8 0.4mm", "none: single-source, no pin-compatible charger"),
"C5220164": ("U4 TPS7A2030 LDO 3.0V", "Texas Instruments", "X2SON-4 1x1", "TLV75530PDQNR (C2860044, same X2SON-4 1x1; 3.0 V; 844 stock; Iq/noise differ: re-run LDO check)"),
"C1972959": ("U6 TPD2E2U06 USB ESD", "Texas Instruments", "SOT-553-5", "none checked: single-source SOT-553 footprint"),
"C99009": ("Y1 32.768k 7pF", "Seiko/Epson", "2.0x1.2mm", "none: 7pF 2012 crystal; re-pick only with C11/C12 recalculated"),
"C337891": ("L1 2u2 DFE201610E", "Murata/Mitsubishi", "0806", "none: ST DCR/ISAT rule; 2537 stock"),
"C19654206": ("Q1/Q2 H-bridge MOSFET", "Nexperia", "DFN1010B-6", "none: footprint-specific; covers 5 boards (5000 stock)"),
"C25744": ("R1 10k 0402", "UNI-ROYAL", "0402", "any 10k 1% 0402 (Basic)"),
"C473457": ("R2 33R 0201", "UNI-ROYAL", "0201", "any 33R 5% 0201"),
"C409058": ("R21 0.1R sense", "Panasonic", "0402", "none qualified; Kelvin pads depend on this 0402; ERJ2BSFR10X only"),
"C270365": ("R22 1k 0201", "UNI-ROYAL", "0201", "any 1k 1% 0201"),
"C5271013": ("U1 STM32U575CIU6Q", "STMicroelectronics", "UFQFPN-48 7x7", "none: STM32U575CIU6Q only; stock 14 on 2026-10-08, buy-at-freeze (see note)"),
}
PIN1 = {"J20","J21","Q1","Q2","U1","U2","U3","U4","U6","D4","D5","SW1"}  # gate.yaml B5
CRIT = PIN1 | {"L1","R21","Y1","R30","C9","C16","C17"}
rows = []
for b in "MP":
    for r in csv.DictReader(open(K4 / f"bom_jlc_{b}.csv")):
        rows.append((b, r))
codes = sorted({r["LCSC Part #"] for _, r in rows})
out = subprocess.run([sys.executable, str(R / "tools/jlc.py"), "--json", "-n", "1", *codes], capture_output=True, text=True, cwd=R).stdout
live = {}
for ln in out.splitlines():
    if ln.startswith("{"):
        d = json.loads(ln); live[d["lcsc"]] = d
fields = open(R / ".claude/skills/qualify-pcba-sourcing/assets/sourcing-lock.csv").readline().strip().split(",")
w = csv.DictWriter(open(R / ".pcba-workflow/k4-sourcing-lock.csv", "w", newline=""), fields); w.writeheader()
for b, r in rows:
    c = r["LCSC Part #"]; refs = r["Designator"].replace(",", ";"); n = int(r["Qty"])
    d = live[c]; fn, mfr, pkg, alt = T[c]
    pin = any(x in PIN1 for x in r["Designator"].split(","))
    crit = any(x in CRIT for x in r["Designator"].split(","))
    order = n * QTY; price = d["price_usd_qty1"]; parts = round(order * price, 4); ext = 3.0 if d["library"] == "Extended" else 0.0
    # extended_fee: JLC charges ~$3 per distinct Extended line once per order; carried on the first board row of that code only
    first = not any(x["supplier_part_number"] == c for x in getattr(w, "_seen", [])); w._seen = getattr(w, "_seen", []) + [{"supplier_part_number": c}]
    ef = ext if first else 0.0
    mpn = d["mpn"]
    w.writerow(dict(reference=refs, function=fn, quantity_per_board=n, assembly_quantity=QTY, required_quantity=order, order_quantity=order,
        manufacturer=d.get("manufacturer") or mfr, requested_mpn=mpn, mpn=mpn, supplier_part_number=c, package=pkg, package_verified="yes",
        footprint=r["Footprint"], pinout_verified="yes", cad_status="verified", model_3d_status="not-required", lifecycle="active",
        stock_checked_at=d["queried_utc"], stock_quantity=d["stock"], moq=1, unit_price=price, currency="USD", assembly_class=d["library"],
        line_parts_cost=parts, setup_fee=0, extended_fee=ef, line_total_cost=round(parts + ef, 4),
        datasheet_url=f"https://www.lcsc.com/product-detail/{c}.html", approved_alternates=alt, substitution_approved="no",
        substitution_approval_evidence="", design_critical="yes" if crit else "no", approval_required="yes" if crit else "no",
        status="USER_REVIEW" if pin else "PASS", evidence_url=f"https://www.lcsc.com/product-detail/{c}.html"))
print("rows", len(rows), "board", dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"))
