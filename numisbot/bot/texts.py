"""All user-facing copy, RU + EN. Design language: Telegram-native cards —
photo-first, short lines, buttons instead of raw links. HTML parse mode
everywhere, so every dynamic value goes through esc()."""
from __future__ import annotations

import datetime as dt
from html import escape as esc

INTERESTS = {
    "ru_imperial": {"ru": "🇷🇺 Россия и Империя", "en": "🇷🇺 Russia & Empire"},
    "world": {"ru": "🌍 Монеты мира", "en": "🌍 World coins"},
    "ancient": {"ru": "🏛 Античность", "en": "🏛 Ancient"},
    "banknotes": {"ru": "💵 Банкноты", "en": "💵 Banknotes"},
    "medals": {"ru": "🎖 Медали и ордена", "en": "🎖 Medals & orders"},
    "gold": {"ru": "🥇 Золото / инвест", "en": "🥇 Gold / bullion"},
}

T = {
    "choose_lang": {
        "ru": "🪙 <b>Katz Coins Radar</b>\n\nВыберите язык / Choose language",
        "en": "🪙 <b>Katz Coins Radar</b>\n\nChoose language / Выберите язык",
    },
    "welcome": {
        "ru": (
            "🪙 <b>Katz Coins Radar</b>\n\n"
            "Слежу за аукционами Katz вместо вас:\n\n"
            "🔔 поймаю лот по вашим словам — «полтина 1859», «Nicholas II»\n"
            "⏰ напомню за час до закрытия\n"
            "📉 покажу, за сколько такое реально уходило\n"
            "💼 помогу продать через Katz\n\n"
            "<b>Что собираете?</b> Можно выбрать несколько:"
        ),
        "en": (
            "🪙 <b>Katz Coins Radar</b>\n\n"
            "I watch Katz auctions for you:\n\n"
            "🔔 catch lots by your keywords — “poltina 1859”, “Nicholas II”\n"
            "⏰ remind you an hour before closing\n"
            "📉 show what similar lots really sold for\n"
            "💼 help you sell via Katz\n\n"
            "<b>What do you collect?</b> Pick a few:"
        ),
    },
    "onboarded_hits": {
        "ru": "🎯 В текущих торгах Katz — <b>{n}</b> лотов по вашим интересам. Вот несколько:",
        "en": "🎯 Live Katz auctions have <b>{n}</b> lots matching your interests. A few of them:",
    },
    "onboarded": {
        "ru": (
            "Отлично! 🎯 Интересы сохранены.\n\n"
            "Начните с малого: добавьте первое отслеживание —\n"
            "<code>/watch рубль 1912</code>\n\n"
            "или посмотрите, что сейчас на торгах: /auctions"
        ),
        "en": (
            "Done! 🎯 Interests saved.\n\n"
            "Start small: add your first watch —\n"
            "<code>/watch rouble 1912</code>\n\n"
            "or see what's on sale now: /auctions"
        ),
    },
    "menu": {
        "ru": "🪙 <b>Меню</b>\n━━━━━━━━━━━━━━━\nВыберите раздел:",
        "en": "🪙 <b>Menu</b>\n━━━━━━━━━━━━━━━\nPick a section:",
    },
    "auctions_header": {
        "ru": "🏛 <b>Аукционы Katz — сейчас и скоро</b>\n━━━━━━━━━━━━━━━",
        "en": "🏛 <b>Katz auctions — live & upcoming</b>\n━━━━━━━━━━━━━━━",
    },
    "no_auctions": {
        "ru": "Пока данных об аукционах нет — парсер обновит их в ближайшие минуты. Загляните чуть позже 🙌",
        "en": "No auction data yet — the parser refreshes within minutes. Check back soon 🙌",
    },
    "watch_usage": {
        "ru": (
            "🔭 <b>Как добавить отслеживание</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "<code>/watch полтина 1859</code>\n"
            "<code>/watch Nicholas II gold &lt;500</code> — с потолком цены\n\n"
            "Как только на Katz появится лот с этими словами — пришлю алерт. "
            "Также напомню за час до закрытия."
        ),
        "en": (
            "🔭 <b>How to add a watch</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "<code>/watch poltina 1859</code>\n"
            "<code>/watch Nicholas II gold &lt;500</code> — with a price cap\n\n"
            "The moment a matching lot appears at Katz you get an alert, "
            "plus a reminder one hour before closing."
        ),
    },
    "watch_added": {
        "ru": "✅ Отслеживание добавлено: <b>{q}</b>{cap}\nСлотов занято: {used}/{total}",
        "en": "✅ Watch added: <b>{q}</b>{cap}\nSlots used: {used}/{total}",
    },
    "watch_limit": {
        "ru": (
            "🚦 <b>Лимит бесплатного тарифа: {total} отслеживания</b>\n\n"
            "На Pro — до 50 отслеживаний, снайпер-алерты за 15 минут до конца "
            "и история цен без ограничений.\n\n👉 /pro"
        ),
        "en": (
            "🚦 <b>Free plan limit: {total} watches</b>\n\n"
            "Pro gives you up to 50 watches, sniper alerts 15 minutes before "
            "closing and unlimited price history.\n\n👉 /pro"
        ),
    },
    "watchlist_header": {
        "ru": "🔭 <b>Ваши отслеживания</b> ({used}/{total})\n━━━━━━━━━━━━━━━",
        "en": "🔭 <b>Your watches</b> ({used}/{total})\n━━━━━━━━━━━━━━━",
    },
    "watchlist_empty": {
        "ru": "Пока пусто. Добавьте первое: <code>/watch рубль 1912</code>",
        "en": "Empty so far. Add one: <code>/watch rouble 1912</code>",
    },
    "search_usage": {
        "ru": "🔎 Поиск по текущим торгам: <code>/find червонец</code>",
        "en": "🔎 Search live lots: <code>/find chervonets</code>",
    },
    "search_empty": {
        "ru": "По «{q}» на текущих торгах ничего нет. Добавить в радар, чтобы поймать появление? 👉 <code>/watch {q}</code>",
        "en": "Nothing live for “{q}”. Add it to your radar to catch new listings 👉 <code>/watch {q}</code>",
    },
    "history_usage": {
        "ru": "📉 История цен: <code>/price рубль Петр</code> — покажу, за сколько уходили похожие лоты в архиве Katz.",
        "en": "📉 Price history: <code>/price rouble Peter</code> — realized prices for similar lots in the Katz archive.",
    },
    "history_free_teaser": {
        "ru": "\n🔒 Показал {shown} из {found}. Полная история и экспорт — в Pro: /pro",
        "en": "\n🔒 Showing {shown} of {found}. Full history & export — in Pro: /pro",
    },
    "alert_match": {
        "ru": "🎯 <b>Совпадение по радару «{q}»</b>",
        "en": "🎯 <b>Radar match for “{q}”</b>",
    },
    "alert_closing": {
        "ru": "⏰ <b>Через ~1 час закрывается лот из вашего радара</b>",
        "en": "⏰ <b>A lot on your radar closes in ~1 hour</b>",
    },
    "pro_pitch": {
        "ru": (
            "⭐ <b>Pro</b> — для коллекционера\n"
            "🔔 25 отслеживаний (вместо 3) · напоминания 24ч/1ч\n"
            "📉 Полная история реализованных цен\n"
            "📬 Дайджест каждого нового аукциона\n\n"
            "🎯 <b>Sniper+</b> — для охотника за лотами\n"
            "Всё из Pro, плюс:\n"
            "♾ Безлимит отслеживаний · алерт за 10 мин до закрытия\n"
            "📢 Алерт «лот ушёл ниже эстимейта» + фид непроданных\n\n"
            "💼 <b>Dealer</b> — для продавца и дилера\n"
            "Всё из Sniper+, плюс:\n"
            "📊 Аналитика спроса: что ищут покупатели прямо сейчас\n"
            "🏷 Оценка ваших монет по базе прошедших продаж\n"
            "🤝 Приоритетная сдача лотов на аукцион Katz\n\n"
            "Оплата в Telegram Stars, продлевается автоматически, отмена в один тап."
        ),
        "en": (
            "⭐ <b>Pro</b> — for collectors\n"
            "🔔 25 watches (vs 3) · 24h/1h reminders\n"
            "📉 Full realized-price history\n"
            "📬 Digest of every new auction\n\n"
            "🎯 <b>Sniper+</b> — for lot hunters\n"
            "Everything in Pro, plus:\n"
            "♾ Unlimited watches · alert 10 min before closing\n"
            "📢 “Sold below estimate” alerts + unsold feed\n\n"
            "💼 <b>Dealer</b> — for sellers & dealers\n"
            "Everything in Sniper+, plus:\n"
            "📊 Demand analytics: what buyers search right now\n"
            "🏷 Valuation of your coins vs realized prices\n"
            "🤝 Priority consignment to Katz auctions\n\n"
            "Paid in Telegram Stars, auto-renews, cancel anytime."
        ),
    },
    "invoice_title_pro": {"ru": "Katz Radar Pro — месяц", "en": "Katz Radar Pro — 1 month"},
    "invoice_title_sniper": {"ru": "Katz Radar Sniper+ — месяц", "en": "Katz Radar Sniper+ — 1 month"},
    "invoice_title_dealer": {"ru": "Katz Radar Dealer — месяц", "en": "Katz Radar Dealer — 1 month"},
    "invoice_desc": {
        "ru": "Подписка продлевается автоматически каждые 30 дней. Отмена — в настройках Telegram.",
        "en": "Auto-renews every 30 days. Cancel in Telegram settings anytime.",
    },
    "paid": {
        "ru": "🎉 Оплата получена! Тариф <b>{tier}</b> активен до {until}.\nДобавьте отслеживания: /watch",
        "en": "🎉 Payment received! <b>{tier}</b> active until {until}.\nAdd watches: /watch",
    },
    "sell_pitch": {
        "ru": (
            "💼 <b>Продать через Katz Auction</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Katz продаёт тысячи лотов ежемесячно покупателям из 100+ стран.\n\n"
            "Опишите одним сообщением, что хотите продать (страна, номинал, "
            "год, состояние — можно приложить фото), и оставьте контакт. "
            "Команда Katz свяжется с оценкой.\n\n"
            "Напишите описание ⬇️"
        ),
        "en": (
            "💼 <b>Sell via Katz Auction</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Katz sells thousands of lots monthly to buyers in 100+ countries.\n\n"
            "Describe what you want to sell in one message (country, denomination, "
            "year, condition — photos welcome) and leave a contact. "
            "The Katz team will get back with a valuation.\n\n"
            "Type your description ⬇️"
        ),
    },
    "sell_thanks": {
        "ru": "🤝 Принято! Заявка №{lead_id} передана команде Katz. Обычно отвечают в течение 1–2 рабочих дней.",
        "en": "🤝 Got it! Request #{lead_id} sent to the Katz team. They usually reply within 1–2 business days.",
    },
    "help": {
        "ru": (
            "🪙 <b>Команды</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "/auctions — текущие и ближайшие аукционы\n"
            "/find — поиск по лотам на торгах\n"
            "/watch — добавить отслеживание\n"
            "/watchlist — мои отслеживания\n"
            "/price — история реализованных цен\n"
            "/sell — продать через Katz\n"
            "/pro — тарифы Pro и Dealer\n"
            "/lang — язык · /help — это меню"
        ),
        "en": (
            "🪙 <b>Commands</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "/auctions — live & upcoming auctions\n"
            "/find — search lots on sale\n"
            "/watch — add a watch\n"
            "/watchlist — my watches\n"
            "/price — realized price history\n"
            "/sell — consign via Katz\n"
            "/pro — Pro & Dealer plans\n"
            "/lang — language · /help — this menu"
        ),
    },
}


