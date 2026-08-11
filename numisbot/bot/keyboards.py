"""Inline keyboards."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .texts import INTERESTS


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
    ]])


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
    b.button(text="💼 Продать" if ru else "💼 Sell", callback_data="m:sell")
    b.button(text="⭐ Pro", callback_data="m:pro")
    b.button(text="ℹ️ Помощь" if ru else "ℹ️ Help", callback_data="m:help")
    b.adjust(2, 2, 2)
    return b.as_markup()


def watchlist_kb(watches, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for w in watches:
        cap = f" <{w['max_price']:.0f}" if w["max_price"] else ""
        b.button(text=f"🗑 {w['query']}{cap}", callback_data=f"unwatch:{w['id']}")
    b.adjust(1)
    return b.as_markup()


def _fit_cb(prefix: str, text: str, limit: int = 64) -> str:
    """Telegram callback_data is capped at 64 bytes; trim at a char boundary."""
    data = prefix + text
    raw = data.encode("utf-8")[:limit]
    return raw.decode("utf-8", errors="ignore")


def lot_kb(lot, lang: str) -> InlineKeyboardMarkup:
    """Buttons under a lot card: open on site + quick-add to radar."""
    ru = lang == "ru"
    rows = []
    if lot["url"]:
        rows.append(InlineKeyboardButton(
            text="Открыть лот ↗" if ru else "Open lot ↗", url=lot["url"]))
    if lot["realized"] is None:
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
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=("🔭 Следить за новыми «%s»" % query[:24]) if ru
            else ("🔭 Watch new “%s”" % query[:24]),
            callback_data=_fit_cb("wq:", query)),
    ]])


def pro_kb(lang: str, pro_stars: int, sniper_stars: int, dealer_stars: int) -> InlineKeyboardMarkup:
    per_month = "/мес" if lang == "ru" else "/mo"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Pro — {pro_stars} Stars{per_month}", callback_data="buy:pro")],
        [InlineKeyboardButton(text=f"🎯 Sniper+ — {sniper_stars} Stars{per_month}", callback_data="buy:sniper")],
        [InlineKeyboardButton(text=f"💼 Dealer — {dealer_stars} Stars{per_month}", callback_data="buy:dealer")],
    ])
