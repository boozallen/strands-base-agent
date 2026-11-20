---
sidebar_position: 1
---

# Overview

Base agent runtime for deploying AI agents built on the AWS Strands Agents SDK.

Strands Base Agent is a baseline starter repo from the Agent Foundry team. It accelerates AI agent delivery for client engagements and team POCs by providing a FastAPI-based HTTP server wired to the AWS Strands Agents SDK, with shared infrastructure abstracted into published `foundry-agent-*` packages. Teams fork this repo into their own environment, configure their model and system prompt in [`config.yaml`](../../config.yaml), add domain-specific tools, and deploy.

## Key Features

- **YAML-first configuration** — All agent settings live in `config.yaml` with environment variable overrides using double-underscore nesting
- **Multi-provider LLM support** — AWS Bedrock, Ollama, and LlamaCpp via the Strands Agents SDK
- **A2A protocol server** — Built-in Agent-to-Agent communication with automatic agent card discovery at `/.well-known/agent-card.json`
- **MCP server integration** — Connect external tools via Model Context Protocol with declarative config
- **OpenTelemetry observability** — OTLP export for tracing and metrics out of the box

## Architecture

The application is a FastAPI server ([`strands_base_agent/server.py`](../../strands_base_agent/server.py)) that exposes REST endpoints for query, streaming, and chat history. A composition root ([`application/factory.py`](../../strands_base_agent/application/factory.py)) wires together [`foundry-agent-config`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-agent-config/index.md) (Pydantic-based configuration), [`foundry-agent-core`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-agent-core/index.md) (agent lifecycle), [`foundry-agent-fastapi`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-agent-fastapi/index.md) (route adapters), and [`foundry-strands-agent`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-strands-agent/index.md) (Strands SDK integration). Domain-specific tools are loaded from the [`tools/`](../../strands_base_agent/tools/) directory at startup. Session state is managed via pluggable backends (file-based or S3).

## Where to Go Next

- **[Quickstart (Local Python)](./quickstart.md)** — get a forked agent running in minutes with `uv` and `just`
- **[Quickstart (Docker Compose)](./quickstart-docker.md)** — same agent, containerized, no local Python install required
- **[Configuration](./configuration/index.md)** — tune the model, agent identity, and runtime behavior
- **[Guides](./guides/index.md)** — add tools, API endpoints, MCP servers, and guardrails
