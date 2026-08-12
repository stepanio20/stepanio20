"""/publish — list your own coin (with industry-standard cert verification),
/market — browse the showcase. Cert chain: see services/certs.py."""
from __future__ import annotations

import asyncio
import json
import re
import time
from collections import defaultdict

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..config import Config
from ..db import Database
from ..keyboards import (admin_verify_kb, cancel_kb, listing_kb, market_more_kb,
                         publish_cert_kb, publish_price_kb)
from ..services import certs
from ..texts import _money, esc, listing_card, t

router = Router()

LISTING_SLOTS = {"free": 1, "pro": 3, "sniper": 5, "dealer": 20}

# album photos arrive as concurrent updates; serialize per-user state writes
_photo_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


class PublishForm(StatesGroup):
    photos = State()
    description = State()
    price = State()
    cert = State()


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


# ---------------------------------------------------------------- publish
async def _publish_gate(user, db: Database, lang: str) -> str | None:
    """Returns a rejection message key, or None when publishing is allowed."""
    if not user.username:
        return "publish_need_username"  # buyers must be able to reach the seller
    if await db.rejected_count(user.id) >= 3:
        return "publish_banned"
    import time as _time
    if _time.time() - await db.last_listing_ts(user.id) < 600:
        return "publish_cooldown"
    tier = await db.effective_tier(user.id)
    if await db.active_listings_of(user.id) >= LISTING_SLOTS.get(tier, 1):
        return "publish_limit"
    return None


@router.message(Command("publish"))
async def cmd_publish(msg: Message, db: Database, state: FSMContext):
    lang = await _lang(db, msg.from_user.id)
    gate = await _publish_gate(msg.from_user, db, lang)
    if gate:
        limit = LISTING_SLOTS.get(await db.effective_tier(msg.from_user.id), 1)
        await msg.answer(t(gate, lang).format(limit=limit))
        await db.track(msg.from_user.id, "publish_gate_" + gate)
        return
    await state.set_state(PublishForm.photos)
    await state.update_data(photos=[])
    await msg.answer(t("publish_start", lang), reply_markup=cancel_kb(lang))
    await db.track(msg.from_user.id, "publish_start")


@router.callback_query(F.data == "m:publish")
async def cb_publish(cb: CallbackQuery, db: Database, state: FSMContext):
    lang = await _lang(db, cb.from_user.id)
    gate = await _publish_gate(cb.from_user, db, lang)
    if gate:
        limit = LISTING_SLOTS.get(await db.effective_tier(cb.from_user.id), 1)
        await cb.message.answer(t(gate, lang).format(limit=limit))
        await cb.answer()
        return
    await state.set_state(PublishForm.photos)
    await state.update_data(photos=[])
    await cb.message.answer(t("publish_start", lang), reply_markup=cancel_kb(lang))
    await db.track(cb.from_user.id, "publish_start")
    await cb.answer()


