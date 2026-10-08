"""Vision no-go vs pod extents (side view, x from hinge). Values from hw/mech/pod.py VISION_X, dims_k4, dims_r2, dims_k1(k1t)."""
V, REAR = 29.5, 67.5
bars = [("K4", 17.65, REAR), ("K1-thin", 33.7, REAR), ("phase2", 29.5, REAR)]
S, X0 = 8.0, 90; EAR = 100.0
x = lambda v: X0 + v*S
o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 400" font-family="sans-serif" font-size="13">',
 '<rect width="1000" height="400" fill="#141518"/>',
 '<text x="30" y="32" fill="#e6e6e6" font-size="18">Peripheral-vision no-go vs pod extent (side view, x rearward from hinge, mm)</text>',
 f'<rect x="{x(0)}" y="70" width="{x(V)-x(0)}" height="290" fill="#5a1e1e" opacity="0.35"/>',
 f'<text x="{x(0)+8}" y="90" fill="#ff8a8a">vision no-go zone (x &lt; 29.5)</text>',
 f'<rect x="{x(0)}" y="120" width="{x(REAR+5)-x(0)}" height="8" fill="#6b7280"/>',
 f'<text x="{x(0)+8}" y="116" fill="#9aa0a6">temple arm: hinge x=0 -> continues rearward to the ear keep-out (off-chart)</text>',
 f'<line x1="{x(V)}" y1="70" x2="{x(V)}" y2="365" stroke="#f5b942" stroke-width="2" stroke-dasharray="6 4"/>',
 f'<text x="{x(V)+6}" y="385" fill="#f5b942">vision line x = 29.5 (estimate; pen test decides)</text>',
 f'<line x1="{x(0)}" y1="70" x2="{x(0)}" y2="365" stroke="#bbb"/><text x="{x(0)-18}" y="385" fill="#bbb">hinge 0</text>',
 f'<line x1="{x(REAR)}" y1="70" x2="{x(REAR)}" y2="365" stroke="#6aa9ff" stroke-dasharray="3 3"/><text x="{x(REAR)-30}" y="385" fill="#6aa9ff">fixed rear 67.5</text>']
y = 150
for n, a, b in bars:
    if a < V:
        o.append(f'<rect x="{x(a)}" y="{y}" width="{x(V)-x(a)}" height="34" fill="#e5484d"/>')
        o.append(f'<rect x="{x(V)}" y="{y}" width="{x(b)-x(V)}" height="34" fill="#3b82c4"/>')
        o.append(f'<text x="{x(a)+4}" y="{y+22}" fill="#fff">{V-a:.2f} mm in no-go</text>')
    else:
        o.append(f'<rect x="{x(a)}" y="{y}" width="{x(b)-x(a)}" height="34" fill="#3b82c4"/>')
    o.append(f'<text x="30" y="{y+22}" fill="#e6e6e6">{n}</text>')
    o.append(f'<text x="{x(b)+8}" y="{y+22}" fill="#e6e6e6">{a:.2f} - {b} (L {b-a:.2f})</text>')
    y += 60
o.append('<text x="30" y="345" fill="#e6e6e6">Max pod 29.5..67.5 = 38.0 mm. K4 (49.85) must lose 11.85 mm of front length (24%).</text>')
o.append('</svg>')
open('docs/diagrams/vision-k4/vision-k4.svg','w').write('\n'.join(o))
