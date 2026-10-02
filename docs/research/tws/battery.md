# Batteries and form factors in TWS earbuds, bone-conduction headsets, audio glasses and hearing aids

Research note, 2026-10-01 (read-only research run; nothing in the spec, schematic or CAD changed).
Question: is there a cell that does better than our **Renata ICP501233PA-02** (3.7 V Li-ion polymer pouch pack, 175 mAh, PCM built in, ≤ 5.3 × 12 × 35 mm, ~4.2 g) in the pod's battery bay? How do small wearables keep their cells small?

## Bottom line (blunt)

1. **There is no hidden cell type that is 2× better.** Small pouch packs with protection run at **~250–320 Wh/L**. Our Renata pack is **291 Wh/L**, normal for the class. Steel-can coin cells (Varta CoinPower) reach **~330–380 Wh/L** in their bounding box at a 4.3 V charge. High-voltage (3.85 V nominal, 4.35–4.48 V charge) cells reach **~370–470 Wh/L**, but they pay for it in cycle life.
2. **Earbuds stay small by carrying very little energy, not by better chemistry.** AirPods: 93 mWh per bud. AirPods Pro: 160 mWh. Galaxy Buds and Pixel Buds 2: ~200 mWh. A pocket case carrying 1.5–2 Wh refills them. **Our pod already carries 0.65 Wh per side**, more than the whole Shokz OpenRun headset (0.62 Wh). Earbud makers win on power draw and a charging case. Neither option is open to us (no case: we dock nightly).
3. **The real design constraint is the bay, not the chemistry.**
   - **Long and thin:** the vision line (front) and the ear hook (rear) fix the pod's length at ~35–38 mm (spec §8, v0.9). A long, thin temple-arm cell (Bose Frames style, 4 × 9 × 45 mm) does not fit, and holds only 0.4 Wh.
   - **Pin cells:** in our 5.3 × 12 × 35 mm bay, two Ø5.3 mm cylinders need **≥ 420 Wh/L at cell level** just to tie the Renata. I found no primary source showing any Ø ≈ 5 mm pin cell near that.
4. **Recommendation: keep the Renata 175 mAh pack** and spend effort on longevity, not on a cell swap:
   - set the charge voltage to **~4.10–4.15 V** (BQ25180 register, 10 mV steps);
   - keep the BQ25180's recharge hysteresis (no trickle charging);
   - buy spares, and keep the 2-wire solder replacement.
   - **Why longevity matters more:** at 500 rated cycles, a cell charged every day reaches its 80 % point in ~1.4 years if every cycle were full-depth (Renata spec). Our real daily depth is ~25–50 %, which helps.
5. **Coin cells are the only credible alternative**, and are not worth it for rev 1:
   - 2–3 × CP1254-class cells in parallel, with an external PCM;
   - same energy at 4.2 V, ~+20 % at Varta's 4.3 V rating;
   - steel can: robust, no swelling;
   - but genuine Varta cells are **not stocked at Digi-Key, TME or LCSC** (2026-10-01).

