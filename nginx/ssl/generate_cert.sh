#!/usr/bin/env bash
DOMAIN=${1:-"localhost"}
openssl genrsa -out "privkey.pem" 4096
openssl req -new -x509 -key "privkey.pem" \
    -out "fullchain.pem" \
    -days 365 \
    -subj "/CN=$DOMAIN" \
    -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1"
echo "Сертификаты созданы для $DOMAIN"
