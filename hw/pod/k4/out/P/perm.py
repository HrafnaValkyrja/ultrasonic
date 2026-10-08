import itertools, subprocess, shutil, sys, os, pcbnew
nets = {"CHG_INT": ["J21.27", "U1.38"], "VBUS_SENSE": ["J21.26", "U1.11"], "BTN": ["J21.29", "U1.10"], "VBAT_SENSE": ["J21.28", "U1.14"]}
subprocess.run(["python3","-c","""
import pcbnew
b=pcbnew.LoadBoard('w1.kicad_pcb')
cs={b.FindNet(n).GetNetCode() for n in %r}
for t in list(b.GetTracks()):
    if t.GetNetCode() in cs: b.Remove(t)
pcbnew.SaveBoard('base.kicad_pcb',b)
""" % list(nets)],capture_output=True)
print(os.path.exists("base.kicad_pcb"),flush=True)
for order in itertools.permutations(nets):
    shutil.copy("base.kicad_pcb", "w.kicad_pcb"); ok = True
    for n in order:
        r = subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0", "python3", "../../../route_net3d.py", "w.kicad_pcb", n] + nets[n], capture_output=True, text=True)
        if "NO PATH" in r.stdout or r.returncode:
            ok = False; break
    print(order, "OK" if ok else "fail at " + n, flush=True)
    if ok:
        shutil.copy("w.kicad_pcb", "w_perm.kicad_pcb"); break
