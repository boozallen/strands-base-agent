# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for query processing API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from foundry_agent_core import AgentBackend, AgentRequest, AgentResponse, QueryProcessingError, ValidationError
from foundry_agent_fastapi import QueryAPIRequest, QueryAPIResponse

from strands_base_agent.api.routes.query import process_query


class TestProcessQueryEndpoint:
    @pytest.fixture
    def mock_query_request(self):
        return QueryAPIRequest(
            query="What are the key architectural patterns?",
            context={"session_id": "test-session"},
        )

    @pytest.fixture
    def mock_domain_request(self):
        return AgentRequest(
            query="What are the key architectural patterns?",
            context={"session_id": "test-session"},
        )

    @pytest.fixture
    def mock_domain_response(self):
        return AgentResponse(
            content="The system uses dependency injection and SOLID principles.",
            processing_time_ms=150.5,
            metadata={"confidence_score": 0.85},
        )

    @pytest.fixture
    def mock_api_response(self):
        return QueryAPIResponse(
            content="The system uses dependency injection and SOLID principles.",
            processing_time_ms=150.5,
            timestamp=datetime.now(),
            correlation_id="test-correlation-id",
        )

    @patch("strands_base_agent.api.routes.query.generate_correlation_id")
    @patch("strands_base_agent.api.routes.query.api_request_to_domain")
    @patch("strands_base_agent.api.routes.query.domain_response_to_api")
    async def test_process_query_success(
        self,
        mock_domain_to_api,
        mock_api_to_domain,
        mock_generate_id,
        mock_query_request,
        mock_domain_request,
        mock_domain_response,
        mock_api_response,
    ):
        mock_generate_id.return_value = "test-correlation-id"
        mock_api_to_domain.return_value = mock_domain_request
        mock_domain_to_api.return_value = mock_api_response

        mock_backend = AsyncMock(spec=AgentBackend)
        mock_backend.process_message.return_value = mock_domain_response

        result = await process_query(mock_query_request, mock_backend)

        assert result == mock_api_response
        mock_api_to_domain.assert_called_once_with(mock_query_request)
        mock_backend.process_message.assert_called_once_with(mock_domain_request)
        mock_domain_to_api.assert_called_once_with(
            mock_domain_response, correlation_id="test-correlation-id", api_version="1.0"
        )

    @patch("strands_base_agent.api.routes.query.generate_correlation_id")
    @patch("strands_base_agent.api.routes.query.api_request_to_domain")
    async def test_process_query_validation_error(
        self,
        mock_api_to_domain,
        mock_generate_id,
        mock_query_request,
    ):
        mock_generate_id.return_value = "test-correlation-id"
        mock_api_to_domain.side_effect = ValidationError(
            field_name="query", field_value="", validation_rule="Query cannot be empty"
        )

        mock_backend = AsyncMock(spec=AgentBackend)

        with pytest.raises(ValidationError):
            await process_query(mock_query_request, mock_backend)

    @patch("strands_base_agent.api.routes.query.generate_correlation_id")
    @patch("strands_base_agent.api.routes.query.api_request_to_domain")
    async def test_process_query_processing_error(
        self,
        mock_api_to_domain,
        mock_generate_id,
        mock_query_request,
        mock_domain_request,
    ):
        mock_generate_id.return_value = "test-correlation-id"
        mock_api_to_domain.return_value = mock_domain_request

        mock_backend = AsyncMock(spec=AgentBackend)
        mock_backend.process_message.side_effect = QueryProcessingError("Agent processing failed")

        with pytest.raises(QueryProcessingError) as exc_info:
            await process_query(mock_query_request, mock_backend)

        assert "Agent processing failed" in str(exc_info.value)
