---
sidebar_position: 2
---

# Quickstart (Local Python)

Get a forked Strands Base Agent running locally in under five minutes. This path is best for active development — `just run` restarts in seconds after a code change (stop it with `Ctrl+C` and run it again) and you have direct access to the venv for debugging.

If you'd rather not install Python 3.14+ and `uv` locally, see the [Docker Compose quickstart](./quickstart-docker.md).

## Prerequisites

- Python 3.14 or newer (currently 3.15)
- [uv](https://docs.astral.sh/uv/) >= 0.9 (matches the version pinned in [`Dockerfile`](../../Dockerfile))
- [just](https://github.com/casey/just) command runner
- AWS credentials with Bedrock access (default model provider)
- Access to install `foundry-agent-*` packages from the package locations configured in [`pyproject.toml`](../../pyproject.toml)

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

   The `pyproject.toml` configures the package locations `uv` fetches `foundry-agent-*` packages from. If `uv sync` or `uv lock` fails to resolve `foundry-agent-*`, verify network access to those locations.

3. Configure the environment:

   ```bash
   cp env.template .env
   ```

   At minimum, set `STRANDS_API_KEY` and your AWS credentials:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Paste the result into `.env` as `STRANDS_API_KEY=<value>`. Also set `AWS_PROFILE` or export AWS credentials for Bedrock access.

4. Edit [`config.yaml`](../../config.yaml) with your model and agent settings:

   ```yaml
   model:
     provider: bedrock
     model_id: us.anthropic.claude-haiku-5-5

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
  -H "Authorization: Bearer <your-key>" \
  -d '{"query": "What is machine learning?"}' | jq .
```

## What's Next

- **[Configuration](./configuration/index.md)** — full reference for `config.yaml` and env var overrides
- **[Adding tools](./guides/adding-tools.md)** — give your agent domain-specific capabilities
- **[Customizing the server](./guides/customizing-server.md)** — wire in custom session managers or model providers
