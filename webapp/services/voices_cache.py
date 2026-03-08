"""
Thread-safe in-memory cache for ElevenLabs voices list.

Avoids blocking the /api/stories/voices endpoint with a 1-5 second HTTP call
on every request. The cache is warmed on startup and refreshed in the
background every hour.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import requests as http_requests

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 3600  # 1 hour

_lock = threading.Lock()
_voices: list[dict[str, Any]] = []
_last_fetched: float = 0.0
_refreshing = False


def _fetch_voices() -> list[dict[str, Any]]:
    """Fetch voices from ElevenLabs API (blocking HTTP call)."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.warning("ELEVENLABS_API_KEY not set, cannot fetch voices")
        return []

    resp = http_requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": api_key},
        timeout=10,
    )
    if resp.status_code != 200:
        logger.warning("ElevenLabs voices API returned %s", resp.status_code)
        return []

    raw_voices = resp.json().get("voices", [])
    return [
        {
            "voice_id": v["voice_id"],
            "name": v["name"],
            "category": v.get("category", ""),
            "labels": v.get("labels", {}),
            "preview_url": v.get("preview_url", ""),
        }
        for v in raw_voices
    ]


def _background_refresh() -> None:
    """Refresh the cache in a background thread."""
    global _voices, _last_fetched, _refreshing  # noqa: PLW0603
    try:
        result = _fetch_voices()
        if result:
            with _lock:
                _voices = result
                _last_fetched = time.monotonic()
    except Exception:
        logger.exception("Failed to refresh voices cache")
    finally:
        with _lock:
            _refreshing = False


def get_voices() -> list[dict[str, Any]]:
    """Return cached voices list, triggering a background refresh if stale.

    Returns empty list only on first cold call when ElevenLabs is unreachable.
    """
    global _refreshing  # noqa: PLW0603
    now = time.monotonic()

    with _lock:
        is_stale = (now - _last_fetched) > _CACHE_TTL_SECONDS
        cached = list(_voices)
        already_refreshing = _refreshing

    if is_stale and not already_refreshing:
        with _lock:
            _refreshing = True
        t = threading.Thread(target=_background_refresh, daemon=True)
        t.start()

        # If cache is empty (cold start), wait for the first fetch
        if not cached:
            t.join(timeout=15)
            with _lock:
                cached = list(_voices)

    return cached


def warm_cache() -> None:
    """Populate the cache (called on startup). Safe to call from any thread."""
    global _voices, _last_fetched  # noqa: PLW0603
    result = _fetch_voices()
    if result:
        with _lock:
            _voices = result
            _last_fetched = time.monotonic()
        logger.info("Voices cache warmed with %d voices", len(result))
    else:
        logger.warning("Voices cache warm-up returned no results")


def reset_cache() -> None:
    """Reset cache state — for tests only."""
    global _voices, _last_fetched, _refreshing  # noqa: PLW0603
    with _lock:
        _voices = []
        _last_fetched = 0.0
        _refreshing = False
