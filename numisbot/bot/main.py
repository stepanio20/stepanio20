"""Entrypoint: long polling. Reads .env if present, wires DB/config/scheduler."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import load_config
from .db import Database
from .handlers import ROUTERS
from .services.scheduler import SchedulerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _load_dotenv() -> None:
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


async def main() -> None:
    _load_dotenv()
    cfg = load_config()
    Path(cfg.db_path).parent.mkdir(parents=True, exist_ok=True)

    db = Database(cfg.db_path)
    await db.connect()

    bot = Bot(cfg.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    for r in ROUTERS:
        dp.include_router(r)

    scheduler = SchedulerService(bot, db, cfg)
    scheduler.start()
    asyncio.create_task(scheduler.refresh_now())  # warm the cache at startup

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
