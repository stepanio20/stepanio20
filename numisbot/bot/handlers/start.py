"""Onboarding: /start → language → interests → menu. Plus /help, /lang, menu callbacks."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..keyboards import interests_kb, lang_kb, menu_kb
from ..texts import t
from .auctions import send_lot_card

router = Router()


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


@router.message(CommandStart())
async def cmd_start(msg: Message, db: Database):
    await db.upsert_user(msg.from_user.id, msg.from_user.username)
    await msg.answer(t("choose_lang", "ru"), reply_markup=lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(cb: CallbackQuery, db: Database):
    lang = cb.data.split(":", 1)[1]
    await db.upsert_user(cb.from_user.id, cb.from_user.username)
    await db.set_lang(cb.from_user.id, lang)
    await cb.message.edit_text(t("welcome", lang), reply_markup=interests_kb(lang, set()))
    await cb.answer()


@router.callback_query(F.data.startswith("int:"))
async def cb_interest(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    choice = cb.data.split(":", 1)[1]
    row = await db.get_user(cb.from_user.id)
    selected = set(x for x in (row["interests"] or "").split(",") if x)
    if choice == "done":
        await cb.message.edit_text(t("onboarded", lang))
        # instant value: show live lots matching the chosen interests
        total, sample = await db.interest_lots(sorted(selected), limit=3)
        if total:
            await cb.message.answer(t("onboarded_hits", lang).format(n=total))
            for lot in sample:
                await send_lot_card(cb.message, lot, lang)
        await cb.message.answer(t("menu", lang), reply_markup=menu_kb(lang))
        await cb.answer()
        return
    selected.symmetric_difference_update({choice})
    await db.set_interests(cb.from_user.id, ",".join(sorted(selected)))
    await cb.message.edit_reply_markup(reply_markup=interests_kb(lang, selected))
    await cb.answer()


@router.message(Command("lang"))
async def cmd_lang(msg: Message):
    await msg.answer(t("choose_lang", "ru"), reply_markup=lang_kb())


@router.message(Command("help"))
async def cmd_help(msg: Message, db: Database):
    lang = await _lang(db, msg.from_user.id)
    await msg.answer(t("help", lang), reply_markup=menu_kb(lang))


@router.message(Command("menu"))
async def cmd_menu(msg: Message, db: Database):
    lang = await _lang(db, msg.from_user.id)
    await msg.answer(t("menu", lang), reply_markup=menu_kb(lang))


@router.callback_query(F.data == "m:help")
async def cb_help(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    await cb.message.answer(t("help", lang))
    await cb.answer()
