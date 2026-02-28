"""
Block system API endpoints — block/unblock users, list blocked users.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from webapp.models.database import Block, Follow, User, get_db
from webapp.models.schemas import BlockedUserItem, BlockResponse
from webapp.services.auth import get_current_user

router = APIRouter(prefix="/api/blocks", tags=["Blocks"])


@router.post("/users/{user_id}", response_model=BlockResponse)
async def toggle_block(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlockResponse:
    """Toggle block/unblock a user."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Block).filter(Block.blocker_id == current_user.id, Block.blocked_id == user_id).first()

    if existing:
        # Unblock
        db.delete(existing)
        db.commit()
        return BlockResponse(blocked=False)

    # Block: remove mutual follows first
    db.query(Follow).filter(Follow.follower_id == current_user.id, Follow.following_id == user_id).delete()
    db.query(Follow).filter(Follow.follower_id == user_id, Follow.following_id == current_user.id).delete()

    db.add(Block(blocker_id=current_user.id, blocked_id=user_id))
    db.commit()
    return BlockResponse(blocked=True)


@router.get("/", response_model=list[BlockedUserItem])
async def list_blocked_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BlockedUserItem]:
    """List all users blocked by the current user."""
    blocks = db.query(Block).filter(Block.blocker_id == current_user.id).order_by(Block.created_at.desc()).all()

    result: list[BlockedUserItem] = []
    for b in blocks:
        user = db.query(User).filter(User.id == b.blocked_id).first()
        if user:
            result.append(
                BlockedUserItem(
                    id=user.id,
                    username=user.username,
                    blocked_at=b.created_at,
                )
            )
    return result
