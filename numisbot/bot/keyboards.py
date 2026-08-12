"""Inline keyboards."""
from __future__ import annotations

from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .texts import BTN, INTERESTS


def main_reply_kb(lang: str) -> ReplyKeyboardMarkup:
    """Persistent bottom keyboard — the primary navigation."""
    b = BTN.get(lang, BTN["en"])
    rows = [
        [KeyboardButton(text=b["auctions"]), KeyboardButton(text=b["watchlist"])],
        [KeyboardButton(text=b["find"]), KeyboardButton(text=b["price"])],
        [KeyboardButton(text=b["market"]), KeyboardButton(text=b["publish"])],
        [KeyboardButton(text=b["sell"]), KeyboardButton(text=b["pro"])],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows, resize_keyboard=True, is_persistent=True,
        input_field_placeholder=("напр.: /watch рубль 1912" if lang == "ru"
                                 else "e.g.: /watch rouble 1912"),
    )


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang:de"),
         InlineKeyboardButton(text="🇨🇿 Čeština", callback_data="lang:cs")],
    ])


def interests_kb(lang: str, selected: set[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, labels in INTERESTS.items():
        mark = "✅ " if key in selected else ""
        b.button(text=mark + labels.get(lang, labels["ru"]), callback_data=f"int:{key}")
    b.adjust(2)
    b.row(InlineKeyboardButton(
        text="Готово ➜" if lang == "ru" else "Done ➜", callback_data="int:done"
    ))
    return b.as_markup()


def menu_kb(lang: str) -> InlineKeyboardMarkup:
    ru = lang == "ru"
    b = InlineKeyboardBuilder()
    b.button(text="🏛 Аукционы" if ru else "🏛 Auctions", callback_data="m:auctions")
    b.button(text="🔭 Радар" if ru else "🔭 Radar", callback_data="m:watchlist")
    b.button(text="📉 Цены" if ru else "📉 Prices", callback_data="m:price")
    b.button(text="🛒 Витрина" if ru else "🛒 Showcase", callback_data="m:market")
    b.button(text="📤 Разместить монету" if ru else "📤 List a coin", callback_data="m:publish")
    b.button(text="💼 Продать через Katz" if ru else "💼 Sell via Katz", callback_data="m:sell")
    b.button(text="⭐ Pro", callback_data="m:pro")
    b.button(text="ℹ️ Помощь" if ru else "ℹ️ Help", callback_data="m:help")
    b.adjust(2, 2, 1, 1, 2)
    return b.as_markup()


def watchlist_kb(watches, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for w in watches:
        cap = f" <{w['max_price']:.0f}" if w["max_price"] else ""
        label = w["query"][:30] + ("…" if len(w["query"]) > 30 else "")
        b.button(text=f"🗑 {label}{cap}", callback_data=f"unwatch:{w['id']}")
    b.adjust(1)
    return b.as_markup()


def _fit_cb(prefix: str, text: str, limit: int = 64) -> str:
    """Telegram callback_data is capped at 64 bytes; trim at a char boundary."""
    data = prefix + text
    raw = data.encode("utf-8")[:limit]
    return raw.decode("utf-8", errors="ignore")


def lot_kb(lot, lang: str, in_radar: bool = False) -> InlineKeyboardMarkup:
    """Buttons under a lot card: open on site + quick-add to radar.

    in_radar=True on radar alerts — the lot is already being watched,
    offering the add button there would just burn a slot.
    """
    ru = lang == "ru"
    rows = []
    if lot["url"]:
        rows.append(InlineKeyboardButton(
            text="Открыть лот ↗" if ru else "Open lot ↗", url=lot["url"]))
    if lot["realized"] is None and not in_radar:
        rows.append(InlineKeyboardButton(
            text="➕ В радар" if ru else "➕ Watch",
            callback_data=f"wl:{lot['id']}"))
    return InlineKeyboardMarkup(inline_keyboard=[rows] if rows else [])


def auctions_kb(auctions, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for a in auctions[:8]:
        mark = "🟢" if a["status"] == "live" else "🗓"
        title = a["title"].strip()
        short = title if len(title) <= 40 else title[:38] + "…"
        b.button(text=f"{mark} {short}", url=a["url"])
    b.adjust(1)
    return b.as_markup()


def price_kb(query: str, lang: str) -> InlineKeyboardMarkup:
    ru = lang == "ru"
    q = query[:20] + ("…" if len(query) > 20 else "")
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"🔭 В радар: {q}" if ru else f"🔭 Watch: {q}",
            callback_data=_fit_cb("wq:", query)),
    ]])


def digest_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="🔕 Не присылать дайджесты" if lang == "ru" else "🔕 Mute digests",
        callback_data="digest:off")]])


def cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="✖️ Отмена" if lang == "ru" else "✖️ Cancel",
        callback_data="cancel")]])


def publish_price_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="💬 Открыт к предложениям" if lang == "ru" else "💬 Open to offers",
        callback_data="pub:offers")]])


def publish_cert_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="Без сертификата ➜" if lang == "ru" else "No certificate ➜",
        callback_data="pub:nocert")]])


def listing_kb(listing, lang: str, is_owner: bool = False) -> InlineKeyboardMarkup:
    from .services.certs import lookup_url
    ru = lang == "ru"
    rows: list[list[InlineKeyboardButton]] = []
    contact = (listing["contact"] or "").lstrip("@")
    row1: list[InlineKeyboardButton] = []
    if contact and not contact.isdigit():
        row1.append(InlineKeyboardButton(
            text="✉️ Написать продавцу" if ru else "✉️ Message seller",
            url=f"https://t.me/{contact}"))
    if listing["cert_service"] and listing["cert_number"]:
        row1.append(InlineKeyboardButton(
            text="🛡 Реестр грейдера ↗" if ru else "🛡 Grader registry ↗",
            url=lookup_url(listing["cert_service"], listing["cert_number"])))
    if row1:
        rows.append(row1)
    if is_owner:
        rows.append([InlineKeyboardButton(
            text="✅ Продано" if ru else "✅ Sold",
            callback_data=f"mksold:{listing['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def market_more_kb(before_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="⬇️ Показать ещё" if lang == "ru" else "⬇️ Show more",
        callback_data=f"mk:{before_id}")]])


def admin_verify_kb(listing) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm:ok:{listing['id']}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm:no:{listing['id']}"),
    ]])


def pro_kb(lang: str, pro_stars: int, sniper_stars: int, dealer_stars: int) -> InlineKeyboardMarkup:
    per_month = "/мес" if lang == "ru" else "/mo"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Pro — {pro_stars} Stars{per_month}", callback_data="buy:pro")],
        [InlineKeyboardButton(text=f"🎯 Sniper+ — {sniper_stars} Stars{per_month}", callback_data="buy:sniper")],
        [InlineKeyboardButton(text=f"💼 Dealer — {dealer_stars} Stars{per_month}", callback_data="buy:dealer")],
    ])
