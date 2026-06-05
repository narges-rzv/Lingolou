"""Tests for social share cards and Open Graph meta injection.

Covers webapp/services/social_image.py, webapp/services/social_meta.py, the
/api/public/*/og-image.png endpoints, and the meta tags injected into the SPA shell
by webapp/main.py.
"""

from webapp.models.database import Story
from webapp.services import social_meta
from webapp.services.mnemonic import generate as generate_mnemonic
from webapp.services.social_image import render_default_card, render_story_card

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _make_story(db, user, *, title="Dragon Tale", visibility="public", language="Spanish"):
    pid, slug = generate_mnemonic()
    story = Story(
        user_id=user.id,
        public_id=pid,
        slug=slug,
        title=title,
        description="A cozy bedtime adventure",
        status="completed",
        visibility=visibility,
        language=language,
        language_level=4,
        share_code=f"code-{slug}",
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


# --- image renderer (unit) ---------------------------------------------------


def test_render_story_card_returns_png():
    data = render_story_card("A Very Long Title That Should Wrap Across Several Lines Nicely", "Persian (Farsi)", 7)
    assert data.startswith(PNG_MAGIC)
    assert len(data) > 1000


def test_render_default_card_returns_png():
    assert render_default_card().startswith(PNG_MAGIC)


def test_render_story_card_handles_missing_language():
    assert render_story_card("Title", None, None).startswith(PNG_MAGIC)


# --- og-image endpoints ------------------------------------------------------


def test_default_og_image_endpoint(client):
    resp = client.get("/api/public/og-image.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(PNG_MAGIC)
    assert "max-age" in resp.headers.get("cache-control", "")


def test_story_og_image_public(client, db, test_user):
    story = _make_story(db, test_user)
    resp = client.get(f"/api/public/stories/{story.slug}/og-image.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(PNG_MAGIC)


def test_story_og_image_private_is_404(client, db, test_user):
    story = _make_story(db, test_user, visibility="private")
    resp = client.get(f"/api/public/stories/{story.slug}/og-image.png")
    assert resp.status_code == 404


def test_story_og_image_unknown_is_404(client):
    resp = client.get("/api/public/stories/does-not-exist/og-image.png")
    assert resp.status_code == 404


# --- meta resolution (unit) --------------------------------------------------


def test_resolve_meta_for_public_story(db, test_user):
    story = _make_story(db, test_user, title="Quest")
    meta = social_meta.resolve_meta(db, f"public/stories/{story.slug}", "https://x.test")
    assert meta["title"] == "Quest · Lingolou"
    assert meta["image"] == f"https://x.test/api/public/stories/{story.slug}/og-image.png"
    assert meta["type"] == "article"


def test_resolve_meta_for_share_code(db, test_user):
    story = _make_story(db, test_user, title="Quest")
    meta = social_meta.resolve_meta(db, f"share/{story.share_code}", "https://x.test")
    assert meta["title"] == "Quest · Lingolou"


def test_resolve_meta_unknown_path_is_default(db):
    meta = social_meta.resolve_meta(db, "dashboard", "https://x.test")
    assert meta["title"] == social_meta._DEFAULT_TITLE
    assert meta["type"] == "website"


def test_resolve_meta_private_story_is_default(db, test_user):
    story = _make_story(db, test_user, visibility="private")
    meta = social_meta.resolve_meta(db, f"share/{story.share_code}", "https://x.test")
    assert meta["title"] == social_meta._DEFAULT_TITLE


def test_render_meta_tags_escapes_html():
    meta = {
        "title": 'Bad <b>"title"</b>',
        "description": "desc & more",
        "image": "https://x.test/i.png",
        "url": "https://x.test",
        "type": "article",
    }
    rendered = social_meta.render_meta_tags(meta)
    assert "<b>" not in rendered
    assert "&lt;b&gt;" in rendered
    assert "&amp;" in rendered


# --- SPA shell injection (integration) ---------------------------------------


def test_share_page_injects_story_meta(client, db, test_user):
    story = _make_story(db, test_user, title="The Brave Little Fox")
    resp = client.get(f"/share/{story.share_code}")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "The Brave Little Fox · Lingolou" in body
    assert 'property="og:image"' in body
    assert f"/api/public/stories/{story.slug}/og-image.png" in body
    assert 'name="twitter:card" content="summary_large_image"' in body
    # The static placeholder title must not survive alongside the injected one.
    assert body.count("<title>") == 1


def test_public_story_page_injects_story_meta(client, db, test_user):
    story = _make_story(db, test_user, title="Midnight Owl")
    resp = client.get(f"/public/stories/{story.slug}")
    assert resp.status_code == 200
    assert "Midnight Owl · Lingolou" in resp.text


def test_unknown_page_injects_default_meta(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert social_meta._DEFAULT_TITLE in resp.text
    assert "/api/public/og-image.png" in resp.text


def test_root_injects_default_meta(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert social_meta._DEFAULT_TITLE in resp.text
