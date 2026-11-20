---
sidebar_position: 3
---

# Quickstart (Docker Compose)

Get a forked Strands Base Agent running in a container in under five minutes. This is the lower-friction path when you don't want to install Python 3.14+ and `uv` locally — Docker builds the image and runs the agent the same way it will run in higher environments.

For active development, where you restart the server after each code change without rebuilding an image, see the [Local Python quickstart](./quickstart.md) instead.

## Prerequisites

- Docker Desktop (or any Docker engine) with Compose 2.8.0 or newer. Check with `docker compose version`. Older versions stop with `Invalid template`, because [`compose.yaml`](../../compose.yaml) uses `${OS:+...}`, which Compose added in 2.8.0.
- AWS credentials with Bedrock access — typically AWS SSO logged in via `~/.aws/sso/cache/`
- Access to install `foundry-agent-*` packages from the package locations configured in [`pyproject.toml`](../../pyproject.toml) (used during the image build)

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

   At minimum, set:

   - `STRANDS_API_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
   - `AWS_PROFILE` — a profile in `~/.aws/config` that has Bedrock access.

   The compose file bind-mounts `~/.aws` into the container so SSO sessions are reused without copying credentials into the image.

   On WSL, load `compose.wsl.yaml` too, so the container can read your `~/.aws`. `just up` does this for you. See [Run](#run).

   On Windows (PowerShell or Command Prompt), `compose.yaml` shares `~/.aws` read-only. It does this when `OS` is set, which Windows does in every shell. This stops the container from rewriting your AWS login, which would make it unreadable in WSL if WSL shares your Windows `.aws` folder. Because the container can't write `~/.aws`, it can't refresh your SSO login itself. AWS calls fail in the login's last 15 minutes.

   To keep the login fresh, run `aws sso login --profile <profile>` on Windows every 20 minutes, where `<profile>` is the `AWS_PROFILE` value from `.env`. Do this while you use the container. If your browser is still signed in to the AWS access portal, it finishes without asking you to sign in again. The container picks up the new login without a restart. If your login lasts less than 40 minutes, run it more often. The `expiresAt` value in the newest file in `~/.aws/sso/cache/` shows when your current login ends.

   If you miss a run, queries return a 500 and `docker compose logs strands-agent` shows `TokenRetrievalError`. Run `aws sso login --profile <profile>` on Windows to fix it.

   Known limitation: in the login's last 15 minutes, the container still asks AWS for a new token, but it can't save it. If AWS cancels the old token when it issues the new one, AWS calls on Windows fail too. Running `aws sso login --profile <profile>` every 20 minutes keeps the login out of its last 15 minutes, which avoids this.

   On Linux (not WSL), your `~/.aws` is readable only by you, so the container's built-in user (UID `65532`) can't read it. Run the container as you instead. Add this line to your shell profile (`~/.bashrc` or `~/.zshrc`), then open a new terminal:

   ```bash
   export STRANDS_HOST_UID="$(id -u)" STRANDS_CONTAINER_HOME=/aws-home
   ```

   This shares `~/.aws` at `/aws-home/.aws`, because `/home/nonroot` in the image is reachable only by UID `65532`. With these set, file-backed sessions (`session_type: file`) and tools that write under `$HOME` (such as MCP servers started with `uvx` or `npx`) aren't supported. Don't add it to root's profile, which would set `STRANDS_HOST_UID` to `0`.

   :::info Optional, WSL only: `~/.aws` shared from your Windows profile
   **Skip this on Mac, Windows, and Linux.** On WSL, run it only if one of these applies:

   - your WSL `~/.aws` (`sso`, `cli`, `config`, or `credentials`) links to your Windows `.aws` folder
   - `id -u` prints something other than `1000`

   In WSL, from the repo folder:

   ```bash
   if [ "$(id -u)" -eq 0 ]; then
     echo "Run this as your normal WSL user, not root."
   elif [ ! -f .env ]; then
     echo "Create .env first: cp env.template .env"
   else
     [ -z "$(tail -c1 .env)" ] || echo >> .env
     sed -i '/^\(STRANDS_HOST_UID\|AWS_LINK_[A-Z]*\)=/d' .env
     if [ "$(id -u)" -ne 1000 ]; then printf 'STRANDS_HOST_UID=%s\n' "$(id -u)" >> .env; fi
     for f in sso cli config credentials; do
       t=$(readlink ~/.aws/$f) || continue
       case "$t" in
         /*) if [ -e "$t" ]; then printf "AWS_LINK_%s='%s'\n" "$(echo "$f" | tr a-z A-Z)" "$(printf '%s' "$t" | sed "s/'/\\\\'/g")" >> .env
             else echo "Skipped ~/.aws/$f: $t doesn't exist. Create it on Windows first (for sso, run aws sso login there), then rerun this."; fi ;;
         *) echo "Note: ~/.aws/$f is a relative link. It works in the container only if it points inside ~/.aws." ;;
       esac
     done
     grep -E '^(STRANDS_HOST_UID|AWS_LINK_[A-Z]*)=' .env
   fi
   ```

   This adds lines to `.env` that share the Windows paths your `~/.aws` links point to and set `STRANDS_HOST_UID` if needed. Then continue with step 3.

   With `compose.wsl.yaml`, file-backed sessions (`session_type: file`) and tools that write under `$HOME` (such as MCP servers started with `uvx` or `npx`) aren't supported. Never set `STRANDS_HOST_UID` to `0`.
   :::

3. Edit [`config.yaml`](../../config.yaml) with your model and agent settings:

   ```yaml
   model:
     provider: bedrock
     model_id: us.anthropic.claude-haiku-5-5

   agent_name: my-agent
   system_prompt: >
     You are an AI assistant specialized in your domain.
   ```

   :::info config.yaml is baked in at build time
   `config.yaml` is `COPY`'d into the image by the [`Dockerfile`](../../Dockerfile). After editing it, rebuild with `docker compose up --build` (or `docker compose build`) — restarting alone won't pick up the change. On WSL, rebuild with `docker compose -f compose.yaml -f compose.wsl.yaml up --build` instead, or the container loses its WSL settings and can't read your AWS login. Secrets and per-environment values come from `.env` at run time and don't require a rebuild.
   :::

## Run

Build the image and start the agent.

macOS, Linux, and Windows:

```bash
docker compose up --build
```

WSL:

```bash
docker compose -f compose.yaml -f compose.wsl.yaml up --build
```

`just up` also loads `compose.wsl.yaml` on WSL, but it doesn't rebuild.

The first build pulls `foundry-agent-*` packages from the package locations configured in `pyproject.toml` — make sure your network can reach them. Subsequent runs without `--build` start instantly.

## Verify

In another terminal, hit the health endpoint. If you set `PORT` in `.env`, use that port instead of 8000 here and in the query below.

```bash
curl http://localhost:8000/api/v1/health
```

You should receive a JSON response with `"status": "healthy"`. The compose file also runs this same check internally — `docker compose ps` shows the container as `healthy` once it passes.

Then test a query:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-key>" \
  -d '{"query": "What is machine learning?"}' | jq .
```

## What's mounted, what persists

The default `compose.yaml` wires up two volumes:

| Mount | Source | Purpose |
|---|---|---|
| `~/.aws` (bind) | host | Reuse host AWS SSO sessions inside the container (read-only on Windows; on WSL, Windows, and Linux, see the notes above) |
| `strands_sessions` (named) | docker volume | Persist `FileSessionManager` state across restarts (not writable under `compose.wsl.yaml` or with `STRANDS_HOST_UID` set) |

Sessions survive `docker compose down`. To wipe them, `docker compose down -v`.

On WSL, `compose.wsl.yaml` adds a second share of `~/.aws` at `/aws-home/.aws`, which is the one the container uses, plus one share for each `AWS_LINK_*` path you set.

## Tuning the compose file

`compose.yaml` ships with sensible defaults; common customizations:

- **Port** — set `PORT` in `.env` to change the host port and avoid collisions with other agents on the same machine. Under compose, `PORT` is the host port only. The agent always listens on 8000 inside the container, so the health check and `EXPOSE 8000` stay correct. Compose also pins `STRANDS__AGENT_PORT` to 8000, so setting it in `.env`, or setting `agent_port` in `config.yaml`, has no effect under compose. A `PORT` set in your shell, such as `$env:PORT` in PowerShell, takes precedence over the one in `.env`.
- **Container / service name** — rename the `strands-agent` service to your agent's name so logs and `docker compose ps` are easier to read. Rename it in `compose.wsl.yaml` too, or WSL users get a separate, broken `strands-agent` service.
- **Extra Compose files** — Compose loads `compose.override.yaml` automatically, except when you pass `-f`, as `just up` does on WSL. On WSL, add `-f compose.override.yaml` after the other files.
- **Network** — the file declares a network named `DockerAINetwork`; mark it `external: true` if you're sharing it with other agents or services.
- **Health check cadence** — `interval: 10s`, `timeout: 5s`, `retries: 5` by default; tune if startup is slow in your environment.

See [Configuration → Docker Configuration](./configuration/index.md#docker-configuration) for the full set of compose-related settings.

## What's Next

- **[Configuration](./configuration/index.md)** — full reference for `config.yaml` and env var overrides
- **[Adding tools](./guides/adding-tools.md)** — give your agent domain-specific capabilities
- **[Customizing the server](./guides/customizing-server.md)** — wire in custom session managers or model providers
