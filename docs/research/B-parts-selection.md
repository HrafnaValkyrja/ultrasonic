# B — Parts selection for the product board (B1–B6, B8)

> **Superseded in parts (banner 2026-10-07, reg-arm 7 / DK-13 / UI-9 / DBG-10):** SW1 is now KMT022NGJLHS (not KXT321LHS), the charger BQ25180 (not MCP73831): MZ-2 BOM hw/pod/bom_jlc_mz2.csv. Current truth: `hw/current.yaml` and `docs/system/`. Kept as history; do not build from the superseded parts.

**Date:** 2026-09-30 (Claude Code session). **Status:** recommendations only. The owner decides every line (spec §0 rule 4).
**Machine-readable lock:** `.pcba-workflow/sourcing-lock.csv` has one row per option, with LCSC number, library class, stock, price and query time.
**Stock and price:** from the JLC parts API (`tools/jlc.py`), queried 2026-09-30 between 06:29 and 06:49 UTC. Prices are qty-1 USD. Stock changes daily, so re-check before ordering.
**Context:** a 20×10 mm board per side with parts on both sides. It carries the STM32U575CIU6Q MCU, the SPH0641LU4H-1 mic, a 3.0 V LDO, the MCP73831 charger, and a 2-level H-bridge driving an 8–12 Ω bone transducer at 200 kHz.

---

## Summary: what I recommend

| # | Function | Recommendation | What it is | Class | Runner-up |
|---|---|---|---|---|---|
| 1 | 3.0 V LDO | **TPS7A2030PDQNR** (C5220164) | TI 300 mA ultra-low-noise LDO, 1×1 mm | Ext | RT9080-30GJ5 (C965900) if bridge peaks exceed ~300 mA |
| 2 | Bridge MOSFET pairs (×2) | **PMCXB290UEZ** (C19654206) | Nexperia complementary N+P pair, 1.1×1.0 mm | Ext | DMC2400UV-7 (C177025), genuine but only 113 in stock |
| 3 | MCU core SMPS inductor | **DFE201610E-2R2M=P2** (C337891) | Murata 2.2 µH metal-alloy shielded, 2.0×1.6×1.0 mm | Ext | TDK TFM201610ALM-2R2MTAA (C695610) |
| 3 | SMPS caps | 2× 2.2 µF 10 V 0402 (C107369) on VDD11; 10 µF 10 V 0603 (C19702) on VDDSMPS | Samsung X5R MLCCs | Ext / **Basic** | 0603 16 V 2.2 µF Basic (C23630) |
| 4 | 32.768 kHz crystal | **Q13FC13500004** (C32346), run the LSE at **high drive** | Epson FC-135, 3.2×1.5 mm, 12.5 pF | **Basic** | Q13FC13500002 (C48615, same can, 7 pF, more margin, Ext). **The 2012-size X1A0000610002 fails the U575 oscillator margin.** |
| 5 | Button | **KXT321LHS** (C221821) | C&K 3.0×2.0×0.6 mm top-push, 1.6 N | Ext | Omron B3U-1000P (C231329); XUNPU TS-1086E (C720473) side-push |
| 6 | ESD, charge pin | **ESD9X5.0ST5G** (C87910) | onsemi 5 V unidirectional TVS, 1.0×0.6 mm | Ext | + 1N5819WS series Schottky (C191023, Basic) only if the magnetic connector isn't keyed |
| 6 | ESD, transducer leads (×2) | **PESD5V0S1BL** (C84374) | Nexperia 5 V bidirectional, 5 nA leakage | Ext | TPD1E10B06DPYR (C48260) |
| 7 | Battery | **401230-class 100–110 mAh with PCM**, e.g. EEMB LP401230 | 4×12×30 mm, ~2 g | not JLC | Adafruit #1570 (100 mAh, 3.8×11.5×31 mm, $5.95) for the bench |
| 8 | Passives | all Basic 0402 (table in §8) | | **Basic** | |

**Extended-part count** for this set is 9 unique Extended lines on top of the MCU, mic and charger. JLC charges a per-part loading fee for each Extended line in each order. That's the price of 1×1 mm packages; every Basic alternative is larger or worse.

---

## 1. 3.0 V LDO (B2)

**Job:** make the quiet 3.0 V rail for the MCU I/O, mic, and the H-bridge from a 3.3–4.2 V LiPo. The bridge's peak current passes through it, so its dropout at 150–300 mA sets how far down the battery curve the rail holds 3.0 V.

