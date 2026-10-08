"""Simple STEP models (with colours) for the K4 photoreal render: BM28 plug/receptacle (Hirose catalogue b18670c dims:
30 pos, 0.35 pitch, 0.6 mated height), Knowles SPH0641 mic can, KMT022 tact switch. Run: python3 tools/render_k4/make_models.py"""
from pathlib import Path
from build123d import Box, Cylinder, Pos, Color, Compound, export_step, Location
OUT = Path(__file__).resolve().parents[2] / "hw/lib/k4_render"
OUT.mkdir(parents=True, exist_ok=True)

def col(shape, rgb, label):
    shape.color = Color(*rgb); shape.label = label; return shape

LCP = (0.12, 0.12, 0.13); GOLD = (0.85, 0.65, 0.2); STEEL = (0.75, 0.76, 0.78)
def contacts(n, y, z0, h, length_x=0.12):
    return [Pos(-2.45 + i * 0.35, y, z0 + h / 2) * Box(0.12, 0.18, h) for i in range(15)]

def receptacle():   # M-side, 0.35 high wall frame with a slot, gold contacts in the slot, steel end tabs
    L, W, H = 6.1, 1.5, 0.35
    body = Pos(0, 0, H / 2) * Box(L, W, H) - Pos(0, 0, H / 2 + 0.1) * Box(5.5, 0.8, H)
    parts = [col(body, (0.10, 0.10, 0.11), "lcp")]
    for y in (-0.3, 0.3):
        for c in contacts(15, y, 0.0, 0.3):
            parts.append(col(c, GOLD, "au"))
    for sx in (-1, 1):
        parts.append(col(Pos(sx * 2.85, 0, 0.14) * Box(0.5, 1.2, 0.28), STEEL, "tab"))
    return Compound(children=parts)

def plug():         # P-side, 0.25 high base + 0.3 blade that enters the receptacle slot
    L, W, H = 6.1, 1.5, 0.25
    parts = [col(Pos(0, 0, H / 2) * Box(L, W, H), (0.10, 0.10, 0.11), "lcp"),
             col(Pos(0, 0, H + 0.15) * Box(5.4, 0.62, 0.3), (0.13, 0.13, 0.14), "blade")]
    for y in (-0.31, 0.31):
        for c in contacts(15, y, H, 0.3):
            parts.append(col(Pos(0, 0, 0.0) * c, GOLD, "au"))
    for sx in (-1, 1):
        parts.append(col(Pos(sx * 2.85, 0, 0.12) * Box(0.5, 1.2, 0.24), STEEL, "tab"))
    return Compound(children=parts)

def mic():          # Knowles SPH0641LU4H-1 3.5 x 2.65 x 0.98 + port on the board side; metal can, gold pads
    can = Pos(0, 0, 0.1 + 0.44) * Box(3.5, 2.65, 0.88)
    parts = [col(can, (0.78, 0.79, 0.80), "can"), col(Pos(0, 0, 0.05) * Box(3.3, 2.45, 0.1), (0.15, 0.4, 0.2), "substrate")]
    parts.append(col(Pos(0.2, 0, 0.98) * Cylinder(0.12, 0.02), (0.2, 0.2, 0.2), "mark"))
    return Compound(children=parts)

def switch():       # KMT022NGJLHS tact switch 3.0 x 2.6, 0.65 high, SMD, mounted on the belly (flipped)
    parts = [col(Pos(0, 0, 0.18) * Box(3.0, 2.6, 0.36), STEEL, "frame"),
             col(Pos(0, 0, 0.36 + 0.14) * Box(2.2, 1.9, 0.28), (0.12, 0.12, 0.12), "cap"),
             col(Pos(0, 0, 0.5 + 0.06) * Cylinder(0.7, 0.12), (0.25, 0.25, 0.27), "btn")]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(col(Pos(sx * 1.45, sy * 0.95, 0.06) * Box(0.4, 0.5, 0.12), GOLD, "term"))
    return Compound(children=parts)

def crystal():      # 2.0 x 1.2 x 0.6 SMD crystal (32.768 kHz class): ceramic body, metal lid, gold end terminations
    parts = [col(Pos(0, 0, 0.25) * Box(2.0, 1.2, 0.5), (0.55, 0.52, 0.45), "xt_body"), col(Pos(0, 0, 0.55) * Box(1.5, 0.9, 0.1), STEEL, "frame")]
    for sx in (-1, 1):
        parts.append(col(Pos(sx * 0.9, 0, 0.25) * Box(0.25, 1.2, 0.5), GOLD, "term"))
    return Compound(children=parts)

for n, f in (("Crystal_2012", crystal), ("BM28_receptacle", receptacle), ("BM28_plug", plug), ("SPH0641_mic", mic), ("KMT022_switch", switch)):
    export_step(f(), str(OUT / f"{n}.step"))
    print(n)
