"""File storage abstraction for audio files.

Supports local filesystem (default) and S3-compatible object storage.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for file storage backends."""

    def save(self, key: str, data: bytes) -> str:
        """Save data and return the URL/path for the stored file."""
        ...

    def delete(self, key: str) -> None:
        """Delete a single file by key."""
        ...

    def delete_dir(self, prefix: str) -> None:
        """Delete all files under a prefix/directory."""
        ...

    @contextmanager
    def get_path(self, key: str) -> Iterator[Path | None]:
        """Yield a local file path for reading.

        For local storage, yields the path directly.
        For S3 storage, downloads to a temp file and cleans up on exit.
        Yields None if the file does not exist.
        """
        ...

    def get_url(self, key: str) -> str:
        """Return a URL/path suitable for serving to the frontend."""
        ...


class LocalStorageBackend:
    """Store files on the local filesystem under webapp/static/audio/."""

    def __init__(self) -> None:
        """Initialize local storage with the audio directory."""
        self._base_dir = Path(__file__).parent.parent / "static" / "audio"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: bytes) -> str:
        """Save data to local filesystem and return the static URL path."""
        file_path = self._base_dir / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return f"/static/audio/{key}"

    def delete(self, key: str) -> None:
        """Delete a single file from local filesystem."""
        file_path = self._base_dir / key
        if file_path.exists():
            file_path.unlink()

    def delete_dir(self, prefix: str) -> None:
        """Delete a directory and all its contents."""
        dir_path = self._base_dir / prefix
        if dir_path.exists():
            shutil.rmtree(dir_path, ignore_errors=True)

    @contextmanager
    def get_path(self, key: str) -> Iterator[Path | None]:
        """Yield the local file path directly."""
        file_path = self._base_dir / key
        yield file_path if file_path.exists() else None

    def get_url(self, key: str) -> str:
        """Return the static URL path."""
        return f"/static/audio/{key}"


class S3StorageBackend:
    """Store files in an S3-compatible bucket (AWS S3, R2, MinIO, etc.)."""

    def __init__(self) -> None:
        """Initialize S3 client from environment variables."""
        import boto3

        self._bucket = os.environ["S3_BUCKET"]
        self._prefix = os.getenv("S3_PREFIX", "audio")

        region = os.getenv("S3_REGION", "us-east-1")
        endpoint_url = os.getenv("S3_ENDPOINT_URL")
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,  # None is fine — boto3 ignores it
        )

    def _s3_key(self, key: str) -> str:
        return f"{self._prefix}/{key}"

    def save(self, key: str, data: bytes) -> str:
        """Upload data to S3 and return the object URL."""
        s3_key = self._s3_key(key)
        self._client.put_object(
            Bucket=self._bucket,
            Key=s3_key,
            Body=data,
            ContentType="audio/mpeg",
        )
        return self.get_url(key)

    def delete(self, key: str) -> None:
        """Delete a single object from S3."""
        self._client.delete_object(Bucket=self._bucket, Key=self._s3_key(key))

    def delete_dir(self, prefix: str) -> None:
        """Delete all objects under a prefix."""
        s3_prefix = self._s3_key(prefix)
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=s3_prefix):
            objects = page.get("Contents", [])
            if objects:
                self._client.delete_objects(
                    Bucket=self._bucket,
                    Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
                )

    @contextmanager
    def get_path(self, key: str) -> Iterator[Path | None]:
        """Download S3 object to a temp file and yield its path."""
        s3_key = self._s3_key(key)
        tmp_dir = tempfile.mkdtemp()
        tmp_path = Path(tmp_dir) / Path(key).name
        try:
            self._client.download_file(self._bucket, s3_key, str(tmp_path))
            yield tmp_path
        except self._client.exceptions.ClientError:
            yield None
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def get_url(self, key: str) -> str:
        """Return a presigned URL for the object."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": self._s3_key(key)},
            ExpiresIn=3600,
        )


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Return the configured storage backend (singleton)."""
    global _storage  # noqa: PLW0603 — module-level singleton
    if _storage is None:
        backend = os.getenv("STORAGE_BACKEND", "local").lower()
        if backend == "s3":
            _storage = S3StorageBackend()
            logger.info("Using S3 storage backend (bucket=%s)", os.getenv("S3_BUCKET"))
        else:
            _storage = LocalStorageBackend()
            logger.info("Using local storage backend")
    return _storage
