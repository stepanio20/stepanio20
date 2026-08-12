"""/estimate — coin valuation from realized Katz prices, with monthly quotas."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..config import Config
from ..db import Database
from ..keyboards import cancel_kb
from ..services.valuation import valuate
from ..texts import _money, esc, realized_line, t

router = Router()

QUOTAS = {"free": 1, "pro": 5, "sniper": 15, "dealer": 30}


class EstimateForm(StatesGroup):
    waiting_description = State()


async def _lang(db: Database, user_id: int) -> str:
    row = await db.get_user(user_id)
    return row["lang"] if row else "ru"


@router.message(Command("estimate"))
async def cmd_estimate(msg: Message, db: Database, state: FSMContext):
    lang = await _lang(db, msg.from_user.id)
    tier = await db.effective_tier(msg.from_user.id)
    quota = QUOTAS.get(tier, 1)
    used = await db.month_usage(msg.from_user.id, "estimate_used")
    if used >= quota:
        await msg.answer(t("estimate_quota", lang).format(used=used, quota=quota))
        return
    await state.set_state(EstimateForm.waiting_description)
    await msg.answer(t("estimate_start", lang), reply_markup=cancel_kb(lang))


@router.message(EstimateForm.waiting_description,
                (F.text & ~F.text.startswith("/")) | F.photo)
async def estimate_run(msg: Message, db: Database, state: FSMContext, cfg: Config):
    lang = await _lang(db, msg.from_user.id)
    text = (msg.text or msg.caption or "").strip()
    if len(text) < 5:
        await msg.answer(t("estimate_start", lang), reply_markup=cancel_kb(lang))
        return
    await state.clear()

    v = await valuate(db, text)
    if v is None:
        await msg.answer(t("estimate_none", lang))
        return

    await db.track(msg.from_user.id, "estimate_used")
    comps = "\n".join(realized_line(r, lang) for r in v.comparables)
    await msg.answer(t("estimate_result", lang).format(
        n=v.n,
        p25=_money(v.p25, "EUR"), p75=_money(v.p75, "EUR"),
        med=_money(v.median, "EUR"),
        lo=_money(v.lo, "EUR"), hi=_money(v.hi, "EUR"),
        words=esc(" ".join(v.used_words)),
        comps=comps,
    ), disable_web_page_preview=True)
