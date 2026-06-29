---
sidebar_position: 2
---

# Quickstart (Local Python)

Get a forked Strands Base Agent running locally in under five minutes. This path is best for active development — `just run` reloads quickly and you have direct access to the venv for debugging.

If you'd rather not install Python 3.14 and `uv` locally, see the [Docker Compose quickstart](./quickstart-docker.md).

## Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/) >= 0.9 (matches the version pinned in `Dockerfile`)
- [just](https://github.com/casey/just) command runner
- AWS credentials with Bedrock access (default model provider)
- Access to install `foundry-agent-*` packages from your team's package registry

## Install

1. Clone (or fork) the repository:

   ```bash
   git clone <repo-url>
   cd strands-base-agent
   ```

2. Install dependencies and pre-commit hooks:

   ```bash
   just setup
   ```

   `foundry-agent-*` packages are pulled from your team's package registry. The `pyproject.toml` ships with a `[[tool.uv.index]]` entry pointing at the internal JFrog Artifactory PyPI registry. If `uv sync` or `uv lock` fails to resolve `foundry-agent-*`, verify network access to that index.

3. Configure the environment:

   ```bash
   cp env.template .env
   # Edit .env with your AWS profile or credentials
   ```

4. Edit `config.yaml` with your model and agent settings:

   ```yaml
   model:
     provider: bedrock
     model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0

   agent_name: my-agent
   system_prompt: >
     You are an AI assistant specialized in your domain.
   ```

## Run

Start the HTTP server:

```bash
just run
```

Or run a one-shot CLI query:

```bash
just demo "Tell me about Python"
```

## Verify

With the server running, hit the health endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

You should receive a JSON response with `"status": "healthy"`. Then test a query:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}' | jq .
```

## What's Next

- **[Configuration](./configuration/index.md)** — full reference for `config.yaml` and env var overrides
- **[Adding tools](./guides/adding-tools.md)** — give your agent domain-specific capabilities
- **[Customizing the server](./guides/customizing-server.md)** — wire in custom session managers or model providers
