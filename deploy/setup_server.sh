#!/usr/bin/env bash
# One-time setup of the DPL site on a fresh Ubuntu 22.04/24.04 VPS (Hostinger KVM).
# Run as root:   bash setup_server.sh
# Safe to re-run: every step checks whether it has already been done.
set -euo pipefail

APP_USER=dpl
APP_DIR=/srv/dpl
REPO_URL=${REPO_URL:-https://github.com/upretybnd/DPL.git}
BRANCH=${BRANCH:-main}
DOMAIN=${DOMAIN:-dpl.org.np}
DB_NAME=dpl
DB_USER=dpl

echo "==> Installing system packages"
apt-get update -y
apt-get install -y python3 python3-venv python3-dev build-essential libpq-dev \
    postgresql postgresql-contrib nginx git rclone ufw curl

echo "==> Firewall: SSH + web only"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "==> App user and folders"
id -u "$APP_USER" >/dev/null 2>&1 || adduser --system --group --home "$APP_DIR" --shell /bin/bash "$APP_USER"
mkdir -p "$APP_DIR"/{logs,run,backups}
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> PostgreSQL database"
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
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/app/requirements.txt"

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

# Cloudflare R2 — fill these in (see DEPLOY.md, step 2)
R2_ACCOUNT_ID=
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
    echo "   Created $APP_DIR/app/.env — fill in R2 and email values, then re-run this script."
fi

echo "==> Database migrations and static files"
cd "$APP_DIR/app"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" manage.py migrate --noinput
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" manage.py collectstatic --noinput
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" manage.py check --deploy

echo "==> Services"
install -m 644 deploy/dpl.service /etc/systemd/system/dpl.service
install -m 644 deploy/nginx.conf /etc/nginx/sites-available/dpl
sed -i "s/__DOMAIN__/$DOMAIN/g" /etc/nginx/sites-available/dpl
ln -sf /etc/nginx/sites-available/dpl /etc/nginx/sites-enabled/dpl
rm -f /etc/nginx/sites-enabled/default

# Let the deploy script restart the app without full root access
echo "$APP_USER ALL=(root) NOPASSWD: /bin/systemctl restart dpl, /bin/systemctl reload nginx" > /etc/sudoers.d/dpl
chmod 440 /etc/sudoers.d/dpl

systemctl daemon-reload
systemctl enable --now dpl
nginx -t && systemctl reload nginx

echo "==> Nightly backups"
install -m 644 deploy/backup.cron /etc/cron.d/dpl-backup

echo
echo "Done. Next: install the Cloudflare Origin Certificate (DEPLOY.md, step 4) and point DNS at this server."
