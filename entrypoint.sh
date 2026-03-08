#!/bin/sh
set -e

# Start embedded Redis for task persistence
mkdir -p "${REDIS_DATA_DIR:-/app/data/redis}"
redis-server --daemonize yes \
  --dir "${REDIS_DATA_DIR:-/app/data/redis}" \
  --save "60 1" \
  --maxmemory 128mb \
  --maxmemory-policy allkeys-lru \
  --loglevel warning

# Wait for Redis to be ready (max 5s)
for i in $(seq 1 50); do
  redis-cli ping >/dev/null 2>&1 && break
  sleep 0.1
done

export REDIS_URL="${REDIS_URL:-redis://localhost:6379}"

exec uvicorn webapp.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'
