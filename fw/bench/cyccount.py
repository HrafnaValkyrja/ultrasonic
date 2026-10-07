#!/usr/bin/env python3
"""fw/bench/cyccount.py - static cycle count (FWSIM-R47 layer E1) of the V4 kernels.

Reads the arm-none-eabi-objdump listing of kernels.o, finds every loop (backward branch), charges
each instruction a [lo, hi] cycle cost from the Cortex-M4 TRM timing tables (proxy for the M33,
see CPI notes), multiplies each loop's exclusive body by its trip count (TRIPS, derived from the
C source and checked against the number of loops found), and adds SRAM wait states per data
access at the target clock. Output: per-kernel cycles per call, per-hop totals for algorithm A,
B and slim B, and MHz needed. This is a STATIC ESTIMATE, not a measurement (no hardware, no
cycle-accurate simulator available locally on 2026-10-07).

usage: cyccount.py name=kernels.lst:NB:TPP [...] [--json=out.json]
"""
import json
import re
import sys

# ---------------------------------------------------------------- CPI table [lo, hi]
# Cortex-M4 TRM r0p1 (ARM DDI 0439B) Table 3-1 (integer) and s7.2.3 (FPU): ALU 1; MUL 1; MLA/MLS 2;
# LDR/STR 2, or 1 when pipelined behind another load/store ("neighbouring loads/stores pipeline");
# LDRD/STRD 1+2; LDM/STM/PUSH/POP 1+N; branch taken 1+P, P = pipeline refill 1..3;
# VADD/VSUB/VMUL/VABS/VNEG/VCVT/VCMP/VMOV 1; VMLA/VFMA 3; VDIV/VSQRT 14; VLDR/VSTR 2 (1 pipelined);
# VLDM/VSTM/VPUSH/VPOP 1+N. FPv5 additions on the M33 (VSEL, VMAXNM/VMINNM, VRINT*) are not in
# the M4 table: charged 1 (single-cycle FP ALU ops on the same FPU datapath) [assumption].
P_LO, P_HI = 1, 3

LOADSTORE = re.compile(r"^(ldr|str)(b|h|sb|sh|t|ex|exb|exh)?(\.w|\.n)?$")
VLS = re.compile(r"^v(ldr|str)(\.\d+)?$")
VMULTI = re.compile(r"^v(ldm|stm|push|pop)")
MULTI = re.compile(r"^(ldm|stm|push|pop)")
COND = "(eq|ne|cs|hs|cc|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al)"
BR = re.compile(r"^b" + COND + r"?(\.w|\.n)?$")


def reglist_n(ops):
    m = re.search(r"\{([^}]*)\}", ops)
    if not m:
        return 1
    n = 0
    for r in m.group(1).split(","):
        r = r.strip()
        if "-" in r:
            a, b = r.split("-")
            n += int(b[1:]) - int(a[1:]) + 1
        else:
            n += 1
        # d registers are two words
    n *= 2 if re.search(r"\bd\d", m.group(1)) else 1
    return n


def cost(mn, ops, prev_ls):
    """[lo, hi] cycles, data accesses (words), is_loadstore."""
    base = mn.split(".")[0]
    if LOADSTORE.match(mn) or VLS.match(mn):
        return (1 if prev_ls else 2), 2, 1, True
    if base in ("ldrd", "strd"):
        return 3, 3, 2, True
    if VMULTI.match(base) or MULTI.match(base):
        n = reglist_n(ops)
        pc = 1 if "pc" in ops else 0
        return 1 + n + pc * P_LO, 1 + n + pc * P_HI, n, True
    if base in ("vdiv", "vsqrt"):
        return 14, 14, 0, False
    if re.match(r"^v(mla|mls|nmla|nmls|fma|fms|fnma|fnms)", base):
        return 3, 3, 0, False
    if base.startswith("v"):
        return 1, 1, 0, False
    if base in ("mla", "mls"):
        return 2, 2, 0, False
    if base in ("sdiv", "udiv"):
        return 2, 12, 0, False
    if base.startswith("it"):
        return 0, 1, 0, False
    if BR.match(mn) or base in ("cbz", "cbnz"):
        return None  # handled by caller (direction known there)
    if base in ("bl", "blx", "bx"):
        return 1 + P_LO, 1 + P_HI, 0, False
    return 1, 1, 0, False


def parse(lst):
    funcs, cur = {}, None
    for line in open(lst):
        m = re.match(r"^([0-9a-f]+) <(\w+)>:", line)
        if m:
            cur = m.group(2)
            funcs[cur] = []
            continue
        m = re.match(r"^\s+([0-9a-f]+):\s+(\S+)\s*(.*)$", line)
        if m and cur:
            ops = m.group(3).split("@")[0].strip()
            funcs[cur].append((int(m.group(1), 16), m.group(2), ops))
    return funcs


