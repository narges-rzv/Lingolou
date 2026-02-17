"""
Shared test fixtures for Lingolou backend tests.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set env vars before importing app modules
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ELEVENLABS_API_KEY", None)

from webapp.main import app
from webapp.models.database import Base, PlatformBudget, User, World, get_db
from webapp.services.auth import create_access_token, get_password_hash


@pytest.fixture()
def db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSession()
    # Seed platform budget
    session.add(PlatformBudget(id=1, total_budget=50.0, total_spent=0.0, free_stories_generated=0))
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    """TestClient with database dependency override."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def test_user(db):
    """Create a test user with password 'testpass123'."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def auth_headers(test_user):
    """Return authorization headers for the test user."""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def other_user(db):
    """Create a second user for ownership tests."""
    user = User(
        email="other@example.com",
        username="otheruser",
        hashed_password=get_password_hash("otherpass123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def other_auth_headers(other_user):
    """Return authorization headers for the other user."""
    token = create_access_token(data={"sub": str(other_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def test_world(db, test_user):
    """Create a test world owned by test_user."""
    import json

    world = World(
        user_id=test_user.id,
        name="Test World",
        description="A test world for unit tests",
        prompt_template="Write a {language} story about {theme} with {plot} in {num_chapters} chapters.",
        characters_json=json.dumps({"NARRATOR": "Tells the story", "HERO": "The main character"}),
        valid_speakers_json=json.dumps(["NARRATOR", "HERO"]),
        voice_config_json=json.dumps({"NARRATOR": {"voice_id": "abc123", "stability": 0.6}}),
        visibility="private",
    )
    db.add(world)
    db.commit()
    db.refresh(world)
    return world


@pytest.fixture()
def builtin_world(db):
    """Create a built-in world (no owner)."""
    import json

    world = World(
        user_id=None,
        name="Built-in World",
        description="A built-in world",
        is_builtin=True,
        prompt_template="Default template for {language}.",
        characters_json=json.dumps({"NARRATOR": "Narrator"}),
        valid_speakers_json=json.dumps(["NARRATOR"]),
        visibility="public",
    )
    db.add(world)
    db.commit()
    db.refresh(world)
    return world
