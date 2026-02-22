"""
World CRUD API endpoints.
"""

from __future__ import annotations

import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from webapp.models.database import Follow, Story, User, World, get_db
from webapp.models.schemas import ShareLinkResponse, WorldCreate, WorldListItem, WorldResponse, WorldUpdate
from webapp.services.auth import get_current_active_user

router = APIRouter(prefix="/api/worlds", tags=["Worlds"])


def _world_to_response(world: World) -> WorldResponse:
    """Convert a World model to a WorldResponse schema."""
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


def _world_to_list_item(world: World) -> WorldListItem:
    """Convert a World model to a WorldListItem schema."""
    return WorldListItem(
        id=world.id,
        name=world.name,
        description=world.description,
        is_builtin=world.is_builtin,
        visibility=world.visibility,
        story_count=len(world.stories),
        owner_name=world.owner.username if world.owner else None,
        created_at=world.created_at,
    )


@router.get("/", response_model=list[WorldListItem])
async def list_worlds(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[WorldListItem]:
    """List user's own worlds plus public, built-in, and followed users' worlds."""
    followed_ids = [f.following_id for f in db.query(Follow).filter(Follow.follower_id == current_user.id).all()]
    worlds = (
        db.query(World)
        .filter(
            or_(
                World.user_id == current_user.id,
                World.visibility == "public",
                World.is_builtin.is_(True),
                (World.visibility == "followers") & (World.user_id.in_(followed_ids)) if followed_ids else False,
            )
        )
        .order_by(World.is_builtin.desc(), World.created_at.desc())
        .all()
    )
    return [_world_to_list_item(w) for w in worlds]


@router.post("/", response_model=WorldResponse, status_code=201)
async def create_world(
    world_data: WorldCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> WorldResponse:
    """Create a new world."""
    if world_data.visibility not in ("private", "link_only", "public", "followers"):
        raise HTTPException(status_code=400, detail="Invalid visibility value")

    world = World(
        user_id=current_user.id,
        name=world_data.name,
        description=world_data.description,
        prompt_template=world_data.prompt_template,
        characters_json=json.dumps(world_data.characters) if world_data.characters else None,
        valid_speakers_json=json.dumps(world_data.valid_speakers) if world_data.valid_speakers else None,
        voice_config_json=json.dumps(world_data.voice_config) if world_data.voice_config else None,
        visibility=world_data.visibility,
    )
    db.add(world)
    db.commit()
    db.refresh(world)
    return _world_to_response(world)


@router.get("/{world_id}", response_model=WorldResponse)
async def get_world(
    world_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> WorldResponse:
    """Get a world by ID (owner, public, or built-in)."""
    world = db.query(World).filter(World.id == world_id).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    if world.user_id != current_user.id and world.visibility != "public" and not world.is_builtin:
        # Allow followers-visibility worlds if user follows the owner
        from webapp.api.follows import is_following as check_following

        if world.visibility != "followers" or not check_following(db, current_user.id, world.user_id):
            raise HTTPException(status_code=404, detail="World not found")

    return _world_to_response(world)


@router.patch("/{world_id}", response_model=WorldResponse)
async def update_world(
    world_id: int,
    world_update: WorldUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> WorldResponse:
    """Update a world (owner only, not built-in)."""
    world = db.query(World).filter(World.id == world_id, World.user_id == current_user.id).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    if world.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot modify built-in worlds")

    if world_update.name is not None:
        world.name = world_update.name
    if world_update.description is not None:
        world.description = world_update.description
    if world_update.prompt_template is not None:
        world.prompt_template = world_update.prompt_template
    if world_update.characters is not None:
        world.characters_json = json.dumps(world_update.characters)
    if world_update.valid_speakers is not None:
        world.valid_speakers_json = json.dumps(world_update.valid_speakers)
    if world_update.voice_config is not None:
        world.voice_config_json = json.dumps(world_update.voice_config)
    if world_update.visibility is not None:
        if world_update.visibility not in ("private", "link_only", "public", "followers"):
            raise HTTPException(status_code=400, detail="Invalid visibility value")
        world.visibility = world_update.visibility
        if world_update.visibility in ("link_only", "public") and not world.share_code:
            world.share_code = str(uuid.uuid4())

    db.commit()
    db.refresh(world)
    return _world_to_response(world)


@router.delete("/{world_id}")
async def delete_world(
    world_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a world (owner only, not built-in, no stories using it)."""
    world = db.query(World).filter(World.id == world_id, World.user_id == current_user.id).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    if world.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot delete built-in worlds")

    story_count = db.query(Story).filter(Story.world_id == world_id).count()
    if story_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete world with {story_count} stories. Remove or reassign stories first.",
        )

    db.delete(world)
    db.commit()
    return {"message": "World deleted"}


@router.post("/{world_id}/share-link", response_model=ShareLinkResponse)
async def generate_world_share_link(
    world_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ShareLinkResponse:
    """Generate or return a share link for a world."""
    world = db.query(World).filter(World.id == world_id, World.user_id == current_user.id).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    if not world.share_code:
        world.share_code = str(uuid.uuid4())
        db.commit()
        db.refresh(world)

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    return ShareLinkResponse(
        share_code=world.share_code,
        share_url=f"{frontend_url}/worlds/share/{world.share_code}",
    )
