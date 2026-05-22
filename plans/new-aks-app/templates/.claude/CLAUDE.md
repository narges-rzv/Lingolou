# CLAUDE.md

## Project Summary

<!-- One sentence describing what this app does. -->

## Tech Stack

- **Backend**: FastAPI (Python 3.12+) in `webapp/`
- **Frontend**: React 18 + Vite + TypeScript (strict mode) in `frontend/`
- **Deployment**: AKS namespace `APP_NAME` on `lingolou-aks`, domain `DOMAIN`
- **CI/CD**: GitHub Actions — CI on all branches, deploy on `v*` tags

## Common Commands

```bash
make install       # install backend + frontend dependencies
make dev           # start FastAPI (:8000) + Vite (:5173)
make test          # backend (pytest) + frontend (vitest) tests
make lint          # ruff check + ruff format --check + mypy
make format        # ruff format + ruff check --fix
make all           # format → lint → test (run before committing)

make release-patch   # bump patch version, push tag → triggers deploy
make release-minor
make release-major

make aks-status      # kubectl get pods -n APP_NAME
make aks-logs        # tail app logs
make aks-restart     # rolling restart
```

## Architecture

**Dev**: FastAPI runs on `:8000`; Vite dev server on `:5173`. `vite.config.ts` proxies `/api/*` and `/static/*` to `:8000` — the browser always hits real API endpoints regardless of which server serves the HTML.

**Production**: `npm run build` compiles the SPA into `webapp/static/frontend/`. FastAPI mounts `/assets` as static files and serves `index.html` for every non-API path. Single Docker image, single port (8000).

## Code Quality

### Python (ruff + mypy)

Ruff enforces `ALL` rules (see `pyproject.toml` for the ignore list). mypy strict mode.

- All public functions and classes outside test files must have docstrings and fully type-annotated signatures.
- Suppress errors with specific codes and a reason, never bare ignores:
  - `# noqa: ANN401 — FastAPI Body() requires Any`
  - `# type: ignore[no-untyped-call] — library lacks stubs`

Tests in `webapp/tests/` are exempt from `D` and `ANN` rules.

### TypeScript (strict mode)

`tsconfig.app.json` sets `strict: true`, `noUnusedLocals`, `noUnusedParameters`, `noUncheckedIndexedAccess`.

- No `any` — use `unknown` with proper narrowing instead.
- All props and state must be explicitly typed.
- Suppress with `// @ts-expect-error — reason` (not `// @ts-ignore`).

## Testing

- **Backend**: `webapp/tests/` — pytest + FastAPI TestClient, shared fixtures in `conftest.py`
- **Frontend**: `frontend/src/test/` — Vitest + React Testing Library
- Every new feature needs tests covering the happy path and key failure modes
- Coverage must not decrease; `make test` must pass before committing

## When Making Changes

1. Write tests in the same commit as the code.
2. Run `make all` before committing.
3. Update `README.md` for user-facing changes; update this file for architectural changes.
4. Deferred work goes in `plans/`.
5. New backend dependencies → `requirements.txt`; new frontend dependencies → `frontend/package.json` + commit the lock file.

## Deployment

- **Release**: `make release-patch` — bumps version in `pyproject.toml`, `webapp/main.py`, and `frontend/package.json`; pushes tag; CI/CD deploys automatically.
- **Manual apply**: `make aks-deploy` (apply k8s manifests), `make aks-restart` (rolling restart).
- **Secrets**: stored in Kubernetes (`kubectl create secret generic APP_NAME-secrets`) — never in files or env vars on disk.
- **Infra**: shared ingress at `57.151.44.179`, cert-manager issues TLS from `letsencrypt-prod` automatically.

## Environment Variables

Required in `.env` for local development (not committed):

```bash
# Add app-specific env vars here
```

In production, set via `kubectl create secret generic APP_NAME-secrets -n APP_NAME`.
