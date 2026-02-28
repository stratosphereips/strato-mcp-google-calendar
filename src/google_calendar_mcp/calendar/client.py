"""Authenticated Google Calendar API client factory."""
from __future__ import annotations

import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

logger = logging.getLogger(__name__)


def build_client(credentials: Credentials) -> Resource:
    """Return an authenticated Google Calendar API resource.

    Args:
        credentials: Valid Google OAuth2 credentials.

    Returns:
        Authenticated ``googleapiclient.discovery.Resource`` for the
        Calendar API v3.
    """
    logger.debug("Building Google Calendar API client")
    return build("calendar", "v3", credentials=credentials)
