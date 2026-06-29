---
sidebar_position: 7
---

# Embedding `process_query`

`strands_base_agent.main.process_query()` is interface-agnostic. It runs a single query through the agent and returns a response, with no assumption about how the call was triggered. Use it to embed the agent in interfaces beyond the default HTTP server — Lambda handlers, custom scripts, alternative web frameworks.

## HTTP Server (Standalone)

If you don't need the full A2A server but want a minimal HTTP wrapper:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from strands_base_agent.main import process_query

app = FastAPI()


class QueryRequestModel(BaseModel):
    query: str


@app.post("/query")
async def handle_query(request: QueryRequestModel):
    response = await process_query(request.query)
    return {"response": response.content}


# Run with: uvicorn main:app --reload
```

## AWS Lambda

```python
import asyncio
import json

from strands_base_agent.main import process_query


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    query = body.get("query", "")

    response = asyncio.run(process_query(query))

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"response": response.content}),
    }
```

## Batch Script

```python
import asyncio

from strands_base_agent.main import process_query


async def batch_process(queries: list[str]) -> list[str]:
    results = []
    for q in queries:
        response = await process_query(q)
        results.append(response.content)
    return results


async def main():
    queries = [
        "What is Python?",
        "Explain machine learning",
        "How does async work?",
    ]
    answers = await batch_process(queries)
    for q, a in zip(queries, answers, strict=True):
        print(f"Q: {q}\nA: {a}\n")


if __name__ == "__main__":
    asyncio.run(main())
```

## Custom Bootstrap with Service Lifecycle

When you need finer-grained control over the agent's lifecycle (long-running consumers, custom middleware), bootstrap the container yourself:

```python
from foundry_strands_agent import (
    AgentFactory,
    StrandsAgentFactory,
    create_agent_service,
)

from strands_base_agent.application.factory import create_application_container


async def custom_interface():
    container = create_application_container()
    container.register_factory(
        AgentFactory,
        lambda: StrandsAgentFactory(container),
        singleton=True,
    )
    service = create_agent_service(container)

    async with service.service_lifecycle() as active_service:
        # Your interface logic here. `active_service` exposes
        # process_query / process_query_stream and handles startup
        # and graceful shutdown via the context manager.
        pass
```
