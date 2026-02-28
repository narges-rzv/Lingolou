"""Tests for the blocks API — block/unblock, block enforcement on follows/timeline/profiles."""

from webapp.models.database import Block, Chapter, Follow, Story


class TestBlockToggle:
    def test_block_user(self, client, test_user, other_user, auth_headers):
        resp = client.post(f"/api/blocks/users/{other_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["blocked"] is True

    def test_unblock_user(self, client, db, test_user, other_user, auth_headers):
        db.add(Block(blocker_id=test_user.id, blocked_id=other_user.id))
        db.commit()
        resp = client.post(f"/api/blocks/users/{other_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["blocked"] is False

    def test_cannot_block_self(self, client, test_user, auth_headers):
        resp = client.post(f"/api/blocks/users/{test_user.id}", headers=auth_headers)
        assert resp.status_code == 400
        assert "yourself" in resp.json()["detail"].lower()

    def test_block_nonexistent_user(self, client, test_user, auth_headers):
        resp = client.post("/api/blocks/users/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_block_removes_mutual_follows(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.add(Follow(follower_id=other_user.id, following_id=test_user.id))
        db.commit()
        resp = client.post(f"/api/blocks/users/{other_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["blocked"] is True
        # Both follows should be removed
        assert (
            db.query(Follow).filter(Follow.follower_id == test_user.id, Follow.following_id == other_user.id).first()
            is None
        )
        assert (
            db.query(Follow).filter(Follow.follower_id == other_user.id, Follow.following_id == test_user.id).first()
            is None
        )

    def test_block_unauthenticated(self, client, other_user):
        resp = client.post(f"/api/blocks/users/{other_user.id}")
        assert resp.status_code == 401


class TestBlockedUserList:
    def test_list_blocked_users(self, client, db, test_user, other_user, auth_headers):
        db.add(Block(blocker_id=test_user.id, blocked_id=other_user.id))
        db.commit()
        resp = client.get("/api/blocks/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["username"] == "otheruser"
        assert "blocked_at" in data[0]

    def test_list_blocked_empty(self, client, test_user, auth_headers):
        resp = client.get("/api/blocks/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestBlockEnforcement:
    def test_blocked_user_cannot_follow(self, client, db, test_user, other_user, other_auth_headers):
        db.add(Block(blocker_id=test_user.id, blocked_id=other_user.id))
        db.commit()
        resp = client.post(f"/api/follows/users/{test_user.id}", headers=other_auth_headers)
        assert resp.status_code == 403

    def test_blocker_cannot_follow_blocked(self, client, db, test_user, other_user, auth_headers):
        db.add(Block(blocker_id=test_user.id, blocked_id=other_user.id))
        db.commit()
        resp = client.post(f"/api/follows/users/{other_user.id}", headers=auth_headers)
        assert resp.status_code == 403

    def test_blocked_user_profile_returns_404(self, client, db, test_user, other_user, auth_headers):
        db.add(Block(blocker_id=test_user.id, blocked_id=other_user.id))
        db.commit()
        resp = client.get(f"/api/follows/users/{other_user.id}/profile", headers=auth_headers)
        assert resp.status_code == 404

    def test_blocked_user_excluded_from_timeline(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        story = Story(user_id=other_user.id, title="Blocked story", status="completed", visibility="public")
        db.add(story)
        db.flush()
        db.add(Chapter(story_id=story.id, chapter_number=1, status="completed"))
        db.commit()
        # Block after following — follows still exist but timeline filters
        db.add(Block(blocker_id=test_user.id, blocked_id=other_user.id))
        db.commit()
        resp = client.get("/api/follows/timeline", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_blocked_user_story_returns_404(self, client, db, test_user, other_user, auth_headers):
        db.add(Block(blocker_id=test_user.id, blocked_id=other_user.id))
        db.commit()
        story = Story(user_id=other_user.id, title="Hidden story", status="completed", visibility="public")
        db.add(story)
        db.flush()
        db.add(Chapter(story_id=story.id, chapter_number=1, status="completed"))
        db.commit()
        resp = client.get(f"/api/public/stories/{story.id}", headers=auth_headers)
        assert resp.status_code == 404
