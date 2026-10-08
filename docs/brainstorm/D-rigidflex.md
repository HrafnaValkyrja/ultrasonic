# D-rigidflex: ledger I-004 kill test (2026-10-08)
verdict: FAIL (fab not offered). Fallback noted at end.
## evidence (fetched 2026-10-08)
- JLCPCB flex capabilities https://jlcpcb.com/capabilities/flex-pcb-capabilities : "Rigid-flex PCBs are not yet supported." FAQ: "JLCPCB currently does not support Rigid-Flex PCBs; we only produce standard Flex PCBs."
- Flex: 1/2/4 Cu layers; finished 0.07-0.12 (1L), 0.11-0.2 (2L), 0.2-0.45 mm (4L), excl. stiffener; dielectric 25/50 um.
- Stiffeners: PI 0.1-0.25, FR4 0.1-1.6, stainless 0.1-0.3 mm, 3M tape.
- Min bend radius: 6x thickness (1L), 10x (multilayer), dynamic 10-15x. Assembly: "full SMT assembly compatibility" (FR4/steel stiffener under parts); no flex-specific PCBA terms given.
- Price: no list price; quote tool only. Flex from ~$2/5 pcs (lcsc.com/pcba page), 4+ day build. PCBA fees (help FAQ, Nov 2025): setup $8, $0.0017/joint, $3/unique Extended part.
- Rigid thickness 0.8 mm exists, but only for rigid boards: https://jlcpcb.com/capabilities/rigid-pcb-capabilities (1-32 L, 0.4-4.5 mm).
- Blog https://jlcpcb.com/blog/understanding-rigid-flex-pcb-technology (upd. 2026-09-09) lists no rigid-flex product.
## kill test
Needs <=6L rigid section at <=0.8 mm inside a rigid-flex board: not buildable at JLC. FAIL.
Bend check (also marginal anyway): 0.6 mm gap fold, 180 deg, inner R ~0.3 mm. Min R for 1L 0.07 mm = 0.42 mm; 2L 0.11-0.2 = 1.1-2.0 mm (gap 2.2-4 mm). Only a 1L flex tail passes, and a 1L tail cannot carry the P/M nets + USB pair.
## fallback (not requested sketch; for owner decision)
Flex-only + FR4 stiffeners (0.8 mm) as the two "rigid" islands, SMT on stiffened zones: JLC makes it, but 4L flex max (vs 6L P/M), and a fold stays impossible at 0.6 mm gap. A flex jumper replacing BM28 (flex tail into a ZIF/FFC) still needs a connector. Gain over BM28 pair: nil. Other route: non-JLC rigid-flex fab (not researched; off-brief).
