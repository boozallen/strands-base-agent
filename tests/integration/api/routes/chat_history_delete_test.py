# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the chat session delete opt-in gate against a real encrypted file store."""

import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundry_agent_core.encryption import is_encrypted
from foundry_strands_agent import AgentFactory, ChatHistorian
from foundry_strands_agent.encrypted_session import EncryptedFileSessionManager

from strands_base_agent.api.dependencies import get_agent_factory, get_chat_history_manager
from strands_base_agent.api.routes.chat_history import router

SESSION_ID = "delete-gate-session"
URL = f"/api/v1/chat/history/{SESSION_ID}"


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    return tmp_path / "sessions"


@pytest.fixture
def client(storage_dir: Path) -> TestClient:
    encryption_key = os.urandom(32)
    factory = Mock(spec=AgentFactory)
    factory.create_session_repository.side_effect = lambda: EncryptedFileSessionManager(
        encryption_key=encryption_key, session_id="default", storage_dir=str(storage_dir)
    )
    historian = ChatHistorian(factory, Mock())

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chat_history_manager] = lambda: historian
    app.dependency_overrides[get_agent_factory] = lambda: factory
    return TestClient(app, raise_server_exceptions=True)


class TestDeleteEnabled:
    @pytest.fixture(autouse=True)
    def _delete_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STRANDS_CHAT_HISTORY_DELETE_ENABLED", "true")

    def test_session_created_with_put_can_be_deleted(self, client: TestClient, storage_dir: Path) -> None:
        assert client.put(URL).status_code == 201

        metafile = storage_dir / f"session_{SESSION_ID}" / "session.json"
        assert is_encrypted(json.loads(metafile.read_text()))

        assert client.delete(URL).status_code == 204
        assert not metafile.parent.exists()
        assert client.delete(URL).status_code == 404


class TestDeleteDisabled:
    def test_delete_returns_403_by_default(
        self, client: TestClient, storage_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STRANDS_CHAT_HISTORY_DELETE_ENABLED", raising=False)
        assert client.put(URL).status_code == 201

        response = client.delete(URL)

        assert response.status_code == 403
        assert (storage_dir / f"session_{SESSION_ID}").is_dir()
