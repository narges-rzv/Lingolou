"""
Public (unauthenticated) API endpoints for shared stories.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from webapp.models.database import get_db, Story, Chapter, User, Vote, PlatformBudget, FREE_STORIES_PER_USER
from webapp.models.schemas import PublicStoryListItem, PublicStoryResponse, BudgetStatus
from webapp.services.auth import get_current_user_optional

router = APIRouter(prefix="/api/public", tags=["Public"])


@router.get("/budget", response_model=BudgetStatus)
async def get_budget_status(db: Session = Depends(get_db)):
    """Get platform free-tier budget status (public, unauthenticated)."""
    budget = db.query(PlatformBudget).first()
    if not budget:
        return BudgetStatus(
            total_budget=50.0, total_spent=0.0,
            free_stories_generated=0, free_stories_per_user=FREE_STORIES_PER_USER,
        )
    return BudgetStatus(
        total_budget=budget.total_budget,
        total_spent=round(budget.total_spent, 2),
        free_stories_generated=budget.free_stories_generated,
        free_stories_per_user=FREE_STORIES_PER_USER,
    )


@router.get("/stories", response_model=List[PublicStoryListItem])
async def list_public_stories(
    skip: int = 0,
    limit: int = 20,
    language: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all public completed stories, ordered by net score."""
    query = (
        db.query(Story)
        .filter(Story.visibility == "public", Story.status == "completed")
    )
    if language:
        query = query.filter(Story.language == language)
    stories = (
        query
        .order_by((Story.upvotes - Story.downvotes).desc(), Story.created_at.desc())
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
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get a public or link-only story with its chapters."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.visibility.in_(["public", "link_only"]),
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    user_vote = None
    if current_user:
        vote = db.query(Vote).filter(
            Vote.story_id == story_id, Vote.user_id == current_user.id
        ).first()
        if vote:
            user_vote = vote.vote_type

    return PublicStoryResponse(
        id=story.id,
        title=story.title,
        description=story.description,
        language=story.language,
        status=story.status,
        visibility=story.visibility,
        share_code=story.share_code,
        upvotes=story.upvotes,
        downvotes=story.downvotes,
        user_vote=user_vote,
        created_at=story.created_at,
        chapters=story.chapters,
        owner_name=story.owner.username,
    )


@router.get("/share/{share_code}", response_model=PublicStoryResponse)
async def get_shared_story(
    share_code: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get a story by its share code (link-only or public)."""
    story = db.query(Story).filter(
        Story.share_code == share_code,
        Story.visibility.in_(["public", "link_only"]),
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    user_vote = None
    if current_user:
        vote = db.query(Vote).filter(
            Vote.story_id == story.id, Vote.user_id == current_user.id
        ).first()
        if vote:
            user_vote = vote.vote_type

    return PublicStoryResponse(
        id=story.id,
        title=story.title,
        description=story.description,
        language=story.language,
        status=story.status,
        visibility=story.visibility,
        share_code=story.share_code,
        upvotes=story.upvotes,
        downvotes=story.downvotes,
        user_vote=user_vote,
        created_at=story.created_at,
        chapters=story.chapters,
        owner_name=story.owner.username,
    )


@router.get("/stories/{story_id}/chapters/{chapter_number}/script")
async def get_public_chapter_script(
    story_id: int,
    chapter_number: int,
    enhanced: bool = True,
    db: Session = Depends(get_db),
):
    """Get the JSON script for a chapter of a public/link-only story."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.visibility.in_(["public", "link_only"]),
    ).first()

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


@router.get("/stories/{story_id}/audio/combined")
async def download_public_combined_audio(
    story_id: int,
    db: Session = Depends(get_db),
):
    """Download combined audio for a public/link-only story."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.visibility.in_(["public", "link_only"]),
    ).first()

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
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list, "-c", "copy", output_path,
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
