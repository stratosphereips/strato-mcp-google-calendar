"""Tests for OAuth flow."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from google_calendar_mcp.auth.oauth import (
    CalendarAuthError,
    _credentials_from_dict,
    _credentials_to_dict,
    get_credentials,
)
from google_calendar_mcp.auth.token_store import FileTokenStore


@pytest.fixture()
def mock_valid_creds():
    creds = MagicMock(spec=Credentials)
    creds.valid = True
    creds.expired = False
    creds.refresh_token = "refresh123"
    creds.token = "access123"
    creds.token_uri = "https://oauth2.googleapis.com/token"
    creds.client_id = "client-id"
    creds.client_secret = "client-secret"
    creds.scopes = ["https://www.googleapis.com/auth/calendar"]
    return creds


@pytest.fixture()
def mock_expired_creds():
    creds = MagicMock(spec=Credentials)
    creds.valid = False
    creds.expired = True
    creds.refresh_token = "refresh123"
    creds.token = "old-access"
    creds.token_uri = "https://oauth2.googleapis.com/token"
    creds.client_id = "client-id"
    creds.client_secret = "client-secret"
    creds.scopes = ["https://www.googleapis.com/auth/calendar"]
    return creds


class TestCredentialsSerialization:
    def test_round_trip(self, mock_valid_creds):
        data = _credentials_to_dict(mock_valid_creds)
        assert data["token"] == "access123"
        assert data["refresh_token"] == "refresh123"

    def test_client_secret_not_persisted(self, mock_valid_creds):
        data = _credentials_to_dict(mock_valid_creds)
        assert "client_secret" not in data

    def test_from_dict_sets_fields(self, valid_config):
        data = {
            "token": "tok",
            "refresh_token": "ref",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
        }
        creds = _credentials_from_dict(data, valid_config)
        assert creds.token == "tok"
        assert creds.refresh_token == "ref"

    def test_from_dict_injects_client_secret_from_config(self, valid_config):
        data = {
            "token": "tok",
            "refresh_token": "ref",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
        }
        creds = _credentials_from_dict(data, valid_config)
        assert creds.client_secret == valid_config.client_secret


class TestGetCredentials:
    def test_returns_cached_valid_credentials(
        self, valid_config, tmp_token_store, sample_token_data
    ):
        tmp_token_store.save("default", sample_token_data)
        with patch(
            "google_calendar_mcp.auth.oauth._credentials_from_dict"
        ) as mock_from_dict:
            mock_creds = MagicMock(spec=Credentials)
            mock_creds.valid = True
            mock_from_dict.return_value = mock_creds

            result = get_credentials("default", valid_config, tmp_token_store)

        assert result is mock_creds

    def test_refreshes_expired_credentials(
        self, valid_config, tmp_token_store, sample_token_data
    ):
        tmp_token_store.save("default", sample_token_data)
        with patch(
            "google_calendar_mcp.auth.oauth._credentials_from_dict"
        ) as mock_from_dict, patch(
            "google_calendar_mcp.auth.oauth._credentials_to_dict"
        ) as mock_to_dict:
            mock_creds = MagicMock(spec=Credentials)
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = "refresh123"
            mock_from_dict.return_value = mock_creds
            mock_to_dict.return_value = sample_token_data

            result = get_credentials("default", valid_config, tmp_token_store)

        mock_creds.refresh.assert_called_once()
        assert result is mock_creds

    def test_runs_browser_flow_when_no_token(self, valid_config, tmp_token_store):
        with patch(
            "google_calendar_mcp.auth.oauth.InstalledAppFlow"
        ) as mock_flow_cls:
            mock_flow = MagicMock()
            mock_creds = MagicMock(spec=Credentials)
            mock_creds.valid = True
            mock_flow.run_local_server.return_value = mock_creds
            mock_flow_cls.from_client_config.return_value = mock_flow

            with patch(
                "google_calendar_mcp.auth.oauth._credentials_to_dict",
                return_value={},
            ):
                result = get_credentials("default", valid_config, tmp_token_store)

        mock_flow.run_local_server.assert_called_once()
        assert result is mock_creds

    def test_raises_auth_error_when_browser_flow_fails(
        self, valid_config, tmp_token_store
    ):
        with patch(
            "google_calendar_mcp.auth.oauth.InstalledAppFlow"
        ) as mock_flow_cls:
            mock_flow_cls.from_client_config.side_effect = Exception("network error")

            with pytest.raises(CalendarAuthError):
                get_credentials("default", valid_config, tmp_token_store)

    def test_falls_back_to_browser_flow_when_refresh_fails(
        self, valid_config, tmp_token_store, sample_token_data
    ):
        tmp_token_store.save("default", sample_token_data)
        with patch(
            "google_calendar_mcp.auth.oauth._credentials_from_dict"
        ) as mock_from_dict, patch(
            "google_calendar_mcp.auth.oauth.InstalledAppFlow"
        ) as mock_flow_cls:
            mock_creds = MagicMock(spec=Credentials)
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = "bad-token"
            mock_creds.refresh.side_effect = RefreshError("token revoked")
            mock_from_dict.return_value = mock_creds

            mock_flow = MagicMock()
            new_creds = MagicMock(spec=Credentials)
            new_creds.valid = True
            mock_flow.run_local_server.return_value = new_creds
            mock_flow_cls.from_client_config.return_value = mock_flow

            with patch(
                "google_calendar_mcp.auth.oauth._credentials_to_dict",
                return_value={},
            ):
                result = get_credentials("default", valid_config, tmp_token_store)

        assert result is new_creds
