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
    BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton,
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

# Dev-only egress shim: some sandboxes route outbound HTTPS through a TLS-intercepting
# proxy with a private CA. Trust that CA and route aiogram through the proxy — but ONLY
# when those are present. In production (Railway) neither exists, so this is a no-op and
# the default direct session is used.
import os as _os
_CA = "/root/.ccr/ca-bundle.crt"
if _os.path.exists(_CA) and not _os.environ.get("SSL_CERT_FILE"):
    _os.environ["SSL_CERT_FILE"] = _CA


def _build_session():
    proxy = _os.environ.get("HTTPS_PROXY") or _os.environ.get("https_proxy")
    if not proxy:
        return None  # production: default session, direct egress
    from aiogram.client.session.aiohttp import AiohttpSession
    log.info("Routing Telegram API through proxy %s", proxy)
    return AiohttpSession(proxy=proxy)

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
    # FREE_REVEAL is a testing switch that opens the paywall for everyone (see config).
    return settings.free_reveal or is_admin(uid) or db.active_subscription(uid) is not None


def role_of(uid: int) -> str:
    u = db.get_user(uid)
    return (u or {}).get("role", "buyer")


# ── LuxeDiam-style persistent reply keyboard ──
BTN_UPLOAD = "💎 Upload Stock"
BTN_SEARCH = "🔎 Search Diamond"
BTN_MINE = "📦 My Diamonds"
BTN_SAVED = "⭐ Saved"
BTN_SOLD = "✅ Mark as Sold"
BTN_SUBSCRIBE = "💳 Subscription"
BTN_SUPPORT = "🆘 Support"
BUTTONS = {BTN_UPLOAD, BTN_SEARCH, BTN_MINE, BTN_SAVED, BTN_SOLD, BTN_SUBSCRIBE, BTN_SUPPORT}

# lightweight per-user input mode ("upload" | "search"); resets on restart (fine for MVP)
_MODE: dict[int, str] = {}


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_UPLOAD), KeyboardButton(text=BTN_SEARCH)],
            [KeyboardButton(text=BTN_MINE), KeyboardButton(text=BTN_SAVED)],
            [KeyboardButton(text=BTN_SOLD), KeyboardButton(text=BTN_SUBSCRIBE)],
            [KeyboardButton(text=BTN_SUPPORT)],
        ],
        resize_keyboard=True, is_persistent=True, input_field_placeholder="Paste a stone or a request…",
    )


def user_tier(uid: int) -> str:
    sub = db.active_subscription(uid)
    return sub["tier"] if sub and sub.get("tier") in settings.tiers else "free"


def stock_status(uid: int) -> tuple[int, object, str]:
    """(used, limit_or_None, tier)."""
    tier = user_tier(uid)
    return db.count_active_listings(uid), settings.stock_limit(tier), tier


def sub_menu() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=payments.plan_label(t), callback_data=f"buy:{t}")]
            for t in settings.paid_tiers]
    return InlineKeyboardMarkup(inline_keyboard=rows)


WELCOME = (
    "💎 <b>DiamondScan</b> — the Dubai diamond radar.\n\n"
    "I turn dealer-chat 'have / looking-for' into a structured feed and <b>match buyers with "
    "sellers automatically</b> — no more scrolling group history.\n\n"
    "• <b>Upload Stock</b> — forward, paste, or CSV your diamonds\n"
    "• <b>Search Diamond</b> — describe what you need, I hunt across all stock\n"
    "• I ping both sides the moment a stone meets a request.\n\n"
    "Use the menu below 👇"
)

