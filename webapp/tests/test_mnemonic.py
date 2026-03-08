"""Tests for mnemonic slug encoding/decoding."""

import json
from pathlib import Path

from webapp.services.mnemonic import decode_slug, encode, generate


def test_word_lists_have_256_entries():
    path = Path(__file__).resolve().parent.parent / "services" / "mnemonic_words.json"
    with open(path) as f:
        data = json.load(f)
    for key in ["adjectives", "nouns_1", "verbs", "prepositions", "nouns_2"]:
        assert len(data[key]) == 256, f"{key} has {len(data[key])} entries, expected 256"


def test_word_lists_no_duplicates():
    path = Path(__file__).resolve().parent.parent / "services" / "mnemonic_words.json"
    with open(path) as f:
        data = json.load(f)
    for key in ["adjectives", "nouns_1", "verbs", "prepositions", "nouns_2"]:
        assert len(data[key]) == len(set(data[key])), f"Duplicates found in {key}"


def test_word_lists_lowercase_alpha():
    path = Path(__file__).resolve().parent.parent / "services" / "mnemonic_words.json"
    with open(path) as f:
        data = json.load(f)
    for key in ["adjectives", "nouns_1", "verbs", "prepositions", "nouns_2"]:
        for word in data[key]:
            assert word.isalpha() and word.islower(), f"Invalid word '{word}' in {key}"


def test_encode_produces_five_words():
    _, slug = generate()
    parts = slug.split("-")
    assert len(parts) == 5


def test_encode_is_deterministic():
    uuid_str, slug = generate()
    assert encode(uuid_str) == slug
    assert encode(uuid_str) == slug


def test_different_uuids_produce_different_slugs():
    slugs = set()
    for _ in range(1000):
        _, slug = generate()
        slugs.add(slug)
    assert len(slugs) == 1000


def test_decode_valid_slug():
    _, slug = generate()
    result = decode_slug(slug)
    assert result is not None
    assert len(result) == 5
    assert all(0 <= b <= 255 for b in result)


def test_decode_invalid_slug_wrong_count():
    assert decode_slug("foo-bar") is None
    assert decode_slug("a-b-c-d") is None
    assert decode_slug("a-b-c-d-e-f") is None


def test_decode_invalid_slug_unknown_word():
    assert decode_slug("xyzzy-plugh-quux-bloop-flarp") is None


def test_generate_returns_uuid_and_slug():
    uuid_str, slug = generate()
    assert len(uuid_str) == 36
    assert "-" in slug
    parts = slug.split("-")
    assert len(parts) == 5
