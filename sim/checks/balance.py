# Where does the added weight land: nose pads or ears?
# Statics of one temple arm: glasses rest on the nose pads (x = 0, at the hinge line to a
# first approximation) and on the ear (x = L). A mass m at distance x behind the hinge puts
# m*(1 - x/L) on the nose pads and m*x/L on the ear. Masses and positions are estimates
# (spec §8); the point is the comparison between layouts, not the absolute grams.
L_EAR = 100.0   # mm, hinge to the ear bend of the temple arm (typical adult frames)

def split(parts):
    nose = sum(m * (1 - x / L_EAR) for _, m, x in parts)
    ear = sum(m * x / L_EAR for _, m, x in parts)
    return nose, ear

def layouts(cell_g):
    transducer = ("transducer + drop-arm at tragus", 1.5, 90.0)
    return {
        "A: everything in one pod at the hinge": [
            ("pod: PCB, mic, cell, shell", 0.8 + cell_g + 2.0, 18.0), transducer],
        "B: electronics at hinge, cell behind it along the arm": [
            ("front: PCB, mic, button, shell", 0.8 + 0.7, 10.0),
            ("cell + shell, centred mid-arm", cell_g + 1.3, 50.0), transducer],
        "C: as B, cell pushed back to just before the Ear Open hook": [
            ("front: PCB, mic, button, shell", 0.8 + 0.7, 10.0),
            ("cell + shell", cell_g + 1.3, 62.0), transducer],
    }

if __name__ == "__main__":
    for cell_mah, cell_g in ((105, 3.0), (150, 4.5)):
        print(f"\n~{cell_mah} mAh cell ({cell_g} g). Added load per side:")
        for name, parts in layouts(cell_g).items():
            nose, ear = split(parts)
            print(f"  {name:58s} total {nose + ear:4.1f} g | nose pads {nose:4.1f} g | ear {ear:4.1f} g")