## Glossary of the part numbers used here
- **ICP501233PA-02** (Renata): Li-ion polymer pack. The IEC 61960 style name "ICP" means Li-ion, cobalt-family cathode, prismatic; "50/12/33" are approximate thickness (×0.1 mm) / width / length in mm. "PA-02" is the pack variant with protection board and wire leads.
- **ICP401230UPR** (Renata): 4.5 × 12.7 × 31 mm, 130 mAh pack with protection circuit.
- **ICP501230** (Renata): 5.5 × 12 × 30 mm, 135 mAh cell. Protection "on request".
- **CP1254, CP1454, CP1654, CP1154, CP1240** (Varta CoinPower): rechargeable Li-ion coin cells. The digits are diameter (12/14/16/11 mm) and height (5.4 / 4.0 mm). A3, A4 and A4X are product generations; per the 2024 brochure, A4X charges to 4.3 V.
- **LIR1254 / LIR1454**: generic (non-Varta) name for 12 × 5.4 / 14 × 5.4 mm rechargeable Li-ion coin cells.
- **GRP1254 / GRP220550 / GRP210436 / GRP5811047** (Grepow, a Chinese cell maker): coin-cell and ultra-narrow pouch models. The pouch numbers encode thickness × width × length.
- **AEC 521129 / AEC 531236**: pouch cells in Shokz headsets. "AEC" is the maker code. The digits read as 5.2 × 11 × 29 and 5.3 × 12 × 36 mm (size-code reading, not a datasheet).
- **AHB330945PST-01** (Synergy): pouch pack in Bose Frames Alto. Labelled 1ICP4/9/45, i.e. ≤ 4 × 9 × 45 mm.
- **PCM** (protection circuit module): a tiny board with a protector IC plus a dual MOSFET. It disconnects the cell on over-charge, over-discharge, over-current or short circuit. It is independent of the charger.
- **S-8261** (ABLIC, formerly Seiko Instruments): single-cell Li-ion protector IC, SOT-23-6.
- **BQ29700 / BQ29707** (TI): single-cell protector ICs.
- **BQ25180** (TI): our linear charger with power path.
- **Wh/L**: energy per litre of bounding box. For a coin cell I give both the true cylinder volume and its square bounding box, because a box is what the bay is.

## 1. What real devices carry (teardowns and maker pages)

