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


def pro_kb(lang: str, pro_stars: int, sniper_stars: int, dealer_stars: int) -> InlineKeyboardMarkup:
    per_month = "/мес" if lang == "ru" else "/mo"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Pro — {pro_stars} Stars{per_month}", callback_data="buy:pro")],
        [InlineKeyboardButton(text=f"🎯 Sniper+ — {sniper_stars} Stars{per_month}", callback_data="buy:sniper")],
        [InlineKeyboardButton(text=f"💼 Dealer — {dealer_stars} Stars{per_month}", callback_data="buy:dealer")],
    ])
