---
name: jlc-parts
description: Look up JLCPCB/LCSC parts - live stock, price breaks, Basic vs Extended library class, package - and fetch their KiCad symbol, footprint and 3D model by LCSC number. Use when choosing or checking any part for a JLC-assembled board, before quoting stock or price anywhere, or when a footprint for an LCSC part is needed.
---

# JLC parts

## Stock and price
```bash
python3 tools/jlc.py STM32L452CEU6 C2879853            # table, in-stock rows first
python3 tools/jlc.py "32.768kHz 2012" --all -n 20       # include zero-stock rows
python3 tools/jlc.py C32346 --json                      # one JSON object per row
```
- Every row carries `queried_utc`. Anything written to docs/ or a sourcing lock quotes the
  LCSC number, library class, stock and price **with that date**. Stock changes daily.
- Library class: **Basic** parts carry no setup fee; **Extended** parts carry a per-part
  fee per order. Prefer Basic when specs are equal (spec §0 rule 5).
- The endpoint is undocumented; a changed response raises `JLCError` with the raw payload.

## Footprints and symbols by LCSC number
```bash
source tools/env.sh
mkdir -p hw/lib/lcsc && easyeda2kicad --symbol --footprint --3d --lcsc_id=C2879853 --output=hw/lib/lcsc/lcsc
```
**Always check an EasyEDA footprint against the manufacturer's recommended land pattern**
(pad size, pitch, pin 1, the mic's acoustic port hole) before using it. Community footprints
are often right and sometimes subtly wrong.

## Evidence standard
For a part choice, pair this with the vendored `qualify-pcba-sourcing` skill: exact MPN, pin
semantics, package drawing, lifecycle, dated stock. Gloss every part number in plain language
(spec §0 rule 2).
