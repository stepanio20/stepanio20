"""Telegram Stars subscriptions: /pro, invoices, pre-checkout, successful payment.

Stars subscription mechanics (Bot API 7.x+): send an invoice with currency XTR
and subscription_period=2592000 (30 days). Telegram then auto-charges monthly;
each renewal arrives as a successful_payment with is_recurring flags.
"""
from __future__ import annotations

import datetime as dt
import time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from ..config import Config
from ..db import Database
from ..keyboards import pro_kb
from ..texts import t

router = Router()


class PaySupportForm(StatesGroup):
    waiting = State()

SUB_PERIOD = 2592000  # 30 days, the only period Telegram allows for Stars subs
TIER_BY_PAYLOAD = {"sub:pro": "pro", "sub:sniper": "sniper", "sub:dealer": "dealer"}


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


@router.message(Command("pro"))
async def cmd_pro(msg: Message, db: Database, cfg: Config):
    lang = await _lang(db, msg.from_user.id)
    await msg.answer(
        t("pro_pitch", lang),
        reply_markup=pro_kb(lang, cfg.price_pro_stars, cfg.price_sniper_stars, cfg.price_dealer_stars),
    )


@router.callback_query(F.data == "m:pro")
async def cb_pro(cb: CallbackQuery, db: Database, cfg: Config):
    lang = await _lang(db, cb.from_user.id)
    await cb.message.answer(
        t("pro_pitch", lang),
        reply_markup=pro_kb(lang, cfg.price_pro_stars, cfg.price_sniper_stars, cfg.price_dealer_stars),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery, db: Database, cfg: Config):
    lang = await _lang(db, cb.from_user.id)
    tier = cb.data.split(":", 1)[1]
    stars = {"pro": cfg.price_pro_stars, "sniper": cfg.price_sniper_stars,
             "dealer": cfg.price_dealer_stars}.get(tier, cfg.price_pro_stars)
    title_key = {"pro": "invoice_title_pro", "sniper": "invoice_title_sniper",
                 "dealer": "invoice_title_dealer"}.get(tier, "invoice_title_pro")
    # subscription_period is a createInvoiceLink-only parameter (Bot API 8.0);
    # sendInvoice silently ignores it and the payment becomes one-off
    link = await cb.bot.create_invoice_link(
        title=t(title_key, lang),
        description=t("invoice_desc", lang),
        payload=f"sub:{tier}",
        currency="XTR",
        prices=[LabeledPrice(label=t(title_key, lang), amount=stars)],
        subscription_period=SUB_PERIOD,
    )
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text=(f"⭐ Оплатить {stars} Stars/мес" if lang == "ru"
              else f"⭐ Pay {stars} Stars/mo"), url=link)]])
    await cb.message.answer(t(title_key, lang) + "\n" + t("invoice_desc", lang),
                            reply_markup=kb)
    await cb.answer()


TIER_LABELS = {"pro": "Pro", "sniper": "Sniper+", "dealer": "Dealer"}


@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    if q.invoice_payload in TIER_BY_PAYLOAD:
        await q.answer(ok=True)
    else:
        await q.answer(ok=False, error_message="Счёт устарел — откройте /pro заново")


@router.message(Command("paysupport"))
async def cmd_paysupport(msg: Message, db: Database, state: FSMContext):
    lang = await _lang(db, msg.from_user.id)
    await state.set_state(PaySupportForm.waiting)
    from ..keyboards import cancel_kb
    await msg.answer(t("paysupport", lang), reply_markup=cancel_kb(lang))


def _nav_labels() -> set[str]:
    from ..texts import BTN
    return {label for labels in BTN.values() for label in labels.values()}


@router.message(PaySupportForm.waiting,
                (F.text & ~F.text.startswith("/") & ~F.text.in_(_nav_labels())) | F.photo)
async def paysupport_msg(msg: Message, db: Database, state: FSMContext, cfg: Config):
    lang = await _lang(db, msg.from_user.id)
    await state.clear()
    await msg.answer(t("paysupport_sent", lang))
    for admin_id in cfg.admin_ids:
        try:
            await msg.forward(admin_id)
            await msg.bot.send_message(
                admin_id, f"💬 <b>/paysupport</b> от id {msg.from_user.id} "
                          f"(@{msg.from_user.username or '—'})")
        except Exception:
            pass


@router.message(F.successful_payment)
async def on_paid(msg: Message, db: Database):
    lang = await _lang(db, msg.from_user.id)
    sp = msg.successful_payment
    # duplicate delivery of the same charge must not re-grant anything
    if await db.payment_exists(sp.telegram_payment_charge_id):
        return
    tier = TIER_BY_PAYLOAD.get(sp.invoice_payload, "pro")
    until = int(time.time()) + SUB_PERIOD
    if sp.subscription_expiration_date:
        until = int(sp.subscription_expiration_date.timestamp())
    await db.set_tier(msg.from_user.id, tier, until)
    await db.add_payment(
        msg.from_user.id,
        sp.telegram_payment_charge_id,
        tier,
        sp.total_amount,
        bool(sp.is_recurring),
    )
    until_str = dt.datetime.fromtimestamp(until, dt.timezone.utc).strftime("%d.%m.%Y")
    await msg.answer(t("paid", lang).format(tier=TIER_LABELS.get(tier, tier), until=until_str))
