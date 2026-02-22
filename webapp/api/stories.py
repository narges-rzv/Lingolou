"""
Stories API endpoints.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import requests as http_requests
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from webapp.models.database import (
    FREE_AUDIO_PER_USER,
    FREE_STORIES_PER_USER,
    Chapter,
    PlatformBudget,
    Story,
    User,
    World,
    get_db,
)
from webapp.models.schemas import (
    ChapterResponse,
    GenerateAudioRequest,
    GenerateStoryRequest,
    ShareLinkResponse,
    StoryCreate,
    StoryListResponse,
    StoryResponse,
    StoryUpdate,
    TaskStatusResponse,
)
from webapp.services.auth import get_current_active_user
from webapp.services.crypto import decrypt_key
from webapp.services.generation import generate_audio, generate_story
from webapp.services.storage import get_storage
from webapp.services.task_store import get_task_backend

router = APIRouter(prefix="/api/stories", tags=["Stories"])


@router.get("/defaults")
async def get_story_defaults(current_user: User = Depends(get_current_active_user)) -> dict:
    """Get default story generation config."""
    config_path = Path(__file__).parent.parent.parent / "story_config.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config file not found")
    with open(config_path) as f:
        config = json.load(f)
    return {
        "default_prompt": config.get("default_prompt", ""),
        "characters": config.get("characters", {}),
        "target_language": config.get("target_language", {}),
        "num_chapters": config.get("generation_settings", {}).get("default_chapters", 3),
    }


@router.get("/voices")
async def get_available_voices(current_user: User = Depends(get_current_active_user)) -> list[dict]:
    """Fetch available voices from ElevenLabs API."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

    resp = http_requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": api_key},
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch voices from ElevenLabs")

    voices = resp.json().get("voices", [])
    return [
        {
            "voice_id": v["voice_id"],
            "name": v["name"],
            "category": v.get("category", ""),
            "labels": v.get("labels", {}),
            "preview_url": v.get("preview_url", ""),
        }
        for v in voices
    ]


