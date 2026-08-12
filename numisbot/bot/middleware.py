"""Inbound-update guards: private-chats-only and a per-user rate limit.

Simple token-bucket: N updates per rolling minute per user; excess is
silently dropped (one polite warning per window). Keeps flood off the
Katz API and the bot inside Telegram's own limits.
"""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

RATE_LIMIT = 25          # updates / minute / user
_WINDOW = 60.0


class GuardMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._buckets: dict[int, list[float]] = {}
        self._warned: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            # money must never be rate-limited: a dropped successful_payment
            # would mean paid Stars with no tier granted
            if event.successful_payment is not None:
                return await handler(event, data)
            if event.chat.type != "private":
                return None  # the bot is a personal radar, not a group bot
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        if user is None:
            return await handler(event, data)

        now = time.monotonic()
        bucket = [t for t in self._buckets.get(user.id, []) if now - t < _WINDOW]
        if len(bucket) >= RATE_LIMIT:
            self._buckets[user.id] = bucket
            if now - self._warned.get(user.id, 0) > _WINDOW:
                self._warned[user.id] = now
                try:
                    if isinstance(event, Message):
                        await event.answer("⏳ Слишком часто — подождите минуту. / Too fast — give it a minute.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⏳")
                except Exception:
                    pass
            return None
        bucket.append(now)
        self._buckets[user.id] = bucket
        if len(self._buckets) > 10000:  # bounded memory
            self._buckets = {u: b for u, b in self._buckets.items()
                             if b and now - b[-1] < _WINDOW}
        return await handler(event, data)
