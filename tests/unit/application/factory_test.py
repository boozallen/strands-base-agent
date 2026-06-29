# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for application factory implementation.

Tests application factory functionality including container creation,
service registration, configuration loading, and error handling
following the Arrange-Act-Assert pattern.
"""

from unittest.mock import Mock, patch

import pytest

from foundry_agent_core import (
    DependencyContainer,
    ErrorTranslator,
    InvalidConfigurationError,
    QueryProcessor,
    ResponseProcessor,
)
from foundry_strands_agent import AgentConfig, AgentFactory, AgentModelConfig, AgentToolRegistry, ChatHistoryManager

from strands_base_agent.application.factory import create_application_container


class TestApplicationFactory:
    """Test application factory implementation."""

    @pytest.fixture
    def mock_agent_config(self) -> AgentConfig:
        """Create mock AgentConfig for testing."""
        model_config = AgentModelConfig(
            provider="bedrock",
            model_id="claude-3-5-sonnet-20241022",
            temperature=0.3,
        )
        return AgentConfig(
            model=model_config,
            system_prompt="Test system prompt",
        )

    @pytest.fixture
    def mock_container(self) -> Mock:
        """Create mock dependency container."""
        container = Mock(spec=DependencyContainer)
        container.register_factory = Mock()
        container.register_factory_with_dependencies = Mock()
        container.get_registered_types = Mock(return_value=[])
        return container

    @pytest.fixture
    def mock_error_translator(self) -> Mock:
        """Create mock error translator."""
        return Mock(spec=ErrorTranslator)

    @patch("strands_base_agent.application.factory.Path.exists", return_value=False)
    @patch("strands_base_agent.application.factory.AgentConfig.from_env")
    @patch("strands_base_agent.application.factory.create_dependency_container")
    @patch("strands_base_agent.application.factory.create_error_translator")
    def test_create_application_container_success(
        self,
        mock_create_error_translator: Mock,
        mock_create_container: Mock,
        mock_load_config: Mock,
        _mock_path_exists: Mock,
        mock_agent_config: AgentConfig,
        mock_container: Mock,
        mock_error_translator: Mock,
    ) -> None:
        """Test successful application container creation with valid configuration."""
        mock_load_config.return_value = mock_agent_config
        mock_create_container.return_value = mock_container
        mock_create_error_translator.return_value = mock_error_translator

        result = create_application_container()

        assert result == mock_container
        mock_load_config.assert_called_once()
        mock_create_container.assert_called_once()

        # Verify AgentConfig registration
        agent_config_call = mock_container.register_factory.call_args_list[0]
        assert agent_config_call[0][0] == AgentConfig
        assert agent_config_call[1]["singleton"] is True

        # Verify ErrorTranslator registration
        error_translator_call = mock_container.register_factory.call_args_list[1]
        assert error_translator_call[0][0] == ErrorTranslator
        assert error_translator_call[1]["singleton"] is True

    @patch("strands_base_agent.application.factory.Path.exists", return_value=False)
    @patch("strands_base_agent.application.factory.AgentConfig.from_env")
    def test_create_application_container_config_error(self, mock_load_config: Mock, _mock_path_exists: Mock) -> None:
        """Test application container creation with configuration error."""
        mock_load_config.side_effect = InvalidConfigurationError("test_key", "invalid_value", "Invalid configuration")

        with pytest.raises(InvalidConfigurationError) as exc_info:
            create_application_container()

        assert "Invalid configuration" in str(exc_info.value)
        mock_load_config.assert_called_once()

    @patch("strands_base_agent.application.factory.Path.exists", return_value=False)
    @patch("strands_base_agent.application.factory.AgentConfig.from_env")
    @patch("strands_base_agent.application.factory.create_dependency_container")
    def test_create_application_container_container_error(
        self,
        mock_create_container: Mock,
        mock_load_config: Mock,
        _mock_path_exists: Mock,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test application container creation with container creation error."""
        mock_load_config.return_value = mock_agent_config
        mock_create_container.side_effect = RuntimeError("Container creation failed")

        with pytest.raises(RuntimeError) as exc_info:
            create_application_container()

        assert "Container creation failed" in str(exc_info.value)
        mock_load_config.assert_called_once()
        mock_create_container.assert_called_once()

    @patch("strands_base_agent.application.factory.Path.exists", return_value=False)
    @patch("strands_base_agent.application.factory.AgentConfig.from_env")
    @patch("strands_base_agent.application.factory.create_dependency_container")
    @patch("strands_base_agent.application.factory.create_error_translator")
    def test_create_application_container_service_registration_error(
        self,
        mock_create_error_translator: Mock,
        mock_create_container: Mock,
        mock_load_config: Mock,
        _mock_path_exists: Mock,
        mock_agent_config: AgentConfig,
        mock_error_translator: Mock,
    ) -> None:
        """Test application container creation with service registration error."""
        mock_load_config.return_value = mock_agent_config
        mock_create_error_translator.return_value = mock_error_translator

        mock_container = Mock(spec=DependencyContainer)
        mock_container.register_factory.side_effect = RuntimeError("Service registration failed")
        mock_create_container.return_value = mock_container

        with pytest.raises(RuntimeError) as exc_info:
            create_application_container()

        assert "Service registration failed" in str(exc_info.value)
        mock_load_config.assert_called_once()
        mock_create_container.assert_called_once()
        mock_container.register_factory.assert_called_once()

    @patch("strands_base_agent.application.factory.Path.exists", return_value=False)
    @patch("strands_base_agent.application.factory.AgentConfig.from_env")
    @patch("strands_base_agent.application.factory.create_dependency_container")
    @patch("strands_base_agent.application.factory.create_error_translator")
    def test_create_application_container_factory_functions_called(
        self,
        mock_create_error_translator: Mock,
        mock_create_container: Mock,
        mock_load_config: Mock,
        _mock_path_exists: Mock,
        mock_agent_config: AgentConfig,
        mock_container: Mock,
        mock_error_translator: Mock,
    ) -> None:
        """Test that all factory functions are called correctly."""
        mock_load_config.return_value = mock_agent_config
        mock_create_container.return_value = mock_container
        mock_create_error_translator.return_value = mock_error_translator

        create_application_container()

        error_factory = mock_container.register_factory.call_args_list[1][0][1]
        assert error_factory() == mock_error_translator
        mock_create_error_translator.assert_called_once()


