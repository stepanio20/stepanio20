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
import re
from html import escape as _esc

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
from ingest import ingest_text, import_stock
from parser import parse_message, Intent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("diamondscan")
router = Router()

# Dev-only egress shim: some sandboxes route outbound HTTPS through a TLS-intercepting
# proxy with a private CA. Trust that CA and route aiogram through the proxy — but ONLY
# when those are present. In production (Railway) neither exists, so this is a no-op and
# the default direct session is used.
import os as _os
from pathlib import Path as _Path
_BRAND = _Path(__file__).resolve().parent / "branding"
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


def _welcome(live: int) -> str:
    head = "💎 <b>DiamondScan</b> — Dubai's diamond radar.\n"
    proof = f"📊 <b>{live:,}</b> stones are live on the desk right now.\n\n" if live else "\n"
    return (
        head + proof +
        "Dealers post “have” and “looking for” across a dozen groups all day. I turn that noise into one "
        "structured feed and <b>match buyers to sellers automatically</b> — so you stop scrolling and start "
        "closing.\n\n"
        "💎 <b>Upload Stock</b> — forward, paste, or drop a CSV/Excel. I list it and alert every buyer who wants it.\n"
        "🔎 <b>Search Diamond</b> — describe the stone; I hunt all live stock and save the search if it's not here yet.\n\n"
        "The moment a stone meets a request, both sides get pinged. 👇"
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
    "💳 <b>Plans</b> — priced by stock size:\n"
    "• <b>Free</b> — up to 500 stones\n"
    "• <b>Grow</b> — up to 1,000 stones · AED 99/mo\n"
    "• <b>Pro</b> — unlimited stones · AED 199/mo"
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
    # mode is sticky (set by the Upload/Search buttons, cleared by any other button) so a whole
    # paste-burst keeps one intent; explicit "looking for"/"available" wording still overrides it.
    if force_intent is not None:
        default_intent = force_intent
    else:
        mode = _MODE.get(uid)
        default_intent = {"upload": Intent.HAVE.value, "search": Intent.WANT.value}.get(mode)
        if default_intent is None:
            role = role_of(uid)
            default_intent = {"seller": Intent.HAVE.value, "buyer": Intent.WANT.value}.get(role)

    # peek at the resolved intent so we enforce the stock cap on any path that stores a listing
    peek = parse_message(text, default_intent=default_intent)
    resolved_have = bool(peek) and peek.intent == Intent.HAVE.value
    if resolved_have and at_stock_limit(uid):
        db.log_event("upload_limit_hit", uid, {})
        await _limit_prompt(msg)
        return

    res = ingest_text(text, tg_id=uid, source=source, default_intent=default_intent)
    if not res:
        await msg.reply("🤔 I couldn't spot a diamond in that. Try this shape:\n"
                        "<code>Round 1.01 G VS2 GIA Rap -22%</code>")
        return
    if not res.get("stored"):
        await msg.reply("🚫 That looked like spam and was filtered out. If it's a real stone, "
                        "re-send just the specs (shape, carat, color, clarity, lab).")
        return

    stone = peek
    kind = res["kind"]

    if kind == "demand":
        db.log_event("demand_created", uid, {"demand_id": res["id"]})
        listings = db.candidate_listings(stone.to_dict())
        pairs = matcher.run_matching([{**stone.to_dict(), "id": res["id"]}], listings, threshold=0.6)
        summ = _esc(stone.key_summary())
        if not pairs:
            await msg.reply(
                f"🔎 <b>Searched:</b> {summ}\n\n"
                "Nothing on the desk right now — but I've <b>saved this search</b>. You'll get an instant "
                "ping the second a matching stone lands. Manage open searches under <b>⭐ Saved</b>.")
            return
        n = len(pairs)
        shown = pairs[:5]
        lines = [f"✨ <b>{n} match{'es' if n != 1 else ''}</b> for <b>{summ}</b>", ""]
        kb_rows = []
        for i, (_d, lis, sc) in enumerate(shown, 1):
            db.record_match(res["id"], lis["id"], sc, notified=1)  # shown live → don't re-alert later
            db.log_event("match_shown", uid, {"demand_id": res["id"], "listing_id": lis["id"], "score": round(sc, 3)})
            lines.append(_stone_block(i, lis, sc))
            lines.append("")
            kb_rows.append([InlineKeyboardButton(text=f"🤝 Connect #{i}", callback_data=f"connect:{lis['id']}")])
        if n > len(shown):
            lines.append(f"…and <b>{n - len(shown)}</b> more. Add color, clarity, or a price ceiling to narrow it.")
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        await msg.reply("\n".join(lines).rstrip(), reply_markup=kb)
    else:
        db.log_event("listing_created", uid, {"listing_id": res["id"], "source": source})
        demands = db.active_demands()
        pairs = matcher.run_matching(demands, [{**stone.to_dict(), "id": res["id"]}], threshold=0.6)
        note = f"✅ Listed: <b>{_esc(stone.key_summary())}</b>."
        if stone.cert_number and stone.lab == "GIA":
            cert = verify_cert(stone.cert_number, "GIA")
            issues = cross_check(stone.to_dict(), cert or {})
            if cert and cert.get("verified"):
                note += "\n📄 GIA cert verified."
                if issues:
                    note += " ⚠️ Mismatch vs text: " + _esc("; ".join(issues))
        if pairs:
            note += f"\n🔔 <b>{len(pairs)}</b> buyer(s) already want this — I'm pinging them now."
            for dem, _l, sc in pairs[:20]:
                db.record_match(dem["id"], res["id"], sc)
        await msg.reply(note)
        await _notify_new_matches(msg.bot)


def _price_str(l: dict) -> str:
    if l.get("price_per_carat"):
        return f"${l['price_per_carat']:,.0f}/ct"
    if l.get("total_price"):
        return f"${l['total_price']:,.0f} total"
    return "price on request"


def _color_str(l: dict) -> str:
    if l.get("fancy_color"):
        return " ".join(x for x in [l.get("fancy_intensity"), l.get("fancy_color")] if x).title()
    return str(l.get("color") or "").upper()


def _listing_line(l: dict) -> str:
    bits = [str(l.get("shape") or "").capitalize(), f"{l.get('carat'):g}ct" if l.get("carat") else "",
            _color_str(l), l.get("clarity") or "", l.get("lab") or ""]
    label = " ".join(b for b in bits if b)
    disc = f" · Rap {l['rap_discount']:+g}%" if l.get("rap_discount") is not None else ""
    return _esc(f"{label} — {_price_str(l)}{disc}")


def _carat_str(l: dict) -> str:
    c = l.get("carat")
    return f"{c:g}ct" if c else ""


def _stone_block(idx: int, l: dict, score: float) -> str:
    """A clean multi-line stone entry for match lists (LuxeDiam-style). All fields escaped."""
    shape = str(l.get("shape") or "Diamond").capitalize()
    head = " ".join(b for b in [f"{idx}.", shape, _carat_str(l), _color_str(l), l.get("clarity") or ""] if b)
    meta = " · ".join(b for b in [
        l.get("lab"),
        (f"Fluor {l['fluorescence']}" if l.get("fluorescence") and str(l['fluorescence']).lower() not in ("none", "nil", "n") else None),
        (f"Rap {l['rap_discount']:+g}%" if l.get("rap_discount") is not None else None),
        ("🌱 lab-grown" if "lab_grown" in (l.get("flags") or "") else None),
    ] if b)
    lines = [f"<b>{_esc(head)}</b>   ·  {score:.0%} fit"]
    if meta:
        lines.append(f"    <i>{_esc(meta)}</i>")
    lines.append(f"    💰 <b>{_esc(_price_str(l))}</b>")
    return "\n".join(lines)


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
        tmp_path = None
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
        finally:
            if tmp_path:
                try:
                    _os.unlink(tmp_path)
                except OSError:
                    pass
        db.mark_notified(m["id"])


# ─────────────────────────────── commands ────────────────────────────────────

async def _send_branded(msg: Message, image: str, caption: str, reply_markup=None) -> None:
    """Send a caption with a branding image on top; fall back to text if the image is missing."""
    path = _BRAND / image
    try:
        with open(path, "rb") as f:
            await msg.answer_photo(BufferedInputFile(f.read(), image), caption=caption,
                                   reply_markup=reply_markup)
    except Exception:  # noqa: BLE001
        await msg.answer(caption, reply_markup=reply_markup)


def role_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💎 I'm selling", callback_data="role:seller"),
        InlineKeyboardButton(text="🔎 I'm buying", callback_data="role:buyer"),
    ]])


