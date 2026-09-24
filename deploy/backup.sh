#!/usr/bin/env bash
# Back up the PostgreSQL database (and weekly, all uploads) to the Cloudflare R2 backup bucket.
#   backup.sh            nightly database backup (kept 30 days)
#   backup.sh media      mirror both upload buckets into the backup bucket
#   backup.sh pre-deploy database snapshot taken before each deploy (kept 30 days)
set -euo pipefail

APP_DIR=/srv/dpl
set -a; source "$APP_DIR/app/.env"; set +a

if [ -z "${R2_ACCOUNT_ID:-}" ]; then
    echo "R2 is not configured in .env" >&2
    exit 1
fi

# rclone reads its R2 connection from these variables — no config file with secrets on disk.
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
export RCLONE_CONFIG_R2_ENDPOINT="https://$R2_ACCOUNT_ID.r2.cloudflarestorage.com"
export RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true
BUCKET="${R2_BACKUP_BUCKET:-dpl-backups}"
STAMP=$(date -u +%Y-%m-%dT%H%MZ)
MODE="${1:-nightly}"

if [ "$MODE" = "media" ]; then
    rclone sync "r2:${R2_PUBLIC_BUCKET:-dpl-media}" "r2:$BUCKET/media-mirror/public" --fast-list
    rclone sync "r2:${R2_PRIVATE_BUCKET:-dpl-private}" "r2:$BUCKET/media-mirror/private" --fast-list
    echo "Uploads mirrored to $BUCKET/media-mirror"
    exit 0
fi

FILE="$APP_DIR/backups/dpl-$MODE-$STAMP.dump"
PGPASSWORD="$DB_PASSWORD" pg_dump --format=custom --no-owner -h "${DB_HOST:-localhost}" -U "$DB_USER" "$DB_NAME" > "$FILE"
rclone copy "$FILE" "r2:$BUCKET/db/" --s3-no-check-bucket
rm -f "$FILE"

# Keep 30 days of database backups
rclone delete "r2:$BUCKET/db/" --min-age 30d
echo "Database backed up to $BUCKET/db/$(basename "$FILE")"
