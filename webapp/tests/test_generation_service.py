"""Tests for webapp/services/generation.py (task store functions only)."""

import pytest
from webapp.services import generation


@pytest.fixture(autouse=True)
def fresh_task_store(monkeypatch):
    """Each test gets an isolated, empty task_store."""
    monkeypatch.setattr(generation, "task_store", {})


def test_update_task_status():
    generation.update_task_status("t1", "running", 50, "halfway")
    assert "t1" in generation.task_store
    assert generation.task_store["t1"]["status"] == "running"
    assert generation.task_store["t1"]["progress"] == 50


def test_get_task_status():
    generation.update_task_status("t1", "pending", 0, "queued")
    result = generation.get_task_status("t1")
    assert result is not None
    assert result["status"] == "pending"


def test_get_task_status_nonexistent():
    assert generation.get_task_status("nope") is None


def test_find_active_task_for_story():
    generation.update_task_status("story_5_100", "running", 30, "generating")
    generation.update_task_status("story_5_200", "completed", 100, "done")

    result = generation.find_active_task_for_story(5)
    assert result is not None
    assert result["task_id"] == "story_5_100"


def test_find_active_task_for_story_audio():
    generation.update_task_status("audio_5_100", "pending", 0, "queued")

    result = generation.find_active_task_for_story(5)
    assert result is not None
    assert result["task_id"] == "audio_5_100"


def test_find_active_task_none():
    generation.update_task_status("story_5_100", "completed", 100, "done")
    assert generation.find_active_task_for_story(5) is None


def test_find_active_task_most_recent():
    generation.update_task_status("story_5_100", "running", 10, "old")
    generation.update_task_status("story_5_200", "running", 50, "new")

    result = generation.find_active_task_for_story(5)
    # Should return the most recently updated
    assert result["task_id"] == "story_5_200"


def test_cancel_running_task():
    generation.update_task_status("t1", "running", 50, "running")
    assert generation.cancel_task("t1") is True
    assert generation.task_store["t1"]["status"] == "cancelled"


def test_cancel_pending_task():
    generation.update_task_status("t1", "pending", 0, "queued")
    assert generation.cancel_task("t1") is True
    assert generation.task_store["t1"]["status"] == "cancelled"


def test_cancel_completed_task():
    generation.update_task_status("t1", "completed", 100, "done")
    assert generation.cancel_task("t1") is False


def test_cancel_nonexistent_task():
    assert generation.cancel_task("nope") is False
