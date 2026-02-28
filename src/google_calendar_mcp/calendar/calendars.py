"""Google Calendar CalendarList API wrappers."""
from __future__ import annotations

import logging
from typing import Any

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from google_calendar_mcp.calendar.events import CalendarApiError

logger = logging.getLogger(__name__)


def list_calendars(client: Resource) -> list[dict[str, Any]]:
    """Return all calendars in the user's calendar list."""
    try:
        result = client.calendarList().list().execute()
        return result.get("items", [])
    except HttpError as exc:
        raise CalendarApiError(f"Failed to list calendars: {exc}") from exc


def get_calendar(client: Resource, calendar_id: str) -> dict[str, Any]:
    """Return a single calendar from the user's calendar list."""
    try:
        return client.calendarList().get(calendarId=calendar_id).execute()
    except HttpError as exc:
        raise CalendarApiError(f"Failed to get calendar {calendar_id!r}: {exc}") from exc
