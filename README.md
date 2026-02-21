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

- **Python 3.12+**
- **Node.js 18+** (required by Vite 6 — check with `node -v`)
- **ffmpeg** (for audio processing)

## Local Development

### 1. Install system dependencies

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### 2. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
make install    # pip install + npm install
```

### 3. Environment variables

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

### 4. Configure voices

```bash
cp voices_config.example.json voices_config.json
# Edit voices_config.json with your ElevenLabs voice IDs
```

### 5. Run the app

```bash
make dev    # Starts backend + frontend (Ctrl-C to stop both)
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

## Docker Deployment

### Docker Compose (recommended)

The easiest way to run Lingolou in production — includes the app and a Redis instance for persistent task tracking:

```bash
# Start app + Redis
make compose-up
# or: docker compose up -d

# Stop
make compose-down
# or: docker compose down
```

Configure via `.env` file or environment variables (see table below). The compose setup uses Redis for task state so background job progress survives container restarts.

### Run integration tests in Docker

```bash
make compose-test
# or: docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

This spins up a Redis container and runs the full backend test suite inside Docker.

### Standalone Docker

#### Build

```bash
make docker-build
# or: docker build -t lingolou .
```

#### Run with SQLite (simple)

```bash
docker run -p 8000:8000 \
  -e SESSION_SECRET_KEY=your-secret-key-at-least-32-chars \
  -e OPENAI_API_KEY=sk-... \
  -e ELEVENLABS_API_KEY=... \
  lingolou
```

#### Run with PostgreSQL (production)

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/lingolou \
  -e SESSION_SECRET_KEY=your-secret-key-at-least-32-chars \
  -e OPENAI_API_KEY=sk-... \
  -e ELEVENLABS_API_KEY=... \
  -e FRONTEND_URL=https://your-domain.com \
  -e CORS_ORIGINS=https://your-domain.com \
  lingolou
```

### S3 Storage (optional)

Add these environment variables to use S3-compatible storage for audio files instead of local filesystem:

```bash
-e STORAGE_BACKEND=s3 \
-e S3_BUCKET=lingolou-audio \
-e S3_REGION=us-east-1 \
-e AWS_ACCESS_KEY_ID=... \
-e AWS_SECRET_ACCESS_KEY=...
```

For Cloudflare R2 or MinIO, also set `S3_ENDPOINT_URL`.

### Azure Container Instances

Deploy the app and Redis as a container group on Azure.

#### 1. Prerequisites

```bash
make az-login    # az login + az acr login -n lingolou
```

#### 2. Push the image

```bash
make docker-push
```

#### 3. Create `.env.azure`

```bash
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
ELEVENLABS_API_KEY="your-elevenlabs-key"
OPENAI_API_KEY="your-openai-key"
STORAGE_BACKEND="s3"
S3_BUCKET="your-blob-container"
S3_ENDPOINT_URL="https://your-account.blob.core.windows.net"
S3_REGION="us-east-1"
S3_PREFIX="audio"
AWS_ACCESS_KEY_ID="your-storage-account-name"
AWS_SECRET_ACCESS_KEY="your-storage-account-key"
SESSION_SECRET_KEY="a-random-string-at-least-32-chars"
STORAGE_ACCOUNT_NAME="your-storage-account-name"
STORAGE_ACCOUNT_KEY="your-storage-account-key"
FRONTEND_URL="https://lingolou.eastus.azurecontainer.io"
CORS_ORIGINS="https://lingolou.eastus.azurecontainer.io"
ACR_PASSWORD="your-acr-password"
```

> `.env.azure` is in `.gitignore` — never commit secrets.

#### 4. Create Azure File Shares

```bash
az storage share-rm create --name lingolou-data --storage-account your-storage-account
az storage share-rm create --name lingolou-redis --storage-account your-storage-account
```

#### 5. Deploy

```bash
make az-create   # first deploy
make az-update   # subsequent updates
```

These commands render `azure.yml` with your secrets into `azure.secret.yml` (gitignored), then deploy via `az container create`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SESSION_SECRET_KEY` | Yes | - | Secret for JWT + session middleware (min 32 chars) |
| `OPENAI_API_KEY` | No | - | Platform OpenAI key for free tier |
| `ELEVENLABS_API_KEY` | No | - | Platform ElevenLabs key for free tier |
| `DATABASE_URL` | No | `sqlite:///./lingolou.db` | Database connection string |
| `REDIS_URL` | No | - | Redis URL for persistent task store (e.g. `redis://localhost:6379/0`) |
| `FRONTEND_URL` | No | `http://localhost:5173` | Frontend URL for share links |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |
| `PORT` | No | `8000` | Server port |
| `STORAGE_BACKEND` | No | `local` | `local` or `s3` |
| `S3_BUCKET` | If S3 | - | S3 bucket name |
| `S3_REGION` | No | `us-east-1` | AWS region |
| `S3_ENDPOINT_URL` | No | - | Custom S3 endpoint (R2, MinIO) |
| `AWS_ACCESS_KEY_ID` | If S3 | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | If S3 | - | AWS secret key |
| `GOOGLE_CLIENT_ID` | No | - | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | - | Google OAuth client secret |

## Code Quality

```bash
make lint      # Ruff lint + format check + mypy type-check
make format    # Auto-fix lint + format issues
make all       # Format, lint, then test (pre-commit check)
```

## Testing

```bash
make test            # Backend + frontend tests
make test-backend    # pytest + coverage
make test-frontend   # Vitest + coverage
make test-e2e        # Playwright (requires backend + frontend running)
make compose-test    # Run backend tests in Docker with Redis
make test-install    # Install all test dependencies
```

## Architecture

Single-container deployment serving both the API and built frontend:

- **Backend**: FastAPI (Python) serving API at `/api/` and static files
- **Frontend**: React SPA built by Vite, served as static files from the same container
- **Database**: SQLite (dev) or PostgreSQL (production) via `DATABASE_URL`
- **Audio Storage**: Local filesystem (default) or S3-compatible object storage
- **Background Tasks**: In-process FastAPI BackgroundTasks
- **Task Store**: In-memory (dev) or Redis (production, via `REDIS_URL`) for tracking task progress

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
│   ├── task_store.py    # Pluggable task backend (in-memory/Redis)
│   ├── storage.py       # File storage abstraction (local/S3)
│   └── oauth.py         # Google OAuth provider config
├── tests/               # Backend tests (pytest)
│   ├── conftest.py      # Shared fixtures
│   └── test_*.py        # Test modules
└── static/
    └── audio/           # Generated audio files (local storage)

frontend/src/
├── App.tsx              # Router setup
├── api.ts               # API client (apiFetch, publicApiFetch)
├── types.ts             # Shared TypeScript interfaces
├── context/
│   ├── AuthContext.tsx   # Auth state, OAuth token handling
│   └── LanguageContext.tsx
├── components/          # Navbar, AudioPlayer, TaskProgress, etc.
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

## OAuth Setup (Google)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Configure OAuth consent screen (External, add `email`/`profile`/`openid` scopes)
3. Create OAuth client ID (Web application) with redirect URI: `http://localhost:8000/api/auth/oauth/google/callback`
4. Add credentials to `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET_KEY`)
5. Add your Google email as a test user while in "Testing" mode

## License

See [LICENSE](LICENSE) for details.
