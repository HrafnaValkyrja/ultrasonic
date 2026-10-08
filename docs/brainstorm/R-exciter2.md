# R-exciter2: second search for a thin high-Bl exciter (rabbit trail, 2026-10-08)

Owner now requires alerts audible at 55-65 dBA (subdivision). Method as R-exciter.md: force at the 208 mA clamp = Bl x I; gain = 20 log10(Bl/1.0), baseline Bl 1.0 N/A is ASSUMED (E1 unmeasured). Same-current drive; pad coupling assumed unchanged. Hand estimate, bone.py not re-run.

## Result: nothing new that is both thin and published
| Part (gloss) | Bl | Re | Size | Price/stock (2026-10-08) | Force @208 mA | Gain |
|---|---|---|---|---|---|---|
| Tectonic TEAX14C02-8 (14 mm round exciter, 0.8 W) | 2.4 T m (search snippet of Tectonic datasheet, via RS; not re-opened) | 7.8 ohm | dia 14 x 9.85 mm thick (datasheet snippet); audiophonics lists 12.99 g | 7.50 EUR incl. tax, "last items" (audiophonics.fr) | 0.50 N = 113.9 dB re 1 uN | **+7.6 dB** |
| Tectonic TEAX13C02-8/RH (13 mm) | not found | n/a | about 9-9.5 mm thick (listings conflict) | Parts Express 297-214 | unknown | unknown |
| Dayton BCT-3 (R-exciter.md) | 4.41 | 3.9 | 44x32 mm | $32.99 | 0.917 N | +12.9 dB, does not fit |
| Knowles BU-21771 / BU-23173 | none: listed as MEMS accelerometer sensors, -45 dB (no reference) | n/a | 7.9x5.6x4.1 | digikey | not an exciter | n/a |
| Sonion BC page | table unreadable, no force/Bl | | | | | |
| Tectonic TEAX09C005-8 (9 mm, 0.5 W) | no datasheet found | | | sciket.com listing only | unknown | unknown |
Not found at all: Foster/Fostex, AAC/Goertek BC modules, hearing-aid B71/B81 BC receivers (published values are 1 kHz mastoid RETFL-type, not usable here), smart-glasses driver datasheets (patents give no numbers). Vendors publish no Bl for under 8 mm thick parts.

## Shortlist
1. **TEAX14C02-8**: +7.6 dB, 14 mm dia x 9.85 mm. 2.9 mm too thick for T 7 (O27 thin first) but would fit as a separate tragus pad in the 15 mm height class. Cheapest real number.
2. **BCT-3**: +12.9 dB, 44x32 mm; only a bench reference.
3. **BCE-1** (21x14x7.8 mm): Bl unknown; measure on E1.

## Reading
Street/subdivision gap is +10 to +20 dB. Best thin-ish part buys +7.6 dB at +2.9 mm. Remaining route: firmware limiter (+6.3 dB, in loudness_fw), pad stiffness (+4 dB), and this exciter swap, together about +18 dB at the front site, borderline for 55-65 dBA. Owner decides; vendor requests (Sonion, Goertek, Knowles) for Bl remain the only way to find a thin part.

Sources (WebSearch snippets 2026-10-08, secondary): audiophonics.fr TEAX14C02-8 page; Tectonic datasheets via docs.rs-online.com; parts-express.com 297-214; digikey Knowles BU-21771.
