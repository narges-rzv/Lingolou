"""Render Open Graph share card images (1200x630 PNG) for stories.

Uses Pillow's scalable default font (``ImageFont.load_default(size=...)``, available
since Pillow 10.1) so rendering works identically on macOS dev and Linux containers
without depending on system font paths.
"""

from __future__ import annotations

import io
from typing import cast

from PIL import Image, ImageDraw, ImageFont

# Open Graph recommended dimensions for summary_large_image cards.
WIDTH = 1200
HEIGHT = 630
PADDING = 80

# Brand palette (matches the frontend theme in frontend/src/index.css).
_GRADIENT_TOP = (124, 110, 240)  # #7c6ef0
_GRADIENT_BOTTOM = (79, 70, 200)  # deeper purple
_ACCENT = (251, 191, 36)  # #fbbf24 (badge)
_ACCENT_TEXT = (40, 30, 5)
_WHITE = (255, 255, 255)
_MUTED = (224, 224, 232)  # #e0e0e8


def _font(size: int) -> ImageFont.FreeTypeFont:
    """Load the scalable default font at the given pixel size."""
    return cast("ImageFont.FreeTypeFont", ImageFont.load_default(size=size))


def _vertical_gradient(width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    """Build a top-to-bottom linear gradient background."""
    base = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(round(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    return base


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int) -> list[str]:
    """Greedily wrap ``text`` to fit ``max_width``, truncating with an ellipsis."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.getlength(candidate) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    # If we ran out of line budget, mark truncation on the last line.
    if len(lines) == max_lines and (len(" ".join(lines).split()) < len(words)):
        last = lines[-1]
        while last and font.getlength(last + "...") > max_width:
            last = last[:-1].rstrip()
        lines[-1] = last + "..."
    return lines


def _render(title: str, subtitle: str | None, badge: str | None) -> bytes:
    """Render a share card and return PNG bytes."""
    img = _vertical_gradient(WIDTH, HEIGHT, _GRADIENT_TOP, _GRADIENT_BOTTOM)
    draw = ImageDraw.Draw(img)

    # Wordmark (top-left).
    wordmark_font = _font(34)
    draw.text((PADDING, PADDING), "LINGOLOU", font=wordmark_font, fill=_MUTED)

    # Title block, vertically centred.
    title_font = _font(76)
    title_lines = _wrap(title or "Lingolou", title_font, WIDTH - 2 * PADDING, max_lines=3)
    line_height = round(title_font.size * 1.18)
    block_height = line_height * len(title_lines)
    y = (HEIGHT - block_height) // 2 - 20
    for line in title_lines:
        draw.text((PADDING, y), line, font=title_font, fill=_WHITE)
        y += line_height

    # Language badge pill below the title.
    if badge:
        badge_font = _font(34)
        text_w = badge_font.getlength(badge)
        pad_x, pad_y = 28, 16
        pill_h = badge_font.size + 2 * pad_y
        pill = (PADDING, y + 16, PADDING + text_w + 2 * pad_x, y + 16 + pill_h)
        draw.rounded_rectangle(pill, radius=pill_h // 2, fill=_ACCENT)
        draw.text((PADDING + pad_x, y + 16 + pad_y), badge, font=badge_font, fill=_ACCENT_TEXT)

    # CTA / subtitle along the bottom.
    cta_font = _font(32)
    cta = subtitle or "Listen free · lingolou.app"
    draw.text((PADDING, HEIGHT - PADDING - cta_font.size), cta, font=cta_font, fill=_MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_story_card(title: str, language: str | None, language_level: int | None = None) -> bytes:
    """Render the share card for a single story."""
    badge = None
    if language:
        badge = f"Learn {language}"
        if language_level:
            badge += f" · Level {language_level}"
    return _render(title=title, subtitle=None, badge=badge)


def render_default_card() -> bytes:
    """Render the generic brand share card (homepage / unknown resources)."""
    return _render(
        title="Lingolou",
        subtitle="AI language-learning audiobooks · lingolou.app",
        badge="Learn 35+ languages",
    )
