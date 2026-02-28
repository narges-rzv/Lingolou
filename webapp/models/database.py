"""
Database models and setup for Lingolou webapp.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lingolou.db")

_engine_kwargs: dict[str, object] = {}

if DATABASE_URL.startswith("sqlite"):
    # Extract the file path from the SQLAlchemy URL
    _db_path = DATABASE_URL.replace("sqlite:///", "", 1)

    def _sqlite_creator() -> sqlite3.Connection:
        """Create a SQLite connection with unix-none VFS (no file locking).

        Safe because we run a single replica (maxReplicas=1). Avoids POSIX
        locking which fails on network filesystems like Azure Files (SMB).
        """
        return sqlite3.connect(
            f"file:{_db_path}?vfs=unix-none",
            uri=True,
            check_same_thread=False,
        )

    _engine_kwargs["creator"] = _sqlite_creator
    _engine_kwargs["poolclass"] = StaticPool
    engine = create_engine("sqlite://", **_engine_kwargs)
else:
    engine = create_engine(DATABASE_URL)

if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):  # noqa: ANN001, ANN202
        """Configure SQLite for network filesystem compatibility."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=DELETE")  # WAL not supported on SMB
        cursor.close()


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
    free_audio_used = Column(Integer, default=0)

    # New-followers awareness
    last_followers_seen_at = Column(DateTime, nullable=True)

    # Relationships
    stories = relationship("Story", back_populates="owner")
    worlds = relationship("World", back_populates="owner")
    usage_logs = relationship("UsageLog", back_populates="user")
    votes = relationship("Vote", back_populates="user")
    reports = relationship("Report", back_populates="user")
    bookmarks = relationship("Bookmark", back_populates="user")
    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        backref="follower",
        cascade="all, delete-orphan",
    )
    followers = relationship(
        "Follow",
        foreign_keys="Follow.following_id",
        backref="followed_user",
        cascade="all, delete-orphan",
    )
    blocks_given = relationship(
        "Block",
        foreign_keys="Block.blocker_id",
        backref="blocker",
        cascade="all, delete-orphan",
    )
    blocks_received = relationship(
        "Block",
        foreign_keys="Block.blocked_id",
        backref="blocked_user",
        cascade="all, delete-orphan",
    )


class World(Base):
    """Story world / universe model."""

    __tablename__ = "worlds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL for built-in
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_builtin = Column(Boolean, default=False)
    prompt_template = Column(Text, nullable=True)
    characters_json = Column(Text, nullable=True)  # JSON: {"RYDER": "The human leader", ...}
    valid_speakers_json = Column(Text, nullable=True)  # JSON: ["NARRATOR", "RYDER", ...]
    voice_config_json = Column(Text, nullable=True)  # JSON: {"NARRATOR": {"voice_id": "abc", ...}, ...}
    visibility = Column(String(20), default="private")  # private, link_only, public
    share_code = Column(String(36), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="worlds")
    stories = relationship("Story", back_populates="world")


class Story(Base):
    """Story project model."""

    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    world_id = Column(Integer, ForeignKey("worlds.id"), nullable=True, index=True)
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
    world = relationship("World", back_populates="stories")
    chapters = relationship("Chapter", back_populates="story", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="story", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="story", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="story", cascade="all, delete-orphan")


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


class Bookmark(Base):
    """User bookmark on a story."""

    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "story_id", name="uq_user_story_bookmark"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookmarks")
    story = relationship("Story", back_populates="bookmarks")


class Follow(Base):
    """Follow relationship between users."""

    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "following_id", name="uq_follower_following"),)

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    following_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Block(Base):
    """Block relationship between users."""

    __tablename__ = "blocks"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_blocker_blocked"),)

    id = Column(Integer, primary_key=True, index=True)
    blocker_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    blocked_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


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


FREE_STORIES_PER_USER = 20
FREE_AUDIO_PER_USER = 5
COST_PER_STORY = 0.05


