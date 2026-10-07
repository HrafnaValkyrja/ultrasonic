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
        lo, hi_, counted, calib, fticks = struct.unpack("<5I", (Path(t) / "l0_count.bin").read_bytes())
    ticks = lo | (hi_ << 32)
    ipt = 2 * 65536 / calib
    return (ticks - fticks) * ipt / counted, ipt, counted, fticks * ipt / counted


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    words = np.load(REPO / "sim/fw/vectors/sweep.npz")["words"]
    res = {}
    for fmac in (True, False):
      elf = l0_arm.build(defines=("-DL0_COUNT",) + (() if fmac else ("-DFW_INTERP_FMAC=0",)))
      static = cycles.estimate(fmac=fmac)
      for v0, kn in cycles.VARIANTS.items():
        v = v0 if fmac else v0 + "_cpu"
        knobs = dict(x.split("=") for x in kn + ["transient_only=0"])
        q, ipt, counted, fm = run(elf, words, knobs)
        s = static[v0]
        mhz = lambda c: round(c * cycles.HOPS_PER_S / 1e6, 1)  # noqa: E731
        res[v] = {"MHz_static_V4ovh": s["MHz_with_V4_overhead"],
                  "MHz_qemu_corrected_V4ovh": [round(mhz(s["cycles_hop"][0] * q / s["insns_hop_static"]) * 1.03 + 0.5, 1),
                                               round(mhz(s["cycles_hop"][1] * q / s["insns_hop_static"]) * 1.08 + 0.5, 1)],"qemu_insns_hop": round(q), "static_insns_hop": s["insns_hop_static"], "ratio_qemu_static": round(q / s["insns_hop_static"], 3),
                  "static_cycles_hop": s["cycles_hop"], "cpi_implied": [round(s["cycles_hop"][0] / q, 2), round(s["cycles_hop"][1] / q, 2)],
                  "insns_per_tick": round(ipt, 3), "hops_counted": counted,
                  "fmac_model_insns_hop_excluded": round(fm), "note": "CPU instructions only: the FMAC model's own instructions (FMAC hardware work on the U575) are excluded"}
        print(v, {k: res[v][k] for k in ("MHz_static_V4ovh", "MHz_qemu_corrected_V4ovh", "qemu_insns_hop", "static_insns_hop", "ratio_qemu_static")})
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
