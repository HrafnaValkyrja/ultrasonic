#!/usr/bin/env python3
"""sim/fw/l0_arm.py: comparison level L0, ARM vs host (FWSIM-R7): the fw/core objects built exactly as the product (fwsim ARM_FLAGS,
arm-none-eabi-gcc, Cortex-M33 FPv5-SP hard float) run on QEMU mps2-an505 (Cortex-M33; qemu-system-arm, GPL-2.0, installed
2026-10-07) over every golden vector x variant; every CCR word and tap must equal the host build (sim/fw/fwlib.py) bit for bit.
I/O by Arm semihosting (fw/port_qemu/l0_main.c).  python3 sim/fw/l0_arm.py [--json PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FW = REPO / "fw"
sys.path[:0] = [str(HERE), str(FW / "tools")]
import fwlib  # noqa: E402
import fwsim  # noqa: E402
import gen_vectors as gv  # noqa: E402

OUT = REPO / "sim/out/fw"
QEMU = ["qemu-system-arm", "-M", "mps2-an505", "-nographic", "-monitor", "none", "-serial", "none",
        "-semihosting-config", "enable=on,target=native"]


def build(defines=()):
    core = [p for p in fwsim.CORE if p.stem not in ("app", "knob_store")]          # no HAL users in the L0 image
    srcs = core + sorted((FW / "port_qemu").glob("*.c"))
    h = hashlib.sha256()
    for p in srcs + sorted(p for d in ("core", "gen", "hal") for p in (FW / d).glob("*.h")) + [FW / "port_qemu/an505.ld"]:
        h.update(p.read_bytes())
    h.update(" ".join(fwsim.ARM_FLAGS + list(defines)).encode())
    elf = OUT / f"l0_an505_{h.hexdigest()[:12]}.elf"
    if not elf.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        cmd = ["arm-none-eabi-gcc", *fwsim.ARM_FLAGS, *defines, *fwsim.WARN, "-Wno-conversion", *fwsim.INC, *map(str, srcs),
               "-T", str(FW / "port_qemu/an505.ld"), "-nostartfiles", "--specs=nano.specs", "-Wl,--gc-sections", "-o", str(elf)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode:
            raise SystemExit(f"l0_arm: ARM build failed\n{p.stderr[-3000:]}")
    return elf


def run_arm(elf, words, knobs, d2, t0_us=0):
    L = fwlib.lib()
    ids = [(L.shim_knob_id(k.encode()), int(v)) for k, v in knobs.items()]
    per_in = 256 if d2 else 128
    n = len(words) // per_in
    hdr = struct.pack("<6I", 0x304C5746, n, int(d2), t0_us & 0xFFFFFFFF, t0_us >> 32, len(ids))
    hdr += b"".join(struct.pack("<Ii", i, v) for i, v in ids)
    with tempfile.TemporaryDirectory(dir=str(OUT)) as t:
        (Path(t) / "l0_in.bin").write_bytes(hdr + np.ascontiguousarray(words[: n * per_in], "<i4").tobytes())
        p = subprocess.run([*QEMU, "-kernel", str(elf)], cwd=t, capture_output=True, text=True, timeout=900)
        if p.returncode != 0:
            raise RuntimeError(f"qemu exit {p.returncode}: {p.stderr[-500:]}")
        raw = (Path(t) / "l0_out.bin").read_bytes()
    return raw, n


def host_bytes(words, knobs, d2, t0_us=0):
    """the host run serialised like l0_main.c"""
    fw = fwlib.Firmware(knobs)
    r = fw.run(words, d2=d2, t0_us=t0_us)
    per = fw.per
    out = bytearray()
    for h in range(len(r["peak"])):
        out += r["ccr"][h * per:(h + 1) * per].astype("<u2").tobytes()
        out += r["dsp"][h * 8:(h + 1) * 8].astype("<f4").tobytes()
        out += r["band"][h].astype("<f4").tobytes() + r["floor"][h].astype("<f4").tobytes()
        out += np.float32(r["peak"][h]).tobytes() + r["norm"][h].astype("<f4").tobytes()
        out += struct.pack("<II", int(r["sq"][h]), int(r["clamp"][h]))
    return bytes(out), r, per


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    elf = build()
    vecs, _ = gv.load()
    rows, bad, t0 = [], [], time.time()
    for name, (arrays, meta) in vecs.items():
        for v in meta["variants"]:
            knobs = dict(gv.FW_KNOBS[v], **({} if v == "A" else {"transient_only": meta["transient_only"]}))
            d2 = meta["front"] == "D2"
            arm, n = run_arm(elf, arrays["words"], knobs, d2)
            host, r, per = host_bytes(arrays["words"], knobs, d2)
            same = arm == host
            first = None
            if not same:
                rec = len(host) // max(n, 1)
                diff = next((i for i in range(min(len(arm), len(host))) if arm[i] != host[i]), min(len(arm), len(host)))
                first = f"hop {diff // rec}, byte {diff % rec} of {rec} (ccr 0..{2 * per - 1}, then dsp, band, floor, peak, norm, sq, clamp); lens {len(arm)}/{len(host)}"
                bad.append(f"{name}.{v}: {first}")
            rows.append(dict(id=f"{name}.{v}", hops=n, bytes=len(host), equal=same, sha=hashlib.sha256(arm).hexdigest()[:12], first_diff=first))
            print(f"{'PASS' if same else 'FAIL'} {name}.{v:5s} {n} hops, {len(host)} B" + ("" if same else f"  {first}"), flush=True)
    res = {"status": "PASS" if not bad else "FAIL", "runs": len(rows), "mismatches": bad, "rows": rows, "elf": str(elf.relative_to(REPO)),
           "qemu": subprocess.run(["qemu-system-arm", "--version"], capture_output=True, text=True).stdout.splitlines()[0], "wall_s": round(time.time() - t0, 1)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "l0_arm.json").write_text(json.dumps(res, indent=1) + "\n")
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")
    print(f"l0_arm: {res['status']} ({len(rows)} runs, {res['wall_s']} s)")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
