"""Tests for free/busy API wrapper."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from google_calendar_mcp.calendar.events import CalendarApiError
from google_calendar_mcp.calendar.freebusy import check_free_busy


def _http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.reason = "error"
    return HttpError(resp=resp, content=b"error")


class TestCheckFreeBusy:
    def test_returns_freebusy_response(self, mock_client):
        fb_data = {
            "calendars": {
                "primary": {
                    "busy": [
                        {"start": "2024-01-15T10:00:00Z", "end": "2024-01-15T11:00:00Z"}
                    ]
                }
            }
        }
        mock_client.freebusy().query.return_value.execute.return_value = fb_data
        result = check_free_busy(
            mock_client,
            calendar_ids=["primary"],
            time_min="2024-01-15T09:00:00Z",
            time_max="2024-01-15T17:00:00Z",
        )
        assert result == fb_data

    def test_passes_correct_body(self, mock_client):
        mock_client.freebusy().query.return_value.execute.return_value = {
            "calendars": {}
        }
        check_free_busy(
            mock_client,
            calendar_ids=["primary", "work@example.com"],
            time_min="2024-01-15T09:00:00Z",
            time_max="2024-01-15T17:00:00Z",
            timezone="America/New_York",
        )
        body = mock_client.freebusy().query.call_args.kwargs["body"]
        assert body["timeMin"] == "2024-01-15T09:00:00Z"
        assert body["timeMax"] == "2024-01-15T17:00:00Z"
        assert body["timeZone"] == "America/New_York"
        assert {"id": "primary"} in body["items"]
        assert {"id": "work@example.com"} in body["items"]

    def test_raises_on_http_error(self, mock_client):
        mock_client.freebusy().query.return_value.execute.side_effect = _http_error(403)
        with pytest.raises(CalendarApiError):
            check_free_busy(
                mock_client,
                calendar_ids=["primary"],
                time_min="2024-01-15T09:00:00Z",
                time_max="2024-01-15T17:00:00Z",
            )
