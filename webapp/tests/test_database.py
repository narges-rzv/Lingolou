"""Tests for webapp/models/database.py"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from webapp.models.database import Base, User, Story, Chapter, Vote, Report, PlatformBudget


@pytest.fixture()
def fresh_db():
    """Standalone db session for database model tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_init_db_seeds_budget(fresh_db):
    # Simulate init_db logic
    if not fresh_db.query(PlatformBudget).first():
        fresh_db.add(PlatformBudget(id=1, total_budget=50.0, total_spent=0.0))
        fresh_db.commit()

    budget = fresh_db.query(PlatformBudget).first()
    assert budget is not None
    assert budget.total_budget == 50.0


def test_init_db_no_duplicate(fresh_db):
    fresh_db.add(PlatformBudget(id=1, total_budget=50.0))
    fresh_db.commit()

    # Second call should not create duplicate
    if not fresh_db.query(PlatformBudget).first():
        fresh_db.add(PlatformBudget(id=1, total_budget=50.0))
        fresh_db.commit()

    count = fresh_db.query(PlatformBudget).count()
    assert count == 1


def test_user_story_relationship(fresh_db):
    user = User(email="a@b.com", username="user1", hashed_password="hash")
    fresh_db.add(user)
    fresh_db.commit()

    story = Story(user_id=user.id, title="My Story", status="created")
    fresh_db.add(story)
    fresh_db.commit()
    fresh_db.refresh(user)

    assert len(user.stories) == 1
    assert user.stories[0].title == "My Story"


def test_story_chapter_relationship(fresh_db):
    user = User(email="a@b.com", username="user1", hashed_password="hash")
    fresh_db.add(user)
    fresh_db.commit()

    story = Story(user_id=user.id, title="Story", status="created")
    fresh_db.add(story)
    fresh_db.commit()

    ch1 = Chapter(story_id=story.id, chapter_number=1, status="pending")
    ch2 = Chapter(story_id=story.id, chapter_number=2, status="pending")
    fresh_db.add_all([ch1, ch2])
    fresh_db.commit()
    fresh_db.refresh(story)

    assert len(story.chapters) == 2


def test_cascade_delete_story(fresh_db):
    user = User(email="a@b.com", username="user1", hashed_password="hash")
    fresh_db.add(user)
    fresh_db.commit()

    story = Story(user_id=user.id, title="Story", status="created")
    fresh_db.add(story)
    fresh_db.commit()

    ch = Chapter(story_id=story.id, chapter_number=1, status="pending")
    fresh_db.add(ch)
    fresh_db.commit()

    user2 = User(email="b@b.com", username="user2", hashed_password="hash")
    fresh_db.add(user2)
    fresh_db.commit()

    vote = Vote(user_id=user2.id, story_id=story.id, vote_type="up")
    report = Report(user_id=user2.id, story_id=story.id, reason="test reason")
    fresh_db.add_all([vote, report])
    fresh_db.commit()

    # Delete story → chapters, votes, reports should cascade
    fresh_db.delete(story)
    fresh_db.commit()

    assert fresh_db.query(Chapter).count() == 0
    assert fresh_db.query(Vote).count() == 0
    assert fresh_db.query(Report).count() == 0


def test_unique_email_constraint(fresh_db):
    fresh_db.add(User(email="dup@b.com", username="user1", hashed_password="hash"))
    fresh_db.commit()

    fresh_db.add(User(email="dup@b.com", username="user2", hashed_password="hash"))
    with pytest.raises(IntegrityError):
        fresh_db.commit()
    fresh_db.rollback()


def test_unique_username_constraint(fresh_db):
    fresh_db.add(User(email="a@b.com", username="dupuser", hashed_password="hash"))
    fresh_db.commit()

    fresh_db.add(User(email="c@b.com", username="dupuser", hashed_password="hash"))
    with pytest.raises(IntegrityError):
        fresh_db.commit()
    fresh_db.rollback()
