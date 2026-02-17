"""Tests for webapp/api/public.py"""

from webapp.models.database import Chapter, Story, Vote


def _create_public_story(db, user, title="Public Story", status="completed", visibility="public"):
    story = Story(
        user_id=user.id,
        title=title,
        description="A public story",
        status=status,
        visibility=visibility,
        language="Persian (Farsi)",
        share_code=f"share-{title.replace(' ', '-').lower()}",
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    ch = Chapter(
        story_id=story.id,
        chapter_number=1,
        status="completed",
        script_json='[{"type": "line", "text": "hello"}]',
        enhanced_json='[{"type": "line", "text": "hello", "emotion": "happy"}]',
    )
    db.add(ch)
    db.commit()
    db.refresh(story)
    return story


def test_get_budget_status(client):
    resp = client.get("/api/public/budget")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_budget"] == 50.0
    assert data["total_spent"] == 0.0
    assert "free_stories_per_user" in data


def test_list_public_stories(client, db, test_user):
    _create_public_story(db, test_user, title="Story A")
    _create_public_story(db, test_user, title="Story B")

    resp = client.get("/api/public/stories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_list_public_stories_filters_private(client, db, test_user):
    _create_public_story(db, test_user, title="Public", visibility="public")
    _create_public_story(db, test_user, title="Private", visibility="private")

    resp = client.get("/api/public/stories")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Public"


def test_list_public_stories_filters_incomplete(client, db, test_user):
    _create_public_story(db, test_user, title="Complete", status="completed")
    _create_public_story(db, test_user, title="Creating", status="created")

    resp = client.get("/api/public/stories")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Complete"


def test_list_public_stories_language_filter(client, db, test_user):
    _create_public_story(db, test_user, title="Farsi Story")
    story2 = _create_public_story(db, test_user, title="Other Story")
    story2.language = "Arabic"
    db.commit()

    resp = client.get("/api/public/stories?language=Persian (Farsi)")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Farsi Story"


def test_get_public_story(client, db, test_user):
    story = _create_public_story(db, test_user)

    resp = client.get(f"/api/public/stories/{story.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Public Story"
    assert data["owner_name"] == "testuser"
    assert data["user_vote"] is None


def test_get_public_story_with_user_vote(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user)

    # Other user votes
    db.add(Vote(user_id=other_user.id, story_id=story.id, vote_type="up"))
    db.commit()

    resp = client.get(f"/api/public/stories/{story.id}", headers=other_auth_headers)
    data = resp.json()
    assert data["user_vote"] == "up"


def test_get_private_story_returns_404(client, db, test_user):
    story = _create_public_story(db, test_user, visibility="private")

    resp = client.get(f"/api/public/stories/{story.id}")
    assert resp.status_code == 404


def test_get_shared_story_by_code(client, db, test_user):
    story = _create_public_story(db, test_user)

    resp = client.get(f"/api/public/share/{story.share_code}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Public Story"


def test_get_shared_story_invalid_code(client):
    resp = client.get("/api/public/share/nonexistent-code")
    assert resp.status_code == 404


def test_fork_public_story(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user, title="Original Story")
    story.prompt = "A story about cats"
    db.commit()

    resp = client.post(f"/api/public/stories/{story.id}/fork", headers=other_auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Copy of Original Story"
    assert data["prompt"] == "A story about cats"
    assert data["language"] == "Persian (Farsi)"
    assert data["status"] == "completed"
    assert data["visibility"] == "private"
    assert data["upvotes"] == 0
    assert data["downvotes"] == 0
    assert len(data["chapters"]) == 1
    assert data["chapters"][0]["audio_path"] is None


def test_fork_story_not_public(client, db, test_user, other_auth_headers):
    story = _create_public_story(db, test_user, visibility="private")

    resp = client.post(f"/api/public/stories/{story.id}/fork", headers=other_auth_headers)
    assert resp.status_code == 404


def test_fork_story_unauthenticated(client, db, test_user):
    story = _create_public_story(db, test_user)

    resp = client.post(f"/api/public/stories/{story.id}/fork")
    assert resp.status_code == 401


def test_fork_story_no_chapters(client, db, test_user, other_auth_headers):
    story = Story(
        user_id=test_user.id,
        title="Empty Story",
        description="No chapters",
        status="completed",
        visibility="public",
        language="Arabic",
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    resp = client.post(f"/api/public/stories/{story.id}/fork", headers=other_auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Copy of Empty Story"
    assert len(data["chapters"]) == 0
