"""Google Calendar Events API wrappers."""
from __future__ import annotations

import logging
from typing import Any

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class CalendarApiError(Exception):
    """Raised when the Google Calendar API returns an error."""


def list_events(
    client: Resource,
    calendar_id: str = "primary",
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 10,
    order_by: str = "startTime",
) -> list[dict[str, Any]]:
    """List events from a calendar.

    Args:
        client: Authenticated Calendar API resource.
        calendar_id: Calendar identifier.
        time_min: Lower bound (RFC3339) for event start time.
        time_max: Upper bound (RFC3339) for event start time.
        max_results: Maximum number of events to return (1–2500).
        order_by: Order of events: 'startTime' or 'updated'.

    Returns:
        List of event resource dicts.
    """
    try:
        kwargs: dict[str, Any] = {
            "calendarId": calendar_id,
            "maxResults": min(max(1, max_results), 2500),
            "singleEvents": True,
            "orderBy": order_by,
        }
        if time_min:
            kwargs["timeMin"] = time_min
        if time_max:
            kwargs["timeMax"] = time_max

        result = client.events().list(**kwargs).execute()
        return result.get("items", [])
    except HttpError as exc:
        raise CalendarApiError(f"Failed to list events: {exc}") from exc


def search_events(
    client: Resource,
    query: str,
    calendar_id: str = "primary",
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Search events by free-text query."""
    try:
        kwargs: dict[str, Any] = {
            "calendarId": calendar_id,
            "q": query,
            "maxResults": min(max(1, max_results), 2500),
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            kwargs["timeMin"] = time_min
        if time_max:
            kwargs["timeMax"] = time_max

        result = client.events().list(**kwargs).execute()
        return result.get("items", [])
    except HttpError as exc:
        raise CalendarApiError(f"Failed to search events: {exc}") from exc


def get_event(
    client: Resource,
    event_id: str,
    calendar_id: str = "primary",
) -> dict[str, Any]:
    """Retrieve a single event by ID."""
    try:
        return client.events().get(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as exc:
        raise CalendarApiError(f"Failed to get event {event_id!r}: {exc}") from exc


def create_event(
    client: Resource,
    summary: str,
    start: str,
    end: str,
    calendar_id: str = "primary",
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    all_day: bool = False,
) -> dict[str, Any]:
    """Create a new calendar event.

    Args:
        client: Authenticated Calendar API resource.
        summary: Event title.
        start: Start time as RFC3339 string or date string (YYYY-MM-DD) for all-day.
        end: End time as RFC3339 string or date string (YYYY-MM-DD) for all-day.
        calendar_id: Calendar to create the event in.
        description: Optional event description.
        location: Optional event location.
        attendees: Optional list of attendee email addresses.
        all_day: If True, treat start/end as dates (not datetimes).

    Returns:
        Created event resource dict.
    """
    if all_day:
        start_obj = {"date": start}
        end_obj = {"date": end}
    else:
        start_obj = {"dateTime": start}
        end_obj = {"dateTime": end}

    body: dict[str, Any] = {
        "summary": summary,
        "start": start_obj,
        "end": end_obj,
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]

    try:
        return (
            client.events()
            .insert(calendarId=calendar_id, body=body)
            .execute()
        )
    except HttpError as exc:
        raise CalendarApiError(f"Failed to create event: {exc}") from exc


def update_event(
    client: Resource,
    event_id: str,
    calendar_id: str = "primary",
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
) -> dict[str, Any]:
    """Update an existing event using patch semantics."""
    body: dict[str, Any] = {}
    if summary is not None:
        body["summary"] = summary
    if start is not None:
        body["start"] = {"dateTime": start}
    if end is not None:
        body["end"] = {"dateTime": end}
    if description is not None:
        body["description"] = description
    if location is not None:
        body["location"] = location
    if attendees is not None:
        body["attendees"] = [{"email": email} for email in attendees]

    try:
        return (
            client.events()
            .patch(calendarId=calendar_id, eventId=event_id, body=body)
            .execute()
        )
    except HttpError as exc:
        raise CalendarApiError(f"Failed to update event {event_id!r}: {exc}") from exc


def delete_event(
    client: Resource,
    event_id: str,
    calendar_id: str = "primary",
) -> None:
    """Delete an event by ID."""
    try:
        client.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as exc:
        raise CalendarApiError(f"Failed to delete event {event_id!r}: {exc}") from exc
