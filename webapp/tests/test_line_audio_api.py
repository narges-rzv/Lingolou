"""Tests for per-line audio endpoints in webapp/api/stories.py."""

import json
import os

from webapp.models.database import Chapter, Story


def _create_story_with_line_audio(db, user_id):
    """Create a story with a chapter that has line_audio_json populated."""
    story = Story(
        user_id=user_id,
        public_id="test-line-audio-id",
        slug="test-line-audio-slug",
        title="Line Audio Test",
        status="completed",
        visibility="private",
    )
    db.add(story)
    db.flush()

    script = [
        {"type": "scene", "title": "Opening"},
        {"type": "line", "speaker": "NARRATOR", "lang": "en", "text": "Hello there."},
        {"type": "pause", "seconds": 0.5},
        {"type": "line", "speaker": "HERO", "lang": "fa", "text": "Salam!"},
    ]
    line_map = {
        "1": f"{story.id}/ch1/line_1.mp3",
        "3": f"{story.id}/ch1/line_3.mp3",
    }
    chapter = Chapter(
        story_id=story.id,
        chapter_number=1,
        title="Chapter 1",
        script_json=json.dumps(script),
        audio_path=f"{story.id}/ch1.mp3",
        line_audio_json=json.dumps(line_map),
        status="completed",
    )
    db.add(chapter)
    db.commit()
    return story


def _create_story_without_line_audio(db, user_id):
    """Create a story whose chapter has no line_audio_json (legacy)."""
    story = Story(
        user_id=user_id,
        public_id="test-no-line-audio-id",
        slug="test-no-line-audio-slug",
        title="No Line Audio Test",
        status="completed",
        visibility="private",
    )
    db.add(story)
    db.flush()

    script = [
        {"type": "line", "speaker": "NARRATOR", "lang": "en", "text": "Hello."},
    ]
    chapter = Chapter(
        story_id=story.id,
        chapter_number=1,
        title="Chapter 1",
        script_json=json.dumps(script),
        audio_path=f"{story.id}/ch1.mp3",
        line_audio_json=None,
        status="completed",
    )
    db.add(chapter)
    db.commit()
    return story


# --- GET line audio tests ---


def test_get_line_audio_success(client, auth_headers, db, test_user):
    story = _create_story_with_line_audio(db, test_user.id)
    resp = client.get(
        f"/api/stories/{story.slug}/chapters/1/lines/1/audio",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data
    assert "line_1.mp3" in data["url"]


def test_get_line_audio_no_segments(client, auth_headers, db, test_user):
    story = _create_story_without_line_audio(db, test_user.id)
    resp = client.get(
        f"/api/stories/{story.slug}/chapters/1/lines/0/audio",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert "No per-line audio" in resp.json()["detail"]


def test_get_line_audio_invalid_index(client, auth_headers, db, test_user):
    story = _create_story_with_line_audio(db, test_user.id)
    # Index 0 is a scene, not in line_audio_json
    resp = client.get(
        f"/api/stories/{story.slug}/chapters/1/lines/0/audio",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert "not found for this index" in resp.json()["detail"]


def test_get_line_audio_not_owner(client, other_auth_headers, db, test_user):
    story = _create_story_with_line_audio(db, test_user.id)
    resp = client.get(
        f"/api/stories/{story.slug}/chapters/1/lines/1/audio",
        headers=other_auth_headers,
    )
    assert resp.status_code == 404


# --- POST regenerate line tests ---


def test_regenerate_line_success(client, auth_headers, db, test_user):
    story = _create_story_with_line_audio(db, test_user.id)
    # Set ElevenLabs key in env so endpoint can resolve it
    os.environ["ELEVENLABS_API_KEY"] = "test-key"
    try:
        resp = client.post(
            f"/api/stories/{story.slug}/chapters/1/lines/1/regenerate",
            headers=auth_headers,
            json=None,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert "task_id" in data
    finally:
        os.environ.pop("ELEVENLABS_API_KEY", None)


def test_regenerate_line_not_a_line(client, auth_headers, db, test_user):
    story = _create_story_with_line_audio(db, test_user.id)
    os.environ["ELEVENLABS_API_KEY"] = "test-key"
    try:
        # Index 0 is a scene entry
        resp = client.post(
            f"/api/stories/{story.slug}/chapters/1/lines/0/regenerate",
            headers=auth_headers,
            json=None,
        )
        assert resp.status_code == 400
        assert "not a dialogue line" in resp.json()["detail"]
    finally:
        os.environ.pop("ELEVENLABS_API_KEY", None)


def test_regenerate_line_no_line_audio(client, auth_headers, db, test_user):
    story = _create_story_without_line_audio(db, test_user.id)
    os.environ["ELEVENLABS_API_KEY"] = "test-key"
    try:
        resp = client.post(
            f"/api/stories/{story.slug}/chapters/1/lines/0/regenerate",
            headers=auth_headers,
            json=None,
        )
        assert resp.status_code == 400
        assert "no per-line audio" in resp.json()["detail"].lower()
    finally:
        os.environ.pop("ELEVENLABS_API_KEY", None)


def test_regenerate_line_no_api_key(client, auth_headers, db, test_user):
    story = _create_story_with_line_audio(db, test_user.id)
    # Ensure no key is available
    os.environ.pop("ELEVENLABS_API_KEY", None)
    resp = client.post(
        f"/api/stories/{story.slug}/chapters/1/lines/1/regenerate",
        headers=auth_headers,
        json=None,
    )
    assert resp.status_code == 403


# --- has_line_audio in ChapterResponse ---


def test_chapter_response_has_line_audio_true(client, auth_headers, db, test_user):
    story = _create_story_with_line_audio(db, test_user.id)
    resp = client.get(f"/api/stories/{story.slug}", headers=auth_headers)
    assert resp.status_code == 200
    chapters = resp.json()["chapters"]
    assert len(chapters) == 1
    assert chapters[0]["has_line_audio"] is True


def test_chapter_response_has_line_audio_false(client, auth_headers, db, test_user):
    story = _create_story_without_line_audio(db, test_user.id)
    resp = client.get(f"/api/stories/{story.slug}", headers=auth_headers)
    assert resp.status_code == 200
    chapters = resp.json()["chapters"]
    assert len(chapters) == 1
    assert chapters[0]["has_line_audio"] is False
