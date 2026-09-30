#!/usr/bin/env python3
"""Smoke tests for the engineering harness: every tool must actually do its job once.

    source tools/env.sh && python3 tools/smoke/run_all.py [--offline] [--keep DIR] [-k NAME]

Each test builds something tiny, checks a physical or numerical answer where there is one,
and reports PASS/FAIL with timing. --offline skips tests that need the network (easyeda2kicad,
JLC API). Exit status is non-zero if any test fails.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))


def sh(cmd, cwd=None, timeout=300, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                       shell=isinstance(cmd, str))
    if check and r.returncode != 0:
        raise RuntimeError(f"command failed ({r.returncode}): {cmd}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r


# ---------------------------------------------------------------- tests
def t_ngspice(w: Path) -> str:
    import spice
    net = """RC low-pass step response
V1 in 0 PULSE(0 1 0 1n 1n 10m 20m)
R1 in out 1k
C1 out 0 1u
.tran 10u 5m
.meas tran t63 WHEN v(out)=0.632 RISE=1
.end
"""
    res = spice.run(net, cwd=w)
    tau = res.meas["t63"]
    assert abs(tau - 1e-3) / 1e-3 < 0.02, f"tau {tau:.4g} s, expected 1 ms"
    return f"RC time constant {tau * 1e3:.3f} ms (expected 1.000)"


def _board(w: Path):
    import pcbnew
    mm = pcbnew.FromMM
    b = pcbnew.BOARD()
    pts = [(0, 0), (20, 0), (20, 12), (0, 12)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        s.SetWidth(mm(0.1))
        b.Add(s)
    lib = os.path.join(os.environ["KICAD10_FOOTPRINT_DIR"], "Resistor_SMD.pretty")
    nets = {}
    for name in ("A", "B"):
        nets[name] = pcbnew.NETINFO_ITEM(b, name)
        b.Add(nets[name])
    fps = []
    for ref, x in (("R1", 5), ("R2", 15)):
        fp = pcbnew.FootprintLoad(lib, "R_0603_1608Metric")
        fp.SetReference(ref)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(6)))
        b.Add(fp)
        fps.append(fp)
    pads = {(f.GetReference(), p.GetNumber()): p for f in fps for p in f.Pads()}
    pads[("R1", "2")].SetNet(nets["A"]); pads[("R2", "1")].SetNet(nets["A"])
    pads[("R1", "1")].SetNet(nets["B"]); pads[("R2", "2")].SetNet(nets["B"])
    return b


def t_kicad_freerouting(w: Path) -> str:
    import pcbnew
    b = _board(w)
    pcb, dsn, ses, routed = (w / n for n in ("t.kicad_pcb", "t.dsn", "t.ses", "t_routed.kicad_pcb"))
    pcbnew.SaveBoard(str(pcb), b)
    assert pcbnew.ExportSpecctraDSN(b, str(dsn)), "DSN export failed"
    sh([os.environ["FREEROUTING_JAVA"], *os.environ.get("FREEROUTING_JAVA_OPTS", "-Xmx1g").split(), "-jar", os.environ["FREEROUTING_JAR"], "-de", str(dsn),
        "-do", str(ses), "-mp", "20", "--gui.enabled=false"], timeout=240)
    b = pcbnew.LoadBoard(str(pcb))
    assert pcbnew.ImportSpecctraSES(b, str(ses)), "SES import failed"
    n_tracks = len(b.GetTracks())
    pcbnew.SaveBoard(str(routed), b)
    drc = w / "drc.json"
    sh(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-error", "--output", str(drc), str(routed)],
       check=False)
    d = json.loads(drc.read_text())
    viol, unconn = len(d.get("violations", [])), len(d.get("unconnected_items", []))
    assert n_tracks > 0 and viol == 0 and unconn == 0, f"tracks {n_tracks}, DRC {viol}, unconnected {unconn}"
    sh(["kicad-cli", "pcb", "export", "gerbers", "--output", str(w / "gerbers"), str(routed)])
    n_gbr = len(list((w / "gerbers").glob("*")))
    sh(["kicad-cli", "pcb", "render", "--output", str(w / "render.png"), "--width", "600", "--height", "360",
        "--zoom", "2.5", "--background", "opaque", str(routed)], timeout=180)
    from PIL import Image
    counts = sorted(c for c, _ in Image.open(w / "render.png").convert("RGB").getcolors(1 << 20))
    share = counts[-1] / sum(counts)  # flat-shaded renders use few colours; an empty one is ~all one colour
    assert len(counts) >= 10 and share < 0.97, f"3D render looks empty ({len(counts)} colours, {share:.0%} one colour)"
    return f"autorouted {n_tracks} tracks, DRC 0 errors / 0 unconnected, {n_gbr} Gerber files, 3D render OK"


def t_skidl(w: Path) -> str:
    cwd = os.getcwd()
    os.chdir(w)
    try:
        import skidl
        from skidl import Net, Part, generate_netlist, set_default_tool
        tool = skidl.KICAD10                      # env.sh points SKiDL at the KiCad 10 libraries
        set_default_tool(tool)
        vin, vout, gnd = Net("VIN"), Net("VOUT"), Net("GND")
        r = Part("Device", "R", value="1k", footprint="Resistor_SMD:R_0603_1608Metric", ref="R1")
        c = Part("Device", "C", value="1u", footprint="Capacitor_SMD:C_0603_1608Metric", ref="C1")
        r.fields["LCSC"] = "C21190"               # 1k 0603, JLC Basic
        vin += r[1]; vout += r[2], c[1]; gnd += c[2]
        out = w / "rc.net"
        generate_netlist(file_=str(out))
        txt = out.read_text()
    finally:
        os.chdir(cwd)
    assert "VOUT" in txt and "R_0603" in txt and "C21190" in txt, "netlist missing expected content"
    return f"netlist {len(txt)} bytes with 2 parts, 3 nets ({tool})"


def t_arm_gcc(w: Path) -> str:
    src = w / "dsp.c"
    src.write_text("""
