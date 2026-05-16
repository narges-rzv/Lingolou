---
name: new-aks-app
description: Scaffold a new TypeScript or Python hello-world web app with tests and deploy it to the Lingolou AKS cluster in its own namespace, alongside the existing Lingolou app. Use this skill when the user wants to create a new app on the shared AKS cluster, optionally with its own domain name.
---

# New AKS App

Scaffolds a new web app (TypeScript/Python) with tests, Dockerfile, Makefile, Kubernetes manifests, and GitHub Actions CI/CD, then deploys it to the shared `lingolou-aks` cluster in an isolated namespace.

## Shared infrastructure (do not recreate)

| Resource | Name |
|---|---|
| AKS cluster | `lingolou-aks`, resource group `Lingolou`, region `eastus` |
| Container registry | `lingolou.azurecr.io` (admin user: `lingolou`) |
| Ingress controller | `ingress-nginx` in namespace `ingress-nginx`, public IP `57.151.44.179` |
| TLS issuer | `cert-manager` in namespace `cert-manager`, ClusterIssuer `letsencrypt-prod` |

The new app lives entirely in its own namespace (`APP_NAME`). It shares nothing with the `lingolou` namespace.

---

## Implementation Steps

### Step 1 — Gather configuration

Ask the user for these values before doing anything else:

| Variable | Description | Example |
|---|---|---|
| `APP_NAME` | Slug — used for namespace, image tag, and all k8s resource names | `myapp` |
| `LANGUAGE` | `typescript` or `python` | `typescript` |
| `REPO_PATH` | Absolute path to the target git repository | `/Users/narges/git/myapp` |
| `DOMAIN` | Fully-qualified domain for this app | `myapp.example.com` |

Confirm values with the user before writing any files. If `REPO_PATH` is not a git repo, run `git init` first.

---

### Step 2 — Scaffold the app in `REPO_PATH`

#### TypeScript (Express + Vitest)

**`package.json`** — version starts at `0.1.0`; `bump-my-version` keeps it in sync with git tags:
```json
{
  "name": "APP_NAME",
  "version": "0.1.0",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "vitest run --coverage",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/node": "^20.0.0",
    "@types/supertest": "^6.0.2",
    "@vitest/coverage-v8": "^1.0.0",
    "supertest": "^6.3.4",
    "tsx": "^4.0.0",
    "typescript": "^5.3.0",
    "vitest": "^1.0.0"
  }
}
```

**`tsconfig.json`**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

**`src/app.ts`** — exported separately so tests import it without binding a port:
```typescript
import express from "express";
import { readFileSync } from "fs";
import { join } from "path";

export const app = express();

function getVersion(): string {
  try {
    const pkg = JSON.parse(readFileSync(join(__dirname, "../package.json"), "utf-8")) as { version: string };
    return pkg.version;
  } catch {
    return "unknown";
  }
}

app.get("/health", (_req, res) => {
  res.json({ status: "ok", version: getVersion() });
});

app.get("/", (_req, res) => {
  res.json({ message: "Hello, world!" });
});
```

**`src/index.ts`**
```typescript
import { app } from "./app";

const PORT = process.env.PORT ?? 3000;
app.listen(PORT, () => {
  console.log(`Listening on :${PORT}`);
});
```

**`src/app.test.ts`**
```typescript
import { describe, it, expect } from "vitest";
import request from "supertest";
import { app } from "./app";

describe("GET /health", () => {
  it("returns ok with version", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ok");
    expect(typeof res.body.version).toBe("string");
  });
});

describe("GET /", () => {
  it("returns hello world", async () => {
    const res = await request(app).get("/");
    expect(res.status).toBe(200);
    expect(res.body.message).toBe("Hello, world!");
  });
});
```

**`vitest.config.ts`**
```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: { provider: "v8", reporter: ["text", "lcov"] },
  },
});
```

**`.gitignore`**
```
node_modules/
dist/
coverage/
```

#### Python (FastAPI + pytest)

