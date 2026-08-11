"""
Subscriptions via the **veym** payment gateway (MamoPay-backed, AED) — the same
gateway the Dubai Unit Bot uses. No Telegram Stars.

Confirmed veym API (auth = `apikey` header):
  GET  /v1/payments            -> list payments (paginated)
  GET  /v1/payments/:id        -> one payment; .status in {success, ...}
  GET  /v1/webhooks            -> registered webhooks {url, authorization}
veym relays MamoPay events to our webhook (path `/mamopay-webhook`) with the
`authorization` header set to VEYM_WEBHOOK_SECRET.

Charge creation happens on MamoPay (hosted checkout) and returns a payment URL.
`create_payment()` posts to MAMO_BASE_URL and is activated once MAMO_API_KEY is
set; until then the subscribe flow degrades gracefully (and FREE_REVEAL lets you
test the full loop without paying).

Flow:
  1. user taps a plan -> create_payment() -> hosted MamoPay URL (button)
  2. user pays -> veym -> POST /mamopay-webhook (verified by secret)
  3. webhook -> activate(): record the subscription, keyed by tg_id in metadata
"""
from __future__ import annotations

import hmac
import json
import logging
from typing import Any, Optional

from config import settings
import db

log = logging.getLogger("diamondscan.payments")

try:  # aiohttp ships with aiogram
    import aiohttp
except Exception:  # pragma: no cover
    aiohttp = None  # type: ignore


# ─────────────────────────────── copy ────────────────────────────────────────

def _cap(tier: str) -> str:
    m = settings.tiers[tier].get("max_stock")
    return "unlimited stock" if m is None else f"up to {m:,} stones"


def plan_label(tier: str) -> str:
    t = settings.tiers[tier]
    return f"💳 AED {t['aed']}/mo — {_cap(tier)}"


def tier_amount(tier: str) -> int:
    return int(settings.tiers[tier]["aed"])


# ─────────────────────────── veym read API ───────────────────────────────────

def _veym_headers() -> dict[str, str]:
    return {"apikey": settings.veym_api_key, "Content-Type": "application/json"}


async def get_payment(payment_id: str) -> Optional[dict]:
    """GET /v1/payments/:id — returns the payment object or None."""
    if not (aiohttp and settings.veym_api_key):
        return None
    url = f"{settings.veym_base_url}/payments/{payment_id}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=_veym_headers(), timeout=aiohttp.ClientTimeout(total=20)) as r:
                body = await r.json(content_type=None)
                return body.get("data", body) if isinstance(body, dict) else None
    except Exception as e:  # noqa: BLE001
        log.warning("veym get_payment failed: %s", e)
        return None


async def is_paid(payment_id: str) -> bool:
    p = await get_payment(payment_id)
    return bool(p and str(p.get("status", "")).lower() in {"success", "paid", "succeeded", "captured"})


# ─────────────────────────── charge creation ─────────────────────────────────

async def create_payment(tier: str, tg_id: int) -> Optional[dict]:
    """Create a hosted charge and return {'url':..., 'id':...}, or None if not configured.

    Posts a MamoPay-style charge. `metadata.tg_id`/`metadata.tier` come back on the
    webhook so we can activate the right user. Endpoint/fields are configurable because
    the exact create call is owned by the merchant (MamoPay) account, not veym.
    """
    if not (aiohttp and settings.mamo_api_key):
        return None
    amount = tier_amount(tier)
    ret = settings.public_base_url or ""
    payload = {
        "title": f"DiamondScan {settings.tiers[tier]['title']} — {settings.tiers[tier]['days']} days",
        "amount": amount,
        "currency": settings.currency,
        "return_url": f"{ret}/paid" if ret else "https://t.me/" + settings.bot_username,
        "failure_return_url": f"{ret}/failed" if ret else "https://t.me/" + settings.bot_username,
        "metadata": {"tg_id": str(tg_id), "tier": tier},
    }
    url = f"{settings.mamo_base_url}/links"
    headers = {"Authorization": f"Bearer {settings.mamo_api_key}", "Content-Type": "application/json"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, data=json.dumps(payload),
                              timeout=aiohttp.ClientTimeout(total=25)) as r:
                body = await r.json(content_type=None)
        pay_url = body.get("payment_url") or body.get("url") or body.get("link")
        pid = body.get("id") or body.get("charge_id")
        if not pay_url:
            log.warning("create_payment: no payment_url in response: %s", str(body)[:200])
            return None
        return {"url": pay_url, "id": pid}
    except Exception as e:  # noqa: BLE001
        log.warning("create_payment failed: %s", e)
        return None


# ─────────────────────────── webhook handling ────────────────────────────────

def verify_webhook_auth(auth_header: str) -> bool:
    """veym sends the shared secret in the `authorization` header (plain, not Bearer).
    Constant-time comparison; fails closed when no secret is configured."""
    if not settings.veym_webhook_secret:
        return False
    return hmac.compare_digest(auth_header.strip(), settings.veym_webhook_secret.strip())


def _extract(event: dict) -> tuple[Optional[int], str, str, int, str]:
    """Pull (tg_id, tier, charge_id, amount, status) out of a webhook payload,
    tolerating a few shapes (top-level, `data`, `payment`)."""
    d = event.get("data") or event.get("payment") or event
    meta = d.get("metadata") or event.get("metadata") or {}
    tg_raw = meta.get("tg_id") or meta.get("telegram_id")
    tg_id = int(tg_raw) if tg_raw and str(tg_raw).lstrip("-").isdigit() else None
    charge_id = str(d.get("id") or d.get("charge_id") or event.get("id") or "")
    try:
        amount = int(float(d.get("amount_total") or d.get("amount") or 0))
    except (TypeError, ValueError):
        amount = 0
    tier = meta.get("tier")
    if tier not in settings.tiers:
        # infer the tier from the paid amount (AED) when metadata is missing/garbled
        tier = next((k for k in settings.paid_tiers if settings.tiers[k]["aed"] == amount), None)
    status = str(d.get("status") or event.get("status") or "").lower()
    return tg_id, tier, charge_id, amount, status


def activate(tg_id: int, tier: str, charge_id: str, amount: int) -> str:
    """Record a paid subscription (idempotent by charge_id). Returns the tier granted."""
    if charge_id and db.subscription_by_charge(charge_id):
        log.info("charge %s already processed — skipping duplicate activation", charge_id)
        return tier
    t = settings.tiers.get(tier) or settings.tiers["free"]
    db.add_subscription(tg_id, tier=tier, stars=amount, days=t["days"], charge_id=charge_id)
    db.log_event("subscription_paid", tg_id, {"tier": tier, "amount": amount,
                                              "charge_id": charge_id, "gateway": "veym"})
    return tier


def handle_webhook_event(event: dict) -> Optional[tuple[int, str]]:
    """Process one webhook event. Returns (tg_id, tier) if a subscription was activated."""
    tg_id, tier, charge_id, amount, status = _extract(event)
    if status not in {"success", "paid", "succeeded", "captured"}:
        return None
    if tg_id is None:
        log.warning("webhook success but no tg_id in metadata: %s", str(event)[:200])
        return None
    if tier not in settings.paid_tiers:
        log.warning("webhook success but unknown tier (amount=%s) — not granting: %s", amount, str(event)[:200])
        return None
    activate(tg_id, tier, charge_id, amount)
    return tg_id, tier