async def _show_shared_stone(msg: Message, lis: dict) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🤝 Connect with seller", callback_data=f"connect:{lis['id']}")]])
    await msg.answer("💎 <b>Shared stone</b>\n\n" + _stone_block(1, lis, 1.0) +
                     "\n\nTap Connect to reach the seller — or use the menu to search live stock.",
                     reply_markup=kb)
    await msg.answer("Menu 👇", reply_markup=main_kb())


@router.message(CommandStart())
async def start(msg: Message) -> None:
    uid = msg.from_user.id
    existing = db.get_user(uid)
    db.upsert_user(uid, msg.from_user.username or "", msg.from_user.full_name or "")
    _MODE.pop(uid, None)
    payload = ""
    parts = (msg.text or "").split(maxsplit=1)
    if len(parts) > 1:
        payload = parts[1].strip()
    db.log_event("start", uid, {"payload": payload, "new_user": existing is None})
    # share-a-stone deep link: t.me/<bot>?start=stone_<id>
    if payload.startswith("stone_") and payload[6:].isdecimal():
        lis = db.get_listing(int(payload[6:]))
        if lis and lis.get("status") == "active":
            await _show_shared_stone(msg, lis)
            return
    live = db.counts().get("listings", 0)
    await _send_branded(msg, "promo_square.png", _welcome(live), reply_markup=main_kb())
    if not (existing or {}).get("role"):
        await msg.answer("Which side are you on? It tells me how to read your messages 👇",
                         reply_markup=role_kb())


