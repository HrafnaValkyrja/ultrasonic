"""Local-search nudge of placement_P.yaml (M fixed): move the parts named in the violations (near etc.) to the nearest
position/rotation/face that lowers the violation count of place_k4.check + stack_check. Fenced, one at a time.

    python3 hw/pod/nudge_k4.py --L 15.5 --cx 9.8 --fine --vip [--rounds 6] [--radius 3.0]
"""
from __future__ import annotations
import argparse, itertools, re, sys, time
from pathlib import Path
import yaml
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import place_k4 as K  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=float, required=True); ap.add_argument("--cx", type=float, default=None)
    ap.add_argument("--u1rot", type=int, default=90); ap.add_argument("--u1cy", type=float, default=4.8)
    ap.add_argument("--win", action="store_true"); ap.add_argument("--fine", action="store_true"); ap.add_argument("--vip", action="store_true")
    ap.add_argument("--rounds", type=int, default=6); ap.add_argument("--radius", type=float, default=3.0)
    ap.add_argument("--step", type=float, default=0.1); ap.add_argument("--budget", type=int, default=600, help="max evaluations")
    a = ap.parse_args()
    K.FINE["on"], K.VIP["on"], K.CX_FIX[0] = a.fine, a.vip, a.cx
    K.U1_ROT, K.U1_CY = a.u1rot, a.u1cy
    K.SOLDER_WIN["on"] = a.win
    L = a.L
    K.MIC_ROT, K._MIC_R, K.MIC_CY = K._mic_rot(K.P.parse_netlist(K.K4 / "pod_k4_M.net")[0]["U2"])
    comps, nets = {}, {}
    for bd in "PM":
        comps[bd], nets[bd] = K.P.parse_netlist(K.K4 / f"pod_k4_{bd}.net")
    plc = {bd: {k: tuple(v) for k, v in yaml.safe_load(open(K.K4 / f"placement_{bd}.yaml")).items()} for bd in "PM"}
    bM, fM, fanM = K.build("M", plc["M"], L)
    vM, _ = K.check("M", bM, fM, comps["M"], L, fanM)
    n_eval = [0]

    def ev(pp):
        n_eval[0] += 1
        b, fps, fan = K.build("P", pp, L)
        v, _ = K.check("P", b, fps, comps["P"], L, fan)
        sv, _ = K.stack_check(fps, fM, comps["P"], comps["M"], L)
        return v + sv

    cur = dict(plc["P"]); viol = ev(cur)
    print("start", len(viol), viol, flush=True)
    t0 = time.time()
    for rd in range(a.rounds):
        if not viol or n_eval[0] > a.budget:
            break
        names = []
        for s in viol:
            names += [t for t in re.findall(r"\b([A-Z]{1,2}\d+)\b", s) if t in cur and t not in ("U1", "J21")]
        for ref in dict.fromkeys(names):
            x0, y0, r0, s0 = cur[ref]
            cands = []
            n = int(a.radius / a.step)
            for i in range(-n, n + 1):
                for j in range(-n, n + 1):
                    d = (i * i + j * j) ** 0.5 * a.step
                    if d <= a.radius:
                        for rot in {r0, 0, 90, 180, 270}:
                            for side in {s0, "F", "B"}:
                                cands.append((d + (0.2 if rot != r0 else 0) + (0.3 if side != s0 else 0), round(x0 + i * a.step, 2), round(y0 + j * a.step, 2), rot, side))
            cands.sort()
            best = (len(viol), None)
            for _, x, y, rot, side in cands[:400]:
                if n_eval[0] > a.budget:
                    break
                if x < 0 or y < 0 or x > L or y > K.H:
                    continue
                trial = dict(cur); trial[ref] = (x, y, rot, side)
                try:
                    v = ev(trial)
                except Exception as e:      # noqa: BLE001
                    continue
                if len(v) < best[0]:
                    best = (len(v), trial, v)
                    break
            if best[1] is not None:
                cur, viol = best[1], best[2]
                print(f"round {rd} {ref} -> {cur[ref]}  viol {len(viol)} ({n_eval[0]} evals, {time.time()-t0:.0f}s)", flush=True)
                yaml.safe_dump({k: list(v) for k, v in sorted(cur.items())}, open(K.K4 / "placement_P.yaml", "w"), default_flow_style=None)
                if not viol:
                    break
    print("final", len(viol), viol, flush=True)


if __name__ == "__main__":
    main()
