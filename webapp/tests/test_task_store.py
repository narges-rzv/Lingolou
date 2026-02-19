"""Tests for webapp/services/task_store.py — InMemory and Redis backends."""

from unittest.mock import MagicMock, patch

import pytest

from webapp.services.task_store import (
    InMemoryTaskBackend,
    RedisTaskBackend,
    _extract_story_id,
    reset_task_backend,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure the module-level singleton is reset between tests."""
    reset_task_backend()
    yield
    reset_task_backend()


def _make_memory_backend():
    return InMemoryTaskBackend()


# ---------------------------------------------------------------------------
# _extract_story_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("task_id", "expected"),
    [
        ("story_42_1700000000", 42),
        ("audio_7_1700000000", 7),
        ("random_string", None),
        ("story__bad", None),
    ],
)
def test_extract_story_id(task_id, expected):
    assert _extract_story_id(task_id) == expected


# ---------------------------------------------------------------------------
# InMemoryTaskBackend
# ---------------------------------------------------------------------------


class TestInMemoryTaskBackend:
    def test_update_and_get(self):
        be = _make_memory_backend()
        be.update("t1", "running", 50, "halfway")
        task = be.get("t1")
        assert task is not None
        assert task["status"] == "running"
        assert task["progress"] == 50
        assert task["message"] == "halfway"
        assert task["updated_at"]

    def test_get_missing(self):
        be = _make_memory_backend()
        assert be.get("nonexistent") is None

    def test_update_with_extras(self):
        be = _make_memory_backend()
        be.update("t1", "running", 30, "gen", result={"story_id": 1}, words_generated=100, estimated_total_words=500)
        task = be.get("t1")
        assert task["result"] == {"story_id": 1}
        assert task["words_generated"] == 100
        assert task["estimated_total_words"] == 500

    def test_find_active_for_story(self):
        be = _make_memory_backend()
        be.update("story_5_100", "running", 10, "a")
        be.update("story_5_200", "pending", 0, "b")
        be.update("audio_5_300", "completed", 100, "done")
        be.update("story_6_100", "running", 20, "other story")

        result = be.find_active_for_story(5)
        assert result is not None
        # Should be the most recently updated active task
        assert result["task_id"] in ("story_5_100", "story_5_200")

    def test_find_active_for_story_none(self):
        be = _make_memory_backend()
        be.update("story_5_100", "completed", 100, "done")
        assert be.find_active_for_story(5) is None

    def test_cancel_running_task(self):
        be = _make_memory_backend()
        be.update("t1", "running", 50, "busy")
        assert be.cancel("t1") is True
        task = be.get("t1")
        assert task["status"] == "cancelled"
        assert "cancelled" in task["message"].lower()

    def test_cancel_pending_task(self):
        be = _make_memory_backend()
        be.update("t1", "pending", 0, "queued")
        assert be.cancel("t1") is True

    def test_cancel_completed_task(self):
        be = _make_memory_backend()
        be.update("t1", "completed", 100, "done")
        assert be.cancel("t1") is False

    def test_cancel_nonexistent_task(self):
        be = _make_memory_backend()
        assert be.cancel("nope") is False


# ---------------------------------------------------------------------------
# RedisTaskBackend (with mock redis)
# ---------------------------------------------------------------------------


class FakeRedis:
    """Minimal Redis mock that behaves like redis.Redis with decode_responses=True."""

    def __init__(self):
        self._hashes = {}
        self._sets = {}
        self._ttls = {}

    def hset(self, key, mapping=None, **kwargs):
        if key not in self._hashes:
            self._hashes[key] = {}
        if mapping:
            self._hashes[key].update(mapping)
        self._hashes[key].update(kwargs)

    def hget(self, key, field):
        return self._hashes.get(key, {}).get(field)

    def hgetall(self, key):
        return self._hashes.get(key, {})

    def expire(self, key, seconds):
        self._ttls[key] = seconds

    def sadd(self, key, *values):
        if key not in self._sets:
            self._sets[key] = set()
        self._sets[key].update(values)

    def smembers(self, key):
        return self._sets.get(key, set())

    def srem(self, key, *values):
        s = self._sets.get(key)
        if s:
            for v in values:
                s.discard(v)


class TestRedisTaskBackend:
    @pytest.fixture()
    def backend(self):
        fake = FakeRedis()
        be = RedisTaskBackend.__new__(RedisTaskBackend)
        be._r = fake
        return be

    def test_update_and_get(self, backend):
        backend.update("t1", "running", 50, "halfway")
        task = backend.get("t1")
        assert task is not None
        assert task["status"] == "running"
        assert task["progress"] == 50.0
        assert task["message"] == "halfway"

    def test_get_missing(self, backend):
        assert backend.get("nonexistent") is None

    def test_update_with_extras(self, backend):
        backend.update(
            "t1", "running", 30, "gen", result={"story_id": 1}, words_generated=100, estimated_total_words=500
        )
        task = backend.get("t1")
        assert task["result"] == {"story_id": 1}
        assert task["words_generated"] == 100
        assert task["estimated_total_words"] == 500

    def test_find_active_for_story(self, backend):
        backend.update("story_5_100", "running", 10, "a")
        backend.update("story_5_200", "pending", 0, "b")
        backend.update("audio_5_300", "completed", 100, "done")

        result = backend.find_active_for_story(5)
        assert result is not None
        assert result["task_id"] in ("story_5_100", "story_5_200")

    def test_find_active_for_story_none(self, backend):
        backend.update("story_5_100", "completed", 100, "done")
        assert backend.find_active_for_story(5) is None

    def test_find_active_cleans_stale(self, backend):
        # Register a task in the story set, but don't create the hash
        backend._r.sadd("story_tasks:5", "story_5_expired")
        backend.update("story_5_100", "running", 10, "a")

        result = backend.find_active_for_story(5)
        assert result is not None
        # The stale entry should have been cleaned up
        assert "story_5_expired" not in backend._r.smembers("story_tasks:5")

    def test_cancel_running_task(self, backend):
        backend.update("t1", "running", 50, "busy")
        assert backend.cancel("t1") is True
        task = backend.get("t1")
        assert task["status"] == "cancelled"

    def test_cancel_completed_task(self, backend):
        backend.update("t1", "completed", 100, "done")
        assert backend.cancel("t1") is False

    def test_cancel_nonexistent_task(self, backend):
        assert backend.cancel("nope") is False

    def test_ttl_set_on_update(self, backend):
        backend.update("t1", "running", 10, "msg")
        assert backend._r._ttls.get("task:t1") == 3600

    def test_deserialize_empty_optionals(self, backend):
        backend.update("t1", "running", 0, "msg")
        task = backend.get("t1")
        assert task["result"] is None
        assert task["words_generated"] is None
        assert task["estimated_total_words"] is None


# ---------------------------------------------------------------------------
# Factory / singleton
# ---------------------------------------------------------------------------


def test_get_task_backend_returns_memory_by_default():
    from webapp.services.task_store import get_task_backend

    be = get_task_backend()
    assert isinstance(be, InMemoryTaskBackend)


def test_get_task_backend_returns_redis_when_url_set(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    with patch("webapp.services.task_store.RedisTaskBackend") as mock_cls:
        mock_cls.return_value = MagicMock()
        from webapp.services.task_store import get_task_backend

        be = get_task_backend()
        mock_cls.assert_called_once_with("redis://localhost:6379/0")
        assert be is mock_cls.return_value