| Part (what it is) | LCSC · class · stock · $ | Package | Iq typ | Noise 10 Hz–100 kHz | Dropout (3.0 V out) | I max / limit | PSRR 1 kHz |
|---|---|---|---|---|---|---|---|
| **TPS7A2030PDQNR**: TI ultra-low-noise LDO, 3.0 V fixed, "P" = active output discharge | C5220164 · Ext · 3,286 · $0.2175 | X2SON-4 **1×1 mm** | **6.5 µA** (8.5 max at 25 °C) | **7 µVrms** (10 at 1 mA) | **140 mV max at 300 mA** → ~70 mV at 150 mA | 300 mA; ICL 360 min / 520 typ; foldback to 160 mA into a short | 92 dB |
| TPS7A2030PDBVR (same die, bigger package) | C963429 · Ext · 6,986 · $0.2308 | SOT-23-5 | 6.5 µA | 7 µVrms | 145 mV max at 300 mA | same | same |
| **RT9080-30GJ5**: Richtek 2 µA LDO | C965900 · Ext · 3,329 · $0.161 | TSOT-23-5 | **2 µA** | 42 µVrms (3.3 V, 150 mA) | 310 typ / 530 max mV at 600 mA → ~80 / 130 mV at 150 mA | **600 mA**; ILIM 610 min | 75 dB |
| TPS7A0230PDQNR: TI 25 nA nanopower LDO | C2867950 · Ext · 361 · $0.82 | X2SON-4 1×1 | 25 nA | 130 µVrms (at 0.8 V) | **310 mV max at 200 mA** → ~230 mV at 150 mA | 200 mA | 55 dB |

Sources: TI SBVS338H (TPS7A20, Mar 2020, rev. Jul 2024), https://www.ti.com/lit/ds/symlink/tps7a20.pdf §5.5. Richtek DS9080-07 (May 2018), via the LCSC copy linked in the lock file. TI SBVS277C (TPS7A02, rev. Sep 2022), https://www.ti.com/lit/ds/symlink/tps7a02.pdf. Values at 150 mA are scaled linearly from the datasheet's full-load maximum, since dropout in this class is essentially R_on × I.

**Recommendation: TPS7A2030PDQNR.**
- It's the only candidate that meets all three targets at once: low noise (6× quieter than RT9080), <150 mV dropout even at 300 mA, and the smallest package.
- Its 6.5 µA Iq misses the "<5 µA" wish, but the cost is negligible. Against RT9080's 2 µA, it's 4.5 µA more, which is 0.036 mAh per 8 h day. In Off mode (MCU Stop 2 at ~2 µA) it still gives more than a year of shelf life on 100 mAh.
- **Why noise matters here, and why it matters less than it looks:** in 2-level PWM, output = V_rail × (2·duty − 1). Rail noise is *multiplied* by the signal instead of added to it, so at idle (50% duty) it cancels. Rail noise still reaches the mic supply, so 7 µV is the safer choice.
- **Watch item: the 300 mA rating.** The bridge's worst case is 3.0 V / (8 Ω + ~1.2 Ω of FETs) ≈ 330 mA at full-scale DC into an 8 Ω transducer. The D17 output ceiling and the coil's inductance keep real peaks lower, but put a **22 µF bulk cap** (C59461, Basic) on the 3.0 V rail. If E1 measures an 8 Ω coil *and* the ceiling allows near-full-scale drive, switch to RT9080, whose 600 mA rating handles it (the footprint differs, so decide before layout).
- **Rejected:** TPS7A02, for 230 mV dropout at 150 mA, 130 µV noise and 55 dB PSRR. Also XC6206, ME6211 and XC6220 (25–40 µA Iq, or 250+ mV dropout), and clone "TPS7A2030" listings (C55191368, C49208542) whose makers aren't TI.

---

## 2. H-bridge MOSFET pairs (B1)

**Job:** two complementary pairs form the D6 H-bridge. The gates are driven straight from TIM1 at 0/3.0 V, so what matters is performance at **Vgs = 3.0 V**, not the headline 4.5 V figures.
- **Gate charge (Qg)** costs battery: I = 200 kHz × total Qg of the 4 FETs.
- **On-resistance** of one P plus one N sits in series with the transducer, which costs loudness.

![MOSFET comparison](../diagrams/B1-mosfet-compare.png)

*`sim/checks/bridge_fet_compare.py`. Bubble area is the footprint. The two SOT-563 parts are 1.6×1.6 mm; the DFN1010B-6 parts are 1.1×1.0 mm.*

