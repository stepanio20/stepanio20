# Katz Coins Radar — Telegram-бот для нумизматики

Аукционный радар поверх [katzauction.com](https://katzauction.com): алерты по ключевым
словам, напоминания о закрытии лотов, история реализованных цен, подписка через
Telegram Stars, лид-форма консигнации для продавцов.

Бот: [@KatzCoinsBot](https://t.me/KatzCoinsBot)

## Что умеет

| Команда | Что делает | Тариф |
|---|---|---|
| `/auctions` | Текущие и ближайшие аукционы Katz | Free |
| `/find <запрос>` | Поиск по лотам на торгах | Free |
| `/watch <запрос> [<цена]` | Радар: алерт при появлении лота + напоминание за час до закрытия | Free 3 слота / Pro 50 |
| `/price <запрос>` | История реализованных цен из архива | Free 3 строки / Pro всё |
| `/sell` | Заявка на продажу через Katz (лид уходит админам) | Free |
| `/pro` | Подписка Pro / Dealer через Telegram Stars (авто-продление 30 дней) | — |
| `/stats`, `/broadcast`, `/refresh` | Админка | admin |

## Запуск

```bash
cp .env.example .env        # вписать BOT_TOKEN и ADMIN_IDS
docker compose up -d --build
```

Без Docker: `pip install -r requirements.txt && python -m bot.main` (Python 3.11+).

**Токен в git не коммитим.** `.env` в `.gitignore`.

## Архитектура

```
bot/
  main.py            # polling, DI (db/cfg/scheduler в handlers)
  config.py          # env-конфиг
  db.py              # SQLite: users, watches, auctions, lots, alerts, leads, payments
  texts.py           # все тексты RU/EN + карточки лотов
  keyboards.py       # inline-клавиатуры
  handlers/          # start (онбординг), auctions, watchlist, subscribe (Stars), seller, admin
  services/
    katz_parser.py   # вежливый парсер katzauction.com (JSON-first, HTML-fallback)
    scheduler.py     # APScheduler: обновление каждые 30 мин, матчинг радара, closing-алерты
```

Парсер работает деликатно: последовательные запросы с паузой ≥1 сек, ограниченное
число страниц за цикл, браузерный UA с пометкой бота. Бот задуман как часть
воронки самого аукционного дома (рост ставок и лидов на консигнацию), а не как
внешний скрейпер.

## Монетизация (Telegram Stars, XTR)

- **Pro** — 299⭐/мес (~$5.99): 25 отслеживаний, напоминания 24ч/1ч, полная история цен.
- **Sniper+** — 749⭐/мес (~$14.99): безлимит, алерт за 10 мин до закрытия, «ушёл ниже эстимейта».
- **Dealer** — 1900⭐/мес (или €290/год инвойсом): + аналитика спроса, оценка монет, приоритетная консигнация.

Инвойсы шлются с `subscription_period=2592000` — Telegram сам продлевает подписку
ежемесячно; продление приходит как `successful_payment` с `is_recurring`.

Подробная аналитика рынка и стратегия — в [docs/REPORT.md](docs/REPORT.md).
