"""Tests for webapp/services/auth.py"""

from datetime import timedelta

from webapp.models.database import User
from webapp.services.auth import (
    UserCreate,
    authenticate_user,
    create_access_token,
    create_user,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_hash_and_verify_correct_password():
    hashed = get_password_hash("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_hash_and_verify_wrong_password():
    hashed = get_password_hash("mypassword")
    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token_and_decode():
    token = create_access_token(data={"sub": "42"})
    token_data = decode_token(token)
    assert token_data is not None
    assert token_data.user_id == 42


def test_decode_expired_token():
    token = create_access_token(data={"sub": "1"}, expires_delta=timedelta(seconds=-1))
    assert decode_token(token) is None


def test_decode_missing_sub():
    token = create_access_token(data={"foo": "bar"})
    assert decode_token(token) is None


def test_decode_garbage_token():
    assert decode_token("not.a.real.token") is None


def test_create_user(db):
    user_in = UserCreate(email="new@test.com", username="newuser", password="pass123")
    user = create_user(db, user_in)
    assert user.id is not None
    assert user.email == "new@test.com"
    assert user.hashed_password != "pass123"


def test_authenticate_user_by_email(db, test_user):
    result = authenticate_user(db, "test@example.com", "testpass123")
    assert result is not None
    assert result.id == test_user.id


def test_authenticate_user_by_username(db, test_user):
    result = authenticate_user(db, "testuser", "testpass123")
    assert result is not None
    assert result.id == test_user.id


def test_authenticate_user_wrong_password(db, test_user):
    assert authenticate_user(db, "test@example.com", "wrong") is None


def test_authenticate_user_nonexistent(db):
    assert authenticate_user(db, "nobody@test.com", "pass") is None


def test_authenticate_oauth_user_no_password(db):
    oauth_user = User(
        email="oauth@test.com",
        username="oauthuser",
        hashed_password=None,
        oauth_provider="google",
        oauth_id="123",
    )
    db.add(oauth_user)
    db.commit()
    assert authenticate_user(db, "oauth@test.com", "anypass") is None


def test_get_current_user_valid(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_get_current_user_invalid_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer badtoken"})
    assert resp.status_code == 401


def test_get_current_user_no_header(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
