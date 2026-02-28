"""MCP tool integration tests — input validation and error handling."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from google_calendar_mcp.calendar.events import CalendarApiError


def _http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.reason = "error"
    return HttpError(resp=resp, content=b"error")


# ---------------------------------------------------------------------------
# Helpers to build minimal FastMCP-like recorders
# ---------------------------------------------------------------------------


class ToolRecorder:
    """Captures tool functions registered via @recorder.tool()."""

    def __init__(self):
        self._tools: dict[str, callable] = {}

    def tool(self):
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn
        return decorator

    def call(self, name: str, **kwargs):
        return self._tools[name](**kwargs)


# ---------------------------------------------------------------------------
# Events tools
# ---------------------------------------------------------------------------


class TestEventTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_client):
        from google_calendar_mcp.tools.events import register_event_tools

        self.recorder = ToolRecorder()
        self.client = mock_client
        register_event_tools(self.recorder, lambda: self.client)

    def test_list_events_returns_json(self):
        self.client.events().list.return_value.execute.return_value = {
            "items": [{"id": "1", "summary": "Meeting"}]
        }
        result = json.loads(self.recorder.call("list_events_tool"))
        assert result["count"] == 1
        assert result["events"][0]["summary"] == "Meeting"

    def test_list_events_returns_error_on_api_failure(self):
        self.client.events().list.return_value.execute.side_effect = _http_error(403)
        result = json.loads(self.recorder.call("list_events_tool"))
        assert "error" in result

    def test_search_events_rejects_empty_query(self):
        result = json.loads(self.recorder.call("search_events_tool", query="   "))
        assert "error" in result

    def test_search_events_returns_results(self):
        self.client.events().list.return_value.execute.return_value = {
            "items": [{"id": "2", "summary": "Standup"}]
        }
        result = json.loads(self.recorder.call("search_events_tool", query="standup"))
        assert result["count"] == 1

    def test_get_event_rejects_empty_id(self):
        result = json.loads(self.recorder.call("get_event_tool", event_id=""))
        assert "error" in result

    def test_create_event_rejects_empty_summary(self):
        result = json.loads(
            self.recorder.call(
                "create_event_tool",
                summary="",
                start="2024-01-15T10:00:00Z",
                end="2024-01-15T11:00:00Z",
            )
        )
        assert "error" in result

    def test_create_event_success(self):
        created = {"id": "new1", "summary": "Lunch"}
        self.client.events().insert.return_value.execute.return_value = created
        result = json.loads(
            self.recorder.call(
                "create_event_tool",
                summary="Lunch",
                start="2024-01-15T12:00:00Z",
                end="2024-01-15T13:00:00Z",
            )
        )
        assert result["id"] == "new1"

    def test_create_event_parses_attendees_csv(self):
        self.client.events().insert.return_value.execute.return_value = {}
        self.recorder.call(
            "create_event_tool",
            summary="Meeting",
            start="2024-01-15T10:00:00Z",
            end="2024-01-15T11:00:00Z",
            attendees="alice@example.com, bob@example.com",
        )
        body = self.client.events().insert.call_args.kwargs["body"]
        assert len(body["attendees"]) == 2

    def test_update_event_rejects_empty_id(self):
        result = json.loads(self.recorder.call("update_event_tool", event_id=""))
        assert "error" in result

    def test_delete_event_returns_confirmation(self):
        self.client.events().delete.return_value.execute.return_value = None
        result = json.loads(self.recorder.call("delete_event_tool", event_id="ev1"))
        assert result["deleted"] is True
        assert result["event_id"] == "ev1"

    def test_delete_event_rejects_empty_id(self):
        result = json.loads(self.recorder.call("delete_event_tool", event_id=""))
        assert "error" in result

    def test_create_tool_resolves_color_name(self):
        self.client.events().insert.return_value.execute.return_value = {}
        self.recorder.call(
            "create_event_tool",
            summary="Test",
            start="2024-01-15T10:00:00Z",
            end="2024-01-15T11:00:00Z",
            color_id="Tomato",
        )
        body = self.client.events().insert.call_args.kwargs["body"]
        assert body["colorId"] == "1"

    def test_create_tool_parses_reminders_string(self):
        self.client.events().insert.return_value.execute.return_value = {}
        self.recorder.call(
            "create_event_tool",
            summary="Test",
            start="2024-01-15T10:00:00Z",
            end="2024-01-15T11:00:00Z",
            reminders="10,30",
        )
        body = self.client.events().insert.call_args.kwargs["body"]
        overrides = body["reminders"]["overrides"]
        assert len(overrides) == 2
        assert {"method": "popup", "minutes": 10} in overrides
        assert {"method": "popup", "minutes": 30} in overrides

    def test_create_tool_omits_color_when_empty(self):
        self.client.events().insert.return_value.execute.return_value = {}
        self.recorder.call(
            "create_event_tool",
            summary="Test",
            start="2024-01-15T10:00:00Z",
            end="2024-01-15T11:00:00Z",
        )
        body = self.client.events().insert.call_args.kwargs["body"]
        assert "colorId" not in body

    def test_create_tool_omits_reminders_when_empty(self):
        self.client.events().insert.return_value.execute.return_value = {}
        self.recorder.call(
            "create_event_tool",
            summary="Test",
            start="2024-01-15T10:00:00Z",
            end="2024-01-15T11:00:00Z",
        )
        body = self.client.events().insert.call_args.kwargs["body"]
        assert "reminders" not in body

    def test_update_tool_resolves_color_name(self):
        self.client.events().patch.return_value.execute.return_value = {}
        self.recorder.call("update_event_tool", event_id="ev1", color_id="Blueberry")
        body = self.client.events().patch.call_args.kwargs["body"]
        assert body["colorId"] == "8"

    def test_update_tool_parses_reminders_string(self):
        self.client.events().patch.return_value.execute.return_value = {}
        self.recorder.call("update_event_tool", event_id="ev1", reminders="15")
        body = self.client.events().patch.call_args.kwargs["body"]
        assert body["reminders"] == {"useDefault": False, "overrides": [{"method": "popup", "minutes": 15}]}

    def test_update_tool_omits_color_when_empty(self):
        self.client.events().patch.return_value.execute.return_value = {}
        self.recorder.call("update_event_tool", event_id="ev1", summary="New")
        body = self.client.events().patch.call_args.kwargs["body"]
        assert "colorId" not in body

    def test_update_tool_omits_reminders_when_empty(self):
        self.client.events().patch.return_value.execute.return_value = {}
        self.recorder.call("update_event_tool", event_id="ev1", summary="New")
        body = self.client.events().patch.call_args.kwargs["body"]
        assert "reminders" not in body


# ---------------------------------------------------------------------------
# Calendar tools
# ---------------------------------------------------------------------------


class TestCalendarTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_client):
        from google_calendar_mcp.tools.calendars import register_calendar_tools

        self.recorder = ToolRecorder()
        self.client = mock_client
        register_calendar_tools(self.recorder, lambda: self.client)

    def test_list_calendars_returns_json(self):
        self.client.calendarList().list.return_value.execute.return_value = {
            "items": [{"id": "primary", "summary": "My Calendar"}]
        }
        result = json.loads(self.recorder.call("list_calendars_tool"))
        assert result["count"] == 1

    def test_get_calendar_rejects_empty_id(self):
        result = json.loads(self.recorder.call("get_calendar_tool", calendar_id=""))
        assert "error" in result

    def test_get_calendar_returns_data(self):
        self.client.calendarList().get.return_value.execute.return_value = {
            "id": "work@example.com",
            "summary": "Work",
        }
        result = json.loads(
            self.recorder.call("get_calendar_tool", calendar_id="work@example.com")
        )
        assert result["id"] == "work@example.com"


# ---------------------------------------------------------------------------
# Free/busy tools
# ---------------------------------------------------------------------------


class TestFreeBusyTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_client):
        from google_calendar_mcp.tools.freebusy import register_freebusy_tools

        self.recorder = ToolRecorder()
        self.client = mock_client
        register_freebusy_tools(self.recorder, lambda: self.client)

    def test_rejects_empty_time_range(self):
        result = json.loads(
            self.recorder.call("check_free_busy_tool", time_min="", time_max="")
        )
        assert "error" in result

    def test_returns_freebusy_data(self):
        fb_data = {
            "calendars": {
                "primary": {"busy": []}
            }
        }
        self.client.freebusy().query.return_value.execute.return_value = fb_data
        result = json.loads(
            self.recorder.call(
                "check_free_busy_tool",
                time_min="2024-01-15T09:00:00Z",
                time_max="2024-01-15T17:00:00Z",
            )
        )
        assert "calendars" in result

    def test_parses_calendar_ids_csv(self):
        self.client.freebusy().query.return_value.execute.return_value = {
            "calendars": {}
        }
        self.recorder.call(
            "check_free_busy_tool",
            time_min="2024-01-15T09:00:00Z",
            time_max="2024-01-15T17:00:00Z",
            calendar_ids="primary, work@example.com",
        )
        body = self.client.freebusy().query.call_args.kwargs["body"]
        assert {"id": "primary"} in body["items"]
        assert {"id": "work@example.com"} in body["items"]
