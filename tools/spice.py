#!/usr/bin/env python3
"""Run ngspice in batch mode and get every analysis back as numpy arrays.

Library use (from the repo root, or put tools/ on sys.path first):

    import sys; sys.path.insert(0, "tools")
    import spice
    res = spice.run("sim/spice/rc.cir")        # a netlist path, or the netlist text itself
    t, v = res.tran["time"], res.tran["v(out)"] # last transient analysis; names are case-insensitive
    res.ac["frequency"], res.ac["v(out)"]       # complex arrays for AC
    res.op["v(out)"][0]                         # operating point (one point)
    res.meas["trise"]                           # every .meas result, as floats (nan if failed)
    spice.tavg(t, i, t0, t1), spice.trms(...)   # averages over ngspice's uneven time steps

The netlist should use dot-analyses (.tran/.ac/.dc/.op/.noise), not a .control block:
ngspice runs as `ngspice -b -r out.raw`, which saves every node voltage and source current
for each analysis. Add `.save` lines to keep device quantities such as @m1[id] or @m1[cgs].
Relative .include/.lib paths resolve against the netlist's directory; a netlist passed as
text runs from `cwd` (default: the current directory).

`compat="ps"` (or "lt", "psa", "ltpsa", ...) sets ngspice's `ngbehavior` for vendor
PSpice/LTspice models.

CLI:
    python3 tools/spice.py net.cir                          # list vectors + .meas results
    python3 tools/spice.py net.cir --plot "v(out),i(v1)" --png out.png [--analysis tran]
        [--xlim 0,1e-3] [--compat ps]
"""
from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

__all__ = ["run", "read_raw", "Plot", "SpiceResult", "SpiceError", "tavg", "trms", "resample",
           "ngspice_version"]

KIND_BY_PLOTNAME = {
    "transient analysis": "tran",
    "ac analysis": "ac",
    "dc transfer characteristic": "dc",
    "operating point": "op",
    "noise spectral density curves": "noise",
    "integrated noise": "noise_total",
    "transfer function": "tf",
    "pole-zero analysis": "pz",
    "sensitivity analysis": "sens",
    "distortion - 2nd harmonic": "disto",
}


class SpiceError(RuntimeError):
    """ngspice failed. `.log` holds the full ngspice output."""

    def __init__(self, msg: str, log: str = ""):
        super().__init__(msg)
        self.log = log


@dataclass
class Plot:
    """One analysis from a rawfile: named vectors sharing one scale (time, frequency, ...)."""
    title: str
    plotname: str
    kind: str
    names: list[str]
    types: list[str]
    data: dict[str, np.ndarray]

    @property
    def scale(self) -> np.ndarray:
        """The independent variable (first vector): time, frequency, sweep value."""
        return self.data[self.names[0]]

    def __getitem__(self, name: str) -> np.ndarray:
        key = name.lower().replace(" ", "")
        cands = [key, f"v({key})"]                      # "out" -> "v(out)"
        if key.startswith("i(") and key.endswith(")"):
            cands.append(key[2:-1] + "#branch")         # "i(v1)" -> "v1#branch"
        if key.endswith("#branch"):
            cands.append(f"i({key[:-7]})")              # "v1#branch" -> "i(v1)"
        for c in cands:
            if c in self.data:
                return self.data[c]
        raise KeyError(f"no vector {name!r} in {self.plotname!r}; have: {', '.join(self.names)}")

    def __contains__(self, name: str) -> bool:
        try:
            self[name]
            return True
        except KeyError:
            return False

    def __repr__(self):
        n = len(self.scale) if self.names else 0
        return f"<Plot {self.kind} '{self.plotname}': {len(self.names)} vectors x {n} points>"


@dataclass
class SpiceResult:
    plots: list[Plot]
    meas: dict[str, float]
    log: str
    warnings: list[str] = field(default_factory=list)

    def get(self, kind: str) -> Plot:
        """Last analysis of this kind ('tran', 'ac', 'dc', 'op', 'noise', ...)."""
        for p in reversed(self.plots):
            if p.kind == kind:
                return p
        raise KeyError(f"no '{kind}' analysis in results (have: {[p.kind for p in self.plots]})")

    tran = property(lambda self: self.get("tran"))
    ac = property(lambda self: self.get("ac"))
    dc = property(lambda self: self.get("dc"))
    op = property(lambda self: self.get("op"))
    noise = property(lambda self: self.get("noise"))

    def __getitem__(self, name: str) -> np.ndarray:
        """Vector from the last analysis."""
        return self.plots[-1][name]


