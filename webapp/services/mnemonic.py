"""Mnemonic slug encoding for story IDs.

Encodes the first 5 bytes of a UUID4 into a human-readable 5-word slug
using the pattern: adjective-noun-verb-preposition-noun.
Each word list has 256 entries (8 bits per word, 40 bits total).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

_WORD_LISTS: dict[str, list[str]] | None = None
_LIST_KEYS = ("adjectives", "nouns_1", "verbs", "prepositions", "nouns_2")
_REVERSE_MAPS: list[dict[str, int]] | None = None


def _load_words() -> dict[str, list[str]]:
    """Load word lists from the bundled JSON file."""
    global _WORD_LISTS  # noqa: PLW0603 — module-level cache
    if _WORD_LISTS is None:
        path = Path(__file__).resolve().parent.parent.parent / "data" / "mnemonic_words.json"
        with open(path) as f:
            _WORD_LISTS = json.load(f)
        for key in _LIST_KEYS:
            if len(_WORD_LISTS[key]) != 256:
                msg = f"Word list '{key}' must have exactly 256 entries, got {len(_WORD_LISTS[key])}"
                raise ValueError(msg)
    return _WORD_LISTS


def _get_reverse_maps() -> list[dict[str, int]]:
    """Build reverse lookup maps (word -> index) for each list."""
    global _REVERSE_MAPS  # noqa: PLW0603 — module-level cache
    if _REVERSE_MAPS is None:
        words = _load_words()
        _REVERSE_MAPS = [{w: i for i, w in enumerate(words[key])} for key in _LIST_KEYS]
    return _REVERSE_MAPS


def encode(uuid_str: str) -> str:
    """Convert a UUID string to a 5-word mnemonic slug.

    Uses the first 5 bytes of the UUID to select one word from each list.
    """
    words = _load_words()
    uuid_bytes = uuid.UUID(uuid_str).bytes[:5]
    parts = [words[_LIST_KEYS[i]][b] for i, b in enumerate(uuid_bytes)]
    return "-".join(parts)


def generate() -> tuple[str, str]:
    """Generate a new UUID4 and its mnemonic slug.

    Returns:
        Tuple of (uuid_string, slug).
    """
    new_uuid = uuid.uuid4()
    uuid_str = str(new_uuid)
    slug = encode(uuid_str)
    return uuid_str, slug


def decode_slug(slug: str) -> list[int] | None:
    """Decode a mnemonic slug back to 5 byte values.

    Returns None if the slug is invalid (wrong format or unknown words).
    """
    parts = slug.split("-")
    if len(parts) != 5:
        return None

    reverse_maps = _get_reverse_maps()
    byte_values = []
    for i, word in enumerate(parts):
        idx = reverse_maps[i].get(word)
        if idx is None:
            return None
        byte_values.append(idx)
    return byte_values
