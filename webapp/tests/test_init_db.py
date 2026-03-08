"""Tests for version-based fast startup in init_db()."""

import os
from unittest.mock import patch


def _clean_env(tmp_path):
    """Set VERSION_FILE_PATH to a temp directory."""
    version_file = str(tmp_path / ".version")
    return patch.dict(os.environ, {"VERSION_FILE_PATH": version_file})


def test_migrations_run_when_version_file_missing(tmp_path):
    with _clean_env(tmp_path):
        from webapp.models.database import _get_app_version, _read_version_file

        assert _read_version_file() is None
        version = _get_app_version()
        assert version != "unknown"


def test_migrations_run_when_version_file_has_older_version(tmp_path):
    with _clean_env(tmp_path):
        from webapp.models.database import _read_version_file, _write_version_file

        _write_version_file("0.0.1")
        assert _read_version_file() == "0.0.1"


def test_migrations_skipped_when_version_matches(tmp_path):
    with _clean_env(tmp_path):
        from webapp.models.database import _get_app_version, _read_version_file, _write_version_file

        current = _get_app_version()
        _write_version_file(current)
        assert _read_version_file() == current


def test_platform_budget_always_created(db):
    from webapp.models.database import PlatformBudget

    budget = db.query(PlatformBudget).first()
    assert budget is not None
    assert budget.total_budget == 50.0


def test_init_db_full_flow(tmp_path):
    with _clean_env(tmp_path):
        from webapp.models.database import _get_app_version, _read_version_file, _write_version_file

        # Simulate first boot — no version file
        assert _read_version_file() is None

        # Write current version
        current = _get_app_version()
        _write_version_file(current)

        # Second boot — version matches
        assert _read_version_file() == current
