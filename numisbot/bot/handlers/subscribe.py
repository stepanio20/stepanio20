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
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from ..config import Config
from ..db import Database
from ..keyboards import pro_kb
from ..texts import t

router = Router()

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
    await cb.message.answer_invoice(
        title=t(title_key, lang),
        description=t("invoice_desc", lang),
        payload=f"sub:{tier}",
        currency="XTR",
        prices=[LabeledPrice(label=t(title_key, lang), amount=stars)],
        subscription_period=SUB_PERIOD,
    )
    await cb.answer()


TIER_LABELS = {"pro": "Pro", "sniper": "Sniper+", "dealer": "Dealer"}


@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    if q.invoice_payload in TIER_BY_PAYLOAD:
        await q.answer(ok=True)
    else:
        await q.answer(ok=False, error_message="Счёт устарел — откройте /pro заново")


@router.message(F.successful_payment)
async def on_paid(msg: Message, db: Database):
    lang = await _lang(db, msg.from_user.id)
    sp = msg.successful_payment
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
