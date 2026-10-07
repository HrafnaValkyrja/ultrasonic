#!/usr/bin/env python3
"""sim/fw/qemu_icount.py: per-hop instruction counts of the ARM build on QEMU mps2-an505 (FWSIM-R47 layer E2 cross-check).
QEMU cannot time a Cortex-M33 (no pipeline/wait-state model), but with -icount shift=0 virtual time advances 1 ns per executed guest
instruction and SysTick (processor clock) counts it: fw/port_qemu/l0_main.c built with -DL0_COUNT brackets every fw_hop with SysTick
reads and calibrates instructions per tick with a 2-instruction loop. Same vector, knobs and counted hops as fw/tools/cycles.py
(sweep, full mode, hops 600..end: active path after the power-on hold); compares with the static model's instruction count.
  python3 sim/fw/qemu_icount.py [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO / "fw/tools")]
import cycles  # noqa: E402
import fwlib  # noqa: E402
import l0_arm  # noqa: E402

SKIP = 600


def run(elf, words, knobs):
    L = fwlib.lib()
    ids = [(L.shim_knob_id(k.encode()), int(v)) for k, v in knobs.items()]
    n = len(words) // 128
    hdr = struct.pack("<6I", 0x304C5746, n, SKIP << 8, 0, 0, len(ids)) + b"".join(struct.pack("<Ii", i, v) for i, v in ids)
    with tempfile.TemporaryDirectory(dir=str(l0_arm.OUT)) as t:
        (Path(t) / "l0_in.bin").write_bytes(hdr + np.ascontiguousarray(words[: n * 128], "<i4").tobytes())
        p = subprocess.run([*l0_arm.QEMU, "-icount", "shift=0", "-kernel", str(elf)], cwd=t, capture_output=True, text=True, timeout=900)
        if p.returncode:
            raise RuntimeError(p.stderr[-400:])
        lo, hi_, counted, calib = struct.unpack("<4I", (Path(t) / "l0_count.bin").read_bytes())
    ticks = lo | (hi_ << 32)
    ipt = 2 * 65536 / calib
    return ticks * ipt / counted, ipt, counted


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    elf = l0_arm.build(defines=("-DL0_COUNT",))
    words = np.load(REPO / "sim/fw/vectors/sweep.npz")["words"]
    static = cycles.estimate()
    res = {}
    for v, kn in cycles.VARIANTS.items():
        knobs = dict(x.split("=") for x in kn + ["transient_only=0"])
        q, ipt, counted = run(elf, words, knobs)
        s = static[v]
        res[v] = {"qemu_insns_hop": round(q), "static_insns_hop": s["insns_hop_static"], "ratio_qemu_static": round(q / s["insns_hop_static"], 3),
                  "static_cycles_hop": s["cycles_hop"], "cpi_implied": [round(s["cycles_hop"][0] / q, 2), round(s["cycles_hop"][1] / q, 2)],
                  "insns_per_tick": round(ipt, 3), "hops_counted": counted}
        print(v, res[v])
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
