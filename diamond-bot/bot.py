"""
DiamondScanBot — Telegram bot entrypoint (aiogram 3).

The "radar": dealers paste/forward stones and requests; the bot structures them,
matches buyers with sellers, and reveals counterparty contact behind a subscription.
Focus market: Dubai. Ingestion is opt-in (forward/CSV) + per-subscriber BYO-session;
no covert WhatsApp scraping (see the market report §5).

Run:  python bot.py   (long-polling; needs TELEGRAM_BOT_TOKEN in .env)
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
    PreCheckoutQuery, BufferedInputFile,
)

import db
import matcher
import payments
from config import settings
from dealcard import generate_caption, render_card, render_match_card, match_caption
from enrich import verify_cert, cross_check
from ingest import ingest_text, import_csv
from parser import parse_message, Intent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("diamondscan")
router = Router()

SEED_GROUPS = [
    {"handle": "@demandsnatural", "title": "DEMANDS Natural Diamonds", "members": 2136, "nature": "want"},
    {"handle": "@diamondsexport", "title": "Natural Diamonds & Jewellery", "members": 1050, "nature": "have"},
    {"handle": "@certifieddiamonds", "title": "Certified Polished Diamonds", "members": 206, "nature": "have"},
    {"handle": "@diamonds_jewels_antwerp", "title": "Diamonds & Jewels Antwerp", "members": 93, "nature": "have"},
]
GROUP_NATURE = {g["handle"]: g["nature"] for g in SEED_GROUPS}


# ─────────────────────────────── helpers ─────────────────────────────────────

def is_admin(uid: int) -> bool:
    return uid in settings.admin_user_ids


def has_sub(uid: int) -> bool:
    return is_admin(uid) or db.active_subscription(uid) is not None


def role_of(uid: int) -> str:
    u = db.get_user(uid)
    return (u or {}).get("role", "buyer")


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 I'm buying", callback_data="role:buyer"),
         InlineKeyboardButton(text="💎 I'm selling", callback_data="role:seller")],
        [InlineKeyboardButton(text="🤝 I'm a broker", callback_data="role:broker")],
        [InlineKeyboardButton(text="⭐ Subscribe", callback_data="menu:subscribe"),
         InlineKeyboardButton(text="✅ Get verified", callback_data="menu:vetting")],
        [InlineKeyboardButton(text="ℹ️ How it works", callback_data="menu:help")],
    ])


def sub_menu() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=payments.plan_label(t), callback_data=f"buy:{t}")]
            for t in settings.tiers]
    return InlineKeyboardMarkup(inline_keyboard=rows)


WELCOME = (
    "💎 <b>DiamondScan</b> — the Dubai diamond radar.\n\n"
    "Paste or <b>forward</b> any stone or request — I structure it, match buyers with "
    "sellers in real time, and ping you the moment your stone or your buyer appears.\n\n"
    "Examples you can send me right now:\n"
    "• <code>Looking for 2ct D VS1 GIA, Rap -25%</code>\n"
    "• <code>Available Cushion 0.90 Fancy Light Pink SI1 GIA $26,000/ct</code>\n\n"
    "First, who are you?"
)

HELP = (
    "<b>How DiamondScan works</b>\n\n"
    "1️⃣ <b>Feed the radar.</b> Forward messages from your dealer groups, paste a stone, "
    "or upload a stock file (CSV/Excel in RapNet format).\n"
    "2️⃣ <b>I structure it.</b> Every 'have' and 'looking-for' becomes a clean record "
    "(shape · carat · color · clarity · cert · Rap%).\n"
    "3️⃣ <b>I match &amp; alert.</b> When a listing meets a request, both sides get pinged.\n"
    "4️⃣ <b>You connect.</b> Subscribers reveal the counterparty and close the deal your way "
    "(memo or wire) — we don't touch goods or money.\n\n"
    "🔐 <b>Trust:</b> get <b>verified</b> (ID + business + OFAC screen) for the ✅ badge.\n"
    "🛡️ We ingest only what you opt in (forwards, your own stock, groups you already belong to). "
    "No covert scraping.\n\n"
    f"Plans: {' · '.join(payments.plan_label(t) for t in settings.tiers)}"
)


async def _handle_stone_text(msg: Message, text: str, source: str) -> None:
    uid = msg.from_user.id
    role = role_of(uid)
    default_intent = {"seller": Intent.HAVE.value, "buyer": Intent.WANT.value}.get(role)
    res = ingest_text(text, tg_id=uid, source=source, default_intent=default_intent)
    if not res:
        await msg.reply("🤔 I couldn't read a diamond in that. Try: "
                        "<code>Round 1.01 G VS2 GIA Rap -22%</code>")
        return
    if not res.get("stored"):
        await msg.reply("🚫 That looked like spam/scam and was filtered out.")
        return

    stone = parse_message(text, default_intent=default_intent)
    kind = res["kind"]
    conf = res.get("confidence", 0)

    if kind == "demand":
        # match this demand against active listings, best first
        listings = db.active_listings()
        pairs = matcher.run_matching([{**stone.to_dict(), "id": res["id"]}], listings, threshold=0.6)
        head = (f"📝 Logged your <b>request</b>: <b>{stone.key_summary()}</b> "
                f"(confidence {conf:.0%}).\n")
        if not pairs:
            await msg.reply(head + "No live match yet — I'll ping you the instant one appears. "
                                   "You can also /subscribe to unlock full history.")
            return
        lines = [head + f"⚡ <b>{len(pairs)} match(es) right now:</b>"]
        kb_rows = []
        for _d, lis, sc in pairs[:5]:
            db.record_match(res["id"], lis["id"], sc)
            lines.append(f"• {_listing_line(lis)}  <b>{sc:.0%}</b>")
            kb_rows.append([InlineKeyboardButton(
                text=f"🤝 Connect · {lis.get('shape','?')} {lis.get('carat','')}ct ({sc:.0%})",
                callback_data=f"connect:{lis['id']}")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        await msg.reply("\n".join(lines), reply_markup=kb)
    else:
        # a new listing: alert buyers whose demands it satisfies
        demands = db.active_demands()
        pairs = matcher.run_matching(demands, [{**stone.to_dict(), "id": res["id"]}], threshold=0.6)
        note = (f"💎 Logged your <b>stone</b>: <b>{stone.key_summary()}</b> "
                f"(confidence {conf:.0%}).")
        if stone.cert_number and stone.lab == "GIA":
            cert = verify_cert(stone.cert_number, "GIA")
            issues = cross_check(stone.to_dict(), cert or {})
            if cert and cert.get("verified"):
                note += "\n📄 GIA cert verified."
                if issues:
                    note += " ⚠️ Mismatch vs text: " + "; ".join(issues)
        if pairs:
            note += f"\n🔔 <b>{len(pairs)} buyer(s)</b> are looking for this — notifying them."
            for dem, _l, sc in pairs[:20]:
                db.record_match(dem["id"], res["id"], sc)
        await msg.reply(note)
        await _notify_new_matches(msg.bot)


def _listing_line(l: dict) -> str:
    bits = [str(l.get("shape") or "").capitalize(), f"{l.get('carat')}ct" if l.get("carat") else "",
            l.get("fancy_color") or l.get("color") or "", l.get("clarity") or "", l.get("lab") or ""]
    label = " ".join(b for b in bits if b)
    price = (f"${l['price_per_carat']:,.0f}/ct" if l.get("price_per_carat")
             else (f"${l['total_price']:,.0f}" if l.get("total_price") else "POR"))
    disc = f" · Rap {l['rap_discount']:+g}%" if l.get("rap_discount") is not None else ""
    return f"{label} — {price}{disc}"


async def _notify_new_matches(bot: Bot) -> None:
    """Push any unnotified matches to the buyer who created the demand."""
    for m in db.unnotified_matches():
        dem = db.get_demand(m["demand_id"])
        lis = db.get_listing(m["listing_id"])
        if not dem or not lis or not dem.get("tg_id"):
            db.mark_notified(m["id"])
            continue
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text=f"🤝 Connect ({m['score']:.0%})", callback_data=f"connect:{lis['id']}")]])
        # locked caption/card: the seller contact stays behind the subscription (revealed on Connect)
        caption = match_caption(dem, lis, m["score"], revealed=False,
                                bot_username=settings.bot_username)
        try:
            card = None
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                card = render_match_card(dem, lis, m["score"], tmp_path, revealed=False)
            except Exception as ce:  # noqa: BLE001
                log.warning("match card render failed: %s", ce)
            if card:
                with open(card, "rb") as f:
                    await bot.send_photo(dem["tg_id"], BufferedInputFile(f.read(), "match.png"),
                                         caption=caption, reply_markup=kb)
            else:
                await bot.send_message(dem["tg_id"], caption, reply_markup=kb)
        except Exception as e:  # noqa: BLE001
            log.warning("notify failed for %s: %s", dem["tg_id"], e)
        db.mark_notified(m["id"])


# ─────────────────────────────── commands ────────────────────────────────────

@router.message(CommandStart())
async def start(msg: Message) -> None:
    db.upsert_user(msg.from_user.id, msg.from_user.username or "",
                   msg.from_user.full_name or "")
    db.log_event("start", msg.from_user.id)
    await msg.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("help"))
async def help_cmd(msg: Message) -> None:
    await msg.answer(HELP)


@router.message(Command("subscribe"))
async def subscribe_cmd(msg: Message) -> None:
    await msg.answer("⭐ <b>Choose a plan</b> — pay in Telegram Stars, cancel anytime:",
                     reply_markup=sub_menu())


@router.message(Command("matches"))
async def matches_cmd(msg: Message) -> None:
    rows = db.matches_for_user(msg.from_user.id)
    if not rows:
        await msg.answer("No matches yet. Send me a request like "
                         "<code>Looking for 1ct F VS1 GIA</code> and I'll hunt.")
        return
    lines = ["<b>Your recent matches</b>"]
    for r in rows[:10]:
        lines.append(f"• {r['listing_text'][:70]}  <b>{r['score']:.0%}</b>")
    await msg.answer("\n".join(lines))


@router.message(Command("status"))
async def status_cmd(msg: Message) -> None:
    if not is_admin(msg.from_user.id):
        return
    c = db.counts()
    await msg.answer("📊 <b>Radar status</b>\n" + "\n".join(f"{k}: <b>{v}</b>" for k, v in c.items()))


@router.message(Command("publish"))
async def publish_cmd(msg: Message) -> None:
    """Admin: /publish <listing_id> — post a deal card to the channel."""
    if not is_admin(msg.from_user.id):
        return
    parts = (msg.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await msg.answer("Usage: <code>/publish &lt;listing_id&gt;</code>")
        return
    lis = db.get_listing(int(parts[1]))
    if not lis:
        await msg.answer("Listing not found.")
        return
    await _publish_listing(msg.bot, lis, target=settings.channel_id or msg.chat.id)
    await msg.answer("Published ✅")


async def _publish_listing(bot: Bot, lis: dict, target) -> None:
    import tempfile
    caption = generate_caption(lis, verified=(lis.get("status") == "active"),
                               contact=settings.contact_phone,
                               bot_username=settings.bot_username)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        card_path = tmp.name
    path = render_card(lis, card_path, verified=True)
    if path:
        with open(path, "rb") as f:
            await bot.send_photo(target, BufferedInputFile(f.read(), "deal.png"), caption=caption)
    else:
        await bot.send_message(target, caption)


# forwarded messages
@router.message(F.forward_date)
async def on_forward(msg: Message) -> None:
    if msg.text or msg.caption:
        await _handle_stone_text(msg, msg.text or msg.caption, source="forward")


# document (CSV/stock file)
@router.message(F.document)
async def on_document(msg: Message) -> None:
    doc = msg.document
    if not (doc.file_name or "").lower().endswith((".csv", ".txt")):
        await msg.reply("Send a CSV stock file (RapNet-style headers) and I'll import it.")
        return
    file = await msg.bot.get_file(doc.file_id)
    buf = await msg.bot.download_file(file.file_path)
    res = import_csv(buf.read(), tg_id=msg.from_user.id)
    await msg.reply(f"📥 Imported <b>{res['stored']}</b> stones ({res['skipped']} skipped). "
                    "Running matches…")
    await _notify_new_matches(msg.bot)


# any other free text = a stone or a request
@router.message(F.text & ~F.text.startswith("/"))
async def on_text(msg: Message) -> None:
    await _handle_stone_text(msg, msg.text, source="manual")


# ─────────────────────────────── callbacks ───────────────────────────────────

@router.callback_query(F.data.startswith("role:"))
async def cb_role(cb: CallbackQuery) -> None:
    role = cb.data.split(":", 1)[1]
    db.upsert_user(cb.from_user.id, cb.from_user.username or "", cb.from_user.full_name or "", role=role)
    db.log_event("role_set", cb.from_user.id, {"role": role})
    tips = {
        "buyer": "Send me what you're hunting: <code>Looking for 2ct D VS1 GIA</code>.",
        "seller": "Forward or paste your stock. I'll alert buyers who want it.",
        "broker": "Forward both sides — requests and stock. I'll match across them.",
    }
    await cb.message.answer(f"Got it — <b>{role}</b>. {tips[role]}")
    await cb.answer()


@router.callback_query(F.data == "menu:subscribe")
async def cb_subscribe(cb: CallbackQuery) -> None:
    await cb.message.answer("⭐ <b>Choose a plan</b>:", reply_markup=sub_menu())
    await cb.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help(cb: CallbackQuery) -> None:
    await cb.message.answer(HELP)
    await cb.answer()


@router.callback_query(F.data == "menu:vetting")
async def cb_vetting(cb: CallbackQuery) -> None:
    db.set_vetting(cb.from_user.id, "pending", "requested via bot")
    db.log_event("vetting_requested", cb.from_user.id)
    await cb.message.answer(
        "✅ <b>Get verified</b>\nReply with: company name, trade licence No., and a photo of "
        "your ID/licence. We run an OFAC/sanctions screen and grant the ✅ badge (usually &lt;1 business day). "
        "Verification is what makes buyers trust your listings.")
    await cb.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery) -> None:
    tier = cb.data.split(":", 1)[1]
    if tier not in settings.tiers:
        await cb.answer("Unknown plan", show_alert=True)
        return
    await payments.send_invoice(cb.bot, cb.from_user.id, tier)
    await cb.answer()


@router.callback_query(F.data.startswith("connect:"))
async def cb_connect(cb: CallbackQuery) -> None:
    listing_id = int(cb.data.split(":", 1)[1])
    lis = db.get_listing(listing_id)
    if not lis:
        await cb.answer("Listing expired", show_alert=True)
        return
    if not has_sub(cb.from_user.id):
        await cb.message.answer(
            "🔒 <b>Contact is a subscriber feature.</b>\nUnlock counterparty details and unlimited "
            "matches:", reply_markup=sub_menu())
        await cb.answer()
        return
    owner = db.get_user(lis.get("tg_id")) if lis.get("tg_id") else None
    contact = "—"
    if owner:
        contact = ("@" + owner["username"]) if owner.get("username") else (owner.get("phone") or owner.get("full_name") or "—")
    db.log_event("contact_revealed", cb.from_user.id, {"listing_id": listing_id})
    await cb.message.answer(
        f"🤝 <b>Connect</b>\nStone: <b>{_listing_line(lis)}</b>\nSeller: <b>{contact}</b>\n"
        f"Source: {lis.get('source_group') or lis.get('source')}\n\n"
        "Close it your way (memo 30–90d or wire). Tip: confirm the GIA cert number and "
        "match the laser inscription before paying.")
    await cb.answer()


# ─────────────────────────────── payments ────────────────────────────────────

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery) -> None:
    await q.answer(ok=True)


@router.message(F.successful_payment)
async def paid(msg: Message) -> None:
    sp = msg.successful_payment
    tier = await payments.on_successful_payment(
        msg.from_user.id, sp.invoice_payload, sp.telegram_payment_charge_id, sp.total_amount)
    await msg.answer(f"✅ <b>{settings.tiers[tier]['title']} active.</b> Contact reveals and full "
                     "match history unlocked. Send me a request or forward your stock.")


# ─────────────────────────────── runner ──────────────────────────────────────

async def _set_commands(bot: Bot) -> None:
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="Start / main menu"),
        BotCommand(command="subscribe", description="Plans & Stars payment"),
        BotCommand(command="matches", description="Your recent matches"),
        BotCommand(command="help", description="How it works"),
    ])


async def main() -> None:
    db.init_db()
    db.seed_groups(SEED_GROUPS)
    bot = Bot(settings.require_token(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await _set_commands(bot)
    me = await bot.get_me()
    log.info("Starting @%s (id=%s), market=%s", me.username, me.id, settings.market)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
