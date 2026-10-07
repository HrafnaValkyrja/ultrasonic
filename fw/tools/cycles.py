#!/usr/bin/env python3
"""fw/tools/cycles.py: static cycles_hop estimate of the firmware DSP per variant (FWSIM-R47 layer E1, FWSIM-R10 cycles_hop),
with fw/bench's counter (fw/bench/cyccount.py: Cortex-M4 TRM CPI table as the M33 proxy, [lo, hi] per instruction, branch
model, 0 wait states = the 55 MHz / Range 3 column of docs/research/drastic/V4-cycles.yaml).

Execution counts: V4 multiplied loop bodies by trip tables written by hand; the firmware's loops sit in -O2 layouts with
out-of-line blocks, so here each ARM instruction (arm-none-eabi-gcc, fwsim ARM_FLAGS + -g, objdump -dl) is attributed to its
source line and multiplied by that line's execution count from a host gcov run of the SAME core sources on a golden vector.
cycles/hop = [sum(cost x count) over a long run - same over a short run] / (hop difference): init and the power-on hold drop out.
Bias (upper side): instructions the ARM compiler hoists out of a loop keep the loop line's count; lines without a gcov record
take the previous executable line's count. Not a measurement: DWT CYCCNT on hardware closes it (FWSIM-R49).

  python3 fw/tools/cycles.py [--json out.json]
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

FW = Path(__file__).resolve().parents[1]
REPO = FW.parent
sys.path[:0] = [str(FW / "bench"), str(FW / "tools")]
import cyccount as cc  # noqa: E402
import fwsim  # noqa: E402

SRCS = ["dsp.c", "dsp_math.c", "fw.c", "out_clamp.c"]
HOPS_PER_S = 200_020 / 128
V4 = {"B": {"cfg": "B_28bands (V4: 28 bands, hop 128, TPP 8, CMSIS FFT)", "MHz": [59.1, 68.8]},
      "slim": {"cfg": "B_slim1 (V4: 16 bands, hop 256, TPP 8, CMSIS FFT)", "MHz": [37.7, 43.7]},
      "A": {"cfg": "A_spec (V4: float mix + 16/40-tap decimators, TPP 8)", "MHz": [30.6, 35.8]}}
VARIANTS = {"B": ["algo=2", "b_variant=0"], "slim": ["algo=2", "b_variant=1"], "A": ["algo=1"]}


def sh(cmd, cwd=None):
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=cwd)
    if p.returncode != 0:
        raise SystemExit(f"cycles: {' '.join(map(str, cmd[:3]))}... failed:\n{p.stderr[-2000:]}")
    return p.stdout


FMAC_DRIVER_EST = [500, 800]   # CPU cycles/hop of the U575 FMAC driver (16 x X2_BASE + START/stop + GPDMA re-arm, ~30-50 each) [L];
                               # the FMAC's own MACs run in the peripheral (V5-fmac-cordic.yaml), so the model is not costed


def arm_listing(tmp, defines=()):
    """[(func, file, line, mnemonic, ops)] for every instruction of SRCS, plus per-function code bytes."""
    rows, size = [], {}
    for s in SRCS:
        o = tmp / (Path(s).stem + ".o")
        sh(["arm-none-eabi-gcc", *fwsim.ARM_FLAGS, *defines, "-g", *fwsim.INC, "-c", FW / "core" / s, "-o", o])
        lst = sh(["arm-none-eabi-objdump", "-dl", "--no-show-raw-insn", o])
        func, f, ln, start, last = None, None, 0, 0, 0
        for line in lst.splitlines():
            m = re.match(r"^[0-9a-f]+ <(\w+)>:", line)
            if m:
                if func:
                    size[func] = last - start + 4
                func, start = m.group(1), None
                continue
            m = re.match(r"^(/\S+\.[ch]):(\d+)", line)
            if m:
                f, ln = Path(m.group(1)).name, int(m.group(2))
                continue
            m = re.match(r"^\s+([0-9a-f]+):\s+(\S+)\s*(.*)$", line)
            if m and func:
                a = int(m.group(1), 16)
                start = a if start is None else start
                last = a
                rows.append((func, f, ln, a, m.group(2), m.group(3).split("@")[0].strip()))
        if func:
            size[func] = last - start + 4
    return rows, size


def costs(rows):
    """[lo, hi] per instruction with cyccount's model (per function so branch direction and load pipelining are right)."""
    out = []
    by_fn = {}
    for r in rows:
        by_fn.setdefault(r[0], []).append(r)
    for fn, rs in by_fn.items():
        ins, _ = cc.analyse([(a, mn, ops) for _, _, _, a, mn, ops in rs])
        for r, (_, lo, hi, mem) in zip(rs, ins):
            out.append((fn, r[1], r[2], lo, hi))
    return out


def line_counts(tmp, words, d2, knobs, hops, defines=()):
    """gcov line execution counts {(file, line): count} after `hops` hops."""
    d = tmp / f"cov_{abs(hash((tuple(knobs), hops, d2, tuple(defines))))}"
    d.mkdir()
    exe = d / "drv"
    sh(["gcc", "--coverage", "-O0", "-std=c11", "-ffp-contract=off", "-fno-math-errno", *defines, *fwsim.INC,
        *[FW / "core" / s for s in SRCS + ["knobs.c", "crc32.c", "fmac_model.c"]], FW / "tools/cycdrv.c", "-lm", "-o", exe], cwd=d)
    per = 256 if d2 else 128
    words[: hops * per].astype("<i4").tofile(d / "w.i32")
    sh([exe, d / "w.i32", int(d2), *knobs], cwd=d)
    cnt, ranges = {}, {}
    for s in SRCS:
        gcda = next(d.glob(f"*-{Path(s).stem}.gcda"))
        j = json.loads(sh(["gcov", "--json-format", "--stdout", gcda.name], cwd=d))
        for fl in j["files"]:
            if Path(fl["file"]).name != s:
                continue
            for L in fl["lines"]:
                cnt[(s, L["line_number"])] = cnt.get((s, L["line_number"]), 0) + L["count"]
            for fn in fl["functions"]:
                ranges[fn["name"]] = (s, fn["start_line"], fn["end_line"], fn["execution_count"])
    cnt["__ranges__"] = ranges
    return cnt


