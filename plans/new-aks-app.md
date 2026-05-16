---
name: new-aks-app
description: Scaffold a new TypeScript or Python hello-world web app with tests and deploy it to the Lingolou AKS cluster in its own namespace, alongside the existing Lingolou app. Use this skill when the user wants to create a new app on the shared AKS cluster, optionally with its own domain name.
---

# New AKS App

Scaffolds a new web app (TypeScript/Python) with tests, Dockerfile, Kubernetes manifests, and GitHub Actions CI/CD, then deploys it to the shared `lingolou-aks` cluster in an isolated namespace.

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

Confirm values with the user before writing any files.

---

### Step 2 — Scaffold the app in `REPO_PATH`

Work entirely inside `REPO_PATH`. If it is not a git repo, run `git init` first.

#### TypeScript (Express + Vitest)

**`package.json`**
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

export const app = express();

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
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
  it("returns ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ok");
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
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


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
    """Health check returns ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_root() -> None:
    """Root returns hello world."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Hello, world!"
```

**`pyproject.toml`**
```toml
[tool.pytest.ini_options]
addopts = "--cov=app --cov-report=term-missing"

[tool.ruff]
line-length = 100
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

### Step 3 — Dockerfile

Multi-stage, `linux/amd64`, non-root user. Create at repo root.

#### TypeScript
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

#### Python
```dockerfile
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN useradd -m app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Container port is **3000** (TypeScript) or **8000** (Python). Use the correct value in every manifest below.

---

### Step 4 — Kubernetes manifests in `k8s/`

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

**`k8s/ingress.yaml`** — cert-manager creates the TLS secret automatically from the annotation:
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

### Step 5 — GitHub Actions CI/CD

**`.github/workflows/deploy.yml`** — fires on `v*` tags:
```yaml
name: Deploy

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # TypeScript:
      - name: Test
        run: npm ci && npm test
      # Python — replace the step above with:
      # - name: Test
      #   run: pip install -r requirements.txt && pytest

      - name: Azure login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and push image
        run: |
          az acr login -n lingolou
          docker buildx build --platform linux/amd64 \
            -t lingolou.azurecr.io/APP_NAME:${{ github.ref_name }} \
            -t lingolou.azurecr.io/APP_NAME:latest --push .

      - name: Set kubectl context
        run: az aks get-credentials -g Lingolou -n lingolou-aks --overwrite-existing

      - name: Deploy
        run: |
          kubectl set image deployment/APP_NAME \
            APP_NAME=lingolou.azurecr.io/APP_NAME:${{ github.ref_name }} \
            -n APP_NAME
          kubectl rollout status deployment/APP_NAME -n APP_NAME
```

Create the `AZURE_CREDENTIALS` secret once:
```bash
az ad sp create-for-rbac --name "github-APP_NAME" \
  --role contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/Lingolou \
  --sdk-auth
# copy the JSON output → GitHub repo → Settings → Secrets → AZURE_CREDENTIALS
```

---

### Step 6 — Domain setup

#### Option A — New domain at a registrar

1. Register the domain at any registrar (GoDaddy, Namecheap, Cloudflare Registrar, etc.)
2. Go to the registrar's DNS management panel
3. Add an **A record**:
   - Host: `@` (apex) or `www` (subdomain only)
   - Value: `57.151.44.179`
   - TTL: 3600

**GoDaddy-specific:** You cannot change a CNAME to an A record in-place — delete the CNAME first, then add the A record.

Verify against the authoritative nameserver (bypasses local cache):
```bash
# Find your registrar's authoritative NS:
dig DOMAIN NS +short

# Verify the A record against it:
dig DOMAIN A +short @<ns-from-above>
# Should return: 57.151.44.179
```

#### Option B — Subdomain of an existing domain

Add a subdomain record at the existing DNS provider (no registrar change needed):
- Host: `APP_NAME` (e.g. `myapp` → resolves as `myapp.lingolou.app`)
- Value: `57.151.44.179`
- TTL: 3600

#### TLS — cert-manager handles it automatically

Once the A record propagates and manifests are applied, cert-manager detects the Ingress annotation and runs an HTTP-01 ACME challenge. No manual cert work needed.

Timeline: DNS propagation is usually 1–5 minutes for existing domains. New registrations at slow registrars can take up to 48h. The ACME challenge completes within ~60 seconds of DNS resolving.

---

### Step 7 — Initial deploy

Run in order. All secrets are passed via CLI — never written to disk.

```bash
# 1. Get AKS credentials
az aks get-credentials -g Lingolou -n lingolou-aks --overwrite-existing

# 2. Create namespace first (all other resources reference it)
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
kubectl rollout status deployment/APP_NAME -n APP_NAME
```

---

### Step 8 — Verify TLS and connectivity

```bash
# Watch for certificate issuance (~30s–2min after DNS propagates)
kubectl get certificate -n APP_NAME -w

# Once READY=True:
curl https://DOMAIN/health
# → {"status":"ok"}

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

- [ ] App scaffolded, tests pass locally
- [ ] Dockerfile builds cleanly for `linux/amd64`
- [ ] `k8s/` manifests created with real values (no placeholders)
- [ ] GitHub Actions workflow added, `AZURE_CREDENTIALS` secret set
- [ ] Namespace created in cluster
- [ ] ACR pull secret created in the new namespace
- [ ] Image built and pushed to `lingolou.azurecr.io/APP_NAME:latest`
- [ ] All manifests applied (`kubectl apply -f k8s/`)
- [ ] DNS A record `DOMAIN → 57.151.44.179` added at registrar
- [ ] DNS verified against authoritative nameserver
- [ ] `kubectl get certificate -n APP_NAME` shows `READY: True`
- [ ] `curl https://DOMAIN/health` returns `{"status":"ok"}`
