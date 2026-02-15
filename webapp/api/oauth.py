"""
OAuth2 authorization code flow endpoints for Google.
"""

import logging
import os
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from webapp.models.database import get_db, User
from webapp.services.auth import create_access_token
from webapp.services.oauth import oauth

router = APIRouter(prefix="/api/auth/oauth", tags=["oauth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def _get_or_create_oauth_user(
    db: Session,
    provider: str,
    oauth_id: str,
    email: Optional[str],
    name: Optional[str],
) -> Optional[User]:
    """Find existing OAuth user, link to email match, or create new user."""
    # 1. Match by (provider, oauth_id)
    user = (
        db.query(User)
        .filter(User.oauth_provider == provider, User.oauth_id == oauth_id)
        .first()
    )
    if user:
        return user

    if not email:
        return None

    # 2. Match by email — link OAuth identity to existing account
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        db.commit()
        return user

    # 3. No match — create new user
    username = email.split("@")[0]
    # Ensure unique username
    base_username = username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    user = User(
        email=email,
        username=username,
        hashed_password=None,
        oauth_provider=provider,
        oauth_id=oauth_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _redirect_with_token(user: User, db: Session) -> RedirectResponse:
    """Generate JWT and redirect to frontend with token."""
    user.last_login = datetime.utcnow()
    db.commit()
    token = create_access_token(data={"sub": str(user.id)})
    return RedirectResponse(url=f"{FRONTEND_URL}/login?token={token}")


def _redirect_with_error(error: str) -> RedirectResponse:
    return RedirectResponse(url=f"{FRONTEND_URL}/login?error={error}")


# ── Google ───────────────────────────────────────────────────────────

@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, str(redirect_uri))


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error("OAuth token exchange failed: %s", e)
        return _redirect_with_error("oauth_failed")

    userinfo = token.get("userinfo", {})
    email = userinfo.get("email")
    name = userinfo.get("name")
    oauth_id = userinfo.get("sub")

    if not oauth_id:
        return _redirect_with_error("oauth_failed")
    if not email:
        return _redirect_with_error("oauth_no_email")

    user = _get_or_create_oauth_user(db, "google", oauth_id, email, name)
    if not user:
        return _redirect_with_error("oauth_no_email")

    return _redirect_with_token(user, db)