@router.callback_query(F.data == "m:market")
async def cb_market(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    rows = await db.browse_listings(limit=3)
    await db.track(cb.from_user.id, "market_view")
    if not rows:
        await cb.message.answer(t("market_empty", lang))
        await cb.answer()
        return
    await cb.message.answer(t("market_header", lang))
    for r in rows:
        await _send_listing_card(cb.message, r, lang, viewer_id=cb.from_user.id)
    if len(rows) == 3:
        await cb.message.answer(t("market_more", lang),
                                reply_markup=market_more_kb(rows[-1]["id"], lang))
    await cb.answer()


@router.message(PublishForm.photos, F.photo)
async def pub_photo(msg: Message, db: Database, state: FSMContext):
    lang = await _lang(db, msg.from_user.id)
    async with _photo_locks[msg.from_user.id]:
        data = await state.get_data()
        photos: list[str] = data.get("photos", [])
        photos.append(msg.photo[-1].file_id)  # best resolution
        await state.update_data(photos=photos[:5])
        first = len(photos) == 1
    if first:
        await msg.answer(t("publish_photo_ok", lang))
        await state.set_state(PublishForm.description)


@router.message(PublishForm.photos, F.text)
async def pub_photo_missing(msg: Message, db: Database):
    lang = await _lang(db, msg.from_user.id)
    await msg.answer(t("publish_need_photo", lang), reply_markup=cancel_kb(lang))


@router.message(PublishForm.description, F.photo)
async def pub_more_photos(msg: Message, db: Database, state: FSMContext):
    lang = await _lang(db, msg.from_user.id)
    async with _photo_locks[msg.from_user.id]:
        data = await state.get_data()
        photos: list[str] = data.get("photos", [])
        photos.append(msg.photo[-1].file_id)
        await state.update_data(photos=photos[:5])
        n = min(len(photos), 5)
    await msg.answer(t("photo_added", lang).format(n=n))


@router.message(PublishForm.description, F.text)
async def pub_description(msg: Message, db: Database, state: FSMContext):
    lang = await _lang(db, msg.from_user.id)
    text = (msg.text or "").strip()
    if len(text) < 10:
        await msg.answer(t("publish_desc_short", lang))
        return
    await state.update_data(description=text[:1500])
    await state.set_state(PublishForm.price)
    await msg.answer(t("publish_price_ask", lang), reply_markup=publish_price_kb(lang))


async def _to_cert_step(msg: Message, lang: str, state: FSMContext):
    await state.set_state(PublishForm.cert)
    await msg.answer(t("publish_cert_ask", lang), reply_markup=publish_cert_kb(lang))


@router.message(PublishForm.price, F.text)
async def pub_price(msg: Message, db: Database, state: FSMContext):
    lang = await _lang(db, msg.from_user.id)
    m = re.search(r"(\d[\d\s]*(?:[.,]\d+)?)", msg.text or "")
    if not m:
        await msg.answer(t("publish_price_bad", lang), reply_markup=publish_price_kb(lang))
        return
    price = float(m.group(1).replace(" ", "").replace(",", "."))
    await state.update_data(price=price)
    await _to_cert_step(msg, lang, state)


@router.callback_query(PublishForm.price, F.data == "pub:offers")
async def pub_price_offers(cb: CallbackQuery, db: Database, state: FSMContext):
    lang = await _lang(db, cb.from_user.id)
    await state.update_data(price=None)
    await _to_cert_step(cb.message, lang, state)
    await cb.answer()


@router.callback_query(PublishForm.cert, F.data == "pub:nocert")
async def pub_no_cert(cb: CallbackQuery, db: Database, state: FSMContext, cfg: Config):
    await _finalize(cb.message, cb.from_user, db, state, cfg, service="", number="")
    await cb.answer()


@router.message(PublishForm.cert, F.text)
async def pub_cert(msg: Message, db: Database, state: FSMContext, cfg: Config):
    lang = await _lang(db, msg.from_user.id)
    parsed = certs.parse_cert_input(msg.text or "")
    if not parsed:
        await msg.answer(t("publish_cert_bad", lang), reply_markup=publish_cert_kb(lang))
        return
    service, number = parsed
    if await db.cert_in_use(service, number):
        await msg.answer(t("publish_cert_dup", lang))
        return
    await _finalize(msg, msg.from_user, db, state, cfg, service=service, number=number)


async def _finalize(msg: Message, user, db: Database, state: FSMContext,
                    cfg: Config, service: str, number: str):
    lang = await _lang(db, user.id)
    data = await state.get_data()
    await state.clear()

    cert_status, cert_note = "none", ""
    if service:
        cert_status, cert_note = await certs.verify(service, number)

    description = data.get("description", "")
    title = " ".join(description.split())[:70]
    contact = f"@{user.username}" if user.username else str(user.id)
    listing_id = await db.add_listing({
        "user_id": user.id, "contact": contact, "title": title,
        "description": description, "price": data.get("price"),
        "photos": json.dumps(data.get("photos", [])),
        "cert_service": service, "cert_number": number,
        "cert_status": cert_status, "cert_note": cert_note,
        "created": int(time.time()),
    })
    await db.note_publication(user.id)  # cooldown counter, survives /forgetme
    await db.track(user.id, "publish_done")

    listing = await db.get_listing(listing_id)
    await msg.answer(t("publish_done", lang).format(id=listing_id))
    await _send_listing_card(msg, listing, lang, viewer_id=user.id)

    # moderation card for admins — compact by construction, never sliced mid-tag
    price_str = _money(listing["price"], "EUR") if listing["price"] else "offers"
    cert_str = (f"{listing['cert_service']} {listing['cert_number']} "
                f"[{listing['cert_status']}]" if listing["cert_service"] else "raw")
    admin_caption = (
        f"🆕 <b>Листинг #{listing_id} на модерацию</b>\n"
        f"{esc(title)}\n"
        f"💶 {esc(price_str)} · 🛡 {esc(cert_str)}\n"
        f"От: {esc(contact)}"
    )
    for admin_id in cfg.admin_ids:
        try:
            photos = json.loads(listing["photos"] or "[]")
            kb = admin_verify_kb(listing)
            if photos:
                await msg.bot.send_photo(admin_id, photos[0], caption=admin_caption,
                                         reply_markup=kb)
            else:
                await msg.bot.send_message(admin_id, admin_caption, reply_markup=kb)
        except Exception:
            pass


# ---------------------------------------------------------------- market
async def _send_listing_card(msg: Message, listing, lang: str,
                             viewer_id: int | None = None) -> None:
    photos = json.loads(listing["photos"] or "[]")
    caption = listing_card(listing, lang)
    if len(caption) > 1024:  # never slice HTML mid-tag: drop the quote block
        caption = listing_card(listing, lang, with_description=False)
    kb = listing_kb(listing, lang, is_owner=(viewer_id == listing["user_id"]))
    if photos:
        try:
            await msg.answer_photo(photos[0], caption=caption, reply_markup=kb)
            return
        except Exception:
            pass
    await msg.answer(caption, reply_markup=kb, disable_web_page_preview=True)


@router.message(Command("market"))
async def cmd_market(msg: Message, db: Database):
    lang = await _lang(db, msg.from_user.id)
    rows = await db.browse_listings(limit=3)
    await db.track(msg.from_user.id, "market_view")
    if not rows:
        await msg.answer(t("market_empty", lang))
        return
    await msg.answer(t("market_header", lang))
    for r in rows:
        await _send_listing_card(msg, r, lang, viewer_id=msg.from_user.id)
    if len(rows) == 3:
        await msg.answer(t("market_more", lang),
                         reply_markup=market_more_kb(rows[-1]["id"], lang))


def _cb_int(data: str, idx: int) -> int | None:
    try:
        return int(data.split(":")[idx])
    except (ValueError, IndexError):
        return None


@router.callback_query(F.data.startswith("mk:"))
async def cb_market_more(cb: CallbackQuery, db: Database):
    lang = await _lang(db, cb.from_user.id)
    before_id = _cb_int(cb.data, 1)
    if before_id is None:
        await cb.answer()
        return
    rows = await db.browse_listings(before_id=before_id, limit=3)
    if not rows:
        await cb.answer("∅")
        return
    for r in rows:
        await _send_listing_card(cb.message, r, lang, viewer_id=cb.from_user.id)
    if len(rows) == 3:
        await cb.message.answer(t("market_more", lang),
                                reply_markup=market_more_kb(rows[-1]["id"], lang))
    await cb.answer()


@router.callback_query(F.data.startswith("mksold:"))
async def cb_mark_sold(cb: CallbackQuery, db: Database):
    listing_id = _cb_int(cb.data, 1)
    if listing_id is None:
        await cb.answer()
        return
    await db.set_listing_status(listing_id, cb.from_user.id, "sold")
    await cb.answer("✅")


# ------------------------------------------------------------- moderation
@router.callback_query(F.data.startswith("adm:"))
async def cb_admin_verify(cb: CallbackQuery, db: Database, cfg: Config):
    if cb.from_user.id not in cfg.admin_ids:
        await cb.answer()
        return
    parts = cb.data.split(":")
    verdict = parts[1] if len(parts) > 2 else ""
    listing_id = _cb_int(cb.data, 2)
    if listing_id is None:
        await cb.answer()
        return
    listing = await db.get_listing(listing_id)
    if not listing:
        await cb.answer("∅")
        return
    owner_lang = await _lang(db, listing["user_id"])
    if verdict == "ok":
        if listing["cert_service"] and listing["cert_status"] in ("linked", "pending"):
            await db.set_cert_status(listing_id, "verified",
                                     listing["cert_note"] or "confirmed by moderator")
        elif listing["cert_status"] == "rejected":  # admin changed their mind
            await db.set_cert_status(
                listing_id, "linked" if listing["cert_service"] else "none", "")
        await db.set_listing_status(listing_id, None, "active")
        await cb.answer("✅ approved")
        note = t("publish_approved", owner_lang).format(id=listing_id)
    else:
        already = listing["cert_status"] == "rejected"
        await db.set_cert_status(listing_id, "rejected", "rejected by moderator")
        await db.set_listing_status(listing_id, None, "hidden")
        if not already:  # double-tap on ❌ must not double-count the strike
            await db.note_rejection(listing["user_id"])
        await cb.answer("❌ rejected")
        note = ("❌ Листинг #%d отклонён модерацией" % listing_id
                if owner_lang == "ru" else "❌ Listing #%d was rejected" % listing_id)
    try:
        await cb.bot.send_message(listing["user_id"], note)
    except Exception:
        pass
