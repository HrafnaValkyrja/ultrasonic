"""Pod size and mass budget: parametric scenarios calibrated on the rev-1 shell (read-only study, 2026-10-02).

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 sim/checks/size_budget.py

What it does
- Rebuilds the outer body of hw/mech/shell_r1.py (main box + belly, 1.0 mm chamfers) from five stack-ups (x, y, z, belly) and
  reports the outer-envelope volume. Calibration: S0 reproduces shell_r1's body volume (7263.2 mm3) exactly.
- Adds the armour plate (area 540.3 mm2 x thickness) and the spine (159.6 mm3) to get the displayed envelope.
- Mass: resin shell = 0.8685 x wall x outer area (+ rail, lip, ribs, plate, heel, spine) x 1.18 g/cm3, minus the dock window;
  cell, board (+0.36 g parts), dock target 0.9 g [derived, unverified], adapter 417 mm3 x 1.18, pad 2.19 g (pad checks.json), misc 0.5 g.
- Balance: nose/ear split of one pod, hinge to ear bend 100 mm (sim/checks/balance.py convention).
Every scenario parameter is a rule in docs/research/simplify/size.md. Numbers are derived, not measured.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hw" / "mech"))
from build123d import Box, Pos, chamfer  # noqa: E402

RHO = 1.18e-3                      # g/mm3 resin (reg-pod-body)
T_EQ = 0.8685                      # wall volume = T_EQ x wall x outer area (1693.3 / (0.8 x 2435.9), calibrated on shell_r1)
FIXED_SHELL = 148.5 + 38.7 + 57.8  # dovetail rail, lid lip, clamp ribs (mm3)
HEEL, SPINE, PLATE_AREA = 190.8, 159.6, 540.3
DOCKS = {                          # target thickness, stack behind its back face to the cell bottom, belly length, mass
    "as_built":    dict(t=2.8, tail=2.3, L=25.5, g=0.9),    # 2.0 mm tails + 0.3
    "flat_tails":  dict(t=2.8, tail=0.85, L=25.5, g=0.9),   # tails bent flat / trimmed + wire
    "flat_noUSBC": dict(t=2.8, tail=0.85, L=23.2, g=0.9),
    "thin":        dict(t=2.0, tail=0.75, L=24.0, g=0.8),   # YZ103915020T-04025-02
}


def _box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


_cache = {}


def body(L, T, H, belly_L, belly_d, cham=1.0):
    key = tuple(round(v, 3) for v in (L, T, H, belly_L, belly_d))
    if key not in _cache:
        m = chamfer(_box(0, L, 0, T, 0, H).edges(), cham)
        if belly_d > 0:
            m = m + chamfer(_box(0, belly_L, 0, T, -belly_d, 1.5).edges(), cham)
        _cache[key] = m
    return _cache[key]


def scenario(name, cell_L=35.0, cell_T=5.3, cell_H=12.0, cell_g=4.2, board_L=34.0, board_H=13.0, wall=0.8,
             y_bgap=1.4, y_fgap=1.5, lid_wall=1.0, plate=0.7, dock="as_built", rear_gap=1.1, z_gap=0.3,
             board_t=0.8, s_fixed=None):
    """s_fixed: slack kept under the cell (0.8 today: the strut-relief fill clears the cell corner by only 0.07 mm)."""
    d = DOCKS[dock]
    L = 2 * wall + 0.3 + cell_L + rear_gap
    T_body = wall + 0.3 + cell_T + y_bgap + board_t + y_fgap + lid_wall
    cav_z = max(board_H + 2 * z_gap, cell_H + 0.6) if s_fixed is None else max(board_H + 2 * z_gap, cell_H + s_fixed + 0.1)
    H = 2 * wall + cav_z
    s_under = s_fixed if s_fixed is not None else (cav_z - cell_H) / 2
    belly_d = max(0.0, d["t"] + d["tail"] - (wall + s_under))
    b = body(L, T_body, H, d["L"], belly_d)
    v_plate = PLATE_AREA * plate
    v_env = b.volume + v_plate + SPINE
    walls = T_EQ * wall * b.area + (lid_wall - wall) * T_EQ * (L * H)
    shell_g = (walls + FIXED_SHELL + v_plate + HEEL + SPINE - 121.0) * RHO     # -121: dock window 21.4 x 7.06 x 0.8
    board_g = board_L * board_H * board_t * 1.85e-3 + 0.36
    parts = [("cell", cell_g, 29.5 + wall + 0.3 + cell_L / 2), ("shell", shell_g, 49.4), ("board+parts", board_g, 30.6 + board_L / 2),
             ("dock", d["g"], 42.1), ("adapter", 417.0 * RHO, 48.0), ("pad", 2.19, 70.6), ("misc", 0.5, 48.0)]
    m = sum(p[1] for p in parts)
    nose = sum(g * (1 - x / 100.0) for _, g, x in parts)
    return dict(name=name, L=round(L, 2), T=round(T_body + plate, 2), H=round(H, 2), belly_d=round(belly_d, 2), belly_L=d["L"],
                z_total=round(H + belly_d, 2), v_body=round(b.volume), v_env=round(v_env), shell_g=round(shell_g, 2),
                mass_g=round(m, 2), nose_g=round(nose, 2), ear_g=round(m - nose, 2), board_area=board_L * board_H,
                from_temple_outer=round(1.8 + T_body + plate, 2), s_under=round(s_under, 2))


if __name__ == "__main__":
    core = dict(board_H=12.0, board_L=26.0, y_bgap=1.4, y_fgap=1.15, lid_wall=0.8, s_fixed=0.8)
    S = [
        scenario("S0 as drawn"),
        scenario("S1 core (SIZ-01,02,03,04,06)", dock="flat_tails", **core),
        scenario("S2 S1 - plate (lid 1.0) - USB-C keep-out (SIZ-05,07)", dock="flat_noUSBC", plate=0.0, **{**core, "lid_wall": 1.0}),
        scenario("S3 S2 with thin target (SIZ-08)", dock="thin", plate=0.0, **{**core, "lid_wall": 1.0}),
        scenario("S4 S1 + 130 mAh (SIZ-12)", dock="flat_tails", cell_L=31.0, cell_T=4.5, cell_H=12.7, cell_g=3.5, **core),
        scenario("S5 S1 + walls 0.6 (SIZ-11)", dock="flat_tails", wall=0.6, **{**core, "lid_wall": 0.6}),
        scenario("S6 max: S3 + walls 0.7", dock="thin", plate=0.0, wall=0.7, **{**core, "lid_wall": 0.7}),
    ]
    for r in S:
        print(json.dumps(r))