| Pair (what it is) | LCSC · class · stock · $ | Package | Vth (N / P) | Rds(on) at 3.0 V, typ (N / P)¹ | Qg at 4.5 V typ (N / P) | Est. gate-drive current² | Vgs max |
|---|---|---|---|---|---|---|---|
| **PMCXB290UEZ**: Nexperia 20 V complementary trench pair | C19654206 · Ext · 5,000 · $0.1706 | DFN1010B-6 (SOT1216) **1.1×1.0×0.37 mm** | 0.45–1.0 / −0.45 to −1.0 V | **0.34 / 0.88 Ω** (max ~0.44 / 1.2) | 0.6 / 0.6 nC | **0.30 mA** | ±8 V |
| **DMC2400UV-7**: Diodes Inc. complementary pair, ESD-protected gates | C177025 · Ext · **113** · $0.0764 | SOT-563 1.6×1.6 mm | 0.5–0.9 / −0.5 to −1.0 V | 0.43 / 0.85 Ω (model: 0.34 / 0.85) | **0.5 / 0.5 nC** (model: 0.24 nC N at 3 V) | **0.25 mA** | ±12 / ±8 V |
| NTZD3155CT1G: onsemi complementary pair, ESD-protected | C236117 · Ext · 8,788 · $0.1684 | SOT-563 | 0.45–1.0 / −0.45 to −1.0 V | 0.48 / 0.58 Ω | 1.5 / 1.7 nC (2.5 max) | 0.79 mA | ±6 V |
| PMCXB900UELZ: Nexperia, older and weaker sibling of the 290UE | C552750 · Ext · 4,842 · $0.1289 | DFN1010B-6 | 0.45–0.95 V | 0.58 / 1.21 Ω | 0.4 / 1.19 nC | 0.39 mA | ±8 V |
| SSM6L36FE,LM: Toshiba pair (checked, not better) | C7544186 · Ext · 144 · $0.198 | SOT-563 | 0.35–1.0 V | N 0.46 at 5 V / P 0.95 at 4.5 V | 1.23 / 1.2 nC at 4 V | ~0.6 mA | — |

¹ Linear interpolation between the datasheet's 2.5 V and 4.5 V typical rows. Nexperia specifies at 1 A and Diodes at 80–200 mA, so the Nexperia P figure is pessimistic by comparison.
² 4 FETs × 200 kHz × Qg(3 V), where Qg(3 V) = 0.62 × Qg(4.5 V). The 0.62 ratio comes from the DMC2400UV manufacturer model. `[Low]` for the others until their own models are run.

Datasheets:
- Nexperia PMCXB290UE, 30 May 2023: https://assets.nexperia.com/documents/data-sheet/PMCXB290UE.pdf
- Diodes DMC2400UV, DS35537 Rev. 11-2, March 2020: https://www.diodes.com/assets/Datasheets/DMC2400UV.pdf
- onsemi NTZD3155C/D Rev. 4, June 2019 (onsemi blocks scripted downloads; LCSC copy in the lock file)
- Nexperia PMCXB900UEL, 28 June 2016: https://assets.nexperia.com/documents/data-sheet/PMCXB900UEL.pdf
- Toshiba SSM6L36FE, 2014-11-14

**What the numbers mean for the product.**
- **All four pairs are fully on at 3.0 V.** Vth max is 1.0 V, so 3 V gives 2 V of overdrive.
- **The on-path resistance differs by only ~0.2 dB of loudness** between the top three pairs (−1.1 to −1.3 dB into 8 Ω).
- **Gate charge is the real difference.** NTZD3155C costs ~0.5 mA more, all day, than the other two. That's ~6% of the whole budget (§7).
- The spec's "~2.5 nC" for NTZD3155C was its *maximum*; the typical is 1.5–1.7 nC. The conclusion doesn't change.

**Recommendation: PMCXB290UEZ for the product.**
- It's the smallest package JLC stocks (1.1 mm², vs 2.56 mm² for SOT-563). It's genuine Nexperia with 5,000 in stock, and has the newest datasheet (2023).
- It's a near-tie with DMC2400UV on battery (+0.05 mA) and on loudness (+0.05 dB).

**Runner-up: DMC2400UV-7.** Its gate charge is the lowest, and its manufacturer SPICE model is in hand. But **only 113 genuine parts are in stock**. C2940616 (3,806 in stock), labelled "DMC2400UV", is a **TECH PUBLIC clone**, not a Diodes part: its own datasheet quotes different figures (800 mΩ at 1.8 V). Don't treat it as the same part.

