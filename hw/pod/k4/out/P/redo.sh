cd /home/hrafnavalkyrja/Desktop/ultrasonic/hw/pod/k4/out/P
cp w1.kicad_pcb w.kicad_pcb; python3 - <<'P' 2>&1 | grep -v "assert\|Debug\|leak"
import pcbnew
mm=pcbnew.FromMM
b=pcbnew.LoadBoard('w.kicad_pcb')
n=b.FindNet('VBUS_SENSE').GetNetCode()
for t in list(b.GetTracks()):
    if t.GetNetCode()==n: b.Remove(t)
pcbnew.SaveBoard('w.kicad_pcb',b)
P
R="systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 python3 ../../../route_net3d.py w.kicad_pcb"
$R CHG_INT J21.27 @8.4,7.8/1,2 U1.38 2>&1 | grep -v "assert\|Debug\|leak"|tail -3
$R VBUS_SENSE U1.11 J21.26 2>&1 | grep -v "assert\|Debug\|leak"|tail -3
kicad-cli pcb drc --format json --severity-error -o drc_w.json w.kicad_pcb >/dev/null 2>&1; python3 -c "
import json;d=json.load(open('drc_w.json'))
print(len(d['violations']),len(d['unconnected_items']))
for v in d['violations']: print(v['description'],[ (i['description'][:50],i['pos']) for i in v['items']])
for u in d['unconnected_items']: print([i['description'] for i in u['items']])"
