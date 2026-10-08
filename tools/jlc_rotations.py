#!/usr/bin/env python3
"""KiCad -> JLCPCB CPL rotation/offset corrections, derived per footprint and applied when writing CPL files.

    source tools/env.sh
    python3 tools/jlc_rotations.py                      # K4 P+M and draft_r2: table + flag list (read-only on boards)
    python3 tools/jlc_rotations.py --write-table OUT.csv --png OUT.png

Library (used by .pcba-workflow/k4-release/build_release.py):
    import jlc_rotations as jr
    rows = jr.analyse("hw/pod/k4/routed_P.kicad_pcb", "<bom>.csv")      # list of dict, one per assembled ref
    jr.write_cpl(rows, "cpl_P.csv")

How the correction is derived (two independent sources, then a fixed bottom-side rule):
 1. EasyEDA/JLC footprint orientation: JLC's CPL rotation 0 means "the EasyEDA footprint of that LCSC part as drawn".
    `easyeda2kicad` converts that footprint without rotating it, so for every LCSC part we fetch it (cached in
    tools/data/jlc_rot/ee/) and compare it with the KiCad footprint on the board: direction pad1->pad2 and the pad-1
    corner, both at rotation 0.  corr = angle(ours) - angle(EasyEDA), snapped to 90 deg.  JLC rotation (top) = KiCad
    rotation + corr.  Offset = difference of pad-centroid positions (our footprint origin vs the EasyEDA origin).
 2. Community rotation database (JLCKicadTools cpl_rotations_db.csv, regex on footprint name; also the database the
    kicad-jlcpcb-tools plugin downloads).  If a rule matches it wins (hand-verified against JLC previews by users)
    and a disagreement with source 1 is flagged.
 3. Bottom side (JLCKicadTools cpl_fix_rotations.py, comment dated 2022-07): corr is SUBTRACTED on the bottom, then
    jlc_rot = (180 - rot) mod 360.  JLC has changed this convention before; the placement preview decides
    (`--bottom-rule asis` reproduces the old raw behaviour).
Limits: JLC keeps a per-part rotation in its own parts DB that is not published.  So ICs / polarised parts are NEVER
'high' confidence here; they go on the placement-preview checklist with a picture of the expected pin-1 corner.

Provenance of the community DB: github.com/matthewlai/JLCKicadTools, jlc_kicad_tools/cpl_rotations_db.csv, last
commit 2024-09-11, fetched 2026-10-08; licence of the repo GPL-3.0 (the plugin kicad-jlcpcb-tools, MIT, downloads this
same file).  Copy: tools/data/jlc_rot/cpl_rotations_db.csv.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "data" / "jlc_rot"
DB_CSV = DATA / "cpl_rotations_db.csv"
EE_DIR = DATA / "ee"
NONPOLAR = ("R", "C", "L", "Y", "RT")           # ref prefixes whose pads are interchangeable (180 deg is harmless)
NEVER_HIGH_PREFIX = ("U", "Q", "D", "J", "SW", "LED", "IC")


# ---------------------------------------------------------------- community DB
def read_db(path=DB_CSV):
    rules = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].strip().lower().startswith("footprint pattern"):
                continue
            rules.append((re.compile(row[0]), int(row[1]),
                          float(row[2]) if len(row) > 2 and row[2].strip() else 0.0,
                          float(row[3]) if len(row) > 3 and row[3].strip() else 0.0, row[0]))
    return rules


def db_match(rules, name):
    hit = None
    for rx, rot, ox, oy, pat in rules:            # last match wins, as in JLCKicadTools
        if rx.match(name):
            hit = (rot, ox, oy, pat)
    return hit


# ---------------------------------------------------------------- footprint geometry
def ang(dx, dy):
    """Screen-CCW angle (deg) of a vector in KiCad file coordinates (y down)."""
    return math.degrees(math.atan2(-dy, dx)) % 360


def snap90(a):
    s = round(a / 90.0) * 90 % 360
    return s, abs(((a - s + 180) % 360) - 180)


class Geo:
    """Pad positions of a footprint at rotation 0, top view, relative to the footprint origin."""
    def __init__(self, pads):
        self.pads = {n: p for n, p in pads.items()}      # name -> (x, y, area)
        areas = sorted(a for *_, a in self.pads.values())
        med = areas[len(areas) // 2] if areas else 0
        sig = {n: p for n, p in self.pads.items() if p[2] <= 4 * med or len(self.pads) <= 2}
        self.sig = sig
        xs = [p[0] for p in sig.values()]; ys = [p[1] for p in sig.values()]
        self.c = (sum(xs) / len(xs), sum(ys) / len(ys)) if xs else (0, 0)

    def pin1(self):
        for k in ("1", "A1"):
            if k in self.sig:
                return k
        return None

    def pin2(self):
        k1 = self.pin1()
        for k in ({"1": "2", "A1": "B1"}.get(k1, ""), "A2"):
            if k in self.sig:
                return k
        return None

    def vec(self):
        """(angle pad1->pad2 or None, angle centroid->pad1 or None, distance of pad1 from centroid)."""
        k1 = self.pin1()
        if k1 is None:
            return None, None, 0
        p1 = self.sig[k1]
        k2 = self.pin2()
        a12 = ang(self.sig[k2][0] - p1[0], self.sig[k2][1] - p1[1]) if k2 else None
        d = math.hypot(p1[0] - self.c[0], p1[1] - self.c[1])
        return a12, (ang(p1[0] - self.c[0], p1[1] - self.c[1]) if d > 0.05 else None), d


def geo_from_kicad_mod(path):
    txt = Path(path).read_text()
    pads = {}
    for m in re.finditer(r'\(pad\s+"?([^"\s)]+)"?\s+(smd|thru_hole|np_thru_hole|connect)\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+[-\d.]+)?\)\s+\(size\s+([-\d.]+)\s+([-\d.]+)', txt):
        n, kind, x, y, w, h = m.groups()
        if kind == "np_thru_hole" or n in ("", "~"):
            continue
        pads.setdefault(n, (float(x), float(y), float(w) * float(h)))
    return Geo(pads)


def geo_from_board_fp(fp, pcbnew):
    """Library-frame (rotation 0, top-view) pad geometry of a placed footprint.
    KiCad stores a bottom footprint mirrored about the x axis, so y is un-mirrored here (checked: stock QFN-48 pad 1
    is at (-3.44, -2.75) in the library and reads (-3.44, +2.75) from the bottom-side board footprint)."""
    pads = {}
    ys = -1.0 if fp.IsFlipped() else 1.0
    for p in fp.Pads():
        n = p.GetNumber()
        if not n or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            continue
        r = p.GetFPRelativePosition()
        s = p.GetSize()
        pads.setdefault(n, (r.x / 1e6, ys * r.y / 1e6, s.x / 1e6 * s.y / 1e6))
    return Geo(pads)


def fetch_ee(lcsc):
    d = EE_DIR / f"{lcsc}.pretty"
    if not list(d.glob("*.kicad_mod")):
        EE_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["easyeda2kicad", "--lcsc_id", lcsc, "--footprint", "--output", str(EE_DIR / lcsc), "--overwrite"],
                       check=True, capture_output=True)
    f = sorted(d.glob("*.kicad_mod"))
    return f[0] if f else None


# ---------------------------------------------------------------- derivation
def derive(ours: Geo, ee: Geo):
    """Return (corr_deg or None, offset (x, y) local, notes)."""
    a_o, c_o, d_o = ours.vec()
    a_e, c_e, d_e = ee.vec()
    notes = []
    ests = []
    if a_o is not None and a_e is not None:
        ests.append(("p1p2", (a_o - a_e) % 360))
    if c_o is not None and c_e is not None:
        ests.append(("corner", (c_o - c_e) % 360))
    if not ests:
        return None, (0, 0), ["no usable pad-1 geometry"]
    snaps = [(k,) + snap90(v) for k, v in ests]
    worst = max(e for _, _, e in snaps)
    corr = snaps[0][1]            # pad1->pad2 direction is the primary estimate
    for k, v in ests[1:]:         # corner estimate is continuous: must agree within 30 deg (pad 1 sits off-diagonal on QFN)
        if abs(((v - corr + 180) % 360) - 180) > 30:
            notes.append(f"estimators disagree p1p2={corr} {k}={v:.0f}")
    if worst > 15:
        notes.append(f"non-orthogonal ({worst:.0f} deg off 90 grid)")
    # origin offset: mean shift of common pads (EasyEDA pads rotated by corr, ours minus theirs, local frame, top view).
    # Only a rigid shift counts (spread < 0.05 mm over >= 2 pads); sub-0.05 mm shifts are footprint-edit noise, not origin moves.
    t = math.radians(corr)
    ds = []
    for n, (ex, ey, _a) in ee.sig.items():
        if n in ours.sig and _a > 0.01 and ours.sig[n][2] > 0.01:
            rx = ex * math.cos(t) + ey * math.sin(t)
            ry = -ex * math.sin(t) + ey * math.cos(t)
            ds.append((ours.sig[n][0] - rx, ours.sig[n][1] - ry))
    off = (0.0, 0.0)
    if len(ds) >= 2:
        sx = max(d[0] for d in ds) - min(d[0] for d in ds); sy = max(d[1] for d in ds) - min(d[1] for d in ds)
        mx = sum(d[0] for d in ds) / len(ds); my = sum(d[1] for d in ds) / len(ds)
        if max(sx, sy) < 0.05 and math.hypot(mx, my) >= 0.05:
            off = (mx, my)
        elif max(sx, sy) >= 0.05:
            notes.append(f"pad sets differ by up to {max(sx, sy):.2f} mm (not a rigid origin shift; no offset applied)")
    return corr, off, notes


def analyse(board_path, bom_path=None, fp_lcsc=None, bottom_rule="jlc2022", rules=None, only_bom=True):
    """One row per assembled footprint.  bom_path: JLC BOM csv (Designator list + 'LCSC Part #').  fp_lcsc: footprint-name -> LCSC fallback."""
    import pcbnew
    rules = rules or read_db()
    bd = pcbnew.LoadBoard(str(board_path))
    ref_lcsc = {}
    if bom_path:
        for r in csv.DictReader(open(bom_path)):
            for ref in r["Designator"].split(","):
                ref_lcsc[ref.strip()] = r["LCSC Part #"].strip()
    rows = []
    for fp in bd.GetFootprints():
        ref = fp.GetReference()
        name = str(fp.GetFPID().GetLibItemName())
        if only_bom and bom_path and ref not in ref_lcsc:
            continue
        lcsc = ref_lcsc.get(ref) or (fp_lcsc or {}).get(name, "")
        if not lcsc:
            continue
        side = "bottom" if fp.GetLayer() == pcbnew.B_Cu else "top"
        rot = fp.GetOrientationDegrees() % 360
        pos = fp.GetPosition()
        notes, src, conf = [], [], "low"
        corr_ee, off_local, n = None, (0.0, 0.0), []
        try:
            f = fetch_ee(lcsc)
            if f:
                corr_ee, off_local, n = derive(geo_from_board_fp(fp, pcbnew), geo_from_kicad_mod(f))
                notes += n
            else:
                notes.append("no EasyEDA footprint; pin-1 not data-derived")
        except Exception as e:            # network / easyeda2kicad failure must not hide the part
            notes.append("no EasyEDA footprint (fetch failed: LCSC part not in EasyEDA API); pin-1 not data-derived")
        hit = db_match(rules, name)
        corr, ox, oy = 0, 0.0, 0.0
        if hit:
            corr, ox, oy, pat = hit
            src.append(f"community DB {pat}")
            if corr_ee is not None and corr_ee % 360 != corr % 360:
                notes.append(f"DB {corr} vs EasyEDA-derived {corr_ee}")
            else:
                conf = "medium"
        elif corr_ee is not None:
            corr = corr_ee
            src.append("EasyEDA pin-1 geometry")
            conf = "medium" if not n else "low"
            # world displacement of the EasyEDA origin so that pad centroids coincide: P' = P + Rot(R)(off), bottom mirrors y
            ly = -off_local[1] if side == "bottom" else off_local[1]
            t = math.radians(rot)
            ox = off_local[0] * math.cos(t) + ly * math.sin(t)
            oy = -off_local[0] * math.sin(t) + ly * math.cos(t)
            if abs(ox) < 0.02 and abs(oy) < 0.02:
                ox = oy = 0.0
            else:
                notes.append(f"origin offset {ox:+.2f},{oy:+.2f} mm (board file frame, y down) applied")
        # symmetric passives: orientation cannot cause a short; one rule for confidence
        prefix = re.sub(r"\d.*$", "", ref)
        sym = prefix in NONPOLAR and len({p.GetNumber() for p in fp.Pads() if p.GetNumber()}) == 2
        if sym and not hit:
            conf = "high" if corr % 180 == 0 else "medium"
            if corr % 180 != 0:
                notes.append("symmetric passive but 90 deg correction")
        if prefix in NEVER_HIGH_PREFIX or any(ref.startswith(p) for p in NEVER_HIGH_PREFIX):
            if conf == "high":
                conf = "medium"
        # final rotation
        if side == "bottom":
            r = (rot - corr) % 360
            r = (-r + 180) % 360 if bottom_rule == "jlc2022" else r
            r = r % 360
        else:
            r = (rot + corr) % 360
        pos_x, pos_y = pos.x / 1e6 + ox, -(pos.y / 1e6 + oy)
        # (CPL y is up: KiCad file y is down, so a file-frame y offset flips sign)
        rows.append(dict(ref=ref, footprint=name, lcsc=lcsc, side=side, kicad_rot=round(rot, 3), corr=corr,
                         jlc_rot=round(r, 3), off_x=round(ox, 3), off_y=round(oy, 3),
                         x=round(pos_x, 4), y=round(pos_y, 4), source="; ".join(src) or "none (default 0)",
                         confidence=conf, notes="; ".join(notes)))
    # flag rule: anything not high must be checked in the JLC preview
    for r in rows:
        r["check_in_preview"] = r["confidence"] != "high"
    return sorted(rows, key=lambda r: (re.sub(r"\d", "", r["ref"]), int(re.sub(r"\D", "", r["ref"]) or 0)))


def write_cpl(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            w.writerow([r["ref"], f"{r['x']:.4f}mm", f"{r['y']:.4f}mm", "Top" if r["side"] == "top" else "Bottom", f"{r['jlc_rot'] % 360:g}"])


COLS = ["board", "ref", "footprint", "lcsc", "side", "kicad_rot", "jlc_rot", "corr", "off_x", "off_y", "source", "confidence", "check_in_preview", "notes"]


def write_table(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


# ---------------------------------------------------------------- picture of the expected pin-1 corner
def corner_word(dx, dy):
    """Corner of pad 1 as seen in the preview (x right, y down in the view)."""
    h = "left" if dx < 0 else "right"
    v = "upper" if dy < 0 else "lower"
    return f"{v}-{h}"


def pin1_png(items, path):
    """items: list of (board, boardfile, rows).  One tile per flagged part: pads in preview orientation, pad 1 red."""
    import pcbnew
    sys.path.insert(0, str(ROOT / "tools"))
    import plotstyle; plotstyle.apply()
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    tiles = []
    for tag, bpath, rows in items:
        bd = pcbnew.LoadBoard(str(bpath))
        fps = {f.GetReference(): f for f in bd.GetFootprints()}
        for r in rows:
            if r["check_in_preview"] and not r["ref"].startswith(("R", "C")) and len(fps[r["ref"]].Pads()) > 2:
                tiles.append((tag, r, fps[r["ref"]]))
    n = len(tiles)
    cols = 4
    nr = max(1, -(-n // cols))
    fig, axs = plt.subplots(nr, cols, figsize=(cols * 3.2, nr * 3.4))
    axs = [axs] if n <= 1 else list(axs.flat)
    for ax in axs:
        ax.axis("off")
    for ax, (tag, r, fp) in zip(axs, tiles):
        bottom = r["side"] == "bottom"
        c = fp.GetPosition()
        P = []
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            q = p.GetPosition(); bb = p.GetBoundingBox()      # bbox: custom-shape pads have a tiny anchor size
            x = (q.x - c.x) / 1e6; y = (q.y - c.y) / 1e6
            sw = bb.GetWidth() / 1e6; sh = bb.GetHeight() / 1e6
            if bottom:
                x = -x                      # preview "bottom" view is the board flipped left-right
            P.append((p.GetNumber(), x, y, sw, sh))
        for num, x, y, sw, sh in P:
            red = num in ("1", "A1")
            ax.add_patch(Rectangle((x - sw / 2, y - sh / 2), sw, sh, fc=plotstyle.SERIES[7] if red else plotstyle.SERIES[0],
                                   ec="none", alpha=0.95 if red else 0.55))
        ext = max(max(abs(x) + sw / 2, abs(y) + sh / 2) for _, x, y, sw, sh in P) * 1.25
        ax.set_xlim(-ext, ext); ax.set_ylim(ext, -ext); ax.set_aspect("equal")
        p1 = next(((x, y) for num, x, y, *_ in P if num in ("1", "A1")), None)
        cx = sum(x for _, x, *_ in P) / len(P); cy = sum(y for _, _, y, *_ in P) / len(P)
        where = corner_word(p1[0] - cx, p1[1] - cy) if p1 else "?"
        ax.set_title(f"{tag} {r['ref']}  {r['footprint'][:26]}\n{r['side']} view, JLC rot {r['jlc_rot']:g}, {r['lcsc']}\nEXPECT PAD 1 (red): {where}", fontsize=7, color=plotstyle.TEXT)
        ax.axis("on"); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(plotstyle.GRID)
    fig.suptitle("Placement-preview checklist: expected pin-1 pad (red) as drawn in JLC's top / bottom view, parts not confirmed from data",
                 fontsize=9, color=plotstyle.TEXT)
    fig.tight_layout(rect=(0, 0, 1, 0.96), h_pad=2.0)
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- K4 release hook
def release(rel_dir=".pcba-workflow/k4-release", bottom_rule="jlc2022"):
    """Write cpl_P/M.csv (corrected), jlc_rotation_corrections.csv and pin1_expected.png into the release folder.
    Boards = hw/pod/k4/routed_{P,M}.kicad_pcb, BOMs = <rel_dir>/src/bom_jlc_{P,M}.csv (the ones matching the boards)."""
    rel = ROOT / rel_dir
    rules, allrows, items = read_db(), [], []
    for b in "PM":
        board = ROOT / f"hw/pod/k4/routed_{b}.kicad_pcb"
        rows = analyse(board, rel / "src" / f"bom_jlc_{b}.csv", bottom_rule=bottom_rule, rules=rules)
        for r in rows:
            r["board"] = f"K4-{b}"
        write_cpl(rows, rel / f"cpl_{b}.csv")
        allrows += rows
        items.append((f"K4-{b}", board, rows))
    write_table(allrows, rel / "jlc_rotation_corrections.csv")
    pin1_png(items, rel / "pin1_expected.png")
    return allrows


# ---------------------------------------------------------------- CLI
JOBS = [
    ("K4-P", "hw/pod/k4/routed_P.kicad_pcb", ".pcba-workflow/k4-release/src/bom_jlc_P.csv"),
    ("K4-M", "hw/pod/k4/routed_M.kicad_pcb", ".pcba-workflow/k4-release/src/bom_jlc_M.csv"),
    ("r2", "hw/pod/draft_r2/out/routed.kicad_pcb", None),          # regression: no BOM, LCSC via footprint name
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-table")
    ap.add_argument("--png")
    ap.add_argument("--release", action="store_true", help="write the K4 release CPLs + table + picture, then exit")
    ap.add_argument("--bottom-rule", default="jlc2022", choices=["jlc2022", "asis"])
    a = ap.parse_args()
    if a.release:
        rows = release(bottom_rule=a.bottom_rule)
        print(len(rows), "rows;", sum(r["check_in_preview"] for r in rows), "to check in the preview")
        return
    rules = read_db()
    fp_lcsc = {}
    for _, b, bom in JOBS[:2]:
        for r in csv.DictReader(open(ROOT / bom)):
            fp_lcsc[r["Footprint"]] = r["LCSC Part #"]
    allrows, items = [], []
    for tag, b, bom in JOBS:
        rows = analyse(ROOT / b, ROOT / bom if bom else None, fp_lcsc=fp_lcsc, bottom_rule=a.bottom_rule, rules=rules,
                       only_bom=bool(bom))
        for r in rows:
            r["board"] = tag
        allrows += rows
        items.append((tag, ROOT / b, rows))
    for r in allrows:
        flag = "CHECK" if r["check_in_preview"] else "ok   "
        print(f"{r['board']:5} {r['ref']:5} {r['footprint'][:34]:34} {r['lcsc']:10} {r['side']:6} k{r['kicad_rot']:5g} -> j{r['jlc_rot']:5g} "
              f"corr{r['corr']:4g} off({r['off_x']:+.2f},{r['off_y']:+.2f}) {r['confidence']:6} {flag} {r['notes']}")
    if a.write_table:
        write_table(allrows, a.write_table)
    if a.png:
        pin1_png(items[:2], a.png)


if __name__ == "__main__":
    main()
