"""Main FastAPI application for APP_NAME."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # Load .env before any module reads os.getenv

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Add startup logic here (e.g. db init, cache warm-up)
    yield
    # Add shutdown logic here


app = FastAPI(title="APP_NAME", version="0.1.0", lifespan=lifespan)

_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

frontend_dir = static_dir / "frontend"
frontend_dir.mkdir(exist_ok=True)
frontend_assets = frontend_dir / "assets"
if frontend_assets.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_assets)), name="frontend-assets")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": app.version}


@app.get("/", response_model=None)
async def root() -> FileResponse | dict[str, str]:
    """Serve SPA index or API info when frontend is not built."""
    index = Path(__file__).parent / "static" / "frontend" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"name": "APP_NAME", "version": app.version, "docs": "/docs"}


@app.get("/{full_path:path}", response_model=None)
async def serve_spa(request: Request, full_path: str) -> FileResponse | JSONResponse:
    """Catch-all: serve SPA for non-API paths, 404 for /api/* misses."""
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    static_file = Path(__file__).parent / "static" / "frontend" / full_path
    if static_file.is_file():
        return FileResponse(str(static_file))
    index = Path(__file__).parent / "static" / "frontend" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"detail": "Frontend not built. Run: cd frontend && npm run build"}, status_code=404)
