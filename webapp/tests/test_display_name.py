"""Tests for display_name feature — profile endpoint, OAuth, public endpoints."""

from webapp.models.database import Story
from webapp.services.mnemonic import generate as generate_mnemonic


def test_register_sets_display_name(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "dn@test.com", "username": "dnuser", "password": "pass123"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "dnuser"


def test_me_returns_display_name(client, test_user, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "display_name" in data


def test_update_profile_happy_path(client, auth_headers):
    resp = client.put(
        "/api/auth/profile",
        json={"display_name": "Cool Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Cool Name"


def test_update_profile_trims_whitespace(client, auth_headers):
    resp = client.put(
        "/api/auth/profile",
        json={"display_name": "  Trimmed  "},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Trimmed"


def test_update_profile_empty_rejected(client, auth_headers):
    resp = client.put(
        "/api/auth/profile",
        json={"display_name": "   "},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_update_profile_too_long_rejected(client, auth_headers):
    resp = client.put(
        "/api/auth/profile",
        json={"display_name": "x" * 51},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_update_profile_unauthenticated(client):
    resp = client.put("/api/auth/profile", json={"display_name": "Nope"})
    assert resp.status_code == 401


def test_public_stories_returns_display_name(client, db, test_user, auth_headers):
    # Set display_name on user
    test_user.display_name = "Storyteller"
    db.commit()

    # Create a public completed story
    public_id, slug = generate_mnemonic()
    story = Story(
        user_id=test_user.id,
        public_id=public_id,
        slug=slug,
        title="Public Story",
        status="completed",
        visibility="public",
    )
    db.add(story)
    db.commit()

    resp = client.get("/api/public/stories")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["owner_name"] == "Storyteller"


def test_public_story_detail_returns_display_name(client, db, test_user, auth_headers):
    test_user.display_name = "Author Name"
    db.commit()

    public_id, slug = generate_mnemonic()
    story = Story(
        user_id=test_user.id,
        public_id=public_id,
        slug=slug,
        title="Visible Story",
        status="completed",
        visibility="public",
    )
    db.add(story)
    db.commit()

    resp = client.get(f"/api/public/stories/{slug}")
    assert resp.status_code == 200
    assert resp.json()["owner_name"] == "Author Name"


def test_public_stories_falls_back_to_username(client, db, test_user, auth_headers):
    # Ensure no display_name set
    test_user.display_name = None
    db.commit()

    public_id, slug = generate_mnemonic()
    story = Story(
        user_id=test_user.id,
        public_id=public_id,
        slug=slug,
        title="Fallback Story",
        status="completed",
        visibility="public",
    )
    db.add(story)
    db.commit()

    resp = client.get("/api/public/stories")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["owner_name"] == "testuser"


def test_user_profile_returns_display_name(client, db, test_user, other_user, other_auth_headers):
    test_user.display_name = "Fancy Name"
    db.commit()

    resp = client.get(f"/api/follows/users/{test_user.id}/profile", headers=other_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Fancy Name"
    assert data["username"] == "testuser"
