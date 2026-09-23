#!/bin/bash
# ============================================================
# Скрипт hardening виртуальной машины для Net Protector
# Запускать от имени root или пользователя с sudo
# ============================================================

set -e

echo "=== [1/6] Создание пользователя с sudo ==="
NEW_USER="${NEW_USER:-deployer}"
if ! id "$NEW_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$NEW_USER"
    echo "Установите пароль для пользователя $NEW_USER:"
    passwd "$NEW_USER"
    usermod -aG sudo "$NEW_USER"
    echo "Пользователь $NEW_USER создан и добавлен в группу sudo"
else
    echo "Пользователь $NEW_USER уже существует"
fi

echo ""
echo "=== [2/6] Настройка SSH ==="
SSH_PORT=2222
SSHD_CONFIG="/etc/ssh/sshd_config"

# Бэкап оригинального конфига
cp "$SSHD_CONFIG" "${SSHD_CONFIG}.bak.$(date +%s)"

# Применяем настройки
cat > /tmp/sshd_hardening.conf <<EOF
# === Hardening by Net Protector ===
Port $SSH_PORT
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowUsers $NEW_USER
EOF

# Добавляем в конец sshd_config
grep -q "Hardening by Net Protector" "$SSHD_CONFIG" || cat /tmp/sshd_hardening.conf >> "$SSHD_CONFIG"
rm /tmp/sshd_hardening.conf

echo "SSH настроен: порт $SSH_PORT, вход только по ключам, root запрещён"

echo ""
echo "=== [3/6] Настройка SSH-ключей для пользователя ==="
USER_HOME="/home/$NEW_USER"
mkdir -p "$USER_HOME/.ssh"
chmod 700 "$USER_HOME/.ssh"

# Если есть публичный ключ у root — копируем
if [ -f /root/.ssh/id_rsa.pub ]; then
    cp /root/.ssh/id_rsa.pub "$USER_HOME/.ssh/authorized_keys"
    echo "Публичный ключ скопирован из /root/.ssh/id_rsa.pub"
elif [ -f /root/.ssh/authorized_keys ]; then
    cp /root/.ssh/authorized_keys "$USER_HOME/.ssh/authorized_keys"
    echo "authorized_keys скопирован из /root"
else
    echo "ВНИМАНИЕ: Нет публичного ключа. Добавьте его вручную:"
    echo "  ssh-copy-id -p $SSH_PORT $NEW_USER@<your-server-ip>"
fi

chown -R "$NEW_USER:$NEW_USER" "$USER_HOME/.ssh"
chmod 600 "$USER_HOME/.ssh/authorized_keys" 2>/dev/null || true

echo ""
echo "=== [4/6] Настройка UFW (межсетевой экран) ==="
apt-get update -qq
apt-get install -y ufw fail2ban

# Сброс правил
ufw --force reset

# Политики по умолчанию
ufw default deny incoming
ufw default allow outgoing

# Разрешаем SSH на новом порту
ufw allow $SSH_PORT/tcp comment 'SSH (hardened)'

# Разрешаем HTTP/HTTPS для веб-приложения
ufw allow 80/tcp comment 'HTTP (redirect to HTTPS)'
ufw allow 443/tcp comment 'HTTPS (Net Protector)'

# Разрешаем Prometheus/Grafana только из локальной сети (опционально)
# ufw allow from 10.0.0.0/8 to any port 3000 comment 'Grafana'
# ufw allow from 10.0.0.0/8 to any port 9090 comment 'Prometheus'

# Включаем UFW
yes | ufw enable
ufw status verbose

echo ""
echo "=== [5/6] Настройка Fail2Ban (защита от перебора) ==="
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
banaction = ufw

[sshd]
enabled = true
port = $SSH_PORT
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl restart fail2ban
echo "Fail2Ban настроен: 3 неудачные попытки SSH → бан на 1 час"

echo ""
echo "=== [6/6] Настройка сложных паролей ==="
apt-get install -y libpam-pwquality

# Политика сложных паролей
cat > /etc/pam.d/common-password.hardening <<EOF
password requisite pam_pwquality.so retry=3 minlen=12 dcredit=-1 ucredit=-1 lcredit=-1 ocredit=-1
EOF

# Добавляем в common-password, если ещё не добавлено
if ! grep -q "pam_pwquality" /etc/pam.d/common-password; then
    sed -i '1i password requisite pam_pwquality.so retry=3 minlen=12 dcredit=-1 ucredit=-1 lcredit=-1 ocredit=-1' /etc/pam.d/common-password
fi

echo "Политика паролей: минимум 12 символов, цифры, верхний/нижний регистр, спецсимволы"

echo ""
echo "============================================"
echo "✅ Hardening завершён!"
echo "============================================"
echo ""
echo "📋 Следующие шаги:"
echo "1. Откройте НОВОЕ окно терминала и проверьте вход:"
echo "   ssh -p $SSH_PORT $NEW_USER@<your-server-ip>"
echo ""
echo "2. Если вход работает — перезапустите SSH:"
echo "   sudo systemctl restart ssh"
echo ""
echo "3. Установите Docker (если ещё не установлен):"
echo "   curl -fsSL https://get.docker.com | sh"
echo "   sudo usermod -aG docker $NEW_USER"
echo ""
echo "4. Клонируйте репозиторий и запустите проект:"
echo "   git clone <repo-url>"
echo "   cd net-protector"
echo "   docker-compose up -d"
echo ""