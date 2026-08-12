"""Backfill the local DB with completed Katz auctions (realized prices).

Usage:
    python -m scripts.backfill --last 12 --db data/archive.sqlite3
    python -m scripts.backfill --all  --db data/archive.sqlite3   # ~11k requests, run overnight

Polite by construction: sequential requests at ~1 rps (KatzParser enforces
spacing), completed auctions are immutable so each is fetched exactly once —
re-runs skip auctions already fully stored.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.db import Database
from bot.services.katz_parser import KatzParser

log = logging.getLogger("backfill")


async def fetch_all_completed(parser: KatzParser) -> list[dict]:
    """Full auction registry (22 pages), completed only, newest first."""
    out: list[dict] = []
    page = 1
    while True:
        data = await parser._get_json("/api/v1.0/auction", order="id_desc", to_page=page)
        for a in data.get("results") or []:
            aid = int(float(a.get("id") or 0))
            if aid <= 0:
                continue
            row = parser._auction_row(a, aid)
            if row["status"] == "past":
                out.append(row)
        if page >= int(data.get("pages") or 1):
            break
        page += 1
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=12, help="how many recent completed auctions")
    ap.add_argument("--all", action="store_true", help="backfill the whole archive")
    ap.add_argument("--db", default="data/archive.sqlite3")
    ap.add_argument("--base", default="https://katzauction.com")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    db = Database(args.db)
    await db.connect()
    parser = KatzParser(args.base)

    try:
        completed = await fetch_all_completed(parser)
        log.info("completed auctions in registry: %d", len(completed))
        targets = completed if args.all else completed[: args.last]

        for i, a in enumerate(targets, 1):
            cur = await db.db.execute(
                "SELECT COUNT(*) c FROM lots WHERE auction_id=?", (a["id"],)
            )
            have = (await cur.fetchone())["c"]
            if have >= a["lots_count"] > 0:
                log.info("[%d/%d] auction %s already stored (%d lots), skip",
                         i, len(targets), a["id"], have)
                continue
            await db.upsert_auction(a)
            lots = await parser.fetch_lots(a["id"], max_pages=70, auction_ends=a["ends"])
            await db.upsert_lots(lots)
            sold = sum(1 for l in lots if l["realized"] is not None)
            log.info("[%d/%d] auction %s '%s': %d lots (%d sold)",
                     i, len(targets), a["id"], a["title"][:45], len(lots), sold)

        cur = await db.db.execute(
            "SELECT COUNT(*) c, SUM(realized IS NOT NULL) s FROM lots"
        )
        row = await cur.fetchone()
        log.info("DONE: %s lots in DB, %s with realized prices", row["c"], row["s"])
    finally:
        await parser.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
