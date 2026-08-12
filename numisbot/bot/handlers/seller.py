"""/sell — consignment lead form (one-message FSM, photos welcome)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..config import Config
from ..db import Database
from ..keyboards import cancel_kb
from ..texts import esc, t

router = Router()


class SellForm(StatesGroup):
    waiting_description = State()


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


@router.message(Command("sell"))
async def cmd_sell(msg: Message, db: Database, state: FSMContext):
    lang = await _lang(db, msg.from_user.id)
    await state.set_state(SellForm.waiting_description)
    await msg.answer(t("sell_pitch", lang), reply_markup=cancel_kb(lang))


@router.callback_query(F.data == "m:sell")
async def cb_sell(cb: CallbackQuery, db: Database, state: FSMContext):
    lang = await _lang(db, cb.from_user.id)
    await state.set_state(SellForm.waiting_description)
    await cb.message.answer(t("sell_pitch", lang), reply_markup=cancel_kb(lang))
    await cb.answer()


@router.message(SellForm.waiting_description, F.text | F.photo | F.document)
async def sell_description(msg: Message, db: Database, state: FSMContext, cfg: Config):
    lang = await _lang(db, msg.from_user.id)
    contact = f"@{msg.from_user.username}" if msg.from_user.username else str(msg.from_user.id)
    description = msg.text or msg.caption or "(photo)"
    lead_id = await db.add_seller_lead(msg.from_user.id, contact, description)
    await db.track(msg.from_user.id, "sell_lead")
    await state.clear()
    await msg.answer(t("sell_thanks", lang).format(lead_id=lead_id))
    # forward the original message (photos intact) + a service note, HTML-safe
    for admin_id in cfg.admin_ids:
        try:
            await msg.forward(admin_id)
            await msg.bot.send_message(
                admin_id,
                f"💼 <b>Заявка на консигнацию #{lead_id}</b>\n"
                f"От: {esc(contact)} (id {msg.from_user.id})",
            )
        except Exception:
            pass
