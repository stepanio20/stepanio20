"""Client for the public katzauction.com JSON API (v1.0).

Recon notes (verified live):
- GET /api/v1.0/auction?to_page=N          — auctions, per_page=10, no auth
  statuses: created | prebidding | waiting_room | live | paused | completed
  pseudo-auctions with id <= 0 ("Master Data", "Shop") must be skipped
- GET /api/v1.0/lot?auction_id=N&display=48&to_page=P — lots, per_page 12/24/48
  numbers arrive as strings; sold_price is int for sold lots, "-" during sale
- Realized prices are public for the whole archive (~205 auctions, ~520k lots)
- Dates are naive ISO in Europe/Prague local time
- No anti-bot beyond Cloudflare defaults; be polite anyway: 1 rps, capped pages

Politeness contract: sequential requests, >=1s spacing, browser-like UA with a
bot marker, bounded page counts per cycle, back off on 5xx.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import re
import time
from typing import Any

import httpx

try:
    from zoneinfo import ZoneInfo
    _PRAGUE = ZoneInfo("Europe/Prague")
except Exception:  # tzdata missing — fall back to fixed CEST
    _PRAGUE = dt.timezone(dt.timedelta(hours=2))

log = logging.getLogger(__name__)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 KatzCoinsRadar/1.0 (Telegram bot)")

_YEAR_RE = re.compile(r"\b(1[0-9]\d{2}|20[0-2]\d)\b")
_GRADE_RE = re.compile(
    r"\b(NGC|PCGS|PMG|LCG)\s*[A-Za-z]*\s*\d{1,2}\b|\b(PROOF|UNC|AUNC|AU|XF|EF|VF|VG)\b",
    re.IGNORECASE,
)
_METALS = [
    ("gold", "Gold"), ("золот", "Gold"), (" av ", "Gold"),
    ("silver", "Silver"), ("серебр", "Silver"), (" ar ", "Silver"),
    ("copper", "Copper"), ("bronze", "Bronze"), (" ae ", "Bronze"),
    ("platinum", "Platinum"), ("nickel", "Nickel"), ("brass", "Brass"),
]

# auction.status → coarse status used by the bot
STATUS_MAP = {
    "created": "upcoming",
    "prebidding": "live",
    "waiting_room": "live",
    "live": "live",
    "paused": "live",
    "completed": "past",
}


def _num(v: Any) -> float | None:
    """API sends numbers as int, str, '-', 'None' or null."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s or s in ("-", "None", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _int(v: Any) -> int:
    n = _num(v)
    return int(n) if n is not None else 0


def _ts(v: Any) -> int | None:
    """Naive ISO datetime in Prague local time → unix ts."""
    if not v or not isinstance(v, str):
        return None
    try:
        d = dt.datetime.fromisoformat(v[:19])
    except ValueError:
        return None
    return int(d.replace(tzinfo=_PRAGUE).timestamp())


def enrich_from_title(title: str, description: str = "") -> dict[str, str]:
    """year/metal/grade live in free text, not in the (null) API fields."""
    text = f"{title} {description}"
    out = {"year": "", "metal": "", "grade": ""}
    if m := _YEAR_RE.search(title):
        out["year"] = m.group(1)
    low = f" {text.lower()} "
    for needle, label in _METALS:
        if needle in low:
            out["metal"] = label
            break
    if m := _GRADE_RE.search(text):
        out["grade"] = m.group(0).upper().strip()
    return out


def category_icon(category: str) -> str:
    c = (category or "").lower()
    if c.startswith("banknote"):
        return "💵"
    if c.startswith("phaleristic"):
        return "🎖"
    return "🪙"


