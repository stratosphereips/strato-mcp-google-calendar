# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: builder — install production dependencies with uv
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Copy only what is needed for dependency resolution first (layer-cache friendly)
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install production dependencies into /app/.venv (no dev extras)
RUN uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Stage 2: runtime — lean image, no build tools
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# TOKEN_STORE_PATH is a filesystem path, not a secret.
# Default is baked in here for convenience; override with --env TOKEN_STORE_PATH=...
# hadolint ignore=DL3044
ENV TOKEN_STORE_PATH=/tokens

WORKDIR /app

# Copy the pre-built venv and source from the builder stage
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Create a non-root user and set up the token volume directory
RUN useradd --uid 1000 --no-create-home --shell /bin/sh appuser \
    && mkdir -p /tokens \
    && chown appuser:appuser /tokens

# Copy the entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER appuser

# Declare the token volume
VOLUME ["/tokens"]

# OCI image labels
LABEL org.opencontainers.image.title="google-calendar-mcp" \
      org.opencontainers.image.description="MCP server exposing Google Calendar as tools for Claude" \
      org.opencontainers.image.source="https://github.com/stratosphericus/strato-mcp-google-calendar" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["serve"]