HELP = (
    "<b>How DiamondScan works</b>\n\n"
    "1️⃣ <b>Feed the radar.</b> Forward messages from your dealer groups, paste a stone, "
    "or upload a stock file (CSV/Excel in RapNet format).\n"
    "2️⃣ <b>I structure it.</b> Every 'have' and 'looking-for' becomes a clean record "
    "(shape · carat · color · clarity · cert · Rap%).\n"
    "3️⃣ <b>I match &amp; alert.</b> When a listing meets a request, both sides get pinged.\n"
    "4️⃣ <b>You connect.</b> Tap Connect to reach the counterparty and close the deal your way "
    "(memo or wire) — we don't touch goods or money.\n\n"
    "🔐 <b>Trust:</b> get <b>verified</b> (ID + business + OFAC screen) for the ✅ badge.\n"
    "🛡️ We ingest only what you opt in (forwards, your own stock, groups you already belong to). "
    "No covert scraping.\n\n"
    "💳 <b>Plans</b> (by stock size): Free up to 500 stones · "
    + " · ".join(f"AED {settings.tiers[t]['aed']}/mo {('unlimited' if settings.tiers[t]['max_stock'] is None else str(settings.tiers[t]['max_stock']))}" for t in settings.paid_tiers)
)


def at_stock_limit(uid: int) -> bool:
    used, limit, _ = stock_status(uid)
    return limit is not None and used >= limit


async def _limit_prompt(msg: Message) -> None:
    used, limit, tier = stock_status(msg.from_user.id)
    await msg.reply(
        f"📦 You're at your plan limit (<b>{used}/{limit}</b> stones on <b>{settings.tiers[tier]['title']}</b>).\n"
        "Upgrade to keep listing — pick a plan 👇", reply_markup=sub_menu())


async def _handle_stone_text(msg: Message, text: str, source: str,
                             force_intent: str | None = None) -> None:
    uid = msg.from_user.id
    if force_intent is None:
        role = role_of(uid)
        default_intent = {"seller": Intent.HAVE.value, "buyer": Intent.WANT.value}.get(role)
    else:
        default_intent = force_intent
    # enforce the stock cap before storing a new listing (upload path)
    if force_intent == Intent.HAVE.value and at_stock_limit(uid):
        await _limit_prompt(msg)
        return
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
    _MODE.pop(msg.from_user.id, None)
    await msg.answer(WELCOME, reply_markup=main_kb())


@router.message(Command("help"))
async def help_cmd(msg: Message) -> None:
    await msg.answer(HELP)


@router.message(Command("subscribe"))
async def subscribe_cmd(msg: Message) -> None:
    await _show_subscription(msg)


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


# forwarded messages = incoming stock (enforce the stock cap)
@router.message(F.forward_date)
async def on_forward(msg: Message) -> None:
    if msg.text or msg.caption:
        await _handle_stone_text(msg, msg.text or msg.caption, source="forward",
                                 force_intent=Intent.HAVE.value)


# document (CSV/stock file)
@router.message(F.document)
async def on_document(msg: Message) -> None:
    doc = msg.document
    if not (doc.file_name or "").lower().endswith((".csv", ".txt")):
        await msg.reply("Send a CSV stock file (RapNet-style headers) and I'll import it.")
        return
    if at_stock_limit(msg.from_user.id):
        await _limit_prompt(msg)
        return
    file = await msg.bot.get_file(doc.file_id)
    buf = await msg.bot.download_file(file.file_path)
    res = import_csv(buf.read(), tg_id=msg.from_user.id)
    await msg.reply(f"📥 Imported <b>{res['stored']}</b> stones ({res['skipped']} skipped). "
                    "Running matches…")
    await _notify_new_matches(msg.bot)


# ── LuxeDiam-style menu views ──

async def _show_subscription(msg: Message) -> None:
    used, limit, tier = stock_status(msg.from_user.id)
    cap = "unlimited" if limit is None else f"{limit:,}"
    lines = [
        f"🆓 <b>{settings.tiers[tier]['title']} tier</b>",
        f"💎 Your stock: <b>{used}</b> stones (limit: <b>{cap}</b>)\n",
        "📊 <b>Pricing</b>",
        "• Up to 500 stones — <b>free</b>",
        f"• 500–1,000 stones — <b>AED {settings.tiers['grow']['aed']} / month</b>",
        f"• 1,000+ stones — <b>AED {settings.tiers['pro']['aed']} / month</b>\n",
        "Growing your stock? Pick a plan anytime 👇",
    ]
    await msg.answer("\n".join(lines), reply_markup=sub_menu())


