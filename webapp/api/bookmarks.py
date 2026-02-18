"""
Bookmark API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from webapp.models.database import Bookmark, Story, User, get_db
from webapp.models.schemas import BookmarkedStoryListItem, BookmarkResponse
from webapp.services.auth import get_current_active_user

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])


@router.post("/stories/{story_id}", response_model=BookmarkResponse)
async def toggle_bookmark(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> BookmarkResponse:
    """Toggle bookmark on a public or link-only story."""
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

    existing = db.query(Bookmark).filter(Bookmark.story_id == story_id, Bookmark.user_id == current_user.id).first()

    if existing:
        db.delete(existing)
        db.commit()
        return BookmarkResponse(bookmarked=False)

    db.add(Bookmark(user_id=current_user.id, story_id=story_id))
    db.commit()
    return BookmarkResponse(bookmarked=True)


@router.get("/stories", response_model=list[BookmarkedStoryListItem])
async def list_bookmarked_stories(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[BookmarkedStoryListItem]:
    """List the current user's bookmarked stories, most recent first."""
    bookmarks = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == current_user.id)
        .order_by(Bookmark.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        BookmarkedStoryListItem(
            id=bm.story.id,
            title=bm.story.title,
            description=bm.story.description,
            language=bm.story.language,
            status=bm.story.status,
            chapter_count=len(bm.story.chapters),
            upvotes=bm.story.upvotes,
            downvotes=bm.story.downvotes,
            created_at=bm.story.created_at,
            owner_name=bm.story.owner.username,
            bookmarked_at=bm.created_at,
        )
        for bm in bookmarks
    ]
