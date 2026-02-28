"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from google_calendar_mcp.auth.token_store import FileTokenStore
from google_calendar_mcp.config import Config


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def valid_config() -> Config:
    return Config(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:8081",
        token_store_path=Path("/tmp/test-tokens"),
        scopes=["https://www.googleapis.com/auth/calendar"],
        default_calendar_id="primary",
    )


# ---------------------------------------------------------------------------
# Token store fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_token_store(tmp_path: Path) -> FileTokenStore:
    return FileTokenStore(tmp_path / "tokens")


@pytest.fixture()
def sample_token_data() -> dict[str, Any]:
    return {
        "token": "ya29.test_access_token",
        "refresh_token": "1//test_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "scopes": ["https://www.googleapis.com/auth/calendar"],
    }


# ---------------------------------------------------------------------------
# Mock Google API client
# ---------------------------------------------------------------------------


def _make_execute(return_value: Any):
    mock = MagicMock()
    mock.execute.return_value = return_value
    return mock


@pytest.fixture()
def mock_client() -> MagicMock:
    """Return a MagicMock that mimics the googleapiclient Resource chain."""
    client = MagicMock()

    # Default empty responses
    client.events().list.return_value = _make_execute({"items": []})
    client.events().get.return_value = _make_execute({})
    client.events().insert.return_value = _make_execute({})
    client.events().patch.return_value = _make_execute({})
    client.events().delete.return_value = _make_execute(None)
    client.calendarList().list.return_value = _make_execute({"items": []})
    client.calendarList().get.return_value = _make_execute({})
    client.freebusy().query.return_value = _make_execute({"calendars": {}})

    return client
