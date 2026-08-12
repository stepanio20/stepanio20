"""Entrypoint: long polling. Reads .env if present, wires DB/config/scheduler."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from .config import load_config
from .db import Database
from .handlers import ROUTERS
from .services.scheduler import SchedulerService

COMMANDS = {
    "ru": [
        ("auctions", "🏛 Аукционы: текущие и ближайшие"),
        ("find", "🔎 Поиск лотов на торгах"),
        ("watch", "🔭 Добавить в радар"),
        ("watchlist", "📋 Мой радар"),
        ("price", "📉 Цены + график проходов"),
        ("market", "🛒 Витрина монет участников"),
        ("publish", "📤 Разместить свою монету"),
        ("sell", "💼 Сдать на аукцион Katz"),
        ("estimate", "🏷 Оценка монеты по базе проходов"),
        ("portfolio", "🧺 Портфель коллекции"),
        ("pro", "⭐ Тарифы Pro / Sniper+ / Dealer"),
        ("invite", "🎁 Месяц Pro за друга"),
        ("digest", "📬 Вкл/выкл дайджесты"),
        ("menu", "🪙 Меню"),
        ("cancel", "✖️ Отменить текущее действие"),
        ("help", "ℹ️ Помощь"),
    ],
    None: [
        ("auctions", "🏛 Live & upcoming auctions"),
        ("find", "🔎 Search lots on sale"),
        ("watch", "🔭 Add to radar"),
        ("watchlist", "📋 My radar"),
        ("price", "📉 Prices + results chart"),
        ("market", "🛒 Members coin showcase"),
        ("publish", "📤 List your coin"),
        ("sell", "💼 Consign to Katz"),
        ("estimate", "🏷 Coin valuation from archive"),
        ("portfolio", "🧺 Collection portfolio"),
        ("pro", "⭐ Plans"),
        ("invite", "🎁 A month of Pro per friend"),
        ("digest", "📬 Toggle digests"),
        ("menu", "🪙 Menu"),
        ("cancel", "✖️ Cancel current action"),
        ("help", "ℹ️ Help"),
    ],
}


async def register_commands(bot: Bot) -> None:
    for lang_code, cmds in COMMANDS.items():
        try:
            await bot.set_my_commands(
                [BotCommand(command=c, description=d) for c, d in cmds],
                language_code=lang_code,
            )
        except Exception:
            pass  # cosmetic — never block startup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _load_dotenv() -> None:
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


async def main() -> None:
    _load_dotenv()
    cfg = load_config()
    Path(cfg.db_path).parent.mkdir(parents=True, exist_ok=True)

    db = Database(cfg.db_path, archive_path=cfg.archive_db_path)
    await db.connect()

    bot = Bot(cfg.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    for r in ROUTERS:
        dp.include_router(r)

    scheduler = SchedulerService(bot, db, cfg)
    scheduler.start()
    asyncio.create_task(scheduler.refresh_now())  # warm the cache at startup
    asyncio.create_task(register_commands(bot))

    # dependency injection for handlers
    dp["db"] = db
    dp["cfg"] = cfg
    dp["scheduler_service"] = scheduler

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await scheduler.shutdown()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
