"""CAD-free dimensions of the K1 pod variant (packet Q1, NON-DEFAULT; synthesis K1, docs/research/drastic/synthesis.md).

    ULTRASONIC_DESIGN=k1  python3 hw/mech/shell_r2.py     # no armour plate, lid 1.0 (synthesis K1: "plate off")
    ULTRASONIC_DESIGN=k1p python3 hw/mech/shell_r2.py     # plate kept: lid 0.8 + plate 0.7 (Phase-2 lid stack)

Same Phase-2 board (unchanged), same frame anchors (heel E, rail, strut relief: the rear face X1 stays at 67.5),
different cell: Renata ICP401230UPR 130 mAh (125 min), PCM + AWG30 wires, envelope max T 4.5 x W 12.7 x L 31.0
(datasheet "ICP401230 V02 08/2019", read 2026-10-07 in docs/research/drastic/V2-cells.yaml; swelling inclusion unknown).
This file overrides ONLY what the cell (and the plate choice) changes; every other number and every derived value
comes from hw/mech/dims_r2.py, executed here with _OVERRIDES (its variant hook). The design id picks the lid stack:
argument-free, from tools/current.py (env ULTRASONIC_DESIGN or hw/current.yaml), default k1.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

CELL_SPEC = dict(part="Renata ICP401230UPR", mAh=130, mAh_min=125, g=3.5, T=4.5, W=12.7, L=31.0,
            src="docs/research/drastic/V2-cells.yaml (datasheet ICP401230 V02 08/2019, read 2026-10-07)")
VARIANTS = {
    "k1": dict(LID_T=1.0, PLATE_T=0.0, note="plate off, lid 1.0 (synthesis K1 R4 trim, walls kept 0.8)"),
    "k1p": dict(LID_T=0.8, PLATE_T=0.7, note="plate kept: Phase-2 lid 0.8 + armour plate 0.7"),
}


def _variant():
    want = (os.environ.get("ULTRASONIC_DESIGN") or "").strip().lower()
    return want if want in VARIANTS else "k1"


VARIANT = _variant()
_OVERRIDES = dict(CELL_T=CELL_SPEC["T"], CELL_W=CELL_SPEC["W"], CELL_L=CELL_SPEC["L"],
                  **{k: v for k, v in VARIANTS[VARIANT].items() if k != "note"})

_DOC = __doc__
exec(compile((HERE / "dims_r2.py").read_text(), str(HERE / "dims_r2.py"), "exec"), globals())   # noqa: S102  (variant hook)
__doc__ = _DOC                         # the exec set dims_r2's docstring; CELL is now the cell BOX (CELL_SPEC = the part)
