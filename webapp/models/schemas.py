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
    config_override: Optional[dict] = None  # Override default config


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


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
    status: str
    created_at: datetime
    updated_at: datetime
    chapters: List[ChapterResponse] = []

    class Config:
        from_attributes = True


class StoryListResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    chapter_count: int
    created_at: datetime

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


# Usage schemas
class UsageStatsResponse(BaseModel):
    total_stories: int
    total_chapters: int
    total_audio_minutes: float
    openai_tokens_used: int
    elevenlabs_characters_used: int
    period_start: datetime
    period_end: datetime