@router.callback_query(F.data.startswith("role:"))
async def cb_role(cb: CallbackQuery) -> None:
    role = cb.data.split(":", 1)[1]
    if role not in ("seller", "buyer"):
        await cb.answer()
        return
    db.upsert_user(cb.from_user.id, cb.from_user.username or "", cb.from_user.full_name or "", role=role)
    db.log_event("role_selected", cb.from_user.id, {"role": role})
    if role == "seller":
        await cb.message.answer(
            "💎 <b>You're selling.</b>\nForward a group message, paste a stone, or drop a CSV/Excel — "
            "I'll list it and ping every buyer who wants it.\n\n"
            "Try: <code>Round 1.01 G VS2 EX GIA $5,600/ct Rap -21%</code>")
    else:
        live = db.counts().get("listings", 0)
        await cb.message.answer(
            f"🔎 <b>You're buying.</b>\nTell me what you're sourcing and I'll search <b>{live:,}</b> live stones.\n\n"
            "Try: <code>2ct round D VS1 GIA</code>")
    await cb.answer()


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
        await msg.answer("No matches yet. Tap <b>🔎 Search Diamond</b> or send a request like "
                         "<code>1ct F VS1 GIA</code> and I'll start hunting.")
        return
    lines = ["<b>Your recent matches</b>", ""]
    for r in rows[:10]:
        lid = r.get("listing_id")
        label = _esc(str(r.get("listing_text") or "")[:70])
        lines.append(f"• {label}  <b>{r['score']:.0%}</b>  → /connect_{lid}" if lid else f"• {label}  <b>{r['score']:.0%}</b>")
    lines.append("\nTap a <b>/connect_…</b> link to reach the seller.")
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
    if len(parts) < 2 or not parts[1].isdecimal():
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
    try:
        path = render_card(lis, card_path, verified=True)
        if path:
            with open(path, "rb") as f:
                await bot.send_photo(target, BufferedInputFile(f.read(), "deal.png"), caption=caption)
        else:
            await bot.send_message(target, caption)
    finally:
        try:
            _os.unlink(card_path)
        except OSError:
            pass


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
    name = (doc.file_name or "").lower()
    if not name.endswith((".csv", ".txt", ".xlsx", ".xlsm", ".xls")):
        await msg.reply("Send a stock file — <b>CSV or Excel</b> (RapNet-style columns: "
                        "Shape, Weight, Color, Clarity, Cut, Lab, Report #, Price/ct…).")
        return
    uid = msg.from_user.id
    used, limit, tier = stock_status(uid)
    if limit is not None and used >= limit:
        db.log_event("upload_limit_hit", uid, {"used": used, "limit": limit, "tier": tier})
        await _limit_prompt(msg)
        return
    remaining = None if limit is None else max(0, limit - used)
    try:
        file = await msg.bot.get_file(doc.file_id)
        buf = await msg.bot.download_file(file.file_path)
        res = import_stock(buf.read(), doc.file_name or "", tg_id=uid, remaining=remaining)
    except Exception as e:  # noqa: BLE001
        log.warning("stock import failed: %s", e)
        await msg.reply("⚠️ Couldn't read that file. Check that <b>row 1 is your column headers</b> "
                        "(Shape, Weight, Color…) and re-send. Files over 20 MB can't be read here.")
        return
    db.log_event("csv_imported", uid, {"stored": res["stored"], "skipped": res.get("skipped", 0),
                                       "limit_skipped": res.get("limit_skipped", 0)})
    extra = ""
    if res.get("limit_skipped"):
        extra = (f"\n⚠️ <b>{res['limit_skipped']}</b> stones exceeded your plan cap and weren't listed — "
                 "upgrade to add them all.")
    await msg.reply(f"📥 Imported <b>{res['stored']}</b> stones "
                    f"({res.get('skipped', 0)} skipped — sold/blank rows).{extra}\n"
                    "I'll ping you the moment a buyer matches any of them.")
    if res.get("limit_skipped"):
        await _show_subscription(msg)
    await _notify_new_matches(msg.bot)


