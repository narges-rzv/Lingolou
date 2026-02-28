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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from webapp.api import auth, blocks, bookmarks, follows, oauth, public, reports, stories, votes, worlds
from webapp.models.database import init_db


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle the life-cycle of the server.

    Args:
        app (FastAPI): The server.

    Returns:
        AsyncGenerator[None, None]: Yields control to the server.
    """
    # Start Up
    init_db()
    # Server
    yield
    # Shut Down


# Initialize FastAPI app
app = FastAPI(
    title="Lingolou API", description="Language Learning Audiobook Generator API", version="1.0.3", lifespan=lifespan
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


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return JSON 500 response for unhandled exceptions."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# Health check
@app.get("/health")
async def health_check() -> dict[str, str | None]:
    """Health check endpoint."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_cfg)
    head = script.get_current_head()
    return {"status": "healthy", "version": app.version, "migration": head}


# Root endpoint — serve SPA if built, otherwise API info
@app.get("/", response_model=None)
async def root() -> FileResponse | dict[str, str]:
    """Serve SPA index or API info."""
    index = Path(__file__).parent / "static" / "frontend" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"name": "Lingolou API", "version": "1.0.0", "docs": "/docs"}


# SPA catch-all: serve index.html for any non-API, non-static path
@app.get("/{full_path:path}", response_model=None)
async def serve_spa(request: Request, full_path: str) -> FileResponse | JSONResponse:
    """Catch-all route to serve SPA for non-API paths."""
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    index = Path(__file__).parent / "static" / "frontend" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"detail": "Frontend not built. Run: cd frontend && npm run build"}, status_code=404)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
