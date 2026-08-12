"""After-sale feed for Sniper+/Dealer: unsold lots of past auctions.

Katz regularly sells passed (unbid) lots directly after a sale, so paying
hunters get a heads-up on radar matches they can still buy: up to
PER_USER_CAP cards per user per run, deduped via alerts_sent
(kind='aftersale'). Wire run_aftersale() into the scheduler as a daily job.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from ..db import Database
from ..keyboards import lot_kb
from ..texts import lot_card, photo_url

log = logging.getLogger(__name__)

KIND = "aftersale"            # alerts_sent.kind used for dedup
PER_USER_CAP = 3              # cards per user per run
TIERS = ("sniper", "dealer")  # who gets the feed

# local copy deck: picked by users.lang, ru is the default
HEADERS = {
    "ru": "📦 <b>Не продан на прошедшем аукционе — можно спросить у Katz напрямую</b>",
    "en": "📦 <b>Unsold at a past auction — you can ask Katz about it directly</b>",
}


async def _unsold_past_lots(db: Database) -> list:
    """Unsold lots (no realized price) of finished, previously announced auctions.

    The announced_auctions filter keeps the feed to sales users actually saw
    while live, instead of replaying the whole historical archive.
    """
    cur = await db.db.execute(
        "SELECT l.* FROM lots l JOIN auctions a ON a.id=l.auction_id "
        "WHERE a.status='past' AND l.realized IS NULL "
        "AND a.id IN (SELECT auction_id FROM announced_auctions) "
        "ORDER BY a.ends DESC, l.number")
    return list(await cur.fetchall())


async def _send_card(bot: Bot, user_id: int, header: str, lot, lang: str) -> None:
    """Photo card with buttons; text fallback on bad images."""
    caption = header + "\n\n" + lot_card(lot, lang)
    kb = lot_kb(lot, lang, in_radar=True)  # it matched their radar already
    url = photo_url(lot)
    if url:
        try:
            await bot.send_photo(user_id, photo=url, caption=caption, reply_markup=kb)
            return
        except Exception:
            pass
    await bot.send_message(user_id, caption, reply_markup=kb,
                           disable_web_page_preview=True)


async def run_aftersale(bot: Bot, db: Database) -> int:
    """Push unsold-lot cards to Sniper+/Dealer radar owners; returns cards sent."""
    lots = await _unsold_past_lots(db)
    if not lots:
        return 0
    watches_by_user: dict[int, list] = {}
    for w in await db.all_watches():
        watches_by_user.setdefault(w["user_id"], []).append(w)
    sent_total = 0
    for user_id, watches in watches_by_user.items():
        if await db.effective_tier(user_id) not in TIERS:
            continue
        user = await db.get_user(user_id)
        lang = (user["lang"] if user else None) or "ru"
        header = HEADERS.get(lang, HEADERS["ru"])
        sent_user = 0
        for w in watches:
            if sent_user >= PER_USER_CAP:
                break
            q = w["query"].lower()
            for lot in lots:
                if sent_user >= PER_USER_CAP:
                    break
                if q not in (lot["title"] or "").lower():
                    continue
                if w["max_price"] and (lot["current_bid"] or lot["start_price"] or 0) > w["max_price"]:
                    continue
                if await db.alert_already_sent(user_id, lot["id"], KIND):
                    continue
                try:
                    await _send_card(bot, user_id, header, lot, lang)
                    await db.mark_alert_sent(user_id, lot["id"], KIND)
                    sent_user += 1
                    sent_total += 1
                except Exception as e:
                    log.debug("aftersale to %s failed: %s", user_id, e)
                await asyncio.sleep(0.05)  # ~20 msg/sec, inside Telegram limits
    return sent_total
