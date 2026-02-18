"""Tests for the bookmarks API."""

from webapp.models.database import Story


def _make_public_story(db, user, title="Public Story"):
    story = Story(
        user_id=user.id,
        title=title,
        description="A public story",
        status="completed",
        visibility="public",
        language="Persian (Farsi)",
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def _make_private_story(db, user):
    story = Story(
        user_id=user.id,
        title="Private Story",
        description="A private story",
        status="completed",
        visibility="private",
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def test_bookmark_story(client, db, test_user, other_user, auth_headers):
    story = _make_public_story(db, other_user)
    resp = client.post(f"/api/bookmarks/stories/{story.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["bookmarked"] is True


def test_unbookmark_story(client, db, test_user, other_user, auth_headers):
    story = _make_public_story(db, other_user)
    # Bookmark first
    client.post(f"/api/bookmarks/stories/{story.id}", headers=auth_headers)
    # Toggle off
    resp = client.post(f"/api/bookmarks/stories/{story.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["bookmarked"] is False


def test_bookmark_private_story(client, db, test_user, other_user, auth_headers):
    story = _make_private_story(db, other_user)
    resp = client.post(f"/api/bookmarks/stories/{story.id}", headers=auth_headers)
    assert resp.status_code == 404


def test_bookmark_unauthenticated(client, db, test_user):
    story = _make_public_story(db, test_user)
    resp = client.post(f"/api/bookmarks/stories/{story.id}")
    assert resp.status_code == 401


def test_list_bookmarked_stories(client, db, test_user, other_user, auth_headers):
    s1 = _make_public_story(db, other_user, title="Story One")
    s2 = _make_public_story(db, other_user, title="Story Two")
    client.post(f"/api/bookmarks/stories/{s1.id}", headers=auth_headers)
    client.post(f"/api/bookmarks/stories/{s2.id}", headers=auth_headers)

    resp = client.get("/api/bookmarks/stories", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Most recent first
    assert data[0]["title"] == "Story Two"
    assert data[1]["title"] == "Story One"
    assert "bookmarked_at" in data[0]
    assert "owner_name" in data[0]


def test_list_bookmarked_stories_empty(client, db, test_user, auth_headers):
    resp = client.get("/api/bookmarks/stories", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_bookmark_nonexistent_story(client, db, test_user, auth_headers):
    resp = client.post("/api/bookmarks/stories/9999", headers=auth_headers)
    assert resp.status_code == 404


def test_public_story_shows_bookmark_state(client, db, test_user, other_user, auth_headers):
    story = _make_public_story(db, other_user)

    # Before bookmarking
    resp = client.get(f"/api/public/stories/{story.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_bookmarked"] is False

    # Bookmark it
    client.post(f"/api/bookmarks/stories/{story.id}", headers=auth_headers)

    # After bookmarking
    resp = client.get(f"/api/public/stories/{story.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_bookmarked"] is True


def test_bookmark_own_story(client, db, test_user, auth_headers):
    """Users can bookmark their own public stories too."""
    story = _make_public_story(db, test_user)
    resp = client.post(f"/api/bookmarks/stories/{story.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["bookmarked"] is True
