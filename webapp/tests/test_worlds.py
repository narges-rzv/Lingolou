"""Tests for world CRUD API endpoints and voice config."""

import json

from webapp.models.database import Chapter, Story


class TestWorldCRUD:
    def test_create_world(self, client, auth_headers):
        resp = client.post(
            "/api/worlds/",
            json={
                "name": "My World",
                "description": "A custom world",
                "prompt_template": "Story about {language} and {theme}",
                "characters": {"HERO": "The brave hero", "VILLAIN": "The sneaky villain"},
                "valid_speakers": ["NARRATOR", "HERO", "VILLAIN"],
                "visibility": "private",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My World"
        assert data["characters"]["HERO"] == "The brave hero"
        assert data["valid_speakers"] == ["NARRATOR", "HERO", "VILLAIN"]
        assert data["is_builtin"] is False
        assert data["visibility"] == "private"

    def test_create_world_invalid_visibility(self, client, auth_headers):
        resp = client.post(
            "/api/worlds/",
            json={"name": "Bad", "visibility": "invalid"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_list_worlds_includes_own_and_builtin(self, client, auth_headers, test_world, builtin_world):
        resp = client.get("/api/worlds/", headers=auth_headers)
        assert resp.status_code == 200
        names = {w["name"] for w in resp.json()}
        assert "Test World" in names
        assert "Built-in World" in names

    def test_list_worlds_excludes_other_private(self, client, other_auth_headers, test_world):
        resp = client.get("/api/worlds/", headers=other_auth_headers)
        assert resp.status_code == 200
        names = {w["name"] for w in resp.json()}
        assert "Test World" not in names

    def test_get_world_owner(self, client, auth_headers, test_world):
        resp = client.get(f"/api/worlds/{test_world.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test World"

    def test_get_world_not_found(self, client, auth_headers):
        resp = client.get("/api/worlds/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_world_other_user_private(self, client, other_auth_headers, test_world):
        resp = client.get(f"/api/worlds/{test_world.id}", headers=other_auth_headers)
        assert resp.status_code == 404

    def test_get_builtin_world(self, client, auth_headers, builtin_world):
        resp = client.get(f"/api/worlds/{builtin_world.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_builtin"] is True

    def test_update_world(self, client, auth_headers, test_world):
        resp = client.patch(
            f"/api/worlds/{test_world.id}",
            json={"name": "Updated World", "visibility": "public"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated World"
        assert data["visibility"] == "public"
        assert data["share_code"] is not None

    def test_update_world_not_owner(self, client, other_auth_headers, test_world):
        resp = client.patch(
            f"/api/worlds/{test_world.id}",
            json={"name": "Hacked"},
            headers=other_auth_headers,
        )
        assert resp.status_code == 404

    def test_update_builtin_forbidden(self, client, auth_headers, builtin_world, db, test_user):
        # Assign user as owner temporarily to pass ownership check
        builtin_world.user_id = test_user.id
        db.commit()
        resp = client.patch(
            f"/api/worlds/{builtin_world.id}",
            json={"name": "Hacked"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_delete_world(self, client, auth_headers, test_world):
        resp = client.delete(f"/api/worlds/{test_world.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "World deleted"

    def test_delete_world_not_owner(self, client, other_auth_headers, test_world):
        resp = client.delete(f"/api/worlds/{test_world.id}", headers=other_auth_headers)
        assert resp.status_code == 404

    def test_delete_builtin_forbidden(self, client, auth_headers, builtin_world, db, test_user):
        builtin_world.user_id = test_user.id
        db.commit()
        resp = client.delete(f"/api/worlds/{builtin_world.id}", headers=auth_headers)
        assert resp.status_code == 403

    def test_delete_world_with_stories(self, client, auth_headers, test_world):
        # Create a story using this world
        client.post(
            "/api/stories/",
            json={"title": "Test Story", "world_id": test_world.id},
            headers=auth_headers,
        )
        resp = client.delete(f"/api/worlds/{test_world.id}", headers=auth_headers)
        assert resp.status_code == 400
        assert "stories" in resp.json()["detail"].lower()

    def test_share_link(self, client, auth_headers, test_world):
        resp = client.post(f"/api/worlds/{test_world.id}/share-link", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["share_code"]
        assert "worlds/share/" in data["share_url"]


class TestWorldPublicEndpoints:
    def test_list_public_worlds(self, client, builtin_world):
        resp = client.get("/api/public/worlds")
        assert resp.status_code == 200
        names = {w["name"] for w in resp.json()}
        assert "Built-in World" in names

    def test_list_public_worlds_excludes_private(self, client, test_world):
        resp = client.get("/api/public/worlds")
        assert resp.status_code == 200
        names = {w["name"] for w in resp.json()}
        assert "Test World" not in names

    def test_get_public_world(self, client, builtin_world):
        resp = client.get(f"/api/public/worlds/{builtin_world.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Built-in World"

    def test_get_private_world_404(self, client, test_world):
        resp = client.get(f"/api/public/worlds/{test_world.id}")
        assert resp.status_code == 404

    def test_get_shared_world(self, client, auth_headers, test_world, db):
        # Make world link_only with share code
        test_world.visibility = "link_only"
        test_world.share_code = "test-share-code"
        db.commit()
        resp = client.get("/api/public/share/world/test-share-code")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test World"

    def test_get_shared_world_not_found(self, client):
        resp = client.get("/api/public/share/world/nonexistent")
        assert resp.status_code == 404


class TestWorldAwareStories:
    def test_create_story_with_world(self, client, auth_headers, test_world):
        resp = client.post(
            "/api/stories/",
            json={"title": "World Story", "world_id": test_world.id},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["world_id"] == test_world.id
        assert data["world_name"] == "Test World"

    def test_create_story_with_invalid_world(self, client, auth_headers):
        resp = client.post(
            "/api/stories/",
            json={"title": "Bad Story", "world_id": 9999},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_story_list_includes_world_name(self, client, auth_headers, test_world):
        client.post(
            "/api/stories/",
            json={"title": "World Story", "world_id": test_world.id},
            headers=auth_headers,
        )
        resp = client.get("/api/stories/", headers=auth_headers)
        assert resp.status_code == 200
        story = resp.json()[0]
        assert story["world_name"] == "Test World"

    def test_story_detail_includes_world_name(self, client, auth_headers, test_world):
        create_resp = client.post(
            "/api/stories/",
            json={"title": "World Story", "world_id": test_world.id},
            headers=auth_headers,
        )
        story_id = create_resp.json()["id"]
        resp = client.get(f"/api/stories/{story_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["world_name"] == "Test World"


class TestVoiceConfig:
    def _create_story_with_script(self, db, user_id, world_id=None):
        story = Story(user_id=user_id, title="Voice Test", status="completed", world_id=world_id)
        db.add(story)
        db.commit()
        db.refresh(story)
        script = json.dumps(
            [
                {"type": "line", "speaker": "NARRATOR", "text": "Hello"},
                {"type": "line", "speaker": "WINNIE", "text": "Let's go"},
                {"type": "line", "speaker": "NARRATOR", "text": "The end"},
            ]
        )
        ch = Chapter(story_id=story.id, chapter_number=1, status="completed", enhanced_json=script)
        db.add(ch)
        db.commit()
        return story

    def test_voice_config_with_world(self, client, auth_headers, test_user, test_world, db):
        story = self._create_story_with_script(db, test_user.id, world_id=test_world.id)
        resp = client.get(f"/api/stories/{story.id}/voice-config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "NARRATOR" in data["speakers"]
        assert "WINNIE" in data["speakers"]
        # Voice config comes from world
        assert data["voice_config"]["NARRATOR"]["voice_id"] == "abc123"

    def test_voice_config_without_world_empty(self, client, auth_headers, test_user, db):
        story = self._create_story_with_script(db, test_user.id)
        resp = client.get(f"/api/stories/{story.id}/voice-config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Speakers still extracted from scripts
        assert "NARRATOR" in data["speakers"]
        assert "WINNIE" in data["speakers"]

    def test_voice_config_not_found(self, client, auth_headers):
        resp = client.get("/api/stories/9999/voice-config", headers=auth_headers)
        assert resp.status_code == 404

    def test_voice_config_no_scripts(self, client, auth_headers, test_user, db):
        story = Story(user_id=test_user.id, title="Empty", status="created")
        db.add(story)
        db.commit()
        db.refresh(story)
        resp = client.get(f"/api/stories/{story.id}/voice-config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["speakers"] == []
        # voice_config may come from disk fallback or be empty
        assert isinstance(data["voice_config"], dict)
