#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose up --build -d

echo "Kinga on-premise is starting."
echo "- API: http://localhost:8000"
echo "- Admin UI: http://localhost:3000"
echo "- Web UI: http://localhost:3001"
