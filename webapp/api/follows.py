"""
Follow system API endpoints — follow/unfollow, followers list, timeline feed, user profiles.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from webapp.models.database import Block, Follow, Story, User, World, get_db
from webapp.models.schemas import (
    FollowResponse,
    FollowUserItem,
    NewFollowersResponse,
    PublicStoryListItem,
    TimelineStoryItem,
    TimelineWorldItem,
    UserProfileResponse,
    WorldListItem,
)
from webapp.services.auth import get_current_user

router = APIRouter(prefix="/api/follows", tags=["Follows"])


def is_following(db: Session, follower_id: int, following_id: int) -> bool:
    """Check whether follower_id follows following_id."""
    return (
        db.query(Follow).filter(Follow.follower_id == follower_id, Follow.following_id == following_id).first()
        is not None
    )


def is_blocked(db: Session, user_a: int, user_b: int) -> bool:
    """Check whether a block exists in either direction between two users."""
    return (
        db.query(Block)
        .filter(
            or_(
                (Block.blocker_id == user_a) & (Block.blocked_id == user_b),
                (Block.blocker_id == user_b) & (Block.blocked_id == user_a),
            )
        )
        .first()
        is not None
    )


def _blocked_user_ids(db: Session, user_id: int) -> set[int]:
    """Return the set of user IDs blocked by or blocking the given user."""
    rows = db.query(Block).filter(or_(Block.blocker_id == user_id, Block.blocked_id == user_id)).all()
    ids: set[int] = set()
    for b in rows:
        ids.add(b.blocker_id)
        ids.add(b.blocked_id)
    ids.discard(user_id)
    return ids


@router.post("/users/{user_id}", response_model=FollowResponse)
async def toggle_follow(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FollowResponse:
    """Toggle follow/unfollow a user."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if is_blocked(db, current_user.id, user_id):
        raise HTTPException(status_code=403, detail="Cannot follow this user")

    existing = db.query(Follow).filter(Follow.follower_id == current_user.id, Follow.following_id == user_id).first()

    if existing:
        db.delete(existing)
        db.commit()
        return FollowResponse(following=False)

    db.add(Follow(follower_id=current_user.id, following_id=user_id))
    db.commit()
    return FollowResponse(following=True)