async def menu_mine(msg: Message) -> None:
    rows = db.listings_for_user(msg.from_user.id, status="active", limit=30)
    used, limit, tier = stock_status(msg.from_user.id)
    cap = "unlimited" if limit is None else f"{limit:,}"
    if not rows:
        await msg.answer(f"📦 <b>My Diamonds</b> — 0 / {cap}.\nTap <b>{BTN_UPLOAD}</b> to add stock.")
        return
    lines = [f"📦 <b>My Diamonds</b> — {used} / {cap} active:"]
    for l in rows[:30]:
        lines.append(f"• #{l['id']} {_listing_line(l)}")
    await msg.answer("\n".join(lines))


async def menu_saved(msg: Message) -> None:
    rows = db.demands_for_user(msg.from_user.id, limit=30)
    if not rows:
        await msg.answer("⭐ <b>Saved searches</b> — none yet.\n"
                         f"Tap <b>{BTN_SEARCH}</b> and describe a stone; I'll keep hunting it for you.")
        return
    lines = ["⭐ <b>Saved searches</b> (I alert you on any match):"]
    for d in rows[:30]:
        label = d.get("raw_text") or " ".join(
            str(d.get(k)) for k in ("shape", "carat", "color", "clarity") if d.get(k)) or "request"
        lines.append(f"• {label[:70]}")
    await msg.answer("\n".join(lines))


async def menu_sold(msg: Message) -> None:
    rows = db.listings_for_user(msg.from_user.id, status="active", limit=30)
    if not rows:
        await msg.answer("Nothing active to mark sold.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Sold: #{l['id']} {l.get('shape','?')} {l.get('carat','')}ct",
                              callback_data=f"sold:{l['id']}")] for l in rows[:15]])
    await msg.answer("✅ <b>Mark as Sold</b> — tap a stone to remove it from the market:", reply_markup=kb)


async def menu_support(msg: Message) -> None:
    if settings.support_url:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text="💬 Open chat with support", url=settings.support_url)]])
        await msg.answer("🆘 Tap below to chat with our support team directly.", reply_markup=kb)
    else:
        await msg.answer("🆘 <b>Support</b>\nReply here with your question — the team will get back to you. "
                         "You can also reach us at " + settings.contact_phone + ".")


# router for the persistent keyboard + free text (stone/request), honoring input mode
@router.message(F.text & ~F.text.startswith("/"))
async def on_text(msg: Message) -> None:
    t = (msg.text or "").strip()
    uid = msg.from_user.id
    if t == BTN_UPLOAD:
        _MODE[uid] = "upload"
        used, limit, _ = stock_status(uid)
        cap = "unlimited" if limit is None else f"{limit:,}"
        await msg.answer(
            f"💎 <b>Upload Stock</b> ({used}/{cap} used)\nForward, paste, or send a CSV. One per line works too.\n"
            "Format: <code>Shape Carat Color Clarity Cut Ratio Rap% Price/ct</code> (+ photo/cert optional)\n"
            "e.g. <code>Round 1.01 G VS2 EX GIA 2141234567 $5,600/ct Rap -21%</code>")
        return
    if t == BTN_SEARCH:
        _MODE[uid] = "search"
        await msg.answer("🔎 <b>Search Diamond</b>\nDescribe what you're looking for.\n"
                         "Example: <code>2 carat round brilliant D VS1</code>")
        return
    if t == BTN_MINE:
        return await menu_mine(msg)
    if t == BTN_SAVED:
        return await menu_saved(msg)
    if t == BTN_SOLD:
        return await menu_sold(msg)
    if t == BTN_SUBSCRIBE:
        return await _show_subscription(msg)
    if t == BTN_SUPPORT:
        return await menu_support(msg)

    # otherwise it's a stone or a request — honor the current mode
    mode = _MODE.get(uid)
    force = {"upload": Intent.HAVE.value, "search": Intent.WANT.value}.get(mode)
    await _handle_stone_text(msg, t, source="manual", force_intent=force)


# ─────────────────────────────── callbacks ───────────────────────────────────