# ----------------------------------------------------------------------------- raw files
def read_raw(path: str | os.PathLike) -> list[Plot]:
    """Parse an ngspice/SPICE3 rawfile (binary or ASCII; one or more analyses)."""
    buf = Path(path).read_bytes()
    plots, pos = [], 0
    while pos < len(buf):
        header, meta, names, types = {}, None, [], []
        # --- header, line by line
        while True:
            end = buf.find(b"\n", pos)
            if end < 0:
                return plots
            line = buf[pos:end].decode("latin-1").rstrip("\r")
            pos = end + 1
            if not line.strip():
                continue
            if line.startswith("Variables:"):
                nvars = int(header["no. variables"])
                for _ in range(nvars):
                    end = buf.find(b"\n", pos)
                    parts = buf[pos:end].decode("latin-1").split()
                    pos = end + 1
                    names.append(parts[1].lower())
                    types.append(parts[2] if len(parts) > 2 else "")
                continue
            if line.startswith(("Binary:", "Values:")):
                meta = line[:-1].lower()
                break
            if ":" in line:
                k, v = line.split(":", 1)
                header[k.strip().lower()] = v.strip()
        nvars = len(names)
        npts = int(header.get("no. points", "0"))
        complex_ = "complex" in header.get("flags", "").lower()
        if meta == "binary":
            width = 16 if complex_ else 8
            avail = (len(buf) - pos) // (nvars * width)
            npts = min(npts, avail) if npts else avail
            nbytes = npts * nvars * width
            arr = np.frombuffer(buf, dtype="<f8", count=nbytes // 8, offset=pos)
            pos += nbytes
            if complex_:
                arr = arr.reshape(npts, nvars, 2)
                arr = arr[..., 0] + 1j * arr[..., 1]
            else:
                arr = arr.reshape(npts, nvars)
        else:  # ASCII "Values:"
            vals = []
            text_end = buf.find(b"\nTitle:", pos)
            chunk = buf[pos:text_end if text_end >= 0 else len(buf)].decode("latin-1")
            pos = text_end + 1 if text_end >= 0 else len(buf)
            toks = chunk.split()
            i = 0
            while i < len(toks):
                i += 1  # point index
                row = []
                for _ in range(nvars):
                    t = toks[i]
                    i += 1
                    if complex_:
                        re_, im_ = t.split(",")
                        row.append(complex(float(re_), float(im_)))
                    else:
                        row.append(float(t))
                vals.append(row)
            arr = np.array(vals, dtype=complex if complex_ else float).reshape(-1, nvars)
        data = {}
        for j, n in enumerate(names):
            col = np.array(arr[:, j])
            # the scale (time/frequency) of a complex plot is real
            if complex_ and j == 0 and np.all(col.imag == 0):
                col = col.real
            data[n] = col
        pname = header.get("plotname", "")
        kind = KIND_BY_PLOTNAME.get(pname.lower(), pname.lower().split()[0] if pname else "?")
        plots.append(Plot(header.get("title", ""), pname, kind, names, types, data))
    return plots


# ----------------------------------------------------------------------------- running
_MEAS_RE = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*=\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|failed)", re.M)


def _parse_meas(log: str) -> dict[str, float]:
    out = {}
    for block in re.split(r"Measurements for ", log)[1:]:
        # a block ends at the first blank line after the results
        body = block.split("\n", 1)[1] if "\n" in block else ""
        for m in _MEAS_RE.finditer(body.split("\n\n\n")[0]):
            val = m.group(2)
            out[m.group(1).lower()] = math.nan if val == "failed" else float(val)
    # measurements that fail are also reported as "Error: measure  name  ..."
    for m in re.finditer(r"measure\s+(\w+)\s+failed", log, re.I):
        out.setdefault(m.group(1).lower(), math.nan)
    return out


def ngspice_version(exe: str = "ngspice") -> str:
    out = subprocess.run([exe, "-v"], capture_output=True, text=True).stdout
    m = re.search(r"ngspice-(\S+)", out)
    return m.group(1) if m else "?"


