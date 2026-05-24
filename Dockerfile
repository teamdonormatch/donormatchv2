FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=donormatch.settings
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libjpeg62-turbo zlib1g curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY . .
RUN mkdir -p /app/media/hospital_logos /app/media/payment_proofs /app/ml_models /app/staticfiles
RUN python manage.py collectstatic --noinput
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed && gunicorn donormatch.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"]