class KatzParser:
    def __init__(self, base_url: str, timeout: float = 25.0):
        self.base = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=timeout, follow_redirects=True,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def _get_json(self, path: str, **params) -> Any:
        await asyncio.sleep(1.0)  # politeness spacing
        for attempt in (1, 2, 3):
            try:
                r = await self.client.get(self.base + path, params=params or None)
                if r.status_code >= 500:
                    raise httpx.HTTPStatusError("5xx", request=r.request, response=r)
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPError, ValueError) as e:
                if attempt == 3:
                    raise
                log.debug("retry %s after %s", path, e)
                await asyncio.sleep(2 * attempt)

    # -- auctions ---------------------------------------------------------
    async def fetch_auctions(self, max_pages: int = 4) -> list[dict[str, Any]]:
        """Recent auctions (newest first). 4 pages × 10 covers current + recent past."""
        out: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            data = await self._get_json("/api/v1.0/auction", order="id_desc", to_page=page)
            results = data.get("results") or []
            for a in results:
                aid = _int(a.get("id"))
                if aid <= 0:  # "Master Data" / "Inventory" / "Shop" pseudo-auctions
                    continue
                out.append(self._auction_row(a, aid))
            if page >= _int(data.get("pages")):
                break
        return out

    def _auction_row(self, a: dict[str, Any], aid: int) -> dict[str, Any]:
        return {
            "id": aid,
            "title": (a.get("title") or f"Auction {aid}").strip()[:200],
            "status": STATUS_MAP.get(str(a.get("status")), "upcoming"),
            "starts": _ts(a.get("planned_starting_time")) or _ts(a.get("starting_time")),
            "ends": _ts(a.get("planned_ending_time")) or _ts(a.get("ending_time")),
            "lots_count": _int(a.get("count_all_items")),
            "url": f"{self.base}/lots?auction_id={aid}",
        }

    # -- lots -------------------------------------------------------------
    async def fetch_lots(
        self, auction_id: int, max_pages: int = 60, auction_ends: int | None = None
    ) -> list[dict[str, Any]]:
        """All lots of one auction, display=48. 60 pages cover a 2,880-lot sale."""
        out: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            data = await self._get_json(
                "/api/v1.0/lot", auction_id=auction_id, display=48, to_page=page
            )
            results = data.get("results") or []
            if not results:
                break
            for l in results:
                out.append(self._lot_row(l, auction_id, auction_ends))
            if page >= _int(data.get("pages")):
                break
        return out

    async def search_lots(self, query: str, pages: int = 1) -> list[dict[str, Any]]:
        """Global full-text search across the whole base (all auctions)."""
        out: list[dict[str, Any]] = []
        for page in range(1, pages + 1):
            data = await self._get_json("/api/v1.0/lot", search=query, display=48, to_page=page)
            results = data.get("results") or []
            for l in results:
                if _int(l.get("auction_id")) <= 0:
                    continue
                out.append(self._lot_row(l, _int(l.get("auction_id")), None))
            if page >= _int(data.get("pages")):
                break
        return out

    def _lot_row(
        self, l: dict[str, Any], auction_id: int, auction_ends: int | None
    ) -> dict[str, Any]:
        lid = _int(l.get("id"))
        title = (l.get("title") or "").strip()
        extra = enrich_from_title(title, str(l.get("description") or "")[:500])
        status = str(l.get("status") or "")
        sold_price = _num(l.get("sold_price"))
        highest_bid = _num((l.get("context") or {}).get("highest_bid"))
        image = ""
        for img in l.get("images") or []:
            if str(img.get("main")) == "True" or not image:
                image = str(img.get("file_path") or "")
        return {
            "id": lid,
            "auction_id": auction_id,
            "number": _int(l.get("lot_number")),
            "title": title[:300],
            "category": str(l.get("category") or ""),
            "country": str(l.get("country") or ""),
            "year": str(l.get("year") or "") if l.get("year") not in (None, "None") else extra["year"],
            "metal": extra["metal"],
            "grade": extra["grade"],
            "start_price": _num(l.get("start_price")),
            "current_bid": highest_bid,
            "bids": 0,  # not exposed by the API
            "estimate": None,  # Katz starts everything at 5 EUR, no estimates
            "currency": str(l.get("currency") or "EUR"),
            # sold_price of an unsold lot is just the last bid — not a real sale
            "realized": sold_price if status == "sold" else None,
            "ends": auction_ends,
            "url": f"{self.base}/lot/{lid}",
            "image": image,
            "updated": int(time.time()),
        }
