#!/usr/bin/env bash
# READ-ONLY look at a server before installing DPL. Changes nothing.
#   bash inspect_server.sh
echo "== System";        . /etc/os-release 2>/dev/null && echo "$PRETTY_NAME"; uname -r
echo "== Resources";     nproc | sed 's/^/CPUs: /'; free -h | sed -n '1,2p'; df -h / | tail -1
echo "== Web ports";     ss -ltnp '( sport = :80 or sport = :443 )' 2>/dev/null
echo "== Other listening ports"; ss -ltnp 2>/dev/null | awk 'NR>1{print $4, $6}' | sort -u
echo "== Web servers";   for s in nginx apache2 httpd lsws caddy; do systemctl is-active --quiet $s 2>/dev/null && echo "$s: running"; done
command -v nginx >/dev/null && nginx -v 2>&1
echo "== Nginx sites";   ls -1 /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null
echo "== Hosting panels"; for p in /usr/local/cpanel /usr/local/CyberCP /usr/local/lsws /www/server/panel /home/clp /usr/local/hestia /usr/local/vesta /opt/plesk /usr/local/psa; do [ -e "$p" ] && echo "found $p"; done
echo "== Databases";     for s in postgresql mysql mariadb; do systemctl is-active --quiet $s 2>/dev/null && echo "$s: running"; done
echo "== Docker";        command -v docker >/dev/null && docker ps --format '{{.Names}}  {{.Ports}}' 2>/dev/null || echo "not installed"
echo "== Firewall";      command -v ufw >/dev/null && ufw status 2>/dev/null | head -20
echo "== Python";        python3 --version 2>/dev/null
echo "== Existing DPL";  ls -d /srv/dpl 2>/dev/null || echo "none"; systemctl is-active dpl 2>/dev/null || true