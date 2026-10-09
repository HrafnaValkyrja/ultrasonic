"""I-020 kill test: programme energy outside the most sensitive bone band, and the dB a spectral shift would give. Fence: systemd-run --user --scope -p MemoryMax=3G"""
import json, pathlib, numpy as np
from scipy import signal
from scipy.io import wavfile
root = pathlib.Path(__file__).resolve().parents[2]
FS = 12500.0
fs0, y0 = wavfile.read(root/"sim/out/nature/2_translated_only.wav"); y = signal.resample_poly(y0/32768.0, 25, 96)
tf = json.load(open(root/"sim/acoustics/out/bone_tf.json")); f_tf=np.array(tf["f_hz"]); NA=np.array(tf["mag_db_n_per_a"]); THRF=np.array(tf["thr_front_measured_db_re_1uN"])
fc = np.array([1000,1250,1600,2000,2500,3150,4000,5000.])
na = np.interp(np.log(fc), np.log(f_tf), NA)
thr_front = np.interp(np.log(fc), np.log(f_tf), THRF)
# Henry&Letowski 2007 mastoid RETFL (repo shared-params, secondary) at 1.5/2/2.5/3/4 kHz
P = np.array([1500,2000,2500,3000,4000.]); H = np.array([36.5,31.0,29.5,30.0,35.5])
thr_mast = np.interp(np.log(fc), np.log(P), H, left=H[0], right=H[-1])
sos=[signal.butter(4,[f/2**(1/6),f*2**(1/6)],"bp",fs=FS,output="sos") for f in fc]
win=int(.2*FS); fr=int(.1*FS); n=len(y)//fr; r=np.sqrt((y[:n*fr].reshape(n,fr)**2).mean(1)); act=r>r.max()*.1
ev=[];i=0
while i<n:
    if act[i]:
        j=i
        while j+1<n and act[j+1:j+4].any(): j+=1
        ev.append((i*fr,(j+1)*fr)); i=j+1
    else: i+=1
ev=[e for e in ev if r[e[0]//fr:e[1]//fr].max()>r.max()*.1]
B=np.array([signal.sosfilt(s,y) for s in sos]); sm=np.array([np.convolve(b**2,np.ones(win)/win,"same") for b in B])
tot=np.sum(sm,0)
out={"bands_hz":fc.tolist(),"thr_front":thr_front.round(1).tolist(),"thr_mastoid_HL":thr_mast.round(1).tolist(),"na_db_per_A":na.round(1).tolist()}
inband=(fc>=2000)&(fc<=4000)
for nm,thr in (("front",thr_front),("mastoid",thr_mast)):
    cost=na-thr          # dB margin per unit band current (higher = more sensitive)
    best=int(np.argmax(np.where(inband,cost,-1e9))); res=[]
    for a,b in ev:
        k=a+np.argmax(tot[a:b]); p=sm[:,k]                       # worst-case 200 ms peak of call
        cur=10*np.log10(p)+cost                                   # per-band margin at equal current scale
        m_now=cur.max()                                           # sim's detector: best band
        m_pow=10*np.log10(np.sum(10**(cur/10)))                   # all bands add
        m_shift=10*np.log10(p.sum())+cost[best]                   # all current into best band
        share=p[~inband].sum()/p.sum()
        res.append((m_shift-m_now,m_shift-m_pow,share))
    r_=np.array(res); out[nm]={"best_band_hz":float(fc[best]),"gain_vs_best_band_db":{"median":float(np.median(r_[:,0])),"min":float(r_[:,0].min()),"max":float(r_[:,0].max())},"gain_vs_powersum_db":{"median":float(np.median(r_[:,1])),"max":float(r_[:,1].max())},"energy_outside_2_4k_frac_median":float(np.median(r_[:,2])),"per_call_gain":r_[:,0].round(2).tolist()}
out["n_calls"]=len(ev); out["band_energy_share"]=(sm[:, ev[0][0]:ev[-1][1]].sum(1)/sm[:, ev[0][0]:ev[-1][1]].sum()).round(4).tolist()
json.dump(out,open(root/"sim/acoustics/out/i020_band.json","w"),indent=1); print(json.dumps(out,indent=1))
