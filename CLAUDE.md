# CLAUDE.md

> This file provides guidance to Claude Code (or any AI assistant) when working on this codebase.

## Project Summary

Lingolou is a language learning audiobook generator. It creates children's stories with multilingual dialogue, generates emotion-tagged scripts using OpenAI GPT-4, and converts them to audio using ElevenLabs. Supports 35+ languages, BYOK (Bring Your Own Key), a public story library with voting, and Google OAuth login.

## Tech Stack

- **Backend**: FastAPI (Python 3.9+)
- **Frontend**: React 18 + Vite
- **Database**: SQLite (dev), PostgreSQL (production)
- **Background Tasks**: FastAPI BackgroundTasks (in-process)
- **Auth**: JWT + Google OAuth (authlib)
- **APIs**: OpenAI (GPT-4), ElevenLabs (eleven_v3)
- **Encryption**: Fernet (cryptography) for API key storage

## Common Commands

```bash
# Backend
uvicorn webapp.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Tests
make test            # backend + frontend unit tests
make test-backend    # pytest + coverage
make test-frontend   # vitest + coverage
make test-e2e        # playwright (requires servers running)

# CLI tools
python generate_story.py -o stories/s1
python generate_audiobook.py stories/s1 --voices voices_config.json
```

## Project Structure

```
webapp/
├── main.py              # FastAPI app, middleware, routers
├── api/
│   ├── auth.py          # /api/auth/* endpoints (login, register, API keys)
│   ├── oauth.py         # /api/auth/oauth/google/* endpoints
│   ├── stories.py       # /api/stories/* endpoints (CRUD, generation)
│   ├── public.py        # /api/public/* endpoints (unauthenticated)
│   ├── votes.py         # /api/votes/* endpoints
│   └── reports.py       # /api/reports/* endpoints
├── models/
│   ├── database.py      # SQLAlchemy models (User, Story, Chapter, Vote, Report, PlatformBudget)
│   └── schemas.py       # Pydantic request/response schemas
├── services/
│   ├── auth.py          # JWT creation, password hashing
│   ├── crypto.py        # API key encryption (Fernet)
│   ├── generation.py    # Background task logic (story/audio generation)
│   └── oauth.py         # Google OAuth provider config
└── tests/
    ├── conftest.py      # Shared fixtures (db, client, auth_headers)
    └── test_*.py        # Backend tests (pytest)

frontend/src/
├── App.jsx              # Router setup
├── api.js               # API client (apiFetch, loginRequest, etc.)
├── languages.js         # Supported languages list
├── context/
│   ├── AuthContext.jsx   # Auth state, OAuth token handling
│   └── LanguageContext.jsx
├── components/          # Navbar, BudgetBanner, TaskProgress, etc.
├── pages/               # Login, Dashboard, StoryDetail, NewStory, Settings, PublicStories, etc.
├── test/                # Frontend tests (Vitest + RTL + MSW)
└── e2e/                 # E2E tests (Playwright)
```

## Code Patterns

### Backend

- **Routers** are in `webapp/api/`, included in `main.py`
- **Database models** use SQLAlchemy declarative base in `database.py`
- **Pydantic schemas** for request validation in `schemas.py`
- **Background tasks** use FastAPI `BackgroundTasks` in `services/generation.py`, with in-memory progress tracking via `task_store` dict
- **Auth** uses `get_current_user` dependency for protected routes; `get_current_user_optional` for routes that work with or without auth
- **BYOK**: Users store encrypted API keys (Fernet via `services/crypto.py`). Generation endpoints check user keys first, then fall back to platform free tier
- **Free tier**: `PlatformBudget` model tracks community spending pool; users get 3 free stories

### Frontend

- **API calls** go through `api.js` which adds the Bearer token from localStorage
- **Auth state** is managed in `AuthContext.jsx`
- **OAuth redirect** is handled on mount in AuthContext (checks for `?token=` param)
- **Language context** provides language selection across components

## Database Schema

Key models in `webapp/models/database.py`:

- **User**: email, username, hashed_password (nullable for OAuth), oauth_provider, oauth_id, encrypted API keys, free_stories_used
- **Story**: title, description, prompt, status, visibility, share_code, upvotes, downvotes, user_id
- **Chapter**: story_id, chapter_number, script_json, enhanced_json, audio_path, status
- **Vote**: user_id, story_id, vote_type (up/down)
- **Report**: user_id, story_id, reason, status
- **PlatformBudget**: monthly_limit, amount_used (community free tier pool)

Note: SQLite is used locally. Schema changes require deleting `lingolou.db` (SQLAlchemy `create_all` won't alter existing tables).

## Environment Variables

Required in `.env` (not committed):

```bash
OPENAI_API_KEY=
ELEVENLABS_API_KEY=
SESSION_SECRET_KEY=  # min 32 chars for session middleware + Fernet key derivation
```

Optional:
```bash
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
FRONTEND_URL=http://localhost:5173
```

## Testing

For every new feature, add meaningful tests covering logical flows and edge cases, aiming to increase coverage. Tests should verify both the happy path and failure modes (invalid input, auth boundaries, ownership checks, etc.).

```bash
make test            # Run backend + frontend tests
make test-backend    # pytest + coverage report
make test-frontend   # vitest + coverage report
make test-e2e        # playwright (requires backend + frontend running)
```

- **Backend tests**: `webapp/tests/` — pytest with in-memory SQLite (StaticPool), FastAPI TestClient, fixtures in `conftest.py`
- **Frontend tests**: `frontend/src/test/` — Vitest + React Testing Library + MSW v2 for network mocking
- **E2E tests**: `frontend/src/e2e/` — Playwright (chromium)
- **Shared test utils**: `frontend/src/test/test-utils.jsx` wraps components in all providers (Router, Auth, Language)

## Gotchas

- **OAuth-only users** have `hashed_password=None` — `authenticate_user()` guards against this
- **SQLite schema changes** require deleting the `.db` file
- **Background tasks** run in-process; task progress is lost on server restart
- **CORS** is set to `allow_origins=["*"]` — restrict in production
- **Session middleware** is required for OAuth state/CSRF (authlib requirement)
- **In-memory SQLite tests** require `StaticPool` to share connections across threads

## When Making Changes

1. **Adding API endpoints**: Create in `webapp/api/`, include router in `main.py`, add tests in `webapp/tests/`
2. **Adding database columns**: Update model in `database.py`, delete `lingolou.db`
3. **Frontend changes**: Files in `frontend/src/`, hot-reloads with Vite, add tests in `frontend/src/test/`
4. **New dependencies**: Add to `requirements.txt`
5. **Always add tests**: Cover logical flows, edge cases, and auth/ownership boundaries. Run `make test` before committing
