"""sim/fw/fwlib.py: the host firmware build as a Python object (ctypes), for golden vectors (FWSIM-R8), L0/L1 (R7) and the e2e
firmware-in-the-loop stages (L2). Builds fw/core + fw/port_host/fake.c + sim/fw/shim.c into a shared library with the SAME flags
as fwsim's host build (fw/tools/fwsim.py HOST_FLAGS), cached under sim/out/fw/ by source hash.

    fw = Firmware(cc="gcc", knobs={"b_variant": 1})
    r = fw.run(words)            # dict: ccr, dsp (12.5 kS/s), band, floor, peak, sq, norm, clamp
"""
from __future__ import annotations

import ctypes as C
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
FW = REPO / "fw"
OUT = REPO / "sim/out/fw"
sys.path.insert(0, str(FW / "tools"))
import fwsim  # noqa: E402

F32P = np.ctypeslib.ndpointer(np.float32, flags="C_CONTIGUOUS")
I32P = np.ctypeslib.ndpointer(np.int32, flags="C_CONTIGUOUS")
U16P = np.ctypeslib.ndpointer(np.uint16, flags="C_CONTIGUOUS")
U32P = np.ctypeslib.ndpointer(np.uint32, flags="C_CONTIGUOUS")
_LIBS: dict = {}


def sources():
    return fwsim.CORE + [FW / "port_host/fake.c", REPO / "sim/fw/shim.c"]


def build(cc="gcc", opt="-O2", defines=()):
    srcs = sources()
    hdrs = sorted(p for d in ("core", "hal", "gen", "port_host") for p in (FW / d).glob("*.h"))
    h = hashlib.sha256()
    for p in srcs + hdrs:
        h.update(p.read_bytes())
    h.update(" ".join([cc, opt, *defines]).encode())
    tag = h.hexdigest()[:12]
    OUT.mkdir(parents=True, exist_ok=True)
    so = OUT / f"libfw_{cc}_{opt.strip('-')}_{tag}.so"
    if not so.exists():
        flags = [f for f in fwsim.HOST_FLAGS if f != "-O2"] + [opt]
        cmd = [cc, *flags, *fwsim.WARN, *defines, "-fPIC", "-shared", *fwsim.INC_HOST, *map(str, srcs), "-lm", "-o", str(so)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"fw host build failed ({cc}):\n{p.stderr[-3000:]}")
    return so


def lib(cc="gcc", opt="-O2", defines=()):
    key = (cc, opt, tuple(defines))
    if key in _LIBS:
        return _LIBS[key]
    L = C.CDLL(str(build(cc, opt, defines)))
    L.shim_state_size.restype = C.c_size_t
    L.shim_knob_id.argtypes = [C.c_char_p]
    L.shim_knob_id.restype = C.c_int32
    L.shim_init.argtypes = [C.c_void_p, I32P, I32P, C.c_int32]
    L.shim_init.restype = C.c_int32
    L.shim_set_noise.argtypes = [C.c_void_p, F32P, C.c_uint32]
    L.shim_set_noise.restype = C.c_int32
    L.shim_hash.argtypes = [C.c_void_p]
    L.shim_hash.restype = C.c_uint32
    L.shim_ccr_per_hop.argtypes = [C.c_void_p]
    L.shim_ccr_per_hop.restype = C.c_uint32
    L.shim_run.argtypes = [C.c_void_p, I32P, C.c_uint32, C.c_int32, U16P, F32P, F32P, F32P, F32P, U32P, F32P, U32P, C.c_uint64, U32P]
    L.shim_run.restype = C.c_int32
    L.shim_out.argtypes = [C.c_void_p, F32P, C.c_uint32, U16P, F32P, U32P]
    L.shim_out.restype = C.c_int32
    L.shim_set_loud.argtypes = [C.c_void_p, C.c_uint32]
    L.shim_set_loud.restype = None
    _LIBS[key] = L
    return L


class Firmware:
    """One firmware instance (fw_state_t in a ctypes buffer)."""

    def __init__(self, knobs=None, cc="gcc", opt="-O2", defines=(), noise=None):
        self.L = lib(cc, opt, defines)
        self.buf = C.create_string_buffer(self.L.shim_state_size())
        knobs = dict(knobs or {})
        ids, vals = [], []
        for k, v in knobs.items():
            i = self.L.shim_knob_id(k.encode())
            if i < 0:
                raise KeyError(f"unknown knob {k}")
            ids.append(i)
            vals.append(int(v))
        rc = self.L.shim_init(self.buf, np.array(ids, np.int32), np.array(vals, np.int32), len(ids))
        if rc:
            raise ValueError(f"knob rejected: {list(knobs.items())[rc - 1]}")
        if noise is not None:
            nb = np.ascontiguousarray(noise, np.float32)
            if self.L.shim_set_noise(self.buf, nb, len(nb)) != 0:
                raise ValueError("noise calibration length does not match the band count")
        self.per = self.L.shim_ccr_per_hop(self.buf)

    def run(self, words, d2=False, t0_us=0):
        """t0_us: time since power-on at the first hop (0 = the scene starts at power-on: 300 ms hold, e2e F4)."""
        w = np.ascontiguousarray(words, np.int32)
        hop_in = 256 if d2 else 128
        n = len(w) // hop_in
        w = w[: n * hop_in]
        r = dict(ccr=np.zeros(n * self.per, np.uint16), dsp=np.zeros(n * 8, np.float32), band=np.zeros(n * 28, np.float32),
                 floor=np.zeros(n * 28, np.float32), peak=np.zeros(n, np.float32), sq=np.zeros(n, np.uint32),
                 norm=np.zeros(n * 3, np.float32), clamp=np.zeros(n, np.uint32), mode=np.zeros(n, np.uint32))
        if self.L.shim_run(self.buf, w, n, int(d2), r["ccr"], r["dsp"], r["band"], r["floor"], r["peak"], r["sq"], r["norm"], r["clamp"], int(t0_us), r["mode"]):
            raise RuntimeError("fw_hop returned 0")
        r["band"] = r["band"].reshape(n, 28)
        r["floor"] = r["floor"].reshape(n, 28)
        r["norm"] = r["norm"].reshape(n, 3)
        return r

    def set_loud(self, on=True):
        self.L.shim_set_loud(self.buf, int(on))

    def out_stage(self, y12k):
        y = np.ascontiguousarray(y12k, np.float32)
        n = len(y) // 8
        ccr = np.zeros(n * self.per, np.uint16)
        peak = np.zeros(n, np.float32)
        sqp = np.zeros(n, np.uint32)
        self.L.shim_out(self.buf, y[: n * 8], n, ccr, peak, sqp)
        return ccr, peak, sqp

    def hash(self):
        return self.L.shim_hash(self.buf)