@router.callback_query(F.data.startswith("sold:"))
async def cb_sold(cb: CallbackQuery) -> None:
    listing_id = int(cb.data.split(":", 1)[1])
    ok = db.mark_listing_sold(listing_id, cb.from_user.id)
    db.log_event("mark_sold", cb.from_user.id, {"listing_id": listing_id, "ok": ok})
    await cb.answer("Marked sold ✅" if ok else "Not found / not yours", show_alert=not ok)
    if ok and cb.message:
        await cb.message.answer(f"✅ #{listing_id} marked sold and removed from the market.")


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery) -> None:
    tier = cb.data.split(":", 1)[1]
    if tier not in settings.paid_tiers:
        await cb.answer("Unknown plan", show_alert=True)
        return
    t = settings.tiers[tier]
    cap = "unlimited stock" if t["max_stock"] is None else f"up to {t['max_stock']:,} stones"
    pay = await payments.create_payment(tier, cb.from_user.id)
    if pay and pay.get("url"):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text=f"💳 Pay AED {t['aed']} / month", url=pay["url"])]])
        await cb.message.answer(
            f"🔒 <b>{t['title']}</b> — {cap}, AED {t['aed']}/month.\n"
            "Tap below to complete payment securely (AED). Your subscription activates "
            "automatically after checkout.", reply_markup=kb)
    else:
        await cb.message.answer(
            f"🔒 <b>{t['title']}</b> — {cap}, AED {t['aed']}/month.\n"
            "Card payments (AED) are being switched on — ping the admin to activate your plan.")
    await cb.answer()


@router.callback_query(F.data.startswith("connect:"))
async def cb_connect(cb: CallbackQuery) -> None:
    listing_id = int(cb.data.split(":", 1)[1])
    lis = db.get_listing(listing_id)
    if not lis:
        await cb.answer("Listing expired", show_alert=True)
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


# ─────────────────────────── payment webhook (veym) ──────────────────────────

async def _webhook_app(bot: Bot):
    """aiohttp app: receives veym/MamoPay events and a health check. Binds $PORT so
    the same Railway service handles both long-polling and inbound webhooks."""
    from aiohttp import web

    async def mamopay_webhook(request: "web.Request"):
        auth = request.headers.get("authorization", "") or request.headers.get("Authorization", "")
        if not payments.verify_webhook_auth(auth):
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
        try:
            event = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "bad json"}, status=400)
        result = payments.handle_webhook_event(event)
        if result:
            tg_id, tier = result
            try:
                await bot.send_message(
                    tg_id, f"✅ <b>{settings.tiers[tier]['title']} active.</b> Contact reveals and "
                           "full match history are unlocked. Send a request or forward your stock.")
            except Exception as e:  # noqa: BLE001
                log.warning("post-payment notify failed for %s: %s", tg_id, e)
        return web.json_response({"ok": True})

    async def ok(_):
        from aiohttp import web as _w
        return _w.Response(text="DiamondScan up")

    app = web.Application()
    app.router.add_post("/mamopay-webhook", mamopay_webhook)
    app.router.add_get("/health", ok)
    app.router.add_get("/", ok)
    app.router.add_get("/paid", lambda r: web.Response(text="Payment received — you can return to Telegram."))
    app.router.add_get("/failed", lambda r: web.Response(text="Payment failed — try again in the bot."))
    return app


# ─────────────────────────────── runner ──────────────────────────────────────

async def _set_commands(bot: Bot) -> None:
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="What DiamondScan does"),
        BotCommand(command="subscribe", description="Plans & payment (AED)"),
        BotCommand(command="matches", description="Your recent matches"),
        BotCommand(command="help", description="How it works"),
    ])


async def main() -> None:
    db.init_db()
    db.seed_groups(SEED_GROUPS)
    bot = Bot(settings.require_token(), session=_build_session(),
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await _set_commands(bot)
    me = await bot.get_me()
    log.info("Starting @%s (id=%s), market=%s, free_reveal=%s", me.username, me.id,
             settings.market, settings.free_reveal)

    # webhook server (payments) alongside long-polling, both in one process
    from aiohttp import web
    app = await _webhook_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.port)
    await site.start()
    log.info("Webhook server on :%s (POST /mamopay-webhook)", settings.port)
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