def t(key: str, lang: str) -> str:
    entry = T[key]
    return entry.get(lang, entry["ru"])


def photo_url(lot) -> str | None:
    """Bunny CDN resizes on the fly; ask for a Telegram-friendly width."""
    img = lot["image"]
    if not img:
        return None
    return img + ("&" if "?" in img else "?") + "width=700"


def category_icon(category: str | None) -> str:
    c = (category or "").lower()
    if c.startswith("banknote") or "paper" in c:
        return "💵"
    if c.startswith("phaleristic"):
        return "🎖"
    return "🪙"


def _money(v: float | None, cur: str) -> str:
    if v is None:
        return ""
    sym = "€" if cur == "EUR" else cur + " "
    return f"{sym}{v:,.0f}".replace(",", " ")


def _fmt_ends(ts: int | None, lang: str) -> str:
    if not ts:
        return ""
    d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    return d.strftime("%d.%m %H:%M UTC")


def lot_card(lot, lang: str) -> str:
    """Telegram-native lot card: short lines, fits a photo caption (<=1024).

    `lot` is a sqlite Row or dict with lot fields; all text is HTML-escaped.
    """
    ru = lang == "ru"
    cur = lot["currency"] or "EUR"
    icon = category_icon(lot["category"] if "category" in lot.keys() else None)
    meta = " · ".join(
        esc(str(x)) for x in [lot["country"], lot["year"], lot["metal"], lot["grade"]] if x
    )
    lines = [f"{icon} <b>{esc(lot['title'])}</b>"]
    if meta:
        lines.append(f"<i>{meta}</i>")
    lines.append("")
    if lot["realized"] is not None:
        lines.append(("✅ Продан за <b>{p}</b>" if ru else "✅ Sold for <b>{p}</b>")
                     .format(p=_money(lot["realized"], cur)))
    else:
        bid = lot["current_bid"]
        if bid:
            lines.append(("💶 Ставка: <b>{p}</b>" if ru else "💶 Bid: <b>{p}</b>")
                         .format(p=_money(bid, cur)))
        elif lot["start_price"]:
            lines.append(("💶 Старт: <b>{p}</b>" if ru else "💶 Start: <b>{p}</b>")
                         .format(p=_money(lot["start_price"], cur)))
        ends = _fmt_ends(lot["ends"], lang)
        if ends:
            lines.append(("⏳ Закрытие: {e}" if ru else "⏳ Closes: {e}").format(e=ends))
    return "\n".join(lines)


