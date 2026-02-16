"""
Pydantic schemas for API request/response models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# Story schemas
class StoryCreate(BaseModel):
    """Request schema for creating a new story."""

    title: str
    description: str | None = None
    prompt: str | None = None
    num_chapters: int = 3
    language: str | None = None
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

    class Config:
        from_attributes = True


class StoryResponse(BaseModel):
    """Response schema for a story with chapters."""

    id: int
    title: str
    description: str | None
    prompt: str | None = None
    language: str | None = None
    status: str
    visibility: str = "private"
    share_code: str | None = None
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    updated_at: datetime
    chapters: list[ChapterResponse] = []
    active_task: TaskStatusResponse | None = None

    class Config:
        from_attributes = True


class StoryListResponse(BaseModel):
    """Response schema for story list items."""

    id: int
    title: str
    description: str | None
    language: str | None = None
    status: str
    visibility: str = "private"
    chapter_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class PublicStoryListItem(BaseModel):
    """Response schema for public story list items."""

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

    class Config:
        from_attributes = True


class PublicStoryResponse(BaseModel):
    """Response schema for a public story with chapters."""

    id: int
    title: str
    description: str | None
    language: str | None = None
    status: str
    visibility: str
    share_code: str | None = None
    upvotes: int = 0
    downvotes: int = 0
    user_vote: str | None = None
    created_at: datetime
    chapters: list[ChapterResponse] = []
    owner_name: str

    class Config:
        from_attributes = True


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


class BudgetStatus(BaseModel):
    """Response schema for platform budget status."""

    total_budget: float
    total_spent: float
    free_stories_generated: int
    free_stories_per_user: int
