"""
Stories API endpoints.
"""

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from webapp.models.database import get_db, Story, Chapter, UsageLog, User
from webapp.models.schemas import (
    StoryCreate, StoryUpdate, StoryResponse, StoryListResponse,
    ChapterResponse, GenerateStoryRequest, GenerateAudioRequest,
    TaskStatusResponse
)
from webapp.services.auth import get_current_active_user
from webapp.services.generation import (
    generate_story_task, generate_audio_task,
    get_task_status, task_store
)

router = APIRouter(prefix="/api/stories", tags=["Stories"])


@router.get("/", response_model=List[StoryListResponse])
async def list_stories(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all stories for the current user."""
    stories = db.query(Story).filter(
        Story.user_id == current_user.id
    ).order_by(Story.created_at.desc()).offset(skip).limit(limit).all()

    return [
        StoryListResponse(
            id=s.id,
            title=s.title,
            description=s.description,
            status=s.status,
            chapter_count=len(s.chapters),
            created_at=s.created_at
        )
        for s in stories
    ]


@router.post("/", response_model=StoryResponse)
async def create_story(
    story: StoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new story (without generating content yet)."""
    db_story = Story(
        user_id=current_user.id,
        title=story.title,
        description=story.description,
        prompt=story.prompt,
        config_json=json.dumps(story.config_override) if story.config_override else None,
        status="created"
    )
    db.add(db_story)
    db.commit()
    db.refresh(db_story)

    # Create empty chapters
    for i in range(1, story.num_chapters + 1):
        chapter = Chapter(
            story_id=db_story.id,
            chapter_number=i,
            status="pending"
        )
        db.add(chapter)
    db.commit()
    db.refresh(db_story)

    return db_story


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific story with all chapters."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return story


@router.patch("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: int,
    story_update: StoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update story metadata."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story_update.title:
        story.title = story_update.title
    if story_update.description:
        story.description = story_update.description

    db.commit()
    db.refresh(story)
    return story


@router.delete("/{story_id}")
async def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a story and all its chapters."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    db.delete(story)
    db.commit()
    return {"message": "Story deleted"}


@router.post("/{story_id}/generate", response_model=TaskStatusResponse)
async def generate_story_content(
    story_id: int,
    request: GenerateStoryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start story script generation (async task)."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status == "generating":
        raise HTTPException(status_code=400, detail="Story is already being generated")

    # Update story with request data
    story.prompt = request.prompt
    story.status = "generating"
    db.commit()

    # Start background task
    task_id = f"story_{story_id}_{current_user.id}"
    background_tasks.add_task(
        generate_story_task,
        task_id=task_id,
        story_id=story_id,
        user_id=current_user.id,
        prompt=request.prompt,
        num_chapters=request.num_chapters,
        enhance=request.enhance
    )

    return TaskStatusResponse(
        task_id=task_id,
        status="pending",
        message="Story generation started"
    )


@router.post("/{story_id}/generate-audio", response_model=TaskStatusResponse)
async def generate_story_audio(
    story_id: int,
    request: GenerateAudioRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start audio generation for chapters (async task)."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()

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
            raise HTTPException(
                status_code=400,
                detail=f"Chapter {chapter.chapter_number} has no script"
            )

    # Start background task
    task_id = f"audio_{story_id}_{current_user.id}"
    chapter_ids = [c.id for c in chapters]

    background_tasks.add_task(
        generate_audio_task,
        task_id=task_id,
        story_id=story_id,
        user_id=current_user.id,
        chapter_ids=chapter_ids
    )

    return TaskStatusResponse(
        task_id=task_id,
        status="pending",
        message=f"Audio generation started for {len(chapters)} chapters"
    )


@router.get("/{story_id}/chapters/{chapter_number}", response_model=ChapterResponse)
async def get_chapter(
    story_id: int,
    chapter_number: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific chapter."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapter = next(
        (c for c in story.chapters if c.chapter_number == chapter_number),
        None
    )

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    return chapter


@router.get("/{story_id}/chapters/{chapter_number}/script")
async def get_chapter_script(
    story_id: int,
    chapter_number: int,
    enhanced: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the JSON script for a chapter."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapter = next(
        (c for c in story.chapters if c.chapter_number == chapter_number),
        None
    )

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    script = chapter.enhanced_json if enhanced and chapter.enhanced_json else chapter.script_json

    if not script:
        raise HTTPException(status_code=404, detail="Script not generated yet")

    return json.loads(script)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_generation_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get status of a generation task."""
    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status
