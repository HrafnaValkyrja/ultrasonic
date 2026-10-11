#!/usr/bin/env python3
"""Capacitor DC-bias derating check for the two K4 0201 caps (owner ruling #7, A-CAP-CURVES).

  K4-P C9  = Samsung CL03A225MP3CRNC  2.2 uF 10 V X5R 0201, VDD11 (MCU core SMPS output, with C8)
  K4-M C17 = Samsung CL03A105MO3NRNC  1 uF 16 V X5R 0201, VSYS (TPS7A2030 LDO input / charger SYS)

USAGE (one command once the owner drops Samsung files in ./inbox):
  python3 sim/checks/cap_derating.py                  # auto-scan ./inbox for both parts
  python3 sim/checks/cap_derating.py --c9 FILE --c17 FILE   # explicit files
  python3 sim/checks/cap_derating.py --placeholder    # self-test on SYNTHETIC curves (NOT an answer)
  options: --t-hot 60 --t-cold 0 (deg C)  --vdd11 1.2  --vsys-nom 4.2 --vsys-max 4.9
           --c9-min 2.0 --c17-min 1.0 (requirements, uF effective)  --c8-eff 1.8 (uF)  --csv-out FILE

INPUT FORMATS (file whose name contains the part number; or a path given with --c9/--c17):
  .csv/.txt/.tsv : DC-bias table. First numeric column = bias in V. Capacitance column chosen by header:
                   '%'/'change' -> percent change vs 0 V; 'uF/nF/pF' (or 'cap') -> absolute capacitance
                   (unit from header, default uF). If several columns carry temperature headers (e.g. '25C',
                   '85C'), each is a temperature curve and the hot one is used. A '(0V)' point sets nominal.
  .xls/.xlsx     : same table via openpyxl/xlrd if installed (else save as CSV).
  .mod/.lib/.cir/.sp/.sub : SPICE .subckt. The sum of C elements = C at the netlist's bias point (Samsung
                   publishes models at 0 V and some at rated bias; the file header comment is echoed); R/L/C
                   in one series branch also give ESR and |Z| at 3 MHz. A SPICE file gives ONE bias point only,
                   so it can set nominal C / ESR but not the bias curve: a DC-bias table is still needed for PASS.
RULES / ASSUMPTIONS (override on the CLI, each printed in the report):
  worst case = table C at bias x (1 - tol 20 %, 'M' suffix) x (1 - 15 % X5R temperature, -55..85 C bound).
  Samsung curves are typical, so the typical-only result is printed too; PASS needs the WORST case >= req.
  C9: VDD11 ~1.2 V; req total effective on VDD11 >= --c9-min with C8 (0402 2.2 uF 10 V) assumed --c8-eff.
      ASSUMPTION to verify against ST DS13737 Rev 10 p.153 (SMPS output cap spec) when the PDF is at hand.
  C17: VSYS up to 4.9 V (gen.py comment: SYS <= 4.9 V; charger regulation 4.2-4.5 V); req >= 1 uF effective
      (TI SLUSE99C Table 9-2 CSYS/CBAT min 1 uF after derating; TPS7A20 CIN 1 uF). Checked at --vsys-max.
Exit code 0 = all PASS, 1 = any FAIL, 2 = missing data. Placeholder runs always print a PLACEHOLDER banner.
"""
import argparse, csv, glob, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARTS = {
    "C9":  dict(pn="CL03A225MP3CRNC", nom=2.2, rated=10, tol=0.20, vlabel="VDD11"),
    "C17": dict(pn="CL03A105MO3NRNC", nom=1.0, rated=16, tol=0.20, vlabel="VSYS"),
}
UNIT = {"pf": 1e-6, "nf": 1e-3, "uf": 1.0, "µf": 1.0}
X5R_TEMP = 0.15

def num(s):
    try: return float(str(s).strip().replace("%", "").replace(",", ""))
    except ValueError: return None

