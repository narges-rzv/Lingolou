"""Tests for webapp/api/stories.py"""

from unittest.mock import patch

from webapp.models.database import PlatformBudget, Story
from webapp.services.crypto import encrypt_key


def _create_story(client, auth_headers, **overrides):
    payload = {
        "title": "Test Story",
        "description": "A test story",
        "prompt": "Tell a story",
        "num_chapters": 2,
        "language": "Persian (Farsi)",
    }
    payload.update(overrides)
    return client.post("/api/stories/", json=payload, headers=auth_headers)


def test_create_story(client, auth_headers):
    resp = _create_story(client, auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Story"
    assert len(data["chapters"]) == 2
    assert data["status"] == "created"


def test_list_stories(client, auth_headers):
    _create_story(client, auth_headers, title="Story 1")
    _create_story(client, auth_headers, title="Story 2")

    resp = client.get("/api/stories/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_list_stories_only_own(client, auth_headers, other_auth_headers):
    _create_story(client, auth_headers, title="My Story")
    _create_story(client, other_auth_headers, title="Other Story")

    resp = client.get("/api/stories/", headers=auth_headers)
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "My Story"


def test_list_stories_pagination(client, auth_headers):
    for i in range(5):
        _create_story(client, auth_headers, title=f"Story {i}")

    resp = client.get("/api/stories/?skip=2&limit=2", headers=auth_headers)
    data = resp.json()
    assert len(data) == 2


def test_get_story(client, auth_headers):
    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.get(f"/api/stories/{story_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == story_id


def test_get_story_not_found(client, auth_headers):
    resp = client.get("/api/stories/999", headers=auth_headers)
    assert resp.status_code == 404


def test_get_other_users_story(client, auth_headers, other_auth_headers):
    create_resp = _create_story(client, other_auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.get(f"/api/stories/{story_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_get_story_generating_lost_task(client, auth_headers, db):
    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    # Manually set story to generating
    story = db.query(Story).filter(Story.id == story_id).first()
    story.status = "generating"
    db.commit()

    # No active task in memory → should mark as failed
    resp = client.get(f"/api/stories/{story_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"


def test_update_story_title(client, auth_headers):
    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/stories/{story_id}",
        json={
            "title": "Updated Title",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


def test_update_story_visibility(client, auth_headers):
    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/stories/{story_id}",
        json={
            "visibility": "public",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["visibility"] == "public"
    assert data["share_code"] is not None


def test_update_story_invalid_visibility(client, auth_headers):
    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/stories/{story_id}",
        json={
            "visibility": "invalid",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_delete_story(client, auth_headers):
    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.delete(f"/api/stories/{story_id}", headers=auth_headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/stories/{story_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_other_users_story(client, auth_headers, other_auth_headers):
    create_resp = _create_story(client, other_auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.delete(f"/api/stories/{story_id}", headers=auth_headers)
    assert resp.status_code == 404


@patch("webapp.api.stories.generate_story")
def test_generate_story_with_own_key(mock_gen, client, auth_headers, db, test_user):
    # Set user's API key
    test_user.openai_api_key = encrypt_key("sk-userkey")
    db.commit()

    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/stories/{story_id}/generate",
        json={
            "title": "Test",
            "prompt": "Tell a story",
            "num_chapters": 2,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    # Verify the background task was called with decrypted key
    call_kwargs = mock_gen.call_args
    assert call_kwargs is not None


@patch("webapp.api.stories.generate_story")
def test_generate_story_free_tier(mock_gen, client, auth_headers, db, test_user):
    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/stories/{story_id}/generate",
        json={
            "title": "Test",
            "prompt": "Tell a story",
            "num_chapters": 2,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Free stories used should have incremented
    db.refresh(test_user)
    assert test_user.free_stories_used == 1


@patch("webapp.api.stories.generate_story")
def test_generate_story_free_tier_exhausted(mock_gen, client, auth_headers, db, test_user):
    test_user.free_stories_used = 3
    db.commit()

    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/stories/{story_id}/generate",
        json={
            "title": "Test",
            "prompt": "Tell a story",
            "num_chapters": 2,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 403
    assert "Free tier limit" in resp.json()["detail"]


@patch("webapp.api.stories.generate_story")
def test_generate_story_platform_budget_exhausted(mock_gen, client, auth_headers, db):
    budget = db.query(PlatformBudget).first()
    budget.total_spent = 50.0  # Match total_budget
    db.commit()

    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/stories/{story_id}/generate",
        json={
            "title": "Test",
            "prompt": "Tell a story",
            "num_chapters": 2,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 403
    assert "budget exhausted" in resp.json()["detail"]


def test_generate_story_already_generating(client, auth_headers, db):
    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    story = db.query(Story).filter(Story.id == story_id).first()
    story.status = "generating"
    db.commit()

    resp = client.post(
        f"/api/stories/{story_id}/generate",
        json={
            "title": "Test",
            "prompt": "Tell a story",
            "num_chapters": 2,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "already being generated" in resp.json()["detail"]


@patch("webapp.api.stories.generate_audio")
def test_generate_audio_with_own_key(mock_gen, client, auth_headers, db, test_user):
    test_user.elevenlabs_api_key = encrypt_key("el-userkey")
    db.commit()

    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    # Add script to chapters
    story = db.query(Story).filter(Story.id == story_id).first()
    for ch in story.chapters:
        ch.script_json = '[{"type": "line", "text": "hello"}]'
        ch.enhanced_json = '[{"type": "line", "text": "hello", "emotion": "happy"}]'
    db.commit()

    resp = client.post(
        f"/api/stories/{story_id}/generate-audio",
        json={
            "story_id": story_id,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


@patch("webapp.api.stories.generate_audio")
def test_generate_audio_with_platform_key(mock_gen, client, auth_headers, db, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "platform-key")

    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    story = db.query(Story).filter(Story.id == story_id).first()
    for ch in story.chapters:
        ch.script_json = '[{"type": "line", "text": "hello"}]'
    db.commit()

    resp = client.post(
        f"/api/stories/{story_id}/generate-audio",
        json={
            "story_id": story_id,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_generate_audio_no_key(client, auth_headers, db, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    story = db.query(Story).filter(Story.id == story_id).first()
    for ch in story.chapters:
        ch.script_json = '[{"type": "line", "text": "hello"}]'
    db.commit()

    resp = client.post(
        f"/api/stories/{story_id}/generate-audio",
        json={
            "story_id": story_id,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 403


def test_generate_audio_no_script(client, auth_headers):
    create_resp = _create_story(client, auth_headers)
    story_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/stories/{story_id}/generate-audio",
        json={
            "story_id": story_id,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "no script" in resp.json()["detail"].lower()


def test_get_task_status(client, auth_headers):
    from webapp.services.generation import update_task_status

    update_task_status("test_task_1", "running", 50, "Halfway there")

    resp = client.get("/api/stories/tasks/test_task_1", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["progress"] == 50


def test_get_task_status_not_found(client, auth_headers):
    resp = client.get("/api/stories/tasks/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


def test_cancel_task(client, auth_headers):
    from webapp.services.generation import update_task_status

    update_task_status("cancel_me", "running", 30, "Running...")

    resp = client.delete("/api/stories/tasks/cancel_me", headers=auth_headers)
    assert resp.status_code == 200
    assert "cancelled" in resp.json()["message"].lower()
