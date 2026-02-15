"""Tests for webapp/api/reports.py"""

from webapp.models.database import Story


def _create_public_story(db, user):
    story = Story(
        user_id=user.id,
        title="Reportable Story",
        status="completed",
        visibility="public",
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def test_report_story(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user)

    resp = client.post(f"/api/reports/stories/{story.id}", json={
        "reason": "This story contains inappropriate content for children",
    }, headers=other_auth_headers)
    assert resp.status_code == 200
    assert "submitted" in resp.json()["message"].lower()


def test_report_own_story(client, db, test_user, auth_headers):
    story = _create_public_story(db, test_user)

    resp = client.post(f"/api/reports/stories/{story.id}", json={
        "reason": "This story is bad and I wrote it",
    }, headers=auth_headers)
    assert resp.status_code == 400
    assert "own story" in resp.json()["detail"].lower()


def test_report_reason_too_short(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user)

    resp = client.post(f"/api/reports/stories/{story.id}", json={
        "reason": "bad",
    }, headers=other_auth_headers)
    assert resp.status_code == 400
    assert "10 characters" in resp.json()["detail"]


def test_report_already_reported(client, db, test_user, other_user, other_auth_headers):
    story = _create_public_story(db, test_user)

    # First report
    client.post(f"/api/reports/stories/{story.id}", json={
        "reason": "Inappropriate content for children",
    }, headers=other_auth_headers)

    # Second report by same user
    resp = client.post(f"/api/reports/stories/{story.id}", json={
        "reason": "Still inappropriate content for children",
    }, headers=other_auth_headers)
    assert resp.status_code == 400
    assert "already reported" in resp.json()["detail"].lower()


def test_report_private_story(client, db, test_user, other_user, other_auth_headers):
    story = Story(
        user_id=test_user.id,
        title="Private Story",
        status="completed",
        visibility="private",
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    resp = client.post(f"/api/reports/stories/{story.id}", json={
        "reason": "This story should not be visible",
    }, headers=other_auth_headers)
    assert resp.status_code == 404
