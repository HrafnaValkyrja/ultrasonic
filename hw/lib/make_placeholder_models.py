#!/usr/bin/env python3
"""Datasheet-dimension placeholder 3D models (CHK-MODELS, 2026-10-07): our own geometry, repo licence, no vendor files.

Why: the routed board showed SW1 0.39 tall (the easyeda .wrl) vs the KMT022 datasheet 0.65, and U2's KiCad path
(Knowles_LGA-5_3.5x2.65mm.step) does not exist in the KiCad 10 library, so U2 (the tallest B part) vanished from 3D
exports, renders and the JLC 3D/DFM preview. These boxes carry the datasheet envelope (max height where a tolerance is
given) so every 3D check sees the real worst case.

    python3 hw/lib/make_placeholder_models.py   # -> hw/lib/lcsc/lcsc.3dshapes/*_placeholder.step

Sources (tools/checks/part_heights.yaml rows): SPH0641LU4H-1 Rev B-1 (2 Dec 2024) s8: 3.50 x 2.65, height 0.98 +-0.10
(modelled at the 1.08 maximum); C&K KMT0 sheet (21 Mar 2018) p.B-9: 3.0 x 2.6 body, total height 0.65 (nominal only),
4 gull-wing leads spanning the 3.8 mm pad row (lead shape not dimensioned: 0.10 thick tabs, [A]).
Frame: KiCad model frame = footprint frame, z up from the board surface; both bodies are centred on the footprint origin.
"""
from pathlib import Path

from build123d import Box, Pos, export_step

OUT = Path(__file__).resolve().parent / "lcsc" / "lcsc.3dshapes"


def mic():
    return Pos(0, 0, 1.08 / 2) * Box(2.65, 3.50, 1.08)          # SPH0641LU4H-1 at max height; x 2.65 / y 3.50 = footprint body


def kmt022():
    body = Pos(0, 0, 0.65 / 2) * Box(3.0, 2.6, 0.65)
    tabs = None
    for sx in (-1, 1):
        for sy in (-1, 1):
            t = Pos(sx * 1.7, sy * 0.925, 0.05) * Box(0.4, 0.5, 0.10)   # 1.85 pitch rows, pads span 3.8 [A shape]
            tabs = t if tabs is None else tabs + t
    return body + tabs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    export_step(mic(), str(OUT / "SPH0641LU4H-1_placeholder.step"))
    export_step(kmt022(), str(OUT / "KMT022NGJLHS_placeholder.step"))
    print("wrote", sorted(p.name for p in OUT.glob("*_placeholder.step")))


if __name__ == "__main__":
    main()
