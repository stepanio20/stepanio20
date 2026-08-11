"""
Subscriptions via Telegram Stars (XTR) — native digital-goods payments, no external
provider or merchant account needed. A fiat provider token (from @BotFather) can be
plugged in later for card payments; the handler shape is identical.

Flow:
  1. user taps a plan   -> send_invoice() with an XTR price
  2. Telegram asks the user to pay in Stars
  3. pre_checkout_query -> we answer ok=True
  4. successful_payment -> we record the subscription in the DB

Refunds: Stars payments are refundable via refundStarPayment(user_id, charge_id).
"""
from __future__ import annotations

from aiogram import Bot
from aiogram.types import LabeledPrice

from config import settings
import db


def plan_label(tier: str) -> str:
    t = settings.tiers[tier]
    return f"{t['title']} — {t['stars']}⭐ / {t['days']} days  (≈${t['usd']}/mo)"


async def send_invoice(bot: Bot, chat_id: int, tier: str) -> None:
    t = settings.tiers[tier]
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"DiamondScan {t['title']} — {t['days']} days",
        description=(
            "Real-time matching of Dubai diamond 'have/looking-for' traffic, "
            "instant alerts when your stone or your buyer appears, and verified deal cards."
        ),
        payload=f"sub:{tier}",
        provider_token="",              # empty => Telegram Stars (XTR)
        currency="XTR",
        prices=[LabeledPrice(label=t["title"], amount=t["stars"])],
        start_parameter=f"subscribe-{tier}",
    )


async def on_successful_payment(user_id: int, payload: str, charge_id: str, amount: int) -> str:
    """Record the subscription. Returns the tier granted."""
    tier = payload.split(":", 1)[1] if payload.startswith("sub:") else "buyer"
    t = settings.tiers.get(tier, settings.tiers["buyer"])
    db.add_subscription(user_id, tier=tier, stars=amount, days=t["days"], charge_id=charge_id)
    db.log_event("subscription_paid", user_id, {"tier": tier, "stars": amount, "charge_id": charge_id})
    return tier
