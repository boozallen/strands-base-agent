# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
from unittest.mock import AsyncMock, Mock

import pytest

from strands_base_agent.server import ReconnectingAgentProxy


def _agen(items):
    async def _gen():
        for item in items:
            yield item

    return _gen()


@pytest.mark.asyncio
async def test_reconnecting_proxy_stream_retries_once_after_mcp_failure_event():
    # First agent emits an MCP-failure-shaped event (should trigger stale + retry)
    agent1 = Mock()
    agent1.stream_async = Mock(return_value=_agen([{"error": "Connection to the MCP server was closed"}]))
    agent1.close = Mock(return_value=None)

    # Recreated agent succeeds
    agent2 = Mock()
    agent2.stream_async = Mock(return_value=_agen([{"type": "final", "text": "ok"}]))
    agent2.close = Mock(return_value=None)

    factory = Mock()
    factory.create_agent = AsyncMock(side_effect=[agent1, agent2])

    proxy = await ReconnectingAgentProxy.create(factory, max_retries=1)

    events = []
    async for event in proxy.stream_async("hello"):
        events.append(event)

    assert events == [{"type": "final", "text": "ok"}]
    assert factory.create_agent.await_count == 2  # initial + one recreate


@pytest.mark.asyncio
async def test_reconnecting_proxy_invoke_retries_once_after_mcp_exception():
    agent1 = Mock()
    agent1.invoke_async = AsyncMock(side_effect=RuntimeError("Connection to the MCP server was closed"))
    agent1.close = Mock(return_value=None)

    agent2 = Mock()
    agent2.invoke_async = AsyncMock(return_value={"status": "ok"})
    agent2.close = Mock(return_value=None)

    factory = Mock()
    factory.create_agent = AsyncMock(side_effect=[agent1, agent2])

    proxy = await ReconnectingAgentProxy.create(factory, max_retries=1)

    result = await proxy.invoke_async("payload")

    assert result == {"status": "ok"}
    assert factory.create_agent.await_count == 2
    agent1.invoke_async.assert_awaited_once()
    agent2.invoke_async.assert_awaited_once()
