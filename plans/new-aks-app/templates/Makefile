ACR_IMAGE ?= lingolou.azurecr.io/APP_NAME:latest

.PHONY: install dev lint format test-backend test-frontend test all \
        docker-build docker-run docker-push az-login \
        aks-context aks-deploy aks-logs aks-status aks-restart \
        aks-backup aks-backup-list \
        release-patch release-minor release-major

install:
	pip install -r requirements.txt
	cd frontend && npm install

dev:
	@trap 'kill 0' EXIT; \
	uvicorn webapp.main:app --reload --port 8000 & \
	cd frontend && npm run dev & \
	wait

lint:
	ruff check .
	ruff format --check .
	mypy webapp/

format:
	ruff format .
	ruff check --fix .

test-backend:
	pytest --cov=webapp --cov-report=term-missing --cov-report=html

test-frontend:
	cd frontend && npx vitest run --coverage

test: test-backend test-frontend

all: format lint test

docker-build:
	docker build -t APP_NAME .

docker-run:
	docker run -p 8000:8000 APP_NAME

docker-push:
	docker buildx build --platform linux/amd64 -t $(ACR_IMAGE) --push .

az-login:
	az login
	az acr login -n lingolou

aks-context:
	az aks get-credentials -g Lingolou -n lingolou-aks

aks-deploy:
	kubectl apply -f k8s/

aks-logs:
	kubectl logs -n APP_NAME deployment/APP_NAME -f

aks-status:
	kubectl get pods -n APP_NAME

aks-restart:
	kubectl rollout restart deployment/APP_NAME -n APP_NAME

# Azure Files snapshots — only relevant if the app uses a PVC
aks-backup:
	az storage share snapshot --account-name APP_NAMEdisk --name APP_NAME-data --output tsv

aks-backup-list:
	az storage share list --account-name APP_NAMEdisk --include-snapshots \
	  --query "[?name=='APP_NAME-data'].snapshot" --output tsv

release-patch:
	bump-my-version bump patch
	git push && git push --tags

release-minor:
	bump-my-version bump minor
	git push && git push --tags

release-major:
	bump-my-version bump major
	git push && git push --tags
