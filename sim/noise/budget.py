"""L1 noise budget: lumped extraction of the board + declared aggressors -> victim-node noise in the bands that matter.

    source tools/env.sh
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/noise/budget.py [board.kicad_pcb] [--out DIR]

Pipeline (all layout-agnostic; the board is only read):
  pcbgeom.load -> plane.Mesh (In1 GND, resistive) -> lumped.add_nets (R+L per segment, via barrels, plane links)
  -> component models (caps with ESR/ESL, 0R, L1, LDO Zout, MCU die + PA5, mic load)
  -> Network.ac: transimpedance from every declared aggressor port pair to every victim probe, at every spectral line
  -> mic PSRR + alias.chain (PDM sampling, CIC5/5, RSFLT/4) -> spur in dBFS at the mic output vs the floor
  -> ranking with the geometry features responsible (reciprocity: Z_t = sum_k z_k I_k(agg) I_k(victim)).
Field coupling (L2) lives in couple.py and is merged into the same ranking.
Every number that is an assumption is in params.yaml / aggressors.yaml with its status.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import alias  # noqa: E402
import lumped  # noqa: E402
import pcbgeom  # noqa: E402
import plane  # noqa: E402

DOC = REPO / "docs/sim/layout-noise.yaml"


def load_yaml(p):
    with open(p) as f:
        return yaml.safe_load(f)


# ---- spectra -----------------------------------------------------------------------------------------------
def sinc(x):
    return 1.0 if abs(x) < 1e-12 else math.sin(x) / x


def lines(wave: dict) -> list[tuple[float, float]]:
    """[(f_hz, peak amplitude)] for tone-like waves; [] for band_noise."""
    k = wave["kind"]
    f0, n = wave.get("f0", 0.0), wave.get("nharm", 0)
    out = []
    if k == "pulse_train":
        A, D, te = wave["amp_a"], wave["duty"], wave["t_edge_s"]
        for h in range(1, n + 1):
            out.append((h * f0, 2 * A * D * abs(sinc(h * math.pi * D)) * abs(sinc(h * math.pi * f0 * te))))
    elif k == "sawtooth":
        for h in range(1, n + 1):
            out.append((h * f0, 2 * wave["amp_a"] / (h * math.pi)))
    elif k == "triangle":
        for h in range(1, n + 1, 2):
            out.append((h * f0, (8 / math.pi ** 2) * (wave["pp_a"] / 2) / h ** 2))
    elif k == "cap_square":
        for h in range(1, n + 1, 2):
            out.append((h * f0, 4 * f0 * wave["c_f"] * wave["v"] * abs(sinc(h * math.pi * f0 * wave["t_edge_s"]))))
    elif k == "band_noise":
        return []
    elif k == "csv_period":
        return lines_from_csv(wave["path"], f0, n, wave.get("t_col", 0), wave.get("i_col", 1))
    else:
        raise ValueError(k)
    m = max(a for _, a in out) if out else 0
    return [(f, a) for f, a in out if a >= 1e-4 * m]


def lines_from_csv(path: str, f0: float, nharm: int, t_col: int = 0, i_col: int = 1, npts: int = 8192):
    """Harmonic amplitudes (peak) of a periodic current exported by a time-domain sim (CSV: time in s, current in A).
    Uses the last whole period at f0 (resampled to npts points). This is the hook for sim/spice exports (IF-AGGRESSOR-I)."""
    d = np.loadtxt(path, delimiter=",", comments="#", ndmin=2)
    t, i = d[:, t_col], d[:, i_col]
    T = 1.0 / f0
    t1 = t[-1]
    t0 = t1 - T
    if t0 < t[0]:
        raise ValueError(f"{path}: shorter than one period of {f0} Hz")
    tt = t0 + T * np.arange(npts) / npts
    x = np.interp(tt, t, i)
    X = np.fft.rfft(x) / npts
    out = [(h * f0, 2 * abs(X[h])) for h in range(1, min(nharm, npts // 2 - 1) + 1)]
    m = max(a for _, a in out) if out else 0
    return [(f, a) for f, a in out if a >= 1e-4 * m]


def a_weight_enbw(f_lo=20.0, f_hi=20000.0) -> float:
    """Equivalent noise bandwidth (Hz) of the A-weighting curve for white noise, 20 Hz - 20 kHz."""
    f = np.logspace(math.log10(f_lo), math.log10(f_hi), 4000)
    ra = (12194.0 ** 2 * f ** 4) / ((f ** 2 + 20.6 ** 2) * np.sqrt((f ** 2 + 107.7 ** 2) * (f ** 2 + 737.9 ** 2)) * (f ** 2 + 12194.0 ** 2))
    a1k = (12194.0 ** 2 * 1e3 ** 4) / ((1e3 ** 2 + 20.6 ** 2) * math.sqrt((1e3 ** 2 + 107.7 ** 2) * (1e3 ** 2 + 737.9 ** 2)) * (1e3 ** 2 + 12194.0 ** 2))
    return float(np.trapezoid((ra / a1k) ** 2, f))


def mic_floor(params: dict, scen: str = "white") -> dict:
    m = params["mic"]
    noise_a = m["sens_dbfs_at_94spl"] - m["snr_dba"]               # dBFS(A), audio band
    enbw = a_weight_enbw()
    dens = noise_a - 10 * math.log10(enbw)                          # dBFS per sqrt(Hz), white extrapolation
    adj = m["noise_scenarios_db"][scen]
    bin_db = dens + 10 * math.log10(m["bin_hz"]) + adj
    lo, hi = m["band_hz"]
    band_db = dens + 10 * math.log10(hi - lo) + adj
    mg = m["margin_below_floor_db"]
    return dict(noise_dbfs_a=noise_a, enbw_a_hz=enbw, density_dbfs_rthz=dens, bin_dbfs=bin_db, band_dbfs=band_db,
                tone_limit_dbfs=bin_db - mg, band_limit_dbfs=band_db - mg, scenario=scen)


# ---- network assembly ---------------------------------------------------------------------------------------
def resolve(spec: str, info: dict, geom: dict) -> str:
    if "@" in spec:
        ref, net = spec.split("@")
        for p in geom["pads"]:
            if p["ref"] == ref and p["net"] == net and f'{p["ref"]}.{p["num"]}' in info["pad_node"]:
                return info["pad_node"][f'{p["ref"]}.{p["num"]}']
        raise KeyError(spec)
    if spec not in info["pad_node"]:
        raise KeyError(f"{spec}: pad not on an included net or not on the board")
    return info["pad_node"][spec]


def attach_components(net: lumped.Network, info: dict, geom: dict, params: dict, bom: dict):
    pn, c = info["pad_node"], params["components"]
    done, skipped = [], []
    for ref, (comment, fp) in sorted(bom.items()):
        a, b = pn.get(f"{ref}.1"), pn.get(f"{ref}.2")
        size = next((s for s in ("0402", "0603", "1206") if s in fp), "0402")
        tag = dict(kind_="comp", ref=ref)
        val = lumped.parse_si(comment)
        if ref == "L1" and a and b:
            L = c["l1"]
            net.add("R", a, f"{ref}x", L["dcr_ohm"], **tag)
            net.add("L", f"{ref}x", b, L["l_uh"] * 1e-6, **tag)
            net.add("C", a, b, L["c_par_pf"] * 1e-12, **tag)
            done.append(ref)
        elif ref.startswith("C") and a and b and val:
            keep = c["dc_bias_keep"].get(comment, 0.8)
            esr = c["esr_ohm"].get(comment, 0.02)
            esl = c["esl_nh"][size] * 1e-9
            net.add("R", a, f"{ref}r", esr, **tag)
            net.add("L", f"{ref}r", f"{ref}l", esl, **tag)
            net.add("C", f"{ref}l", b, val * keep, **tag)
            done.append(ref)
        elif ref.startswith("R") and a and b and val is not None:
            r = val if val > 0 else c["r_zero_ohm"]
            net.add("R", a, f"{ref}x", r, **tag)
            net.add("L", f"{ref}x", b, c["resistor_esl_nh"] * 1e-9, **tag)
            done.append(ref)
        elif a or b:
            skipped.append(ref)
    # LDO, mic, MCU die
    d, ldo, m = params["die"], params["ldo"], params["mic"]
    net.add("R", pn["U4.1"], "ldo_x", ldo["r_out_ohm"], kind_="comp", ref="U4")
    net.add("L", "ldo_x", pn["U4.2"], ldo["l_out_nh"] * 1e-9, kind_="comp", ref="U4")
    net.add("R", pn["U2.5"], pn["U2.3"], m["r_load_ohm"], kind_="comp", ref="U2")
    sup = [f"U1.{p}" for p in (1, 9, 21, 25, 36, 48) if f"U1.{p}" in pn]
    gnd = [f"U1.{p}" for p in (8, 22, 24, 35, 47, 49) if f"U1.{p}" in pn]
    for kind, pins, node in (("vdd", sup, "DIE_VDD"), ("vss", gnd, "DIE_VSS")):
        for p in pins:
            net.add("R", pn[p], f"{p}_{kind}x", d["r_pin_ohm"], kind_="comp", ref="U1")
            net.add("L", f"{p}_{kind}x", node, d["l_pin_nh"] * 1e-9, kind_="comp", ref="U1")
    net.add("R", "DIE_VDD", "die_c", d["esr_die_ohm"], kind_="comp", ref="U1")
    net.add("C", "die_c", "DIE_VSS", d["c_die_nf"] * 1e-9, kind_="comp", ref="U1")
    net.add("R", pn["U1.15"], "DIE_VDD", d["r_pa5_ohm"], kind_="comp", ref="U1")   # PA5 high output driving MIC_VDD
    if "U1.20" in pn and "U1.22" in pn:
        net.add("R", pn["U1.20"], pn["U1.22"], d["r_vlx_ohm"], kind_="comp", ref="U1")  # switch node held by the SMPS switch
    # AC reference: the cell's GND pad
    gref = next(v for k, v in pn.items() if k.startswith("J4."))
    net.add("R", gref, "0", 1e-6, kind_="ref")
    return dict(modelled=done, skipped_two_pad_parts=skipped)


def build_l1(geom: dict, params: dict, bom: dict, pitch: float | None = None):
    st = geom["stackup"]
    rs = params["materials"]["rho_cu_ohm_m"] / (st["copper_um"][params["board"]["plane_layer"]] * 1e-6)
    zs = [z for z in geom["zones"] if z["layer"] == params["board"]["plane_layer"] and z["net"] == params["board"]["ground_net"]]
    if not zs or not any(p["outer"] for p in zs[0]["polys"]):
        raise SystemExit(f"{geom['path']}: no filled {params['board']['ground_net']} zone on {params['board']['plane_layer']}: refill zones in KiCad (B) or set board.plane_layer/ground_net in params.yaml")
    z = zs[0]
    mesh = plane.Mesh(z, pitch=pitch or params["board"]["plane_pitch_mm"], rs=rs)
    ports = lumped.plane_ports(geom, params["board"]["ground_net"], params["board"]["plane_layer"])
    red = mesh.reduce(ports)
    net = lumped.Network()
    info = lumped.add_nets(net, geom, set(params["board"]["nets"]), plane_red=red,
                           plane_net=params["board"]["ground_net"], t_plate_um=params["materials"]["t_plate_um"])
    try:
        info["components"] = attach_components(net, info, geom, params, bom)
    except KeyError as e:
        raise SystemExit(f"board lacks pad {e} that the component models need (U1 MCU pins, U2 mic, U4 LDO, J6 cell GND): adapt attach_components() or the nets list in params.yaml")
    info["plane"] = dict(sheet_ohm_sq=rs, pitch_mm=mesh.pitch, cells=red["n_cells"], area_mm2=round(mesh.area_mm2, 2),
                         zone_area_mm2=round(mesh.zone_area_mm2, 2), ports=len(ports), orphan_ports=red["orphan_ports"],
                         cells_dropped=red["cells_dropped"])
    return net, info, mesh, red


# ---- analysis ----------------------------------------------------------------------------------------------
def psrr_extra_db(f_in: float, params: dict, scen: str) -> float:
    """dB of spur above the 1 kHz PSRR figure. Number = flat extra above 20 kHz; 'rolloff_1k' = the e2e sim's rolloff curve
    (sim/e2e/stages.SupplyInject.psrr_db: PSRR 55 - 20 log10(f/1 kHz), floored at 5 dB), shared table docs/sim/shared-params.yaml#psrr."""
    v = params["mic"]["psrr_scenarios"][scen]
    if isinstance(v, str):
        return min(20 * math.log10(max(f_in, 1e3) / 1e3), 50.0)
    return float(v) if f_in >= 20e3 else 0.0


