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
        print(f"[ERROR] {exc}", file=sys.stderr)
        print(
            "\n[ERROR] No valid token found. Run authentication first:\n\n"
            "  docker run --rm -it -p 8081:8081 \\\n"
            "    -v google-calendar-tokens:/tokens \\\n"
            "    -e GOOGLE_CLIENT_ID=... -e GOOGLE_CLIENT_SECRET=... \\\n"
            "    google-calendar-mcp:latest auth\n",
            file=sys.stderr,
        )
        sys.exit(1)

    _client = build_client(credentials)
    logger.info("Google Calendar client initialised successfully")

    _register_tools()

    mcp.run()


def auth_main() -> None:
    """Entry point for the google-calendar-auth command.

    Runs only the OAuth flow, saves the token, and exits 0.
    Does not start the MCP server.
    """
    from google_calendar_mcp.auth.oauth import CalendarAuthError, get_credentials
    from google_calendar_mcp.auth.token_store import FileTokenStore
    from google_calendar_mcp.config import ConfigurationError, load_config

    try:
        config = load_config()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    token_store = FileTokenStore(config.token_store_path)

    try:
        get_credentials("default", config, token_store)
        print("Authentication successful. Token saved.", file=sys.stderr)
    except CalendarAuthError as exc:
        print(f"Authentication error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
