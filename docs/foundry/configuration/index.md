---
sidebar_position: 4
---

# Configuration

Strands Base Agent uses a YAML-first configuration approach, with environment variables for overrides and secrets.

## Configuration Priority

Configuration is loaded in this order (later sources override earlier):

1. **`config.yaml`** — primary source for non-secret settings
2. **Environment variables** — override YAML values; required for secrets

## Default `config.yaml`

The starter repo ships with a flat `config.yaml` that drives the agent directly:

```yaml
model:
  provider: bedrock
  model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0
  temperature: 0.3
  streaming: true

agent_name: my-agent
agent_description: A brief description of what your agent does
agent_version: "1.0"

system_prompt: >
  You are an AI assistant specialized in [your domain].

log_level: INFO

# Session management (uncomment to enable)
# session_type: file
# session_storage_dir: ./sessions

# MCP servers
# mcp_servers:
#   - name: github
#     url: https://api.githubcopilot.com/mcp/
#     headers:
#       Authorization: "Bearer ${GITHUB_PAT}"

# A2A agents
# a2a_servers:
#   - name: example-agent
#     url: https://example-agent.com/api/
```

This is all most adopters need. Edit the file and restart.

## Environment Variable Overrides

Env vars override YAML values using the `STRANDS__` prefix with double-underscore (`__`) as the nesting delimiter. Single underscores within field names are preserved.

| YAML key path | Env var |
|---------------|---------|
| `model.provider` | `STRANDS__MODEL__PROVIDER` |
| `model.model_id` | `STRANDS__MODEL__MODEL_ID` |
| `model.temperature` | `STRANDS__MODEL__TEMPERATURE` |
| `agent_name` | `STRANDS__AGENT_NAME` |
| `session_type` | `STRANDS__SESSION_TYPE` |
| `log_level` | `STRANDS__LOG_LEVEL` |

`session_type` becomes `STRANDS__SESSION_TYPE` (not `STRANDS__SESSION__TYPE`) — the underscore inside the field name is preserved.

Example — override the model in production without changing YAML:

```bash
export STRANDS__MODEL__MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
export STRANDS__MODEL__TEMPERATURE=0.1
```

For the full list of YAML fields and env vars, see [Environment Variables](./environment-variables.md).

## How env vars work: two loader paths

Env-var naming depends on which loader path the config goes through:

- **`from_yaml()` (default)** — used whenever `config.yaml` exists. Overrides
  use the **double-underscore** form (`STRANDS__MODEL__GUARDRAILS__GUARDRAIL_ID`),
  mirroring the YAML key path. This is the path almost every adopter is on.
- **`from_env()` (env-only)** — used when there is no `config.yaml`. Overrides
  use the **single-underscore** form with ad-hoc keys
  (`STRANDS_GUARDRAIL_ID`, `STRANDS_O11Y_ENABLED`, `STRANDS_MCP_SERVERS`).
  These keys are *not* honored by the YAML loader.

If a doc shows a single-underscore env var, it only applies on the
`from_env()` path. On the default boot path, use the YAML field or the
double-underscore override.

## Structured Configuration

YAML is the right home for structured settings that are awkward as flat env vars:

```yaml
mcp_servers:
  - name: github
    url: https://api.githubcopilot.com/mcp/
    headers:
      Authorization: "Bearer ${GITHUB_PAT}"

a2a_servers:
  - name: finance-agent
    url: https://finance-agent.internal/api/
  - name: search-agent
    url: https://search-agent.internal/api/
```

## Composed Configuration (Domain-Specific)

When your agent needs domain-specific configuration beyond what `StrandsAgentConfig` provides, wrap it in a custom Pydantic model rather than subclassing.

### Before (flat — default starter repo)

```yaml
# config.yaml
model:
  provider: bedrock
  model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0
agent_name: my-agent
```

```python
# application/factory.py
config = StrandsAgentConfig.from_yaml(Path("config.yaml"), "STRANDS")
```

### After (composed — domain-specific)

```yaml
# config.yaml
agent:
  model:
    provider: bedrock
    model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0
  agent_name: finance-analyzer

# Domain-specific fields
db_url: postgresql://localhost/finance
api_key_env: FINANCE_API_KEY
report_format: pdf
```

```python
from pydantic import BaseModel
from foundry_agent_config import load_config
from foundry_strands_agent import StrandsAgentConfig

class FinanceAgentConfig(BaseModel):
    model_config = {"frozen": True}
    agent: StrandsAgentConfig
    db_url: str = ""
    api_key_env: str = ""
    report_format: str = "pdf"

# application/factory.py
config = load_config(FinanceAgentConfig, Path("config.yaml"), "FINANCE")
strands_config = config.agent  # Pass to the Strands layer
```

Env var overrides for the composed pattern use the outer prefix:

```bash
export FINANCE__AGENT__MODEL__PROVIDER=ollama
export FINANCE__DB_URL=postgresql://prod-db/finance
export FINANCE__REPORT_FORMAT=xlsx
```

### Why Compose, Not Subclass

- Frozen-dataclass inheritance has field-ordering and `__hash__` sharp edges
- A new required field in `StrandsAgentConfig` silently breaks every subclass
- Composition insulates your config from upstream package schema evolution
- `config.agent` is a value object at a known, stable path

## Secrets

Secrets (API keys, tokens, passwords) should **never** go in `config.yaml`. Use environment variables via `.env`:

```bash
# .env
AWS_PROFILE=production
GITHUB_PAT=ghp_xxxxxxxxxxxx
FINANCE_API_KEY=sk-xxxxxxxxxxxx
```

Reference secrets in YAML by env var name when the code needs to know which variable to read:

```yaml
api_key_env: FINANCE_API_KEY  # Code reads os.getenv(config.api_key_env)
```

## Docker Configuration

When running with Docker Compose, `config.yaml` is copied into the image at build time and secrets are passed via environment variables from `.env`.

Customize `compose.yaml` for your agent:

```yaml
services:
  my-agent:                    # rename from strands-agent
    ports:
      - "8301:8000"            # pick a unique host port
    container_name: my-agent

networks:
  my-network:
    name: my-network
    external: true             # use when sharing with other services
```

### Health check

`compose.yaml` defines an inline `healthcheck` that hits `/api/v1/health` via `python3 -c "..."` and exits 0 when the agent reports `"healthy"`. Docker uses this to determine container readiness. Default cadence is `interval: 10s`, `timeout: 5s`, `retries: 5` — tune in `compose.yaml` if you need different thresholds.
