# AGENTS.md - Strands Base Agent (Starter Repo)

This file provides guidance for AI assistants and human contributors working
with this codebase.

## What this repo is

A baseline starter repo from the Agent Foundry team, used to accelerate
client delivery and team POCs. You forked or cloned it to build an agent
for a specific use case in your own environment. This repo is the
**composition root** — it wires `foundry-agent-*` packages (installed
from the package locations configured in `pyproject.toml`) into a
runnable service. The shared infrastructure (DI, lifecycle, middleware,
retry, OTel, tool loading) lives in those packages, not here.

What this repo provides directly:

- A composition root that wires the packages together (`server.py`)
- HTTP API routes for query processing and chat history
- A2A protocol server for multi-agent communication
- A `config.yaml` for YAML-first configuration
- A `tools/` directory for domain-specific tools

## First 90 seconds after forking

1. `just setup` — syncs dependencies and installs pre-commit hooks
2. Edit `config.yaml` — set `model`, `agent_name`, `system_prompt`
3. `cp env.template .env` — set `STRANDS_API_KEY` and AWS Bedrock credentials
4. `just demo "Tell me about Python"` — verify the agent runs
5. `just dev` — start the A2A server locally on :8000

## Two ways to extend this baseline

You can use either or both. Adopters choose based on team practice.

### Path A — Direct extension (default)

Open your coding agent, describe what you want, let it modify code. Best for
small or exploratory changes.

- Add tools in `tools/`
- Add API routes in `api/routes/`
- Add MCP servers in `config.yaml`
- Customize session managers / model providers in `server.py`

### Path B — Spec-driven via OpenSpec (opt-in)

For larger changes where you want a written proposal before code lands.

- `openspec/` holds only `config.yaml` in this copy. The `openspec` CLI
  (or matching slash commands in your coding agent) creates
  `openspec/changes/` for new proposals and `openspec/specs/` for
  capability specs as you use it.
- See `openspec/config.yaml` for project orientation passed to coding agents.

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                   Starter Repo (this repo)            │
├──────────────────────────────────────────────────────┤
│  server.py           - Composition root, A2A server  │
│  application/        - DI container setup, lifecycle │
│  api/routes/         - Query, streaming, chat history│
│  api/dependencies.py - FastAPI DI bridge             │
│  config.yaml         - Default configuration         │
│  tools/              - Domain-specific tools          │
└──────────────────────────────────────────────────────┘
                         │ pip install
                         ▼
┌──────────────────────────────────────────────────────┐
│               foundry-agent-* Packages                │
├──────────────────────────────────────────────────────┤
│  foundry-agent-core   - DI, protocols, types,        │
│                         exceptions, lifecycle         │
│  foundry-agent-config - YAML loader + env overrides  │
│  foundry-agent-fastapi- Middleware, models, mappers,  │
│                         health router                 │
│  foundry-strands-agent- StrandsAgentBackend, factory, │
│                         orchestrator, tool_loader,    │
│                         chat historian, config models │
└──────────────────────────────────────────────────────┘
```

## File Structure

```
strands_base_agent/
├── __init__.py              # Package root
├── __main__.py              # CLI entry point
├── main.py                  # process_query() function
├── server.py                # Composition root + A2A server
├── application/
│   ├── factory.py           # DI container setup
│   ├── lifecycle.py         # Startup/shutdown
│   └── runtime_container.py # Process-wide container singleton
├── api/
│   ├── dependencies.py      # FastAPI DI bridge
│   └── routes/
│       ├── query.py         # Query + streaming endpoints
│       └── chat_history.py  # Chat history endpoints
└── tools/
    └── __init__.py          # Custom tools go here
