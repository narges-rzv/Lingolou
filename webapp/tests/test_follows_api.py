"""Tests for the follows API — follow/unfollow, timeline, user profiles, followers visibility."""

from webapp.models.database import Chapter, Follow, Story, World


class TestFollowToggle:
    def test_follow_user(self, client, test_user, other_user, auth_headers):
        resp = client.post(f"/api/follows/users/{other_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["following"] is True

    def test_unfollow_user(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        resp = client.post(f"/api/follows/users/{other_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["following"] is False

    def test_cannot_follow_self(self, client, test_user, auth_headers):
        resp = client.post(f"/api/follows/users/{test_user.id}", headers=auth_headers)
        assert resp.status_code == 400
        assert "yourself" in resp.json()["detail"].lower()

    def test_follow_nonexistent_user(self, client, test_user, auth_headers):
        resp = client.post("/api/follows/users/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_follow_unauthenticated(self, client, other_user):
        resp = client.post(f"/api/follows/users/{other_user.id}")
        assert resp.status_code == 401


class TestFollowLists:
    def test_list_following(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        resp = client.get("/api/follows/following", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["username"] == "otheruser"
        assert data[0]["is_following"] is True

    def test_list_followers(self, client, db, test_user, other_user, other_auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        resp = client.get("/api/follows/followers", headers=other_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["username"] == "testuser"


class TestTimeline:
    def _create_story(self, db, user, *, visibility="public", status="completed"):
        story = Story(
            user_id=user.id,
            title=f"{user.username}'s story",
            status=status,
            visibility=visibility,
        )
        db.add(story)
        db.flush()
        db.add(Chapter(story_id=story.id, chapter_number=1, status="completed"))
        db.commit()
        db.refresh(story)
        return story

    def test_timeline_shows_followed_public_stories(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        self._create_story(db, other_user, visibility="public")
        resp = client.get("/api/follows/timeline", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["owner_name"] == "otheruser"

    def test_timeline_shows_followers_visibility_stories(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        self._create_story(db, other_user, visibility="followers")
        resp = client.get("/api/follows/timeline", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_timeline_excludes_private_stories(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        self._create_story(db, other_user, visibility="private")
        resp = client.get("/api/follows/timeline", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_timeline_excludes_followers_stories_from_non_followed(
        self, client, db, test_user, other_user, third_user, auth_headers
    ):
        # test_user does NOT follow third_user
        self._create_story(db, third_user, visibility="followers")
        resp = client.get("/api/follows/timeline", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_timeline_empty_when_no_follows(self, client, test_user, auth_headers):
        resp = client.get("/api/follows/timeline", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestTimelineWorlds:
    def test_timeline_worlds(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        world = World(
            user_id=other_user.id,
            name="Other's World",
            visibility="public",
        )
        db.add(world)
        db.commit()
        resp = client.get("/api/follows/timeline/worlds", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Other's World"


class TestUserProfile:
    def test_get_profile(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        resp = client.get(f"/api/follows/users/{other_user.id}/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "otheruser"
        assert data["follower_count"] == 1
        assert data["is_following"] is True

    def test_profile_not_found(self, client, test_user, auth_headers):
        resp = client.get("/api/follows/users/9999/profile", headers=auth_headers)
        assert resp.status_code == 404


class TestFollowersVisibility:
    def _create_story(self, db, user, *, visibility="followers"):
        story = Story(
            user_id=user.id,
            title="Followers-only story",
            status="completed",
            visibility=visibility,
        )
        db.add(story)
        db.flush()
        db.add(Chapter(story_id=story.id, chapter_number=1, status="completed"))
        db.commit()
        db.refresh(story)
        return story

    def test_follower_can_access_followers_story(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        story = self._create_story(db, other_user)
        resp = client.get(f"/api/public/stories/{story.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Followers-only story"

    def test_non_follower_cannot_access_followers_story(
        self, client, db, test_user, other_user, third_user, third_auth_headers
    ):
        story = self._create_story(db, other_user)
        resp = client.get(f"/api/public/stories/{story.id}", headers=third_auth_headers)
        assert resp.status_code == 404

    def test_unauthenticated_cannot_access_followers_story(self, client, db, other_user):
        story = self._create_story(db, other_user)
        resp = client.get(f"/api/public/stories/{story.id}")
        assert resp.status_code == 404

    def test_followers_world_visible_to_follower(self, client, db, test_user, other_user, auth_headers):
        db.add(Follow(follower_id=test_user.id, following_id=other_user.id))
        db.commit()
        world = World(user_id=other_user.id, name="Followers World", visibility="followers")
        db.add(world)
        db.commit()
        db.refresh(world)
        resp = client.get(f"/api/worlds/{world.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Followers World"

    def test_followers_world_hidden_from_non_follower(self, client, db, other_user, third_user, third_auth_headers):
        world = World(user_id=other_user.id, name="Followers World", visibility="followers")
        db.add(world)
        db.commit()
        db.refresh(world)
        resp = client.get(f"/api/worlds/{world.id}", headers=third_auth_headers)
        assert resp.status_code == 404
