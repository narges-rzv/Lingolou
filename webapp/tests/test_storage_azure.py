"""Tests for AzureBlobStorageBackend."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def mock_azure():
    """Patch Azure SDK classes and return mock instances."""
    with (
        patch("azure.identity.DefaultAzureCredential") as mock_cred_cls,
        patch("azure.storage.blob.BlobServiceClient") as mock_svc_cls,
    ):
        mock_cred = MagicMock()
        mock_cred_cls.return_value = mock_cred

        mock_service = MagicMock()
        mock_service.account_name = "lingoloudisk"
        mock_svc_cls.return_value = mock_service

        mock_container = MagicMock()
        mock_service.get_container_client.return_value = mock_container

        yield {
            "credential": mock_cred,
            "service_client": mock_service,
            "container_client": mock_container,
        }


@pytest.fixture()
def backend(mock_azure):
    """Create an AzureBlobStorageBackend with mocked Azure SDK."""
    from webapp.services.storage import AzureBlobStorageBackend

    return AzureBlobStorageBackend()


def test_save(backend, mock_azure):
    mock_blob = MagicMock()
    mock_blob.url = "https://lingoloudisk.blob.core.windows.net/audio/story1/ch1.mp3"
    mock_azure["container_client"].get_blob_client.return_value = mock_blob

    # Mock get_url dependencies
    delegation_key = MagicMock()
    mock_azure["service_client"].get_user_delegation_key.return_value = delegation_key

    with patch("azure.storage.blob.generate_blob_sas", return_value="sig=abc"):
        url = backend.save("story1/ch1.mp3", b"audio-data")

    mock_blob.upload_blob.assert_called_once()
    assert "story1/ch1.mp3" in mock_azure["container_client"].get_blob_client.call_args[0]
    assert "sig=abc" in url


def test_delete(backend, mock_azure):
    mock_blob = MagicMock()
    mock_azure["container_client"].get_blob_client.return_value = mock_blob

    backend.delete("story1/ch1.mp3")

    mock_blob.delete_blob.assert_called_once()


def test_delete_dir(backend, mock_azure):
    blob1 = MagicMock()
    blob1.name = "story1/ch1.mp3"
    blob2 = MagicMock()
    blob2.name = "story1/ch2.mp3"
    mock_azure["container_client"].list_blobs.return_value = [blob1, blob2]

    backend.delete_dir("story1/")

    assert mock_azure["container_client"].delete_blob.call_count == 2


def test_get_path(backend, mock_azure):
    mock_blob = MagicMock()
    mock_azure["container_client"].get_blob_client.return_value = mock_blob

    mock_stream = MagicMock()
    mock_blob.download_blob.return_value = mock_stream

    with backend.get_path("story1/ch1.mp3") as path:
        assert path is not None
        assert isinstance(path, Path)
        assert path.name == "ch1.mp3"


def test_get_path_missing_blob(backend, mock_azure):
    mock_blob = MagicMock()
    mock_azure["container_client"].get_blob_client.return_value = mock_blob
    mock_blob.download_blob.side_effect = Exception("BlobNotFound")

    with backend.get_path("nonexistent.mp3") as path:
        assert path is None


def test_get_url(backend, mock_azure):
    mock_blob = MagicMock()
    mock_blob.url = "https://lingoloudisk.blob.core.windows.net/audio/story1/ch1.mp3"
    mock_azure["container_client"].get_blob_client.return_value = mock_blob

    delegation_key = MagicMock()
    mock_azure["service_client"].get_user_delegation_key.return_value = delegation_key

    with patch("azure.storage.blob.generate_blob_sas", return_value="sig=xyz123"):
        url = backend.get_url("story1/ch1.mp3")

    assert url == "https://lingoloudisk.blob.core.windows.net/audio/story1/ch1.mp3?sig=xyz123"


def test_get_storage_factory_azure_blob(mock_azure):
    from webapp.services import storage

    # Reset singleton
    storage._storage = None

    with patch.dict("os.environ", {"STORAGE_BACKEND": "azure_blob"}):
        result = storage.get_storage()

    assert isinstance(result, storage.AzureBlobStorageBackend)

    # Clean up singleton
    storage._storage = None
