"""I-027: idle bridge at 50 % duty (AD, as fw squelch does) vs Hi-Z (all four FETs off), plus re-enable transient.
python3 sim/checks/bridge_hiz_idle.py   (fence: systemd-run --user --scope -p MemoryMax=3G ...)"""
import sys, re
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import bridge_spice as B
spice = B.spice
T = B.T

def run(mode, L, dt=12.5e-9, n=80, t_en=40 * T):
    k = np.arange(n); d = np.full(n, 0.5)
    pa, na = B.gate_pwl(d, dt, n * T)
    pb, nb = B.gate_pwl(1 - d, dt, n * T, centre_offset=T / 2 + 100e-12)
    if mode == "hiz":
        pa, na, pb, nb = [[(0.0, B.VDD)], [(0.0, 0.0)], [(0.0, B.VDD)], [(0.0, 0.0)]]
    elif mode == "reen":   # off until t_en, then the 50 % pattern
        def cut(l, off):
            l = [(t, v) for t, v in l if t >= t_en]
            return [(0.0, off), (t_en - 1e-9, off)] + [(t, v) for t, v in l]
        pa, na, pb, nb = cut(pa, B.VDD), cut(na, 0.0), cut(pb, B.VDD), cut(nb, 0.0)
    txt = B.netlist(dt, 0.0, 2000.0, L, n, None)
    for name, w in (("VGPA", pa), ("VGNA", na), ("VGPB", pb), ("VGNB", nb)):
        txt = re.sub(rf"^{name} (\S+) 0 PWL\(.*\)$", lambda m: f"{name} {m.group(1)} 0 PWL({B.fmt(w)})", txt, flags=re.M)
    res = spice.run(txt)
    return res.tran["time"], -res.tran["i(vin)"], res.tran["i(lx)"]

for L in (0.3e-3, 1.26e-3):
    for mode in ("sq50", "hiz"):
        t, iv, il = run(mode, L, n=60)
        print(f"L={L*1e3:.2f}mH {mode:5s} bus avg {spice.tavg(t, iv, 5*T, t[-1])*1e3:7.3f} mA  coil pk {np.max(np.abs(il[t>5*T]))*1e3:6.1f} mA")
    t, iv, il = run("reen", L)
    t_en = 40 * T
    w = (t > t_en) & (t < t_en + 20 * T)
    # low-pass the coil current to the audio band (mean over 5 us bins -> 20 us window) to see the DC-offset decay
    tb = np.arange(t_en, t_en + 20 * T, 5e-6)
    m = [np.mean(il[(t >= a) & (t < a + 5e-6)]) * 1e3 for a in tb]
    print(f"   re-enable: coil peak {np.max(np.abs(il[w]))*1e3:.1f} mA; 5us-mean coil I (mA): {', '.join(f'{x:.2f}' for x in m[:8])}; pre-enable leak {np.max(np.abs(il[(t>5*T)&(t<t_en)]))*1e6:.2f} uA")
