#!/usr/bin/env python3
"""Look up parts in the JLCPCB assembly library (stock, price, Basic/Extended, package).

Stock and price change daily: every result carries the query timestamp, and anything
written into docs/ or a sourcing lock must quote it.

    python3 tools/jlc.py STM32L452CEU6 SPH0641LU4H-1          # table, in-stock rows first
    python3 tools/jlc.py C2879853 --json                       # machine-readable, one line per part
    python3 tools/jlc.py "32.768kHz 2012" --all -n 20          # include zero-stock rows, 20 rows

Library use:
    import sys; sys.path.insert(0, "tools"); import jlc
    rows = jlc.search("DMC2400UV")          # list of dicts; see Part fields below

Uses the same public JSON endpoint as jlcpcb.com's parts search page. It is undocumented, so
a changed response shape raises JLCError with the raw payload instead of guessing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys

API = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"


class JLCError(RuntimeError):
    pass


def _post(payload: dict) -> dict:
    # curl rather than urllib: it honours the environment's proxy and CA bundle the same way
    # every other tool here does.
    cmd = ["curl", "-sS", "--http1.1", "-m", "30", "-A", "Mozilla/5.0", API,
           "-H", "content-type: application/json", "-d", json.dumps(payload)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise JLCError(f"curl failed ({out.returncode}): {out.stderr.strip()}")
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError as e:
        raise JLCError(f"non-JSON response: {out.stdout[:300]!r}") from e


def search(keyword: str, page_size: int = 10) -> list[dict]:
    """Return parts matching `keyword` (an MPN, LCSC code like C2879853, or free text)."""
    data = _post({"keyword": keyword, "currentPage": 1, "pageSize": page_size})
    try:
        items = data["data"]["componentPageInfo"]["list"] or []
    except (KeyError, TypeError) as e:
        raise JLCError(f"unexpected response shape: {json.dumps(data)[:300]}") from e
    when = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    rows = []
    for c in items:
        prices = c.get("componentPrices") or []
        rows.append({
            "query": keyword,
            "queried_utc": when,
            "mpn": c.get("componentModelEn"),
            "lcsc": c.get("componentCode"),
            "manufacturer": c.get("componentBrandEn"),
            "package": c.get("componentSpecificationEn"),
            "library": {"base": "Basic", "expand": "Extended"}.get(c.get("componentLibraryType"),
                                                                   c.get("componentLibraryType")),
            "stock": c.get("stockCount"),
            "price_usd_qty1": prices[0].get("productPrice") if prices else None,
            "price_breaks": [(p.get("startNumber"), p.get("productPrice")) for p in prices],
            "description": c.get("describe") or c.get("erpComponentName"),
            "datasheet": c.get("dataManualUrl"),
        })
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("keywords", nargs="+", help="MPNs, LCSC codes (C123456) or search text")
    ap.add_argument("-n", type=int, default=10, help="rows per keyword (default 10)")
    ap.add_argument("--all", action="store_true", help="also show zero-stock rows")
    ap.add_argument("--json", action="store_true", help="print JSON lines instead of a table")
    a = ap.parse_args(argv)
    status = 0
    for kw in a.keywords:
        try:
            rows = search(kw, a.n)
        except JLCError as e:
            print(f"{kw}: ERROR {e}", file=sys.stderr)
            status = 1
            continue
        if not a.all:
            rows = [r for r in rows if (r["stock"] or 0) > 0]
        rows.sort(key=lambda r: -(r["stock"] or 0))
        if a.json:
            for r in rows:
                print(json.dumps(r))
            continue
        stamp = rows[0]["queried_utc"] if rows else dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        print(f"## {kw}  (JLC parts API, {stamp})")
        if not rows:
            print("   no in-stock matches" + ("" if a.all else " (try --all)"))
        for r in rows:
            price = f"${r['price_usd_qty1']:.4f}" if isinstance(r["price_usd_qty1"], (int, float)) else "-"
            print(f"   {r['mpn']!s:28} {r['lcsc']!s:10} {r['library']!s:8} stock {r['stock']!s:>8}  "
                  f"{price:>9}  {r['package']}")
    return status


if __name__ == "__main__":
    sys.exit(main())