@router.get("/following", response_model=list[FollowUserItem])
async def list_following(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FollowUserItem]:
    """List users the current user follows."""
    blocked_ids = _blocked_user_ids(db, current_user.id)
    follows = (
        db.query(Follow)
        .filter(Follow.follower_id == current_user.id)
        .order_by(Follow.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result: list[FollowUserItem] = []
    for f in follows:
        if f.following_id in blocked_ids:
            continue
        user = db.query(User).filter(User.id == f.following_id).first()
        if user:
            story_count = db.query(func.count(Story.id)).filter(Story.user_id == user.id).scalar() or 0
            result.append(
                FollowUserItem(
                    id=user.id,
                    username=user.username,
                    story_count=story_count,
                    is_following=True,
                )
            )
    return result


@router.get("/followers", response_model=list[FollowUserItem])
async def list_followers(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FollowUserItem]:
    """List the current user's followers."""
    blocked_ids = _blocked_user_ids(db, current_user.id)
    follows = (
        db.query(Follow)
        .filter(Follow.following_id == current_user.id)
        .order_by(Follow.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result: list[FollowUserItem] = []
    for f in follows:
        if f.follower_id in blocked_ids:
            continue
        user = db.query(User).filter(User.id == f.follower_id).first()
        if user:
            story_count = db.query(func.count(Story.id)).filter(Story.user_id == user.id).scalar() or 0
            result.append(
                FollowUserItem(
                    id=user.id,
                    username=user.username,
                    story_count=story_count,
                    is_following=is_following(db, current_user.id, user.id),
                )
            )
    return result


@router.get("/users/{user_id}/followers", response_model=list[FollowUserItem])
async def list_user_followers(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FollowUserItem]:
    """List any user's followers (paginated)."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if is_blocked(db, current_user.id, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    blocked_ids = _blocked_user_ids(db, current_user.id)
    follows = (
        db.query(Follow)
        .filter(Follow.following_id == user_id)
        .order_by(Follow.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result: list[FollowUserItem] = []
    for f in follows:
        if f.follower_id in blocked_ids:
            continue
        user = db.query(User).filter(User.id == f.follower_id).first()
        if user:
            story_count = db.query(func.count(Story.id)).filter(Story.user_id == user.id).scalar() or 0
            result.append(
                FollowUserItem(
                    id=user.id,
                    username=user.username,
                    story_count=story_count,
                    is_following=is_following(db, current_user.id, user.id),
                )
            )
    return result


@router.get("/users/{user_id}/following", response_model=list[FollowUserItem])
async def list_user_following(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FollowUserItem]:
    """List any user's following (paginated)."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if is_blocked(db, current_user.id, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    blocked_ids = _blocked_user_ids(db, current_user.id)
    follows = (
        db.query(Follow)
        .filter(Follow.follower_id == user_id)
        .order_by(Follow.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result: list[FollowUserItem] = []
    for f in follows:
        if f.following_id in blocked_ids:
            continue
        user = db.query(User).filter(User.id == f.following_id).first()
        if user:
            story_count = db.query(func.count(Story.id)).filter(Story.user_id == user.id).scalar() or 0
            result.append(
                FollowUserItem(
                    id=user.id,
                    username=user.username,
                    story_count=story_count,
                    is_following=is_following(db, current_user.id, user.id),
                )
            )
    return result


@router.get("/new-followers", response_model=NewFollowersResponse)
async def get_new_followers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NewFollowersResponse:
    """Get followers since last_followers_seen_at."""
    blocked_ids = _blocked_user_ids(db, current_user.id)
    query = db.query(Follow).filter(Follow.following_id == current_user.id)
    if current_user.last_followers_seen_at:
        query = query.filter(Follow.created_at > current_user.last_followers_seen_at)

    new_follows = query.order_by(Follow.created_at.desc()).all()

    result: list[FollowUserItem] = []
    for f in new_follows:
        if f.follower_id in blocked_ids:
            continue
        user = db.query(User).filter(User.id == f.follower_id).first()
        if user:
            story_count = db.query(func.count(Story.id)).filter(Story.user_id == user.id).scalar() or 0
            result.append(
                FollowUserItem(
                    id=user.id,
                    username=user.username,
                    story_count=story_count,
                    is_following=is_following(db, current_user.id, user.id),
                )
            )

    return NewFollowersResponse(count=len(result), followers=result)


@router.post("/new-followers/seen", response_model=dict)
async def mark_new_followers_seen(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Mark new followers as seen by setting last_followers_seen_at to now."""
    current_user.last_followers_seen_at = datetime.now(tz=UTC)
    db.commit()
    return {"status": "ok"}


@router.get("/timeline", response_model=list[TimelineStoryItem])
async def get_timeline(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TimelineStoryItem]:
    """Get stories from followed users (public + followers visibility, completed only)."""
    blocked_ids = _blocked_user_ids(db, current_user.id)
    followed_ids = [
        f.following_id
        for f in db.query(Follow).filter(Follow.follower_id == current_user.id).all()
        if f.following_id not in blocked_ids
    ]

    if not followed_ids:
        return []

    stories = (
        db.query(Story)
        .filter(
            Story.user_id.in_(followed_ids),
            Story.status == "completed",
            or_(Story.visibility == "public", Story.visibility == "followers"),
        )
        .order_by(Story.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        TimelineStoryItem(
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
            owner_id=s.user_id,
        )
        for s in stories
    ]


@router.get("/timeline/worlds", response_model=list[TimelineWorldItem])
async def get_timeline_worlds(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TimelineWorldItem]:
    """Get worlds from followed users (public + followers visibility)."""
    blocked_ids = _blocked_user_ids(db, current_user.id)
    followed_ids = [
        f.following_id
        for f in db.query(Follow).filter(Follow.follower_id == current_user.id).all()
        if f.following_id not in blocked_ids
    ]

    if not followed_ids:
        return []

    worlds = (
        db.query(World)
        .filter(
            World.user_id.in_(followed_ids),
            or_(World.visibility == "public", World.visibility == "followers"),
        )
        .order_by(World.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        TimelineWorldItem(
            id=w.id,
            name=w.name,
            description=w.description,
            visibility=w.visibility,
            story_count=len(w.stories),
            owner_name=w.owner.username if w.owner else "Unknown",
            owner_id=w.user_id or 0,
            created_at=w.created_at,
        )
        for w in worlds
    ]


@router.get("/users/{user_id}/stories", response_model=list[PublicStoryListItem])
async def list_user_stories(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PublicStoryListItem]:
    """List a user's stories with visibility gating."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id != current_user.id and is_blocked(db, current_user.id, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(Story).filter(Story.user_id == user_id)

    if user_id == current_user.id:
        # Own profile: all stories
        pass
    elif is_following(db, current_user.id, user_id):
        query = query.filter(
            Story.status == "completed",
            or_(Story.visibility == "public", Story.visibility == "followers"),
        )
    else:
        query = query.filter(Story.status == "completed", Story.visibility == "public")

    stories = query.order_by(Story.created_at.desc()).offset(skip).limit(limit).all()

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
            owner_id=s.user_id,
        )
        for s in stories
    ]


@router.get("/users/{user_id}/worlds", response_model=list[WorldListItem])
async def list_user_worlds(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorldListItem]:
    """List a user's worlds with visibility gating."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id != current_user.id and is_blocked(db, current_user.id, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(World).filter(World.user_id == user_id)

    if user_id == current_user.id:
        # Own profile: all worlds
        pass
    elif is_following(db, current_user.id, user_id):
        query = query.filter(or_(World.visibility == "public", World.visibility == "followers"))
    else:
        query = query.filter(World.visibility == "public")

    worlds = query.order_by(World.created_at.desc()).offset(skip).limit(limit).all()

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


@router.get("/users/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Get a user's public profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if is_blocked(db, current_user.id, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    story_count = (
        db.query(func.count(Story.id))
        .filter(Story.user_id == user_id, Story.visibility.in_(["public", "followers"]))
        .scalar()
        or 0
    )
    world_count = (
        db.query(func.count(World.id))
        .filter(World.user_id == user_id, World.visibility.in_(["public", "followers"]))
        .scalar()
        or 0
    )
    follower_count = db.query(func.count(Follow.id)).filter(Follow.following_id == user_id).scalar() or 0
    following_count = db.query(func.count(Follow.id)).filter(Follow.follower_id == user_id).scalar() or 0

    return UserProfileResponse(
        id=user.id,
        username=user.username,
        story_count=story_count,
        world_count=world_count,
        follower_count=follower_count,
        following_count=following_count,
        is_following=is_following(db, current_user.id, user_id),
        is_blocked=False,
        created_at=user.created_at,
    )
