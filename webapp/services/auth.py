"""
Authentication service for user management and JWT tokens.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, EmailStr

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from webapp.models.database import User, get_db

# Configuration
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# Pydantic models
class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user info response."""

    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for decoded token data."""

    user_id: int | None = None


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Token utilities
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with expiration."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        return TokenData(user_id=int(sub))
    except JWTError:
        return None


# User operations
def get_user_by_email(db: Session, email: str) -> User | None:
    """Look up a user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """Look up a user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Look up a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user with hashed password."""
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, login: str, password: str) -> User | None:
    """Authenticate a user by login (email or username) and password."""
    user = get_user_by_email(db, login) or get_user_by_username(db, login)
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def update_last_login(db: Session, user: User) -> None:
    """Update the user's last_login timestamp."""
    user.last_login = datetime.now(UTC)
    db.commit()


# Dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """FastAPI dependency that extracts and validates the current user from JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user = get_user_by_id(db, token_data.user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency that ensures the current user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """Return the current user if a valid token is present, else None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    token_data = decode_token(token)
    if token_data is None or token_data.user_id is None:
        return None
    return get_user_by_id(db, token_data.user_id)
