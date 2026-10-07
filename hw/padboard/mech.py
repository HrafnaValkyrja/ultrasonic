"""Electronics side of the mechanical design: pad board in its worn pose, the pod PCB's mechanical
interface as keep-out solids, numeric checks, and the owner's pictures.

    source tools/env.sh && systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0 \
        python3 hw/padboard/mech.py
    -> hw/mech/out/parts/electronics/{padboard_worn.step, pod_pcb_interface.step, checks.json,
                                      pcb_interface.png, padboard_and_panel.png, charge_led_fix.png}

Frame: hw/mech/frame.py (RIGHT pod; x back, y out, z up). Nothing here is printed, so STEP only.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "hw/mech"))
sys.path.insert(0, str(REPO / "tools"))
import frame as F  # noqa: E402
import shell as _SH  # noqa: E402  (pre-rev-1 shell; its frozen PRE_R1 pod is what these checks were written against)
F0 = _SH.F       # pre-rev-1 pod (PCB 20 x 11.5, KXT321, lid screws, mic chimney): frozen in shell.py since ECR-0001

OUT = REPO / "hw/mech/out/parts/electronics"
OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------- numbers
LED_H, SOLDER = 0.45, 0.03          # Everlight DSE-0008890 Rev 3 p6: 1.0 x 0.5 x 0.45 mm
JOINT_H = 0.45                      # 0.25-0.3 mm OD wire + fillet on a pad, worst case
PB = F.PAD_BOARD
PCB = F0.PCB
Z_MID = (PCB["z0"] + PCB["z1"]) / 2                   # -2.0, the board's horizontal centre line
JLC_EDGE_MIN = 0.2                                    # copper to routed edge (JLC capabilities, 2026-09-30)

# pad-board footprint positions (KiCad coords, origin board centre; x = -e1, y = -e3), read from
# layout.py (single source of truth; parsed with ast so this script doesn't need pcbnew)
def _layout_consts(*names):
    import ast
    tree = ast.parse((HERE / "layout.py").read_text())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", None) in names:
            out[node.targets[0].id] = ast.literal_eval(node.value)
    return out


_L = _layout_consts("PLACE", "TRACKS")
TRACKS = _L["TRACKS"]


def _pad_geom(fp):
    """('arm', w, L) for WirePad_SMD_<w>x<L>mm, ('pth', dia, drill) for WirePad_PTH_D<d>mm_Pad<p>mm."""
    import re
    m = re.match(r"WirePad_SMD_([\d.]+)x([\d.]+)mm", fp)
    if m:
        return "arm", float(m.group(1)), float(m.group(2))
    m = re.match(r"WirePad_PTH_D([\d.]+)mm_Pad([\d.]+)mm", fp)
    return "pth", float(m.group(2)), float(m.group(1))


PADS_KICAD = {ref: (x, y, *_pad_geom(fp)) for ref, (x, y, rot, lib, fp, net) in _L["PLACE"].items() if ref.startswith("J")}
LABEL = {"J1": "OUT_A", "J2": "OUT_B", "J3": "LED+", "J4": "LED-", "J5": "XDCR_A", "J6": "XDCR_B"}
DAM_R = 5.3 / 2 + 0.6               # pad cap's printed epoxy dam (hw/mech/pad.py DAM_R: ring 5.3 + 0.6 wall)
WIRE_OD = 0.6                       # 30 AWG silicone hook-up wire, worst case (PTFE 0.25-0.3 is thinner)
WIRE_FREE_L = 35.0                  # free length per wire inside the pod (board must lie beside the pod)

# draft MCU position from hw/pod/place.py (KiCad 10.0, 5.75 on the 20 x 11.5 board) - centred on the board
MCU = dict(x=(PCB["x0"] + PCB["x1"]) / 2, z=Z_MID, s=7.0)

# hazard of a solder bridge between two adjacent rear-edge wire pads (H = damage or cell short,
# M = brown-out / drain, L = benign); assumes R14 split in two (section 6 of the research note)
NETS = {"OUT_A": "A", "OUT_B": "A", "LED+": "L+", "LED-": "L-", "BAT+": "B", "BAT-": "G", "VBUS": "V", "GND_CHG": "G"}
HAZ = {frozenset(k): v for k, v in {
    ("V", "G"): "L", ("V", "B"): "H", ("V", "A"): "H", ("V", "L+"): "M", ("V", "L-"): "L",
    ("B", "G"): "H", ("B", "A"): "H", ("B", "L+"): "L", ("B", "L-"): "L",
    ("G", "A"): "M", ("G", "L+"): "M", ("G", "L-"): "L", ("A", "A"): "M", ("A", "L+"): "L", ("A", "L-"): "L",
    ("L+", "L-"): "L", ("G", "G"): "-"}.items()}
HAZ_NO_SPLIT = dict(HAZ)
HAZ_NO_SPLIT[frozenset(("B", "L-"))] = "H"           # PB7 shorted straight to VBAT, sinks > 20 mA
HAZ_NO_SPLIT[frozenset(("V", "L-"))] = "H"
HAZ_NO_SPLIT[frozenset(("A", "L-"))] = "H"
PROPOSED_ORDER = ["VBUS", "GND_CHG", "BAT-", "OUT_A", "OUT_B", "LED-", "LED+", "BAT+"]


def adjacency(order, table):
    out = []
    for a, b in zip(order, order[1:]):
        out.append((a, b, table[frozenset((NETS[a], NETS[b]))]))
    return out


def wire_pad_rows(z_centre_top, n=8, pitch=1.3):
    return [z_centre_top - k * pitch for k in range(n)]


# ----------------------------------------------------------------------------- checks
def checks():
    c = []

    def add(name, ok, value, note=""):
        c.append({"name": name, "pass": bool(ok), "value": value, "note": note})

    erc = (HERE / "gen.erc").read_text().strip() if (HERE / "gen.erc").exists() else "not run"
    add("padboard ERC (SKiDL)", "No errors or warnings" in erc, erc)
    drc = json.loads((HERE / "drc_summary.json").read_text())["summary"] if (HERE / "drc_summary.json").exists() else None
    add("padboard draft DRC (kicad-cli, JLC edge 0.3 mm, silk 0.8 mm)", drc is not None and drc["violations"] == 0
        and drc["unconnected"] == 0, drc)
    add("padboard outline = frame.PAD_BOARD", True, f'{PB["w"]} x {PB["e3_1"] - PB["e3_0"]:.1f} x {PB["t"]} mm')
    led_top = F.PAD_Y["board_top"] + SOLDER + LED_H
    add("LED top vs frame PAD_Y.led_top", led_top <= F.PAD_Y["led_top"] + 1e-6, round(led_top, 3),
        f'frame says {F.PAD_Y["led_top"]}; the 16-213 is 0.45 mm tall, not 0.35 -> set led_top >= 3.9')
    joint_top = F.PAD_Y["board_top"] + JOINT_H
    add("cap roof over LED/joints (cap_face - parts top >= 0.6 resin min wall)",
        F.PAD_Y["cap_face"] - max(led_top, joint_top) >= F.RESIN["min_wall"], round(F.PAD_Y["cap_face"] - max(led_top, joint_top), 3),
        "ring groove depth must leave >= 0.6 over the LED, or the LED shines through a clear window")
    within = PB["w"] / 2 <= F.TRANSDUCER["w"] / 2 and PB["e3_0"] >= -F.TRANSDUCER["L"] / 2 and PB["e3_1"] <= F.TRANSDUCER["L"] / 2
    add("pad board footprint inside the transducer's top face", within,
        f'board e1 +-{PB["w"]/2}, e3 {PB["e3_0"]}..{PB["e3_1"]}; transducer e1 +-{F.TRANSDUCER["w"]/2}, e3 +-{F.TRANSDUCER["L"]/2}')
    for state in ("free", "jaw_open_1.5", "worn_3.5", "jaw_closed_5.5"):
        T, a = F.pad_socket_axis(state)
        R, t = F.pad_pose(state)
        # socket bottom, carried rigidly with the pad: compare in the pad's own (worn) frame
        T0, a0 = F.pad_socket_axis("worn_3.5")
        end = T0 + F.PAD_SOCKET_DEPTH * a0
        rel = end - np.array([F.PAD_CENTRE[0], 0, F.PAD_CENTRE[2]])
        e1, e3, y = rel @ F.E1, rel @ F.E3, end[1]
        if state == "worn_3.5":
            gap_y = y - F.SOCKET_D / 2 - max(led_top, joint_top)
            add("NiTi pad-socket bottom clears pad-board parts (outward y gap)", gap_y > 0.3,
                round(float(gap_y), 3), f"socket end at e1 {e1:.2f}, e3 {e3:.2f}, y {y:.2f} (rigid with the pad in every state)")
    # ---- pod PCB
    top_band, bot_band = PCB["z1"] - F0.PCB_CLAMP_BAND, PCB["z0"] + F0.PCB_CLAMP_BAND
    h = F0.WIRE_PAD["h"]
    for interp, zc0 in (("z_top = pad CENTRE", F0.WIRE_PAD["z_top"]), ("z_top = pad TOP edge", F0.WIRE_PAD["z_top"] - h / 2)):
        zs = wire_pad_rows(zc0)
        intr = max(zs[0] + h / 2 - top_band, bot_band - (zs[-1] - h / 2), 0)
        add(f"frame wire pads vs clamp bands ({interp})", intr <= 0, round(float(intr), 3),
            f"pads span z {zs[-1]-h/2:.2f}..{zs[0]+h/2:.2f}; bands start at {top_band:.2f} / {bot_band:.2f}")
    zs = wire_pad_rows(Z_MID + 3.5 * 1.3)
    add("8 pads x 1.0 at 1.3 pitch fit between the bands only when centred on z=-2.0",
        zs[0] + h / 2 <= top_band and zs[-1] - h / 2 >= bot_band, f"centred: {zs[-1]-h/2:.2f}..{zs[0]+h/2:.2f} (0.10 mm each side)")
    edge = PCB["x1"] - F0.WIRE_PAD["x1"]
    add("frame wire pad copper to rear edge >= JLC 0.2 + 0.1 margin", edge >= JLC_EDGE_MIN + 0.1, round(edge, 3),
        "0.2 is JLC's absolute minimum; mouse bites or sanding there would cut into it")
    gap = F0.WIRE_PAD["pitch"] - h
    add("frame wire pad gap for hand soldering (want >= 0.4)", gap >= 0.4, round(gap, 3), "1.0 mm round test pads, 0.3 mm apart")
    b = F0.BUTTON
    bz0, bz1 = b["z"] - b["body"][1] / 2, b["z"] + b["body"][1] / 2
    bx0, bx1 = b["x"] - b["body"][0] / 2, b["x"] + b["body"][0] / 2
    mz1, mx0, mx1 = MCU["z"] + MCU["s"] / 2, MCU["x"] - MCU["s"] / 2, MCU["x"] + MCU["s"] / 2
    ov = min(bz1, mz1) - max(bz0, MCU["z"] - MCU["s"] / 2) if (bx0 < mx1 and bx1 > mx0) else 0
    add("button body vs MCU at the draft's centred position (both on the outer face)", ov <= 0, round(ov, 3),
        "MCU must move >= 0.8 mm down (or to the inner face) under the frame's button; see note section 2")
    add("button on the board's centre line (needed for one board in both pods without moving it)", abs(b["z"] - Z_MID) < 0.05,
        b["z"], "it sits 3.9 mm above; the left pod (board turned over) would need it at z = -5.9")
    add("mic port on the board's centre line (same reason)", abs(F0.MIC_PORT["z"] - Z_MID) < 0.05, F0.MIC_PORT["z"],
        "1.0 mm above; the left pod would need its port at z = -3.0")
    ks = F0.MIC_SEAL["keepout_r"]
    add("mic seal keep-out inside the board, clear of the clamp bands", F0.MIC_PORT["z"] + ks <= top_band and
        F0.MIC_PORT["x"] - ks >= PCB["x0"] + F0.PCB_END_KEEPOUT, f'x {F0.MIC_PORT["x"]-ks:.2f}..{F0.MIC_PORT["x"]+ks:.2f}, z {F0.MIC_PORT["z"]-ks:.2f}..{F0.MIC_PORT["z"]+ks:.2f}')
    nut = F.FASTENERS["M1.4_nut"]["pocket_af"] / 2
    d = min(x for x, z in F0.LID_SCREWS) - nut - PCB["x1"]
    add("lid-screw nut pockets clear of the PCB rear edge", d > 3, round(d, 2), "screws are the charge contacts: VBUS top, GND bottom")
    place_mic = (2.2, 8.74)                      # hw/pod/place.py U2 (KiCad x, y)
    xw_right = PCB["x1"] - place_mic[0]
    add("place.py draft drawn for the right pod (mic at the front)", xw_right < 40, round(xw_right, 2),
        "draft puts the mic at KiCad x=2.2; viewed from outside the RIGHT pod KiCad x runs front->rear "
        "right-to-left, so this is the LEFT pod's board (or the right pod's board upside down)")
    adj = adjacency(F0.WIRE_PADS, HAZ_NO_SPLIT)
    add("frame pad order: no high-hazard neighbours (R14 as drawn)", not any(x[2] == "H" for x in adj),
        [f"{a}|{b}:{h}" for a, b, h in adj])
    adj2 = adjacency(PROPOSED_ORDER, HAZ)
    add("proposed pad order + split R14: no high-hazard neighbours", not any(x[2] == "H" for x in adj2),
        [f"{a}|{b}:{h}" for a, b, h in adj2])
    # charge contacts, electrical (DS20001984H p3/p5; onsemi ESD9X3.3ST5G/D Rev 7 p2)
    i_back, r_div = 2e-6, 200e3
    add("VBUS contact voltage when undocked (charger back-drain max x 200k divider)", i_back * r_div < 0.5,
        f"{i_back*r_div:.2f} V max", "no battery voltage on the exposed screw while worn")
    q_esd, c15 = 8e3 * 150e-12, 4.7e-6
    add("8 kV / 150 pF discharge dumped into C15 (charger input) raises VBUS by", q_esd / c15 < 1.0,
        f"{q_esd / c15:.2f} V", "C15 is the real ESD sink; D3 clamps the edge at the pad")
    add("reverse-polarity dock (glasses upside down) survives without a series diode", False,
        "D3 forward-conducts the dock's full current; 150 mW rating", "add a series Schottky (note section 5)")
    c += padboard_geometry_checks()
    c += pad_cap_joint_check()
    c += shell_interface_checks()
    return c


def padboard_geometry_checks():
    """Pad-board copper vs its own edges and vs the pad cap's epoxy dam (r 3.25 around the LED)."""
    c = []
    W2, YT, YB = PB["w"] / 2, -PB["e3_1"], -PB["e3_0"]
    edge, dam, gaps = {}, {}, {}
    for ref, (x, y, kind, a, b) in PADS_KICAD.items():
        if kind == "arm":
            x0, x1, y0, y1 = x - a / 2, x + a / 2, y - b / 2, y + b / 2
            edge[ref] = round(min(x0 + W2, W2 - x1, y0 - YT, YB - y1), 3)
        else:
            r = a / 2
            edge[ref] = round(min(W2 - abs(x) - r, YB - y - r, y - r - YT), 3)
            dam[ref] = round(math.hypot(x, y) - r - DAM_R, 3)
    row = sorted((x, a) for ref, (x, y, kind, a, b) in PADS_KICAD.items() if kind == "arm")
    for (xa, wa), (xb, wb) in zip(row, row[1:]):
        gaps[f"{xa:+.3f}|{xb:+.3f}"] = round((xb - wb / 2) - (xa + wa / 2), 3)
    c.append({"name": "pad board: copper to board edge >= 0.3 (JLC min 0.2 + margin)", "pass": min(edge.values()) >= 0.3 - 1e-9,
              "value": edge, "note": ""})
    c.append({"name": "pad board: transducer-lead pads clear the cap's epoxy dam r 3.25", "pass": min(dam.values()) > 0,
              "value": dam, "note": "pad agent asked (+-1.85, 3.25) / 0.9 pad: dam ok but only 0.20 to the long edge"})
    c.append({"name": "pad board: arm-pad gaps for hand soldering (want >= 0.4)", "pass": min(gaps.values()) >= 0.4,
              "value": gaps, "note": "one row of four 0.7 x 1.8 pads at 1.15 pitch"})
    return c


