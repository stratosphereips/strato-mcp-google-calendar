"""MCP server entry point for Google Calendar."""
from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("Google Calendar")

# Lazy globals — populated in main() after config + auth succeed
_client = None


def _get_client():
    if _client is None:
        raise RuntimeError(
            "Google Calendar client not initialised. "
            "Ensure main() completed authentication before tools are called."
        )
    return _client


def _register_tools() -> None:
    from google_calendar_mcp.tools.calendars import register_calendar_tools
    from google_calendar_mcp.tools.events import register_event_tools
    from google_calendar_mcp.tools.freebusy import register_freebusy_tools

    register_event_tools(mcp, _get_client)
    register_calendar_tools(mcp, _get_client)
    register_freebusy_tools(mcp, _get_client)


def main() -> None:
    """Entry point called by the pyproject.toml script."""
    global _client

    # Import here so logging is configured by config.py before anything else
    from google_calendar_mcp.auth.oauth import CalendarAuthError, get_credentials
    from google_calendar_mcp.auth.token_store import FileTokenStore
    from google_calendar_mcp.calendar.client import build_client
    from google_calendar_mcp.config import ConfigurationError, load_config

    try:
        config = load_config()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    token_store = FileTokenStore(config.token_store_path)

    try:
        credentials = get_credentials("default", config, token_store)
    except CalendarAuthError as exc:
        print(f"Authentication error: {exc}", file=sys.stderr)
        print(
            "Re-run 'google-calendar-mcp' to restart the OAuth flow.",
            file=sys.stderr,
        )
        sys.exit(1)

    _client = build_client(credentials)
    logger.info("Google Calendar client initialised successfully")

    _register_tools()

    mcp.run()


if __name__ == "__main__":
    main()
