---
name: new-aks-app
description: Scaffold a new FastAPI + React/TypeScript app (or add AKS deployment, Redis, or persistent storage to an existing one) on the shared lingolou-aks cluster. Templates live in plans/new-aks-app/templates/.
---

# New AKS App

Scaffolds a **Python FastAPI backend + React/TypeScript frontend** (the same architecture as Lingolou), with Kubernetes manifests, GitHub Actions CI/CD, and optional Redis sidecar or Azure Files persistent storage. All template files live in `plans/new-aks-app/templates/`.

> **For existing apps**: Skip Step 2. Use the template files as a reference — copy what you need (k8s manifests, workflows, etc.) into the existing repo and substitute `APP_NAME`/`DOMAIN` throughout.

## Shared infrastructure (do not recreate)

| Resource | Name |
|---|---|
| AKS cluster | `lingolou-aks`, resource group `Lingolou`, region `eastus` |
| Container registry | `lingolou.azurecr.io` (admin user: `lingolou`) |
| Ingress controller | `ingress-nginx` in namespace `ingress-nginx`, public IP `57.151.44.179` |
| TLS issuer | `cert-manager` in namespace `cert-manager`, ClusterIssuer `letsencrypt-prod` |

The new app lives entirely in its own namespace (`APP_NAME`). It shares nothing with the `lingolou` namespace.

---

## Step 1 — Gather configuration

Ask the user for these values before doing anything else:

| Variable | Description | Example |
|---|---|---|
| `APP_NAME` | Slug — used for namespace, image tag, and all k8s resource names | `myapp` |
| `REPO_PATH` | Absolute path to the target git repository | `/Users/narges/git/myapp` |
| `DOMAIN` | Fully-qualified domain for this app | `myapp.example.com` |

Also confirm which **optional infrastructure** the app needs:

- [ ] **Persistent storage** (Azure Files PVC) — required if the app writes files to disk, uses SQLite, or needs Redis data to survive pod restarts
- [ ] **Redis sidecar** — for caching, sessions, task queues, or pub/sub (`REDIS_URL=redis://localhost:6379`)
- [ ] **Managed NoSQL** (Azure Cosmos DB) — document store accessed via connection string; no extra k8s manifests needed

Confirm all values with the user before writing any files. If `REPO_PATH` is not a git repo, run `git init` first.

---

## Step 2 — Scaffold the app

> **Skip this step if the app already exists.** Jump to Step 3.

Copy template files from `plans/new-aks-app/templates/` into `REPO_PATH`, then substitute every occurrence of `APP_NAME` and `DOMAIN`.

### File layout (mirrors Lingolou)

```
REPO_PATH/
├── Dockerfile                          ← multi-stage: Node 18 builds frontend, Python 3.12 runs it
├── .dockerignore
├── entrypoint.sh                       ← uvicorn startup
├── Makefile
├── pyproject.toml                      ← ruff + mypy + bump-my-version config
├── requirements.txt
├── .gitignore
├── webapp/
│   ├── __init__.py
│   ├── main.py                         ← FastAPI app; mounts static assets, /health, SPA catch-all
│   └── tests/
│       ├── conftest.py
│       └── test_health.py
└── frontend/                           ← React + TypeScript; Vite builds into webapp/static/frontend/
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── tsconfig.app.json
    ├── tsconfig.node.json
    ├── vite.config.ts                  ← outDir: ../webapp/static/frontend; /api proxy → :8000
    ├── vitest.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        └── test/
            ├── setup.ts
            └── App.test.tsx
```

### How backend and frontend connect

- **Dev**: `make dev` runs FastAPI on `:8000` and Vite on `:5173`. `vite.config.ts` proxies `/api/*` and `/static/*` to `:8000`, so the browser always hits real API endpoints.
- **Production**: `npm run build` compiles the SPA into `webapp/static/frontend/`. FastAPI mounts `/assets` as static files and serves `index.html` for every non-API path. Single Docker image, single port (8000).

### After copying templates

1. Replace every `APP_NAME` occurrence with the actual slug.
2. Replace every `DOMAIN` occurrence with the actual domain.
3. Edit `webapp/main.py` — set `title=` in `FastAPI(...)` to a human-readable name.
4. Edit `frontend/index.html` — set `<title>` to the app name.
5. Verify locally:

