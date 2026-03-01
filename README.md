# Stratosphere MCP Google Calendar

A Python MCP server that exposes Google Calendar as tools for AI assistants. Currently supporting **9 tools:** list, search, get, create, update, and delete events; list and get calendars; check free/busy intervals.

Compatible with Claude, Gemini CLI, OpenAI Codex, and any MCP-compatible client.


## Prerequisites

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


## Quick start (Docker)

### Step 1: Build

```bash
docker compose build
```

### Step 2: Configure

```bash
cp .env.example .env
# Fill in GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
```

> This file contains your OAuth credentials in plain text. Restrict its permissions:
> `chmod 600 .env`

### Step 3: Authenticate (once)

Run the auth service. It prints an authorization URL. Open it in your browser, sign in, and grant calendar access. The token is saved to the shared Docker volume and the command exits.

```bash
docker compose run --rm -p 8081:8081 auth
```

### Step 4: Register with your AI assistant

<details>
<summary><strong>Claude</strong></summary>

**Claude Desktop** — edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "google-calendar-mcp-tokens:/tokens",
        "--env-file", "/absolute/path/to/.env",
        "google-calendar-mcp:latest",
        "serve"
      ]
    }
  }
}
```

Replace `/absolute/path/to/.env` with the full path to your `.env` file. Claude Desktop
launches Docker from an unspecified working directory; relative paths do not work.

**Claude Code:**

```bash
claude mcp add --transport stdio google-calendar -- \
  docker run --rm -i \
    -v google-calendar-mcp-tokens:/tokens \
    --env-file /absolute/path/to/.env \
    google-calendar-mcp:latest serve
```

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

Edit `~/.gemini/settings.json` (or `.gemini/settings.json` in your project root for project-scoped config):

```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "google-calendar-mcp-tokens:/tokens",
        "--env-file", "/absolute/path/to/.env",
        "google-calendar-mcp:latest",
        "serve"
      ]
    }
  }
}
```

Replace `/absolute/path/to/.env` with the full path to your `.env` file.

</details>

<details>
<summary><strong>OpenAI Codex</strong></summary>

Edit `~/.codex/config.toml` (or `.codex/config.toml` in your project root for project-scoped config):

```toml
[[mcp_servers]]
name = "google-calendar"
command = "docker"
args = [
  "run", "--rm", "-i",
  "-v", "google-calendar-mcp-tokens:/tokens",
  "--env-file", "/absolute/path/to/.env",
  "google-calendar-mcp:latest",
  "serve"
]
```

Replace `/absolute/path/to/.env` with the full path to your `.env` file.

</details>


## Alternative: local install (without Docker)

### Step 1: Install

```bash
git clone https://github.com/stratosphereips/strato-mcp-google-calendar
cd strato-mcp-google-calendar
uv venv && source .venv/bin/activate
uv pip install -e .
```

### Step 2: Configure

```bash
cp .env.example .env
# Fill in GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
```

> This file contains your OAuth credentials in plain text. Restrict its permissions:
> `chmod 600 .env`

### Step 3: Authenticate (once)

Run the auth command. It prints an authorization URL — open it in your browser, sign in,
and grant calendar access. The token is saved to `~/.config/google-calendar-mcp/`.

```bash
google-calendar-auth
```

### Step 4: Register with your AI assistant

<details>
<summary><strong>Claude</strong></summary>

**Claude Desktop** — edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

> This file will contain your OAuth credentials in plain text. Restrict its permissions
> after editing: `chmod 600 ~/Library/Application\ Support/Claude/claude_desktop_config.json`.

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

**Claude Code:**

```bash
claude mcp add google-calendar /absolute/path/.venv/bin/google-calendar-mcp \
  --env-file /absolute/path/to/.env
```

> Avoid `--env KEY=VALUE` — credentials passed that way appear in shell history and `ps`.

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

Edit `~/.gemini/settings.json` (or `.gemini/settings.json` in your project root for project-scoped config):

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

> This file will contain your OAuth credentials in plain text. Restrict its permissions
> after editing: `chmod 600 ~/.gemini/settings.json`.

</details>

<details>
<summary><strong>OpenAI Codex</strong></summary>

Edit `~/.codex/config.toml` (or `.codex/config.toml` in your project root for project-scoped config):

```toml
[[mcp_servers]]
name = "google-calendar"
command = "/absolute/path/.venv/bin/google-calendar-mcp"

[mcp_servers.env]
GOOGLE_CLIENT_ID = "your_client_id"
GOOGLE_CLIENT_SECRET = "your_client_secret"
```

> This file will contain your OAuth credentials in plain text. Restrict its permissions:
> `chmod 600 ~/.codex/config.toml`.

</details>


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


## Configuration reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | Yes | — | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | — | OAuth client secret |
| `GOOGLE_REDIRECT_URI` | No | `http://localhost:8081` | OAuth redirect URI |
| `TOKEN_STORE_PATH` | No | `~/.config/google-calendar-mcp/` (local); `/tokens` (Docker) | Token storage directory |
| `GOOGLE_SCOPES` | No | `https://www.googleapis.com/auth/calendar` | OAuth scopes (comma-separated). The default grants full read/write access (create, update, delete). For read-only access use `https://www.googleapis.com/auth/calendar.readonly`. |
| `DEFAULT_CALENDAR_ID` | No | `primary` | Default calendar |
| `LOG_LEVEL` | No | `WARNING` | Log level (stderr only) |


## Development

```bash
uv pip install -e ".[dev]"
pytest                        # run all 88 tests
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
