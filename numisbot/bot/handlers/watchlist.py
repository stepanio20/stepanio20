"""Watchlist: /watch <query> [<max price], /watchlist, delete buttons."""
from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from ..config import Config
from ..db import Database
from ..keyboards import watchlist_kb
from ..texts import esc, t

router = Router()

_CAP_RE = re.compile(r"[<≤]\s*(\d+(?:[.,]\d+)?)\s*$")


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


async def _maybe_reward_referrer(bot, db: Database, user_id: int, was_first: bool) -> None:
    """First watch = activation: the inviter earns +30 days of Pro."""
    if not was_first:
        return
    referrer = await db.reward_referral(user_id)
    if referrer:
        ref_row = await db.get_user(referrer)
        ref_lang = ref_row["lang"] if ref_row else "ru"
        try:
            await bot.send_message(referrer, t("referral_reward", ref_lang))
        except Exception:
            pass


def _slots(cfg: Config, tier: str) -> int:
    return cfg.watch_slots(tier)


@router.message(Command("watch"))
async def cmd_watch(msg: Message, command: CommandObject, db: Database, cfg: Config):
    lang = await _lang(db, msg.from_user.id)
    query = (command.args or "").strip()
    if not query:
        await msg.answer(t("watch_usage", lang))
        return

    max_price = None
    m = _CAP_RE.search(query)
    if m:
        max_price = float(m.group(1).replace(",", "."))
        query = query[: m.start()].strip()

    if len(query) < 3:
        await msg.answer(t("watch_too_short", lang))
        return
    if await db.has_watch(msg.from_user.id, query):
        await msg.answer(t("already_watching", lang))
        return

    tier = await db.effective_tier(msg.from_user.id)
    used = len(await db.list_watches(msg.from_user.id))
    total = _slots(cfg, tier)
    if used >= total:
        await msg.answer(t("watch_limit", lang).format(total=total))
        return

    await db.add_watch(msg.from_user.id, query, max_price)
    await db.track(msg.from_user.id, "watch_add")
    cap = f" (&lt;{max_price:.0f})" if max_price else ""
    await msg.answer(t("watch_added", lang).format(q=esc(query), cap=cap, used=used + 1, total=total))
    await _maybe_reward_referrer(msg.bot, db, msg.from_user.id, was_first=(used == 0))


@router.message(Command("watchlist"))
async def cmd_watchlist(msg: Message, db: Database, cfg: Config):
    await _show_watchlist(msg, msg.from_user.id, db, cfg)


@router.callback_query(F.data == "m:watchlist")
async def cb_watchlist(cb: CallbackQuery, db: Database, cfg: Config):
    await _show_watchlist(cb.message, cb.from_user.id, db, cfg)
    await cb.answer()


async def _show_watchlist(msg: Message, user_id: int, db: Database, cfg: Config):
    lang = await _lang(db, user_id)
    watches = await db.list_watches(user_id)
    tier = await db.effective_tier(user_id)
    total = _slots(cfg, tier)
    header = t("watchlist_header", lang).format(used=len(watches), total=total)
    if not watches:
        await msg.answer(header + "\n" + t("watchlist_empty", lang))
        return
    await msg.answer(header, reply_markup=watchlist_kb(watches, lang))


async def _try_add_watch(cb: CallbackQuery, db: Database, cfg: Config, query: str) -> None:
    lang = await _lang(db, cb.from_user.id)
    if await db.has_watch(cb.from_user.id, query):
        await cb.answer(t("already_watching", lang), show_alert=False)
        return
    tier = await db.effective_tier(cb.from_user.id)
    used = len(await db.list_watches(cb.from_user.id))
    total = _slots(cfg, tier)
    if used >= total:
        await cb.message.answer(t("watch_limit", lang).format(total=total))
        await cb.answer("🚦")
        return
    await db.add_watch(cb.from_user.id, query, None)
    await db.track(cb.from_user.id, "watch_add")
    await cb.message.answer(
        t("watch_added", lang).format(q=esc(query), cap="", used=used + 1, total=total)
    )
    await cb.answer("🔭")
    await _maybe_reward_referrer(cb.bot, db, cb.from_user.id, was_first=(used == 0))


@router.callback_query(F.data.startswith("wl:"))
async def cb_watch_lot(cb: CallbackQuery, db: Database, cfg: Config):
    """'➕ В радар' under a lot card: watch by the lot's title prefix."""
    lot = await db.get_lot(int(cb.data.split(":", 1)[1]))
    if lot is None:
        await cb.answer("⚠️", show_alert=False)
        return
    query = " ".join(lot["title"].split())[:40].strip()
    await _try_add_watch(cb, db, cfg, query)


@router.callback_query(F.data.startswith("wq:"))
async def cb_watch_query(cb: CallbackQuery, db: Database, cfg: Config):
    """'🔭 Следить' under /price results: watch the searched query."""
    query = cb.data.split(":", 1)[1].strip()
    if not query:
        await cb.answer()
        return
    await _try_add_watch(cb, db, cfg, query)


@router.callback_query(F.data.startswith("unwatch:"))
async def cb_unwatch(cb: CallbackQuery, db: Database, cfg: Config):
    watch_id = int(cb.data.split(":", 1)[1])
    await db.delete_watch(cb.from_user.id, watch_id)
    lang = await _lang(db, cb.from_user.id)
    watches = await db.list_watches(cb.from_user.id)
    tier = await db.effective_tier(cb.from_user.id)
    total = _slots(cfg, tier)
    header = t("watchlist_header", lang).format(used=len(watches), total=total)
    try:
        if watches:
            await cb.message.edit_text(header, reply_markup=watchlist_kb(watches, lang))
        else:
            await cb.message.edit_text(header + "\n" + t("watchlist_empty", lang))
    except Exception:
        pass  # double-tap → "message is not modified"
    await cb.answer("🗑")