# ── LuxeDiam-style menu views ──

_TIER_EMOJI = {"free": "🆓", "grow": "📈", "pro": "⭐"}


async def _show_subscription(msg: Message) -> None:
    uid = msg.from_user.id
    used, limit, tier = stock_status(uid)
    cap = "unlimited" if limit is None else f"{limit:,}"
    db.log_event("subscribe_viewed", uid, {"used": used, "tier": tier})
    sub = db.active_subscription(uid)
    header = f"{_TIER_EMOJI.get(tier, '💳')} <b>You're on {settings.tiers[tier]['title']}.</b>"
    if sub and sub.get("expires_at"):
        import time as _t
        days = max(0, int((sub["expires_at"] - _t.time()) / 86400))
        header += f"  ·  renews in {days}d"
    lines = [
        header,
        f"💎 Stock in use: <b>{used}</b> / <b>{cap}</b>\n",
        "Every plan includes auto-matching and instant buyer/seller alerts. "
        "You pay only for how much you list:",
        "• <b>Free</b> — up to 500 stones",
        f"• <b>Grow</b> — up to 1,000 stones · <b>AED {settings.tiers['grow']['aed']}/mo</b>",
        f"• <b>Pro</b> — unlimited stones · <b>AED {settings.tiers['pro']['aed']}/mo</b>\n",
        "Outgrowing your cap? Upgrade in two taps 👇",
    ]
    await msg.answer("\n".join(lines), reply_markup=sub_menu())


async def menu_mine(msg: Message) -> None:
    uid = msg.from_user.id
    rows = db.listings_for_user(uid, status="active", limit=30)
    used, limit, _ = stock_status(uid)
    cap = "unlimited" if limit is None else f"{limit:,}"
    if not rows:
        await msg.answer(f"📦 <b>My Diamonds</b> — 0 / {cap}\n"
                         f"No stock listed yet. Tap <b>{BTN_UPLOAD}</b> to add your first stones — "
                         "I'll start matching buyers immediately.")
        return
    head = f"📦 <b>My Diamonds</b> — {used} / {cap} active"
    if used > len(rows):
        head += f"  <i>(showing first {len(rows)})</i>"
    lines = [head, ""]
    for l in rows:
        lines.append(f"• #{l['id']} {_listing_line(l)}")
    await msg.answer("\n".join(lines))


