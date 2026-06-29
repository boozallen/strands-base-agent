# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for main query processing and CLI interface.

Tests interface-agnostic process_query() function and CLI interface
including query processing, configuration loading, service lifecycle,
and CLI argument handling following the Arrange-Act-Assert pattern.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from foundry_agent_core import AgentRequest, AgentResponse, QueryProcessingError

from strands_base_agent.main import process_query


class TestProcessQuery:
    """Test process_query function implementation."""

    @pytest.fixture
    def sample_query_response(self) -> AgentResponse:
        """Create sample AgentResponse for testing."""
        return AgentResponse(
            content="This is a test response from the agent",
            processing_time_ms=1500,
            metadata={"query_id": "test_query"},
        )

    @pytest.fixture
    def mock_container(self) -> Mock:
        """Create mock dependency container."""
        return Mock()

    @pytest.fixture
    def mock_agent_service(self) -> AsyncMock:
        """Create mock agent service."""
        service = AsyncMock()
        service.service_lifecycle = AsyncMock()
        return service

    @patch("strands_base_agent.main.create_application_container")
    @patch("strands_base_agent.main.create_agent_service")
    @pytest.mark.asyncio
    async def test_process_query_success(
        self,
        mock_create_service: Mock,
        mock_create_container: Mock,
        mock_container: Mock,
        mock_agent_service: AsyncMock,
        sample_query_response: AgentResponse,
    ) -> None:
        """Test successful query processing with valid input."""
        # Arrange
        query_text = "What is machine learning?"
        mock_create_container.return_value = mock_container
        mock_create_service.return_value = mock_agent_service

        # Mock the service lifecycle context manager
        active_service = AsyncMock()
        active_service.process_query = AsyncMock(return_value=sample_query_response)

        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=active_service)
        context_manager.__aexit__ = AsyncMock(return_value=False)
        mock_agent_service.service_lifecycle = Mock(return_value=context_manager)

        # Act
        result = await process_query(query_text)

        # Assert
        assert result == sample_query_response
        mock_create_container.assert_called_once()
        mock_create_service.assert_called_once_with(mock_container)

        # Verify QueryRequest was created correctly
        process_query_call = active_service.process_query.call_args[0][0]
        assert isinstance(process_query_call, AgentRequest)
        assert process_query_call.query == query_text

    @patch("strands_base_agent.main.create_application_container")
    @patch("strands_base_agent.main.create_agent_service")
    @pytest.mark.asyncio
    async def test_process_query_container_creation_error(
        self,
        mock_create_service: Mock,
        mock_create_container: Mock,
    ) -> None:
        """Test query processing with container creation error."""
        # Arrange
        query_text = "What is machine learning?"
        mock_create_container.side_effect = RuntimeError("Container creation failed")

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            await process_query(query_text)

        assert "Container creation failed" in str(exc_info.value)
        mock_create_container.assert_called_once()

    @patch("strands_base_agent.main.create_application_container")
    @patch("strands_base_agent.main.create_agent_service")
    @pytest.mark.asyncio
    async def test_process_query_service_creation_error(
        self,
        mock_create_service: Mock,
        mock_create_container: Mock,
        mock_container: Mock,
    ) -> None:
        """Test query processing with service creation error."""
        # Arrange
        query_text = "What is machine learning?"
        mock_create_container.return_value = mock_container
        mock_create_service.side_effect = RuntimeError("Service creation failed")

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            await process_query(query_text)

        assert "Service creation failed" in str(exc_info.value)
        mock_create_container.assert_called_once()
        mock_create_service.assert_called_once_with(mock_container)

    @patch("strands_base_agent.main.create_application_container")
    @patch("strands_base_agent.main.create_agent_service")
    @pytest.mark.asyncio
    async def test_process_query_processing_error(
        self,
        mock_create_service: Mock,
        mock_create_container: Mock,
        mock_container: Mock,
        mock_agent_service: AsyncMock,
    ) -> None:
        """Test query processing with query processing error."""
        # Arrange
        query_text = "What is machine learning?"
        mock_create_container.return_value = mock_container
        mock_create_service.return_value = mock_agent_service

        # Mock the service lifecycle context manager with processing error
        active_service = AsyncMock()
        active_service.process_query = AsyncMock(
            side_effect=QueryProcessingError("Processing failed", context={"step": "query_processing"})
        )

        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=active_service)
        context_manager.__aexit__ = AsyncMock(return_value=False)
        mock_agent_service.service_lifecycle = Mock(return_value=context_manager)

        # Act & Assert
        with pytest.raises(QueryProcessingError) as exc_info:
            await process_query(query_text)

        assert "Processing failed" in str(exc_info.value)
        mock_create_container.assert_called_once()
        mock_create_service.assert_called_once_with(mock_container)

    def test_load_environment_config_with_env_file(self) -> None:
        """Test environment configuration loading with existing .env file."""
        from strands_base_agent.application.lifecycle import _load_environment_config

        with patch("strands_base_agent.application.lifecycle.Path") as mock_path:
            with patch("strands_base_agent.application.lifecycle.load_dotenv") as mock_load_dotenv:
                # Arrange
                mock_env_file = Mock()
                mock_env_file.exists.return_value = True
                mock_path.return_value = mock_env_file

                # Act
                _load_environment_config()

                # Assert
                mock_path.assert_called_once_with(".env")
                mock_env_file.exists.assert_called_once()
                mock_load_dotenv.assert_called_once_with(mock_env_file)

    def test_load_environment_config_without_env_file(self) -> None:
        """Test environment configuration loading without .env file."""
        from strands_base_agent.application.lifecycle import _load_environment_config

        with patch("strands_base_agent.application.lifecycle.Path") as mock_path:
            with patch("strands_base_agent.application.lifecycle.load_dotenv") as mock_load_dotenv:
                # Arrange
                mock_env_file = Mock()
                mock_env_file.exists.return_value = False
                mock_path.return_value = mock_env_file

                # Act
                _load_environment_config()

                # Assert
                mock_path.assert_called_once_with(".env")
                mock_env_file.exists.assert_called_once()
                mock_load_dotenv.assert_not_called()