**Costs of the recommendation (be clear-eyed):**
1. **No EasyEDA footprint for C19654206.** The SOT1216 footprint fetched via its sibling C552750 (`hw/lib/lcsc/lcsc.pretty/SOT1216_…`) has 0.16×0.20 mm pads. Nexperia's reflow land pattern (datasheet Fig. 32) uses larger pads, so **draw the footprint from Fig. 32**.
2. **0.35 mm pitch, leadless.** The joints can't be inspected by eye, and hand rework is hard. JLC lists and places the part, but it's the finest pitch on the board.
3. **No SPICE model downloaded.** Nexperia's and onsemi's sites both serve a bot challenge to scripted downloads (tried 2026-09-30: curl, WebFetch, and headless Chromium). Details are under *SPICE models* below.

**Bench board (Phase 2):** put both footprints on it: one SOT-563 site (DMC2400UV) and one DFN1010 site (PMCXB290UE). The owner can then measure switching and current on each, and the SOT-563 is easier to probe.

**SPICE models (`sim/spice/models/`)**
- `DMC2400UV.lib`: Diodes Inc. "Dual MOSFETs" collection, https://www.diodes.com/productcollection/spicemodels/8360/Dual+MOSFETs.spice.txt?eid=1042. Downloaded 2026-09-30; model v1.0, revised 2014-11-18. Extracted verbatim, with a header giving source and date.
  - Checked in `sim/spice/dmc2400uv_rds_qg.cir`: at Vgs = 3.0 V and 200 mA the model gives **N 0.34 Ω, P 0.85 Ω**. At 2.5 V it gives 0.39 / 1.00 Ω (datasheet typical 0.45 / 0.90). At 4.5 V it gives 0.28 / 0.66 Ω (datasheet 0.35 / 0.70). So the model's N-channel is ~15–20% optimistic.
  - Gate charge to 3.0 V: **0.24 nC** (0.39 nC to 4.5 V at Vds = 3 V).
- **PMCXB290UE / NTZD3155C: not downloaded.** Both manufacturers' sites return a bot challenge ("Challenge Validation" / Akamai "Access Denied") to curl, WebFetch and headless Chromium. That's the manufacturer's site, not the session proxy. The owner can grab them in a browser:
  - Nexperia: product page → Documentation → "SPICE model" (N- and P-channel files, dated 2021-04-21 per search index): https://www.nexperia.com/product/PMCXB290UE
  - onsemi: product page → Design Resources → Simulation Models (zip): https://www.onsemi.com/products/discrete-power-modules/mosfets/ntzd3155c
  - Drop them in `sim/spice/models/` and I'll add the headers and rerun the Qg/Rds check.

**Gate pull resistors (D6, mandatory):** 100 kΩ 0402 (C25741, Basic).
- They cost **~60 µA** while switching: each resistor has 3 V across it half the time, so 4 × 30 µA × 50%.
- Don't go to 1 MΩ. The worst-case gate leakage (Nexperia 0.5 µA at 2.5 V; Diodes 1 µA at 5 V) × 1 MΩ = 0.5–1 V, which reaches Vth min, so a "held-off" FET could creep on during reset.

---

## 3. STM32U575 core SMPS: inductor and caps (D11)

**What ST requires** (DS13737 Rev 8, Aug 2023, §5.1.6 and Figure 25, "STM32U575xQ power supply scheme (with SMPS)"; LCSC copy of the datasheet linked in the lock file):

| Item | ST requirement |
|---|---|
| L, VLXSMPS → VDD11 | **2.2 µH ±20%, Isat > 0.5 A, DCR < 200 mΩ** |
| C_OUT on the two VDD11 pins | **2 × 2.2 µF ±20%, ESR < 20 mΩ at 3 MHz, rated ≥ 10 V**; optional 100 nF at each VDD11 pin |
| C_IN on VDDSMPS | **10 µF ±20%, ESR < 10 mΩ at 3 MHz, rated ≥ 10 V** |
| Switching frequency (Table 35) | **3 MHz** in voltage ranges 1–3 when VDD > 1.9 V (1.5 MHz below). "**The SMPS is asynchronous in range 4 and low-power modes.**" |

