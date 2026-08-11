"""Configuration loaded from environment (.env is loaded by main)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "")
    return {int(x) for x in raw.replace(";", ",").split(",") if x.strip().isdigit()}


@dataclass(frozen=True)
class Config:
    bot_token: str = field(default_factory=lambda: os.environ["BOT_TOKEN"])
    admin_ids: set[int] = field(default_factory=_admin_ids)
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "data/numisbot.sqlite3"))
    katz_base_url: str = field(default_factory=lambda: os.getenv("KATZ_BASE_URL", "https://katzauction.com"))
    parse_interval_minutes: int = field(default_factory=lambda: int(os.getenv("PARSE_INTERVAL_MINUTES", "30")))
    http_timeout: float = field(default_factory=lambda: float(os.getenv("HTTP_TIMEOUT_SECONDS", "25")))
    price_pro_stars: int = field(default_factory=lambda: int(os.getenv("PRICE_PRO_STARS", "299")))
    price_sniper_stars: int = field(default_factory=lambda: int(os.getenv("PRICE_SNIPER_STARS", "749")))
    price_dealer_stars: int = field(default_factory=lambda: int(os.getenv("PRICE_DEALER_STARS", "1900")))
    # Watch slots per tier
    free_watch_slots: int = 3
    pro_watch_slots: int = 25
    sniper_watch_slots: int = 999

    def watch_slots(self, tier: str) -> int:
        return {
            "free": self.free_watch_slots,
            "pro": self.pro_watch_slots,
        }.get(tier, self.sniper_watch_slots)


def load_config() -> Config:
    return Config()
