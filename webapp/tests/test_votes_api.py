"""Tests for webapp/api/votes.py"""

from webapp.models.database import Story, Chapter


def _create_public_story(db, user):
    story = Story(
        user_id=user.id,
        title="Voteable Story",
        status="completed",
        visibility="public",
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def test_upvote(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user)

    resp = client.post(f"/api/votes/stories/{story.id}", json={
        "vote_type": "up",
    }, headers=other_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["upvotes"] == 1
    assert data["downvotes"] == 0
    assert data["user_vote"] == "up"


def test_downvote(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user)

    resp = client.post(f"/api/votes/stories/{story.id}", json={
        "vote_type": "down",
    }, headers=other_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["downvotes"] == 1
    assert data["user_vote"] == "down"


def test_change_vote(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user)

    # Upvote
    client.post(f"/api/votes/stories/{story.id}", json={
        "vote_type": "up",
    }, headers=other_auth_headers)

    # Change to downvote
    resp = client.post(f"/api/votes/stories/{story.id}", json={
        "vote_type": "down",
    }, headers=other_auth_headers)
    data = resp.json()
    assert data["upvotes"] == 0
    assert data["downvotes"] == 1
    assert data["user_vote"] == "down"


def test_remove_vote(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user)

    # Upvote first
    client.post(f"/api/votes/stories/{story.id}", json={
        "vote_type": "up",
    }, headers=other_auth_headers)

    # Remove vote
    resp = client.post(f"/api/votes/stories/{story.id}", json={
        "vote_type": None,
    }, headers=other_auth_headers)
    data = resp.json()
    assert data["upvotes"] == 0
    assert data["downvotes"] == 0
    assert data["user_vote"] is None


def test_vote_own_story(client, db, test_user, auth_headers):
    story = _create_public_story(db, test_user)

    resp = client.post(f"/api/votes/stories/{story.id}", json={
        "vote_type": "up",
    }, headers=auth_headers)
    assert resp.status_code == 400
    assert "own story" in resp.json()["detail"].lower()


def test_vote_private_story(client, db, test_user, other_user, other_auth_headers):
    story = Story(
        user_id=test_user.id,
        title="Private Story",
        status="completed",
        visibility="private",
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    resp = client.post(f"/api/votes/stories/{story.id}", json={
        "vote_type": "up",
    }, headers=other_auth_headers)
    assert resp.status_code == 404


def test_vote_invalid_type(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user)

    resp = client.post(f"/api/votes/stories/{story.id}", json={
        "vote_type": "invalid",
    }, headers=other_auth_headers)
    assert resp.status_code == 400
