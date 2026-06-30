FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r /app/apps/onprem-api/requirements.txt && \
    prisma generate --schema /app/packages/db/prisma/schema.prisma

EXPOSE 8002

CMD ["sh", "-c", "cd /app/apps/onprem-api && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8002}"]