def _seed_paw_patrol_world(db: Session) -> None:
    """Seed the built-in PAW Patrol world."""
    import json

    if db.query(World).filter(World.is_builtin.is_(True), World.name == "PAW Patrol").first():
        return

    characters = {
        "NARRATOR": "Tells the story",
        "RYDER": "The human leader of the PAW Patrol",
        "CHASE": "Police pup, brave and loyal",
        "MARSHALL": "Fire pup, clumsy but enthusiastic",
        "SKYE": "Aviation pup, cheerful and confident",
        "ROCKY": "Recycling pup, clever and resourceful",
        "RUBBLE": "Construction pup, strong and friendly",
        "ZUMA": "Water rescue pup, laid-back and cool",
        "EVEREST": "Snow rescue pup, adventurous",
    }
    valid_speakers = [
        "NARRATOR",
        "RYDER",
        "CHASE",
        "MARSHALL",
        "SKYE",
        "ROCKY",
        "RUBBLE",
        "ZUMA",
        "EVEREST",
    ]
    prompt_template = (
        "Write a story aimed for 4-8 year old kids, which involves the PAW Patrol "
        "in a new adventure. They meet a new pup, who speaks a different language "
        "({language} here), and the PAW Patrol learn a bit of basic {language} by "
        "communicating with the new pup, and repeating. Include short repetition of "
        "the language lessons. The current theme is {theme} and a few basic nouns, "
        "sentence structures, and pronouns. The plot is around {plot}. Keep the story "
        "in {num_chapters} chapters. Each chapter should be around 1000 words."
    )

    world = World(
        user_id=None,
        name="PAW Patrol",
        description="The classic PAW Patrol language learning world with Ryder and all the pups.",
        is_builtin=True,
        prompt_template=prompt_template,
        characters_json=json.dumps(characters),
        valid_speakers_json=json.dumps(valid_speakers),
        voice_config_json=None,
        visibility="public",
    )
    db.add(world)
    db.commit()


def _seed_winnie_the_pooh_world(db: Session) -> None:
    """Seed the built-in Winnie the Pooh world."""
    import json

    if db.query(World).filter(World.is_builtin.is_(True), World.name == "Winnie the Pooh").first():
        return

    characters = {
        "NARRATOR": "Tells the story in a warm, storybook tone",
        "WINNIE": "Winnie the Pooh, a lovable bear of very little brain who adores honey",
        "PIGLET": "Pooh's best friend, small and timid but brave when it counts",
        "TIGGER": "Bouncy, energetic tiger who loves to bounce and have fun",
        "EEYORE": "A gloomy but endearing donkey, often losing his tail",
        "RABBIT": "Organized and bossy, loves his garden",
        "OWL": "Thinks he is very wise, uses big words (sometimes incorrectly)",
        "KANGA": "A kind, motherly kangaroo",
        "ROO": "Kanga's adventurous little joey",
        "CHRISTOPHER_ROBIN": "The human child who is friends with everyone in the Hundred Acre Wood",
    }
    valid_speakers = [
        "NARRATOR",
        "WINNIE",
        "PIGLET",
        "TIGGER",
        "EEYORE",
        "RABBIT",
        "OWL",
        "KANGA",
        "ROO",
        "CHRISTOPHER_ROBIN",
    ]
    prompt_template = (
        "Write a gentle, whimsical children's story set in the Hundred Acre Wood "
        "with Winnie the Pooh and friends. The characters meet a new visitor who "
        "speaks {language}, and through friendship and curiosity they learn basic "
        "{language} words and phrases together. Include short, playful repetition "
        "of new words by different characters to reinforce learning. Pooh might "
        "mix things up in a funny way, Owl might try to sound clever, and Tigger "
        "might bounce while repeating. The learning theme is {theme}. "
        "The plot is: {plot}. Keep the story in {num_chapters} chapters, each "
        "around 1000 words. The tone should be cozy, humorous, and age-appropriate "
        "for 4-8 year olds."
    )

    world = World(
        user_id=None,
        name="Winnie the Pooh",
        description=(
            "The Hundred Acre Wood — a cozy world with Pooh, Piglet, Tigger, Eeyore, "
            "and friends learning new languages through gentle adventures."
        ),
        is_builtin=True,
        prompt_template=prompt_template,
        characters_json=json.dumps(characters),
        valid_speakers_json=json.dumps(valid_speakers),
        voice_config_json=None,  # No default voice assignments yet
        visibility="public",
    )
    db.add(world)
    db.commit()


