"""Configuration loading via environment variables / .env file."""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# All logging goes to stderr so stdout stays clean for MCP stdio transport
logging.basicConfig(
    stream=sys.stderr,
    level=os.getenv("LOG_LEVEL", "WARNING").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""


DEFAULT_SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_REDIRECT_URI = "http://localhost:8081"
DEFAULT_TOKEN_STORE_PATH = "~/.config/google-calendar-mcp/"
DEFAULT_CALENDAR_ID = "primary"


@dataclass
class Config:
    client_id: str
    client_secret: str
    redirect_uri: str = DEFAULT_REDIRECT_URI
    token_store_path: Path = field(
        default_factory=lambda: Path(DEFAULT_TOKEN_STORE_PATH).expanduser()
    )
    scopes: list[str] = field(default_factory=lambda: list(DEFAULT_SCOPES))
    default_calendar_id: str = DEFAULT_CALENDAR_ID
    log_level: str = "WARNING"

    def __post_init__(self) -> None:
        if isinstance(self.token_store_path, str):
            self.token_store_path = Path(self.token_store_path).expanduser()
        if isinstance(self.scopes, str):
            self.scopes = [s.strip() for s in self.scopes.split(",")]


def load_config() -> Config:
    """Load configuration from environment variables.

    Raises:
        ConfigurationError: If required variables are missing.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

    missing = []
    if not client_id:
        missing.append("GOOGLE_CLIENT_ID")
    if not client_secret:
        missing.append("GOOGLE_CLIENT_SECRET")
    if missing:
        raise ConfigurationError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in your Google OAuth credentials."
        )

    scopes_raw = os.getenv("GOOGLE_SCOPES", "")
    scopes = (
        [s.strip() for s in scopes_raw.split(",") if s.strip()]
        if scopes_raw
        else list(DEFAULT_SCOPES)
    )

    token_store_path = Path(
        os.getenv("TOKEN_STORE_PATH", DEFAULT_TOKEN_STORE_PATH)
    ).expanduser()

    return Config(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        token_store_path=token_store_path,
        scopes=scopes,
        default_calendar_id=os.getenv("DEFAULT_CALENDAR_ID", DEFAULT_CALENDAR_ID),
        log_level=os.getenv("LOG_LEVEL", "WARNING"),
    )
