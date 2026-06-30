FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt && \
    prisma generate --schema /app/packages/db/prisma/schema.prisma

EXPOSE 8000

CMD ["sh", "-c", "cd /app/apps/api && uvicorn main:app --host 0.0.0.0 --port ${API_PORT:-8000}"]
