#!/usr/bin/env bash
# Pull the latest code and restart. Run on the server as the `dpl` user:
#   sudo -u dpl /srv/dpl/app/deploy/deploy.sh
# GitHub Actions runs this automatically after tests pass on `main`.
set -euo pipefail

APP_DIR=/srv/dpl
BRANCH=${BRANCH:-main}
cd "$APP_DIR/app"

echo "==> Backing up the database before deploying"
"$APP_DIR/app/deploy/backup.sh" pre-deploy || echo "   (backup skipped: R2 not configured yet)"

echo "==> Updating code ($BRANCH)"
git fetch --quiet origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "==> Dependencies, migrations, static files"
"$APP_DIR/venv/bin/pip" install --quiet -r requirements.txt
"$APP_DIR/venv/bin/python" manage.py migrate --noinput
"$APP_DIR/venv/bin/python" manage.py collectstatic --noinput --verbosity 0

echo "==> Restarting"
sudo /bin/systemctl restart dpl
sleep 3
curl --fail --silent --unix-socket "$APP_DIR/run/gunicorn.sock" -H "Host: dpl.org.np" -H "X-Forwarded-Proto: https" \
    http://localhost/robots.txt > /dev/null && echo "==> Site is up"
