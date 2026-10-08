#!/usr/bin/env python3
"""Pod mass roll-up for the current design (physical.md issue 8, reg-pod-body issue 10, 00-whole risk 18, spec D18).

Volumes come from the shell_r2 STLs (hw/mech/out/r2, run `python3 hw/mech/shell_r2.py` first) and the build123d adapter;
masses from sources where one exists, otherwise a [A] range. Output = low / high per item and in total, one pod, worn
(pod + arm + pad + adapter). One resin density range covers both numbers in the sources (1.15 pad.py, 1.18 shell notes).
Run (fenced): systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/pod_mass.py
Writes sim/out/mech/pod_mass.json (phase2) / pod_mass_<id>.json.
K4 (2026-10-08): ULTRASONIC_DESIGN=k4 K4_DOCK=under -> volumes from hw/mech/out/k4s (run hw/mech/shell_k4.py first), dims from dims_k4. Every design also gets
centre of mass + nose/ear split (spec D18 method of sim/checks/balance.py: hinge-to-ear 100 mm, pod front at the hinge, x = distance behind the hinge).
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/mech"))
import dims as D  # noqa: E402  (selected design: phase2 -> out/r2; ULTRASONIC_DESIGN=k1/k1p -> out/k1, out/k1p)
R2 = D.OUT_DIR
CELL_PART = getattr(D, "CELL_SPEC", dict(part="Renata ICP501233PA-02", g=4.2, L=35.0, W=12.0))   # V03 08/2019 (sub-power cell block)
CELL_PART.setdefault("L", getattr(D, "CELL_L", CELL_PART.get("L")))
CELL_PART.setdefault("W", getattr(D, "CELL_W", CELL_PART.get("W")))


def stl_volume(p: Path) -> float:
    """Signed volume (mm3) of a closed STL, binary or ASCII."""
    b = p.read_bytes()
    if b[:5] == b"solid" and b"facet" in b[:400]:
        v = np.array([list(map(float, ln.split()[1:4])) for ln in b.decode().splitlines() if ln.strip().startswith("vertex")])
        tri = v.reshape(-1, 3, 3)
    else:
        n = struct.unpack("<I", b[80:84])[0]
        rec = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
        tri = rec["v"].reshape(-1, 3, 3).astype(float)
    return float(abs(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()) / 6.0)


L_EAR = 100.0        # mm hinge to ear bend (balance.py, spec D18)
PAD_X = 70.6         # mm behind the hinge: pad + exciter + NiTi (tragus-arm.md, ear-open-fit.md); sensitivity: 90 (balance.py's transducer)
POD_FRONT = D.X0     # the pod starts at the hinge (V8-thin-long.yaml K4 balance note)


def stl_centroid_x(p: Path) -> float:
    """Volume centroid x (mm, frame x) of a closed STL."""
    b = p.read_bytes()
    n = struct.unpack("<I", b[80:84])[0]
    if b[:5] == b"solid" and b"facet" in b[:400]:
        v = np.array([list(map(float, ln.split()[1:4])) for ln in b.decode().splitlines() if ln.strip().startswith("vertex")])
        tri = v.reshape(-1, 3, 3)
    else:
        rec = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
        tri = rec["v"].reshape(-1, 3, 3).astype(float)
    dv = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])) / 6.0
    return float((dv * tri[:, :, 0].sum(axis=1) / 4.0).sum() / dv.sum())


def balance(items, xs):
    """items {name: (lo, hi)}, xs {name: frame x}; returns CoM (mm behind hinge) and nose/ear split for lo and hi totals, per scope."""
    d = {k: xs[k] - POD_FRONT for k in items}
    res = {}
    for case, (ipos) in (("lo", 0), ("hi", 1)):
        m = {k: items[k][ipos] for k in items}
        tot = sum(m.values())
        com = sum(m[k] * d[k] for k in m) / tot
        nose = sum(m[k] * (1 - d[k] / L_EAR) for k in m)
        res[case] = dict(total_g=round(tot, 2), com_behind_hinge_mm=round(com, 1), nose_g=round(nose, 2), ear_g=round(tot - nose, 2))
    return res


RESIN = (1.15, 1.18)          # g/cm3: pad.py / shell notes (the two numbers in the sources)
SILICONE = (1.10, 1.20)       # [A] skin
VHB = (0.72, 0.96)            # [A] acrylic foam tape (3M TDS 4914 gives no density)
FR4 = (1.85, 1.95)            # [A]


def rng(v_mm3, dens):
    return (v_mm3 * dens[0] / 1000, v_mm3 * dens[1] / 1000)


def items_k1(v, cx, adapter):
    pcb_area = 30.0 * 12.0
    pad = json.loads((ROOT / "hw/mech/out/parts/pad/checks.json").read_text())
    pad_mass = next(c["value"] for c in pad["checks"] if c["name"].startswith("mass estimate"))
    pad_wo_exc = pad_mass["total"] - pad_mass["transducer (estimate, [Low], E1 weighs it)"]
    X = {}
    items = {
        "tub (resin, incl. heel + rail)": rng(v["tub"], RESIN),
        "lid + armour plate (resin)": rng(v["lid"], RESIN),
        "puck (resin)": rng(v["puck"], RESIN),
        "skin (silicone) [A density]": rng(v["skin"], SILICONE),
        "VHB board tape (shell_r2.vhb) [A density]": rng(v["vhb"], VHB),
        f"VHB cell tape {CELL_PART['L']:g} x {CELL_PART['W']:g} x 0.25 [A density]": rng(CELL_PART["L"] * CELL_PART["W"] * 0.25, VHB),
        "adapter clip (resin)": rng(adapter.volume, RESIN),
        f"cell {CELL_PART['part']}": (CELL_PART["g"], CELL_PART["g"]),       # datasheet weight (phase2: V03 08/2019; K1: V2-cells.yaml)
        "bare board FR-4 30x12x0.8 [A density]": rng(v["pcb"], FR4),
        "board copper (4 layers 35/15/15/35 um, 50-80 % fill) [A]": (pcb_area * 0.100 * 0.5 * 8.96 / 1000, pcb_area * 0.100 * 0.8 * 8.96 / 1000),
        "components (74 parts; QFN48, L1, mic, crystal, passives) [A]": (0.20, 0.40),
        "dock target YZT0675 (body + pogo + magnets) [A: CAD envelope x 2.0-4.0 g/cm3]": (v["dock"] * 2.0 / 1000, v["dock"] * 4.0 / 1000),
        "wires 12 x ~25 mm 30-34 AWG + arm bundle 4 x ~60 mm [A]": (0.05, 0.12),
        "solder, potting, RTV, shrink tube [A]": (0.05, 0.15),
        "pad without exciter (pad.py, resin 1.15)": (pad_wo_exc, pad_wo_exc * RESIN[1] / RESIN[0]),
        "exciter RC-BC02 [Low: E1 weighs it]": (1.0, 1.5),
        "NiTi arm wire (0.8 mm x ~25 mm, 6.45 g/cm3)": (0.08, 0.09),
    }
    keys = list(items)
    xs = dict(zip(keys[:3], [cx["tub"], cx["lid"], cx["puck"]]))
    xs[keys[3]] = cx["skin"]; xs[keys[4]] = cx["vhb"]; xs[keys[5]] = cx["cell"]; xs[keys[6]] = adapter.center().X; xs[keys[7]] = cx["cell"]
    xs[keys[8]] = xs[keys[9]] = cx["pcb"]; xs[keys[10]] = cx["parts_B"]; xs[keys[11]] = cx["dock"]
    xs[keys[12]] = xs[keys[13]] = cx["tub"]
    for k in keys[14:]:
        xs[k] = POD_FRONT + PAD_X
    return items, xs


def items_k4(v, cx, adapter):
    """K4 end-to-end pod (O33): two 6-layer boards in the stack block, 130 mAh cell. Dims from dims_k4, volumes from the shell_k4 STLs."""
    area = D.STACK_L * D.STACK_H
    pad = json.loads((ROOT / "hw/mech/out/parts/pad/checks.json").read_text())
    pad_mass = next(c["value"] for c in pad["checks"] if c["name"].startswith("mass estimate"))
    pad_wo_exc = pad_mass["total"] - pad_mass["transducer (estimate, [Low], E1 weighs it)"]
    cu = 2 * (2 * 35 + 4 * 15)             # um of copper, two boards: 2 outer 35 + 4 inner 15 each (6L)
    cu_lo, cu_hi = (area * cu / 1000 * f * 8.96 / 1000 for f in (0.5, 0.8))
    items = {
        "tub (resin, incl. heel + rail)": rng(v["tub"], RESIN),
        "lid (resin, flat 1.0)": rng(v["lid"], RESIN),
        "puck (resin)": rng(v["puck"], RESIN),
        "skin (silicone) [A density]": rng(v["skin"], SILICONE),
        "VHB stack-to-lid [A density]": rng(v["vhb"], VHB),
        "cell tape 0.10 [A density]": rng(v["ctape"], VHB),
        "adapter clip (resin)": rng(adapter.volume, RESIN),
        f"cell {D.CELL_SPEC['part']}": (D.CELL_SPEC["g"], D.CELL_SPEC["g"]),
        f"2 bare boards FR-4 {D.STACK_L:g}x{D.STACK_H:g}x{D.PCB_T:g} [A density]": rng(2 * area * D.PCB_T, FR4),
        "copper, 2 boards x 6 layers (2x35 + 4x15 um, 50-80 % fill) [A]": (cu_lo, cu_hi),
        "components + BM28 B2B (r2 74-part range) [A]": (0.20, 0.40),
        "M dock tab FR-4 (stl) + 2 N52 2.5x1 discs (0.04 g)": (v["m_tab"] * FR4[0] / 1000 + 0.04, v["m_tab"] * FR4[1] / 1000 + 0.04),
        "wires + solder + potting [A]": (0.10, 0.27),
        "pad without exciter (pad.py, resin 1.15)": (pad_wo_exc, pad_wo_exc * RESIN[1] / RESIN[0]),
        "exciter RC-BC02 [Low: E1 weighs it]": (1.0, 1.5),
        "NiTi arm wire (0.8 mm x ~25 mm, 6.45 g/cm3)": (0.08, 0.09),
    }
    k = list(items)
    xs = {k[0]: cx["tub"], k[1]: cx["lid"], k[2]: cx["puck"], k[3]: cx["skin"], k[4]: cx["vhb"], k[5]: cx["ctape"], k[6]: adapter.center().X,
          k[7]: cx["cell"], k[8]: cx["stack_body"], k[9]: cx["stack_body"], k[10]: cx["stack_body"], k[11]: cx["m_tab"], k[12]: cx["tub"]}
    for n in k[13:]:
        xs[n] = POD_FRONT + PAD_X
    return items, xs


def main():
    k4 = D.DESIGN.id.startswith("k4")
    names = (("tub", "lid", "puck", "skin", "vhb", "ctape", "cell", "pcb_top", "stack_body", "m_tab", "dock_mags", "u2_mic") if k4
             else ("tub", "lid", "puck", "skin", "vhb", "pcb", "dock", "parts_B", "cell"))
    v = {k: stl_volume(R2 / f"{k}.stl") for k in names}
    cx = {k: stl_centroid_x(R2 / f"{k}.stl") for k in names}
    import os
    keep = os.environ.get("ULTRASONIC_DESIGN")
    if k4:      # blade/pod/frame read the shell_r2 facts (D.PCB ...) that dims_k4 lacks; the adapter only needs the frame-fixed X1/Y_IN, so build it in the phase2 frame at K4's z centre
        os.environ["ULTRASONIC_DESIGN"] = "phase2"
    import blade  # build123d
    adapter = blade.adapter(zc=(D.Z0 + D.Z1) / 2)
    if keep is None:
        os.environ.pop("ULTRASONIC_DESIGN", None)
    else:
        os.environ["ULTRASONIC_DESIGN"] = keep
    v["adapter"] = adapter.volume
    items, xs = (items_k4 if k4 else items_k1)(v, cx, adapter)
    lo = sum(a for a, _ in items.values())
    hi = sum(b for _, b in items.values())
    pod_only = [k for k in items if not k.startswith(("pad", "exciter", "NiTi", "adapter"))]
    worn = balance(items, xs)
    saved = PAD_X
    globals()["PAD_X"] = 90.0                       # sensitivity: balance.py puts pad + transducer + arm at 90 mm
    items90, xs90 = (items_k4 if k4 else items_k1)(v, cx, adapter)
    bal90 = balance(items90, xs90)
    globals()["PAD_X"] = saved
    pod_items = {k: items[k] for k in pod_only}
    out = dict(src="sim/checks/pod_mass.py", date="2026-10-08", design=D.DESIGN.id, dock=getattr(D, "DOCK", None),
               volumes_mm3={k: round(x, 1) for k, x in v.items()},
               items_g={k: [round(a, 3), round(b, 3)] for k, (a, b) in items.items()},
               item_x_behind_hinge_mm={k: round(xs[k] - POD_FRONT, 1) for k in items},
               total_worn_g=[round(lo, 2), round(hi, 2)],
               pod_body_only_g=[round(sum(items[k][0] for k in pod_only), 2), round(sum(items[k][1] for k in pod_only), 2)],
               balance_worn=dict(method="sim/checks/balance.py statics: hinge-to-ear %g mm, pod front at the hinge, pad+exciter+NiTi at %g mm" % (L_EAR, PAD_X), **worn),
               balance_worn_pad_at_90=bal90, balance_pod_body_only=balance(pod_items, xs),
               pod_envelope_mm=dict(L=round(D.L, 2) if hasattr(D, "L") else None, T=getattr(D, "T", None), H=round(D.Z1 - D.Z0, 2)),
               target_g=8.0, hurts_g=15.0, d18_target_split_g=dict(nose=3.7, ear=4.1, com_mm=52),
               note="per pod; one pair = 2x. [A] items are assumed ranges; cell is the only sourced heavy item")
    od = ROOT / "sim/out/mech"
    od.mkdir(parents=True, exist_ok=True)
    (od / ("pod_mass.json" if D.DESIGN.id == "phase2" else f"pod_mass_{D.DESIGN.id}.json")).write_text(json.dumps(out, indent=1))
    for k, (a, b) in items.items():
        print(f"{a:6.3f} - {b:6.3f} g  x={xs[k] - POD_FRONT:5.1f}  {k}")
    print("TOTAL worn per side:", out["total_worn_g"], "g; pod body only:", out["pod_body_only_g"], "g; target ~8, hurts ~15")
    print("worn balance:", worn, "\n  pad at 90:", bal90, "\n  pod body only:", out["balance_pod_body_only"])


if __name__ == "__main__":
    main()