@router.get("/", response_model=list[StoryListResponse])
async def list_stories(
    skip: int = 0, limit: int = 20, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> list[StoryListResponse]:
    """List all stories for the current user."""
    stories = (
        db.query(Story)
        .filter(Story.user_id == current_user.id)
        .order_by(Story.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        StoryListResponse(
            id=s.id,
            title=s.title,
            description=s.description,
            language=s.language,
            world_id=s.world_id,
            world_name=s.world.name if s.world else None,
            status=s.status,
            visibility=s.visibility,
            chapter_count=len(s.chapters),
            created_at=s.created_at,
        )
        for s in stories
    ]


@router.post("/", response_model=StoryResponse)
async def create_story(
    story: StoryCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> StoryResponse:
    """Create a new story (without generating content yet)."""
    # Validate world_id if provided
    if story.world_id:
        world = db.query(World).filter(World.id == story.world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

    db_story = Story(
        user_id=current_user.id,
        world_id=story.world_id,
        title=story.title,
        description=story.description,
        prompt=story.prompt,
        language=story.language,
        config_json=json.dumps(story.config_override) if story.config_override else None,
        status="created",
    )
    db.add(db_story)
    db.commit()
    db.refresh(db_story)

    # Create empty chapters
    for i in range(1, story.num_chapters + 1):
        chapter = Chapter(story_id=db_story.id, chapter_number=i, status="pending")
        db.add(chapter)
    db.commit()
    db.refresh(db_story)

    response = StoryResponse.model_validate(db_story)
    response.world_name = db_story.world.name if db_story.world else None
    return response


# Task routes must be defined before /{story_id} to avoid route conflicts
@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_generation_status(
    task_id: str, current_user: User = Depends(get_current_active_user)
) -> TaskStatusResponse:
    """Get status of a generation task."""
    status_info = get_task_backend().get(task_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(**status_info)


@router.delete("/tasks/{task_id}")
async def cancel_generation_task(task_id: str, current_user: User = Depends(get_current_active_user)) -> dict[str, str]:
    """Cancel a running task."""
    was_running = get_task_backend().cancel(task_id)
    if was_running:
        return {"message": "Task cancelled", "task_id": task_id}

    status_info = get_task_backend().get(task_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": f"Task already {status_info['status']}", "task_id": task_id}


@router.get("/{story_id}/voice-config")
async def get_voice_config(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get effective voice config and speakers for a story."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Get voice config from world or disk fallback
    voice_config: dict = {}
    if story.world_id:
        world = db.query(World).filter(World.id == story.world_id).first()
        if world and world.voice_config_json:
            voice_config = json.loads(world.voice_config_json)

    if not voice_config:
        voices_path = Path(__file__).parent.parent.parent / "voices_config.json"
        if voices_path.exists():
            with open(voices_path) as f:
                raw = json.load(f)
            # voices_config.json has {"voices": {"SPEAKER": {...}}} or flat format
            voice_config = raw.get("voices", raw) if isinstance(raw, dict) else {}

    # Extract unique speakers from chapter scripts
    speakers: list[str] = []
    seen: set[str] = set()
    for chapter in sorted(story.chapters, key=lambda c: c.chapter_number):
        script_json = chapter.enhanced_json or chapter.script_json
        if not script_json:
            continue
        script = json.loads(script_json)
        for entry in script:
            speaker = entry.get("speaker")
            if speaker and speaker not in seen:
                speakers.append(speaker)
                seen.add(speaker)

    return {"speakers": speakers, "voice_config": voice_config}


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> StoryResponse:
    """Get a specific story with all chapters."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    response = StoryResponse.model_validate(story)
    response.world_name = story.world.name if story.world else None

    # If the story is generating, look for an active in-memory task
    if story.status == "generating":
        active = get_task_backend().find_active_for_story(story_id)
        if active:
            response.active_task = TaskStatusResponse(**active)
        else:
            # Task lost (e.g. server restart) — mark as failed so user can retry
            story.status = "failed"
            db.commit()
            response.status = "failed"

    return response


@router.patch("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: int,
    story_update: StoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Story:
    """Update story metadata."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story_update.title:
        story.title = story_update.title
    if story_update.description:
        story.description = story_update.description
    if story_update.visibility is not None:
        if story_update.visibility not in ("private", "link_only", "public", "followers"):
            raise HTTPException(status_code=400, detail="Invalid visibility value")
        story.visibility = story_update.visibility
        if story_update.visibility in ("link_only", "public") and not story.share_code:
            story.share_code = str(uuid.uuid4())

    db.commit()
    db.refresh(story)
    return story


@router.post("/{story_id}/generate-share-link", response_model=ShareLinkResponse)
async def generate_share_link(
    story_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ShareLinkResponse:
    """Generate or return a share link for a story."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if not story.share_code:
        story.share_code = str(uuid.uuid4())
        db.commit()
        db.refresh(story)

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    return ShareLinkResponse(share_code=story.share_code, share_url=f"{frontend_url}/share/{story.share_code}")


@router.delete("/{story_id}")
async def delete_story(
    story_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> dict[str, str]:
    """Delete a story and all its chapters."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Delete audio files from storage
    get_storage().delete_dir(str(story_id))

    db.delete(story)
    db.commit()
    return {"message": "Story deleted"}


@router.post("/{story_id}/generate", response_model=TaskStatusResponse)
async def generate_story_content(
    story_id: int,
    request: GenerateStoryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> TaskStatusResponse:
    """Start story script generation (async background task)."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status == "generating":
        raise HTTPException(status_code=400, detail="Story is already being generated")

    # Update story with request data
    story.prompt = request.prompt
    story.status = "generating"

    # Reset existing chapters for regeneration and adjust count
    existing_chapters = sorted(story.chapters, key=lambda c: c.chapter_number)

    for ch in existing_chapters:
        if ch.chapter_number <= request.num_chapters:
            ch.script_json = None
            ch.enhanced_json = None
            ch.audio_path = None
            ch.audio_duration = None
            ch.status = "pending"
        else:
            db.delete(ch)

    # Delete old audio files from storage
    get_storage().delete_dir(str(story_id))

    # Create any missing chapters if count was increased
    existing_nums = {ch.chapter_number for ch in existing_chapters}
    for i in range(1, request.num_chapters + 1):
        if i not in existing_nums:
            db.add(Chapter(story_id=story_id, chapter_number=i, status="pending"))

    db.commit()

    # Resolve OpenAI API key
    openai_api_key = None
    use_platform_key = False
    if current_user.openai_api_key:
        openai_api_key = decrypt_key(current_user.openai_api_key)
    else:
        # Free tier check
        used = current_user.free_stories_used or 0
        budget = db.query(PlatformBudget).first()
        if used >= FREE_STORIES_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Free tier limit reached ({used}/{FREE_STORIES_PER_USER} stories used). "
                    "Add your own OpenAI API key in Settings to continue."
                ),
            )
        if budget and budget.total_spent >= budget.total_budget:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=("Community free tier budget exhausted. Add your own OpenAI API key in Settings to continue."),
            )
        use_platform_key = True
        current_user.free_stories_used = used + 1
        db.commit()

    # Start background task
    task_id = f"story_{story_id}_{int(time.time())}"
    get_task_backend().update(task_id, "pending", 0, "Task queued, waiting to start...")
    background_tasks.add_task(
        generate_story,
        task_id=task_id,
        story_id=story_id,
        user_id=current_user.id,
        prompt=request.prompt,
        num_chapters=request.num_chapters,
        enhance=request.enhance,
        openai_api_key=openai_api_key,
        use_platform_key=use_platform_key,
    )

    return TaskStatusResponse(task_id=task_id, status="pending", message="Story generation started")


@router.post("/{story_id}/generate-audio", response_model=TaskStatusResponse)
async def generate_story_audio(
    story_id: int,
    request: GenerateAudioRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> TaskStatusResponse:
    """Start audio generation for chapters (async background task)."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Get chapters to generate
    if request.chapter_numbers:
        chapters = [c for c in story.chapters if c.chapter_number in request.chapter_numbers]
    else:
        chapters = story.chapters

    if not chapters:
        raise HTTPException(status_code=400, detail="No chapters to generate")

    # Check chapters have scripts
    for chapter in chapters:
        if not chapter.enhanced_json and not chapter.script_json:
            raise HTTPException(status_code=400, detail=f"Chapter {chapter.chapter_number} has no script")

    # Resolve ElevenLabs API key
    elevenlabs_api_key = None
    use_platform_audio_key = False
    if current_user.elevenlabs_api_key:
        elevenlabs_api_key = decrypt_key(current_user.elevenlabs_api_key)
    elif os.environ.get("ELEVENLABS_API_KEY"):
        # Free tier check for audio
        audio_used = current_user.free_audio_used or 0
        if audio_used >= FREE_AUDIO_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Free audio limit reached ({audio_used}/{FREE_AUDIO_PER_USER} used). "
                    "Add your own ElevenLabs API key in Settings to continue."
                ),
            )
        use_platform_audio_key = True
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Add your own ElevenLabs API key in Settings to generate audio.",
        )

    # Increment free audio counter if using platform key
    if use_platform_audio_key:
        current_user.free_audio_used = (current_user.free_audio_used or 0) + 1
        db.commit()

    # Start background task
    chapter_ids = [c.id for c in chapters]
    task_id = f"audio_{story_id}_{int(time.time())}"
    get_task_backend().update(task_id, "pending", 0, "Task queued, waiting to start...")
    background_tasks.add_task(
        generate_audio,
        task_id=task_id,
        story_id=story_id,
        user_id=current_user.id,
        chapter_ids=chapter_ids,
        elevenlabs_api_key=elevenlabs_api_key,
        voice_override=request.voice_override,
    )

    return TaskStatusResponse(
        task_id=task_id, status="pending", message=f"Audio generation started for {len(chapters)} chapters"
    )


@router.get("/{story_id}/audio/combined")
async def download_combined_audio(
    story_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> FileResponse:
    """Combine all chapter audio files into a single MP3 download."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    storage = get_storage()
    chapters_with_audio = sorted([c for c in story.chapters if c.audio_path], key=lambda c: c.chapter_number)

    if not chapters_with_audio:
        raise HTTPException(status_code=404, detail="No audio files available")

    if len(chapters_with_audio) == 1:
        key = f"{story_id}/ch{chapters_with_audio[0].chapter_number}.mp3"
        with storage.get_path(key) as single:
            if not single:
                raise HTTPException(status_code=404, detail="Audio file not found")
            return FileResponse(str(single), media_type="audio/mpeg", filename=f"{story.title}.mp3")

    # Build ffmpeg concat file — use get_path to get local files for each chapter
    concat_list_path = None
    output_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for ch in chapters_with_audio:
                key = f"{story_id}/ch{ch.chapter_number}.mp3"
                with storage.get_path(key) as ch_path:
                    if ch_path:
                        f.write(f"file '{ch_path}'\n")
            concat_list_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            output_path = tmp.name

        result = subprocess.run(  # noqa: S603
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c", "copy", output_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Failed to combine audio files")

        return FileResponse(
            output_path,
            media_type="audio/mpeg",
            filename=f"{story.title}.mp3",
        )
    finally:
        if concat_list_path:
            os.unlink(concat_list_path)


@router.get("/{story_id}/chapters/{chapter_number}", response_model=ChapterResponse)
async def get_chapter(
    story_id: int,
    chapter_number: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Chapter:
    """Get a specific chapter."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapter = next((c for c in story.chapters if c.chapter_number == chapter_number), None)

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    return chapter


@router.get("/{story_id}/chapters/{chapter_number}/script")
async def get_chapter_script(
    story_id: int,
    chapter_number: int,
    enhanced: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list:
    """Get the JSON script for a chapter."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapter = next((c for c in story.chapters if c.chapter_number == chapter_number), None)

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    script = chapter.enhanced_json if enhanced and chapter.enhanced_json else chapter.script_json

    if not script:
        raise HTTPException(status_code=404, detail="Script not generated yet")

    return json.loads(script)


@router.put("/{story_id}/chapters/{chapter_number}/script")
async def update_chapter_script(
    story_id: int,
    chapter_number: int,
    script: Any = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Update the JSON script for a chapter."""
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == current_user.id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapter = next((c for c in story.chapters if c.chapter_number == chapter_number), None)

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    script_str = json.dumps(script, ensure_ascii=False)
    # Save to enhanced_json if it existed, otherwise script_json
    if chapter.enhanced_json:
        chapter.enhanced_json = script_str
    else:
        chapter.script_json = script_str
    db.commit()

    return {"message": "Script updated"}
