"""Google Calendar Free/Busy API wrapper."""
from __future__ import annotations

import logging
from typing import Any

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from google_calendar_mcp.calendar.events import CalendarApiError

logger = logging.getLogger(__name__)


def check_free_busy(
    client: Resource,
    calendar_ids: list[str],
    time_min: str,
    time_max: str,
    timezone: str = "UTC",
) -> dict[str, Any]:
    """Query free/busy information for one or more calendars.

    Args:
        client: Authenticated Calendar API resource.
        calendar_ids: List of calendar identifiers to query.
        time_min: Start of interval (RFC3339).
        time_max: End of interval (RFC3339).
        timezone: IANA timezone name for the response.

    Returns:
        FreeBusy response dict with ``calendars`` mapping each calendar_id
        to its list of busy ``{start, end}`` intervals.
    """
    body: dict[str, Any] = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": timezone,
        "items": [{"id": cid} for cid in calendar_ids],
    }
    try:
        result = client.freebusy().query(body=body).execute()
        return result
    except HttpError as exc:
        raise CalendarApiError(f"Failed to query free/busy: {exc}") from exc
