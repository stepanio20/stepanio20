"""Primary navigation: persistent reply-keyboard buttons, /menu, /cancel,
free-text search fallback and a stale-callback catch-all.

Registered FIRST so a nav button always works as an escape hatch from any
FSM flow (state is cleared before dispatching).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..config import Config
from ..db import Database
from ..keyboards import main_reply_kb
from ..texts import BTN, t

router = Router()

# label → action, both languages
_ACTIONS: dict[str, str] = {}
for _lang_labels in BTN.values():
    for _action, _label in _lang_labels.items():
        _ACTIONS[_label] = _action


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


@router.message(Command("menu"))
async def cmd_menu(msg: Message, db: Database, state: FSMContext):
    await state.clear()
    lang = await _lang(db, msg.from_user.id)
    await msg.answer(t("menu", lang), reply_markup=main_reply_kb(lang))


@router.message(Command("cancel"))
async def cmd_cancel(msg: Message, db: Database, state: FSMContext):
    await state.clear()
    lang = await _lang(db, msg.from_user.id)
    await msg.answer(t("cancelled", lang), reply_markup=main_reply_kb(lang))


@router.callback_query(F.data == "cancel")
async def cb_cancel(cb: CallbackQuery, db: Database, state: FSMContext):
    await state.clear()
    lang = await _lang(db, cb.from_user.id)
    await cb.message.answer(t("cancelled", lang), reply_markup=main_reply_kb(lang))
    await cb.answer()


@router.message(F.text.in_(set(_ACTIONS)))
async def on_nav_button(msg: Message, db: Database, cfg: Config,
                        state: FSMContext, scheduler_service=None):
    """Reply-keyboard button pressed — always wins, cancels any flow."""
    await state.clear()
    await db.upsert_user(msg.from_user.id, msg.from_user.username)
    action = _ACTIONS[msg.text]
    lang = await _lang(db, msg.from_user.id)

    # local imports to avoid circular deps at module load
    from . import auctions, market, seller, subscribe, watchlist

    if action == "auctions":
        await auctions._show_auctions(msg, msg.from_user.id, db)
    elif action == "watchlist":
        await watchlist._show_watchlist(msg, msg.from_user.id, db, cfg)
    elif action == "find":
        await state.set_state(auctions.QueryForm.find)
        await msg.answer(t("ask_find_query", lang))
    elif action == "price":
        await state.set_state(auctions.QueryForm.price)
        await msg.answer(t("ask_price_query", lang))
    elif action == "market":
        await market.cmd_market(msg, db)
    elif action == "publish":
        await market.cmd_publish(msg, db, state)
    elif action == "sell":
        await seller.cmd_sell(msg, db, state)
    elif action == "pro":
        await subscribe.cmd_pro(msg, db, cfg)
