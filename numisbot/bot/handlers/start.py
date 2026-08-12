"""Onboarding: /start → language → interests → menu. Plus /help, /lang, menu callbacks."""
from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

from ..db import Database
from ..keyboards import interests_kb, lang_kb
from ..texts import t
from .auctions import send_lot_card

router = Router()

HERO = Path(__file__).resolve().parent.parent.parent / "assets" / "hero.png"


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


@router.message(CommandStart())
async def cmd_start(msg: Message, command: CommandObject, db: Database, state=None):
    if state is not None:
        await state.clear()
    # referral deep link: t.me/<bot>?start=ref_<user_id>
    payload = (command.args or "").strip()
    if payload.startswith("ref_") and payload[4:].isdigit():
        await db.set_referrer(msg.from_user.id, int(payload[4:]))
    await db.upsert_user(msg.from_user.id, msg.from_user.username)
    await db.track(msg.from_user.id, "start")
    row = await db.get_user(msg.from_user.id)
    if row and row["interests"]:  # returning user — straight to the point
        lang = row["lang"]
        from ..keyboards import main_reply_kb
        await msg.answer(t("welcome_back", lang), reply_markup=main_reply_kb(lang))
        return
    if HERO.exists():
        try:
            await msg.answer_photo(FSInputFile(HERO), caption=t("choose_lang", "ru"),
                                   reply_markup=lang_kb())
            return
        except Exception:
            pass
    await msg.answer(t("choose_lang", "ru"), reply_markup=lang_kb())


async def _edit(message: Message, text: str, kb=None) -> None:
    """Edit either a text message or a photo caption (the /start hero).

    Double-taps raise 'message is not modified' — swallow, the content is there.
    """
    try:
        if message.photo:
            await message.edit_caption(caption=text, reply_markup=kb)
        else:
            await message.edit_text(text, reply_markup=kb)
    except Exception:
        pass


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(cb: CallbackQuery, db: Database):
    lang = cb.data.split(":", 1)[1]
    await db.upsert_user(cb.from_user.id, cb.from_user.username)
    await db.set_lang(cb.from_user.id, lang)
    await _edit(cb.message, t("welcome", lang), interests_kb(lang, set()))
    await cb.answer()


@router.callback_query(F.data.startswith("int:"))
async def cb_interest(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    choice = cb.data.split(":", 1)[1]
    row = await db.get_user(cb.from_user.id)
    selected = set(x for x in (row["interests"] or "").split(",") if x)
    if choice == "done":
        await _edit(cb.message, t("onboarded", lang))
        await db.track(cb.from_user.id, "onboard_done")
        # welcome gift: 7 days of Pro, once per user
        if await db.try_use_trial(cb.from_user.id):
            await cb.message.answer(t("trial_granted", lang))
        # instant value: show live lots matching the chosen interests
        total, sample = await db.interest_lots(sorted(selected), limit=3)
        if total:
            await cb.message.answer(t("onboarded_hits", lang).format(n=total))
            for lot in sample:
                await send_lot_card(cb.message, lot, lang)
        from ..keyboards import main_reply_kb
        await cb.message.answer(t("menu", lang), reply_markup=main_reply_kb(lang))
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
    from ..keyboards import main_reply_kb
    await msg.answer(t("help", lang), reply_markup=main_reply_kb(lang))


@router.callback_query(F.data == "m:help")
async def cb_help(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    from ..keyboards import main_reply_kb
    await cb.message.answer(t("help", lang), reply_markup=main_reply_kb(lang))
    await cb.answer()


@router.message(Command("invite"))
async def cmd_invite(msg: Message, db: Database):
    lang = await _lang(db, msg.from_user.id)
    me = await msg.bot.me()
    link = f"https://t.me/{me.username}?start=ref_{msg.from_user.id}"
    await msg.answer(t("invite", lang).format(link=link),
                     disable_web_page_preview=True)
    await db.track(msg.from_user.id, "invite_view")


@router.message(Command("forgetme"))
async def cmd_forgetme(msg: Message, db: Database):
    lang = await _lang(db, msg.from_user.id)
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 Да, удалить всё" if lang == "ru" else "🗑 Yes, delete all",
                             callback_data="forget:yes"),
        InlineKeyboardButton(text="Отмена" if lang == "ru" else "Cancel",
                             callback_data="cancel"),
    ]])
    await msg.answer(t("forgetme_confirm", lang), reply_markup=kb)


@router.callback_query(F.data == "forget:yes")
async def cb_forget(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    await db.wipe_user(cb.from_user.id)
    from aiogram.types import ReplyKeyboardRemove
    await cb.message.answer(t("forgetme_done", lang), reply_markup=ReplyKeyboardRemove())
    await cb.answer("🗑")


@router.message(Command("digest"))
async def cmd_digest(msg: Message, db: Database):
    lang = await _lang(db, msg.from_user.id)
    off = await db.toggle_digest(msg.from_user.id)
    await msg.answer(t("digest_off" if off else "digest_on", lang))


@router.callback_query(F.data == "digest:off")
async def cb_digest_off(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    row = await db.get_user(cb.from_user.id)
    if row and not row["digest_off"]:
        await db.toggle_digest(cb.from_user.id)
    await cb.message.answer(t("digest_off", lang))
    await cb.answer("🔕")