#include <math.h>
float mix(const float *x, float *y, int n, float w) {
    float acc = 0.0f;
    for (int i = 0; i < n; i++) { y[i] = x[i] * cosf(w * (float)i); acc += y[i] * y[i]; }
    return sqrtf(acc);
}
""")
    obj = w / "dsp.o"
    sh(["arm-none-eabi-gcc", "-mcpu=cortex-m4", "-mthumb", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard",
        "-O2", "-ffast-math", "-c", str(src), "-o", str(obj)])
    size = sh(["arm-none-eabi-size", str(obj)]).stdout.splitlines()[-1].split()[0]
    dis = sh(["arm-none-eabi-objdump", "-d", str(obj)]).stdout
    assert "vmul.f32" in dis or "vfma.f32" in dis or "vmla.f32" in dis, "no hardware-float instructions"
    return f"Cortex-M4F object, {size} bytes of code, uses the FPU"


def t_easyeda2kicad(w: Path) -> str:
    out = w / "lcsc" / "mic"
    out.parent.mkdir(parents=True, exist_ok=True)
    exe = Path(sys.executable).with_name("easyeda2kicad")
    sh([str(exe), "--footprint", "--symbol", "--lcsc_id=C2879853", f"--output={out}"], timeout=120)
    mods = list(w.glob("lcsc/**/*.kicad_mod"))
    syms = list(w.glob("lcsc/**/*.kicad_sym"))
    assert mods and syms, "no footprint/symbol produced"
    return f"SPH0641LU4H-1 (C2879853): {mods[0].name} + symbol library"


def t_jlc(w: Path) -> str:
    import jlc
    rows = jlc.search("C2879853", 3)
    assert rows and rows[0]["lcsc"] == "C2879853", "lookup failed"
    return f"{rows[0]['mpn']} {rows[0]['library']} stock {rows[0]['stock']} ({rows[0]['queried_utc']})"


def t_build123d(w: Path) -> str:
    from build123d import Box, Pos, export_stl, export_step
    body = Pos(10, 6, 2) * Box(20, 12, 4) - Pos(10, 6, 2) * Box(6, 6, 4)  # 20x12x4 mm with a 6x6 window
    vol = body.volume
    assert abs(vol - (20 * 12 * 4 - 6 * 6 * 4)) < 1e-6, f"volume {vol}"
    com = body.center()
    export_stl(body, str(w / "part.stl"))
    export_step(body, str(w / "part.step"))
    mass_g = vol * 1e-3 * 1.01  # PA12 nylon ~1.01 g/cm^3
    return f"volume {vol:.0f} mm^3 (PA12 {mass_g:.2f} g), centre ({com.X:.1f}, {com.Y:.1f}, {com.Z:.1f}) mm, STL+STEP written"


def t_scikit_fem(w: Path) -> str:
    """Cantilever in plane stress vs Euler-Bernoulli: tip deflection F L^3 / (3 E I)."""
    import numpy as np
    from skfem import (Basis, ElementTriP2, ElementVector, FacetBasis, LinearForm, MeshTri,
                       asm, condense, solve)
    from skfem.models.elasticity import lame_parameters, linear_elasticity
    L, h, t = 20.0, 1.0, 1.0            # mm; slender beam, unit thickness
    E, nu, F = 2000.0, 0.35, 0.01       # MPa (nylon-ish), -, N
    m = MeshTri.init_tensor(np.linspace(0, L, 81), np.linspace(0, h, 5)).with_boundaries(
        {"clamp": lambda x: x[0] < 1e-9, "tip": lambda x: x[0] > L - 1e-9})
    e = ElementVector(ElementTriP2())
    basis = Basis(m, e)
    lam, mu = lame_parameters(E, nu)
    lam_ps = 2 * lam * mu / (lam + 2 * mu)                    # plane stress
    K = asm(linear_elasticity(lam_ps, mu), basis)
    fb = FacetBasis(m, e, facets=m.boundaries["tip"])
    traction = -F / (h * t)                                   # downward shear on the tip face

    @LinearForm
    def load(v, w_):
        return traction * v[1]

    f = asm(load, fb)
    u = solve(*condense(K, f, D=basis.get_dofs("clamp")))
    tip_nodes = np.where(m.p[0] > L - 1e-9)[0]
    uy = u[basis.nodal_dofs[1, tip_nodes]].mean()
    I = t * h ** 3 / 12
    ref = -F * L ** 3 / (3 * E * I)
    err = abs(uy - ref) / abs(ref)
    assert err < 0.05, f"tip {uy:.4g} mm vs beam theory {ref:.4g} mm ({err:.1%})"
    return f"cantilever tip {abs(uy) * 1e3:.1f} um vs beam theory {abs(ref) * 1e3:.1f} um ({err:.1%} off)"


def t_render(w: Path) -> str:
    svg, mmd = REPO / "docs/diagrams/system-overview.svg", w / "t.mmd"
    mmd.write_text("flowchart LR\n  A[mic] -->|PDM| B[DFSDM] --> C[DSP] --> D[PWM] --> E[tragus]\n")
    out = []
    for src in (svg, mmd):
        png = w / (src.stem + ".png")
        sh([str(REPO / "docs/diagrams/render.sh"), str(src), str(png)], timeout=120)
        assert png.stat().st_size > 2000, f"{png.name} looks empty"
        out.append(png.name)
    return "SVG and Mermaid rendered to PNG: " + ", ".join(out)


TESTS = [("ngspice", t_ngspice, False), ("kicad+freerouting", t_kicad_freerouting, False),
         ("skidl", t_skidl, False), ("arm-gcc", t_arm_gcc, False), ("build123d", t_build123d, False),
         ("scikit-fem", t_scikit_fem, False), ("render", t_render, False),
         ("easyeda2kicad", t_easyeda2kicad, True), ("jlc-api", t_jlc, True)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip network tests")
    ap.add_argument("--keep", help="keep outputs in this directory")
    ap.add_argument("-k", help="run only tests whose name contains this")
    a = ap.parse_args()
    root = Path(a.keep) if a.keep else Path(tempfile.mkdtemp(prefix="ultra-smoke-"))
    root.mkdir(parents=True, exist_ok=True)
    failed = 0
    for name, fn, needs_net in TESTS:
        if a.k and a.k not in name:
            continue
        if needs_net and a.offline:
            print(f"SKIP  {name:18} (offline)")
            continue
        w = root / name
        w.mkdir(exist_ok=True)
        t0 = time.time()
        try:
            msg = fn(w)
            print(f"PASS  {name:18} {time.time() - t0:5.1f} s  {msg}", flush=True)
        except Exception as e:  # noqa: BLE001 - report every failure and keep going
            failed += 1
            print(f"FAIL  {name:18} {time.time() - t0:5.1f} s  {e}", flush=True)
            if os.environ.get("SMOKE_TRACEBACK"):
                traceback.print_exc()
    if not a.keep:
        shutil.rmtree(root, ignore_errors=True)
    print(f"{'ALL PASSED' if not failed else f'{failed} FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
