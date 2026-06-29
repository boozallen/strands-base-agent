---
sidebar_position: 3
---

# Quickstart (Docker Compose)

Get a forked Strands Base Agent running in a container in under five minutes. This is the lower-friction path when you don't want to install Python 3.14 and `uv` locally — Docker builds the image and runs the agent the same way it will run in higher environments.

For active development with hot reload, see the [Local Python quickstart](./quickstart.md) instead.

## Prerequisites

- Docker Desktop (or any Docker engine) with Compose v2
- AWS credentials with Bedrock access — typically AWS SSO logged in via `~/.aws/sso/cache/`
- Access to install `foundry-agent-*` packages from your team's package registry (used during the image build)

## Install

1. Clone (or fork) the repository:

   ```bash
   git clone <repo-url>
   cd strands-base-agent
   ```

2. Configure the environment:

   ```bash
   cp env.template .env
   ```

   At minimum, set `AWS_PROFILE` to a profile in `~/.aws/config` that has Bedrock access. The compose file bind-mounts `~/.aws` into the container so SSO sessions are reused without copying credentials into the image.

3. Edit `config.yaml` with your model and agent settings:

   ```yaml
   model:
     provider: bedrock
     model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0

   agent_name: my-agent
   system_prompt: >
     You are an AI assistant specialized in your domain.
   ```

   :::info config.yaml is baked in at build time
   `config.yaml` is `COPY`'d into the image by the `Dockerfile`. After editing it, rebuild with `docker compose up --build` (or `docker compose build`) — restarting alone won't pick up the change. Secrets and per-environment values come from `.env` at run time and don't require a rebuild.
   :::

## Run

Build the image and start the agent:

```bash
docker compose up --build
```

The first build pulls `foundry-agent-*` packages from your registry — make sure your network can reach it. Subsequent runs without `--build` start instantly.

## Verify

In another terminal, hit the health endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

You should receive a JSON response with `"status": "healthy"`. The compose file also runs this same check internally — `docker compose ps` shows the container as `healthy` once it passes.

Then test a query:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}' | jq .
```

## What's mounted, what persists

The default `compose.yaml` wires up two volumes:

| Mount | Source | Purpose |
|---|---|---|
| `~/.aws` (bind) | host | Reuse host AWS SSO sessions inside the container |
| `strands_sessions` (named) | docker volume | Persist `FileSessionManager` state across restarts |

Sessions survive `docker compose down`. To wipe them, `docker compose down -v`.

## Tuning the compose file

`compose.yaml` ships with sensible defaults; common customizations:

- **Port** — change the host side of `"$PORT:8000"` (or set `PORT` in `.env`) to avoid collisions with other agents on the same machine.
- **Container / service name** — rename the `strands-agent` service to your agent's name so logs and `docker compose ps` are easier to read.
- **Network** — the file declares an `agentic-platform` network; mark it `external: true` if you're sharing it with other agents or services.
- **Health check cadence** — `interval: 10s`, `timeout: 5s`, `retries: 5` by default; tune if startup is slow in your environment.

See [Configuration → Docker Configuration](./configuration/index.md#docker-configuration) for the full set of compose-related settings.

## What's Next

- **[Configuration](./configuration/index.md)** — full reference for `config.yaml` and env var overrides
- **[Adding tools](./guides/adding-tools.md)** — give your agent domain-specific capabilities
- **[Customizing the server](./guides/customizing-server.md)** — wire in custom session managers or model providers
