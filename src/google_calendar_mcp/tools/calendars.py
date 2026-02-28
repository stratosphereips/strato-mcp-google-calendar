"""MCP tool definitions for Google Calendar management."""
from __future__ import annotations

import json
import logging
from typing import Any

from google_calendar_mcp.calendar.calendars import get_calendar, list_calendars
from google_calendar_mcp.calendar.events import CalendarApiError

logger = logging.getLogger(__name__)


def _error(msg: str) -> str:
    return json.dumps({"error": msg})


def register_calendar_tools(mcp: Any, get_client: Any) -> None:
    """Register all calendar-management MCP tools on the given FastMCP instance."""

    @mcp.tool()
    def list_calendars_tool() -> str:
        """List all calendars in the user's Google Calendar account."""
        try:
            client = get_client()
            calendars = list_calendars(client)
            return json.dumps({"calendars": calendars, "count": len(calendars)})
        except CalendarApiError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in list_calendars_tool")
            return _error(f"Unexpected error: {exc}")

    @mcp.tool()
    def get_calendar_tool(calendar_id: str) -> str:
        """Retrieve details for a specific calendar.

        Args:
            calendar_id: The calendar's unique identifier (e.g. 'primary' or an email address).
        """
        if not calendar_id.strip():
            return _error("calendar_id must not be empty")
        try:
            client = get_client()
            calendar = get_calendar(client, calendar_id=calendar_id)
            return json.dumps(calendar)
        except CalendarApiError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in get_calendar_tool")
            return _error(f"Unexpected error: {exc}")