def run(netlist: str | os.PathLike, *, cwd: str | os.PathLike | None = None, compat: str | None = None,
        timeout: float = 600, keep: str | os.PathLike | None = None, exe: str = "ngspice",
        check: bool = True) -> SpiceResult:
    """Run a netlist (path or text) in ngspice batch mode; return all analyses as numpy arrays.

    compat  ngspice `ngbehavior` value for vendor models, e.g. "ps", "lt", "psa", "ltpsa".
    keep    directory to copy the rawfile and log into (default: discard).
    check   raise SpiceError on ngspice errors (else return what exists, errors in .warnings).
    """
    if shutil.which(exe) is None:
        raise SpiceError(f"{exe} not found; run tools/setup.sh")
    is_path = isinstance(netlist, os.PathLike) or ("\n" not in str(netlist) and Path(str(netlist)).is_file())
    with tempfile.TemporaryDirectory(prefix="spice-") as tmp:
        tmp = Path(tmp)
        if is_path:
            net = Path(netlist).resolve()
            run_dir = net.parent
        else:
            text = str(netlist)
            if not text.rstrip().lower().endswith(".end"):
                text = text.rstrip() + "\n.end\n"
            net = tmp / "netlist.cir"
            net.write_text(text)
            run_dir = Path(cwd).resolve() if cwd else Path.cwd()
        raw, logf = tmp / "out.raw", tmp / "out.log"
        cmd = [exe, "-b", "-r", str(raw), "-o", str(logf)]
        if compat:
            cmd += ["-D", f"ngbehavior={compat}"]
        cmd.append(str(net))
        env = dict(os.environ, SPICE_ASCIIRAWFILE="0")
        try:
            proc = subprocess.run(cmd, cwd=run_dir, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired as e:
            raise SpiceError(f"ngspice timed out after {timeout} s", str(e.stdout or "")) from None
        log = (logf.read_text(errors="replace") if logf.exists() else "") + proc.stdout + proc.stderr
        errors = [ln.strip() for ln in log.splitlines()
                  if re.search(r"\berror\b|fatal|aborted|timestep too small|singular matrix", ln, re.I)
                  and "no error" not in ln.lower()]
        warnings = [ln.strip() for ln in log.splitlines() if re.search(r"\bwarning\b", ln, re.I)]
        plots = read_raw(raw) if raw.exists() and raw.stat().st_size > 0 else []
        # ngspice (42) refuses `.meas` when batch mode writes a rawfile ("No .measure possible
        # in batch mode (-b) with -r rawfile set!"), so measurements need a second batch pass
        # without -r. It re-runs the simulation; only netlists that use .meas pay for it.
        meas_log = ""
        if re.search(r"^\s*\.meas", net.read_text(errors="replace"), re.I | re.M):
            mlog = tmp / "meas.log"
            mcmd = [c for c in cmd if c not in ("-r", str(raw), "-o", str(logf))]
            mcmd[mcmd.index(str(net)):mcmd.index(str(net))] = ["-o", str(mlog)]
            try:
                mproc = subprocess.run(mcmd, cwd=run_dir, capture_output=True, text=True,
                                       timeout=timeout, env=env)
            except subprocess.TimeoutExpired as e:
                raise SpiceError(f"ngspice (.meas pass) timed out after {timeout} s", str(e.stdout or "")) from None
            meas_log = (mlog.read_text(errors="replace") if mlog.exists() else "") + mproc.stdout + mproc.stderr
            log += "\n--- .meas pass ---\n" + meas_log
        if keep:
            kd = Path(keep)
            kd.mkdir(parents=True, exist_ok=True)
            for f in (raw, logf):
                if f.exists():
                    shutil.copy(f, kd / f"{net.stem}{f.suffix}")
        if check and (proc.returncode != 0 or errors or not plots):
            tail = "\n".join(log.splitlines()[-40:])
            why = "; ".join(errors[:5]) or f"exit code {proc.returncode}" + ("" if plots else ", no analysis output")
            raise SpiceError(f"ngspice failed: {why}\n--- log tail ---\n{tail}", log)
        return SpiceResult(plots, _parse_meas(meas_log or log), log, warnings + errors)


# ----------------------------------------------------------------------------- helpers
def _window(t, y, t0, t1):
    t = np.asarray(t, float)
    y = np.asarray(y)
    t0 = t[0] if t0 is None else t0
    t1 = t[-1] if t1 is None else t1
    m = (t >= t0) & (t <= t1)
    return t[m], y[m]


def tavg(t, y, t0=None, t1=None) -> float:
    """Time average of y over [t0, t1] on ngspice's non-uniform time grid (trapezoidal)."""
    tt, yy = _window(t, y, t0, t1)
    return float(np.trapezoid(yy, tt) / (tt[-1] - tt[0]))


def trms(t, y, t0=None, t1=None) -> float:
    """RMS of y over [t0, t1] on a non-uniform time grid."""
    tt, yy = _window(t, y, t0, t1)
    return float(np.sqrt(np.trapezoid(np.abs(yy) ** 2, tt) / (tt[-1] - tt[0])))


def resample(t, y, dt, t0=None, t1=None):
    """Linear interpolation onto a uniform grid (for FFTs). Returns (t_uniform, y_uniform)."""
    t = np.asarray(t, float)
    t0 = t[0] if t0 is None else t0
    t1 = t[-1] if t1 is None else t1
    tu = np.arange(t0, t1, dt)
    return tu, np.interp(tu, t, np.asarray(y, float))


# ----------------------------------------------------------------------------- CLI
def _summary(res: SpiceResult) -> str:
    lines = []
    for p in res.plots:
        n = len(p.scale)
        lines.append(f"== {p.kind}: {p.plotname} ({len(p.names)} vectors, {n} points)")
        for name, typ in zip(p.names, p.types):
            v = p.data[name]
            if np.iscomplexobj(v):
                mag = np.abs(v)
                lines.append(f"   {name:<28} {typ:<10} |x| min {mag.min():.4g}  max {mag.max():.4g}")
            else:
                lines.append(f"   {name:<28} {typ:<10} min {v.min():.4g}  max {v.max():.4g}  last {v[-1]:.4g}")
    if res.meas:
        lines.append("== .meas")
        for k, v in res.meas.items():
            lines.append(f"   {k:<28} {v:.6g}")
    return "\n".join(lines)


def plot(res: SpiceResult, names: list[str], png: str | os.PathLike, analysis: str | None = None,
         xlim: tuple[float, float] | None = None, title: str | None = None):
    """One stacked subplot per signal (shared x). AC signals get magnitude (dB) and phase rows."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import plotstyle
    plt = plotstyle.apply()
    p = res.get(analysis) if analysis else res.plots[-1]
    x = p.scale
    is_ac = p.kind == "ac"
    rows = []
    for n in names:
        v = p[n]
        if np.iscomplexobj(v) or is_ac:
            rows.append((n, "|%s| (dB)" % n, 20 * np.log10(np.maximum(np.abs(v), 1e-30))))
            rows.append((n, "phase %s (deg)" % n, np.degrees(np.unwrap(np.angle(v)))))
        else:
            rows.append((n, n, v))
    fig, axes = plt.subplots(len(rows), 1, sharex=True, figsize=(8, 1.9 * len(rows) + 0.6), squeeze=False)
    for i, (ax, (_, label, y)) in enumerate(zip(axes[:, 0], rows)):
        ax.plot(x, y, color=plotstyle.SERIES[i % len(plotstyle.SERIES)])
        ax.set_ylabel(label)
        if is_ac:
            ax.set_xscale("log")
    xl = p.names[0]
    axes[-1, 0].set_xlabel("frequency (Hz)" if is_ac else ("time (s)" if xl == "time" else xl))
    if xlim:
        axes[-1, 0].set_xlim(*xlim)
    axes[0, 0].set_title(title or f"{p.plotname}: {p.title}")
    fig.align_ylabels()
    fig.savefig(png)
    plt.close(fig)
    return Path(png)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("netlist")
    ap.add_argument("--plot", help="comma-separated vectors to plot, e.g. 'v(out),i(v1)'")
    ap.add_argument("--png", help="PNG path for --plot (default: <netlist>.png)")
    ap.add_argument("--analysis", help="tran, ac, dc, op, noise (default: last analysis)")
    ap.add_argument("--xlim", help="x range as 'min,max'")
    ap.add_argument("--compat", help="ngbehavior for vendor models: ps, lt, psa, ltpsa, ...")
    ap.add_argument("--keep", help="directory to keep the rawfile and log")
    a = ap.parse_args(argv)
    try:
        res = run(a.netlist, compat=a.compat, keep=a.keep)
    except SpiceError as e:
        print(e, file=sys.stderr)
        return 1
    print(_summary(res))
    if a.plot:
        png = a.png or str(Path(a.netlist).with_suffix(".png"))
        xlim = tuple(float(v) for v in a.xlim.split(",")) if a.xlim else None
        plot(res, [s.strip() for s in a.plot.split(",") if s.strip()], png, a.analysis, xlim)
        print(f"plot: {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
