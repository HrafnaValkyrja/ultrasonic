# Earbuds, bone-conduction headsets and glasses: what they do for power and size, and what transfers to our pod

Research note, 2026-10-01 (synthesis; fact-check corrections and my own datasheet re-reads dated 2026-10-02).
Read-only research: nothing in the spec, schematic, firmware or CAD changed. The two working notes behind this one are `docs/research/tws/battery.md` and `docs/research/tws/power.md`. **Where they disagree with this note, this note wins** (section 6 lists every correction).

Sources are maker pages and datasheets, iFixit teardowns, PubMed abstracts and our own repo files. The web-search quota was spent before this run, so there is no search-engine coverage; what I could not open is marked **unverified** or **not opened**. Each number carries a source and the date it was read.

Diagram: `docs/diagrams/tws-cells.svg` (render: `bash docs/diagrams/render.sh docs/diagrams/tws-cells.svg`).

![Pod cell envelope vs candidates, to scale, with runtime bars](../diagrams/tws-cells.png)

## Key to the codes used

| Code | Meaning |
|---|---|
| D11 | Spec decision: switching regulator only as the MCU's internal core SMPS (switched-mode supply); everything else linear; must pass the listening test (E11) |
| D18 | Runtime >= 8 h, target ~12 h, balance the mass along the arm |
| O16 / O18 / O19 / O20 | Owner decisions: cell and charger picked / rev 1 must fail informatively, every uncertain value a firmware knob / personal device, serviceable, never touch the schematic again / rev 1 is the final size |
| E2 / E4 / E11 | Bench measurements: level needed at the tragus / current per mode (PPK2 power profiler) / SMPS whine listening test |
| ECR-0005 | Engineering change request: LDO 300 mA rating vs ~0.32 A full-scale bridge peaks |

---

## 1. Bottom line (blunt)

**What the others do that we don't**

1. **They carry a case.** A bud holds 0.09-0.22 Wh and a pocket case 1.0-2.0 Wh refills it. We carry 0.65 Wh **per side** with no case, because the glasses stay on the face and we dock nightly (D18). Per side we hold as much as a whole Shokz OpenRun headset (0.62 Wh) and about three AirPods Pro 3 buds (0.22 Wh each).
2. **They accept shorter runtimes.** AirPods Pro 2: 6 h. AirPods Pro 3: 8 h. Shokz OpenRun: 8 h. Nuance Audio hearing-aid glasses: 8 h (10+ h for the Plus). We ask 8 h minimum and ~12 h, with no mid-day top-up.
3. **They use custom silicon at about 1 V.** Apple's H2 chip, hearing-aid chips. We run a general-purpose MCU at 3.0 V behind a linear regulator. Real hearing aids sit about an order of magnitude below us (Energizer's zinc-air test load is ~2-3 mW). We cannot close that gap with parts we can buy, and our ultrasonic mic alone (~4 mW) costs more than that.
4. **They do not use a better cell.** Small protected pouch packs run **250-330 Wh/L**; ours is **291**. No hidden 2x. The densest option I found at the same size class is a high-voltage pouch at **332 Wh/L** (Renata ICP621333HPMT, 4.35 V charge), +14%.

**Where we stand on current.** We are in the earbud band, not above it: **~6.8 mA nominal awake (5.0-9.8)** against 5.8-8.3 mA for AirPods and 8.0 mA for the Nothing Ear (open). The closest bone-conduction product, the Shokz OpenRun, averages **~20 mA** by label arithmetic (160 mAh over its claimed 8 h), three times ours, though it also runs a Bluetooth link. (Section 2.)

**The 175 mAh cell already clears the target by a wide margin.** At the spec's 5-8.5 mA mean it lasts **17.5-29.8 h** (85% usable). Only the stacked worst case (awake 9.8 mA + LED 0.75 mA, 75% usable) brings it to **12.4 h**, and at end of life (80% of the *minimum* capacity, 136 mAh) to **9.7 h**. It is sized for the pessimistic corner, not the expected one.

**The 3 biggest levers for our pod**

| # | Lever | Size or power effect | Status |
|---|---|---|---|
| 1 | **Pick the cell from the measured current (E4), not the estimated range.** The cell is **4.2 g of a >= 10.2 g pod (41%)** and 2.2 cm3 of the 6.8 cm3 shell envelope (33%) (`physical.md`). Every 1 mA of true mean current is **14 mAh** over 12 h (**0.34 g**, 5 mAh per mm of cell length). At 7 mA the 12 h need is **99 mAh** (nominal) and 169 mAh only at the stacked worst case | -0.7 g and -20% bay volume (130 mAh slim option) if E4 comes in at or below ~8 mA | Needs E4. Under O20 rev 1 is the final size, so decide before the shell freezes |
| 2 | **Firmware gating of the MCU:** algorithm A with a lower clock (Range 3, <= 55 MHz), idle detector in Stop 2, squelch stops the bridge | **-0.9 to -1.4 mA awake** (A, clock floor), **-0.2 to -0.4 mA averaged** (Stop 2 idle), 0.77 mA x squelched fraction (bridge). All `[Low]`-grade estimates | Firmware only, so O18-clean. Stop 2 must pass the E11 listening test (section 4) |
| 3 | **The mic: 1.35 mA in every state** (20% of awake, 61% of idle). The only big always-on load | **-0.3 to -0.5 mA** if a 1.8 V rail or the TDK T5838 works. **Unverified** | Hardware change, so it fights O18/O19/O20. Measure the SPH0641 at 3.0 V / 4 MHz first (E3/E4) |

