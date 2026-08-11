"""Background jobs: refresh auction data, match watches, closing-soon alerts."""
from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import asyncio

from ..config import Config
from ..db import Database
from ..keyboards import lot_kb
from ..texts import esc, lot_card, photo_url, t
from .katz_parser import KatzParser

log = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, bot: Bot, db: Database, cfg: Config):
        self.bot = bot
        self.db = db
        self.cfg = cfg
        self.parser = KatzParser(cfg.katz_base_url, cfg.http_timeout)
        self.scheduler = AsyncIOScheduler()
        self._refresh_lock = asyncio.Lock()

    def start(self) -> None:
        self.scheduler.add_job(
            self.refresh_now, "interval",
            minutes=self.cfg.parse_interval_minutes, id="refresh",
        )
        self.scheduler.add_job(self.closing_alerts, "interval", minutes=7, id="closing")
        self.scheduler.start()

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        await self.parser.close()

    # -- jobs -------------------------------------------------------------
    async def refresh_now(self) -> str:
        if self._refresh_lock.locked():
            return "already running"
        async with self._refresh_lock:
            return await self._refresh_now_locked()

    async def _refresh_now_locked(self) -> str:
        try:
            auctions = await self.parser.fetch_auctions()
        except Exception as e:
            log.warning("auction refresh failed: %s", e)
            return "fetch failed"
        new_lots = 0
        for a in auctions:
            await self.db.upsert_auction(a)
        # sync lots of active auctions only; archive is reachable via API search
        for a in [x for x in auctions if x["status"] in ("live", "upcoming")][:4]:
            try:
                lots = await self.parser.fetch_lots(a["id"], auction_ends=a["ends"])
            except Exception as e:
                log.warning("lots fetch failed for %s: %s", a["id"], e)
                continue
            await self.db.upsert_lots(lots)
            new_lots += len(lots)
        await self.match_watches()
        return f"{len(auctions)} auctions, {new_lots} lots"

    async def api_search(self, query: str, live_only: bool = True, limit: int = 8):
        """Live global search straight from the Katz API (all ~520k lots).

        Results are cached into our own DB (lot rows incl. image URLs) so
        card buttons like '➕ В радар' can look the lot up later.
        """
        rows = await self.parser.search_lots(query, pages=1)
        await self.db.upsert_lots(rows)
        if live_only:
            rows = [r for r in rows if r["realized"] is None]
        return rows[:limit]

    async def api_price_history(self, query: str, limit: int = 20):
        rows = await self.parser.search_lots(query, pages=2)
        await self.db.upsert_lots(rows)
        return [r for r in rows if r["realized"] is not None][:limit]

    async def _send_lot_alert(self, user_id: int, header: str, lot, lang: str) -> None:
        """Photo card with buttons; text fallback on bad images."""
        caption = header + "\n\n" + lot_card(lot, lang)
        kb = lot_kb(lot, lang, in_radar=True)  # it matched their radar already
        url = photo_url(lot)
        if url:
            try:
                await self.bot.send_photo(user_id, photo=url, caption=caption, reply_markup=kb)
                return
            except Exception:
                pass
        await self.bot.send_message(user_id, caption, reply_markup=kb,
                                    disable_web_page_preview=True)

    async def match_watches(self) -> None:
        """Send radar alerts for new matching lots."""
        for w in await self.db.all_watches():
            lots = await self.db.search_lots(w["query"], limit=5)
            user = await self.db.get_user(w["user_id"])
            lang = user["lang"] if user else "ru"
            for lot in lots:
                if w["max_price"] and (lot["current_bid"] or lot["start_price"] or 0) > w["max_price"]:
                    continue
                if await self.db.alert_already_sent(w["user_id"], lot["id"], "match"):
                    continue
                try:
                    await self._send_lot_alert(
                        w["user_id"], t("alert_match", lang).format(q=esc(w["query"])),
                        lot, lang)
                    await self.db.mark_alert_sent(w["user_id"], lot["id"], "match")
                except Exception as e:
                    log.debug("alert to %s failed: %s", w["user_id"], e)

    async def closing_alerts(self) -> None:
        """~1h reminder for everyone; extra ~10-min sniper ping for Sniper+/Dealer."""
        lots_1h = await self.db.closing_soon(within_minutes=70)
        lots_10m = await self.db.closing_soon(within_minutes=12)
        if not lots_1h and not lots_10m:
            return
        for w in await self.db.all_watches():
            q = w["query"].lower()
            user = await self.db.get_user(w["user_id"])
            lang = user["lang"] if user else "ru"
            tier = await self.db.effective_tier(w["user_id"])
            plans = [("closing", lots_1h, t("alert_closing", lang))]
            if tier in ("sniper", "dealer"):
                plans.append(("closing10", lots_10m, t("alert_closing10", lang)))
            for kind, lots, header in plans:
                for lot in lots:
                    if q not in (lot["title"] or "").lower():
                        continue
                    if await self.db.alert_already_sent(w["user_id"], lot["id"], kind):
                        continue
                    try:
                        await self._send_lot_alert(w["user_id"], header, lot, lang)
                        await self.db.mark_alert_sent(w["user_id"], lot["id"], kind)
                    except Exception as e:
                        log.debug("%s alert to %s failed: %s", kind, w["user_id"], e)
