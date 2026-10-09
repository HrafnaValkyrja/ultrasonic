"""Kill tests I-034 (flat-top drive) and I-036 (all-pass crest reduction) on the translated calls (Port Meadow-derived, sim/out/nature/2_translated_only.wav)
using the per-call 200 ms method of audibility_reconciled.py. Equal peak = limiter ceiling (0.5203 FS = the 208 mA clamp); current = 208 mA * mean|x|/ceiling.
    systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 sim/acoustics/crest_kill.py   -> sim/acoustics/out/crest_kill.json"""
import json, re, pathlib, numpy as np
from scipy import signal
src = open(pathlib.Path(__file__).with_name("audibility_reconciled.py")).read()
head = src.split("tf = json.load")[0]; head = head.replace("plotstyle.apply()", "pass").replace("import plotstyle", "pass").replace("import matplotlib.pyplot as plt", "")
ns = {"__file__": str(pathlib.Path(__file__).with_name("audibility_reconciled.py"))}; exec(head, ns)
y, pk0, lahead, FS, CEIL = ns["y"], ns["pk0"], ns["lahead"], ns["FS"], ns["CEIL"]["A"]
base = y / pk0
fr = int(.1 * FS); n = len(y) // fr; r = np.sqrt((y[:n*fr].reshape(n, fr)**2).mean(1)); act = r > r.max()*.1
ev = []; i = 0
while i < n:
    if act[i]:
        j = i
        while j+1 < n and act[j+1:j+4].any(): j += 1
        ev.append((i*fr, (j+1)*fr)); i = j+1
    else: i += 1
win = int(.2*FS); bp = signal.butter(4, [1500, 4000], "bp", fs=FS, output="sos")
def stats(x):
    b = signal.sosfilt(bp, x); sw = np.sqrt(np.convolve(b**2, np.ones(win)/win, "same"))
    lev = np.array([20*np.log10(sw[a:e].max()+1e-12) for a, e in ev])
    cur = 208.0*np.abs(x).mean()/CEIL                      # mA, whole file mean
    callcur = np.array([208.0*np.abs(x[a:e]).mean()/CEIL for a, e in ev])
    return lev, cur, callcur
def spread(x, ref):                                         # distortion proxies on call segments
    out = []
    for a, e in ev:
        s = x[a:e]; F = np.abs(np.fft.rfft(s*np.hanning(len(s))))**2; f = np.fft.rfftfreq(len(s), 1/FS)
        out_band = F[(f < 1500) | (f > 4000)].sum()/F.sum()
        rf = signal.sosfilt(bp, ref[a:e]); g = (s@rf)/(rf@rf); thd = ((s-g*rf)**2).sum()/(s**2).sum()   # not-explained-by-linear-gain power
        out.append((out_band, thd))
    o = np.array(out); return float(np.median(o[:, 0])), float(np.median(o[:, 1]))
def run(name, pre, drive_db=12):
    z = pre(base)
    z = z/np.abs(z).max()*CEIL*10**(drive_db/20)
    return lahead(z, CEIL)
sat = lambda k: (lambda x: np.tanh(k*x/np.abs(x).max())/np.tanh(k)*np.abs(x).max())
def ap_chain(secs):
    def f(x):
        for fc, q in secs:
            w = 2*np.pi*fc/FS; al = np.sin(w)/(2*q); b = [1-al, -2*np.cos(w), 1+al]; a = [1+al, -2*np.cos(w), 1-al]
            x = signal.lfilter(b, a, x)
        return x
    return f
rng = np.random.default_rng(1)
def rand_secs(m): return [(float(np.exp(rng.uniform(np.log(1200), np.log(4500)))), float(rng.uniform(0.3, 3))) for _ in range(m)]
ref_x = run("ref", lambda x: x); ref_lev, ref_cur, ref_cc = stats(ref_x)
res = {"ref (limiter only, +12 dB drive)": (0, 0)}; out = {}
def rec(name, x):
    lev, cur, cc = stats(x); ob, th = spread(x, base)
    d = lev-ref_lev; out[name] = {"gain_db_median": float(np.median(d)), "gain_db_mean": float(d.mean()), "gain_db_p10": float(np.percentile(d, 10)), "gain_db_min": float(d.min()), "gain_db_max": float(d.max()),
        "mean_ma": float(cur), "ma_ratio": float(cur/ref_cur), "call_ma_ratio_median": float(np.median(cc/ref_cc)), "out_of_band_frac_median": ob, "nonlinear_frac_median": th, "crest_db_file": float(20*np.log10(np.abs(x).max()/x.std()))}
    print("%-34s gain med %+.2f mean %+.2f p10 %+.2f [%+.2f..%+.2f] | mA x%.2f (call x%.2f) | outband %.3f nonlin %.3f crest %.1f" % (name, d.mean()*0+np.median(d), d.mean(), np.percentile(d, 10), d.min(), d.max(), cur/ref_cur, np.median(cc/ref_cc), ob, th, out[name]["crest_db_file"]))
rec("ref", ref_x); print("events", len(ev), "ref mA mean %.1f, ref crest %.1f" % (ref_cur, out["ref"]["crest_db_file"]))
for k in (1.5, 2, 2.5, 3, 6, 12): rec("flat-top tanh k=%g (+12 dB)" % k, run("s", sat(k)))
for k in (3, 12): rec("flat-top tanh k=%g (+12 dB, pre-limit)" % k, run("s", sat(k), 0))
for m in (2, 4, 8): rec("all-pass %d sections fixed" % m, run("a", ap_chain([(1500*(3/1.5)**(i/(max(m-1, 1))), 1.0) for i in range(m)])))
best = None   # random search 4 and 8 sections, scored on the corpus mean gain (optimistic: tuned on the test set)
for m in (4, 8):
    bs, bg = None, -9
    for t in range(40):
        s = rand_secs(m); c = ap_chain(s); z = c(base); g = np.abs(base).max()/np.abs(z).max()
        zz = z/np.abs(z).max()*CEIL*10**(12/20); x = lahead(zz, CEIL); gm = np.mean(stats(x)[0]-ref_lev)
        if gm > bg: bg, bs = gm, s
    rec("all-pass %d sections searched (tuned on corpus)" % m, lahead(ap_chain(bs)(base)/np.abs(ap_chain(bs)(base)).max()*CEIL*10**(12/20), CEIL)); out["all-pass %d sections searched (tuned on corpus)" % m]["secs"] = bs
json.dump(out, open(pathlib.Path(__file__).parent/"out/crest_kill.json", "w"), indent=1)
