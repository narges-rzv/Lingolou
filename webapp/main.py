"""
Main FastAPI application for Lingolou.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator

from dotenv import load_dotenv

load_dotenv()  # Load .env before any module reads os.getenv

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from webapp.api import auth, blocks, bookmarks, follows, oauth, public, reports, stories, votes, worlds
from webapp.middleware.etag import ETagMiddleware
from webapp.models.database import get_db, init_db
from webapp.services import social_meta


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle the life-cycle of the server.

    Args:
        app (FastAPI): The server.

    Returns:
        AsyncGenerator[None, None]: Yields control to the server.
    """
    import threading

    from webapp.services.generation import resume_incomplete_stories
    from webapp.services.voices_cache import warm_cache

    # Start Up
    init_db()

    # Warm the voices cache in a daemon thread (non-blocking startup)
    threading.Thread(target=warm_cache, daemon=True).start()

    # Resume any stories stuck in 'generating' from a previous shutdown
    threading.Thread(target=resume_incomplete_stories, daemon=True).start()

    # Server
    yield
    # Shut Down


# Initialize FastAPI app
app = FastAPI(
    title="Lingolou API", description="Language Learning Audiobook Generator API", version="1.1.7", lifespan=lifespan
)

# Session middleware (required by authlib for OAuth state/CSRF)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "change-me-to-a-random-secret-at-least-32-chars"),
)

# CORS middleware — set CORS_ORIGINS env var for production (comma-separated)
_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ETag middleware for GET /api/* JSON responses (after CORS so headers are present)
app.add_middleware(ETagMiddleware)

# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount frontend SPA assets (built by Vite into static/frontend/)
frontend_dir = static_dir / "frontend"
frontend_dir.mkdir(exist_ok=True)
frontend_assets = frontend_dir / "assets"
if frontend_assets.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_assets)), name="frontend-assets")

# Include routers
app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(oauth.router)
app.include_router(public.router)
app.include_router(votes.router)
app.include_router(reports.router)
app.include_router(bookmarks.router)
app.include_router(blocks.router)
app.include_router(follows.router)
app.include_router(worlds.router)


# Redis-not-ready handler — returns 503 with Retry-After so clients can retry
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return JSON error response for unhandled exceptions."""
    from webapp.services.task_store import RedisNotReadyError

    if isinstance(exc, RedisNotReadyError):
        return JSONResponse(
            status_code=503,
            content={"detail": "Service starting up, please retry"},
            headers={"Retry-After": "2"},
        )
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# Health check
@app.get("/health")
async def health_check() -> dict[str, str | None]:
    """Health check endpoint."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from webapp.services.task_store import RedisTaskBackend, get_task_backend

    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_cfg)
    head = script.get_current_head()

    # Check Redis status
    backend = get_task_backend()
    if isinstance(backend, RedisTaskBackend):
        redis_status = "connected" if backend.ping() else "error"
    else:
        redis_status = "not_configured"

    return {"status": "healthy", "version": app.version, "alembic_head": head, "redis": redis_status}


def _serve_spa_shell(request: Request, db: Session, full_path: str) -> Response:
    """Serve index.html with server-rendered Open Graph meta tags injected.

    Crawlers don't run JS, so we resolve the requested path to a story and inject the
    right unfurl tags; real users still get the same shell and React hydrates over it.
    """
    index = Path(__file__).parent / "static" / "frontend" / "index.html"
    if not index.exists():
        return JSONResponse({"detail": "Frontend not built. Run: cd frontend && npm run build"}, status_code=404)
    base_url = social_meta.get_base_url(request)
    meta = social_meta.resolve_meta(db, full_path, base_url)
    html_doc = social_meta.inject_meta(index.read_text(encoding="utf-8"), meta)
    return HTMLResponse(content=html_doc)


# Root endpoint — serve SPA if built, otherwise API info
@app.get("/", response_model=None)
async def root(request: Request, db: Session = Depends(get_db)) -> Response | dict[str, str]:
    """Serve SPA index or API info."""
    index = Path(__file__).parent / "static" / "frontend" / "index.html"
    if index.exists():
        return _serve_spa_shell(request, db, "")
    return {"name": "Lingolou API", "version": "1.0.0", "docs": "/docs"}


# SPA catch-all: serve index.html for any non-API, non-static path
@app.get("/{full_path:path}", response_model=None)
async def serve_spa(request: Request, full_path: str, db: Session = Depends(get_db)) -> Response:
    """Catch-all route to serve SPA for non-API paths."""
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    # Serve static files from the frontend build directory if they exist
    static_file = Path(__file__).parent / "static" / "frontend" / full_path
    if static_file.is_file():
        return FileResponse(str(static_file))
    return _serve_spa_shell(request, db, full_path)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
