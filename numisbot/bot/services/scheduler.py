"""Background jobs: refresh auction data, match watches, closing-soon alerts."""
from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import asyncio
import datetime as dt

from ..config import Config
from ..db import Database
from ..keyboards import digest_kb, lot_kb
from ..texts import esc, lot_card, photo_url, t
from .aftersale import run_aftersale
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
        # user-triggered searches share a small budget against the Katz API
        self._search_sem = asyncio.Semaphore(2)

    def start(self) -> None:
        self.scheduler.add_job(
            self.refresh_now, "interval",
            minutes=self.cfg.parse_interval_minutes, id="refresh",
        )
        self.scheduler.add_job(self.closing_alerts, "interval", minutes=7, id="closing")
        # Monday 09:00 UTC ≈ late morning across the RU/EU audience
        self.scheduler.add_job(self.weekly_digest, "cron",
                               day_of_week="mon", hour=9, id="digest")
        # daily unsold-lots feed for Sniper+/Dealer (3 cards/run, dedup inside)
        self.scheduler.add_job(self.aftersale, "cron", hour=10, id="aftersale")
        self.scheduler.start()

    async def aftersale(self) -> int:
        return await run_aftersale(self.bot, self.db)

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
        cur = await self.db.db.execute("SELECT COUNT(*) c FROM auctions")
        first_run = (await cur.fetchone())["c"] == 0
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
        await self.announce_new_auctions(silent=first_run)
        await self.match_watches()
        return f"{len(auctions)} auctions, {new_lots} lots"

    async def announce_new_auctions(self, silent: bool = False) -> None:
        """Broadcast newly published auctions once; silent on the first sync."""
        fresh = await self.db.unannounced_auctions()
        for a in fresh:
            await self.db.mark_announced(a["id"])
            if silent:
                continue
            when = "—"
            if a["starts"]:
                when = dt.datetime.fromtimestamp(
                    a["starts"], dt.timezone.utc).strftime("%d.%m %H:%M UTC")
            for u in await self.db.digest_recipients():
                lang = u["lang"] or "ru"
                text = t("new_auction", lang).format(
                    title=esc(a["title"].strip()), lots=a["lots_count"], when=when)
                interests = [x for x in (u["interests"] or "").split(",") if x]
                if interests:
                    n, _ = await self.db.interest_lots(interests, limit=1)
                    if n:
                        text += t("new_auction_hits", lang).format(n=n)
                try:
                    await self.bot.send_message(u["id"], text,
                                                reply_markup=digest_kb(lang))
                except Exception:
                    pass
                await asyncio.sleep(0.05)

    async def weekly_digest(self) -> None:
        """Monday digest: hottest live lots by each user's interests."""
        for u in await self.db.digest_recipients():
            lang = u["lang"] or "ru"
            interests = [x for x in (u["interests"] or "").split(",") if x]
            lots = await self.db.top_live_lots(interests, limit=3)
            if not lots:
                continue
            lines = [t("digest_header", lang)]
            for lot in lots:
                bid = f"€{lot['current_bid']:.0f}" if lot["current_bid"] else "€5"
                title = esc(lot["title"][:60])
                lines.append(f'▫️ <a href="{lot["url"]}">{title}</a> — {bid}')
            try:
                await self.bot.send_message(
                    u["id"], "\n".join(lines),
                    reply_markup=digest_kb(lang), disable_web_page_preview=True)
                await self.db.track(u["id"], "digest_sent")
            except Exception:
                pass
            await asyncio.sleep(0.05)

    async def api_search(self, query: str, live_only: bool = True, limit: int = 8):
        """Live global search straight from the Katz API (all ~520k lots).

        Results are cached into our own DB (lot rows incl. image URLs) so
        card buttons like '➕ В радар' can look the lot up later.
        """
        async with self._search_sem:
            rows = await self.parser.search_lots(query, pages=1)
        await self.db.upsert_lots(rows)
        if live_only:
            rows = [r for r in rows if r["realized"] is None]
        return rows[:limit]

    async def api_price_history(self, query: str, limit: int = 20):
        async with self._search_sem:
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
