# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Chat history API endpoints.

Implements FastAPI routes for chat history retrieval with dependency injection
and direct ChatHistoryManager injection. Uncaught domain errors are handled by
``ErrorHandlingMiddleware``.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from fastapi import status as HttpStatus
from strands.types.session import SessionType

from foundry_agent_fastapi import ErrorResponse, generate_correlation_id
from foundry_strands_agent import ChatHistoryManager, Session, SessionMessage

from strands_base_agent.api.dependencies import get_chat_history_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat/history", tags=["chat_history"])
SessionIdPath = Annotated[str, Path(min_length=3, max_length=40, description="Unique identifier for the chat sesson")]


@router.get(
    "",
    status_code=HttpStatus.HTTP_200_OK,
    summary="Get chat session history",
    responses={
        200: {"description": "Chat sessions retrieved successfully", "model": list[Session]},
        400: {"description": "Invalid request parameters", "model": ErrorResponse},
        500: {"description": "Internal server error during session retrieval", "model": ErrorResponse},
    },
)
async def get_chat_sessions_history(
    chat_history: Annotated[ChatHistoryManager, Depends(get_chat_history_manager)],
    limit: Annotated[
        int | None, Query(ge=1, le=100, description="Maximum number of sessions to return (1-100)")
    ] = None,
    offset: Annotated[int | None, Query(ge=0, description="Number of sessions to skip for pagination")] = None,
) -> list[Session]:
    correlation_id = generate_correlation_id()

    logger.info(
        "Retrieving chat sessions history",
        extra={"correlation_id": correlation_id, "limit": limit, "offset": offset},
    )

    sessions = await chat_history.get_chat_sessions_history(limit=limit, offset=offset)

    logger.info(
        "Chat sessions history retrieved successfully",
        extra={"correlation_id": correlation_id, "session_count": len(sessions), "limit": limit, "offset": offset},
    )

    return sessions


@router.get(
    "/{session_id}",
    status_code=HttpStatus.HTTP_200_OK,
    summary="Get chat session messages",
    responses={
        200: {"description": "Chat session messages retrieved successfully", "model": list[SessionMessage]},
        400: {"description": "Invalid session ID or pagination parameters", "model": ErrorResponse},
        404: {"description": "Chat session not found", "model": ErrorResponse},
        500: {"description": "Internal server error during message retrieval", "model": ErrorResponse},
    },
)
async def get_chat_session_messages_history(
    session_id: SessionIdPath,
    chat_history: Annotated[ChatHistoryManager, Depends(get_chat_history_manager)],
    limit: Annotated[
        int | None, Query(ge=1, le=100, description="Maximum number of messages to return (1-100)")
    ] = None,
    offset: Annotated[int | None, Query(ge=0, description="Number of messages to skip for pagination")] = None,
) -> list[SessionMessage]:
    correlation_id = generate_correlation_id()

    logger.info(
        "Retrieving chat session messages",
        extra={"correlation_id": correlation_id, "session_id": session_id, "limit": limit, "offset": offset},
    )

    messages = await chat_history.get_chat_session_messages_history(session_id, limit=limit, offset=offset)

    logger.info(
        "Chat session messages retrieved successfully",
        extra={"correlation_id": correlation_id, "session_id": session_id, "message_count": messages and len(messages)},
    )

    return messages


def set_chat_history_content_location(session_id: str, response: Response) -> None:
    status_code = response.status_code
    if 200 <= status_code and status_code < 300:
        response.headers["Content-Location"] = f"/chat/history/{session_id}"


@router.put(
    "/{session_id}",
    status_code=HttpStatus.HTTP_201_CREATED,
    summary="Create chat session history",
    responses={
        200: {"description": "Chat session exists", "model": Session},
        201: {"description": "Chat session created successfully", "model": Session},
        400: {"description": "Invalid session ID", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def create_chat_session_messages_history(
    session_id: SessionIdPath,
    _response: Response,
    chat_history: Annotated[ChatHistoryManager, Depends(get_chat_history_manager)],
) -> Session:
    correlation_id = generate_correlation_id()

    logger.info("Creating new chat session", extra={"correlation_id": correlation_id, "session_id": session_id})

    session = await chat_history.create_chat_session_messages_history(session_id)

    if not session:
        logger.info("Chat session already exists", extra={"correlation_id": correlation_id, "session_id": session_id})
        _response.status_code = 200
        set_chat_history_content_location(session_id, _response)
        return Session(session_id=session_id, session_type=SessionType.AGENT)

    logger.info("Chat session created successfully", extra={"correlation_id": correlation_id, "session_id": session_id})
    _response.status_code = 201
    set_chat_history_content_location(session_id, _response)

    return session


@router.delete(
    "/{session_id}",
    status_code=HttpStatus.HTTP_204_NO_CONTENT,
    summary="Delete chat session history",
    responses={
        204: {"description": "Chat session deleted successfully"},
        400: {"description": "Invalid session ID", "model": ErrorResponse},
        404: {"description": "Chat session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def delete_chat_session_messages_history(
    session_id: SessionIdPath,
    chat_history: Annotated[ChatHistoryManager, Depends(get_chat_history_manager)],
) -> None:
    correlation_id = generate_correlation_id()

    logger.info("Deleting a chat session", extra={"correlation_id": correlation_id, "session_id": session_id})

    sessions = await chat_history.get_chat_sessions_history()
    if not any(s.session_id == session_id for s in sessions):
        raise HTTPException(status_code=404, detail=f"Chat session '{session_id}' not found")

    await chat_history.delete_chat_session_messages_history(session_id)

    logger.info("Chat session deleted successfully", extra={"correlation_id": correlation_id, "session_id": session_id})
