
### 2.2. `docs/DEPLOY.md` — Руководство по развёртыванию

```markdown
# Руководство по развёртыванию Net Protector

## 1. Системные требования

### 1.1. Минимальные требования
- **ОС:** Ubuntu 24.04 LTS (рекомендуется) или другая Linux-система с Docker
- **CPU:** 2+ ядра
- **RAM:** 4+ ГБ
- **Диск:** 40+ ГБ
- **Сеть:** Открытые порты 80, 443, 2222 (SSH)

### 1.2. Программное обеспечение
- Docker 20.10+
- Docker Compose 2.0+
- Git

## 2. Подготовка сервера

### 2.1. Установка Ubuntu 24.04
1. Установите Ubuntu 24.04 LTS на сервер или виртуальную машину
2. Обновите систему:
   ```bash
   sudo apt update && sudo apt upgrade -y
2.2. Hardening сервера
Запустите скрипт hardening для настройки безопасности:
# Клонируйте репозиторий
git clone <your-repo-url> net-protector
cd net-protector

# Запустите hardening-скрипт от имени root
sudo NEW_USER=deployer bash scripts/harden_vm.sh
Что делает скрипт:
Создаёт пользователя deployer с sudo-правами
Настраивает SSH на порт 2222 (только по ключам, root запрещён)
Настраивает UFW (разрешает порты 2222, 80, 443)
Устанавливает Fail2Ban (защита от перебора SSH)
Настраивает политику сложных паролей
Важно: После выполнения скрипта:
Откройте новое окно терминала
Проверьте вход: ssh -p 2222 deployer@<your-server-ip>
Только после успешной проверки перезапустите SSH: sudo systemctl restart ssh
2.3. Установка Docker
# Под пользователем deployer
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Проверка
docker run hello-world
