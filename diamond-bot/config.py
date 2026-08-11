"""Central configuration, loaded from environment (.env is gitignored)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    """Minimal .env loader (no external dependency) so `python bot.py` just works."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def _ids(raw: str) -> set[int]:
    out: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.add(int(part))
    return out


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    provider_token: str = os.environ.get("TELEGRAM_PROVIDER_TOKEN", "")
    gia_api_key: str = os.environ.get("GIA_API_KEY", "")
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    market: str = os.environ.get("MARKET", "dubai")
    database_path: str = os.environ.get("DATABASE_PATH", str(BASE_DIR / "diamond_bot.db"))
    channel_id: str = os.environ.get("TELEGRAM_CHANNEL_ID", "")
    admin_user_ids: set[int] = field(default_factory=lambda: _ids(os.environ.get("ADMIN_USER_IDS", "")))

    # Subscription tiers, in Telegram Stars (XTR). ~ USD shown for reference in copy.
    # Stars price is what Telegram charges; adjust to taste. 1 Star ≈ $0.013–0.02 net.
    tiers: dict = field(default_factory=lambda: {
        "buyer":  {"title": "Buyer",  "stars": 1900, "usd": 39,  "days": 30},
        "broker": {"title": "Broker", "stars": 7500, "usd": 149, "days": 30},
    })

    contact_phone: str = os.environ.get("CONTACT_PHONE", "+971 56 000 0000")
    bot_username: str = os.environ.get("BOT_USERNAME", "DiamondScanBot")

    def require_token(self) -> str:
        if not self.bot_token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN is not set. Put it in diamond-bot/.env (gitignored)."
            )
        return self.bot_token


settings = Settings()
