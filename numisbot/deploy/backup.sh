#!/usr/bin/env bash
# Бэкап data/*.sqlite3 → $BACKUP_DIR/numisbot-data-YYYYmmdd-HHMMSS.tar.gz,
# хранит последние 14 архивов (KEEP). Cron (ежедневно в 03:20):
#   20 3 * * * /opt/stepanio20/numisbot/deploy/backup.sh >> /var/log/numisbot-backup.log 2>&1
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
KEEP="${KEEP:-14}"

cd "$APP_DIR"
shopt -s nullglob
files=(data/*.sqlite3)
[ "${#files[@]}" -gt 0 ] || { echo "backup: нет data/*.sqlite3 — нечего бэкапить" >&2; exit 1; }

mkdir -p "$BACKUP_DIR"
stamp="$(date +%Y%m%d-%H%M%S)"
archive="$BACKUP_DIR/numisbot-data-$stamp.tar.gz"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/data"

# sqlite3 .backup даёт консистентную копию живой БД (WAL учитывается);
# без sqlite3 — обычный cp (+ wal/shm, если есть).
for f in "${files[@]}"; do
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$f" ".backup '$tmp/data/${f##*/}'"
  else
    cp -p "$f" "$tmp/data/"
    for ext in -wal -shm; do
      if [ -f "$f$ext" ]; then cp -p "$f$ext" "$tmp/data/"; fi
    done
  fi
done

tar -czf "$archive" -C "$tmp" data
echo "backup OK: $archive ($(du -h "$archive" | cut -f1))"

# Ротация: оставить последние KEEP архивов
ls -1t "$BACKUP_DIR"/numisbot-data-*.tar.gz | tail -n +"$((KEEP + 1))" | xargs -r rm -f --
