"""
Public (unauthenticated) API endpoints for shared stories.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from webapp.models.database import (
    FREE_STORIES_PER_USER,
    Bookmark,
    Chapter,
    PlatformBudget,
    Story,
    User,
    Vote,
    World,
    get_db,
)
from webapp.models.schemas import (
    BudgetStatus,
    PublicStoryListItem,
    PublicStoryResponse,
    StoryResponse,
    WorldListItem,
    WorldResponse,
)
from webapp.services.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/public", tags=["Public"])


@router.get("/budget", response_model=BudgetStatus)
async def get_budget_status(db: Session = Depends(get_db)) -> BudgetStatus:
    """Get platform free-tier budget status (public, unauthenticated)."""
    budget = db.query(PlatformBudget).first()
    if not budget:
        return BudgetStatus(
            total_budget=50.0,
            total_spent=0.0,
            free_stories_generated=0,
            free_stories_per_user=FREE_STORIES_PER_USER,
        )
    return BudgetStatus(
        total_budget=budget.total_budget,
        total_spent=round(budget.total_spent, 2),
        free_stories_generated=budget.free_stories_generated,
        free_stories_per_user=FREE_STORIES_PER_USER,
    )


@router.get("/stories", response_model=list[PublicStoryListItem])
async def list_public_stories(
    skip: int = 0,
    limit: int = 20,
    language: str | None = None,
    db: Session = Depends(get_db),
) -> list[PublicStoryListItem]:
    """List all public completed stories, ordered by net score."""
    query = db.query(Story).filter(Story.visibility == "public", Story.status == "completed")
    if language:
        query = query.filter(Story.language == language)
    stories = (
        query.order_by((Story.upvotes - Story.downvotes).desc(), Story.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        PublicStoryListItem(
            id=s.id,
            title=s.title,
            description=s.description,
            language=s.language,
            world_id=s.world_id,
            world_name=s.world.name if s.world else None,
            status=s.status,
            chapter_count=len(s.chapters),
            upvotes=s.upvotes,
            downvotes=s.downvotes,
            created_at=s.created_at,
            owner_name=s.owner.username,
        )
        for s in stories
    ]


@router.get("/stories/{story_id}", response_model=PublicStoryResponse)
async def get_public_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> PublicStoryResponse:
    """Get a public or link-only story with its chapters."""
    story = (
        db.query(Story)
        .filter(
            Story.id == story_id,
            Story.visibility.in_(["public", "link_only"]),
        )
        .first()
    )

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    user_vote = None
    is_bookmarked = False
    if current_user:
        vote = db.query(Vote).filter(Vote.story_id == story_id, Vote.user_id == current_user.id).first()
        if vote:
            user_vote = vote.vote_type
        is_bookmarked = (
            db.query(Bookmark).filter(Bookmark.story_id == story_id, Bookmark.user_id == current_user.id).first()
            is not None
        )

    return PublicStoryResponse(
        id=story.id,
        title=story.title,
        description=story.description,
        prompt=story.prompt,
        language=story.language,
        status=story.status,
        visibility=story.visibility,
        share_code=story.share_code,
        upvotes=story.upvotes,
        downvotes=story.downvotes,
        user_vote=user_vote,
        is_bookmarked=is_bookmarked,
        created_at=story.created_at,
        chapters=story.chapters,
        owner_name=story.owner.username,
    )


@router.get("/share/{share_code}", response_model=PublicStoryResponse)
async def get_shared_story(
    share_code: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> PublicStoryResponse:
    """Get a story by its share code (link-only or public)."""
    story = (
        db.query(Story)
        .filter(
            Story.share_code == share_code,
            Story.visibility.in_(["public", "link_only"]),
        )
        .first()
    )

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    user_vote = None
    is_bookmarked = False
    if current_user:
        vote = db.query(Vote).filter(Vote.story_id == story.id, Vote.user_id == current_user.id).first()
        if vote:
            user_vote = vote.vote_type
        is_bookmarked = (
            db.query(Bookmark).filter(Bookmark.story_id == story.id, Bookmark.user_id == current_user.id).first()
            is not None
        )

    return PublicStoryResponse(
        id=story.id,
        title=story.title,
        description=story.description,
        prompt=story.prompt,
        language=story.language,
        status=story.status,
        visibility=story.visibility,
        share_code=story.share_code,
        upvotes=story.upvotes,
        downvotes=story.downvotes,
        user_vote=user_vote,
        is_bookmarked=is_bookmarked,
        created_at=story.created_at,
        chapters=story.chapters,
        owner_name=story.owner.username,
    )


@router.post("/stories/{story_id}/fork", response_model=StoryResponse, status_code=201)
async def fork_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StoryResponse:
    """Fork a public/link-only story into the current user's collection."""
    source = (
        db.query(Story)
        .filter(
            Story.id == story_id,
            Story.visibility.in_(["public", "link_only"]),
        )
        .first()
    )

    if not source:
        raise HTTPException(status_code=404, detail="Story not found")

    new_story = Story(
        user_id=current_user.id,
        title=f"Copy of {source.title}",
        description=source.description,
        prompt=source.prompt,
        language=source.language,
        world_id=source.world_id,
        config_json=source.config_json,
        status="completed",
        visibility="private",
        upvotes=0,
        downvotes=0,
    )
    db.add(new_story)
    db.flush()

    for src_ch in sorted(source.chapters, key=lambda c: c.chapter_number):
        new_ch = Chapter(
            story_id=new_story.id,
            chapter_number=src_ch.chapter_number,
            title=src_ch.title,
            script_json=src_ch.script_json,
            enhanced_json=src_ch.enhanced_json,
            status="completed",
            audio_path=None,
            audio_duration=None,
        )
        db.add(new_ch)

    db.commit()
    db.refresh(new_story)

    return StoryResponse(
        id=new_story.id,
        title=new_story.title,
        description=new_story.description,
        prompt=new_story.prompt,
        language=new_story.language,
        world_id=new_story.world_id,
        world_name=new_story.world.name if new_story.world else None,
        status=new_story.status,
        visibility=new_story.visibility,
        share_code=new_story.share_code,
        upvotes=new_story.upvotes,
        downvotes=new_story.downvotes,
        created_at=new_story.created_at,
        updated_at=new_story.updated_at,
        chapters=new_story.chapters,
    )


