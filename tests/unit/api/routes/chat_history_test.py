# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for chat history API endpoints."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from strands.types.session import SessionType

from foundry_strands_agent import ChatHistoryManager, Session, SessionMessage

from strands_base_agent.api.routes.chat_history import (
    create_chat_session_messages_history,
    delete_chat_session_messages_history,
    get_chat_session_messages_history,
    get_chat_sessions_history,
    set_chat_history_content_location,
)


def _mock_chat_history() -> AsyncMock:
    return AsyncMock(spec=ChatHistoryManager)


class TestGetChatSessionsHistory:
    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_get_chat_sessions_history_success(self, mock_generate_id):
        mock_generate_id.return_value = "chat-sessions-correlation-id"

        mock_history = _mock_chat_history()
        mock_sessions = [
            Session(
                session_id="session-1",
                session_type=SessionType.AGENT,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
        ]
        mock_history.get_chat_sessions_history.return_value = mock_sessions

        result = await get_chat_sessions_history(mock_history)

        assert result == mock_sessions
        mock_history.get_chat_sessions_history.assert_called_once_with(limit=None, offset=None)

    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_get_chat_sessions_with_pagination(self, mock_generate_id):
        mock_generate_id.return_value = "corr-id"

        mock_history = _mock_chat_history()
        mock_history.get_chat_sessions_history.return_value = []

        result = await get_chat_sessions_history(mock_history, limit=10, offset=5)

        assert result == []
        mock_history.get_chat_sessions_history.assert_called_once_with(limit=10, offset=5)


class TestGetChatSessionMessagesHistory:
    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_get_messages_success(self, mock_generate_id):
        mock_generate_id.return_value = "corr-id"

        mock_history = _mock_chat_history()
        mock_message = Mock(spec=SessionMessage)
        mock_history.get_chat_session_messages_history.return_value = [mock_message]

        result = await get_chat_session_messages_history("session-1", mock_history)

        assert result == [mock_message]
        mock_history.get_chat_session_messages_history.assert_called_once_with("session-1", limit=None, offset=None)


class TestCreateChatSessionMessagesHistory:
    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_create_session_success(self, mock_generate_id):
        mock_generate_id.return_value = "corr-id"

        mock_history = _mock_chat_history()
        mock_session = Session(
            session_id="new-session",
            session_type=SessionType.AGENT,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        mock_history.create_chat_session_messages_history.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {}

        result = await create_chat_session_messages_history("new-session", mock_response, mock_history)

        assert result == mock_session

    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_create_existing_session_returns_200(self, mock_generate_id):
        mock_generate_id.return_value = "corr-id"

        mock_history = _mock_chat_history()
        mock_history.create_chat_session_messages_history.return_value = None

        mock_response = Mock()
        mock_response.headers = {}

        result = await create_chat_session_messages_history("existing-session", mock_response, mock_history)

        assert mock_response.status_code == 200
        assert result.session_id == "existing-session"
        assert result.session_type == SessionType.AGENT

    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_create_new_session_returns_201(self, mock_generate_id):
        mock_generate_id.return_value = "corr-id"

        mock_history = _mock_chat_history()
        mock_session = Session(
            session_id="new-session",
            session_type=SessionType.AGENT,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        mock_history.create_chat_session_messages_history.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {}

        result = await create_chat_session_messages_history("new-session", mock_response, mock_history)

        assert result == mock_session

    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_content_location_header_set_on_200(self, mock_generate_id):
        mock_generate_id.return_value = "corr-id"

        mock_history = _mock_chat_history()
        mock_history.create_chat_session_messages_history.return_value = None

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        await create_chat_session_messages_history("existing-session", mock_response, mock_history)

        assert mock_response.headers["Content-Location"] == "/chat/history/existing-session"

    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_content_location_header_set_on_201(self, mock_generate_id):
        mock_generate_id.return_value = "corr-id"

        mock_history = _mock_chat_history()
        mock_session = Session(
            session_id="new-session",
            session_type=SessionType.AGENT,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        mock_history.create_chat_session_messages_history.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {}

        await create_chat_session_messages_history("new-session", mock_response, mock_history)

        assert mock_response.headers["Content-Location"] == "/chat/history/new-session"


class TestDeleteChatSessionMessagesHistory:
    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_delete_session_success(self, mock_generate_id):
        mock_generate_id.return_value = "corr-id"

        mock_history = _mock_chat_history()
        mock_history.get_chat_sessions_history.return_value = [
            Session(
                session_id="session-1",
                session_type=SessionType.AGENT,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
        ]

        await delete_chat_session_messages_history("session-1", mock_history)

        mock_history.delete_chat_session_messages_history.assert_called_once_with("session-1")

    @patch("strands_base_agent.api.routes.chat_history.generate_correlation_id")
    async def test_delete_nonexistent_session_returns_404(self, mock_generate_id):
        mock_generate_id.return_value = "corr-id"

        mock_history = _mock_chat_history()
        mock_history.get_chat_sessions_history.return_value = []

        with pytest.raises(HTTPException) as exc_info:
            await delete_chat_session_messages_history("nonexistent-session", mock_history)

        assert exc_info.value.status_code == 404
        assert "nonexistent-session" in exc_info.value.detail
        mock_history.delete_chat_session_messages_history.assert_not_called()


class TestSetChatHistoryContentLocation:
    def test_sets_header_on_success(self):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {}

        set_chat_history_content_location("session-1", mock_response)

        assert mock_response.headers["Content-Location"] == "/chat/history/session-1"
