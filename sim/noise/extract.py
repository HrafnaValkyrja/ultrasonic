"""Layout-noise extraction scaffold: read a routed KiCad board, report per-net geometry, build the lumped R+L
network, and write SPICE (a MIC_VDD path subckt, a GND return subckt, and a flat test deck).

    source tools/env.sh
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 \
        python3 sim/noise/extract.py [board.kicad_pcb] [--out DIR] [--budget] [--selfcheck]

Reads only (never writes the board). Default board/netlist/BOM: hw/current.yaml (tools/current.py). Smoke run on the Phase-2 routed board: ~4 s, ~0.3 GB.
Outputs in --out (default sim/noise/out/, git-ignored):
  geometry.json      per-net segments/layers/lengths/widths/vias/pads, GND plane summary, board hash, stackup source
  mic_vdd_path.sub   .subckt MIC_VDD_PATH <pad nodes>: R + L per MIC_VDD segment and via barrel (ports PA5 pin, C13, mic VDD)
  gnd_return.sub     .subckt GND_RETURN <all GND pad nodes>: GND stubs, vias, and the Kron-reduced In1 plane (resistive mesh)
  l1_full.cir        the flat network incl. component models; node 0 = cell GND pad. Load it in ngspice with your own sources.
  extract_report.txt human summary
Pad nodes are named REF_PAD (U2_5 = mic VDD pin). Every element line carries no tag in SPICE; geometry.json has the segments.
--selfcheck runs ngspice 45 on l1_full.cir and compares it with the internal solver (must agree to < 1 %).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools"))
import budget  # noqa: E402
import lumped  # noqa: E402
import pcbgeom  # noqa: E402
import plane  # noqa: E402


def geometry_report(geom: dict, mesh_info: dict, nets_info: dict) -> dict:
    summ = pcbgeom.per_net_summary(geom)
    widths = sorted({round(s["w"], 3) for s in geom["segments"]})
    return dict(
        board=geom["path"], sha256=geom["sha256"], size_mm=[round(v, 3) for v in geom["board_mm"]],
        stackup=geom["stackup"],
        counts=dict(segments=len(geom["segments"]), vias=len(geom["vias"]), pads=len(geom["pads"]), nets=len(geom["nets"]),
                    zones=[(z["net"], z["layer"], round(z["area_mm2"], 2)) for z in geom["zones"]]),
        track_widths_mm=widths,
        per_net=summ, plane=mesh_info, l1=nets_info)


def write_spice(net: lumped.Network, info: dict, geom: dict, out: Path, header: str):
    pn = info["pad_node"]
    mic_ports = sorted({v for k, v in pn.items() if any(p["ref"] + "." + p["num"] == k and p["net"] == "MIC_VDD" for p in geom["pads"])})
    gnd_ports = sorted({v for k, v in pn.items() if any(p["ref"] + "." + p["num"] == k and p["net"] == "GND" for p in geom["pads"])})
    (out / "mic_vdd_path.sub").write_text(net.to_spice(
        "MIC_VDD_PATH", mic_ports, lambda e: e.get("net") == "MIC_VDD" and e.get("kind_") in ("trace", "via"), header))
    (out / "gnd_return.sub").write_text(net.to_spice(
        "GND_RETURN", gnd_ports, lambda e: e.get("net") == "GND" and e.get("kind_") in ("trace", "via", "plane"), header))
    (out / "l1_full.cir").write_text(net.to_spice("L1_FULL", None, None, header) + ".end\n")
    return mic_ports, gnd_ports


def selfcheck(net: lumped.Network, out: Path, pair: tuple[str, str], probe: tuple[str, str], freqs=(2e4, 2e5, 4e6)):
    """ngspice 45 vs the internal MNA solver on the same element list. Returns max relative error."""
    import spice  # tools/spice.py
    deck = (out / "l1_full.cir").read_text().replace(".end\n", "")
    into, frm = pair
    deck += f"Iinj {frm} {into} DC 0 AC 1\n.ac dec 1 {freqs[0]} {freqs[0] * 1.0001}\n"
    errs = []
    for f in freqs:
        d = deck.split(".ac")[0] + f".ac lin 1 {f} {f}\n.end\n"
        r = spice.run(d, cwd=str(out))
        v = r.ac[f"v({probe[0].lower()})"][0] - r.ac[f"v({probe[1].lower()})"][0]
        mine = net.ac(np.array([f]), [pair], [probe])[0][0][0]
        errs.append(abs(v - mine) / abs(mine))
    return max(errs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board", nargs="?", default=None, help="default: env NOISE_BOARD, else hw/current.yaml board (pcbgeom.default_board)")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--params", default=str(HERE / "params.yaml"))
    ap.add_argument("--netlist", default=None, help="default: hw/current.yaml netlist; schematic netlist to compare the board's pad->net map against ('' to skip)")
    ap.add_argument("--budget", action="store_true", help="also run the L1 noise budget (budget.py)")
    ap.add_argument("--selfcheck", action="store_true", help="cross-check the SPICE deck in ngspice against the internal solver")
    a = ap.parse_args(argv)
    a.board = a.board or pcbgeom.default_board(REPO)
    a.netlist = pcbgeom.default_netlist(REPO) if a.netlist is None else a.netlist
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    params = budget.load_yaml(a.params)
    geom = pcbgeom.load(a.board)
    bom = lumped.read_bom(pcbgeom.bom_path(REPO, params))
    rep = []
    P = rep.append
    P(f"board {a.board}  sha256[:16] {geom['sha256']}  size {geom['board_mm'][2]:.2f} x {geom['board_mm'][3]:.2f} mm")
    P(f"stackup: {geom['stackup']['src']}")
    if a.netlist and Path(a.netlist).exists():
        nd = pcbgeom.netlist_diff(geom, a.netlist)
        P(f"netlist check: {nd['pads_netlist']} netlist pads, {nd['pads_board']} board pads, {len(nd['mismatch'])} mismatches" + (f" (board is STALE vs {Path(a.netlist).name}): {nd['mismatch'][:6]}" if nd["mismatch"] else " (board == schematic netlist)"))
    P(f"counts: {len(geom['segments'])} segments, {len(geom['vias'])} vias, {len(geom['pads'])} pads, {len(geom['nets'])} nets; track widths mm {sorted({round(s['w'], 3) for s in geom['segments']})}")
    P(f"{'net':14s}{'segs':>5s}{'F.Cu':>8s}{'In2.Cu':>8s}{'B.Cu':>8s}{'total':>8s}{'vias':>5s}{'pads':>5s}{'w_min':>7s}{'w_max':>7s}")
    summ = pcbgeom.per_net_summary(geom)
    for n, s in sorted(summ.items(), key=lambda kv: -kv[1]["len_total_mm"]):
        L = s["len_mm"]
        P(f"{n:14s}{s['segs']:5d}{L.get('F.Cu', 0):8.2f}{L.get('In2.Cu', 0):8.2f}{L.get('B.Cu', 0):8.2f}{s['len_total_mm']:8.2f}{s['vias']:5d}{s['pads']:5d}{s['w_min']:7.2f}{s['w_max']:7.2f}")
    # plane: two pitches for a discretisation check
    z = next(z for z in geom["zones"] if z["layer"] == params["board"]["plane_layer"])
    rs = params["materials"]["rho_cu_ohm_m"] / (geom["stackup"]["copper_um"][params["board"]["plane_layer"]] * 1e-6)
    P(f"GND plane {z['layer']}: zone fill {z['area_mm2']:.2f} mm2, {len(z['polys'])} polygon(s), {sum(len(p['holes']) for p in z['polys'])} holes, sheet R {rs * 1e3:.3f} mohm/sq")
    net, info, mesh, red = budget.build_l1(geom, params, bom)
    ports = lumped.plane_ports(geom)
    chk = {}
    for pitch in (0.2, 0.1):
        m2 = plane.Mesh(z, pitch=pitch, rs=rs)
        r2 = m2.reduce(ports)
        k = sorted(ports)
        chk[pitch] = plane.reff(r2["G"], 0, len(k) // 2) * 1e3
        P(f"  mesh pitch {pitch} mm: raster {m2.area_mm2:.1f} mm2, {r2['n_cells']} cells, R(via0, via{len(k) // 2}) {chk[pitch]:.3f} mohm")
    P(f"  GND vias on the plane: {len(ports)}")
    P(f"L1 network: {len(net.nodes)} nodes, {len(net.elems)} elements; {info['n_segments']} segments, {info['n_vias']} via-layer links, {info['n_plane_links']} plane links; floating pads: {info['floating_pads'] or 'none'}")
    for n, t in sorted(info["totals"].items()):
        P(f"  {n:12s} series R sum {t['R_ohm']:.3f} ohm, L sum {t['L_nH']:.2f} nH over {t['segs']} segments (sums over a tree, not a path)")
    header = f"board {Path(a.board).name} sha {geom['sha256']}; {geom['stackup']['src']}; plane pitch {mesh.pitch} mm; generated by sim/noise/extract.py"
    mic_ports, gnd_ports = write_spice(net, info, geom, out, header)
    P(f"SPICE: mic_vdd_path.sub ports {mic_ports}; gnd_return.sub {len(gnd_ports)} ports; l1_full.cir {len(net.elems)} elements")
    gj = geometry_report(geom, dict(info["plane"], pitch_check_mohm=chk), dict(totals=info["totals"], floating=info["floating_pads"]))
    (out / "geometry.json").write_text(json.dumps(gj, indent=1, default=float))
    if a.selfcheck:
        pn = info["pad_node"]
        err = selfcheck(net, out, (pn["U1.24"], pn["U1.25"]), (pn["U2.5"], pn["U2.3"]))
        P(f"selfcheck ngspice 45 vs internal MNA (U1.25->U1.24 injection, probe U2.5-U2.3, 20 kHz/200 kHz/4 MHz): max rel err {err:.2e}")
        assert err < 0.01, err
        import couple
        P(f"selfcheck L2 filament model vs closed forms (Grover M, image-line M', image-wire Cm): {couple.selftest()}")
        import alias
        alias.selftest()
        import tempfile, os
        fs_ = 200.0225e3
        tt = np.linspace(0, 6 / fs_, 6 * 4000, endpoint=False)
        ph = (tt * fs_) % 1.0
        amp, duty, te = 0.018, 0.1, 5e-9
        x = amp * np.clip(np.minimum(ph / (te * fs_), 1.0) - np.clip((ph - duty) / (te * fs_), 0.0, 1.0), 0.0, 1.0)
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as td:
            fn = os.path.join(td, "p.csv")
            np.savetxt(fn, np.c_[tt, x], delimiter=",")
            got = dict(budget.lines_from_csv(fn, fs_, 5))
        ref = dict(budget.lines(dict(kind="pulse_train", f0=fs_, amp_a=amp, duty=duty, t_edge_s=te, nharm=5)))
        e1 = abs(got[fs_] / ref[fs_] - 1)
        P(f"selfcheck CSV aggressor import vs analytic pulse_train (harmonic 1, 10 % duty, 5 ns edges sampled at 1.25 ns): rel err {e1:.3f}")
        assert e1 < 0.1, e1
        P("selfcheck alias.py: PWM carrier, mic clock harmonics fold to 0 Hz; 3 MHz does not: ok")
    P(f"extract done in {time.time() - t0:.1f} s")
    (out / "extract_report.txt").write_text("\n".join(rep) + "\n")
    print("\n".join(rep))
    if a.budget:
        res = budget.main([a.board, "--out", str(out), "--check-doc", "--plot", "--netlist", a.netlist or ""])
        return budget.exit_code(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
