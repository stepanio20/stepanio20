# Деплой numisbot (Katz Coins Radar) на VPS

Целевая площадка: Hetzner CX22 (2 vCPU / 4 GB) или любой VPS с Ubuntu 24.04.
Бот работает по long polling — домен и открытые входящие порты **не нужны**.
Команды ниже — от root (либо с `sudo`).

Файлы пакета: `deploy/DEPLOY.md` (этот гайд), `deploy/numisbot.service` (systemd),
`deploy/backup.sh` (бэкап БД), `deploy/healthcheck.sh` (мониторинг).

## 1. Docker + compose plugin

```bash
apt-get update && apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
docker --version && docker compose version   # проверка
```

## 2. Клонирование репозитория

Бот лежит в подкаталоге `numisbot` монорепо:

```bash
git clone https://github.com/stepanio20/stepanio20.git /opt/stepanio20
cd /opt/stepanio20/numisbot
```

## 3. Конфиг `.env`

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Обязательно:

- `BOT_TOKEN` — у **@BotFather**: `/newbot` (или `/mybots` → бот → *API Token*).
- `ADMIN_IDS` — ваш Telegram ID: напишите любое сообщение боту **@userinfobot**,
  в ответе будет `Id: 123456789` — это он. Несколько админов — через запятую:
  `ADMIN_IDS=123456789,987654321`.

Опционально:

- `PCGS_API_TOKEN` — бесплатно на <https://www.pcgs.com/publicapi>; без него
  PCGS-сертификаты в `/publish` уходят на ручную модерацию.

## 4. Первый запуск

```bash
docker compose up -d --build
docker compose ps                    # ждём STATUS: Up ... (healthy)
docker compose logs -f --tail 50     # Ctrl+C — выйти из логов
```

Проверка: бот отвечает на `/start` в Telegram.

## 5. Ночная полная выкачка архива цен (~520k лотов, вежливо 1 rps)

Вариант A — фоном внутри работающего контейнера:

```bash
docker compose exec -d numisbot sh -c \
  'nohup python -m scripts.backfill --all --db data/archive.sqlite3 >> data/backfill.log 2>&1'
tail -f data/backfill.log            # прогресс; файл виден на хосте в ./data
```

Вариант B — отдельным одноразовым контейнером (не зависит от рестартов основного):

```bash
docker compose run -d --rm --no-deps numisbot \
  python -m scripts.backfill --all --db data/archive.sqlite3
docker ps | grep numisbot-run        # имя контейнера → docker logs -f <имя>
```

Скрипт резюмируемый: оборвался — запустите ту же команду снова, уже сохранённые
аукционы пропустятся. Быстрый старт вместо `--all`: `--last 12` (~40 минут).

## 6. Логи

```bash
docker compose logs -f --tail 200
docker compose logs --since 1h | grep ERROR
```

Ротация уже настроена в `docker-compose.yml`: json-file, 3 файла по 10 МБ.

## 7. Обновление

```bash
cd /opt/stepanio20/numisbot
git pull
docker compose up -d --build
docker image prune -f
```

БД лежит в `./data` (том) и переживает пересборку контейнера.

## 8. Бэкап `data/`

`deploy/backup.sh` пакует `data/*.sqlite3` в `backups/numisbot-data-<дата>.tar.gz`
и хранит последние 14 архивов. Для консистентного снимка живой БД поставьте
`sqlite3` (`apt-get install -y sqlite3`) — скрипт использует его автоматически.

```bash
/opt/stepanio20/numisbot/deploy/backup.sh    # ручной прогон
crontab -e                                   # ежедневно в 03:20
```

```cron
20 3 * * * /opt/stepanio20/numisbot/deploy/backup.sh >> /var/log/numisbot-backup.log 2>&1
```

Восстановление:

```bash
cd /opt/stepanio20/numisbot
docker compose down
tar -xzf backups/numisbot-data-<дата>.tar.gz -C .
docker compose up -d
```

Последний архив периодически забирайте с VPS (`scp`/S3) — бэкап на той же машине
не спасает от гибели диска.

## 9. Ротация токена при утечке

1. **@BotFather** → `/mybots` → бот → *API Token* → **Revoke current token**.
   Старый токен гаснет мгновенно (бот встанет — это ожидаемо).
2. Новый токен в `.env`: `BOT_TOKEN=...`.
3. `docker compose up -d --force-recreate`
4. `docker compose logs --tail 20` + `/start` — убедиться, что polling пошёл.

Если токен попал в git — ревокнуть в любом случае (чистка истории через
`git filter-repo` не отменяет компрометацию). `PCGS_API_TOKEN` при утечке
перевыпустить в кабинете pcgs.com и так же пересоздать контейнер.

## 10. Health-мониторинг

Docker сам рестартует упавший процесс (`restart: unless-stopped`) и раз в минуту
проверяет его (`healthcheck` в compose):

```bash
docker inspect --format '{{.State.Health.Status}}' "$(docker compose ps -q numisbot)"
```

Cron-алерт в Telegram каждые 10 минут (`deploy/healthcheck.sh` = процесс жив
**и** нет `ERROR` в логах за последние 10 минут; выход 0/1):

```cron
*/10 * * * * /opt/stepanio20/numisbot/deploy/healthcheck.sh >/dev/null 2>&1 || curl -sS -m 10 "https://api.telegram.org/bot<BOT_TOKEN>/sendMessage" -d chat_id=<ВАШ_ID> -d text="numisbot: healthcheck FAIL on $(hostname)" >/dev/null
```

## 11. Вариант без Docker: systemd

```bash
apt-get update && apt-get install -y git python3 python3-venv sqlite3
useradd -r -s /usr/sbin/nologin numisbot
git clone https://github.com/stepanio20/stepanio20.git /opt/stepanio20
cd /opt/stepanio20/numisbot
python3 -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env && chmod 600 .env
chown -R numisbot:numisbot /opt/stepanio20/numisbot
cp deploy/numisbot.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now numisbot
systemctl status numisbot --no-pager
journalctl -u numisbot -f                    # логи
```

Пути в `deploy/numisbot.service` рассчитаны на `/opt/stepanio20/numisbot` + `venv`;
при другой раскладке поправьте `WorkingDirectory`, `EnvironmentFile`, `ExecStart`.

Выкачка архива в этом варианте:

```bash
sudo -u numisbot bash -c 'cd /opt/stepanio20/numisbot && \
  nohup venv/bin/python -m scripts.backfill --all --db data/archive.sqlite3 >> data/backfill.log 2>&1 &'
```

Обновление: `git pull && systemctl restart numisbot`.
`backup.sh` и `healthcheck.sh` работают и здесь — режим (docker/systemd)
определяется автоматически.