| Inductor (what it is) | LCSC · class · stock · $ | Size (mm) | DCR | Isat | Core | Verdict |
|---|---|---|---|---|---|---|
| **DFE201610E-2R2M=P2**: Murata metal-alloy wire-wound, shielded | C337891 · Ext · 2,786 · $0.1366 | 2.0×1.6×1.0 | ~140 mΩ | 2.4 A | metal alloy, molded | **Recommended** |
| TFM201610ALM-2R2MTAA: TDK thin-film metal | C695610 · Ext · 401 · $0.3253 | 2.0×1.6×1.0 | 130 typ / **146 max** mΩ | 2.4 / 2.6 A | thin-film metal | Alternate (low stock) |
| WPN201610H2R2MT: Sunlord | C97005 · Ext · 18,133 · $0.041 | 2.0×1.6×1.0 | 170 mΩ | 2.15 A | not verified (datasheet PDF was empty) | Cheap fallback, `[Low]` |
| LSCND1608HKT2R2MF: Taiyo Yuden 0603 metal multilayer | C31123918 · Ext · 3,400 · $0.2447 | 1.6×0.8 | **250 mΩ max** | 1.3 A | metal multilayer | **Rejected**: exceeds ST's DCR limit |
| DFE201210U-2R2M=P2 | C2049745 · Ext · 7,911 · $0.1938 | 2.0×1.2×1.0 | **228 mΩ** | 2.0 A | metal alloy | Rejected: DCR |

Sources:
- Murata spec J(E)TE243A-0001 (LCSC copy). The DCR and rated currents were read with the JLC listing's summary, because the PDF table extracts scrambled.
- TDK TFM201610ALM catalogue (LCSC copy), row "2R2MTAA".
- Taiyo Yuden TY-COMPAS part detail for LSCND1608HKT2R2MF (via search index, 2026-09-30).

**Recommendation: Murata DFE201610E-2R2M=P2 + 2× CL05A225KP5NSNC (2.2 µF 10 V 0402, C107369, Ext) + CL10A106KP8NNNC (10 µF 10 V 0603, C19702, Basic).**
- **Why 0402 2.2 µF is Extended:** the Basic 0402 2.2 µF (C12530) is rated 6.3 V, and ST asks for ≥10 V. The Basic alternative is 0603 16 V (C23630), 2.5× the area.
- **Magnetostriction:** no maker publishes it for these parts.
  - It doesn't matter at 3 MHz, which is 150× above hearing. Magnetostrictive or piezo "singing" is only audible when the *envelope* of the current has audio-band content, as in burst/skip mode.
  - Metal-alloy powder cores in a molded body are the usual choice for quiet inductors. Their mechanical coupling to the board is weak, and they don't have a ferrite core's air gap.
- **Two flags for the owner:**
  1. **D11's "no Class-2 ceramics on the switching node" can't be met literally.** ST mandates 2.2 µF and 10 µF, and no C0G part at those values fits a 20×10 mm board. The real node that switches is VLX, and it carries no capacitor; the X5R caps sit on the filtered VDD11 and VDDSMPS rails. At a constant 3 MHz those caps can't sing audibly. Suggest rewording D11 to "no Class-2 ceramics where the ripple has audio-band content" (spec change for the owner).
  2. **The datasheet says the SMPS goes asynchronous in voltage range 4 and in low-power modes.** That's exactly the burst-like behaviour D11 warns about. If the C9 idle-listening mode drops the core to range 4 (the lowest-voltage range, for low clock rates), expect the whine risk there; E11 should listen specifically in that mode. The alternative is to stay in range 3 while listening, at a small current cost, or to switch to the LDO for idle-listening.

---

## 4. 32.768 kHz crystal (B8)

**Check:** ST's oscillator criterion (AN2867): the crystal's gm_crit = 4·ESR·(2πf)²·(C0 + CL)² must be **below** the U575's Gmcritmax for the chosen drive level.
- The U575's Gmcritmax values (DS13737 Table 80) are 0.5 / 0.75 / 1.7 / 2.7 µA/V for LSEDRV = low / medium-low / medium-high / high.
- The LSE draws 410–700 nA across that range.

| Crystal (what it is) | LCSC · class · stock · $ | Size | CL | ESR max | C0 | gm_crit | Needs LSEDRV | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Q13FC13500004**: Epson FC-135 watch crystal | C32346 · **Basic** · 467,179 · $0.1717 | 3.2×1.5×0.8 | 12.5 pF | 70 kΩ | 1.0 pF | **2.16 µA/V** | **high (11)**, Gmcritmax 2.7 | **Recommended**: passes, 1.25× below the limit |
| Q13FC13500002: FC-135, 7 pF version | C48615 · Ext · 34,217 · $0.1858 | 3.2×1.5 | 7 pF | 70 kΩ | 1.0 pF | **0.76 µA/V** | medium-high (10), 2.2× margin | Alternate: more margin, ~110 nA less LSE current |
| X1A0000610002: Epson FC-12M, 2012 size | C55208 · Ext · 22,457 · $0.2386 | 2.0×1.2 | 12.5 pF | 90 kΩ | 1.3 pF | **~2.9 µA/V** | none | **Rejected: fails even at high drive** |
| SC-16S: Seiko Instruments 1610 | C398713 · Ext · 8,350 · $0.3076 | 1.6×1.0 | 12.5 pF | ~90 kΩ `[Low]` | ~1 pF | ~2.8 µA/V | none | Rejected, same reason |

