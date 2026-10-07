#!/usr/bin/env python3
"""Pod mass roll-up for the current design (physical.md issue 8, reg-pod-body issue 10, 00-whole risk 18, spec D18).

Volumes come from the shell_r2 STLs (hw/mech/out/r2, run `python3 hw/mech/shell_r2.py` first) and the build123d adapter;
masses from sources where one exists, otherwise a [A] range. Output = low / high per item and in total, one pod, worn
(pod + arm + pad + adapter). One resin density range covers both numbers in the sources (1.15 pad.py, 1.18 shell notes).
Run (fenced): systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/checks/pod_mass.py
Writes sim/out/mech/pod_mass.json.
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
CELL_PART.setdefault("L", D.CELL_L)
CELL_PART.setdefault("W", D.CELL_W)


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


RESIN = (1.15, 1.18)          # g/cm3: pad.py / shell notes (the two numbers in the sources)
SILICONE = (1.10, 1.20)       # [A] skin
VHB = (0.72, 0.96)            # [A] acrylic foam tape (3M TDS 4914 gives no density)
FR4 = (1.85, 1.95)            # [A]


def rng(v_mm3, dens):
    return (v_mm3 * dens[0] / 1000, v_mm3 * dens[1] / 1000)


def main():
    v = {k: stl_volume(R2 / f"{k}.stl") for k in ("tub", "lid", "puck", "skin", "vhb", "pcb", "dock", "parts_B", "cell")}
    import blade  # build123d
    v["adapter"] = blade.adapter(zc=(D.Z0 + D.Z1) / 2).volume
    pad = json.loads((ROOT / "hw/mech/out/parts/pad/checks.json").read_text())
    pad_mass = next(c["value"] for c in pad["checks"] if c["name"].startswith("mass estimate"))
    pad_wo_exc = pad_mass["total"] - pad_mass["transducer (estimate, [Low], E1 weighs it)"]
    pcb_area = 30.0 * 12.0
    items = {
        "tub (resin, incl. heel + rail)": rng(v["tub"], RESIN),
        "lid + armour plate (resin)": rng(v["lid"], RESIN),
        "puck (resin)": rng(v["puck"], RESIN),
        "skin (silicone) [A density]": rng(v["skin"], SILICONE),
        "VHB board tape (shell_r2.vhb) [A density]": rng(v["vhb"], VHB),
        f"VHB cell tape {CELL_PART['L']:g} x {CELL_PART['W']:g} x 0.25 [A density]": rng(CELL_PART["L"] * CELL_PART["W"] * 0.25, VHB),
        "adapter clip (resin)": rng(v["adapter"], RESIN),
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
    lo = sum(a for a, _ in items.values())
    hi = sum(b for _, b in items.values())
    pod_only = [k for k in items if not k.startswith(("pad", "exciter", "NiTi", "adapter"))]
    out = dict(src="sim/checks/pod_mass.py", date="2026-10-07", design=D.DESIGN.id, volumes_mm3={k: round(x, 1) for k, x in v.items()},
               items_g={k: [round(a, 3), round(b, 3)] for k, (a, b) in items.items()},
               total_worn_g=[round(lo, 2), round(hi, 2)],
               pod_body_only_g=[round(sum(items[k][0] for k in pod_only), 2), round(sum(items[k][1] for k in pod_only), 2)],
               target_g=8.0, hurts_g=15.0, note="per pod; one pair = 2x. [A] items are assumed ranges; cell is the only sourced heavy item")
    od = ROOT / "sim/out/mech"
    od.mkdir(parents=True, exist_ok=True)
    (od / ("pod_mass.json" if D.DESIGN.id == "phase2" else f"pod_mass_{D.DESIGN.id}.json")).write_text(json.dumps(out, indent=1))
    for k, (a, b) in items.items():
        print(f"{a:6.3f} - {b:6.3f} g  {k}")
    print("TOTAL worn per side:", out["total_worn_g"], "g; pod body only:", out["pod_body_only_g"], "g; target ~8, hurts ~15")


if __name__ == "__main__":
    main()
