# Changelog

All notable changes to `strands-base-agent` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-06-30

Packaging fix so a fresh clone installs without access to internal
infrastructure. v1.0.0 shipped with `uv.lock` resolving the four
`foundry-agent-*` wheels from a private Booz Allen JFrog index; the
packages are now public on GitHub Releases, and this release repoints
the lockfile accordingly.

### Changed

- `pyproject.toml` — the four `foundry-agent-*` dependencies now use
  direct-URL specs pointing at
  [`boozallen/foundry-agent-packages`](https://github.com/boozallen/foundry-agent-packages)
  GitHub Release wheels. `[tool.hatch.metadata] allow-direct-references = true`
  added so Hatchling accepts the URL specs in this repo's own metadata.
- `uv.lock` — regenerated; no longer references the internal JFrog index.

### Added

- README — "Installing the `foundry-*` packages" section documenting the
  GitHub-Release install path (for evaluation / POCs) and the intended
  adoption pattern (mirror wheels into an internal index for production).
- AGENTS.md — one-line pointer to the README install note.

## [1.0.0] - 2026-06-29

Initial public release of the Strands Base Agent — a baseline starter repo
that teams fork into their own environment and customize for their use case.
Shared infrastructure (DI, lifecycle, middleware, retry, OTel, tool loading)
lives in the published `foundry-agent-*` packages; this repo is the
composition root that wires them into a runnable service.

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
- **Security artifacts** — STIG checklist (`security/stig_checklist.json`).

### Notes

- GitHub Actions workflows (CI/CD, CodeQL) are intentionally not included
  in this initial scaffold; corresponding badges were removed from the
  README.
- `develop` is the primary integration branch for this OSS repo.