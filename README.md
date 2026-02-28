# strato-mcp-google-calendar

A Python MCP server that exposes Google Calendar as tools for Claude.

## Features

- **9 tools**: list/search/get/create/update/delete events, list/get calendars, check free/busy
- OAuth 2.0 browser flow on first run; tokens stored locally
- All logging goes to `stderr` — `stdout` stays clean for MCP stdio transport
- Architecturally ready for multi-user support

## Setup

### 1. Get Google OAuth credentials

**Enable the Google Calendar API:**

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. In the top bar, select your existing project from the project picker (or create a new one)
3. Go to `APIs & Services` → `Library`
4. Search for `Google Calendar API`
5. Open it and click `Enable`

> If you already enabled it before, you'll see `Manage` instead of `Enable` — you're good to go.

**Create OAuth credentials:**

1. Go to `APIs & Services` → `OAuth consent screen` and configure it if you haven't already (choose *External* for personal use)
2. Go to `APIs & Services` → `Credentials` → `Create credentials` → `OAuth client ID` → `Desktop app`
3. Copy the `Client ID` and `Client Secret` — you'll add them to your `.env` in the next step

### 2. Install

```bash
git clone https://github.com/your-org/strato-mcp-google-calendar
cd strato-mcp-google-calendar
uv venv && source .venv/bin/activate
uv pip install -e .
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and fill in GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
```

### 4. Authenticate (first run)

```bash
google-calendar-mcp
# Browser opens → sign in → grant calendar access → Ctrl+C once redirected
```

Tokens are saved to `~/.config/google-calendar-mcp/default.token.json`.

---

## Register with Claude

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "/absolute/path/.venv/bin/google-calendar-mcp",
      "env": {
        "GOOGLE_CLIENT_ID": "your_client_id",
        "GOOGLE_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add google-calendar /absolute/path/.venv/bin/google-calendar-mcp \
  --env GOOGLE_CLIENT_ID=your_client_id \
  --env GOOGLE_CLIENT_SECRET=your_client_secret
```

---

## Available Tools

| Tool | Description |
|---|---|
| `list_events_tool` | List upcoming events from a calendar |
| `search_events_tool` | Full-text search across events |
| `get_event_tool` | Retrieve a single event by ID |
| `create_event_tool` | Create a new event |
| `update_event_tool` | Patch an existing event |
| `delete_event_tool` | Delete an event |
| `list_calendars_tool` | List all calendars |
| `get_calendar_tool` | Get details for one calendar |
| `check_free_busy_tool` | Query busy intervals across calendars |

---

## Development

```bash
uv pip install -e ".[dev]"   # install with dev dependencies
pytest                        # run all 65 tests
```

### Project structure

```
src/google_calendar_mcp/
├── server.py          # FastMCP entry point
├── config.py          # Env-var config loading
├── auth/
│   ├── oauth.py       # OAuth flow
│   └── token_store.py # TokenStore ABC + FileTokenStore
├── calendar/
│   ├── client.py      # Google API client factory
│   ├── events.py      # Events API wrappers
│   ├── calendars.py   # CalendarList wrappers
│   └── freebusy.py    # FreeBusy wrapper
└── tools/
    ├── events.py      # MCP tool definitions
    ├── calendars.py
    └── freebusy.py
```

---

## Running with Docker

### 1. Build the image

```bash
docker build -t google-calendar-mcp:latest .
```

### 2. Authenticate (once)

Run the auth flow interactively. It will open a browser, save the token to a named volume, and exit:

```bash
docker run --rm -it -p 8081:8081 \
  -v google-calendar-tokens:/tokens \
  --env-file .env \
  google-calendar-mcp:latest auth
```

Credentials are read from `.env` — they do not appear in the shell command, shell history, or `ps` output.

### 3. Test locally

```bash
docker compose run --rm mcp
```

### 4. Register with Claude Desktop (Docker)

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "google-calendar-tokens:/tokens",
        "--env-file", "/absolute/path/to/.env",
        "google-calendar-mcp:latest",
        "serve"
      ]
    }
  }
}
```

Replace `/absolute/path/to/.env` with the full path to your `.env` file. Claude Desktop launches docker from an unspecified working directory, so a relative path will not work.

### 5. Register with Claude Code (Docker)

```bash
claude mcp add google-calendar -- \
  docker run --rm -i \
    -v google-calendar-tokens:/tokens \
    --env-file /absolute/path/to/.env \
    google-calendar-mcp:latest serve
```

(`-i` keeps stdin open for the MCP stdio transport.)

---

## Configuration reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | Yes | — | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | — | OAuth client secret |
| `GOOGLE_REDIRECT_URI` | No | `http://localhost:8081` | OAuth redirect URI |
| `TOKEN_STORE_PATH` | No | `~/.config/google-calendar-mcp/` | Token storage directory |
| `GOOGLE_SCOPES` | No | `https://www.googleapis.com/auth/calendar` | OAuth scopes (comma-separated) |
| `DEFAULT_CALENDAR_ID` | No | `primary` | Default calendar |
| `LOG_LEVEL` | No | `WARNING` | Log level (stderr only) |
