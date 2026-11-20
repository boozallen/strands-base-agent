---
sidebar_position: 8
---

# Built-in HTTP API

The default agent ships with three groups of HTTP endpoints alongside the A2A protocol routes:

| Group | Path prefix | Purpose |
|---|---|---|
| Query | `/api/v1/query` | Send a query, get a response (sync or SSE stream) |
| Chat history | `/api/v1/chat/history` | List, read, create, and delete chat sessions |
| Health | `/api/v1/health` | Liveness probe for orchestrators |

A2A protocol routes (`/.well-known/agent-card.json` and the JSON-RPC endpoint) are mounted on the same server but are documented by the A2A spec and the Strands Agents SDK. This page covers the REST endpoints this repo defines directly.

The OpenAPI spec at `http://localhost:8000/docs` is the authoritative source for request/response shapes — this page is a concise reference and field guide.

## Authentication

All endpoints require a bearer token in the `Authorization` header:

```
Authorization: Bearer <your-key>
```

The token is validated against the `STRANDS_API_KEY` environment variable. Requests without a valid token receive `401 Unauthorized`.

Exempt paths (no token required):

- `GET /api/v1/health`
- `GET /.well-known/agent.json`
- `GET /.well-known/agent-card.json`
- All `OPTIONS` requests (CORS preflight)

The server requires `STRANDS_API_KEY` to be set in the environment.

A2A calls to the JSON-RPC endpoint need the same token. The agent card says so, so A2A clients can find out before their first call: `securitySchemes` has a `bearer` entry (`"type": "http"`, `"scheme": "bearer"`), and `security` is `[{"bearer": []}]`.

## Sync Query

```
POST /api/v1/query
Content-Type: application/json
```

Runs a single query through the agent and returns the full response when generation finishes. Use for one-shot calls where streaming offers no benefit (batch jobs, integrations, simple chat UIs).

### Request body

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `query` | string | yes | 1–8192 chars, non-whitespace | The user's question |
| `session_id` | string \| null | no | 8–128 chars, `[A-Za-z0-9_-]+` | Persists conversation state across calls |
| `context` | object \| null | no | ≤32 keys, ≤16 KiB serialized, string keys | Free-form metadata forwarded to the agent |
| `max_results` | int | no | 1–100, default 10 | Hint for retrieval-shaped tools |
| `similarity_threshold` | float | no | 0.0–1.0, default 0.7 | Hint for retrieval-shaped tools |

### Response body — `200 OK`

| Field | Type | Description |
|---|---|---|
| `content` | string | Agent-generated response text |
| `session_id` | string \| null | Echoed from the request (or assigned by the agent) |
| `processing_time_ms` | float | Total wall-clock time for this query |
| `timestamp` | ISO 8601 datetime | When the response was generated |
| `metadata` | object \| null | Backend-specific extras (token usage, etc.) |
| `correlation_id` | string \| null | Server-assigned ID for tracing |
| `api_version` | string | Schema version, currently `"1.0"` |

### Example

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-key>" \
  -d '{
    "query": "What is machine learning?",
    "session_id": "user-42-session-1"
  }' | jq .
```

## Streaming Query (SSE)

```
POST /api/v1/query/stream
Content-Type: application/json
Accept: text/event-stream
```

Streams response tokens as Server-Sent Events. Use for chat UIs where time-to-first-token matters.

The request body is identical to the sync endpoint. The response is `text/event-stream` with the following event types:

| Event | When | Payload |
|---|---|---|
| `token` | Each model output token | `content`, `correlation_id`, `session_id` |
| `result` | Final assembled response (some backends) | `content`, `session_id`, `query_id`, `correlation_id`, `api_version` |
| `done` | End of successful stream | `processing_time_ms`, `session_id`, `query_id`, `correlation_id`, `api_version` |
| `error` | Stream terminated with a failure | `error`, `message`, `correlation_id`, `session_id`, `retryable` |
| `event` | Backend event the API does not classify | `payload` (the raw event), `correlation_id` |

Always close the stream when you receive `done` or `error`. `retryable: true` on an error indicates a transient failure (e.g., MCP reconnect) that a client may retry.

### Example

```bash
curl -N -X POST http://localhost:8000/api/v1/query/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-key>" \
  -d '{"query": "Explain async/await in Python"}'
```

```
event: token
data: {"content": "Async", "correlation_id": "…", "session_id": null}

event: token
data: {"content": "/await", "correlation_id": "…", "session_id": null}

…

event: done
data: {"processing_time_ms": 1842.3, "session_id": null, "query_id": "…", "correlation_id": "…", "api_version": "1.0"}
```

## Chat History

```
/api/v1/chat/history
```

CRUD over persisted chat sessions. Backed by the configured `ChatHistoryManager` (file or S3). Chat history is off by default for security. Set `session_type` in [`config.yaml`](../../../config.yaml) to turn it on. While it's off, these routes return a generic `500`, because errors don't expose internal details.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/chat/history` | List sessions (most recent first) - disabled by default, see below |
| `GET` | `/api/v1/chat/history/{session_id}` | List messages in a session |
| `PUT` | `/api/v1/chat/history/{session_id}` | Create a session (idempotent) |
| `DELETE` | `/api/v1/chat/history/{session_id}` | Delete a session and its messages - disabled by default, see below |