@router.get("/stories/{story_id}/chapters/{chapter_number}/script")
async def get_public_chapter_script(
    story_id: int,
    chapter_number: int,
    enhanced: bool = True,
    db: Session = Depends(get_db),
) -> list:
    """Get the JSON script for a chapter of a public/link-only story."""
    story = (
        db.query(Story)
        .filter(
            Story.id == story_id,
            Story.visibility.in_(["public", "link_only"]),
        )
        .first()
    )

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapter = next(
        (c for c in story.chapters if c.chapter_number == chapter_number),
        None,
    )

    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    script = chapter.enhanced_json if enhanced and chapter.enhanced_json else chapter.script_json

    if not script:
        raise HTTPException(status_code=404, detail="Script not generated yet")

    return json.loads(script)


@router.get("/worlds", response_model=list[WorldListItem])
async def list_public_worlds(
    db: Session = Depends(get_db),
) -> list[WorldListItem]:
    """List public and built-in worlds."""
    from sqlalchemy import or_

    worlds = (
        db.query(World)
        .filter(or_(World.visibility == "public", World.is_builtin.is_(True)))
        .order_by(World.is_builtin.desc(), World.created_at.desc())
        .all()
    )
    return [
        WorldListItem(
            id=w.id,
            name=w.name,
            description=w.description,
            is_builtin=w.is_builtin,
            visibility=w.visibility,
            story_count=len(w.stories),
            owner_name=w.owner.username if w.owner else None,
            created_at=w.created_at,
        )
        for w in worlds
    ]


@router.get("/worlds/{world_id}", response_model=WorldResponse)
async def get_public_world(
    world_id: int,
    db: Session = Depends(get_db),
) -> WorldResponse:
    """Get a public or built-in world."""
    from sqlalchemy import or_

    world = (
        db.query(World)
        .filter(World.id == world_id, or_(World.visibility == "public", World.is_builtin.is_(True)))
        .first()
    )
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    return WorldResponse(
        id=world.id,
        name=world.name,
        description=world.description,
        is_builtin=world.is_builtin,
        prompt_template=world.prompt_template,
        characters=json.loads(world.characters_json) if world.characters_json else None,
        valid_speakers=json.loads(world.valid_speakers_json) if world.valid_speakers_json else None,
        voice_config=json.loads(world.voice_config_json) if world.voice_config_json else None,
        visibility=world.visibility,
        share_code=world.share_code,
        story_count=len(world.stories),
        owner_name=world.owner.username if world.owner else None,
        created_at=world.created_at,
        updated_at=world.updated_at,
    )


@router.get("/share/world/{share_code}", response_model=WorldResponse)
async def get_shared_world(
    share_code: str,
    db: Session = Depends(get_db),
) -> WorldResponse:
    """Get a world by its share code."""
    from sqlalchemy import or_

    world = (
        db.query(World)
        .filter(
            World.share_code == share_code,
            or_(World.visibility.in_(["public", "link_only"]), World.is_builtin.is_(True)),
        )
        .first()
    )
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    return WorldResponse(
        id=world.id,
        name=world.name,
        description=world.description,
        is_builtin=world.is_builtin,
        prompt_template=world.prompt_template,
        characters=json.loads(world.characters_json) if world.characters_json else None,
        valid_speakers=json.loads(world.valid_speakers_json) if world.valid_speakers_json else None,
        voice_config=json.loads(world.voice_config_json) if world.voice_config_json else None,
        visibility=world.visibility,
        share_code=world.share_code,
        story_count=len(world.stories),
        owner_name=world.owner.username if world.owner else None,
        created_at=world.created_at,
        updated_at=world.updated_at,
    )


@router.get("/stories/{story_id}/audio/combined")
async def download_public_combined_audio(
    story_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download combined audio for a public/link-only story."""
    story = (
        db.query(Story)
        .filter(
            Story.id == story_id,
            Story.visibility.in_(["public", "link_only"]),
        )
        .first()
    )

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    audio_dir = Path(__file__).parent.parent / "static" / "audio" / str(story_id)
    chapters_with_audio = sorted(
        [c for c in story.chapters if c.audio_path],
        key=lambda c: c.chapter_number,
    )

    if not chapters_with_audio:
        raise HTTPException(status_code=404, detail="No audio files available")

    if len(chapters_with_audio) == 1:
        single = audio_dir / f"ch{chapters_with_audio[0].chapter_number}.mp3"
        if not single.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        return FileResponse(
            str(single),
            media_type="audio/mpeg",
            filename=f"{story.title}.mp3",
        )

    # Build ffmpeg concat file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for ch in chapters_with_audio:
            ch_path = audio_dir / f"ch{ch.chapter_number}.mp3"
            if ch_path.exists():
                f.write(f"file '{ch_path}'\n")
        concat_list = f.name

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        output_path = tmp.name
    try:
        result = subprocess.run(  # noqa: S603
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-c",
                "copy",
                output_path,
            ],
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
        os.unlink(concat_list)
