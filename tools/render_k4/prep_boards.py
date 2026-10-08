"""Copy routed_P/M to a work dir (originals untouched): black mask + ENIG stackup, real model paths, BM28/mic/switch models.
Usage: python3 tools/render_k4/prep_boards.py WORKDIR"""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
W = Path(sys.argv[1]); W.mkdir(parents=True, exist_ok=True)
MD = ROOT / "hw/lib/k4_render"
def layer(n, t, name, typ, extra=""):
    return f'(layer "{name}" (type "{typ}") (thickness {t}){extra})'
st = ['(stackup', '(layer "F.SilkS" (type "Top Silk Screen") (color "White"))',
      '(layer "F.Paste" (type "Top Solder Paste"))',
      '(layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.02))',
      '(layer "F.Cu" (type "copper") (thickness 0.0152))']
cus = ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]
for i, c in enumerate(cus):
    st.append(f'(layer "dielectric {i+1}" (type "prepreg") (thickness 0.134) (material "FR4") (epsilon_r 4.3) (loss_tangent 0.02))')
    st.append(f'(layer "{c}" (type "copper") (thickness 0.0152))')
st.append('(layer "dielectric 5" (type "prepreg") (thickness 0.134) (material "FR4") (epsilon_r 4.3) (loss_tangent 0.02))')
st += ['(layer "B.Cu" (type "copper") (thickness 0.0152))',
       '(layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.02))',
       '(layer "B.Paste" (type "Bottom Solder Paste"))',
       '(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))',
       '(copper_finish "ENIG")', '(dielectric_constraints no)', ')']
SW = {"SPH0641LU4H-1_placeholder.step": "SPH0641_mic.step", "KMT022NGJLHS_placeholder.step": "KMT022_switch.step"}
for n in "PM":
    t = (ROOT / f"hw/pod/k4/routed_{n}.kicad_pcb").read_text()
    t = re.sub(r"\(setup\b", "(setup\n" + " ".join(st), t, count=1)
    t = t.replace('"hw/lib/', f'"{ROOT}/hw/lib/')
    t = re.sub(r'(\(property "(?:Reference|Value)" "[^"]*"\s*\(at [^)]*\)\s*\(layer "[^"]*"\))', r'\1 (hide yes)', t)
    t = t.replace('EP5.6x5.6mm.step', 'EP5.15x5.15mm.step')   # stock KiCad has no EP5.6 model; same 7x7 / 0.5 mm body
    t = re.sub(r'"[^"]*Crystal_SMD_2012-2Pin_2.0x1.2mm.step"', f'"{MD}/Crystal_2012.step"', t)   # not in the KiCad install
    for a, b in SW.items():
        t = re.sub(r'"[^"]*' + re.escape(a) + '"', f'"{MD}/{b}"', t)
    ref, mdl = ("J21", "BM28_plug") if n == "P" else ("J20", "BM28_receptacle")
    # insert a model block before the closing paren of the connector footprint
    i = t.index(f'(property "Reference" "{ref}"'); j = t.rfind("(footprint", 0, i)
    depth = 0; k = j
    while True:
        c = t[k]; depth += (c == "(") - (c == ")")
        if depth == 0: break
        k += 1
    blk = f'\n\t\t(model "{MD}/{mdl}.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n\t'
    t = t[:k] + blk + t[k:]
    (W / f"{n}.kicad_pcb").write_text(t)
print("ok")
