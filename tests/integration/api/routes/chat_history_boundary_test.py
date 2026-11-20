# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for chat history session_id path-parameter boundary validation."""

from unittest.mock import AsyncMock, Mock
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from strands.session.session_repository import SessionRepository

from foundry_strands_agent import AgentFactory, ChatHistoryManager

from strands_base_agent.api.dependencies import get_agent_factory, get_chat_history_manager
from strands_base_agent.api.routes.chat_history import router


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("STRANDS_CHAT_HISTORY_DELETE_ENABLED", "true")
    app = FastAPI()
    app.include_router(router)

    mock_history = AsyncMock(spec=ChatHistoryManager)
    mock_history.get_chat_session_messages_history.return_value = []
    mock_history.get_chat_sessions_history.return_value = []
    mock_history.create_chat_session_messages_history.return_value = None
    app.dependency_overrides[get_chat_history_manager] = lambda: mock_history

    mock_repository = Mock(spec=SessionRepository)
    mock_repository.read_session.return_value = None
    mock_factory = Mock(spec=AgentFactory)
    mock_factory.create_session_repository.return_value = mock_repository
    app.dependency_overrides[get_agent_factory] = lambda: mock_factory

    return TestClient(app, raise_server_exceptions=True)


VALID_SESSION_ID = "valid-session-id"
TOO_SHORT_SESSION_ID = "short"
TOO_LONG_SESSION_ID = "a" * 129
DISALLOWED_CHARS_SESSION_ID = "bad session id"


class TestSessionIdControlCharacterRejection:
    def test_get_rejects_newline_in_session_id(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/chat/history/{quote('valid\nsession')}")

        assert response.status_code == 422

    def test_put_rejects_control_character_in_session_id(self, client: TestClient) -> None:
        response = client.put(f"/api/v1/chat/history/{quote('valid\x00session')}")

        assert response.status_code == 422

    def test_delete_rejects_ansi_escape_in_session_id(self, client: TestClient) -> None:
        response = client.delete(f"/api/v1/chat/history/{quote('valid\x1b[31msession')}")

        assert response.status_code == 422


class TestSessionIdLengthRejection:
    def test_get_rejects_session_id_shorter_than_8_chars(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/chat/history/{TOO_SHORT_SESSION_ID}")

        assert response.status_code == 422

    def test_put_rejects_session_id_shorter_than_8_chars(self, client: TestClient) -> None:
        response = client.put(f"/api/v1/chat/history/{TOO_SHORT_SESSION_ID}")

        assert response.status_code == 422

    def test_get_rejects_session_id_longer_than_128_chars(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/chat/history/{TOO_LONG_SESSION_ID}")

        assert response.status_code == 422

    def test_put_rejects_session_id_longer_than_128_chars(self, client: TestClient) -> None:
        response = client.put(f"/api/v1/chat/history/{TOO_LONG_SESSION_ID}")

        assert response.status_code == 422


class TestSessionIdCharsetRejection:
    def test_get_rejects_disallowed_characters(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/chat/history/{quote(DISALLOWED_CHARS_SESSION_ID)}")

        assert response.status_code == 422

    def test_delete_rejects_disallowed_characters(self, client: TestClient) -> None:
        response = client.delete(f"/api/v1/chat/history/{quote('bad@id.here')}")

        assert response.status_code == 422


class TestWellFormedSessionIdAccepted:
    def test_get_accepts_well_formed_session_id(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/chat/history/{VALID_SESSION_ID}")

        assert response.status_code == 200

    def test_put_accepts_well_formed_session_id(self, client: TestClient) -> None:
        response = client.put(f"/api/v1/chat/history/{VALID_SESSION_ID}")

        assert response.status_code in (200, 201)

    def test_delete_accepts_well_formed_session_id_but_404s_when_missing(self, client: TestClient) -> None:
        response = client.delete(f"/api/v1/chat/history/{VALID_SESSION_ID}")

        assert response.status_code == 404