**`pyproject.toml`** — version field is kept in sync with git tags by `bump-my-version`:
```toml
[project]
version = "0.1.0"

[tool.bumpversion]
current_version = "0.1.0"
commit = true
tag = true
tag_name = "v{new_version}"

[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'current_version = "{current_version}"'
replace = 'current_version = "{new_version}"'

[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'version = "{current_version}"'
replace = 'version = "{new_version}"'

[tool.pytest.ini_options]
addopts = "--cov=app --cov-report=term-missing"

[tool.ruff]
line-length = 100
```

**`requirements.txt`**
```
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
httpx>=0.27.0
pytest>=8.0.0
pytest-cov>=5.0.0
```

**`app/main.py`**
```python
"""Hello world FastAPI application."""
import tomllib
from pathlib import Path

from fastapi import FastAPI

def _get_version() -> str:
    try:
        with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        return "unknown"

app = FastAPI(title="APP_NAME", version=_get_version())


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": app.version}


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Hello, world!"}
```

**`app/test_main.py`**
```python
"""Tests for the main application."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health() -> None:
    """Health check returns ok with version."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert isinstance(resp.json()["version"], str)


def test_root() -> None:
    """Root returns hello world."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Hello, world!"
```

**`.gitignore`**
```
__pycache__/
.pytest_cache/
.coverage
htmlcov/
```

Verify tests pass locally before continuing:
```bash
# TypeScript
npm ci && npm test

# Python
pip install -r requirements.txt && pytest
```

---

### Step 3 — Makefile

Create a `Makefile` at repo root. Adapt the language-specific targets to the chosen stack.

#### TypeScript
```makefile
.PHONY: install dev build test lint all docker-build docker-push aks-context aks-deploy aks-logs aks-status aks-restart release-patch release-minor release-major

ACR_IMAGE ?= lingolou.azurecr.io/APP_NAME:latest

install:
	npm ci

dev:
	npm run dev

build:
	npm run build

lint:
	npm run lint

test:
	npm test

all: lint test

docker-build:
	docker build -t lingolou.azurecr.io/APP_NAME:latest .

docker-push:
	docker buildx build --platform linux/amd64 -t $(ACR_IMAGE) --push .

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

release-patch:
	bump-my-version bump patch
	git push && git push --tags

release-minor:
	bump-my-version bump minor
	git push && git push --tags

release-major:
	bump-my-version bump major
	git push && git push --tags
```

#### Python
```makefile
.PHONY: install dev test lint format all docker-build docker-push aks-context aks-deploy aks-logs aks-status aks-restart release-patch release-minor release-major

ACR_IMAGE ?= lingolou.azurecr.io/APP_NAME:latest

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --port 8000

lint:
	ruff check . && ruff format --check .

format:
	ruff format . && ruff check --fix .

test:
	pytest

all: format lint test

docker-build:
	docker build -t lingolou.azurecr.io/APP_NAME:latest .

docker-push:
	docker buildx build --platform linux/amd64 -t $(ACR_IMAGE) --push .

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

release-patch:
	bump-my-version bump patch
	git push && git push --tags

release-minor:
	bump-my-version bump minor
	git push && git push --tags

release-major:
	bump-my-version bump major
	git push && git push --tags
```

Install `bump-my-version` once (global):
```bash
pip install bump-my-version
```

For TypeScript, add a `[[tool.bumpversion.files]]` entry in a `pyproject.toml` (or `.bumpversion.toml`) at the repo root targeting `package.json`:
```toml
[tool.bumpversion]
current_version = "0.1.0"
commit = true
tag = true
tag_name = "v{new_version}"

[[tool.bumpversion.files]]
filename = "package.json"
search = '"version": "{current_version}"'
replace = '"version": "{new_version}"'
```

---

### Step 4 — Dockerfile

Multi-stage, `linux/amd64`, non-root user. Create at repo root.

#### TypeScript (port 3000)
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package.json .
USER app
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

#### Python (port 8000)
```dockerfile
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN useradd -m app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Use the correct `PORT` (3000 or 8000) in every k8s manifest below.

---

### Step 5 — Kubernetes manifests in `k8s/`

Substitute real values for `APP_NAME`, `DOMAIN`, and `PORT` — do not leave placeholders.

**`k8s/namespace.yaml`**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: APP_NAME
```

