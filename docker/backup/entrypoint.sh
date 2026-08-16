#!/usr/bin/env bash
# Entrypoint for the backup container.
#
# Default mode: run a backup at startup (optional), install the nightly cron
# schedule, and stay alive running crond.
#
# If a command is given (e.g. `docker run scout-backup /scripts/restore.sh ...`),
# that command is exec'd instead of starting cron.
set -euo pipefail

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

if [ "${BACKUP_ON_START:-true}" = "true" ]; then
  echo "[$(date -u +%FT%TZ)] running backup at startup"
  /scripts/backup.sh || echo "[$(date -u +%FT%TZ)] startup backup failed (exit $?)"
fi

CRON_SCHEDULE="${CRON_SCHEDULE:-0 3 * * *}"
echo "Installing cron schedule: ${CRON_SCHEDULE}"
echo "${CRON_SCHEDULE} root /scripts/backup.sh >> /var/log/backup-cron.log 2>&1" > /etc/crontabs/root

exec crond -f -l 2