def analyse(insns):
    """Per instruction [lo, hi, mem]; loops as (start, end, branch_addr) sorted outer->inner."""
    loops, out, prev_ls = [], [], False
    for a, mn, ops in insns:
        c = cost(mn, ops, prev_ls)
        if c is None:  # branch
            m = re.match(r"^([0-9a-f]+)", ops.split(",")[-1].strip())
            tgt = int(m.group(1), 16) if m else None
            if tgt is not None and tgt <= a:          # backward: loop latch, taken every iteration
                loops.append((tgt, a))
                lo, hi = 1 + P_LO, 1 + P_HI
            elif mn.split(".")[0] == "b":               # unconditional forward jump
                lo, hi = 1 + P_LO, 1 + P_HI
            else:                                       # forward conditional: usually not taken
                lo, hi = 1, 1 + P_HI
            c = (lo, hi, 0, False)
        out.append((a, c[0], c[1], c[2]))
        prev_ls = c[3]
    loops.sort(key=lambda l: (l[0], -l[1]))
    return out, loops


# ---------------------------------------------------------------- trip counts (from kernels.c)
def trips(p):
    """Per function: trip count of each loop in (start address) order, as total executions of
    the loop BODY per call (inner loops = total over all outer iterations)."""
    NB, TPP, NBIN, HOP, OUT, UP = p["NB"], p["TPP"], 84, 128, 8, 16
    interp = [] if TPP <= 16 else [None]               # tap loop fully unrolled up to 16
    return {
        "in_window": [256 // 4],                 # unrolled x4
        "halfband_d2": [128],                    # 8 pairs fully unrolled
        "bitrev128": [56],                       # 56 swap pairs for 7-bit reversal (128 - 16 palindromes)/2
        "cfft128": [7, 127, 448],                # stages, twiddle groups (1+2+..+64), butterflies (7*64)
        "rsplit256": [63],
        "b_bands": [NB, NBIN],
        "b_update": [NB],
        "b_synth": [OUT, NB],                    # 8-sample ramp fully unrolled
        "a_mix": [HOP],
        "a_decim": [HOP // 4, OUT, OUT * 40 // 8, 15, 39],   # stage 1 (16 taps) fully unrolled, stage 2 x8
        "a_post": [OUT],
        "out_hop": [OUT, OUT, OUT * UP] + interp + [OUT * UP] + [TPP - 1],
        "a_mix_q15": [HOP],
        "a_decim_q15": [HOP // 4, OUT, 16, 40],             # both tap loops fully unrolled (SMLAD pairs)
        "out_hop_q15": [OUT, OUT, OUT * UP, OUT * UP, TPP - 1],
    }


def count(insns, nloops_expected, tripv):
    ins, loops = analyse(insns)
    if len(loops) != nloops_expected:
        raise SystemExit(f"loop count mismatch: found {len(loops)} {[(hex(a), hex(b)) for a, b in loops]}, expected {nloops_expected}")
    lo = hi = mem = 0.0
    body = [[0, 0, 0] for _ in loops]            # exclusive cycles per iteration [lo, hi, mem]
    for a, clo, chi, cm in ins:
        best = None                              # innermost loop containing a
        for i, (s, e) in enumerate(loops):
            if s <= a <= e and (best is None or (e - s) < (loops[best][1] - loops[best][0])):
                best = i
        mult = tripv[best] if best is not None else 1
        if best is not None:
            body[best][0] += clo; body[best][1] += chi; body[best][2] += cm
        lo += clo * mult
        hi += chi * mult
        mem += cm * mult
    return lo, hi, mem, loops, body


def run(lst, params):
    f = parse(lst)
    tv = trips(params)
    res = {}
    for name, t in tv.items():
        lo, hi, mem, loops, body = count(f[name], len(t), t)
        res[name] = {"lo": int(lo), "hi": int(hi), "mem": int(mem),
                     "loops": [{"range": [hex(s), hex(e)], "trips": n, "body_lo_hi_mem": b}
                               for (s, e), n, b in zip(loops, t, body)],
                     "code_bytes": f[name][-1][0] - f[name][0][0] + 4}
    return res


if __name__ == "__main__":
    # args: name=listing:NB:TPP ... [--json=out.json]
    out = {}
    for arg in sys.argv[1:]:
        if arg.startswith("--json="):
            continue
        name, rest = arg.split("=", 1)
        path, nb, tpp = rest.rsplit(":", 2)
        r = run(path, {"NB": int(nb), "TPP": int(tpp)})
        out[name] = {"params": {"NB": int(nb), "TPP": int(tpp)}, "kernels": r}
        print(f"== {name}: NB={nb} TPP={tpp}  (cycles per call = per 0.64 ms hop; mem = data words)")
        for k, v in r.items():
            lp = "; ".join(f"x{l['trips']} @{l['body_lo_hi_mem'][0]}-{l['body_lo_hi_mem'][1]}" for l in v["loops"])
            print(f"  {k:12s} {v['lo']:6d}-{v['hi']:6d} cyc  mem {v['mem']:5d}  code {v['code_bytes']:4d} B  loops: {lp}")
    for a in sys.argv[1:]:
        if a.startswith("--json="):
            json.dump(out, open(a.split("=", 1)[1], "w"), indent=1)
