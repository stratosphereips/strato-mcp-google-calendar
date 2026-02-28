"""MCP tool definitions for free/busy queries."""
from __future__ import annotations

import json
import logging
from typing import Any

from google_calendar_mcp.calendar.events import CalendarApiError
from google_calendar_mcp.calendar.freebusy import check_free_busy

logger = logging.getLogger(__name__)


def _error(msg: str) -> str:
    return json.dumps({"error": msg})


def register_freebusy_tools(mcp: Any, get_client: Any) -> None:
    """Register free/busy MCP tools on the given FastMCP instance."""

    @mcp.tool()
    def check_free_busy_tool(
        time_min: str,
        time_max: str,
        calendar_ids: str = "primary",
        timezone: str = "UTC",
    ) -> str:
        """Check free/busy status for one or more calendars within a time range.

        Args:
            time_min: Start of the time range in RFC3339 format (e.g. 2024-01-15T09:00:00Z).
            time_max: End of the time range in RFC3339 format.
            calendar_ids: Comma-separated list of calendar IDs (default: primary).
            timezone: IANA timezone name for interpreting results (default: UTC).
        """
        if not time_min.strip() or not time_max.strip():
            return _error("time_min and time_max must not be empty")

        cal_ids = [c.strip() for c in calendar_ids.split(",") if c.strip()]
        if not cal_ids:
            cal_ids = ["primary"]

        try:
            client = get_client()
            result = check_free_busy(
                client,
                calendar_ids=cal_ids,
                time_min=time_min,
                time_max=time_max,
                timezone=timezone,
            )
            return json.dumps(result)
        except CalendarApiError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error in check_free_busy_tool")
            return _error(f"Unexpected error: {exc}")
