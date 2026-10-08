# Generates build-sequence.svg (dark palette applied by render.sh)
steps=[("1","Parts check, print, ream","hand",1,15),("2","Wires to M: J7 J8, J4 J5","hand solder",3,40),
("3","Wire J2 (P inner) then J1","hand solder",5,35),("4","Mate P to M (BM28, once)","press",3,20),
("5","Bench power-up, flash, button","bench",2,60),("6","Cell on tape, arm litz, heel","hand",2,25),
("7","Stack onto lid (VHB, puck)","hand",3,30),("8","Epoxy post dab + close","hand",3,25),
("9","Cell leads to J5/J4 fold","hand solder",4,25),("10","Magnets, RTV, seam, mesh, skin","hand",3,40),
("11","First charge (G5)","supervised",2,90)]
hard={"3","9","7"}
W=1100;H=90+len(steps)*46+40
o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">',
f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
'<text x="20" y="34" font-size="22" font-weight="bold" fill="#111">K4 pod: owner build sequence (one pod, JLC assembles both boards)</text>',
'<text x="20" y="58" font-size="13" fill="#444">bar = difficulty 1-5 (red = 3 hardest) | minutes in grey | total about 6.8 h first pod, about 5 h second pod</text>']
for i,(n,t,m,d,mi) in enumerate(steps):
    y=80+i*46; c="#c0392b" if n in hard else "#2c7bb6"
    o.append(f'<rect x="20" y="{y}" width="{W-40}" height="38" rx="6" fill="#f0f0f0" stroke="#bbb"/>')
    o.append(f'<text x="34" y="{y+25}" font-size="16" font-weight="bold" fill="#111">{n}</text>')
    o.append(f'<text x="70" y="{y+25}" font-size="15" fill="#111">{t}</text>')
    o.append(f'<text x="520" y="{y+25}" font-size="13" fill="#555">{m}</text>')
    for k in range(5):
        o.append(f'<rect x="{650+k*44}" y="{y+9}" width="40" height="20" rx="3" fill="{c if k<d else "#d8d8d8"}"/>')
    o.append(f'<text x="900" y="{y+25}" font-size="13" fill="#555">{mi} min</text>')
    if n in hard: o.append(f'<text x="980" y="{y+25}" font-size="13" font-weight="bold" fill="#c0392b">HARD</text>')
o.append('</svg>')
open("build-sequence.svg","w").write("\n".join(o))
print(sum(s[4] for s in steps))
