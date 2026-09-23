#!/bin/bash
# ============================================================
# Скрипт получения Let's Encrypt сертификата через Certbot
# Требует: домен, указывающий на сервер, и открытый порт 80
# ============================================================

set -e

DOMAIN="${1:-}"
EMAIL="${2:-}"

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Использование: $0 <domain> <email>"
    echo "Пример: $0 netprotector.example.com admin@example.com"
    exit 1
fi

echo "=== Установка Certbot ==="
apt-get update -qq
apt-get install -y certbot

echo ""
echo "=== Остановка Nginx (для standalone режима) ==="
docker-compose stop nginx

echo ""
echo "=== Получение сертификата ==="
certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN" \
    --preferred-challenges http

echo ""
echo "=== Копирование сертификатов в nginx/ssl ==="
mkdir -p nginx/ssl
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/fullchain.pem
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/privkey.pem
chmod 644 nginx/ssl/fullchain.pem
chmod 600 nginx/ssl/privkey.pem

echo ""
echo "=== Настройка автообновления ==="
cat > /etc/cron.d/certbot-renew <<EOF
0 3 * * * root certbot renew --quiet --deploy-hook "cd $(pwd) && docker-compose restart nginx"
EOF

echo ""
echo "=== Запуск Nginx ==="
docker-compose start nginx

echo ""
echo "============================================"
echo "✅ Сертификат получен для $DOMAIN"
echo "============================================"
echo ""
echo "Автообновление настроено через cron (ежедневно в 3:00)"