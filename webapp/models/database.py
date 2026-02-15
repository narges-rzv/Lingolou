"""
Database models and setup for Lingolou webapp.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///./lingolou.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(255), nullable=True)

    # BYOK: encrypted API keys
    openai_api_key = Column(Text, nullable=True)
    elevenlabs_api_key = Column(Text, nullable=True)
    free_stories_used = Column(Integer, default=0)

    # Relationships
    stories = relationship("Story", back_populates="owner")
    usage_logs = relationship("UsageLog", back_populates="user")
    votes = relationship("Vote", back_populates="user")
    reports = relationship("Report", back_populates="user")


class Story(Base):
    """Story project model."""
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    prompt = Column(Text, nullable=True)
    config_json = Column(Text, nullable=True)  # Store the config used
    language = Column(String(100), nullable=True)  # Target language name (e.g. "Persian (Farsi)")
    status = Column(String(50), default="created")  # created, generating, completed, failed
    visibility = Column(String(20), default="private")  # private, link_only, public
    share_code = Column(String(36), unique=True, nullable=True, index=True)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="stories")
    chapters = relationship("Chapter", back_populates="story", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="story", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="story", cascade="all, delete-orphan")


class Chapter(Base):
    """Chapter model for a story."""
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    script_json = Column(Text, nullable=True)  # Base script
    enhanced_json = Column(Text, nullable=True)  # With emotion tags
    audio_path = Column(String(500), nullable=True)
    audio_duration = Column(Float, nullable=True)  # Duration in seconds
    status = Column(String(50), default="pending")  # pending, generating_script, generating_audio, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    story = relationship("Story", back_populates="chapters")


class Vote(Base):
    """User vote on a story."""
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("user_id", "story_id", name="uq_user_story_vote"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False, index=True)
    vote_type = Column(String(10), nullable=False)  # "up" or "down"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="votes")
    story = relationship("Story", back_populates="votes")


class Report(Base):
    """User report on a story."""
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("user_id", "story_id", name="uq_user_story_report"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reports")
    story = relationship("Story", back_populates="reports")


class UsageLog(Base):
    """Track API usage for billing/limits."""
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)  # story_generation, audio_generation, etc.
    details = Column(Text, nullable=True)  # JSON with details
    tokens_used = Column(Integer, nullable=True)  # OpenAI tokens
    characters_used = Column(Integer, nullable=True)  # ElevenLabs characters
    cost_estimate = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="usage_logs")


class PlatformBudget(Base):
    """Single-row table tracking the free-tier budget pool."""
    __tablename__ = "platform_budget"

    id = Column(Integer, primary_key=True)
    total_budget = Column(Float, default=50.0)
    total_spent = Column(Float, default=0.0)
    free_stories_generated = Column(Integer, default=0)


FREE_STORIES_PER_USER = 3
COST_PER_STORY = 0.05


def init_db():
    """Initialize the database tables and seed platform budget."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(PlatformBudget).first():
            db.add(PlatformBudget(id=1, total_budget=50.0, total_spent=0.0, free_stories_generated=0))
            db.commit()
    finally:
        db.close()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
