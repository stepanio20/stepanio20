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


def _bool(raw: str, default: bool = False) -> bool:
    if raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    gia_api_key: str = os.environ.get("GIA_API_KEY", "")
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    market: str = os.environ.get("MARKET", "dubai")
    database_path: str = os.environ.get("DATABASE_PATH", str(BASE_DIR / "diamond_bot.db"))
    channel_id: str = os.environ.get("TELEGRAM_CHANNEL_ID", "")
    admin_user_ids: set[int] = field(default_factory=lambda: _ids(os.environ.get("ADMIN_USER_IDS", "")))

    # ── Payments: veym gateway (MamoPay-backed, AED). No Telegram Stars. ──
    # veym exposes: GET /v1/payments, GET /v1/payments/:id, /v1/webhooks (auth via `apikey` header).
    # Charges are created on MamoPay; veym relays events to our /mamopay-webhook.
    veym_base_url: str = os.environ.get("VEYM_BASE_URL", "https://veym.up.railway.app/v1").rstrip("/")
    veym_api_key: str = os.environ.get("VEYM_API_KEY", "")
    veym_webhook_secret: str = os.environ.get("VEYM_WEBHOOK_SECRET", "")
    # How a charge is created. Filled from the Dubai Unit Bot's flow: a MamoPay charge/link
    # endpoint that returns a hosted payment URL. Left configurable until confirmed.
    mamo_api_key: str = os.environ.get("MAMO_API_KEY", "")
    mamo_base_url: str = os.environ.get("MAMO_BASE_URL", "https://business.mamopay.com/manage_api/v1").rstrip("/")
    currency: str = os.environ.get("CURRENCY", "AED")

    # Public HTTPS base (Railway domain) — used for webhook + return URLs. e.g. https://xxx.up.railway.app
    public_base_url: str = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    port: int = int(os.environ.get("PORT", "8080") or "8080")

    # Testing switch: reveal counterparty contact without a paid subscription.
    # MUST be false in production — it disables the paywall.
    free_reveal: bool = _bool(os.environ.get("FREE_REVEAL", ""), default=False)

    # Subscription tiers priced by how many stones you can list (LuxeDiam-style),
    # charged via veym/MamoPay in AED. max_stock=None means unlimited. usd ≈ reference.
    tiers: dict = field(default_factory=lambda: {
        "free": {"title": "Free", "aed": 0,   "usd": 0,  "max_stock": 500,  "days": 0},
        "grow": {"title": "Grow", "aed": 99,  "usd": 25, "max_stock": 1000, "days": 30},
        "pro":  {"title": "Pro",  "aed": 199, "usd": 50, "max_stock": None, "days": 30},
    })
    paid_tiers: tuple = ("grow", "pro")

    contact_phone: str = os.environ.get("CONTACT_PHONE", "+971 56 000 0000")
    bot_username: str = os.environ.get("BOT_USERNAME", "DiamondScanBot")
    support_url: str = os.environ.get("SUPPORT_URL", "")   # t.me/<user> or https://… for the Support button

    def stock_limit(self, tier: str) -> Optional[int]:
        return self.tiers.get(tier, self.tiers["free"]).get("max_stock")

    def require_token(self) -> str:
        if not self.bot_token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN is not set. Put it in diamond-bot/.env (gitignored)."
            )
        return self.bot_token


settings = Settings()
