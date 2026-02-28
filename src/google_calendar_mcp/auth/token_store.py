"""TokenStore ABC and FileTokenStore implementation."""
from __future__ import annotations

import fcntl
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TokenStore(ABC):
    """Abstract base class for token persistence.

    Implementations must be thread-safe for the user_id they operate on.
    Future implementations (e.g. DatabaseTokenStore) swap in here without
    changing the OAuth or tool layers.
    """

    @abstractmethod
    def load(self, user_id: str) -> dict[str, Any] | None:
        """Return stored token data for user_id, or None if not found."""

    @abstractmethod
    def save(self, user_id: str, data: dict[str, Any]) -> None:
        """Persist token data for user_id."""

    @abstractmethod
    def delete(self, user_id: str) -> None:
        """Remove stored token for user_id (e.g. on auth revocation)."""


class FileTokenStore(TokenStore):
    """Stores one JSON file per user_id under a configurable directory.

    File name pattern: ``{store_dir}/{user_id}.token.json``
    """

    def __init__(self, store_dir: Path | str) -> None:
        self._store_dir = Path(store_dir).expanduser()

    def _token_path(self, user_id: str) -> Path:
        # Sanitise user_id to prevent path traversal
        safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
        if not safe_id:
            raise ValueError(f"Invalid user_id: {user_id!r}")
        return self._store_dir / f"{safe_id}.token.json"

    def load(self, user_id: str) -> dict[str, Any] | None:
        path = self._token_path(user_id)
        if not path.exists():
            logger.debug("No token file found at %s", path)
            return None
        try:
            with path.open("r") as fh:
                fcntl.flock(fh, fcntl.LOCK_SH)
                data = json.load(fh)
            logger.debug("Loaded token for user %s", user_id)
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load token for %s: %s", user_id, exc)
            return None

    def save(self, user_id: str, data: dict[str, Any]) -> None:
        self._store_dir.mkdir(parents=True, exist_ok=True)
        path = self._token_path(user_id)
        tmp = path.with_suffix(".tmp")
        try:
            with tmp.open("w") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                json.dump(data, fh, indent=2)
            tmp.chmod(0o600)
            tmp.replace(path)  # atomic on same filesystem
            logger.debug("Saved token for user %s to %s", user_id, path)
        except OSError as exc:
            logger.error("Failed to save token for %s: %s", user_id, exc)
            raise

    def delete(self, user_id: str) -> None:
        path = self._token_path(user_id)
        if path.exists():
            path.unlink()
            logger.debug("Deleted token for user %s", user_id)
