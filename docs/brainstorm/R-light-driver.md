# R-light-driver: tragus/bone drivers <=3 g (rabbit trail, 2026-10-08)

Why: TEAX14C02-8 = 12.8 g per side (Tectonic datasheet via RS 8765272), vs RC-BC02 (today's pad exciter, 1.2 g `[Low]`, docs/system/reg-pad.md:39). Too heavy at the ear. Limits: <=3 g, <=dia 14 x 6 mm, published Bl/force/sensitivity. Method as R-exciter2: force at the 208 mA clamp = Bl x I, gain = 20 log10(Bl/1.0); baseline Bl 1.0 N/A ASSUMED (E1 unmeasured). WebSearch snippets only, secondary, not re-opened.

## Result: nothing meets all three limits (mass, size, published Bl)
| Part (gloss) | Mass | Size | Bl | Gain @208 mA | Verdict |
|---|---|---|---|---|---|
| Tectonic TEAX09C005-8 (rectangular 0.5 W exciter) | 3.2 g (datasheet DS-TEAX09C005-8 v1.1, parts-express/RS 1345564) | 26 x 13 x 6.5 mm | 1.1 T m, Mms 0.13 g, f0 ~635 Hz | **+0.8 dB** (0.23 N) | misses size (26 x 13) and mass by 0.2 g; no gain over RC-BC02 |
| Dayton BCE-1 (22x14 exciter, 4 ohm) | 2.3 g (audiophonics) vs 0.57 g (axiomedia): listings disagree | 21.2 x 14.4 x 7.8 mm | not published | unknown | mass maybe OK, 1.8 mm too thick; weigh one on E1 |
| TEAX14C02-8 | 12.8 g | dia 14 x 9.85 | 2.4 | +7.6 dB | MASS KILL (4x pod exciter mass x 10) |
| Knowles BU-21771/23173 | 0.1 g class | 7.9x5.6x4.1 | accelerometer sensor, not an exciter | n/a | wrong device |
| Sonion / Goertek / AAC BC modules, hearing-aid B71/B81 | - | - | none public (OEM/NDA; audiometric values are mastoid RETFL, not Bl) | n/a | ask vendors |
No PUI, Dayton BCT or AAC part found with Bl AND mass AND under 6 mm (searched 2026-10-08).

## Reading
Light published-Bl parts do not exist in the open market: the one datasheet with Bl and a 3.2 g mass (TEAX09) is no stronger than the baseline guess. Gain per gram: TEAX14 +7.6 dB / 12.8 g; TEAX09 +0.8 dB / 3.2 g. Loudness must come from the firmware limiter, pad stiffness and drive (see R-exciter2), not from a heavier exciter. Open route: request Bl + mass from Sonion/Goertek/Knowles; weigh BCE-1 and RC-BC02 on E1.

Sources: parts-express.com/pedocs/specs/297-2111--hihx09c005-8-data-sheet.pdf; rs-online 1345564; audiophonics.fr BCE-1 p-11203; axiomedia.it BCE-1 (all via WebSearch 2026-10-08).
