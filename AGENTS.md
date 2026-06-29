# AGENTS.md - Strands Base Agent (Starter Repo)

This file provides guidance for AI assistants and human contributors working
with this codebase.

## What this repo is

A baseline starter repo from the Agent Foundry team, used to accelerate
client delivery and team POCs. You forked or cloned it to build an agent
for a specific use case in your own environment. This repo is the
**composition root** — it wires `foundry-agent-*` packages into a runnable service. The shared infrastructure
(DI, lifecycle, middleware, retry, OTel, tool loading) lives in those
packages, not here.

What this repo provides directly:

- A composition root that wires the packages together (`server.py`)
- HTTP API routes for query processing and chat history
- A2A protocol server for multi-agent communication
- A `config.yaml` for YAML-first configuration
- A `tools/` directory for domain-specific tools

## First 90 seconds after forking

1. `just setup` — installs dependencies and pre-commit hooks
2. Edit `config.yaml` — set `model`, `agent_name`, `system_prompt`
3. `cp env.template .env` — set AWS Bedrock credentials
4. `just demo "Tell me about Python"` — verify the agent runs

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

- `openspec/specs/` documents the **baseline capabilities** this repo ships
  with — read these to understand what already exists before proposing
  changes. They are useful even if you never write a new spec yourself.
- `openspec/changes/` is where new proposals live. The `openspec` CLI
  (or matching slash commands in your coding agent) drives the workflow.
- See `openspec/config.yaml` for project orientation passed to coding agents.

## Security posture & STIG tracking

This repo ships with a baseline assessment against the DISA Application
Security and Development (ASD) STIG. The intent is to give adopters
pursuing ATO-style requirements a head start: the controls inherited
from the baseline are pre-recorded, and what remains is whatever the
adopter adds on top of it.

- `security/stig_checklist.json` — machine-readable checklist of every
  STIG finding, with `status`, `responsibility` (baseline vs. adopter),
  `finding_details`, and longer-form `comments` per control. This is
  the single file to update as the baseline (or your fork) evolves —
  evidence lives inside it, not alongside it.
- `security/README.md` — orientation for the directory, including how
  to refresh the checklist and what to put in `finding_details` vs.
  `comments`.

**Treat the checklist as a recommended template, not a hard requirement.**
Adopters in regulated environments should keep it current alongside code
changes. Adopters with no compliance obligation can tailor or remove it.

**Keeping it current.** Two patterns work; pick whichever matches your
team's level of AI adoption:

- *Skill-driven (what the Foundry team uses internally):* coding agents
  drive the assessment via `foundry-stigkit`-backed skills. These are
  tooling not included in this repo, but the pattern (run a domain
  assessment, triage findings, update the JSON) is reproducible with
  any coding agent and the JSON schema in the file.
- *Manual / traditional:* edit `security/stig_checklist.json` directly
  when a code change affects a control. Use the `responsibility` field
  to mark whether the control is satisfied by the baseline or by an
  adopter overlay.

When a change touches a STIG-relevant area (auth, authz, crypto, audit
logging, session handling, data handling, input validation), update the
checklist in the same PR.

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
  model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0
  temperature: 0.3
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
just setup              # Install deps + pre-commit hooks
just run                # Start A2A server on :8000
just demo               # Run CLI with test query
just test               # All tests
just lint               # Ruff linting
just dead-code          # Advisory vulture scan (not part of check/ci)
just check              # All quality checks (lint, format, type-check, test)
```

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
# Custom session manager
container.register_factory(
    AgentFactory,
    lambda: StrandsAgentFactory(
        container,
        session_manager_factories={
            "file": _default_file_session_manager,
            "s3": _default_s3_session_manager,
            "dynamodb": my_dynamodb_factory,
        },
    ),
    singleton=True,
)
```

The `AgentBackend` protocol enables future framework adapters (LangChain, CrewAI) without changing the starter repo's API layer.

## Testing

- Unit tests in `tests/unit/` test starter repo code (routes, factory, dependencies)
- Integration tests in `tests/integration/` test tool loading and startup
- Package tests live in the `foundry-agent-packages` monorepo

```bash
just test               # Run all tests
just test-unit          # Unit tests only
just test-integration   # Integration tests only
```

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
- Python 3.14 is required (any 3.14.x — see `pyproject.toml`)

## Documentation

- `env.template` — environment variable reference
- `CONTRIBUTING.md` — development process, commit/PR conventions
- `security/README.md` — STIG checklist and security posture
- See `docs/foundry/` for deeper guides (configuration, MCP setup, tool authoring, server customization). This is the same content published to the Agent Foundry docs site.
