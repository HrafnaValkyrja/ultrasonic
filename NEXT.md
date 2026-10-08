# NEXT 5 (ranked; 2026-10-08 16:2x ET, re-ranked on the owner's four-proofs ruling)
Her words (via Stolas): "I want it working hard to verify that the board is electrically, thermally and physically possible, and that the device is possible to assemble (and easy enough for me to build)." The pen test moves to a weekend bench day; both pods stay alive. Evidence goes in docs/proof/<proof>/ (README + dark PNG); one status line per proof as it lands.

1. P-ELEC: electrical proof, K4 P+M (power budget, rails, noise, SI on BM28/clock, DRC/ERC, part ratings with margin). ~1.5 h.
2. P-THERM: thermal proof (worst-case dissipation: charge 130 mA + MCU + bridge; hotspots; path to the shell; cell temperature limit). ~1.5 h.
3. P-PHYS: physical proof (stack-up, clearances, fit with tolerances, vision line for both pods). ~1.5 h.
4. P-BUILD: assembly + buildability by her (step-by-step sequence, tools, hand-solder vs reflow, hardest steps flagged with easier alternatives). ~1.5 h.
5. N-K4-TOOLS cherry-pick (a7b29cf), after N-K1T-RELEASE (running) finishes. ~10 min.
Later: N-K1T-BUTTON (board edit + re-route, serial heavy job); the K4 heights entries for C16/C17/C21.
Done today: N-K1T-PARITY, N-PENTEST-CARD, N-POST-GAP, N-6L-STACKUP (B4 still open: JLC lists 6L at 1.2/1.6/2.0 only), N-K1T-DUCT (425f8d6).

Ruling-needed (hers): A-K4-VISION (weekend bench day), A-TODAY-BODY-MEASURE, A-IDLE-TRADE, A-6L-QUOTE (optional), A-CAP-CURVES (optional), GitHub Issues permission. Orders/payments: owner-only.
