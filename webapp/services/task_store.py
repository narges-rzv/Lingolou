"""
Pluggable task-status backends for background generation tasks.

Provides an ABC with two implementations:
- InMemoryTaskBackend  (default, for local dev)
- RedisTaskBackend     (production, when REDIS_URL is set)
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any


class TaskBackend(ABC):
    """Abstract interface for storing / querying task progress."""

    @abstractmethod
    def update(
        self,
        task_id: str,
        status: str,
        progress: float = 0,
        message: str = "",
        *,
        result: dict[str, Any] | None = None,
        words_generated: int | None = None,
        estimated_total_words: int | None = None,
    ) -> None:
        """Create or update a task entry."""

    @abstractmethod
    def get(self, task_id: str) -> dict[str, Any] | None:
        """Return the full task dict, or None if not found."""

    @abstractmethod
    def find_active_for_story(self, story_id: int) -> dict[str, Any] | None:
        """Return the most-recently-updated active (pending/running) task for *story_id*."""

    @abstractmethod
    def cancel(self, task_id: str) -> bool:
        """Mark task as cancelled. Returns True if the task was pending/running."""


# ---------------------------------------------------------------------------
# In-memory implementation (default, matches previous behaviour)
# ---------------------------------------------------------------------------


class InMemoryTaskBackend(TaskBackend):
    """Dict-backed task store — single-process only, lost on restart."""

    def __init__(self) -> None:
        """Initialise empty in-memory store."""
        self._store: dict[str, dict[str, Any]] = {}

    def update(
        self,
        task_id: str,
        status: str,
        progress: float = 0,
        message: str = "",
        *,
        result: dict[str, Any] | None = None,
        words_generated: int | None = None,
        estimated_total_words: int | None = None,
    ) -> None:
        """Create or update a task entry."""
        self._store[task_id] = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message,
            "result": result,
            "words_generated": words_generated,
            "estimated_total_words": estimated_total_words,
            "updated_at": datetime.now(UTC).isoformat(),
        }

    def get(self, task_id: str) -> dict[str, Any] | None:
        """Return the full task dict, or None if not found."""
        return self._store.get(task_id)

    def find_active_for_story(self, story_id: int) -> dict[str, Any] | None:
        """Return the most-recently-updated active task for *story_id*."""
        prefixes = (f"story_{story_id}_", f"audio_{story_id}_")
        active = [
            val
            for key, val in self._store.items()
            if any(key.startswith(p) for p in prefixes) and val.get("status") in ("pending", "running")
        ]
        if not active:
            return None
        active.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
        return active[0]

    def cancel(self, task_id: str) -> bool:
        """Mark task as cancelled. Returns True if the task was pending/running."""
        entry = self._store.get(task_id)
        if entry and entry["status"] in ("pending", "running"):
            entry["status"] = "cancelled"
            entry["message"] = "Task cancelled by user"
            return True
        return False


# ---------------------------------------------------------------------------
# Redis implementation (production)
# ---------------------------------------------------------------------------

_TASK_TTL_SECONDS = 3600  # 1 hour
_ACTIVE_STATUSES = frozenset({"pending", "running"})

# Task-id patterns: story_{id}_{ts} or audio_{id}_{ts}
_STORY_ID_RE = re.compile(r"^(?:story|audio)_(\d+)_")


def _extract_story_id(task_id: str) -> int | None:
    m = _STORY_ID_RE.match(task_id)
    return int(m.group(1)) if m else None


class RedisTaskBackend(TaskBackend):
    """Redis-backed task store — survives restarts, supports multi-instance."""

    def __init__(self, redis_url: str) -> None:
        """Connect to the Redis instance at *redis_url*."""
        import redis as _redis

        self._r: _redis.Redis[str] = _redis.from_url(redis_url, decode_responses=True)

    # -- helpers ----------------------------------------------------------

    def _task_key(self, task_id: str) -> str:
        return f"task:{task_id}"

    def _story_set_key(self, story_id: int) -> str:
        return f"story_tasks:{story_id}"

    def _register_task(self, task_id: str) -> None:
        """Add *task_id* to the per-story index set."""
        story_id = _extract_story_id(task_id)
        if story_id is not None:
            self._r.sadd(self._story_set_key(story_id), task_id)

    # -- public API -------------------------------------------------------

    def update(
        self,
        task_id: str,
        status: str,
        progress: float = 0,
        message: str = "",
        *,
        result: dict[str, Any] | None = None,
        words_generated: int | None = None,
        estimated_total_words: int | None = None,
    ) -> None:
        """Create or update a task entry."""
        key = self._task_key(task_id)
        data: dict[str, str] = {
            "task_id": task_id,
            "status": status,
            "progress": str(progress),
            "message": message,
            "result": json.dumps(result) if result is not None else "",
            "words_generated": str(words_generated) if words_generated is not None else "",
            "estimated_total_words": str(estimated_total_words) if estimated_total_words is not None else "",
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self._r.hset(key, mapping=data)  # type: ignore[arg-type]
        self._r.expire(key, _TASK_TTL_SECONDS)
        self._register_task(task_id)

    def get(self, task_id: str) -> dict[str, Any] | None:
        """Return the full task dict, or None if not found."""
        raw = self._r.hgetall(self._task_key(task_id))
        if not raw:
            return None
        return self._deserialize(raw)

    def find_active_for_story(self, story_id: int) -> dict[str, Any] | None:
        """Return the most-recently-updated active task for *story_id*."""
        set_key = self._story_set_key(story_id)
        members = self._r.smembers(set_key)
        active: list[dict[str, Any]] = []
        stale: list[str] = []

        for task_id in members:
            entry = self.get(task_id)
            if entry is None:
                stale.append(task_id)
                continue
            if entry.get("status") in _ACTIVE_STATUSES:
                active.append(entry)

        # Clean up expired/stale task ids from the set
        for tid in stale:
            self._r.srem(set_key, tid)

        if not active:
            return None
        active.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
        return active[0]

    def cancel(self, task_id: str) -> bool:
        """Mark task as cancelled. Returns True if the task was pending/running."""
        key = self._task_key(task_id)
        current_status = self._r.hget(key, "status")
        if current_status and current_status in _ACTIVE_STATUSES:
            self._r.hset(key, mapping={"status": "cancelled", "message": "Task cancelled by user"})
            return True
        return False

    # -- serialisation helpers --------------------------------------------

    @staticmethod
    def _deserialize(raw: dict[str, str]) -> dict[str, Any]:
        """Convert Redis hash strings back to native Python types."""
        result_str = raw.get("result", "")
        progress_str = raw.get("progress", "0")
        wg = raw.get("words_generated", "")
        etw = raw.get("estimated_total_words", "")
        return {
            "task_id": raw.get("task_id", ""),
            "status": raw.get("status", ""),
            "progress": float(progress_str) if progress_str else 0,
            "message": raw.get("message", ""),
            "result": json.loads(result_str) if result_str else None,
            "words_generated": int(wg) if wg else None,
            "estimated_total_words": int(etw) if etw else None,
            "updated_at": raw.get("updated_at", ""),
        }


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_backend: TaskBackend | None = None


def get_task_backend() -> TaskBackend:
    """Return the global TaskBackend singleton (lazy-initialised)."""
    global _backend  # noqa: PLW0603
    if _backend is None:
        redis_url = os.environ.get("REDIS_URL")
        _backend = RedisTaskBackend(redis_url) if redis_url else InMemoryTaskBackend()
    return _backend


def reset_task_backend() -> None:
    """Reset the singleton — useful in tests."""
    global _backend  # noqa: PLW0603
    _backend = None