| Device | Cell | Energy / capacity | Where it sits | Source (accessed) |
|---|---|---|---|---|
| AirPods (1st gen, 2016) | cylindrical pin cell in the stem, spot-welded tabs | **93 mWh** per bud; case 398 mAh / 1.52 Wh, 3.81 V | stem | iFixit AirPods teardown, published 2016-12-20, steps 3, 9, 15: https://www.ifixit.com/Teardown/AirPods+Teardown/75578 (API read 2026-10-01) |
| AirPods 2 (2019) | same 93 mWh cell | 93 mWh | stem | iFixit AirPods 2 teardown, 2019-03-29, step 7: https://www.ifixit.com/Teardown/AirPods+2+Teardown/121471 (2026-10-01) |
| AirPods Pro (2019) | **Varta CP1154** coin cell, 3.7 V, soldered cable | **0.16 Wh** per bud; case 2 cells, 1.98 Wh | head of the bud | iFixit AirPods Pro teardown, 2019-10-31 (edited 2024-05-23), steps 8, 15: https://www.ifixit.com/Teardown/AirPods+Pro+Teardown/127551 (2026-10-01) |
| Samsung Galaxy Buds (2019) | **Varta CP1254** coin cell | **200 mWh** (iFixit) | clip-in plastic battery housing, push-out holes | same AirPods Pro teardown, step 8; Galaxy Buds battery guide https://www.ifixit.com/Guide/Samsung+Galaxy+Buds+Battery+Replacement/127556 step 9 (2026-10-01) |
| Google Pixel Buds 2 (2020) | **Varta CP1240 A3**, 3.7 V | **0.2 Wh** | stack under main PCB | iFixit teardown, 2020-05-26, step 16: https://www.ifixit.com/Teardown/Google+Pixel+Buds+2+Teardown/133888 (2026-10-01) |
| Sony WF-1000XM3 | Varta CP1254 A3 (iFixit's linked replacement part) | n/a | soldered to board | https://www.ifixit.com/Guide/Sony+WF-1000XM3+Battery+Replacement/144994 (2021-09-25; 2026-10-01) |
| Sony WF-1000XM4 | coin cell held by **pressure contacts**, no solder | n/a | under the board, "negative terminal up" | https://www.ifixit.com/Guide/Sony+WF-1000XM4+Wireless+Earbuds+battery+replacement/162365 steps 8–11 (2023-06-25; 2026-10-01) |
| Nothing Ear (1) (2021) | button cell, soldered | n/a | outer half of the head | https://www.ifixit.com/Teardown/Nothing+Ear+(1)+Teardown/145624 steps 5, 7 (2021-11-15; 2026-10-01) |
| **AfterShokz Trekz Titanium** (bone conduction) | pouch, label "AEC 531236", "Li-polymer, 0.74 Wh, 4.2V", "200 mAh, 3.7 V" | **200 mAh / 0.74 Wh** for the whole headset | one rear pod (left) | https://www.ifixit.com/Teardown/Aftershokz+Trekz+Titanium+Teardown/144329 step 8 (2021-08-06; 2026-10-01) |
| **Shokz OpenRun** (bone conduction) | pouch with PCM tab, label **"AEC 521129, 160mAh 3.85V"** (read by me from the teardown photo) | **160 mAh × 3.85 V = 0.62 Wh** whole headset; maker claims "8-Hour Battery Life" | one rear pod | photo: https://guide-images.cdn.ifixit.com/igi/S5VrFoRg6wJqlUSg.large in https://www.ifixit.com/Teardown/Aftershoks+OpenRun+Teardown/182927 step 3 (2025-03-11; 2026-10-01); claim: https://shokz.com/products/openrun (2026-10-01) |
| Shokz OpenRun Pro 2 | not stated | "up to 12 hours … thanks to a larger, weight-optimized battery" | n/a | https://shokz.com/products/openrunpro2 (fetched 2026-09-30 by an earlier session; re-read 2026-10-01) |
| Shokz OpenFit (open earbud) | not stated (no mAh on page) | 7 h per charge; earbud 8.3 ± 0.2 g | "drivers and battery at the ends of the hooks" for balance | https://shokz.com/products/openfit (2026-10-01); https://shokz.com/pages/comfort-tech (fetched 2026-09-30, re-read 2026-10-01) |
| **Bose Frames Alto** (audio glasses) | **long thin pouch pack in the temple arm**, label "SYNERGY … AHB330945PST-01 3.7V 110mAh 0.4Wh … Ucl:4.2Vdc 1ICP4/9/45" (read by me from the guide photo) | **110 mAh / 0.4 Wh**, ≤ 4 × 9 × 45 mm. Third (white) wire goes to a "BMS board" | left earpiece (temple), taped next to the hinge, beside the speaker | https://www.ifixit.com/Guide/Bose+Frames+Alto+Battery+Replacement/202556 steps 5–8 and photo https://guide-images.cdn.ifixit.com/igi/JIT4QQZsOojpb6xM.full (guide 2025-12-10; read 2026-10-01). Whether the right arm also has a cell: **not stated** |
| Ray-Ban Meta / Oakley Meta | **not found** | – | – | meta.com returns HTTP 400 to automated reads, and iFixit has no teardown (2026-10-01). **Unverified, no data** |
| Hearing aids (Phonak Audéo Infinio Ultra Sphere) | Li-ion (capacity not stated) | "up to 56 hours of battery life*" | – | https://www.phonak.com/en-us/hearing-devices/hearing-aids/audeo-sphere (2026-10-01). **Cell capacities for hearing aids not found in an opened source** |

**What the table says:**
- Earbuds carry **0.09–0.2 Wh per bud**: AirPods-class pin cells, or 11–12 mm coin cells.
- Bone-conduction headsets carry **0.6–0.75 Wh for the whole headset**, in one 5 × 11–12 × 29–36 mm pouch.
- Audio glasses use a **≤ 4 × 9 × 45 mm, 0.4 Wh pouch** lying along the temple.
- **Our 0.65 Wh per side is at the top of all of these.**

## 2. Cell types and energy density

Computed by me from the maker's capacity × nominal voltage ÷ the maker's (maximum) envelope. Script: scratchpad `bat/dens.py`, run 2026-10-01.

| Cell (gloss above) | mAh / V nom / charge V | Envelope (mm) | Wh | **Wh/L (box)** | Wh/kg | Source |
|---|---|---|---|---|---|---|
| **Renata ICP501233PA-02 (pack, PCM inside)** | 175 / 3.7 / 4.2 | ≤ 5.3 × 12 × 35 | 0.647 | **291** | 154 | Renata spec Rev V03 08/2019: https://www.renata.com/en/downloads/?product=icp501233pa-02&fileid=7abf6afc8d36a1c32abedc0003 (fetched 2026-10-01) |
| Renata ICP401230UPR (pack, PCM) | 130 / 3.7 / 4.2 | ≤ 4.5 × 12.7 × 31 | 0.481 | 271 | 137 | Renata spec Rev V02 08/2019: https://www.renata.com/en-us/downloads/?product=icp401230upr&fileid=c3ffa3e27d8b9b28a9de2a7c18 (fetched 2026-09-30) |
| Renata ICP501230 (cell, PCM on request) | 135 / 3.7 / 4.2 | ≤ 5.5 × 12 × 30 | 0.499 | 252 | 151 | https://www.renata.com/en-us/downloads/?product=icp501230&fileid=5c6a1e3d01c0b698c6b4e49d62 (fetched 2026-09-30) |
| EEMB LP401230 | 100 / 3.7 | ≤ 4.3 × 12.5 × 31 | 0.370 | 222 | 185 | `docs/research/B-parts-selection.md` §7 (EEMB spec 2022-10-19) |
| Bose Frames Alto pack | 110 / 3.7 / 4.2 | ≤ 4 × 9 × 45 (IEC label) | 0.407 | 251 (305 if 3.3 mm thick) | – | iFixit photo above |
| Shokz OpenRun AEC 521129 | 160 / **3.85** (high-voltage) | 5.2 × 11 × 29 (size-code reading) | 0.616 | **371** | – | iFixit photo above; dimensions **unverified** (inferred from the code) |
| Trekz Titanium AEC 531236 | 200 / 3.7 | 5.3 × 12 × 36 (size-code reading) | 0.74 | 323 | – | iFixit step 8; dimensions **unverified** |
| Grepow GRP220550 ("narrow temples" for glasses) | 47 / ~3.8 / 4.35 | 2.38 × 5.6 × 50 | 0.179 | 268 | – | https://www.grepow.com/wearables/smart-glasses.html (2026-10-01) |
| Grepow GRP210436 | 19.2 / ~3.8 / 4.35 | 2.16 × 4 × 36.5 | 0.073 | 231 | – | same; and https://www.grepow.com/shaped-battery/ultra-narrow-battery.html (2026-10-01) |
| Grepow GRP5811047 (high-rate, 20C) | 200 / 3.7 / 4.2 | 5.6 × 11 × 47 | 0.74 | 256 | – | ultra-narrow page above |
| **Varta CP1254 A4X** | 74 / 3.7 / **4.3** | Ø12.1 × 5.4 | 0.274 | **346** (441 cylinder) | 152 | Varta CoinPower brochure, Nov 2024: https://www.varta-ag.com/fileadmin/varta/industry/downloads/products/lithium-ion-cells/VARTA_CoinPower_EN_digital_221124_A5_6p.pdf (fetched 2026-09-30) |
| Varta CP1454 A4X | 108 / 3.7 / 4.3 | Ø14.1 × 5.4 | 0.400 | 372 (474) | 166 | same |
| Varta CP1654 A4X | 145 / 3.7 / 4.3 | Ø16.1 × 5.4 | 0.536 | 383 (488) | 173 | same |
| Varta CP1454 A3 (older, 4.2 V) | 85 nom / 3.7 / 4.2 | Ø14.1 × 5.4 | 0.315 | 293 (373) | 137 | Varta datasheet 2018-01-15: https://datasheet.octopart.com/63145201013-Varta-datasheet-145015682.pdf (fetched 2026-09-30) |
| Grepow GRP1254M1 (NMC) | 77 / 3.7 / 4.2 | Ø12 × 5.4 | 0.285 | 366 (466) | 158 | https://www.grepow.com/button-cell-battery/grp1254-g1-75mah.html (2026-10-01) |
| Grepow GRP1254RL (LCO) | 68 / 3.7 / 4.2 | Ø12 × 5.4 | 0.252 | 324 (412) | 140 | same |
| Grepow GRP1254NI1 | 96 / 3.83 / **4.48** | Ø12 × 5.4 | 0.368 | **473** (602) | 184 | same (page claims "up to 556Wh/L") |
| Varta CoinPower family (maker claim) | – | – | – | **370–410 Wh/L**, 180–210 Wh/kg | – | Varta CoinPower Handbook (2017-12, rev. 2018-02) §1.1: https://www.weisbauer.de/fileadmin/news/varta/180301/coinpower_hb.pdf (fetched 2026-09-30) |

Box Wh/L, sorted (`#` = 25 Wh/L):

```
Grepow GRP1254NI1 4.48V coin  473 |###################
Varta CP1654 A4X 4.3V coin    383 |###############
Shokz OpenRun 3.85V pouch     371 |###############
Varta CP1254 A4X 4.3V coin    346 |##############
Grepow GRP1254RL 4.2V coin    324 |#############
Trekz Ti 4.2V pouch           323 |#############
Renata ICP501233PA-02 (ours)  291 |############   <- pack incl. PCM
Grepow GRP220550 narrow       268 |###########
Bose Frames Alto pouch        251 |##########
EEMB LP401230                 222 |#########
```

**Why the numbers come out this way:**
- **The fixed overhead dominates small cells.** A pouch loses its sealed edge, its tabs and its PCM board; a coin cell loses its can wall and gasket. The smaller the cell, the larger that fraction.
  - Varta: the steel two-part can and foil gasket give "the most efficient use of the space inside the cell" (handbook §1.5).
  - The Renata figure already includes its PCM. The coin-cell figures don't: a coin cell still needs a PCM somewhere, so it is not a free +20 %.
- **Charge voltage is the other knob:**
  - Varta A4X cells are rated at a **4.3 V** charge (brochure: "Maximum-charge voltage for A4X and A5X Generation: 4.3 V").
  - The CP1254 A4 datasheet gives 70 mAh nominal "at 0.2C from 4.3 V to 3.0 V" (2020-02-18, https://www.elektronik.ropla.eu/pdf/stock/vmb/cp1254a4.pdf, fetched 2026-09-30).
  - Grepow's 4.2 V coin cells (68–77 mAh) land at the same box density as our pouch.
- **Pin cells:** the only number opened is Apple's 93 mWh per stem. EVE's and Grepow's sites list no pin-cell specs (EVE consumer page, 2026-10-01: no model data; Grepow TWS page lists only coin cells). Pin-cell density at Ø ≈ 5 mm is **unverified**.
- **Silicon-anode cells:** not opened. The Enovix site lists no wearable specs, and its newsroom returns HTTP 403 (2026-10-01). Not buyable in ones as far as I could see. **Unverified.**

## 3. How glasses put the cell in the arm
- **Bose Frames Alto:**
  - one long, thin pouch pack (≤ 4 × 9 × 45 mm, 110 mAh), lying flat inside the left temple beside the speaker;
  - held by double-sided tape at the hinge end only;
  - three wires: + and − to the board, a third (white) to the "BMS board", probably a thermistor or ID line (the guide doesn't say);
  - the cover is glued (iFixit 202556).
- **Grepow's "smart glasses" page:** sells "ultra narrow" pouches for "narrow temples" (2.38 × 5.6 × 50 mm, 47 mAh; 2.16 × 4 × 36.5 mm, 19 mAh), all at 4.35 V charge. Its narrowest stated width is "4.1 mm".
  - These are tiny-energy cells: the 50 mm one holds 0.18 Wh, a quarter of ours.
- **Shokz:** the cell goes in a rear pod behind the ear. On OpenFit, the battery sits "at the ends of the hooks" to balance weight. That's the same balance logic as our D18. We can't copy the location, because nothing may sit behind the ear (§1.2.4).

## 4. Fit in our pod: three real options

The bay today (`hw/mech/shell_r1.py` `CELL`, via `docs/system/physical.md`) is 35 (along the arm) × 5.3 (thickness) × 12 (height) mm. Runtimes use the sub-power model: full chain awake 9.8 mA pessimistic + LED 0.75 mA, 75 % usable; nominal 6.8 + 0.55 mA, 85 % usable.

| Option | Energy | Fits the bay? | Pessimistic always-on + LED / nominal | Notes |
|---|---|---|---|---|
| **A. Keep Renata ICP501233PA-02** (recommended) | 175 mAh, 0.65 Wh | exact | **12.4 h / 20.2 h** | PCM inside. 1C charge, 2C pulse = 350 mA, which covers the ~315 mA bridge peaks. >500 cycles to 80 % of minimum capacity (0.5C/0.5C). No public price (bom.md, 2026-10-01) |
| A′. Same cell charged to ~4.10 V (BQ25180 VBATREG) | ≈ 0.85–0.9 × 175 ≈ 150–155 mAh (BU-808 table, secondary) | exact | ≈ 10.8 h / 17.6 h | Roughly **doubles cycles** per BU-808 (secondary). Still above 8 h worst case. Firmware-only change |
| **B. 2–3 × CP1254-class coins in parallel + external PCM** | 2 × ~68–74 = 136–148 mAh; 3 × = 204–222 mAh | **no** (as-is): Ø12.1 > 12.0 bay height; 5.4 (+0.2) > 5.3 bay thickness; 3 in a row = 36.3 mm > 35 | 2×: 9.7–10.5 h; 3×: **14.5 h** / 23.6 h | Needs the bay ~0.5 mm thicker, plus tab welds and a PCM board. One CP1254 is rated **140 mA continuous / 210 mA pulse (2 s)**, so a single cell can't feed 315 mA bridge peaks; two or more in parallel can. Steel can, no swelling. **Availability is the killer** (§5) |
| C. Thinner pack, e.g. Renata ICP401230UPR | 130 mAh, 0.48 Wh | yes; 0.8 mm thinner, 4 mm shorter | 9.2 h / 15.0 h | Buys ~0.8 mm of pod thickness and 4 mm of length for −26 % energy. Meets the 8 h minimum with ~1 h margin |
| (rejected) Long thin Bose-type ≤ 4 × 9 × 45 | 110 mAh | **no**: 45 mm > 35 mm usable length | 7.8 h / 12.7 h | Misses the 8 h minimum at the pessimistic end. The vision line and ear hook (spec §8 v0.9) leave no extra length |
| (rejected) 2 pin cells Ø5.3 × 35 | ? | geometry only | – | Two cylinders fill 1.54 cm³ of the 2.23 cm³ bay. Tying the Renata needs ≥ 420 Wh/L at cell level. No source shows a Ø5 mm pin cell anywhere near that |
| (rejected) Ultra-narrow glasses pouches (Grepow GRP220550) | 47 mAh | yes, ×2 side by side | < 4 h | Built for a different problem: hiding a cell inside a 6 mm-wide frame temple |

## 5. Can a hobbyist buy these in ones or tens? (checked 2026-10-01)
- **Varta CoinPower:**
  - Digi-Key search "varta coinpower": **no results** (https://www.digikey.com/en/products/result?keywords=varta%20coinpower).
  - TME search "CP1254": **no products** (https://www.tme.eu/en/katalog/?queryPhrase=CP1254).
  - JLC/LCSC parts API: no rechargeable coin cells under "CP1254", "LIR1254", "VARTA" or "LIR2450" (query 2026-10-02T00:56Z UTC = 2026-10-01 20:56 local).
  - Mouser: page timed out; **unverified**.
  - Varta sells through industrial distributors (the datasheets above came from Ropla PL, Texim Europe and Weisbauer DE); buying in ones there is **unverified**.
- **Aftermarket coins:**
  - iFixit sells "LIR1254" replacement pairs at **$14.99** ("aftermarket", 3.6 V, no capacity or datasheet; "Shipping restrictions apply"): https://www.ifixit.com/products/samsung-galaxy-buds-and-buds-live-replacement-batteries.
  - The same for LIR1454 at $14.99: https://www.ifixit.com/products/galaxy-buds-plus-batteries.
  - Buyable, but **no datasheet**, so not acceptable for a cell worn on the head for years.
- **Grepow:** B2B; no MOQ or sample price on any page opened. **Unverified** for ones.
- **Renata:** distributor quote only, no public price, not on Digi-Key (`docs/build/bom.md`, 2026-10-01).
- **Pouch packs with PCM in ones:** the Adafruit #1570 (100 mAh, 3.8 × 11.5 × 31 mm, PCM, **$5.95**, in stock: https://www.adafruit.com/product/1570, cached 2026-09-30) remains the easiest to buy. The EEMB standard list includes LP401230 (100 mAh), LP501230 (140 mAh) and LP401745 (250 mAh): https://www.eemb.com/products-55 (2026-10-01).
- **Shipping:** lithium cells ship as dangerous goods, hence the iFixit "Shipping restrictions apply" note.

## 6. Safety, protection and charging limits
- **A PCM is mandatory for a bare cell.**
  - Varta, on every CoinPower datasheet: "Cell must not be used without external safety electronics (PCM – Protection Circuit Module)!"
  - Required functions (handbook §7.3): over-charge, over-discharge, over-current and short-circuit protection.
  - Varta's recommended PCM ICs: Seiko (now ABLIC) S-8211C / S-8200A, Mitsumi MM3077 / MM2511, TI BQ29700 / BQ29707, Diodes AP9211.
  - Example protector **ABLIC S-8261** (Rev.5.5_00, 2023; https://www.ablic.com/en/doc/datasheet/battery_protection/S8261_E.pdf, fetched 2026-09-30):
    - over-charge detection settable 3.900–4.500 V in 5 mV steps, ±25 mV;
    - over-discharge 2.0–3.0 V;
    - 3.5 µA typ.;
    - SOT-23-6, plus a dual MOSFET.
  - The Renata pack already has a "Safety Circuit: Yes".
- **The charger is not a PCM.** The BQ25180 (SLUSE99C, Jan 2023) is a good first line, but it is the same chip that could misbehave:
  - battery undervoltage lockout (default 3.0 V, settable 2.0–3.0 V);
  - battery over-current protection (0.5 / 1 / 1.5 A or disabled);
  - charge voltage 3.5–4.65 V in 10 mV steps;
  - recharge threshold 100 or 200 mV below regulation.
  - Keep the PCM as the independent second layer.
- **Charge window: 0–45 °C** for Renata and all Varta CoinPower types. Varta's rapid charge (2C) is allowed only up to 4.0 V and only at ≥ 15 °C (CP1254 A4 / CP1454 A3 footnote 3). `docs/system/sub-power.md` already flags the BQ25180's default 60 °C hot threshold as unsafe for this cell.
- **No trickle or float charging** (Varta handbook §8.2):
  - stop at ~0.02C;
  - restart only after a measurable discharge, or when the cell has fallen below 4.0 V.
  - The BQ25180's termination plus its 100/200 mV recharge threshold satisfies this. **Keep it enabled for a pod that sits in its dock all night.**
- **Over-discharge:** recharge stored cells periodically, keeping them at 3–3.8 V. A deeply discharged cell must be pre-charged at 0.01–0.07C for 15–30 min (handbook §8.3; the BQ25180 has a pre-charge phase).
- **Cycle life** (all rated 0.5C charge / 0.5C discharge at room temperature):
  - Renata ICP501233PA-02: > 80 % of minimum capacity after 500 cycles.
  - Renata ICP401230UPR and ICP501230: the same.
  - Varta CP1254 A4 and CP1454 A3: > 500 cycles to > 80 %.
  - Grepow: "800+" (TWS page) and "Up to 1000+" (GRP1254 page); maker claims, conditions not stated.
- **Daily charging over years** (BU-808 is a secondary source, Battery University, updated 2023-10-11, https://batteryuniversity.com/article/bu-808-how-to-prolong-lithium-based-batteries; values "estimated"):
  - **Charge voltage vs cycles:**
    - 4.20 V: 300–500 cycles, 100 %;
    - 4.13 V: 400–700, 90 %;
    - 4.06 V: 600–1,000, 81 %;
    - 4.00 V: 850–1,500, 73 %.
  - **Depth of discharge, NMC:** 100 %: ~300 cycles; 60 %: ~600; 40 %: ~1,000; 20 %: ~2,000.
  - **Our daily depth** (sub-power model, 12 h worn, LED on): **50 %** if never idle, **35 %** at half idle, **25 %** in a quiet room. So the cell ages far slower than "500 full cycles = 1.4 years" suggests.
  - Heat and dwelling at full charge stress the cell more than cycling (BU-808). A warm dock at 4.2 V all night is the worst case.

## 7. Techniques worth copying (and not)
1. **Lower the end-of-charge voltage.**
   - Firmware only: BQ25180 VBATREG = 4.10–4.15 V.
   - About −10–15 % capacity for ~1.5–2× cycles (BU-808, secondary).
   - Worst-case runtime stays ≥ 10.8 h.
   - **Copy this.**
2. **Serviceable cell mounting.**
   - Sony WF-1000XM4: the coin cell sits on spring/pressure contacts with no solder.
   - Galaxy Buds: the cell sits in a clip-in plastic housing with push-out holes.
   - For us, with a pouch: a 2-wire solder joint at J5/J6 with slack is already planned. A tiny 2-pin connector would make swaps solder-free; it costs ~1–2 mm. **Owner's call.**
3. **Steel-can coin cells for robustness.** No swelling, very stiff can (Varta handbook §1.5). Worth it only if Varta cells become obtainable in ones. **Not for rev 1.**
4. **High-voltage chemistry** (3.85 V nominal, 4.35–4.48 V charge).
   - +15–60 % box density in the examples above (Shokz OpenRun cell 371 Wh/L; Grepow GRP1254NI1 473 Wh/L).
   - Charged to 4.4 V, it trades cycle life away. Charged to 4.2 V, it is roughly a standard cell.
   - **Don't** for a years-long daily device.
5. **Tiny cells plus a charging case** (every TWS bud). Not applicable: no case, nightly dock (spec D18).
6. **Battery placed for balance** (Shokz OpenFit hooks; our D18 "cell just before the ear hook"). Already done.

## 8. What I could not verify (labelled, not guessed)
- Ray-Ban Meta, Oakley Meta and Echo Frames cells: no source opened (meta.com HTTP 400; no iFixit teardown).
- Hearing-aid cell capacities: none opened. Phonak gives only "up to 56 hours".
- Pin-cell (TWS stem) dimensions and density: only Apple's 93 mWh is known.
- Silicon-anode cells (Enovix and others): no spec opened.
- Mouser stock of Varta CoinPower; Varta distributors' minimum orders; Grepow sample terms.
- The Shokz AEC cell dimensions (inferred from the size code) and whether the Bose Frames' right arm also holds a cell.
- Note: the web-search budget for this session was exhausted before this run, and the Consensus paper search was out of quota. Everything above comes from direct maker, distributor and iFixit URLs and from datasheets cached by earlier sessions on 2026-09-30, re-read 2026-10-01.
