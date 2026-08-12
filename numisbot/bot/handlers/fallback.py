"""Tail router: free text becomes a search; stale buttons get a polite answer.

Registered LAST — anything that reached this point matched no command,
no FSM state and no nav button.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..texts import t

router = Router()


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def free_text_search(msg: Message, db: Database, scheduler_service=None):
    """'рубль 1912' without any command — the most natural input there is."""
    query = (msg.text or "").strip()
    if len(query) < 3:
        return
    from .auctions import _do_find
    await _do_find(msg, query, db, scheduler_service)


@router.callback_query()
async def stale_callback(cb: CallbackQuery, db: Database):
    row = await db.get_user(cb.from_user.id)
    lang = row["lang"] if row else "ru"
    await cb.answer(t("stale_button", lang), show_alert=False)
