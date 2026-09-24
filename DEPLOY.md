# Deploying dpl.org.np

Target: **Hostinger VPS (KVM 4, Ubuntu)** · **Cloudflare** DNS/SSL/CDN · **Cloudflare R2** for images and backups.

```
Visitor ──► Cloudflare (DNS, HTTPS, cache) ──► Nginx on VPS ──► Gunicorn ──► Django ──► PostgreSQL
                     │
                     └──► media.dpl.org.np ──► R2 bucket "dpl-media"  (public images)
                          R2 bucket "dpl-private"  (documents, signed links only)
                          R2 bucket "dpl-backups"  (nightly DB dumps + weekly upload mirror)
```

## 1. Cloudflare DNS
1. Add `dpl.org.np` to Cloudflare (if it isn't already) and switch the domain's nameservers to Cloudflare's.
2. **Don't point `@`/`www` at the VPS yet** — the old site keeps running until step 6.

## 2. Cloudflare R2
1. **R2 → Create bucket**: `dpl-media`, `dpl-private`, `dpl-backups` (location: Asia-Pacific).
2. `dpl-media` → **Settings → Custom domains → Connect** `media.dpl.org.np`. Leave the other two buckets private.
3. **R2 → Manage API tokens → Create token**: *Object Read & Write*, limited to those three buckets.
   Note the **Account ID**, **Access Key ID** and **Secret Access Key** — they go only into the server's `.env`.

## 3. Server setup (VPS)
```bash
ssh root@<VPS-IP>
curl -fsSL https://raw.githubusercontent.com/upretybnd/DPL/main/deploy/setup_server.sh -o setup_server.sh
bash setup_server.sh                     # creates /srv/dpl/app/.env on the first run
nano /srv/dpl/app/.env                   # fill in R2_*, EMAIL_*, DONATION_* values
bash setup_server.sh                     # second run: migrates, collects static, starts services
sudo -u dpl /srv/dpl/app/deploy/backup.sh   # test a backup to R2
```

## 4. HTTPS (Cloudflare Origin Certificate)
1. Cloudflare → **SSL/TLS → Origin Server → Create certificate** for `dpl.org.np, *.dpl.org.np`.
2. On the VPS save them as `/etc/ssl/cloudflare/origin.pem` and `/etc/ssl/cloudflare/origin.key` (`chmod 600` the key).
3. `nginx -t && systemctl reload nginx`
4. Cloudflare → SSL/TLS mode **Full (strict)**, enable **Always Use HTTPS**.

## 5. Move data from the current (cPanel) site
1. On cPanel, download the database (phpMyAdmin export, or the SQLite file) and the `media/` folder.
2. Locally, point Django at that old database, upgrade it and export:
   ```bash
   python manage.py migrate            # upgrades the old schema to this version
   python manage.py dumpdata --natural-foreign --natural-primary \
       -e contenttypes -e auth.permission -e admin.logentry -e sessions --indent 2 > dpl-data.json
   ```
3. Copy `dpl-data.json` to the VPS and load it: `sudo -u dpl /srv/dpl/venv/bin/python manage.py loaddata dpl-data.json`
4. Upload images to R2 (rclone, from the old `media/` folder):
   ```bash
   # Sensitive folders go to the private bucket, everything else to the public one
   rclone copy media/ r2:dpl-private --include "{citizenship_documents,payment_screenshots,candidate_profiles,donation_proofs,project_evidence}/**"
   rclone copy media/ r2:dpl-media   --exclude "{citizenship_documents,payment_screenshots,candidate_profiles,donation_proofs,project_evidence}/**"
   ```

## 6. Go live
1. Test the site on the VPS with a hosts-file entry (`<VPS-IP> dpl.org.np`) — log in, open MIS, upload a photo.
2. Cloudflare DNS: `A @ → <VPS-IP>` and `CNAME www → dpl.org.np`, both **Proxied** (orange cloud).
3. Keep the cPanel site untouched for a week as a fallback, then cancel it.

## 7. Automatic deploys
GitHub → repo **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `VPS_HOST` | VPS IP |
| `VPS_USER` | SSH user (e.g. `root`) |
| `VPS_SSH_KEY` | private key of a key pair made for GitHub (public half in the VPS `~/.ssh/authorized_keys`) |
| `VPS_KNOWN_HOSTS` | output of `ssh-keyscan <VPS-IP>` |

After that, every push to `main` runs the tests and — only if they pass — backs up the database and deploys.

## Backups
- **Database:** nightly at 02:30 NPT → `dpl-backups/db/` (30 days kept), plus a snapshot before every deploy.
- **Images:** stored in R2 (redundant storage), mirrored weekly to `dpl-backups/media-mirror/`.
- **Restore a database backup:**
  ```bash
  rclone copy r2:dpl-backups/db/<file>.dump .    # (with the RCLONE_CONFIG_R2_* vars from backup.sh)
  pg_restore --clean --no-owner -d dpl <file>.dump
  ```

## Everyday commands (on the VPS)
```bash
sudo -u dpl /srv/dpl/app/deploy/deploy.sh      # manual deploy
journalctl -u dpl -f                           # app logs
tail -f /srv/dpl/logs/error.log                # gunicorn errors
sudo -u dpl /srv/dpl/venv/bin/python /srv/dpl/app/manage.py createsuperuser
```