**Not a size lever, but the best use of the margin:** charge to **4.10-4.15 V** and never float (section 3). It costs 7-14% of capacity and buys roughly **1.25-1.6x the cycles** (Battery University's estimate, a secondary source), which matters for a cell worn daily for years (O19).

---

## 2. Real devices: cell, runtime, implied current

Implied mean current = rated mAh divided by rated hours. It includes the Bluetooth link, codec and sensors that we do not have, and the rated runtimes are vendor figures under vendor test conditions. Treat it as a ballpark.

| Device (type) | Cell: capacity, type / size | Rated runtime | Implied mean current | Source (read) |
|---|---|---|---|---|
| AirPods, 1st gen (TWS earbud, 2016) | **93 mWh** cylindrical "pin" cell in the stem, per bud. Case 398 mAh / 1.52 Wh | not opened | n/a | iFixit teardown 75578, published 2016-12-20, steps 3, 9, 15 (2026-10-01) |
| AirPods Pro, 1st gen (2019) | **Varta CP1154** coin cell (Ø11 x 5.4 mm class), 3.7 V, **0.16 Wh** per bud; case 1.98 Wh | not opened | n/a | iFixit 127551, published 2019-10-31, steps 8, 15 (2026-10-01) |
| Samsung Galaxy Buds (2019) | **Varta CP1254** coin cell (Ø12 x 5.4 mm), ~**0.2 Wh** | not opened | n/a | iFixit AirPods Pro teardown step 8 (2026-10-01) |
| Google Pixel Buds 2 (2020) | **Varta CP1240 A3**, 3.7 V, **0.2 Wh** | not opened | n/a | iFixit 133888, published 2020-05-26, step 16 (2026-10-01) |
| AirPods Pro 2 (Apple H2 chip) | 49.7 mAh, 0.182 Wh per bud; case 523 mAh. **Capacity from Wikipedia's spec template, no cited source: secondary** | 6 h listening (5.5 h with spatial audio); 30 h with case | **~8.3 mA** (~30 mW) | Apple support 111851 (2026-10-01, re-read 2026-10-02); Wikipedia Template:AirPods_technical_specifications (2026-10-01) |
| AirPods Pro 3 (Apple H2), ANC | 58 mAh, 0.221 Wh per bud (same secondary source) | 8 h ANC | **~7.3 mA** (~28 mW) | apple.com/airpods-pro/specs (2026-10-01, re-read 2026-10-02) |
| AirPods Pro 3, Hearing Aid feature in Transparency | same cell | **10 h**. Apple's footnote: volume and amplification at 50%, **no audio playing from the iPhone**, pre-production units, tested Jul-Aug 2025 | **~5.8 mA** (~22 mW) | same page. This is the closest product to ours in function (mic -> DSP -> speaker, all day) and it is a best case, not a streaming figure |
| Nothing Ear (open) (open-ear earbud, BT 5.3) | 64 mAh per bud; case 635 mAh | 8 h playback; 6 h talk | **~8.0 mA** playback, ~10.7 mA talk | nothing.tech/products/ear-open spec data (2026-10-01, re-read 2026-10-02). The owner's own earbuds |
| **Shokz OpenRun** (bone conduction, neckband) | **AEC 521129, 160 mAh, 3.85 V** (label read from teardown photo) = 0.62 Wh, one pouch for the whole headset | **8 h** | **~20 mA** (~77 mW) | iFixit 182927, published 2025-03-11, step 3 photo (2026-10-01); shokz.com/products/openrun (2026-10-01) |
| Shokz OpenRun Pro 2 | not published | 12 h | unknown | shokz.com/products/openrunpro2 (2026-10-02). The "larger, weight-optimized battery" sentence was on the 2026-09-30 cached copy only; cite it as cached |
| Shokz OpenFit (open-ear air-conduction earbud) | not published | 7 h; 8.3 +/- 0.2 g per bud; battery and driver "at the ends of the hooks" for balance | unknown | shokz.com/products/openfit, /pages/comfort-tech (2026-10-01) |
| AfterShokz Trekz Titanium (bone conduction) | **AEC 531236, 200 mAh**, 3.7 V, 0.74 Wh, one rear pod | not opened | n/a | iFixit 144329, published 2021-08-06, step 8 (2026-10-01) |
| **Bose Frames Alto** (audio glasses) | **Synergy AHB330945PST-01, 110 mAh**, 0.4 Wh, <= 4 x 9 x 45 mm, taped in the left temple beside the speaker | not opened | n/a | iFixit guide 202556, 2025-12-10, steps 5-8 + label photo (2026-10-01) |
| **Nuance Audio Glasses / Plus** (hearing-aid glasses; the closest commercial analogue) | not published ("high-efficiency battery") | Glasses: up to 8 h (quiet), 7-8 h (50-65 dB), 5.5-7 h (> 65 dB). Plus: 10+ h (9 h 38 min to 10 h 36 min across conditions) | unknown | nuanceaudio.com/en-us/c/frame-battery-life-guide (read 2026-10-02) |
| Ray-Ban Meta / Oakley Meta | **not found** | - | - | meta.com returned HTTP 400; iFixit has no teardown (2026-10-01, 2026-10-02). **Unverified** |
| Research behind-the-ear hearing aid, custom 22 nm chip, 5 g (Karrenbauer et al.) | rechargeable, mAh not given | 9 h wireless off, 6 h on | **31 mW / 47 mW** (~8 / ~12 mA at an assumed 3.8 V) | IEEE EMBC 2023, doi 10.1109/EMBC40787.2023.10340206, abstract via PubMed (2026-10-01). The chip alone is 1.45 mW (TBioCAS 2025, doi 10.1109/TBCAS.2024.3481044), but the abstracts do not say where the other ~30 mW goes |
| Zinc-air 312 hearing-aid cell (Energizer) | 181 mAh to 1.05 V, 1.4 V, 0.5 g | IEC test load 2 mA base with 10 mA pulses; "streaming" test 5 mA x 15 min + 2 mA x 45 min | **~2.75 mA at 1.2-1.4 V (~3-4 mW)**. This is a cell-rating test profile, not a measured device draw | data.energizer.com/pdfs/312.pdf, form 312GL0318 (2026-10-01) |
| Phonak Audeo Infinio Ultra Sphere (hearing aid) | not stated | "up to 56 hours" (maximum runtime) | unknown | phonak.com Audeo Sphere page (2026-10-01) |
| **Ours, one pod** | Renata ICP501233PA-02 175 mAh, 0.65 Wh | target >= 8 h, ~12 h | **awake 6.8 mA nominal (5.0-9.8)**, idle 2.2 (1.7-3.4), plus LED 0.14-0.75 | `sim/checks/power.py` rev 2; `docs/system/sub-power.md` |

**Reading it.**
- Energy per bud: 0.09-0.24 Wh. Ours: 0.65 Wh per side. We are the heaviest cell in the table apart from the case.
- The Pro 3's hearing-aid mode (~22 mW) is in our band (~25 mW awake). That is not a lost cause for a general-purpose MCU, but note the Apple figure has no streaming.
- The bone-conduction headset we can actually compare with draws three times our current. The exciter itself is our unknown (section 5).

---

## 3. Cell options for the pod

**The bay today** (`hw/mech/shell_r1.py` `CELL`, `docs/system/physical.md`): **35 mm along the arm x 5.3 mm thick x 12 mm high**. The 0.3 mm gap beside the cell holds 0.25 mm of VHB tape (3M double-sided acrylic foam tape), so there is no thickness slack. Pod envelope 38.0 x 11.8 x 15.2 mm. Pod mass >= ~10.2 g (lower bound) against the ~8 g target.

**Part numbers.** **ICP501233PA-02, ICP621333PA-01, ICP621333HPMT, ICP401230UPR**: Renata (Swatch Group, Switzerland) Li-ion polymer pouch packs; "ICP" = prismatic Li-ion polymer, the digits are thickness (x0.1 mm) / width / length; "PA/UPR/HPMT" mark protection circuit, lead type and, for HPMT, a high-voltage cell with NTC (10 kOhm-class thermistor). **ICR1254 B2**: Renata rechargeable Li-ion coin cell, Ø12.2 x 5.6 mm, no protection circuit. **PCM** = protection circuit module (protector IC plus dual MOSFET; cuts the cell on over-charge, over-discharge, over-current, short).

Computed from the makers' maximum envelopes (box volume, so it counts the dead corners of a coin cell). Runtime = capacity x 0.85 / mean current at 5 / 7 / 8.5 mA; "worst" = awake 9.8 mA + LED 0.75 mA at 75% usable (10.55 mA; `sub-power.md`). Arithmetic: scratchpad `tws/cells.py`, run 2026-10-02.

| Cell (all 3.7 V nominal unless stated) | Capacity (min) / energy | Envelope T x W x L (max, mm) | Wh/L | Mass | PCM / NTC | Runtime at 5 / 7 / 8.5 mA, then worst (h) | Buy in ones? | Fit in the 35 x 5.3 x 12 bay |
|---|---|---|---|---|---|---|---|---|
| **Renata ICP501233PA-02 (ours)** | 175 (170) mAh / 0.65 Wh | 5.3 x 12 x 35 | **291** | 4.2 g | PCM yes, **no NTC** | 29.8 / 21.2 / 17.5, worst **12.4** | Distributor quote only; not on Digi-Key; renata.com shows no price or MOQ | Exact (that is how the bay was drawn) |
| Renata ICP401230UPR | 130 mAh / 0.48 Wh | 4.5 x 12.7 x 31 | 271 | 3.5 g | PCM yes | 22.1 / 15.8 / 13.0, worst 9.2 | Same channel; **unverified** | **Not drop-in: 0.7 mm too tall.** 0.8 mm thinner, 4 mm shorter |
| Renata ICP621333PA-01 | 240 (230) mAh / 0.89 Wh | 6.7 x 13 x 35 | 291 | 5.5 g | PCM yes; datasheet says "IEC62133 certified" | 40.8 / 29.1 / 24.0, worst 17.1 | Same channel; unverified | Bay +1.4 mm thick, +1.0 mm high, +1.3 g |
| Renata ICP621333HPMT (3.8 V, **4.35 V** charge) | 270 (260) mAh / 1.03 Wh | 6.8 x 13 x 35 ("after 500 cycles") | **332** | 5.6 g | PCM yes, **incl. NTC** | 45.9 / 32.8 / 27.0, worst 19.2 | Same channel; unverified | Bay +1.5 mm thick, +1.0 mm high, +1.4 g. 2C pulse 540 mA (ours 350) |
| 2 x Renata ICR1254 B2 coin (3.8 V, 4.3 V charge, 1000 cycles) | 154 (144) mAh / 0.59 Wh | 2 x Ø12.2 x 5.6 = 24.4 x 12.2 x 5.6 | 351 cells only; **~245 in the 35 mm bay** with room for a PCM | 3.6 g + PCM | **No PCM: add one** (e.g. ABLIC S-8261 + dual MOSFET) | 26.2 / 18.7 / 15.4, worst 10.9 | Digi-Key "renata ICR1254": zero results (2026-10-02); unverified elsewhere | Bay +0.3 mm thick, +0.2 mm high; tabs must be spot-welded; 72 mA continuous per cell |
| 3 x Renata ICR1254 B2 | 231 (216) mAh / 0.88 Wh | 36.6 x 12.2 x 5.6 (cells only) | 351 / ~220 | 5.4 g + PCM | add PCM | 39.3 / 28.1 / 23.1, worst 16.4 | as above | **No: 36.6 mm of cells before PCM and tabs** |
| Varta CoinPower CP1254 A4X (74 mAh, 4.3 V) / Grepow GRP1254 RL, M1 (68-77 mAh, 4.2 V), same Ø12 x 5.4 coin | 68-77 mAh each | Ø12 x 5.4 | 324-366 (4.2 V), 346 (Varta, 4.3 V) | 1.8 g | PCM mandatory (Varta datasheet) | not shown | **No.** Digi-Key and TME: zero results (2026-10-01/02); LCSC and Mouser **bot-blocked, unverified**; iFixit sells an aftermarket LIR1254 pair, $14.99, no datasheet | as the Renata coin |
| Bose-Frames-type temple pouch (Synergy AHB330945PST-01) | 110 mAh / 0.41 Wh | <= 4 x 9 x 45 | 251 | n/a | "BMS board" on a 3rd wire | 18.7 / 13.4 / 11.0, worst **7.8** | AliExpress replacement linked from the iFixit guide; unverified | **No: 45 mm > 35 mm** and it misses 8 h at the worst case |
| Adafruit #1570 (bench only) | 100 mAh / 0.37 Wh | 3.8 x 11.5 x 31 | 273 | 3 g | PCM yes | 17.0 / 12.1 / 10.0, worst 7.1 | **Yes, $5.95** (cached page 2026-09-30) | Fits; too small for 12 h with margin |
| Two Ø~5 mm pin cells (AirPods-stem style) | unknown | unknown | would need >= 420 Wh/L at cell level just to tie ours | - | - | - | **No source found** (EVE, Grepow list none) | Rejected on geometry: a cylinder wastes ~21% of a rectangular bay |

Sources: Renata catalogue page renata.com/en/products/lithium-polymer-batteries/ and rechargeable coin-cell page (both read 2026-10-02); Renata datasheets ICP501233PA V03 08/2019, ICP621333PA V03 10/2019, ICP621333HPMT V01 11/2020, ICR1254 B2 V00 03.2024 (read 2026-10-02); masses cross-checked against Renata's UN 38.3 transport summaries (4.2 g, 5.5 g, 5.6 g; 0.6 Wh/170 mAh, 0.85 Wh/230 mAh, 1.0 Wh/260 mAh; documents dated 2019-11-25 and 2023-02-01). ICP401230UPR V02 08/2019 (cached 2026-09-30). Varta CoinPower brochure Nov 2024 and CP1254 A4 datasheet 2020-02-18 (cached 2026-09-30). Grepow GRP1254 page (2026-10-01). Digi-Key and TME searches (2026-10-01 and 2026-10-02).

**What the numbers say**
- **The 175 mAh cell is oversized for expected use and right-sized for the stacked worst case.** The 12 h need is 71 / 99 / 120 mAh at 5 / 7 / 8.5 mA and **169 mAh** at the worst corner. Hence the margin is a real choice: bigger than needed on average, exactly enough in the worst case.
- **End of life matters.** Renata rates >80% of the *minimum* capacity after 500 cycles (0.5C / 0.5C). That is **136 mAh, 78% of nominal**, and the worst-case runtime then drops to **~9.7 h**. A cell charged every day reaches 500 cycles in about 1.4 years if every cycle were full depth; ours are 25-50% deep (sub-power model), so expect much longer, but that is a model, not a Renata figure.
- **Swelling is not covered.** The HPMT sheet quotes its dimensions "after 500 cycles"; the ICP501233PA-02 sheet does not say whether 5.3 mm is a fresh or an aged maximum. Our bay has no thickness slack. I found no primary source that puts a percentage on pouch swelling. A steel-can coin cell may avoid the question (Varta's handbook sells the can on robustness; the fact-checker also reported a "no measurable swelling" claim on Renata's ICR1254 page, but I could not reproduce that sentence on 2026-10-02, so it is **unverified**).
- **The 332 Wh/L HPMT is not a free upgrade.** Its 4.35 V charge is what buys the density. Renata rates it for the same 500 cycles as the 4.2 V packs, so the "high voltage kills cycle life" claim in the earlier note is unsupported for Renata's own part. Capacity if charged only to 4.2 V is not stated: **unverified**.
- **Lower charge voltage, from Battery University BU-808** (updated 2023-10-11, a secondary source, "all values are estimated", generic cobalt-based cells), read 2026-10-01 and 2026-10-02, interpolated by me:

  | Charge voltage | Energy kept | Cycles (est.) | vs 4.20 V |
  |---|---|---|---|
  | 4.20 V | 100% | 300-500 | 1x |
  | 4.15 V | ~93% | ~370-640 | ~1.25x |
  | 4.13 V | 90% | 400-700 | 1.3-1.4x |
  | 4.10 V | ~86% | ~490-830 | ~1.6x |
  | 4.06 V | 81% | 600-1000 | 2.0x |

  So "10-15% for 1.5-2x" in the earlier note was optimistic: **4.10 V gives ~1.6x for -14%; ~2x needs 4.06 V at -19%.** The worst-case runtime at 4.10 V is ~10.7 h. The BQ25180 charger (TI, single-cell Li-ion charger with power path, U3) sets the charge voltage in 10 mV steps from 3.5 to 4.65 V over I2C (TI SLUSE99C, Jan 2023), so this is a firmware knob (O18).
- **Coin cells are the only real alternative and are not for rev 1.** 2 x Renata ICR1254 B2 give 154 mAh (-12% capacity, -10% energy vs ours, at the 4.3 V charge Renata rates them for) and a 1000-cycle rating (twice the pouch's 500), but they need a new PCM circuit, spot-welded tabs, +0.3 mm thickness and +0.2 mm height, and each cell is rated 72 mA continuous. Three cells do not fit. A single cell cannot feed the bridge. Park this for a rev 2 *if* pouch swelling or ageing bites.

### Options (owner decides)

| | Option | What changes | Runtime (7 mA / worst) | Cost |
|---|---|---|---|---|
| **A (recommended)** | **Keep Renata ICP501233PA-02 175 mAh.** Charge to 4.10-4.15 V, no float, put the NTC on the cell via J9, buy spares (O19: cell replaced as it ages) | Nothing in the shell or board | 21.2 h / 12.4 h at 4.20 V; ~10.7-11.5 h worst at 4.10-4.15 V | Zero size. Ask Renata the questions below before ordering |
| B | **Slim: Renata ICP401230UPR 130 mAh** | Shell: -0.8 mm thick, -4 mm long, **+0.7 mm high**; -0.7 g, -20% bay volume | 15.8 h / 9.2 h | Meets 8 h everywhere, 12 h only on average. Only after E4 shows <= ~8 mA awake including the LED. Needs the shell re-sized (O20: decide before freeze) |
| C | **Grow: Renata ICP621333HPMT 270 mAh** (NTC built in, 4.35 V cell) | Shell +1.5 mm thick, +1.0 mm high; +1.4 g | 32.8 h / 19.2 h | Works against O20 (final size) and the mass target. Only if E4 comes in high (> ~10 mA) or the owner wants a multi-year ageing margin. The built-in NTC does not justify it: the J9 pad already takes a taped-on NTC |
| (parked) | 2 x Renata ICR1254 B2 coin + PCM | New PCM circuit, tabs, +0.3 T, +0.2 H | 18.7 h / 10.9 h | A rev 2 idea if swelling shows up |

**Recommendation: A.** The owner's pick (O16) is right for rev 1. Spend the margin on longevity, not on capacity. Do not buy a bigger or a different cell for rev 1.

**Questions for Renata before ordering** (none is answered in the sheets I read):
1. Maximum thickness **after 500 cycles** (the HPMT sheet gives it; the 501233PA-02 sheet does not).
2. Is the pack IEC 62133 certified? (The ICP621333PA-01 sheet says so; the 501233PA-02 sheet does not state it. I have only the UN 38.3 transport summary, tested 2017-01-14, document 2019-11-25: "Passed" T.1-T.8.) This is the R23 safety item.
3. Lead exit and PCM position inside the pouch (physical.md issue 10), and whether a 175 mAh variant with NTC exists.
4. Price, MOQ and lead time for 3-6 pieces.

---

## 4. Power techniques, ranked by mA saved for our budget

Baseline: awake 6.76 mA nominal (MCU 2.7 incl. a ~1.45 mA sleep floor at 80 MHz, mic 1.35, exciter 1.1 *guess*, bridge 0.77, peripherals 0.73, misc 0.11); idle 2.2 mA (mic 1.35, MCU detector 0.7). Rev 2 of `power.py`; algorithm B. Savings are in average battery current. **1 mA = 14 mAh over 12 h.**

| Rank | Technique | Saving (nominal) | Basis and confidence | Cost in size / complexity | Conflicts with our rules |
|---|---|---|---|---|---|
| 0 | **Measure the exciter (E2 level at the tragus, E4 current).** The 1.1 mA line (range 0.4-2.5) is a guess | Swing of about **0 to -1.1 mA** if physics holds; could also be higher | Physics bound, derived: a lossless bridge on a 3.0 V bus into ~9.3 Ohm draws m^2 x 3.0/(2 x 9.3) mA at modulation depth m: **1.6 mA at -20 dBFS while playing, 0.16 mA at -30 dBFS** (I re-derived this). The 1.1 mA guess equals -21 dBFS playing continuously. With calls 30-60% of awake time: ~0.05-0.9 mA | None: a measurement | None. Not a technique, but the largest unknown |
| 1 | **Algorithm A with a lower clock** (Range 3, 48-55 MHz) | **-0.9 to -1.4 mA awake** (MCU 2.7 -> ~1.3-1.8). Table-supported part from the clock floor alone: **-0.5 to -0.6 mA** (sleep floor 1.45 -> 0.92 mA, DS13737 Tables 39/46) | The 1.3-1.8 mA for A is marked `[Unverified]` in `A3-u575-plan.md` §5 (M33 cycles assumed equal to M4). The 55 MHz Range 3 row was measured with an external clock and no PLL, so PLL current eats some of the saving. Dynamic cost per Mcycle/s is the same at 80 and 55 MHz (~23 uA) | PWM steps drop from 200 to ~120-137 (**-3.3 to -4.4 dB** resolution); D14's HCLK/400 lock changes; algorithm A is the owner's listening decision | None of D11. A knob (O18) |
| 2 | **Idle detector in Stop 2** (ADF + LPDMA into SRAM4; CPU wakes per FFT) | **-0.45 mA while idle**, so **-0.22 mA at 50% idle, -0.37 mA at 82% idle** (quiet room) | `[Low]`: the 0.25 mA end state is `A3-u575-plan.md` §1.3's own estimate (~0.1 mA) plus a 0.15 mA burst guess; no datasheet current behind it | Firmware; the ADF runs from MSIK in Stop 2, so the mic clock source changes between idle and awake | **D11/E11:** in Stop the core SMPS runs in an asynchronous mode (A3 §4; DS Table 35 footnote). The saving stands only if the E11 listening test passes **in Stop 2** (spec E11 already requires it). Firmware knob (O18) |
| 3 | **Mic at a lower supply, or the TDK T5838 mic** | **-0.3 to -0.5 mA, always on**. **Unverified** | SPH0641 datasheet gives 845 uA typ at **1.8 V**, 3.072 MHz. Our 1.35 mA at 3.0 V / 4 MHz is a repo re-derivation, so the comparison mixes supply, clock and load. T5838: 500 uA at 1.8 V, 4.8 MHz | 1.8 V rail: a second LDO plus a 2-bit level translator. T5838: clock must be **4.2-4.8 MHz** (ours is 4.0), so a new clock chain and decimation; its response is plotted only to 50 kHz (above that is unspecified, not shown lost) | **O18/O19/O20:** hardware change, adds parts and size; not a firmware knob. D13 band risk. Measure first (E3/E4) |
| 4 | **Dead time 12.5 -> 25 ns** in the bridge | **-0.3 mA awake** (bus 0.49 -> 0.10-0.20 mA) | Repo SPICE (`sub-output.md`, C3 §5); not re-run by me | Distortion rises (the AD scheme relies on dead-time symmetry) | A TIM1 register, so an O18 knob. Bench decision |
| 5 | **Squelch stops the bridge while awake** | 0.77 mA x squelched fraction | Repo model | Pop-free restart (D17) | None |
| 6 | **FMAC filter accelerator** | **-0.1 to -0.15 mA per 10 Mcycle/s** moved off the CPU | DS13737 Table 72: FMAC 0.92 uA/MHz | Fixed-point FIR work | Only if algorithm B is CPU-tight |

**Do not copy**

| Idea | Why not |
|---|---|
| Buck converter for the 3.0 V rail | **Violates D11.** An ideal 88% buck saves ~9% on average (~0.6 mA of 6.8; the 88% is an assumption). TI's TPS62840 (60 nA-Iq buck) draws **3 mA with no load in forced PWM** (typical, at 3.6 V in / 1.8 V out, SLVSEC6D, March 2020). Power-save mode bursts at a load-dependent rate; by the fact-checker's calculation from TI's equation that falls inside the mic's 20-96 kHz band at our loads (derived, not independently verified). So the objection is in-band spurs, not audible whine |
| Integrated class-D amplifier | TI TPA2011D1 (3.2 W handset class-D amp, 1.21 x 1.16 mm): Iq 1.5 mA typ / 2.3 mA max at 3.6 V, no load (SLOS626B, Nov 2015). Ours: 0.77 mA. It also cannot make a 200 kHz carrier. It is an idle-current reference only |
| Duty-cycling the mic | SPH0641 datasheet (Rev B-1, 2 Dec 2024): sleep 80 uA, wake <= 15 ms, no direct wake into ultrasonic mode, mode change <= 10 ms, cold power-up <= 50 ms. The realistic path is >= 25 ms; bat calls last 2-20 ms. The T5838's activity detector is a low-pass detector, so it cannot wake on ultrasound |
| Ultra-low-power MCU (Ambiq Apollo4 Plus, AMAP42KP-KBR: 4 uA/MHz, 192 MHz, 1.71-2.2 V, 146-pin 5 x 5 mm BGA) | v2 at best: ~-2 mA awake `[Low]`, but a full firmware port, a 1.8 V rail, a BGA, and **unverified** 4 MHz ultrasonic PDM input and dead-time bridge timer. JLC listing C5357190: Extended, $10.24, **stock 0** (checked 2026-10-02) |
| Charging case / mid-day top-up | No case (D18). A spare pair swapped at midday halves the capacity need; it is a chore, the owner's call. The pod already slides off its rail (spec §8 v0.14) |
| Wear detection | Saves only off-head hours; not a size lever |

**Stock note** (JLC parts API queries made by the fact-check pass, 2026-10-02; I did not re-run them): STM32U575CIU6Q (ST Cortex-M33 MCU, JLC C5271013) **8 in stock** at $8.93, so buy spares once (O19). TDK T5838 C7230692: 684 in stock, $3.47. SPH0641LU4H-1 C2879853: 960, $1.99.

---

## 5. Open questions only a measurement can answer

| # | Question | Why it matters | Measure with |
|---|---|---|---|
| 1 | **True mean current per mode and per scene**, not 5-8.5 mA. Especially the exciter line (0.05-2.5 mA) | Sets the cell (lever 1), and decides option A vs B vs C above | E4 (PPK2) with E2 for the drive level |
| 2 | **Mic current at 3.0 V / 4 MHz** (re-derived 1.35 mA; datasheet is 845 uA at 1.8 V / 3.072 MHz) | Decides whether a 1.8 V mic rail is worth a part | E3/E4 |
| 3 | **Idle current in Stop 2**, and whether the **SMPS in its asynchronous Stop mode** is audible against the temple | The -0.45 mA saving is an estimate; D11 requires the listening test | E4, E11 (Stop 2 and 16 MHz Range 3 included) |
| 4 | **Algorithm A cycles on the M33** at 48 MHz | The -0.9 to -1.4 mA clock lever rests on a number marked unverified | Cycle counter (S3) |
| 5 | **Real awake fraction of a day**, in her environments | The 18% quiet-room model against 50-100% near electronics sets the average (and the cell's depth of discharge, 25-50%) | Logging firmware on rev 1 |
| 6 | **MCU sleep floor at 80 MHz Range 2** (1.45 mA is interpolated) | It is larger than all the DSP work | E4 |
| 7 | **LED current** (0.14-0.75 mA on battery) | It moves the 12 h need by ~10 mAh | E4 |
| 8 | **Cell voltage sag under bridge peaks.** Renata gives < 480 mOhm at 30% state of charge; 0.32 A x 0.48 Ohm = 0.15 V (derived), on top of the LDO's dropout at the 3.3-3.4 V knee (ECR-0005) | Decides how much of the last 15% of capacity is usable | E4 with a scope on VBAT |
| 9 | **Cell temperature** against the temple, the dock and the sun (charge window 0-45 C; Renata's sheets give capacity only at 20 C) | The "75% usable" and the 4.1 V longevity advice assume a mild cell; BU-808 warns that heat plus full charge ages cells faster than cycling | Taped NTC on the cell (J9) read by firmware |
| 10 | **Pouch swelling over time** in a bay with no slack | Not quantified in any source I opened | Calipers on the spare cells you age on purpose |

---

## 6. Corrections applied (what changed against the two working notes)

| Claim in the working notes | Correction | Evidence |
|---|---|---|
| Two CP1254-class coin cells match the Renata | **Two give 136-154 mAh, 12-22% less. Three beat it** (204-231 mAh) but need 36.6 mm of cells before a PCM and tabs. Cell height also exceeds the 12 mm bay (Ø12.1-12.2) | Varta CP1254 A4 datasheet 2020-02-18; Renata ICR1254 B2 datasheet V00 03.2024 |
| Grepow 4.2 V coin cells are "level" with our pouch | They are **+11% (LCO) and +26% (NMC)** by box density; only the older Varta A3 at 4.2 V is level | Grepow GRP1254 page (2026-10-01) |
| Charging to 4.10-4.15 V gives 1.5-2x cycles for -10-15% | **~1.25x at 4.15 V (-7%), ~1.6x at 4.10 V (-14%); 2x needs 4.06 V (-19%).** Secondary source, "all values estimated" | BU-808 table, updated 2023-10-11 |
| "No Varta at Digi-Key, TME or LCSC" | Digi-Key and TME confirmed (zero results). The "LCSC" check was only JLC's SMT parts library; **lcsc.com and Mouser are bot-blocked: unverified** | WebFetch searches 2026-10-02; `tools/jlc.py` |
| Sony WF-1000XM4: coin cell "held by pressure contacts, user-swappable" | **Over-read.** The cell is glued, the board is stuck to it, and there are metal contacts; not user-swappable. The "XM3 soldered" row is unsupported | iFixit guide 162365, published 2023-06-25 |
| High-voltage cells "trade away cycle life" | **Unsupported.** Renata's 4.35 V HPMT is rated >500 cycles to 80%, same as the 4.2 V packs. A judgement, not evidence | Renata ICP621333HPMT V01 11/2020 (re-read 2026-10-02) |
| OpenRun cell is +27% denser (371 vs 291 Wh/L) | Not like for like: OpenRun's 5.2 x 11 x 29 mm is **guessed from the "521129" code**; it is a bare cell, ours includes the PCM at max envelope. The label (160 mAh, 3.85 V) is verified from the photo | iFixit 182927 photo, 2025-03-11 |
| Varta "180-210 Wh/kg" | Varta's own datasheets give **137-173 Wh/kg**; the claim holds only against cylinder volume | Varta handbook (2017-12, rev 2018-02) vs brochure Nov 2024 |
| Renata ">500 cycles" so end of life is the same as nominal | Rated to 80% of the **minimum** capacity: **136 mAh, 78% of nominal**; worst-case runtime then ~9.7 h. Aged dimensions are not stated for our pack | Renata ICP501233PA V03 08/2019 |
| Renata coin and 240/270 mAh packs not considered | **Added** (section 3). They were the strongest miss: same vendor, same 35 mm length | renata.com catalogue and datasheets (2026-10-02) |
| ICP401230UPR "fits" | **Not drop-in: 12.7 mm tall against a 12 mm bay** (0.7 mm over) | Renata ICP401230UPR V02 08/2019 |
| Option A: awake 6.76 -> 5.96 mA "firmware only" | **The whole -0.8 mA is the exciter line re-estimated from 1.1 to 0.3 mA nominal: an assumption.** Stop 2 only touches idle. The 25.0 / 16.0 h figures are conditional on that guess; E4 could come in higher | Re-run of the working note's calculation |
| Option B: "105-120 mAh would do" | Omitted the LED (0.55-0.75 mA) and the 2.5 mA exciter ceiling. **The need is ~107-133 mAh**, so 105 mAh fails the worst case. The 13.4 h headline is **12.4-12.5 h with the LED** | `sub-power.md` runtime table |
| "11-14 mm shorter" cell | The 5 mAh/mm rate only holds for the Renata's 5.3 x 12 mm cross-section. Real 100-110 mAh cells are ~4-5 mm shorter. **Volume and mass are the honest units** | Renata and EEMB datasheets |
| Clock floor saves -0.5 to -0.9 mA | **-0.5 to -0.6 mA** on the tables; the rest is algorithm A being cheaper than B, which is itself unverified | DS13737 Rev 8 Tables 39/46 |
| Stop-2 idle: only open issue is the mic clock | Misses that the core SMPS goes asynchronous in Stop; the same noise argument is used against a buck | `A3-u575-plan.md` §4; spec E11 |
| TPS62840 "kills the buck" because of 3 mA | 3 mA is typical, at 3.6 V in / 1.8 V out, not our 3.0 V. Verdict stands; the reason is D11 and in-band spurs | TI SLVSEC6D |
| BEST-transducer papers (+2-10 dB at 1-10 kHz; B81 more efficient) as power levers | **Mis-applied.** They compare audiometric vibrators, not a commodity RC-BC02 exciter; the 1990 paper is about implanted-vs-external gaps. **Dropped as evidence** (Hakansson, JASA 113(2):818-825, 2003; Freden Jansson et al., Int J Audiol 54(5):334-340, 2015; PMID 12597176, 25519145, 2113260) | PubMed abstracts re-read 2026-10-02 |
| "Hearing aids: 31 mW because the mics and regulators take the rest"; "~2-3 mW commercial" | Inference. The ~2-3 mW is Energizer's **cell test profile**, not a measured device. The 1.45 mW chip number is a different workload (beamformer) | EMBC 2023 and TBioCAS 2025 abstracts; Energizer 312 sheet |
| T5838 "loses the band above 50 kHz" | Overstated: **unspecified** above 50 kHz. It also needs a 4.2-4.8 MHz clock (ours 4.0 MHz) | TDK T5838 Rev 1.0, 11 Jun 2022, p.1 and Figs 9-10 |
| Mic duty cycling: "50 ms power-up" | That is the cold power-up; the sleep path is <= 25 ms with an 80 uA floor. Conclusion unchanged | SPH0641 Rev B-1, 2 Dec 2024 |
| 1.8 V mic rail saves 0.3-0.5 mA | Compares unlike supply, clock and load; **a measurement item, not a design lever yet** | `sim/checks/power.py` comment; SPH0641 datasheet |
| Cell density table: LP401230 270 Wh/L | 270 uses nominal name dimensions; on the datasheet's max envelope it is **222 Wh/L**. The table does not show that small cells lose density | EEMB LP401230 sheet (repo copy) |
| AirPods Pro 2/3 capacities (49.7 / 58 mAh) | **Secondary only**: Wikipedia's template, no cited source; Apple publishes none | Apple pages; Wikipedia raw template |
| 8-16x smaller bud cells than the case | Loose: 7.5-22x from the cited numbers; Apple's own teardown says ~16x for AirPods; Galaxy Buds is ~5x | iFixit 75578, 127551, 121471, 120693 |
| (missing) | **Added:** Nuance Audio hearing-aid glasses as the closest commercial analogue (8 h / 10+ h, no mAh) | nuanceaudio.com (2026-10-02) |

---

## 7. Could not verify, or not opened

- Ray-Ban Meta, Oakley Meta, Echo Frames cells. Hearing-aid cell capacities (Phonak: "up to 56 hours" only). Shokz capacities other than the OpenRun label and Trekz Titanium (no mAh on any Shokz page).
- Vendor TWS chip currents (Qualcomm QCC51xx, Airoha AB15xx, Bestechnic BES2xxx, Realtek RTL87xx): pages 404 or JavaScript-only, figures NDA-only. onsemi Ezairo 7100/8300 (HTTP 403), MAX98357A (timeout), STM32U3 page (timeout).
- Pin-cell datasheets (EVE, Grepow list none). Silicon-anode cells (Enovix: no wearable data, newsroom HTTP 403).
- Mouser and lcsc.com stock for any coin cell (bot-blocked). Renata MOQ, price, lead time for any pack (no public price). Grepow MOQ and sample terms.
- Renata's "Tabbed Lithium Coin Cells" category (exists on renata.com/en/products; not opened). Grepow's custom-shape and 4.4 V narrow cells (GRP8511047 430 mAh, GRP4609021 88 mAh at ~407 Wh/L per the fact-checker's read of the Grepow ultra-narrow page; not re-opened by me).
- Aged thickness of the ICP501233PA-02, and capacity of the HPMT at 4.2 V.
- **The magnetic dock connector** (the other big size driver) is outside this research: no earbud, headset or glasses source I opened gives a connector size or contact design worth copying.
- Skin-contact temperature and cold-weather capacity (no primary source opened).

## Sources (read dates)

- Renata: product catalogue https://www.renata.com/en/products/lithium-polymer-batteries/ and https://www.renata.com/en/products/rechargeable-lithium-coin-cells/ (2026-10-02). Datasheets (renata.com/en/downloads/?product=...): ICP501233PA-02 V03 08/2019, ICP621333PA-01 V03 10/2019, ICP621333HPMT V01 11/2020, ICR1254 B2 V00 03.2024 (2026-10-02); ICP401230UPR V02 08/2019 (cached 2026-09-30). UN 38.3 transport summaries for ICP501233PA-02 (test 2017-01-14), ICP621333PA-01 (test 2017-04-05), ICP621333HPMT (test 2022-10-26) (2026-10-02).
- iFixit: AirPods teardown 75578 (2016-12-20); AirPods 2 121471 (2019-03-29); AirPods Pro 127551 (2019-10-31); Pixel Buds 2 133888 (2020-05-26); AfterShokz Trekz Titanium 144329 (2021-08-06); Shokz OpenRun 182927 (2025-03-11); Bose Frames Alto battery guide 202556 (2025-12-10); Sony WF-1000XM4 guide 162365 (2023-06-25); Galaxy Buds teardown 120693 (case 1.03 Wh, per the fact-check). Read 2026-10-01, spot-checked 2026-10-02.
- Apple: https://support.apple.com/en-us/111851; https://www.apple.com/airpods-pro/specs/ (2026-10-01, 2026-10-02). Wikipedia Template:AirPods_technical_specifications (2026-10-01, secondary).
- Nothing: https://nothing.tech/products/ear-open (2026-10-01, 2026-10-02). Shokz: shokz.com/products/openrun, /openrunpro2, /openfit, /openmove, /pages/comfort-tech (2026-10-01, 2026-10-02). Nuance Audio: https://www.nuanceaudio.com/en-us/c/frame-battery-life-guide (2026-10-02). Phonak: https://www.phonak.com/en-us/hearing-devices/hearing-aids/audeo-sphere (2026-10-01).
- Varta CoinPower brochure Nov 2024; CP1254 A4 datasheet 2020-02-18; CoinPower Handbook 2017-12 rev 2018-02 (cached 2026-09-30). Grepow GRP1254 and ultra-narrow pages (2026-10-01). Battery University BU-808, updated 2023-10-11 (2026-10-01; secondary).
- Datasheets: TI BQ25180 SLUSE99C (Jan 2023); TI TPS62840 SLVSEC6D (Mar 2020); TI TPA2011D1 SLOS626B (Nov 2015); Syntiant SPH0641LU4H-1 Rev B-1 (2 Dec 2024); TDK T5838 Rev 1.0 (11 Jun 2022); ST DS13737 Rev 8 (Aug 2023); ABLIC S-8261 Rev 5.5_00 (2023); Energizer 312 form 312GL0318; Ambiq Apollo4 Plus page (2026-10-01).
- Papers (abstracts via PubMed): Karrenbauer et al., IEEE EMBC 2023, doi 10.1109/EMBC40787.2023.10340206; IEEE TBioCAS 19(3):669-685, 2025, doi 10.1109/TBCAS.2024.3481044.
- Repo: `docs/spec.md` §7, §8, D11, D18, O16-O20, E4, E11; `docs/system/sub-power.md`, `sub-output.md`, `physical.md`; `sim/checks/power.py` rev 2; `docs/research/A3-u575-plan.md` §1.3, §4, §5; `docs/build/bom.md` (Renata sourcing, 2026-10-01).
- JLC parts API stock checks by the fact-check pass, 2026-10-02 (STM32U575CIU6Q C5271013, T5838 C7230692, SPH0641LU4H-1 C2879853, AMAP42KP-KBR C5357190).
- Not used as evidence: the three BEST-transducer papers cited in `power.md` (see section 6).
