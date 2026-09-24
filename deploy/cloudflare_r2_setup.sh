#!/usr/bin/env bash
# Create the DPL R2 buckets and connect media.dpl.org.np, using the Cloudflare API.
# Reads CF_API_TOKEN and CF_ACCOUNT_ID from .cloudflare.env (git-ignored). Never prints the token.
# Safe to re-run: existing buckets/domains are left as they are.
set -euo pipefail

ENV_FILE="${1:-.cloudflare.env}"
[ -f "$ENV_FILE" ] || { echo "Missing $ENV_FILE"; exit 1; }
set -a; source <(tr -d '\r' < "$ENV_FILE"); set +a
: "${CF_API_TOKEN:?CF_API_TOKEN not set}" "${CF_ACCOUNT_ID:?CF_ACCOUNT_ID not set}"

DOMAIN="${DOMAIN:-dpl.org.np}"
MEDIA_HOST="${MEDIA_HOST:-media.$DOMAIN}"
API="https://api.cloudflare.com/client/v4"
ACC="$API/accounts/$CF_ACCOUNT_ID"

cf() {  # cf METHOD URL [JSON]
    curl -sS -X "$1" "$2" -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" ${3:+--data "$3"}
}
ok()  { python -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("success") else 1)'; }
err() { python -c 'import json,sys; d=json.load(sys.stdin); print("; ".join(f"{e.get(\"code\")}: {e.get(\"message\")}" for e in d.get("errors",[])))'; }

echo "==> Checking token"
resp=$(cf GET "$ACC/r2/buckets")
echo "$resp" | ok || { echo "   Token can't list R2 buckets: $(echo "$resp" | err)"; exit 1; }
echo "   OK"

echo "==> Buckets"
for bucket in dpl-media dpl-private dpl-backups; do
    resp=$(cf POST "$ACC/r2/buckets" "{\"name\":\"$bucket\",\"locationHint\":\"apac\"}")
    if echo "$resp" | ok; then
        echo "   created $bucket"
    elif echo "$resp" | err | grep -q "10004"; then
        echo "   $bucket already exists"
    else
        echo "   $bucket failed: $(echo "$resp" | err)"; exit 1
    fi
done

echo "==> Custom domain $MEDIA_HOST -> dpl-media"
ZONE_ID=$(cf GET "$API/zones?name=$DOMAIN" | python -c 'import json,sys; r=json.load(sys.stdin).get("result") or []; print(r[0]["id"] if r else "")')
[ -n "$ZONE_ID" ] || { echo "   Zone $DOMAIN not found in this account (token needs Zone:Read)"; exit 1; }
existing=$(cf GET "$ACC/r2/buckets/dpl-media/domains/custom" | python -c 'import json,sys; d=json.load(sys.stdin); print(" ".join(x.get("domain","") for x in (d.get("result") or {}).get("domains",[])))')
if echo " $existing " | grep -q " $MEDIA_HOST "; then
    echo "   already connected"
else
    resp=$(cf POST "$ACC/r2/buckets/dpl-media/domains/custom" "{\"domain\":\"$MEDIA_HOST\",\"zoneId\":\"$ZONE_ID\",\"enabled\":true,\"minTLS\":\"1.2\"}")
    echo "$resp" | ok && echo "   connected (SSL may take a few minutes)" || { echo "   failed: $(echo "$resp" | err)"; exit 1; }
fi

echo "==> Backup retention (delete database backups after 35 days)"
resp=$(cf PUT "$ACC/r2/buckets/dpl-backups/lifecycle" '{"rules":[{"id":"expire-db-backups","enabled":true,"conditions":{"prefix":"db/"},"deleteObjectsTransition":{"condition":{"type":"Age","maxAge":3024000}}}]}')
echo "$resp" | ok && echo "   set" || echo "   skipped: $(echo "$resp" | err)"

echo
echo "Done. Buckets: dpl-media (public at https://$MEDIA_HOST), dpl-private, dpl-backups."