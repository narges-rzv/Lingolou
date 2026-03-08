"""Tests for voice config path resolution."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from webapp.models.database import Chapter, Story, World
from webapp.services.mnemonic import generate as generate_mnemonic


def test_voice_config_from_world(client, db, auth_headers, test_user):
    """When a world has voice_config_json, the endpoint uses it."""
    world = World(
        user_id=test_user.id,
        name="VoiceWorld",
        voice_config_json=json.dumps({"NARRATOR": {"voice_id": "world-voice"}}),
        characters_json=json.dumps({"NARRATOR": "Tells story"}),
        valid_speakers_json=json.dumps(["NARRATOR"]),
        visibility="private",
    )
    db.add(world)
    db.commit()
    db.refresh(world)

    _pid, _slug = generate_mnemonic()
    story = Story(
        user_id=test_user.id, title="VC Test", world_id=world.id, status="completed", public_id=_pid, slug=_slug
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    ch = Chapter(
        story_id=story.id,
        chapter_number=1,
        script_json=json.dumps([{"speaker": "NARRATOR", "text": "Hello"}]),
        status="completed",
    )
    db.add(ch)
    db.commit()

    resp = client.get(f"/api/stories/{story.slug}/voice-config", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["voice_config"]["NARRATOR"]["voice_id"] == "world-voice"


def test_voice_config_from_disk(client, db, auth_headers, test_user, tmp_path):
    """When world has no voice config, falls back to disk file."""
    world = World(
        user_id=test_user.id,
        name="NoVoiceWorld",
        voice_config_json=None,
        characters_json=json.dumps({"NARRATOR": "Tells story"}),
        valid_speakers_json=json.dumps(["NARRATOR"]),
        visibility="private",
    )
    db.add(world)
    db.commit()
    db.refresh(world)

    _pid, _slug = generate_mnemonic()
    story = Story(
        user_id=test_user.id, title="Disk VC", world_id=world.id, status="completed", public_id=_pid, slug=_slug
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    ch = Chapter(
        story_id=story.id,
        chapter_number=1,
        script_json=json.dumps([{"speaker": "NARRATOR", "text": "Hello"}]),
        status="completed",
    )
    db.add(ch)
    db.commit()

    # Write a voices config file to temp path
    voices_file = tmp_path / "voices_config.json"
    voices_file.write_text(json.dumps({"voices": {"NARRATOR": {"voice_id": "disk-voice"}}}))

    with patch.dict(os.environ, {"VOICES_CONFIG_PATH": str(voices_file)}):
        resp = client.get(f"/api/stories/{story.slug}/voice-config", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["voice_config"]["NARRATOR"]["voice_id"] == "disk-voice"


def test_voice_config_missing_returns_empty(client, db, auth_headers, test_user):
    """When no voice config at all, returns empty config."""
    world = World(
        user_id=test_user.id,
        name="EmptyWorld",
        voice_config_json=None,
        characters_json=json.dumps({"NARRATOR": "Tells story"}),
        valid_speakers_json=json.dumps(["NARRATOR"]),
        visibility="private",
    )
    db.add(world)
    db.commit()
    db.refresh(world)

    _pid, _slug = generate_mnemonic()
    story = Story(
        user_id=test_user.id, title="No VC", world_id=world.id, status="completed", public_id=_pid, slug=_slug
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    ch = Chapter(
        story_id=story.id,
        chapter_number=1,
        script_json=json.dumps([{"speaker": "NARRATOR", "text": "Hello"}]),
        status="completed",
    )
    db.add(ch)
    db.commit()

    with patch.dict(os.environ, {"VOICES_CONFIG_PATH": "/nonexistent/voices_config.json"}):
        resp = client.get(f"/api/stories/{story.slug}/voice-config", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["voice_config"] == {}


def test_copy_bundled_voices_config(tmp_path):
    """Test auto-copy of bundled voices_config.json on startup."""
    from webapp.models.database import _copy_bundled_voices_config

    target = tmp_path / "voices_config.json"
    with patch.dict(os.environ, {"VOICES_CONFIG_PATH": str(target)}):
        _copy_bundled_voices_config()

    # Should have copied if the bundled file exists at project root
    project_root = Path(__file__).resolve().parent.parent.parent / "voices_config.json"
    if project_root.exists():
        assert target.exists()
    else:
        # If running in CI without the bundled file, skip
        pytest.skip("No bundled voices_config.json found")
