"""MCP tool definitions for Google Calendar events."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from google_calendar_mcp.calendar.events import (
    CalendarApiError,
    create_event,
    delete_event,
    get_event,
    list_events,
    search_events,
    update_event,
)

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)


def _error(msg: str) -> str:
    return json.dumps({"error": msg})


_VALID_ORDER_BY = {"startTime", "updated"}

_COLOR_NAMES: dict[str, str] = {
    "tomato": "1", "flamingo": "2", "tangerine": "3", "banana": "4",
    "sage": "5", "basil": "6", "peacock": "7", "blueberry": "8",
    "lavender": "9", "grape": "10", "graphite": "11",
}
_VALID_COLOR_IDS = set(_COLOR_NAMES.values())

# Google Calendar API limits: max 5 overrides, minutes 0–40320 (4 weeks)
_MAX_REMINDERS = 5
_MAX_REMINDER_MINUTES = 40320


def _resolve_color_id(value: str) -> str | None:
    """Accept '1'–'11' or a color name; return the numeric string, or None if invalid."""
    v = value.strip().lower()
    resolved = _COLOR_NAMES.get(v, value.strip())
    if resolved not in _VALID_COLOR_IDS:
        return None
    return resolved


def _parse_reminders(value: str) -> list[dict]:
    """Parse '10,30' → [{"method":"popup","minutes":10}, ...]. Capped at 5 entries."""
    result = []
    for part in value.split(","):
        part = part.strip()
        if part.isdigit():
            minutes = int(part)
            if 0 <= minutes <= _MAX_REMINDER_MINUTES:
                result.append({"method": "popup", "minutes": minutes})
        if len(result) >= _MAX_REMINDERS:
            break
    return result


def register_event_tools(mcp: Any, get_client: Any) -> None:
    """Register all event-related MCP tools on the given FastMCP instance."""

    @mcp.tool()
    def list_events_tool(
        calendar_id: str = "primary",
        time_min: str = "",
        time_max: str = "",
        max_results: int = 10,
        order_by: str = "startTime",
    ) -> str:
        """List upcoming events from a Google Calendar.

        Args:
            calendar_id: Calendar to query (default: primary).
            time_min: Start of time range in RFC3339 format (e.g. 2024-01-01T00:00:00Z).
            time_max: End of time range in RFC3339 format.
            max_results: Maximum number of events to return (1-2500).
            order_by: Sort order: 'startTime' or 'updated'.
        """
        if order_by not in _VALID_ORDER_BY:
            return _error(f"order_by must be one of: {', '.join(sorted(_VALID_ORDER_BY))}")
        try:
            client = get_client()
            events = list_events(
                client,
                calendar_id=calendar_id,
                time_min=time_min or None,
                time_max=time_max or None,
                max_results=max_results,
                order_by=order_by,
            )
            return json.dumps({"events": events, "count": len(events)})
        except CalendarApiError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in list_events_tool")
            return _error(f"Unexpected error: {exc}")

    @mcp.tool()
    def search_events_tool(
        query: str,
        calendar_id: str = "primary",
        time_min: str = "",
        time_max: str = "",
        max_results: int = 10,
    ) -> str:
        """Search for events by text query in a Google Calendar.

        Args:
            query: Free-text search string.
            calendar_id: Calendar to search (default: primary).
            time_min: Start of time range in RFC3339 format.
            time_max: End of time range in RFC3339 format.
            max_results: Maximum number of events to return.
        """
        if not query.strip():
            return _error("query must not be empty")
        try:
            client = get_client()
            events = search_events(
                client,
                query=query,
                calendar_id=calendar_id,
                time_min=time_min or None,
                time_max=time_max or None,
                max_results=max_results,
            )
            return json.dumps({"events": events, "count": len(events)})
        except CalendarApiError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in search_events_tool")
            return _error(f"Unexpected error: {exc}")

    @mcp.tool()
    def get_event_tool(event_id: str, calendar_id: str = "primary") -> str:
        """Retrieve a single calendar event by its ID.

        Args:
            event_id: The event's unique identifier.
            calendar_id: Calendar containing the event (default: primary).
        """
        if not event_id.strip():
            return _error("event_id must not be empty")
        try:
            client = get_client()
            event = get_event(client, event_id=event_id, calendar_id=calendar_id)
            return json.dumps(event)
        except CalendarApiError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in get_event_tool")
            return _error(f"Unexpected error: {exc}")

    @mcp.tool()
    def create_event_tool(
        summary: str,
        start: str,
        end: str,
        calendar_id: str = "primary",
        description: str = "",
        location: str = "",
        attendees: str = "",
        all_day: bool = False,
        color_id: str = "",
        reminders: str = "",
    ) -> str:
        """Create a new event in a Google Calendar.

        Args:
            summary: Event title.
            start: Start time in RFC3339 format, or YYYY-MM-DD for all-day events.
            end: End time in RFC3339 format, or YYYY-MM-DD for all-day events.
            calendar_id: Calendar to create the event in (default: primary).
            description: Optional event description.
            location: Optional event location.
            attendees: Comma-separated list of attendee email addresses.
            all_day: Set to true for all-day events (use YYYY-MM-DD for start/end).
            color_id: Optional event color. Use a number 1-11 or a name:
                1=Tomato 2=Flamingo 3=Tangerine 4=Banana 5=Sage 6=Basil
                7=Peacock 8=Blueberry 9=Lavender 10=Grape 11=Graphite
            reminders: Comma-separated minutes before event for popup reminders.
                E.g. "10" for 10-minute reminder, "10,30" for two reminders.
                Leave empty to use the calendar's default reminders.
        """
        if not summary.strip():
            return _error("summary must not be empty")
        if not start.strip() or not end.strip():
            return _error("start and end must not be empty")

        attendee_list = (
            [e.strip() for e in attendees.split(",") if e.strip()]
            if attendees
            else None
        )
        resolved_color = _resolve_color_id(color_id) if color_id else None
        parsed_reminders = _parse_reminders(reminders) if reminders else None
        try:
            client = get_client()
            event = create_event(
                client,
                summary=summary,
                start=start,
                end=end,
                calendar_id=calendar_id,
                description=description or None,
                location=location or None,
                attendees=attendee_list,
                all_day=all_day,
                color_id=resolved_color,
                reminders=parsed_reminders,
            )
            return json.dumps(event)
        except CalendarApiError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in create_event_tool")
            return _error(f"Unexpected error: {exc}")

    @mcp.tool()
    def update_event_tool(
        event_id: str,
        calendar_id: str = "primary",
        summary: str = "",
        start: str = "",
        end: str = "",
        description: str = "",
        location: str = "",
        attendees: str = "",
        color_id: str = "",
        reminders: str = "",
    ) -> str:
        """Update an existing calendar event.

        Only fields provided (non-empty) will be updated.

        Args:
            event_id: The event's unique identifier.
            calendar_id: Calendar containing the event (default: primary).
            summary: New event title (leave empty to keep current).
            start: New start time in RFC3339 format (leave empty to keep current).
            end: New end time in RFC3339 format (leave empty to keep current).
            description: New description (leave empty to keep current).
            location: New location (leave empty to keep current).
            attendees: New comma-separated attendee emails (leave empty to keep current).
            color_id: Optional event color. Use a number 1-11 or a name:
                1=Tomato 2=Flamingo 3=Tangerine 4=Banana 5=Sage 6=Basil
                7=Peacock 8=Blueberry 9=Lavender 10=Grape 11=Graphite
            reminders: Comma-separated minutes before event for popup reminders.
                E.g. "10" for 10-minute reminder, "10,30" for two reminders.
                Leave empty to keep current reminders.
        """
        if not event_id.strip():
            return _error("event_id must not be empty")

        attendee_list = (
            [e.strip() for e in attendees.split(",") if e.strip()]
            if attendees
            else None
        )
        resolved_color = _resolve_color_id(color_id) if color_id else None
        parsed_reminders = _parse_reminders(reminders) if reminders else None
        try:
            client = get_client()
            event = update_event(
                client,
                event_id=event_id,
                calendar_id=calendar_id,
                summary=summary or None,
                start=start or None,
                end=end or None,
                description=description or None,
                location=location or None,
                attendees=attendee_list,
                color_id=resolved_color,
                reminders=parsed_reminders,
            )
            return json.dumps(event)
        except CalendarApiError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in update_event_tool")
            return _error(f"Unexpected error: {exc}")

    @mcp.tool()
    def delete_event_tool(event_id: str, calendar_id: str = "primary") -> str:
        """Delete a calendar event by its ID.

        Args:
            event_id: The event's unique identifier.
            calendar_id: Calendar containing the event (default: primary).
        """
        if not event_id.strip():
            return _error("event_id must not be empty")
        try:
            client = get_client()
            delete_event(client, event_id=event_id, calendar_id=calendar_id)
            return json.dumps({"deleted": True, "event_id": event_id})
        except CalendarApiError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in delete_event_tool")
            return _error(f"Unexpected error: {exc}")
