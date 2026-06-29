---
sidebar_position: 9
---

# Built-in A2A Protocol

In addition to the [REST endpoints](./http-api.md), the default agent serves the [Agent-to-Agent (A2A) protocol](https://a2a.dev) on the same FastAPI app. These routes are mounted by `strands.multiagent.a2a.A2AServer` (the Strands Agents SDK adapter) — the strands-base-agent fork wires its `Agent` instance into that adapter in `strands_base_agent/server.py` and includes the REST routers on the resulting app.

| Group | Path | Purpose |
|---|---|---|
| Discovery | `/.well-known/agent-card.json` | Public agent card |
| JSON-RPC | `/` (default) | All A2A methods — `message/send`, `message/stream`, `tasks/get`, `tasks/cancel`, push config |
| Extended card | `/agent/authenticatedExtendedCard` | Optional, only mounted when `supports_authenticated_extended_card` is set on the card |

The authoritative wire format is defined by the [A2A specification](https://a2a-protocol.org) and the `a2a-sdk` Python types (`a2a.types`). This page is a field guide for what the baseline mounts and how the agent identity is populated — it is not a replacement for the spec.

:::note Example URLs
Examples below use `<AGENT_BASE_URL>` for the agent's HTTP base. Substitute the URL your agent is reachable at — `http://localhost:8000` for local dev (see the [quickstart](../quickstart.md)), or the deployed hostname for any other environment.
:::

## Agent Card

```
GET /.well-known/agent-card.json
```

Returns the public `AgentCard` JSON document used for discovery and capability negotiation. The card is constructed at server boot from the agent's identity and tool registry.

| Field | Source | Notes |
|---|---|---|
| `name` | `agent_name` (config.yaml) | Required — non-empty |
| `description` | `agent_description` (config.yaml) | Required — non-empty |
| `version` | `agent_version` (config.yaml, default `"1.0"`) | Free-form, advertised verbatim |
| `url` | `STRANDS_AGENT_PUBLIC_URL` env or `http://{agent_name}:{port}` | Public URL clients should call |
| `capabilities` | Always `{ "streaming": true }` | The baseline supports `message/stream` |
| `skills` | Derived from the agent's `tool_registry` | One `AgentSkill` per registered tool, with `id`/`name` = tool name and `description` = tool description |
| `default_input_modes` / `default_output_modes` | `["text"]` | Override via Strands' `A2AServer(skills=...)` if needed |

A legacy alias at `/.well-known/agent.json` is also served for backward compatibility and emits a deprecation warning in the logs.

### Example

```bash
curl -s <AGENT_BASE_URL>/.well-known/agent-card.json | jq .
```

```json
{
  "name": "my-agent",
  "description": "A brief description of what your agent does",
  "version": "1.0",
  "url": "http://my-agent:8000/",
  "capabilities": { "streaming": true },
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "skills": [
    { "id": "calculator", "name": "calculator", "description": "Evaluate arithmetic expressions" }
  ]
}
```

`STRANDS_AGENT_PUBLIC_URL` controls the `url` field — set it to the ingress URL you actually want peers to call. The default (`http://{agent_name}:{port}`) only works on a Docker network where the service name resolves; the server logs a warning on boot if the env var is unset.

## JSON-RPC Endpoint

```
POST /
Content-Type: application/json
```

Every A2A method is dispatched through this single endpoint using [JSON-RPC 2.0](https://www.jsonrpc.org/specification). The `method` field selects the operation; `params` carries the operation-specific payload.

Methods the baseline supports:

| Method | Purpose | Response shape |
|---|---|---|
| `message/send` | Run the agent to completion on a message and return the final result | JSON-RPC response (single body) |
| `message/stream` | Run the agent and stream events as Server-Sent Events | SSE stream of JSON-RPC responses |
| `tasks/get` | Read the current state of a previously created task | JSON-RPC response |
| `tasks/cancel` | Request cancellation of an in-flight task | JSON-RPC response |
| `tasks/pushNotificationConfig/set` | Register a push notification target | Only available if a `push_config_store` is wired in |
| `tasks/pushNotificationConfig/get` | Read the current push config |  |
| `tasks/pushNotificationConfig/list` | List configured push targets |  |
| `tasks/pushNotificationConfig/delete` | Remove a push target |  |
| `agent/authenticatedExtendedCard` | Fetch the authenticated extended agent card | Only when the card opts in |

The default `task_store` is `InMemoryTaskStore` and there is no `push_config_store`, so `tasks/get` and `tasks/cancel` work out of the box but the push-notification methods return `MethodNotFoundError` (`-32601`) unless customized. See [Customizing the Server](./customizing-server.md) to plug in a durable task store or push sender.

### Sending a message

`message/send` and `message/stream` share the same params shape (`MessageSendParams`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `message` | `Message` | yes | The user message — see below |
| `configuration` | `MessageSendConfiguration` \| null | no | Per-request overrides (e.g. accepted modes) |
| `metadata` | object \| null | no | Free-form extension metadata |

A `Message` is:

| Field | Type | Notes |
|---|---|---|
| `messageId` | string | UUID generated by the sender |
| `role` | `"user"` \| `"agent"` | Always `"user"` on requests |
| `parts` | array of `Part` | At least one `TextPart`/`FilePart`/`DataPart` |
| `kind` | `"message"` | Discriminator, fixed |
| `contextId` | string \| null | Persists conversation state across calls (analogue of `session_id` on the REST route) |
| `taskId` | string \| null | Set when continuing an existing task |
| `referenceTaskIds` | string[] \| null | Other tasks this message references |

### Example — `message/send`

```bash
curl -X POST <AGENT_BASE_URL>/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "messageId": "11111111-1111-1111-1111-111111111111",
        "role": "user",
        "kind": "message",
        "parts": [{ "kind": "text", "text": "What is machine learning?" }]
      }
    }
  }' | jq .
```

The response is a JSON-RPC envelope wrapping either a `Message` (agent reply) or a `Task` (for long-running work).

## Streaming via JSON-RPC (`message/stream`)

```
POST /
Content-Type: application/json
Accept: text/event-stream
```

`message/stream` returns a [Server-Sent Events](https://html.spec.whatwg.org/multipage/server-sent-events.html) stream. Each `data:` line is a JSON-RPC response whose `result` is a `Task`, `TaskStatusUpdateEvent`, `TaskArtifactUpdateEvent`, or `Message` per the A2A spec.

Two streaming behaviors are available, controlled by the `enable_a2a_compliant_streaming` flag on `A2AServer`:

- **Default (`False`)** — legacy status-update streaming. Backward-compatible with older A2A clients.
- **A2A-compliant (`True`)** — emits artifact-update events as defined by the current spec. Toggle when adopting a stricter client.

The baseline ships with the default. To switch, edit `strands_base_agent/server.py` where `A2AServer(...)` is constructed and pass `enable_a2a_compliant_streaming=True`.

### Example

```bash
curl -N -X POST <AGENT_BASE_URL>/ \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/stream",
    "params": {
      "message": {
        "messageId": "22222222-2222-2222-2222-222222222222",
        "role": "user",
        "kind": "message",
        "parts": [{ "kind": "text", "text": "Explain async/await in Python" }]
      }
    }
  }'
```

```
data: {"jsonrpc":"2.0","id":"1","result":{"kind":"status-update","status":{"state":"working"},"taskId":"…"}}

data: {"jsonrpc":"2.0","id":"1","result":{"kind":"status-update","status":{"state":"completed","message":{"role":"agent","parts":[{"kind":"text","text":"Async/await is…"}]}},"taskId":"…","final":true}}
```

Close the connection when you receive an event with `final: true` or a `JSONRPCErrorResponse`.

## Task lifecycle methods

```
POST /
{ "jsonrpc": "2.0", "id": "…", "method": "tasks/get",    "params": { "id": "<task-id>" } }
{ "jsonrpc": "2.0", "id": "…", "method": "tasks/cancel", "params": { "id": "<task-id>" } }
```

`tasks/get` returns the current `Task` (status + accumulated messages and artifacts). `tasks/cancel` requests cancellation; the response surfaces `TaskNotCancelableError` (`-32002`) for terminal tasks and `TaskNotFoundError` (`-32001`) when the ID is unknown.

Because the default task store is in-memory, task IDs do not survive a process restart. Swap in a durable `TaskStore` if you need persistence — see [Customizing the Server](./customizing-server.md).

## Error Format

All A2A errors are JSON-RPC errors:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "error": {
    "code": -32602,
    "message": "Invalid parameters",
    "data": null
  }
}
```

Codes used by the baseline:

| Code | Name | Meaning |
|---|---|---|
| `-32700` | JSONParseError | Request body was not valid JSON |
| `-32600` | InvalidRequestError | Not a valid JSON-RPC request |
| `-32601` | MethodNotFoundError | Method is not supported in this configuration |
| `-32602` | InvalidParamsError | Params failed validation |
| `-32603` | InternalError | Unhandled server error |
| `-32001` | TaskNotFoundError | No task with that ID |
| `-32002` | TaskNotCancelableError | Task is already terminal |
| `-32003` | PushNotificationNotSupportedError | No `push_config_store` is wired in |
| `-32004` | UnsupportedOperationError | Operation is recognized but not enabled |
| `-32005` | ContentTypeNotSupportedError | Requested input/output mode is not in the agent card |
| `-32006` | InvalidAgentResponseError | Agent produced a response that violated the protocol |
| `-32007` | AuthenticatedExtendedCardNotConfiguredError | Extended card endpoint hit but not configured |

The baseline additionally maps **transient MCP failures** that bubble up through the A2A executor to HTTP `400` with `{"error": "mcp_session_stale", "retryable": true}` (see `handle_a2a_server_error` in `strands_base_agent/server.py`). This is a strands-base-agent extension on top of the standard JSON-RPC body — clients should retry once on this shape before surfacing an error.

## OpenAPI / Swagger UI

`A2AFastAPIApplication` augments the FastAPI OpenAPI schema with the `A2ARequest` discriminated union, so the live spec includes JSON-RPC payload shapes alongside the REST routes:

- **Swagger UI** — `<AGENT_BASE_URL>/docs`
- **ReDoc** — `<AGENT_BASE_URL>/redoc`
- **OpenAPI JSON** — `<AGENT_BASE_URL>/openapi.json`

## Related

- **[Built-in HTTP API](./http-api.md)** — the REST sibling of these routes (`/api/v1/query`, chat history, health)
- **[Customizing the Server](./customizing-server.md)** — swap the task store, plug in a push sender, or enable spec-compliant streaming