def realized_line(lot, lang: str) -> str:
    cur = lot["currency"] or "EUR"
    title = esc(str(lot["title"])[:70])
    return f"▫️ {title} — <b>{_money(lot['realized'], cur)}</b>"


def price_summary(query: str, rows, lang: str, shown: int, locked: int) -> str:
    """Header + stats + list for /price. Fits a photo caption when trimmed."""
    ru = lang == "ru"
    prices = sorted(r["realized"] for r in rows)
    med = prices[len(prices) // 2]
    head = (f"📉 <b>«{esc(query)}» на аукционах Katz</b>" if ru
            else f"📉 <b>“{esc(query)}” at Katz auctions</b>")
    stats = (
        f"Продано: <b>{len(rows)}</b> · медиана <b>{_money(med, 'EUR')}</b> · "
        f"{_money(prices[0], 'EUR')}–{_money(prices[-1], 'EUR')}"
        if ru else
        f"Sold: <b>{len(rows)}</b> · median <b>{_money(med, 'EUR')}</b> · "
        f"{_money(prices[0], 'EUR')}–{_money(prices[-1], 'EUR')}"
    )
    body = "\n".join(realized_line(r, lang) for r in rows[:shown])
    tail = ""
    if locked > 0:
        tail = ("\n\n🔒 Ещё {n} проходов — в Pro: /pro" if ru
                else "\n\n🔒 {n} more results — in Pro: /pro").format(n=locked)
    return f"{head}\n{stats}\n\n{body}{tail}"
