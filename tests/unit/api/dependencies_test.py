# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for FastAPI dependency injection integration."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from foundry_agent_core import AgentBackend, DependencyContainer
from foundry_agent_fastapi.mappers import api_request_to_domain, domain_response_to_api
from foundry_strands_agent import AgentService

from strands_base_agent.api.dependencies import (
    get_agent_backend,
    get_agent_service,
    get_container,
    get_correlation_id,
)


class TestGetContainer:
    @patch("strands_base_agent.api.dependencies.get_dependency_container")
    def test_get_container_returns_application_container(self, mock_get_dependency_container):
        mock_container = MagicMock(spec=DependencyContainer)
        mock_get_dependency_container.return_value = mock_container

        result = get_container()

        assert result == mock_container
        mock_get_dependency_container.assert_called_once()

    @patch("strands_base_agent.api.dependencies.get_dependency_container")
    def test_get_container_propagates_runtime_error(self, mock_get_dependency_container):
        mock_get_dependency_container.side_effect = RuntimeError("Container not initialized")

        with pytest.raises(RuntimeError) as exc_info:
            get_container()

        assert "Container not initialized" in str(exc_info.value)


class TestGetAgentBackend:
    def test_get_agent_backend_resolves_from_container(self):
        mock_container = MagicMock(spec=DependencyContainer)
        mock_backend = MagicMock(spec=AgentBackend)
        mock_container.resolve.return_value = mock_backend

        result = get_agent_backend(mock_container)

        assert result == mock_backend
        mock_container.resolve.assert_called_once_with(AgentBackend)


class TestGetAgentService:
    @patch("strands_base_agent.api.dependencies.create_agent_service")
    def test_get_agent_service_creates_service_with_container(self, mock_create_agent_service):
        mock_container = MagicMock(spec=DependencyContainer)
        mock_agent_service = MagicMock(spec=AgentService)
        mock_create_agent_service.return_value = mock_agent_service

        result = get_agent_service(mock_container)

        assert result == mock_agent_service
        mock_create_agent_service.assert_called_once_with(mock_container)

    @patch("strands_base_agent.api.dependencies.create_agent_service")
    def test_get_agent_service_returns_fresh_instance(self, mock_create_agent_service):
        mock_container = MagicMock(spec=DependencyContainer)
        mock_agent_service_1 = MagicMock(spec=AgentService)
        mock_agent_service_2 = MagicMock(spec=AgentService)
        mock_create_agent_service.side_effect = [mock_agent_service_1, mock_agent_service_2]

        result_1 = get_agent_service(mock_container)
        result_2 = get_agent_service(mock_container)

        assert result_1 != result_2
        assert mock_create_agent_service.call_count == 2


class TestMappersModule:
    def test_api_request_mapper_is_callable(self):
        assert callable(api_request_to_domain)

    def test_domain_response_mapper_is_callable(self):
        assert callable(domain_response_to_api)

    def test_mappers_are_distinct_functions(self):
        assert api_request_to_domain is not domain_response_to_api


class TestGetCorrelationId:
    def test_get_correlation_id_from_request_state(self):
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.state.correlation_id = "test-correlation-id"

        result = get_correlation_id(mock_request)

        assert result == "test-correlation-id"

    def test_get_correlation_id_missing_returns_empty_string(self):
        mock_request = MagicMock(spec=Request)
        mock_state = MagicMock()
        if hasattr(mock_state, "correlation_id"):
            delattr(mock_state, "correlation_id")
        mock_request.state = mock_state

        result = get_correlation_id(mock_request)

        assert result == ""

    def test_get_correlation_id_no_state_returns_empty_string(self):
        mock_request = MagicMock(spec=Request)
        del mock_request.state

        result = get_correlation_id(mock_request)

        assert result == ""


class TestDependencyIntegration:
    @patch("strands_base_agent.api.dependencies.get_dependency_container")
    @patch("strands_base_agent.api.dependencies.create_agent_service")
    def test_dependency_chain_integration(self, mock_create_agent_service, mock_get_dependency_container):
        mock_container = MagicMock(spec=DependencyContainer)
        mock_agent_service = MagicMock(spec=AgentService)

        mock_get_dependency_container.return_value = mock_container
        mock_create_agent_service.return_value = mock_agent_service

        container = get_container()
        agent_service = get_agent_service(container)

        assert container == mock_container
        assert agent_service == mock_agent_service

        mock_get_dependency_container.assert_called_once()
        mock_create_agent_service.assert_called_once_with(mock_container)

    def test_correlation_id_dependency_isolation(self):
        mock_request_1 = MagicMock(spec=Request)
        mock_request_1.state = MagicMock()
        mock_request_1.state.correlation_id = "correlation-1"

        mock_request_2 = MagicMock(spec=Request)
        mock_request_2.state = MagicMock()
        mock_request_2.state.correlation_id = "correlation-2"

        correlation_1 = get_correlation_id(mock_request_1)
        correlation_2 = get_correlation_id(mock_request_2)

        assert correlation_1 == "correlation-1"
        assert correlation_2 == "correlation-2"
        assert correlation_1 != correlation_2


class TestDependencyTypeAliases:
    def test_type_aliases_import_correctly(self):
        from strands_base_agent.api.dependencies import (
            AgentBackendDep,
            AgentServiceDep,
            ChatHistoryManagerDep,
            ContainerDep,
            CorrelationIdDep,
        )

        assert ContainerDep is not None
        assert AgentBackendDep is not None
        assert AgentServiceDep is not None
        assert ChatHistoryManagerDep is not None
        assert CorrelationIdDep is not None