def _seed_bluey_world(db: Session) -> None:
    """Seed the built-in Bluey world."""
    import json

    if db.query(World).filter(World.is_builtin.is_(True), World.name == "Bluey").first():
        return

    characters = {
        "NARRATOR": "Tells the story in a bright, Australian-flavoured tone",
        "BLUEY": "A six-year-old Blue Heeler puppy, imaginative and full of energy",
        "BINGO": "Bluey's younger sister, sweet, creative, and a little more sensitive",
        "BANDIT": "Bluey and Bingo's dad, playful and always up for a game",
        "CHILLI": "Bluey and Bingo's mum, warm and clever with a dry sense of humour",
        "MUFFIN": "Bluey's younger cousin, chaotic and hilarious",
        "STRIPE": "Muffin's dad and Bandit's brother",
        "TRIXIE": "Muffin's mum, patient and kind",
        "LUCKY": "Bluey's next-door neighbour and friend",
        "MACKENZIE": "Bluey's school friend, a Greyhound with a New Zealand accent",
        "CALYPSO": "Bluey's wise and calm school teacher",
    }
    valid_speakers = [
        "NARRATOR",
        "BLUEY",
        "BINGO",
        "BANDIT",
        "CHILLI",
        "MUFFIN",
        "STRIPE",
        "TRIXIE",
        "LUCKY",
        "MACKENZIE",
        "CALYPSO",
    ]
    prompt_template = (
        "Write a fun, heartfelt children's story featuring Bluey and her family "
        "and friends. In this adventure the Heeler family meets someone who speaks "
        "{language}, and through imaginative play and everyday family moments they "
        "pick up basic {language} words and phrases. Include playful repetition — "
        "Bluey might turn the new words into a game, Bingo might repeat them in a "
        "sing-song voice, and Bandit might comically mispronounce things before "
        "getting them right. The learning theme is {theme}. The plot is: {plot}. "
        "Keep the story in {num_chapters} chapters, each around 1000 words. "
        "The tone should be warm, funny, and true to Bluey's spirit — celebrating "
        "play, family, and the little moments that matter, for ages 4-8."
    )

    world = World(
        user_id=None,
        name="Bluey",
        description=(
            "The Heeler family home and beyond — Bluey, Bingo, Bandit, and Chilli "
            "learn new languages through imaginative play and everyday adventures."
        ),
        is_builtin=True,
        prompt_template=prompt_template,
        characters_json=json.dumps(characters),
        valid_speakers_json=json.dumps(valid_speakers),
        voice_config_json=None,
        visibility="public",
    )
    db.add(world)
    db.commit()


def _seed_peppa_pig_world(db: Session) -> None:
    """Seed the built-in Peppa Pig world."""
    import json

    if db.query(World).filter(World.is_builtin.is_(True), World.name == "Peppa Pig").first():
        return

    characters = {
        "NARRATOR": "Tells the story in a cheerful, simple narrator voice",
        "PEPPA": "Peppa Pig, a cheeky little pig who loves jumping in muddy puddles",
        "GEORGE": "Peppa's little brother, loves his dinosaur and says 'Dine-saw!' a lot",
        "MUMMY_PIG": "Peppa and George's mum, kind and often works on her computer",
        "DADDY_PIG": "Peppa and George's dad, jolly and a bit clumsy, proud of his big tummy",
        "SUZY_SHEEP": "Peppa's best friend, a sheep who loves dressing up",
        "REBECCA_RABBIT": "Peppa's friend, a rabbit with lots of brothers and sisters",
        "DANNY_DOG": "Peppa's friend, loves pirates and playing outside",
        "PEDRO_PONY": "Peppa's friend, a pony who often gets confused but is very sweet",
        "EMILY_ELEPHANT": "Peppa's friend, a quiet and clever elephant",
        "MADAME_GAZELLE": "Peppa's school teacher, originally from another country, loves music",
        "GRANDPA_PIG": "Peppa's grandpa, loves his garden, his boat, and telling stories",
        "GRANNY_PIG": "Peppa's granny, loves her chickens and baking",
    }
    valid_speakers = [
        "NARRATOR",
        "PEPPA",
        "GEORGE",
        "MUMMY_PIG",
        "DADDY_PIG",
        "SUZY_SHEEP",
        "REBECCA_RABBIT",
        "DANNY_DOG",
        "PEDRO_PONY",
        "EMILY_ELEPHANT",
        "MADAME_GAZELLE",
        "GRANDPA_PIG",
        "GRANNY_PIG",
    ]
    prompt_template = (
        "Write a simple, cheerful children's story featuring Peppa Pig and her "
        "family and friends. In this adventure, Peppa meets someone who speaks "
        "{language}, and through everyday activities — like playgroup, trips to "
        "the shops, or playing outside — the characters learn basic {language} "
        "words and phrases. Include gentle repetition: Peppa might say a new word "
        "proudly, George might try to copy it in his own funny way, and Daddy Pig "
        "might get it hilariously wrong before Mummy Pig helps. Madame Gazelle "
        "could help explain the new words at school. The learning theme is {theme}. "
        "The plot is: {plot}. Keep the story in {num_chapters} chapters, each "
        "around 1000 words. The tone should be light, funny, and very simple — "
        "short sentences, lots of laughter, and suitable for ages 3-7."
    )

    world = World(
        user_id=None,
        name="Peppa Pig",
        description=(
            "Peppa's world — playgroup, muddy puddles, and family fun. "
            "Peppa, George, and friends learn new languages through simple everyday adventures."
        ),
        is_builtin=True,
        prompt_template=prompt_template,
        characters_json=json.dumps(characters),
        valid_speakers_json=json.dumps(valid_speakers),
        voice_config_json=None,
        visibility="public",
    )
    db.add(world)
    db.commit()


