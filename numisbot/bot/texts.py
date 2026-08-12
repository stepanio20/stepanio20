"""All user-facing copy, RU + EN. Design language: Telegram-native cards —
photo-first, short lines, buttons instead of raw links. HTML parse mode
everywhere, so every dynamic value goes through esc()."""
from __future__ import annotations

import datetime as dt
from html import escape as esc

# reply-keyboard button labels (exact-match routed in handlers/nav.py)
BTN = {
    "ru": {
        "auctions": "🏛 Аукционы", "watchlist": "🔭 Мой радар",
        "find": "🔎 Найти лот", "price": "📉 Цены проходов",
        "market": "🛒 Витрина", "publish": "📤 Продать монету",
        "sell": "💼 На аукцион Katz", "pro": "⭐ Pro",
    },
    "en": {
        "auctions": "🏛 Auctions", "watchlist": "🔭 My radar",
        "find": "🔎 Find a lot", "price": "📉 Sold prices",
        "market": "🛒 Showcase", "publish": "📤 Sell a coin",
        "sell": "💼 Consign to Katz", "pro": "⭐ Pro",
    },
}

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
        "ru": (
            "🪙 <b>Katz Coins Radar</b>\n\n"
            "Ловлю лоты по вашим запросам, напоминаю о закрытии торгов, "
            "показываю цены прошлых продаж и витрину монет участников.\n\n"
            "Жмите кнопки внизу 👇"
        ),
        "en": (
            "🪙 <b>Katz Coins Radar</b>\n\n"
            "I catch lots by your queries, remind you before closings, "
            "show realized prices and the members' coin showcase.\n\n"
            "Use the buttons below 👇"
        ),
    },
    "welcome_back": {
        "ru": "🪙 С возвращением! Что посмотрим?",
        "en": "🪙 Welcome back! What shall we look at?",
    },
    "ask_find_query": {
        "ru": "🔎 Что ищем на торгах? Напишите одним сообщением — например: <code>талер 1780</code> или <code>Nicholas II gold</code>",
        "en": "🔎 What are we hunting? Type it in one message — e.g. <code>thaler 1780</code> or <code>Nicholas II gold</code>",
    },
    "ask_price_query": {
        "ru": "📉 По какой монете показать цены продаж? Например: <code>полтина 1859</code>",
        "en": "📉 Which coin's sold prices? E.g. <code>poltina 1859</code>",
    },
    "price_empty": {
        "ru": ("📉 В архиве Katz нет продаж по «{q}».\n"
               "Попробуйте короче — тип и год: <code>/price рубль 1912</code>\n"
               "Или поставьте радар: <code>/watch {q}</code> — пришлю, как только лот появится."),
        "en": ("📉 No Katz sales found for “{q}”.\n"
               "Try shorter — type and year: <code>/price rouble 1912</code>\n"
               "Or set a radar: <code>/watch {q}</code> — I'll ping you when one appears."),
    },
    "cancelled": {
        "ru": "✖️ Отменено. Возвращаю в меню 👇",
        "en": "✖️ Cancelled. Back to the menu 👇",
    },
    "stale_button": {
        "ru": "Кнопка устарела — откройте /menu",
        "en": "This button expired — open /menu",
    },
    "already_watching": {
        "ru": "Уже в радаре ✅",
        "en": "Already on your radar ✅",
    },
    "watch_too_short": {
        "ru": ("Запрос слишком короткий — нужно от 3 символов, иначе алерты придут "
               "почти на каждый лот. Пример: <code>/watch полтина 1859</code>"),
        "en": ("Query too short — 3+ characters needed, otherwise you'd get alerts "
               "for nearly every lot. Example: <code>/watch poltina 1859</code>"),
    },
    "photo_added": {
        "ru": "📷 Фото {n}/5 добавлено.",
        "en": "📷 Photo {n}/5 added.",
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
            "🚦 <b>Все {total} слота радара заняты</b>\n\n"
            "⭐ Pro — 25 отслеживаний и напоминания 24 ч / 1 ч\n"
            "🎯 Sniper+ — безлимит и алерт за 10 минут до закрытия\n\n"
            "👉 /pro · освободить слот: /watchlist"
        ),
        "en": (
            "🚦 <b>All {total} radar slots are in use</b>\n\n"
            "⭐ Pro — 25 watches plus 24h / 1h reminders\n"
            "🎯 Sniper+ — unlimited watches and a 10-minute closing alert\n\n"
            "👉 /pro · free a slot: /watchlist"
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
    "alert_closing10": {
        "ru": "🎯 <b>Снайпер-алерт: ~10 минут до закрытия!</b>",
        "en": "🎯 <b>Sniper alert: ~10 minutes to close!</b>",
    },
    "pro_pitch": {
        "ru": (
            "⭐ <b>Pro</b> — для коллекционера\n"
            "🔔 25 отслеживаний (вместо 3) · напоминания 24 ч / 1 ч\n"
            "📉 Полная история цен с графиком (Free — 5 строк)\n"
            "🛒 3 монеты в витрине (вместо 1)\n\n"
            "🎯 <b>Sniper+</b> — для охотника за лотами\n"
            "Всё из Pro, плюс:\n"
            "♾ Безлимит отслеживаний · алерт за 10 мин до закрытия\n"
            "🛒 5 монет в витрине · приоритет в поддержке\n\n"
            "💼 <b>Dealer</b> — для продавца и дилера\n"
            "Всё из Sniper+, плюс:\n"
            "🛒 До 20 монет в витрине с бейджем дилера\n"
            "🤝 Приоритетная сдача лотов на аукцион Katz\n"
            "📊 Аналитика спроса — скоро, для Dealer бесплатно\n\n"
            "Оплата в Telegram Stars, продлевается автоматически, отмена в один тап."
        ),
        "en": (
            "⭐ <b>Pro</b> — for collectors\n"
            "🔔 25 watches (vs 3) · 24h / 1h reminders\n"
            "📉 Full price history with chart (Free — 5 rows)\n"
            "🛒 3 showcase listings (vs 1)\n\n"
            "🎯 <b>Sniper+</b> — for lot hunters\n"
            "Everything in Pro, plus:\n"
            "♾ Unlimited watches · 10-min closing alert\n"
            "🛒 5 showcase listings · priority support\n\n"
            "💼 <b>Dealer</b> — for sellers & dealers\n"
            "Everything in Sniper+, plus:\n"
            "🛒 Up to 20 showcase listings with a dealer badge\n"
            "🤝 Priority consignment to Katz auctions\n"
            "📊 Demand analytics — coming soon, free for Dealer\n\n"
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
            "год, состояние — можно приложить фото). "
            "Команда Katz свяжется с оценкой.\n\n"
            "Опишите монету одним сообщением ⬇️\n"
            "Передумали — жмите «Отмена» или /cancel."
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
    "estimate_start": {
        "ru": ("🏷 <b>Оценка по базе проходов Katz</b>\n\n"
               "Опишите монету одним сообщением: страна, номинал, год, "
               "особенности (можно приложить фото для заявки продавцу).\n"
               "Пример: <code>Россия полтина 1859 Александр II</code>"),
        "en": ("🏷 <b>Valuation from the Katz sales archive</b>\n\n"
               "Describe the coin in one message: country, denomination, year, "
               "specifics (a photo is welcome for a seller lead).\n"
               "Example: <code>Russia poltina 1859 Alexander II</code>"),
    },
    "estimate_result": {
        "ru": ("🏷 <b>Оценка по {n} реальным продажам Katz</b>\n"
               "Диапазон (типичный): <b>{p25}–{p75}</b>\n"
               "Медиана: <b>{med}</b> · весь разброс {lo}–{hi}\n"
               "<i>По словам: {words}</i>\n\n"
               "Похожие проходы:\n{comps}\n\n"
               "💼 Хотите продать? /sell — сдать на аукцион Katz\n"
               "🛒 Или в витрину: /publish"),
        "en": ("🏷 <b>Estimate from {n} real Katz sales</b>\n"
               "Typical range: <b>{p25}–{p75}</b>\n"
               "Median: <b>{med}</b> · full spread {lo}–{hi}\n"
               "<i>Matched on: {words}</i>\n\n"
               "Similar results:\n{comps}\n\n"
               "💼 Want to sell? /sell — consign to Katz\n"
               "🛒 Or list it: /publish"),
    },
    "estimate_none": {
        "ru": ("По этому описанию в архиве Katz аналогов не нашлось. "
               "Попробуйте иначе: страна + номинал + год, без лишних слов. "
               "Или отправьте на живую оценку команде: /sell"),
        "en": ("No comparables in the Katz archive for that description. "
               "Try country + denomination + year, no extra words. "
               "Or send it to the team for a live valuation: /sell"),
    },
    "estimate_quota": {
        "ru": ("🚦 Лимит оценок на вашем тарифе исчерпан ({used}/{quota} за 30 дней).\n"
               "⭐ Pro — 5/мес · 🎯 Sniper+ — 15 · 💼 Dealer — 30 👉 /pro"),
        "en": ("🚦 Valuation limit reached ({used}/{quota} per 30 days).\n"
               "⭐ Pro — 5/mo · 🎯 Sniper+ — 15 · 💼 Dealer — 30 👉 /pro"),
    },
    "pf_header": {
        "ru": "🧺 <b>Портфель коллекции</b> ({n} поз.)\nОценка по свежим проходам Katz:",
        "en": "🧺 <b>Collection portfolio</b> ({n} items)\nValued against fresh Katz results:",
    },
    "pf_empty": {
        "ru": ("🧺 Портфель пуст. Добавьте первую монету — и я буду переоценивать "
               "её по каждым свежим торгам Katz."),
        "en": ("🧺 Portfolio is empty. Add your first coin — I'll revalue it "
               "against every fresh Katz sale."),
    },
    "pf_total": {
        "ru": "\nИтого оценка: <b>{lo}–{hi}</b> (медианы: {med}){vs}",
        "en": "\nTotal estimate: <b>{lo}–{hi}</b> (medians: {med}){vs}",
    },
    "pf_vs_buy": {
        "ru": " · вложено {buy}",
        "en": " · invested {buy}",
    },
    "pf_add_ask": {
        "ru": ("Опишите монету (страна, номинал, год). Если хотите — добавьте цену "
               "покупки в конце: <code>… за 250</code>"),
        "en": ("Describe the coin (country, denomination, year). Optionally append "
               "the buy price: <code>… for 250</code>"),
    },
    "pf_added": {
        "ru": "✅ Добавлено в портфель: <b>{title}</b>{buy}",
        "en": "✅ Added to portfolio: <b>{title}</b>{buy}",
    },
    "pf_limit": {
        "ru": "🚦 Лимит позиций портфеля на вашем тарифе: {limit}. Больше — в Pro: /pro",
        "en": "🚦 Portfolio limit on your plan: {limit}. More — in Pro: /pro",
    },
    "trial_granted": {
        "ru": ("🎁 <b>7 дней Pro — в подарок за знакомство!</b>\n"
               "25 слотов радара и полная история цен уже включены. "
               "Понравится — /pro продлит за 299 ⭐/мес."),
        "en": ("🎁 <b>7 days of Pro — welcome gift!</b>\n"
               "25 radar slots and full price history are now on. "
               "Like it? /pro extends for 299 ⭐/mo."),
    },
    "referral_reward": {
        "ru": "🎉 Ваш друг активировал радар — вам начислено <b>+30 дней Pro</b>! Приглашайте ещё: /invite",
        "en": "🎉 Your friend activated their radar — you got <b>+30 days of Pro</b>! Invite more: /invite",
    },
    "invite": {
        "ru": ("🎁 <b>Месяц Pro за друга</b>\n\n"
               "Ваша ссылка:\n{link}\n\n"
               "Когда друг запустит бота и поставит первое отслеживание — "
               "вам автоматически прилетит +30 дней Pro (до 6 наград в год)."),
        "en": ("🎁 <b>A month of Pro per friend</b>\n\n"
               "Your link:\n{link}\n\n"
               "When a friend starts the bot and sets their first watch, "
               "you automatically get +30 days of Pro (up to 6 rewards a year)."),
    },
    "new_auction": {
        "ru": "🏛 <b>Новый аукцион на Katz!</b>\n{title}\n{lots} лотов · старт торгов: {when}",
        "en": "🏛 <b>New Katz auction!</b>\n{title}\n{lots} lots · starts: {when}",
    },
    "new_auction_hits": {
        "ru": "\n🎯 По вашим интересам — <b>{n}</b> лотов",
        "en": "\n🎯 Matching your interests — <b>{n}</b> lots",
    },
    "digest_header": {
        "ru": "📬 <b>Дайджест недели</b>\nСамые горячие лоты на торгах прямо сейчас:",
        "en": "📬 <b>Weekly digest</b>\nHottest lots on sale right now:",
    },
    "digest_off": {
        "ru": "🔕 Дайджесты и анонсы отключены. Включить обратно: /digest",
        "en": "🔕 Digests and announcements are off. Turn back on: /digest",
    },
    "digest_on": {
        "ru": "🔔 Дайджесты и анонсы включены. Отключить: /digest",
        "en": "🔔 Digests and announcements are on. Turn off: /digest",
    },
    "publish_start": {
        "ru": (
            "📸 <b>Публикация монеты — шаг 1 из 4</b>\n\n"
            "Пришлите фото монеты (аверс; можно добавить ещё до 5 фото на следующем шаге).\n\n"
            "<i>Хорошее фото = быстрая продажа: дневной свет, тёмный фон, обе стороны.</i>"
        ),
        "en": (
            "📸 <b>List your coin — step 1 of 4</b>\n\n"
            "Send a photo of the coin (obverse; you can add up to 5 photos at the next step).\n\n"
            "<i>Good photos sell faster: daylight, dark background, both sides.</i>"
        ),
    },
    "publish_photo_ok": {
        "ru": ("✅ Фото получено.\n\n<b>Шаг 2 из 4.</b> Теперь опишите монету одним сообщением: "
               "страна, номинал, год, металл, состояние/грейд. Можно докинуть ещё фото."),
        "en": ("✅ Photo received.\n\n<b>Step 2 of 4.</b> Now describe the coin in one message: "
               "country, denomination, year, metal, condition/grade. You may add more photos."),
    },
    "publish_need_photo": {
        "ru": "Нужно фото 📷 — пришлите изображение монеты (или /menu для отмены).",
        "en": "A photo is required 📷 — send an image of the coin (or /menu to cancel).",
    },
    "publish_desc_short": {
        "ru": "Слишком коротко. Опишите подробнее: страна, номинал, год, металл, состояние.",
        "en": "Too short. More detail please: country, denomination, year, metal, condition.",
    },
    "publish_price_ask": {
        "ru": "<b>Шаг 3 из 4.</b> Какая цена в EUR? Напишите число — или жмите «Открыт к предложениям».",
        "en": "<b>Step 3 of 4.</b> Asking price in EUR? Type a number — or tap “Open to offers”.",
    },
    "publish_price_bad": {
        "ru": "Не понял цену. Напишите число (например <code>150</code>) или жмите кнопку.",
        "en": "Couldn't parse that. Type a number (e.g. <code>150</code>) or tap the button.",
    },
    "publish_cert_ask": {
        "ru": (
            "<b>Шаг 4 из 4 — верификация.</b>\n\n"
            "Если монета в слабе NGC / PCGS / PMG — пришлите номер сертификата, например:\n"
            "<code>PCGS 45689164</code> или <code>NGC 6805461-001</code>\n\n"
            "🛡 Проверяем по официальному реестру грейдера: PCGS — автоматически через "
            "PCGS Public API, NGC/PMG — по публичной странице проверки + модерация. "
            "Листинги с подтверждённым сертификатом получают бейдж ✅ и доверие покупателей."
        ),
        "en": (
            "<b>Step 4 of 4 — verification.</b>\n\n"
            "If the coin is slabbed by NGC / PCGS / PMG — send the cert number, e.g.:\n"
            "<code>PCGS 45689164</code> or <code>NGC 6805461-001</code>\n\n"
            "🛡 We check the grader's official registry: PCGS — automatically via the "
            "PCGS Public API, NGC/PMG — via the public cert-lookup page + moderation. "
            "Listings with a confirmed cert get a ✅ badge and buyer trust."
        ),
    },
    "publish_cert_bad": {
        "ru": ("Не похоже на номер сертификата. Формат: <code>PCGS 45689164</code>, "
               "<code>NGC 6805461-001</code>, <code>PMG 1234567-001</code> — или «Без сертификата»."),
        "en": ("That doesn't look like a cert number. Format: <code>PCGS 45689164</code>, "
               "<code>NGC 6805461-001</code>, <code>PMG 1234567-001</code> — or “No certificate”."),
    },
    "publish_cert_dup": {
        "ru": "⚠️ Этот сертификат уже привязан к активному листингу. Один слаб — один листинг.",
        "en": "⚠️ This certificate already backs an active listing. One slab — one listing.",
    },
    "publish_limit": {
        "ru": "🚦 Лимит активных листингов на вашем тарифе: {limit}. Больше слотов — в Pro/Dealer: /pro",
        "en": "🚦 Active-listing limit on your plan: {limit}. More slots — Pro/Dealer: /pro",
    },
    "publish_done": {
        "ru": ("🎉 <b>Листинг #{id} опубликован!</b>\n"
               "Он появился в витрине /market и уйдёт в еженедельный дайджест. "
               "Продали? Отметьте кнопкой под карточкой."),
        "en": ("🎉 <b>Listing #{id} is live!</b>\n"
               "It's now in /market and goes into the weekly digest. "
               "Sold it? Mark it with the button under the card."),
    },
    "market_header": {
        "ru": "🛒 <b>Витрина коллекционеров</b>\nСвежие монеты от участников — с проверкой сертификатов:",
        "en": "🛒 <b>Collectors' showcase</b>\nFresh coins from members — certs verified:",
    },
    "market_empty": {
        "ru": "Витрина пока пуста. Станьте первым: /publish 🪙",
        "en": "The showcase is empty so far. Be the first: /publish 🪙",
    },
    "market_more": {"ru": "Показать ещё?", "en": "Show more?"},
    "help": {
        "ru": (
            "🪙 <b>Команды</b>\n\n"
            "/auctions — текущие и ближайшие аукционы\n"
            "/find — поиск по лотам на торгах\n"
            "/watch — добавить отслеживание\n"
            "/watchlist — мой радар\n"
            "/price — цены: за сколько уходило + график\n"
            "/market — витрина монет участников\n"
            "/publish — разместить свою монету (c проверкой сертификата)\n"
            "/sell — сдать на аукцион Katz\n"
            "/estimate — оценка монеты по базе проходов\n"
            "/portfolio — портфель коллекции с переоценкой\n"
            "/invite — месяц Pro за друга\n"
            "/digest — вкл/выкл дайджесты\n"
            "/pro — тарифы · /lang — язык"
        ),
        "en": (
            "🪙 <b>Commands</b>\n\n"
            "/auctions — live & upcoming auctions\n"
            "/find — search lots on sale\n"
            "/watch — add a watch\n"
            "/watchlist — my radar\n"
            "/price — realized prices + chart\n"
            "/market — members' coin showcase\n"
            "/publish — list your coin (with cert verification)\n"
            "/sell — consign to Katz auctions\n"
            "/estimate — coin valuation from sales archive\n"
            "/portfolio — collection tracker with revaluation\n"
            "/invite — a month of Pro per friend\n"
            "/digest — toggle digests\n"
            "/pro — plans · /lang — language"
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


CERT_BADGES = {
    "verified": {"ru": "✅ Сертификат {svc} №{num} подтверждён", "en": "✅ {svc} cert #{num} verified"},
    "linked": {"ru": "🛡 {svc} №{num} — проверьте в реестре по кнопке", "en": "🛡 {svc} #{num} — check via the registry button"},
    "pending": {"ru": "⏳ {svc} №{num} — проверка сертификата идёт", "en": "⏳ {svc} #{num} — cert check in progress"},
    "mismatch": {"ru": "⚠️ {svc} №{num} не найден в реестре", "en": "⚠️ {svc} #{num} not found in the registry"},
}


def listing_card(listing, lang: str, with_description: bool = True) -> str:
    """Showcase card for a user-published coin. Fits a photo caption."""
    ru = lang == "ru"
    lines = [f"🪙 <b>{esc(listing['title'])}</b>"]
    desc = (listing["description"] or "").strip()
    if with_description and len(desc) > len(listing["title"]):
        extra = desc[len(listing["title"]):].strip(" .,\n")
        if extra:
            lines.append(f"<blockquote>{esc(extra[:250])}</blockquote>")
    price = listing["price"]
    lines.append(("💶 Цена: <b>{p}</b>" if ru else "💶 Price: <b>{p}</b>").format(
        p=_money(price, "EUR")) if price
        else ("💬 Открыт к предложениям" if ru else "💬 Open to offers"))
    if listing["cert_service"] and listing["cert_status"] in CERT_BADGES:
        badge = CERT_BADGES[listing["cert_status"]]
        line = badge.get(lang, badge["ru"]).format(
            svc=listing["cert_service"], num=esc(listing["cert_number"]))
        if listing["cert_status"] == "verified" and listing["cert_note"]:
            line += f"\n<i>{esc(listing['cert_note'][:120])}</i>"
        lines.append(line)
    elif not listing["cert_service"]:
        lines.append("◽️ Без сертификата (raw)" if ru else "◽️ No certificate (raw)")
    lines.append(("Продавец: {c}" if ru else "Seller: {c}").format(
        c=esc(listing["contact"] or "")))
    return "\n".join(lines)


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
