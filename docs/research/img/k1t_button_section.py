"""Section render of k1t button options A (dome) and C (proud skin). Dark, true-black. Numbers: sim/out/mech/button_concepts.json."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
fig, ax = plt.subplots(1, 2, figsize=(11, 5), facecolor="black")
def base(a, title):
    a.set_facecolor("black"); a.set_xlim(-4, 4); a.set_ylim(-1.9, 1.5); a.set_aspect("equal"); a.axis("off")
    a.set_title(title, color="#e6e6e6", fontsize=10)
    a.add_patch(Rectangle((-4, -0.8), 8, 0.8, fc="#2a6f4a", ec="none"))          # board 0.8 (F face at y 0)
    a.text(-3.9, -0.55, "PCB (F face = 0)", color="#cfe", fontsize=7)
def lid(a, relief):
    a.add_patch(Rectangle((-4, 0.30), 8, 0.6, fc="#555", ec="none"))               # lid 0.6, inner face 0.30
    if relief: a.add_patch(Rectangle((-2.3, 0.30), 4.6, 0.10, fc="black"))        # 0.10 relief
    a.add_patch(Rectangle((-1.3, 0.30), 2.6, 0.6, fc="black"))                      # bore D2.6
    a.text(-3.9, 0.6, "lid 0.6", color="#ddd", fontsize=7)
# A
a = ax[0]; base(a, "A  dome HYP 600-415S: flush, T unchanged")
lid(a, True)
a.add_patch(Rectangle((-2.0, 0), 4.0, 0.075, fc="#999", ec="none"))              # PSA overlay
a.add_patch(Polygon([(-2, 0.075), (-1.3, 0.255), (0, 0.275), (1.3, 0.255), (2, 0.075)], closed=False, fc="none", ec="#ffd24a", lw=1.6))
a.add_patch(Rectangle((-1.15, 0.275), 2.3, 0.35, fc="#e08a3c", ec="none"))       # puck (schematic)
a.add_patch(Rectangle((-2.3, 0.65), 4.6, 0.25, fc="#6ab7ff", ec="none"))          # skin 0.25 in recess
a.annotate("dome top +0.275 (0.20 + 0.075 PSA)\nbelow lid inner (+0.30): 0.025", (1.3, 0.28), (1.6, 0.8), color="#ffd24a", fontsize=7, arrowprops=dict(arrowstyle="-", color="#ffd24a"))
a.text(-3.9, -1.0, "frees 0.375 vs KMT022 (top +0.65)\ncap clear at bore edge 0.09 worst\nforce 1.47-2.45 N, ~0.15-0.20 travel", color="#ddd", fontsize=7.5, va="top")
# C
a = ax[1]; base(a, "C  KMT022 kept, skin 0.20 proud: bump on the lid")
lid(a, False)
a.add_patch(Rectangle((-1.5, 0), 3.0, 0.65, fc="#bbb", ec="none")); a.text(-1.2, 0.2, "KMT022", color="k", fontsize=7)
a.add_patch(Rectangle((-2.3, 0.90), 4.6, 0.20, fc="#6ab7ff", ec="none"))          # proud skin (0.25 total, 0.05 in recess)
a.add_patch(Rectangle((-2.3, 0.85), 4.6, 0.05, fc="#6ab7ff", ec="none"))
a.add_patch(Rectangle((-1.15, 0.65), 2.3, 0.20, fc="#e08a3c", ec="none"))         # nub dot, selective fit
a.text(-3.9, -1.0, "skin underside gap to switch 0.20 nominal; worst -0.018 (fit by 0.05 dot kit)\nlocal T +0.20 over D4.6; force 1.6 N + skin; travel 0.15 +-0.1", color="#ddd", fontsize=7.5, va="top")
fig.savefig("docs/research/img/k1t_button_section.png", dpi=170, facecolor="black"); 
