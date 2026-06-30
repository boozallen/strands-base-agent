# Strands Base Agent

![Project Status: Available](https://img.shields.io/badge/status-available-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.1-blue)

A baseline starter repo from the Agent Foundry team. Teams fork this repo into their own environment and customize it for their use case. Shared infrastructure (DI, lifecycle, middleware, retry, OTel, tool loading) lives in the published `foundry-agent-*` packages — this repo is the composition root that wires them into a runnable service.

## Installing the `foundry-*` packages

The four `foundry-agent-*` wheels this repo depends on are published as
assets on [`boozallen/foundry-agent-packages`](https://github.com/boozallen/foundry-agent-packages)
GitHub Releases. The default `pyproject.toml` pins each package to its
GitHub Release wheel URL so a fresh clone runs out of the box — useful for
evaluation, demos, and POCs.

**Intended adoption pattern:** mirror the wheels into your own internal
package index (Artifactory, AWS CodeArtifact, Sonatype Nexus, GitLab
Package Registry, etc.) and repoint the dependency specs in `pyproject.toml`
at that index. Direct dependence on `github.com` release URLs is fine for
kicking the tires, but production deployments should resolve packages from
infrastructure you control.

## Where to go

| If you want to… | Read |
|---|---|
| Get the agent running locally with Python and `uv` | [Quickstart (Local Python)](docs/foundry/quickstart.md) |
| Get the agent running in a container | [Quickstart (Docker Compose)](docs/foundry/quickstart-docker.md) |
| Understand the codebase (file layout, packages, extension points) | [AGENTS.md](AGENTS.md) |
| Configure the model, system prompt, MCP servers, A2A peers | [Configuration guide](docs/foundry/configuration/index.md) |
| Add tools, API endpoints, guardrails, or customize the server | [Guides](docs/foundry/guides/index.md) — start with [After You Fork](docs/foundry/guides/after-you-fork.md) |
| Understand the security posture and STIG checklist | [security/README.md](security/README.md) |
| Contribute changes | [CONTRIBUTING.md](CONTRIBUTING.md) |