def read_rows(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xls", ".xlsx"):
        try:
            import openpyxl
            ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
            return [[("" if c is None else c) for c in r] for r in ws.iter_rows(values_only=True)]
        except ImportError:
            try:
                import xlrd
                sh = xlrd.open_workbook(path).sheet_by_index(0)
                return [sh.row_values(i) for i in range(sh.nrows)]
            except ImportError:
                sys.exit("need openpyxl or xlrd for %s; save it as CSV" % path)
    txt = open(path, errors="replace").read()
    dialect = csv.Sniffer().sniff(txt[:2000], delimiters=",;\t") if txt.strip() else csv.excel
    return list(csv.reader(txt.splitlines(), dialect))

def parse_table(path, nominal):
    """-> {temp_C or None: [(V, C_uF)]}, notes"""
    rows = read_rows(path)
    head, data = [], []
    for r in rows:
        v = [num(x) for x in r]
        if len(r) >= 2 and v[0] is not None and any(x is not None for x in v[1:]) and data is not None and (head or True) and v[0] is not None and not isinstance(r[0], str) or (len(r) >= 2 and v[0] is not None and v[1] is not None):
            data.append(v)
        elif any(str(x).strip() for x in r) and not data:
            head = [str(x).strip().lower() for x in r]
    if not data: sys.exit("no numeric table found in " + path)
    ncol = max(len(d) for d in data)
    curves, notes = {}, []
    for j in range(1, ncol):
        h = head[j] if j < len(head) else ""
        pts = [(d[0], d[j]) for d in data if j < len(d) and d[j] is not None]
        if not pts: continue
        m = re.search(r"(-?\d+)\s*(?:°|deg)?\s*c\b", h)
        temp = float(m.group(1)) if m else None
        if "%" in h or "change" in h or "delta" in h or "rate" in h:
            c0 = min(pts, key=lambda p: abs(p[0]))[1]
            pts = [(v, nominal * (1 + p / 100.0)) for v, p in pts]; notes.append("col %d '%s': percent change x nominal %.3g uF" % (j, h, nominal))
        else:
            u = next((UNIT[k] for k in UNIT if k in h), 1.0)
            pts = [(v, c * u) for v, c in pts]; notes.append("col %d '%s': absolute C" % (j, h))
        curves.setdefault(temp, pts)
    return curves, notes

def parse_spice(path):
    txt = open(path, errors="replace").read()
    R = L = C = 0.0; ncap = 0
    sc = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6}
    def val(s):
        m = re.match(r"([-+0-9.eE]+)\s*(meg|[fpnumk])?", s.strip(), re.I)
        return float(m.group(1)) * sc.get((m.group(2) or "").lower(), 1) if m else None
    for line in txt.splitlines():
        t = line.split()
        if len(t) >= 4 and not line.lstrip().startswith(("*", ".", "$")):
            v = val(t[3]) if val(t[3]) is not None else None
            if v is None: continue
            k = t[0][0].upper()
            if k == "R": R += v
            elif k == "L": L += v
            elif k == "C": C += v; ncap += 1
    hdr = [l.strip("* ").strip() for l in txt.splitlines() if l.startswith("*")][:3]
    return dict(R=R, L=L, C_uF=C * 1e6, ncap=ncap, hdr=hdr)

def interp(pts, v):
    pts = sorted(pts)
    if v <= pts[0][0]: return pts[0][1]
    for (v0, c0), (v1, c1) in zip(pts, pts[1:]):
        if v <= v1: return c0 + (c1 - c0) * (v - v0) / (v1 - v0)
    return pts[-1][1]          # beyond table: hold last point (flagged by caller)

def find(ref, explicit):
    if explicit: return [explicit]
    pn = PARTS[ref]["pn"].lower()
    return sorted(f for f in glob.glob(os.path.join(ROOT, "inbox", "**", "*"), recursive=True)
                  if os.path.isfile(f) and (pn in os.path.basename(f).lower() or pn[:-4] in os.path.basename(f).lower()))

def placeholder(ref):
    """SYNTHETIC curve, NOT Samsung data: C/C0 = 1 - a*(V/Vr)^1.5 (typical X5R shape, magnitude guessed)."""
    p = PARTS[ref]; a = {"C9": 0.60, "C17": 0.75}[ref]
    return {None: [(v / 10, p["nom"] * (1 - a * (v / 10 / p["rated"]) ** 1.5)) for v in range(0, int(p["rated"] * 10) + 1, 2)]}

