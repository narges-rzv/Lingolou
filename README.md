# Lingolou - Language Learning Audiobook Generator

A web app and CLI pipeline for generating children's language learning audiobooks:
1. **Story Generation** — Create story scripts using OpenAI GPT-4
2. **Emotion Enhancement** — Add voice emotion tags automatically
3. **Audio Generation** — Convert to audiobook using ElevenLabs

Designed for kids' language learning with support for multiple characters, 35+ languages, emotions, and concurrent group dialogue.

## Features

- **Web app** with React frontend and FastAPI backend
- **AI Story Generation** via OpenAI GPT-4
- **Multi-character voices** — each character gets their own distinct ElevenLabs voice
- **35+ languages** supported via ElevenLabs `eleven_v3` model
- **Emotion tags** (`[excited]`, `[warm]`, `[concerned]`, etc.) control voice delivery
- **BYOK (Bring Your Own Key)** — users can add their own API keys, or use the free community tier
- **Public story library** — share stories, vote, and browse
- **Google OAuth** login support

## Prerequisites

- **Python 3.9+**
- **Node.js 18+** (required by Vite 6 — check with `node -v`)
- **ffmpeg** (for audio processing)

## Setup

### 1. Install system dependencies

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### 2. Backend setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend && npm install
```

### 4. Environment variables

Create a `.env` file in the project root:

```bash
# Required for story/audio generation (or users can add their own keys in Settings)
OPENAI_API_KEY="your-openai-key"
ELEVENLABS_API_KEY="your-elevenlabs-key"

# Required for OAuth and session middleware
SESSION_SECRET_KEY="a-random-string-at-least-32-chars"

# Optional
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
FRONTEND_URL="http://localhost:5173"
```

> `.env` is in `.gitignore` — never commit API keys.

### 5. Configure voices

```bash
cp voices_config.example.json voices_config.json
# Edit voices_config.json with your ElevenLabs voice IDs
```

### 6. Run the app

```bash
# Terminal 1: Backend
uvicorn webapp.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

## Testing

```bash
# Run all tests (backend + frontend)
make test

# Backend only (pytest + coverage)
make test-backend

# Frontend only (Vitest)
make test-frontend

# E2E tests (requires backend + frontend running)
make test-e2e

# Install all test dependencies
make test-install
```

## Project Structure

```
webapp/
├── main.py              # FastAPI app, middleware, routers
├── api/
│   ├── auth.py          # /api/auth/* endpoints
│   ├── oauth.py         # /api/auth/oauth/google/* endpoints
│   ├── stories.py       # /api/stories/* endpoints
│   ├── public.py        # /api/public/* endpoints (unauthenticated)
│   ├── votes.py         # /api/votes/* endpoints
│   └── reports.py       # /api/reports/* endpoints
├── models/
│   ├── database.py      # SQLAlchemy models
│   └── schemas.py       # Pydantic request/response schemas
├── services/
│   ├── auth.py          # JWT creation, password hashing
│   ├── crypto.py        # API key encryption (Fernet)
│   ├── generation.py    # Background task logic (story/audio)
│   └── oauth.py         # Google OAuth provider config
├── tests/               # Backend tests (pytest)
│   ├── conftest.py      # Shared fixtures
│   └── test_*.py        # Test modules
└── static/
    └── audio/           # Generated audio files

frontend/src/
├── App.jsx              # Router setup
├── api.js               # API client (apiFetch, loginRequest, etc.)
├── languages.js         # Supported languages list
├── context/
│   ├── AuthContext.jsx   # Auth state, OAuth token handling
│   └── LanguageContext.jsx
├── components/          # Navbar, BudgetBanner, TaskProgress, etc.
├── pages/               # Login, Dashboard, StoryDetail, NewStory, Settings, etc.
├── test/                # Frontend tests (Vitest + RTL + MSW)
└── e2e/                 # E2E tests (Playwright)
```

## CLI Tools

The project also includes standalone CLI tools for story/audio generation:

```bash
# Generate a story
python generate_story.py -o stories/s2

# Generate with custom prompt
python generate_story.py -o stories/s2 -p "Create a story about space..."

# Generate audiobook from story
python generate_audiobook.py stories/s2 --voices voices_config.json

# List available ElevenLabs voices
python test_voice.py list
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get JWT token |
| GET | `/api/auth/me` | Get current user info |
| GET | `/api/auth/api-keys` | Get API key status (never returns actual keys) |
| PUT | `/api/auth/api-keys` | Save encrypted API keys |

### Stories (authenticated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stories/` | List user's stories |
| POST | `/api/stories/` | Create new story |
| GET | `/api/stories/{id}` | Get story with chapters |
| PATCH | `/api/stories/{id}` | Update story metadata |
| DELETE | `/api/stories/{id}` | Delete story |
| POST | `/api/stories/{id}/generate` | Generate story scripts |
| POST | `/api/stories/{id}/generate-audio` | Generate audio files |
| GET | `/api/stories/tasks/{task_id}` | Check task status |
| DELETE | `/api/stories/tasks/{task_id}` | Cancel a running task |

### Public (unauthenticated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/public/budget` | Community free-tier budget status |
| GET | `/api/public/stories` | List public completed stories |
| GET | `/api/public/stories/{id}` | Get a public story |
| GET | `/api/public/share/{code}` | Get story by share code |

### Votes & Reports (authenticated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/votes/stories/{id}` | Vote on a story (up/down/null) |
| POST | `/api/reports/stories/{id}` | Report a story |

## Database

SQLite (`lingolou.db`) in development. Key models:

- **User** — account, OAuth, encrypted API keys, free tier usage
- **Story** — title, prompt, status, visibility, votes
- **Chapter** — script JSON, enhanced JSON, audio path
- **Vote** / **Report** — user interactions on public stories
- **PlatformBudget** — community free-tier spending pool

> Schema changes require deleting `lingolou.db` (SQLAlchemy `create_all` won't alter existing tables).

## OAuth Setup (Google)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Configure OAuth consent screen (External, add `email`/`profile`/`openid` scopes)
3. Create OAuth client ID (Web application) with redirect URI: `http://localhost:8000/api/auth/oauth/google/callback`
4. Add credentials to `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET_KEY`)
5. Add your Google email as a test user while in "Testing" mode
