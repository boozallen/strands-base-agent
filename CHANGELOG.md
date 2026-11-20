# Changelog

All notable changes to `strands-base-agent` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [4.0.0] - 2026-11-19

### Features

- add optional mTLS support for native TLS mode
- add circuit breaker to MCP reconnection

### Fixes

- mask and bound session_id in chat history logs
- bump pydantic-settings to 2.14.2
- pass AgentConfig to ChatHistorian factory registration
- _LazyAgentProxy crashes A2A executor on first request
- use exclude_also so coverage built-in exclusions stay in effect
- use extend-exclude to skip openspec and docs from ruff
- resolve AgentConfig from container in start_server()
- upgrade foundry-agent-packages pins
- disable session-list endpoint by default
- rename STRANDS_TLS_MODE value 'platform' to 'off'
- raise floors for open Dependabot/Grype alerts
- let the Compose container read the host AWS login on WSL
- make chat session delete opt-in and fix existence check
- pin compose container port so PORT sets the host port only
- isolate A2A conversations with per-context agent_factory
- bump filelock, virtualenv and OpenTelemetry for Dependabot alerts
- share AWS login safely from Windows and Linux in Docker Compose
- turn on A2A-compliant streaming in the A2A server
- raise the pyasn1 floor to 0.6.5
- bump opentelemetry and soupsieve for CVE fixes

### Maintenance

- Security and maintenance updates
- Dependency updates
- document nims and region_name model config fields
- add unit tests for _LazyAgentProxy snapshot methods
- document outbound mTLS env vars in env.template
- standardize justfile quality/test recipes
- add --strict-markers and --strict-config to pytest addopts
- exclude openspec/changes/ from ruff format
- update foundry-agent-* package versions
- fix guides that don't match the code
- Upgrade to Python 3.15 (Chainguard base image bump)
- tell adopters to pin a release tag when forking
- rebuild on latest Chainguard base image
- drop "production-ready" from the guardrails guide
- guardrails links, publish the TLS guide, and clean up the docs links
- add OpenAPI spec for query endpoints

## [1.0.1] - 2026-06-30

### Changed

- `pyproject.toml` — the four `foundry-agent-*` dependencies now use
  direct-URL specs pointing at
  [`boozallen/foundry-agent-packages`](https://github.com/boozallen/foundry-agent-packages)
  GitHub Release wheels. `[tool.hatch.metadata] allow-direct-references = true`
  added so Hatchling accepts the URL specs in this repo's own metadata.
- `uv.lock` — regenerated against the public GitHub Release wheels.

### Added

- README — "Installing the `foundry-*` packages" section documenting the
  GitHub-Release install path (for evaluation / POCs) and the intended
  adoption pattern (mirror wheels into an internal index for production).
- AGENTS.md — one-line pointer to the README install note.

## [1.0.0] - 2026-06-29

### Added

- **Runtime package** (`strands_base_agent/`) — FastAPI composition root,
  A2A agent server, application factory, lifecycle management, runtime
  container, TLS config, and query/chat-history/health API routes.
- **Test suite** (`tests/`) — unit coverage for API routes, application
  factory/lifecycle, runtime container, TLS config, A2A server, and main
  entrypoint; integration tests for tool loading, concurrent MCP dispatch,
  and application startup.
- **Tooling & packaging** — `pyproject.toml` (Python 3.13, version 1.0.0),
  `uv.lock`, `Dockerfile`, `compose.yaml`, `justfile`,
  `.pre-commit-config.yaml`, `.grype.yaml`.
- **Governance** — `LICENSE`, `NOTICE`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CODEOWNERS`, GitHub issue templates, Dependabot config, PR template.
- **Documentation** (`docs/foundry/`) — quickstart (local + Docker),
  configuration reference (environment variables), and guides for
  guardrails, A2A protocol, HTTP API, MCP servers, tool integration,
  adding API endpoints, customizing the server, embedding the query
  process, and post-fork workflows.
- **AI assistant integrations** — Claude Code, Cursor, and GitHub Copilot
  skill/prompt scaffolding; OpenSpec workflow (`openspec/`) initialized
  with a clean changes archive.

### Notes

- GitHub Actions workflows (CI/CD, CodeQL) are intentionally not included
  in this initial scaffold; corresponding badges were removed from the
  README.
- `develop` is the primary integration branch for this OSS repo.