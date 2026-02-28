"""Tests for calendar management API wrappers."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from google_calendar_mcp.calendar.calendars import get_calendar, list_calendars
from google_calendar_mcp.calendar.events import CalendarApiError


def _http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.reason = "error"
    return HttpError(resp=resp, content=b"error")


class TestListCalendars:
    def test_returns_calendars(self, mock_client):
        cal_data = [{"id": "primary", "summary": "My Calendar"}]
        mock_client.calendarList().list.return_value.execute.return_value = {
            "items": cal_data
        }
        result = list_calendars(mock_client)
        assert result == cal_data

    def test_returns_empty_list_when_none(self, mock_client):
        mock_client.calendarList().list.return_value.execute.return_value = {}
        result = list_calendars(mock_client)
        assert result == []

    def test_raises_on_http_error(self, mock_client):
        mock_client.calendarList().list.return_value.execute.side_effect = _http_error(403)
        with pytest.raises(CalendarApiError):
            list_calendars(mock_client)


class TestGetCalendar:
    def test_returns_calendar(self, mock_client):
        cal_data = {"id": "work@example.com", "summary": "Work"}
        mock_client.calendarList().get.return_value.execute.return_value = cal_data
        result = get_calendar(mock_client, "work@example.com")
        assert result == cal_data

    def test_raises_on_http_error(self, mock_client):
        mock_client.calendarList().get.return_value.execute.side_effect = _http_error(404)
        with pytest.raises(CalendarApiError):
            get_calendar(mock_client, "nonexistent")