def spur_dbfs(vrms: float, f_in: float, att_db: float, params: dict, scen: str) -> float:
    m = params["mic"]
    return m["psrr_dbfs_per_vrms_1k"] + psrr_extra_db(f_in, params, scen) + 20 * math.log10(max(vrms, 1e-18)) + att_db


def analyse(net, info, geom, params, agg, out_dir: Path, log=print, l2=True):
    t0 = time.time()
    warnings = []
    if info["floating_pads"]:
        warnings.append(f"{len(info['floating_pads'])} pads on the extracted nets have no copper path (unrouted board?): {info['floating_pads'][:8]}")

    def ok_pads(specs, what):
        try:
            names = [resolve(s, info, geom) for s in specs]
            for nm in names:
                net.node(nm)          # an unrouted pad still gets a (floating) node; the warning above says so
            return names
        except KeyError as e:
            warnings.append(f"{what} skipped: {e}")
            return None
    aggs, pairs = [], []
    for a in agg["aggressors"]:
        r = ok_pads([a["inject"]["into"], a["inject"]["from"]], a["id"])
        if r:
            aggs.append(a); pairs.append(tuple(r))
    victims, probes = [], []
    for v in agg["victims"]:
        r = ok_pads(v["probe"], v["id"])
        if r:
            victims.append(v); probes.append(tuple(r))
    # frequency set: exact lines + log grid + capture-band grid
    exact = sorted({round(f, 3) for a in aggs for f, _ in lines(a["wave"])})
    grid = list(np.logspace(3, 8, 400))
    band = list(np.linspace(20e3, 85e3, 27))
    freqs = np.array(sorted(set(exact) | set(grid) | set(band) | {5e3}))
    Zt = net.ac(freqs, pairs, probes)
    log(f"  ac solve: {len(freqs)} freqs x {len(pairs)} aggressors x {len(probes)} probes, {len(net.nodes)} nodes, {len(net.elems)} elements, {time.time() - t0:.1f} s")
    fidx = {round(f, 3): i for i, f in enumerate(freqs)}

    def zt(ai, vi, f):
        z = Zt[ai][vi]
        i = fidx.get(round(f, 3))
        if i is not None:
            return abs(z[i])
        return float(np.exp(np.interp(math.log(f), np.log(freqs), np.log(np.abs(z) + 1e-30))))

    floor_nom, floor_pes = mic_floor(params, "white"), mic_floor(params, "pessimistic")
    rows = []
    tone_lim, band_lim = floor_nom["tone_limit_dbfs"], floor_nom["band_limit_dbfs"]
    for ai, a in enumerate(aggs):
        w = a["wave"]
        for vi, v in enumerate(victims):
            if v["class"] != "mic_supply":
                continue
            best = None
            if w["kind"] == "band_noise":
                fb = np.array(band)
                zi = np.array([zt(ai, vi, f) for f in fb])
                vr = math.sqrt(np.trapezoid(zi ** 2, fb) / (fb[-1] - fb[0])) * w["i_rms_a"]  # flat current density
                s_nom, s_pes = spur_dbfs(vr, 50e3, 0.0, params, "nominal"), spur_dbfs(vr, 50e3, 0.0, params, "pessimistic")
                s_w = spur_dbfs(vr, 85e3, 0.0, params, "worst")      # worst: rolloff evaluated at the band top (conservative)
                best = dict(kind="band", f_hz=50e3, f_out_hz=50e3, v_rms=vr, spur_nom=s_nom, spur_pes=s_pes, limit=band_lim,
                            margin_nom=band_lim - s_nom, margin_pes=band_lim - s_pes, spur_worst=s_w, margin_worst=band_lim - s_w)
            else:
                for f, amp in lines(w):
                    fo, att, dc = alias.chain(f)
                    if (a.get("sync") and dc) or f > params["model"]["f_max_net_hz"] * (1 + a.get("f_tol_frac", 0.0)):
                        continue
                    tol = a.get("f_tol_frac", 0.0)
                    # asynchronous: the line may sit anywhere in f*(1+-tol); take the worst alias inside that range
                    cand = [f] if tol == 0 or a.get("sync") else list(np.linspace(f * (1 - tol), f * (1 + tol), 400))
                    for fc in cand:
                        fo_c, att_c, dc_c = alias.chain(fc)
                        if dc_c or not (20e3 <= fo_c <= 96e3) or fc > params["model"]["f_max_net_hz"]:
                            continue
                        vr = amp / math.sqrt(2) * zt(ai, vi, fc if fc != f else f)
                        s_nom, s_pes = spur_dbfs(vr, fc, att_c, params, "nominal"), spur_dbfs(vr, fc, att_c, params, "pessimistic")
                        s_w = spur_dbfs(vr, fc, att_c, params, "worst")
                        r = dict(kind="tone", f_hz=fc, f_k_nominal_hz=f, f_out_hz=fo_c, att_db=att_c, i_peak_a=amp, v_rms=vr,
                                 spur_nom=s_nom, spur_pes=s_pes, limit=tone_lim, margin_nom=tone_lim - s_nom, margin_pes=tone_lim - s_pes,
                                 spur_worst=s_w, margin_worst=tone_lim - s_w)
                        if best is None or r["margin_pes"] < best["margin_pes"]:
                            best = r
                    # lines that stay below 20 kHz or fold to DC are listed separately (band floor removes them)
            if best:
                best.update(aggressor=a["id"], victim=v["id"], mechanism="conduction")
                rows.append(best)
    rows.sort(key=lambda r: r["margin_pes"])

    # ---- other victims: rms level per aggressor, and the Kelvin / low-frequency metrics
    other = []
    for ai, a in enumerate(aggs):
        for vi, v in enumerate(victims):
            if v["class"] == "mic_supply":
                continue
            ls = lines(a["wave"])
            if a["wave"]["kind"] == "band_noise":
                fb = np.array(band)
                zi = np.array([zt(ai, vi, f) for f in fb])
                vr = math.sqrt(np.trapezoid(zi ** 2, fb) / (fb[-1] - fb[0])) * a["wave"]["i_rms_a"]
                other.append(dict(aggressor=a["id"], victim=v["id"], v_rms=vr, band="20-85k noise"))
                continue
            vp = [(f, amp / math.sqrt(2) * zt(ai, vi, f)) for f, amp in ls]
            if vp:
                f, vv = max(vp, key=lambda t: t[1])
                row = dict(aggressor=a["id"], victim=v["id"], v_rms=vv, f_hz=f, total_rms=math.sqrt(sum(x * x for _, x in vp)))
                for key, lo, hi in (("lf16k", 0.0, 16e3), ("audio", 1.5e3, 8e3)):
                    sel = [t for t in vp if lo <= t[0] <= hi]
                    if sel:
                        ff, vvv = max(sel, key=lambda t: t[1])
                        row[key] = dict(f_hz=ff, v_rms=vvv)
                other.append(row)
    kel = {}
    i3 = next(i for i, a in enumerate(aggs) if a["id"] == "A03_BRIDGE_CARRIER")
    vk = next(i for i, v in enumerate(victims) if v["class"] == "kelvin")
    kel["z_kelvin_5khz_mohm"] = zt(i3, vk, 5e3) * 1e3
    kel["z_kelvin_error_pct_of_r21"] = zt(i3, vk, 5e3) / 0.1 * 100
    kel["features"] = contributions(net, pairs[i3], probes[vk], 5e3, top=5)   # which copper makes the Kelvin error (LF-1), any board
    # transfer impedance spectrum for the report (mic supply from each aggressor), a few decades
    zsum = {}
    for ai, a in enumerate(aggs):
        vi = next(i for i, v in enumerate(victims) if v["class"] == "mic_supply")
        zsum[a["id"]] = {f"{f:.0f}": round(zt(ai, vi, f) * 1e3, 4) for f in (1e3, 5e3, 20e3, 85e3, 200e3, 1e6, 4e6, 12e6)}
    # element contributions for the top rows (reciprocity)
    for r in rows[:6]:
        ai = next(i for i, a in enumerate(aggs) if a["id"] == r["aggressor"])
        vi = next(i for i, v in enumerate(victims) if v["id"] == r["victim"])
        r["features"] = contributions(net, pairs[ai], probes[vi], r["f_hz"], top=5)
    l2_rows, pair_table = [], []
    if l2:
        import couple  # noqa: PLC0415  (couple imports this module: keep the import lazy)
        info["_stackup"] = geom["stackup"]
        l2_rows, pair_table, l2_meta = couple.run_l2(geom, info, net, params, agg, probes, victims, floor_nom["tone_limit_dbfs"], log)
        log(f"  L2 field coupling: {len(l2_rows)} rows, f_cross {l2_meta['f_cross_hz'] / 1e6:.2f} MHz, {time.time() - t0:.1f} s")
    log(f"  analysis {time.time() - t0:.1f} s")
    return dict(warnings=warnings, rows=rows, l2_rows=l2_rows, l2_pairs=pair_table, other=other, kelvin=kel, z_mic_supply_mohm=zsum, floor=dict(nominal=floor_nom, pessimistic=floor_pes),
                n_freqs=len(freqs)), (freqs, Zt, pairs, probes, aggs, victims)