async def menu_saved(msg: Message) -> None:
    rows = db.demands_for_user(msg.from_user.id, limit=30)
    if not rows:
        await msg.answer("⭐ <b>Saved searches</b> — none yet\n"
                         f"Tap <b>{BTN_SEARCH}</b> and describe a stone. I'll keep hunting it and ping you "
                         "the moment it appears.")
        return
    lines = ["⭐ <b>Saved searches</b> — I alert you on any match:", ""]
    for d in rows:
        label = d.get("raw_text") or " ".join(
            str(d.get(k)) for k in ("shape", "carat", "color", "clarity") if d.get(k)) or "request"
        lines.append(f"• {_esc(str(label)[:70])}")
    await msg.answer("\n".join(lines))


async def menu_sold(msg: Message) -> None:
    rows = db.listings_for_user(msg.from_user.id, status="active", limit=15)
    if not rows:
        await msg.answer("✅ <b>Mark as Sold</b>\nNothing active to mark sold yet — your listed stones "
                         "will show up here.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"✅ #{l['id']} — {str(l.get('shape') or '?').capitalize()} {_carat_str(l)}".strip(),
            callback_data=f"sold:{l['id']}")] for l in rows])
    await msg.answer("✅ <b>Mark as Sold</b> — tap a stone to remove it from the market:", reply_markup=kb)


async def menu_support(msg: Message) -> None:
    if settings.support_url:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text="💬 Open chat with support", url=settings.support_url)]])
        await msg.answer("🆘 <b>Support</b>\nQuestion, verification, or a payment issue? "
                         "Tap below to chat with our team.", reply_markup=kb)
    else:
        extra = ""
        cp = (settings.contact_phone or "").strip()
        if cp and cp != "+971 56 000 0000":
            extra = f" Or reach us at {_esc(cp)}."
        await msg.answer("🆘 <b>Support</b>\nReply right here with your question and the team will get "
                         "back to you." + extra)


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
            f"💎 <b>Upload Stock</b> — {used}/{cap} used\n"
            "Forward a group message, paste a stone, or drop a CSV/Excel file. One stone per line.\n\n"
            "<b>Format:</b> <code>Shape Carat Color Clarity Cut Rap% Price/ct Lab Cert#</code>\n"
            "<b>Example:</b> <code>Round 1.01 G VS2 EX GIA 2141234567 $5,600/ct Rap -21%</code>")
        return
    if t == BTN_SEARCH:
        _MODE[uid] = "search"
        await msg.answer("🔎 <b>Search Diamond</b>\n"
                         "Describe the stone in plain words — I'll match it against all live stock.\n"
                         "<b>Example:</b> <code>2ct round D VS1 GIA under $18k/ct</code>")
        return
    if t in (BTN_MINE, BTN_SAVED, BTN_SOLD, BTN_SUBSCRIBE, BTN_SUPPORT):
        _MODE.pop(uid, None)  # leaving upload/search flow
        if t == BTN_MINE:
            return await menu_mine(msg)
        if t == BTN_SAVED:
            return await menu_saved(msg)
        if t == BTN_SOLD:
            return await menu_sold(msg)
        if t == BTN_SUBSCRIBE:
            return await _show_subscription(msg)
        return await menu_support(msg)

    # otherwise it's a stone or a request — _handle_stone_text honors the sticky mode
    await _handle_stone_text(msg, t, source="manual")


# ─────────────────────────────── callbacks ───────────────────────────────────

def _cb_id(data: str) -> Optional[int]:
    try:
        return int(data.split(":", 1)[1])
    except (ValueError, IndexError):
        return None


