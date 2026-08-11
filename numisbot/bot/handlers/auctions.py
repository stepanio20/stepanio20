"""/auctions, /find, /price — browse cached auction data."""
from __future__ import annotations

import datetime as dt

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..texts import lot_card, realized_line, t

router = Router()


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


def _fmt_ts(ts: int | None, lang: str) -> str:
    if not ts:
        return "—"
    d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    return d.strftime("%d.%m.%Y %H:%M UTC")


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
    lines = [t("auctions_header", lang)]
    for a in auctions[:10]:
        status = "🟢 LIVE" if a["status"] == "live" else "🗓"
        when = _fmt_ts(a["starts"], lang) if a["status"] != "live" else _fmt_ts(a["ends"], lang)
        label = ("завершение" if a["status"] == "live" else "старт") if lang == "ru" else (
            "ends" if a["status"] == "live" else "starts")
        lots = f" · {a['lots_count']} " + ("лотов" if lang == "ru" else "lots") if a["lots_count"] else ""
        link = f' — <a href="{a["url"]}">↗</a>' if a["url"] else ""
        lines.append(f"{status} <b>{a['title']}</b>{lots}\n     {label}: {when}{link}")
    await msg.answer("\n".join(lines), disable_web_page_preview=True)


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
    for lot in lots[:5]:
        await msg.answer(lot_card(lot, lang), disable_web_page_preview=False)


@router.message(Command("price"))
async def cmd_price(msg: Message, command: CommandObject, db: Database, scheduler_service=None):
    lang = await _lang(db, msg.from_user.id)
    query = (command.args or "").strip()
    if not query:
        await msg.answer(t("history_usage", lang))
        return
    rows = []
    if scheduler_service is not None:
        try:
            rows = await scheduler_service.api_price_history(query, limit=20)
        except Exception:
            rows = []
    if not rows:
        rows = await db.price_history(query, limit=20)
    if not rows:
        await msg.answer(t("search_empty", lang).format(q=query))
        return
    tier = await db.effective_tier(msg.from_user.id)
    shown = rows if tier != "free" else rows[:3]
    header = ("📉 <b>Реализованные цены: «{q}»</b>\n━━━━━━━━━━━━━━━" if lang == "ru"
              else "📉 <b>Realized prices: “{q}”</b>\n━━━━━━━━━━━━━━━").format(q=query)
    body = "\n".join(realized_line(r, lang) for r in shown)
    tail = ""
    if tier == "free" and len(rows) > len(shown):
        tail = t("history_free_teaser", lang).format(shown=len(shown), found=len(rows))
    await msg.answer(f"{header}\n{body}{tail}", disable_web_page_preview=True)


@router.callback_query(F.data == "m:price")
async def cb_price(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    await cb.message.answer(t("history_usage", lang))
    await cb.answer()