def contributions(net, agg_pair, probe_pair, f, top=5):
    """Per-geometry-feature share of the transimpedance at f: Z_t = sum_k z_k * I_k(aggressor) * I_k(victim)."""
    res, cur = net.ac(np.array([f]), [agg_pair, probe_pair], [probe_pair], want_currents=True)
    ia, iv = cur[0][0], cur[1][0]
    y = net.admittances(f)
    c = (1.0 / y) * ia * iv
    groups: dict[tuple, complex] = {}
    for e, ck in zip(net.elems, c):
        k = e.get("kind_", "?")
        if k == "trace":
            key = ("trace", e["net"], e["layer"], e["xy"])
        elif k == "via":
            key = ("via", e["net"], e["layer"], e["xy"])
        elif k == "plane":
            key = ("plane", e["net"], "In1.Cu", e["xy"])
        elif k == "comp":
            key = ("comp", e["ref"], "", ())
        else:
            continue
        groups[key] = groups.get(key, 0) + ck
    tot = sum(groups.values())
    ranked = sorted(groups.items(), key=lambda kv: -abs(kv[1]))[:top]
    lay = sum(abs(v) for k, v in groups.items() if k[0] in ("trace", "via", "plane")) / max(sum(abs(v) for v in groups.values()), 1e-30)
    return [dict(layout_share_pct=round(100 * lay, 1))] + [dict(kind=k[0], net_or_ref=k[1], layer=k[2], xy=list(k[3]), contribution_mohm=round(abs(v) * 1e3, 4),
                 share_pct_of_abs_total=round(100 * abs(v) / max(sum(abs(x) for x in groups.values()), 1e-30), 1)) for k, v in ranked] + \
           [dict(kind="total", z_t_mohm=round(abs(tot) * 1e3, 4), check_vs_direct_mohm=round(abs(res[0][0][0]) * 1e3, 4))]


