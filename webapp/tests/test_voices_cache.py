"""Tests for the ElevenLabs voices cache."""

import os
from unittest.mock import MagicMock, patch

import pytest

from webapp.services.voices_cache import get_voices, reset_cache, warm_cache

FAKE_VOICES_RESPONSE = {
    "voices": [
        {
            "voice_id": "abc123",
            "name": "Test Voice",
            "category": "premade",
            "labels": {"accent": "american"},
            "preview_url": "https://example.com/preview.mp3",
        },
        {
            "voice_id": "def456",
            "name": "Another Voice",
            "category": "cloned",
            "labels": {},
            "preview_url": "",
        },
    ]
}


@pytest.fixture(autouse=True)
def _reset():
    reset_cache()
    yield
    reset_cache()


@pytest.fixture()
def _set_api_key():
    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
        yield


def _mock_response(status_code=200, json_data=None):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or FAKE_VOICES_RESPONSE
    return mock


@pytest.mark.usefixtures("_set_api_key")
def test_warm_cache_populates_cache():
    with patch("webapp.services.voices_cache.http_requests.get", return_value=_mock_response()):
        warm_cache()
        voices = get_voices()
    assert len(voices) == 2
    assert voices[0]["voice_id"] == "abc123"
    assert voices[1]["name"] == "Another Voice"


@pytest.mark.usefixtures("_set_api_key")
def test_cached_data_returned_on_second_call():
    mock_get = MagicMock(return_value=_mock_response())
    with patch("webapp.services.voices_cache.http_requests.get", mock_get):
        warm_cache()
        first = get_voices()
        second = get_voices()

    # warm_cache calls fetch once; get_voices may trigger background refresh
    # but returns cached data immediately
    assert first == second
    assert mock_get.call_count == 1  # Only warm_cache fetched


@pytest.mark.usefixtures("_set_api_key")
def test_graceful_degradation_on_elevenlabs_error():
    with patch("webapp.services.voices_cache.http_requests.get", return_value=_mock_response(status_code=500)):
        warm_cache()
        voices = get_voices()
    assert voices == []


@pytest.mark.usefixtures("_set_api_key")
def test_empty_list_on_cold_call_when_elevenlabs_down():
    with patch("webapp.services.voices_cache.http_requests.get", return_value=_mock_response(status_code=502)):
        voices = get_voices()
    assert voices == []


def test_no_api_key_returns_empty():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ELEVENLABS_API_KEY", None)
        warm_cache()
        voices = get_voices()
    assert voices == []
