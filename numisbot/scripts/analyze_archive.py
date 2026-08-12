"""Aggregate a backfilled archive DB into demand/price analytics (JSON to stdout).

Usage: python -m scripts.analyze_archive --db data/archive.sqlite3 > analytics.json

This is the data behind the Dealer-tier "demand analytics" feature and the
pitch deck for the auction house.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics


def auction_kind(title: str) -> str:
    t = (title or "").lower()
    if "gold" in t:
        return "Gold"
    if "paper" in t or "banknote" in t:
        return "Paper Money"
    return "Coins"


PRICE_BINS = [(5, 10), (10, 20), (20, 50), (50, 100), (100, 200),
              (200, 500), (500, 1000), (1000, 5000), (5000, 10 ** 9)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/archive.sqlite3")
    args = ap.parse_args()

    c = sqlite3.connect(args.db)
    c.row_factory = sqlite3.Row

    lots = c.execute(
        "SELECT l.*, a.title AS auction_title FROM lots l "
        "JOIN auctions a ON a.id = l.auction_id"
    ).fetchall()
    sold = [l for l in lots if l["realized"] is not None]
    prices = [l["realized"] for l in sold]

    out: dict = {
        "auctions": c.execute("SELECT COUNT(DISTINCT auction_id) FROM lots").fetchone()[0],
        "lots": len(lots),
        "sold": len(sold),
        "sell_through_pct": round(100 * len(sold) / max(len(lots), 1), 1),
        "hammer_total_eur": round(sum(prices)),
        "median_eur": round(statistics.median(prices), 1) if prices else 0,
        "mean_eur": round(statistics.fmean(prices), 1) if prices else 0,
    }

    # by auction kind (Coins / Gold / Paper Money)
    kinds: dict[str, dict] = {}
    for l in lots:
        k = auction_kind(l["auction_title"])
        d = kinds.setdefault(k, {"lots": 0, "sold": 0, "sum": 0.0, "prices": []})
        d["lots"] += 1
        if l["realized"] is not None:
            d["sold"] += 1
            d["sum"] += l["realized"]
            d["prices"].append(l["realized"])
    out["by_kind"] = {
        k: {
            "lots": d["lots"], "sold": d["sold"],
            "sell_through_pct": round(100 * d["sold"] / max(d["lots"], 1), 1),
            "hammer_eur": round(d["sum"]),
            "median_eur": round(statistics.median(d["prices"]), 1) if d["prices"] else 0,
        }
        for k, d in sorted(kinds.items())
    }

    # price histogram over sold lots
    out["price_histogram"] = [
        {"bin": f"{lo}–{hi}" if hi < 10 ** 9 else f"{lo}+",
         "count": sum(1 for p in prices if lo <= p < hi)}
        for lo, hi in PRICE_BINS
    ]

    def top(group_field: str, n: int = 10, min_sold: int = 5) -> list[dict]:
        agg: dict[str, dict] = {}
        for l in sold:
            key = (l[group_field] or "").strip()
            if not key:
                continue
            d = agg.setdefault(key, {"sold": 0, "sum": 0.0, "prices": []})
            d["sold"] += 1
            d["sum"] += l["realized"]
            d["prices"].append(l["realized"])
        rows = [
            {"name": k, "sold": d["sold"], "hammer_eur": round(d["sum"]),
             "median_eur": round(statistics.median(d["prices"]), 1)}
            for k, d in agg.items() if d["sold"] >= min_sold
        ]
        return sorted(rows, key=lambda r: -r["hammer_eur"])[:n]

    out["top_categories"] = top("category")
    out["top_countries"] = top("country")

    # metal split (extracted from titles at parse time)
    metal_agg: dict[str, float] = {}
    for l in sold:
        m = l["metal"] or "Other/unspecified"
        metal_agg[m] = metal_agg.get(m, 0) + l["realized"]
    out["metal_hammer_eur"] = {
        k: round(v) for k, v in sorted(metal_agg.items(), key=lambda x: -x[1])
    }

    out["top_lots"] = [
        {"title": l["title"], "realized_eur": l["realized"],
         "country": l["country"], "category": l["category"],
         "auction": l["auction_title"].strip(), "url": l["url"]}
        for l in sorted(sold, key=lambda x: -x["realized"])[:12]
    ]

    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
