# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""End-to-end A2A conversation isolation.

Runs the real A2A server app built by start_server() over ASGI, with the real
StrandsAgentFactory and AgentBuilder. Only the model is fake: it answers with a
secret if one appears earlier in its own message history, and NONE otherwise.
So a context that can see another context's messages answers with the secret.
The last test checks the shape of a streamed A2A answer.
"""

from __future__ import annotations

import os
import re
import secrets
from collections.abc import AsyncIterator
from functools import partial
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from strands.models import Model

from foundry_strands_agent import StrandsAgentFactory

from strands_base_agent.server import start_server

_API_KEY = "isolation-test-key"
_SECRET_PATTERN = re.compile(r"SECRET=(\w+)")


class _HistoryEchoModel(Model):
    """Replies with the last SECRET=<value> seen in the conversation, else NONE."""

    def update_config(self, **model_config: Any) -> None:
        pass

    def get_config(self) -> dict[str, Any]:
        return {}

    async def structured_output(self, *args: Any, **kwargs: Any):  # pragma: no cover - unused
        raise NotImplementedError
        yield {}

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs: Any) -> AsyncIterator[Any]:
        secrets = [
            match
            for message in messages[:-1]
            for block in message.get("content", [])
            for match in _SECRET_PATTERN.findall(block.get("text", ""))
        ]
        answer = secrets[-1] if secrets else "NONE"
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": answer}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}


_CHUNKS = ["Machine learning is a bran", "ch of art", "ificial intelligence."]


class _ChunkedModel(_HistoryEchoModel):
    """Streams a fixed answer in several text chunks, like a real model."""

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs: Any) -> AsyncIterator[Any]:
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        for chunk in _CHUNKS:
            yield {"contentBlockDelta": {"delta": {"text": chunk}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}


_TOOL_FILE = '''from strands import tool


@tool
def weather() -> str:
    """Today's weather."""
    return "72F"
