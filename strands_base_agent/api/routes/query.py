# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Query processing API endpoints.

Implements FastAPI routes for query processing with dependency injection
integration, and real agent service orchestration. Uncaught domain and
infrastructure errors are handled by ``ErrorHandlingMiddleware``.
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from foundry_agent_core import AgentBackend, DomainError, QueryProcessingError, ValidationError
from foundry_agent_fastapi import ErrorResponse, QueryAPIRequest, QueryAPIResponse, generate_correlation_id
from foundry_agent_fastapi.mappers import api_request_to_domain, domain_response_to_api
from foundry_strands_agent import AgentService

from strands_base_agent.api.dependencies import get_agent_backend, get_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/query", tags=["query"])


@router.post(
    "",
    response_model=QueryAPIResponse,
    status_code=status.HTTP_200_OK,
    summary="Process a query through the agent system",
    responses={
        200: {"description": "Query processed successfully", "model": QueryAPIResponse},
        400: {"description": "Invalid request data or validation error", "model": ErrorResponse},
        422: {"description": "Request validation failed", "model": ErrorResponse},
        500: {"description": "Internal server error during query processing", "model": ErrorResponse},
    },
)
async def process_query(
    query_request: QueryAPIRequest,
    agent_backend: Annotated[AgentBackend, Depends(get_agent_backend)],
) -> QueryAPIResponse:
    correlation_id = generate_correlation_id()

    logger.info(
        "Processing query request",
        extra={
            "correlation_id": correlation_id,
            "session_id": query_request.session_id,
            "query_length": len(query_request.query),
            "has_context": bool(query_request.context),
        },
    )

    domain_request = api_request_to_domain(query_request)
    domain_response = await agent_backend.process_message(domain_request)

    api_response = domain_response_to_api(domain_response, correlation_id=correlation_id, api_version="1.0")

    logger.info(
        "Query processed successfully",
        extra={
            "correlation_id": correlation_id,
            "session_id": query_request.session_id,
            "response_length": len(api_response.content),
            "processing_time_ms": api_response.processing_time_ms,
        },
    )

    return api_response


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _stream_generator(
    query_request: QueryAPIRequest,
    correlation_id: str,
    agent_service: AgentService,
) -> AsyncGenerator[str]:
    try:
        domain_request = api_request_to_domain(query_request)

        async with agent_service.service_lifecycle() as active_service:
            async for event in active_service.process_query_stream(domain_request):
                event_type = event.get("type", "message")

                if event_type == "token":
                    yield _sse(
                        "token",
                        {
                            "content": event.get("content", ""),
                            "correlation_id": correlation_id,
                            "session_id": query_request.session_id,
                        },
                    )
                elif event_type == "done":
                    yield _sse(
                        "done",
                        {
                            "processing_time_ms": event.get("processing_time_ms", 0),
                            "session_id": event.get("session_id") or query_request.session_id,
                            "query_id": event.get("query_id"),
                            "correlation_id": correlation_id,
                            "api_version": "1.0",
                        },
                    )
                elif event_type == "result":
                    yield _sse(
                        "result",
                        {
                            "content": event.get("content", ""),
                            "session_id": event.get("session_id") or query_request.session_id,
                            "query_id": event.get("query_id"),
                            "correlation_id": correlation_id,
                            "api_version": "1.0",
                        },
                    )
                else:
                    yield _sse(
                        "event",
                        {"payload": event, "correlation_id": correlation_id},
                    )

    except ValidationError:
        yield _sse(
            "error",
            {
                "error": "Validation error",
                "message": "failed to validate query request",
                "correlation_id": correlation_id,
                "session_id": query_request.session_id,
                "retryable": False,
            },
        )
    except QueryProcessingError as e:
        yield _sse(
            "error",
            {
                "error": "Query processing failed",
                "message": "failed to process query",
                "correlation_id": correlation_id,
                "session_id": query_request.session_id,
                "retryable": getattr(e, "retryable", True),
            },
        )
    except DomainError as e:
        yield _sse(
            "error",
            {
                "error": "Processing error",
                "message": "failed to process query",
                "correlation_id": correlation_id,
                "session_id": query_request.session_id,
                "retryable": getattr(e, "retryable", False),
            },
        )
    except Exception:
        logger.exception(
            "Unexpected error during query streaming",
            extra={"correlation_id": correlation_id, "session_id": query_request.session_id},
        )
        yield _sse(
            "error",
            {
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "correlation_id": correlation_id,
                "session_id": query_request.session_id,
                "retryable": False,
            },
        )


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream a query through the agent system",
)
async def process_query_stream(
    query_request: QueryAPIRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
):
    correlation_id = generate_correlation_id()

    return StreamingResponse(
        _stream_generator(query_request, correlation_id, agent_service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
