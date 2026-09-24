FROM python:3.11-slim

WORKDIR /app

# Создание non-root пользователя
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Директории для записи
RUN mkdir -p /app/uploads/tmp /app/uploads/final /app/uploads/avatars /app/ml_models \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]