def evaluate(ref, curves, a, spice, synthetic):
    p = PARTS[ref]
    hot = [t for t in curves if t is not None]
    pts = curves[max(hot)] if hot else curves[None] if None in curves else next(iter(curves.values()))
    vmax_tab = max(v for v, _ in pts)
    v = a.vdd11 if ref == "C9" else a.vsys_max
    ctyp = interp(pts, v)
    cw = ctyp * (1 - p["tol"]) * (1 - (0 if hot else X5R_TEMP))
    req = a.c9_min if ref == "C9" else a.c17_min
    warn = []
    if v > vmax_tab: warn.append("bias %.2f V beyond table max %.2f V (held at last point)" % (v, vmax_tab))
    if v > p["rated"]: warn.append("bias exceeds rated %g V" % p["rated"])
    if not hot: warn.append("no temperature columns: applied X5R +/-15 %% bound (%g..%g C)" % (a.t_cold, a.t_hot))
    if ref == "C9":
        tot_t, tot_w = ctyp + a.c8_eff, cw + a.c8_eff * (1 - p["tol"])
        used = tot_w; label = "C9 + C8 (assumed %.2f uF eff) on VDD11 @ %.2f V" % (a.c8_eff, v)
    else:
        tot_t, tot_w = ctyp, cw; used = cw; label = "C17 on VSYS @ %.2f V (max) / %.2f V (nom)" % (v, a.vsys_nom)
    ok = used >= req
    print("%s %s [%s]: %s" % (ref, p["pn"], "SYNTHETIC PLACEHOLDER" if synthetic else "measured data", label))
    print("   nominal %.2f uF -> typical at bias %.3f uF (%.0f %%); worst (tol %d %%%s) %.3f uF" %
          (p["nom"], ctyp, 100 * ctyp / p["nom"], p["tol"] * 100, "" if hot else ", X5R temp", cw))
    if ref == "C17": print("   typical at nominal %.2f V: %.3f uF" % (a.vsys_nom, interp(pts, a.vsys_nom)))
    print("   requirement %.2f uF effective%s; worst-case total %.3f uF (typ %.3f)" % (req, " (total on VDD11)" if ref == "C9" else "", tot_w, tot_t))
    if spice:
        z = complex(spice["R"], 2 * math.pi * 3e6 * spice["L"] - (1 / (2 * math.pi * 3e6 * spice["C_uF"] * 1e-6) if spice["C_uF"] else 0))
        print("   SPICE: C=%.3f uF ESR~%.1f mOhm |Z|@3MHz=%.1f mOhm (series R+L+C; %s)" % (spice["C_uF"], spice["R"] * 1e3, abs(z) * 1e3, "; ".join(spice["hdr"])[:80]))
    for w in warn: print("   WARN:", w)
    print("   %s margin %+.3f uF (%+.0f %%)" % ("PASS" if ok else "FAIL", used - req, 100 * (used - req) / req) + ("   [PLACEHOLDER - NOT AN ANSWER]" if synthetic else ""))
    return ok

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--c9"); ap.add_argument("--c17"); ap.add_argument("--placeholder", action="store_true")
    ap.add_argument("--t-hot", type=float, default=60); ap.add_argument("--t-cold", type=float, default=0)
    ap.add_argument("--vdd11", type=float, default=1.2); ap.add_argument("--vsys-nom", type=float, default=4.2)
    ap.add_argument("--vsys-max", type=float, default=4.9)
    ap.add_argument("--c9-min", type=float, default=2.0); ap.add_argument("--c17-min", type=float, default=1.0)
    ap.add_argument("--c8-eff", type=float, default=1.8); ap.add_argument("--csv-out")
    a = ap.parse_args()
    if a.placeholder:
        print("#" * 70 + "\n# PLACEHOLDER: SYNTHETIC curves, not Samsung data. Not an answer.\n" + "#" * 70)
    res, missing = {}, False
    for ref in PARTS:
        curves = spice = None
        if a.placeholder:
            curves, syn = placeholder(ref), True
        else:
            syn = False
            for f in find(ref, getattr(a, ref.lower())):
                if os.path.splitext(f)[1].lower() in (".mod", ".lib", ".cir", ".sp", ".sub", ".cki"):
                    spice = parse_spice(f)
                elif curves is None:
                    curves, notes = parse_table(f, PARTS[ref]["nom"]); syn = syn or "placeholder" in f.lower(); print("%s: %s %s" % (ref, os.path.relpath(f, ROOT), notes))
            if curves is None:
                print("%s %s: no DC-bias table in ./inbox%s" % (ref, PARTS[ref]["pn"], " (SPICE file found, one bias point only)" if spice else "")); missing = True; continue
        res[ref] = evaluate(ref, curves, a, spice, syn)
    sys.exit(2 if missing and not res else (0 if res and all(res.values()) and not missing else 1) if res else 2)

if __name__ == "__main__":
    main()
