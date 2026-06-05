"""Server-rendered Open Graph / Twitter Card meta tags for the SPA shell.

Social crawlers (iMessage, WhatsApp, Slack, Discord, X, Facebook, Reddit, ...) do not
execute JavaScript, so a single-page app serves them an empty shell and links unfurl
blank. This module resolves a requested path to a story and injects the right
``<meta>`` tags into ``index.html`` before it is returned.
"""

from __future__ import annotations

import html
import os

from sqlalchemy.orm import Session
from starlette.requests import Request

from webapp.models.database import Story

# Visibility levels whose share cards are safe to expose to anonymous crawlers.
_SHAREABLE = ("public", "link_only")

_SITE_NAME = "Lingolou"
_DEFAULT_TITLE = "Lingolou — AI language-learning audiobooks"
_DEFAULT_DESCRIPTION = (
    "Create and listen to children's stories with multilingual dialogue. "
    "Learn 35+ languages with free, AI-generated audiobooks."
)


def get_base_url(request: Request) -> str:
    """Resolve the public base URL for absolute og: URLs.

    Prefers ``PUBLIC_BASE_URL`` / ``FRONTEND_URL`` (stable behind a proxy), falling
    back to the request's own base URL for local/dev use.
    """
    configured = os.getenv("PUBLIC_BASE_URL") or os.getenv("FRONTEND_URL")
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")


def _og_image_url(base_url: str, story: Story) -> str:
    return f"{base_url}/api/public/stories/{story.slug}/og-image.png"


def _story_meta(story: Story, base_url: str, canonical_path: str) -> dict[str, str]:
    """Build the meta dict for a single story."""
    description: str
    if story.description:
        description = str(story.description)
    elif story.language:
        description = f"A {story.language} language-learning audiobook on Lingolou. Listen free."
    else:
        description = _DEFAULT_DESCRIPTION
    return {
        "title": f"{story.title} · Lingolou",
        "description": description,
        "image": _og_image_url(base_url, story),
        "url": f"{base_url}/{canonical_path.lstrip('/')}",
        "type": "article",
    }


def _default_meta(base_url: str) -> dict[str, str]:
    return {
        "title": _DEFAULT_TITLE,
        "description": _DEFAULT_DESCRIPTION,
        "image": f"{base_url}/api/public/og-image.png",
        "url": base_url,
        "type": "website",
    }


def resolve_meta(db: Session, full_path: str, base_url: str) -> dict[str, str]:
    """Resolve a request path to the meta dict for that resource.

    Falls back to the default brand meta for unknown or non-shareable paths.
    """
    segments = [s for s in full_path.strip("/").split("/") if s]

    story: Story | None = None
    if len(segments) == 2 and segments[0] == "share":
        story = db.query(Story).filter(Story.share_code == segments[1], Story.visibility.in_(_SHAREABLE)).first()
    elif len(segments) == 3 and segments[0] == "public" and segments[1] == "stories":
        story = (
            db.query(Story)
            .filter(
                (Story.slug == segments[2]) | (Story.public_id == segments[2]),
                Story.visibility.in_(_SHAREABLE),
            )
            .first()
        )

    if story is not None:
        return _story_meta(story, base_url, full_path)
    return _default_meta(base_url)


def render_meta_tags(meta: dict[str, str]) -> str:
    """Render the meta dict into an HTML fragment (attribute-escaped)."""

    def esc(value: str) -> str:
        return html.escape(value, quote=True)

    title = esc(meta["title"])
    tags = [
        f"<title>{title}</title>",
        f'<meta name="description" content="{esc(meta["description"])}" />',
        f'<meta property="og:site_name" content="{_SITE_NAME}" />',
        f'<meta property="og:title" content="{title}" />',
        f'<meta property="og:description" content="{esc(meta["description"])}" />',
        f'<meta property="og:image" content="{esc(meta["image"])}" />',
        f'<meta property="og:url" content="{esc(meta["url"])}" />',
        f'<meta property="og:type" content="{esc(meta["type"])}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{title}" />',
        f'<meta name="twitter:description" content="{esc(meta["description"])}" />',
        f'<meta name="twitter:image" content="{esc(meta["image"])}" />',
    ]
    return "\n    ".join(tags)


def inject_meta(html_doc: str, meta: dict[str, str]) -> str:
    """Inject rendered meta tags into the HTML shell, replacing the static <title>."""
    tags = render_meta_tags(meta)
    # Drop the placeholder <title> from the static build so we don't duplicate it.
    import re

    html_doc = re.sub(r"<title>.*?</title>", "", html_doc, count=1, flags=re.IGNORECASE | re.DOTALL)
    if "</head>" in html_doc:
        return html_doc.replace("</head>", f"    {tags}\n  </head>", 1)
    # No head (shouldn't happen) — prepend.
    return tags + html_doc
