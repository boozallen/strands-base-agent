---
sidebar_position: 4
---

# Customizing the Server

[`server.py`](../../../strands_base_agent/server.py) is the **composition root**. It's where adopters wire in custom session managers, model providers, or alternative agent backends. Application-level infrastructure (DI container, middleware, lifecycle hooks) is provided by the `foundry-agent-*` packages and registered in [`application/factory.py`](../../../strands_base_agent/application/factory.py) — leave that alone.

## What Lives Where

| File | Purpose |
|------|---------|
| [`server.py`](../../../strands_base_agent/server.py) | Composition root. Registers `AgentFactory` and `AgentBackend`. **Customize here.** |
| [`application/factory.py`](../../../strands_base_agent/application/factory.py) | Infrastructure DI registration. Don't add domain wiring here — it belongs in [`server.py`](../../../strands_base_agent/server.py). |
| [`api/dependencies.py`](../../../strands_base_agent/api/dependencies.py) | FastAPI bridge that resolves types from the container. Add a getter when introducing a new injectable type. |

## Custom Session Manager

Sessions support two backends, `file` and `s3`, chosen with `session_type` in [`config.yaml`](../../../config.yaml):

```yaml
session_type: s3
session_s3_bucket: my-sessions-bucket
session_s3_prefix: agents/strands
```

Only `file` and `s3` are supported. Any other `session_type`, such as `dynamodb`, is rejected at startup.

## Custom Model Provider

`StrandsAgentFactory` accepts a `model_provider_factories` dict keyed by `model.provider`. Register a new provider name and pair it with a factory that returns a Strands-compatible model object.

## Alternative Agent Backend

`AgentBackend` is a protocol from [`foundry-agent-core`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-agent-core/index.md). The default implementation is `StrandsAgentBackend`, but the protocol is intentionally agnostic — future adapters (LangChain, CrewAI, Pydantic AI) can plug in without changing the API layer.

If you need to swap the backend, register a different implementation:

```python
container.register_factory(
    AgentBackend,
    lambda: MyAlternativeBackend(container),
    singleton=True,
)
```

The route handlers in [`api/routes/query.py`](../../../strands_base_agent/api/routes/query.py) only depend on the `AgentBackend` protocol, so they continue to work.

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

2. Expose a getter in [`api/dependencies.py`](../../../strands_base_agent/api/dependencies.py):

   ```python
   def get_report_renderer(container: Annotated[DependencyContainer, Depends(get_container)]) -> ReportRenderer:
       return container.resolve(ReportRenderer)
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

- `tool_loader.py` lives in [`foundry-strands-agent`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-strands-agent/index.md) and is security-critical. Don't reimplement it.
- OTel, retry logic, middleware, signal handlers — provided by the packages.
- The DI container itself, agent protocols, lifecycle hooks — owned by `foundry-agent-core`.

If a customization needs to reach into one of those, it's a signal the change belongs in a package PR rather than in your fork.
