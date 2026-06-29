---
sidebar_position: 1
---

# After You Fork

A short tour of what to change once you've forked Strands Base Agent for your own agent. Follow the [Local Python](../quickstart.md) or [Docker Compose](../quickstart-docker.md) quickstart first to confirm the unmodified agent runs.

## 1. Set Agent Identity

Edit `config.yaml`:

```yaml
agent_name: finance-analyzer
agent_description: Analyzes quarterly finance reports and answers questions about them.
agent_version: "1.0"

system_prompt: >
  You are a financial analyst assistant. You answer questions about
  quarterly reports using the tools available to you. Cite sources
  when summarizing data.
```

Agent name flows through to the A2A agent card discovery endpoint at `/.well-known/agent-card.json`.

## 2. Pick a Model

Default is AWS Bedrock with Claude Haiku. To use a different model or provider:

```yaml
model:
  provider: bedrock
  model_id: us.anthropic.claude-sonnet-4-20250514-v1:0
  temperature: 0.2
  streaming: true
```

For Ollama or LlamaCpp, set `provider: ollama` or `provider: llamacpp` and the matching `*_url` field. See [Configuration](../configuration/index.md) for the full schema.

## 3. Add Domain Tools

Drop a Python file into `tools/` with `@tool`-decorated functions, then point `config.yaml` at it:

```yaml
tools_files:
  - ./tools/finance_tools.py
```

See [Adding Tools](./adding-tools.md) for the details.

## 4. Add API Endpoints (If Needed)

The default agent exposes `/api/v1/query`, `/api/v1/query/stream`, and chat history routes — see the [Built-in HTTP API](./http-api.md) reference for request/response shapes and the SSE event format. If your agent needs custom endpoints (file upload, batch processing, domain-specific reads), see [Adding API Endpoints](./adding-api-endpoints.md).

## 5. Wire External Services

- **MCP servers** — declarative config in `config.yaml`. See [MCP Servers](./mcp-servers.md).
- **A2A agents** — declarative config in `config.yaml` for delegating to other agents.
- **Custom session managers / model providers** — registered in `server.py`. See [Customizing the Server](./customizing-server.md).

## 6. Update the README

Replace the starter README's content with what your fork actually does. Adopters and reviewers should be able to learn the agent's purpose without reading code.

## 7. Run the Quality Gate

Before pushing changes:

```bash
just check  # lint, format, type-check, test
```

## What You Don't Need to Touch

These responsibilities live upstream in `foundry-agent-*` packages and should not be reimplemented in the fork:

- Tool loading (`foundry-strands-agent`)
- OpenTelemetry instrumentation, retry logic, shutdown handlers
- DI container, agent protocols, lifecycle hooks
- Middleware (CORS, error handling, request logging)

If you find yourself reaching to rewrite one of these, that's a signal the work belongs in a package PR, not in your fork.
