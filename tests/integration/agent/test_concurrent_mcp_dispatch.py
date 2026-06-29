# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for concurrent multi-agent MCP dispatch.

Verifies that multiple agents with MCP tools can be invoked concurrently
via asyncio.gather without event loop conflicts (GH #326).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from strands_base_agent.server import ReconnectingAgentProxy


class _FakeAgent:
    """Minimal fake agent that simulates invoke_async and stream_async."""

    def __init__(self, name: str, response: str, delay: float = 0.01):
        self.name = name
        self.description = ""
        self._response = response
        self._delay = delay

    async def invoke_async(self, query: str) -> str:
        await asyncio.sleep(self._delay)
        return f"[{self.name}] {self._response}: {query}"

    async def stream_async(self, query: str):
        await asyncio.sleep(self._delay)
        yield {"data": f"[{self.name}] chunk1"}
        await asyncio.sleep(self._delay)
        yield {"data": f"[{self.name}] chunk2"}
        yield {"result": f"[{self.name}] {self._response}"}

    def close(self):
        pass


def _make_factory(agents: list[_FakeAgent]):
    """Create a mock factory that yields agents from the list in order."""
    factory = Mock()
    factory.create_agent = AsyncMock(side_effect=agents)
    return factory


@pytest.mark.asyncio
async def test_concurrent_invoke_async_no_event_loop_conflict():
    """Multiple agents invoked concurrently via asyncio.gather complete without errors."""
    agents = [_FakeAgent(f"agent-{i}", f"response-{i}") for i in range(3)]
    factories = [_make_factory([a]) for a in agents]

    proxies = [await ReconnectingAgentProxy.create(f, max_retries=1) for f in factories]

    results = await asyncio.gather(
        proxies[0].invoke_async("query-0"),
        proxies[1].invoke_async("query-1"),
        proxies[2].invoke_async("query-2"),
    )

    assert results[0] == "[agent-0] response-0: query-0"
    assert results[1] == "[agent-1] response-1: query-1"
    assert results[2] == "[agent-2] response-2: query-2"


@pytest.mark.asyncio
async def test_concurrent_stream_async_no_event_loop_conflict():
    """Multiple agents streamed concurrently via asyncio.gather complete without errors."""
    agents = [_FakeAgent(f"agent-{i}", f"result-{i}") for i in range(3)]
    factories = [_make_factory([a]) for a in agents]

    proxies = [await ReconnectingAgentProxy.create(f, max_retries=1) for f in factories]

    async def collect_stream(proxy, query):
        events = []
        async for event in proxy.stream_async(query):
            events.append(event)
        return events

    results = await asyncio.gather(
        collect_stream(proxies[0], "q0"),
        collect_stream(proxies[1], "q1"),
        collect_stream(proxies[2], "q2"),
    )

    for i, events in enumerate(results):
        assert any(f"agent-{i}" in str(e) for e in events)
        assert len(events) >= 2


@pytest.mark.asyncio
async def test_concurrent_invoke_with_mcp_retry():
    """Concurrent agents where one hits MCP error and retries still complete."""
    good_agent = _FakeAgent("good", "ok")
    failing_agent = MagicMock()
    failing_agent.invoke_async = AsyncMock(side_effect=RuntimeError("Connection to the MCP server was closed"))
    failing_agent.close = Mock(return_value=None)
    recovered_agent = _FakeAgent("recovered", "back")

    good_factory = _make_factory([good_agent])
    failing_factory = Mock()
    failing_factory.create_agent = AsyncMock(side_effect=[failing_agent, recovered_agent])

    proxy_good = await ReconnectingAgentProxy.create(good_factory, max_retries=1)
    proxy_failing = await ReconnectingAgentProxy.create(failing_factory, max_retries=1)

    results = await asyncio.gather(
        proxy_good.invoke_async("hello"),
        proxy_failing.invoke_async("world"),
    )

    assert results[0] == "[good] ok: hello"
    assert results[1] == "[recovered] back: world"


@pytest.mark.asyncio
async def test_high_concurrency_invoke():
    """10 agents invoked simultaneously all complete without interference."""
    count = 10
    agents = [_FakeAgent(f"agent-{i}", f"resp-{i}", delay=0.005) for i in range(count)]
    factories = [_make_factory([a]) for a in agents]
    proxies = [await ReconnectingAgentProxy.create(f, max_retries=1) for f in factories]

    results = await asyncio.gather(*(proxy.invoke_async(f"query-{i}") for i, proxy in enumerate(proxies)))

    assert len(results) == count
    for i, result in enumerate(results):
        assert f"agent-{i}" in result
        assert f"query-{i}" in result