@router.callback_query(F.data.startswith("sold:"))
async def cb_sold(cb: CallbackQuery) -> None:
    listing_id = _cb_id(cb.data)
    if listing_id is None:
        await cb.answer()
        return
    ok = db.mark_listing_sold(listing_id, cb.from_user.id)
    db.log_event("mark_sold", cb.from_user.id, {"listing_id": listing_id, "ok": ok})
    await cb.answer("Marked sold ✅" if ok else "Not found / not yours", show_alert=not ok)
    if ok and cb.message:
        await cb.message.answer(f"✅ Sold — #{listing_id} is off the market. Nice one.")


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery) -> None:
    tier = cb.data.split(":", 1)[1]
    if tier not in settings.paid_tiers:
        await cb.answer("Unknown plan", show_alert=True)
        return
    t = settings.tiers[tier]
    cap = "unlimited stock" if t["max_stock"] is None else f"up to {t['max_stock']:,} stones"
    pay = await payments.create_payment(tier, cb.from_user.id)
    db.log_event("buy_clicked", cb.from_user.id, {"tier": tier, "link_created": bool(pay and pay.get("url"))})
    if pay and pay.get("url"):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text=f"💳 Pay AED {t['aed']} / month", url=pay["url"])]])
        await cb.message.answer(
            f"🔒 <b>{t['title']}</b> — {cap} · AED {t['aed']}/month\n"
            "Secure AED checkout below. Your plan activates automatically the moment payment clears.",
            reply_markup=kb)
    else:
        await cb.message.answer(
            f"🔒 <b>{t['title']}</b> — {cap} · AED {t['aed']}/month\n"
            "Card checkout is being switched on. Tap <b>🆘 Support</b> and we'll activate your plan right away.")
    await cb.answer()


def _reveal_text(listing_id: int) -> tuple[str, bool, bool]:
    """Build the Connect reveal text. Returns (text, ok, seller_reachable)."""
    lis = db.get_listing(listing_id)
    if not lis or lis.get("status") != "active":
        return ("That listing is no longer available.", False, False)
    owner_id = lis.get("tg_id")
    if not owner_id:
        return ("💠 <b>Indexed stock</b>\nThis stone is from an indexed market feed — the seller isn't on "
                "DiamondScan yet. I've noted your interest and will ping you if they join. Need it now? "
                "Tap <b>🆘 Support</b> and we'll chase the source.", True, False)
    owner = db.get_user(owner_id)
    contact = "—"
    if owner:
        contact = ("@" + owner["username"]) if owner.get("username") else (
            owner.get("phone") or owner.get("full_name") or "—")
    handle = str(lis.get("source_group") or "")
    group_line = f"\nGroup: {_esc(handle)}" if handle.startswith("@") else ""
    return (f"🤝 <b>Connect</b>\nStone: <b>{_listing_line(lis)}</b>\nSeller: <b>{_esc(contact)}</b>{group_line}\n\n"
            "Close it your way — memo (30–90d) or wire. DiamondScan never touches goods or money.\n"
            "⚠️ Before paying: confirm the GIA report number and match the laser inscription on the girdle.",
            True, True)


@router.callback_query(F.data.startswith("connect:"))
async def cb_connect(cb: CallbackQuery) -> None:
    listing_id = _cb_id(cb.data)
    if listing_id is None:
        await cb.answer()
        return
    text, ok, reachable = _reveal_text(listing_id)
    if not ok:
        await cb.answer(text, show_alert=True)
        return
    db.log_event("contact_revealed", cb.from_user.id, {"listing_id": listing_id, "seller_reachable": reachable})
    await cb.message.answer(text)
    await cb.answer()


@router.message(F.text.regexp(r"^/connect_\d+"))
async def connect_cmd(msg: Message) -> None:
    m = re.match(r"^/connect_(\d+)", msg.text or "")
    if not m:
        return
    listing_id = int(m.group(1))
    text, ok, reachable = _reveal_text(listing_id)
    if ok:
        db.log_event("contact_revealed", msg.from_user.id, {"listing_id": listing_id, "seller_reachable": reachable})
    await msg.answer(text)


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
            cap = settings.tiers[tier]["max_stock"]
            cap_str = "unlimited" if cap is None else f"{cap:,}"
            try:
                await bot.send_message(
                    tg_id, f"✅ <b>{settings.tiers[tier]['title']} is active — thank you.</b>\n"
                           f"Your stock cap is now <b>{cap_str}</b>. Forward or upload your stones and "
                           "I'll start matching buyers to them right away.")
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
