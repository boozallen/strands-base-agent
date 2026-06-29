---
sidebar_position: 2
---

# Environment Variables

Complete reference for environment variables that influence Strands Base Agent at runtime.

For an overview of how YAML and env vars interact, start with the [Configuration guide](./index.md).

## Quick Start (Minimal Setup)

Most settings live in `config.yaml`. Env vars are typically only needed for secrets:

```bash
# Required for AWS Bedrock access
AWS_DEFAULT_REGION=us-east-1
AWS_PROFILE=default
```

All other configuration has sensible defaults in `config.yaml`.

## Override Convention

When configuration is loaded from `config.yaml` (the recommended path), env vars override YAML values using the `STRANDS__` prefix with double-underscore (`__`) as the nesting delimiter. Single underscores inside field names are preserved.

```bash
STRANDS__MODEL__PROVIDER=bedrock        # overrides model.provider
STRANDS__MODEL__MODEL_ID=...            # overrides model.model_id
STRANDS__SESSION_TYPE=file              # overrides session_type (not session.type)
```

List fields accept comma-separated values:

```bash
STRANDS__TOOLS_MODULES=myapp.tools.search,myapp.tools.weather
```

## Server

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `DEBUG` | Application log level (read directly, not via the config loader) |

## AWS / Bedrock

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_PROFILE` | `default` | AWS profile for Bedrock access |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region |
| `AWS_READ_TIMEOUT` | `900` | Bedrock read timeout (seconds) |
| `AWS_CONNECT_TIMEOUT` | `60` | Bedrock connect timeout (seconds) |

## Model

| YAML field | Env override | Default |
|------------|--------------|---------|
| `model.provider` | `STRANDS__MODEL__PROVIDER` | `bedrock` |
| `model.model_id` | `STRANDS__MODEL__MODEL_ID` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| `model.temperature` | `STRANDS__MODEL__TEMPERATURE` | `0.3` |
| `model.streaming` | `STRANDS__MODEL__STREAMING` | `true` |
| `model.max_tokens` | `STRANDS__MODEL__MAX_TOKENS` | — |
| `model.top_p` | `STRANDS__MODEL__TOP_P` | — |
| `model.ollama_url` | `STRANDS__MODEL__OLLAMA_URL` | — |
| `model.llamacpp_url` | `STRANDS__MODEL__LLAMACPP_URL` | — |

To point at a local Ollama or llama.cpp instance, set
`model.ollama_url` / `model.llamacpp_url` in `config.yaml` (or the
`STRANDS__MODEL__OLLAMA_URL` / `STRANDS__MODEL__LLAMACPP_URL` overrides for
environment-specific values). The bare `OLLAMA_URL` / `LLAMACPP_URL` vars
shipped in `env.template` only apply on the `from_env()` path (defaults
`http://host.docker.internal:11434` and `http://localhost:8080`); see
[How env vars work](./index.md#how-env-vars-work-two-loader-paths).

## Agent Identity

| YAML field | Env override | Default |
|------------|--------------|---------|
| `agent_name` | `STRANDS__AGENT_NAME` | `strands-base-agent` |
| `agent_description` | `STRANDS__AGENT_DESCRIPTION` | (see config.yaml) |
| `agent_version` | `STRANDS__AGENT_VERSION` | `1.0` |
| `agent_port` | `STRANDS__AGENT_PORT` | — |
| `system_prompt` | `STRANDS__SYSTEM_PROMPT` | (see config.yaml) |

## Tools

| YAML field | Env override | Default |
|------------|--------------|---------|
| `tools_modules` | `STRANDS__TOOLS_MODULES` | — |
| `tools_files` | `STRANDS__TOOLS_FILES` | — |

## Conversation & Memory

| YAML field | Env override | Default |
|------------|--------------|---------|
| `max_conversation_length` | `STRANDS__MAX_CONVERSATION_LENGTH` | `10` |
| `conversation_window_size` | `STRANDS__CONVERSATION_WINDOW_SIZE` | `100` |
| `conversation_truncate_results` | `STRANDS__CONVERSATION_TRUNCATE_RESULTS` | `false` |
| `enable_memory` | `STRANDS__ENABLE_MEMORY` | `false` |
| `knowledge_base_id` | `STRANDS__KNOWLEDGE_BASE_ID` | — |
| `agent_state_initial_values` | `STRANDS__AGENT_STATE_INITIAL_VALUES` | `{}` |

## Session Management

| YAML field | Env override | Default |
|------------|--------------|---------|
| `session_id` | `STRANDS__SESSION_ID` | — |
| `session_type` | `STRANDS__SESSION_TYPE` | — |
| `session_storage_dir` | `STRANDS__SESSION_STORAGE_DIR` | — |
| `session_s3_bucket` | `STRANDS__SESSION_S3_BUCKET` | — |
| `session_s3_prefix` | `STRANDS__SESSION_S3_PREFIX` | — |

## Guardrails

Guardrails live under `model.guardrails` in `config.yaml`. Setting
`guardrail_id` enables them.

| YAML field | Env override | Default |
|------------|--------------|---------|
| `model.guardrails.guardrail_id` | `STRANDS__MODEL__GUARDRAILS__GUARDRAIL_ID` | — |
| `model.guardrails.guardrail_version` | `STRANDS__MODEL__GUARDRAILS__GUARDRAIL_VERSION` | `""` |
| `model.guardrails.guardrail_trace` | `STRANDS__MODEL__GUARDRAILS__GUARDRAIL_TRACE` | `enabled` |

The single-underscore form (`STRANDS_GUARDRAIL_ID`, `STRANDS_GUARDRAIL_VERSION`,
`STRANDS_GUARDRAIL_TRACE`) only applies on the `from_env()` path — see
[How env vars work](./index.md#how-env-vars-work-two-loader-paths).

See the [Guardrails guide](../guides/guardrails.md) for setup steps.

## MCP and A2A

These are structured fields. YAML is strongly recommended over env vars.

```yaml
# config.yaml
mcp_servers:
  - name: github
    url: https://api.githubcopilot.com/mcp/
    headers:
      Authorization: "Bearer ${GITHUB_PAT}"

a2a_servers:
  - name: finance-agent
    url: https://finance-agent.internal/api/
```

See the [MCP servers guide](../guides/mcp-servers.md) for details.

## Observability

| YAML field | Env override | Default |
|------------|--------------|---------|
| `observability_enabled` | `STRANDS__OBSERVABILITY_ENABLED` | `false` |

The single-underscore form (`STRANDS_O11Y_ENABLED`) only applies on the
`from_env()` path — see
[How env vars work](./index.md#how-env-vars-work-two-loader-paths).

OTLP exporter settings are read directly by the OpenTelemetry SDK, not by the
config loader:

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP endpoint URL |
| `OTEL_EXPORTER_OTLP_HEADERS` | — | OTLP auth headers |
| `OTEL_SERVICE_NAME` | `strands-base-agent` | Service name |

## CORS

Set on the FastAPI middleware via `foundry-agent-fastapi`:

| Variable | Default | Description |
|----------|---------|-------------|
| `STRANDS_CORS_ORIGINS` | localhost dev ports | Comma-separated allowed origins |
| `STRANDS_CORS_ALLOW_CREDENTIALS` | `false` | Allow credentials |
| `STRANDS_CORS_ALLOW_METHODS` | `GET,POST,PUT,DELETE,OPTIONS,HEAD` | Allowed HTTP methods |
| `STRANDS_CORS_ALLOW_HEADERS` | `Accept,Content-Type,Authorization,...` | Allowed headers |

## Query Processing

| YAML field | Env override | Default |
|------------|--------------|---------|
| `max_query_length` | `STRANDS__MAX_QUERY_LENGTH` | `2000` |
| `default_similarity_threshold` | `STRANDS__DEFAULT_SIMILARITY_THRESHOLD` | `0.7` |
| `max_response_time_ms` | `STRANDS__MAX_RESPONSE_TIME_MS` | `30000` |

## Miscellaneous

| Variable | Default | Description |
|----------|---------|-------------|
| `STRANDS_AGENT_PUBLIC_URL` | `http://{agent_name}:{port}` | Public URL for the A2A agent card |
| `STRANDS_IGNORE_DOTENV` | `false` | Skip loading `.env` at startup |

## Security Note

Secrets (API keys, tokens, AWS credentials) should stay in `.env` files and **never** in `config.yaml`.
