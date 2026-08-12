#!/usr/bin/env bash
# Healthcheck numisbot: процесс жив И в логах за последние 10 минут нет ERROR.
# Выход: 0 = OK, 1 = проблема. Cron-алерт:
#   */10 * * * * /opt/stepanio20/numisbot/deploy/healthcheck.sh >/dev/null 2>&1 || <алерт>
# Режим (docker / systemd / голый процесс) определяется автоматически.
set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
WINDOW_MIN="${WINDOW_MIN:-10}"
UNIT="${UNIT:-numisbot}"

fail() { echo "healthcheck FAIL: $*" >&2; exit 1; }
ok()   { echo "healthcheck OK: $*"; exit 0; }

cd "$APP_DIR" || fail "нет каталога $APP_DIR"

# --- Docker ---
if command -v docker >/dev/null 2>&1 && [ -f docker-compose.yml ] \
   && docker compose ps -aq numisbot 2>/dev/null | grep -q .; then
  docker compose ps --status running -q numisbot 2>/dev/null | grep -q . \
    || fail "контейнер numisbot не запущен"
  if docker compose logs --since "${WINDOW_MIN}m" numisbot 2>&1 | grep -qF " ERROR "; then
    fail "ERROR в логах контейнера за последние ${WINDOW_MIN} мин"
  fi
  ok "docker: контейнер запущен, ERROR за ${WINDOW_MIN} мин нет"
fi

# --- systemd ---
if command -v systemctl >/dev/null 2>&1 && systemctl cat "$UNIT" >/dev/null 2>&1; then
  systemctl is-active --quiet "$UNIT" || fail "сервис $UNIT не активен"
  if journalctl -u "$UNIT" --since "${WINDOW_MIN} min ago" --no-pager 2>/dev/null | grep -qF " ERROR "; then
    fail "ERROR в журнале за последние ${WINDOW_MIN} мин"
  fi
  ok "systemd: сервис активен, ERROR за ${WINDOW_MIN} мин нет"
fi

# --- голый процесс (fallback, логи проверить нечем) ---
pgrep -f 'bot\.main' >/dev/null 2>&1 || fail "процесс bot.main не найден (ни docker, ни systemd)"
ok "процесс bot.main жив (логи недоступны для проверки ERROR)"