```bash
cd REPO_PATH
make install
make all         # format → lint → test — must pass before continuing
```

---

## Step 3 — Kubernetes manifests

Copy `plans/new-aks-app/templates/k8s/` into `REPO_PATH/k8s/`. Substitute `APP_NAME` and `DOMAIN` — no placeholders in deployed files.

| File | Purpose |
|---|---|
| `k8s/namespace.yaml` | Isolated namespace |
| `k8s/deployment.yaml` | Pod spec: app container, probes, resource limits |
| `k8s/service.yaml` | ClusterIP mapping port 80 → 8000 |
| `k8s/ingress.yaml` | nginx ingress + cert-manager TLS for `DOMAIN` |

### Optional: Redis sidecar

Use `plans/new-aks-app/templates/k8s-optional/deployment-with-redis.yaml` **instead of** the base `k8s/deployment.yaml`. It adds:

- A `redis:7-alpine` sidecar container
- `REDIS_URL=redis://localhost:6379` env var on the app container
- `volumeMounts` for both containers using the Azure Files PVC (subPath `redis/` for Redis data)

> Redis **with** a PVC persists data across pod restarts. Redis **without** a PVC is ephemeral — acceptable for pure caching.

### Optional: Persistent storage (Azure Files PVC)

Required if the app uses SQLite, writes files to disk, or needs Redis data to survive restarts.

1. Create the storage account and file share:
   ```bash
   az storage account create --name APP_NAMEdisk --resource-group Lingolou --sku Standard_LRS
   STORAGE_KEY=$(az storage account keys list --account-name APP_NAMEdisk --query '[0].value' -o tsv)
   az storage share create --account-name APP_NAMEdisk --name APP_NAME-data --account-key "$STORAGE_KEY"
   ```

2. Create the Kubernetes secret with storage credentials (in the app namespace):
   ```bash
   STORAGE_KEY=$(az storage account keys list --account-name APP_NAMEdisk --query '[0].value' -o tsv)
   kubectl create secret generic azure-files-secret -n APP_NAME \
     --from-literal=azurestorageaccountname=APP_NAMEdisk \
     --from-literal=azurestorageaccountkey="$STORAGE_KEY"
   ```

3. Copy `plans/new-aks-app/templates/k8s-optional/pvc.yaml` into `REPO_PATH/k8s/pvc.yaml`, substitute `APP_NAME`, and apply it after creating the namespace (Step 6).

### Optional: Managed NoSQL (Azure Cosmos DB)

No extra k8s manifests — Cosmos DB is accessed via a connection string stored in the app secret.

```bash
az cosmosdb create --name APP_NAME-cosmos --resource-group Lingolou \
  --kind MongoDB --capabilities EnableMongo

# Get connection string to add to the k8s secret in Step 6
az cosmosdb keys list --name APP_NAME-cosmos --resource-group Lingolou \
  --type connection-strings --query connectionStrings[0].connectionString -o tsv
```

---

## Step 4 — GitHub Actions

Copy `plans/new-aks-app/templates/.github/` into `REPO_PATH/.github/`. Substitute `APP_NAME` in both workflow files.

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | push to any branch (not `v*` tags) | `make install && make all` (lint + test) |
| `deploy.yml` | push of `v*` tag | lint+test → Docker build+push → `kubectl set image` → ACR purge |

### Required GitHub secrets

Set at GitHub repo → Settings → Secrets and variables → Actions:

| Secret | Command to get the value |
|---|---|
| `AZURE_CREDENTIALS` | `az ad sp create-for-rbac --name "github-APP_NAME" --role contributor --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/Lingolou --sdk-auth` |
| `ACR_USERNAME` | `az acr credential show -n lingolou --query username -o tsv` |
| `ACR_PASSWORD` | `az acr credential show -n lingolou --query passwords[0].value -o tsv` |

---

## Step 5 — Domain setup

### Option A — New domain at a registrar

1. Register the domain.
2. Add an **A record**: host `@` (apex) or `www`, value `57.151.44.179`, TTL 3600.

**GoDaddy-specific:** delete any existing CNAME first, then add the A record.

