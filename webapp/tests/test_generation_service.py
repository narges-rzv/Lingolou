"""Tests for task store integration via generation module."""

from unittest.mock import MagicMock, patch

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


# --- resume_incomplete_stories tests ---


@patch("webapp.services.generation.generate_story")
@patch("webapp.services.generation.threading.Thread")
def test_resume_incomplete_stories(mock_thread, mock_gen, db, test_user):
    from webapp.models.database import Chapter, Story
    from webapp.services.generation import resume_incomplete_stories
    from webapp.services.mnemonic import generate as gen_mnemonic

    _pid, _slug = gen_mnemonic()
    user = test_user
    story = Story(
        user_id=user.id,
        title="Stuck Story",
        status="generating",
        prompt="test prompt",
        public_id=_pid,
        slug=_slug,
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    ch1 = Chapter(story_id=story.id, chapter_number=1, status="completed", script_json='[{"type":"line","text":"hi"}]')
    ch2 = Chapter(story_id=story.id, chapter_number=2, status="generating_script")
    db.add_all([ch1, ch2])
    db.commit()

    mock_thread_instance = MagicMock()
    mock_thread.return_value = mock_thread_instance

    with (
        patch("webapp.services.generation.SessionLocal", return_value=db),
        patch.object(db, "close"),
    ):  # prevent resume from closing our test session
        resume_incomplete_stories()

    mock_thread.assert_called_once()
    mock_thread_instance.start.assert_called_once()
    call_kwargs = mock_thread.call_args[1]["kwargs"]
    assert call_kwargs["story_id"] == story.id
    assert call_kwargs["num_chapters"] == 2


@patch("webapp.services.generation.threading.Thread")
def test_resume_incomplete_stories_no_chapters_marks_failed(mock_thread, db, test_user):
    from webapp.models.database import Story
    from webapp.services.generation import resume_incomplete_stories
    from webapp.services.mnemonic import generate as gen_mnemonic

    _pid, _slug = gen_mnemonic()
    user = test_user
    story = Story(
        user_id=user.id,
        title="Empty Story",
        status="generating",
        public_id=_pid,
        slug=_slug,
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    with (
        patch("webapp.services.generation.SessionLocal", return_value=db),
        patch.object(db, "close"),
    ):  # prevent resume_incomplete_stories from closing our test session
        resume_incomplete_stories()

    db.refresh(story)
    assert story.status == "failed"
    mock_thread.assert_not_called()


def test_resume_incomplete_stories_noop_when_none(db):
    from webapp.services.generation import resume_incomplete_stories

    with patch("webapp.services.generation.SessionLocal", return_value=db), patch.object(db, "close"):
        resume_incomplete_stories()  # should not raise
