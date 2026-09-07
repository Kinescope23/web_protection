FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Обучение ML-модели при первой сборке
RUN python -m app.ml.train || true

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]