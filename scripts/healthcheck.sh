#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://localhost:8000/ >/dev/null
curl -fsS http://localhost:3000/ >/dev/null
curl -fsS http://localhost:3001/ >/dev/null

echo "All services are responding."
