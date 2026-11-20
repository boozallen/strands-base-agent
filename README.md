# Strands Base Agent

![Version](https://img.shields.io/badge/version-4.0.0-blue)

A baseline starter repo from the Agent Foundry team. Teams fork this repo into their own environment and customize it for their use case. Shared infrastructure (DI, lifecycle, middleware, retry, OTel, tool loading) lives in the published `foundry-agent-*` packages — this repo is the composition root that wires them into a runnable service.

All HTTP endpoints require bearer token authentication. Set `STRANDS_API_KEY` in your environment before starting the server. See [Environment Variables](docs/foundry/configuration/environment-variables.md#authentication) for details.

If you fork or copy this repo, pin to a release tag. Don't track `develop`. See [After You Fork](docs/foundry/guides/after-you-fork.md#0-pin-your-version) for why.

## Where to go

| If you want to… | Read |
|---|---|
| Get the agent running locally with Python and `uv` | [Quickstart (Local Python)](docs/foundry/quickstart.md) |
| Get the agent running in a container | [Quickstart (Docker Compose)](docs/foundry/quickstart-docker.md) |
| Understand the codebase (file layout, packages, extension points) | [AGENTS.md](AGENTS.md) |
| Configure the model, system prompt, MCP servers, A2A peers | [Configuration guide](docs/foundry/configuration/index.md) |
| Add tools, API endpoints, guardrails, or customize the server | [Guides](docs/foundry/guides/index.md) — start with [After You Fork](docs/foundry/guides/after-you-fork.md) |
| Understand the security posture | [SECURITY.md](SECURITY.md) |
| Contribute changes | [CONTRIBUTING.md](CONTRIBUTING.md) |
