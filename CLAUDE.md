# CLAUDE.md

> This file provides guidance to Claude Code (or any AI assistant) when working on this codebase.

## Project Summary

Lingolou is a language learning audiobook generator. It creates children's stories with multilingual dialogue (English + Farsi), generates emotion-tagged scripts using OpenAI, and converts them to audio using ElevenLabs.

## Tech Stack

- **Backend**: FastAPI (Python 3.9+)
- **Frontend**: React 18 + Vite
- **Database**: SQLite (dev), PostgreSQL (production)
- **Background Tasks**: FastAPI BackgroundTasks (in-process)
- **Auth**: JWT + Google OAuth (authlib)
- **APIs**: OpenAI (GPT-4), ElevenLabs (eleven_v3)

## Common Commands

```bash
# Backend
uvicorn webapp.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# CLI tools
python generate_story.py -o stories/s1
python generate_audiobook.py stories/s1 --voices voices_config.json
```

## Project Structure

```
webapp/
├── main.py              # FastAPI app, middleware, routers
├── api/
│   ├── auth.py          # /api/auth/* endpoints
│   ├── oauth.py         # /api/auth/oauth/google/* endpoints
│   └── stories.py       # /api/stories/* endpoints
├── models/
│   ├── database.py      # SQLAlchemy models
│   └── schemas.py       # Pydantic request/response schemas
└── services/
    ├── auth.py          # JWT creation, password hashing
    ├── generation.py    # Background task logic (story/audio generation)
    └── oauth.py         # Google OAuth provider config

frontend/src/
├── App.jsx              # Router setup
├── api.js               # API client (apiFetch, loginRequest, etc.)
├── context/AuthContext.jsx  # Auth state, OAuth token handling
└── pages/               # Login, Dashboard, StoryDetail, NewStory, EditStory
```

## Code Patterns

### Backend

- **Routers** are in `webapp/api/`, included in `main.py`
- **Database models** use SQLAlchemy declarative base in `database.py`
- **Pydantic schemas** for request validation in `schemas.py`
- **Background tasks** use FastAPI `BackgroundTasks` in `services/generation.py`, with in-memory progress tracking
- **Auth** uses `get_current_user` dependency for protected routes

### Frontend

- **API calls** go through `api.js` which adds the Bearer token from localStorage
- **Auth state** is managed in `AuthContext.jsx`
- **OAuth redirect** is handled on mount in AuthContext (checks for `?token=` param)

## Database Schema

Key models in `webapp/models/database.py`:

- **User**: email, username, hashed_password (nullable for OAuth), oauth_provider, oauth_id
- **Story**: title, description, prompt, status, user_id
- **Chapter**: story_id, chapter_number, script_json, enhanced_json, audio_path, status

Note: SQLite is used locally. Schema changes require deleting `lingolou.db` (SQLAlchemy `create_all` won't alter existing tables).

## Environment Variables

Required in `.env` (not committed):

```bash
OPENAI_API_KEY=
ELEVENLABS_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
SESSION_SECRET_KEY=  # min 32 chars for session middleware
```

Optional:
```bash
FRONTEND_URL=http://localhost:5173
```

## Testing

For every new feature, add meaningful tests covering logical flows and edge cases, aiming to increase coverage. Tests should verify both the happy path and failure modes (invalid input, auth boundaries, ownership checks, etc.).

```bash
# Run all tests
make test

# Backend only (pytest + coverage report)
make test-backend

# Frontend only (Vitest + coverage report)
make test-frontend

# E2E (requires backend + frontend running)
make test-e2e
```

- **Backend tests**: `webapp/tests/` — pytest with in-memory SQLite, FastAPI TestClient, fixtures in `conftest.py`
- **Frontend tests**: `frontend/src/test/` — Vitest + React Testing Library + MSW v2 for network mocking
- **E2E tests**: `frontend/src/e2e/` — Playwright (chromium)
- **Shared test utils**: `frontend/src/test/test-utils.jsx` wraps components in all providers (Router, Auth, Language)

## Gotchas

- **OAuth-only users** have `hashed_password=None` — `authenticate_user()` guards against this
- **SQLite schema changes** require deleting the `.db` file
- **Background tasks** run in-process; task progress is lost on server restart
- **CORS** is set to `allow_origins=["*"]` — restrict in production
- **Session middleware** is required for OAuth state/CSRF (authlib requirement)

## When Making Changes

1. **Adding API endpoints**: Create in `webapp/api/`, include router in `main.py`, add tests in `webapp/tests/`
2. **Adding database columns**: Update model in `database.py`, delete `lingolou.db`
3. **Frontend changes**: Files in `frontend/src/`, hot-reloads with Vite, add tests in `frontend/src/test/`
4. **New dependencies**: Add to both `requirements.txt` and `webapp/requirements.txt`
5. **Always add tests**: Cover logical flows, edge cases, and auth/ownership boundaries. Run `make test` before committing
