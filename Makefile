ACR_IMAGE ?= lingolou.azurecr.io/lingolou-app:latest

.PHONY: test test-backend test-frontend test-e2e test-all test-install install dev lint format all docker-build docker-run docker-run-prod compose-up compose-down compose-test docker-push

# Install all dependencies (backend + frontend)
install:
	pip install -r requirements.txt
	cd frontend && npm install

# Start backend + frontend dev servers (kill both on Ctrl-C)
dev:
	@trap 'kill 0' EXIT; \
	uvicorn webapp.main:app --reload --port 8000 & \
	cd frontend && npm run dev & \
	wait

# Lint and type-check
lint:
	ruff check .
	ruff format --check .
	mypy webapp/ generate_story.py generate_audiobook.py test_voice.py

# Auto-fix lint issues and format
format:
	ruff format .
	ruff check --fix .

# Lint then test
all: format lint test

# Backend tests with coverage
test-backend:
	pytest --cov=webapp --cov-report=term-missing --cov-report=html

# Frontend unit/component tests with coverage
test-frontend:
	cd frontend && npx vitest run --coverage

# E2E tests (requires backend + frontend running)
test-e2e:
	cd frontend && npx playwright test

# Install all test dependencies
test-install:
	pip install pytest pytest-cov pytest-asyncio httpx
	cd frontend && npm install
	cd frontend && npx playwright install chromium

# Run all tests (fails if any suite fails or coverage below threshold)
test-all: test-backend test-frontend

# Alias
test: test-all

# Build Docker image
docker-build:
	docker build -t lingolou .

# Run with SQLite (local testing)
docker-run:
	docker run -p 8000:8000 -e SESSION_SECRET_KEY=$${SESSION_SECRET_KEY} lingolou

# Run with PostgreSQL
docker-run-prod:
	docker run -p 8000:8000 \
		-e DATABASE_URL=$${DATABASE_URL} \
		-e SESSION_SECRET_KEY=$${SESSION_SECRET_KEY} \
		-e FRONTEND_URL=$${FRONTEND_URL} \
		lingolou

# Docker Compose targets
compose-up:
	docker compose up -d

compose-down:
	docker compose down

compose-test:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
	docker compose -f docker-compose.test.yml down

# Build linux/amd64 image and push to Azure Container Registry
docker-push:
	docker buildx build --platform linux/amd64 -t $(ACR_IMAGE) --push .
