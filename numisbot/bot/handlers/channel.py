"""Admin: /channelpost — ready-to-forward hot-lots post for the Katz TG channel."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..config import Config
from ..db import Database
from ..texts import esc

router = Router()

TOP_LOTS = 6
HEADER = "🔥 <b>Горячие лоты недели на Katz</b>"
FOOTER = "Следи за своими темами: @KatzCoinsBot"


def _is_admin(cfg: Config, user_id: int) -> bool:
    return user_id in cfg.admin_ids


def _price(lot) -> str:
    """€1 234-style price tag; mirrors texts._money formatting."""
    v = lot["current_bid"] or lot["start_price"] or 0
    cur = lot["currency"] or "EUR"
    sym = "€" if cur == "EUR" else cur + " "
    return f"{sym}{v:,.0f}".replace(",", " ")


@router.message(Command("channelpost"))
async def cmd_channelpost(msg: Message, db: Database, cfg: Config):
    """Send the admin one standalone message they can forward to the channel as-is."""
    if not _is_admin(cfg, msg.from_user.id):
        return
    lots = await db.top_live_lots([], limit=TOP_LOTS)
    if not lots:
        await msg.answer("Пока нет live-лотов со ставками — постить нечего.")
        return
    lines = [HEADER, ""]
    for lot in lots:
        title = esc(str(lot["title"])[:60])
        if lot["url"]:
            lines.append(f'▫️ <a href="{esc(lot["url"])}">{title}</a> — <b>{_price(lot)}</b>')
        else:
            lines.append(f"▫️ {title} — <b>{_price(lot)}</b>")
    lines += ["", FOOTER]
    await msg.answer("\n".join(lines), disable_web_page_preview=True)
