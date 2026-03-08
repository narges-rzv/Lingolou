# Stage 1: Build frontend
FROM node:18-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg redis-server && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY webapp/ webapp/
COPY alembic.ini .
COPY --from=frontend /app/webapp/static/frontend/ webapp/static/frontend/
COPY generate_story.py generate_audiobook.py ./
COPY story_config.json ./
COPY VERSION* ./
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh
EXPOSE 8000
CMD ["./entrypoint.sh"]
