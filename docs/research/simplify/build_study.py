#!/usr/bin/env python3
"""Build docs/research/simplification-study.md from study-template.md and synthesis.json.

    python3 docs/research/simplify/build_study.py        (run synthesis.py first)

Fills <!--RANKED-->, <!--TOTALS--> and <!--ECRS--> so no number in the note is typed twice.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parents[2]
J = json.load(open(HERE / "synthesis.json"))
S = J["pkg"]


def sgn(v, f="{:+d}"):
    return "0" if v == 0 else f.format(v)


def ranked():
    L = ["| # | Opportunity | Pkg | Pts | Plc | Ext | $/order | $/pod | Area mm2 | Vol mm3 | Power | Risk (FW = firmware-fixable, HW = hardware-only) | Owner decisions | Relations |",
         "|--:|---|---|--:|--:|--:|--:|--:|--:|--:|---|---|---|---|"]
    for x in J["opps"]:
        pk = " ".join(x["pkgs"]) if x["pkgs"] != "-" else "none"
        star = "*" if x["id"] in ("PER-07", "PER-08") else ""
        usd = x["usd_order"]
        L.append(f'| {x["rank"]} | **{x["id"]}** {x["name"]} | {pk} | {x["pts"]} | {sgn(x["P"])} | {sgn(x["E"])} | '
                 f'{"0" if usd == 0 else f"{usd:+.2f}"}{star} | {"0" if x["usd_pod"] == 0 else f"{x["usd_pod"]:+.3f}"} | '
                 f'{"0" if x["area"] == 0 else f"{x["area"]:+.2f}"} | {sgn(x["vol"])} | {x["power"]} | {x["risk"]}'
                 f'{"; gates " + str(x["g"]) if x["g"] else ""} | {x["dec"]} | {x["rel"]} |')
    return "\n".join(L)


def totals():
    keys = "TABCD"
    hdr = "| | Today (Rev E) | **A** Cleanups | **B** Final-size integration (recommended) | **C** B + BQ25186 | D Ceiling (no ECR) |"
    L = [hdr, "|---|--:|--:|--:|--:|--:|"]

    def row(label, f):
        L.append(f"| {label} | " + " | ".join(f(S[k]) for k in keys) + " |")

    def delta(cur, base, fmt="{}", d="{:+}"):
        return fmt.format(cur) + ("" if cur == base else f" ({d.format(round(cur - base, 2))})")
    T = S["T"]
    row("**Placed parts (pod board)**", lambda s: f'**{delta(s["placements"], T["placements"])}**')
    for b in T["blocks"]:
        row(f"&nbsp;&nbsp;{b}", lambda s, b=b: f'{s["blocks"][b]["kept"] + s["blocks"][b]["added"]}' +
            ("" if s["blocks"][b]["kept"] + s["blocks"][b]["added"] == T["blocks"][b]["today"] else
             f' ({s["blocks"][b]["kept"] + s["blocks"][b]["added"] - T["blocks"][b]["today"]:+d})'))
    row("**BOM lines per JLC order**", lambda s: delta(s["lines"], T["lines"]))
    row("**Extended types per order** (pod board 10 + the LED)", lambda s: delta(s["ext"], T["ext"]))
    row("BOM parts $/pod (delta)", lambda s: "-" if s["key"] == "T" else f'{s["usd_pod"]:+.2f}')
    row("$/order, parts (4 boards)", lambda s: "-" if s["key"] == "T" else f'{s["usd_order_parts"]:+.2f}')
    row("$/order, BOM-line fees ($1.53 each)", lambda s: "-" if s["key"] == "T" else f'{s["usd_order_fees"]:+.2f}')
    row("$/order, pad board not ordered (derived, unquoted)", lambda s: "-" if s["key"] == "T" else f'{s["usd_order_padboard_est"]:+.2f}')
    row("**$/order total delta**", lambda s: "-" if s["key"] == "T" else f'**{s["usd_order_total"]:+.2f}**')
    row("(old bom.md model: $3 per Extended type)", lambda s: "-" if s["key"] == "T" else f'{s["usd_order_legacy_ext"]:+.2f}')
    row("Courtyards, mm2", lambda s: delta(s["court"], T["court"], "{:.0f}", "{:+.0f}"))
    row("Board outline (mm), per-face area", lambda s: f'{s["board"][0]} x {s["board"][1]} = {s["face"]}')
    row("Courtyard density (both faces; proven routed 42.9 %)", lambda s: f'{s["density_pct"]} %')
    row("**Pod envelope, cm3**", lambda s: f'**{round(s["size"]["vol"] / 1000 + 1e-9, 2):.2f}**' + ("" if s["key"] == "T" or s["size"]["dvol_pct"] == 0 else f' ({s["size"]["dvol_pct"]:+.1f} %)'))
    row("L x T x H + belly (mm)", lambda s: f'{s["size"]["L"]} x {s["size"]["T"]} x {s["size"]["H"]} + {s["size"]["belly"]}')
    row("Total height incl. belly (mm)", lambda s: f'{s["size"]["z"]}')
    row("Off the temple (mm)", lambda s: f'{s["size"]["off_temple"]}')
    row("Mass (g, derived)", lambda s: f'{s["size"]["mass"]}')
    row("Hand-solder wires / pads", lambda s: f'{s["wires"]} / {s["pads"]}')
    row("Arm wires", lambda s: str(s["arm"]))
    row("MCU pins listed free (PB5 consumed as a strap)", lambda s: str(s["spare_listed"]))
    row("&nbsp;&nbsp;not yet claimed (PB6 = USART1_TX hook in B, C, D)", lambda s: str(s["spare_unassigned"]))
    row("&nbsp;&nbsp;clean (also not PB1/PB8 MDF fallback, PC13 static, PB15 UCPD hazard)", lambda s: str(s["spare_clean"]))
    row("+3V0 peak (rating 300 mA, ICL 360)", lambda s: "326 mA" if s["key"] == "T" else "about 92 mA")
    row("VSYS peak, % of cell 350 mA pulse rating", lambda s: "93 %" if s["key"] == "T" else "about 27 %")
    row("Average current, delta (FW-1 over-current guard OFF in normal listening)", lambda s: {"T": "-", "A": "0", "B": "-0.03 mA", "C": "-0.03 mA", "D": "-0.10 to -0.69 mA (+0.9 h pessimistic)"}[s["key"]])

    def rt(s):
        a, b = s["rt_typ"], s["rt_worst"]
        typ = f"{a[0]:.1f}" if a[0] == a[1] else f"{a[0]:.1f}-{a[1]:.1f}"
        wst = f"{b[0]:.1f}" if b[0] == b[1] else f"{b[0]:.1f}-{b[1]:.1f}"
        return f"{typ} / {wst}"
    row("Runtime at 4.20 V, h: typical (7 mA) / worst case (tws-power-size.md, derived)", rt)
    row("Fine-pitch / hidden-joint packages retired", lambda s: {"T": "-", "A": "none", "B": "none", "C": "DSBGA-8 -> WSON-10 (still X-ray)", "D": "as C"}[s["key"]])
    row("Hardware-only gates (resolve before the freeze only if O21 is lifted; else proved on rev 1, O22)", lambda s: {
        "T": "-", "A": "none (OUT-07 needs your acceptance)",
        "B": "JLCDFM footprints (free); dock keying*, wear dummies / outline*, E1 exciter leads*, lid-hung bond + SW1 press coupon*. *Needs a purchase O21 forbids: lift it for the sample set or take B3 (3.9)",
        "C": "B + BQ25186 re-audit and board-1 read-back", "D": "C + D16 trim, no-LED, I2C margin, wall and plate coupons"}[s["key"]])
    return "\n".join(L)


def ecrs():
    p = HERE / "ecr-ids.json"
    if not p.exists():
        return "_(ECR ids not yet recorded)_"
    ids = json.load(open(p))
    L = ["| Package | ECR | Title |", "|---|---|---|"]
    for k in "ABC":
        e = ids.get(k)
        if e:
            L.append(f"| {k} | [{e['id']}](../system/plm/ecr/{e['id']}.md) | {e['title']} |")
    return "\n".join(L)


def variants():
    V = J["var"]
    cols = [("**B** (full)", S["B"], "JLCDFM, keying, E1, dummies, bond coupon", "O8, O12(a)/O16(3), O21 lifted"),
            ("**B1** dock sample fails (R18, J12 stay)", V["B1"], "JLCDFM, E1, dummies, bond coupon", "O8, O21 lifted"),
            ("**B2** PER-07 off (O8 kept)", V["B2"], "JLCDFM, keying, dummies, bond coupon", "O12(a)/O16(3), O21 lifted"),
            ("**B3** both off = B on the defaults", V["B3"], "JLCDFM; pod-only dummies; bond coupon if VHB is on hand", "O21 unchanged, O8 and O12(a) kept")]
    L = ["| | " + " | ".join(c[0] for c in cols) + " |", "|---|" + "--:|" * len(cols)]

    def row(label, f):
        L.append(f"| {label} | " + " | ".join(f(c[1]) for c in cols) + " |")
    row("Placed parts (pod board)", lambda s: str(s["placements"]))
    row("BOM lines per JLC order", lambda s: str(s["lines"]))
    row("Extended types per order", lambda s: str(s["ext"]))
    row("Hand-solder wires / pads", lambda s: f'{s["wires"]} / {s["pads"]}')
    row("Arm wires", lambda s: str(s["arm"]))
    row("Pod envelope, cm3", lambda s: f'{round(s["size"]["vol"] / 1000 + 1e-9, 2):.2f}')
    L.append("| Gates left | " + " | ".join(c[2] for c in cols) + " |")
    L.append("| Owner decisions | " + " | ".join(c[3] for c in cols) + " |")
    return "\n".join(L)


t = (HERE / "study-template.md").read_text()
t = t.replace("<!--RANKED-->", ranked()).replace("<!--TOTALS-->", totals()).replace("<!--ECRS-->", ecrs()).replace("<!--VARIANTS-->", variants())
out = REPO / "docs/research/simplification-study.md"
out.write_text(t)
print(out, len(t.splitlines()), "lines")