`session_id` path parameters are 8–128 characters: letters, digits, `_`, and `-`. Anything else returns `422`.

**`GET /api/v1/chat/history` is disabled by default** and returns `403` unless
`STRANDS_CHAT_HISTORY_LIST_ENABLED=true` is set. Auth here is a single shared bearer token, not
per-user identity, so this endpoint has no way to scope results to the caller - enabling it lets
any bearer-token holder enumerate every session on the instance. See
[Environment Variables](../configuration/environment-variables.md#authentication).

**`DELETE /api/v1/chat/history/{session_id}` is also disabled by default** and returns `403`
unless `STRANDS_CHAT_HISTORY_DELETE_ENABLED=true` is set, for the same reason: any bearer-token
holder could otherwise delete any session. The check runs before storage is read, so a disabled
endpoint returns the same `403` whether or not the session exists. The two flags are independent;
neither affects the other, and the `GET`/`PUT` endpoints for a single session are unaffected by
both.

### List sessions

```
GET /api/v1/chat/history?limit=20&offset=0
```

Query params: `limit` (1–100, optional) and `offset` (≥0, optional). Returns `200 OK` with a list of `Session` objects:

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |
| `session_type` | string | `"AGENT"` for chat sessions |
| `created_at` | ISO 8601 string | Creation timestamp |
| `updated_at` | ISO 8601 string | Last modification timestamp |

### List messages in a session

```
GET /api/v1/chat/history/{session_id}?limit=50&offset=0
```

Messages are returned with the oldest first. Each `SessionMessage`:

| Field | Type | Description |
|---|---|---|
| `message` | object | Strands `Message` (role + content blocks) |
| `message_id` | int | Index of the message in conversation history |
| `redact_message` | object \| null | If redacted, the content to show instead of `message` |
| `created_at` | ISO 8601 string | Message creation timestamp |
| `updated_at` | ISO 8601 string | Last modification timestamp |

Returns `404 Not Found` if the session does not exist.

### Create a session

```
PUT /api/v1/chat/history/{session_id}
```

- `201 Created` — session was created (response body is the new `Session`)
- `200 OK` — session already existed (response body is a `Session` stub)

Both successful responses set `Content-Location: /chat/history/{session_id}`.

### Delete a session

```
DELETE /api/v1/chat/history/{session_id}
```

- `204 No Content` — session deleted
- `403 Forbidden` — deletion is disabled (`STRANDS_CHAT_HISTORY_DELETE_ENABLED` unset or not `true`)
- `404 Not Found` — deletion is enabled but no session with that ID exists

## Health

```
GET /api/v1/health
```

Returns `{"status": "healthy"}` (and additional readiness details) when the agent is ready to serve requests. Used by Docker, ECS, and Kubernetes probes — `docker compose ps` reports the container as `healthy` once this endpoint returns 200. Provided by [`foundry-agent-fastapi`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-agent-fastapi/index.md)'s `health_router`.

## Error Format

Errors come back in one of three shapes, depending on where they're raised.

Errors from the agent (`400`, `500`) are produced by `ErrorHandlingMiddleware`:

```json
{
  "error": "QueryProcessingError",
  "message": "An internal error occurred. Use the correlation_id to reference this request.",
  "details": null,
  "correlation_id": "req_061d689b",
  "timestamp": "2026-06-26T12:34:56"
}
```

A missing or wrong API key (`401`) returns `{"error": "unauthorized", "message": "Invalid or missing API key"}`, and an open MCP circuit breaker (`503`) returns `error`, `message`, and `correlation_id`.

Errors from the route itself use FastAPI's `detail` shape. `403` and `404` return a message, for example `{"detail": "Chat session listing is disabled"}`. `422` returns a list, one entry per invalid field:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "query"],
      "msg": "Value error, Query cannot be empty or whitespace only",
      "input": "   "
    }
  ]
}
```

Common statuses:

| Status | Meaning |
|---|---|
| `400` | Domain validation rejected the request (also used for transient MCP failures with `retryable: true`) |
| `401` | Missing or invalid bearer token |
| `403` | Session listing or deletion is disabled (`GET /api/v1/chat/history` without `STRANDS_CHAT_HISTORY_LIST_ENABLED=true`, or `DELETE /api/v1/chat/history/{session_id}` without `STRANDS_CHAT_HISTORY_DELETE_ENABLED=true`) |
| `404` | Session ID not found (chat history routes only) |
| `422` | Request validation failed (for example an empty query or a bad `session_id`) |
| `500` | Unhandled server error. Chat history routes also return a generic `500` while chat history is off |
| `503` | MCP circuit breaker is open (query routes only); retry later |

For streaming, a failure after the stream starts arrives as an `error` SSE event whose payload has `error`, `message`, `correlation_id`, `session_id`, and `retryable`.

## OpenAPI / Swagger UI

While the server is running, browse the live spec:

- **Swagger UI** — `http://localhost:8000/docs`
- **ReDoc** — `http://localhost:8000/redoc`
- **OpenAPI JSON** — `http://localhost:8000/openapi.json`

## Related

- **[Adding API Endpoints](./adding-api-endpoints.md)** — add custom routes alongside the built-in ones
- **[Embedding `process_query`](./embedding-process-query.md)** — bypass the HTTP layer entirely from Lambda, CLI, or other interfaces
- **[Customizing the Server](./customizing-server.md)** — swap session managers or model providers
