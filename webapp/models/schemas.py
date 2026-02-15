"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# Story schemas
class StoryCreate(BaseModel):
    title: str
    description: Optional[str] = None
    prompt: Optional[str] = None
    num_chapters: int = 3
    language: Optional[str] = None
    config_override: Optional[dict] = None  # Override default config


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None


class ChapterResponse(BaseModel):
    id: int
    chapter_number: int
    title: Optional[str]
    status: str
    audio_path: Optional[str]
    audio_duration: Optional[float]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StoryResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    prompt: Optional[str] = None
    language: Optional[str] = None
    status: str
    visibility: str = "private"
    share_code: Optional[str] = None
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    updated_at: datetime
    chapters: List[ChapterResponse] = []
    active_task: Optional["TaskStatusResponse"] = None

    class Config:
        from_attributes = True


class StoryListResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    language: Optional[str] = None
    status: str
    visibility: str = "private"
    chapter_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class PublicStoryListItem(BaseModel):
    id: int
    title: str
    description: Optional[str]
    language: Optional[str] = None
    status: str
    chapter_count: int
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    owner_name: str

    class Config:
        from_attributes = True


class PublicStoryResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    language: Optional[str] = None
    status: str
    visibility: str
    share_code: Optional[str] = None
    upvotes: int = 0
    downvotes: int = 0
    user_vote: Optional[str] = None
    created_at: datetime
    chapters: List[ChapterResponse] = []
    owner_name: str

    class Config:
        from_attributes = True


# Generation schemas
class GenerateStoryRequest(BaseModel):
    title: str
    prompt: Optional[str] = None
    num_chapters: int = 3
    enhance: bool = True


class GenerateAudioRequest(BaseModel):
    story_id: int
    chapter_numbers: Optional[List[int]] = None  # None = all chapters


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    progress: Optional[float] = None  # 0-100
    message: Optional[str] = None
    result: Optional[dict] = None
    words_generated: Optional[int] = None
    estimated_total_words: Optional[int] = None


# Resolve forward reference for StoryResponse -> TaskStatusResponse
StoryResponse.model_rebuild()


# Vote / Report / Share schemas
class VoteRequest(BaseModel):
    vote_type: Optional[str] = None  # "up", "down", or None to remove


class ReportRequest(BaseModel):
    reason: str


class ShareLinkResponse(BaseModel):
    share_code: str
    share_url: str


# API key schemas
class ApiKeysUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None


class ApiKeysStatus(BaseModel):
    has_openai_key: bool
    has_elevenlabs_key: bool
    free_stories_used: int
    free_stories_limit: int


class BudgetStatus(BaseModel):
    total_budget: float
    total_spent: float
    free_stories_generated: int
    free_stories_per_user: int
