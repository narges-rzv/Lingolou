"""
Pydantic schemas for API request/response models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Story schemas
class StoryCreate(BaseModel):
    """Request schema for creating a new story."""

    title: str
    description: str | None = None
    prompt: str | None = None
    num_chapters: int = 3
    language: str | None = None
    world_id: int | None = None
    config_override: dict | None = None  # Override default config


class StoryUpdate(BaseModel):
    """Request schema for updating story metadata."""

    title: str | None = None
    description: str | None = None
    visibility: str | None = None


class ChapterResponse(BaseModel):
    """Response schema for a chapter."""

    id: int
    chapter_number: int
    title: str | None
    status: str
    audio_path: str | None
    audio_duration: float | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoryResponse(BaseModel):
    """Response schema for a story with chapters."""

    id: int
    title: str
    description: str | None
    prompt: str | None = None
    language: str | None = None
    world_id: int | None = None
    world_name: str | None = None
    status: str
    visibility: str = "private"
    share_code: str | None = None
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    updated_at: datetime
    chapters: list[ChapterResponse] = []
    active_task: TaskStatusResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class StoryListResponse(BaseModel):
    """Response schema for story list items."""

    id: int
    title: str
    description: str | None
    language: str | None = None
    world_id: int | None = None
    world_name: str | None = None
    status: str
    visibility: str = "private"
    chapter_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicStoryListItem(BaseModel):
    """Response schema for public story list items."""

    id: int
    title: str
    description: str | None
    language: str | None = None
    world_id: int | None = None
    world_name: str | None = None
    status: str
    chapter_count: int
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    owner_name: str
    owner_id: int = 0

    model_config = ConfigDict(from_attributes=True)


class PublicStoryResponse(BaseModel):
    """Response schema for a public story with chapters."""

    id: int
    title: str
    description: str | None
    prompt: str | None = None
    language: str | None = None
    status: str
    visibility: str
    share_code: str | None = None
    upvotes: int = 0
    downvotes: int = 0
    user_vote: str | None = None
    is_bookmarked: bool = False
    created_at: datetime
    chapters: list[ChapterResponse] = []
    owner_name: str
    owner_id: int = 0

    model_config = ConfigDict(from_attributes=True)


# Follow / Timeline / Profile schemas
class FollowResponse(BaseModel):
    """Response schema for follow toggle."""

    following: bool


class FollowUserItem(BaseModel):
    """Response schema for a user in a follow list."""

    id: int
    username: str
    story_count: int = 0
    is_following: bool = False


class TimelineStoryItem(BaseModel):
    """Response schema for a story in the timeline feed."""

    id: int
    title: str
    description: str | None = None
    language: str | None = None
    world_id: int | None = None
    world_name: str | None = None
    status: str
    chapter_count: int = 0
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    owner_name: str
    owner_id: int


class TimelineWorldItem(BaseModel):
    """Response schema for a world in the timeline feed."""

    id: int
    name: str
    description: str | None = None
    visibility: str
    story_count: int = 0
    owner_name: str
    owner_id: int
    created_at: datetime


class UserProfileResponse(BaseModel):
    """Response schema for a user profile."""

    id: int
    username: str
    story_count: int = 0
    world_count: int = 0
    follower_count: int = 0
    following_count: int = 0
    is_following: bool = False
    is_blocked: bool = False
    created_at: datetime


class BlockResponse(BaseModel):
    """Response schema for block toggle."""

    blocked: bool


class BlockedUserItem(BaseModel):
    """Response schema for a user in the blocked list."""

    id: int
    username: str
    blocked_at: datetime


class NewFollowersResponse(BaseModel):
    """Response schema for new followers since last seen."""

    count: int
    followers: list[FollowUserItem]


# Generation schemas
class GenerateStoryRequest(BaseModel):
    """Request schema for story generation."""

    title: str
    prompt: str | None = None
    num_chapters: int = 3
    enhance: bool = True


class GenerateAudioRequest(BaseModel):
    """Request schema for audio generation."""

    story_id: int
    chapter_numbers: list[int] | None = None  # None = all chapters
    voice_override: dict[str, dict] | None = None  # speaker -> voice settings override


class TaskStatusResponse(BaseModel):
    """Response schema for background task status."""

    task_id: str
    status: str  # pending, running, completed, failed
    progress: float | None = None  # 0-100
    message: str | None = None
    result: dict | None = None
    words_generated: int | None = None
    estimated_total_words: int | None = None


# Resolve forward reference for StoryResponse -> TaskStatusResponse
StoryResponse.model_rebuild()


# Bookmark schemas
class BookmarkResponse(BaseModel):
    """Response schema for bookmark toggle."""

    bookmarked: bool


class BookmarkedStoryListItem(BaseModel):
    """Response schema for a bookmarked story in the user's list."""

    id: int
    title: str
    description: str | None
    language: str | None = None
    status: str
    chapter_count: int
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    owner_name: str
    bookmarked_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Vote / Report / Share schemas
class VoteRequest(BaseModel):
    """Request schema for voting on a story."""

    vote_type: str | None = None  # "up", "down", or None to remove


class ReportRequest(BaseModel):
    """Request schema for reporting a story."""

    reason: str


class ShareLinkResponse(BaseModel):
    """Response schema for share link."""

    share_code: str
    share_url: str


# API key schemas
class ApiKeysUpdate(BaseModel):
    """Request schema for updating API keys."""

    openai_api_key: str | None = None
    elevenlabs_api_key: str | None = None


class ApiKeysStatus(BaseModel):
    """Response schema for API key status."""

    has_openai_key: bool
    has_elevenlabs_key: bool
    free_stories_used: int
    free_stories_limit: int
    free_audio_used: int
    free_audio_limit: int


class BudgetStatus(BaseModel):
    """Response schema for platform budget status."""

    total_budget: float
    total_spent: float
    free_stories_generated: int
    free_stories_per_user: int


# World schemas
class WorldCreate(BaseModel):
    """Request schema for creating a new world."""

    name: str
    description: str | None = None
    prompt_template: str | None = None
    characters: dict[str, str] | None = None
    valid_speakers: list[str] | None = None
    voice_config: dict[str, dict] | None = None
    visibility: str = "private"


class WorldUpdate(BaseModel):
    """Request schema for updating a world."""

    name: str | None = None
    description: str | None = None
    prompt_template: str | None = None
    characters: dict[str, str] | None = None
    valid_speakers: list[str] | None = None
    voice_config: dict[str, dict] | None = None
    visibility: str | None = None


class WorldResponse(BaseModel):
    """Response schema for a world with full data."""

    id: int
    name: str
    description: str | None
    is_builtin: bool
    prompt_template: str | None
    characters: dict[str, str] | None = None
    valid_speakers: list[str] | None = None
    voice_config: dict | None = None
    visibility: str
    share_code: str | None = None
    story_count: int = 0
    owner_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldListItem(BaseModel):
    """Response schema for world list items."""

    id: int
    name: str
    description: str | None
    is_builtin: bool
    visibility: str
    story_count: int = 0
    owner_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
