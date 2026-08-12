"""/portfolio — collection tracker revalued against fresh Katz results."""
from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..config import Config
from ..db import Database
from ..keyboards import cancel_kb
from ..services.valuation import valuate
from ..texts import _money, esc, t

router = Router()

PF_SLOTS = {"free": 5, "pro": 100, "sniper": 500, "dealer": 500}
_BUY_RE = re.compile(r"\b(?:за|for)\s+(\d[\d\s]*(?:[.,]\d+)?)\s*€?\s*$", re.IGNORECASE)


class PortfolioForm(StatesGroup):
    waiting_item = State()


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


def _pf_kb(items, lang: str) -> InlineKeyboardMarkup:
    ru = lang == "ru"
    rows = [[InlineKeyboardButton(
        text="➕ Добавить монету" if ru else "➕ Add a coin",
        callback_data="pf:add")]]
    for it in items[:20]:
        label = it["title"][:28] + ("…" if len(it["title"]) > 28 else "")
        rows.append([InlineKeyboardButton(text=f"🗑 {label}",
                                          callback_data=f"pf:del:{it['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("portfolio"))
async def cmd_portfolio(msg: Message, db: Database):
    await _show_portfolio(msg, msg.from_user.id, db)


async def _show_portfolio(msg: Message, user_id: int, db: Database):
    lang = await _lang(db, user_id)
    items = await db.portfolio_list(user_id)
    await db.track(user_id, "portfolio_view")
    if not items:
        await msg.answer(t("pf_empty", lang), reply_markup=_pf_kb([], lang))
        return

    lines = [t("pf_header", lang).format(n=len(items))]
    total_med = total_lo = total_hi = 0.0
    total_buy = 0.0
    have_buy = False
    for it in items:
        v = await valuate(db, it["title"])
        title = esc(it["title"][:48])
        if v:
            total_med += v.median
            total_lo += v.p25
            total_hi += v.p75
            lines.append(f"▫️ {title} — <b>{_money(v.median, 'EUR')}</b> "
                         f"({_money(v.p25, 'EUR')}–{_money(v.p75, 'EUR')}, {v.n} прод.)")
        else:
            lines.append(f"▫️ {title} — <i>{'аналогов нет' if lang == 'ru' else 'no comps'}</i>")
        if it["buy_price"]:
            have_buy = True
            total_buy += it["buy_price"]

    vs = t("pf_vs_buy", lang).format(buy=_money(total_buy, "EUR")) if have_buy else ""
    lines.append(t("pf_total", lang).format(
        lo=_money(total_lo, "EUR"), hi=_money(total_hi, "EUR"),
        med=_money(total_med, "EUR"), vs=vs))
    # Telegram caps messages at 4096 chars — chunk large portfolios
    chunks: list[str] = []
    cur = ""
    for line in lines:
        if len(cur) + len(line) + 1 > 3500:
            chunks.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    chunks.append(cur)
    for i, chunk in enumerate(chunks):
        kb = _pf_kb(items, lang) if i == len(chunks) - 1 else None
        await msg.answer(chunk, reply_markup=kb, disable_web_page_preview=True)


@router.callback_query(F.data == "pf:add")
async def cb_pf_add(cb: CallbackQuery, db: Database, cfg: Config, state: FSMContext):
    lang = await _lang(db, cb.from_user.id)
    tier = await db.effective_tier(cb.from_user.id)
    limit = PF_SLOTS.get(tier, 5)
    if len(await db.portfolio_list(cb.from_user.id)) >= limit:
        await cb.message.answer(t("pf_limit", lang).format(limit=limit))
        await cb.answer("🚦")
        return
    await state.set_state(PortfolioForm.waiting_item)
    await cb.message.answer(t("pf_add_ask", lang), reply_markup=cancel_kb(lang))
    await cb.answer()


@router.message(PortfolioForm.waiting_item, F.text & ~F.text.startswith("/"))
async def pf_add_item(msg: Message, db: Database, state: FSMContext):
    lang = await _lang(db, msg.from_user.id)
    text = (msg.text or "").strip()
    if len(text) < 5:
        await msg.answer(t("pf_add_ask", lang), reply_markup=cancel_kb(lang))
        return
    await state.clear()
    buy = None
    if m := _BUY_RE.search(text):
        buy = float(m.group(1).replace(" ", "").replace(",", "."))
        text = text[: m.start()].strip()
    await db.portfolio_add(msg.from_user.id, text[:120], buy)
    await db.track(msg.from_user.id, "portfolio_add")
    buy_str = f" · {_money(buy, 'EUR')}" if buy else ""
    await msg.answer(t("pf_added", lang).format(title=esc(text[:60]), buy=buy_str))
    await _show_portfolio(msg, msg.from_user.id, db)


@router.callback_query(F.data.startswith("pf:del:"))
async def cb_pf_del(cb: CallbackQuery, db: Database):
    await db.portfolio_delete(cb.from_user.id, int(cb.data.split(":")[2]))
    await cb.answer("🗑")
    await _show_portfolio(cb.message, cb.from_user.id, db)
