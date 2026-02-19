"""
Authentication API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from webapp.models.database import FREE_AUDIO_PER_USER, FREE_STORIES_PER_USER, User, get_db
from webapp.models.schemas import ApiKeysStatus, ApiKeysUpdate
from webapp.services.auth import (
    Token,
    UserCreate,
    UserResponse,
    authenticate_user,
    create_access_token,
    create_user,
    get_current_active_user,
    get_user_by_email,
    get_user_by_username,
    update_last_login,
)
from webapp.services.crypto import encrypt_key

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a new user account."""
    # Check if email exists
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Check if username exists
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    # Create user
    db_user = create_user(db, user)
    return db_user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> dict[str, str]:
    """Login and get access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    update_last_login(db, user)

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current user information."""
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)) -> dict[str, str]:
    """Logout (client should discard token)."""
    # In a more complex setup, you might blacklist the token
    return {"message": "Successfully logged out"}


@router.put("/api-keys", response_model=ApiKeysStatus)
async def update_api_keys(
    keys: ApiKeysUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiKeysStatus:
    """Save user's own API keys (encrypted)."""
    if keys.openai_api_key is not None:
        current_user.openai_api_key = encrypt_key(keys.openai_api_key) if keys.openai_api_key else None
    if keys.elevenlabs_api_key is not None:
        current_user.elevenlabs_api_key = encrypt_key(keys.elevenlabs_api_key) if keys.elevenlabs_api_key else None
    db.commit()
    db.refresh(current_user)
    return ApiKeysStatus(
        has_openai_key=bool(current_user.openai_api_key),
        has_elevenlabs_key=bool(current_user.elevenlabs_api_key),
        free_stories_used=current_user.free_stories_used or 0,
        free_stories_limit=FREE_STORIES_PER_USER,
        free_audio_used=current_user.free_audio_used or 0,
        free_audio_limit=FREE_AUDIO_PER_USER,
    )


@router.get("/api-keys", response_model=ApiKeysStatus)
async def get_api_keys_status(
    current_user: User = Depends(get_current_active_user),
) -> ApiKeysStatus:
    """Get whether user has API keys configured (never returns actual keys)."""
    return ApiKeysStatus(
        has_openai_key=bool(current_user.openai_api_key),
        has_elevenlabs_key=bool(current_user.elevenlabs_api_key),
        free_stories_used=current_user.free_stories_used or 0,
        free_stories_limit=FREE_STORIES_PER_USER,
        free_audio_used=current_user.free_audio_used or 0,
        free_audio_limit=FREE_AUDIO_PER_USER,
    )
