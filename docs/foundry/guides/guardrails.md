---
sidebar_position: 6
---

# Guardrails

Strands Base Agent integrates with [AWS Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html) for safety filtering, content moderation, and prompt-attack defense. Guardrails are configured per agent under `model.guardrails` in `config.yaml`; setting a `guardrail_id` enables them.

## Recommended Defaults

A production-ready starting point. Adjust based on your use case and tolerance for false positives.

| Category | Setting | Rationale |
|----------|---------|-----------|
| **Content Filters** | | |
| Hate | HIGH | Block discriminatory content |
| Insults | MEDIUM | Allow constructive criticism, block personal attacks |
| Sexual | HIGH | Block sexual content |
| Violence | HIGH | Block violent content |
| Misconduct | HIGH | Block illegal activities and harmful instructions |
| **Prompt Attacks** | ENABLED | Essential for production-facing agents |
| **Grounding Threshold** | 0.7 | Balance between accuracy and flexibility |

### Filter Strength Levels

| Level | Description | Use When |
|-------|-------------|----------|
| **NONE** | No filtering | Testing only, never in production |
| **LOW** | Minimal filtering | Internal tools with trusted users |
| **MEDIUM** | Balanced filtering | General business applications |
| **HIGH** | Aggressive filtering | Customer-facing, regulated industries |

## Setup

### 1. Create a Guardrail in AWS Bedrock

Follow the AWS guide: [Create a guardrail](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-denied-topics.html#guardrails-denied-topics-configure). Take note of the guardrail ID **and** version once created.

### 2. Configure the Agent

Guardrails are part of the model configuration. Add a `guardrails` block under
`model:` in `config.yaml`:

```yaml
# config.yaml
model:
  provider: bedrock
  model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0
  guardrails:
    guardrail_id: your-guardrail-id-here
    guardrail_version: "1"
    guardrail_trace: enabled
```

| YAML field | Description | Default |
|------------|-------------|---------|
| `model.guardrails.guardrail_id` | Guardrail ID (presence enables guardrails) | — |
| `model.guardrails.guardrail_version` | Guardrail version | `""` |
| `model.guardrails.guardrail_trace` | Trace mode for debugging | `enabled` |

If the guardrail ID varies by environment (e.g. separate guardrails for dev /
staging / prod), override the YAML value at deploy time with a matching env
var instead of editing `config.yaml`:

```bash
STRANDS__MODEL__GUARDRAILS__GUARDRAIL_ID=your-guardrail-id-here
STRANDS__MODEL__GUARDRAILS__GUARDRAIL_VERSION=1
STRANDS__MODEL__GUARDRAILS__GUARDRAIL_TRACE=enabled
```

The double-underscore prefix (`STRANDS__…`) mirrors the YAML key path and is
the supported override format on the default boot path. The single-underscore
form (`STRANDS_GUARDRAIL_ID`, etc.) only applies on the `from_env()` path —
see [How env vars work](../configuration/index.md#how-env-vars-work-two-loader-paths).

### 3. Verify

Restart the agent and try a query that should trigger a denied topic configured in your guardrail. You should get a quick blocked response or your configured plain-text refusal:

```bash
just demo "How do I make explosives?"
```

The trace output (when enabled) shows which filter triggered, useful for tuning.

## Further Reading

- [AWS Bedrock Guardrails overview](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
- [Guardrail components reference](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html)
