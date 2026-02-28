"""Tests for calendar events API wrappers."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from google_calendar_mcp.calendar.events import (
    CalendarApiError,
    create_event,
    delete_event,
    get_event,
    list_events,
    search_events,
    update_event,
)


def _http_error(status: int, reason: str = "error") -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.reason = reason
    return HttpError(resp=resp, content=reason.encode())


class TestListEvents:
    def test_returns_events(self, mock_client):
        events_data = [{"id": "1", "summary": "Meeting"}]
        mock_client.events().list.return_value.execute.return_value = {
            "items": events_data
        }
        result = list_events(mock_client)
        assert result == events_data

    def test_passes_time_filters(self, mock_client):
        mock_client.events().list.return_value.execute.return_value = {"items": []}
        list_events(
            mock_client,
            calendar_id="work@example.com",
            time_min="2024-01-01T00:00:00Z",
            time_max="2024-01-31T23:59:59Z",
            max_results=5,
        )
        call_kwargs = mock_client.events().list.call_args.kwargs
        assert call_kwargs["calendarId"] == "work@example.com"
        assert call_kwargs["timeMin"] == "2024-01-01T00:00:00Z"
        assert call_kwargs["timeMax"] == "2024-01-31T23:59:59Z"
        assert call_kwargs["maxResults"] == 5

    def test_clamps_max_results(self, mock_client):
        mock_client.events().list.return_value.execute.return_value = {"items": []}
        list_events(mock_client, max_results=9999)
        call_kwargs = mock_client.events().list.call_args.kwargs
        assert call_kwargs["maxResults"] == 2500

    def test_raises_on_http_error(self, mock_client):
        mock_client.events().list.return_value.execute.side_effect = _http_error(403)
        with pytest.raises(CalendarApiError):
            list_events(mock_client)

    def test_returns_empty_list_when_no_items(self, mock_client):
        mock_client.events().list.return_value.execute.return_value = {}
        result = list_events(mock_client)
        assert result == []


class TestSearchEvents:
    def test_returns_matching_events(self, mock_client):
        events_data = [{"id": "2", "summary": "Team sync"}]
        mock_client.events().list.return_value.execute.return_value = {
            "items": events_data
        }
        result = search_events(mock_client, query="sync")
        assert result == events_data

    def test_passes_query_parameter(self, mock_client):
        mock_client.events().list.return_value.execute.return_value = {"items": []}
        search_events(mock_client, query="standup")
        call_kwargs = mock_client.events().list.call_args.kwargs
        assert call_kwargs["q"] == "standup"


class TestGetEvent:
    def test_returns_event(self, mock_client):
        event_data = {"id": "abc123", "summary": "Review"}
        mock_client.events().get.return_value.execute.return_value = event_data
        result = get_event(mock_client, event_id="abc123")
        assert result == event_data

    def test_raises_on_http_error(self, mock_client):
        mock_client.events().get.return_value.execute.side_effect = _http_error(404)
        with pytest.raises(CalendarApiError):
            get_event(mock_client, event_id="missing")


class TestCreateEvent:
    def test_creates_event(self, mock_client):
        created = {"id": "new1", "summary": "Lunch"}
        mock_client.events().insert.return_value.execute.return_value = created
        result = create_event(mock_client, summary="Lunch", start="2024-01-15T12:00:00Z", end="2024-01-15T13:00:00Z")
        assert result == created

    def test_creates_all_day_event(self, mock_client):
        mock_client.events().insert.return_value.execute.return_value = {}
        create_event(mock_client, summary="Holiday", start="2024-01-15", end="2024-01-16", all_day=True)
        body = mock_client.events().insert.call_args.kwargs["body"]
        assert "date" in body["start"]
        assert "dateTime" not in body["start"]

    def test_includes_optional_fields(self, mock_client):
        mock_client.events().insert.return_value.execute.return_value = {}
        create_event(
            mock_client,
            summary="Meeting",
            start="2024-01-15T10:00:00Z",
            end="2024-01-15T11:00:00Z",
            description="Agenda here",
            location="Conference room",
            attendees=["alice@example.com", "bob@example.com"],
        )
        body = mock_client.events().insert.call_args.kwargs["body"]
        assert body["description"] == "Agenda here"
        assert body["location"] == "Conference room"
        assert len(body["attendees"]) == 2

    def test_raises_on_http_error(self, mock_client):
        mock_client.events().insert.return_value.execute.side_effect = _http_error(400)
        with pytest.raises(CalendarApiError):
            create_event(mock_client, summary="X", start="t", end="t")


class TestUpdateEvent:
    def test_patches_event(self, mock_client):
        updated = {"id": "ev1", "summary": "Updated"}
        mock_client.events().patch.return_value.execute.return_value = updated
        result = update_event(mock_client, event_id="ev1", summary="Updated")
        assert result == updated

    def test_only_sends_provided_fields(self, mock_client):
        mock_client.events().patch.return_value.execute.return_value = {}
        update_event(mock_client, event_id="ev1", summary="New title")
        body = mock_client.events().patch.call_args.kwargs["body"]
        assert "summary" in body
        assert "description" not in body


class TestDeleteEvent:
    def test_deletes_event(self, mock_client):
        mock_client.events().delete.return_value.execute.return_value = None
        delete_event(mock_client, event_id="ev1")  # Should not raise

    def test_raises_on_http_error(self, mock_client):
        mock_client.events().delete.return_value.execute.side_effect = _http_error(404)
        with pytest.raises(CalendarApiError):
            delete_event(mock_client, event_id="missing")
