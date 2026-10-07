"""Local re-route of the Phase-2 board: apply placement.yaml moves to an already routed board, rip only what the moves touch,
lock everything else, and let FreeRouting route just the ripped nets (2026-10-07, B-DOC-AUDIT-0007).

Why: a full place_r2 --route of the edited placement left 2-7 boxed-in escapes (U1 pins 10/11/27/28/33, U3 ball A1) on
every variant tried; the committed board's routing elsewhere is proven (DRC 0, all LN metrics pass), so keep it.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=4G -p MemorySwapMax=0 \
        python3 hw/pod/local_reroute.py ROUTED_IN.kicad_pcb PLACEMENT.yaml OUT_DIR [--rip NET ...]

Steps: (1) move every footprint whose placement row differs from the board; (2) rip every signal net with a pad on a moved
part (all its tracks + vias), plus --rip nets; for the plane nets GND/+3V0 rip only the stubs ending in a moved pad and the
vias they leave dangling; (3) add place_r2's mic-port keep-out rule area and pre-routes (LSE, VDDA, NRST, corner via) and rip
any F copper / via inside the keep-out; (4) lock all remaining copper, export DSN, FreeRouting, import (locked copper is
kept), restore the lock state; (5) write OUT_DIR/placed.kicad_pcb (input to the route) and OUT_DIR/routed.kicad_pcb.
Then run the usual post-route chain (close_gaps, fb_bridge, kelvin_r21, silk) and DRC.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

import pcbnew
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import place_r2 as R2  # noqa: E402

mm, MM = pcbnew.FromMM, pcbnew.ToMM
PLANE = {"GND", "+3V0"}


def main():
    src, plc, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    extra = sys.argv[sys.argv.index("--rip") + 1:] if "--rip" in sys.argv else []
    out.mkdir(parents=True, exist_ok=True)
    place = yaml.safe_load(open(plc))
    b = pcbnew.LoadBoard(str(src))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    moved, old_pads = [], []
    for ref, (x, y, rot, side) in place.items():
        f = fps[ref]
        fx, fy = MM(f.GetPosition().x), MM(f.GetPosition().y)
        frot = f.GetOrientationDegrees()
        want = rot if side == "F" else (180 - rot) % 360       # KiCad reports a flipped part's angle mirrored
        if abs(fx - x) > 1e-3 or abs(fy - y) > 1e-3 or abs(((frot - want + 180) % 360) - 180) > 0.01:
            moved.append(ref)
            old_pads += [(p.GetNetname(), R2.R1._rect(p)) for p in f.Pads()]
            f.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            f.SetOrientationDegrees(want)
    print("moved", moved)
    rip = {p.GetNetname() for r in moved for p in fps[r].Pads() if p.GetNetname() and p.GetNetname() not in PLANE} | set(extra)
    gone = 0
    for t in list(b.GetTracks()):
        if t.GetNetname() in rip and not t.IsLocked():
            b.Delete(t); gone += 1
    # plane nets: stubs that end inside a moved part's old pad, then vias left with no track
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_TRACK" and t.GetNetname() in PLANE:
            ends = [(MM(q.x), MM(q.y)) for q in (t.GetStart(), t.GetEnd())]
            if any(n == t.GetNetname() and R2.R1._d_rect(x, y, r) < 1e-3 for n, r in old_pads for x, y in ends):
                b.Delete(t); gone += 1
    for v in [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() in PLANE]:
        p = v.GetPosition()
        tied = any(t.GetClass() == "PCB_TRACK" and t.GetNetCode() == v.GetNetCode() and (t.GetStart() == p or t.GetEnd() == p)
                   for t in b.GetTracks())
        new_hit = any(R2.R1._d_rect(MM(p.x), MM(p.y), R2.R1._rect(q)) < R2.VIA_D / 2 + 0.12
                      for r in moved for q in fps[r].Pads() if q.GetNetname() != v.GetNetname())
        if not tied and (new_hit or any(R2.R1._d_rect(MM(p.x), MM(p.y), r) < 0.6 for _, r in old_pads)):
            b.Delete(v); gone += 1
    print("ripped nets", sorted(rip), "items", gone)
    px, py = R2.port_xy(fps)
    R2.port_keepout(b, px, py)
    ko = []
    for t in list(b.GetTracks()):
        if (t.GetClass() == "PCB_VIA" or t.IsOnLayer(pcbnew.F_Cu)) and R2._copper_dist(t, px, py) < R2.PORT_KEEPOUT:
            ko.append(t.GetNetname())
    for n in set(ko):                                   # rip the whole net that enters the keep-out
        for t in list(b.GetTracks()):
            if t.GetNetname() == n and not t.IsLocked():
                b.Delete(t)
    print("keep-out ripped", sorted(set(ko)))
    # pre-routes: first rip unlocked copper of other nets in their way (plane nets: the item; signal nets: the whole net)
    R2.preroute(b, fps)
    pre = [t for t in b.GetTracks() if t.IsLocked()]
    hit = set()
    for t in list(b.GetTracks()):
        if t.IsLocked():
            continue
        for q in pre:
            if q.GetNetCode() != t.GetNetCode() and any(
                    t.IsOnLayer(l) and q.IsOnLayer(l) and t.GetEffectiveShape(l).Collide(q.GetEffectiveShape(l), mm(R2.ROUTE_CLEARANCE))
                    for l in (pcbnew.F_Cu, pcbnew.B_Cu)):
                hit.add(t.GetNetname()) if t.GetNetname() not in PLANE else None
                b.Delete(t)
                break
    for t in list(b.GetTracks()):
        if t.GetNetname() in hit and not t.IsLocked():
            b.Delete(t)
    for t in pre:                                       # re-lay so the clearance check runs against the cleaned board
        b.Delete(t)
    bad = R2.preroute(b, fps)
    print("preroute", bad or "clear", "ripped for pre-routes", sorted(hit))
    # plane fan-out for the moved parts' GND / +3V0 pads (legal via + stub, close_gaps rules, outside the port keep-out)
    import close_gaps as C
    added, missed = 0, []
    for r in moved:
        for p in fps[r].Pads():
            n = p.GetNetname()
            if n not in PLANE:
                continue
            c = (MM(p.GetPosition().x), MM(p.GetPosition().y))
            if any(t.IsLocked() and t.GetNetname() == n and (MM(t.GetStart().x), MM(t.GetStart().y)) == c for t in b.GetTracks()
                   if t.GetClass() == "PCB_TRACK"):
                continue                                # already tied by a pre-route
            lay = pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu
            ok = False
            for spot, need, _ in C.via_spots(b, p.GetNetCode(), (*c, {lay}), radii=(0.45, 0.6, 0.8, 1.0)):
                if not need or math.hypot(spot[0] - px, spot[1] - py) < R2.PORT_KEEPOUT + R2.VIA_D / 2 + 0.05:
                    continue
                if any(R2.R1._d_rect(spot[0], spot[1], R2.R1._rect(q)) < R2.VIA_D / 2 + 0.05 for f in fps.values() for q in f.Pads()):
                    continue                            # no via in any pad
                if C.try_via(b, p.GetNetCode(), spot) and C.try_segment(b, p.GetNetCode(), lay, c, spot):
                    added += 1; ok = True
                    break
            if not ok:
                missed.append(f"{r}.{p.GetNumber()}")
    print("fan-out vias", added, "missed", missed)
    was_locked = {t.m_Uuid.AsString() for t in b.GetTracks() if t.IsLocked()}
    for t in b.GetTracks():
        t.SetLocked(True)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    placed = out / "placed.kicad_pcb"
    pcbnew.SaveBoard(str(placed), b)
    dsn, ses = out / "local.dsn", out / "local.ses"
    b.GetDesignSettings().m_NetSettings.GetDefaultNetclass().SetClearance(mm(R2.ROUTE_CLEARANCE))
    assert pcbnew.ExportSpecctraDSN(b, str(dsn))
    subprocess.run([os.environ["FREEROUTING_JAVA"], *os.environ.get("FREEROUTING_JAVA_OPTS", "-Xmx1g").split(), "-jar",
                    os.environ["FREEROUTING_JAR"], "-de", str(dsn), "-do", str(ses), "-mp", "200", "--gui.enabled=false"],
                   check=True, timeout=3000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = pcbnew.LoadBoard(str(placed))
    assert pcbnew.ImportSpecctraSES(r, str(ses))
    for t in r.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(0.1):
            t.SetWidth(mm(0.1))
        t.SetLocked(t.m_Uuid.AsString() in was_locked)
    pcbnew.ZONE_FILLER(r).Fill(r.Zones())
    r.GetDesignSettings().m_NetSettings.GetDefaultNetclass().SetClearance(mm(0.09))
    pcbnew.SaveBoard(str(out / "routed.kicad_pcb"), r)
    print("routed ->", out / "routed.kicad_pcb")


if __name__ == "__main__":
    main()
