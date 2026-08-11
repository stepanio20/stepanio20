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
    await msg.answer(
        "📊 <b>Статистика</b>\n"
        f"Пользователи: {s['users']} (платящих: {s['paying']})\n"
        f"Отслеживаний: {s['watches']}\n"
        f"Лотов в базе: {s['lots']}\n"
        f"Заявок на продажу: {s['leads']}"
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
