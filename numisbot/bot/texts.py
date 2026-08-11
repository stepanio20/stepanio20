"""All user-facing copy, RU + EN. Design language: dark-gold Katz palette,
coin iconography, compact cards. HTML parse mode everywhere."""
from __future__ import annotations

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
            "🪙 <b>Katz Coins Radar</b> — ваш радар на аукционах Katz\n"
            "━━━━━━━━━━━━━━━\n"
            "Тысячи лотов каждый месяц: монеты, банкноты, медали, ордена. "
            "Бот следит за ними за вас:\n\n"
            "🔔 <b>Алерты по ключевым словам</b> — «полтина 1859», «Nicholas II», «таульер»…\n"
            "⏰ <b>Напоминания</b> — лот из вотчлиста закрывается через час\n"
            "📉 <b>История цен</b> — за сколько такие лоты реально уходили\n"
            "💼 <b>Продавцам</b> — оценка и сдача монет на аукцион\n\n"
            "Что вам интереснее всего? (можно несколько)"
        ),
        "en": (
            "🪙 <b>Katz Coins Radar</b> — your radar for Katz auctions\n"
            "━━━━━━━━━━━━━━━\n"
            "Thousands of lots every month: coins, banknotes, medals, orders. "
            "The bot watches them for you:\n\n"
            "🔔 <b>Keyword alerts</b> — “poltina 1859”, “Nicholas II”, “thaler”…\n"
            "⏰ <b>Reminders</b> — your watched lot closes in an hour\n"
            "📉 <b>Price history</b> — what similar lots really sold for\n"
            "💼 <b>For sellers</b> — valuation & consignment to auction\n\n"
            "What are you into? (pick a few)"
        ),
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


def lot_card(lot, lang: str) -> str:
    """Compact lot card. `lot` is a sqlite Row or dict with lot fields."""
    g = lot["grade"] or ""
    parts_meta = " · ".join(x for x in [lot["country"] or "", str(lot["year"] or ""), lot["metal"] or "", g] if x)
    cur = lot["currency"] or "USD"
    price_bits = []
    if lot["current_bid"]:
        price_bits.append(("Ставка" if lang == "ru" else "Bid") + f": <b>{lot['current_bid']:.0f} {cur}</b>")
    elif lot["start_price"]:
        price_bits.append(("Старт" if lang == "ru" else "Start") + f": <b>{lot['start_price']:.0f} {cur}</b>")
    if lot["estimate"]:
        price_bits.append(("Эстимейт" if lang == "ru" else "Est.") + f": {lot['estimate']:.0f} {cur}")
    if lot["bids"]:
        price_bits.append(("ставок " if lang == "ru" else "bids ") + str(lot["bids"]))
    lines = [f"🪙 <b>{lot['title']}</b>"]
    if parts_meta:
        lines.append(f"<i>{parts_meta}</i>")
    if price_bits:
        lines.append(" · ".join(price_bits))
    if lot["url"]:
        lines.append(f'<a href="{lot["url"]}">' + ("Открыть лот ↗" if lang == "ru" else "Open lot ↗") + "</a>")
    return "\n".join(lines)


def realized_line(lot, lang: str) -> str:
    cur = lot["currency"] or "USD"
    return f"• {lot['title']} — <b>{lot['realized']:.0f} {cur}</b>"
