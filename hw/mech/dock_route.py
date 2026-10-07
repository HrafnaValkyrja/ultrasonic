#!/usr/bin/env python3
"""Dock-wire route, belly target -> rear B pads, in BOTH pods (sub-dock-usb DK-05, physical issues 3/15, reg-board 5).

One board serves both pods (O16-5); the left pod's shell is the mirror of the right, so in each pod's own frame the
shell is identical and only the board flips: pod z = PCB z0 + by (right, = dims_r2.bpt) or PCB z0 + (12 - by) (left).
Right pod: dock pads (board y 1.7-6.55) sit LOW, arm pads (y 7.7-9.9) HIGH. Left pod: they swap.
Wires (DK-16, 2026-10-07): VBUS/GND 32 AWG enamel OD 0.249, D+/D-/CC 36 AWG OD 0.160, laid as a flat ribbon.
Route (closed lid, centrelines): tails' ends at the target's rear end [A: x 52.9, y 9.15, the 5-pin row; DK-02/03 open]
-> under the cell (z -8.5, between the cavity floor -8.9 and the cell bottom -8.1) -> rear gap behind the cell
(x 65.85, the cell-side half of the 1.1 gap; the arm bundle owns the wall side x 66.2-66.4) -> climb to the pad's z,
then up in y to EDGE_Y 11.55 -> forward under the board's rear edge (x 60.55) -> pad.
Arm bundle: heel.wire_route() (right pod, modelled there); left pod = exit -> wall-side rear gap at the exit z -> up in
y to 11.55 -> fan to the (now low) arm pads [derived sketch, heel.py does not model the left pod].
Checks: min surface clearance dock wire <-> arm bundle/wires, <-> cell (must stay >= 0), inside the cavity, lengths.
Run (fenced): systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 hw/mech/dock_route.py
Writes hw/mech/out/dock_route.json and docs-side PNG sim/out/mech/dock_route.png (dark).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import dims as D  # noqa: E402  (selected design: dims_r2 | dims_k1)

PCB, CELL, CAV = D.PCB, D.CELL, D.CAV
EDGE_Y = PCB["y0"] - 0.55              # phase2 11.55 (B face 12.1); relative since 2026-10-07 (K1 variant)
DOCK_PADS = {"J3": ("DOCK_VBUS", 25.1, 1.7, 0.249), "J4": ("GND", 27.0, 1.9, 0.249), "J12": ("CC", 27.0, 4.35, 0.160),
             "J10": ("USB_DP", 28.9, 5.5, 0.160), "J11": ("USB_DN", 27.0, 6.55, 0.160)}      # placement.yaml 2026-10-07
ARM_PADS = {"J1": 9.9, "J7": 7.7, "J2": 10.95, "J8": 8.75}                                   # placement.yaml 2026-10-07 (info only; routes come from heel.wire_route)
ARM_X = {"J1": 28.9, "J7": 28.9, "J2": 27.0, "J8": 27.0}
BUNDLE_D, ARM_WIRE_OD = 0.51, 0.21
CH_EXIT = np.array([66.20, 5.15, -5.50])
X_DOCK_GAP = 65.85                    # dock ribbon in the rear gap, cell side (cell rear face 65.6)
X_ARM_GAP = 66.40                     # arm bundle against the rear wall (heel.py)
TAIL = np.array([round(D.DOCK["x1"] + 0.2, 3), 9.15, -8.5])   # [A] tails end, 5-pin row centre (phase2 52.9)
Y_HI = PCB["y0"] + 0.45               # ribbon level in the stowage behind the board (phase2 12.55: cell top 10.7, lid inner 13.2)
S_BEHIND = min(1.0, (X_DOCK_GAP - PCB["x1"]) / 5.3)   # 1 in phase2; a shorter pod (K1) compresses the climb zone
X_UP = PCB["x1"] + max(4.05 * S_BEHIND, 1.5)   # first wire's climb line (x), behind the board's rear edge (phase2 64.6 vs 60.55);
# K1: 5 wires at the fixed 0.3 pitch need 1.2 + edge clearance -> x1 + 1.5 (over the cell's rear edge, above the cell top)
SUFFIX = "" if D.DESIGN.id in ("phase2", "revg") else f"_{D.DESIGN.id}"   # NON-DEFAULT variants write their own outputs


def pz(by, pod):
    return PCB["z0"] + (by if pod == "right" else 12.0 - by)


def dense(pts, step=0.05):
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(int(np.linalg.norm(b - a) / step), 1)
        out += [a + t * (b - a) for t in np.linspace(0, 1, n, endpoint=False)]
    return np.array(out + [pts[-1]])


def plen(pts):
    return float(sum(np.linalg.norm(b - a) for a, b in zip(pts[:-1], pts[1:])))


def dock_wire(ref, k, pod):
    net, bx, by, od = DOCK_PADS[ref]
    z = pz(by, pod)
    y_rib = TAIL[1] - 0.52 + 0.26 * k                   # ribbon position across y (flat, 0.26 pitch >= the 0.249 OD)
    pad = np.array([PCB["x0"] + bx, PCB["y0"] - od / 2, z])
    # v2 (2026-10-07, clearance >= 0.3): climb in y while LOW (z -8.5, ~3 mm under the arm exit height), then climb in z
    # above the cell top in the stowage behind the board (y Y_HI, between the cell top 10.7 and the lid 13.2), where the
    # arm bundle never is (it runs at y <= 11.6); come down to EDGE_Y only at the pad's own z.
    x_up = X_UP - 0.3 * k                                                                    # ribbon spread in x while climbing in z
    pts = [np.array([TAIL[0], y_rib, TAIL[2]]), np.array([X_DOCK_GAP, y_rib, TAIL[2]]),     # under the cell
           np.array([X_DOCK_GAP, Y_HI, TAIL[2]]),                                           # up the rear gap in y, low
           np.array([x_up, Y_HI, TAIL[2]]),                                                 # forward over the cell's rear-top edge
           np.array([x_up, Y_HI, z]),                                                       # climb to the pad's z, above the cell
           np.array([PCB["x1"] + 0.3, EDGE_Y, z]), np.array([PCB["x1"], EDGE_Y, z]),        # down to the edge level at the pad's z
           np.array([pad[0] + 0.5, pad[1], z]), pad]
    return dict(net=net, od=od, pts=pts)


def arm_route(pod):
    if True:   # heel.py models both pods since 2026-10-07 (ARM-LEFT)
        import heel   # noqa: F401  (build123d import; only the polylines are used)
        b, w = heel.wire_route(pod)
        return np.array(b), {k: np.array(v["pts"]) for k, v in w.items()}
    fan = np.array([62.3, 11.60, -4.6])
    bundle = [CH_EXIT, np.array([X_ARM_GAP, 6.3, CH_EXIT[2]]), np.array([X_ARM_GAP, 11.55, CH_EXIT[2]]), fan]
    wires = {}
    for ref, by in ARM_PADS.items():
        z = pz(by, pod)
        pad = np.array([PCB["x0"] + ARM_X[ref], PCB["y0"] - ARM_WIRE_OD / 2, z])
        wires[ref] = np.array([fan, np.array([PCB["x1"], EDGE_Y, z]), np.array([pad[0] + 0.5, pad[1], z]), pad])
    return np.array(bundle), wires


def min_d(a, b):
    A, B = dense(list(a)), dense(list(b))
    d = np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(-1))
    i, j = np.unravel_index(np.argmin(d), d.shape)
    return float(d[i, j]), A[i], B[j]


def box_clear(P, b):
    """Signed distance from points to a box surface: >0 outside."""
    q = np.maximum(np.stack([b["x0"] - P[:, 0], P[:, 0] - b["x1"]], 1).max(1), -1e9)
    dx = np.maximum(np.maximum(b["x0"] - P[:, 0], P[:, 0] - b["x1"]), 0)
    dy = np.maximum(np.maximum(b["y0"] - P[:, 1], P[:, 1] - b["y1"]), 0)
    dz = np.maximum(np.maximum(b["z0"] - P[:, 2], P[:, 2] - b["z1"]), 0)
    out = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    inside = (dx == 0) & (dy == 0) & (dz == 0)
    pen = np.minimum.reduce([P[:, 0] - b["x0"], b["x1"] - P[:, 0], P[:, 1] - b["y0"], b["y1"] - P[:, 1], P[:, 2] - b["z0"], b["z1"] - P[:, 2]])
    del q
    return np.where(inside, -pen, out)


def main():
    res = {"date": "2026-10-07", "assumptions": {"tail_end": TAIL.tolist(), "ribbon_pitch": 0.26, "route": "v2 y-first (climb in z above the cell, behind the board)", "x_dock_gap": X_DOCK_GAP,
                                                 "arm_route": "heel.wire_route(pod), both pods"}}
    curves = {}
    for pod in ("right", "left"):
        bundle, arms = arm_route(pod)
        r = {}
        for k, ref in enumerate(DOCK_PADS):
            w = dock_wire(ref, k, pod)
            P = dense(w["pts"])
            rw = w["od"] / 2
            cb, _, _ = min_d(w["pts"], bundle)
            ca = min(min_d(w["pts"], v)[0] - ARM_WIRE_OD / 2 for v in arms.values())
            cell_c = float(box_clear(P, CELL).min()) - rw
            # inside the cavity: distance to the cavity walls (points must be inside: -box_clear = depth)
            cav_in = float((-box_clear(P[:-1], CAV)).min()) - rw
            r[ref] = dict(net=w["net"], od=w["od"], pad_z=round(pz(DOCK_PADS[ref][2], pod), 2), length_mm=round(plen(w["pts"]), 1),
                          clear_to_arm_bundle=round(cb - BUNDLE_D / 2 - rw, 3), clear_to_arm_wires=round(ca - rw, 3),
                          clear_to_cell=round(cell_c, 3), clear_to_cavity_walls=round(cav_in, 3))
            curves[(pod, ref)] = w["pts"]
        # lid opened 180 deg about the rear seam edge (x CAV x1, y Y_SPLIT): the board lands mirrored behind the pod, B up.
        # Wire from its last tub anchor (taped at the cell's rear-top edge, point 3 of the route) to the seam edge, then
        # straight to the mirrored pad. Extra length needed vs closed = service loop (DBG-17).
        x_h, y_h = CAV["x1"], D.Y_SPLIT
        for k2, ref in enumerate(DOCK_PADS):
            pts = curves[(pod, ref)]
            anchor = pts[2]
            closed_from_anchor = plen(pts[2:])
            q = pts[-1]
            qm = np.array([2 * x_h - q[0], q[1], q[2]])
            open_len = float(np.linalg.norm(np.array([x_h, y_h, anchor[2]]) - anchor) + np.linalg.norm(qm - np.array([x_h, y_h, anchor[2]])))
            r[ref]["lid_open_extra_mm"] = round(open_len - closed_from_anchor, 1)
        worst = {k: min(v[k] for v in r.values()) for k in ("clear_to_arm_bundle", "clear_to_arm_wires", "clear_to_cell", "clear_to_cavity_walls")}
        worst["service_loop_needed_mm"] = max(v["lid_open_extra_mm"] for v in r.values())
        res[pod] = dict(wires=r, worst=worst, pass_all=all(v >= 0.0 for k, v in worst.items() if k.startswith("clear")),
                        arm_pads_z=[round(pz(by, pod), 2) for by in ARM_PADS.values()])
        curves[(pod, "bundle")] = bundle
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / f"dock_route{SUFFIX}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import plotstyle
        plotstyle.apply()
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
        for ax, pod in zip(axs, ("right", "left")):
            ax.add_patch(Rectangle((CELL["x0"], CELL["z0"]), CELL["x1"] - CELL["x0"], CELL["z1"] - CELL["z0"], fc="#3a3f4b", ec="none", label="cell"))
            ax.add_patch(Rectangle((CAV["x0"], CAV["z0"]), CAV["x1"] - CAV["x0"], CAV["z1"] - CAV["z0"], fc="none", ec="#8f96a3", lw=0.8, label="cavity"))
            ax.add_patch(Rectangle((PCB["x0"], PCB["z0"]), PCB["x1"] - PCB["x0"], PCB["z1"] - PCB["z0"], fc="none", ec="#6fa8dc", lw=0.8, ls="--", label="board (above)"))
            b = curves[(pod, "bundle")]
            ax.plot(b[:, 0], b[:, 2], lw=3, color="#e69138", label="arm bundle")
            for ref in DOCK_PADS:
                p = np.array(curves[(pod, ref)])
                ax.plot(p[:, 0], p[:, 2], lw=1.2, label=f"{ref} {DOCK_PADS[ref][0]}")
            ax.set_xlim(50, 67.5)
            ax.set_ylim(-9.5, 4.5)
            ax.set_aspect("equal")
            ax.set_title(f"{pod} pod: dock wires (side view x-z; worst arm clearance {res[pod]['worst']['clear_to_arm_bundle']:.2f} mm)")
            ax.set_xlabel("pod x (mm)")
            ax.set_ylabel("pod z (mm)")
        axs[1].legend(fontsize=7, loc="upper left")
        fig.tight_layout()
        od = ROOT / "sim/out/mech"
        od.mkdir(parents=True, exist_ok=True)
        fig.savefig(od / f"dock_route{SUFFIX}.png", dpi=130)
    except Exception as e:  # noqa: BLE001
        print("plot skipped:", e)


if __name__ == "__main__":
    main()
