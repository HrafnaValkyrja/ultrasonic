#!/usr/bin/env python3
"""K4 two-board interface/BOM checks (interfaces.py and bom_check.py are single-board, 4L/one-netlist tools: they cannot read P+M).
    source tools/env.sh && python3 tools/checks/k4_checks.py [--json]
Per board X in {P, M}, against its own pod_k4_X.net and bom_jlc_X.csv:
  refs      board refs == netlist refs (board-only: fiducials/NPTH holes)
  nets      every board pad's net == the netlist net of that pin (cross-board nets stay split at the BM28 J20/J21)
  jlc-bom   bom_jlc_X.csv designators == board refs that are assembled (not board-only / excluded from BOM)
  union     P and M together hold every part of the full circuit exactly once (hw/pod/k4/gen.py partition), J20/J21 mate pin for pin
  outline   Edge.Cuts x-extent of both boards == dims_k4.STACK_L (+/-0.1), same H 12
  mic-port  U2's NPTH on M == dims_k4.MIC board point (1.75, 6.0) +/-0.05
  gnd/tie   every BM28 contact net on J20 equals the net on J21 pad-for-pad
NOT covered (interfaces.py had them for Phase 2): part heights vs the stack bands, clamp bands, switch plunger, rails/pins contract: see docs/research/drastic/V9-k4-board.yaml k4_post_route.
Exit 1 on any FAIL."""
import json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools")); sys.path.insert(0, str(REPO / "sim/noise")); sys.path.insert(0, str(REPO / "hw/mech"))
import pcbnew  # noqa: E402
import dims_k4 as D  # noqa: E402
from pcbgeom import read_netlist  # noqa: E402
K = REPO / "hw/pod/k4"; NM = 1e-6
res = []
def R(st, cid, msg): res.append((st, cid, msg)); print(f"{st} {cid} {msg}")
brd, refs, pads, nl, nlrefs = {}, {}, {}, {}, {}
for b in "PM":
    brd[b] = pcbnew.LoadBoard(str(K / f"routed_{b}.kicad_pcb"))
    refs[b] = {f.GetReference(): f for f in brd[b].GetFootprints()}
    nl[b] = read_netlist(str(K / f"pod_k4_{b}.net"))
    nlrefs[b] = {r for r, _ in nl[b]}
    pads[b] = {(f.GetReference(), p.GetNumber()): p.GetNetname() for f in brd[b].GetFootprints() for p in f.Pads() if p.GetNetname()}
for b in "PM":
    bo = {r for r, f in refs[b].items() if f.IsBoardOnly()}
    ex, mi = sorted(set(refs[b]) - bo - nlrefs[b]), sorted(nlrefs[b] - set(refs[b]))
    R("PASS" if not ex and not mi else "FAIL", f"refs-{b}", f"{len(refs[b])} board refs ({len(bo)} board-only) vs {len(nlrefs[b])} netlist refs; extra {ex[:6]} missing {mi[:6]}")
    bad = [(k, pads[b].get(k), nl[b].get(k)) for k in sorted(set(pads[b]) | set(nl[b])) if pads[b].get(k) != nl[b].get(k)]
    R("PASS" if not bad else "FAIL", f"nets-{b}", f"{len(pads[b])} board pads vs {len(nl[b])} netlist pins; {len(bad)} differ {bad[:4]}")
    rows = [l for l in (K / f"bom_jlc_{b}.csv").read_text().splitlines()[1:]]
    import csv, io
    bom = set()
    for r in csv.DictReader(io.StringIO((K / f"bom_jlc_{b}.csv").read_text())):
        bom |= {x.strip() for x in r["Designator"].split(",") if x.strip()}
    asm = {r for r, f in refs[b].items() if not f.IsBoardOnly() and not f.IsExcludedFromBOM() and not f.IsDNP()}
    R("PASS" if bom == asm else "FAIL", f"jlc-bom-{b}", f"BOM {len(bom)} designators vs {len(asm)} assembled board parts; only BOM {sorted(bom - asm)[:6]} only board {sorted(asm - bom)[:6]}")
allr = [r for b in "PM" for r in refs[b] if not refs[b][r].IsBoardOnly() and r not in ("J20", "J21")]
dup = sorted({r for r in allr if allr.count(r) > 1})
R("PASS" if not dup else "FAIL", "union", f"{len(allr)} distinct parts on P+M, duplicates {dup}")
j20 = {p.GetNumber(): p.GetNetname() for p in refs["M"]["J20"].Pads()}; j21 = {p.GetNumber(): p.GetNetname() for p in refs["P"]["J21"].Pads()}
dif = {k: (j20.get(k), j21.get(k)) for k in sorted(set(j20) | set(j21)) if j20.get(k) != j21.get(k)}
R("PASS" if not dif else "FAIL", "b2b-mate", f"J20 (M) vs J21 (P): {len(j20)} / {len(j21)} contacts, {len(dif)} net differences {dict(list(dif.items())[:4])}")
for b in "PM":
    bb = brd[b].GetBoardEdgesBoundingBox(); L, H = bb.GetWidth() * NM - 0.05, bb.GetHeight() * NM - 0.05
    R("PASS" if abs(L - D.STACK_L) <= 0.1 and abs(H - 12.0) <= 0.1 else "FAIL", f"outline-{b}", f"{L:.2f} x {H:.2f} vs dims_k4 STACK_L {D.STACK_L} x 12.0")
u2 = refs["M"]["U2"]
hole = [p for p in u2.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]
org = brd["M"].GetBoardEdgesBoundingBox(); ox, oy = org.GetX() * NM + 0.025, org.GetY() * NM + 0.025
if hole:
    c = hole[0].GetPosition(); mx, my = c.x * NM - ox, c.y * NM - oy
    R("PASS" if abs(mx - 1.75) <= 0.05 and abs(my - 6.0) <= 0.05 else "FAIL", "mic-port", f"U2 NPTH at board ({mx:.2f}, {my:.2f}) vs dims_k4 MIC (1.75, 6.0)")
else:
    R("FAIL", "mic-port", "U2 has no NPTH pad")
sys.exit(1 if any(s == "FAIL" for s, *_ in res) else 0)
