"""Tests for config loading and token store."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from google_calendar_mcp.auth.token_store import FileTokenStore
from google_calendar_mcp.config import Config, ConfigurationError, load_config


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_raises_when_client_id_missing(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
        with pytest.raises(ConfigurationError, match="GOOGLE_CLIENT_ID"):
            load_config()

    def test_raises_when_client_secret_missing(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "some-id")
        monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
        with pytest.raises(ConfigurationError, match="GOOGLE_CLIENT_SECRET"):
            load_config()

    def test_returns_config_with_defaults(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "id123")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret456")
        monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
        monkeypatch.delenv("TOKEN_STORE_PATH", raising=False)
        monkeypatch.delenv("GOOGLE_SCOPES", raising=False)
        monkeypatch.delenv("DEFAULT_CALENDAR_ID", raising=False)

        config = load_config()

        assert config.client_id == "id123"
        assert config.client_secret == "secret456"
        assert config.redirect_uri == "http://localhost:8081"
        assert config.default_calendar_id == "primary"
        assert "https://www.googleapis.com/auth/calendar" in config.scopes

    def test_custom_values_are_applied(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "custom-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "custom-secret")
        monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:9090")
        monkeypatch.setenv("DEFAULT_CALENDAR_ID", "work@example.com")
        monkeypatch.setenv(
            "GOOGLE_SCOPES",
            "https://www.googleapis.com/auth/calendar.readonly",
        )

        config = load_config()

        assert config.redirect_uri == "http://localhost:9090"
        assert config.default_calendar_id == "work@example.com"
        assert config.scopes == ["https://www.googleapis.com/auth/calendar.readonly"]


class TestConfig:
    def test_scopes_string_normalised_to_list(self):
        config = Config(
            client_id="x",
            client_secret="y",
            scopes="https://www.googleapis.com/auth/calendar",  # type: ignore[arg-type]
        )
        assert isinstance(config.scopes, list)

    def test_token_store_path_string_expanded(self):
        config = Config(
            client_id="x",
            client_secret="y",
            token_store_path="~/.config/test",  # type: ignore[arg-type]
        )
        assert isinstance(config.token_store_path, Path)
        assert not str(config.token_store_path).startswith("~")


# ---------------------------------------------------------------------------
# FileTokenStore tests
# ---------------------------------------------------------------------------


class TestFileTokenStore:
    def test_load_returns_none_when_no_file(self, tmp_token_store):
        assert tmp_token_store.load("default") is None

    def test_save_and_load_round_trip(self, tmp_token_store, sample_token_data):
        tmp_token_store.save("default", sample_token_data)
        loaded = tmp_token_store.load("default")
        assert loaded == sample_token_data

    def test_save_creates_parent_dirs(self, tmp_path):
        store = FileTokenStore(tmp_path / "deep" / "nested" / "tokens")
        store.save("user1", {"token": "abc"})
        assert (tmp_path / "deep" / "nested" / "tokens" / "user1.token.json").exists()

    def test_file_has_restricted_permissions(self, tmp_token_store, sample_token_data):
        tmp_token_store.save("default", sample_token_data)
        path = tmp_token_store._token_path("default")
        mode = path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_atomic_write_leaves_no_tmp_file(self, tmp_token_store, sample_token_data):
        tmp_token_store.save("default", sample_token_data)
        path = tmp_token_store._token_path("default")
        tmp_path = path.with_suffix(".tmp")
        assert path.exists()
        assert not tmp_path.exists()

    def test_multiple_users_have_separate_files(self, tmp_token_store):
        tmp_token_store.save("alice", {"token": "alice-token"})
        tmp_token_store.save("bob", {"token": "bob-token"})
        assert tmp_token_store.load("alice") == {"token": "alice-token"}
        assert tmp_token_store.load("bob") == {"token": "bob-token"}

    def test_delete_removes_file(self, tmp_token_store, sample_token_data):
        tmp_token_store.save("default", sample_token_data)
        tmp_token_store.delete("default")
        assert tmp_token_store.load("default") is None

    def test_delete_nonexistent_is_silent(self, tmp_token_store):
        tmp_token_store.delete("nobody")  # should not raise

    def test_invalid_user_id_raises_on_empty_result(self, tmp_token_store):
        # A user_id composed entirely of disallowed chars sanitizes to empty -> ValueError
        with pytest.raises(ValueError):
            tmp_token_store.load("///...")

    def test_path_traversal_is_sanitized(self, tmp_token_store):
        # Path traversal chars are stripped; the resolved path stays within the store dir
        path = tmp_token_store._token_path("../../etc/passwd")
        assert tmp_token_store._store_dir in path.parents or path.parent == tmp_token_store._store_dir

    def test_load_returns_none_on_corrupt_json(self, tmp_token_store):
        path = tmp_token_store._store_dir / "default.token.json"
        tmp_token_store._store_dir.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json")
        assert tmp_token_store.load("default") is None