**`k8s/deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: APP_NAME
  namespace: APP_NAME
spec:
  replicas: 1
  selector:
    matchLabels:
      app: APP_NAME
  template:
    metadata:
      labels:
        app: APP_NAME
    spec:
      imagePullSecrets:
        - name: acr-secret
      containers:
        - name: APP_NAME
          image: lingolou.azurecr.io/APP_NAME:latest
          ports:
            - containerPort: PORT
          readinessProbe:
            httpGet:
              path: /health
              port: PORT
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 256Mi
```

**`k8s/service.yaml`**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: APP_NAME
  namespace: APP_NAME
spec:
  selector:
    app: APP_NAME
  ports:
    - port: 80
      targetPort: PORT
```

**`k8s/ingress.yaml`**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: APP_NAME
  namespace: APP_NAME
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - DOMAIN
      secretName: APP_NAME-tls
  rules:
    - host: DOMAIN
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: APP_NAME
                port:
                  number: 80
```

---

### Step 6 — GitHub Actions

Two workflows: CI runs on every push (except tags); deploy runs only on `v*` tags.

**`.github/workflows/ci.yml`**
```yaml
name: CI

on:
  push:
    branches: ["**"]
    tags-ignore: ["v*"]
  pull_request:

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # TypeScript:
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: make install
      - run: make all

      # Python — replace the three steps above with:
      # - uses: actions/setup-python@v5
      #   with:
      #     python-version: "3.12"
      # - run: make install
      # - run: make all
```

**`.github/workflows/deploy.yml`**
```yaml
name: Build and Deploy to AKS

on:
  push:
    tags:
      - "v*"

env:
  ACR_REGISTRY: lingolou.azurecr.io
  IMAGE_NAME: APP_NAME
  RESOURCE_GROUP: Lingolou
  AKS_CLUSTER: lingolou-aks

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # TypeScript:
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Lint and test
        run: make install && make all

      # Python — replace the two steps above with:
      # - uses: actions/setup-python@v5
      #   with:
      #     python-version: "3.12"
      # - name: Lint and test
      #   run: make install && make all

      - name: Extract version from tag
        id: version
        run: echo "tag=${GITHUB_REF#refs/tags/}" >> "$GITHUB_OUTPUT"

      - name: Write VERSION file
        run: echo "${{ steps.version.outputs.tag }}" > VERSION

      - name: Log in to Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Log in to ACR
        uses: azure/docker-login@v2
        with:
          login-server: ${{ env.ACR_REGISTRY }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}

      - name: Build and push Docker image
        run: |
          docker buildx build --platform linux/amd64 \
            -t ${{ env.ACR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.version.outputs.tag }} \
            -t ${{ env.ACR_REGISTRY }}/${{ env.IMAGE_NAME }}:latest \
            --push .

      - name: Set AKS context
        uses: azure/aks-set-context@v4
        with:
          resource-group: ${{ env.RESOURCE_GROUP }}
          cluster-name: ${{ env.AKS_CLUSTER }}

      - name: Deploy to AKS
        run: |
          kubectl set image deployment/${{ env.IMAGE_NAME }} \
            ${{ env.IMAGE_NAME }}=${{ env.ACR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.version.outputs.tag }} \
            -n ${{ env.IMAGE_NAME }}
          kubectl rollout status deployment/${{ env.IMAGE_NAME }} \
            -n ${{ env.IMAGE_NAME }} --timeout=120s

      - name: Purge old ACR images
        run: |
          az acr run \
            --cmd "mcr.microsoft.com/acr/acr-cli:0.16 purge \
              --filter '${{ env.IMAGE_NAME }}:v*' \
              --keep 3 \
              --ago 0d \
              --untagged" \
            --registry lingolou \
            /dev/null
```

#### Required GitHub secrets

| Secret | How to get it |
|---|---|
| `AZURE_CREDENTIALS` | `az ad sp create-for-rbac --name "github-APP_NAME" --role contributor --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/Lingolou --sdk-auth` |
| `ACR_USERNAME` | `az acr credential show -n lingolou --query username -o tsv` |
| `ACR_PASSWORD` | `az acr credential show -n lingolou --query passwords[0].value -o tsv` |

