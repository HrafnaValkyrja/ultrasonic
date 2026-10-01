"""Numeric checks behind docs/build/hardware.md (sourcing & build materials), 2026-09-30.

Writes hw/mech/out/parts/hardware/checks.json. No CAD, no simulation: arithmetic on published
numbers (source + access date on every input) and on the module notes in hw/mech/notes/.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0 \
        python3 docs/build/hardware_checks.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw" / "mech"))
import frame  # noqa: E402  (shared interface; read-only)

D = "2026-09-30"
OUT = ROOT / "hw" / "mech" / "out" / "parts" / "hardware"
checks: list[dict] = []


def chk(name, ok, value, source=""):
    checks.append({"name": name, "pass": bool(ok), "value": value, "source": source})


# ------------------------------------------------------------------ 1. NiTi plateaus (FWM minimums)
FWM = "fwmetals.com superelastic-nitinol (straight-annealed MINIMUMS, tension, 22 and 37 C), " + D
fwm = {  # grade: (upper22, lower22, upper37, lower37) MPa
    "#1 (Af 10..18)": (483, 138, 552, 207),
    "#2 (Af 0..18)": (552, 207, 621, 276),
    "#9 (Af -10..5)": (517, 172, 552, 207),
}
T_SKIN = 32.0
f = (T_SKIN - 22) / (37 - 22)
interp = {g: (u22 + f * (u37 - u22), l22 + f * (l37 - l22)) for g, (u22, l22, u37, l37) in fwm.items()}
lowers = [v[1] for v in interp.values()]
uppers = [v[0] for v in interp.values()]
chk("niti_lower_plateau_200MPa_is_a_floor", min(lowers) - 20 <= 200 <= max(lowers),
    {g: round(v[1]) for g, v in interp.items()} | {"model": 200, "note": "linear interp. to 32 C; FWM minimums"},
    FWM)
chk("niti_loading_plateau_450MPa_not_low", 450 >= min(uppers),
    {g: round(v[0]) for g, v in interp.items()} | {"model": 450,
     "ratio_range": [round(min(uppers) / 450, 2), round(max(uppers) / 450, 2)],
     "consequence": "put-on peak force likely 15-33 % above the model"}, FWM)
chk("niti_af_le_0C_purchasable_0.75_to_0.85mm", False,
    "Kellogg's 0.75 SE: Af 0-10 C; Nexmetal 0.8: 'Standard (above freezing)'; -20/-30 C grades only "
    "0.3/0.5/1.0 mm+. heel.md's 'Af <= 0 C' is not buyable off the shelf",
    "kelloggsresearchlabs.com round-wire; nexmetal.com nitinol-superelastic-wire, " + D)
chk("niti_0.85mm_stock", False, "no stock source; Kellogg's 0.033 in (0.838 mm) by quote", "kelloggsresearchlabs.com, " + D)
ratio = {d: round((d / 0.80) ** 3, 3) for d in (0.75, 0.80, 0.838)}
chk("niti_force_scale_d_cubed", True, ratio, "plateau force ~ sigma*d^3 (bending of a round section)")
cut = frame.HEEL_SOCKET_DEPTH + frame.SPAN + frame.PAD_SOCKET_DEPTH
chk("niti_cut_length_per_arm_mm", True, {"socket_heel": frame.HEEL_SOCKET_DEPTH, "span": round(frame.SPAN, 2),
    "socket_pad": frame.PAD_SOCKET_DEPTH, "total": round(cut, 2), "cut": 20.0,
    "arms_per_5ft_kelloggs": int(5 * 304.8 // 20.0)}, "hw/mech/frame.py")

# ------------------------------------------------------------------ 2. Fasteners
# ISO 68-1 basic profile: H = (sqrt3/2) P ; internal-thread basic depth H1 = 5H/8 = 0.5413 P.
def engagement(d, p, pilot):
    h1 = 5 / 8 * math.sqrt(3) / 2 * p
    return (d - pilot) / 2 / h1


THREAD = {"M1.2": (1.2, 0.25), "M1.4": (1.4, 0.30), "M1.6": (1.6, 0.35)}
eng = {}
for name, pilot in (("M1.2", 0.95), ("M1.2", 1.00), ("M1.2", 1.05), ("M1.4", 1.10), ("M1.4", 1.15), ("M1.4", 1.20)):
    d, p = THREAD[name]
    eng[f"{name} pilot {pilot:.2f}"] = round(100 * engagement(d, p, pilot))
chk("M1.2_pilot_0.95_thread_engagement_le_75pct", eng["M1.2 pilot 0.95"] <= 75,
    eng | {"guidance": "60-75 % for thread-forming in plastics; 0.95 is ~ the tapping-drill size (D1 0.929)",
           "used_by": "pad.md cup closure screw M1.2x4 (eyeglass machine screw) into a 0.95 pilot"},
    "ISO 68-1 basic profile; Toray self-tap guidance (plastics.toray tec_027), " + D)
nut_threads = 1.2 / THREAD["M1.4"][1]
chk("set_and_lid_screws_full_nut_engagement", nut_threads >= 3, {"threads_in_DIN934_M1.4_nut": nut_threads},
    "DIN 934 M1.4 m = 1.2 mm; pitch 0.3")
chk("lid_screw_length_3mm_only", True, {"buy": "M1.4 x 3", "max_safe": 3.6, "M1.4x4": "too long for the lid (shell.md)"},
    "hw/mech/notes/shell.md")
chk("hex_key_0.7_fits_DIN916_M1.4_and_M1.6", True, {"M1.4 s": 0.7, "M1.6 s": 0.7},
    "Fuller Fasteners DIN 916 table, " + D)
chk("M1.4_cup_set_screw_2_3mm_cheap_stock", False,
    "FastenerMart SHA545-530 (M1.4x3, 45H) 45 pcs $55.97; cheap stock is Polar Bear Camera cone-point slotted "
    "GBP 6.99/pack (qty not stated). ISO 4026 flat point (heel.md's preference): no hobby source found",
    "fastenermart.com, polarbearcamera.com, " + D)
chk("M1.4_brass_nut_DIN934_verified_source", False,
    "marketplace only (eBay, ~$2.65/pack, unverified); Accu stocks M1.4 DIN 934 only in 303/316 stainless",
    "accu-components.com snippet, ebay listings, " + D)
chk("threadlocker_222_ok_on_resin", False,
    "Henkel: 'not normally recommended for use on plastics (particularly thermoplastic materials where stress "
    "cracking ... could result)'. heel.md lists it as optional; test a drop on a support-raft scrap first",
    "LOCTITE 222 TDS, May 2022 (datasheets.tdx.henkel.com), " + D)

# per-pod hardware, from the module notes (hw/mech/notes/*.md, 2026-09-30)
per_pod = {
    "M1.4x3 pan/cheese (lid = charge contacts)": 2,
    "M1.4 brass nut DIN 934": 2 + 1 + 1,       # lid x2, heel x1, pad x1
    "M1.4x3 set screw (heel)": 1,
    "M1.4x2 set screw (pad)": 1,
    "M1.2x4 pan (pad closure)": 1,
}
chk("hardware_per_pod_from_module_notes", True, per_pod | {"x2_pods": {k: 2 * v for k, v in per_pod.items()}},
    "hw/mech/notes/shell.md, heel.md, pad.md")

# ------------------------------------------------------------------ 3. Conductors
# strand bending strain at the NiTi root: R = r_niti / eps_niti
r_bend = (frame.NITI_D / 2) / 0.05
strain = {f"{d} mm strand": round(100 * d / (2 * r_bend), 2) for d in (0.10, 0.05, 0.025)}
chk("strand_strain_at_root_pct", strain["0.05 mm strand"] < 0.5, strain | {"bend_radius_mm": r_bend},
    "eps = d / 2R; NiTi at 5 % outer-fibre strain")


def bundle4(d):  # smallest circle around 4 equal circles
    return d * (1 + math.sqrt(2))


wires = {"7/44 served litz (Elecify)": 0.21, "Cooner NUF38-1650": 0.38,
         "PTFE 36 AWG 7/44 thin": 0.36, "PTFE 36 AWG 7/44 thick": 0.51, "module notes' '0.3 mm OD'": 0.30}
channels = {"pad strut channel": 1.0, "heel channel": 1.2}
fit = {}
for wn, d in wires.items():
    b = bundle4(d)
    fit[wn] = {"OD": d, "bundle_of_4": round(b, 2)} | {c: round(D_ - b, 2) for c, D_ in channels.items()}
litz_ok = all(v > 0.3 for k, v in fit["7/44 served litz (Elecify)"].items() if k in channels)
chk("arm_conductors_fit_channels_margin_gt_0.3", litz_ok, fit | {"note": "margin = channel D - bundle D"},
    "pad.md (D1.0), heel.md (D1.2); OD: elecify.com, coonerwire.com catalogue, nassaunationalcable.com, " + D)
area = 7 * math.pi * 0.025 ** 2
chk("litz_resistance_ohm_per_m", True, round(0.01724 / area, 2), "copper 0.01724 ohm mm^2/m; 7 x 0.05 mm")
chk("arm_wire_le_0.3mm_OD_flex", True, "7/44 served litz OD ~0.21 mm, 10 m $0.71 (Elecify)", "elecify.com, " + D)
chk("charge_nut_wire", True, "Adafruit 30 AWG silicone, OD 0.8 mm, -60..200 C, 2 m $0.75; red = VBUS, black = GND_CHG",
    "adafruit.com/product/2051, " + D)
chk("prewired_LED_not_needed", True, "the pad board carries a JLC-placed 0402 LED (pad.md, electronics.md)",
    "hw/mech/notes/pad.md")

# ------------------------------------------------------------------ 4. Resin / tapes
chk("resin_min_slot_0.3_ok", frame.RESIN["min_slot"] >= 0.4,
    {"frame": frame.RESIN["min_slot"], "source_limit": 0.4}, "formlabs.com/support/Design-Specs (Form 2), " + D)
chk("resin_min_wall_0.6_ok", frame.RESIN["min_wall"] >= 0.4, {"frame": frame.RESIN["min_wall"]},
    "Formlabs Form 2: 0.4 supported/unsupported, " + D)
chk("resin_holes_below_0.8_print_reliably", False, "Form 2: holes < 0.8 mm may close -> print undersize, drill",
    "formlabs.com Design-Specs, " + D)
chk("resin_candidate_full_TDS", True, "Siraya Blu: 50 MPa, 32 %, Izod 45 J/m, HDT 70 C, E 1.8 GPa, $32.65/kg",
    "siraya.tech, " + D)
chk("vhb_4914_fits_tape_gap", 0.25 <= frame.TAPE, {"tape": 0.25, "gap": frame.TAPE, "spare": round(frame.TAPE - 0.25, 2)},
    "3M VHB 4914 (Tekra snippet), " + D)
chk("poron_0.79_for_0.8_washer", True, {"thinnest_PORON_4701-30_mm": 0.79, "washer_t": frame.MIC_SEAL["washer_t"]},
    "rogerscorp.com PORON 4701-30 (snippet), " + D)

# ------------------------------------------------------------------ 5. Dock
gf = 9.80665e-3
pogo_n = 2 * 60 * gf
chk("pogo_pin_selected", True, {"part": "Mill-Max 0906-1-15-20-75-14-11-0", "force_each_gf": 60,
    "stroke_mm": 1.52, "two_pins_N": round(pogo_n, 2), "price_each": 0.73},
    "Mill-Max data sheet 2021-07-28; Digi-Key (snippet), " + D)
chk("dock_retention_by_magnet_on_A2_screws", False,
    "A2 stainless is essentially non-magnetic; cradle, clip or hidden steel disc needed", "")

# ------------------------------------------------------------------ 6. Spend
verified = {  # USD, as read 2026-09-30, before shipping/tax
    "Kellogg's 0.75 SE 5 ft": 13.49, "Nexmetal 0.8 x 3 ft": 3 * 1.74, "iFixit Mako 64": 39.95,
    "Elecify litz 10 m": 0.71, "Adafruit 30AWG silicone red": 0.75, "Adafruit 30AWG silicone black": 0.75,
    "Siraya Blu 1 kg": 32.65, "Mill-Max pogo x8": 8 * 0.73,
}
chk("verified_core_spend_usd", True, {"items": verified, "total": round(sum(verified.values()), 2)},
    "prices as read " + D + "; GBP items (Polar Bear set screws) and unverified items excluded")
chk("every_price_dated", True, "all " + D + "; [S]/[U] tags in hardware.md mark snippet-only or unverified", "")

OUT.mkdir(parents=True, exist_ok=True)
doc = {"module": "hardware", "date": D, "doc": "docs/build/hardware.md", "note": "hw/mech/notes/hardware.md",
       "generator": "docs/build/hardware_checks.py", "checks": checks}
(OUT / "checks.json").write_text(json.dumps(doc, indent=1))
for c in checks:
    print(("PASS " if c["pass"] else "FAIL ") + c["name"])
print(json.dumps({c["name"]: c["value"] for c in checks if c["name"] in (
    "M1.2_pilot_0.95_thread_engagement_le_75pct", "arm_conductors_fit_channels_margin_gt_0.3",
    "verified_core_spend_usd", "niti_cut_length_per_arm_mm")}, indent=1))
