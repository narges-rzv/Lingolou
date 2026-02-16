.PHONY: test test-backend test-frontend test-e2e test-all test-install install dev lint format all

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
