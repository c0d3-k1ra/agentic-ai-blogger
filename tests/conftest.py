"""Pytest configuration for LLM tests."""

import shutil
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def backup_env_file():
    """Backup .env file during test session to prevent pollution."""
    env_file = Path(".env")
    backup_file = Path(".env.test_backup")

    # Backup if exists
    if env_file.exists():
        shutil.copy(env_file, backup_file)
        env_file.unlink()

    yield

    # Restore
    if backup_file.exists():
        shutil.move(backup_file, env_file)