Sources:
- Epson FC-135 sheet (Q13FC13500004, LCSC copy): R1 70 kΩ max, C0 1 pF typ, CL 12.5 pF, drive level 0.5 µW max.
- Epson FC-12M / FC-12D sheet (LCSC copy for C55208): R1 90 kΩ max, C0 1.3 pF.
- ST DS13737 Rev 8, Table 80.

**Recommendation: keep C32346 (Basic), set LSEDRV = high (11), load caps 2 × 15 pF C0G (C1548, Basic).**
- **Load caps:** C = 2 × (CL − C_stray). C_stray is 3 pF (CS_PARA, Table 80) plus ~1.5 pF of board, so C = 2 × (12.5 − 4.5) = 16 pF → 15 pF. S1 trims it by measuring the RTC error.
- **A correction to spec §9 / D16:** it lists the 2012-size X1A0000610002 as an option, but that part **doesn't meet the U575's LSE margin**. The only way to a smaller can that works is a low-CL (7 pF) part, and JLC stocks none in 2012 or smaller today.
- If the owner prefers margin over the Basic fee, choose C48615 (7 pF) with ~2 × 5.6 pF load caps.

---

## 5. Button (B5)

| Switch (what it is) | LCSC · class · stock · $ | Size (mm) | Actuation | Force | Notes |
|---|---|---|---|---|---|
| **KXT321LHS**: C&K ultra-thin tact switch | C221821 · Ext · 6,982 · $0.1672 | **3.0×2.0×0.6** | top | 1.6 N | Smallest JLC-stocked. Siblings: KXT311 1.0 N (697 stock), KXT331 2.4 N (7,951) |
| B3U-1000P: Omron micro tact switch | C231329 · Ext · 143,617 · $0.1865 | 3.0×2.5×1.6 | top | 1.53 N | Taller, so it reaches a housing cap without a plunger |
| TS-1086E-AC03526: XUNPU side-push tact switch | C720473 · Ext · 4,171 · $0.0634 | 4.6×1.8×3.5 | **side** (right-angle) | 2.6 N | For a button through the pod's side wall; sits on the board edge |

Sources: C&K KXT3 sheet (LCSC copy, C221821); Omron B3U catalogue https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3u.pdf; XUNPU TS-1086E (LCSC copy). The only Basic tact switch found is 5.1×5.1 mm (TS-1187A, C318884).

**Recommendation: KXT321LHS.** At 0.6 mm tall it can sit under a printed flexure in the pod wall. Choose 1.6 N over 1.0 N so it doesn't get pressed by accident when the glasses are handled. If the mechanical design (cad-mech) wants the press on the side face, use TS-1086E instead.

---

## 6. ESD, TVS and reverse polarity (B6)

**Charge pogo pins (VBUS, GND).** The MCP73831 input is rated 7 V abs max (DS20001984H).

| Option | Parts | Pros | Cons |
|---|---|---|---|
| **A (recommended)** | Polarity-keyed magnetic pogo + **ESD9X5.0ST5G** (C87910, onsemi 5 V *uni*directional TVS, SOD-923 1.0×0.6 mm, Ext · 43,942 · $0.0478) on VBUS | One tiny part. If a reversed supply is ever applied, the TVS forward-conducts and clamps VBUS to ~−0.7 V (the dock supply must be current-limited) | Relies on the connector's magnets for polarity |
| B | A + **1N5819WS** series Schottky (C191023, Hottech, SOD-323, **Basic** · 4.8 M · $0.0137) | Blocks reverse polarity outright; Basic | ~0.3 V drop at 45 mA (the MCP73831 still has plenty of headroom from 5 V); one more part. Its 500 µA reverse leakage is harmless because the charger isolates the battery (0.15–2 µA back-drain) |
| C | SMF5.0A (C193402, 200 W, SOD-123FL) | Surge-rated | 3.5×1.8 mm; overkill for a dock |

**Transducer leads (two exposed wires to the arm).** Each bridge output already has a MOSFET body diode to each rail, and the rail caps absorb that energy, so a TVS here is belt-and-braces for ESD from a touched lead.

