"""/auctions, /find, /price — Telegram-native cards: photo-first, buttons."""
from __future__ import annotations

import datetime as dt

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..keyboards import auctions_kb, lot_kb, price_kb
from ..texts import lot_card, photo_url, price_summary, t

router = Router()


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


async def send_lot_card(msg: Message, lot, lang: str) -> None:
    caption = lot_card(lot, lang)
    kb = lot_kb(lot, lang)
    url = photo_url(lot)
    if url:
        try:
            await msg.answer_photo(photo=url, caption=caption, reply_markup=kb)
            return
        except Exception:
            pass  # bad/expired image — fall back to text
    await msg.answer(caption, reply_markup=kb, disable_web_page_preview=True)


def _fmt_ts(ts: int | None) -> str:
    if not ts:
        return "—"
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%d.%m %H:%M UTC")


@router.message(Command("auctions"))
async def cmd_auctions(msg: Message, db: Database):
    await _show_auctions(msg, msg.from_user.id, db)


@router.callback_query(F.data == "m:auctions")
async def cb_auctions(cb: CallbackQuery, db: Database):
    await _show_auctions(cb.message, cb.from_user.id, db)
    await cb.answer()


async def _show_auctions(msg: Message, user_id: int, db: Database):
    lang = await _lang(db, user_id)
    auctions = await db.live_auctions()
    if not auctions:
        await msg.answer(t("auctions_header", lang) + "\n" + t("no_auctions", lang))
        return
    ru = lang == "ru"
    lines = [t("auctions_header", lang), ""]
    for a in auctions[:8]:
        if a["status"] == "live":
            when = ("завершение " if ru else "ends ") + _fmt_ts(a["ends"])
            mark = "🟢"
        else:
            when = ("старт " if ru else "starts ") + _fmt_ts(a["starts"])
            mark = "🗓"
        lots = f" · {a['lots_count']} " + ("лотов" if ru else "lots") if a["lots_count"] else ""
        lines.append(f"{mark} <b>{a['title'].strip()}</b>{lots}\n      {when}")
    await msg.answer("\n".join(lines), reply_markup=auctions_kb(auctions, lang),
                     disable_web_page_preview=True)


@router.message(Command("find"))
async def cmd_find(msg: Message, command: CommandObject, db: Database, scheduler_service=None):
    lang = await _lang(db, msg.from_user.id)
    query = (command.args or "").strip()
    if not query:
        await msg.answer(t("search_usage", lang))
        return
    lots = []
    if scheduler_service is not None:
        try:
            lots = await scheduler_service.api_search(query, live_only=True)
        except Exception:
            lots = []
    if not lots:
        lots = await db.search_lots(query)
    if not lots:
        await msg.answer(t("search_empty", lang).format(q=query))
        return
    for lot in lots[:4]:
        await send_lot_card(msg, lot, lang)


@router.message(Command("price"))
async def cmd_price(msg: Message, command: CommandObject, db: Database, scheduler_service=None):
    lang = await _lang(db, msg.from_user.id)
    query = (command.args or "").strip()
    if not query:
        await msg.answer(t("history_usage", lang))
        return
    # local archive first (fast, offline); fall back to live API
    rows = await db.price_history(query, limit=30)
    if not rows and scheduler_service is not None:
        try:
            rows = await scheduler_service.api_price_history(query, limit=30)
        except Exception:
            rows = []
    if not rows:
        await msg.answer(t("search_empty", lang).format(q=query))
        return

    tier = await db.effective_tier(msg.from_user.id)
    shown = len(rows) if tier != "free" else min(5, len(rows))
    locked = len(rows) - shown
    caption = price_summary(query, rows, lang, shown=shown, locked=locked)
    kb = price_kb(query, lang)

    url = photo_url(rows[0]) if rows[0]["image"] else None
    if url and len(caption) <= 1024:
        try:
            await msg.answer_photo(photo=url, caption=caption, reply_markup=kb)
            return
        except Exception:
            pass
    await msg.answer(caption, reply_markup=kb, disable_web_page_preview=True)


@router.callback_query(F.data == "m:price")
async def cb_price(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    await cb.message.answer(t("history_usage", lang))
    await cb.answer()
