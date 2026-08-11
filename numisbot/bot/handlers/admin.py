"""Admin: /stats, /broadcast <text>, /refresh (force parse)."""
from __future__ import annotations

import asyncio

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from ..config import Config
from ..db import Database

router = Router()


def _is_admin(cfg: Config, user_id: int) -> bool:
    return user_id in cfg.admin_ids


@router.message(Command("stats"))
async def cmd_stats(msg: Message, db: Database, cfg: Config):
    if not _is_admin(cfg, msg.from_user.id):
        return
    s = await db.stats()
    m = await db.metrics()
    await msg.answer(
        "📊 <b>Метрики продукта</b>\n\n"
        f"👥 Пользователи: <b>{s['users']}</b> · платящих: <b>{s['paying']}</b> "
        f"(конверсия {m['conversion_pct']}%)\n"
        f"📈 DAU {m['dau']} · WAU {m['wau']} · MAU {m['mau']}\n"
        f"🎯 Активация (≥1 радар): <b>{m['activation_pct']}%</b>\n"
        f"🔭 Отслеживаний: {s['watches']} · поисков за 7д: {m['searches_7d']}\n"
        f"🛒 Листингов в витрине: {m['listings_active']}\n"
        f"💼 Заявок на консигнацию: {s['leads']}\n"
        f"🗃 Лотов в базе: {s['lots']}"
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(msg: Message, command: CommandObject, db: Database, cfg: Config):
    if not _is_admin(cfg, msg.from_user.id):
        return
    text = (command.args or "").strip()
    if not text:
        await msg.answer("Использование: /broadcast <текст>")
        return
    sent = failed = 0
    for uid in await db.all_user_ids():
        try:
            await msg.bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # ~20 msg/sec, inside Telegram limits
    await msg.answer(f"Разослано: {sent}, ошибок: {failed}")


@router.message(Command("refresh"))
async def cmd_refresh(msg: Message, cfg: Config, scheduler_service=None):
    if not _is_admin(cfg, msg.from_user.id):
        return
    if scheduler_service is None:
        await msg.answer("Парсер не подключён.")
        return
    await msg.answer("⏳ Запускаю обновление…")
    stats = await scheduler_service.refresh_now()
    await msg.answer(f"✅ Обновлено: {stats}")
