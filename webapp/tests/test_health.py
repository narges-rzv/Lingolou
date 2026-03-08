"""Tests for the /health endpoint with Redis status."""

from unittest.mock import MagicMock, patch

from webapp.services.task_store import InMemoryTaskBackend, RedisTaskBackend


def test_health_redis_not_configured(client):
    """When no REDIS_URL is set, health shows redis: not_configured."""
    with patch("webapp.services.task_store._backend", InMemoryTaskBackend()):
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["redis"] == "not_configured"
    assert data["status"] == "healthy"


def test_health_redis_connected(client):
    """When Redis is available, health shows redis: connected."""
    mock_backend = MagicMock(spec=RedisTaskBackend)
    mock_backend.ping.return_value = True
    with patch("webapp.services.task_store._backend", mock_backend):
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["redis"] == "connected"


def test_health_redis_error(client):
    """When Redis is unreachable, health shows redis: error (still 200)."""
    mock_backend = MagicMock(spec=RedisTaskBackend)
    mock_backend.ping.return_value = False
    with patch("webapp.services.task_store._backend", mock_backend):
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["redis"] == "error"
