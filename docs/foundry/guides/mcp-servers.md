---
sidebar_position: 5
---

# MCP Servers

MCP (Model Context Protocol) servers add capabilities to your agent — GitHub integration, file operations, custom tool services. The agent discovers and uses these tools automatically once they're configured.

## Configure in `config.yaml`

YAML is the recommended way to declare MCP servers, since the config is structured:

```yaml
mcp_servers:
  - name: github
    url: https://api.githubcopilot.com/mcp/
    headers:
      Authorization: "Bearer ${GITHUB_PAT}"

  - name: local-tools
    url: http://localhost:8080/mcp
```

Fields:

- **`name`** *(optional)* — human-readable identifier
- **`url`** *(required)* — MCP server endpoint URL
- **`headers`** *(optional)* — request headers, useful for auth tokens

YAML supports `${VAR}` substitution for secrets, so your token stays in `.env` rather than being committed.

## Example: GitHub MCP Server

The official GitHub MCP server gives the agent access to repositories, issues, and pull requests.

### 1. Generate a Personal Access Token

In GitHub: **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token**.

Recommended scopes:

- `repo` — full control of private repositories
- `read:org` — read org and team membership
- `read:user` — read user profile data

### 2. Add the Token to `.env`

```bash
# .env
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
```

### 3. Add the Server to `config.yaml`

```yaml
mcp_servers:
  - name: github
    url: https://api.githubcopilot.com/mcp/
    headers:
      Authorization: "Bearer ${GITHUB_PAT}"
```

### 4. Use It

```bash
just demo "List the recent issues in my repository"
just demo "Show me pull requests that need review"
```

## Reconnection Behavior

The base agent wraps the underlying Strands agent in a `ReconnectingAgentProxy` that recreates the agent if an MCP connection drops mid-request. Failed requests retry once before surfacing a `mcp_reconnect_failed` error to the caller. This behavior is in `server.py` and applies to both sync and streaming endpoints.
