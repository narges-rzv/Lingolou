"""Tests for webapp/api/auth.py"""

import pytest
from webapp.services.crypto import encrypt_key


def test_register_success(client):
    resp = client.post("/api/auth/register", json={
        "email": "new@test.com",
        "username": "newuser",
        "password": "pass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "new@test.com"
    assert data["username"] == "newuser"


def test_register_duplicate_email(client, test_user):
    resp = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "username": "different",
        "password": "pass123",
    })
    assert resp.status_code == 400
    assert "Email already registered" in resp.json()["detail"]


def test_register_duplicate_username(client, test_user):
    resp = client.post("/api/auth/register", json={
        "email": "different@test.com",
        "username": "testuser",
        "password": "pass123",
    })
    assert resp.status_code == 400
    assert "Username already taken" in resp.json()["detail"]


def test_login_success(client, test_user):
    resp = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, test_user):
    resp = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "wrong",
    })
    assert resp.status_code == 401


def test_me_authenticated(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


def test_me_unauthenticated(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_update_api_keys_openai(client, auth_headers):
    resp = client.put("/api/auth/api-keys", json={
        "openai_api_key": "sk-test123",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_openai_key"] is True
    assert data["has_elevenlabs_key"] is False


def test_update_api_keys_elevenlabs(client, auth_headers):
    resp = client.put("/api/auth/api-keys", json={
        "elevenlabs_api_key": "el-test123",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_elevenlabs_key"] is True


def test_update_api_keys_none_doesnt_overwrite(client, auth_headers):
    # Set OpenAI key first
    client.put("/api/auth/api-keys", json={
        "openai_api_key": "sk-test123",
    }, headers=auth_headers)

    # Update only ElevenLabs, OpenAI should remain
    resp = client.put("/api/auth/api-keys", json={
        "elevenlabs_api_key": "el-test123",
    }, headers=auth_headers)
    data = resp.json()
    assert data["has_openai_key"] is True
    assert data["has_elevenlabs_key"] is True


def test_update_api_keys_empty_string_clears(client, auth_headers):
    # Set key first
    client.put("/api/auth/api-keys", json={
        "openai_api_key": "sk-test123",
    }, headers=auth_headers)

    # Clear with empty string
    resp = client.put("/api/auth/api-keys", json={
        "openai_api_key": "",
    }, headers=auth_headers)
    data = resp.json()
    assert data["has_openai_key"] is False


def test_get_api_keys_status(client, auth_headers):
    resp = client.get("/api/auth/api-keys", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "has_openai_key" in data
    assert "has_elevenlabs_key" in data
    assert "free_stories_used" in data
    assert "free_stories_limit" in data
    # Keys should never be returned
    assert "openai_api_key" not in data
    assert "elevenlabs_api_key" not in data
