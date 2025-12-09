# Етап 1: Builder (збірка залежностей)
FROM python:3.11-alpine AS builder

WORKDIR /app

# Встановлюємо системні бібліотеки для збірки (gcc, musl-dev потрібні для Flask/Werkzeug)
RUN apk add --no-cache gcc musl-dev libffi-dev

# Копіюємо та встановлюємо залежності
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Етап 2: Final (чистий, легкий образ для запуску)
FROM python:3.11-alpine

WORKDIR /app

# Встановлюємо curl для Healthcheck (це важливо, щоб контейнер не падав)
RUN apk add --no-cache curl

# Копіюємо встановлені пітон-пакети з першого етапу
COPY --from=builder /root/.local /root/.local

# Налаштовуємо шляхи
ENV PATH=/root/.local/bin:$PATH
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/database.db

# Створюємо папку для бази даних і даємо права
RUN mkdir -p /app/data && chmod 777 /app/data

# Копіюємо весь код проєкту
COPY . .

# Відкриваємо порт 5000 (внутрішній)
EXPOSE 5000

# Healthcheck: перевіряє, чи працює сайт
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/api/v1/status || exit 1

# Запуск
CMD ["python", "app.py"]