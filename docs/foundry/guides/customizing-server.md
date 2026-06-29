---
sidebar_position: 4
---

# Customizing the Server

`server.py` is the **composition root**. It's where adopters wire in custom session managers, model providers, or alternative agent backends. Application-level infrastructure (DI container, middleware, lifecycle hooks) is provided by the `foundry-agent-*` packages and registered in `application/factory.py` — leave that alone.

## What Lives Where

| File | Purpose |
|------|---------|
| `server.py` | Composition root. Registers `AgentFactory` and `AgentBackend`. **Customize here.** |
| `application/factory.py` | Infrastructure DI registration. Don't add domain wiring here — it belongs in `server.py`. |
| `api/dependencies.py` | FastAPI bridge that resolves types from the container. Add a getter when introducing a new injectable type. |

## Custom Session Manager

`StrandsAgentFactory` accepts a `session_manager_factories` dict that maps `session_type` strings to factory callables. The defaults are `file` and `s3`. Add your own — for example, DynamoDB:

```python
# server.py (excerpt — illustrative)
# Replace `build_dynamodb_session_manager` with your own factory; no
# DynamoDB session manager ships in this repo.
from strands_base_agent.tools.session import build_dynamodb_session_manager

container.register_factory(
    AgentFactory,
    lambda: StrandsAgentFactory(
        container,
        session_manager_factories={
            "file": _default_file_session_manager,
            "s3": _default_s3_session_manager,
            "dynamodb": build_dynamodb_session_manager,
        },
    ),
    singleton=True,
)
```

Then enable it via config:

```yaml
session_type: dynamodb
session_dynamodb_table: my-agent-sessions
```

Your factory receives the resolved `AgentConfig` and returns whatever object your session backend expects.

## Custom Model Provider

Same pattern — `StrandsAgentFactory` accepts a `model_provider_factories` dict keyed by `model.provider`. Register a new provider name and pair it with a factory that returns a Strands-compatible model object.

## Alternative Agent Backend

`AgentBackend` is a protocol from `foundry-agent-core`. The default implementation is `StrandsAgentBackend`, but the protocol is intentionally agnostic — future adapters (LangChain, CrewAI, Pydantic AI) can plug in without changing the API layer.

If you need to swap the backend, register a different implementation:

```python
container.register_factory(
    AgentBackend,
    lambda: MyAlternativeBackend(container),
    singleton=True,
)
```

The route handlers in `api/routes/query.py` only depend on the `AgentBackend` protocol, so they continue to work.

## Adding New Injectable Types

If you introduce a new service (say, `ReportRenderer`) that route handlers need:

1. Register a factory in `application/factory.py` (if it's truly infrastructure) or in `server.py` (if it's domain-specific):

   ```python
   container.register_factory(
       ReportRenderer,
       lambda: ReportRenderer(),
       singleton=True,
   )
   ```

2. Expose a getter in `api/dependencies.py`:

   ```python
   def get_report_renderer() -> ReportRenderer:
       return get_runtime_container().resolve(ReportRenderer)
   ```

3. Inject it into your route:

   ```python
   from typing import Annotated
   from fastapi import Depends

   async def render_report(
       renderer: Annotated[ReportRenderer, Depends(get_report_renderer)],
   ):
       ...
   ```

## What Not to Touch

- `tool_loader.py` lives in `foundry-strands-agent` and is security-critical. Don't reimplement it.
- OTel, retry logic, middleware, signal handlers — provided by the packages.
- The DI container itself, agent protocols, lifecycle hooks — owned by `foundry-agent-core`.

If a customization needs to reach into one of those, it's a signal the change belongs in a package PR rather than in your fork.
