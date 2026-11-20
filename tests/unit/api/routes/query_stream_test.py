# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.responses import StreamingResponse

from foundry_agent_core import AgentRequest, QueryProcessingError, ValidationError
from foundry_agent_fastapi import QueryAPIRequest
from foundry_strands_agent import AgentService

from strands_base_agent.api.routes.query import _stream_generator, process_query_stream


def _agen(items):
    async def _gen():
        for item in items:
            yield item

    return _gen()


class TestProcessQueryStreamEndpoint:
    @pytest.fixture
    def mock_query_request(self):
        return QueryAPIRequest(
            query="Stream this answer",
            session_id="sess_123",
            max_results=5,
            similarity_threshold=0.7,
        )

    @pytest.fixture
    def mock_domain_request(self):
        return AgentRequest(
            query="Stream this answer",
            session_id="sess_123",
        )

    @pytest.mark.asyncio
    @patch("strands_base_agent.api.routes.query.api_request_to_domain")
    async def test_stream_generator_emits_token_and_done(
        self,
        mock_api_to_domain,
        mock_query_request,
        mock_domain_request,
    ):
        mock_api_to_domain.return_value = mock_domain_request

        mock_service = AsyncMock(spec=AgentService)
        mock_active_service = AsyncMock()
        mock_active_service.process_query_stream = Mock(
            return_value=_agen(
                [
                    {"type": "token", "content": "Hello "},
                    {"type": "token", "content": "world"},
                    {"type": "done", "processing_time_ms": 12.5, "session_id": "sess_123", "query_id": "q1"},
                ]
            )
        )

        @asynccontextmanager
        async def mock_service_lifecycle():
            yield mock_active_service

        mock_service.service_lifecycle = mock_service_lifecycle

        chunks = [chunk async for chunk in _stream_generator(mock_query_request, "corr_1", mock_service)]

        assert any("event: token" in c and "Hello " in c for c in chunks)
        assert any("event: token" in c and "world" in c for c in chunks)
        assert any("event: done" in c and '"correlation_id": "corr_1"' in c for c in chunks)

    @pytest.mark.asyncio
    @patch("strands_base_agent.api.routes.query.api_request_to_domain")
    async def test_stream_generator_validation_error_emits_error_event(self, mock_api_to_domain, mock_query_request):
        mock_api_to_domain.side_effect = ValidationError(
            field_name="query",
            field_value="",
            validation_rule="Query cannot be empty",
        )

        dummy_service = MagicMock(spec=AgentService)
        chunks = [chunk async for chunk in _stream_generator(mock_query_request, "corr_2", dummy_service)]

        assert len(chunks) == 1
        assert "event: error" in chunks[0]
        assert '"error": "Validation error"' in chunks[0]
        assert '"retryable": false' in chunks[0]

    @pytest.mark.asyncio
    @patch("strands_base_agent.api.routes.query.api_request_to_domain")
    async def test_stream_generator_processing_error_emits_error_event(
        self,
        mock_api_to_domain,
        mock_query_request,
        mock_domain_request,
    ):
        mock_api_to_domain.return_value = mock_domain_request

        mock_service = AsyncMock(spec=AgentService)
        mock_active_service = AsyncMock()
        mock_active_service.process_query_stream = Mock(side_effect=QueryProcessingError("stream failed"))

        @asynccontextmanager
        async def mock_service_lifecycle():
            yield mock_active_service

        mock_service.service_lifecycle = mock_service_lifecycle

        chunks = [chunk async for chunk in _stream_generator(mock_query_request, "corr_3", mock_service)]

        assert len(chunks) == 1
        assert "event: error" in chunks[0]
        assert '"error": "Query processing failed"' in chunks[0]

    @pytest.mark.asyncio
    @patch("strands_base_agent.api.routes.query.generate_correlation_id")
    async def test_process_query_stream_returns_streaming_response(self, mock_generate_id, mock_query_request):
        mock_generate_id.return_value = "corr_4"
        mock_service = AsyncMock(spec=AgentService)

        response = await process_query_stream(mock_query_request, mock_service)

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["Connection"] == "keep-alive"