Add all three at GitHub repo → Settings → Secrets and variables → Actions.

---

### Step 7 — Domain setup

#### Option A — New domain at a registrar

1. Register the domain (GoDaddy, Namecheap, Cloudflare Registrar, etc.)
2. In the DNS management panel, add an **A record**:
   - Host: `@` (apex) or `www`
   - Value: `57.151.44.179`
   - TTL: 3600

**GoDaddy-specific:** you cannot convert a CNAME to an A record in-place — delete the CNAME first, then add the A record.

Verify against the authoritative nameserver (bypasses local TTL cache):
```bash
dig DOMAIN NS +short          # find your registrar's NS
dig DOMAIN A +short @<ns>     # should return 57.151.44.179
```

#### Option B — Subdomain of an existing domain

Add a single DNS record at the existing provider (no registrar change):
- Host: `APP_NAME` (e.g. `myapp` → `myapp.lingolou.app`)
- Value: `57.151.44.179`
- TTL: 3600

#### TLS

cert-manager detects the Ingress annotation and runs an HTTP-01 ACME challenge automatically. DNS propagation for existing domains is typically 1–5 minutes. New registrations at slow registrars can take up to 48h.

---

### Step 8 — Initial deploy

Run in order. Secrets are passed via CLI — never written to disk.

```bash
# 1. Get AKS credentials
az aks get-credentials -g Lingolou -n lingolou-aks

# 2. Create namespace first
kubectl apply -f k8s/namespace.yaml

# 3. Create ACR pull secret scoped to the new namespace
kubectl create secret docker-registry acr-secret -n APP_NAME \
  --docker-server=lingolou.azurecr.io \
  --docker-username=lingolou \
  --docker-password="$(az acr credential show -n lingolou --query passwords[0].value -o tsv)"

# 4. Build and push initial image
az acr login -n lingolou
docker buildx build --platform linux/amd64 \
  -t lingolou.azurecr.io/APP_NAME:v0.1.0 \
  -t lingolou.azurecr.io/APP_NAME:latest --push .

# 5. Apply all remaining manifests
kubectl apply -f k8s/

# 6. Wait for rollout
kubectl rollout status deployment/APP_NAME -n APP_NAME --timeout=120s
```

Subsequent deploys: `make release-patch` (or `release-minor` / `release-major`) bumps the version, commits, pushes the tag, and CI/CD takes over from there.

---

### Step 9 — Verify TLS and connectivity

```bash
# Watch for certificate issuance (~30s–2min after DNS propagates)
kubectl get certificate -n APP_NAME -w

# Once READY=True:
curl https://DOMAIN/health
# → {"status":"ok","version":"0.1.0"}

curl https://DOMAIN/
# → {"message":"Hello, world!"}
```

If the certificate stays `READY=False` longer than 5 minutes:
```bash
kubectl describe certificaterequest -n APP_NAME
kubectl describe order -n APP_NAME
```

Common causes: DNS not yet propagated; port 80 LB probe issue (see pitfall #7 in `plans/aks-migration-status.md`).

---

## Checklist

- [ ] App scaffolded, tests pass locally (`make test`)
- [ ] `make all` passes (lint + test)
- [ ] Dockerfile builds cleanly for `linux/amd64`
- [ ] `k8s/` manifests written with real values (no placeholders)
- [ ] Both GitHub Actions workflows added
- [ ] `AZURE_CREDENTIALS`, `ACR_USERNAME`, `ACR_PASSWORD` secrets set in GitHub
- [ ] `bump-my-version` installed, config in `pyproject.toml` / `.bumpversion.toml`
- [ ] Namespace created in cluster
- [ ] ACR pull secret created in the new namespace
- [ ] Initial image built and pushed to ACR
- [ ] All manifests applied (`kubectl apply -f k8s/`)
- [ ] DNS A record `DOMAIN → 57.151.44.179` added and verified
- [ ] `kubectl get certificate -n APP_NAME` shows `READY: True`
- [ ] `curl https://DOMAIN/health` returns `{"status":"ok","version":"..."}`
