import sys
import os
from pathlib import Path

# Добавляем корневую директорию backend/ в PYTHONPATH
# Это позволяет тестам импортировать модули из app/
sys.path.insert(0, str(Path(__file__).parent))

# Устанавливаем тестовые переменные окружения ДО импорта app
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-pipeline-32-chars")
os.environ.setdefault("MASTER_INVITE_KEY", "NP-MASTER-2026-SUPER-ADMIN")
os.environ.setdefault("FRONTEND_URL", "https://localhost")