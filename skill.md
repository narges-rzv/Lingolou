# Lingolou Project Context

> This file captures the current state of the project for resuming conversations with clean context.

## Project Overview

**Lingolou** is a language learning audiobook generator with:
- **Backend**: FastAPI + Celery + Redis for background tasks
- **Frontend**: React (Vite) SPA
- **Database**: SQLite (local dev), needs PostgreSQL for cloud
- **Audio**: ElevenLabs API
- **Story Generation**: OpenAI API

## Repository

- **Location**: `/Users/narges/git/Lingolou`
- **Remote**: `github.com:narges-rzv/Lingolou.git`
- **Branch**: `main`

## Recent Changes (This Session)

### 1. Added Google OAuth Login

**Files created:**
- `webapp/services/oauth.py` — Authlib config for Google OpenID Connect
- `webapp/api/oauth.py` — `/api/auth/oauth/google/login` and `/callback` endpoints

**Files modified:**
- `webapp/models/database.py` — Added `oauth_provider`, `oauth_id` columns; made `hashed_password` nullable
- `webapp/services/auth.py` — Guard `authenticate_user()` against OAuth-only users (no password)
- `webapp/main.py` — Added `SessionMiddleware`, included `oauth.router`
- `frontend/src/context/AuthContext.jsx` — Handle `?token=` URL param from OAuth redirect
- `frontend/src/pages/Login.jsx` — Google login button with SVG icon
- `frontend/src/app.css` — OAuth button styles
- `requirements.txt` & `webapp/requirements.txt` — Added `authlib>=1.3.0`, `httpx>=0.27.0`

**Commits:**
- `34f8178` — Add Google & Facebook OAuth login with React frontend
- `6964061` — Remove Facebook OAuth login (keep Google only)

### 2. Updated .gitignore

Added exclusions for:
- `.env`
- `*.ignore`
- `client_secret*.json`
- `*.db`

### 3. Updated README

- OAuth environment variables
- Detailed Google Cloud Console setup guide
- Removed Facebook references

## Pending Git State

There are unstaged changes in:
- `webapp/api/auth.py`
- `webapp/api/stories.py`
- `webapp/models/schemas.py`

These were not part of the OAuth work and weren't committed.

## OAuth Flow

```
1. User clicks "Sign in with Google" on Login page
2. Browser → GET /api/auth/oauth/google/login
3. Backend redirects → Google consent screen
4. User grants consent → Google redirects to /api/auth/oauth/google/callback
5. Backend exchanges code for user info, finds/creates user, issues JWT
6. Backend redirects → http://localhost:5173/login?token=<jwt>
7. Frontend stores token, cleans URL, loads dashboard
```

**Account linking logic** (in `_get_or_create_oauth_user`):
1. Match by `(oauth_provider, oauth_id)` → existing OAuth user
2. Match by `email` → link OAuth to existing account
3. No match → create new user (username from email prefix, no password)

## Environment Variables

```bash
# Required
OPENAI_API_KEY=
ELEVENLABS_API_KEY=

# OAuth (for Google login)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
SESSION_SECRET_KEY=  # min 32 chars

# Optional
REDIS_URL=redis://localhost:6379/0
FRONTEND_URL=http://localhost:5173
```

## Architecture

```
Lingolou/
├── webapp/
│   ├── main.py              # FastAPI app entry
│   ├── celery_app.py        # Celery config
│   ├── tasks.py             # Background tasks
│   ├── api/
│   │   ├── auth.py          # Login/register endpoints
│   │   ├── oauth.py         # Google OAuth endpoints
│   │   └── stories.py       # Story CRUD + generation
│   ├── models/
│   │   ├── database.py      # SQLAlchemy models (User, Story, Chapter)
│   │   └── schemas.py       # Pydantic schemas
│   └── services/
│       ├── auth.py          # JWT, password hashing
│       └── oauth.py         # Authlib OAuth config
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js           # API client
│   │   ├── context/AuthContext.jsx
│   │   └── pages/           # Login, Dashboard, StoryDetail, etc.
│   └── vite.config.js
├── generate_story.py        # CLI story generator
├── generate_audiobook.py    # CLI audio generator
└── requirements.txt
```

## Cloud Deployment Discussion

**Decision:** Remove Celery/Redis to simplify deployment.

**Original options considered:**
1. **Cloud Run** (recommended) — serverless, originally needed PostgreSQL + Redis
2. **Compute Engine** — VM, simpler migration
3. **App Engine** — managed but restrictive

**Redis was considered but rejected:**
- Memorystore: ~$30/mo (too expensive for MVP)
- Redis Cloud free tier: 30 MB, 30 connections (adds complexity)
- **Better solution:** Remove Celery entirely, use FastAPI BackgroundTasks

**Post-refactor deployment (Cloud Run):**
- Cloud Run: ~$0 (free tier)
- Cloud SQL (PostgreSQL): ~$7-10/mo
- Cloud Storage: ~$0.02/GB
- **No Redis needed**

## Next Steps

### Immediate: Remove Celery/Redis (See REFACTOR_PLAN.md)

- [ ] Move task logic from `webapp/tasks.py` to async functions in `webapp/services/generation.py`
- [ ] Update `webapp/api/stories.py` to use FastAPI `BackgroundTasks` instead of Celery
- [ ] Add in-memory task status store for progress tracking
- [ ] Delete `webapp/celery_app.py` and `webapp/tasks.py`
- [ ] Remove `celery[redis]` and `redis` from both `requirements.txt` files
- [ ] Update README to remove Celery/Redis setup instructions
- [ ] Test generation flow without Celery worker

### Then: Cloud Deployment

- [ ] Dockerize the app for Cloud Run
- [ ] Switch from SQLite to PostgreSQL (Cloud SQL)
- [ ] Configure Cloud Storage for audio files
- [ ] Deploy to Google Cloud

**No Redis needed after refactor.**

## Key Files Reference

| File | Purpose |
|------|---------|
| `README.md` | Full setup guide including Google OAuth |
| `webapp/main.py` | FastAPI app with middleware |
| `webapp/api/oauth.py` | Google OAuth endpoints |
| `webapp/services/oauth.py` | Authlib provider config |
| `webapp/models/database.py` | User model with OAuth fields |
| `frontend/src/pages/Login.jsx` | Login page with Google button |
