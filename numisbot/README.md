# Katz Coins Radar — Telegram-бот для нумизматики

Аукционный радар поверх [katzauction.com](https://katzauction.com) + витрина монет
с индустриальной верификацией сертификатов. Бот: [@KatzCoinsBot](https://t.me/KatzCoinsBot).

## Что умеет

**Навигация** — постоянные reply-кнопки внизу чата (аукционы, радар, поиск, цены,
витрина, продажа) + свободный текст: сообщение «рубль 1912» без команды — уже поиск.

| Функция | Что делает | Тариф |
|---|---|---|
| 🏛 `/auctions` | Текущие и ближайшие аукционы с кнопками | Free |
| 🔎 `/find` | Фото-карточки лотов с торгов, кнопки «Открыть ↗» / «➕ В радар» | Free |
| 🔭 `/watch запрос [<цена]` | Радар: алерт при появлении + за час до закрытия | Free 3 / Pro 25 / Sniper+ ∞ |
| 🎯 Снайпер-алерт | Дополнительный пинг за ~10 минут до закрытия | Sniper+ / Dealer |
| 📉 `/price` | Сводка проходов + **график** (бары, медиана) из локального архива | Free 5 строк / Pro всё |
| 🛒 `/market` | Витрина монет участников с бейджами верификации | Free |
| 📤 `/publish` | Публикация своей монеты: фото → описание → цена → **сертификат** | слоты 1/3/5/20 по тирам |
| 💼 `/sell` | Консигнация в Katz — лид с фото форвардится админам | Free |
| ⭐ `/pro` | Stars-подписки с автопродлением: Pro 299⭐ / Sniper+ 749⭐ / Dealer 1900⭐ | — |
| 📊 `/stats` | DAU/WAU/MAU, активация, конверсия, листинги (админ) | admin |

## Верификация сертификатов (индустриальный стандарт)

Цепочка доверия для `/publish`:
1. Формат номера валидируется по схемам грейдеров (PCGS 7–9 цифр, NGC/PMG `XXXXXXX-XXX`,
   только ASCII-цифры — гомоглифы отсекаются).
2. **PCGS** — автоматическая проверка через официальный [PCGS Public API](https://api.pcgs.com)
   (`PCGS_API_TOKEN`, бесплатный): имя монеты и грейд из реестра пишутся в карточку.
3. **NGC / PMG** — публичного API нет: карточка получает кнопку «🛡 Реестр грейдера ↗»
   на официальную страницу проверки + модерация админом в один тап (✅/❌).
4. Один сертификат = один активный листинг (анти-фрод), отклонённые листинги скрываются.

Статусы: `verified` ✅ · `linked` 🛡 · `pending` ⏳ · `mismatch` ⚠️ · `rejected`.

## Запуск

```bash
cp .env.example .env        # BOT_TOKEN, ADMIN_IDS (свой Telegram ID!), опц. PCGS_API_TOKEN
docker compose up -d --build
```

Без Docker: `pip install -r requirements.txt && python -m bot.main` (Python 3.11+).

Архив реализованных цен (для мгновенного `/price` и аналитики):
```bash
python -m scripts.backfill --last 12 --db data/archive.sqlite3   # ~40 мин, вежливо 1 rps
python -m scripts.backfill --all  --db data/archive.sqlite3      # весь архив ~520k лотов, на ночь
python -m scripts.analyze_archive --db data/archive.sqlite3      # JSON-аналитика спроса
```

**Токен в git не коммитим.** `.env` в `.gitignore`.

## Архитектура

```
bot/
  main.py            # polling, DI, регистрация команд RU/EN на старте
  config.py          # env-конфиг, слоты тиров
  db.py              # SQLite: users/watches/lots/listings/events (+ATTACH архива read-only,
                     #         unicode-aware поиск lower_u — кириллица регистронезависимо)
  texts.py           # все тексты RU/EN, карточки (HTML-safe), reply-кнопки
  keyboards.py       # inline + reply клавиатуры
  handlers/
    nav.py           # reply-кнопки = универсальный выход из любого FSM, /menu, /cancel
    start.py         # онбординг: язык → интересы → живые лоты по интересам
    auctions.py      # /auctions /find /price + кнопочные диалоги запроса
    watchlist.py     # радар: лимиты, дедуп, минимум 3 символа
    market.py        # /publish (4 шага, верификация) + /market (витрина, модерация)
    subscribe.py     # Stars-подписки (роутер ПЕРВЫЙ — successful_payment неприкосновенен)
    seller.py        # /sell → форвард лида с фото админам
    admin.py         # /stats (метрики), /broadcast, /refresh
    fallback.py      # свободный текст → поиск; устаревшие кнопки → вежливый ответ
  services/
    katz_parser.py   # вежливый клиент публичного API Katz (1 rps, ретраи)
    scheduler.py     # синк 30 мин + алерты (матч, 1ч, снайпер 10 мин) под локом
    certs.py         # верификация сертификатов NGC/PCGS/PMG
    charts.py        # PIL-графики цен в фирменном стиле
scripts/
  backfill.py        # выкачка архива (резюмируемая), analyze_archive.py — аналитика
tests/               # 197 pytest-тестов (без сети): парсер, БД, карточки, сертификаты
```

## Качество

- `pytest tests/ -q` → **197 passed**; тесты покрывают HTML-инъекции, лимиты Telegram
  (caption 1024, callback 64 байта), кириллицу, идемпотентность БД, анти-фрод сертификатов.
- Код прошёл три раунда агент-ревью (баги / Telegram-UX / тесты) — находки исправлены.

Аналитика рынка и стратегия — в [docs/REPORT.md](docs/REPORT.md) (+ PDF рядом).