_SRC = {}


def src_line(f, ln):
    if f not in _SRC:
        _SRC[f] = (FW / "core" / f).read_text().splitlines() if (FW / "core" / f).exists() else []
    L = _SRC[f]
    return L[ln - 1].strip() if 0 < ln <= len(L) else ""


def adjusted(cnt):
    """gcov counts a for-header once per condition test (iterations + 1 per entry); the ARM code attributed to it (increment,
    compare, branch) runs once per iteration: use the body's first executable line instead."""
    out = dict(cnt)
    for (f, ln), c in cnt.items():
        if src_line(f, ln).startswith("for ("):
            for k in range(ln + 1, ln + 4):
                if (f, k) in cnt and not src_line(f, k).startswith("for ("):
                    out[(f, ln)] = min(c, cnt[(f, k)])
                    break
    return out


def total(cost_rows, cnt):
    ranges = cnt["__ranges__"]
    cnt = adjusted({k: v for k, v in cnt.items() if k != "__ranges__"})
    lo = hi = ins = 0.0
    per_fn = {}
    prev = {}
    for fn, f, ln, clo, chi in cost_rows:
        base = fn.split(".")[0]                         # gcc clones: b_update.constprop.0 -> b_update
        own = ranges.get(base)
        inside = own is not None and own[0] == f and own[1] <= ln <= own[2]
        c = cnt.get((f, ln)) if inside else None
        if inside and (ln == own[1] or ln == own[2] or src_line(f, ln) in ("{", "}")):
            c = own[3]                                 # prologue / epilogue: once per call
        if c is None:                                  # inlined code from elsewhere, or no gcov record: the previous own line's count
            c = prev.get(fn, 0)
        prev[fn] = c
        lo += clo * c
        hi += chi * c
        ins += c
        a = per_fn.setdefault(fn, [0.0, 0.0])
        a[0] += clo * c
        a[1] += chi * c
    total.last_insns = ins
    return lo, hi, per_fn


def estimate(vector="sweep", transient=0, fmac=True):
    defines = () if fmac else ("-DFW_INTERP_FMAC=0",)
    z = np.load(REPO / f"sim/fw/vectors/{vector}.npz")
    words = z["words"]
    res = {}
    with tempfile.TemporaryDirectory(dir=str(FW / "out")) as t:
        tmp = Path(t)
        rows, size = arm_listing(tmp, defines)
        cr = costs(rows)
        n_all = len(words) // 128
        h1, h2 = n_all, max(600, n_all // 2)
        assert h1 - h2 >= 300, "vector too short for a steady-state difference"
        for v, kn in VARIANTS.items():
            kn = kn + [f"transient_only={transient}"]
            c1 = line_counts(tmp, words, False, kn, h1, defines)
            c2 = line_counts(tmp, words, False, kn, h2, defines)
            lo1, hi1, f1 = total(cr, c1)
            i1 = total.last_insns
            lo2, hi2, f2 = total(cr, c2)
            i2 = total.last_insns
            dh = h1 - h2
            lo, hi = (lo1 - lo2) / dh, (hi1 - hi2) / dh
            if fmac:
                lo, hi = lo + FMAC_DRIVER_EST[0], hi + FMAC_DRIVER_EST[1]
            fns = {k: [round((f1[k][0] - f2.get(k, [0, 0])[0]) / dh), round((f1[k][1] - f2.get(k, [0, 0])[1]) / dh)] for k in f1}
            fns = {k: x for k, x in sorted(fns.items(), key=lambda kv: -kv[1][1]) if x[1] > 0}
            used = [k for k in fns]
            res[v] = {"cycles_hop": [round(lo), round(hi)], "insns_hop_static": round((i1 - i2) / dh), "MHz_dsp": [round(lo * HOPS_PER_S / 1e6, 1), round(hi * HOPS_PER_S / 1e6, 1)],
                      "MHz_with_V4_overhead": [round(lo * HOPS_PER_S / 1e6 * 1.03 + 0.5, 1), round(hi * HOPS_PER_S / 1e6 * 1.08 + 0.5, 1)],
                      "per_function": fns, "code_bytes_used": sum(size.get(k, 0) for k in used),
                      "vector": vector, "hops_measured": dh, "v4": V4[v], "interp": "FMAC (+driver est %s)" % FMAC_DRIVER_EST if fmac else "CPU float"}
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    res = estimate()
    res.update({f"{v}_cpu": r for v, r in estimate(fmac=False).items()})
    for v, r in res.items():
        print(f"{v:5s} cycles/hop {r['cycles_hop']}  DSP {r['MHz_dsp']} MHz  +V4 overhead {r['MHz_with_V4_overhead']} MHz   V4 {r['v4']['MHz']} ({r['v4']['cfg']})  code {r['code_bytes_used']} B")
        print("      top:", ", ".join(f"{k} {x[0]}-{x[1]}" for k, x in list(r["per_function"].items())[:7]))
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
