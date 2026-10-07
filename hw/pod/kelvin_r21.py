"""Post-route Kelvin fix for the current-sense shunt R21 (Phase 2 board, 2026-10-07, LN-M03).

Replaces the 0.55 mm B.Cu stub from the R21 GND pad to its via with two GND vias hugging the pad (above + beside,
0.25 mm stubs). Options scored with sim/noise (LN-M03, limit 2 %): stub 3.31 % / one edge via 2.38 % / two edge
vias 1.29 % (chosen) / via-in-pad 1.54 % (needs filled+capped vias: extra fab cost). DRC 0 for all.

    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 hw/pod/kelvin_r21.py IN.kicad_pcb OUT.kicad_pcb edge3
"""
import sys, pcbnew
import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parent)); import close_gaps as C
src, dst, mode = sys.argv[1], sys.argv[2], sys.argv[3]
b = pcbnew.LoadBoard(src); M, mm = pcbnew.ToMM, pcbnew.FromMM
gnd = b.FindNet("GND").GetNetCode()
for t in list(b.GetTracks()):
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    if t.GetNetCode() == gnd and all(abs(M(q.x) - 18.67) < 0.3 and abs(M(q.y) - 6.45) < 0.05 for q in pts):
        b.Delete(t)
px, py = 18.94, 6.45
if mode == "edges":       # two vias touching the pad's top and bottom edges (pad 0.54 x 0.64)
    spots = [(px, py - 0.32 - 0.12), (px, py + 0.32 + 0.12)]
elif mode == "edge3":
    spots = [(px, py - 0.32 - 0.12), (px, py + 0.32 + 0.12), (px - 0.27 - 0.12, py)]
else:                     # via in pad (needs filled + capped vias)
    spots = [(px, py)]
added = 0
for s in spots:
    circ = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(mm(s[0]), mm(s[1])), mm(C.VIA_D / 2))
    if all(C.clear(b, gnd, l, circ) for l in C.OUTER):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(s[0]), mm(s[1]))); v.SetWidth(mm(C.VIA_D)); v.SetDrill(mm(C.VIA_DRILL)); v.SetNetCode(gnd); b.Add(v); added += 1
        if s != (px, py):
            t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(mm(px), mm(py))); t.SetEnd(pcbnew.VECTOR2I(mm(s[0]), mm(s[1])))
            t.SetWidth(mm(0.25)); t.SetLayer(pcbnew.B_Cu); t.SetNetCode(gnd); b.Add(t)
    else:
        print("blocked", s)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(dst, b); print(mode, "vias added", added)