Verify against the authoritative nameserver (bypasses TTL cache):
```bash
dig DOMAIN NS +short        # find registrar's nameserver
dig DOMAIN A +short @<ns>   # should return 57.151.44.179
```

### Option B — Subdomain of existing domain

Add a single DNS record at the existing provider:
- Host: `APP_NAME` (e.g. `myapp` → `myapp.lingolou.app`)
- Value: `57.151.44.179`, TTL 3600

### TLS

cert-manager detects the Ingress annotation and issues a certificate via HTTP-01 ACME automatically. DNS propagation for existing domains: 1–5 min. New registrations: up to 48h.

---

## Step 6 — Initial deploy

Run in order. Secrets are passed via CLI — never written to disk.

```bash
# 1. Get AKS credentials
az aks get-credentials -g Lingolou -n lingolou-aks

# 2. Create namespace
kubectl apply -f k8s/namespace.yaml

# 3. Create ACR pull secret
kubectl create secret docker-registry acr-secret -n APP_NAME \
  --docker-server=lingolou.azurecr.io \
  --docker-username=lingolou \
  --docker-password="$(az acr credential show -n lingolou --query passwords[0].value -o tsv)"

# 4. Create app secrets (add all required env vars for this app)
kubectl create secret generic APP_NAME-secrets -n APP_NAME \
  --from-literal=SESSION_SECRET_KEY="$(openssl rand -hex 32)"
  # add more: --from-literal=MONGODB_URL=... etc.

# 5. If using Azure Files PVC — create the azure-files-secret first (Step 3), then:
# kubectl apply -f k8s/pvc.yaml

# 6. Build and push initial image
az acr login -n lingolou
docker buildx build --platform linux/amd64 \
  -t lingolou.azurecr.io/APP_NAME:v0.1.0 \
  -t lingolou.azurecr.io/APP_NAME:latest --push .

# 7. Apply all remaining manifests
kubectl apply -f k8s/

# 8. Wait for rollout
kubectl rollout status deployment/APP_NAME -n APP_NAME --timeout=120s
```

Subsequent deploys: `make release-patch` bumps the version, commits, pushes the tag, and CI/CD takes over.

---

## Step 7 — Verify TLS and connectivity

```bash
# Watch for certificate issuance (~30s–2min after DNS propagates)
kubectl get certificate -n APP_NAME -w

# Once READY=True:
curl https://DOMAIN/health
# → {"status":"healthy","version":"0.1.0"}

curl https://DOMAIN/
# → serves the React SPA (index.html)
```

If the certificate stays `READY=False` longer than 5 minutes:
```bash
kubectl describe certificaterequest -n APP_NAME
kubectl describe order -n APP_NAME
```

Common causes: DNS not yet propagated; port 80 blocked at registrar or firewall.

---

## Step 8 — Create `.claude/CLAUDE.md` in the new repo

Copy `plans/new-aks-app/templates/.claude/CLAUDE.md` into `REPO_PATH/.claude/CLAUDE.md`. Fill in the project summary and any app-specific details.

---

## Checklist

- [ ] Template files copied and `APP_NAME` / `DOMAIN` substituted throughout
- [ ] `make all` passes (format → lint → test)
- [ ] Dockerfile builds cleanly for `linux/amd64`
- [ ] `k8s/` manifests have no placeholders
- [ ] Both GitHub Actions workflows added and GitHub secrets set
- [ ] Namespace created in cluster
- [ ] ACR pull secret created in namespace
- [ ] App secrets created (`kubectl create secret generic APP_NAME-secrets`)
- [ ] `azure-files-secret` + `pvc.yaml` applied (if using persistent storage)
- [ ] Initial image built and pushed to ACR (`lingolou.azurecr.io/APP_NAME:v0.1.0`)
- [ ] All manifests applied (`kubectl apply -f k8s/`)
- [ ] DNS A record `DOMAIN → 57.151.44.179` verified
- [ ] `kubectl get certificate -n APP_NAME` shows `READY: True`
- [ ] `curl https://DOMAIN/health` returns `{"status":"healthy","version":"..."}`
- [ ] `.claude/CLAUDE.md` created in the new repo