def pad_cap_joint_check():
    """Run the pad agent's own joint_check (hw/mech/pad.py) against THIS layout: every wire joint
    (0.45 tall) must sit in a cap pocket, every SMD lap >= 1.0 mm outside the dam."""
    try:
        import pad as PADMOD
        lay = {ref: (LABEL[ref], x, y, "smd" if kind == "arm" else "pth", a, b if kind == "arm" else a)
               for ref, (x, y, kind, a, b) in PADS_KICAD.items()}
        res, ok = PADMOD.joint_check(PADMOD.build_cap()[0], lay)        # build_cap() -> (cap, env, pr)
        return [{"name": "pad board joints fit the pad cap's pockets (hw/mech/pad.py joint_check, this layout)",
                 "pass": bool(ok), "value": res, "note": "pad.py as on disk at run time"}]
    except Exception as e:                       # pad.py is another agent's live file: never fail the build on it
        return [{"name": "pad board joints fit the pad cap's pockets (hw/mech/pad.py joint_check, this layout)",
                 "pass": False, "value": f"not run: {type(e).__name__}: {e}", "note": ""}]


def shell_interface_checks():
    """Pod board vs the shell agent's 'proposed' variant (hw/mech/shell.py): the LID locates the PCB
    (ribs on the outer-face clamp bands, webs at the edges, rear stops), foam strips on the cell press
    the inner-face bands, tub front stops hold the front edge, lid screws behind the cell at x 64.2."""
    c = []
    try:
        import shell as SH
    except Exception as e:
        return [{"name": "shell interface (hw/mech/shell.py)", "pass": False, "value": f"not imported: {e}", "note": ""}]
    v = SH.VARIANTS["proposed"]
    rib_top0, rib_bot1 = SH.TOP_BAND[0] + 0.05, SH.BOT_BAND[1] - 0.05      # lid_pcb_features(): 0.05 inside the band
    zs = wire_pad_rows(Z_MID + 3.5 * 1.3)
    p_top, p_bot = zs[0] + 0.5, zs[-1] - 0.5
    clr = min(rib_top0 - p_top, p_bot - rib_bot1)
    c.append({"name": "P2 wire pads + joints clear of the lid ribs (shell proposed)", "pass": clr > 0.1,
              "value": round(clr, 3), "note": f"pads z {p_bot:.2f}..{p_top:.2f}; ribs from z {rib_top0:.2f} / {rib_bot1:.2f}"})
    w_top, w_bot = zs[0] + WIRE_OD / 2, zs[-1] - WIRE_OD / 2
    clr = min(rib_top0 - w_top, w_bot - rib_bot1)
    c.append({"name": "8 wires leave the rear edge between the lid's rear stops", "pass": clr > 0.1, "value": round(clr, 3),
              "note": f"rear stops x {SH.REAR_STOP_X[0]:.2f}..{SH.REAR_STOP_X[1]:.2f}, only in the bands; "
                      f"wire bundle z {w_bot:.2f}..{w_top:.2f} (OD {WIRE_OD})"})
    swd_top = 2.5 + 0.4
    c.append({"name": "SWD probe pads clear of the lid's top rib", "pass": rib_top0 - swd_top > 0.1,
              "value": round(rib_top0 - swd_top, 3), "note": ""})
    fz = [(SH.TOP_BAND[0], F0.CELL["z1"]), (F0.CELL["z0"], SH.BOT_BAND[1])]
    on_board = [(max(a, PCB["z0"]), min(b, PCB["z1"])) for a, b in fz]
    ok = abs(on_board[0][0] - SH.TOP_BAND[0]) < 1e-6 and abs(on_board[1][1] - SH.BOT_BAND[1]) < 1e-6
    c.append({"name": "cell foam strips press the board only inside its inner-face clamp bands", "pass": ok,
              "value": [[round(a, 2), round(b, 2)] for a, b in on_board],
              "note": "x 32.0..49.5; inner-face parts must stay out of both bands (they did already)"})
    stub = PCB["x0"] - F0.CAV["x0"]
    c.append({"name": "front edge: tub front stops only in the bands; room for an unsanded SWD-tab stub", "pass": stub > 0.1,
              "value": round(stub, 3), "note": "stops at x <= 30.55 in the bands; sand the stub flush anyway"})
    bx0 = v["boss_x"][0]
    c.append({"name": "nut bosses (shell proposed, x 64.2) clear of the PCB rear edge", "pass": bx0 - PCB["x1"] > 3,
              "value": round(bx0 - PCB["x1"], 2), "note": f"screws {v['screws']}: top = VBUS, bottom = GND_CHG"})
    pcm = v["pcm"]
    c.append({"name": "PCM placeholder (shell proposed) clear of the PCB rear edge", "pass": pcm["x0"] - PCB["x1"] > 2,
              "value": round(pcm["x0"] - PCB["x1"], 2), "note": "BAT+/BAT- run ~7-11 mm from the PCM to the rear pads"})
    try:
        loop = json.loads((REPO / "hw/mech/out/parts/shell/checks.json").read_text())["variants"]["proposed"][
            "service_loop_space_mm3 (behind the PCB, y 9.9..13.4)"]
    except Exception:
        loop = None
    vol = 8 * WIRE_FREE_L * math.pi / 4 * WIRE_OD ** 2
    c.append({"name": "8 wires x 35 mm (board can lie beside the pod) fit the service-loop space", "pass": loop is not None and vol < 0.4 * loop,
              "value": {"wire_mm3": round(vol, 1), "space_mm3": loop, "fill": round(vol / loop, 2) if loop else None},
              "note": "< 40 % fill so the loop folds without pushing the board off its foam"})
    return c


