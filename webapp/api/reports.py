"""
Report API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from webapp.models.database import Report, User, get_db
from webapp.models.schemas import ReportRequest
from webapp.services.auth import get_current_active_user

from .stories import _get_story_by_identifier

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.post("/stories/{story_id}")
async def report_story(
    story_id: str,
    request: ReportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Report a story as inappropriate."""
    story = _get_story_by_identifier(db, story_id)
    if story and story.visibility not in ("public", "link_only"):
        story = None

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot report your own story")

    if len(request.reason.strip()) < 10:
        raise HTTPException(status_code=400, detail="Reason must be at least 10 characters")

    existing = db.query(Report).filter(Report.story_id == story.id, Report.user_id == current_user.id).first()

    if existing:
        raise HTTPException(status_code=400, detail="You have already reported this story")

    db.add(
        Report(
            user_id=current_user.id,
            story_id=story.id,
            reason=request.reason.strip(),
        )
    )
    db.commit()

    return {"message": "Report submitted"}
