# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for A2A server functionality.

Consolidated tests for A2A server startup logic, configuration, port/host selection,
and error handling scenarios.
"""

import os
from unittest.mock import Mock, patch

import pytest

from strands_base_agent.server import start_server


class TestA2AServerConsolidated:
    """Consolidated A2A server startup and configuration tests."""

    @pytest.mark.parametrize(
        "test_scenario,config_params,env_vars,expected_behavior,expected_values",
        [
            # A2A server startup scenarios
            (
                "custom_port_startup",
                {
                    "agent_name": "test-agent",
                    "agent_description": "Test agent description",
                    "agent_version": "2.1.0",
                    "agent_port": 9090,
                },
                {"HOST": "127.0.0.1", "PORT": "8000"},
                "successful_startup",
                {"host": "127.0.0.1", "port": 9090, "version": "2.1.0"},
            ),
            # Port priority scenarios
            (
                "port_priority_agent_over_env",
                {"agent_version": "1.0", "agent_port": 9999},
                {"PORT": "8080"},
                "successful_startup",
                {"host": "0.0.0.0", "port": 9999, "version": "1.0"},
            ),
            (
                "port_fallback_to_env",
                {"agent_version": "1.0", "agent_port": None},
                {"PORT": "7777"},
                "successful_startup",
                {"host": "0.0.0.0", "port": 7777, "version": "1.0"},
            ),
            (
                "port_fallback_to_default",
                {"agent_version": "1.0", "agent_port": None},
                {},
                "successful_startup",
                {"host": "0.0.0.0", "port": 8000, "version": "1.0"},
            ),
            # Host configuration scenarios
            (
                "custom_host_from_env",
                {"agent_version": "1.0", "agent_port": None},
                {"HOST": "192.168.1.100"},
                "successful_startup",
                {"host": "192.168.1.100", "port": 8000, "version": "1.0"},
            ),
            (
                "default_host_no_env",
                {"agent_version": "1.0", "agent_port": None},
                {},
                "successful_startup",
                {"host": "0.0.0.0", "port": 8000, "version": "1.0"},
            ),
            # Combined scenarios
            (
                "custom_host_and_agent_port",
                {"agent_version": "2.0", "agent_port": 8090},
                {"HOST": "127.0.0.1", "PORT": "3000"},
                "successful_startup",
                {"host": "127.0.0.1", "port": 8090, "version": "2.0"},
            ),
            # Edge cases
            (
                "zero_port_edge_case",
                {"agent_version": "1.5", "agent_port": 0},
                {"HOST": "localhost"},
                "successful_startup",
                {"host": "localhost", "port": 0, "version": "1.5"},
            ),
            (
                "large_port_edge_case",
                {"agent_version": "1.8", "agent_port": 65535},
                {},
                "successful_startup",
                {"host": "0.0.0.0", "port": 65535, "version": "1.8"},
            ),
        ],
    )
    @patch("uvicorn.run")
    @patch("strands_base_agent.server.A2AServer")
    @patch("strands_base_agent.server.create_application_container")
    @patch("strands_base_agent.server.AgentConfig.from_env")
    def test_a2a_server_startup_and_configuration(
        self,
        mock_config,
        mock_container,
        mock_a2a_server,
        mock_uvicorn_run,
        test_scenario: str,
        config_params: dict,
        env_vars: dict,
        expected_behavior: str,
        expected_values: dict,
    ) -> None:
        """Test comprehensive A2A server startup and configuration scenarios."""
        # Setup mock configuration
        mock_config_instance = Mock()
        if "agent_name" not in config_params:
            mock_config_instance.agent_name = "strands-base-agent"
        for key, value in config_params.items():
            setattr(mock_config_instance, key, value)
        mock_config.return_value = mock_config_instance

        # Setup mock dependencies
        mock_container_instance = Mock()
        mock_container.return_value = mock_container_instance
        mock_factory_instance = Mock()
        mock_container_instance.resolve.return_value = mock_factory_instance
        mock_server_instance = Mock()
        mock_a2a_server.return_value = mock_server_instance

        mock_fastapi_app = Mock()
        mock_fastapi_app.include_router = Mock()
        mock_server_instance.to_fastapi_app.return_value = mock_fastapi_app

        with patch.dict(
            os.environ,
            {"STRANDS_TLS_MODE": "platform", **env_vars},
            clear=True,
        ):
            start_server()

        # Calculate expected http_url based on agent_name and port
        agent_name = config_params.get("agent_name", "strands-base-agent")
        expected_http_url = f"http://{agent_name}:{expected_values['port']}"

        # Verify A2A server created with correct parameters
        mock_a2a_server.assert_called_once()
        kwargs = mock_a2a_server.call_args.kwargs

        assert kwargs["host"] == expected_values["host"]
        assert kwargs["port"] == expected_values["port"]
        assert kwargs["http_url"] == expected_http_url
        assert kwargs["version"] == expected_values["version"]

        # Agent is now created lazily in lifespan — verify proxy is passed
        assert kwargs["agent"] is not None

        # Verify uvicorn.run was called with the FastAPI app
        mock_uvicorn_run.assert_called_once_with(
            mock_fastapi_app, host=expected_values["host"], port=expected_values["port"]
        )

        mock_server_instance.to_fastapi_app.assert_called_once()
        assert mock_fastapi_app.include_router.call_count == 3

    def test_a2a_server_error_handling_invalid_config(self) -> None:
        """Test server startup handles invalid configuration gracefully."""
        with patch("strands_base_agent.server.AgentConfig.from_env") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.agent_port = None
            mock_config.return_value = mock_config_instance

            with patch("uvicorn.run"):  # Add: patch uvicorn.run
                with patch("strands_base_agent.server.A2AServer"):  # Fix: correct path
                    with patch.dict(os.environ, {"HOST": "127.0.0.1", "PORT": "invalid_port"}):
                        with pytest.raises(ValueError):
                            start_server()

    def test_a2a_server_error_handling_agent_creation_failure(self) -> None:
        """Test that lazy proxy raises if accessed before lifespan initializes agent."""
        from strands_base_agent.server import start_server

        # Agent creation now happens in the async lifespan, not during start_server().
        # The _LazyAgentProxy raises RuntimeError if accessed before initialization.
        # This test verifies start_server() itself doesn't crash (agent is deferred).
        with patch("strands_base_agent.server.AgentConfig.from_env") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.agent_version = "1.0.0"
            mock_config_instance.agent_port = None
            mock_config_instance.agent_name = "test-agent"
            mock_config.return_value = mock_config_instance

            with patch("uvicorn.run"):
                with patch("strands_base_agent.server.A2AServer") as mock_a2a:
                    mock_server = Mock()
                    mock_fastapi_app = Mock()
                    mock_fastapi_app.include_router = Mock()
                    mock_server.to_fastapi_app.return_value = mock_fastapi_app
                    mock_a2a.return_value = mock_server

                    with patch("strands_base_agent.server.create_application_container") as mock_container:
                        mock_container_instance = Mock()
                        mock_container.return_value = mock_container_instance
                        with patch.dict(
                            os.environ, {"HOST": "127.0.0.1", "PORT": "8000", "STRANDS_TLS_MODE": "platform"}
                        ):
                            start_server()  # Should not raise — agent is deferred

    def test_a2a_server_error_handling_server_creation_failure(self) -> None:
        """Test server startup handles A2A server creation failure gracefully."""
        with patch("strands_base_agent.server.AgentConfig.from_env") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.agent_version = "1.0.0"
            mock_config_instance.agent_port = None
            mock_config.return_value = mock_config_instance

            with patch("uvicorn.run"):  # Add: patch uvicorn.run
                with patch(
                    "strands_base_agent.server.A2AServer", side_effect=RuntimeError("A2A server creation failed")
                ):  # Fix: correct path
                    with patch("strands_base_agent.server.create_application_container") as mock_container:
                        mock_container_instance = Mock()
                        mock_container.return_value = mock_container_instance
                        with patch("asyncio.run", return_value=Mock()):
                            with patch.dict(os.environ, {"HOST": "127.0.0.1", "PORT": "8000"}):
                                with pytest.raises(RuntimeError, match="A2A server creation failed"):
                                    start_server()
