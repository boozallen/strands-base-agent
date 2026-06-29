# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for server.py utility functions and ReconnectingAgentProxy."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from strands_base_agent.server import ReconnectingAgentProxy


class TestReconnectingAgentProxyCreate:
    @pytest.mark.asyncio
    async def test_create_calls_factory_and_returns_proxy(self):
        mock_agent = MagicMock()
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory, max_retries=2)

        mock_factory.create_agent.assert_awaited_once()
        assert proxy._agent is mock_agent
        assert proxy._max_retries == 2


class TestReconnectingAgentProxyGetattr:
    @pytest.mark.asyncio
    async def test_getattr_returns_attribute_from_agent(self):
        mock_agent = MagicMock()
        mock_agent.name = "test-agent"
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        assert proxy.name == "test-agent"

    @pytest.mark.asyncio
    async def test_getattr_returns_callable_from_agent(self):
        mock_agent = MagicMock()
        mock_agent.some_method = MagicMock(return_value="result")
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        result = proxy.some_method()
        assert result == "result"


class TestReconnectingAgentProxyInvokeAsync:
    @pytest.mark.asyncio
    async def test_invoke_async_delegates_to_agent(self):
        mock_agent = AsyncMock()
        mock_agent.invoke_async = AsyncMock(return_value="response")
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        result = await proxy.invoke_async("hello")
        assert result == "response"
        mock_agent.invoke_async.assert_awaited_once_with("hello")

    @pytest.mark.asyncio
    async def test_invoke_async_retries_on_mcp_error(self):
        mock_agent = AsyncMock()
        mock_agent.invoke_async = AsyncMock(side_effect=RuntimeError("MCP connection error"))
        new_agent = AsyncMock()
        new_agent.invoke_async = AsyncMock(return_value="recovered")

        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(side_effect=[mock_agent, new_agent])

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        result = await proxy.invoke_async("hello")
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_invoke_async_raises_non_mcp_error(self):
        mock_agent = AsyncMock()
        mock_agent.invoke_async = AsyncMock(side_effect=ValueError("unrelated"))
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        with pytest.raises(ValueError, match="unrelated"):
            await proxy.invoke_async("hello")


class TestReconnectingAgentProxyAclose:
    @pytest.mark.asyncio
    async def test_aclose_calls_close_on_agent(self):
        mock_agent = MagicMock()
        mock_agent.close = MagicMock(return_value=None)
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        await proxy.aclose()
        mock_agent.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_handles_async_close(self):
        mock_agent = MagicMock()

        async def async_close():
            pass

        mock_agent.close = MagicMock(return_value=async_close())
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        await proxy.aclose()
        mock_agent.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_handles_no_close_method(self):
        mock_agent = MagicMock(spec=[])
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        await proxy.aclose()


class TestIsMcpError:
    @pytest.mark.asyncio
    async def test_detects_mcp_errors(self):
        mock_agent = MagicMock()
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        assert proxy._is_mcp_error(RuntimeError("MCP connection failed"))
        assert proxy._is_mcp_error(RuntimeError("client session is not running"))
        assert not proxy._is_mcp_error(RuntimeError("some other error"))

    @pytest.mark.asyncio
    async def test_event_has_mcp_failure(self):
        mock_agent = MagicMock()
        mock_factory = AsyncMock()
        mock_factory.create_agent = AsyncMock(return_value=mock_agent)

        proxy = await ReconnectingAgentProxy.create(mock_factory)

        assert proxy._event_has_mcp_failure({"error": "MCPClientInitializationError"})
        assert proxy._event_has_mcp_failure({"msg": "tool execution failed"})
        assert not proxy._event_has_mcp_failure({"msg": "everything is fine"})
