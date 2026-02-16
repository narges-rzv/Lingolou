"""
Main FastAPI application for Lingolou.
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # Load .env before any module reads os.getenv

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from webapp.api import auth, oauth, public, reports, stories, votes
from webapp.models.database import init_db

# Initialize FastAPI app
app = FastAPI(title="Lingolou API", description="Language Learning Audiobook Generator API", version="1.0.0")

# Session middleware (required by authlib for OAuth state/CSRF)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "change-me-to-a-random-secret-at-least-32-chars"),
)

# CORS middleware (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
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


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return JSON 500 response for unhandled exceptions."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# Startup event
@app.on_event("startup")
async def startup() -> None:
    """Initialize database on startup."""
    init_db()


# Health check
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


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
    index = Path(__file__).parent / "static" / "frontend" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"detail": "Frontend not built. Run: cd frontend && npm run build"}, status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
