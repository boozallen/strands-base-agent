---
sidebar_position: 1
---

# After You Fork

A short tour of what to change once you've forked Strands Base Agent for your own agent. Follow [Quickstart (Local Python)](../quickstart.md) or [Quickstart (Docker Compose)](../quickstart-docker.md) first to confirm the unmodified agent runs.

## 0. Pin Your Version

Pin your fork to a release tag. Don't track `develop`.

```bash
git clone --branch <tag> <repo-url>
```

Three things can break if you don't pin.

- **Upstream changes.** `develop` changes all the time. Some changes break things. Check the [`CHANGELOG.md`](../../../CHANGELOG.md) `### Breaking` entries.
- **`foundry-agent-*` packages.** This repo pins their versions in [`pyproject.toml`](../../../pyproject.toml). A merge from `develop` can change those versions under code you already changed.
- **The Docker base image.** The [`Dockerfile`](../../../Dockerfile) uses the Chainguard `python:latest-dev` tag. This tag floats. See [`AGENTS.md`'s "Things to leave alone"](../../../AGENTS.md#things-to-leave-alone) note on the Python version. Even a pinned checkout can get a different base image on a later rebuild. Pin the image digest too if you need reproducible builds.

To get an upstream fix later, compare your fork to the tag you pinned. Don't merge all of `develop`.

## 1. Set Agent Identity

Edit [`config.yaml`](../../../config.yaml):

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

Default is AWS Bedrock with Claude Haiku. To use a different Bedrock model, such as Sonnet, set
`model_id` to its latest inference profile in your region (`aws bedrock list-inference-profiles`
lists them):

```yaml
model:
  provider: bedrock
  model_id: <latest Sonnet inference profile ID>
  streaming: true
```

For Ollama or LlamaCpp, set `provider: ollama` or `provider: llamacpp` and the matching `*_url` field. See [Configuration](../configuration/index.md) for the full schema.

## 3. Add Domain Tools

Drop a Python file into [`strands_base_agent/tools/`](../../../strands_base_agent/tools/) with `@tool`-decorated functions, then point `config.yaml` at it:

```yaml
tools_dir: strands_base_agent/tools
tools_files:
  - strands_base_agent/tools/finance_tools.py
```

Tools load only from inside `tools_dir`, and only [`strands_base_agent/`](../../../strands_base_agent/) is copied into the Docker image.

See [Adding Tools](./adding-tools.md) for the details.

## 4. Add API Endpoints (If Needed)

The default agent exposes `/api/v1/query`, `/api/v1/query/stream`, and chat history routes — see the [Built-in HTTP API](./http-api.md) reference for request/response shapes and the SSE event format. If your agent needs custom endpoints (file upload, batch processing, domain-specific reads), see [Adding API Endpoints](./adding-api-endpoints.md).

## 5. Wire External Services

- **MCP servers** — declarative config in `config.yaml`. See [MCP Servers](./mcp-servers.md).
- **A2A agents** — declarative config in `config.yaml` for delegating to other agents.
- **Custom session managers / model providers** — registered in [`server.py`](../../../strands_base_agent/server.py). See [Customizing the Server](./customizing-server.md).

## 6. Update the README

Replace the starter README's content with what your fork actually does. Adopters and reviewers should be able to learn the agent's purpose without reading code.

## 7. Run the Quality Gate

Before pushing changes:

```bash
just check  # lint, format, type-check, test
```

## What You Don't Need to Touch

These responsibilities live upstream in `foundry-agent-*` packages and should not be reimplemented in the fork:

- Tool loading ([`foundry-strands-agent`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-strands-agent/index.md))
- OpenTelemetry instrumentation, retry logic, shutdown handlers
- DI container, agent protocols, lifecycle hooks
- Middleware (CORS, error handling, request logging)

If you find yourself reaching to rewrite one of these, that's a signal the work belongs in a package PR, not in your fork.
