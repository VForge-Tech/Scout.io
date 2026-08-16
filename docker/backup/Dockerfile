# Backup + restore container for Scout.io.
#
# Based on the postgres image so pg_dump / pg_restore are guaranteed to match
# the production Postgres major version (16). Adds the AWS CLI v2 for uploads to
# any S3-compatible object store and cron for the nightly schedule.
FROM postgres:16-alpine

RUN apk add --no-cache \
        aws-cli \
        curl \
        docker-cli \
        docker-cli-compose \
        tzdata \
    && mkdir -p /scripts /backup

COPY backup.sh restore.sh entrypoint.sh /scripts/
RUN chmod +x /scripts/backup.sh /scripts/restore.sh /scripts/entrypoint.sh

# Used by cron (set via env, default UTC)
ENV TZ=UTC \
    CRON_SCHEDULE="0 3 * * *" \
    BACKUP_ON_START=true

ENTRYPOINT ["/scripts/entrypoint.sh"]