```

## Key Files

| File | Purpose |
|------|---------|
| `server.py` | Composition root. Registers `AgentFactory` and `AgentBackend` in the DI container. Adopters customize session managers and model providers here. |
| `application/factory.py` | Creates the DI container and registers infrastructure services. Loads config from `config.yaml` with env var fallback. |
| `application/lifecycle.py` | Startup/shutdown lifecycle. Signal handlers, logging init. |
| `api/dependencies.py` | FastAPI dependency injection bridge. Resolves `AgentBackend`, `AgentService`, `ChatHistoryManager` from the container. |
| `api/routes/query.py` | `POST /api/v1/query` (sync via `AgentBackend`) and `POST /api/v1/query/stream` (SSE via `AgentService`). |
| `api/routes/chat_history.py` | CRUD endpoints for chat session history. Injects `ChatHistoryManager` directly. |
| `config.yaml` | Default YAML configuration. Env vars override using double-underscore nesting (`STRANDS__MODEL__PROVIDER`). |
| `main.py` | Interface-agnostic `process_query()` for CLI, Lambda, scripts. |

## Packages

Pinned versions live in `pyproject.toml`; this table only describes what each
package provides.

| Package | What It Provides |
|---------|-----------------|
| `foundry-agent-core` | `AgentBackend` protocol, `AgentRequest`/`AgentResponse`/`TokenUsage` types, `DependencyContainer`, exception hierarchy, lifecycle/retry |
| `foundry-agent-config` | `load_config()` function. YAML primary, env var overrides with type coercion. |
| `foundry-agent-fastapi` | CORS/error/logging middleware, `QueryAPIRequest`/`QueryAPIResponse` models, health router, mappers |
| `foundry-strands-agent` | `StrandsAgentBackend`, `StrandsAgentFactory`, `QueryOrchestrator`, `ChatHistorian`, `AgentService`, tool loader, config models |

## Configuration

YAML is the primary config source. Environment variables override YAML values.

```yaml
# config.yaml
model:
  provider: bedrock
  model_id: us.anthropic.claude-haiku-5-5
  streaming: true

agent_name: strands-base-agent
system_prompt: "You are a helpful AI assistant..."
```

Env var overrides use double-underscore nesting:

| YAML path | Env var |
|-----------|---------|
| `model.provider` | `STRANDS__MODEL__PROVIDER` |
| `model.model_id` | `STRANDS__MODEL__MODEL_ID` |
| `agent_name` | `STRANDS__AGENT_NAME` |

See `docs/foundry/configuration/index.md` for the full guide including the composed config pattern for domain-specific fields.

## Development Commands

```bash
# Setup & Dependencies
just sync                # Sync the virtual environment with the lockfile
just setup               # sync + install pre-commit hooks

# Code Quality
just lint                # Ruff lint + the bandit command-injection sink set
just lint-fix            # Auto-fix ruff lint findings
just format              # Check code formatting (does not modify files)
just format-fix          # Auto-format code
just type-check          # basedpyright type checking
just check               # Every quality gate: lint, format, type-check, test

# Testing
just test                # Whole tree: tests/ (unit + integration)
just test-unit           # tests/unit/ only
just test-integration    # tests/integration/ only (no coverage gate)

# Local Runtime
just dev                 # Start the A2A server on :8000 (alias: just run)
just demo                # Run the CLI demo against a prompt
just dead-code           # Advisory vulture scan (not part of `check`)
just up                  # Start the agent container (alias: just start)
just down                # Stop the container (alias: just stop)
just logs                # Follow logs (optionally: just logs <service>)
just status              # Container status + health check
just build               # Build the agent Docker image
just reset               # Stop containers, clean artifacts, re-run setup