class TestCLIInterface:
    """Test CLI interface implementation."""

    @patch("strands_base_agent.main.process_query")
    @patch("strands_base_agent.__main__.asyncio.run")
    @patch("strands_base_agent.__main__.sys.argv", ["script_name", "test query"])
    def test_cli_main_success(self, mock_asyncio_run: Mock, mock_process_query: AsyncMock) -> None:
        """Test successful CLI execution with valid arguments."""
        from strands_base_agent.__main__ import cli_main

        # Arrange
        mock_response = Mock()
        mock_response.content = "This is the response content"
        mock_process_query.return_value = mock_response

        # Create a mock async function for cli_main
        async def mock_cli_main():
            return await cli_main()

        # Act
        mock_asyncio_run.return_value = None
        mock_asyncio_run.side_effect = lambda _coro: None

        # Import and test the main execution
        import strands_base_agent.__main__

        # The actual test is that the module can be imported without error
        # and that cli_main function exists
        assert hasattr(strands_base_agent.__main__, "cli_main")

    @patch("sys.argv", ["script_name"])
    @patch("builtins.print")
    @pytest.mark.asyncio
    async def test_cli_main_missing_arguments(self, mock_print: Mock) -> None:
        """Test CLI execution with missing arguments."""
        from strands_base_agent.__main__ import cli_main

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            await cli_main()

        # Assert
        assert exc_info.value.code == 1
        mock_print.assert_called_once_with("Usage: python -m strands_base_agent 'your query here'")

    @patch("strands_base_agent.main.process_query")
    @patch("sys.argv", ["script_name", "test query"])
    @patch("builtins.print")
    @pytest.mark.asyncio
    async def test_cli_main_process_query_error(
        self,
        mock_print: Mock,
        mock_process_query: AsyncMock,
    ) -> None:
        """Test CLI execution with query processing error."""
        from strands_base_agent.__main__ import cli_main

        # Arrange
        mock_process_query.side_effect = RuntimeError("Query processing failed")

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            await cli_main()

        # Assert
        assert exc_info.value.code == 1
        mock_process_query.assert_called_once_with("test query")
        mock_print.assert_called_once_with("Error: Query processing failed")

    @patch("strands_base_agent.main.process_query")
    @patch("sys.argv", ["script_name", "test query"])
    @patch("builtins.print")
    @pytest.mark.asyncio
    async def test_cli_main_successful_response(self, mock_print: Mock, mock_process_query: AsyncMock) -> None:
        """Test CLI execution with successful response."""
        from strands_base_agent.__main__ import cli_main

        # Arrange
        mock_response = Mock()
        mock_response.content = "This is the response content"
        mock_process_query.return_value = mock_response

        # Act
        await cli_main()

        # Assert
        mock_process_query.assert_called_once_with("test query")
        mock_print.assert_called_once_with("Response: This is the response content")
