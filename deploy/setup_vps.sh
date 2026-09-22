#!/usr/bin/env bash
# Первичная настройка VPS TimeWeb под sale_b24 (Ubuntu/Debian).
# Запуск на сервере: sudo bash deploy/setup_vps.sh

set -euo pipefail

APP_DIR="/opt/sale_b24"
APP_USER="${APP_USER:-www-data}"
DOMAIN="${DOMAIN:-}"

echo "==> Пакеты"
apt-get update
apt-get install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx ufw

echo "==> Каталог приложения"
mkdir -p "$APP_DIR/data"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

if [[ ! -f "$APP_DIR/requirements.txt" ]]; then
  echo "Сначала загрузите файлы проекта в $APP_DIR (SFTP/scp)."
  exit 1
fi

echo "==> Python venv"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "Создан $APP_DIR/.env — заполните переменные перед запуском."
fi

echo "==> systemd"
cp "$APP_DIR/deploy/sale-b24.service" /etc/systemd/system/sale-b24.service
systemctl daemon-reload
systemctl enable sale-b24

echo "==> Firewall"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

if [[ -n "$DOMAIN" ]]; then
  echo "==> Nginx + SSL для $DOMAIN"
  sed "s/bot.example.com/$DOMAIN/g" "$APP_DIR/deploy/nginx.example.conf" \
    > "/etc/nginx/sites-available/sale-b24"
  ln -sf "/etc/nginx/sites-available/sale-b24" /etc/nginx/sites-enabled/sale-b24
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl reload nginx
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" || true
fi

systemctl restart sale-b24
systemctl status sale-b24 --no-pager || true

echo
echo "Готово. Дальше:"
echo "  1. nano $APP_DIR/.env"
echo "  2. systemctl restart sale-b24"
echo "  3. curl https://$DOMAIN/health   (или http://127.0.0.1:8000/health локально)"
echo "  4. После модерации MAX: python scripts/activate_max.py https://$DOMAIN"
