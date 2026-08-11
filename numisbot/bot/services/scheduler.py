"""Background jobs: refresh auction data, match watches, closing-soon alerts."""
from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..config import Config
from ..db import Database
from ..texts import lot_card, t
from .katz_parser import KatzParser

log = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, bot: Bot, db: Database, cfg: Config):
        self.bot = bot
        self.db = db
        self.cfg = cfg
        self.parser = KatzParser(cfg.katz_base_url, cfg.http_timeout)
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self.scheduler.add_job(
            self.refresh_now, "interval",
            minutes=self.cfg.parse_interval_minutes, id="refresh",
        )
        self.scheduler.add_job(self.closing_alerts, "interval", minutes=10, id="closing")
        self.scheduler.start()

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        await self.parser.close()

    # -- jobs -------------------------------------------------------------
    async def refresh_now(self) -> str:
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
        """Live global search straight from the Katz API (all ~520k lots)."""
        rows = await self.parser.search_lots(query, pages=1)
        if live_only:
            rows = [r for r in rows if r["realized"] is None]
        return rows[:limit]

    async def api_price_history(self, query: str, limit: int = 20):
        rows = await self.parser.search_lots(query, pages=2)
        return [r for r in rows if r["realized"] is not None][:limit]

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
                    await self.bot.send_message(
                        w["user_id"],
                        t("alert_match", lang).format(q=w["query"]) + "\n\n" + lot_card(lot, lang),
                    )
                    await self.db.mark_alert_sent(w["user_id"], lot["id"], "match")
                except Exception as e:
                    log.debug("alert to %s failed: %s", w["user_id"], e)

    async def closing_alerts(self) -> None:
        """Notify watchers ~1h before a matched lot closes (15 min for Pro)."""
        lots = await self.db.closing_soon(within_minutes=70)
        if not lots:
            return
        for w in await self.db.all_watches():
            q = w["query"].lower()
            user = await self.db.get_user(w["user_id"])
            lang = user["lang"] if user else "ru"
            for lot in lots:
                if q not in (lot["title"] or "").lower():
                    continue
                if await self.db.alert_already_sent(w["user_id"], lot["id"], "closing"):
                    continue
                try:
                    await self.bot.send_message(
                        w["user_id"],
                        t("alert_closing", lang) + "\n\n" + lot_card(lot, lang),
                    )
                    await self.db.mark_alert_sent(w["user_id"], lot["id"], "closing")
                except Exception as e:
                    log.debug("closing alert to %s failed: %s", w["user_id"], e)