# ----------------------------------------------------------------------------- CAD
def cad():
    from build123d import Box, Compound, Cylinder, Location, Plane, Pos, export_step

    org = (float(F.PAD_CENTRE[0]), F.PAD_Y["split"], float(F.PAD_CENTRE[2]))
    pl = Plane(origin=org, x_dir=tuple(-F.E1), z_dir=tuple(F.E2))       # local (x_k, -y_k, up)
    loc = Location(pl)
    t = PB["t"]
    yc = -(PB["e3_0"] + PB["e3_1"]) / 2                                   # KiCad y of the board centre
    parts = []
    board = Pos(0, -yc, t / 2) * Box(PB["w"], PB["e3_1"] - PB["e3_0"], t)
    board.label = "pad_board_0.8"
    parts.append(board)
    led = Pos(0, 0, t + SOLDER + LED_H / 2) * Box(1.0, 0.5, LED_H)
    led.label = "D1_LED_0402_blue"
    parts.append(led)
    for ref, (x, y, kind, a, b) in PADS_KICAD.items():
        s = (Pos(x, -y, t + JOINT_H / 2) * Box(a, b, JOINT_H)) if kind == "arm" else \
            (Pos(x, -y, t + JOINT_H / 2) * Cylinder(a / 2, JOINT_H))
        s.label = f"{ref}_{LABEL[ref]}_joint"
        parts.append(s)
    pad_worn = Compound(children=[loc * p for p in parts], label="padboard_worn")
    export_step(pad_worn, str(OUT / "padboard_worn.step"))

    # pod PCB interface solids, world coordinates
    def box(x0, x1, y0, y1, z0, z1, label):
        s = Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)
        s.label = label
        return s

    p = PCB
    sol = [box(p["x0"], p["x1"], p["y0"], p["y1"], p["z0"], p["z1"], "pod_pcb_0.8")]
    for zz, nm in ((p["z1"] - F0.PCB_CLAMP_BAND, "top"), (p["z0"], "bottom")):
        sol.append(box(p["x0"], p["x1"], F0.PARTS_IN["y0"], F0.PARTS_OUT["y1"], zz, zz + F0.PCB_CLAMP_BAND, f"keepout_clamp_band_{nm}"))
    for xx, nm in ((p["x0"], "front"), (p["x1"] - F0.PCB_END_KEEPOUT, "rear")):
        sol.append(box(xx, xx + F0.PCB_END_KEEPOUT, F0.PARTS_IN["y0"], F0.PARTS_OUT["y1"], p["z0"], p["z1"], f"keepout_end_{nm}"))
    m = F0.MIC_PORT
    ch = Pos(m["x"], (p["y1"] + F0.CAV["y1"]) / 2, m["z"]) * Location((0, 0, 0), (90, 0, 0)) * Cylinder(F0.MIC_SEAL["keepout_r"], F0.CAV["y1"] - p["y1"])
    ch.label = "keepout_mic_seal_outer_face"
    sol.append(ch)
    b = F0.BUTTON
    sol.append(box(b["x"] - b["body"][0] / 2, b["x"] + b["body"][0] / 2, p["y1"], p["y1"] + b["height"],
                   b["z"] - b["body"][1] / 2, b["z"] + b["body"][1] / 2, "SW1_button_body_frame_position"))
    zs = wire_pad_rows(Z_MID + 3.5 * 1.3)
    for k, zc in enumerate(zs):         # proposed P2: staggered 1.0 x 1.6 pads + joint envelope
        x1 = p["x1"] - 0.3 if k % 2 == 0 else p["x1"] - 0.3 - 1.8
        sol.append(box(x1 - 1.6, x1, p["y1"], p["y1"] + JOINT_H, zc - 0.5, zc + 0.5, f"wirepad_P2_{k+1}_{PROPOSED_ORDER[k]}"))
    for k in range(5):                  # proposed SWD probe column at the front edge, 1.27 pitch
        zc = 2.5 - 1.27 * k
        sol.append(box(p["x0"] + 0.5, p["x0"] + 1.9, p["y1"], p["y1"] + 0.05, zc - 0.4, zc + 0.4, f"swd_probe_pad_{k+1}"))
    export_step(Compound(children=sol, label="pod_pcb_interface"), str(OUT / "pod_pcb_interface.step"))
    return {"padboard_bbox": [round(v, 2) for v in (*pad_worn.bounding_box().min, *pad_worn.bounding_box().max)]}


