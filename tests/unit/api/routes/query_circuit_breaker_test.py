# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.responses import JSONResponse

from foundry_agent_core import AgentResponse, QueryProcessingError
from foundry_agent_core.exceptions import AgentCreationError, ToolExecutionError
from foundry_agent_fastapi import QueryAPIRequest

from strands_base_agent.api.circuit_breaker import _CircuitBreaker, _CircuitState


@pytest.fixture(autouse=True)
def _reset_query_circuit():
    from strands_base_agent.api.routes import query

    query._query_circuit = _CircuitBreaker(threshold=5, reset_interval=60.0)
    yield
    query._query_circuit = _CircuitBreaker(threshold=5, reset_interval=60.0)


def _request():
    return QueryAPIRequest(query="hello")


def _mcp_error():
    cause = AgentCreationError("Failed to create Strands Agent: Failed to start MCP client")
    exc = QueryProcessingError("Failed to create agent for query processing: ...")
    exc.__cause__ = cause
    return exc


def _non_mcp_error():
    return QueryProcessingError("Some other validation error")


class TestQueryCircuitBreakerOpens:
    @pytest.mark.asyncio
    async def test_circuit_opens_after_5_mcp_failures(self):
        from strands_base_agent.api.routes import query
        from strands_base_agent.api.routes.query import process_query

        backend = AsyncMock()
        backend.process_message = AsyncMock(side_effect=_mcp_error())

        for _ in range(5):
            with pytest.raises(QueryProcessingError):
                await process_query(_request(), backend)

        assert query._query_circuit.state == _CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_returns_503_when_open(self):
        from strands_base_agent.api.routes import query
        from strands_base_agent.api.routes.query import process_query

        query._query_circuit._state = _CircuitState.OPEN
        query._query_circuit._opened_at = 1000.0

        backend = AsyncMock()

        with patch("strands_base_agent.api.circuit_breaker.time.monotonic", return_value=1010.0):
            result = await process_query(_request(), backend)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 503
        backend.process_message.assert_not_called()


class TestQueryCircuitBreakerNonMcp:
    @pytest.mark.asyncio
    async def test_non_mcp_error_does_not_trip_circuit(self):
        from strands_base_agent.api.routes import query
        from strands_base_agent.api.routes.query import process_query

        backend = AsyncMock()
        backend.process_message = AsyncMock(side_effect=_non_mcp_error())

        for _ in range(6):
            with pytest.raises(QueryProcessingError):
                await process_query(_request(), backend)

        assert query._query_circuit.state == _CircuitState.CLOSED
        assert query._query_circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_tool_execution_failure_does_not_trip_circuit(self):
        from strands_base_agent.api.routes import query
        from strands_base_agent.api.routes.query import process_query

        cause = ToolExecutionError("hello tool returned error: bad input")
        exc = QueryProcessingError("Query processing failed: tool error")
        exc.__cause__ = cause

        backend = AsyncMock()
        backend.process_message = AsyncMock(side_effect=exc)

        for _ in range(6):
            with pytest.raises(QueryProcessingError):
                await process_query(_request(), backend)

        assert query._query_circuit.state == _CircuitState.CLOSED
        assert query._query_circuit.failure_count == 0


class TestQueryCircuitBreakerSuccess:
    @pytest.mark.asyncio
    @patch("strands_base_agent.api.routes.query.domain_response_to_api")
    @patch("strands_base_agent.api.routes.query.api_request_to_domain")
    async def test_successful_query_resets_failure_count(self, mock_to_domain, mock_to_api):
        from strands_base_agent.api.routes import query
        from strands_base_agent.api.routes.query import process_query

        query._query_circuit._failure_count = 3

        backend = AsyncMock()
        backend.process_message = AsyncMock(
            return_value=AgentResponse(content="hi", session_id=None, processing_time_ms=10.0)
        )
        mock_to_api.return_value = AsyncMock(content="hi")

        await process_query(_request(), backend)

        assert query._query_circuit.failure_count == 0