class TestProtocolRegistrations:
    """Test that all extension-point protocols are registered."""

    @pytest.fixture
    def mock_agent_config(self) -> AgentConfig:
        """Create mock AgentConfig for testing."""
        model_config = AgentModelConfig(
            provider="bedrock",
            model_id="claude-3-5-sonnet-20241022",
            temperature=0.3,
        )
        return AgentConfig(
            model=model_config,
            system_prompt="Test system prompt",
        )

    @patch("strands_base_agent.application.factory.Path.exists", return_value=False)
    @patch("strands_base_agent.application.factory.AgentConfig.from_env")
    @patch("strands_base_agent.application.factory.create_dependency_container")
    @patch("strands_base_agent.application.factory.create_error_translator")
    def test_all_protocols_registered(
        self,
        mock_create_error_translator: Mock,
        mock_create_container: Mock,
        mock_load_config: Mock,
        _mock_path_exists: Mock,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test that all extension-point protocols are registered in the container."""
        mock_load_config.return_value = mock_agent_config
        mock_container = Mock(spec=DependencyContainer)
        mock_container.register_factory = Mock()
        mock_container.register_factory_with_dependencies = Mock()
        mock_container.get_registered_types = Mock(return_value=[])
        mock_create_container.return_value = mock_container

        create_application_container()

        registered_types = []
        for call in mock_container.register_factory.call_args_list:
            registered_types.append(call[0][0])
        for call in mock_container.register_factory_with_dependencies.call_args_list:
            registered_types.append(call[0][0])

        assert AgentConfig in registered_types
        assert ErrorTranslator in registered_types
        assert ResponseProcessor in registered_types
        assert AgentToolRegistry in registered_types
        assert ChatHistoryManager in registered_types
        assert QueryProcessor in registered_types
        assert len(registered_types) == 6

    @patch("strands_base_agent.application.factory.Path.exists", return_value=False)
    @patch("strands_base_agent.application.factory.AgentConfig.from_env")
    @patch("strands_base_agent.application.factory.create_dependency_container")
    @patch("strands_base_agent.application.factory.create_error_translator")
    def test_chat_history_manager_depends_on_agent_factory(
        self,
        mock_create_error_translator: Mock,
        mock_create_container: Mock,
        mock_load_config: Mock,
        _mock_path_exists: Mock,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test that ChatHistoryManager is registered with AgentFactory dependency."""
        mock_load_config.return_value = mock_agent_config
        mock_container = Mock(spec=DependencyContainer)
        mock_container.register_factory = Mock()
        mock_container.register_factory_with_dependencies = Mock()
        mock_container.get_registered_types = Mock(return_value=[])
        mock_create_container.return_value = mock_container

        create_application_container()

        chat_history_call = None
        for call in mock_container.register_factory_with_dependencies.call_args_list:
            if call[0][0] == ChatHistoryManager:
                chat_history_call = call
                break

        assert chat_history_call is not None
        assert AgentFactory in chat_history_call[1]["dependencies"]

    @patch("strands_base_agent.application.factory.Path.exists", return_value=False)
    @patch("strands_base_agent.application.factory.AgentConfig.from_env")
    @patch("strands_base_agent.application.factory.create_dependency_container")
    @patch("strands_base_agent.application.factory.create_error_translator")
    def test_query_processor_depends_on_three_protocols(
        self,
        mock_create_error_translator: Mock,
        mock_create_container: Mock,
        mock_load_config: Mock,
        _mock_path_exists: Mock,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test that QueryProcessor is registered with correct dependencies."""
        mock_load_config.return_value = mock_agent_config
        mock_container = Mock(spec=DependencyContainer)
        mock_container.register_factory = Mock()
        mock_container.register_factory_with_dependencies = Mock()
        mock_container.get_registered_types = Mock(return_value=[])
        mock_create_container.return_value = mock_container

        create_application_container()

        query_processor_call = None
        for call in mock_container.register_factory_with_dependencies.call_args_list:
            if call[0][0] == QueryProcessor:
                query_processor_call = call
                break

        assert query_processor_call is not None
        dependencies = query_processor_call[1]["dependencies"]
        assert AgentFactory in dependencies
        assert AgentToolRegistry in dependencies
        assert ResponseProcessor in dependencies
        assert len(dependencies) == 3