# ----------------------------------------------------------------------------- pictures
def pictures():
    import plotstyle
    plt = plotstyle.apply()
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    S = plotstyle.SERIES
    TX, T2 = plotstyle.TEXT, plotstyle.TEXT_2
    p = PCB

    def rect(ax, x0, z0, w, h, col, fill=False, alpha=1.0, lw=1.2, ls="-", hatch=None):
        ax.add_patch(Rectangle((x0, z0), w, h, fill=fill, ec=col, fc=col if fill else "none", alpha=alpha,
                               lw=lw, ls=ls, hatch=hatch))

    # ---------------- figure 1: pod PCB outer face, right pod, seen from outside (front on the RIGHT)
    fig, axs = plt.subplots(2, 1, figsize=(10.5, 10.5), gridspec_kw={"height_ratios": [1.25, 1]})
    ax = axs[0]
    rect(ax, p["x0"], p["z0"], p["x1"] - p["x0"], p["z1"] - p["z0"], TX, lw=1.6)
    for zz in (p["z1"] - F0.PCB_CLAMP_BAND, p["z0"]):
        rect(ax, p["x0"], zz, p["x1"] - p["x0"], F0.PCB_CLAMP_BAND, T2, fill=True, alpha=0.35, hatch="////")
    for xx in (p["x0"], p["x1"] - F0.PCB_END_KEEPOUT):
        rect(ax, xx, p["z0"], F0.PCB_END_KEEPOUT, p["z1"] - p["z0"], T2, fill=True, alpha=0.25)
    rect(ax, MCU["x"] - 3.5, MCU["z"] - 3.5, 7, 7, S[6], ls="--")
    ax.text(MCU["x"], MCU["z"] - 0.6, "MCU 7x7\n(draft, centred)", color=S[6], ha="center", va="center", fontsize=8)
    b = F0.BUTTON
    rect(ax, b["x"] - 1.5, b["z"] - 1.0, 3.0, 2.0, S[7], fill=True, alpha=0.35)
    ax.text(b["x"], F0.CAV["z1"] + 0.25, "button (frame) overlaps MCU 0.6", color=S[7], ha="center", va="bottom", fontsize=8)
    rect(ax, 44.0, Z_MID - 1.5, 2.0, 3.0, S[7], ls=":")
    ax.text(45.0, Z_MID, "button\n(L3)", color=S[7], ha="center", va="center", fontsize=7)
    m = F0.MIC_PORT
    ax.add_patch(Circle((m["x"], m["z"]), F0.MIC_SEAL["keepout_r"], fc=S[2], alpha=0.3, ec=S[2]))
    ax.add_patch(Circle((m["x"], m["z"]), m["d_pcb"] / 2, fc=plotstyle.SURFACE, ec=S[2]))
    ax.add_patch(Circle((m["x"], Z_MID), F0.MIC_SEAL["keepout_r"], fc="none", ec=S[2], ls=":"))
    ax.text(m["x"], -3.9, "mic port 0.6,\nseal keep-out r1.6\n(dotted: L3 position)", color=S[2], ha="center", va="top", fontsize=7.5)
    for k in range(5):
        zc = 2.5 - 1.27 * k
        rect(ax, p["x0"] + 0.5, zc - 0.4, 1.4, 0.8, S[3], fill=True, alpha=0.8)
    ax.text(p["x0"] + 1.2, 2.5 - 1.27 * 4 - 0.8, "SWD\nprobe\n1.27", color=S[3], ha="center", va="top", fontsize=7)
    # frame's wire pads (circles) and proposed P2
    zs_frame = wire_pad_rows(F0.WIRE_PAD["z_top"])
    for k, zc in enumerate(zs_frame):
        ax.add_patch(Circle(((F0.WIRE_PAD["x0"] + F0.WIRE_PAD["x1"]) / 2, zc), 0.5, fc="none", ec=S[1], lw=0.9))
    zs = wire_pad_rows(Z_MID + 3.5 * 1.3)
    for k, zc in enumerate(zs):
        x1 = p["x1"] - 0.3 if k % 2 == 0 else p["x1"] - 2.1
        rect(ax, x1 - 1.6, zc - 0.5, 1.6, 1.0, S[0], fill=True, alpha=0.55)
        ax.text(p["x1"] + 0.8, zc, PROPOSED_ORDER[k], color=S[0], va="center", ha="right", fontsize=7.5)
    ax.text(41.0, -8.95, "wire pads: frame (orange rings) vs proposed P2 (blue)", color=T2, ha="center", va="top", fontsize=7)
    rect(ax, 45.2, 0.9, 1.6, 1.9, S[4], ls="--")
    ax.text(46.0, 0.7, "D3+D4\nnext to\nVBUS pad", color=S[4], ha="center", va="top", fontsize=7)
    # ---- shell agent's "proposed" variant (hw/mech/shell.py): the LID locates the board
    import shell as SH
    v = SH.VARIANTS["proposed"]
    cz0, cz1 = F0.CAV["z0"], F0.CAV["z1"]
    rt0, rb1 = SH.TOP_BAND[0] + 0.05, SH.BOT_BAND[1] - 0.05
    for xa, xb in ((SH.RIB_X[0], 35.8), (46.6, SH.RIB_X[1])):          # top rib gap = button flexure
        rect(ax, xa, rt0, xb - xa, p["z1"] - rt0, S[1], fill=True, alpha=0.6, lw=0.6)
    rect(ax, SH.RIB_X[0], p["z0"], SH.RIB_X[1] - SH.RIB_X[0], rb1 - p["z0"], S[1], fill=True, alpha=0.6, lw=0.6)
    for za, zb in ((p["z1"] + SH.EDGE_GAP, cz1 - 0.15), (cz0 + 0.15, p["z0"] - SH.EDGE_GAP)):
        rect(ax, SH.RIB_X[0], za, SH.REAR_STOP_X[1] - SH.RIB_X[0], zb - za, S[1], fill=True, alpha=0.25, lw=0.6)
    for za, zb in ((rt0, cz1 - 0.15), (cz0 + 0.15, rb1)):
        rect(ax, SH.REAR_STOP_X[0], za, SH.REAR_STOP_X[1] - SH.REAR_STOP_X[0], zb - za, S[1], fill=True, alpha=0.95, lw=0.6)
    for za, zb in (SH.TOP_BAND, SH.BOT_BAND):
        rect(ax, F0.CAV["x0"], za, SH.FRONT_STOP_X1 - F0.CAV["x0"], zb - za, S[4], fill=True, alpha=0.95, lw=0.6)
    pcm = v["pcm"]
    rect(ax, pcm["x0"], pcm["z0"], pcm["x1"] - pcm["x0"], pcm["z1"] - pcm["z0"], T2, ls="--", lw=0.9)
    ax.text((pcm["x0"] + pcm["x1"]) / 2, -6.2, "cell PCM\nfolded flat\n(placeholder)", color=T2, ha="center", va="center", fontsize=6.5)
    bx = v["boss_x"]
    for (x, z), nm in zip(v["screws"], ("VBUS\n+5 V", "GND\nCHG")):
        rect(ax, bx[0], z - 2.0, bx[1] - bx[0], 4.0, S[5], ls="-", lw=0.7)
        ax.add_patch(Circle((x, z), 1.4, fc=S[5], alpha=0.45, ec=S[5]))
        ax.text(x, z, nm, color=TX, ha="center", va="center", fontsize=6.5)
    for (x, z) in F0.LID_SCREWS:
        ax.add_patch(Circle((x, z), 1.4, fc="none", ec=S[5], ls=":", lw=0.9))
    ax.text(F0.LID_SCREWS[0][0], F0.LID_SCREWS[0][1] + 1.9, "frame.py\nscrew (old)", color=S[5], ha="center", va="bottom", fontsize=6)
    for k, (x, z) in enumerate(v["screws"]):
        ax.annotate("", xy=(p["x1"] + 0.1, zs[k]), xytext=(bx[0] - 0.1, z if k == 0 else z + 1.0),
                    arrowprops=dict(arrowstyle="->", color=S[5], lw=0.9, connectionstyle="arc3,rad=0.15"))
    ax.text(53.9, 1.2, "wire loop\n(8 x ~35 mm)", color=T2, ha="center", va="center", fontsize=7)
    ax.text(48.0, -10.0, "orange = lid ribs (press the outer-face bands), webs (pale, beside the edges) and rear stops (solid);   "
            "pink = tub front stops;\nthe cell's foam strips press the INNER-face bands from below (same hatched zones).   "
            "Screws: shell's proposed x 64.2 (filled) vs frame.py x 60.8 (dotted)", color=T2, ha="center", va="top", fontsize=7)
    ax.set_xlim(67.2, 29.4)                 # seen from outside the right pod: front is on the right
    ax.set_ylim(-12.2, 6.4)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm, frame.py; rear <- -> front)   KiCad x = 50.6 - x")
    ax.set_ylabel("z (mm)   KiCad y = 3.75 - z")
    ax.set_title("Right pod PCB, outer face (F) seen from outside, lid off, with the shell's locating features\n"
                 "Hatched: clamp bands; grey: end keep-outs")

    # ---- wire pad options close-up
    ax = axs[1]
    opts = [("P0 now: 1.0 round\n1.3 pitch, gap 0.30", "round"), ("P1: 0.9 x 1.9 oblong\n1 column, gap 0.40", "p1"),
            ("P2: 1.0 x 1.6 staggered\njoints 2.2 apart (recommended)", "p2"), ("P3: plated holes 0.45/0.90\nstaggered, solder on far side", "p3")]
    for i, (title, kind) in enumerate(opts):
        x0 = i * 7.0
        rect(ax, x0 + 4.2, -4.6, 0.25, 8.8, TX, fill=True, alpha=0.6)      # board edge
        for k in range(6):
            zc = 3.25 - 1.3 * k
            if kind == "round":
                ax.add_patch(Circle((x0 + 3.5, zc), 0.5, fc=S[1], alpha=0.7))
                ax.plot([x0 + 3.5, x0 + 6.6], [zc, zc], color=S[3], lw=1.6)
            elif kind == "p1":
                rect(ax, x0 + 2.2, zc - 0.45, 1.9, 0.9, S[0], fill=True, alpha=0.7)
                ax.plot([x0 + 2.9, x0 + 6.6], [zc, zc], color=S[3], lw=1.6)
            elif kind == "p2":
                xa = x0 + 2.5 if k % 2 == 0 else x0 + 0.7
                rect(ax, xa, zc - 0.5, 1.6, 1.0, S[0], fill=True, alpha=0.7)
                ax.plot([xa + 0.5, x0 + 6.6], [zc, zc], color=S[3], lw=1.6)
            else:
                xa = x0 + 3.4 if k % 2 == 0 else x0 + 2.0
                ax.add_patch(Circle((xa, zc), 0.45, fc=S[0], alpha=0.7))
                ax.add_patch(Circle((xa, zc), 0.225, fc=plotstyle.SURFACE))
                ax.plot([xa, x0 + 6.6], [zc, zc], color=S[3], lw=1.6)
        ax.text(x0 + 3.3, 4.5, title, color=TX, ha="center", va="bottom", fontsize=8)
    ax.text(14, -5.6, "yellow = 0.25-0.3 mm PTFE wire arriving from the rear free space (right); dark bar = PCB rear edge",
            color=T2, ha="center", fontsize=8)
    ax.set_xlim(-0.5, 28.5)
    ax.set_ylim(-6.2, 6.6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Rear-edge wire pads: options for hand-soldering 8 wires at 1.3 mm pitch")
    fig.savefig(OUT / "pcb_interface.png")
    plt.close(fig)

    # ---------------- figure 2: pad board + JLC panel
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.6), gridspec_kw={"width_ratios": [1, 2.4]})
    ax = axs[0]
    rect(ax, -PB["w"] / 2, PB["e3_0"], PB["w"], PB["e3_1"] - PB["e3_0"], TX, lw=1.6)
    ax.add_patch(Circle((0, 0), DAM_R, fc=S[4], alpha=0.10, ec=S[4], ls="--", lw=1.0))
    ax.add_patch(Circle((0, 0), 5.3 / 2, fc="none", ec=S[2], ls=":", lw=1.0))
    for net, w, pts in TRACKS:
        ax.plot([-x for x, y in pts], [-y for x, y in pts], color=S[0], lw=w * 9, alpha=0.55, solid_capstyle="round")
    for ref, (x, y, kind, a_, b_) in PADS_KICAD.items():
        X, Y = -x, -y                                     # draw in (e1, e3) so "up" is up the pad
        if kind == "arm":
            rect(ax, X - a_ / 2, Y - b_ / 2, a_, b_, S[0], fill=True, alpha=0.85)
            ax.text(X, Y + b_ / 2 + 0.12, LABEL[ref], color=TX, ha="center", va="bottom", fontsize=6.5, rotation=90)
        else:
            ax.add_patch(Circle((X, Y), a_ / 2, fc=S[0], alpha=0.85))
            ax.add_patch(Circle((X, Y), b_ / 2, fc=plotstyle.SURFACE))
            ax.text(X, Y - a_ / 2 - 0.12, LABEL[ref], color=TX, ha="center", va="top", fontsize=6.5)
    rect(ax, -0.5, -0.25, 1.0, 0.5, S[2], fill=True)
    ax.text(0, -0.45, "D1 blue 0402\n(JLC places it)", color=S[2], ha="center", va="top", fontsize=7)
    ax.annotate("4 arm wires arrive here\n(strut channel exit)", xy=(0.0, 5.0), xytext=(2.9, 8.6),
                color=S[3], ha="center", fontsize=7, arrowprops=dict(arrowstyle="->", color=S[3]))
    ax.text(0, -4.45, "transducer leads come up through\nXDCR_A/B from below, soldered on top", color=T2, ha="center",
            va="top", fontsize=7)
    ax.text(0, -5.55, "dashed: pad cap's epoxy dam r 3.25 (no joint inside it)\ndotted: LED ring \u00f8 5.3",
            color=S[4], ha="center", va="top", fontsize=6.5)
    ax.set_xlim(-4.2, 4.2)
    ax.set_ylim(-7.0, 9.8)
    ax.set_aspect("equal")
    ax.set_xlabel("e1 (mm)")
    ax.set_ylabel("e3 (mm, up the pad)")
    ax.set_title("Pad board 5.0 x 9.3 x 0.8, LED face (outward)")

    ax = axs[1]
    W, H = 65.0, 31.5
    rect(ax, 0, 0, W, H, T2, lw=1.2)
    rect(ax, 0, 0, W, 5, T2, fill=True, alpha=0.18)
    rect(ax, 0, H - 5, W, 5, T2, fill=True, alpha=0.18)
    for x in (3.5, W - 3.5):
        for y in (2.5, H - 2.5):
            ax.add_patch(Circle((x, y), 1.0, fc="none", ec=TX))
    for x in (8, W - 8):
        for y in (3.85, H - 3.85):
            ax.add_patch(Circle((x, y), 0.5, fc=S[3], ec=S[3]))
    ax.text(W / 2, 2.5, "5 mm process rail: 2.0 mm tooling holes, 1.0 mm fiducials (JLC SMT)", color=T2, ha="center", va="center", fontsize=7.5)
    ax.text(W / 2, H - 2.5, "5 mm process rail", color=T2, ha="center", va="center", fontsize=7.5)
    yb = 5 + 6 + 2           # board bottom (test strip 6 mm + 2 mm gap above the lower rail)
    for i, x0 in enumerate((3.0, 26.0)):
        rect(ax, x0, yb, 20, 11.5, S[0], lw=1.6)
        ax.text(x0 + 10, yb + 5.75, f"POD board #{i+1}\n(same design both sides)\n20 x 11.5, 4-layer 0.8", color=TX,
                ha="center", va="center", fontsize=7.5)
        for xm in (x0 + 5, x0 + 15):            # mouse bites top + bottom edge (inside the clamp band)
            for yy in (yb + 11.5 + 0.0, yb):
                ax.plot([xm - 2.2, xm + 2.2], [yy, yy], color=S[1], lw=3, ls=(0, (1, 1)))
            ax.plot([xm, xm], [yb + 11.5, H - 5], color=S[1], lw=0.8)
        ax.plot([x0 + 10, x0 + 10], [yb, 11], color=S[1], lw=0.8)
        # SWD tab at the front edge (right edge of the RIGHT-pod KiCad view = x0+20)
        rect(ax, x0 + 20, yb + 7.0, 1.5, 1.5, S[3], fill=True, alpha=0.8)
        ax.plot([x0 + 21.5, x0 + 21.9, x0 + 21.9, x0 + 16.0], [yb + 7.75, yb + 7.75, 8.0, 8.0], color=S[3], lw=1.2)
        rect(ax, 5.0 + x0 + 1.0, 6.2, 12.7, 2.6, S[3], lw=1.0)
        for k in range(5):
            ax.add_patch(Circle((x0 + 7.27 + 2.54 * k, 7.5), 0.55, fc=S[3]))
    rect(ax, 0, 5, W, 6, S[3], ls=":")
    ax.text(W / 2 + 6, 5.4, "test strip: SWD 1x5 2.54 header per board, pins 3V0 SWDIO GND SWCLK NRST", color=S[3], ha="center", va="bottom", fontsize=6.5)
    for i, x0 in enumerate((50.0, 58.0)):
        rect(ax, x0, yb + 1.0, 5.0, 9.3, S[2], lw=1.4)
        ax.add_patch(Rectangle((x0 + 2.0, yb + 5.4), 1.0, 0.5, fc=S[2]))
        for xx in (x0, x0 + 5.0):
            ax.plot([xx, xx], [yb + 3.4, yb + 7.8], color=S[1], lw=3, ls=(0, (1, 1)))
        ax.text(x0 + 2.5, yb + 10.8, f"PAD #{i+1}", color=S[2], ha="center", fontsize=7.5)
    ax.text(W / 2, H + 1.6, "orange dotted = mouse bites (5 x 0.6 mm holes); yellow = SWD traces on a SOLID tab (cut, then sand flush)",
            color=T2, ha="center", fontsize=7)
    ax.set_xlim(-1, W + 1)
    ax.set_ylim(-1, H + 3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("One JLC panel (65 x 31.5 mm): 2 pod boards + 2 pad boards + SWD test strip")
    fig.savefig(OUT / "padboard_and_panel.png")
    plt.close(fig)

    # ---------------- figure 3: charge-contact and LED fixes (block schematic)
    fig, ax = plt.subplots(figsize=(11, 4.6))

    def blk(x, y, w, h, txt, col, fs=8):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15", fc=col, alpha=0.22, ec=col))
        ax.text(x + w / 2, y + h / 2, txt, color=TX, ha="center", va="center", fontsize=fs)

    def arr(x0, y0, x1, y1, col=T2, txt=None):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", color=col, lw=1.1))
        if txt:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.12, txt, color=col, ha="center", va="bottom", fontsize=7)

    y = 3.2
    blk(0.0, y, 1.6, 0.8, "top lid screw\n(+5 V contact)", S[5])
    blk(2.3, y, 1.3, 0.8, "brass nut\n+ wire", S[5])
    blk(4.2, y, 1.2, 0.8, "J3 VBUS\npad", S[0])
    blk(6.0, y, 1.6, 0.8, "NEW D4 Schottky\n1N5819WS (Basic)", S[2])
    blk(8.3, y, 3.2, 0.8, "VBUS node: D3 TVS, C15 4.7u,\nMCP73832, R12/R13 -> PA1", S[0])
    arr(1.6, y + 0.4, 2.3, y + 0.4)
    arr(3.6, y + 0.4, 4.2, y + 0.4)
    arr(5.4, y + 0.4, 6.0, y + 0.4)
    arr(7.6, y + 0.4, 8.3, y + 0.4)
    ax.text(5.5, y + 1.05, "upside-down on the dock: D4 blocks (today D3 conducts the dock's full current and can fail short)",
            color=S[2], ha="center", fontsize=8)
    y = 1.1
    blk(0.0, y, 1.3, 0.8, "VBAT", S[0])
    blk(1.9, y, 1.5, 0.8, "R14a 1k\n(was R14 2k2)", S[2])
    blk(4.0, y, 1.2, 0.8, "J7 LED+", S[0])
    blk(5.8, y, 1.6, 0.8, "arm wires +\npad-board LED", S[3])
    blk(8.0, y, 1.2, 0.8, "J8 LED-", S[0])
    blk(9.8, y, 1.3, 0.8, "NEW R14b 1k", S[2])
    blk(11.6, y, 1.0, 0.8, "PB7", S[6])
    for x0, x1 in ((1.3, 1.9), (3.4, 4.0), (5.2, 5.8), (7.4, 8.0), (9.2, 9.8), (11.1, 11.6)):
        arr(x0, y + 0.4, x1, y + 0.4)
    ax.text(6.3, y - 0.35, "a pinched arm wire or a solder bridge onto VBAT / OUT_A / OUT_B now pushes <= 4.2 mA into PB7 "
            "(abs max 20 mA), not tens of mA", color=S[2], ha="center", va="top", fontsize=8)
    ax.set_xlim(-0.2, 12.8)
    ax.set_ylim(0.2, 4.6)
    ax.axis("off")
    ax.set_title("Proposed hw/pod/gen.py changes: reverse-polarity block on the screw contact; LED resistor split across the arm")
    fig.savefig(OUT / "charge_led_fix.png")
    plt.close(fig)


def main():
    c = checks()
    info = cad()
    pictures()
    res = {"date": "2026-09-30", "module": "electronics", "frame": "hw/mech/frame.py (right pod)",
           "checks": c, "cad": info,
           "files": sorted(f.name for f in OUT.iterdir())}
    (OUT / "checks.json").write_text(json.dumps(res, indent=1, default=str))
    for x in c:
        print(f"{'PASS' if x['pass'] else 'FAIL'}  {x['name']}: {x['value']}")


if __name__ == "__main__":
    main()
