---
sidebar_position: 3
---

# Adding API Endpoints

The default agent exposes `/api/v1/query`, `/api/v1/query/stream`, and `/api/v1/chat/history` — see the [Built-in HTTP API](./http-api.md) reference for what those endpoints already provide. Add custom endpoints when your agent needs domain-specific HTTP surface area — file uploads, batch queries, scheduled jobs, admin actions.

## 1. Create a Router

Add a new file under `api/routes/`:

```python
# strands_base_agent/api/routes/reports.py
from typing import Annotated

from fastapi import APIRouter, Depends

from foundry_agent_core import AgentBackend

from strands_base_agent.api.dependencies import get_agent_backend

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    agent_backend: Annotated[AgentBackend, Depends(get_agent_backend)],
):
    # Your logic here. Inject what you need from the DI container
    # via api/dependencies.py.
    return {"report_id": report_id, "status": "ok"}
```

Use the dependency-injection bridge in `api/dependencies.py` to resolve `AgentBackend`, `AgentService`, `ChatHistoryManager`, or any other type registered in the application container.

## 2. Export the Router

Add it to `api/routes/__init__.py`:

```python
from strands_base_agent.api.routes.chat_history import router as chat_history_router
from strands_base_agent.api.routes.query import router as query_router
from strands_base_agent.api.routes.reports import router as reports_router

__all__ = [
    "chat_history_router",
    "query_router",
    "reports_router",
]
```

## 3. Register It in `server.py`

In `start_server()`, after the existing routers are included:

```python
from strands_base_agent.api.routes import (
    chat_history_router,
    query_router,
    reports_router,
)

fastapi_app.include_router(health_router)
fastapi_app.include_router(query_router)
fastapi_app.include_router(chat_history_router)
fastapi_app.include_router(reports_router)
```

## 4. Verify

Restart the server and hit your new endpoint. Substitute `<AGENT_BASE_URL>` with the URL your agent is reachable at (`http://localhost:8000` for local dev, or your deployed hostname):

```bash
curl <AGENT_BASE_URL>/api/v1/reports/123 | jq .
```

You should also see it in the OpenAPI spec at `<AGENT_BASE_URL>/docs`.

## When to Use a New Endpoint vs. a Tool

- **Tool** — when the agent should decide whether to invoke the capability based on user input.
- **API endpoint** — when the *caller* invokes the capability directly (e.g., admin pages, webhooks, batch jobs that don't go through the LLM).

Some capabilities warrant both: a tool the agent calls, and an endpoint a UI calls directly with the same underlying logic factored out.