# Maintenance
just clean               # Remove build artifacts and tooling caches
just clean-all           # clean + this project's containers and volumes
```

The justfile is grouped into sections: Setup & Dependencies, Code Quality,
Testing, Local Runtime (repo-specific), then Maintenance. The section banners and
the comments for shared recipes are kept textually identical across the Foundry
single-package repos so the justfiles diff cleanly.
`just check` ends by printing `All quality checks passed`. Ruff and basedpyright
receive explicit path arguments rather than relying on config-driven discovery.
`just test-integration` treats "no tests collected" (pytest exit code 5) as
success and prints `No integration tests collected - not a failure.`, so the
recipe stays portable across repos that have no integration suite yet; this repo
does have one.

## Common Tasks

### Add a New Tool
1. Create tool function with `@tool` decorator (from strands SDK)
2. Place in `tools/` directory
3. Set `STRANDS__TOOLS_MODULES` or `STRANDS__TOOLS_FILES` in config

### Add API Endpoint
1. Create router in `api/routes/`
2. Add to `api/routes/__init__.py`
3. Register in `server.py`

### Customize Agent Behavior
1. Edit `config.yaml` for model, system prompt, tools
2. Add MCP servers in `config.yaml` under `mcp_servers`
3. Register custom session manager factories in `server.py`

### Extend Configuration (Domain-Specific)
See `docs/foundry/configuration/index.md` for the composed config pattern. Wrap `StrandsAgentConfig` in a custom Pydantic model with your domain fields.

## Extension Points

Adopters customize by editing `server.py` (the composition root):

```python
# Custom model provider
container.register_factory(
    AgentFactory,
    lambda: StrandsAgentFactory(
        container,
        model_provider_factories={"my-provider": my_model_factory},
    ),
    singleton=True,
)
```

Set `model.provider: my-provider` in `config.yaml`. `my_model_factory` receives
the config as a dict and returns a Strands model. The dict replaces the built-in
providers, so list every provider you use.

Only `file` and `s3` session backends are supported. Any other `session_type`
is rejected at startup.

The `AgentBackend` protocol enables future framework adapters (LangChain, CrewAI) without changing the starter repo's API layer.

## Testing

Tiering is by **directory**, not by marker: a test's tier is decided by where the
file lives, so it cannot be forgotten. No recipe passes `-m`.

- Unit tests in `tests/unit/` test starter repo code (routes, factory, dependencies)
- Integration tests in `tests/integration/` test tool loading and startup
- Package tests live in the `foundry-agent-packages` monorepo

```bash
just test               # Whole tree: tests/ (unit + integration)
just test-unit          # tests/unit/ only
just test-integration   # tests/integration/ only (no coverage gate)
```

Coverage reporting is always on via `[tool.pytest.ini_options]` addopts, both
terminal and HTML (written to `htmlcov/`), so there is no separate coverage
recipe. The `integration` marker remains declared as a trait tag, but nothing
selects on it. Unit test files use the `*_test.py` suffix here, which is why
`python_files` lists both `test_*.py` and `*_test.py`.

## Commit Guidelines

- One logical change per commit
- Each commit should compile and pass tests
- Small, incremental, reviewable diffs

```
<type>: <short description>

<optional body explaining why, not what>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

## Python Style

- Modern PEP 585 syntax: `list[int]`, `dict[str, Any]`, `X | Y | None`
- Use `%` interpolation in logging calls, never f-strings
- Pydantic v2: `@field_validator`, `model_config = {"frozen": True}`
- No mutable default arguments, no global mutable state, no staticmethod
- Prefer composition over inheritance

## Things to leave alone

These responsibilities live upstream in `foundry-agent-*` packages. If you
find yourself reaching to re-implement them in this repo, that's a signal the
work belongs in a package PR instead.

- `tool_loader.py` — lives in `foundry-strands-agent`, security-critical;
  never re-implement in this repo
- OTel instrumentation, retry logic, and shutdown handlers — provided by the
  packages; do not duplicate
- DI container, protocol definitions, lifecycle hooks — `foundry-agent-core`
  owns these
- Python 3.14 or newer is required (currently 3.15, tracking the
  Chainguard base image's floating tag — see `pyproject.toml`)

## Documentation

- `env.template` — environment variable reference
- `CONTRIBUTING.md` — development process, commit/PR conventions
- See `docs/foundry/` for deeper guides (configuration, MCP setup, tool authoring, server customization). This is the same content published to the Agent Foundry docs site.
