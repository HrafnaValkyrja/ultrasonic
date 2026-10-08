"""Route one K4 board (P or M) that place_k4.py already built: FreeRouting twice (second pass from the routed board, keep
the better), the same import/cleanup/DRC as place_r2.route(). LEAD SESSION ONLY, one board at a time, fenced:

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 \
        python3 hw/pod/route_k4.py P|M [--layers 6] [--fr-args "..."]

Reads hw/pod/k4/out/<B>/placed.kicad_pcb; writes routed.kicad_pcb, drc.json, route.json in the same folder.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import place_r2 as R2  # noqa: E402

mm = pcbnew.FromMM


def fr(dsn, ses, extra):
    subprocess.run([os.environ["FREEROUTING_JAVA"], *os.environ.get("FREEROUTING_JAVA_OPTS", "-Xmx1g").split(),
                    "-jar", os.environ["FREEROUTING_JAR"], "-de", str(dsn), "-do", str(ses), "-mp", "200",
                    "--gui.enabled=false", *extra], check=True, timeout=3000,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", choices=["P", "M"])
    ap.add_argument("--fr-args", default="")
    ap.add_argument("--layers", type=int, default=4, help="6 = add In3/In4 as signal layers (planes stay In1 GND, In2 +3V0)")
    a = ap.parse_args()
    out = HERE / "k4" / "out" / a.board
    extra = a.fr_args.split()
    if a.layers != 4:                               # rewrite placed.kicad_pcb with more copper layers before routing
        b0 = pcbnew.LoadBoard(str(out / "placed.kicad_pcb"))
        b0.SetCopperLayerCount(a.layers)
        pcbnew.SaveBoard(str(out / "placed.kicad_pcb"), b0)
    b = pcbnew.LoadBoard(str(out / "placed.kicad_pcb"))
    b.GetDesignSettings().m_NetSettings.GetDefaultNetclass().SetClearance(mm(R2.ROUTE_CLEARANCE))
    dsn, ses = out / "board.dsn", out / "board.ses"
    assert pcbnew.ExportSpecctraDSN(b, str(dsn))
    fr(dsn, ses, extra)
    target = out / "routed.kicad_pcb"
    pcbnew.SaveBoard(str(target), R2._import(out, ses))
    first = R2._drc(target, out / "drc.json")
    bt = pcbnew.LoadBoard(str(target))
    bt.GetDesignSettings().m_NetSettings.GetDefaultNetclass().SetClearance(mm(R2.ROUTE_CLEARANCE))
    dsn2, ses2 = out / "board2.dsn", out / "board2.ses"
    assert pcbnew.ExportSpecctraDSN(bt, str(dsn2))
    fr(dsn2, ses2, extra)
    b2 = R2._import(out, ses2)
    t2 = out / "routed2.kicad_pcb"
    pcbnew.SaveBoard(str(t2), b2)
    second = R2._drc(t2, out / "drc2.json")
    score = lambda r: (len(r["unconnected"]), sum(r["drc_by_type"].values()))  # noqa: E731
    if score(second) < score(first):
        pcbnew.SaveBoard(str(target), b2)
        (out / "drc.json").write_text((out / "drc2.json").read_text())
        best = second
    else:
        best = first
    best["passes"] = {"first": score(first), "second": score(second)}
    (out / "route.json").write_text(json.dumps(best, indent=1))
    print(json.dumps({"board": a.board, "unconnected": len(best["unconnected"]), "drc": best["drc_by_type"],
                      "tracks": best["tracks"], "vias": best["vias"], "passes": best["passes"]}))


if __name__ == "__main__":
    main()
