"""Tests for task store integration via generation module."""

import pytest

from webapp.services.task_store import InMemoryTaskBackend, get_task_backend, reset_task_backend


@pytest.fixture(autouse=True)
def fresh_task_store():
    """Each test gets an isolated, empty task backend."""
    reset_task_backend()
    backend = get_task_backend()
    assert isinstance(backend, InMemoryTaskBackend)
    yield
    reset_task_backend()


def test_update_task_status():
    be = get_task_backend()
    be.update("t1", "running", 50, "halfway")
    task = be.get("t1")
    assert task is not None
    assert task["status"] == "running"
    assert task["progress"] == 50


def test_get_task_status():
    be = get_task_backend()
    be.update("t1", "pending", 0, "queued")
    result = be.get("t1")
    assert result is not None
    assert result["status"] == "pending"


def test_get_task_status_nonexistent():
    assert get_task_backend().get("nope") is None


def test_find_active_task_for_story():
    be = get_task_backend()
    be.update("story_5_100", "running", 30, "generating")
    be.update("story_5_200", "completed", 100, "done")

    result = be.find_active_for_story(5)
    assert result is not None
    assert result["task_id"] == "story_5_100"


def test_find_active_task_for_story_audio():
    be = get_task_backend()
    be.update("audio_5_100", "pending", 0, "queued")

    result = be.find_active_for_story(5)
    assert result is not None
    assert result["task_id"] == "audio_5_100"


def test_find_active_task_none():
    be = get_task_backend()
    be.update("story_5_100", "completed", 100, "done")
    assert be.find_active_for_story(5) is None


def test_find_active_task_most_recent():
    be = get_task_backend()
    be.update("story_5_100", "running", 10, "old")
    be.update("story_5_200", "running", 50, "new")

    result = be.find_active_for_story(5)
    # Should return the most recently updated
    assert result["task_id"] == "story_5_200"


def test_cancel_running_task():
    be = get_task_backend()
    be.update("t1", "running", 50, "running")
    assert be.cancel("t1") is True
    task = be.get("t1")
    assert task is not None
    assert task["status"] == "cancelled"


def test_cancel_pending_task():
    be = get_task_backend()
    be.update("t1", "pending", 0, "queued")
    assert be.cancel("t1") is True
    task = be.get("t1")
    assert task is not None
    assert task["status"] == "cancelled"


def test_cancel_completed_task():
    be = get_task_backend()
    be.update("t1", "completed", 100, "done")
    assert be.cancel("t1") is False


def test_cancel_nonexistent_task():
    assert get_task_backend().cancel("nope") is False
