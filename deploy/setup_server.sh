#!/usr/bin/env bash
# One-time setup of the DPL site on an Ubuntu 22.04/24.04 VPS (Hostinger KVM).
# Run as root:   bash setup_server.sh
# Safe to re-run: every step checks whether it has already been done.
#
# SHARED-SERVER SAFE: other sites on this VPS are not touched.
#  - never removes or edits other Nginx sites, never changes the firewall policy
#  - refuses to continue if something other than Nginx owns ports 80/443
#  - Nginx is only reloaded if the full config (all sites) passes `nginx -t`
#  - everything DPL uses is namespaced: /srv/dpl, user "dpl", DB "dpl", service "dpl"
# Run deploy/inspect_server.sh first to see what's already on the server.
set -euo pipefail

APP_USER=dpl
APP_DIR=/srv/dpl
REPO_URL=${REPO_URL:-https://github.com/upretybnd/DPL.git}
BRANCH=${BRANCH:-main}
DOMAIN=${DOMAIN:-dpl.org.np}
DB_NAME=dpl
DB_USER=dpl

echo "==> Checking ports 80/443 are free or already served by Nginx"
WEB_OWNERS=$(ss -ltnpH '( sport = :80 or sport = :443 )' 2>/dev/null | grep -oE 'users:\(\("[^"]+' | cut -d'"' -f2 | sort -u | tr '\n' ' ' || true)
if [ -n "${WEB_OWNERS// /}" ] && [ "$(echo $WEB_OWNERS)" != "nginx" ]; then
    echo "   Ports 80/443 are used by: $WEB_OWNERS"
    echo "   Not installing Nginx, to avoid breaking existing sites."
    echo "   Next step: add DPL as a reverse-proxy site in the existing web server/panel instead."
    exit 1
fi

echo "==> Installing system packages (existing packages are left as they are)"
apt-get update -y
apt-get install -y python3 python3-venv python3-dev build-essential libpq-dev \
    postgresql postgresql-contrib nginx git rclone curl

echo "==> Firewall"
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
    ufw allow OpenSSH >/dev/null
    ufw allow 'Nginx Full' >/dev/null
    echo "   ufw is active: allowed SSH + web (existing rules unchanged)"
else
    echo "   ufw not active: leaving the firewall exactly as it is"
fi

echo "==> App user and folders"
id -u "$APP_USER" >/dev/null 2>&1 || adduser --system --group --home "$APP_DIR" --shell /bin/bash "$APP_USER"
mkdir -p "$APP_DIR"/{logs,run,backups}
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> PostgreSQL database (a separate database; other databases are untouched)"
systemctl enable --now postgresql
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    DB_PASSWORD=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-32)
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    echo "$DB_PASSWORD" > "$APP_DIR/.db_password"
    chmod 600 "$APP_DIR/.db_password"
    chown "$APP_USER:$APP_USER" "$APP_DIR/.db_password"
fi

echo "==> Code"
if [ ! -d "$APP_DIR/app/.git" ]; then
    sudo -u "$APP_USER" git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR/app"
fi

echo "==> Python environment"
if [ ! -d "$APP_DIR/venv" ]; then
    sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
fi
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/app/requirements.txt"

echo "==> Environment file"
if [ ! -f "$APP_DIR/app/.env" ]; then
    SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
    DB_PASSWORD=$(cat "$APP_DIR/.db_password")
    cat > "$APP_DIR/app/.env" <<EOF
SECRET_KEY=$SECRET
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN

DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432

# Cloudflare R2 — paste the dpl-website token's keys (see DEPLOY.md, step 2)
R2_ACCOUNT_ID=e0f760b577bb7d05fb7b62459c697a91
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_PUBLIC_BUCKET=dpl-media
R2_PRIVATE_BUCKET=dpl-private
R2_BACKUP_BUCKET=dpl-backups
R2_PUBLIC_DOMAIN=media.$DOMAIN

# Email — fill these in
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=no-reply@$DOMAIN
CONTACT_EMAIL=contact@$DOMAIN

DONATION_BANK_NAME=
DONATION_ACCOUNT_NAME=Dynamic Public Library
DONATION_ACCOUNT_NUMBER=
DONATION_BANK_BRANCH=
DONATION_ESEWA_ID=
DONATION_KHALTI_ID=
EOF
    chown "$APP_USER:$APP_USER" "$APP_DIR/app/.env"
    chmod 600 "$APP_DIR/app/.env"
    echo "   Created $APP_DIR/app/.env — add the R2 keys (and email), then re-run this script."
    exit 0
fi

echo "==> Database migrations and static files"
cd "$APP_DIR/app"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" manage.py migrate --noinput
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" manage.py collectstatic --noinput --verbosity 0
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" manage.py check --deploy

echo "==> App service"
install -m 644 deploy/dpl.service /etc/systemd/system/dpl.service
systemctl daemon-reload
systemctl enable --now dpl

# Let the deploy script restart only the DPL app
echo "$APP_USER ALL=(root) NOPASSWD: /bin/systemctl restart dpl" > /etc/sudoers.d/dpl
chmod 440 /etc/sudoers.d/dpl

echo "==> Nginx site (added alongside existing sites)"
if [ -f /etc/ssl/cloudflare/dpl-origin.pem ] && [ -f /etc/ssl/cloudflare/dpl-origin.key ]; then
    install -m 644 deploy/nginx.conf /etc/nginx/sites-available/dpl
    sed -i "s/__DOMAIN__/$DOMAIN/g" /etc/nginx/sites-available/dpl
    ln -sf /etc/nginx/sites-available/dpl /etc/nginx/sites-enabled/dpl
    if nginx -t; then
        systemctl reload nginx
        echo "   DPL site enabled"
    else
        echo "   Nginx config test failed — removing the DPL site so other sites keep working"
        rm -f /etc/nginx/sites-enabled/dpl
        exit 1
    fi
else
    echo "   Skipped: add the Cloudflare Origin Certificate first (DEPLOY.md step 4), then re-run."
fi

echo "==> Nightly backups"
install -m 644 deploy/backup.cron /etc/cron.d/dpl-backup

echo
echo "Done. App: systemctl status dpl · Logs: /srv/dpl/logs/"