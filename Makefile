.PHONY: test test-backend test-frontend test-e2e test-all test-install

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
