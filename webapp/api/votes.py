"""
Vote API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from webapp.models.database import get_db, Story, Vote, User
from webapp.models.schemas import VoteRequest
from webapp.services.auth import get_current_active_user

router = APIRouter(prefix="/api/votes", tags=["Votes"])


@router.post("/stories/{story_id}")
async def vote_on_story(
    story_id: int,
    request: VoteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Vote on a story. Send vote_type=null to remove vote."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.visibility.in_(["public", "link_only"]),
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot vote on your own story")

    if request.vote_type is not None and request.vote_type not in ("up", "down"):
        raise HTTPException(status_code=400, detail="vote_type must be 'up', 'down', or null")

    existing = db.query(Vote).filter(
        Vote.story_id == story_id, Vote.user_id == current_user.id
    ).first()

    if request.vote_type is None:
        # Remove vote
        if existing:
            if existing.vote_type == "up":
                story.upvotes = max(0, story.upvotes - 1)
            else:
                story.downvotes = max(0, story.downvotes - 1)
            db.delete(existing)
    elif existing:
        # Update vote
        if existing.vote_type != request.vote_type:
            if existing.vote_type == "up":
                story.upvotes = max(0, story.upvotes - 1)
                story.downvotes += 1
            else:
                story.downvotes = max(0, story.downvotes - 1)
                story.upvotes += 1
            existing.vote_type = request.vote_type
    else:
        # New vote
        db.add(Vote(
            user_id=current_user.id,
            story_id=story_id,
            vote_type=request.vote_type,
        ))
        if request.vote_type == "up":
            story.upvotes += 1
        else:
            story.downvotes += 1

    db.commit()
    db.refresh(story)

    return {
        "upvotes": story.upvotes,
        "downvotes": story.downvotes,
        "user_vote": request.vote_type,
    }
