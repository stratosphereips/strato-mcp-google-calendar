"""OAuth 2.0 flow orchestration for Google Calendar."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from google_calendar_mcp.auth.token_store import TokenStore
from google_calendar_mcp.config import Config

logger = logging.getLogger(__name__)


class CalendarAuthError(Exception):
    """Raised when authentication cannot be completed or refreshed."""


def _credentials_to_dict(creds: Credentials) -> dict[str, Any]:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "scopes": list(creds.scopes) if creds.scopes else [],
        # client_secret intentionally omitted — injected from live config at load time
    }


def _credentials_from_dict(data: dict[str, Any], config: Config) -> Credentials:
    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=config.client_id,
        client_secret=config.client_secret,
        scopes=data.get("scopes"),
    )


def get_credentials(
    user_id: str,
    config: Config,
    token_store: TokenStore,
    *,
    headless: bool = False,
) -> Credentials:
    """Return valid Google credentials for user_id.

    Flow:
    1. Try to load saved token from token_store.
    2. If valid, return immediately.
    3. If expired and refresh token exists, refresh and save.
    4. If no token or refresh fails:
       - headless=True: raise CalendarAuthError immediately (serve path).
       - headless=False: run browser OAuth flow and save (auth path).

    Args:
        user_id: Identifier for the user. Use "default" for single-user mode.
        config: Application configuration.
        token_store: Persistence layer for tokens.
        headless: When True, raise instead of launching a browser flow.

    Returns:
        Valid :class:`google.oauth2.credentials.Credentials`.

    Raises:
        CalendarAuthError: If authentication cannot be completed.
    """
    token_data = token_store.load(user_id)
    creds: Credentials | None = None

    if token_data:
        creds = _credentials_from_dict(token_data, config)

    if creds and creds.valid:
        logger.debug("Using valid cached credentials for user %s", user_id)
        return creds

    if creds and creds.expired and creds.refresh_token:
        logger.info("Refreshing expired credentials for user %s", user_id)
        try:
            creds.refresh(Request())
            token_store.save(user_id, _credentials_to_dict(creds))
            return creds
        except RefreshError as exc:
            logger.warning(
                "Token refresh failed for user %s: %s.", user_id, exc
            )

    if headless:
        raise CalendarAuthError(
            f"No valid token found for user {user_id!r} and browser flow is disabled."
        )

    # No valid credentials — run browser flow
    logger.info("Starting OAuth browser flow for user %s", user_id)
    client_config = {
        "installed": {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uris": [config.redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    port = urlparse(config.redirect_uri).port or 8081
    try:
        flow = InstalledAppFlow.from_client_config(client_config, scopes=config.scopes)
        creds = flow.run_local_server(host="0.0.0.0", port=port, open_browser=False)
    except Exception as exc:
        raise CalendarAuthError(
            f"OAuth flow failed for user {user_id!r}: {exc}"
        ) from exc

    token_store.save(user_id, _credentials_to_dict(creds))
    logger.info("OAuth flow completed successfully for user %s", user_id)
    return creds
