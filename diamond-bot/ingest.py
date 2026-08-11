"""
Ingestion paths (the defensible ones, per the market study):

  1. forward()        — a dealer forwards messages/stock into the bot (opt-in, zero risk)
  2. import_csv()     — a supplier uploads a stock file in the RapNet-ish schema
  3. TelethonIngestor — per-subscriber BYO-session read-only reader for Telegram groups
                        the subscriber ALREADY belongs to (Telegram-sanctioned for user
                        sessions; never a central scraper account)

There is deliberately NO WhatsApp central-scraping path: covert WhatsApp parsing is a
ToS/ban/legal non-starter (see the market report §5).

The Telethon class is import-guarded so the bot runs without Telethon installed; the
group ingestor is opt-in and run per consenting subscriber.
"""
from __future__ import annotations

import csv
import io
from typing import Callable, Iterable, Optional

from parser import parse_message, Intent
import db


# ─────────────────────────── forward / manual ────────────────────────────────

def ingest_text(text: str, *, tg_id: Optional[int] = None, source: str = "forward",
                source_group: str = "", default_intent: Optional[str] = None) -> Optional[dict]:
    """Parse one message and store it as a listing or demand. Returns a summary dict."""
    stone = parse_message(text, default_intent=default_intent)
    if not stone:
        return None
    if "scam_suspect" in stone.flags:
        db.log_event("scam_filtered", tg_id, {"text": text[:200]})
        return {"stored": False, "reason": "scam_suspect", "summary": stone.key_summary()}
    payload = stone.to_dict()
    if stone.intent == Intent.WANT.value:
        did = db.add_demand(payload, tg_id=tg_id, source=source, source_group=source_group)
        return {"stored": True, "kind": "demand", "id": did, "summary": stone.key_summary(),
                "confidence": stone.confidence}
    else:
        lid = db.add_listing(payload, tg_id=tg_id, source=source, source_group=source_group)
        return {"stored": True, "kind": "listing", "id": lid, "summary": stone.key_summary(),
                "confidence": stone.confidence}


# ─────────────────────────── CSV / stock file ────────────────────────────────

# Map common RapNet-style headers to our fields (case-insensitive, spaces stripped).
_CSV_MAP = {
    "shape": "shape", "weight": "carat", "carat": "carat", "caratweight": "carat",
    "color": "color", "colour": "color", "clarity": "clarity", "cut": "cut",
    "cutgrade": "cut", "lab": "lab", "labname": "lab",
    "certificate": "cert_number", "certificate#": "cert_number", "certno": "cert_number",
    "reportnumber": "cert_number", "report#": "cert_number", "stocknumber": "stock",
    "fluorescence": "fluorescence", "fluorescenceintensity": "fluorescence",
    "cashprice": "total_price", "priceperct": "price_per_carat",
    "rapnetdiscountpercent": "rap_discount", "discount%": "rap_discount",
}


def import_csv(data: bytes, *, tg_id: Optional[int] = None, source_group: str = "") -> dict:
    """Import a supplier stock file. Returns counts."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    stored = 0
    skipped = 0
    for row in reader:
        norm = {}
        for k, v in row.items():
            if k is None:
                continue
            key = _CSV_MAP.get(k.strip().lower().replace(" ", "").replace("_", ""))
            if key and v not in (None, ""):
                norm[key] = v
        # coerce numerics
        for nk in ("carat", "price_per_carat", "total_price", "rap_discount"):
            if nk in norm:
                try:
                    norm[nk] = float(str(norm[nk]).replace(",", ""))
                except ValueError:
                    norm.pop(nk, None)
        if norm.get("color"):
            norm["color"] = str(norm["color"]).upper()
        if norm.get("clarity"):
            norm["clarity"] = str(norm["clarity"]).upper()
        if norm.get("lab"):
            norm["lab"] = str(norm["lab"]).upper()
        if not (norm.get("shape") or norm.get("carat")):
            skipped += 1
            continue
        norm["raw_text"] = "; ".join(f"{k}={v}" for k, v in norm.items())
        norm["confidence"] = 1.0
        db.add_listing(norm, tg_id=tg_id, source="csv", source_group=source_group)
        stored += 1
    return {"stored": stored, "skipped": skipped}


# ─────────────────────── Telegram BYO-session reader ──────────────────────────

class TelethonIngestor:  # pragma: no cover  (requires network + a real session)
    """
    Read-only ingestion of Telegram groups a *consenting subscriber* already belongs to.

    Usage (per subscriber, with their own api_id/api_hash + a StringSession they authorized):
        ing = TelethonIngestor(api_id, api_hash, session_string)
        await ing.run(groups=["@demandsnatural", ...], on_stone=callback)

    This is the Telegram-sanctioned path for user sessions. It NEVER sends messages
    (read-only => lowest ban risk) and processes per subscriber, not from a central account.
    """

    def __init__(self, api_id: int, api_hash: str, session_string: str):
        try:
            from telethon import TelegramClient, events           # noqa: F401
            from telethon.sessions import StringSession
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("Install telethon to use BYO-session ingestion: pip install telethon") from e
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        self._events = __import__("telethon").events
        self.client = TelegramClient(StringSession(session_string), api_id, api_hash)

    async def run(self, groups: Iterable[str], on_stone: Callable[[dict], None],
                  group_nature: Optional[dict] = None) -> None:
        group_nature = group_nature or {}
        events = self._events

        @self.client.on(events.NewMessage(chats=list(groups)))
        async def _handler(event):  # noqa: ANN001
            text = event.raw_text or ""
            handle = getattr(event.chat, "username", None)
            default = group_nature.get(f"@{handle}") if handle else None
            res = ingest_text(text, source="session",
                              source_group=f"@{handle}" if handle else "",
                              default_intent=default)
            if res and res.get("stored"):
                on_stone(res)

        await self.client.start()
        await self.client.run_until_disconnected()