def metrics(res: dict, agg: dict, limits: dict) -> list[dict]:
    """Evaluate the numeric metrics of docs/sim/layout-noise.yaml against this run. Thresholds come from `limits`."""
    out = []
    mic = [r for r in res["rows"] + res["l2_rows"] if r["victim"] in ("V1_MIC_SUPPLY", "FV1_MIC_VDD") and r["kind"] in ("tone", "band")]
    w = min(mic, key=lambda r: r["margin_pes"]) if mic else None
    wn = min(mic, key=lambda r: r["margin_nom"]) if mic else None
    ww = min(mic, key=lambda r: r.get("margin_worst", 1e9)) if mic else None
    out.append(dict(id="LN-M01", name="mic supply spur margin (worst line/band, pessimistic PSRR)", value_db=w and round(w["margin_pes"], 1),
                    limit_db=">= 0 (sign-off >= 10)", ok=bool(w and w["margin_pes"] >= 0), signoff=bool(w and w["margin_pes"] >= 10),
                    at=w and f"{w['aggressor']} {w['mechanism'] if 'mechanism' in w else ''} {w['f_hz']:.0f} Hz -> {w['f_out_hz']:.0f} Hz",
                    value_db_nominal=wn and round(wn["margin_nom"], 1),
                    value_db_worst=ww and round(ww.get("margin_worst", float("nan")), 1),
                    at_worst=ww and f"{ww['aggressor']} {ww.get('mechanism', '')} {ww['f_hz']:.0f} Hz -> {ww['f_out_hz']:.0f} Hz",
                    psrr_scenarios="nominal flat 55 dB | pessimistic 35 dB above 20 kHz | worst e2e rolloff 55-20log10(f/1k), floor 5 dB (docs/sim/shared-params.yaml#psrr)"))
    dig = [r for r in res["l2_rows"] if r["kind"] == "digital"]
    if dig:
        d = min(dig, key=lambda r: r["margin_pes"])
        out.append(dict(id="LN-M02", name="PDM line pickup, sum of harmonics vs 100 mV", value_db=round(d["margin_pes"], 1), limit_db=">= 12", ok=d["margin_pes"] >= 12,
                        review=d["margin_pes"] < 12 + 10, review_why="margin inside the +-10 dB L2 model error (layout-noise.yaml limits.regime_error_budget): treat as REVIEW at the next re-route",
                        at=f"{d['aggressor']} -> {d['victim']} {d['mechanism']}"))
    k = res["kelvin"]["z_kelvin_error_pct_of_r21"]
    out.append(dict(id="LN-M03", name="I_SENSE Kelvin error (plane+stub drop shunt-GND to MCU VSSA, % of R21) at 5 kHz", value_pct=round(k, 2), limit_pct="<= 2", ok=k <= 2.0))
    adc = [(r["lf16k"]["v_rms"], r) for r in res["other"] if r["victim"] == "V3_ADC_REF" and "lf16k" in r]
    if adc:
        v, a = max(adc, key=lambda t: t[0])
        out.append(dict(id="LN-M04", name="ADC reference ripple, lines <= 16 kHz, peak vs 0.37 mV (0.5 LSB of 12 bit at 3.0 V)", value_mv_pk=round(v * math.sqrt(2) * 1e3, 4), limit_mv_pk="<= 0.37", ok=v * math.sqrt(2) * 1e3 <= 0.37, at=f"{a['aggressor']} {a['lf16k']['f_hz']:.0f} Hz"))
    br = [(r["audio"]["v_rms"], r) for r in res["other"] if r["victim"] == "V5_BRIDGE_RAIL" and "audio" in r]
    if br:
        v, a = max(br, key=lambda t: t[0])
        eps = 0.1
        out.append(dict(id="LN-M05", name="bridge rail ripple 1.5-8 kHz x leg asymmetry 10 % vs 50 uV rms", value_uv=round(v * eps * 1e6, 3), limit_uv="<= 50", ok=v * eps * 1e6 <= 50, at=f"{a['aggressor']} {a['audio']['f_hz']:.0f} Hz"))
    e = res.get("e2e_if")
    if e:
        out.append(dict(id="LN-M06", name="INFORMATIONAL: ripple at mic VDD 1-100 kHz (background lines + noise), mV rms; the pass/fail form is LN-M01 (per line/band after PSRR, 20-96 kHz)",
                        value_mv_rms=round(e["background_mv_rms"], 4), value_mv_rms_20k_100k=round(e["background_mv_rms_20k_100k"], 4),
                        limit_mv_rms="none (retired 2026-10-02: a white-ripple rms limit is ill-posed for a line spectrum below the band)",
                        ok=None, at=f"{e['dominant_line']['source']} {e['dominant_line']['f_hz']:.0f} Hz" if e.get("dominant_line") else None))
    return json.loads(json.dumps(out, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


def export_if(res, freqs, Zt, pairs, probes, aggs, victims, out: Path, board_sha: str):
    """IF-MIC-VDD-NOISE for the e2e sim (docs/sim/e2e-chain.yaml `interfaces`): bridge-supply-current transfer functions and the
    background ripple lines/PSD at the mic VDD pin. Written to out/IF-MIC-VDD-NOISE.json."""
    ia = next(i for i, a in enumerate(aggs) if a["id"] == "A03_BRIDGE_CARRIER")
    v1 = next(i for i, v in enumerate(victims) if v["class"] == "mic_supply")
    v5 = next(i for i, v in enumerate(victims) if v["class"] == "bridge_rail")
    sel = (freqs >= 1e3) & (freqs <= 2e5)
    f = freqs[sel]
    zr, hm = Zt[ia][v5][sel], Zt[ia][v1][sel]
    lines_out, tot_sq, tot_sq_cap = [], 0.0, 0.0
    for ai, a in enumerate(aggs):
        if a["wave"]["kind"] == "band_noise":
            continue
        for fl, amp in lines(a["wave"]):
            if 1e3 <= fl <= 1e5:
                i = np.argmin(abs(freqs - fl))
                vr = amp / math.sqrt(2) * abs(Zt[ai][v1][i]) if abs(freqs[i] - fl) < 1e-3 * fl else amp / math.sqrt(2) * float(np.exp(np.interp(math.log(fl), np.log(freqs), np.log(abs(Zt[ai][v1]) + 1e-30))))
                lines_out.append(dict(f_hz=fl, v_rms=vr, source=a["id"], sync=bool(a.get("sync"))))
                tot_sq += vr * vr
                if fl >= 2e4:
                    tot_sq_cap += vr * vr
    noise = []
    for ai, a in enumerate(aggs):
        if a["wave"]["kind"] == "band_noise":
            w = a["wave"]
            m = (freqs >= w["f_lo"]) & (freqs <= w["f_hi"])
            dens = (w["i_rms_a"] ** 2) / (w["f_hi"] - w["f_lo"])
            noise.append(dict(source=a["id"], f_hz=freqs[m].tolist(), psd_v2_per_hz=(dens * abs(Zt[ai][v1][m]) ** 2).tolist(),
                              v_rms_band=math.sqrt(dens * np.trapezoid(abs(Zt[ai][v1][m]) ** 2, freqs[m]))))
    js = dict(
        id="IF-MIC-VDD-NOISE", provider="sim/noise/budget.py", date=time.strftime("%Y-%m-%d"), board_sha256=board_sha,
        note="volts at U2.5 (mic VDD) relative to U2.3 (mic GND). z_rail = volts at the bridge P-source rail (Q1.4 vs R21.2) per ampere of bridge supply current; h_ibridge_to_micvdd = volts at the mic VDD pin per ampere of the same current. Both complex, 1 kHz-200 kHz, A03 injection pair (Q1.4 -> R21.1).",
        f_hz=f.tolist(), z_rail_ohm={"re": zr.real.tolist(), "im": zr.imag.tolist()},
        h_ibridge_to_micvdd_ohm={"re": hm.real.tolist(), "im": hm.imag.tolist()},
        background_lines_1k_100k=lines_out, background_v_rms_lines_1k_100k=math.sqrt(tot_sq), background_noise=noise,
        e2e_requirement={"psrr_flat55_mv_rms_max": 10.0, "psrr_rolloff_mv_rms_max": 0.3, "src": "docs/sim/e2e-chain.yaml interfaces.IF-MIC-VDD-NOISE.requirement_from_e2e"},
        e2e_check={"background_mv_rms": 1e3 * math.sqrt(tot_sq + sum(n["v_rms_band"] ** 2 for n in noise)),
                   "background_mv_rms_20k_100k": 1e3 * math.sqrt(tot_sq_cap + sum(n["v_rms_band"] ** 2 for n in noise)),
                   "dominant_line": max(lines_out, key=lambda r: r["v_rms"]) if lines_out else None,
                   "note": "background excludes the bridge's own audio-band supply current: the e2e sim supplies ctx.side['i_sup'] and multiplies by h_ibridge_to_micvdd"})
    (out / "IF-MIC-VDD-NOISE.json").write_text(json.dumps(js, default=float))
    return js["e2e_check"]


def dc_rail_paths(net, info, pairs=(("U4.1", "Q1.4"), ("U4.1", "Q2.4"), ("U4.1", "U1.25"), ("U4.1", "U1.21"), ("U1.15", "U2.5"), ("Q1.1", "R21.1"),
                                    ("U2.3", "U1.24"), ("C13.2", "U2.3"), ("C13.2", "U1.24"), ("R21.2", "U1.8"), ("U1.24", "J4.1"), ("C14.2", "R21.2"))):
    """DC copper resistance (mOhm) of rail/return paths: inductors shorted, capacitors open, plane meshed. For IR-drop at peak current."""
    pn = info["pad_node"]
    out = {}
    for a, b in pairs:
        if a not in pn or b not in pn:
            continue
        n2 = lumped.Network()
        for e in net.elems:
            if e["kind"] == "R" and (e.get("kind_") in ("trace", "via", "plane") or e.get("ref") in ("R20", "R21")):
                n2.add("R", e["n1"], e["n2"], e["val"])
            elif e["kind"] == "L" and (e.get("kind_") in ("trace", "via") or e.get("ref") in ("R20", "R21")):
                n2.add("R", e["n1"], e["n2"], 1e-9)
        n2.add("R", pn[b], "0", 1e-9)
        try:
            r = abs(n2.ac(np.array([1.0]), [(pn[a], pn[b])], [(pn[a], pn[b])], gmin=1e-15)[0][0][0])
        except Exception:
            continue
        out[f"{a}->{b}"] = round(float(r) * 1e3, 2)
    return out


def dc_metrics(red, geom, info, params):
    """Plane-only DC resistances between named pad groups (mOhm). Uses the nearest GND via of each pad."""
    names, G = red["names"], red["G"]
    vias = {n: (geom["vias"][int(n[2:])]["x"], geom["vias"][int(n[2:])]["y"]) for n in names}

    def near(ref, num):
        p = next(p for p in geom["pads"] if p["ref"] == ref and p["num"] == str(num))
        return min(range(len(names)), key=lambda i: (vias[names[i]][0] - p["x"]) ** 2 + (vias[names[i]][1] - p["y"]) ** 2)

    out = {}
    for a, b, label in [(("U2", 3), ("U1", 24), "mic_gnd_to_mcu_vss"), (("R21", 2), ("U1", 8), "shunt_gnd_to_mcu_vssa"),
                        (("U1", 24), ("J4", 1), "mcu_vss_to_cell_neg"), (("R21", 2), ("J4", 1), "shunt_gnd_to_cell_neg"),
                        (("C13", 2), ("U1", 24), "mic_bypass_gnd_to_mcu_vss")]:
        try:
            out[label] = round(plane.reff(G, near(*a), near(*b)) * 1e3, 3)
        except StopIteration:
            pass
    return out


SWEEPS = [  # label, dotted-path overrides applied to params (each multiplies or replaces)
    ("base", {}),
    ("LDO Zout x10", {"ldo.r_out_ohm": ("x", 10.0), "ldo.l_out_nh": ("x", 10.0)}),
    ("LDO Zout x0.2", {"ldo.r_out_ohm": ("x", 0.2), "ldo.l_out_nh": ("x", 0.2)}),
    ("PA5 R 25 ohm (less filtering)", {"die.r_pa5_ohm": ("=", 25.0)}),
    ("PA5 R 100 ohm", {"die.r_pa5_ohm": ("=", 100.0)}),
    ("die C 0.5 nF (x0.1)", {"die.c_die_nf": ("x", 0.1)}),
    ("all MLCC at 30 % of nominal C", {"components.dc_bias_keep": ("map", 0.3)}),
    ("ESR x3", {"components.esr_ohm": ("mapx", 3.0)}),
    ("mic floor -6 dB (optimistic) vs +8 dB handled in LN-M01 note", {}),
]


def _apply(params, ov):
    import copy
    p = copy.deepcopy(params)
    for path, (op, val) in ov.items():
        d = p
        keys = path.split(".")
        for k in keys[:-1]:
            d = d[k]
        k = keys[-1]
        if op == "x":
            d[k] = d[k] * val
        elif op == "=":
            d[k] = val
        elif op == "map":
            d[k] = {kk: val for kk in d[k]}
        elif op == "mapx":
            d[k] = {kk: vv * val for kk, vv in d[k].items()}
    return p


def sweep(geom, params, bom, agg, out, log=print):
    rows = []
    for label, ov in SWEEPS[:-1]:
        p = _apply(params, ov)
        net, info, mesh, red = build_l1(geom, p, bom)
        res, _ = analyse(net, info, geom, p, agg, out, log=lambda *a, **k: None, l2=False)
        mic = res["rows"]
        w = min(mic, key=lambda r: r["margin_pes"])
        rows.append(dict(case=label, worst_margin_pes_db=round(w["margin_pes"], 1), worst_margin_nom_db=round(w["margin_nom"], 1), at=f"{w['aggressor']} {w['f_hz']:.0f} Hz",
                         kelvin_pct=round(res["kelvin"]["z_kelvin_error_pct_of_r21"], 2)))
        log(f"  sweep {label:34s} worst margin nom/pes {w['margin_nom']:6.1f}/{w['margin_pes']:6.1f} dB at {w['aggressor']} {w['f_hz']:.0f} Hz; Kelvin {rows[-1]['kelvin_pct']} %")
    return rows


def plot(res, freqs, Zt, aggs, victims, out: Path):
    """noise_budget.png (dark, tools/plotstyle.py): transimpedance aggressor -> mic VDD, and the worst margins."""
    sys.path.insert(0, str(REPO / "tools"))
    import plotstyle  # noqa: PLC0415
    plt = plotstyle.apply()
    v1 = next(i for i, v in enumerate(victims) if v["class"] == "mic_supply")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw=dict(width_ratios=[1.25, 1]))
    for k, (ai, a) in enumerate(enumerate(aggs)):
        a1.loglog(freqs, np.abs(Zt[ai][v1]) * 1e3, color=plotstyle.SERIES[k % 8], ls="-" if k < 8 else "--", label=a["id"].split("_")[0], lw=1.2)
    a1.axvspan(20e3, 96e3, color=plotstyle.SERIES[3], alpha=0.12, lw=0)
    a1.text(21e3, a1.get_ylim()[0] * 3, "capture band", color=plotstyle.SERIES[3], fontsize=8)
    a1.set_xlim(1e3, 1e8)
    a1.set_xlabel("Hz"); a1.set_ylabel("mohm: volts at U2.5-U2.3 per ampere injected")
    a1.set_title("Aggressor -> mic VDD transimpedance (draft board)")
    a1.legend(ncol=2, labelcolor=plotstyle.TEXT)
    rows = sorted([r for r in res["rows"] + res["l2_rows"] if r["kind"] in ("tone", "band")], key=lambda r: r["margin_pes"])[:10]
    lab = [f"{r['aggressor'].split('_')[0]} {r.get('mechanism', 'conduction')[:4]} {r['f_hz'] / 1e3:.0f}k" for r in rows]
    a2.barh(range(len(rows)), [r["margin_pes"] for r in rows], color=plotstyle.SERIES[2], label="pessimistic PSRR")
    a2.barh(range(len(rows)), [r["margin_nom"] for r in rows], color="none", edgecolor=plotstyle.SERIES[0], label="nominal PSRR")
    a2.axvline(0, color=plotstyle.SERIES[7]); a2.axvline(10, color=plotstyle.SERIES[3], ls="--")
    a2.set_yticks(range(len(rows))); a2.set_yticklabels(lab); a2.invert_yaxis()
    a2.set_xlabel("margin to the tone/band limit, dB (0 = limit, dashed = sign-off 10)")
    a2.set_title("Worst mic-supply spurs"); a2.legend(labelcolor=plotstyle.TEXT)
    fig.savefig(out / "noise_budget.png")


def check_doc(res: dict, doc_path: Path = DOC) -> list[str]:
    """Compare this run with docs/sim/layout-noise.yaml: thresholds always, `results` only when the board sha matches."""
    out = []
    if not res.get("valid", True):
        out.append("INVALID run (stale board vs netlist, or unrouted nets): results not comparable; " + "; ".join(res.get("warnings", [])[:2]))
    if not doc_path.exists():
        return out + [f"doc missing: {doc_path}"]
    d = yaml.safe_load(doc_path.read_text())
    fl = res["floor"]["nominal"]
    th = d["thresholds"]
    for key, val in (("tone_limit_dbfs", fl["tone_limit_dbfs"]), ("band_limit_dbfs", fl["band_limit_dbfs"])):
        if abs(th[key]["value"] - val) > 0.05:
            out.append(f"DRIFT thresholds.{key}: doc {th[key]['value']} vs code {val:.2f}")
    dr = d["results"]
    if dr.get("board_sha256") != res["board"]["sha256"]:
        out.append(f"doc results are for board sha {dr.get('board_sha256')}, this run is {res['board']['sha256']}: results section is STALE (thresholds checked)")
        return out
    m = {x["id"]: x for x in res["metrics"]}
    dm = dr["metrics"]
    chk = [("LN-M01", "value_db_pessimistic", m["LN-M01"].get("value_db"), 0.5), ("LN-M02", "value_db", m.get("LN-M02", {}).get("value_db"), 0.5),
           ("LN-M03", "value_pct", m["LN-M03"].get("value_pct"), 0.05), ("LN-M04", "value_mv_pk", m.get("LN-M04", {}).get("value_mv_pk"), 0.01),
           ("LN-M05", "value_uv_rms", m.get("LN-M05", {}).get("value_uv"), 0.1)]
    for mid, key, val, tol in chk:
        if val is None or abs(dm[mid][key] - val) > tol:
            out.append(f"DRIFT results.metrics.{mid}.{key}: doc {dm[mid][key]} vs run {val}")
    for k, v in res["dc_rail_paths_mohm"].items():
        dv = dr["rail_paths_dc_mohm"].get(k)
        if dv is not None and abs(dv - v) > 0.5:
            out.append(f"DRIFT results.rail_paths_dc_mohm.{k}: doc {dv} vs run {v}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("board", nargs="?", default=None, help="default: newest routed board (pcbgeom.default_board; env NOISE_BOARD)")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--params", default=str(HERE / "params.yaml"))
    ap.add_argument("--netlist", default=str(REPO / "hw/pod/pod.net"), help="schematic netlist for the stale-board check ('' to skip)")
    ap.add_argument("--aggressors", default=str(HERE / "aggressors.yaml"))
    ap.add_argument("--no-l2", action="store_true")
    ap.add_argument("--plot", action="store_true", help="write noise_budget.png (dark)")
    ap.add_argument("--check-doc", action="store_true", help="compare thresholds/results with docs/sim/layout-noise.yaml")
    ap.add_argument("--sweep", action="store_true", help="re-run L1 under perturbed assumptions (LDO Zout, PA5 R, die C, MLCC derating, ESR)")
    a = ap.parse_args(argv)
    a.board = a.board or pcbgeom.default_board(REPO)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    params, agg = load_yaml(a.params), load_yaml(a.aggressors)
    geom = pcbgeom.load(a.board)
    nd = pcbgeom.netlist_diff(geom, a.netlist) if a.netlist and Path(a.netlist).exists() else None
    bom = lumped.read_bom(str(REPO / params["board"]["bom"]))
    t0 = time.time()
    net, info, mesh, red = build_l1(geom, params, bom)
    print(f"L1 network: {len(net.nodes)} nodes, {len(net.elems)} elements, plane {info['plane']['cells']} cells ({time.time() - t0:.1f} s)")
    res, (freqs, Zt, pairs, probes, aggs_ok, victims_ok) = analyse(net, info, geom, params, agg, out, l2=not a.no_l2)
    res["e2e_if"] = export_if(res, freqs, Zt, pairs, probes, aggs_ok, victims_ok, out, geom["sha256"])
    res["dc_plane_mohm"] = dc_metrics(red, geom, info, params)
    res["dc_rail_paths_mohm"] = dc_rail_paths(net, info)
    if nd is not None:
        res["netlist_check"] = dict(netlist=a.netlist, pads_netlist=nd["pads_netlist"], pads_board=nd["pads_board"], mismatches=len(nd["mismatch"]),
                                    first=[list(map(str, m)) for m in nd["mismatch"][:6]])
        if nd["mismatch"]:
            res["warnings"].insert(0, f"board is STALE vs {Path(a.netlist).name}: {len(nd['mismatch'])} pad->net mismatches (first {nd['mismatch'][:4]})")
    else:
        res["netlist_check"] = dict(skipped=True)
    res["valid"] = not any("no copper path" in w or "STALE" in w for w in res["warnings"])
    res["metrics"] = metrics(res, agg, {})
    res["board"] = dict(path=a.board, sha256=geom["sha256"], stackup=geom["stackup"]["src"])
    np.savez_compressed(out / "transimpedance.npz", freqs=freqs, aggressors=[x["id"] for x in aggs_ok], probes=[v["id"] for v in victims_ok],
                        Z=np.array([[Zt[i][j] for j in range(len(victims_ok))] for i in range(len(aggs_ok))]))
    if a.plot:
        plot(res, freqs, Zt, aggs_ok, victims_ok, out)
    if a.sweep:
        res["sweep"] = sweep(geom, params, bom, agg, out)
    (out / "budget.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"{'aggressor':26s} {'victim':20s} {'f_in':>10s} {'f_out':>8s} {'Vrms':>10s} {'spur nom':>9s} {'spur pes':>9s} {'limit':>7s} {'margin nom/pes dB':>18s}")
    for r in res["rows"][:12]:
        print(f"{r['aggressor']:26s} {r['victim']:20s} {r['f_hz']:10.0f} {r['f_out_hz']:8.0f} {r['v_rms']:10.3e} {r['spur_nom']:9.1f} {r['spur_pes']:9.1f} {r['limit']:7.1f} {r['margin_nom']:8.1f}/{r['margin_pes']:.1f}")
    print("L2 field pickup (worst per aggressor/victim/mechanism):")
    for r in sorted(res["l2_rows"], key=lambda r: r["margin_pes"]):
        if r["kind"] == "tone":
            print(f"  {r['aggressor']:18s} {r['victim']:14s} {r['mechanism']:9s} f {r['f_hz']:11.0f} f_out {r['f_out_hz']:7.0f} Vrms {r['v_rms']:.2e} spur {r['spur_nom']:.0f}/{r['spur_pes']:.0f} dBFS margin {r['margin_nom']:.1f}/{r['margin_pes']:.1f} dB [{r['regime']}]")
        else:
            print(f"  {r['aggressor']:18s} {r['victim']:14s} {r['mechanism']:9s} f {r['f_hz']:11.0f} Vpk worst line {r['v_pk']:.2e}, sum of harmonics {r['v_pk_sum_harmonics']:.2e} V, margin vs 100 mV {r['margin_pes']:.1f} dB [{r['regime']}]")
    for p in res["l2_pairs"]:
        print(f"  pair {p['aggressor']:16s}->{p['victim']:10s} M free/image {p['M_free_nH']:8.4f}/{p['M_image_nH']:8.4f} nH   Cm free/image {p['Cm_free_fF']:8.3f}/{p['Cm_image_fF']:8.3f} fF")
    for w in res["warnings"]:
        print("WARNING:", w)
    if not res["valid"]:
        print("RESULTS INVALID: stale board (pad->net map != schematic netlist) or nets without copper; fix before reading any number below")
    print("IF-MIC-VDD-NOISE written; background ripple at mic VDD (all declared non-bridge lines + noise, 1-100 kHz):", f"{res['e2e_if']['background_mv_rms']:.4f} mV rms, of which 20-100 kHz {res['e2e_if']['background_mv_rms_20k_100k']:.4f} mV rms")
    print("DC rail paths mOhm (copper only, pad to pad):", res["dc_rail_paths_mohm"])
    if a.check_doc:
        res["doc_check"] = check_doc(res)
        print("DOC CHECK:", res["doc_check"] or "doc and run agree (thresholds + results for this board sha)")
    print("METRICS:")
    for m in res["metrics"]:
        print("  ", {k: v for k, v in m.items()})
    print("DC plane mOhm:", res["dc_plane_mohm"], " Kelvin:", res["kelvin"])
    return res


def exit_code(res: dict) -> int:
    """0 = valid run and (if checked) doc agrees; 1 = invalid run or doc drift/stale (the smoke run must fail loudly)."""
    return 0 if res.get("valid", False) and not res.get("doc_check") else 1


if __name__ == "__main__":
    sys.exit(exit_code(main()))
