#!/usr/bin/env python3
"""Build K4 BOM/CPL/pin-1 table/cost from the two routed boards + dated JLC API lookups. Read-only on the boards."""
import csv, json, sys, math, collections, datetime as dt, hashlib, re
sys.path.insert(0, "tools"); import jlc
import pcbnew
R = ".pcba-workflow/k4-release"
NBRD = 5
out = {}
lookups = {}
def lk(c):
    if c not in lookups:
        rows = [r for r in jlc.search(c) if r["lcsc"] == c]
        lookups[c] = rows[0]
    return lookups[c]
def price_at(r, q):
    p = r["price_usd_qty1"]
    for lo, v in r["price_breaks"]:
        if q >= lo: p = v
    return p
BOMS = {}
for b in "PM":
    rows = list(csv.DictReader(open(f"{R}/src/bom_jlc_{b}.csv")))
    bd = pcbnew.LoadBoard(f"hw/pod/k4/routed_{b}.kicad_pcb")
    fp = {f.GetReference(): f for f in bd.GetFootprints()}
    bomrefs = set()
    for r in rows: bomrefs |= set(x.strip() for x in r["Designator"].split(","))
    asm = {k for k, f in fp.items() if not (f.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES) and not k.startswith("J") or k in ("J20","J21")}
    asm = {k for k in asm if not (k.startswith("J") and k not in ("J20","J21"))}
    print(b, "bom-only", sorted(bomrefs - set(fp)), "board-only(non TP/J)", sorted(asm - bomrefs))
    BOMS[b] = (rows, fp, bomrefs)
# CPL: KiCad rotation -> JLC rotation via tools/jlc_rotations.py (EasyEDA pin-1 geometry + community DB + bottom-side rule);
# also writes jlc_rotation_corrections.csv and pin1_expected.png (placement-preview checklist)
import jlc_rotations
jlc_rotations.release(R)
for b in "PM":
    rows, fp, bomrefs = BOMS[b]
    n_cpl = len(list(csv.DictReader(open(f"{R}/cpl_{b}.csv"))))
    print(b, "cpl rows", n_cpl, "bom refs", len(bomrefs), "(TP/wire pads in BOM-less refs are excluded)")
    # BOM with JLC columns
    with open(f"{R}/bom_{b}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for r in rows: w.writerow([r["Comment"], r["Designator"], r["Footprint"], r["LCSC Part #"]])
# pin-1 table
def pin1(f):
    for p in f.Pads():
        if p.GetNumber() in ("1", "A1"): 
            c = f.GetPosition(); q = p.GetPosition()
            return (q.x - c.x) / 1e6, (q.y - c.y) / 1e6
    return None
chk = []
for b in "PM":
    rows, fp, _ = BOMS[b]
    for ref in ("U1","U2","U3","U4","U6","J20","J21","Q1","Q2","D4","D5","SW1","Y1","L1"):
        if ref in fp:
            f = fp[ref]; p = pin1(f)
            chk.append([b, ref, f.GetFPID().GetLibItemName(), f.GetLayerName(), f"{f.GetOrientationDegrees():g}", "" if not p else f"{p[0]:+.2f},{p[1]:+.2f}"])
with open(f"{R}/pin1_check.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["board", "ref", "footprint", "side", "kicad_rot_deg", "pin1_offset_from_origin_mm(board x right, y down)"]); w.writerows(chk)
# cost
now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
lines = {}; tot = 0.0; types = set(); ext = set()
detail = []
for b in "PM":
    rows, fp, _ = BOMS[b]
    for r in rows:
        c = r["LCSC Part #"]; L = lk(c); n = int(r["Qty"]) * NBRD
        types.add((b, c)); 
        if L["library"] == "Extended": ext.add((b, c))
        detail.append(dict(board=b, lcsc=c, mpn=L["mpn"], comment=r["Comment"], refs=r["Designator"], qty_board=int(r["Qty"]), qty_total=n, lib=L["library"], stock=L["stock"], stock_ok=L["stock"] >= n, unit=price_at(L, n), line=round(price_at(L, n) * n, 4), queried=L["queried_utc"]))
parts = sum(d["line"] for d in detail)
with open(f"{R}/sourcing_dated.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(detail[0])); w.writeheader(); w.writerows(detail)
lines_P = len(BOMS["P"][0]); lines_M = len(BOMS["M"][0])
print("lines", lines_P, lines_M, "parts total $%.2f" % parts, "ext lines", len(ext), "stock fails", [(d['board'], d['lcsc'], d['stock'], d['qty_total']) for d in detail if not d['stock_ok']])
json.dump(dict(queried=now, parts_usd=round(parts, 2), lines_P=lines_P, lines_M=lines_M, ext_lines=len(ext)), open(f"{R}/cost_inputs.json", "w"))
print(now)
