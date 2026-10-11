"""I-027 pop de-risk: H-bridge + transducer (R + L + motional branch) re-enable from / stop into Hi-Z, at the firmware's real sequence,
then the acoustic transient vs the tragus threshold. python3 sim/checks/hiz_reenable_click.py  (fence 3G; ~1 min)
fw sequence (fw/port_u575/hal_u575_periph.c hal_pwm_start): CCR1=CCR3=ARR/2, UG (CNT=0), CEN, MOE last -> the first edge is the CENTRE of leg A's
active window (centre-aligned mode 1, active while CNT<CCR), leg B inverted (AD): deterministic phase, not arbitrary. Stop (hal_pwm_stop,
app.c apply_outputs) is at an arbitrary phase of the 200 kHz period (hop boundary vs timer), so 8 stop phases are swept.
Transducer nominal (bone_tf.json cond): Re 8 + r_extra 1.52, Le 0.5 mH (0.3 / 1.3 mH range), Bl 1, mm 0.45 g, f0 350 Hz, Qm 3 -> series motional
parallel RLC: Cm = mm/Bl^2, Lm = Bl^2/k, Rm = Bl^2 Q/(w0 mm)... Force = |H(f)| |I(f)| with H = bone_tf nominal N/A (absolute level assumed 1 N/A, not measured)."""
import sys, re, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import bridge_spice as B
spice, T, VDD, EDGE = B.spice, B.T, B.VDD, B.EDGE
REPO = Path(__file__).resolve().parents[2]
RE, MM, F0, Q, BL = 9.52, 0.45e-3, 350.0, 3.0, 1.0
W0 = 2 * np.pi * F0
CM, LM, RM = MM / BL**2, 1 / (MM * W0**2) * BL**2, BL**2 * Q / (W0 * MM) / Q * Q  # RM placeholder fixed below
RM = BL**2 / (MM * W0 / Q)   # electrical equivalent of mechanical damping
TEN = 40 * T

def val(lst, t):
    ts, vs = zip(*lst); return float(np.interp(t, ts, vs))

def build(L, dt, mode, t_x):
    d = np.full(140, 0.5)
    pa, na = B.gate_pwl(d, dt, 140 * T, centre_offset=-T / 2)
    pb, nb = B.gate_pwl(1 - d, dt, 140 * T, centre_offset=0.0 + 100e-12)
    offs = (VDD, 0.0, VDD, 0.0)
    out = []
    for w, off in zip((pa, na, pb, nb), offs):
        if mode == "start":
            v0 = val(w, t_x)
            w2 = [(0.0, off), (t_x - 1e-9, off), (t_x, v0)] + [(t, v) for t, v in w if t > t_x]
        else:
            v0 = val(w, t_x)
            w2 = [(t, v) for t, v in w if t < t_x] + [(t_x, v0), (t_x + EDGE, off)]
        out.append(w2)
    txt = B.netlist(dt, 0.0, 2000.0, L, 140, None)
    for name, w in zip(("VGPA", "VGNA", "VGPB", "VGNB"), out):
        txt = re.sub(rf"^{name} (\S+) 0 PWL\(.*\)$", lambda m: f"{name} {m.group(1)} 0 PWL({B.fmt(w)})", txt, flags=re.M)
    txt = txt.replace("RX outa xm 8\nLX xm outb %s" % L,
        f"RX outa xm {RE}\nLX xm xm2 {L}\nCMOT xm2 outb {CM}\nLMOT xm2 outb {LM}\nRMOT xm2 outb {RM}")
    assert "CMOT" in txt
    return txt

def run(L, dt, mode, t_x):
    r = spice.run(build(L, dt, mode, t_x)); return r.tran["time"], r.tran["i(lx)"]

def avgT(t, i):   # one-period boxcar (kills the 200 kHz ripple exactly), sampled every T/4
    du = 5e-9; tu = np.arange(0, t[-1], du); iu = np.interp(tu, t, i)
    c = np.concatenate([[0], np.cumsum(iu)]); n = int(round(T / du))
    m = (c[n:] - c[:-n]) / n; tm = tu[n - 1:len(m) + n - 1]
    s = n // 4; return tm[::s], m[::s]

tf = json.load(open(REPO / "sim/acoustics/out/bone_tf.json"))
FH = np.array(tf["f_hz"]); NA = np.array(tf["mag_db_n_per_a"]); THR = np.array(tf["thr_front_measured_db_re_1uN"])
FB = np.array([250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000.])
TINT = 0.2   # s, temporal integration of the ear (energy-equivalent tone burst; conservative: short clicks need more than this)

def acoustic(tm, m):
    dts = tm[1] - tm[0]; res = []
    for f in FB:
        I = abs(np.sum(m * np.exp(-2j * np.pi * f * tm)) * dts)          # A*s
        Fp = I * 10 ** (np.interp(f, FH, NA) / 20)                        # N*s
        ft = 2 * Fp * np.sqrt(0.23 * f / TINT)                            # equivalent steady-tone amplitude, 1/3-oct band energy
        db = 20 * np.log10(max(ft, 1e-30) / 1e-6)
        res.append((f, I, db, db - np.interp(f, FH, THR)))
    return res

out = {}
for L in (0.3e-3, 0.5e-3, 1.3e-3):
    for dt in (12.5e-9, 25e-9):
        cases = {"start": [TEN]} | {"stop": [TEN + k * T / 8 for k in range(8)]}
        for mode, txs in cases.items():
            worst = None
            for tx in txs:
                t, i = run(L, dt, mode, tx)
                tm, m = avgT(t, i); k = tm >= tx - 2 * T
                a = acoustic(tm[k] - tx, m[k])
                mg = max(x[3] for x in a)
                if worst is None or mg > worst[0]:
                    worst = (mg, a, float(np.max(np.abs(m[k]))) * 1e3, float(np.sum(m[k]) * (tm[1] - tm[0])) * 1e6)
            out[f"L{L*1e3:.1f}mH_dt{dt*1e9:.1f}ns_{mode}"] = worst
            f_w = max(worst[1], key=lambda x: x[3])
            print(f"L={L*1e3:.1f}mH dt={dt*1e9:4.1f}ns {mode:5s}: boxcar-I peak {worst[2]:.3f} mA, area {worst[3]:.4f} uA*s; worst band {f_w[0]:.0f} Hz eq. tone {f_w[2]:.1f} dB re 1uN vs thr -> margin {f_w[3]:+.1f} dB", flush=True)
json.dump({k: dict(margin_db=v[0], peak_mA=v[2], area_uAs=v[3], bands=[list(map(float, x)) for x in v[1]]) for k, v in out.items()},
          open(REPO / "sim/out/hiz_reenable_click.json", "w"), indent=1)