'''


class _ToolTurnModel(_HistoryEchoModel):
    """Says it will look something up and calls `weather`, then answers from the tool result."""

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs: Any) -> AsyncIterator[Any]:
        has_tool_result = any("toolResult" in block for block in messages[-1].get("content", []))
        yield {"messageStart": {"role": "assistant"}}
        if has_tool_result:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": "It is 72F."}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
            return
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": "Let me look that up."}}}
        yield {"contentBlockStop": {}}
        yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": "tool-1", "name": "weather"}}}}
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": "{}"}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}


def _start_app(env: dict[str, str], model_class: type[Model] = _HistoryEchoModel):
    """Run start_server() with uvicorn patched out and return the FastAPI app."""
    captured: dict[str, Any] = {}
    factory = partial(StrandsAgentFactory, model_provider_factories={"fake": lambda _config: model_class()})
    with (
        patch.dict(os.environ, env, clear=True),
        patch("strands_base_agent.server.StrandsAgentFactory", factory),
        patch("uvicorn.run", side_effect=lambda app, **_kw: captured.setdefault("app", app)),
    ):
        start_server()
    return captured["app"]


def _base_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    return {
        "STRANDS_TLS_MODE": "off",
        "STRANDS_API_KEY": _API_KEY,
        "STRANDS_AGENT_PUBLIC_URL": "http://test-agent:8000",
        "STRANDS__MODEL__PROVIDER": "fake",
        "STRANDS__MCP_SERVERS": "[]",
        "STRANDS__TOOLS_DIR": str(tmp_path / "no-tools"),
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        **extra,
    }


def _texts(value: Any) -> list[str]:
    if isinstance(value, dict):
        found = [value["text"]] if isinstance(value.get("text"), str) else []
        return found + [t for v in value.values() for t in _texts(v)]
    if isinstance(value, list):
        return [t for v in value for t in _texts(v)]
    return []


async def _post_message(client: httpx.AsyncClient, context_id: str, text: str, message_id: str) -> dict[str, Any]:
    body = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
                "messageId": message_id,
                "contextId": context_id,
            }
        },
    }
    response = await client.post("/", json=body, headers={"Authorization": f"Bearer {_API_KEY}"})
    response.raise_for_status()
    payload = response.json()
    assert "error" not in payload, payload
    return payload


async def _send(client: httpx.AsyncClient, context_id: str, text: str, message_id: str) -> str:
    payload = await _post_message(client, context_id, text, message_id)
    replies = [t for t in _texts(payload["result"]) if t != text]
    # Compliant streaming sends one part per chunk, so the parts join with no separator.
    return "".join(replies)


async def _run_conversations(app, steps: list[tuple[str, str]]) -> list[str]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return [await _send(client, ctx, text, f"m{i}") for i, (ctx, text) in enumerate(steps)]


@pytest.mark.asyncio
async def test_new_contexts_cannot_see_another_contexts_secret(tmp_path):
    env = _base_env(tmp_path)
    app = _start_app(env)
    with patch.dict(os.environ, env):
        replies = await _run_conversations(
            app,
            [
                ("ctx-one", "Remember this. SECRET=MANGO4410"),
                ("ctx-two", "What secret was shared earlier in this conversation?"),
                ("ctx-three", "What secret was shared earlier in this conversation?"),
                ("ctx-one", "What secret was shared earlier in this conversation?"),
            ],
        )

    assert "MANGO4410" not in replies[1]
    assert "NONE" in replies[1]
    assert "MANGO4410" not in replies[2]
    assert "NONE" in replies[2]
    assert "MANGO4410" in replies[3]


@pytest.mark.asyncio
async def test_agent_card_context_id_is_served_by_a_real_agent(tmp_path):
    """A request reusing the card's context id gets a working agent, not the card stub."""
    env = _base_env(tmp_path)
    app = _start_app(env)
    with patch.dict(os.environ, env):
        replies = await _run_conversations(
            app,
            [
                ("__agent_card__", "Remember this. SECRET=KIWI7"),
                ("__agent_card__", "What secret was shared earlier in this conversation?"),
            ],
        )

    assert "KIWI7" in replies[1]


@pytest.mark.asyncio
async def test_file_sessions_are_per_context(tmp_path):
    """Each context persists to its own session, and only its own history comes back."""
    storage = tmp_path / "sessions"
    env = _base_env(
        tmp_path,
        STRANDS__SESSION_TYPE="file",
        STRANDS__SESSION_STORAGE_DIR=str(storage),
        SESSION_ENCRYPTION_KEY=secrets.token_hex(32),
    )
    question = "What secret was shared earlier in this conversation?"

    with patch.dict(os.environ, env):
        await _run_conversations(
            _start_app(env),
            [("ctx-alpha", "Remember this. SECRET=ALPHA1"), ("ctx-beta", "Remember this. SECRET=BETA2")],
        )
        # A second app on the same storage, as after a restart, restores each session.
        replies = await _run_conversations(_start_app(env), [("ctx-alpha", question), ("ctx-beta", question)])

    session_dirs = sorted(p.name for p in storage.iterdir() if p.is_dir())
    assert len(session_dirs) == 2, session_dirs
    # A2A sessions carry the "a2a." prefix, which a REST session_id cannot contain.
    assert any("a2a.ctx-alpha" in name for name in session_dirs), session_dirs
    assert any("a2a.ctx-beta" in name for name in session_dirs), session_dirs
    assert "ALPHA1" in replies[0] and "BETA2" not in replies[0]
    assert "BETA2" in replies[1] and "ALPHA1" not in replies[1]


@pytest.mark.asyncio
async def test_invalid_context_id_is_an_invalid_params_error(tmp_path):
    """With sessions on, a contextId the session store can't use gets a JSON-RPC client error."""
    env = _base_env(
        tmp_path,
        STRANDS__SESSION_TYPE="file",
        STRANDS__SESSION_STORAGE_DIR=str(tmp_path / "sessions"),
        SESSION_ENCRYPTION_KEY=secrets.token_hex(32),
    )
    app = _start_app(env)
    body = {
        "jsonrpc": "2.0",
        "id": "m0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "hello"}],
                "messageId": "m0",
                "contextId": "a/b",
            }
        },
    }
    with patch.dict(os.environ, env):
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/", json=body, headers={"Authorization": f"Bearer {_API_KEY}"})

    assert response.status_code == 200
    error = response.json()["error"]
    assert error["code"] == -32602
    assert error["message"].startswith("Invalid contextId")
    assert "a/b" not in error["message"]


@pytest.mark.asyncio
async def test_rest_session_ids_cannot_name_an_a2a_session(tmp_path):
    """The "." in "a2a." is outside the REST session_id pattern, so REST can't open an A2A session."""
    env = _base_env(tmp_path)
    app = _start_app(env)
    headers = {"Authorization": f"Bearer {_API_KEY}"}
    with patch.dict(os.environ, env):
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                query = await client.post(
                    "/api/v1/query", json={"query": "hi", "session_id": "a2a.ctx-alpha"}, headers=headers
                )
                history = await client.get("/api/v1/chat/history/a2a.ctx-alpha", headers=headers)

    assert query.status_code == 422
    assert history.status_code == 422


@pytest.mark.asyncio
async def test_streamed_answer_is_one_artifact_not_history_messages(tmp_path, recwarn):
    """A2A-compliant streaming: chunks build one artifact and stay out of history."""
    env = _base_env(tmp_path)
    app = _start_app(env, model_class=_ChunkedModel)
    with patch.dict(os.environ, env):
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                payload = await _post_message(client, "ctx-stream", "What is machine learning?", "m0")

    task = payload["result"]
    assert task["status"]["state"] == "completed"
    assert [message["role"] for message in task["history"]] == ["user"]
    assert len(task["artifacts"]) == 1
    artifact = task["artifacts"][0]
    assert artifact["name"] == "agent_response"
    # The chunks arrive as separate parts; a client joins them to get the answer.
    assert "".join(part["text"] for part in artifact["parts"]) == "".join(_CHUNKS)
    assert not [w for w in recwarn if "enable_a2a_compliant_streaming" in str(w.message)]


@pytest.mark.asyncio
async def test_text_before_a_tool_call_is_part_of_the_artifact(tmp_path):
    """The artifact holds the text of every model turn, joined with no separator, not just the last one."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "weather.py").write_text(_TOOL_FILE)
    env = _base_env(tmp_path, STRANDS__TOOLS_DIR=str(tools_dir), STRANDS__TOOLS_FILES=str(tools_dir / "weather.py"))
    app = _start_app(env, model_class=_ToolTurnModel)
    with patch.dict(os.environ, env):
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                payload = await _post_message(client, "ctx-tool", "What is the weather?", "m0")

    task = payload["result"]
    assert task["status"]["state"] == "completed"
    parts = task["artifacts"][0]["parts"]
    assert "".join(part["text"] for part in parts) == "Let me look that up.It is 72F."
