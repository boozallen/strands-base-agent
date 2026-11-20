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

### Credentials require `https`

An entry that sends a credential must use `https`. A credential is a credential-bearing header (`Authorization`, `Cookie`, `X-Api-Key`, and similar) or a `user:token@` in the url. Otherwise config load fails with `InvalidConfigurationError`. This applies to `a2a_servers` too. An `https` MCP server that redirects to `http` is also refused. Entries with no credential, like `local-tools` above, can use `http`.

If TLS is terminated outside the agent process, such as by a service-mesh sidecar, the deployer can opt in:

```yaml
allow_insecure_credentialed_endpoints: true   # default false; logs a warning per entry
```

You can also set `STRANDS__ALLOW_INSECURE_CREDENTIALED_ENDPOINTS=true` in the environment.

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

The A2A server builds a fresh agent per conversation (`contextId`), and every agent shares the same MCP clients. Each client is a `ReconnectingMCPClient` from [`foundry-strands-agent`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-strands-agent/index.md), which reopens a dropped MCP connection in place. One reconnect restores MCP tools in every cached conversation, with no agent rebuilt.

The server builds one agent at startup, so every MCP server connects when the server starts. If an MCP server can't be reached or is misconfigured, startup fails with the error instead of the first A2A request failing later.

- A tool call that fails after it was sent returns its error and is not re-sent, because the MCP server may already have run the tool. The next tool call reconnects first.
- Concurrent tool calls share one reconnect.
- After 5 failed reconnects in a row, tool calls fail fast for 60 seconds, then one reconnect is tried again.

The `/api/v1/query` endpoint has its own circuit breaker, which stops calling a failing MCP server after repeated errors.
