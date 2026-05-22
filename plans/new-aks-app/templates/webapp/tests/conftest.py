"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from webapp.main import app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)
