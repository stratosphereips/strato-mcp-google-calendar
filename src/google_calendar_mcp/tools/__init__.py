"""Shared utilities for MCP tool modules."""
from __future__ import annotations

import logging
import re

from google_calendar_mcp.calendar.events import CalendarApiError

logger = logging.getLogger(__name__)

# Matches the HTTP status code in CalendarApiError messages, e.g. "HttpError 403"
_HTTP_STATUS_RE = re.compile(r"HttpError\s+(\d{3})")


def sanitize_api_error(exc: CalendarApiError) -> str:
    """Return a safe, client-facing error string for a CalendarApiError.

    Logs the full exception (including HTTP body) at WARNING so it appears in
    server logs, but returns only the HTTP status code to the caller to avoid
    leaking internal URLs, response bodies, or resource identifiers.
    """
    logger.warning("Calendar API error: %s", exc)
    match = _HTTP_STATUS_RE.search(str(exc))
    if match:
        return f"Calendar API error ({match.group(1)})"
    return "Calendar API request failed"