def _seed_elara_and_arion_world(db: Session) -> None:
    """Seed the built-in Elara and Arion world."""
    import json

    if db.query(World).filter(World.is_builtin.is_(True), World.name == "Elara and Arion").first():
        return

    characters = {
        "NARRATOR": "Tells the story",
        "ELARA": "Elara, an energetic 4-year-old girl who is smart, kind, and very creative",
        "ARION": "Arion, a fun and energetic almost 2-year-old boy who loves cars, animals, and running around",
    }
    valid_speakers = ["NARRATOR", "ELARA", "ARION"]
    prompt_template = (
        "Write a story aimed for 4-8 year old kids. It is built around the world of "
        "Elara and Arion. Elara and Arion are siblings. Elara is an energetic 4yo girl. "
        "She is smart and kind and very creative. Arion is a fun and energetic almost "
        "2 year old boy. He loves cars and anything that moves, animals and running "
        "around. Elara and Arion play a lot of games and go to playground, daycare/school, "
        "swimming class, and they love each other and their mommy and daddies. Their mom "
        "and dads also love them, and they have the most cozy, magical and amazing days "
        "and nights.\n\nElara and Arion have lots of friends, and they play with them "
        "all the time.\n\nThis story is about {theme}. The characters learn basic "
        "{language} words and phrases. The plot is: {plot}. Keep the story in "
        "{num_chapters} chapters."
    )

    voice_config = {
        "NARRATOR": {
            "voice_id": "8Es4wFxsDlHBmFWAOWRS",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        },
        "ELARA": {
            "voice_id": "BrSJSyxXUlQmFzftrXCz",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        },
        "ARION": {
            "voice_id": "mHX7OoPk2G45VMAuinIt",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        },
    }

    world = World(
        user_id=None,
        name="Elara and Arion",
        description=(
            "Elara and Arion are siblings. Elara is an energetic 4yo girl who is smart, "
            "kind, and very creative. Arion is a fun and energetic almost 2-year-old boy "
            "who loves cars, animals, and running around. They have the most cozy, magical "
            "and amazing days and nights with their family and friends."
        ),
        is_builtin=True,
        prompt_template=prompt_template,
        characters_json=json.dumps(characters),
        valid_speakers_json=json.dumps(valid_speakers),
        voice_config_json=json.dumps(voice_config),
        visibility="public",
    )
    db.add(world)
    db.commit()


def init_db() -> None:
    """Initialize the database tables via Alembic and seed data."""
    import logging
    from pathlib import Path

    import sqlalchemy
    from alembic import command
    from alembic.config import Config

    logger = logging.getLogger(__name__)

    alembic_cfg = Config(str(Path(__file__).resolve().parent.parent.parent / "alembic.ini"))

    inspector = sqlalchemy.inspect(engine)
    existing_tables = inspector.get_table_names()
    has_app_tables = "users" in existing_tables

    # Check if Alembic is tracking this DB (has a stamped revision)
    has_alembic_stamp = False
    if "alembic_version" in existing_tables:
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT version_num FROM alembic_version"))
            has_alembic_stamp = result.first() is not None

    if has_app_tables and not has_alembic_stamp:
        # Existing DB without Alembic tracking — stamp as current
        logger.info("Existing database detected without alembic tracking — stamping head")
        command.stamp(alembic_cfg, "head")
    else:
        # Fresh DB or already tracked — run migrations
        command.upgrade(alembic_cfg, "head")
    db = SessionLocal()
    try:
        if not db.query(PlatformBudget).first():
            db.add(PlatformBudget(id=1, total_budget=50.0, total_spent=0.0, free_stories_generated=0))
            db.commit()
        _seed_paw_patrol_world(db)
        _seed_winnie_the_pooh_world(db)
        _seed_bluey_world(db)
        _seed_peppa_pig_world(db)
        _seed_elara_and_arion_world(db)
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