| Option | Part | Leakage | C | Note |
|---|---|---|---|---|
| **A (recommended)** | **PESD5V0S1BL** (C84374, Nexperia 5 V *bi*directional, DFN1006 1.0×0.6, Ext · 122,523 · $0.0334) | **5 nA** | 35 pF | Adds 35 pF × (3 V)² × 200 kHz ≈ 63 µW per lead of switching loss |
| B | TPD1E10B06DPYR (C48260, TI 6 V bidirectional, 0.6×1.0, Ext · 286,460 · $0.0417) | 100 nA max | 12 pF | Lower capacitance; more leakage |
| C | None | — | — | Saves two parts; relies on the body diodes |

Sources: onsemi ESD9X5.0S and Nexperia PESD5V0S1BL sheets (LCSC copies); TI TPD1E10B06 (https://www.ti.com/lit/ds/symlink/tpd1e10b06.pdf).

**Also put ESD on the SWD pogo pads** if they're exposed on the housing. Otherwise the SWD pins' own protection is enough for bench use.

---

## 7. Battery (B4)

The spec's v0.9 pod (~35 mm) holds a **~30 mm cell**, and the brief asks for 80–105 mAh at about 30×12×4 mm. The standard LiPo size code is thickness-width-length, so **401230 = 4.0×12×30 mm** is the natural fit.

| Listing (what it is) | Capacity | Size T×W×L (mm) | Mass | Charge / discharge max | PCM | Price | Source (accessed 2026-09-30) |
|---|---|---|---|---|---|---|---|
| **EEMB LP401230**: maker spec sheet | 100 mAh nom / 95 min | ≤4.3 × ≤12.5 × ≤31 (cell) | ~2 g | 100 mA (1C) / **200 mA (2C)**; Rint ≤380 mΩ | spec has a PCM chapter; **confirm the pack variant** | not listed (sold via allthingslithium.com) | https://www.eemb.com/product-121 · spec ZJQM-RD-SPC-H2294, 2022-10-19 |
| **Adafruit #1570**: 100 mAh LiPo | 100 mAh | 3.8 × 11.5 × 31 | 3 g | charge ≤100 mA | yes, 3.0 V cutoff, short protection | **$5.95** (10+: $5.36; 100+: $4.76), in stock | https://www.adafruit.com/product/1570 |
| lipobattery.us LP401230 with PCM | 110 mAh | 4.0 × 12 × 30 (+PCM) | 2.2 g | 55 mA / **110 mA (1C)** | yes: OV ≥4.25 V, UV <2.75 V, short circuit | not retrieved (page is bot-walled) | https://www.lipobattery.us/lipo-battery-lp401230-3-7v-110mah-0-41wh-with-protection-circuit-and-wires-15mm/ `[Med]`: from the search index, not the page |
| Generic 301230 (e.g. "Liter" 80 mAh) | 80 mAh | 2.75–3.0 × 12 × 30 | ~2 g | 1C / 1.5C pulse | yes | not retrieved | https://www.amazon.com/dp/B09WK8Y183 `[Low]`: search index only |

**Recommendation: a 401230-class 100–110 mAh cell with PCM.** For the bench, buy the Adafruit #1570 now: it's in stock with a known price and the same footprint class. For the product, ask EEMB (or equivalent) for the LP401230 *with PCM and ~50 mm leads*. Their spec sheet is the only primary one of the set, and it carries the 2C discharge rating.

- **Why the discharge rating matters:** bridge peaks reach ~300 mA. On a 1C-rated 110 mAh cell that's 2.7C for a few milliseconds, and the PCM trips far above that (typically ≥1 A). The sag is 0.38 Ω × 0.3 A ≈ 0.11 V. Above ~3.25 V of cell voltage the LDO still holds 3.0 V; below that the rail droops on peaks. The 22 µF bulk cap covers the 200 kHz part but not millisecond peaks.
- **Runtime:** with 85% usable, 100 mAh gives ~10–17 h at algorithm A and ~8–11 h at B (spec §7 budget). **An 80 mAh cell misses 8 h in B** at the pessimistic end (~6.5 h), unless idle-listening mode (C9) delivers.
- **Charge current:** the MCP73831 with R_PROG = 22 kΩ (C25768, Basic) gives I = 1000 V / 22 kΩ = **45 mA**, which is ≤0.45C for 100–110 mAh. R_PROG must stay 2–67 kΩ; 70 kΩ or more puts the chip in shutdown (DS20001984H, Microchip, 2005–2020).
- **Spec note:** B4's text says 105–150 mAh and ≤45 mm long; the v0.9 pod leaves room for ~30 mm only. This is the O5 decision. The 401230 is what the 35 mm pod can actually hold.

---

## 8. Passives (0402, Basic unless stated)

| Role | Value | Part (maker) | LCSC · class · stock · $ | Notes |
|---|---|---|---|---|
| Decoupling | 100 nF 16 V X7R | CL05B104KO5NNNC (Samsung) | C1525 · Basic · 22.3 M · $0.0045 | Each VDD pin, mic VDD |
| Decoupling | 1 µF 25 V X5R | CL05A105KA5NQNC (Samsung) | C52923 · Basic · 5.7 M · $0.0099 | LDO in/out (TPS7A20 needs ≥1 µF out), VDDA |
| Decoupling | 4.7 µF 10 V X5R | CL05A475MP5NRNC (Samsung) | C23733 · Basic · 2.4 M · $0.0166 | General bulk (LDO output, mic area) |
| Decoupling | 10 µF 6.3 V X5R | CL05A106MQ5NUNC (Samsung) | C15525 · Basic · 9.2 M · $0.0256 | MCU VDD bulk (ST Fig. 25: n×100 nF + 10 µF). Expect ~40–50% of nominal at 3 V bias. **Not** for VDDSMPS (needs ≥10 V; use C19702) |
| SMPS C_IN | 10 µF 10 V X5R **0603** | CL10A106KP8NNNC (Samsung) | C19702 · Basic · 10.5 M · $0.0319 | §3 |
| SMPS C_OUT | 2.2 µF 10 V X5R | CL05A225KP5NSNC (Samsung) | C107369 · **Ext** · 878 k · $0.0129 | §3; Basic 0603 alternative C23630 |
| Rail bulk | 22 µF 6.3 V X5R **0603** | CL10A226MQ8NRNC (Samsung) | C59461 · Basic · 8.0 M · $0.0311 | 3.0 V rail at the bridge |
| Charger PROG | 22 kΩ 1% | 0402WGF2202TCE (Uni-Royal) | C25768 · Basic · 850 k · $0.0024 | 45 mA (§7). 24 kΩ (41.7 mA) is Extended (C25769) |
| Gate pulls | 100 kΩ 1% | 0402WGF1003TCE (Uni-Royal) | C25741 · Basic · 8.4 M · $0.0024 | 4 per board (§2) |
| LSE load | 15 pF C0G | 0402CG150J500NT (Fenghua) | C1548 · Basic · 1.4 M · $0.0038 | §4 |

**Class-1 (C0G/NP0) Basic parts for near the mic.** Class-2 MLCCs (X5R/X7R) are piezoelectric: they turn board vibration into voltage and voltage ripple into sound. Near the mic and with the transducer on the same head, keep them off signal lines.
- Basic 0402 C0G values: 12 pF (C1547), 15 pF (C1548), 18 pF (C1549), 20 pF (C1554), **22 pF (C1555)**, 33 pF (C1562), **100 pF (C1546)**. Use them for any RC on the PDM clock/data line.
- 1 nF C0G is Extended: C53547 (Fenghua) or C307441 (Samsung).
- **The mic's own 100 nF VDD bypass has to stay X7R.** No 0402 C0G reaches 100 nF. Place it at the mic, where it's the lesser evil.

---

## Footprints fetched (`hw/lib/lcsc/`)

These came from `easyeda2kicad` on 2026-09-30. **Check each against the maker's land pattern before layout** (jlc-parts skill):

| Footprint | Fetched via | Status |
|---|---|---|
| X2SON-4 1×1 mm | C5220164 (TPS7A20) | Check against TI DQN land pattern |
| SOT-563 | C177025 (DMC2400UV) | Check |
| SOT1216 (DFN1010B-6) | C552750 (PMCXB900UEL; C19654206 has no EasyEDA data) | **Pads smaller than Nexperia Fig. 32: redraw** |
| L0806 | C337891 (Murata DFE201610E) | Check |
| FC-135R | C32346 | Check |
| KXT3 switch | C221821 | Check |
| SOD-882 | C84374 | Check |
| SOD-923 | C87910 | Check |

## Spec items this touches (for the owner; §1 untouched)
1. **§9 / D16:** drop X1A0000610002 (2012 crystal) as an option; it fails the U575 LSE margin (§4).
2. **D11:** reword "no Class-2 ceramics on the switching node" (§3), and add "SMPS is asynchronous in range 4 / low-power modes" to E11's test list.
3. **D6 / B1:** NTZD3155C's Qg is 1.5–1.7 nC typical (2.5 nC max). Candidate list is now PMCXB290UE (rec.) / DMC2400UV (genuine stock 113).
4. **§7:** add ~60 µA for the gate pull resistors, and the ~0.25–0.3 mA gate drive is confirmed.
5. **B3:** charge current 45 mA (22 kΩ) instead of 50–75 mA, sized for the 100–110 mAh cell the v0.9 pod can hold.
