"""P-THERM lumped thermal proof, K4 pod (2026-10-08). Run: python3 docs/proof/thermal/thermal.py -> thermal.png + printed numbers.
Nodes: J (U3 die) - B (board) - S (shell skin) - A (35 C ambient); C (cell) coupled to B (1.4 mm gap) and S (tape + 0.6 floor)."""
import sys, numpy as np
sys.path.insert(0, "hw/mech"); sys.path.insert(0, "tools")
import dims_k4 as K, plotstyle as ps
ps.apply(); import matplotlib.pyplot as plt
TA = 35.0
L, H, T = K.L, K.H, K.T                       # mm, outer envelope
A_out = 2*(L*H + L*T + H*T)*1e-6              # m2, whole outer surface
A_cell = 31.0*12.7e-6
def R_air(d_mm, A): return (d_mm*1e-3/0.026/A)
# parameters (ASSUMED values flagged in README)
H_CONV = {"docked, still air": 10.0, "worn, partly covered (bound)": 5.0}   # W/m2K conv+rad
R_BS = 30.0                       # board -> lid/shell via VHB + 1.0 lid, K/W (assumed)
R_BC = 1/(1/R_air(1.4, 30e-3*12e-3) + 6*30e-3*12e-3)    # board->cell, air+radiation across 1.4 mm
R_CS = 0.6e-3/0.2/A_cell + R_air(0.1, A_cell)*0 + 0.1e-3/0.2/A_cell + 5.0   # cell -> floor: 0.6 resin + 0.1 tape + contact
TH_JB = 30.3                      # U3 RthJB, BQ25180 SLUSE99C 7.3
TH_JA_EVM, TH_JA_JEDEC = 65.0, 107.1
C_cell, C_pod = 3.5*1.0, 3.0      # J/K (3.5 g x ~1 J/gK; board+shell ~3 J/K)
def powers(vbat):
    vin = 5.0 - 0.30                              # D4 PMEG3005EL ~0.3 V at 0.13 A
    p_u3 = (vin - vbat)*0.130 + (vin - vbat)*0.005 # PBAT + PSYS (5 mA system, VSYS ~ VBAT)
    p_d4 = 0.30*0.135
    p_cell = 0.130**2*0.30                        # 0.3 ohm cell+PCM (assumed)
    return p_u3, p_d4, p_cell
def run(h):
    R_S = 1/(h*A_out)
    t = np.arange(0, 3600*1.2, 1.0); Tb = Ts = Tc = TA
    vbat = 3.3; out = []
    for ti in t:
        vbat = min(4.2, vbat + 0.9/(3000.0))      # CC: ~50 min for 3.3 -> 4.2 V
        cc = vbat < 4.2
        if cc: pu, pd, pc = powers(vbat)
        else:
            frac = max(0.0, 1 - (ti-3000)/1500); pu, pd, pc = powers(4.2)[0]*frac*0.5, 0.0, 0.0
        Pb = pu + pd
        dTb = (Pb - (Tb-Ts)/R_BS - (Tb-Tc)/R_BC)/C_pod
        dTc = (pc + (Tb-Tc)/R_BC - (Tc-Ts)/R_CS)/C_cell
        dTs = ((Tb-Ts)/R_BS + (Tc-Ts)/R_CS - (Ts-TA)/R_S)/C_pod
        Tb += dTb; Tc += dTc; Ts += dTs
        out.append((ti/60, Ts, Tb, Tc, Tb + pu*TH_JB, pu))
    return np.array(out)
res = {k: run(h) for k, h in H_CONV.items()}
for k, r in res.items():
    i = r[:, 3].argmax(); print(f"{k}: shell max {r[:,1].max():.1f}  board max {r[:,2].max():.1f}  cell max {r[:,3].max():.1f}  Tj(JB) max {r[:,4].max():.1f}  at t={r[i,0]:.0f} min; U3 P0 {r[0,5]:.3f} W")
print("Tj bounds at P0, board at 35+shell rise:", [round(TA + 0.2*th,1) for th in (TH_JA_EVM, TH_JA_JEDEC)])
print(f"A_out {A_out*1e4:.1f} cm2, R_BC {R_BC:.0f} K/W, R_CS {R_CS:.1f} K/W, R_S(h10) {1/(10*A_out):.1f} K/W")
# awake: VSYS 4.2 worst for LDO
I_awake = {"MCU": 5.8, "audio-in": 2.15, "bridge ctrl": 1.06, "transducer avg": 2.5}   # mA at 3.0 V rail
Itot = sum(I_awake.values()); P_awake = 3.0*Itot*1e-3 + (4.2-3.0)*Itot*1e-3
print(f"awake worst: {Itot:.1f} mA, {P_awake*1e3:.0f} mW total (LDO {1.2*Itot:.0f} mW); shell rise docked-air-like {P_awake/(10*A_out):.1f} K, bound {P_awake/(5*A_out):.1f} K; U4 rise {1.2*Itot*1e-3*166:.1f} K")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for (k, r), c in zip(res.items(), ps.SERIES):
    ax[0].plot(r[:,0], r[:,3], color=c, label=f"cell, {k}")
    ax[0].plot(r[:,0], r[:,1], color=c, ls="--", label=f"shell, {k}")
ax[0].axhline(45, color=ps.SERIES[7], lw=1); ax[0].text(1, 45.3, "cell charge limit 45 C (Renata)", color=ps.SERIES[7], fontsize=8)
ax[0].axhline(43, color=ps.SERIES[3], lw=1); ax[0].text(1, 43.3, "skin touch 43 C (long contact)", color=ps.SERIES[3], fontsize=8)
ax[0].set_xlabel("min into charge (130 mA, 35 C ambient)"); ax[0].set_ylabel("deg C"); ax[0].set_title("K4 charging 130 mA: shell and cell"); ax[0].legend(fontsize=7, loc="lower right")
r = res["docked, still air"]
ax[1].plot(r[:,0], r[:,4], color=ps.SERIES[1], label="U3 junction (board + P x RthJB)")
ax[1].plot(r[:,0], r[:,2], color=ps.SERIES[0], label="board")
ax[1].axhline(100, color=ps.SERIES[7], lw=1); ax[1].text(1, 101, "U3 thermal regulation 100 C", color=ps.SERIES[7], fontsize=8)
ax[1].set_xlabel("min"); ax[1].set_title("U3 junction vs its limit (docked)"); ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig("docs/proof/thermal/thermal.png", dpi=130)
