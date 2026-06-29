# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for agent card URL warning at startup."""

import logging
import os
from unittest.mock import Mock, patch

from strands_base_agent.server import start_server


class TestAgentCardUrlWarning:
    @patch("uvicorn.run")
    @patch("strands_base_agent.server.A2AServer")
    @patch("strands_base_agent.server.create_application_container")
    @patch("strands_base_agent.server.AgentConfig.from_env")
    @patch("asyncio.run")
    def test_warns_when_public_url_unset(
        self,
        mock_asyncio,
        mock_config,
        mock_container,
        mock_a2a_server,
        mock_uvicorn_run,
        caplog,
    ):
        mock_config_instance = Mock()
        mock_config_instance.agent_name = "strands-base-agent"
        mock_config_instance.agent_version = "1.0"
        mock_config_instance.agent_port = None
        mock_config.return_value = mock_config_instance

        mock_container_instance = Mock()
        mock_container.return_value = mock_container_instance
        mock_container_instance.resolve.return_value = Mock()
        mock_asyncio.return_value = Mock()

        mock_fastapi_app = Mock()
        mock_a2a_server.return_value.to_fastapi_app.return_value = mock_fastapi_app

        with patch.dict(
            os.environ,
            {"STRANDS_TLS_MODE": "platform"},
            clear=True,
        ):
            with caplog.at_level(logging.WARNING):
                start_server()

        assert any("STRANDS_AGENT_PUBLIC_URL is not set" in record.message for record in caplog.records)

    @patch("uvicorn.run")
    @patch("strands_base_agent.server.A2AServer")
    @patch("strands_base_agent.server.create_application_container")
    @patch("strands_base_agent.server.AgentConfig.from_env")
    @patch("asyncio.run")
    def test_no_warning_when_public_url_set(
        self,
        mock_asyncio,
        mock_config,
        mock_container,
        mock_a2a_server,
        mock_uvicorn_run,
        caplog,
    ):
        mock_config_instance = Mock()
        mock_config_instance.agent_name = "strands-base-agent"
        mock_config_instance.agent_version = "1.0"
        mock_config_instance.agent_port = None
        mock_config.return_value = mock_config_instance

        mock_container_instance = Mock()
        mock_container.return_value = mock_container_instance
        mock_container_instance.resolve.return_value = Mock()
        mock_asyncio.return_value = Mock()

        mock_fastapi_app = Mock()
        mock_a2a_server.return_value.to_fastapi_app.return_value = mock_fastapi_app

        with patch.dict(
            os.environ,
            {
                "STRANDS_TLS_MODE": "platform",
                "STRANDS_AGENT_PUBLIC_URL": "https://my-agent.example.com",
            },
            clear=True,
        ):
            with caplog.at_level(logging.WARNING):
                start_server()

        assert not any("STRANDS_AGENT_PUBLIC_URL is not set" in record.message for record in caplog.records)
